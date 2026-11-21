"""make_figures_p2b.py — Regenerate the Arabic ablation and seed-robustness figures.

Produces properly proportioned (wide, short, matching fig_p2_rebate's aspect
ratio) versions of:
    fig_p2_ablation — primary-run Arabic baseline / grammar-aware / shuffled-control bpc
    fig_p2_seeds    — same three regimes, mean +/- sample std over four seeds

Data sources:
    fig_p2_ablation: the primary-run bpc values quoted in sec_06_results.tex
        S5.3 (no separate data file carries them; this is the single training
        run reported in prose, distinct from the four-seed replication).
    fig_p2_seeds: results/phase2_seeds/results.csv (per-seed final_eval_bpc).

Writes manuscript/figures/fig_p2_ablation.{pdf,png} and fig_p2_seeds.{pdf,png}.
Both figures share one set of regime labels so the paper names the three
models identically in each.

Usage:
    python morph_efficiency_project/scripts/make_figures_p2b.py
"""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SEEDS_CSV = ROOT / "results" / "phase2_seeds" / "results.csv"
OUT = ROOT / "manuscript" / "figures"

# One label per regime, shared by both figures.
LABELS = [
    "baseline\n(byte-pair only)",
    "grammar-aware\n(real root + wazn)",
    "shuffled control\n(shuffled root + wazn)",
]

# sec_06_results.tex S5.3, primary run (single training run, not seed-averaged).
ABLATION_PRIMARY = dict(zip(LABELS, [1.1464, 1.1246, 1.1676]))
ABLATION_COLORS = ["#888888", "#1d5619", "#c0392b"]

plt.rcParams.update({
    "figure.dpi": 150,
    "font.family": "serif",
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 10,
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.bbox": "tight",
})


def save(fig, stem: str) -> None:
    for ext in ("pdf", "png"):
        path = OUT / f"{stem}.{ext}"
        fig.savefig(path)
        print(f"wrote {path}")
    plt.close(fig)


def fig_p2_ablation() -> None:
    labels = list(ABLATION_PRIMARY.keys())
    values = list(ABLATION_PRIMARY.values())

    fig, ax = plt.subplots(figsize=(5.6, 1.9))
    bars = ax.bar(labels, values, color=ABLATION_COLORS, edgecolor="black",
                   linewidth=0.6, width=0.55)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.0015, f"{v:.4f}",
                 ha="center", va="bottom", fontsize=7.5, color="#333")

    ax.axhline(values[0], color="#888", linewidth=0.7, linestyle=":")
    ax.set_ylabel("bits per character")
    ax.set_ylim(1.115, 1.175)
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    save(fig, "fig_p2_ablation")


def fig_p2_seeds() -> None:
    rows = list(csv.DictReader(open(SEEDS_CSV)))
    groups = defaultdict(list)
    for r in rows:
        groups[r["cell"].rsplit("_s", 1)[0]].append(float(r["final_eval_bpc"]))

    order = ["ar_baseline", "ar_morph", "ar_shuf"]
    colors = ["#888888", "#1d5619", "#c0392b"]

    means = [statistics.mean(groups[k]) for k in order]
    stds = [statistics.stdev(groups[k]) for k in order]

    fig, ax = plt.subplots(figsize=(5.6, 1.9))
    x = np.arange(len(order))
    bars = ax.bar(x, means, yerr=stds, capsize=4, color=colors,
                   edgecolor="black", linewidth=0.6, width=0.55,
                   error_kw=dict(elinewidth=1.0, ecolor="#333"))
    for bar, v, sd in zip(bars, means, stds):
        ax.text(bar.get_x() + bar.get_width() / 2, v + sd + 0.002,
                 f"{v:.4f}", ha="center", va="bottom", fontsize=7.5, color="#333")

    ax.set_xticks(x)
    ax.set_xticklabels(LABELS)
    ax.set_ylabel("bits per character")
    ax.set_ylim(1.115, 1.175)
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    save(fig, "fig_p2_seeds")


def main() -> int:
    if not SEEDS_CSV.exists():
        print(f"Missing input: {SEEDS_CSV}.")
        return 1
    fig_p2_ablation()
    fig_p2_seeds()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
