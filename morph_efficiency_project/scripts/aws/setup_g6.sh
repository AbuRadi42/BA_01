#!/usr/bin/env bash
# One-time environment setup on a g6.xlarge (NVIDIA L4, 24GB) or g6e.2xlarge
# (NVIDIA L40S, 48GB). Run from the repo root after `git clone`.
#
#   bash morph_efficiency_project/scripts/aws/setup_g6.sh
#
# Idempotent: safe to re-run.
set -euo pipefail

echo "[setup] python : $(python3 --version 2>&1)"

# CUDA-enabled PyTorch. On the AWS Deep Learning AMI torch is preinstalled; on a
# plain image install the CUDA 12.1 build (matches L4 / L40S).
if python3 -c "import torch; assert torch.cuda.is_available()" 2>/dev/null; then
    echo "[setup] torch+CUDA already present"
else
    echo "[setup] installing CUDA torch ..."
    pip install -q torch --index-url https://download.pytorch.org/whl/cu121
fi

# Training needs torch + numpy; full-corpus data prep needs datasets.
pip install -q numpy datasets

echo "[setup] GPU   : $(python3 -c 'import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NO GPU DETECTED")')"
python3 -c "import torch,numpy; print('[setup] torch', torch.__version__, '| numpy', numpy.__version__)"
echo "[setup] OK. Next: bash morph_efficiency_project/scripts/aws/run_phase2_g6.sh"
