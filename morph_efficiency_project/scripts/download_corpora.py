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

# Each language draws from multiple diverse registers (encyclopedic Wikipedia +
# large-scale web crawl) so both its models see the broadest possible variety of
# text. All sources are ungated HF parquet datasets with a "text" column; we read
# the parquet directly (bypassing `datasets`, which auto-imports torch here).
#   spec = (repo_id, shard_path_prefix, text_column)
SOURCES = {
    "zh": [
        ("wikimedia/wikipedia", "20231101.zh/", "text"),
        ("HuggingFaceFW/fineweb-2", "data/cmn_Hani/train/", "text"),
    ],
    "en": [
        ("wikimedia/wikipedia", "20231101.en/", "text"),
        ("HuggingFaceFW/fineweb", "sample/10BT/", "text"),
    ],
    "tr": [
        ("wikimedia/wikipedia", "20231101.tr/", "text"),
        ("HuggingFaceFW/fineweb-2", "data/tur_Latn/train/", "text"),
    ],
    "ar": [
        ("wikimedia/wikipedia", "20231101.ar/", "text"),
        ("HuggingFaceFW/fineweb-2", "data/arb_Arab/train/", "text"),
    ],
}

N_TRAIN = 80_000   # module default; raise with --n-train for a full-scale run
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


def _collect_from_source(repo_id: str, prefix: str, col: str, cap: int,
                         seen: set, lang: str) -> list:
    """Stream one parquet source, returning up to `cap` new (deduped) sentences.
    Reads parquet directly from the HF Hub (bypasses `datasets`/torch)."""
    from huggingface_hub import HfApi, hf_hub_download
    import pyarrow.parquet as pq
    out: list = []
    if cap <= 0:
        return out
    api = HfApi()
    try:
        files = api.list_repo_files(repo_id=repo_id, repo_type="dataset")
    except Exception as e:
        log_event("error", lang=lang, repo=repo_id, stage="list_repo_files", error=str(e))
        print(f"[{lang}] {repo_id}: list_repo_files failed: {e}", file=sys.stderr)
        return out
    shards = sorted(f for f in files
                    if f.startswith(prefix) and f.endswith(".parquet"))
    if not shards:
        print(f"[{lang}] {repo_id}: no parquet shards under {prefix}", file=sys.stderr)
        return out
    print(f"[{lang}] {repo_id}: {len(shards)} shard(s); pulling up to {cap:,}",
          file=sys.stderr)
    try:
        for shard in shards:
            local = hf_hub_download(repo_id=repo_id, filename=shard, repo_type="dataset")
            pf = pq.ParquetFile(local)
            for rg_idx in range(pf.num_row_groups):
                tbl = pf.read_row_group(rg_idx, columns=[col])
                for text in tbl.column(col).to_pylist():
                    if not text:
                        continue
                    for sent in SENT_SPLIT.split(text):
                        sent = " ".join(sent.split())
                        if len(sent) < MIN_LINE_CHARS:
                            continue
                        h = hash(sent)
                        if h in seen:
                            continue
                        seen.add(h)
                        out.append(sent)
                        if len(out) >= cap:
                            return out
    except Exception as e:
        log_event("error", lang=lang, repo=repo_id, stage="stream",
                  collected=len(out), error=str(e))
        print(f"[{lang}] {repo_id}: stream failed after {len(out):,}: {e}",
              file=sys.stderr)
    return out


def download_language(lang: str, n_train: int, n_val: int, n_test: int,
                      seed: int, force: bool) -> bool:
    import random
    if already_downloaded(lang) and not force:
        log_event("skip", lang=lang, reason="already_downloaded")
        print(f"[{lang}] already downloaded, skipping", file=sys.stderr)
        return True

    try:
        import huggingface_hub  # noqa: F401
        import pyarrow  # noqa: F401
    except ImportError as e:
        print(f"required library missing: {e}. pip install huggingface_hub pyarrow",
              file=sys.stderr)
        return False

    sources = SOURCES[lang]
    target_total = n_train + n_val + n_test
    log_event("start", lang=lang, sources=[s[0] for s in sources], target=target_total)
    print(f"[{lang}] fetching from {len(sources)} sources, target {target_total:,}",
          file=sys.stderr)
    t0 = time.time()

    seen: set = set()
    # Pass 1: balanced pull so the registers are represented roughly equally.
    per_source = -(-target_total // len(sources))  # ceil division
    pools = [_collect_from_source(r, p, c, per_source, seen, lang)
             for (r, p, c) in sources]
    collected = [s for pool in pools for s in pool]
    # Pass 2: if a source ran dry, top up from the others to hit the target.
    for (r, p, c) in sources:
        if len(collected) >= target_total:
            break
        collected.extend(_collect_from_source(
            r, p, c, target_total - len(collected), seen, lang))

    if len(collected) < target_total:
        log_event("partial", lang=lang, collected=len(collected), target=target_total)
        print(f"[{lang}] only {len(collected):,}/{target_total:,} sentences available",
              file=sys.stderr)

    # Shuffle so the two registers interleave (no large homogeneous blocks).
    random.Random(seed).shuffle(collected)
    train = collected[:n_train]
    val = collected[n_train:n_train + n_val]
    test = collected[n_train + n_val:n_train + n_val + n_test]

    for split, lines in (("train", train), ("val", val), ("test", test)):
        p = DATA_DIR / f"{lang}_{split}.txt"
        tmp = p.with_suffix(".txt.tmp")
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        tmp.replace(p)

    elapsed = time.time() - t0
    per_source_counts = {s[0]: len(pool) for s, pool in zip(sources, pools)}
    log_event("complete", lang=lang, n_train=len(train), n_val=len(val),
              n_test=len(test), per_source=per_source_counts,
              elapsed_s=round(elapsed, 1))
    print(f"[{lang}] wrote {len(train):,} train / {len(val):,} val / "
          f"{len(test):,} test from {per_source_counts} ({elapsed:.0f}s)",
          file=sys.stderr)
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--langs", nargs="+", default=list(SOURCES.keys()),
                    choices=list(SOURCES.keys()))
    ap.add_argument("--n-train", type=int, default=N_TRAIN)
    ap.add_argument("--n-val", type=int, default=N_VAL)
    ap.add_argument("--n-test", type=int, default=N_TEST)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--force-redownload", action="store_true")
    args = ap.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    failures = 0
    for lang in args.langs:
        if not download_language(lang, args.n_train, args.n_val, args.n_test,
                                 args.seed, args.force_redownload):
            failures += 1

    print(f"\nFailures: {failures} / {len(args.langs)}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
