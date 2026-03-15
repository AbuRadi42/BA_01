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

Run this from WSL on your local machine (replace `<host>` and `<port>` with values from Vast.ai):

```bash
rsync -avz --exclude '.git' --exclude '__pycache__' \
  /mnt/c/Users/Sameh\ AbuRadi/Desktop/BA_01/ \
  root@<host>:/workspace/BA_01/ \
  -e "ssh -i ~/.ssh/vastai -p <port>"
```

---

## 3. Connect and Install Dependencies

```bash
wsl ssh -i ~/.ssh/vastai root@<host> -p <port>
cd /workspace/BA_01
pip install sentencepiece datasets matplotlib
```

---

## 4. Run the Pipeline

All commands from `/workspace/BA_01`. Use tmux so jobs survive SSH disconnects.

### ⚠️ Do This First — Dry Run (~5 min, costs ~$0.10)

Before committing to the full run, verify each stage works end-to-end with a tiny slice:

```bash
python morph_efficiency_project/scripts/download_data.py --language all --base_dir morph_efficiency_project --max-sentences 50000
python morph_efficiency_project/scripts/preprocess_baseline.py --language all --base_dir morph_efficiency_project --max-sentences 50000
python morph_efficiency_project/scripts/preprocess_morph.py --language all --base_dir morph_efficiency_project --max-sentences 50000 --workers 4

ls -lh morph_efficiency_project/data/processed/en/baseline/
ls -lh morph_efficiency_project/data/processed/en/morph/
```

If all files are present and non-empty, wipe and start the real run:

```bash
rm -rf morph_efficiency_project/data/raw/*/
rm -rf morph_efficiency_project/data/processed/*/
rm -rf morph_efficiency_project/tokenizers/
```

---

### Stage 1 — Download corpora

All three languages target 2.5B whitespace tokens each. Download stops automatically the moment the target is reached.

- EN: hits target from Wikipedia alone (~77M sentences, ~3–4 hrs)
- AR: requires Wikipedia + CC-100 + OPUS-100 + mC4 + MADLAD-400 to reach target (~5–8 hrs)
- TR: same expanded sources (~5–8 hrs)

```bash
python morph_efficiency_project/scripts/download_data.py --language all --base_dir morph_efficiency_project 2>&1 | tee logs/download.log
```

### Stage 2 — Baseline preprocessing (~2–4 hrs total)

Trains a SentencePiece BPE tokenizer (32k vocab) per language and encodes all splits into `.npy` token arrays.

```bash
python morph_efficiency_project/scripts/preprocess_baseline.py --language all --base_dir morph_efficiency_project 2>&1 | tee logs/preprocess_base.log
```

### Stage 3 — Morph preprocessing

All three languages use 32 parallel workers and target 2.5B tokens each — equal budget across all three for a fair comparison. The script is fully resumable — each worker's chunk is saved to disk immediately, so a crash only loses in-flight chunks, not completed ones.

Expected time: ~6–12 hrs per language depending on morphological complexity (TR > AR > EN). All three are run with identical settings.

```bash
# EN (~6–10 hrs, 32 workers)
python morph_efficiency_project/scripts/preprocess_morph.py --language en --base_dir morph_efficiency_project --workers 32 2>&1 | tee logs/preprocess_morph_en.log

# AR (~8–12 hrs, 32 workers)
python morph_efficiency_project/scripts/preprocess_morph.py --language ar --base_dir morph_efficiency_project --workers 32 2>&1 | tee logs/preprocess_morph_ar.log

# TR (~8–12 hrs, 32 workers)
python morph_efficiency_project/scripts/preprocess_morph.py --language tr --base_dir morph_efficiency_project --workers 32 2>&1 | tee logs/preprocess_morph_tr.log
```

Note: earlier versions of this document showed EN as single-threaded (~48 hrs) and AR/TR as a fast parallel pair (~1 hr combined). Those estimates were based on the original unequal token budgets (EN 2.5B, AR 350M, TR 162M). After the source expansion fix (see incident log), all three languages now target 2.5B tokens and run with 32 workers — the estimates above reflect the corrected setup.

To check progress (counts completed chunks out of 33 total per language):

```bash
ls morph_efficiency_project/data/processed/en/morph_chunks_train/*.npz 2>/dev/null | wc -l
ls morph_efficiency_project/data/processed/ar/morph_chunks_train/*.npz 2>/dev/null | wc -l
ls morph_efficiency_project/data/processed/tr/morph_chunks_train/*.npz 2>/dev/null | wc -l
```

### Stage 4 — Train all six models (~8–12 hrs each, ~3–4 days total)

