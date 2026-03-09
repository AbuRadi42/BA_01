# Feasibility Assessment
## Morphological Efficiency in Small Multilingual Language Models
**Author:** Sameh AbuRadi
**Date:** February 2026
**Status:** Pre-implementation review — revised after budget assessment

---

## 1. Project Summary

This project trains and evaluates six language models across three languages (English, Arabic, Turkish), each with a baseline and a morphology-aware variant, to empirically test whether grammatical structure priors reduce learning cost under identical conditions.

The experiment is governed by a frozen scientific contract. Results are reported as-found — no outcome is assumed in advance.

---

## 2. Model Scale Decision (Revised)

After budget assessment, the model scale was reduced from the originally planned 425M to 125M parameters. See §11 for the full technical record of this decision.

The revised scale in use:

| Parameter | Value |
|---|---|
| Parameters per model | ~125M |
| Training tokens per model | 2.5B |
| Architecture | Decoder-only GPT-style transformer |
| Layers | 12 |
| Hidden size | 768 |
| Attention heads | 12 |
| FFN dimension | 3072 |
| Context length | 1024 tokens |
| Vocabulary size | 32k (baseline) / determined by morpheme inventory (morph) |
| Precision | bfloat16 |

This scale sits at the Chinchilla-optimal point (125M × 20 = 2.5B tokens).

---

## 3. Why This Scale

| Scale | Params | Interactive? | Scientifically valid? |
|---|---|---|---|
| Toy (original plan) | ~4M | No | Yes |
| Current (revised) | 125M | Barely | Yes |
| Original plan | 425M | Yes | Yes |
| Large | 1B+ | Yes | Yes, but high cost |

The 125M scale is sufficient to produce measurable, interpretable results across all five evaluation metrics. Output fluency is reduced compared to 425M, but the core scientific comparison — baseline vs. morph efficiency — is fully valid at this scale.

---

## 4. Compute Infrastructure

**Selected platform:** Vast.ai

| Platform | GPU | Price/hr | Notes |
|---|---|---|---|
| Vast.ai | A100 80GB | ~$0.35–0.70 | Cheapest available; spot instances; less stable than RunPod |
| RunPod | A100 80GB | ~$0.79 | Good cost/reliability balance; original recommendation |
| Lambda Labs | A100 80GB | ~$1.10 | Simpler UX; higher cost |
| Google Colab Pro+ | A100 | ~$50/mo flat | Not suitable — session limits prevent multi-day runs |
| AWS/GCP/Azure | A100 | ~$3–4/hr | Overkill complexity and cost for this project |

**Why Vast.ai over Google Colab Pro:**
Colab Pro+ gives roughly 24–48 hours of compute per session before hitting usage limits, and sessions are not resumable across billing cycles in a reliable way. A single 125M model requires ~15–18 GPU hours — manageable in one session — but running all 6 sequentially across multiple sessions introduces significant friction and risk of data loss between sessions. Vast.ai spot instances are cheaper per hour, support persistent storage volumes, and allow unattended multi-day runs with checkpoint resumption. The tradeoff is occasional instance preemption, which is mitigated by the checkpoint-every-1000-steps mechanism already built into `train_lm.py`.

**Verdict:** Vast.ai is the better option for this workload. Colab Pro is acceptable as a fallback for single-model test runs only.

---

## 5. Compute Cost Estimate (Revised)

Each 125M model trained on 2.5B tokens on a single A100 80GB:

- Throughput estimate: ~80,000–100,000 tokens/sec (125M bfloat16 + flash attention)
- Estimated GPU hours per model: ~7–9 hrs
- 6 models total: ~42–54 GPU hours
- At $0.50/hr (Vast.ai mid estimate): **$21 – $27**
- With buffer for reruns, preprocessing, evaluation, spot preemptions: **~$60–$100 total**

This is a significant reduction from the original $1,200–$1,500 estimate, which was based on the 425M / 8.4B token configuration.

---

## 6. Data Requirements

2.5B tokens per language is achievable from Wikipedia alone for English and Arabic. Turkish may require supplementing with OPUS TR.

