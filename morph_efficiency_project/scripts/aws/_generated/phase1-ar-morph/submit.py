"""Generated submit script for job 'morph-phase1-ar-morph'.

Run from morph_efficiency_project/ with AWS credentials configured:
    python scripts/aws/_generated/phase1-ar-morph/submit.py
"""
import boto3
from sagemaker.pytorch import PyTorch

estimator = PyTorch(
    entry_point="train_model.py",
    source_dir="scripts",
    role="REPLACE_WITH_ROLE_ARN",
    instance_type="ml.g5.xlarge",
    instance_count=1,
    framework_version="2.3.0",
    py_version="py310",
    hyperparameters={"lang": "ar", "regime": "morph", "model-dim": 128, "layers": 4, "max-tokens": 5000000, "batch-size": 32, "seq-len": 128, "eval-every": 1000, "save-every": 5000, "log-every": 50, "output-dir": "/opt/ml/model"},
    output_path="s3://morph-efficiency-default/runs/phase1-ar-morph/",
    checkpoint_s3_uri="s3://morph-efficiency-default/checkpoints/phase1-ar-morph/",
    max_run=14400,
    base_job_name="morph-phase1-ar-morph",
    region="us-east-1",
)
estimator.fit({"training": "s3://morph-efficiency-default/data/ar_morph/"})
