#!/bin/bash
cd /workspace/BA_01
BASE=morph_efficiency_project
LOG=/workspace/full_pipeline.log
WORKERS=32

echo "=== PARALLEL MORPH: ar + tr START: $(date) ===" | tee -a $LOG

echo "--- Morph preprocess: ar ---" | tee -a $LOG
python ${BASE}/scripts/preprocess_morph.py --language ar --base_dir ${BASE} --workers ${WORKERS} 2>&1 | tee -a $LOG

echo "--- Morph preprocess: tr ---" | tee -a $LOG
python ${BASE}/scripts/preprocess_morph.py --language tr --base_dir ${BASE} --workers ${WORKERS} 2>&1 | tee -a $LOG

echo "=== PARALLEL MORPH DONE: $(date) ===" | tee -a $LOG
