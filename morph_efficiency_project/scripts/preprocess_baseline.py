"""
preprocess_baseline.py
----------------------
Step 1: Train a SentencePiece BPE tokenizer on each language's raw train corpus.
Step 2: Tokenize train/val/test splits and save token ID arrays as .npy files.

Outputs per language L in {en, ar, tr}:
  tokenizers/L_base/         — SentencePiece model + vocab
  data/processed/L/baseline/train_tokens.npy
  data/processed/L/baseline/val_tokens.npy
  data/processed/L/baseline/test_tokens.npy
  logs/evaluation/L_baseline_token_stats.json  (updated with processed counts)

Usage:
  python scripts/preprocess_baseline.py --language en
  python scripts/preprocess_baseline.py --language ar
  python scripts/preprocess_baseline.py --language tr
  python scripts/preprocess_baseline.py --language all
"""

import argparse
import json
import logging
import os
import tempfile

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

VOCAB_SIZE       = 32_000
CHAR_COVERAGE    = 0.9995
# SentencePiece trains on a sampled subset to keep memory manageable.
# 10M sentences is sufficient for a stable 32k BPE vocab.
SP_TRAIN_SAMPLE  = 10_000_000
# Tokenize in chunks to avoid loading full corpus into RAM.
CHUNK_LINES      = 200_000


def get_paths(lang: str) -> dict:
    return {
        "train_raw":  os.path.join("data", "raw", lang, "train.txt"),
        "val_raw":    os.path.join("data", "raw", lang, "val.txt"),
        "test_raw":   os.path.join("data", "raw", lang, "test.txt"),
        "tok_dir":    os.path.join("tokenizers", f"{lang}_base"),
        "proc_dir":   os.path.join("data", "processed", lang, "baseline"),
        "log_path":   os.path.join("logs", "evaluation", f"{lang}_baseline_token_stats.json"),
    }


# ── Step 1: Train tokenizer ───────────────────────────────────────────────────

