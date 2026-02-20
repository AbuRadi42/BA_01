"""
compute_metrics.py
------------------
Aggregates all evaluation JSON logs into summary tables and plots (plan.md §10).

Reads from:  logs/evaluation/
Writes to:   logs/summary/
  - summary_table.csv
  - learning_curves_{lang}.png  (one per language)
  - tokens_per_unit.png
  - agreement_accuracy.png
  - flops_vs_accuracy.png
  - conclusion.md

Usage:
  python scripts/compute_metrics.py
"""

import json
import logging
import os
from typing import Dict, List, Optional

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

LANGS   = ["en", "ar", "tr"]
REGIMES = ["baseline", "morph"]
EVAL_DIR    = os.path.join("logs", "evaluation")
SUMMARY_DIR = os.path.join("logs", "summary")
TRAIN_DIR   = os.path.join("logs", "training")


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def load_json(path: str) -> Optional[Dict]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"Could not read {path}: {e}")
        return None


def load_training_log(lang: str, regime: str) -> List[Dict]:
    path = os.path.join(TRAIN_DIR, f"{lang}_{regime}_training.json")
    data = load_json(path)
    if data is None:
        return []
    return data if isinstance(data, list) else []


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

def build_summary_table() -> List[Dict]:
    rows = []
    for lang in LANGS:
        for regime in REGIMES:
            row: Dict = {"model": f"{lang}_{regime}", "language": lang, "regime": regime}

            lm = load_json(os.path.join(EVAL_DIR, f"{lang}_{regime}_lm.json"))
            if lm:
                row["test_ppl"]  = lm.get("test_ppl")
                row["val_ppl"]   = lm.get("val_ppl")
                row["test_loss"] = lm.get("test_loss")

            morph = load_json(os.path.join(EVAL_DIR, f"{lang}_{regime}_morph.json"))
            if morph:
                row["tokens_per_unit"]   = morph.get("tokens_per_meaning_unit")
                row["agreement_acc"]     = morph.get("agreement_accuracy")
                row["bundle_acc"]        = morph.get("bundle_accuracy")
                row["nats_per_morpheme"] = morph.get("nats_per_morpheme")

            compute = load_json(os.path.join(EVAL_DIR, f"{lang}_{regime}_compute.json"))
            if compute:
                row["flops_per_token"]   = compute.get("flops_per_token")
                row["latency_ms"]        = compute.get("inference_latency_ms")
                row["attn_gini"]         = compute.get("attn_gini")
                row["attn_entropy"]      = compute.get("attn_entropy")

            # Training stats from last checkpoint
            train_log = load_training_log(lang, regime)
            if train_log:
                last = train_log[-1]
                row["train_tokens"]  = last.get("tokens_processed")
                row["train_time_hr"] = round(last.get("wall_time_sec", 0) / 3600, 2)

            rows.append(row)
    return rows


def save_csv(rows: List[Dict], path: str):
    if not rows:
        return
    cols = list(rows[0].keys())
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(cols) + "\n")
        for row in rows:
            f.write(",".join(str(row.get(c, "")) for c in cols) + "\n")
    log.info(f"Summary table saved → {path}")


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_learning_curves():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        log.warning("matplotlib not available — skipping plots.")
        return

    for lang in LANGS:
        fig, ax = plt.subplots(figsize=(8, 5))
        plotted = False
        for regime in REGIMES:
            train_log = load_training_log(lang, regime)
            if not train_log:
                continue
            steps  = [e["step"]            for e in train_log if "step"  in e]
            losses = [e["loss"]            for e in train_log if "loss"  in e]
            if steps and losses:
                ax.plot(steps, losses, label=f"{lang}_{regime}")
                plotted = True

        if plotted:
            ax.set_xlabel("Training step")
            ax.set_ylabel("Loss")
            ax.set_title(f"Learning curves — {lang.upper()}")
            ax.legend()
            out = os.path.join(SUMMARY_DIR, f"learning_curves_{lang}.png")
            fig.savefig(out, dpi=150, bbox_inches="tight")
            log.info(f"Saved → {out}")
        plt.close(fig)


def plot_bar(values_by_model: Dict[str, Optional[float]], ylabel: str,
             title: str, filename: str):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return

    labels = [k for k, v in values_by_model.items() if v is not None]
    vals   = [values_by_model[k] for k in labels]
    if not labels:
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    colors  = ["#4C72B0" if "baseline" in l else "#DD8452" for l in labels]
    ax.bar(labels, vals, color=colors)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=45)
    out = os.path.join(SUMMARY_DIR, filename)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info(f"Saved → {out}")


