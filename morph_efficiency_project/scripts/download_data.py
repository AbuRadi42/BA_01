"""
download_data.py
----------------
Downloads corpora for EN, AR, TR and creates train/val/test splits.

Sources per language:
  EN: Wikipedia EN, OPUS (TED2020 + News-Commentary), CC-100 EN
  AR: Wikipedia AR, OPUS AR, CC-100 AR, OSIAN
  TR: Wikipedia TR, OPUS TR, CC-100 TR

Outputs per language L in {en, ar, tr}:
  data/raw/L/train.txt
  data/raw/L/val.txt
  data/raw/L/test.txt

Each line is one sentence / short document segment (UTF-8).
Token counts (whitespace-based) are logged to:
  logs/evaluation/L_baseline_token_stats.json

Usage:
  python scripts/download_data.py --language en
  python scripts/download_data.py --language ar
  python scripts/download_data.py --language tr
  python scripts/download_data.py --language all
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
    "train": 8_000_000_000,
    "val":     200_000_000,
    "test":    200_000_000,
}

# ── Random seeds (fixed per language for reproducibility) ────────────────────
SEEDS = {"en": 42, "ar": 43, "tr": 44}

# ── Source configs ────────────────────────────────────────────────────────────
# Each source is a (dataset_name, config_name, split, text_field) tuple.
# All loaded via HuggingFace `datasets`.
SOURCES = {
    "en": [
        ("wikipedia",        "20220301.en",  "train", "text"),
        ("Helsinki-NLP/opus_books", "en",    "train", "text"),  # OPUS books
        ("cc100",            "en",           "train", "text"),
    ],
    "ar": [
        ("wikipedia",        "20220301.ar",  "train", "text"),
        ("cc100",            "ar",           "train", "text"),
        ("Helsinki-NLP/opus-100", "ar-en",   "train", "translation"),  # OPUS AR side
    ],
    "tr": [
        ("wikipedia",        "20220301.tr",  "train", "text"),
        ("cc100",            "tr",           "train", "text"),
        ("Helsinki-NLP/opus-100", "tr-en",   "train", "translation"),  # OPUS TR side
    ],
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def count_tokens(text: str) -> int:
    """Whitespace-based token count."""
    return len(text.split())


def clean_line(text: str, lang: str) -> str:
    """
    Minimal cleaning:
    - Strip leading/trailing whitespace
    - Collapse internal whitespace runs to single space
    - Drop lines that are pure URLs, wiki markup headers, or < 5 tokens
    """
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    # Drop wiki section headers (== Heading ==)
    if re.match(r"^=+\s*.+\s*=+$", text):
        return ""
    # Drop bare URLs
    if re.match(r"^https?://\S+$", text):
        return ""
    # Drop very short lines
    if count_tokens(text) < 5:
        return ""
    return text


def extract_text(example: dict, text_field: str, lang: str) -> list[str]:
    """
    Extract one or more lines of text from a dataset example.
    Handles the OPUS translation dict format ({"ar": "...", "en": "..."}).
    """
    raw = example.get(text_field, "")
    if isinstance(raw, dict):
        # OPUS translation pair — take the target language side
        raw = raw.get(lang, "")
    if not isinstance(raw, str):
        return []
    lines = raw.split("\n")
    cleaned = [clean_line(l, lang) for l in lines]
    return [l for l in cleaned if l]


def make_dirs(lang: str) -> tuple[str, str, str]:
    """Create output directories and return file paths."""
    raw_dir = os.path.join("data", "raw", lang)
    log_dir = os.path.join("logs", "evaluation")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    train_path = os.path.join(raw_dir, "train.txt")
    val_path   = os.path.join(raw_dir, "val.txt")
    test_path  = os.path.join(raw_dir, "test.txt")
    return train_path, val_path, test_path


# ── Core pipeline ─────────────────────────────────────────────────────────────

def stream_sentences(lang: str):
    """
    Generator: yields cleaned sentences from all sources for `lang`.
    Uses HuggingFace datasets in streaming mode to avoid loading
    multi-billion-token corpora into RAM.
    """
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
                trust_remote_content=True,
            )
            for example in ds:
                for sentence in extract_text(example, text_field, lang):
                    yield sentence
        except Exception as e:
            log.warning(f"  Skipping {dataset_name}/{config}: {e}")
            continue


def build_corpus(lang: str):
    """
    Streams all sources, shuffles with a reservoir, then writes
    train / val / test splits to data/raw/{lang}/.
    """
    rng = random.Random(SEEDS[lang])
    train_path, val_path, test_path = make_dirs(lang)

    # Total target tokens across all splits
    total_target = TARGET["train"] + TARGET["val"] + TARGET["test"]

    log.info(f"[{lang}] Starting corpus build. Target: {total_target:,} tokens")

    # ── Pass 1: stream into a temp buffer until we hit the token target ───────
    # We use a large in-memory list then shuffle before splitting.
    # For 8B+ token corpora this would OOM — so we cap the buffer at
    # BUFFER_SENTENCES and write in chunks if needed.
    # Practical note: at ~15 tokens/sentence average, 8B tokens ≈ 533M sentences.
    # We stream-write directly to avoid OOM.

    FLUSH_EVERY = 500_000  # sentences between progress logs

    token_counts = {"train": 0, "val": 0, "test": 0}
    sentence_count = 0

    # Val/test boundaries (fraction of total sentences)
    # We assign splits probabilistically to avoid two-pass streaming.
    # P(val) = val_target / total_target, P(test) = test_target / total_target
    p_val  = TARGET["val"]  / total_target
    p_test = TARGET["test"] / total_target

    with open(train_path, "w", encoding="utf-8") as f_train, \
         open(val_path,   "w", encoding="utf-8") as f_val, \
         open(test_path,  "w", encoding="utf-8") as f_test:

        for sentence in stream_sentences(lang):
            # Probabilistic split assignment (fixed seed → reproducible)
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

            # Stop once train target is reached (val/test will be proportional)
            if token_counts["train"] >= TARGET["train"]:
                log.info(f"  [{lang}] Train target reached. Stopping stream.")
                break

    log.info(
        f"[{lang}] Done. "
        f"train={token_counts['train']:,} "
        f"val={token_counts['val']:,} "
        f"test={token_counts['test']:,} tokens | "
        f"{sentence_count:,} total sentences"
    )

    # ── Log token stats ───────────────────────────────────────────────────────
    stats = {
        "language": lang,
        "sentence_count": sentence_count,
        "token_counts": token_counts,
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
    parser.add_argument(
        "--language",
        choices=["en", "ar", "tr", "all"],
        required=True,
        help="Language to download, or 'all' for all three.",
    )
    args = parser.parse_args()

    langs = ["en", "ar", "tr"] if args.language == "all" else [args.language]
    for lang in langs:
        log.info(f"=== Building corpus for: {lang} ===")
        build_corpus(lang)
    log.info("All done.")


if __name__ == "__main__":
    main()
