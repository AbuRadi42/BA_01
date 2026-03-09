#!/bin/bash
# Runs locally in WSL. Syncs results from the Vast.ai instance every hour.
# Self-terminates once the pipeline is fully done and all files are confirmed.

REMOTE="root@ssh3.vast.ai"
REMOTE_PORT=32214
SSH_KEY="$HOME/.ssh/vastai"
REMOTE_BASE="/workspace/BA_01/morph_efficiency_project"
LOCAL_BASE="/mnt/c/Users/Sameh AbuRadi/Desktop/BA_01/morph_efficiency_project"
LOG_REMOTE="/workspace/full_pipeline.log"
SYNC_LOG="/tmp/sync_progress.log"

SSH="ssh -i $SSH_KEY -p $REMOTE_PORT -o StrictHostKeyChecking=no"
SCP="scp -i $SSH_KEY -P $REMOTE_PORT -o StrictHostKeyChecking=no"

EXPECTED_FILES=(
    "data/processed/en/baseline/train_tokens.npy"
    "data/processed/ar/baseline/train_tokens.npy"
    "data/processed/tr/baseline/train_tokens.npy"
    "data/processed/en/morph/train_tokens.npy"
    "data/processed/ar/morph/train_tokens.npy"
    "data/processed/tr/morph/train_tokens.npy"
    "logs/summary/en_morph_summary.json"
    "logs/summary/ar_morph_summary.json"
    "logs/summary/tr_morph_summary.json"
)

sync_files() {
    echo "[$(date)] Syncing from instance..." | tee -a "$SYNC_LOG"

    # Sync logs
    rsync -az -e "$SSH -p $REMOTE_PORT" \
        "$REMOTE:$REMOTE_BASE/logs/" \
        "$LOCAL_BASE/logs/" 2>>"$SYNC_LOG"

    # Sync processed data
    rsync -az -e "$SSH -p $REMOTE_PORT" \
        "$REMOTE:$REMOTE_BASE/data/processed/" \
        "$LOCAL_BASE/data/processed/" 2>>"$SYNC_LOG"

    # Sync tokenizers
    rsync -az -e "$SSH -p $REMOTE_PORT" \
        "$REMOTE:$REMOTE_BASE/tokenizers/" \
        "$LOCAL_BASE/tokenizers/" 2>>"$SYNC_LOG"

    # Sync models (once they exist)
    rsync -az -e "$SSH -p $REMOTE_PORT" \
        "$REMOTE:$REMOTE_BASE/models/" \
        "$LOCAL_BASE/models/" 2>>"$SYNC_LOG"

    echo "[$(date)] Sync complete." | tee -a "$SYNC_LOG"
}

all_files_present() {
    for f in "${EXPECTED_FILES[@]}"; do
        if ! $SSH "$REMOTE" "test -f $REMOTE_BASE/$f" 2>/dev/null; then
            return 1
        fi
    done
    return 0
}

pipeline_done() {
    $SSH "$REMOTE" "grep -q 'PIPELINE DONE' $LOG_REMOTE" 2>/dev/null
}

echo "[$(date)] Sync loop started. Syncing every 60 minutes." | tee "$SYNC_LOG"
echo "Monitor sync progress: tail -f $SYNC_LOG"

while true; do
    sync_files

    if pipeline_done && all_files_present; then
        echo "[$(date)] Pipeline complete and all files confirmed. Running final sync..." | tee -a "$SYNC_LOG"
        sync_files
        # Also pull the full pipeline log
        $SCP "$REMOTE:$LOG_REMOTE" "$LOCAL_BASE/../full_pipeline.log" 2>>"$SYNC_LOG"
        echo "[$(date)] All done. Sync loop exiting." | tee -a "$SYNC_LOG"
        exit 0
    fi

    echo "[$(date)] Pipeline still running. Next sync in 60 minutes." | tee -a "$SYNC_LOG"
    sleep 3600
done
