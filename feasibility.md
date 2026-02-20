# Feasibility Assessment
## Morphological Efficiency in Small Multilingual Language Models
**Author:** Sameh AbuRadi
**Date:** February 2026
**Status:** Pre-implementation review

---

## 1. Project Summary

This project trains and evaluates six language models across three languages (English, Arabic, Turkish), each with a baseline and a morphology-aware variant, to empirically test whether grammatical structure priors reduce learning cost under identical conditions.

The experiment is governed by a frozen scientific contract. Results are reported as-found — no outcome is assumed in advance.

---

## 2. Model Scale Decision

After evaluation of interactivity requirements and compute constraints, the following scale was selected:

| Parameter | Value |
|---|---|
| Parameters per model | ~425M |
| Training tokens per model | 8.4B |
| Architecture | Decoder-only GPT-style transformer |
| Layers | 24 |
| Hidden size | 1024 |
| Attention heads | 16 |
| FFN dimension | 4096 |
| Context length | 1024 tokens |
| Vocabulary size | 32k |
| Precision | bfloat16 |

This scale sits at the Chinchilla-optimal point (425M × 20 ≈ 8.5B tokens), meaning the model is neither under-trained nor wastefully over-trained. At this scale, models produce coherent, interactive outputs suitable for demonstration to non-technical audiences.

---

## 3. Why This Scale

| Scale | Params | Interactive? | Scientifically valid? |
|---|---|---|---|
| Toy (original plan) | ~4M | No | Yes |
| Small | 125M | Barely | Yes |
| Selected | 425M | Yes | Yes |
| Large | 1B+ | Yes | Yes, but high cost |

The 425M scale is the lowest parameter count that produces outputs coherent enough for live demonstration while remaining within a reasonable compute budget.

---

## 4. Compute Infrastructure

**Recommended platform:** RunPod or Lambda Labs

| Platform | GPU | Price/hr | Notes |
|---|---|---|---|
| RunPod | A100 80GB | ~$0.79 | Best cost/reliability balance |
| Lambda Labs | A100 80GB | ~$1.10 | Simpler UX, slightly higher cost |
| Vast.ai | A100 80GB | ~$0.35–0.70 | Cheapest, spot instances, less stable |
| Colab Pro+ | A100 | ~$50/mo flat | Not suitable for multi-day runs |
| AWS/GCP/Azure | A100 | ~$3–4/hr | Overkill complexity for this project |

**Recommendation:** RunPod for cost efficiency. Lambda Labs as fallback for reliability.

---

## 5. Compute Cost Estimate

Each 425M model trained on 8.4B tokens on a single A100 80GB:

- Estimated GPU hours per model: 150–200 hrs
- 6 models total: 900–1,200 GPU hours
- At $0.79/hr (RunPod): **$710 – $950**
- With buffer for reruns, debugging, preprocessing: **~$1,200 – $1,500 total**

This is a one-time cost for the full experiment.

---

## 6. Data Requirements

8.4B tokens per language requires combining multiple open corpora:

| Language | Primary Sources |
|---|---|
| English | Wikipedia EN, OPUS (TED, News), CC-100 EN subset |
| Arabic | Wikipedia AR, OPUS AR, CC-100 AR, OSIAN corpus |
| Turkish | Wikipedia TR, OPUS TR, CC-100 TR |

Wikipedia alone provides roughly 1–3B tokens per language. The remainder comes from OPUS and CC-100, both freely available. Data download and preprocessing is non-trivial but fully automatable via `scripts/download_data.py`.

Split targets per language:
- Train: ~8B tokens
- Validation: ~200M tokens
- Test: ~200M tokens

---

## 7. Timeline Estimate

| Phase | Duration |
|---|---|
| Environment setup + data pipeline | 1–2 weeks |
| Tokenizer training (all 6) | 2–3 days |
| Model training (6 models, parallelizable) | 2–4 weeks |
| Evaluation + metrics aggregation | 1 week |
| Dashboard and presentation build | 1 week |
| **Total** | **6–9 weeks** |

Training can be parallelized across multiple GPU instances to compress the timeline. Running 2 models simultaneously halves training wall time at double the hourly cost — total spend remains the same.

---

## 8. Presentation Layer

In addition to the scientific pipeline, a browser-based HTML/Tailwind CSS/JavaScript dashboard will be built to present results to non-technical audiences. It will:

- Load experiment metrics from JSON output files
- Display learning curves, side-by-side comparisons, and efficiency metrics visually
- Present findings neutrally — the data speaks, no conclusions are pre-written
- Run locally with no server required (open in browser)

This dashboard is a separate deliverable from the scientific pipeline and can be built incrementally as results come in.

---

## 9. Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| camel_tools Arabic analyzer instability | Medium | Test early, have fallback (Farasa or CAMeL) |
| Turkish morpheme chains causing sequence length blowup | Medium | Cap morpheme depth, monitor avg tokens/sentence |
| GPU session interruption mid-training | High | Checkpoint every 1k steps, resume from checkpoint |
| Data quality issues in CC-100 | Low-Medium | Filter by language confidence score, deduplicate |
| Compute cost overrun | Low | Set hard budget alerts on RunPod, checkpoint before stopping |

---

## 10. Feasibility Verdict

This project is feasible within a budget of approximately $1,200–$1,500 and a timeline of 6–9 weeks.

The scientific design is sound, the compute requirements are well-scoped, and the data is available from open sources. The addition of a visual presentation dashboard makes the results accessible to non-technical stakeholders without compromising scientific integrity.

The experiment is designed to report whatever the data shows. No outcome is assumed.