```bash
python morph_efficiency_project/scripts/train_lm.py --language en --regime baseline
python morph_efficiency_project/scripts/train_lm.py --language en --regime morph
python morph_efficiency_project/scripts/train_lm.py --language ar --regime baseline
python morph_efficiency_project/scripts/train_lm.py --language ar --regime morph
python morph_efficiency_project/scripts/train_lm.py --language tr --regime baseline
python morph_efficiency_project/scripts/train_lm.py --language tr --regime morph
```

Add `--resume` to continue from last checkpoint if the instance is interrupted.

### Stage 5 — Evaluate (~1–2 hrs)

```bash
python morph_efficiency_project/scripts/eval_lm.py --language all --regime all
python morph_efficiency_project/scripts/eval_morphology.py --language all --regime all
python morph_efficiency_project/scripts/eval_downstream.py --language all --regime all
```

### Stage 6 — Aggregate results

```bash
python morph_efficiency_project/scripts/compute_metrics.py
```

Results land in `logs/summary/`.

---

## 5. Monitor and Sync

Two scripts run locally in WSL tmux and handle this automatically. Both now take `<host>` and `<port>` as arguments — no need to edit the files:

- `_sync_from_instance.sh` — rsyncs logs, processed data, tokenizers, and models every 30 minutes. Self-terminates when pipeline is fully done.
- `_monitor.sh` — checks instance every 15 minutes, alerts via Windows notification if pipeline crashes or sessions die unexpectedly.

```bash
# In one WSL tmux window:
wsl bash _monitor.sh <host> <port>

# In another WSL tmux window:
wsl bash _sync_from_instance.sh <host> <port>

# Check sync progress
tail -f /tmp/sync_progress.log

# Check monitor
tail -f /tmp/monitor.log
```

To manually sync at any point:

```bash
rsync -avz -e "ssh -i ~/.ssh/vastai -p <port>" \
  root@<host>:/workspace/BA_01/morph_efficiency_project/logs/ \
  /mnt/c/Users/Sameh\ AbuRadi/Desktop/BA_01/morph_efficiency_project/logs/
```

---

## 6. Destroy the Instance

Once all results are confirmed locally, go to Vast.ai → Instances → Destroy.

---

## 7. View the Presentation

Open `morph_efficiency_project/presentation/index.html` in a browser.

---

---

# Execution Log (Actual Run — March 2026)

## Instance Details

- Provider: Vast.ai
- GPU: A100 PCIE 80GB (UK datacenter)
- Instance ID: 32552214
- SSH: `ssh3.vast.ai` port `32214`
- Cost: ~$1.228/hr
- SSH key: WSL `~/.ssh/vastai` — always use `wsl ssh`, never PowerShell ssh directly

## What Has Been Done

### ✅ Dry Run (Mar 8, ~20:30–21:00 UTC+1)

- Ran `download_data.py --max-sentences 50000` — completed for all 3 languages
- Ran `preprocess_baseline.py --max-sentences 50000` — all tokenizers trained, .npy files written
- Ran `preprocess_morph.py --max-sentences 50000` — all morph .npy files written
- Confirmed all output files present
- Wiped dry-run data

### ✅ Stage 1 — Download (Mar 8, ~21:07–22:03 UTC+1)

- `download_data.py --language all --base_dir morph_efficiency_project`
- EN hit 2.5B whitespace token target at 77.6M sentences
- AR and TR exhausted all configured sources before hitting target (see token imbalance issue below)
- Final sentence counts: EN 77.6M, AR 9.6M, TR 3.75M
- AR and TR will be re-downloaded after EN morph completes using expanded sources

### ✅ Stage 2 — Baseline Preprocessing (Mar 8, ~22:03 – Mar 9, ~00:54 UTC+1)

- `preprocess_baseline.py --language all --base_dir morph_efficiency_project`
- SentencePiece BPE tokenizers trained (32k vocab each)
- Subword token counts after tokenization:
  - EN: 3.57B train / 89M val / 89M test ✅
  - AR: 350M train / 8.75M val / 8.7M test ⚠️ (insufficient — will redo after re-download)
  - TR: 162M train / 4.05M val / 4.06M test ⚠️ (insufficient — will redo after re-download)

### ✅ Stage 3 — EN Morph Preprocessing (Mar 11–12, complete)

