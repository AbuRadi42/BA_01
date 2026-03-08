#!/bin/bash
set -e
cd /workspace/BA_01

BASE=morph_efficiency_project

echo "=== DRY RUN: download 50k sentences per language ==="
python ${BASE}/scripts/download_data.py --language all --max-sentences 50000 --base_dir ${BASE}

echo "=== DRY RUN: baseline preprocessing ==="
python ${BASE}/scripts/preprocess_baseline.py --language all --max-sentences 50000 --base_dir ${BASE}

echo "=== DRY RUN: morph preprocessing ==="
python ${BASE}/scripts/preprocess_morph.py --language all --max-sentences 50000 --base_dir ${BASE}

echo "=== Verifying output files ==="
ls -lh ${BASE}/data/raw/en/
ls -lh ${BASE}/data/raw/ar/
ls -lh ${BASE}/data/raw/tr/
ls -lh ${BASE}/data/processed/en/baseline/
ls -lh ${BASE}/data/processed/en/morph/
ls -lh ${BASE}/data/processed/ar/baseline/
ls -lh ${BASE}/data/processed/ar/morph/
ls -lh ${BASE}/data/processed/tr/baseline/
ls -lh ${BASE}/data/processed/tr/morph/

echo "=== DRY RUN COMPLETE ==="
