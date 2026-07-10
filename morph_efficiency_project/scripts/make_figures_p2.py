"""make_figures_p2.py — Regenerate the Phase 2 rebate and prediction figures.

Produces properly proportioned (wide, short) versions of:
    fig_p2_rebate      — Delta bpc by language (Table tab:phase2 in sec_06_results.tex)
    fig_p2_prediction  — Delta bpc vs rho*H predictor

Data sources (no other file in the repo carries these numbers):
    Delta bpc, per language: Table tab:phase2, sec_06_results.tex
    rho*H, per language:     manuscript/rho_h_20k.json

Writes to manuscript/figures/ as *_v2.pdf / *_v2.png so the existing
fig_p2_rebate.pdf / fig_p2_prediction.pdf are left untouched pending review.

Usage:
    python morph_efficiency_project/scripts/make_figures_p2.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RHO_H = ROOT / "manuscript" / "rho_h_20k.json"
OUT = ROOT / "manuscript" / "figures"

LANG_ORDER = ["zh", "en", "tr", "ar"]
LANG_LABEL = {"zh": "Mandarin", "en": "English", "tr": "Turkish", "ar": "Arabic"}
LANG_COLOR = {"zh": "#e08214", "en": "#394195", "tr": "#df3e29", "ar": "#1d5619"}

# Table tab:phase2, sec_06_results.tex — Delta bpc column.
DELTA_BPC = {"zh": -0.0044, "en": -0.0356, "tr": -0.0165, "ar": 0.0218}

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


def fig_p2_rebate() -> None:
    langs = LANG_ORDER
    values = [DELTA_BPC[l] for l in langs]
    colors = [LANG_COLOR[l] for l in langs]

    fig, ax = plt.subplots(figsize=(5.6, 1.9))
    x = np.arange(len(langs))
    bars = ax.bar(x, values, color=colors, edgecolor="black", linewidth=0.6, width=0.55)
    for bar, v in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            v + (0.0015 if v >= 0 else -0.0015),
            f"{v:+.4f}",
            ha="center", va="bottom" if v >= 0 else "top",
            fontsize=7.5, color="#333",
        )

    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([LANG_LABEL[l] for l in langs])
    ax.set_ylabel(r"$\Delta\mathrm{bpc}$")
    ax.grid(True, axis="y", linestyle=":", alpha=0.4)
    ax.set_ylim(-0.045, 0.032)
    save(fig, "fig_p2_rebate_v2")


def fig_p2_prediction() -> None:
    rho_h_data = json.loads(RHO_H.read_text())
    langs = LANG_ORDER
    xs = [rho_h_data[l]["rho_H"] for l in langs]
    ys = [DELTA_BPC[l] for l in langs]
    colors = [LANG_COLOR[l] for l in langs]

    fig, ax = plt.subplots(figsize=(5.6, 2.1))
    for l, x, y, c in zip(langs, xs, ys, colors):
        ax.scatter(x, y, s=70, color=c, zorder=3, edgecolor="black", linewidth=0.7)
        ax.annotate(
            LANG_LABEL[l], xy=(x, y), xytext=(6, 5), textcoords="offset points",
            fontsize=8, color=c, weight="bold",
        )

    ax.axhline(0, color="#888", linewidth=0.8, linestyle=":")
    ax.set_xlabel(r"$\rho(L)\cdot H(L)$")
    ax.set_ylabel(r"$\Delta\mathrm{bpc}$")
    ax.grid(True, linestyle=":", alpha=0.4)
    save(fig, "fig_p2_prediction_v2")


def main() -> int:
    if not RHO_H.exists():
        print(f"Missing input: {RHO_H}.")
        return 1
    fig_p2_rebate()
    fig_p2_prediction()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
