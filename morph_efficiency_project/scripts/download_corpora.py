"""
download_corpora.py — Fetch Wikipedia samples for the six additional languages.

Phase 1 used wikimedia/wikipedia via the datasets library (see
mini_experiment/run_mini.py). This script pulls the same source for the six
new-spectrum languages and writes per-split plain-text files matching the
filename convention compute_hl.py expects:

    mini_experiment/data/{lang}_train.txt
    mini_experiment/data/{lang}_val.txt
    mini_experiment/data/{lang}_test.txt

Resumable: skips any language whose three split files already exist and meet
a minimum sentence-count threshold. Run again safely after interruption.

Forensic log: appends a JSON line per language download event to
    mini_experiment/data/download_log.jsonl

Usage:
    python morph_efficiency_project/scripts/download_corpora.py
    python morph_efficiency_project/scripts/download_corpora.py --langs de es hu
    python morph_efficiency_project/scripts/download_corpora.py --force-redownload
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "mini_experiment" / "data"
LOG_FILE = DATA_DIR / "download_log.jsonl"

SOURCES = {
    "zh": ("wikimedia/wikipedia", "20231101.zh"),
}

N_TRAIN = 80_000
N_VAL = 5_000
N_TEST = 5_000
MIN_LINE_CHARS = 20   # skip very short lines
MIN_SENTENCE_COUNT = 100  # sanity threshold for "already downloaded"

SENT_SPLIT = re.compile(r"(?<=[.!?。！？])\s+")


def log_event(event: str, **fields) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rec = {
        "event": event,
        "ts": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def count_lines(p: Path) -> int:
    if not p.exists():
        return 0
    with p.open("r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def already_downloaded(lang: str) -> bool:
    return all(
        count_lines(DATA_DIR / f"{lang}_{split}.txt") >= MIN_SENTENCE_COUNT
        for split in ("train", "val", "test")
    )


def download_language(lang: str, force: bool) -> bool:
    if already_downloaded(lang) and not force:
        log_event("skip", lang=lang, reason="already_downloaded")
        print(f"[{lang}] already downloaded, skipping", file=sys.stderr)
        return True

    ds_name, ds_config = SOURCES[lang]
    log_event("start", lang=lang, dataset=ds_name, config=ds_config)
    print(f"[{lang}] fetching {ds_name}:{ds_config} ...", file=sys.stderr)

    # Bypass `datasets` (which auto-imports torch and fails here) and read
    # the raw parquet files directly from the HF Hub.
    try:
        from huggingface_hub import HfApi, hf_hub_download
        import pyarrow.parquet as pq
    except ImportError as e:
        print(f"required library missing: {e}. pip install huggingface_hub pyarrow", file=sys.stderr)
        return False

    t0 = time.time()
    repo_id = ds_name
    api = HfApi()
    try:
        files = api.list_repo_files(repo_id=repo_id, repo_type="dataset")
    except Exception as e:
        log_event("error", lang=lang, stage="list_repo_files", error=str(e))
        print(f"[{lang}] list_repo_files failed: {e}", file=sys.stderr)
        return False

    # wikimedia/wikipedia parquet files are in <config>/train-xxxxx-of-yyyyy.parquet
    shards = sorted(f for f in files if f.startswith(ds_config + "/") and f.endswith(".parquet"))
    if not shards:
        log_event("error", lang=lang, stage="list_shards", message="no shards found")
        print(f"[{lang}] no parquet shards under {ds_config}/", file=sys.stderr)
        return False
    print(f"[{lang}] {len(shards)} parquet shard(s) available; streaming from first", file=sys.stderr)

    target_total = N_TRAIN + N_VAL + N_TEST
    collected: list[str] = []

    try:
        for shard in shards:
            local = hf_hub_download(repo_id=repo_id, filename=shard, repo_type="dataset")
            pf = pq.ParquetFile(local)
            # iterate row groups to avoid loading whole shard into memory
            for rg_idx in range(pf.num_row_groups):
                tbl = pf.read_row_group(rg_idx, columns=["text"])
                for text in tbl.column("text").to_pylist():
                    if not text:
                        continue
                    for sent in SENT_SPLIT.split(text):
                        sent = sent.strip()
                        if len(sent) < MIN_LINE_CHARS:
                            continue
                        sent = " ".join(sent.split())
                        collected.append(sent)
                        if len(collected) >= target_total:
                            break
                    if len(collected) >= target_total:
                        break
                if len(collected) >= target_total:
                    break
            if len(collected) >= target_total:
                break
    except Exception as e:
        log_event("error", lang=lang, stage="stream", collected=len(collected), error=str(e))
        print(f"[{lang}] parquet stream failed after {len(collected)} sentences: {e}", file=sys.stderr)
        return False

    if len(collected) < target_total:
        log_event("partial", lang=lang, collected=len(collected), target=target_total)
        print(f"[{lang}] only {len(collected)}/{target_total} sentences available", file=sys.stderr)

    train = collected[:N_TRAIN]
    val = collected[N_TRAIN:N_TRAIN + N_VAL]
    test = collected[N_TRAIN + N_VAL:N_TRAIN + N_VAL + N_TEST]

    for split, lines in (("train", train), ("val", val), ("test", test)):
        p = DATA_DIR / f"{lang}_{split}.txt"
        tmp = p.with_suffix(".txt.tmp")
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        tmp.replace(p)

    elapsed = time.time() - t0
    log_event(
        "complete", lang=lang,
        n_train=len(train), n_val=len(val), n_test=len(test),
        elapsed_s=round(elapsed, 1),
    )
    print(
        f"[{lang}] wrote {len(train)} train / {len(val)} val / {len(test)} test "
        f"({elapsed:.0f}s)",
        file=sys.stderr,
    )
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--langs", nargs="+", default=list(SOURCES.keys()),
                    choices=list(SOURCES.keys()))
    ap.add_argument("--force-redownload", action="store_true")
    args = ap.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    failures = 0
    for lang in args.langs:
        if not download_language(lang, args.force_redownload):
            failures += 1

    print(f"\nFailures: {failures} / {len(args.langs)}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
