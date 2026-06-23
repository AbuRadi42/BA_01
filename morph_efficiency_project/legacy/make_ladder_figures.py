"""
make_ladder_figures.py — Paper-ready figures from the scale-ladder data.

Reads:
    manuscript/ladder_metrics.json (from aggregate_ladder.py)

Writes (PDF + PNG for each):
    manuscript/figures/fig_04_learning_curves_grid.{pdf,png}
    manuscript/figures/fig_05_alpha_vs_scale.{pdf,png}
    manuscript/figures/fig_06_ordinal_per_rung.{pdf,png}

Missing (lang, rung) cells are drawn as grey placeholders in the learning-
curve grid and omitted from the other figures — safe to run while the
ladder is still in flight.

Usage:
    python morph_efficiency_project/scripts/make_ladder_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
LADDER_METRICS = ROOT / "manuscript" / "ladder_metrics.json"
OUT_DIR = ROOT / "manuscript" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LANG_LABEL = {
    "en": "English", "ar": "Arabic", "tr": "Turkish",
    "de": "German", "es": "Spanish", "hu": "Hungarian",
    "sw": "Swahili", "eu": "Basque", "zh": "Mandarin",
}
LANG_COLOR = {
    "en": "#394195", "ar": "#1d5619", "tr": "#df3e29",
    "de": "#7c5b2b", "es": "#a1572d", "hu": "#6b3fa0",
    "sw": "#2c8a8a", "eu": "#b02a7f", "zh": "#555555",
}

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
        path = OUT_DIR / f"{stem}.{ext}"
        fig.savefig(path)
        print(f"wrote {path}")
    plt.close(fig)


def load() -> dict:
    if not LADDER_METRICS.exists():
        raise SystemExit(f"missing {LADDER_METRICS}; run aggregate_ladder.py first")
    return json.loads(LADDER_METRICS.read_text(encoding="utf-8"))


def fig_learning_curves(data: dict) -> None:
    """3x3 grid: one panel per language, BPE vs morph across rungs."""
    derived = data["derived"]
    by_lang: dict[str, dict[int, dict]] = {}
    for d in derived:
        by_lang.setdefault(d["lang"], {})[d["rung"]] = d

    langs = sorted(by_lang.keys(), key=lambda l: LANG_LABEL.get(l, l))
    cols = 3
    rows = max(1, (len(langs) + cols - 1) // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.6, rows * 2.2), squeeze=False)

    for idx in range(rows * cols):
        r, c = divmod(idx, cols)
        ax = axes[r][c]
        if idx >= len(langs):
            ax.axis("off")
            continue
        lang = langs[idx]
        rungs = sorted(by_lang[lang].keys())
        xs, ys_bpe, ys_morph = [], [], []
        for rung in rungs:
            entry = by_lang[lang][rung]
            if not (entry.get("has_baseline") and entry.get("has_morph")):
                continue
            xs.append(entry.get("n_params_baseline") or entry.get("params_target"))
            ys_bpe.append(entry["L_baseline"])
            ys_morph.append(entry["L_morph"])

        color = LANG_COLOR.get(lang, "#333")
        if xs:
            ax.plot(xs, ys_bpe, "o-", color=color, label="BPE", linewidth=1.2)
            ax.plot(xs, ys_morph, "s--", color=color, label="Morph", linewidth=1.2, markerfacecolor="white")
        else:
            ax.text(0.5, 0.5, "no data", transform=ax.transAxes,
                    ha="center", va="center", color="#aaa", fontsize=8)

        ax.set_title(LANG_LABEL.get(lang, lang), color=color, fontsize=10)
        ax.set_xscale("log")
        if xs:
            ax.legend(loc="upper right", frameon=False, fontsize=7)
        if c == 0:
            ax.set_ylabel(r"$\mathcal{L}$ (nats)")
        if r == rows - 1:
            ax.set_xlabel(r"$N$ (params, log)")
        ax.grid(True, which="both", linestyle=":", alpha=0.4)

    fig.suptitle("Fig. 4 — Per-language learning curves across the Chinchilla-ratio scale ladder",
                 fontsize=10, y=1.02)
    save(fig, "fig_04_learning_curves_grid")


def fig_alpha_vs_scale(data: dict) -> None:
    """One plot: implied alpha per language across rungs, symlog-y so that
    sign-flipped rungs (negative implied alpha, i.e. morph-worse-than-BPE at
    well-trained scales) remain visible instead of being silently dropped by
    a plain log axis."""
    derived = data["derived"]
    by_lang: dict[str, list[tuple[int, float]]] = {}
    for d in derived:
        if d.get("implied_alpha_params_per_bit") is not None and d.get("n_params_baseline"):
            by_lang.setdefault(d["lang"], []).append(
                (d["n_params_baseline"], d["implied_alpha_params_per_bit"])
            )

    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    any_drawn = False
    for lang, points in sorted(by_lang.items()):
        points.sort()
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        if not xs:
            continue
        any_drawn = True
        color = LANG_COLOR.get(lang, "#333")
        ax.plot(xs, ys, "o-", color=color,
                label=LANG_LABEL.get(lang, lang), linewidth=1.3)
        # Mark sign-flipped rungs with a hollow red ring so the reader sees
        # "morph worse than BPE at this scale" rather than a dropped datum.
        neg_xs = [x for x, y in points if y < 0]
        neg_ys = [y for x, y in points if y < 0]
        if neg_xs:
            ax.scatter(neg_xs, neg_ys, s=120, facecolors="none",
                       edgecolors="#b03030", linewidth=1.5, zorder=4)

    if not any_drawn:
        ax.text(0.5, 0.5, "no paired runs yet", transform=ax.transAxes,
                ha="center", va="center", color="#aaa")
    else:
        ax.set_xscale("log")
        ax.set_yscale("symlog", linthresh=1e4)
        ax.axhline(0, color="#888", linewidth=0.8, linestyle=":")
        ax.set_xlabel(r"Parameter count $N$ (log scale)")
        ax.set_ylabel(r"Implied $\alpha$  (parameters per bit of $\rho\cdot H$, symlog)")
        ax.legend(loc="best", frameon=False)
        ax.grid(True, which="both", linestyle=":", alpha=0.4)

    ax.set_title("Fig. 5 — Implied $\\alpha$ across the scale ladder (A-vs-B discriminating figure)",
                 fontsize=10)
    save(fig, "fig_05_alpha_vs_scale")


def fig_ordinal_per_rung(data: dict) -> None:
    """Per-rung scatter of Delta_L vs rho*H. Uses symlog-y so that sign-flipped
    (negative Delta_L) points remain visible rather than being silently dropped
    by a plain log axis. The y-axis is shared across panels to make cross-rung
    comparison straightforward."""
    derived = data["derived"]
    rungs = sorted({d["rung"] for d in derived if d.get("delta_L") is not None})
    if not rungs:
        print("no rungs with delta_L yet; skipping fig_06")
        return

    # Global y-range across all panels so panels align visually.
    all_y = [d["delta_L"] for d in derived if d.get("delta_L") is not None]
    if all_y:
        y_min, y_max = min(all_y), max(all_y)
        y_pad = 0.15 * max(abs(y_min), abs(y_max))
        y_lim = (y_min - y_pad, y_max + y_pad)
    else:
        y_lim = (-1, 1)

    all_x = [d.get("rho_times_H_bits") for d in derived if d.get("rho_times_H_bits") is not None]
    if all_x:
        x_min, x_max = min(all_x), max(all_x)
        x_pad = 0.15 * (x_max - x_min or 1)
        x_lim = (x_min - x_pad, x_max + x_pad)
    else:
        x_lim = (0, 5)

    cols = min(3, len(rungs))
    rows = max(1, (len(rungs) + cols - 1) // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3.0, rows * 2.8),
                             squeeze=False, sharey=True, sharex=True)

    for idx in range(rows * cols):
        r, c = divmod(idx, cols)
        ax = axes[r][c]
        if idx >= len(rungs):
            ax.axis("off")
            continue
        rung = rungs[idx]
        entries = [d for d in derived if d["rung"] == rung and d.get("delta_L") is not None]
        entries.sort(key=lambda d: d.get("rho_times_H_bits") or 0)
        for d in entries:
            x = d.get("rho_times_H_bits")
            y = d.get("delta_L")
            if x is None or y is None:
                continue
            color = LANG_COLOR.get(d["lang"], "#333")
            ax.scatter(x, y, s=60, color=color,
                       edgecolor="black", linewidth=0.5, zorder=3)
            ax.annotate(LANG_LABEL.get(d["lang"], d["lang"]),
                        xy=(x, y), xytext=(5, 3), textcoords="offset points",
                        fontsize=7, color=color)
        xs = [d.get("rho_times_H_bits") for d in entries if d.get("rho_times_H_bits") is not None]
        ys = [d.get("delta_L") for d in entries if d.get("delta_L") is not None]
        if xs and ys:
            order = np.argsort(xs)
            ax.plot(np.array(xs)[order], np.array(ys)[order], "--", color="#aaa", linewidth=0.8)

        ax.axhline(0, color="#888", linewidth=0.8, linestyle=":")
        ax.set_xlim(x_lim)
        ax.set_ylim(y_lim)
        ax.set_title(f"Rung {rung}", fontsize=9)
        if c == 0:
            ax.set_ylabel(r"$\Delta\mathcal{L}$ (nats)")
        if r == rows - 1:
            ax.set_xlabel(r"$\rho\cdot H$ (bits)")
        ax.grid(True, which="both", linestyle=":", alpha=0.4)

    fig.suptitle("Fig. 6 — Ordinal consistency across the ladder (linear y-axis; dotted line marks $\\Delta\\mathcal{L}=0$)",
                 fontsize=10, y=1.02)
    save(fig, "fig_06_ordinal_per_rung")


def main() -> int:
    data = load()
    fig_learning_curves(data)
    fig_alpha_vs_scale(data)
    fig_ordinal_per_rung(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
