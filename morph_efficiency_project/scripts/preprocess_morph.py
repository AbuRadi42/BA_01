"""
preprocess_morph.py
-------------------
Thin orchestrator for morphology-aware preprocessing.
Grammar engines live in scripts/engines/.
Uses multiprocessing to parallelize across CPU cores for large files.

Resumable: each chunk's output is saved to disk immediately after processing.
On restart, completed chunks are skipped and only missing ones are reprocessed.

Usage:
  python scripts/preprocess_morph.py --language en
  python scripts/preprocess_morph.py --language all
  python scripts/preprocess_morph.py --language en --max-sentences 50000  # dry run
  python scripts/preprocess_morph.py --language all --workers 32
"""

import argparse
import json
import logging
import os
import sys
from multiprocessing import Pool
from typing import List, Tuple

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
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ENGINES = {
    "en": EnglishEngine,
    "ar": ArabicEngine,
    "tr": TurkishEngine,
}


# ── Worker: processes one chunk, saves to persistent chunk dir ────────────────

def _worker(args: Tuple) -> Tuple[str, str]:
    """
    Process a chunk of lines. Saves output to a persistent .npz in chunk_dir.
    If the chunk file already exists (resume), skips processing entirely.
    Returns (chunk_path, stats_json).
    """
    lang, chunk_lines, config_dir, chunk_idx, chunk_dir = args

    chunk_path = os.path.join(chunk_dir, f"chunk_{chunk_idx:05d}.npz")

    # Resume: chunk already done
    if os.path.exists(chunk_path) and os.path.getsize(chunk_path) > 0:
        data = np.load(chunk_path, allow_pickle=True)
        stats = json.loads(str(data["stats_json"]))
        return chunk_path, json.dumps(stats)

    import sys as _sys
    if _project_root not in _sys.path:
        _sys.path.insert(0, _project_root)

    engine_cls = ENGINES[lang]
    engine = engine_cls(config_dir=config_dir)

    surfaces: List[str] = []
    bundles:  List[str] = []
    total = valid = foreign = 0

    for sentence in chunk_lines:
        sentence = sentence.strip()
        if not sentence:
            continue
        tokens, is_valid, _ = engine.analyze_sentence(sentence)
        total += len(tokens)
        if is_valid:
            valid += 1
        for ti in tokens:
            if ti.pos == "FOREIGN" or not ti.root:
                foreign += 1
            surfaces.append(ti.token_str())
            bundles.append(ti.feature_bundle_str())

    stats = {"total_tokens": total, "valid_sentences": valid, "foreign_tokens": foreign}
    np.savez_compressed(
        chunk_path,
        surfaces=np.array(surfaces, dtype=object),
        bundles=np.array(bundles, dtype=object),
        stats_json=np.array(json.dumps(stats)),
    )
    return chunk_path, json.dumps(stats)


# ── Split file into N chunks ──────────────────────────────────────────────────