- Restarted Mar 11 ~00:11 UTC+1 with 32 parallel workers after first reboot incident
- 73.9M lines split into 33 chunks across 32 workers
- Resumable: each chunk saved to `data/processed/en/morph_chunks_train/` on completion
- Mar 11 ~03:55 UTC+1: 27/33 chunks done, then pool deadlocked (workers alive but 99% CPU idle — `multiprocessing.Pool.map()` hung waiting on results that never returned)
- Killed and restarted with 6 workers — immediately deadlocked again at 28/33
- Attempted `--workers 1` restart — produced corrupt output (1 chunk = 1/32nd of data, falsely resumed from old chunk_00000), bad train output deleted
- Fixed: added `maxtasksperchild=1` to Pool to recycle workers after each chunk, preventing memory buildup; raised resume size threshold to 500MB to reject partial outputs
- Second Vast.ai reboot at Mar 12 ~00:50 UTC+1 wiped all processed data again (see incident log)
- 24 good chunks backed up locally before reboot, re-uploaded and pipeline resumed from chunk 24
- All 33 chunks completed Mar 12 ~13:44 UTC+1, merge finished ~15:33 UTC+1
- Final output: train 9.4GB × 2 (tokens + feature_ids), val/test 239MB × 2 each — ~2.5B tokens, 18 feature bundles
- All output files backed up locally immediately after merge

### ✅ Stage 4a — EN Baseline Training (Mar 12, complete)

- Decision: complete a full EN pipeline (baseline + morph train → eval → results) before starting AR/TR
- Rationale: validate methodology end-to-end on one language before committing compute to all three
- AR/TR preprocessing will resume once EN results are confirmed
- `en_baseline` training started Mar 12 ~18:14 UTC+1, completed ~23:20 UTC+1 (~5 hrs)
- 110M params, 76,293 steps, 2,499,969,024 tokens — full Chinchilla budget consumed
- Final checkpoint: `models/en_baseline/ckpt_step0076293.pt`
- Checkpoints saved every 1,000 steps — resumable with `--resume` flag

### ✅ Stage 4b — EN Morph Training (Mar 13, complete)

- `en_morph` failed to start immediately after baseline — CUDA OOM: tried to allocate 38.74 GiB
- Root cause: morph vocab was 27,079,783 unique `root.POS` tokens — embedding table alone ~41GB in bfloat16
- Fix: capped vocab to top-50,000 by frequency, remapped all token ID arrays, `<unk>` for the rest
- 50k vocab embedding table = ~77MB — fits easily on A100 80GB
- Vocab cap script (`_cap_morph_vocab.py`) ran on instance — capped to 50k, unk_rate=10.68%
- `en_morph` training started Mar 13 ~23:54 UTC+1, completed Mar 13 ~05:35 UTC+1 (~5.7 hrs)
- 124M params, 76,293 steps, 2,499,969,024 tokens — full Chinchilla budget consumed
- Final checkpoint: `models/en_morph/ckpt_step0076293.pt`, backed up locally

### ✅ Stage 5 — EN Evaluation (Mar 13, complete)

**LM Evaluation (eval_lm.py):**
- EN Baseline: test loss=3.6743, test PPL=39.42, val PPL=39.41
- EN Morph: test loss=4.0158, test PPL=55.47, val PPL=55.49
- Raw PPL not directly comparable: different tokenizations (BPE subwords vs morpheme units), morph has 10.68% unk rate from vocab cap inflating loss

**Morphology Evaluation (eval_morphology.py):**
- EN Baseline: tokens_per_meaning_unit=1.0, nats_per_morpheme=3.6743, agreement_accuracy=None (no feature bundles in baseline)
- EN Morph: tokens_per_meaning_unit=4.9094, nats_per_morpheme=19.7149, agreement_accuracy=1.0, bundle_accuracy=1.0
- 4.91× token compression per meaning unit in morph regime
- All results saved to `logs/evaluation/en_baseline_lm.json`, `en_morph_lm.json`, `en_baseline_morph.json`, `en_morph_morph.json`

### ✅ Stage 6 — Aggregate Results (Mar 13, complete)

- `compute_metrics.py` ran successfully
- Outputs: `logs/summary/summary_table.csv`, `conclusion.md`, `learning_curves_en.png`, `tokens_per_unit.png`, `agreement_accuracy.png`, `flops_vs_accuracy.png`
- AR/TR rows in summary table marked as deferred
- All results synced locally via rsync

**Current status:** EN is the only completed language pipeline. AR and TR deferred due to compute budget exhaustion after two provider-side reboots and infrastructure incidents. EN results serve as proof-of-concept for the full three-language experiment. Full experiment estimated at ~€1,800 total compute.

### 🔜 Next: AR/TR Baseline Training

- Rent a new Vast.ai instance (A100 80GB, ≥100GB disk, PyTorch template)
- Upload project from WSL:
  ```bash
  rsync -avz --exclude '.git' --exclude '__pycache__' \
    /mnt/c/Users/Sameh\ AbuRadi/Desktop/BA_01/ \
    root@<host>:/workspace/BA_01/ \
    -e "ssh -i ~/.ssh/vastai -p <port>"
  ```
