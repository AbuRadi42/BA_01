"""
launch_run.py
=============
Emit the SageMaker deployment artefacts for one (language, regime) training
run. With ``--deploy`` plus valid AWS credentials, actually submit the job.

Without ``--deploy``: writes (1) a SageMaker estimator config JSON, (2) a
``requirements.txt`` for the training image, (3) a ``submit.py`` snippet the
user can run by hand, and prints the cost estimate, S3 paths, and IAM
requirements. With ``--deploy``: imports boto3 + sagemaker and submits the
estimator; degrades gracefully if either is missing.

Pricing baseline: ml.g5.xlarge on-demand ~ $1.40/hour (us-east-1, 2026 Q2).
We assume ~2-4 hours per phase-1 run (model_dim=128, layers=4, 5M tokens).

CLI examples:
    python launch_run.py --lang ar --regime morph --model-dim 128 \\
        --instance ml.g5.xlarge --max-tokens 5_000_000 --tag phase1-ar-morph
    python launch_run.py --deploy --lang ar --regime morph \\
        --model-dim 128 --instance ml.g5.xlarge --max-tokens 5_000_000 \\
        --tag phase1-ar-morph
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parents[3]
_ARTEFACTS_ROOT = _THIS.parent / "_generated"

# Approximate on-demand US pricing per instance, $/hour. Update as needed.
_PRICING = {
    "ml.g5.xlarge": 1.408,
    "ml.g5.2xlarge": 1.515,
    "ml.g5.4xlarge": 2.03,
    "ml.g5.12xlarge": 7.09,
    "ml.p4d.24xlarge": 37.69,
    "ml.g4dn.xlarge": 0.736,
}

# Coarse hour estimates per 1M training tokens, by instance. Phase 1 figures
# come from local CPU smoke calibration scaled to single-GPU throughput.
_HOURS_PER_MTOKEN = {
    "ml.g5.xlarge": 0.5,
    "ml.g5.2xlarge": 0.45,
    "ml.g5.4xlarge": 0.4,
    "ml.g5.12xlarge": 0.15,
    "ml.p4d.24xlarge": 0.05,
    "ml.g4dn.xlarge": 0.9,
}


def _parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    p.add_argument("--lang", required=True, choices=("zh", "en", "tr", "ar"))
    p.add_argument("--regime", required=True, choices=("baseline", "morph"))
    p.add_argument("--model-dim", type=int, default=128)
    p.add_argument("--layers", type=int, default=4)
    p.add_argument("--max-tokens",
                   type=lambda s: int(float(s.replace("_", ""))),
                   default=5_000_000)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--seq-len", type=int, default=128)
    p.add_argument("--instance", default="ml.g5.xlarge")
    p.add_argument("--tag", required=True,
                   help="Short identifier, used in S3 paths and job name.")
    p.add_argument("--bucket", default=None,
                   help="S3 bucket. Default $MORPH_S3_BUCKET or "
                        "'morph-efficiency-<account>'.")
    p.add_argument("--region", default=os.environ.get("AWS_REGION",
                                                       "us-east-1"))
    p.add_argument("--role-arn", default=os.environ.get("MORPH_SM_ROLE_ARN"),
                   help="SageMaker execution role ARN. Required for --deploy.")
    p.add_argument("--py-version", default="py310")
    p.add_argument("--framework-version", default="2.3.0",
                   help="PyTorch framework version for the SageMaker image.")
    p.add_argument("--max-run-seconds", type=int, default=4 * 3600)
    p.add_argument("--deploy", action="store_true",
                   help="Actually submit the SageMaker training job.")
    p.add_argument("--output-dir", type=Path, default=None,
                   help="Where to write the generated artefacts. Default "
                        "scripts/aws/_generated/<tag>/.")
    return p.parse_args(argv)


def _cost_estimate(instance: str, max_tokens: int) -> dict:
    price = _PRICING.get(instance)
    hours_per_m = _HOURS_PER_MTOKEN.get(instance)
    if price is None or hours_per_m is None:
        return {"instance": instance, "known": False}
    hours = (max_tokens / 1_000_000) * hours_per_m
    return {
        "instance": instance,
        "known": True,
        "on_demand_usd_per_hour": price,
        "estimated_hours": round(hours, 2),
        "estimated_usd_low": round(hours * price * 0.8, 2),
        "estimated_usd_high": round(hours * price * 1.5, 2),
    }


def _hyperparams(args) -> dict:
    return {
        "lang": args.lang,
        "regime": args.regime,
        "model-dim": args.model_dim,
        "layers": args.layers,
        "max-tokens": args.max_tokens,
        "batch-size": args.batch_size,
        "seq-len": args.seq_len,
        "eval-every": 1000,
        "save-every": 5000,
        "log-every": 50,
        "output-dir": "/opt/ml/model",
    }


def _build_config(args) -> dict:
    bucket = args.bucket or os.environ.get("MORPH_S3_BUCKET",
                                            "morph-efficiency-default")
    job_name = f"morph-{args.tag}".replace("_", "-")[:63]
    cost = _cost_estimate(args.instance, args.max_tokens)
    # Safety: the SageMaker MaxRuntime must cover the actual run. The old 4h
    # default would kill any real (multi-hour) training job mid-flight. Auto-raise
    # it to the estimated runtime + 50% margin, capped at SageMaker's 28-day limit.
    _SM_MAX = 28 * 24 * 3600
    max_run = args.max_run_seconds
    auto_raised = False
    if cost.get("known"):
        needed = int(cost["estimated_hours"] * 3600 * 1.5)
        if needed > max_run:
            max_run = min(needed, _SM_MAX)
            auto_raised = True
    return {
        "job_name": job_name,
        "tag": args.tag,
        "lang": args.lang,
        "regime": args.regime,
        "region": args.region,
        "instance_type": args.instance,
        "instance_count": 1,
        "framework": "pytorch",
        "framework_version": args.framework_version,
        "py_version": args.py_version,
        "role_arn": args.role_arn,
        "entry_point": "train_model.py",
        "source_dir_s3": f"s3://{bucket}/source/{args.tag}/source.tar.gz",
        "input_data_s3": f"s3://{bucket}/data/{args.lang}_{args.regime}/",
        "output_s3": f"s3://{bucket}/runs/{args.tag}/",
        "checkpoint_s3": f"s3://{bucket}/checkpoints/{args.tag}/",
        "max_run_seconds": max_run,
        "max_run_seconds_requested": args.max_run_seconds,
        "max_run_seconds_auto_raised": auto_raised,
        "hyperparameters": _hyperparams(args),
        "cost_estimate": cost,
        "iam_requirements": [
            "sagemaker:CreateTrainingJob",
            "sagemaker:DescribeTrainingJob",
            "s3:GetObject", "s3:PutObject", "s3:ListBucket",
            "logs:CreateLogStream", "logs:PutLogEvents",
            "ecr:GetAuthorizationToken",
        ],
    }


def _write_artefacts(cfg: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "estimator_config.json", "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)
    with open(out_dir / "requirements.txt", "w", encoding="utf-8") as fh:
        fh.write("numpy>=1.24\ntorch>=2.1\n")
    submit = f"""\