def _read_chunks(path: str, n_workers: int, max_sentences: int = 0) -> List[List[str]]:
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    if max_sentences > 0:
        lines = lines[:max_sentences]
    chunk_size = max(1, len(lines) // n_workers)
    return [lines[i:i + chunk_size] for i in range(0, len(lines), chunk_size)]


# ── Main split processor ──────────────────────────────────────────────────────

def process_split(
    lang: str,
    split: str,
    config_dir: str,
    vocab: MorphVocab,
    base_dir: str = "morph_efficiency_project",
    max_sentences: int = 0,
    n_workers: int = 16,
) -> dict:
    in_path  = os.path.join(base_dir, "data", "raw", lang, f"{split}.txt")
    out_dir  = os.path.join(base_dir, "data", "processed", lang, "morph")
    log_dir  = os.path.join(base_dir, "logs", "evaluation")
    # Persistent chunk cache — survives crashes
    chunk_dir = os.path.join(base_dir, "data", "processed", lang, f"morph_chunks_{split}")
    os.makedirs(out_dir,   exist_ok=True)
    os.makedirs(log_dir,   exist_ok=True)
    os.makedirs(chunk_dir, exist_ok=True)

    if not os.path.exists(in_path):
        log.warning(f"Input file not found: {in_path} — skipping.")
        return {}

    # ── Resume: skip entire split if final output already exists ─────────────
    out_tokens_path  = os.path.join(out_dir, f"{split}_tokens.npy")
    out_feature_path = os.path.join(out_dir, f"{split}_feature_ids.npy")
    log_path = os.path.join(log_dir, f"{lang}_morph_{split}_stats.json")
    MIN_EXPECTED_BYTES = 500_000_000  # ~500MB — a real full-split output is always larger
    if (os.path.exists(out_tokens_path) and os.path.getsize(out_tokens_path) > MIN_EXPECTED_BYTES
            and os.path.exists(out_feature_path) and os.path.getsize(out_feature_path) > MIN_EXPECTED_BYTES
            and os.path.exists(log_path)):
        log.info(f"[{lang}/{split}] Output already exists — skipping (resume).")
        with open(log_path) as f:
            return json.load(f)

    dry_run = max_sentences > 0
    log.info(f"[{lang}/{split}] Reading {in_path}" +
             (f" (cap: {max_sentences:,})" if dry_run else ""))

    chunks = _read_chunks(in_path, n_workers, max_sentences)
    actual_workers = min(n_workers, len(chunks))

    # Count how many chunks are already done
    done = sum(
        1 for i in range(len(chunks))
        if os.path.exists(os.path.join(chunk_dir, f"chunk_{i:05d}.npz"))
        and os.path.getsize(os.path.join(chunk_dir, f"chunk_{i:05d}.npz")) > 0
    )
    log.info(f"[{lang}/{split}] {sum(len(c) for c in chunks):,} lines → "
             f"{len(chunks)} chunks ({done} already done), {actual_workers} workers")

    worker_args = [(lang, chunk, config_dir, i, chunk_dir) for i, chunk in enumerate(chunks)]

    with Pool(processes=actual_workers, maxtasksperchild=1) as pool:
        results = pool.map(_worker, worker_args)

    # ── Merge: encode all surfaces/bundles through the shared vocab ───────────
    log.info(f"[{lang}/{split}] Merging {len(results)} chunks...")
    token_ids:   List[int] = []
    feature_ids: List[int] = []
    total_tokens = valid_sentences = foreign_tokens = 0

    for chunk_path, stats_json in results:
        chunk_stats = json.loads(stats_json)
        total_tokens    += chunk_stats["total_tokens"]
        valid_sentences += chunk_stats["valid_sentences"]
        foreign_tokens  += chunk_stats["foreign_tokens"]

        data = np.load(chunk_path, allow_pickle=True)
        for tok_str, bun_str in zip(data["surfaces"], data["bundles"]):
            tok_id = vocab.token2id.setdefault(str(tok_str), len(vocab.token2id))
            bun_id = vocab.bundle2id.setdefault(str(bun_str), len(vocab.bundle2id))
            token_ids.append(tok_id)
            feature_ids.append(bun_id)

    np.save(out_tokens_path,  np.array(token_ids,   dtype=np.int32))
    np.save(out_feature_path, np.array(feature_ids, dtype=np.int32))

    stats = {
        "language": lang, "split": split,
        "total_sentences": sum(len(c) for c in chunks),
        "valid_sentences": valid_sentences,
        "total_tokens": total_tokens,
        "foreign_tokens": foreign_tokens,
        "foreign_rate": round(foreign_tokens / max(total_tokens, 1), 4),
        "vocab_size": len(vocab.token2id),
        "feature_bundles": len(vocab.bundle2id),
    }
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    log.info(f"[{lang}/{split}] Done. {total_tokens:,} tokens | "
             f"foreign_rate={stats['foreign_rate']:.2%} | vocab={stats['vocab_size']:,}")

    # Clean up chunk cache now that final output is written
    import shutil
    shutil.rmtree(chunk_dir, ignore_errors=True)

    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=["en", "ar", "tr", "all"], required=True)
    parser.add_argument("--base_dir", default="morph_efficiency_project")
    parser.add_argument("--workers", type=int, default=16,
                        help="Number of parallel workers (default 16).")
    parser.add_argument(
        "--max-sentences", type=int, default=0,
        help="Dry-run cap: stop after this many sentences per split (0 = full run).",
    )
    args = parser.parse_args()

    langs = ["en", "ar", "tr"] if args.language == "all" else [args.language]
    config_dir = os.path.join(args.base_dir, "configs")

    for lang in langs:
        log.info(f"=== Morphology preprocessing: {lang} ===")
        vocab = MorphVocab()
        all_stats = []

        for split in ("train", "val", "test"):
            stats = process_split(
                lang, split, config_dir, vocab,
                base_dir=args.base_dir,
                max_sentences=args.max_sentences,
                n_workers=args.workers,
            )
            if stats:
                all_stats.append(stats)

        tok_dir = os.path.join(args.base_dir, "tokenizers", f"{lang}_morph")
        vocab.save(tok_dir)

        summary = {
            "language": lang, "splits": all_stats,
            "final_vocab_size": len(vocab.token2id),
            "final_feature_bundles": len(vocab.bundle2id),
        }
        summary_path = os.path.join(
            args.base_dir, "logs", "summary", f"{lang}_morph_summary.json"
        )
        os.makedirs(os.path.dirname(summary_path), exist_ok=True)
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        log.info(f"[{lang}] Summary saved to {summary_path}")

        # Write marker file so watcher knows this completed cleanly
        marker = f"/workspace/.{lang}_morph_done"
        try:
            open(marker, "w").close()
        except Exception:
            pass

    log.info("All done.")


if __name__ == "__main__":
    main()
