"""
preprocess_morph.py
-------------------
Thin orchestrator for morphology-aware preprocessing.
Grammar engines live in scripts/engines/.

Usage:
  python scripts/preprocess_morph.py --language en
  python scripts/preprocess_morph.py --language all
  python scripts/preprocess_morph.py --language en --max-sentences 50000  # dry run
"""

import argparse
import json
import logging
import os
import sys
from typing import List

import numpy as np

# ── Ensure engines are importable regardless of working directory ─────────────
_here = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_here, "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from morph_efficiency_project.scripts.engines import (
    EnglishEngine,
    ArabicEngine,
    TurkishEngine,
    MorphVocab,
    TokenInfo,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ENGINES = {
    "en": EnglishEngine,
    "ar": ArabicEngine,
    "tr": TurkishEngine,
}


def process_split(
    lang: str,
    split: str,
    engine,
    vocab: MorphVocab,
    base_dir: str = "morph_efficiency_project",
    max_sentences: int = 0,
) -> dict:
    in_path = os.path.join(base_dir, "data", "raw", lang, f"{split}.txt")
    out_dir = os.path.join(base_dir, "data", "processed", lang, "morph")
    log_dir = os.path.join(base_dir, "logs", "evaluation")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    if not os.path.exists(in_path):
        log.warning(f"Input file not found: {in_path} — skipping.")
        return {}

    token_ids:   List[int] = []
    feature_ids: List[int] = []
    total_sentences = valid_sentences = invalid_sentences = 0
    total_tokens = foreign_tokens = 0

    dry_run = max_sentences > 0
    log.info(f"[{lang}/{split}] Processing {in_path}"
             + (f" (dry-run cap: {max_sentences:,})" if dry_run else ""))

    with open(in_path, encoding="utf-8") as f:
        for line in f:
            sentence = line.strip()
            if not sentence:
                continue
            total_sentences += 1
            tokens, is_valid, _ = engine.analyze_sentence(sentence)
            total_tokens += len(tokens)
            if is_valid:
                valid_sentences += 1
            else:
                invalid_sentences += 1
            for ti in tokens:
                if ti.pos in ("FOREIGN", "UNKNOWN") or not ti.root:
                    foreign_tokens += 1
                tok_id, bundle_id = vocab.encode(ti)
                token_ids.append(tok_id)
                feature_ids.append(bundle_id)

            if total_sentences % 500_000 == 0:
                log.info(
                    f"  [{lang}/{split}] {total_sentences:,} sentences | "
                    f"{total_tokens:,} tokens | valid={valid_sentences:,}"
                )

            if dry_run and total_sentences >= max_sentences:
                log.info(f"  [{lang}/{split}] Dry-run cap reached.")
                break

    np.save(os.path.join(out_dir, f"{split}_tokens.npy"),      np.array(token_ids,   dtype=np.int32))
    np.save(os.path.join(out_dir, f"{split}_feature_ids.npy"), np.array(feature_ids, dtype=np.int32))

    stats = {
        "language": lang, "split": split,
        "total_sentences": total_sentences, "valid_sentences": valid_sentences,
        "invalid_sentences": invalid_sentences, "total_tokens": total_tokens,
        "foreign_tokens": foreign_tokens,
        "foreign_rate": round(foreign_tokens / max(total_tokens, 1), 4),
        "vocab_size": len(vocab.token2id), "feature_bundles": len(vocab.bundle2id),
    }
    log_path = os.path.join(log_dir, f"{lang}_morph_{split}_stats.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    log.info(
        f"[{lang}/{split}] Done. {total_tokens:,} tokens | "
        f"foreign_rate={stats['foreign_rate']:.2%} | vocab={stats['vocab_size']:,}"
    )
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=["en", "ar", "tr", "all"], required=True)
    parser.add_argument("--base_dir", default="morph_efficiency_project")
    parser.add_argument(
        "--max-sentences", type=int, default=0,
        help="Dry-run cap: stop after this many sentences per split (0 = full run).",
    )
    args = parser.parse_args()

    langs = ["en", "ar", "tr"] if args.language == "all" else [args.language]
    for lang in langs:
        log.info(f"=== Morphology preprocessing: {lang} ===")
        engine = ENGINES[lang](config_dir=os.path.join(args.base_dir, "configs"))
        vocab  = MorphVocab()
        all_stats = []
        for split in ("train", "val", "test"):
            stats = process_split(lang, split, engine, vocab,
                                  base_dir=args.base_dir,
                                  max_sentences=args.max_sentences)
            if stats:
                all_stats.append(stats)
        tok_dir = os.path.join(args.base_dir, "tokenizers", f"{lang}_morph")
        vocab.save(tok_dir)
        summary = {
            "language": lang, "splits": all_stats,
            "final_vocab_size": len(vocab.token2id),
            "final_feature_bundles": len(vocab.bundle2id),
        }
        summary_path = os.path.join(args.base_dir, "logs", "summary", f"{lang}_morph_summary.json")
        os.makedirs(os.path.dirname(summary_path), exist_ok=True)
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        log.info(f"[{lang}] Summary saved to {summary_path}")
    log.info("All done.")


if __name__ == "__main__":
    main()
