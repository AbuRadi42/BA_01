# Mini Morphological Efficiency Experiment

A self-contained, CPU-runnable version of the full experiment.
Trains all 6 models (EN/AR/TR × baseline/morph) in ~30–60 min on a modern laptop.

## What it does

1. Downloads ~90k Wikipedia sentences per language (streaming, no large files)
2. Trains a SentencePiece BPE tokenizer (8k vocab) per language — baseline
3. Runs a rule-based morphological segmenter per language — morph
4. Trains 6 tiny GPT models (~2M params, 4 layers, 128 hidden, 5M tokens each)
5. Evaluates all 6 on held-out test sets
6. Prints a summary table with PPL ratios and tokens-per-meaning-unit

## Setup

```bash
pip install torch sentencepiece datasets numpy
```

## Run

```bash
python mini_experiment/run_mini.py
```

Fully resumable — re-running skips completed steps.

To run a single language first:
```bash
python mini_experiment/run_mini.py --langs en
```

## Outputs

| Path | Contents |
|------|----------|
| `mini_experiment/results/` | `{lang}_{regime}_eval.json` per model |
| `mini_experiment/results/mini_summary.json` | All results + PPL ratios |
| `mini_experiment/logs/` | Training timeseries JSONL per model |
| `mini_experiment/models/` | Final checkpoints |

## Caveats and theoretical framing

This is a **pilot**, not a conclusion. Three things to keep in mind:

**Scale:** The models are ~55× smaller than the full experiment (2M vs 110M params)
and trained on ~500× less data (5M vs 2.5B tokens). Scaling laws predict that
efficiency differences are *more pronounced* at larger scale, so a positive signal
here is a conservative lower bound.

**Morph tokenizer:** The full experiment uses language-specific grammar engines
(Arabic templatic segmentation, Turkish suffix-chain FSTs). The mini version uses
rule-based approximations — accurate enough to capture the information-density
difference, but not the full morphological structure.

**PPL comparability:** Baseline and morph models use different vocabularies, so
raw PPL numbers are not directly comparable across regimes. The meaningful signal
is the *learning curve* — how many tokens each model needs to reach a given loss
threshold — and the *tokens-per-meaning-unit* ratio.

The PPL ratio and learning efficiency numbers from this experiment can be used as
calibration points for a Chinchilla-based projection to full scale.
