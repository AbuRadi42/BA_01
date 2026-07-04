# Phase 2, Stage 1: Arabic seed-replication results

This directory holds the raw, per-run results of the Arabic seed-replication study
reported in the manuscript (`manuscript/tex/`). It is the durable, citable record of
the experiment: for each training run we keep its final-metrics summary, its exact
run configuration, and its full training-metrics log.

## What each file is

For every cell `ar_<regime>_s<seed>/`:

- `summary.json` : the headline per-run numbers, including `final_eval_bpc`
  (bits per character, the tokeniser-neutral metric the paper compares on),
  `final_eval_loss`, `final_eval_ppl`, `n_params`, `tokens_seen`, and throughput.
- `run_config.json` : the exact hyperparameters the run was launched with.
- `metrics.jsonl` : per-eval training curve (one JSON record per evaluation step).

Top level:

- `results.csv` : all cells' summary numbers in one table.
- `training_run.log` : the complete stdout of the queued training run, in order.

## Design

Every cell trains an identical transformer (model dim 512, 10 layers, 8 heads,
~48M transformer parameters) on a compute-optimal Arabic token budget
(640M tokens, batch 64, sequence length 128, 78,125 steps). The only thing that
varies is the tokenisation regime and the random seed:

- `baseline` : one input stream (byte-pair surface tokens).
- `morph`    : the grammar-aware regime, four input streams
  (surface + feature bundle + consonantal root + `wazn` pattern).
- `shuf`     : the shuffled control. Identical to `morph` in every way, including
  parameter count, except the root and `wazn` stream *contents* are randomly
  permuted per seed. This separates "structure" from "extra capacity".

The random seed controls the training-data sampling order; weight initialisation
also varies run to run (the trainer does not pin PyTorch's global RNG), so each
seed is an independent draw over both sources of randomness.

## Headline result (all four seeds complete)

bits per character, lower is better:

| seed | baseline | morph | shuffled | morph vs baseline | morph vs shuffled |
|------|----------|-------|----------|-------------------|-------------------|
| 1    | 1.1456   | 1.1239 | 1.1663  | +0.0217           | +0.0424           |
| 2    | 1.1422   | 1.1228 | 1.1652  | +0.0194           | +0.0424           |
| 3    | 1.1415   | 1.1260 | 1.1689  | +0.0155           | +0.0429           |
| 4    | 1.1461   | 1.1257 | 1.1697  | +0.0204           | +0.0440           |

- **Grammar-aware Arabic beats baseline by +0.0192 +/- 0.0023 bpc** across four seeds
  (all four positive). The mean sits roughly eight standard deviations from zero:
  the rebate is large relative to run-to-run noise.
- **Real root/wazn beats scrambled root/wazn by +0.0429 +/- 0.0007 bpc**, and the
  scrambled control lands *below* baseline in every seed (-0.021, -0.023, -0.027,
  -0.024). Same parameter count, only the grammatical content differs: the gain is
  structural, not a capacity artefact.

All 12 cells (4 seeds x baseline/morph/shuffled) are present; `results.csv` and
`training_run.log` cover the complete run.

## Reproducing

The trainer is `morph_efficiency_project/scripts/train_model.py`; each cell's
`run_config.json` records its exact arguments. The tokeniser vocabularies are
tracked at `mini_experiment/tokenizers/`. The tokenised `.npy` streams are not
stored here (they are large and regenerate deterministically from the vocabularies
via `morph_efficiency_project/scripts/tokenize_for_training.py`).
