"""
_plot_bundle_distribution.py
----------------------------
Per-language bundle-distribution visualisation (Tier 3 item 9).

For each of {zh, en, tr, ar} (canonical order), scan
mini_experiment/data/<lang>_train.txt (cap 20,000 sentences),
count bundle frequencies via engine.analyze(), and produce:

    logs/summary/bundle_dist_<lang>.png   single-language log-log Zipf plot
    logs/summary/bundle_dist_combined.png all 4 overlaid
    logs/summary/bundle_distribution_report.md

The Zipf exponent (slope of the log-log rank/frequency fit, taken as a
positive number) is reported per language as a sanity metric.

Usage:
    python morph_efficiency_project/scripts/_plot_bundle_distribution.py
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from morph_efficiency_project.scripts.engines import (
    ArabicEngine,
    EnglishEngine,
    MandarinEngine,
    TurkishEngine,
)

LANG_ORDER = ("zh", "en", "tr", "ar")
LANG_NAMES = {"zh": "Mandarin", "en": "English", "tr": "Turkish", "ar": "Arabic"}
COLOURS = {
    "zh": "#2c5fa8",  # blue
    "en": "#c46519",  # gold/amber
    "tr": "#2e7d4f",  # green
    "ar": "#6a3aa3",  # purple
}
ENGINES = {
    "zh": MandarinEngine,
    "en": EnglishEngine,
    "tr": EnglishEngine,  # placeholder, overwritten below
    "ar": ArabicEngine,
}
ENGINES["tr"] = TurkishEngine

CORPUS_DIR = ROOT / "mini_experiment" / "data"
OUT_DIR = ROOT / "morph_efficiency_project" / "logs" / "summary"
SENTENCE_CAP = 20_000
HEARTBEAT_EVERY = 2_000


def bundle_label(pos: str, tags_frozen: frozenset) -> str:
    """Human-readable gloss for a (POS, tags) bundle."""
    if not tags_frozen:
        return pos
    parts = sorted(f"{k}={v}" for k, v in tags_frozen)
    return f"{pos}[{','.join(parts)}]"


def scan_corpus(lang: str, sentence_cap: int = SENTENCE_CAP) -> Tuple[Counter, int, int]:
    """Return (bundle_counter, n_sentences, n_tokens) over train corpus."""
    engine = ENGINES[lang]()
    counts: Counter = Counter()
    n_sent = 0
    n_tok = 0
    path = CORPUS_DIR / f"{lang}_train.txt"
    if not path.exists():
        print(f"[{lang}] WARNING: {path} not found", flush=True)
        return counts, n_sent, n_tok

    print(f"[{lang}] scanning {path.name} (cap {sentence_cap:,})...", flush=True)
    t0 = time.time()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if n_sent >= sentence_cap:
                break
            words = list(line) if lang == "zh" else line.split()
            for w in words:
                if not w.strip():
                    continue
                try:
                    info = engine.analyze(w)
                except Exception:
                    continue
                pos = info.pos or "UNKNOWN"
                tags = frozenset(info.tags.items()) if info.tags else frozenset()
                counts[(pos, tags)] += 1
                n_tok += 1
            n_sent += 1
            if n_sent % HEARTBEAT_EVERY == 0:
                dt = time.time() - t0
                print(f"[{lang}]   {n_sent:>6,} sentences   "
                      f"{n_tok:>9,} tokens   {len(counts):>6,} unique bundles   "
                      f"({dt:.1f}s)", flush=True)
    dt = time.time() - t0
    print(f"[{lang}] done: {n_sent:,} sentences, {n_tok:,} tokens, "
          f"{len(counts):,} unique bundles ({dt:.1f}s)", flush=True)
    return counts, n_sent, n_tok


def zipf_exponent(freqs: List[int]) -> float:
    """Fit log(freq) = -alpha * log(rank) + c; return positive alpha.

    Uses ranks 1..min(len, 1000) on positive frequencies, both in log10.
    Returns nan if fewer than 5 distinct frequencies.
    """
    sorted_freqs = sorted([f for f in freqs if f > 0], reverse=True)
    if len(sorted_freqs) < 5:
        return float("nan")
    n = min(len(sorted_freqs), 1000)
    ranks = np.arange(1, n + 1)
    fs = np.asarray(sorted_freqs[:n], dtype=float)
    log_r = np.log10(ranks)
    log_f = np.log10(fs)
    slope, _ = np.polyfit(log_r, log_f, 1)
    return float(-slope)


def plot_single(lang: str, counts: Counter, alpha: float, out_path: Path) -> None:
    sorted_freqs = sorted(counts.values(), reverse=True)
    ranks = np.arange(1, len(sorted_freqs) + 1)
    fig, ax = plt.subplots(figsize=(6.0, 4.5))
    ax.loglog(ranks, sorted_freqs, marker="o", linestyle="none",
              markersize=3, color=COLOURS[lang], alpha=0.8,
              label=f"{LANG_NAMES[lang]} (alpha={alpha:.2f})")
    ax.set_xlabel("Rank (log)")
    ax.set_ylabel("Frequency (log)")
    ax.set_title(f"{LANG_NAMES[lang]} bundle frequency distribution")
    ax.grid(True, which="both", linestyle=":", alpha=0.4)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def plot_combined(per_lang: Dict[str, Tuple[Counter, float]], out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    for lang in LANG_ORDER:
        counts, alpha = per_lang[lang]
        if not counts:
            continue
        sorted_freqs = sorted(counts.values(), reverse=True)
        ranks = np.arange(1, len(sorted_freqs) + 1)
        ax.loglog(ranks, sorted_freqs, marker="o", linestyle="none",
                  markersize=2.5, color=COLOURS[lang], alpha=0.75,
                  label=f"{LANG_NAMES[lang]} (alpha={alpha:.2f})")
    ax.set_xlabel("Rank (log)")
    ax.set_ylabel("Frequency (log)")
    ax.set_title("Bundle frequency distribution by language")
    ax.grid(True, which="both", linestyle=":", alpha=0.4)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def verdict_for(alpha: float, counts: Counter) -> str:
    """Heuristic verdict on distribution health."""
    if not counts:
        return "no data"
    total = sum(counts.values())
    top_share = max(counts.values()) / total if total else 0.0
    if np.isnan(alpha):
        return "too few bundles to fit Zipf reliably"
    if top_share > 0.6:
        return (f"unhealthy: single bundle dominates "
                f"({top_share*100:.1f}% of mass)")
    if alpha < 0.5:
        return f"borderline: very flat tail (alpha={alpha:.2f})"
    if 0.7 <= alpha <= 2.2:
        return f"healthy: Zipf-like (alpha={alpha:.2f})"
    if alpha > 2.2:
        return f"steep: heavy head, thin tail (alpha={alpha:.2f})"
    return f"borderline (alpha={alpha:.2f})"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    per_lang: Dict[str, Tuple[Counter, float]] = {}
    stats: Dict[str, dict] = {}

    for lang in LANG_ORDER:
        counts, n_sent, n_tok = scan_corpus(lang)
        alpha = zipf_exponent(list(counts.values()))
        per_lang[lang] = (counts, alpha)
        single_path = OUT_DIR / f"bundle_dist_{lang}.png"
        plot_single(lang, counts, alpha, single_path)
        print(f"[{lang}] wrote {single_path.name}", flush=True)
        stats[lang] = {
            "n_sentences": n_sent,
            "n_tokens": n_tok,
            "n_unique_bundles": len(counts),
            "zipf_alpha": None if np.isnan(alpha) else round(alpha, 3),
            "top5": [
                {"bundle": bundle_label(pos, tags),
                 "count": int(c),
                 "share": round(c / max(sum(counts.values()), 1), 4)}
                for (pos, tags), c in counts.most_common(5)
            ],
            "verdict": verdict_for(alpha, counts),
        }

    combined_path = OUT_DIR / "bundle_dist_combined.png"
    plot_combined(per_lang, combined_path)
    print(f"wrote {combined_path.name}", flush=True)

    # Write JSON sidecar for downstream programmatic use.
    json_path = OUT_DIR / "bundle_distribution.json"
    json_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2),
                         encoding="utf-8")

    # Markdown report.
    lines: List[str] = []
    lines.append("# Bundle distribution report")
    lines.append("")
    lines.append(f"Corpus: `mini_experiment/data/<lang>_train.txt`, "
                 f"cap {SENTENCE_CAP:,} sentences per language.")
    lines.append("")
    lines.append("## Combined view")
    lines.append("")
    lines.append(f"![combined]({combined_path.name})")
    lines.append("")
    lines.append("## Per-language summary")
    lines.append("")
    lines.append("| Lang | Sentences | Tokens | Unique bundles | Zipf alpha | Verdict |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for lang in LANG_ORDER:
        s = stats[lang]
        alpha_str = "n/a" if s["zipf_alpha"] is None else f"{s['zipf_alpha']:.2f}"
        lines.append(f"| {LANG_NAMES[lang]} ({lang}) | "
                     f"{s['n_sentences']:,} | {s['n_tokens']:,} | "
                     f"{s['n_unique_bundles']:,} | {alpha_str} | {s['verdict']} |")
    lines.append("")

    for lang in LANG_ORDER:
        s = stats[lang]
        lines.append(f"### {LANG_NAMES[lang]} ({lang})")
        lines.append("")
        lines.append(f"![{lang}](bundle_dist_{lang}.png)")
        lines.append("")
        lines.append(f"- Total tokens scanned: {s['n_tokens']:,}")
        lines.append(f"- Unique bundles: {s['n_unique_bundles']:,}")
        alpha_str = "n/a" if s["zipf_alpha"] is None else f"{s['zipf_alpha']:.3f}"
        lines.append(f"- Zipf exponent (alpha): {alpha_str}")
        lines.append(f"- Verdict: {s['verdict']}")
        lines.append("")
        lines.append("Top-5 most frequent bundles:")
        lines.append("")
        lines.append("| Rank | Bundle (gloss) | Count | Share |")
        lines.append("|---:|---|---:|---:|")
        for i, entry in enumerate(s["top5"], 1):
            lines.append(f"| {i} | `{entry['bundle']}` | "
                         f"{entry['count']:,} | {entry['share']*100:.2f}% |")
        lines.append("")

    lines.append("## Methodology")
    lines.append("")
    lines.append("Zipf alpha is fit as the negated slope of "
                 "log10(freq) vs log10(rank) over the top 1,000 bundles "
                 "(or fewer if the unique-bundle count is smaller). "
                 "Healthy range is roughly 0.7 to 2.2; flat tails (alpha < 0.5) "
                 "or single-bundle dominance (top share > 60%) flag a problem.")
    lines.append("")

    report_path = OUT_DIR / "bundle_distribution_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {report_path.name}", flush=True)
    print(f"wrote {json_path.name}", flush=True)


if __name__ == "__main__":
    main()
