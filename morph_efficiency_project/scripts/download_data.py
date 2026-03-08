"""
download_data.py
----------------
Downloads corpora for EN, AR, TR and creates train/val/test splits.

Sources per language:
  EN: Wikipedia EN, OPUS books, CC-100 EN
  AR: Wikipedia AR, CC-100 AR, OPUS-100 AR-EN
  TR: Wikipedia TR, CC-100 TR, OPUS-100 TR-EN

Outputs per language L in {en, ar, tr}:
  data/raw/L/train.txt
  data/raw/L/val.txt
  data/raw/L/test.txt

Token counts (whitespace-based) are logged to:
  logs/evaluation/L_baseline_token_stats.json

Usage:
  python scripts/download_data.py --language en
  python scripts/download_data.py --language all
  python scripts/download_data.py --language en --max-sentences 50000  # dry run
"""

import argparse
import json
import logging
import os
import random
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Target sizes (whitespace tokens, approximate) ────────────────────────────
TARGET = {
    "train": 2_500_000_000,
    "val":      62_500_000,
    "test":     62_500_000,
}

# ── Random seeds (fixed per language for reproducibility) ────────────────────
SEEDS = {"en": 42, "ar": 43, "tr": 44}

# ── Source configs ────────────────────────────────────────────────────────────
# Each entry: (dataset_name, config_name, split, text_field)
# text_field may be a string key or "translation:{lang}" for OPUS translation pairs.
SOURCES = {
    "en": [
        ("wikimedia/wikipedia",    "20231101.en", "train", "text"),
        ("Helsinki-NLP/opus_books","en-fr",        "train", "translation:en"),
        ("cc100",                  "en",           "train", "text"),
    ],
    "ar": [
        ("wikimedia/wikipedia",    "20231101.ar",  "train", "text"),
        ("cc100",                  "ar",           "train", "text"),
        ("Helsinki-NLP/opus-100",  "ar-en",        "train", "translation:ar"),
    ],
    "tr": [
        ("wikimedia/wikipedia",    "20231101.tr",  "train", "text"),
        ("cc100",                  "tr",           "train", "text"),
        ("Helsinki-NLP/opus-100",  "tr-en",        "train", "translation:tr"),
    ],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def count_tokens(text: str) -> int:
    return len(text.split())

def clean_line(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    if re.match(r"^=+\s*.+\s*=+$", text):   # wiki section headers
        return ""
    if re.match(r"^https?://\S+$", text):    # bare URLs
        return ""
    if count_tokens(text) < 5:
        return ""
    return text

def extract_text(example: dict, text_field: str, lang: str) -> list:
    """
    Handles plain text fields and "translation:{lang}" fields for OPUS pairs.
    """
    if text_field.startswith("translation:"):
        target_lang = text_field.split(":", 1)[1]
        raw = example.get("translation", {})
        if isinstance(raw, dict):
            raw = raw.get(target_lang, "")
        else:
            return []
    else:
        raw = example.get(text_field, "")

    if not isinstance(raw, str):
        return []
    lines = raw.split("\n")
    return [c for c in (clean_line(l) for l in lines) if c]

def make_dirs(lang: str):
    raw_dir = os.path.join("data", "raw", lang)
    log_dir = os.path.join("logs", "evaluation")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    return (
        os.path.join(raw_dir, "train.txt"),
        os.path.join(raw_dir, "val.txt"),
        os.path.join(raw_dir, "test.txt"),
    )

# ── Core pipeline ─────────────────────────────────────────────────────────────

def stream_sentences(lang: str):
    try:
        from datasets import load_dataset
    except ImportError:
        raise ImportError("pip install datasets")

    for dataset_name, config, split, text_field in SOURCES[lang]:
        log.info(f"  Streaming {dataset_name} / {config} ({split})")
        try:
            ds = load_dataset(
                dataset_name,
                config,
                split=split,
                streaming=True,
            )
            for example in ds:
                for sentence in extract_text(example, text_field, lang):
                    yield sentence
        except Exception as e:
            log.warning(f"  Skipping {dataset_name}/{config}: {e}")
            continue

def build_corpus(lang: str, max_sentences: int = 0):
    """
    max_sentences > 0 activates dry-run mode: stops after that many sentences
    regardless of token targets.
    """
    rng = random.Random(SEEDS[lang])
    train_path, val_path, test_path = make_dirs(lang)

    total_target = TARGET["train"] + TARGET["val"] + TARGET["test"]
    p_val  = TARGET["val"]  / total_target
    p_test = TARGET["test"] / total_target

    dry_run = max_sentences > 0
    if dry_run:
        log.info(f"[{lang}] DRY RUN — capped at {max_sentences:,} sentences")
    else:
        log.info(f"[{lang}] Starting corpus build. Target: {total_target:,} tokens")

    token_counts   = {"train": 0, "val": 0, "test": 0}
    sentence_count = 0
    FLUSH_EVERY    = 500_000

    with open(train_path, "w", encoding="utf-8") as f_train, \
         open(val_path,   "w", encoding="utf-8") as f_val, \
         open(test_path,  "w", encoding="utf-8") as f_test:

        for sentence in stream_sentences(lang):
            r = rng.random()
            if r < p_val:
                f_val.write(sentence + "\n")
                token_counts["val"] += count_tokens(sentence)
            elif r < p_val + p_test:
                f_test.write(sentence + "\n")
                token_counts["test"] += count_tokens(sentence)
            else:
                f_train.write(sentence + "\n")
                token_counts["train"] += count_tokens(sentence)

            sentence_count += 1

            if sentence_count % FLUSH_EVERY == 0:
                log.info(
                    f"  [{lang}] {sentence_count:,} sentences | "
                    f"train={token_counts['train']:,} "
                    f"val={token_counts['val']:,} "
                    f"test={token_counts['test']:,} tokens"
                )

            # Stop conditions
            if dry_run and sentence_count >= max_sentences:
                log.info(f"  [{lang}] Dry-run cap reached. Stopping.")
                break
            if not dry_run and token_counts["train"] >= TARGET["train"]:
                log.info(f"  [{lang}] Train target reached. Stopping.")
                break

    log.info(
        f"[{lang}] Done. "
        f"train={token_counts['train']:,} "
        f"val={token_counts['val']:,} "
        f"test={token_counts['test']:,} tokens | "
        f"{sentence_count:,} total sentences"
    )

    stats = {
        "language":    lang,
        "dry_run":     dry_run,
        "sentence_count": sentence_count,
        "token_counts":   token_counts,
        "avg_tokens_per_sentence": round(
            sum(token_counts.values()) / max(sentence_count, 1), 2
        ),
        "split_files": {
            "train": train_path,
            "val":   val_path,
            "test":  test_path,
        },
    }
    log_path = os.path.join("logs", "evaluation", f"{lang}_baseline_token_stats.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    log.info(f"[{lang}] Token stats saved to {log_path}")

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Download and split corpora.")
    parser.add_argument("--language", choices=["en", "ar", "tr", "all"], required=True)
    parser.add_argument(
        "--max-sentences", type=int, default=0,
        help="Dry-run cap: stop after this many sentences per language (0 = full run).",
    )
    args = parser.parse_args()

    langs = ["en", "ar", "tr"] if args.language == "all" else [args.language]
    for lang in langs:
        log.info(f"=== Building corpus for: {lang} ===")
        build_corpus(lang, max_sentences=args.max_sentences)
    log.info("All done.")

if __name__ == "__main__":
    main()
