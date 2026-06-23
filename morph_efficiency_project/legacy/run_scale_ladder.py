"""
run_scale_ladder.py — Orchestrate the 9-language × 2-regime × 4-rung Chinchilla
-ratio scale ladder described in MANUSCRIPT_PLAN.md §6.7 and manuscript/
framework_math.md §6.4.

Design goals
============
- **Resumable.** Each run has a durable state.json. On relaunch, completed
  runs are skipped, and stale "running" runs (heartbeat older than the
  configured threshold) are eligible for retry.
- **Atomic.** result.json is written to a .tmp file then renamed; state
  transitions are flushed before the training call.
- **Forensically logged.** Every run appends JSONL events (start, step,
  checkpoint, failure, complete) to its log, and the orchestrator writes a
  single append-only history log at manuscript/ladder_run_history.log.
- **Idempotent downstream.** aggregate_ladder.py (separate script) can be
  re-run at any time, producing ladder_metrics.json from whatever result
  JSONs exist.

Directory layout
================
    mini_experiment/results_ladder/
    |-- manifest.json                  # index of all 72 runs + summary
    |-- ladder_run_history.log         # append-only invocation log
    `-- <run_id>/                      # one directory per run
        |-- state.json
        |-- config.json
        |-- log.jsonl
        |-- checkpoint_latest.pt       # written by the training callback
        |-- result.json                # final metrics (atomic)
        `-- traceback.txt              # only if run failed

Run ID convention
=================
    <lang>_<regime>_rung<n>_<params>p_<tokens>t

Example: ``tr_morph_rung3_1000000p_20000000t``

Usage
=====
    python morph_efficiency_project/scripts/run_scale_ladder.py
    python morph_efficiency_project/scripts/run_scale_ladder.py --dry-run
    python morph_efficiency_project/scripts/run_scale_ladder.py --rungs 1 2
    python morph_efficiency_project/scripts/run_scale_ladder.py --langs en tr
    python morph_efficiency_project/scripts/run_scale_ladder.py --stale-minutes 45
    python morph_efficiency_project/scripts/run_scale_ladder.py --retry-failed

This script *orchestrates* — it delegates the actual training to
``mini_experiment.run_mini`` (or a future ``train_one_model`` entry point).
It is safe to run, inspect progress (via manifest.json), interrupt, and
resume.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LADDER_DIR = ROOT / "mini_experiment" / "results_ladder"
HISTORY_LOG = ROOT / "manuscript" / "ladder_run_history.log"
MANIFEST = LADDER_DIR / "manifest.json"

# Chinchilla-ratio ladder. Tokens = ~20 * params.
RUNGS = [
    {"n": 1, "params_target": 250_000,   "tokens":   5_000_000, "n_layer": 2, "n_embd": 64,  "n_head": 4, "ffn_dim": 256},
    {"n": 2, "params_target": 500_000,   "tokens":  10_000_000, "n_layer": 3, "n_embd": 96,  "n_head": 4, "ffn_dim": 384},
    {"n": 3, "params_target": 1_000_000, "tokens":  20_000_000, "n_layer": 4, "n_embd": 128, "n_head": 4, "ffn_dim": 512},
    {"n": 4, "params_target": 2_000_000, "tokens":  40_000_000, "n_layer": 4, "n_embd": 192, "n_head": 4, "ffn_dim": 768},
]

LANGS = ["en", "ar", "tr", "de", "es", "hu", "sw", "eu", "zh"]
REGIMES = ["baseline", "morph"]

STALE_MINUTES_DEFAULT = 30


@dataclass
class RunSpec:
    run_id: str
    lang: str
    regime: str
    rung: int
    params_target: int
    tokens: int
    n_layer: int
    n_embd: int
    n_head: int
    ffn_dim: int

    @property
    def dir(self) -> Path:
        return LADDER_DIR / self.run_id


def build_run_specs(
    langs: list[str] | None = None,
    rungs: list[int] | None = None,
    regimes: list[str] | None = None,
) -> list[RunSpec]:
    langs = langs or LANGS
    rungs = rungs or [r["n"] for r in RUNGS]
    regimes = regimes or REGIMES
    specs: list[RunSpec] = []
    for rung in RUNGS:
        if rung["n"] not in rungs:
            continue
        for lang in langs:
            for regime in regimes:
                run_id = f"{lang}_{regime}_rung{rung['n']}_{rung['params_target']}p_{rung['tokens']}t"
                specs.append(RunSpec(
                    run_id=run_id,
                    lang=lang,
                    regime=regime,
                    rung=rung["n"],
                    params_target=rung["params_target"],
                    tokens=rung["tokens"],
                    n_layer=rung["n_layer"],
                    n_embd=rung["n_embd"],
                    n_head=rung["n_head"],
                    ffn_dim=rung["ffn_dim"],
                ))
    return specs


# ---- State-file helpers -------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_log(path: Path, event: str, **fields) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {"event": event, "ts": now_iso(), **fields}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def load_state(spec: RunSpec) -> dict | None:
    p = spec.dir / "state.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def save_state(spec: RunSpec, status: str, **extra) -> None:
    data = {
        "run_id": spec.run_id,
        "status": status,
        "updated_at": now_iso(),
        **extra,
    }
    write_json_atomic(spec.dir / "state.json", data)


def is_stale_running(state: dict, stale_minutes: int) -> bool:
    if state.get("status") != "running":
        return False
    updated = state.get("updated_at")
    if not updated:
        return True
    try:
        t = datetime.fromisoformat(updated)
    except ValueError:
        return True
    age_minutes = (datetime.now(timezone.utc) - t).total_seconds() / 60.0
    return age_minutes > stale_minutes


# ---- Environment capture ------------------------------------------------

def capture_environment() -> dict:
    def _run(cmd: list[str]) -> str:
        try:
            out = subprocess.run(cmd, check=False, capture_output=True, text=True, cwd=str(ROOT))
            return (out.stdout or out.stderr or "").strip()
        except Exception:
            return ""
    return {
        "ts": now_iso(),
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "git_sha": _run(["git", "rev-parse", "HEAD"]),
        "git_branch": _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "git_dirty": bool(_run(["git", "status", "--porcelain"])),
    }


# ---- Manifest -----------------------------------------------------------

def rebuild_manifest(specs: list[RunSpec]) -> dict:
    entries = []
    status_counts: dict[str, int] = {}
    for spec in specs:
        state = load_state(spec) or {"status": "pending"}
        entries.append({
            "run_id": spec.run_id,
            "lang": spec.lang,
            "regime": spec.regime,
            "rung": spec.rung,
            "status": state.get("status", "pending"),
            "updated_at": state.get("updated_at"),
        })
        status_counts[state.get("status", "pending")] = status_counts.get(state.get("status", "pending"), 0) + 1
    manifest = {
        "updated_at": now_iso(),
        "total_runs": len(entries),
        "status_counts": status_counts,
        "runs": entries,
    }
    write_json_atomic(MANIFEST, manifest)
    return manifest


# ---- Training delegation ------------------------------------------------

def train_one(spec: RunSpec) -> dict:
    """Invoke the actual trainer. Returns the result dict to be persisted.

    Delegates to ``scripts.train_one.train_one_model``. Torch is imported
    lazily inside that module so the orchestrator's dry-run and manifest
    operations stay torch-free.
    """
    sys.path.insert(0, str(ROOT))
    from morph_efficiency_project.scripts.train_one import train_one_model  # type: ignore

    model_cfg = dict(
        n_layer=spec.n_layer,
        n_embd=spec.n_embd,
        n_head=spec.n_head,
        ffn_dim=spec.ffn_dim,
        seq_len=128,
        dropout=0.0,
    )
    train_cfg = dict(
        total_tokens=spec.tokens,
        batch_size=16,
        lr=3e-4,
        weight_decay=0.01,
        grad_clip=1.0,
        warmup_steps=200,
        log_every=100,
        checkpoint_every=500,
    )

    return train_one_model(
        lang=spec.lang,
        regime=spec.regime,
        model_cfg=model_cfg,
        train_cfg=train_cfg,
        out_dir=spec.dir,
        # orchestrator already writes its own log.jsonl entries via
        # state transitions; the inner logger writes training-step
        # detail to the same file.
        log_callback=None,
    )


# ---- Main loop ---------------------------------------------------------

def process_run(spec: RunSpec, stale_minutes: int, retry_failed: bool, dry_run: bool) -> str:
    state = load_state(spec)
    if state:
        status = state.get("status")
        if status == "completed":
            return "skip_completed"
        if status == "failed" and not retry_failed:
            return "skip_failed"
        if status == "running" and not is_stale_running(state, stale_minutes):
            return "skip_running_fresh"

    if dry_run:
        return "would_run"

    # Persist config + start state atomically before touching the trainer.
    write_json_atomic(spec.dir / "config.json", asdict(spec))
    save_state(spec, "running", started_at=now_iso(), env=capture_environment())
    append_log(spec.dir / "log.jsonl", "start", spec=asdict(spec))

    t0 = time.time()
    try:
        result = train_one(spec)
    except Exception as e:
        tb = traceback.format_exc()
        (spec.dir / "traceback.txt").write_text(tb, encoding="utf-8")
        append_log(spec.dir / "log.jsonl", "failure", error=str(e))
        save_state(spec, "failed", failed_at=now_iso(), error=str(e))
        return "failed"

    elapsed = round(time.time() - t0, 1)
    result = dict(result)
    result["run_id"] = spec.run_id
    result["elapsed_s"] = elapsed
    write_json_atomic(spec.dir / "result.json", result)
    append_log(spec.dir / "log.jsonl", "complete", elapsed_s=elapsed)
    save_state(spec, "completed", completed_at=now_iso(), elapsed_s=elapsed)
    return "completed"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--langs", nargs="+", choices=LANGS)
    ap.add_argument("--rungs", nargs="+", type=int, choices=[1, 2, 3, 4])
    ap.add_argument("--regimes", nargs="+", choices=REGIMES)
    ap.add_argument("--dry-run", action="store_true",
                    help="Plan only; don't invoke trainer.")
    ap.add_argument("--retry-failed", action="store_true",
                    help="Retry runs with status=failed.")
    ap.add_argument("--stale-minutes", type=int, default=STALE_MINUTES_DEFAULT,
                    help=f"Heartbeat age (min) beyond which a 'running' run is "
                         f"considered stale and eligible for retry "
                         f"(default {STALE_MINUTES_DEFAULT}).")
    args = ap.parse_args()

    LADDER_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_LOG.parent.mkdir(parents=True, exist_ok=True)

    specs = build_run_specs(args.langs, args.rungs, args.regimes)
    append_log(HISTORY_LOG, "invoke",
               argv=sys.argv, total_runs=len(specs),
               dry_run=args.dry_run, retry_failed=args.retry_failed,
               env=capture_environment())

    print(f"Planning {len(specs)} runs across "
          f"{len(set(s.lang for s in specs))} languages x "
          f"{len(set(s.regime for s in specs))} regimes x "
          f"{len(set(s.rung for s in specs))} rungs.",
          file=sys.stderr)

    counts: dict[str, int] = {}
    for spec in specs:
        outcome = process_run(spec, args.stale_minutes, args.retry_failed, args.dry_run)
        counts[outcome] = counts.get(outcome, 0) + 1
        print(f"  {spec.run_id:55s} {outcome}", file=sys.stderr)

    rebuild_manifest(specs)
    print(f"\nOutcomes: {counts}", file=sys.stderr)
    append_log(HISTORY_LOG, "finish", counts=counts)
    return 0 if not counts.get("failed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
