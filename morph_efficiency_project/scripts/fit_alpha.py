"""
fit_alpha.py — Fit the coefficient alpha in the parameter-rebate formula

    Delta_N(L) = alpha * rho(L) * H(L)           [R1]

from Phase 1 mini-experiment observations (test_loss under BPE and
morph-aligned tokenization, identical architecture) combined with the
H(L) and rho(L) values produced by compute_hl.py.

Conversion from Delta_L (test cross-entropy, nats) to Delta_N (parameters)
uses the Hoffmann/Chinchilla (2022) scaling law evaluated at the Phase 1
operating point (N = 2M, D = 5M tokens):

    L(N, D) = E + A * N^(-alpha_N) + B * D^(-alpha_D)
    dL / dN = -alpha_N * (L - E) / N

so Delta_N = Delta_L * N / (alpha_N * (L_baseline - E)).

Caveats (honest reporting in alpha_fit.json):
- alpha_N = 0.34 is taken from Hoffmann 2022; Phase 1 is ~8x
  Chinchilla-suboptimal in tokens, so the derivative estimate is
  a first-order approximation, not a precise calibration.
- E (irreducible entropy floor) varies by tokenizer and language.
  We report results with three choices: E = 0, E = 1.7 (Chinchilla
  English estimate), and a language-specific E_L = L_baseline - (1 nat).

Usage:
    python morph_efficiency_project/scripts/fit_alpha.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

HL_METRICS = ROOT / "manuscript" / "hl_metrics.json"
MINI_SUMMARY = ROOT / "mini_experiment" / "results" / "mini_summary.json"
OUT = ROOT / "manuscript" / "alpha_fit.json"

# Scaling-law constants
PHASE1_N = 2.0e6          # ~2M parameters, per mini_experiment/run_mini.py
PHASE1_D = 5.0e6          # ~5M training tokens
ALPHA_N = 0.34            # Hoffmann 2022, parameter scaling exponent
E_CANDIDATES = {
    "E0":         0.0,
    "E_chinch":   1.7,     # conventional English irreducible-entropy estimate
}


def load_hl() -> dict[str, dict]:
    data = json.loads(HL_METRICS.read_text(encoding="utf-8"))
    return {r["lang"]: r for r in data["results"]}


def load_mini() -> dict[tuple[str, str], dict]:
    data = json.loads(MINI_SUMMARY.read_text(encoding="utf-8"))
    return {(r["language"], r["regime"]): r for r in data["results"]}


def implied_delta_N(delta_L_nats: float, L_baseline_nats: float, E: float) -> float:
    denom = ALPHA_N * max(L_baseline_nats - E, 1e-6)
    return delta_L_nats * PHASE1_N / denom


def main() -> int:
    hl = load_hl()
    mini = load_mini()

    rows = []
    for lang in ("en", "ar", "tr"):
        if lang not in hl:
            print(f"[{lang}] missing from hl_metrics.json — skipping", file=sys.stderr)
            continue
        try:
            L_base = mini[(lang, "baseline")]["test_loss"]
            L_morph = mini[(lang, "morph")]["test_loss"]
        except KeyError:
            print(f"[{lang}] missing from mini_summary.json — skipping", file=sys.stderr)
            continue

        delta_L = L_base - L_morph
        rho = hl[lang]["rho_signature"]
        H = hl[lang]["H_bits"]
        rho_H = rho * H

        row = {
            "lang": lang,
            "L_baseline_nats": L_base,
            "L_morph_nats": L_morph,
            "delta_L_nats": delta_L,
            "rho": rho,
            "H_bits": H,
            "rho_times_H_bits": rho_H,
        }
        for e_name, e_val in E_CANDIDATES.items():
            d_N = implied_delta_N(delta_L, L_base, e_val)
            row[f"delta_N_{e_name}_params"] = d_N
            row[f"alpha_{e_name}_params_per_bit"] = d_N / rho_H if rho_H > 0 else float("nan")
        # Language-specific E that pins L_baseline - E = 1 nat (stress test)
        d_N_local = implied_delta_N(delta_L, L_base, L_base - 1.0)
        row["delta_N_Elocal_params"] = d_N_local
        row["alpha_Elocal_params_per_bit"] = d_N_local / rho_H if rho_H > 0 else float("nan")
        rows.append(row)

    # Summary stats on alpha dispersion
    for e_name in list(E_CANDIDATES.keys()) + ["Elocal"]:
        alphas = [r[f"alpha_{e_name}_params_per_bit"] for r in rows]
        if alphas:
            mn, mx = min(alphas), max(alphas)
            ratio = mx / mn if mn > 0 else float("nan")
            print(f"E = {e_name:>9}  alpha range: [{mn:>10.0f}, {mx:>10.0f}] params/bit   spread {ratio:>5.1f}x")

    print()
    print(
        f"{'Lang':>5} {'L_base':>7} {'L_morph':>7} {'dL':>7} "
        f"{'rho*H':>6} {'dN_E0':>10} {'dN_Echn':>10} {'aE0':>9} {'aEchn':>9}"
    )
    for r in rows:
        print(
            f"{r['lang']:>5} "
            f"{r['L_baseline_nats']:>7.3f} {r['L_morph_nats']:>7.3f} {r['delta_L_nats']:>7.4f} "
            f"{r['rho_times_H_bits']:>6.2f} "
            f"{r['delta_N_E0_params']:>10.0f} {r['delta_N_E_chinch_params']:>10.0f} "
            f"{r['alpha_E0_params_per_bit']:>9.0f} {r['alpha_E_chinch_params_per_bit']:>9.0f}"
        )

    # Per-E OLS fit (through origin) across languages: alpha minimises
    # sum_L (dN_L - alpha * rho_H_L)^2 => alpha = sum(dN*rhoH) / sum(rhoH^2)
    print()
    for e_name in list(E_CANDIDATES.keys()) + ["Elocal"]:
        num = sum(r[f"delta_N_{e_name}_params"] * r["rho_times_H_bits"] for r in rows)
        den = sum(r["rho_times_H_bits"] ** 2 for r in rows)
        a_ols = num / den if den > 0 else float("nan")
        resid = [
            r[f"delta_N_{e_name}_params"] - a_ols * r["rho_times_H_bits"]
            for r in rows
        ]
        rmse = math.sqrt(sum(x * x for x in resid) / len(resid)) if resid else float("nan")
        print(f"OLS alpha (E={e_name:>9}): {a_ols:>10.0f} params/bit   residual RMSE {rmse:>10.0f}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "phase1_N": PHASE1_N,
        "phase1_D": PHASE1_D,
        "alpha_N_scaling_exponent": ALPHA_N,
        "E_candidates": E_CANDIDATES,
        "rows": rows,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
