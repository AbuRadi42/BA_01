# AWS deployment

End-to-end guide for shipping a `(language, regime)` training run to
SageMaker. The trainer (`scripts/train_model.py`) and the launcher
(`scripts/aws/launch_run.py`) are the two moving parts; this doc covers
the cloud plumbing around them.

## 1. AWS account setup

You need:

1. An AWS account with billing active.
2. An IAM role that SageMaker can assume (call it
   `MorphEfficiencyTrainingRole`). Attach:
   - `AmazonSageMakerFullAccess`
   - A custom S3 policy granting `Get/Put/ListBucket` on the bucket from
     step 2.
   - `AmazonEC2ContainerRegistryReadOnly` (so SageMaker can pull the
     PyTorch image).
3. An IAM user (or SSO session) on your laptop with permission to call
   `sagemaker:CreateTrainingJob`, `iam:PassRole` on the role above, and
   `s3:*` on the bucket below.

Export the role ARN locally:
```bash
export MORPH_SM_ROLE_ARN=arn:aws:iam::<account-id>:role/MorphEfficiencyTrainingRole
export AWS_REGION=us-east-1
```

## 2. S3 buckets

One bucket is enough; the launcher partitions inside it.

```bash
aws s3 mb s3://morph-efficiency-<your-suffix> --region us-east-1
export MORPH_S3_BUCKET=morph-efficiency-<your-suffix>
```

Layout the launcher writes to:
```
s3://$MORPH_S3_BUCKET/
  source/<tag>/source.tar.gz       # packaged scripts/ dir
  data/<lang>_<regime>/            # tokenised .npy + vocab .json
  runs/<tag>/                      # SageMaker output (model.tar.gz)
  checkpoints/<tag>/               # streaming checkpoints
```

Upload the data once per `(lang, regime)`:
```bash
aws s3 sync mini_experiment/data/   s3://$MORPH_S3_BUCKET/data/raw/
aws s3 sync mini_experiment/tokenizers/ s3://$MORPH_S3_BUCKET/data/tokenizers/
```

## 3. Local test before cloud

Always smoke-test on your laptop first. The trainer is CPU-friendly at
tiny scale:

```bash
python morph_efficiency_project/scripts/train_model.py \
    --lang en --regime baseline --model-dim 64 --layers 2 \
    --max-tokens 50000 --batch-size 4 --seq-len 32 \
    --eval-every 100 --save-every 500 \
    --output-dir /tmp/smoke_en_baseline
```

Expect: training loss drops from ~10.4 to ~7.0 over ~400 steps in under
a minute, a `ckpt_step_*.pt` lands in the output dir, and
`metrics.jsonl` has one record per eval.

## 4. One-command deploy

Dry-run first (writes artefacts, prints cost + IAM, no AWS calls):

```bash
python morph_efficiency_project/scripts/aws/launch_run.py \
    --lang ar --regime morph --model-dim 128 \
    --instance ml.g5.xlarge --max-tokens 5_000_000 \
    --tag phase1-ar-morph
```

Real deploy (requires `pip install sagemaker boto3` and credentials):

```bash
python morph_efficiency_project/scripts/aws/launch_run.py \
    --deploy --lang ar --regime morph --model-dim 128 \
    --instance ml.g5.xlarge --max-tokens 5_000_000 \
    --tag phase1-ar-morph
```

The 4 languages x 2 regimes matrix in canonical order (ZH, EN, TR, AR):

| lang | baseline               | morph                  |
|------|------------------------|------------------------|
| zh   | `phase1-zh-baseline`   | `phase1-zh-morph`      |
| en   | `phase1-en-baseline`   | `phase1-en-morph`      |
| tr   | `phase1-tr-baseline`   | `phase1-tr-morph`      |
| ar   | `phase1-ar-baseline`   | `phase1-ar-morph`      |

## 5. Cost estimate

Pricing assumes `ml.g5.xlarge` on-demand (us-east-1, 2026 Q2,
~$1.408/h). Numbers come from the launcher's heuristics and should be
trued up after the first real run.

| run scale                            | hours | $/run     |
|--------------------------------------|-------|-----------|
| Phase 1: 5M tokens, 128-dim, 4 layer | 2-4   | $3 - $6   |
| Phase 2: 30M tokens, headline rung   | ~15   | ~$21      |
| Full 8-cell sweep (Phase 1)          | -     | $24 - $48 |

For the 30M-parameter Chinchilla-optimal headline rung (~600M training
tokens at 20 tokens/param), on a single `ml.g5.xlarge` expect roughly
300 GPU-hours, ~$420 per run. Moving to `ml.g5.12xlarge` (4xA10G,
~$7.09/h) cuts wall-clock to ~90h for ~$640 per run. Across 8 cells
(4 langs x 2 regimes) the headline sweep is therefore in the
$3.5k-$5k range.

## 6. Monitoring + retrieval

- Logs stream to CloudWatch under
  `/aws/sagemaker/TrainingJobs/<job-name>`.
- Checkpoints land in `s3://$MORPH_S3_BUCKET/checkpoints/<tag>/`.
- Final model.tar.gz lands in `s3://$MORPH_S3_BUCKET/runs/<tag>/`.

Pull a finished run back:

```bash
aws s3 sync s3://$MORPH_S3_BUCKET/runs/phase1-ar-morph/ \
    morph_efficiency_project/runs/phase1-ar-morph/
```

## 7. Troubleshooting

- `boto3` / `sagemaker` import error: the launcher's `--deploy` branch
  needs both. `pip install sagemaker boto3`.
- "Role cannot be assumed": confirm the role's trust policy lists
  `sagemaker.amazonaws.com` as a trusted principal.
- ResourceLimitExceeded for `ml.g5.xlarge`: request a quota raise in
  Service Quotas before deploying.

