# Citation Verification Checklist

**Purpose.** Every citation flagged `[VERIFY]` in `manuscript/section_09_references.md` needs confirmation before submission. For each item below, the manuscript makes a specific claim attributed to that source; if the paper does not actually support the claim, the reference must be replaced or the claim softened.

**Scope.** Week 1 lit-review task per `MANUSCRIPT_PLAN.md` §5.

---

## High-stakes — claims load-bearing, citation must be right

### 1. Allen-Zhu and Li (2024) — bits-per-parameter capacity — ✅ VERIFIED 2026-04-19

- **Used in:** §4.5 (equation 4.5 / κ ≈ 2), Appendix D (implicitly via κ).
- **Status:** Title, authors, arXiv:2404.05405 confirmed. Abstract claim "language models can and only can store 2 bits of knowledge per parameter, even when quantized to int8" matches draft usage exactly.

### 2. Ahia et al. (2023) — per-language compute cost — ✅ VERIFIED 2026-04-19

- **Used in:** §3.5 Related Work (Green AI, linguistic equity, edge ML neighbourhood).
- **Status:** Confirmed as EMNLP 2023, pp. 9904–9923, Singapore. `ahia2023` bib entry enriched with pages and address.

### 3. Morpheme-aware tokenizer prior art for Turkish / Arabic — ✅ VERIFIED 2026-04-19

- **Used in:** §3.2 Related Work.
- **Status:** Placeholder footnote replaced with two verified inline citations:
  - \citet{ataman2018} — ACL 2018 (Vol. 2 Short Papers), pp. 305–311, "Compositional Representation of Morphologically-Rich Input for Neural Machine Translation" (Turkish focus).
  - \citet{bostrom2020} — Findings of EMNLP 2020, pp. 4617–4624, "Byte Pair Encoding is Suboptimal for Language Model Pretraining" (morphology alignment of unigram LM vs BPE).

---

## Medium-stakes — bibliographic detail only

### 4. Comrie (1989) — *Language Universals and Linguistic Typology* — ✅ VERIFIED 2026-04-19

- **Status:** 2nd edition, 1989, confirmed via OpenLibrary MARC (LCCN 89040280). Published jointly by Blackwell (Oxford, ISBN 0631129715) and University of Chicago Press (Chicago, ISBN 0226114333). Draft uses the Chicago printing (correct); ISBN added.

### 5. Haspelmath and Sims (2010) — *Understanding Morphology* — ✅ VERIFIED 2026-04-19, entry corrected

- **Status:** 2nd edition, 2010, authoritative imprint is **Routledge**, London, ISBN 9780340950012 (publisher product page). Draft previously said Hodder Education — corrected. (Hodder was the group at release; Routledge is the canonical imprint after Taylor & Francis consolidation.)

### 6. Buckwalter (2004) — Arabic Morphological Analyzer — ✅ VERIFIED 2026-04-19

- **Status:** LDC2004L02 confirmed via catalog.ldc.upenn.edu. Bib entry enriched with address (Philadelphia, PA) and URL.

### 7. Schaeffer et al. (2023) — emergence mirage — ✅ VERIFIED 2026-04-19

- **Status:** NeurIPS 2023 (Advances vol. 36), pp. 55565–55581, Curran Associates. Bib entry updated with volume, pages, publisher.

### 8. Wei et al. (2023) — Native language structural connectome — ✅ VERIFIED 2026-04-19

- **Used in:** §2 Introduction (motivation for Templatic Lexical Surplus).
- **Status:** PMID 36805092, NeuroImage vol. 270, art. 119955, DOI 10.1016/j.neuroimage.2023.119955. All six authors confirmed. §2 paraphrase tightened to match actual finding (semantic language regions + posterior corpus callosum, not "phonological regions").

---

## Low-stakes — already confident, verification for form only

These citations are recalled with high confidence; verification is a formality.

- Vaswani et al. 2017 (Attention Is All You Need).
- Kaplan et al. 2020 (Scaling Laws).
- Hoffmann et al. 2022 (Chinchilla) — already cross-checked in earlier project docs.
- Sennrich et al. 2016 (BPE).
- Kudo & Richardson 2018 (SentencePiece).
- Loshchilov & Hutter 2019 (AdamW).
- Oflazer 1994 (Turkish morphology).
- Greenberg 1960 (Index of Synthesis) — original IJAL article.
- Schwartz et al. 2020 (Green AI).
- Strubell et al. 2019 (Energy and Policy).
- Bender et al. 2021 (Stochastic Parrots).
- Wei et al. 2022 (Emergent Abilities) — TMLR publication confirmed.

---

## Verification workflow

Per item:

1. Search the ACL Anthology, arXiv, or Google Scholar for the claimed author–year combination.
2. Open the paper; confirm the specific claim the manuscript attaches to it is the paper's actual finding (or a direct implication).
3. Copy authoritative bibliographic fields (DOI, arXiv ID, venue, page range) into the reference entry.
4. If the paper does not support the claim: replace, soften, or remove the citation, and note the change in this file.

Target: all `[VERIFY]` tags resolved by end of Week 1 (2026-04-24).
