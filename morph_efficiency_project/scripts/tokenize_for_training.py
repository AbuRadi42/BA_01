"""
tokenize_for_training.py
========================

Post-engine tokenizer construction pipeline for the LM training experiments
across {zh, en, tr, ar}. This is Tier 1 item 1 of the AWS-readiness roadmap
and subsumes both the phase-1 logic in mini_experiment/run_mini.py and the
engine-backed prototypes in tokenize_morph_engine.py / tokenize_tier2_ar.py.

For each language it produces:

Baseline stream (BPE-style, surface-only, capped at 32k):
    mini_experiment/tokenizers/<lang>_baseline_vocab.json
    mini_experiment/data/<lang>_baseline_<split>.npy

Morph surface stream (engine root+bundle composite token, capped at 32k):
    mini_experiment/tokenizers/<lang>_morph_surface_vocab.json
    mini_experiment/data/<lang>_morph_<split>.npy

Morph feature-bundle stream (uncapped):
    mini_experiment/tokenizers/<lang>_morph_bundle_vocab.json
    mini_experiment/data/<lang>_morph_feat_<split>.npy

AR only, root and wazn streams:
    mini_experiment/tokenizers/ar_morph_root_vocab.json  (~7,142 from ar_roots.json)
    mini_experiment/tokenizers/ar_morph_wazn_vocab.json  (185 semantic_role values)
    mini_experiment/data/ar_morph_root_<split>.npy
    mini_experiment/data/ar_morph_wazn_<split>.npy

ZH only, Kangxi radical stream (214 entries):
    mini_experiment/tokenizers/zh_morph_radical_vocab.json
    mini_experiment/data/zh_morph_radical_<split>.npy

All streams use np.int32 with reserved IDs: <pad>=0, <unk>=1, <s>=2, </s>=3.
Idempotent: re-running skips splits whose .npy already exists unless --force.

Usage:
    python morph_efficiency_project/scripts/tokenize_for_training.py --smoke
    python morph_efficiency_project/scripts/tokenize_for_training.py --full
    python morph_efficiency_project/scripts/tokenize_for_training.py --full --force --langs ar zh
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from morph_efficiency_project.scripts.engines.ar_engine import ArabicEngine
from morph_efficiency_project.scripts.engines.en_engine import EnglishEngine
from morph_efficiency_project.scripts.engines.tr_engine import TurkishEngine
from morph_efficiency_project.scripts.engines.zh_engine import MandarinEngine
from morph_efficiency_project.scripts.engines.he_engine import HebrewEngine
from morph_efficiency_project.scripts.engines.shared import TokenInfo

# Sentence-grammar layer: context-aware POS resolution. disambiguate_pos takes
# the line's token list and rewrites POS/tags in place against neighbours, so a
# homograph (EN "run" NOUN-vs-VERB, ZH 把 classifier-vs-ADP, TR "evin"
# GEN-vs-2SG-poss, AR case under نواسخ) gets the contextually correct bundle.
from morph_efficiency_project.scripts.engines.grammar.ar_grammar import (
    disambiguate_pos as _ar_disambiguate,
)
from morph_efficiency_project.scripts.engines.grammar.en_grammar import (
    disambiguate_pos as _en_disambiguate,
)
from morph_efficiency_project.scripts.engines.grammar.tr_grammar import (
    disambiguate_pos as _tr_disambiguate,
)
from morph_efficiency_project.scripts.engines.grammar.zh_grammar import (
    disambiguate_pos as _zh_disambiguate,
)

DISAMBIGUATORS = {
    "ar": _ar_disambiguate,
    "en": _en_disambiguate,
    "tr": _tr_disambiguate,
    "zh": _zh_disambiguate,
}

ENGINES = {
    "en": EnglishEngine,
    "ar": ArabicEngine,
    "tr": TurkishEngine,
    "zh": MandarinEngine,
    "he": HebrewEngine,
}

DATA_DIR = ROOT / "mini_experiment" / "data"
TOK_DIR = ROOT / "mini_experiment" / "tokenizers"
CFG_DIR = ROOT / "morph_efficiency_project" / "configs"

SPECIALS = {"<pad>": 0, "<unk>": 1, "<s>": 2, "</s>": 3}
PAD, UNK, BOS, EOS = 0, 1, 2, 3

BASELINE_CAP = 32_000
MORPH_SURFACE_CAP = 32_000

SPLITS = ("train", "val", "test")


# ---------------------------------------------------------------------------
# Heartbeat / logging
# ---------------------------------------------------------------------------

def hb(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Corpus iteration
# ---------------------------------------------------------------------------

def iter_lines(path: Path, limit: int | None = None) -> Iterable[str]:
    n = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield line
            n += 1
            if limit is not None and n >= limit:
                return


def tokenize_words(line: str, lang: str) -> List[str]:
    """Whitespace tokenisation for EN/AR/TR; per-character for ZH."""
    if lang == "zh":
        # Engine analyses per Han character. Non-Han characters are passed
        # through as their own tokens so the stream still aligns to the corpus.
        return [ch for ch in line if not ch.isspace()]
    return [w for w in line.split() if w]


# ---------------------------------------------------------------------------
# Vocab helpers
# ---------------------------------------------------------------------------

def make_vocab(counter: Counter, cap: int | None) -> Dict[str, int]:
    """Build a token -> id mapping seeded with specials, ordered by frequency."""
    vocab = dict(SPECIALS)
    items = counter.most_common()
    if cap is not None:
        items = items[: max(cap - len(SPECIALS), 0)]
    for tok, _ in items:
        if tok in vocab:
            continue
        vocab[tok] = len(vocab)
    return vocab


def save_vocab(vocab: Dict[str, int], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(vocab, ensure_ascii=False), encoding="utf-8")


def load_vocab(path: Path) -> Dict[str, int]:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Engine output extraction
# ---------------------------------------------------------------------------

# Per-(lang, surface) memoisation of the *morphology* (the expensive
# engine.analyze() call). Real-world corpora are heavily Zipfian: the same
# function words appear thousands of times. Caching the TokenInfo by surface
# form (within a language) means each unique surface is analysed once. This is
# what makes Turkish tractable (full corpus ~30h -> ~16min); do NOT remove it.
#
# Context-aware POS resolution happens AFTER the cache, on per-token shallow
# copies (see analyze_line). The cached TokenInfo objects are shared and must
# never be mutated, or disambiguation of one line would poison every later
# occurrence of that surface form ("cache poisoning").
_INFO_CACHE: Dict[Tuple[str, str], TokenInfo] = {}

# Sentinel marker for a surface the engine could not analyse. Stored as a
# TokenInfo so the cache stays homogeneous and disambiguators see a real token.
_NO_FEAT_POS = "UNKNOWN"


def _analyze_cached(engine, word: str, lang: str) -> TokenInfo:
    """Return the engine's TokenInfo for `word`, memoised per (lang, surface).

    The returned object is the shared cached instance: callers that intend to
    mutate POS/tags (disambiguation) must copy it first. Each unique surface
    is analysed at most once per run.
    """
    key = (lang, word)
    hit = _INFO_CACHE.get(key)
    if hit is not None:
        return hit
    try:
        info = engine.analyze(word)
    except Exception:
        info = TokenInfo(surface=word, clitics={}, template="",
                         root=word, tags={}, pos=_NO_FEAT_POS, derived_chain=[])
    _INFO_CACHE[key] = info
    return info


def _streams_from_info(info: TokenInfo, word: str, lang: str
                       ) -> Tuple[str, str, str, str]:
    """Extract (surface_composite, bundle, root, wazn_or_radical) from a
    (possibly context-disambiguated) TokenInfo.

    surface_composite: "<root>+<bundle>" composite morph surface token.
    bundle:            feature_bundle_str (reflects context POS after disambig).
    root:              info.root or surface fallback.
    wazn_or_radical:   AR semantic_role (wazn class); ZH radical; else "".
    """
    root = info.root or word
    bundle = info.feature_bundle_str()
    surface_composite = f"{root}+{bundle}"
    wazn_radical = ""
    if lang == "ar":
        wazn_radical = info.tags.get("semantic_role") or info.tags.get("wazn_class") or ""
    elif lang == "he":
        # Hebrew's 4th stream is the binyan (verbal pattern), the structural
        # analogue of Arabic's wazn semantic_role.
        wazn_radical = info.tags.get("binyan") or ""
    elif lang == "zh":
        wazn_radical = info.tags.get("radical") or ""
    return surface_composite, bundle, root, wazn_radical


def analyze_line(engine, words: List[str], lang: str) -> List[TokenInfo]:
    """Analyse a whole corpus line and return CONTEXT-RESOLVED TokenInfo objects.

    Per the design that preserves the speed cache:
      1. Look up each word's morphology from the per-surface cache (one
         engine.analyze() per unique surface, ever).
      2. Shallow-copy each cached TokenInfo with a fresh tags dict so the
         disambiguator can mutate POS/tags without poisoning the shared cache.
      3. Run the language's disambiguate_pos over the copies. It rewrites
         POS/tags in place and returns the same-length list, so token alignment
         across the surface/feat/root/wazn streams is preserved.
    """
    copies: List[TokenInfo] = []
    for w in words:
        cached = _analyze_cached(engine, w, lang)
        copies.append(dataclasses.replace(cached, tags=dict(cached.tags)))
    disambiguate = DISAMBIGUATORS.get(lang)
    if disambiguate is not None and copies:
        try:
            copies = disambiguate(copies)
        except Exception:
            # A grammar-layer failure must never abort tokenisation; fall back
            # to the context-free (already-copied) analyses for this line.
            pass
    return copies


def analyze_token(engine, word: str, lang: str) -> Tuple[str, str, str, str]:
    """Context-FREE single-word extraction. Retained for spot-checks only;
    the training streams go through analyze_line for context resolution.
    """
    return _streams_from_info(_analyze_cached(engine, word, lang), word, lang)


# ---------------------------------------------------------------------------
# Pre-built vocabularies for closed-set streams
# ---------------------------------------------------------------------------

def load_ar_root_vocab() -> Dict[str, int]:
    """Closed-set Arabic root vocabulary from ar_roots.json."""
    data = json.loads((CFG_DIR / "ar_roots.json").read_text(encoding="utf-8"))
    roots = data.get("roots", []) if isinstance(data, dict) else data
    vocab = dict(SPECIALS)
    for r in roots:
        if r not in vocab:
            vocab[r] = len(vocab)
    return vocab


def load_ar_wazn_vocab() -> Dict[str, int]:
    """Wazn vocab from ar_templates.json:semantic_role values."""
    data = json.loads((CFG_DIR / "ar_templates.json").read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("templates", [])
    seen = set()
    classes: List[str] = []
    for t in items:
        if not isinstance(t, dict):
            continue
        sr = t.get("semantic_role")
        if sr and sr not in seen:
            seen.add(sr)
            classes.append(sr)
    vocab = dict(SPECIALS)
    for c in classes:
        vocab[c] = len(vocab)
    return vocab


def load_zh_radical_vocab() -> Dict[str, int]:
    """Reserve a slot for each Kangxi index 1..214 so the vocab stays stable
    even when the project's zh_radicals.json ships only a partial char map.
    """
    data = json.loads((CFG_DIR / "zh_radicals.json").read_text(encoding="utf-8"))
    radicals = data.get("radicals", {})
    vocab = dict(SPECIALS)
    for idx in range(1, 215):
        key = str(idx)
        meta = radicals.get(key, {})
        form = meta.get("radical") or meta.get("form") or f"#{idx}"
        token = form if form not in vocab else f"{form}#{idx}"
        vocab[token] = len(vocab)
    return vocab


def zh_radical_token(engine, char: str, vocab: Dict[str, int]) -> int:
    """Look up the Kangxi-radical slot id for a Han character."""
    entry = getattr(engine, "_char_to_radical", {}).get(char)
    if not entry:
        return UNK
    idx = entry.get("kangxi_index") if isinstance(entry, dict) else None
    if idx is None:
        return UNK
    rad_meta = getattr(engine, "_radicals", {}).get(str(idx), {})
    form = rad_meta.get("radical") or rad_meta.get("form") or f"#{idx}"
    token = form if form in vocab else f"{form}#{idx}"
    return vocab.get(token, UNK)


# ---------------------------------------------------------------------------
# Baseline (whitespace surface) tokenizer
# ---------------------------------------------------------------------------

def build_baseline_vocab(lang: str, max_lines: int | None) -> Dict[str, int]:
    counter: Counter = Counter()
    train_path = DATA_DIR / f"{lang}_train.txt"
    for line in iter_lines(train_path, limit=max_lines):
        for tok in tokenize_words(line, lang):
            counter[tok] += 1
    return make_vocab(counter, cap=BASELINE_CAP)


def encode_baseline_split(lang: str, split: str, vocab: Dict[str, int],
                          max_lines: int | None) -> np.ndarray:
    out: List[int] = []
    path = DATA_DIR / f"{lang}_{split}.txt"
    for line in iter_lines(path, limit=max_lines):
        out.append(BOS)
        for tok in tokenize_words(line, lang):
            out.append(vocab.get(tok, UNK))
        out.append(EOS)
    return np.asarray(out, dtype=np.int32)


# ---------------------------------------------------------------------------
# Morph passes
# ---------------------------------------------------------------------------

def first_pass_morph(lang: str, engine, max_lines: int | None
                     ) -> Tuple[Dict[str, int], Dict[str, int]]:
    """Single scan of train corpus to build morph surface + bundle vocabularies."""
    surface_counter: Counter = Counter()
    bundle_vocab: Dict[str, int] = dict(SPECIALS)
    bundle_vocab["no_features"] = len(bundle_vocab)

    train_path = DATA_DIR / f"{lang}_train.txt"
    n_lines = 0
    for line in iter_lines(train_path, limit=max_lines):
        words = tokenize_words(line, lang)
        infos = analyze_line(engine, words, lang)
        for word, info in zip(words, infos):
            surface, bundle, _root, _wazn = _streams_from_info(info, word, lang)
            surface_counter[surface] += 1
            if bundle not in bundle_vocab:
                bundle_vocab[bundle] = len(bundle_vocab)
        n_lines += 1
        if n_lines % 5000 == 0:
            hb(f"[{lang}/morph-scan] {n_lines:,} lines, "
               f"|surface|={len(surface_counter):,} |bundle|={len(bundle_vocab):,}")

    surface_vocab = make_vocab(surface_counter, cap=MORPH_SURFACE_CAP)
    return surface_vocab, bundle_vocab


def encode_morph_split(lang: str, split: str, engine,
                       surface_vocab: Dict[str, int],
                       bundle_vocab: Dict[str, int],
                       root_vocab: Dict[str, int] | None,
                       wazn_vocab: Dict[str, int] | None,
                       radical_vocab: Dict[str, int] | None,
                       max_lines: int | None) -> Dict[str, np.ndarray]:
    tok_ids: List[int] = []
    feat_ids: List[int] = []
    root_ids: List[int] = []
    wazn_ids: List[int] = []
    rad_ids: List[int] = []

    do_root = root_vocab is not None
    do_wazn = wazn_vocab is not None
    do_rad = radical_vocab is not None

    path = DATA_DIR / f"{lang}_{split}.txt"
    n_lines = 0
    for line in iter_lines(path, limit=max_lines):
        tok_ids.append(BOS); feat_ids.append(BOS)
        if do_root: root_ids.append(BOS)
        if do_wazn: wazn_ids.append(BOS)
        if do_rad:  rad_ids.append(BOS)
        words = tokenize_words(line, lang)
        infos = analyze_line(engine, words, lang)
        for word, info in zip(words, infos):
            surface, bundle, root, wazn_or_rad = _streams_from_info(info, word, lang)
            tok_ids.append(surface_vocab.get(surface, UNK))
            feat_ids.append(bundle_vocab.get(bundle, UNK))
            if do_root:
                root_ids.append(root_vocab.get(root, UNK))
            if do_wazn:
                # PAD (=0) means no wazn applies to this token.
                wazn_ids.append(wazn_vocab.get(wazn_or_rad, UNK) if wazn_or_rad else PAD)
            if do_rad:
                rad_ids.append(zh_radical_token(engine, word, radical_vocab))
        tok_ids.append(EOS); feat_ids.append(EOS)
        if do_root: root_ids.append(EOS)
        if do_wazn: wazn_ids.append(EOS)
        if do_rad:  rad_ids.append(EOS)
        n_lines += 1
        if n_lines % 5000 == 0:
            hb(f"[{lang}/morph-enc/{split}] {n_lines:,} lines, "
               f"{len(tok_ids):,} tokens")

    streams: Dict[str, np.ndarray] = {
        "morph": np.asarray(tok_ids, dtype=np.int32),
        "morph_feat": np.asarray(feat_ids, dtype=np.int32),
    }
    if do_root:
        streams["morph_root"] = np.asarray(root_ids, dtype=np.int32)
    if do_wazn:
        streams["morph_wazn"] = np.asarray(wazn_ids, dtype=np.int32)
    if do_rad:
        streams["morph_radical"] = np.asarray(rad_ids, dtype=np.int32)
    return streams


# ---------------------------------------------------------------------------
# Per-language driver
# ---------------------------------------------------------------------------

def count_source(lang: str, split: str, max_lines: int | None) -> tuple:
    """Count source characters, words, and lines for a split, using the SAME
    line budget as encoding. Needed to convert per-token loss into the
    tokeniser-fair bits-per-character metric, and to report fertility."""
    p = DATA_DIR / f"{lang}_{split}.txt"
    n_chars = n_words = n_lines = 0
    if not p.exists():
        return 0, 0, 0
    with p.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if max_lines is not None and i >= max_lines:
                break
            s = line.strip()
            n_chars += len(s)
            n_words += len(tokenize_words(s, lang))
            n_lines += 1
    return n_chars, n_words, n_lines


def process_language(lang: str, max_lines: int | None, force: bool) -> dict:
    hb(f"[{lang}] start (max_lines={max_lines}, force={force})")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TOK_DIR.mkdir(parents=True, exist_ok=True)

    # Baseline.
    baseline_vocab_path = TOK_DIR / f"{lang}_baseline_vocab.json"
    baseline_paths = {s: DATA_DIR / f"{lang}_baseline_{s}.npy" for s in SPLITS}
    baseline_done = baseline_vocab_path.exists() and all(p.exists() for p in baseline_paths.values())
    if baseline_done and not force:
        baseline_vocab = load_vocab(baseline_vocab_path)
        hb(f"[{lang}/baseline] cached: |V|={len(baseline_vocab):,}")
    else:
        hb(f"[{lang}/baseline] building vocab")
        baseline_vocab = build_baseline_vocab(lang, max_lines)
        save_vocab(baseline_vocab, baseline_vocab_path)
        hb(f"[{lang}/baseline] |V|={len(baseline_vocab):,}; encoding splits")
        for split in SPLITS:
            arr = encode_baseline_split(lang, split, baseline_vocab, max_lines)
            np.save(baseline_paths[split], arr)
            hb(f"[{lang}/baseline/{split}] {len(arr):,} tokens")

    # Morph.
    engine = ENGINES[lang]()

    surface_vocab_path = TOK_DIR / f"{lang}_morph_surface_vocab.json"
    bundle_vocab_path = TOK_DIR / f"{lang}_morph_bundle_vocab.json"
    morph_outputs = {s: DATA_DIR / f"{lang}_morph_{s}.npy" for s in SPLITS}
    feat_outputs = {s: DATA_DIR / f"{lang}_morph_feat_{s}.npy" for s in SPLITS}

    root_vocab = wazn_vocab = radical_vocab = None
    root_outputs: Dict[str, Path] = {}
    wazn_outputs: Dict[str, Path] = {}
    rad_outputs: Dict[str, Path] = {}
    extra_vocab_paths: Dict[str, Path] = {}

    if lang == "ar":
        root_vocab = load_ar_root_vocab()
        wazn_vocab = load_ar_wazn_vocab()
        root_outputs = {s: DATA_DIR / f"ar_morph_root_{s}.npy" for s in SPLITS}
        wazn_outputs = {s: DATA_DIR / f"ar_morph_wazn_{s}.npy" for s in SPLITS}
        extra_vocab_paths["root"] = TOK_DIR / "ar_morph_root_vocab.json"
        extra_vocab_paths["wazn"] = TOK_DIR / "ar_morph_wazn_vocab.json"
    if lang == "zh":
        radical_vocab = load_zh_radical_vocab()
        rad_outputs = {s: DATA_DIR / f"zh_morph_radical_{s}.npy" for s in SPLITS}
        extra_vocab_paths["radical"] = TOK_DIR / "zh_morph_radical_vocab.json"

    morph_done = (
        surface_vocab_path.exists()
        and bundle_vocab_path.exists()
        and all(p.exists() for p in morph_outputs.values())
        and all(p.exists() for p in feat_outputs.values())
        and (not root_outputs or all(p.exists() for p in root_outputs.values()))
        and (not wazn_outputs or all(p.exists() for p in wazn_outputs.values()))
        and (not rad_outputs or all(p.exists() for p in rad_outputs.values()))
    )

    if morph_done and not force:
        surface_vocab = load_vocab(surface_vocab_path)
        bundle_vocab = load_vocab(bundle_vocab_path)
        if lang == "ar":
            root_vocab = load_vocab(extra_vocab_paths["root"])
            wazn_vocab = load_vocab(extra_vocab_paths["wazn"])
        if lang == "zh":
            radical_vocab = load_vocab(extra_vocab_paths["radical"])
        hb(f"[{lang}/morph] cached: "
           f"surface={len(surface_vocab):,} bundle={len(bundle_vocab):,}")
    else:
        hb(f"[{lang}/morph] first pass over train")
        surface_vocab, bundle_vocab = first_pass_morph(lang, engine, max_lines)
        save_vocab(surface_vocab, surface_vocab_path)
        save_vocab(bundle_vocab, bundle_vocab_path)
        if lang == "ar":
            save_vocab(root_vocab, extra_vocab_paths["root"])
            save_vocab(wazn_vocab, extra_vocab_paths["wazn"])
        if lang == "zh":
            save_vocab(radical_vocab, extra_vocab_paths["radical"])

        for split in SPLITS:
            streams = encode_morph_split(
                lang, split, engine,
                surface_vocab, bundle_vocab,
                root_vocab if lang == "ar" else None,
                wazn_vocab if lang == "ar" else None,
                radical_vocab if lang == "zh" else None,
                max_lines,
            )
            np.save(morph_outputs[split], streams["morph"])
            np.save(feat_outputs[split], streams["morph_feat"])
            if lang == "ar":
                np.save(root_outputs[split], streams["morph_root"])
                np.save(wazn_outputs[split], streams["morph_wazn"])
            if lang == "zh":
                np.save(rad_outputs[split], streams["morph_radical"])
            hb(f"[{lang}/morph/{split}] {len(streams['morph']):,} tokens")

    summary: dict = {
        "lang": lang,
        "baseline_vocab": len(baseline_vocab),
        "morph_surface_vocab": len(surface_vocab),
        "morph_bundle_vocab": len(bundle_vocab),
        "tokens": {},
    }
    if lang == "ar":
        summary["morph_root_vocab"] = len(root_vocab)
        summary["morph_wazn_vocab"] = len(wazn_vocab)
    if lang == "zh":
        summary["morph_radical_vocab"] = len(radical_vocab)
    for split in SPLITS:
        summary["tokens"][split] = {
            "baseline": int(np.load(baseline_paths[split]).shape[0]),
            "morph": int(np.load(morph_outputs[split]).shape[0]),
        }

    # --- source-text counts + tokeniser fertility (paper figures) ---------
    summary["source"] = {}
    summary["fertility"] = {}
    for split in SPLITS:
        n_chars, n_words, n_lines = count_source(lang, split, max_lines)
        bt = summary["tokens"][split]["baseline"]
        mt = summary["tokens"][split]["morph"]
        summary["source"][split] = {
            "chars": n_chars, "words": n_words, "lines": n_lines}
        summary["fertility"][split] = {
            "baseline_tok_per_word": bt / max(1, n_words),
            "morph_tok_per_word": mt / max(1, n_words),
            "baseline_tok_per_char": bt / max(1, n_chars),
            "morph_tok_per_char": mt / max(1, n_chars),
        }

    # --- persist the stats sidecar (read by the trainer for bpc; plotted) -
    stats_path = DATA_DIR / f"{lang}_tokstats.json"
    stats_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    hb(f"[{lang}] wrote {stats_path.name} (chars/words/fertility)")
    return summary


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def smoke_check(lang: str, summary: dict) -> List[str]:
    """Re-load each emitted .npy, confirm dtype / range / shape invariants."""
    issues: List[str] = []
    streams: Dict[str, int] = {
        "baseline": summary["baseline_vocab"],
        "morph": summary["morph_surface_vocab"],
        "morph_feat": summary["morph_bundle_vocab"],
    }
    if lang == "ar":
        streams["morph_root"] = summary["morph_root_vocab"]
        streams["morph_wazn"] = summary["morph_wazn_vocab"]
    if lang == "zh":
        streams["morph_radical"] = summary["morph_radical_vocab"]

    for split in SPLITS:
        for stream, vsize in streams.items():
            path = DATA_DIR / f"{lang}_{stream}_{split}.npy"
            if not path.exists():
                issues.append(f"missing {path.name}")
                continue
            arr = np.load(path)
            if arr.dtype != np.int32:
                issues.append(f"{path.name} dtype={arr.dtype}")
            if arr.size == 0:
                issues.append(f"{path.name} empty")
                continue
            if int(arr.min()) < 0:
                issues.append(f"{path.name} has negatives")
            if int(arr.max()) >= vsize:
                issues.append(f"{path.name} max={arr.max()} >= |V|={vsize}")
    return issues


def random_spot_check(lang: str, engine, n: int = 5) -> List[str]:
    train_path = DATA_DIR / f"{lang}_train.txt"
    words: List[str] = []
    with train_path.open("r", encoding="utf-8") as f:
        for line in f:
            words.extend(tokenize_words(line.strip(), lang))
            if len(words) > 2000:
                break
    sample = random.sample(words, min(n, len(words)))
    out = []
    for w in sample:
        surface, bundle, root, extra = analyze_token(engine, w, lang)
        out.append(f"  {w!r}: root={root!r} bundle={bundle!r} extra={extra!r}")
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_summary_table(summaries: List[dict]) -> None:
    print()
    print("=" * 88)
    print(f"{'lang':<6}{'stream':<22}{'|V|':>10}{'train':>14}{'val':>10}{'test':>10}")
    print("-" * 88)
    for s in summaries:
        lang = s["lang"]
        rows = [
            ("baseline", s["baseline_vocab"], "baseline"),
            ("morph_surface", s["morph_surface_vocab"], "morph"),
            ("morph_bundle", s["morph_bundle_vocab"], "morph"),
        ]
        if lang == "ar":
            rows.append(("morph_root", s["morph_root_vocab"], "morph"))
            rows.append(("morph_wazn", s["morph_wazn_vocab"], "morph"))
        if lang == "zh":
            rows.append(("morph_radical", s["morph_radical_vocab"], "morph"))
        for name, vsize, token_key in rows:
            t = s["tokens"]["train"][token_key]
            v = s["tokens"]["val"][token_key]
            te = s["tokens"]["test"][token_key]
            print(f"{lang:<6}{name:<22}{vsize:>10,}{t:>14,}{v:>10,}{te:>10,}")
        print("-" * 88)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", nargs="+", default=["zh", "en", "tr", "ar"],
                    choices=list(ENGINES.keys()))
    ap.add_argument("--smoke", action="store_true",
                    help="Process only 100 lines per split for fast iteration.")
    ap.add_argument("--full", action="store_true",
                    help="Process all lines (production run).")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite cached vocabularies and stream files.")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    if args.smoke and args.full:
        ap.error("--smoke and --full are mutually exclusive")
    max_lines: int | None = 100 if args.smoke else None

    random.seed(args.seed)

    summaries: List[dict] = []
    for lang in args.langs:
        t0 = time.time()
        summary = process_language(lang, max_lines, args.force)
        summaries.append(summary)
        hb(f"[{lang}] done in {time.time()-t0:.1f}s")

        issues = smoke_check(lang, summary)
        if issues:
            hb(f"[{lang}] SMOKE ISSUES:")
            for it in issues:
                hb(f"   - {it}")
        else:
            hb(f"[{lang}] smoke check OK")

        engine = ENGINES[lang]()
        hb(f"[{lang}] 5-word spot check:")
        for line in random_spot_check(lang, engine, n=5):
            hb(line)

    print_summary_table(summaries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
