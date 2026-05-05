"""
aggregate_ladder.py — Merge scale-ladder result JSONs into a single
analysis-ready metrics file.

Reads:
    mini_experiment/results_ladder/*/result.json
    manuscript/hl_metrics.json       (for rho and H per language)

Writes:
    manuscript/ladder_metrics.json   (per-run rows + per-(lang, rung) Delta_L
                                      + implied alpha per language)

Idempotent: safe to re-run any time; regenerates outputs from whatever
result JSONs exist on disk. Missing runs are reported as "incomplete" and
excluded from derived quantities rather than aborting.

Usage:
    python morph_efficiency_project/scripts/aggregate_ladder.py
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LADDER_DIR = ROOT / "mini_experiment" / "results_ladder"
HL_METRICS = ROOT / "manuscript" / "hl_metrics.json"
OUT = ROOT / "manuscript" / "ladder_metrics.json"

ALPHA_N = 0.34       # Hoffmann 2022 param-scaling exponent
E_CHINCHILLA = 1.7   # nats — conventional English irreducible-entropy estimate


def load_hl_by_lang() -> dict[str, dict]:
    if not HL_METRICS.exists():
        return {}
    return {r["lang"]: r for r in json.loads(HL_METRICS.read_text(encoding="utf-8"))["results"]}


def iter_result_jsons() -> list[Path]:
    return sorted(LADDER_DIR.glob("*/result.json"))


def parse_run_id(p: Path) -> dict | None:
    """Parse a run_id like 'en_baseline_rung1_250000p_5000000t'.

    Returns None for non-standard IDs (e.g. 'ar_morph_tier2_rung1_...'),
    which belong to side experiments and are aggregated separately.
    """
    run_id = p.parent.name
    parts = run_id.split("_")
    # Standard pattern: [lang, regime, rungN, Xp, Yt] (5 parts)
    if len(parts) != 5:
        return None
    lang, regime, rung_str, params_str, tokens_str = parts
    if not rung_str.startswith("rung"):
        return None
    try:
        rung = int(rung_str.removeprefix("rung"))
        params_target = int(params_str.removesuffix("p"))
        tokens = int(tokens_str.removesuffix("t"))
    except ValueError:
        return None
    return {
        "run_id": run_id,
        "lang": lang,
        "regime": regime,
        "rung": rung,
        "params_target": params_target,
        "tokens": tokens,
    }


def main() -> int:
    hl = load_hl_by_lang()
    rows: list[dict] = []
    for p in iter_result_jsons():
        meta = parse_run_id(p)
        if meta is None:
            continue  # side-experiment result (e.g. tier-2), handled elsewhere
        try:
            res = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        rows.append({**meta, **{
            "n_params": res.get("n_params"),
            "vocab_size": res.get("vocab_size"),
            "test_loss": res.get("test_loss"),
            "test_ppl": res.get("test_ppl"),
            "tokens_scored": res.get("tokens_scored"),
            "final_step": res.get("final_step"),
            "elapsed_s": res.get("elapsed_s"),
        }})

    # Pair baseline with morph per (lang, rung) to compute Delta_L and alpha.
    by_key: dict[tuple[str, int], dict[str, dict]] = {}
    for r in rows:
        by_key.setdefault((r["lang"], r["rung"]), {})[r["regime"]] = r

    derived: list[dict] = []
    for (lang, rung), regimes in sorted(by_key.items()):
        entry = {
            "lang": lang, "rung": rung,
            "has_baseline": "baseline" in regimes,
            "has_morph": "morph" in regimes,
        }
        if entry["has_baseline"] and entry["has_morph"]:
            bl, mr = regimes["baseline"], regimes["morph"]
            entry["L_baseline"] = bl["test_loss"]
            entry["L_morph"] = mr["test_loss"]
            entry["delta_L"] = bl["test_loss"] - mr["test_loss"]
            entry["ppl_baseline"] = bl["test_ppl"]
            entry["ppl_morph"] = mr["test_ppl"]
            entry["delta_ppl_pct"] = 100 * (1 - mr["test_ppl"] / bl["test_ppl"]) if bl["test_ppl"] else None
            entry["n_params_baseline"] = bl["n_params"]
            entry["n_params_morph"] = mr["n_params"]
            entry["tokens"] = bl.get("tokens") or mr.get("tokens")

            # rho * H and implied alpha under Chinchilla floor.
            if lang in hl:
                h_info = hl[lang]
                rho = h_info["rho_signature"]
                H = h_info["H_bits"]
                rho_H = rho * H
                entry["rho"] = rho
                entry["H_bits"] = H
                entry["rho_times_H_bits"] = rho_H
                # Delta_N via Hoffmann derivative at the baseline operating point.
                N = bl["n_params"] or 0
                if N > 0 and bl["test_loss"] > E_CHINCHILLA and rho_H > 0:
                    deltaN = entry["delta_L"] * N / (ALPHA_N * (bl["test_loss"] - E_CHINCHILLA))
                    entry["implied_delta_N_params"] = deltaN
                    entry["implied_alpha_params_per_bit"] = deltaN / rho_H
        derived.append(entry)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runs": rows,
        "derived": derived,
        "hl_source": str(HL_METRICS),
        "alpha_N": ALPHA_N,
        "E_chinchilla_nats": E_CHINCHILLA,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(OUT)

    # Short stdout summary
    print(f"runs:    {len(rows)} result files found")
    print(f"pairs:   {sum(1 for d in derived if d.get('has_baseline') and d.get('has_morph'))} complete (baseline+morph) per (lang, rung)")
    print()
    print(f"{'Lang':>5} {'Rung':>4} {'L_base':>7} {'L_morph':>7} {'dL':>7} {'Δppl%':>7} {'rho*H':>6} {'dN':>12} {'alpha':>10}")
    for d in derived:
        if d.get("has_baseline") and d.get("has_morph"):
            print(
                f"{d['lang']:>5} {d['rung']:>4} "
                f"{d['L_baseline']:>7.3f} {d['L_morph']:>7.3f} "
                f"{d['delta_L']:>7.4f} "
                f"{(d.get('delta_ppl_pct') or 0):>7.2f} "
                f"{(d.get('rho_times_H_bits') or 0):>6.2f} "
                f"{(d.get('implied_delta_N_params') or 0):>12.0f} "
                f"{(d.get('implied_alpha_params_per_bit') or 0):>10.0f}"
            )
    print(f"\nWrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
