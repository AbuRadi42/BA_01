"""
make_figures.py — Manuscript figure draft generator.

Produces three figures from the existing hl_metrics.json, alpha_fit.json,
and mini_summary.json artefacts:

    Figure 1 — Ordinal validation: rho * H(L) vs observed Delta L across
               the three Phase 1 languages.
    Figure 2 — Implied per-language alpha dispersion under three entropy
               floor choices (the Agglutinative Compounding Effect plot).
    Figure 3 — Schematic of the capability-vs-scale curve shift predicted
               by equation (4.8) under morphology-aligned tokenization.

Outputs go to manuscript/figures/ as PDF (for LaTeX) and PNG (for review).

Usage:
    python morph_efficiency_project/scripts/make_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HL = ROOT / "manuscript" / "hl_metrics.json"
ALPHA = ROOT / "manuscript" / "alpha_fit.json"
OUT = ROOT / "manuscript" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

LANG_LABEL = {"en": "English", "ar": "Arabic", "tr": "Turkish"}
LANG_ORDER = ["en", "ar", "tr"]
LANG_COLOR = {"en": "#394195", "ar": "#1d5619", "tr": "#df3e29"}

# Journal-friendly defaults
plt.rcParams.update({
    "figure.figsize": (6.0, 3.8),
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


def fig1_ordinal_validation() -> None:
    """Figure 1 — rho*H vs observed Delta L across three languages."""
    hl_data = {r["lang"]: r for r in json.loads(HL.read_text())["results"]}
    alpha_data = {r["lang"]: r for r in json.loads(ALPHA.read_text())["rows"]}

    fig, ax = plt.subplots()
    xs, ys = [], []
    for lang in LANG_ORDER:
        x = hl_data[lang]["rho_sig_times_H_bits"]
        y = alpha_data[lang]["delta_L_nats"]
        xs.append(x); ys.append(y)
        ax.scatter(x, y, s=80, color=LANG_COLOR[lang], zorder=3,
                   edgecolor="black", linewidth=0.8)
        ax.annotate(
            LANG_LABEL[lang],
            xy=(x, y),
            xytext=(8, 6), textcoords="offset points",
            fontsize=9, color=LANG_COLOR[lang], weight="bold",
        )

    # Connecting dashed line showing the monotonic ordering
    order = np.argsort(xs)
    ax.plot(np.array(xs)[order], np.array(ys)[order],
            linestyle="--", linewidth=0.8, color="#888", zorder=2)

    ax.set_xlabel(r"$\rho(L)\cdot H(L)$  (bits, engine-derived)")
    ax.set_ylabel(r"$\Delta\mathcal{L}$  (nats, morph vs BPE at 2M params)")
    ax.set_yscale("log")
    ax.set_title("Fig. 1 — Ordinal validation of the parameter-rebate prediction")
    ax.grid(True, which="both", linestyle=":", alpha=0.4)
    save(fig, "fig_01_ordinal_validation")


def fig2_alpha_dispersion() -> None:
    """Figure 2 — implied alpha per language under three E choices."""
    data = json.loads(ALPHA.read_text())
    rows = {r["lang"]: r for r in data["rows"]}

    E_labels = {
        "E0":       r"$E = 0$",
        "E_chinch": r"$E = 1.7$ (Chinchilla)",
        "Elocal":   r"$E_L = \mathcal{L}_{\mathrm{BPE}} - 1$",
    }
    E_keys = list(E_labels.keys())

    langs = LANG_ORDER
    x = np.arange(len(langs))
    width = 0.26

    fig, ax = plt.subplots()
    for i, ek in enumerate(E_keys):
        values = [rows[l][f"alpha_{ek}_params_per_bit"] for l in langs]
        bars = ax.bar(
            x + (i - 1) * width,
            values,
            width=width,
            label=E_labels[ek],
            edgecolor="black",
            linewidth=0.6,
        )
        for bar, v in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                v * 1.08,
                f"{v/1000:.0f}k",
                ha="center", va="bottom", fontsize=7, color="#444",
            )

    ax.set_xticks(x)
    ax.set_xticklabels([LANG_LABEL[l] for l in langs])
    ax.set_ylabel(r"Implied $\alpha$  (parameters per bit of $\rho\cdot H$)")
    ax.set_yscale("log")
    ax.set_title(r"Fig. 2 — Dispersion of implied $\alpha$: the Agglutinative Compounding Effect")
    ax.legend(loc="upper left", frameon=False)
    ax.grid(True, axis="y", which="both", linestyle=":", alpha=0.4)

    # Annotate the max/min spread on the E_chinch row
    en_a = rows["en"]["alpha_E_chinch_params_per_bit"]
    tr_a = rows["tr"]["alpha_E_chinch_params_per_bit"]
    spread = tr_a / en_a
    ax.text(
        0.98, 0.03,
        f"Turkish / English (E=1.7): {spread:.1f}x",
        transform=ax.transAxes, ha="right", va="bottom",
        fontsize=8, color="#555", style="italic",
    )
    save(fig, "fig_02_alpha_dispersion")


def fig3_curve_shift_schematic() -> None:
    """Figure 3 — schematic of the capability-vs-scale curve shift [eq. 4.8]."""
    fig, ax = plt.subplots()

    N = np.logspace(7, 11, 200)            # parameter count, log scale
    # Two sigmoid capability curves: morph shifted left by delta_logN
    def sigmoid(logN, center):
        return 1.0 / (1.0 + np.exp(-(logN - center) * 4.0))

    log_centre_bpe = 10.2
    log_centre_morph = log_centre_bpe - 0.7  # illustrative shift

    y_bpe = sigmoid(np.log10(N), log_centre_bpe)
    y_morph = sigmoid(np.log10(N), log_centre_morph)

    ax.plot(N, y_bpe, color="#394195", linewidth=1.6, label="BPE baseline")
    ax.plot(N, y_morph, color="#df3e29", linewidth=1.6, linestyle="--",
            label="Morphology-aligned")

    # Target capability
    T = 0.7
    ax.axhline(T, color="#888", linewidth=0.8, linestyle=":")
    ax.text(N[0], T + 0.02, r"target capability $T$", color="#555", fontsize=8)

    # Crossings
    from numpy import argmin
    N_bpe = N[argmin(np.abs(y_bpe - T))]
    N_morph = N[argmin(np.abs(y_morph - T))]
    ax.axvline(N_bpe, color="#394195", linewidth=0.7, linestyle=":")
    ax.axvline(N_morph, color="#df3e29", linewidth=0.7, linestyle=":")

    # Arrow showing the shift
    ax.annotate(
        "", xy=(N_morph, 0.15), xytext=(N_bpe, 0.15),
        arrowprops=dict(arrowstyle="->", color="black", lw=1.0),
    )
    ax.text(
        np.sqrt(N_bpe * N_morph), 0.18,
        r"$\Delta N(L) = \alpha\,\rho(L)\,H(L)$",
        ha="center", va="bottom", fontsize=9,
    )

    # Edge budget
    N_edge = 1e9
    ax.axvspan(N[0], N_edge, alpha=0.08, color="#1d5619")
    ax.text(
        N[0] * 1.3, 0.93,
        "edge-hostable\nregime",
        color="#1d5619", fontsize=8, va="top",
    )

    ax.set_xscale("log")
    ax.set_xlim(N[0], N[-1])
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Parameter count $N$ (log scale)")
    ax.set_ylabel("Capability score")
    ax.set_title("Fig. 3 — Predicted capability-vs-scale curve shift under morphology-aligned tokenization")
    ax.legend(loc="center right", frameon=False)
    ax.grid(True, which="both", linestyle=":", alpha=0.4)
    save(fig, "fig_03_curve_shift_schematic")


def main() -> int:
    if not HL.exists() or not ALPHA.exists():
        print(f"Missing inputs: {HL} or {ALPHA}. Run compute_hl.py and fit_alpha.py first.")
        return 1
    fig1_ordinal_validation()
    fig2_alpha_dispersion()
    fig3_curve_shift_schematic()
    print(f"\n{len(list(OUT.glob('fig_*.pdf')))} PDF + PNG pairs in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
