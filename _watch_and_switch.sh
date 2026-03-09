#!/bin/bash
# Watches full_pipeline.log for EN morph completion.
# When detected, kills the running pipeline and relaunches AR+TR
# using the parallel preprocess_morph.py.

LOG=/workspace/full_pipeline.log
BASE=morph_efficiency_project
WORKERS=32

echo "[watcher] Started. Waiting for EN morph to complete..."

while true; do
    # EN morph is done when we see the summary line for EN
    if grep -q "\[en\] Summary saved" "$LOG" 2>/dev/null; then
        echo "[watcher] EN morph done. Killing pipeline session..."
        tmux kill-session -t pipeline 2>/dev/null || true

        echo "[watcher] Launching AR+TR with $WORKERS parallel workers..."
        tmux new-session -d -s pipeline_parallel "bash /workspace/run_parallel.sh"
        echo "[watcher] Done. Monitor with: tail -f $LOG"
        exit 0
    fi
    sleep 60
done