- SSH in, start tmux, run pipeline:
  ```bash
  wsl ssh -i ~/.ssh/vastai root@<host> -p <port>
  tmux new -s pipeline
  cd /workspace/BA_01
  bash _run_ar_tr_baseline.sh 2>&1 | tee full_pipeline.log
  ```
- Start local monitors (each in its own WSL tmux window):
  ```bash
  wsl bash _monitor.sh <host> <port>
  wsl bash _sync_from_instance.sh <host> <port>
  ```
- After pipeline completes: run `python _embed_data.py` locally to update `data.js` with AR/TR results
- Update STEPS.md with AR/TR baseline completion

### ✅ Fix: AR/TR Source Expansion (Mar 9–11)

- Original sources (Wikipedia + CC-100 + OPUS-100) exhausted before 2.5B target for AR and TR
- First fix attempt used `oscar-corpus/OSCAR-2301` — discovered to be gated (suspended, requires manual HF approval)
- Final fix: replaced with `allenai/MADLAD-400` — freely streamable, CC-BY-4.0, no gating
- Final source lists:
  - AR: Wikipedia AR + CC-100 AR + OPUS-100 AR + mC4 AR + MADLAD-400 AR (~8.8B combined capacity)
  - TR: Wikipedia TR + CC-100 TR + OPUS-100 TR + mC4 TR + MADLAD-400 TR (~25.8B combined capacity)
- Download script stops the moment 2.5B train tokens are reached — no wasted processing

---

## ✅ Resolved: Token Count Imbalance Across Languages

**Original problem:** After the initial Stage 1 download, subword token counts were severely unequal — EN 3.57B, AR 350M, TR 162M. Root cause: AR and TR sources were exhausted before hitting the 2.5B target.

**Fix applied (Mar 9–11):** Added `allenai/MADLAD-400` as final source for AR and TR. Combined capacity now ~8.8B for AR and ~25.8B for TR — both will easily hit 2.5B when re-downloaded.

**Current status:** AR/TR re-download and preprocessing deferred. We are completing the full EN pipeline first (train → eval → results) to validate the methodology end-to-end before committing compute to AR/TR. AR/TR will resume after EN results are confirmed.

---

## ⚠️ Incident: Vast.ai Instance Reboot — ~$48 Lost (Mar 10)

**What happened:** The Vast.ai instance was rebooted by the provider at ~10:15 UTC+1 on Mar 10, killing all tmux sessions mid-run. EN morph preprocessing had reached 36M/74M sentences (~1.196B tokens) before dying.

**Why the work was lost:** `preprocess_morph.py` had no resume/checkpoint logic at the time. It processed all chunks in memory and only wrote output after merging — a crash meant zero output saved.

**Cost:** ~39 hours of instance time at $1.228/hr = **~$48 wasted**.

**Fixes applied:**
1. Added chunk-level checkpointing — each worker saves its `.npz` to a persistent directory immediately on completion. Restart skips already-done chunks.
2. Added split-level resume — if final `.npy` output for a split already exists, the entire split is skipped.
3. Switched EN morph from single-threaded to 32 parallel workers — reduces processing time from ~85 hrs to ~6–10 hrs.
4. Added `_monitor.sh` — runs locally, checks instance every 15 min, sends Windows alert if pipeline crashes.

---

## ⚠️ Incident: Second Vast.ai Reboot — Additional Cost Lost (Mar 12)

**What happened:** The Vast.ai instance rebooted again at ~00:50 UTC+1 on Mar 12, killing all tmux sessions and wiping `/workspace/BA_01/morph_efficiency_project/data/processed/`. EN morph was at 28/33 chunks and had been deadlocked since ~03:55 the previous day.

**Why the work was partially saved:** 24 of the 28 completed chunks had been backed up locally via `_backup_chunks.sh` before the reboot. These are being re-uploaded to the instance to resume from chunk 24.

**Additional context:** The pool deadlock (workers alive, 99% CPU idle) was caused by memory pressure on large chunks. Fixed by adding `maxtasksperchild=1` to `multiprocessing.Pool` — workers are now recycled after each chunk, preventing memory buildup. Resume size threshold also raised to 500MB to reject corrupt partial outputs from the `--workers 1` incident.

---

| Date | Event | Balance |
|------|-------|---------|
| Mar 8 | Started instance | ~$9 |
| Mar 9 | Added $25 | ~$34 |
| Mar 9 | Added $115 | ~$124 |
| Mar 10 | Instance rebooted by Vast.ai — ~$48 lost, 36M sentences discarded | ~$76 |
| Mar 11–12 | EN morph pool deadlocks + second reboot — additional hours lost, 24/33 chunks recovered from local backup | — |
| Ongoing | ~$1.228/hr | — |
