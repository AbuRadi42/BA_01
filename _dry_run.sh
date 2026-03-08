#!/bin/bash
set -e
cd /workspace/BA_01

echo "=== DRY RUN: download 50k sentences per language ==="
python morph_efficiency_project/scripts/download_data.py --language all --max-sentences 50000

echo "=== DRY RUN: baseline preprocessing ==="
python morph_efficiency_project/scripts/preprocess_baseline.py --language all --max-sentences 50000

echo "=== DRY RUN: morph preprocessing ==="
python morph_efficiency_project/scripts/preprocess_morph.py --language all --max-sentences 50000

echo "=== Verifying output files ==="
ls -lh morph_efficiency_project/data/raw/en/
ls -lh morph_efficiency_project/data/raw/ar/
ls -lh morph_efficiency_project/data/raw/tr/
ls -lh morph_efficiency_project/data/processed/en/baseline/
ls -lh morph_efficiency_project/data/processed/en/morph/
ls -lh morph_efficiency_project/data/processed/ar/baseline/
ls -lh morph_efficiency_project/data/processed/ar/morph/
ls -lh morph_efficiency_project/data/processed/tr/baseline/
ls -lh morph_efficiency_project/data/processed/tr/morph/

echo "=== DRY RUN COMPLETE ==="
