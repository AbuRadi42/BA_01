# Experimental Contract
## Morphological Efficiency in Small Multilingual Language Models

**Author:** Sameh AbuRadi
**Purpose:** Internal research contract governing experiment design, execution, and interpretation
**Status:** Frozen before implementation

---

## 1. Purpose of This Document

This document defines the scientific scope, constraints, and success criteria of the project
“Morphological Efficiency in Small Multilingual Language Models.”

Its purpose is to:
- Fix the research question before implementation
- Prevent scope creep and post-hoc justification
- Ensure fair and interpretable comparisons
- Align implementation decisions with publishable claims

This document is not intended for submission or publication.

---

## 2. Core Research Claim

The central claim tested in this project is:

> Explicit morphology-aware grammar priors reduce the effective learning cost of small language models under identical architectures, data, and training budgets, with stronger effects observed in morphologically rich languages.

This is the only claim the project is required to support.

---

## 3. Definition of “Effective Learning Cost”

In this project, effective learning cost refers to the amount of computational effort required for a model to reach a given level of task performance.

Learning cost is operationalized using the following measurable proxies:

- Number of training tokens processed
- Number of training steps required
- Wall-clock training time (where available)
- Memory usage (secondary)

A reduction in learning cost is demonstrated if a morphology-aware model reaches a predefined performance threshold using fewer resources than its baseline counterpart.

---

## 4. Definition of “No Performance Sacrifice”

A morphology-aware model is considered to achieve its gains “without sacrificing performance” if:

- Its final test performance is equal to or greater than that of the baseline model, or
- Its performance is statistically indistinguishable from the baseline model within reasonable variance

Minor performance fluctuations that do not affect overall conclusions are acceptable. Systematic degradation is not.

---

## 5. Experimental Scope and Non-Goals

This project explicitly does NOT aim to:

- Claim superiority of one language over another
- Generalize results to all languages
- Compete with or replace large-scale language models
- Propose a new linguistic theory
- Formally validate Integrated Information Theory (IIT)
- Build production-ready grammar-constrained systems

Any findings outside the defined scope are considered exploratory and must be labeled as such.

---

## 6. Definition of “Grammar Priors” in This Project

In this project, grammar priors refer to:

- Morphology-aligned tokenization
- Explicit morphological feature embeddings
- Optional, non-generative grammatical constraints used only for analysis

Grammar priors do NOT include:
- Full symbolic grammars
- Handwritten syntactic parsers
- Semantic or world-knowledge rules

---

## 7. Parity and Fairness Rules

### 7.1 Within-Language Parity (Primary Requirement)

For each language (English, Arabic, Turkish):

- Baseline and morphology-aware models must share:
  - Identical model architecture
  - Identical raw data and data splits
  - Identical training budget and optimization settings

The only permitted difference is the inclusion of morphology-aware representations.

### 7.2 Cross-Language Comparisons (Secondary Analysis)

Cross-language comparisons are treated as a secondary research question.

They are conducted under explicitly defined fairness conditions (e.g., parallel translated tasks) and are interpreted cautiously.

No claims about inherent language superiority are permitted.

---

## 8. Language-Specific Morphological Features

Morphological features are language-specific by necessity.

To maintain fairness:
- Each language is assigned a small set of high-frequency, core morphological features that are standard for that language
- Feature sets are limited in size and complexity
- Rare, optional, or stylistic features are excluded

The goal is not to equalize grammatical expressiveness across languages, but to apply the same type of morphology-aware inductive bias within each language.

---

## 9. Success Criteria

The experiment is considered successful if at least one of the following holds consistently:

- Morphology-aware models reach target performance using fewer training tokens or steps
- Morphology-aware models show improved efficiency metrics (e.g., tokens per meaning unit)
- Morphology-aware models demonstrate improved grammatical agreement accuracy at comparable perplexity

Failure to observe these effects constitutes a valid negative result and must be reported honestly.

---

## 10. Primary and Secondary Research Questions

### Primary Question
Does incorporating morphology-aware grammar priors reduce the learning cost of small language models within a given language?

### Secondary Question
Do languages with richer morphological structure exhibit larger efficiency gains or different reasoning behavior under identical modeling constraints?

The primary question takes precedence in analysis and presentation.

---

## 11. Interpretation Rules

- Results must be interpreted conservatively
- Correlation must not be framed as causation
- All claims must be directly supported by reported metrics
- Ambiguous outcomes must be acknowledged explicitly

---

## 12. Freeze Clause

Once implementation begins:
- This contract may not be altered to fit results
- Deviations must be documented and justified
- New experiments may be added only if clearly labeled as exploratory

---

**End of Experimental Contract**