def train_tokenizer(lang: str, paths: dict):
    try:
        import sentencepiece as spm
    except ImportError:
        raise ImportError("pip install sentencepiece")

    os.makedirs(paths["tok_dir"], exist_ok=True)
    model_prefix = os.path.join(paths["tok_dir"], f"{lang}_base")

    if os.path.exists(model_prefix + ".model"):
        log.info(f"[{lang}] Tokenizer already exists at {model_prefix}.model — skipping training.")
        return

    log.info(f"[{lang}] Sampling up to {SP_TRAIN_SAMPLE:,} sentences for tokenizer training...")

    # Write a temp file with the sampled sentences
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt",
                                     delete=False, encoding="utf-8") as tmp:
        tmp_path = tmp.name
        count = 0
        with open(paths["train_raw"], encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if line:
                    tmp.write(line + "\n")
                    count += 1
                    if count >= SP_TRAIN_SAMPLE:
                        break
    log.info(f"[{lang}] Sampled {count:,} sentences. Training SentencePiece BPE...")

    spm.SentencePieceTrainer.train(
        input=tmp_path,
        model_prefix=model_prefix,
        vocab_size=VOCAB_SIZE,
        character_coverage=CHAR_COVERAGE,
        model_type="bpe",
        pad_id=0,
        unk_id=1,
        bos_id=2,
        eos_id=3,
        pad_piece="<pad>",
        unk_piece="<unk>",
        bos_piece="<s>",
        eos_piece="</s>",
        num_threads=os.cpu_count(),
        input_sentence_size=SP_TRAIN_SAMPLE,
        shuffle_input_sentence=True,
    )
    os.unlink(tmp_path)
    log.info(f"[{lang}] Tokenizer saved to {paths['tok_dir']}/")


# ── Step 2: Tokenize splits ───────────────────────────────────────────────────

def tokenize_split(lang: str, split: str, raw_path: str, out_dir: str,
                   sp_model) -> dict:
    """
    Tokenizes one split line-by-line in chunks, appending BOS+EOS per line,
    and saves the full token ID sequence as a memory-mapped .npy file.
    Returns stats dict.
    """
    import sentencepiece as spm

    out_path = os.path.join(out_dir, f"{split}_tokens.npy")
    if os.path.exists(out_path):
        log.info(f"[{lang}/{split}] Already tokenized at {out_path} — skipping.")
        existing = np.load(out_path, mmap_mode="r")
        return {"split": split, "num_tokens": len(existing), "skipped": True}

    bos_id = sp_model.bos_id()
    eos_id = sp_model.eos_id()

    log.info(f"[{lang}/{split}] Tokenizing {raw_path} ...")

    # Two-pass: first count tokens to pre-allocate, then fill.
    # Single-pass with dynamic list is simpler but uses more RAM.
    # We use a dynamic list then convert — acceptable for 200M token val/test.
    # For train (8B tokens) we write in chunks to a growing memmap.

    all_ids = []
    line_count = 0
    chunk = []

    with open(raw_path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            ids = [bos_id] + sp_model.encode(line) + [eos_id]
            chunk.extend(ids)
            line_count += 1

            if len(chunk) >= CHUNK_LINES * 50:  # ~50 tokens/line avg
                all_ids.extend(chunk)
                chunk = []
                if line_count % 500_000 == 0:
                    log.info(f"  [{lang}/{split}] {line_count:,} lines | "
                             f"{len(all_ids):,} tokens so far")

    all_ids.extend(chunk)
    arr = np.array(all_ids, dtype=np.int32)
    np.save(out_path, arr)

    stats = {
        "split": split,
        "num_lines": line_count,
        "num_tokens": len(arr),
        "avg_tokens_per_line": round(len(arr) / max(line_count, 1), 2),
    }
    log.info(f"[{lang}/{split}] Done. {stats['num_tokens']:,} tokens → {out_path}")
    return stats


def tokenize_all_splits(lang: str, paths: dict):
    try:
        import sentencepiece as spm
    except ImportError:
        raise ImportError("pip install sentencepiece")

    os.makedirs(paths["proc_dir"], exist_ok=True)
    model_path = os.path.join(paths["tok_dir"], f"{lang}_base.model")

    sp = spm.SentencePieceProcessor()
    sp.load(model_path)
    log.info(f"[{lang}] Loaded tokenizer from {model_path} (vocab={sp.get_piece_size()})")

    split_stats = {}
    for split, raw_path in [
        ("train", paths["train_raw"]),
        ("val",   paths["val_raw"]),
        ("test",  paths["test_raw"]),
    ]:
        stats = tokenize_split(lang, split, raw_path, paths["proc_dir"], sp)
        split_stats[split] = stats

    return split_stats


# ── Log update ────────────────────────────────────────────────────────────────

def update_log(lang: str, paths: dict, split_stats: dict):
    log_path = paths["log_path"]
    existing = {}
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                pass

    existing["baseline_tokenized"] = split_stats
    existing["tokenizer"] = {
        "type": "sentencepiece_bpe",
        "vocab_size": VOCAB_SIZE,
        "character_coverage": CHAR_COVERAGE,
        "model_path": os.path.join(paths["tok_dir"], f"{lang}_base.model"),
    }

    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    log.info(f"[{lang}] Stats updated at {log_path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def process_language(lang: str):
    paths = get_paths(lang)
    log.info(f"=== [{lang}] Baseline preprocessing ===")

    if not os.path.exists(paths["train_raw"]):
        raise FileNotFoundError(
            f"Raw corpus not found: {paths['train_raw']}\n"
            f"Run download_data.py --language {lang} first."
        )

    train_tokenizer(lang, paths)
    split_stats = tokenize_all_splits(lang, paths)
    update_log(lang, paths, split_stats)
    log.info(f"=== [{lang}] Baseline preprocessing complete ===\n")


def main():
    parser = argparse.ArgumentParser(description="Baseline tokenization pipeline.")
    parser.add_argument(
        "--language",
        choices=["en", "ar", "tr", "all"],
        required=True,
    )
    args = parser.parse_args()
    langs = ["en", "ar", "tr"] if args.language == "all" else [args.language]
    for lang in langs:
        process_language(lang)


if __name__ == "__main__":
    main()
