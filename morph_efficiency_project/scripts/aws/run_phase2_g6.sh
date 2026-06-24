#!/usr/bin/env bash
# Phase-2 proof-of-concept sweep on a single GPU box (g6.xlarge / g6e.2xlarge).
# Trains all 8 cells: 4 languages (ZH, EN, TR, AR) x 2 regimes (baseline, morph)
# at parameter-matched ~30M-param Chinchilla-optimal scale, then aggregates the
# final eval losses (the morphology-rebate result).
#
#   bash morph_efficiency_project/scripts/aws/run_phase2_g6.sh             # full run
#   STAGE=train bash .../run_phase2_g6.sh                                   # skip data prep
#
# Idempotent: train_model.py --resume picks up from the latest checkpoint, and a
# cell whose final checkpoint already exists is skipped.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

# Python with torch/datasets. On the AWS Deep Learning AMI it lives in /opt/pytorch.
PY=${PY:-/opt/pytorch/bin/python3}
[ -x "$PY" ] || PY=python3

# ---- headline config (baseline and morph share the transformer => matched) ----
DIM=${DIM:-512}; LAYERS=${LAYERS:-10}; HEADS=${HEADS:-8}
SEQ=${SEQ:-128}; BATCH=${BATCH:-64}
TOKENS=${TOKENS:-600000000}        # ~20 tokens/param, Chinchilla-optimal for ~30M
OUT=${OUT:-runs/phase2}
LANGS=${LANGS:-"zh en tr ar"}
STAGE=${STAGE:-all}
# corpus size per language (sentences), mixed Wikipedia + FineWeb for variety
NTRAIN=${NTRAIN:-1500000}; NVAL=${NVAL:-30000}; NTEST=${NTEST:-30000}

"$PY" -c "import torch; assert torch.cuda.is_available(), 'no GPU'; print('[gpu]', torch.cuda.get_device_name(0))"

# ---- Stage 1: data (download full corpora + tokenise with the reformed engines)
# NOTE: download_corpora.py's per-language sentence count governs how many UNIQUE
# tokens exist. For a true ~600M-token Chinchilla run raise N_TRAIN there; with a
# smaller corpus the trainer simply repeats it (more epochs). This is a science
# knob, set it deliberately before a real publish run.
if [ "$STAGE" = "all" ] || [ "$STAGE" = "data" ]; then
    echo "=== [data] download (Wikipedia + FineWeb mix) + tokenise ==="
    "$PY" morph_efficiency_project/scripts/download_corpora.py --langs $LANGS \
        --n-train "$NTRAIN" --n-val "$NVAL" --n-test "$NTEST" --force-redownload
    "$PY" -X utf8 morph_efficiency_project/scripts/tokenize_for_training.py --full --force
fi

# ---- Stage 2: the 8-cell sweep ------------------------------------------------
if [ "$STAGE" = "all" ] || [ "$STAGE" = "train" ]; then
    for lang in $LANGS; do
        for regime in baseline morph; do
            cell="${lang}_${regime}"; dir="$OUT/$cell"
            if ls "$dir"/ckpt_step_*.pt >/dev/null 2>&1; then
                echo "=== [skip] $cell already has a checkpoint ==="; continue
            fi
            echo "=== [train] $cell  (dim=$DIM layers=$LAYERS heads=$HEADS tokens=$TOKENS) ==="
            "$PY" morph_efficiency_project/scripts/train_model.py \
                --lang "$lang" --regime "$regime" \
                --model-dim "$DIM" --layers "$LAYERS" --heads "$HEADS" \
                --max-tokens "$TOKENS" --batch-size "$BATCH" --seq-len "$SEQ" \
                --eval-every 2000 --save-every 10000 --log-every 50 --seed 0 \
                --output-dir "$dir"
        done
    done
fi

