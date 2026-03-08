#!/bin/bash
cd /workspace/BA_01
BASE=morph_efficiency_project
LOG=/workspace/full_pipeline.log

echo "=== FULL PIPELINE START: $(date) ===" | tee $LOG

echo "--- Step 1: Download ---" | tee -a $LOG
python ${BASE}/scripts/download_data.py --language all --base_dir ${BASE} 2>&1 | tee -a $LOG

echo "--- Step 2: Baseline preprocess ---" | tee -a $LOG
python ${BASE}/scripts/preprocess_baseline.py --language all --base_dir ${BASE} 2>&1 | tee -a $LOG

echo "--- Step 3: Morph preprocess ---" | tee -a $LOG
python ${BASE}/scripts/preprocess_morph.py --language all --base_dir ${BASE} 2>&1 | tee -a $LOG

echo "=== PIPELINE DONE: $(date) ===" | tee -a $LOG
