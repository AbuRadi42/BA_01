"""
compute_hl.py — Grammatical information content H(L) and structural
                recoverability rho(L) per language.

Implements the Week-1 numerical inputs for the framework derivation
(see manuscript/framework_math.md, sections 1, 3.3, 5.3).

For each language L:

    H_max(L)   = log2 |B(L)|                       upper bound (SSC)
    H(L)       = - sum_b p(b) log2 p(b)            corpus-weighted Shannon entropy
    rho_surf   = 1 - H(bundle | surface) / H(L)    recoverability from full surface
    rho_sig    = 1 - H(bundle | signature) / H(L)  recoverability from a root-stripped
                                                   surface signature (path A: templatic
                                                   skeleton for Arabic; surface minus
                                                   root for English and Turkish)

rho_surf is a degenerate upper bound: engines are deterministic over
their input, so H(bundle | surface) = 0 and rho_surf = 1 for any language.
It is reported only for auditability.

rho_sig is the working measurement. It simulates what a regular parser
without lexicon access would see: the grammatical structure visible in
the surface form after the root's lexical identity is abstracted away.
Ambiguity across different bundles sharing the same signature (e.g.
English noun-plural vs verb-3SG under "_s"; Arabic VERB_TRILATERAL_BARE
spanning multiple tense/voice combinations) produces H(bundle | signature) > 0.

Usage:
    python morph_efficiency_project/scripts/compute_hl.py
    python morph_efficiency_project/scripts/compute_hl.py --langs en ar tr
    python morph_efficiency_project/scripts/compute_hl.py --max-sentences 5000
    python morph_efficiency_project/scripts/compute_hl.py --corpus-root /some/path

Outputs:
    stdout: summary table.
    JSON:   manuscript/hl_metrics.json (timestamped run).

This script assumes each engine exposes:
    engine.analyze(word: str) -> TokenInfo
    TokenInfo.feature_bundle_str() -> str
as implemented in morph_efficiency_project/scripts/engines/.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from morph_efficiency_project.scripts.engines.en_engine import EnglishEngine
from morph_efficiency_project.scripts.engines.ar_engine import ArabicEngine
from morph_efficiency_project.scripts.engines.tr_engine import TurkishEngine
from morph_efficiency_project.scripts.engines.zh_engine import MandarinEngine
from morph_efficiency_project.scripts.engines.he_engine import HebrewEngine

ENGINES = {
    "en": EnglishEngine,
    "ar": ArabicEngine,
    "tr": TurkishEngine,
    "zh": MandarinEngine,
    "he": HebrewEngine,
}

# Languages whose signature should come from the engine's template field
# rather than a root-stripped surface. Arabic is the canonical templatic case;
# Hebrew is its Semitic twin and uses the same templatic-signature path.
TEMPLATIC_LANGS = {"ar", "he"}

DEFAULT_CORPUS_ROOT = ROOT / "mini_experiment" / "data"
DEFAULT_OUT = ROOT / "manuscript" / "hl_metrics.json"


def _whitespace_tokenize(line: str) -> list[str]:
    return [w for w in line.strip().split() if w]


def _jieba_tokenize(line: str) -> list[str]:
    # Lazy import so non-zh runs don't pay the startup cost or require the library.
    import jieba  # noqa: WPS433
    return [w for w in jieba.cut(line.strip()) if w and not w.isspace()]


def iter_words(corpus_path: Path, max_sentences: int, lang: str) -> list[str]:
    """Stream words from a line-per-sentence text file, up to max_sentences.

    Mandarin (`zh`) requires segmentation because surface text carries no
    whitespace between words; we use jieba, matching the tokenisation the
    Mandarin engine was designed to receive. All other languages use
    whitespace splitting.
    """
    tokenize = _jieba_tokenize if lang == "zh" else _whitespace_tokenize
    words: list[str] = []
    with corpus_path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= max_sentences:
                break
            words.extend(tokenize(line))
    return words


def shannon_entropy(counts: Counter) -> float:
    """Shannon entropy in bits from a Counter of event frequencies."""
    total = sum(counts.values())
    if total == 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        if c <= 0:
            continue
        p = c / total
        h -= p * math.log2(p)
    return h


def surface_signature(info, lang: str) -> str:
    """Root-stripped surface signature — path A from framework_math.md §3.3.

    For Arabic (templatic, non-concatenative): use the engine's template field
    directly; it already names the grammatical skeleton (e.g. VERB_TRILATERAL_BARE,
    NOM_DERIVED). Falls back to root-masked surface if template is empty.

    For English / Turkish (concatenative): strip the root from the surface.
    Falls back to the full surface if the root is not a substring (e.g. suppletive
    forms like went/go).
    """
    if lang in TEMPLATIC_LANGS:
        if info.template:
            return info.template
        if info.root:
            root_chars = set(info.root)
            return "".join("_" if c in root_chars else c for c in info.surface)
        return info.surface

    s = (info.surface or "").lower()
    if info.root:
        r = info.root.lower()
        if r and r in s:
            return s.replace(r, "_", 1)
    return s


def conditional_entropy(joint: dict[str, Counter]) -> float:
    """H(bundle | condition) given a dict mapping each condition value to its
    bundle-frequency Counter.
    """
    total_tokens = sum(sum(bc.values()) for bc in joint.values())
    if total_tokens == 0:
        return 0.0
    h = 0.0
    for bc in joint.values():
        n = sum(bc.values())
        if n == 0:
            continue
        h += (n / total_tokens) * shannon_entropy(bc)
    return h


def compute_for_language(lang: str, corpus_path: Path, max_sentences: int) -> dict:
    engine = ENGINES[lang]()
    words = iter_words(corpus_path, max_sentences, lang)

    bundles: Counter = Counter()
    by_surface: dict[str, Counter] = defaultdict(Counter)
    by_signature: dict[str, Counter] = defaultdict(Counter)
    n_analyzed = 0
    n_failed = 0

    for w in words:
        try:
            info = engine.analyze(w)
        except Exception:
            n_failed += 1
            continue
        bundle = info.feature_bundle_str()
        sig = surface_signature(info, lang)
        bundles[bundle] += 1
        by_surface[w][bundle] += 1
        by_signature[sig][bundle] += 1
        n_analyzed += 1

    observed_bundle_count = len(bundles)
    H_max_observed = math.log2(observed_bundle_count) if observed_bundle_count > 0 else 0.0
    H = shannon_entropy(bundles)

    H_cond_surf = conditional_entropy(by_surface)
    H_cond_sig = conditional_entropy(by_signature)

    rho_surf = (1.0 - H_cond_surf / H) if H > 1e-12 else float("nan")
    rho_sig = (1.0 - H_cond_sig / H) if H > 1e-12 else float("nan")

    return {
        "lang": lang,
        "tokens_analyzed": n_analyzed,
        "tokens_failed": n_failed,
        "unique_surface_forms": len(by_surface),
        "unique_signatures": len(by_signature),
        "unique_bundles_observed": observed_bundle_count,
        "H_max_observed_bits": H_max_observed,
        "H_bits": H,
        "H_cond_surface_bits": H_cond_surf,
        "H_cond_signature_bits": H_cond_sig,
        "rho_surface": rho_surf,
        "rho_signature": rho_sig,
        "rho_sig_times_H_bits": rho_sig * H if not math.isnan(rho_sig) else float("nan"),
    }


def print_table(results: list[dict]) -> None:
    def fmt(x, w=10, p=3):
        if isinstance(x, float):
            if math.isnan(x):
                return f"{'nan':>{w}}"
            return f"{x:>{w}.{p}f}"
        return f"{x:>{w}}"

    cols = [
        ("Lang",      "lang",                     6,  None),
        ("Tokens",    "tokens_analyzed",          9,  0),
        ("|B| obs",   "unique_bundles_observed",  9,  0),
        ("Sigs",      "unique_signatures",        7,  0),
        ("H_max",     "H_max_observed_bits",      7,  2),
        ("H",         "H_bits",                   7,  2),
        ("H(b|sig)",  "H_cond_signature_bits",    9,  2),
        ("rho_sig",   "rho_signature",            8,  3),
        ("rho_sig*H", "rho_sig_times_H_bits",     9,  2),
    ]
    header = " ".join(f"{name:>{w}}" for name, _, w, _ in cols)
    print(header)
    print("-" * len(header))
    for r in results:
        parts = []
        for _name, key, w, p in cols:
            v = r[key]
            if p is None:
                parts.append(f"{v:>{w}}")
            elif isinstance(v, float):
                parts.append(fmt(v, w, p))
            else:
                parts.append(f"{v:>{w}}")
        print(" ".join(parts))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--langs", nargs="+", default=list(ENGINES.keys()),
        choices=list(ENGINES.keys()),
        help="Languages to analyze.",
    )
    parser.add_argument(
        "--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT,
        help="Directory containing <lang>_train.txt files.",
    )
    parser.add_argument(
        "--split", choices=("train", "val", "test"), default="train",
        help="Which corpus split to use.",
    )
    parser.add_argument(
        "--max-sentences", type=int, default=20_000,
        help="Max sentences to sample per language (for fast iteration).",
    )
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT,
        help="JSON output path.",
    )
    args = parser.parse_args()

    results = []
    for lang in args.langs:
        corpus_path = args.corpus_root / f"{lang}_{args.split}.txt"
        if not corpus_path.exists():
            print(f"[{lang}] corpus not found: {corpus_path} — skipping", file=sys.stderr)
            continue
        print(f"[{lang}] analyzing {corpus_path} (max {args.max_sentences} sentences)...", file=sys.stderr)
        results.append(compute_for_language(lang, corpus_path, args.max_sentences))

    if not results:
        print("no results — did you pass valid --corpus-root?", file=sys.stderr)
        return 1

    print_table(results)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "split": args.split,
        "max_sentences": args.max_sentences,
        "corpus_root": str(args.corpus_root),
        "results": results,
    }
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