# ---- Stage 3: aggregate every paper-worthy number ----------------------------
# Emits, under $OUT/:
#   results.csv        one row per cell: params, tokens, loss, ppl, BPC, fertility, throughput
#   figures_data.json  structured for the headline plots (rebate bars, fertility bars)
# and prints the fair (bits-per-character) rebate table. Learning-curve data lives
# per-cell in metrics.jsonl (tokens_seen vs eval_bpc) for the line plots.
echo "=== [results] aggregating ==="
"$PY" - "$OUT" <<'PY'
import json, glob, os, sys
out = sys.argv[1]
DATA = os.path.join("mini_experiment", "data")
ORDER = {"zh": 0, "en": 1, "tr": 2, "ar": 3}   # canonical typological order

def tokstats(lang):
    p = os.path.join(DATA, f"{lang}_tokstats.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}

cells = {}
for d in sorted(glob.glob(os.path.join(out, "*_*"))):
    sp = os.path.join(d, "summary.json")
    if not os.path.exists(sp):
        continue
    s = json.load(open(sp, encoding="utf-8"))
    lang, regime = s["lang"], s["regime"]
    ts = tokstats(lang).get("fertility", {}).get("val", {})
    s["val_tok_per_word"] = ts.get(f"{regime}_tok_per_word")
    s["val_tok_per_char"] = ts.get(f"{regime}_tok_per_char")
    cells[(lang, regime)] = s

# results.csv
cols = ["lang", "regime", "n_params", "tokens_seen", "final_eval_loss",
        "final_eval_ppl", "final_eval_bpc", "val_tok_per_word",
        "val_tok_per_char", "tokens_per_sec", "elapsed_s"]
csv_path = os.path.join(out, "results.csv")
with open(csv_path, "w", encoding="utf-8") as fh:
    fh.write(",".join(cols) + "\n")
    for k in sorted(cells, key=lambda k: (ORDER.get(k[0], 9), k[1])):
        s = cells[k]
        fh.write(",".join(str(s.get(c, "")) for c in cols) + "\n")
print(f"[results] wrote {csv_path}")

# headline: per-language baseline vs morph, in the FAIR bits-per-char metric
print(f"\n{'lang':5} {'base_bpc':>9} {'morph_bpc':>10} {'Δbpc':>8} "
      f"{'base_ppl':>9} {'morph_ppl':>10} {'base_t/w':>9} {'morph_t/w':>10}")
fig = {"rebate_bpc": [], "fertility_tok_per_word": [], "perplexity": []}
for lang in sorted({k[0] for k in cells}, key=lambda l: ORDER.get(l, 9)):
    b, m = cells.get((lang, "baseline")), cells.get((lang, "morph"))
    if not (b and m):
        continue
    bb, mb = b.get("final_eval_bpc"), m.get("final_eval_bpc")
    d = (bb - mb) if (bb and mb) else None
    print(f"{lang:5} {bb if bb else float('nan'):9.4f} "
          f"{mb if mb else float('nan'):10.4f} {d if d else float('nan'):8.4f} "
          f"{b['final_eval_ppl']:9.2f} {m['final_eval_ppl']:10.2f} "
          f"{(b.get('val_tok_per_word') or 0):9.3f} "
          f"{(m.get('val_tok_per_word') or 0):10.3f}")
    fig["rebate_bpc"].append({"lang": lang, "baseline": bb, "morph": mb})
    fig["fertility_tok_per_word"].append({"lang": lang,
        "baseline": b.get("val_tok_per_word"), "morph": m.get("val_tok_per_word")})
    fig["perplexity"].append({"lang": lang,
        "baseline": b["final_eval_ppl"], "morph": m["final_eval_ppl"]})
json.dump(fig, open(os.path.join(out, "figures_data.json"), "w"), indent=2)
print(f"\n[results] figure data -> {os.path.join(out, 'figures_data.json')}")
PY
echo "=== [done] results.csv + figures_data.json + per-cell metrics.jsonl under $OUT/ ==="