\"\"\"Generated submit script for job '{cfg['job_name']}'.

Run from morph_efficiency_project/ with AWS credentials configured:
    python scripts/aws/_generated/{cfg['tag']}/submit.py
\"\"\"
import boto3
from sagemaker.pytorch import PyTorch

estimator = PyTorch(
    entry_point="{cfg['entry_point']}",
    source_dir="scripts",
    role="{cfg['role_arn'] or 'REPLACE_WITH_ROLE_ARN'}",
    instance_type="{cfg['instance_type']}",
    instance_count={cfg['instance_count']},
    framework_version="{cfg['framework_version']}",
    py_version="{cfg['py_version']}",
    hyperparameters={json.dumps(cfg['hyperparameters'])},
    output_path="{cfg['output_s3']}",
    checkpoint_s3_uri="{cfg['checkpoint_s3']}",
    max_run={cfg['max_run_seconds']},
    base_job_name="{cfg['job_name']}",
    region="{cfg['region']}",
)
estimator.fit({{"training": "{cfg['input_data_s3']}"}})
"""
    with open(out_dir / "submit.py", "w", encoding="utf-8") as fh:
        fh.write(submit)


def _try_deploy(cfg: dict) -> int:
    if not cfg.get("role_arn"):
        print("[deploy] ERROR: no role ARN. Set --role-arn or "
              "$MORPH_SM_ROLE_ARN.", file=sys.stderr)
        return 2
    try:
        import sagemaker  # noqa: F401
        from sagemaker.pytorch import PyTorch
    except ImportError as e:
        print(f"[deploy] sagemaker SDK not installed ({e}). "
              "pip install sagemaker boto3", file=sys.stderr)
        return 3
    print(f"[deploy] submitting job={cfg['job_name']} "
          f"instance={cfg['instance_type']}", flush=True)
    est = PyTorch(
        entry_point=cfg["entry_point"],
        source_dir=str(_REPO_ROOT / "morph_efficiency_project" / "scripts"),
        role=cfg["role_arn"],
        instance_type=cfg["instance_type"],
        instance_count=cfg["instance_count"],
        framework_version=cfg["framework_version"],
        py_version=cfg["py_version"],
        hyperparameters=cfg["hyperparameters"],
        output_path=cfg["output_s3"],
        checkpoint_s3_uri=cfg["checkpoint_s3"],
        max_run=cfg["max_run_seconds"],
        base_job_name=cfg["job_name"],
    )
    est.fit({"training": cfg["input_data_s3"]}, wait=False)
    print(f"[deploy] submitted: {est.latest_training_job.job_name}",
          flush=True)
    return 0


def main(argv=None) -> int:
    args = _parse_args(argv)
    cfg = _build_config(args)
    out_dir = args.output_dir or (_ARTEFACTS_ROOT / args.tag)
    _write_artefacts(cfg, out_dir)

    print(f"[launch] wrote artefacts to {out_dir}")
    print(f"[launch] job_name      = {cfg['job_name']}")
    print(f"[launch] instance      = {cfg['instance_type']}")
    print(f"[launch] source S3     = {cfg['source_dir_s3']}")
    print(f"[launch] input  S3     = {cfg['input_data_s3']}")
    print(f"[launch] output S3     = {cfg['output_s3']}")
    print(f"[launch] checkpoint S3 = {cfg['checkpoint_s3']}")
    ce = cfg["cost_estimate"]
    if ce.get("known"):
        print(f"[cost] est. {ce['estimated_hours']:.2f}h * "
              f"${ce['on_demand_usd_per_hour']:.3f}/h "
              f"= ~${ce['estimated_usd_low']:.2f}-"
              f"${ce['estimated_usd_high']:.2f}")
    else:
        print(f"[cost] unknown pricing for instance {ce['instance']}")
    mr = cfg["max_run_seconds"]
    note = " (auto-raised to cover the estimate)" if cfg.get("max_run_seconds_auto_raised") else ""
    print(f"[runtime] max_run_seconds = {mr} ({mr/3600:.1f}h){note}")
    if not ce.get("known"):
        print("[runtime] WARNING: unknown instance runtime — verify max_run_seconds "
              "exceeds the real training time before --deploy (the 4h default kills long runs).")
    print("[iam] required actions:")
    for a in cfg["iam_requirements"]:
        print(f"        {a}")

    if args.deploy:
        return _try_deploy(cfg)
    print("[launch] dry-run (no --deploy). Inspect "
          f"{out_dir}/submit.py to run by hand.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