| Language | Primary Sources |
|---|---|
| English | Wikipedia EN, OPUS (TED, News), CC-100 EN subset |
| Arabic | Wikipedia AR, OPUS AR, CC-100 AR, OSIAN corpus |
| Turkish | Wikipedia TR, OPUS TR, CC-100 TR |

Split targets per language:
- Train: ~2.5B tokens
- Validation: ~62.5M tokens
- Test: ~62.5M tokens

---

## 7. Timeline Estimate (Revised)

| Phase | Duration |
|---|---|
| Environment setup + data pipeline | 3–5 days |
| Tokenizer training (all 6) | 1 day |
| Model training (6 models, sequential on Vast.ai) | 3–5 days |
| Evaluation + metrics aggregation | 2–3 days |
| Dashboard and presentation build | done |
| **Total** | **~2–3 weeks** |

Training can be parallelized across two Vast.ai instances (3 models each) to halve wall time at the same total cost.

---

## 8. Presentation Layer

A browser-based slide presentation (`presentation/index.html`) has been built with HTML, Tailwind CSS, D3.js, and a slide-based layout. It:

- Loads experiment metrics from JSON/JSONL log files output by the training and evaluation scripts
- Renders animated learning curves, perplexity comparisons, tokens-per-meaning-unit charts, agreement accuracy, learning efficiency (steps to threshold), downstream task tables, a Pareto compute chart, and a full summary table
- Presents findings neutrally — auto-generated from measured data, no pre-written conclusions
- Runs locally with no server required

---

## 9. Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Vast.ai spot instance preemption | Medium-High | Checkpoint every 1k steps; `--resume` flag in train_lm.py |
| camel_tools Arabic analyzer instability | Medium | Test early; Farasa fallback configured |
| Turkish morpheme chains causing sequence length blowup | Medium | Cap morpheme depth; monitor avg tokens/sentence |
| Data quality issues in CC-100 | Low-Medium | Filter by language confidence score; deduplicate |
| Compute cost overrun | Low | Budget is small; set spend alerts on Vast.ai |

---

## 10. Feasibility Verdict

At the revised 125M / 2.5B token scale on Vast.ai, this project is feasible within a budget of approximately **$60–$100** and a timeline of **2–3 weeks**.

The scientific design remains sound. All five evaluation metrics (perplexity, tokens per meaning unit, morphological agreement accuracy, learning efficiency, downstream task performance) are fully measurable at 125M scale. The within-language baseline vs. morph comparison is not affected by the scale reduction.

---

## 11. Scale Downgrade Record (for academic reference)

This section documents the technical decision to reduce model scale, for inclusion in the methods section of the final paper.

**Original specification:**
- Parameters: ~425M per model
- Training tokens: 8.4B per model (Chinchilla-optimal at 425M × 20)
- Architecture: 24 layers, hidden size 1024, 16 attention heads, FFN dim 4096
- Estimated compute: 150–200 GPU hours per model; ~$1,200–$1,500 total at RunPod pricing
- Rationale for original scale: 425M is the minimum parameter count at which decoder-only transformers produce outputs coherent enough for live interactive demonstration to non-technical audiences

**Revised specification:**
- Parameters: ~125M per model
- Training tokens: 2.5B per model (Chinchilla-optimal at 125M × 20)
- Architecture: 12 layers, hidden size 768, 12 attention heads, FFN dim 3072
- Estimated compute: 7–9 GPU hours per model; ~$60–$100 total at Vast.ai pricing
- Platform: Vast.ai (spot A100 80GB instances, ~$0.35–$0.70/hr)

**Reason for downgrade:** Budget constraints. The $1,200–$1,500 cost of the 425M configuration was not feasible for an independently funded research project. The 125M scale was selected as the largest configuration achievable within a ~$100 budget while remaining Chinchilla-optimal and scientifically valid for the core research question.

**Scientific impact of downgrade:** None on the primary research question. The experiment compares baseline vs. morphology-aware models within each language under identical conditions. This within-language comparison is scale-invariant — the efficiency signal being measured does not require a specific parameter count to be detectable. The reduction in output fluency is noted but does not affect any of the five quantitative evaluation metrics. Results at 125M are not directly comparable to results at 425M, and no such comparison is made in this paper.

