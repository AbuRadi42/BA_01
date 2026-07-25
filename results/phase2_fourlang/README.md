# Phase 2, Stage 1: four-language headline results

This directory holds the raw, per-run readings behind the four-language headline
table (`tab:phase2`) in the manuscript (`manuscript/tex/sections/sec_06_results.tex`).
It is the committed, citable record for the Mandarin, English, and Turkish rows, and
for the single-run Arabic row; the seed-replicated Arabic study lives separately in
`../phase2_seeds/`.

## What each file is

For every cell `<lang>_<regime>/` (languages in typological order ZH, EN, TR, AR):

- `summary.json` : the headline per-run numbers, including `final_eval_bpc`
  (bits per character, the tokeniser-neutral metric the paper compares on),
  `final_eval_loss`, `final_eval_ppl`, `n_params`, `tokens_seen`, and throughput.
- `run_config.json` : the exact hyperparameters the run was launched with.
- `metrics.jsonl` : per-eval training curve (one JSON record per evaluation step).

Top level:

- `results.csv` : all eight cells' summary numbers in one table.
- `figures_data.json` : the aggregated values the Phase 2 figures are drawn from.

## The numbers that appear in the manuscript

`final_eval_bpc`, baseline then morph, matching `tab:phase2` exactly:

| Language | baseline | morph | Delta bpc |
|----------|----------|-------|-----------|
| Mandarin | 4.379491 | 4.383930 | -0.0044 |
| English  | 1.052717 | 1.088323 | -0.0356 |
| Turkish  | 0.881075 | 0.897596 | -0.0165 |
| Arabic   | 1.146388 | 1.124583 | +0.0218 |

Of the four, only Arabic shows a positive rebate. The seed-replicated Arabic study
in `../phase2_seeds/` confirms that Arabic rebate holds across four seeds
(+0.0192 +/- 0.0023 bpc) and separates structure from capacity against a shuffled
control.

## Provenance and the weights

These runs were executed on a raw g6 EC2 box (NVIDIA L4 / L40S), each on a
compute-optimal 640M-token budget. What is committed here are the readings only.
The trained checkpoints (~539 MB per cell) are retained on the training box and the
local VPS backup, not committed here: they are large and regenerate deterministically
from `run_config.json` plus the tracked tokeniser vocabularies at
`mini_experiment/tokenizers/`. The Arabic seed cells in `../phase2_seeds/` are a
separate matter: there the queue deleted the checkpoints, so the readings are the
only surviving artefact for those.

## Reproducing

The trainer is `morph_efficiency_project/scripts/train_model.py`; each cell's
`run_config.json` records its exact arguments. The tokenised `.npy` streams are not
stored here (they regenerate deterministically from the tokeniser vocabularies via
`morph_efficiency_project/scripts/tokenize_for_training.py`).