def plot_flops_vs_accuracy(rows: List[Dict]):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return

    fig, ax = plt.subplots(figsize=(8, 6))
    for row in rows:
        flops = row.get("flops_per_token")
        ppl   = row.get("test_ppl")
        if flops is None or ppl is None:
            continue
        label  = row["model"]
        marker = "o" if row["regime"] == "baseline" else "^"
        ax.scatter(flops, ppl, label=label, marker=marker, s=80)

    ax.set_xlabel("FLOPs per token")
    ax.set_ylabel("Test perplexity (lower = better)")
    ax.set_title("FLOPs vs Accuracy (Pareto view)")
    ax.legend(fontsize=7)
    out = os.path.join(SUMMARY_DIR, "flops_vs_accuracy.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info(f"Saved → {out}")


# ---------------------------------------------------------------------------
# Conclusion report
# ---------------------------------------------------------------------------

def write_conclusion(rows: List[Dict]):
    path = os.path.join(SUMMARY_DIR, "conclusion.md")

    lines = ["# Conclusion\n"]

    for lang in LANGS:
        base_row  = next((r for r in rows if r["language"] == lang and r["regime"] == "baseline"), {})
        morph_row = next((r for r in rows if r["language"] == lang and r["regime"] == "morph"),    {})

        lines.append(f"\n## {lang.upper()}\n")

        # Perplexity
        b_ppl = base_row.get("test_ppl")
        m_ppl = morph_row.get("test_ppl")
        if b_ppl and m_ppl:
            delta = round(b_ppl - m_ppl, 2)
            lines.append(
                f"Test perplexity: baseline={b_ppl}, morph={m_ppl} "
                f"(delta={delta:+.2f}).\n"
            )

        # Tokens per meaning unit
        b_tpu = base_row.get("tokens_per_unit")
        m_tpu = morph_row.get("tokens_per_unit")
        if b_tpu and m_tpu:
            lines.append(
                f"Tokens per meaning unit: baseline={b_tpu}, morph={m_tpu}.\n"
            )

        # Agreement accuracy
        b_agr = base_row.get("agreement_acc")
        m_agr = morph_row.get("agreement_acc")
        if b_agr is not None or m_agr is not None:
            lines.append(
                f"Agreement accuracy: baseline={b_agr}, morph={m_agr}.\n"
            )

        # FLOPs
        b_fl = base_row.get("flops_per_token")
        m_fl = morph_row.get("flops_per_token")
        if b_fl and m_fl:
            lines.append(
                f"FLOPs per token: baseline={b_fl:,}, morph={m_fl:,}.\n"
            )

    lines.append("\n## Research Questions\n")
    lines.append(
        "1. Does morphology-aware preprocessing reduce tokens per meaning unit? "
        "— See tokens_per_unit column above.\n"
    )
    lines.append(
        "2. Does it reduce compute cost at equal performance? "
        "— See flops_per_token and test_ppl columns.\n"
    )
    lines.append(
        "3. Do Arabic and Turkish benefit more than English? "
        "— Compare delta values across languages.\n"
    )
    lines.append(
        "4. Is the efficiency gain significant enough to justify scaling research? "
        "— Determined by magnitude of deltas above.\n"
    )
    lines.append("\n*Only quantified findings are reported. No interpretation beyond the data.*\n")

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    log.info(f"Conclusion saved → {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(SUMMARY_DIR, exist_ok=True)

    rows = build_summary_table()
    save_csv(rows, os.path.join(SUMMARY_DIR, "summary_table.csv"))

    plot_learning_curves()

    tpu_map = {r["model"]: r.get("tokens_per_unit") for r in rows}
    plot_bar(tpu_map, "Tokens per meaning unit",
             "Tokens per Meaning Unit — Baseline vs Morph",
             "tokens_per_unit.png")

    agr_map = {r["model"]: r.get("agreement_acc") for r in rows}
    plot_bar(agr_map, "Agreement accuracy",
             "Agreement Accuracy — Baseline vs Morph",
             "agreement_accuracy.png")

    plot_flops_vs_accuracy(rows)
    write_conclusion(rows)

    log.info("compute_metrics.py complete.")


if __name__ == "__main__":
    main()
