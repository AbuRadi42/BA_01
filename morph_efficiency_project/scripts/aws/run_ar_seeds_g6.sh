#!/usr/bin/env bash
# Phase-2 Arabic seed replication and shuffled control on a single GPU box.
# Trains 12 cells: seeds 1-4 x {baseline, morph, shuf}, with the exact
# configuration recorded in results/phase2_seeds/*/run_config.json, then writes
# results.csv. Run run_phase2_g6.sh STAGE=data first so the Arabic streams exist.
#
#   bash morph_efficiency_project/scripts/aws/run_ar_seeds_g6.sh
#
# shuf = the morph model with its root and wazn streams randomly permuted per
# seed (train_model.py --shuffle-streams root,wazn): same parameters, no real
# templatic structure. Idempotent: a cell with a summary.json is skipped.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PY=${PY:-/opt/pytorch/bin/python3}
[ -x "$PY" ] || PY=python3

DIM=512; LAYERS=10; HEADS=8; SEQ=128; BATCH=64; TOKENS=640000000
OUT=${OUT:-runs/phase2_seeds}
SEEDS=${SEEDS:-"1 2 3 4"}

"$PY" -c "import torch; assert torch.cuda.is_available(), 'no GPU'; print('[gpu]', torch.cuda.get_device_name(0))"

for seed in $SEEDS; do
    for cell in baseline morph shuf; do
        dir="$OUT/ar_${cell}_s${seed}"
        if [ -f "$dir/summary.json" ]; then
            echo "=== [skip] $dir already finished ==="; continue
        fi
        regime=$cell; extra=()
        if [ "$cell" = "shuf" ]; then regime=morph; extra=(--shuffle-streams root,wazn); fi
        echo "=== [train] ar_${cell}_s${seed} ==="
        "$PY" morph_efficiency_project/scripts/train_model.py \
            --lang ar --regime "$regime" "${extra[@]}" \
            --model-dim "$DIM" --layers "$LAYERS" --heads "$HEADS" \
            --max-tokens "$TOKENS" --batch-size "$BATCH" --seq-len "$SEQ" \
            --eval-every 2000 --save-every 10000 --log-every 200 --seed "$seed" \
            --output-dir "$dir"
    done
done

echo "=== [results] aggregating ==="
"$PY" - "$OUT" <<'PY'
import csv, glob, json, os, sys
out = sys.argv[1]
cols = ["cell", "lang", "regime", "seed", "n_params", "tokens_seen",
        "final_eval_loss", "final_eval_ppl", "final_eval_bpc"]
rows = []
for d in sorted(glob.glob(os.path.join(out, "ar_*_s*"))):
    sp = os.path.join(d, "summary.json")
    if os.path.exists(sp):
        s = json.load(open(sp, encoding="utf-8"))
        s["cell"] = os.path.basename(d)
        s["seed"] = s["cell"].rsplit("_s", 1)[1]
        rows.append(s)
with open(os.path.join(out, "results.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
print(f"[results] {len(rows)} cells -> {os.path.join(out, 'results.csv')}")
PY
