"""
tokenize_morph_engine.py — Engine-backed morph tokenizer for all nine
languages in the scale-ladder plan.

The current mini_experiment/run_mini.py implements morph tokenisation only
for English, Arabic, and Turkish, via hand-written affix lists. This
script provides a general replacement that uses the language-specific
grammar engines (morph_efficiency_project/scripts/engines/*) directly.
Every engine exposes TokenInfo with a root and a feature-bundle string,
which is exactly what the morph training regime needs.

Output format matches tokenize_morph in run_mini.py:
    mini_experiment/data/{lang}_morph_{train,val,test}.npy         # root token IDs
    mini_experiment/data/{lang}_morph_feat_{train,val,test}.npy    # bundle IDs
    mini_experiment/tokenizers/{lang}_morph_vocab.json             # root -> id
    mini_experiment/tokenizers/{lang}_morph_bundles.json           # bundle -> id

Cached: per language, per split. Idempotent.

Usage:
    python morph_efficiency_project/scripts/tokenize_morph_engine.py --lang de
    python morph_efficiency_project/scripts/tokenize_morph_engine.py --langs de es hu sw eu zh
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from morph_efficiency_project.scripts.engines.en_engine import EnglishEngine
from morph_efficiency_project.scripts.engines.ar_engine import ArabicEngine
from morph_efficiency_project.scripts.engines.tr_engine import TurkishEngine
from morph_efficiency_project.scripts.engines.zh_engine import MandarinEngine

ENGINES = {
    "en": EnglishEngine, "ar": ArabicEngine, "tr": TurkishEngine,
    "zh": MandarinEngine,
}

DATA_DIR = ROOT / "mini_experiment" / "data"
TOK_DIR = ROOT / "mini_experiment" / "tokenizers"
VOCAB_CAP = 50_000

SPECIALS = {"<pad>": 0, "<unk>": 1, "<s>": 2, "</s>": 3}


def _tokenize_line(line: str, lang: str):
    if lang == "zh":
        import jieba
        return [w for w in jieba.cut(line.strip()) if w and not w.isspace()]
    return [w for w in line.strip().split() if w]


def _encode(line: str, lang: str, engine, token2id: dict, bundle2id: dict,
            build_vocab: bool) -> tuple[list[int], list[int]]:
    tok_ids: list[int] = [SPECIALS["<s>"]]
    feat_ids: list[int] = [0]
    for word in _tokenize_line(line, lang):
        try:
            info = engine.analyze(word)
            root = info.root or word
            bundle = info.feature_bundle_str()
        except Exception:
            root = word
            bundle = "no_features"
        surface = f"{root}+{bundle}"
        if build_vocab:
            if surface not in token2id:
                token2id[surface] = len(token2id)
            if bundle not in bundle2id:
                bundle2id[bundle] = len(bundle2id)
        tok_ids.append(token2id.get(surface, SPECIALS["<unk>"]))
        feat_ids.append(bundle2id.get(bundle, 0))
    tok_ids.append(SPECIALS["</s>"])
    feat_ids.append(0)
    return tok_ids, feat_ids


def _encode_file(path: Path, lang: str, engine, token2id: dict, bundle2id: dict,
                 build_vocab: bool):
    tok, feat = [], []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            t, g = _encode(line, lang, engine, token2id, bundle2id, build_vocab)
            tok.extend(t)
            feat.extend(g)
    return np.array(tok, dtype=np.int32), np.array(feat, dtype=np.int32)


def tokenize(lang: str, force: bool = False) -> dict:
    if lang not in ENGINES:
        raise ValueError(f"unknown language: {lang}")

    TOK_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    vocab_path = TOK_DIR / f"{lang}_morph_vocab.json"
    bundles_path = TOK_DIR / f"{lang}_morph_bundles.json"

    all_exist = all(
        (DATA_DIR / f"{lang}_morph_{split}.npy").exists()
        and (DATA_DIR / f"{lang}_morph_feat_{split}.npy").exists()
        for split in ("train", "val", "test")
    ) and vocab_path.exists() and bundles_path.exists()

    if all_exist and not force:
        vocab = json.loads(vocab_path.read_text(encoding="utf-8"))
        bundles = json.loads(bundles_path.read_text(encoding="utf-8"))
        return {
            "paths": {s: (str(DATA_DIR / f"{lang}_morph_{s}.npy"),
                          str(DATA_DIR / f"{lang}_morph_feat_{s}.npy"))
                      for s in ("train", "val", "test")},
            "vocab_size": len(vocab),
            "n_feat_bundles": len(bundles),
            "cached": True,
        }

    engine = ENGINES[lang]()
    token2id: dict = dict(SPECIALS)
    bundle2id: dict = {"no_features": 0}

    # Build vocab on train.
    train_path = DATA_DIR / f"{lang}_train.txt"
    _encode_file(train_path, lang, engine, token2id, bundle2id, build_vocab=True)

    # Cap vocab.
    if len(token2id) > VOCAB_CAP:
        token2id = dict(list(token2id.items())[:VOCAB_CAP])

    vocab_path.write_text(json.dumps(token2id, ensure_ascii=False), encoding="utf-8")
    bundles_path.write_text(json.dumps(bundle2id, ensure_ascii=False), encoding="utf-8")

    paths: dict = {}
    for split in ("train", "val", "test"):
        tok_out = DATA_DIR / f"{lang}_morph_{split}.npy"
        feat_out = DATA_DIR / f"{lang}_morph_feat_{split}.npy"
        toks, feats = _encode_file(
            DATA_DIR / f"{lang}_{split}.txt", lang, engine, token2id, bundle2id,
            build_vocab=False,
        )
        np.save(tok_out, toks)
        np.save(feat_out, feats)
        paths[split] = (str(tok_out), str(feat_out))

    return {
        "paths": paths,
        "vocab_size": len(token2id),
        "n_feat_bundles": len(bundle2id),
        "cached": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", nargs="+", default=list(ENGINES.keys()),
                    choices=list(ENGINES.keys()))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    for lang in args.langs:
        info = tokenize(lang, args.force)
        print(f"[{lang}] vocab={info['vocab_size']:,} bundles={info['n_feat_bundles']:,} "
              f"(cached={info['cached']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
