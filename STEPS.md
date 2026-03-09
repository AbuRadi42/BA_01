# Vast.ai Pipeline Execution Steps

## 0. SSH Key Setup (WSL, one-time)

```bash
ssh-keygen -t ed25519   # hit Enter for all prompts
cat ~/.ssh/id_ed25519.pub
```

Copy the output. In Vast.ai → Account → SSH Keys → paste it. No API key needed for SSH access.

---

## 1. Rent an Instance

- Go to Vast.ai → Search
- Filter: GPU = A100 80GB, Disk ≥ 100GB
- Template: PyTorch (pre-installed CUDA + PyTorch)
- Click Rent → wait ~1–2 min for it to start
- Copy the SSH command shown (looks like `ssh root@<ip> -p <port>`)

---

## 2. Upload the Project

Run this from WSL on your local machine:

```bash
rsync -avz --exclude '.git' --exclude '__pycache__' \
  /mnt/c/Users/Sameh\ AbuRadi/Desktop/BA_01/ \
  root@<instance-ip>:/workspace/BA_01/ \
  -e "ssh -p <port>"
```

Replace `<instance-ip>` and `<port>` with the values from Vast.ai.

---

## 3. Connect and Install Dependencies

```bash
ssh root@<instance-ip> -p <port>
cd /workspace/BA_01
pip install sentencepiece datasets matplotlib
```

---

## 4. Run the Pipeline

All commands from `/workspace/BA_01`. Use `nohup` so jobs survive SSH disconnects.

### ⚠️ Do This First — Dry Run (~5 min, costs ~$0.10)

Before committing to the full run, verify each stage works end-to-end with a tiny slice:

```bash
# Download 50k sentences per language (tests all 3 HuggingFace sources)
python morph_efficiency_project/scripts/download_data.py --language all --max-sentences 50000

# Verify output files exist and are non-empty
ls -lh morph_efficiency_project/data/raw/en/
ls -lh morph_efficiency_project/data/raw/ar/
ls -lh morph_efficiency_project/data/raw/tr/

# Baseline tokenization on the tiny slice
python morph_efficiency_project/scripts/preprocess_baseline.py --language all --max-sentences 50000

# Morph preprocessing on the tiny slice
python morph_efficiency_project/scripts/preprocess_morph.py --language all --max-sentences 50000

# Verify processed arrays exist
ls -lh morph_efficiency_project/data/processed/en/baseline/
ls -lh morph_efficiency_project/data/processed/en/morph/
```

If all files are present and non-empty, the pipeline is proven. Then wipe the dry-run data and start the real run:

```bash
rm -rf morph_efficiency_project/data/raw/*/
rm -rf morph_efficiency_project/data/processed/*/
rm -rf morph_efficiency_project/tokenizers/
```

---

### Stage 1 — Download corpora (~3–6 hrs)

```bash
nohup python morph_efficiency_project/scripts/download_data.py --language all \
  > logs/download.log 2>&1 &
tail -f logs/download.log   # monitor progress; Ctrl+C to stop tailing
```

### Stage 2 — Baseline preprocessing (~1–2 hrs)

```bash
nohup python morph_efficiency_project/scripts/preprocess_baseline.py --language all \
  > logs/preprocess_base.log 2>&1 &
tail -f logs/preprocess_base.log
```

### Stage 3 — Morph preprocessing (~4–8 hrs)

```bash
nohup python morph_efficiency_project/scripts/preprocess_morph.py --language all \
  > logs/preprocess_morph.log 2>&1 &
tail -f logs/preprocess_morph.log
```

### Stage 4 — Train all six models (~7–9 hrs each, ~42–54 hrs total)

Run sequentially on one instance, or split across two instances (3 models each) to halve wall time.

```bash
nohup python morph_efficiency_project/scripts/train_lm.py --language en --regime baseline > logs/train_en_base.log 2>&1 &
# wait for it to finish, then:
nohup python morph_efficiency_project/scripts/train_lm.py --language en --regime morph   > logs/train_en_morph.log 2>&1 &
nohup python morph_efficiency_project/scripts/train_lm.py --language ar --regime baseline > logs/train_ar_base.log 2>&1 &
nohup python morph_efficiency_project/scripts/train_lm.py --language ar --regime morph   > logs/train_ar_morph.log 2>&1 &
nohup python morph_efficiency_project/scripts/train_lm.py --language tr --regime baseline > logs/train_tr_base.log 2>&1 &
nohup python morph_efficiency_project/scripts/train_lm.py --language tr --regime morph   > logs/train_tr_morph.log 2>&1 &
```

If the instance gets preempted, reconnect and add `--resume` — training continues from the last checkpoint:

```bash
nohup python morph_efficiency_project/scripts/train_lm.py --language en --regime baseline --resume > logs/train_en_base.log 2>&1 &
```

### Stage 5 — Evaluate (~1–2 hrs)

```bash
nohup python morph_efficiency_project/scripts/eval_lm.py --language all --regime all \
  > logs/eval_lm.log 2>&1 &

nohup python morph_efficiency_project/scripts/eval_morphology.py --language all --regime all \
  > logs/eval_morph.log 2>&1 &

nohup python morph_efficiency_project/scripts/eval_downstream.py --language all --regime all \
  > logs/eval_downstream.log 2>&1 &
```

### Stage 6 — Aggregate results (~5 min)

```bash
python morph_efficiency_project/scripts/compute_metrics.py
```

Results land in `logs/summary/`:
- `summary_table.csv` — all metrics for all 6 models
- `conclusion.md` — auto-generated findings
- `learning_curves_{lang}.png` — one per language
- `tokens_per_unit.png`, `agreement_accuracy.png`, `flops_vs_accuracy.png`

---

## 5. Download Results Back to Local Machine

Run from WSL on your local machine:

```bash
rsync -avz \
  root@<instance-ip>:/workspace/BA_01/morph_efficiency_project/logs/ \
  /mnt/c/Users/Sameh\ AbuRadi/Desktop/BA_01/morph_efficiency_project/logs/ \
  -e "ssh -p <port>"

rsync -avz \
  root@<instance-ip>:/workspace/BA_01/morph_efficiency_project/models/ \
  /mnt/c/Users/Sameh\ AbuRadi/Desktop/BA_01/morph_efficiency_project/models/ \
  -e "ssh -p <port>"
```

---

## 6. View the Presentation

Open `morph_efficiency_project/presentation/index.html` in a browser. No server needed — it reads the JSON logs directly from the `logs/` folder.

---

## 7. Destroy the Instance

Once results are downloaded, go to Vast.ai → Instances → Destroy. You stop being charged immediately.

---

## Week Schedule

| Day | Task | Est. GPU time |
|-----|------|---------------|
| 1 | Setup + download corpora | 3–6 hrs |
| 2 | Baseline + morph preprocessing | 5–10 hrs |
| 2–5 | Train all 6 models (start overnight) | 42–54 hrs |
| 5–6 | Evaluation scripts | 1–2 hrs |
| 6 | Aggregate + check results | ~1 hr |
| 7 | Buffer / write-up | — |

With two parallel instances (3 models each), training wall time drops to ~21–27 hrs at the same total cost.
