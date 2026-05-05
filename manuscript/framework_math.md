# Framework Derivation — H(L) to the Parameter Rebate

**Status:** Working draft v1 — the keystone of the paper's §4.2.
**Purpose:** Derive a defensible formula connecting a language's grammatical information content H(L) to a parameter-count rebate ΔN(L) in a transformer trained under morphology-aligned vs BPE tokenization.
**Next step:** Sanity-check every numerical assumption; lock the weakest step before writing §4.2 prose.

---

## 0. Notation

| Symbol | Meaning |
|--------|---------|
| L | a language |
| B(L) | set of grammatical feature bundles realisable on a single word form in L |
| H(L) | grammatical information content of a word form in L, in bits |
| ρ(L) | structural recoverability coefficient — fraction of H(L) recoverable by a regular algorithm from surface form, ∈ [0, 1] |
| N | transformer parameter count |
| D | training token count |
| κ | effective model capacity coefficient, bits per parameter |
| ℒ(N, D) | test cross-entropy loss of a transformer with N params trained on D tokens |
| E | irreducible entropy floor of the data distribution |
| ΔN(L) | parameter rebate: reduction in N required to reach a fixed capability under morphology-aligned tokenization |
| α | cross-lingual coefficient linking H(L) to ΔN(L), to be estimated empirically |

---

## 1. Grammatical information content H(L)

### 1.1 Upper bound (Structural Synthesis Ceiling)

For a language L whose morphology realises feature bundles in B(L):

    H_max(L) = log₂ |B(L)|       (bits per word form, upper bound)

This is the **Structural Synthesis Ceiling (SSC)**: the maximum grammatical information content a single word form can carry, given the language's grammatical categories and their interactions, after accounting for syncretism, defectiveness, and paradigm gaps.

SSC is a structural property of the grammar, derivable from an engine without reference to any corpus. It differs from Greenberg's (1960) Index of Synthesis, which is a corpus-averaged count of morphemes per word form; SSC is an upper bound on what the morphology can express in principle.

### 1.2 Corpus-weighted entropy

The realised grammatical information content, weighted by the distribution over feature bundles in naturally occurring text:

    H(L) = − Σ_{b ∈ B(L)} p(b) log₂ p(b)

with p(b) estimated from a tokenised corpus. H(L) ≤ H_max(L), with equality iff every bundle is equiprobable.

### 1.3 Numerical values (Phase 1 engines, first-pass upper bounds)

| Language | \|B(L)\| | H_max(L) = log₂ \|B(L)\| bits |
|----------|----------|-------------------------------|
| English  | 23       | 4.52                          |
| Turkish  | 63       | 5.98                          |
| Arabic   | 270      | 8.08                          |

(Corpus-weighted H(L) is computed in `scripts/compute_hl.py` — pending.)

---

## 2. Decomposition of the transformer test loss

### 2.1 The published scaling law

Hoffmann et al. (2022) report test loss for a decoder-only transformer as:

    ℒ(N, D) = E + A·N^(−α_N) + B·D^(−α_D)

with α_N ≈ 0.34, α_D ≈ 0.28 at their regime. E is the irreducible entropy floor.

The shape is language-agnostic by assumption in the original work. This framework treats that assumption as the thing to question.

### 2.2 Loss decomposition by source

The cross-entropy ℒ is the expected bits-per-token the model spends predicting held-out text. It decomposes, at least conceptually, into:

    ℒ ≈ H_semantic + H_grammatical + H_noise

where H_grammatical is the portion attributable to predicting grammatical form (person, number, tense, etc.), H_semantic covers lexical and world-knowledge content, and H_noise captures unpredictable content (proper nouns, stylistic choice). Only the grammatical component varies by tokenization regime for the same language and corpus.

---

## 3. Implicit grammar cost under BPE

### 3.1 The claim

Under byte-pair tokenization, grammatical structure is not pre-encoded. The model must learn, from distributional co-occurrence alone, that e.g. `book-s` and `cat-s` share the plural morpheme. This learning consumes capacity.

Call **C_implicit(L)** the model capacity (in bits) spent learning H_grammatical(L) under BPE.

### 3.2 Scaling with H(L)

The number of distinct grammatical states the model must distinguish is |B(L)|. The distributional learning cost of reconstructing these states, in bits of model capacity, scales with the entropy of their joint distribution — approximately H(L) — times some inefficiency factor f_BPE capturing how poorly BPE fragments align with morphemes:

    C_implicit(L) ≈ f_BPE · H(L) · |V_context|

where |V_context| is the effective number of distinct lexical contexts the grammar must be learned across. For a fixed corpus and language, the second and third factors are approximately constant across the languages compared; the critical variable is H(L).

Promoting this relationship to a named framework assumption:

> **Assumption A1 (dominant-term linearity).** The capacity a BPE-trained transformer spends reconstructing grammatical structure from distribution is, to first order, linear in the grammatical information content H(L):
>
>     C_implicit(L) = α · H(L) + O(lower-order terms)
>
> where α absorbs the language-invariant factors (f_BPE, |V_context|, κ) introduced in §5.

A1 is the simplest non-trivial form consistent with the Phase 1 three-language ordering. Richer parameterisations (log-linear, threshold non-linearities, rule-count-based scaling) are compatible with the framework but are not required to explain the observed gradient. Distinguishing A1 from these alternatives requires more than three data points and is left to follow-up validation across the six additional engines in the repository (de/es/hu/sw/eu/zh).

### 3.3 Structural recoverability

Not all H(L) bits are equally easy for a distributional learner to recover. In agglutinative languages (Turkish), morpheme boundaries are cleanly marked and BPE fragments approximately align with them. In templatic languages (Arabic), root and pattern fuse across discontiguous positions of the surface form; the same surface string can correspond to multiple grammatical bundles, and disambiguation requires lexical context.

**Definition.** The structural recoverability of a language L is:

    ρ(L) = 1 − H(bundle | surface) / H(bundle)

where H(bundle) is the marginal entropy of grammatical bundles in the corpus (the quantity H(L) of §1.2), and H(bundle | surface) is the conditional entropy of the bundle given the surface form alone, estimated from a held-out corpus via

    H(bundle | surface) = Σ_s p(s) · H(bundle | surface = s)

with H(bundle | surface = s) computed over the empirical distribution of bundles observed for each surface string s.

**Interpretation.** ρ(L) is the fraction of grammatical uncertainty resolved by observing the surface form alone.
- A bijective morphology (surface ↔ bundle one-to-one) has H(bundle | surface) = 0, so ρ = 1.
- A fully ambiguous morphology (surface form reveals no structure) has H(bundle | surface) = H(bundle), so ρ = 0.

ρ(L) is a property of the grammar (and the corpus distribution), not of the tokenizer. It is computable from an engine's output on held-out text. First-pass expected ordering — ρ(Turkish) ≈ 1.0 > ρ(English) ≈ 0.9 > ρ(Arabic) ≈ 0.5–0.7 — will be tested against the computed values in `scripts/compute_hl.py`; if the computed ordering diverges substantially, the framework is refined accordingly.

The effective grammatical information a BPE model can recover through distributional learning — and that a morph-aligned tokenizer can deliver as explicit structure:

    H_eff(L) = ρ(L) · H(L)

Both tokenization regimes are capped at H_eff(L). The rebate argument below concerns this effective quantity.

---

## 4. Explicit grammar cost under morphology-aligned tokenization

Under morphology-aligned tokenization, the grammatical feature bundle is an input to the model, summed at the embedding layer (per the existing pipeline: `x = token_emb[root_id] + feat_emb[bundle_id]`).

The capacity cost is the size of the feature-bundle embedding table:

    C_explicit(L) = |B(L)| · d_emb · (bits per weight)

For Arabic with |B(L)| = 270, d_emb = 768, bits per weight = 16 (bfloat16):

    C_explicit(Arabic) = 270 · 768 · 16 ≈ 3.3 Mbit ≈ 0.4 MB

Compared to a 100M-parameter model (~200 MB at bfloat16), this is a three-order-of-magnitude-smaller overhead. For the purposes of the rebate argument, **C_explicit(L) ≈ 0**.

---

## 5. The parameter rebate

### 5.1 Definition

The parameter rebate is the reduction in parameter count required to reach a fixed capability threshold when moving from BPE to morphology-aligned tokenization:

    ΔN(L) = N_BPE(L, T) − N_morph(L, T)

where T is a fixed capability target (e.g. loss threshold, downstream task score).

### 5.2 From capacity to parameters

Model capacity in bits is approximately κ · N for a well-trained transformer, where κ is an effective bits-per-parameter coefficient. Allen-Zhu and Li (2024), in "Physics of Language Models: Part 3.3, Knowledge Capacity Scaling Laws," report that transformers saturate at approximately 2 bits of storable knowledge per parameter across architecture variants and training regimes. We take **κ ≈ 2 bits/param** as the working value.

If the precise Allen-Zhu coefficient shifts under re-examination during Week 1 lit review, the ordinal predictions of this framework are unaffected; only the numerical fit for α in [R1] is rescaled. The Kaplan (2020) and Hoffmann (2022) scaling-law fits give implicit estimates of the same quantity that agree with Allen-Zhu to within an order of magnitude.

The rebate in capacity terms:

    ΔC(L) = C_implicit(L) − C_explicit(L) ≈ f_BPE · ρ(L) · H(L) · |V_context|

(The explicit term is negligible, as shown in §4.)

Converting to parameters:

    ΔN(L) = ΔC(L) / κ = (f_BPE · |V_context| / κ) · ρ(L) · H(L)

Grouping the language-invariant coefficients:

    **ΔN(L) = α · ρ(L) · H(L)**       [R1]

where α = f_BPE · |V_context| / κ is a cross-lingual constant — a single number to be fit from data across all languages.

### 5.3 Ordinal check against Phase 1

The formula predicts that languages rank-order by ρ(L) · H(L). Plugging in first-pass values:

| Language | ρ(L) | H_max(L) | ρ·H  | Phase 1 PPL gain |
|----------|------|----------|------|------------------|
| English  | 0.9  | 4.52     | 4.07 | ~1%              |
| Arabic   | 0.6  | 8.08     | 4.85 | 13.9%            |
| Turkish  | 1.0  | 5.98     | 5.98 | 56.9%            |

Ordering by ρ·H: **English < Arabic < Turkish**.
Ordering by PPL gain: **English < Arabic < Turkish**. ✓

The ordinal prediction holds. Magnitude calibration (fitting α) requires more data points or larger-scale runs; left to follow-up.

### 5.4 What the ordinal match does and does not prove

**Does prove:**
- The rebate mechanism exists — morphology-aligned tokenization delivers measurable efficiency gains relative to BPE.
- The gain is ordered by a pre-computable quantity ρ(L) · H(L) derivable from the grammar without reference to any training run.

**Does not prove:**
- The quantitative form ΔN(L) = α · ρ(L) · H(L) is correct (three data points cannot distinguish linear from weakly non-linear fits).
- The inference that α is language-invariant (could vary with typological family, corpus, etc.).
- That the rebate persists at larger scale (the extrapolation to reasoning-capable sizes is a prediction, not a demonstration).

These are stated openly as limitations in §6.

---

## 6. Connection to PPL in Phase 1

### 6.1 Loss-to-parameter-count derivative and the α fit

From the Hoffmann scaling law evaluated at Phase 1's operating point (N = 2 × 10^6, D = 5 × 10^6):

    ∂ℒ / ∂N = −α_N · (ℒ − E) / N

with α_N = 0.34. Given an observed drop in test cross-entropy Δℒ = ℒ_BPE − ℒ_morph, the implied parameter rebate is:

    ΔN(L) ≈ Δℒ · N / (α_N · (ℒ_BPE − E))

Combined with the H(L) and ρ(L) values from `compute_hl.py` (20,000-sentence run), this yields per-language implied α values (in params/bit, under E = 1.7 nats, the Chinchilla-English irreducible-entropy estimate):

| Language | ℒ_BPE | ℒ_morph | Δℒ | ρ · H | ΔN | implied α |
|----------|-------|---------|----|-------|----|-----------|
| English  | 5.803 | 5.792   | 0.0107 | 1.28 | 15,341 | 11,992 |
| Arabic   | 6.413 | 6.263   | 0.1497 | 3.20 | 186,838 | 58,299 |
| Turkish  | 4.187 | 3.344   | 0.8427 | 4.20 | 1,993,509 | 474,322 |

Under Assumption A1 (single cross-lingual α), the three languages should agree on α within noise. They do not: the Turkish-implied α is 40× the English-implied α. An OLS fit through the origin gives α ≈ 304,000 params/bit with residual RMSE ≈ 651,000 — residuals of the same order as the fit itself. The magnitude claim of A1 **fails at Phase 1 scale**.

### 6.2 Honest interpretation

Two non-exclusive readings:

1. **The framework's functional form is non-linear in ρ · H.** The Turkish Δℒ is disproportionately large relative to its ρ · H; a super-linear form (e.g. quadratic, or gated above a threshold) would fit better. Three data points are insufficient to identify the correct non-linearity.

2. **The scaling-law derivative is unreliable at 2M/5M.** Phase 1 trained at ~5M tokens; Chinchilla-optimal for 2M parameters is ~40M tokens. Phase 1 is approximately 8× suboptimal on tokens, placing all three models in the data-starved regime where Hoffmann's coefficients apply only approximately. The implied ΔN values are accurate only to within this distortion.

Both readings converge on the same consequence for the manuscript: **the ordinal claim (§5.3) survives Phase 1 evidence; the magnitude claim (A1 linearity, single α) does not**.

### 6.3 What Phase 1 does and does not establish

**Established (Phase 1, three languages):**
- A parameter-reducing rebate mechanism exists and is measurable.
- The rebate is ordered monotonically by ρ(L) · H(L).
- The ordering matches the framework's ordinal prediction.

**Not established (Phase 1 alone):**
- The functional form of the rebate in ρ · H.
- A single cross-lingual α value.
- Quantitative magnitude of the rebate at any scale above 2M parameters.

### 6.4 What would resolve the magnitude question

Two independent paths, not required for this submission but noted as the natural follow-up:

- **Spectrum expansion.** The six additional engines (de/es/hu/sw/eu/zh) already in the repository span the morphological spectrum; nine data points across the same regime would allow identification of a simple non-linear form if one exists.
- **Scale ladder.** Training each language at the small (20M/100M) and medium (60M/1.2B) scales of the manuscript's Table 2 would place Phase 2 results in a Chinchilla-optimal regime where the scaling-law derivative is trustworthy and α, if constant, can be pinned.

Either path turns the framework from an ordinal predictor into a quantitative one. This manuscript establishes the framework and the ordinal evidence; the quantitative calibration is explicitly scoped to follow-up work.

---

## 7. The capability-vs-scale curve shift

### 7.1 Reframing emergence

Wei et al. (2022) characterised reasoning as an emergent capability appearing around 10^10–10^11 parameters in standard (BPE-trained, English-centric) transformers. Schaeffer et al. (2023) argued that much of what is called "emergence" is a measurement artefact of discontinuous scoring metrics: under continuous scoring, capability typically improves smoothly with scale rather than crossing a sharp threshold.

This framework is neutral between those positions. It does not require a sharp reasoning threshold. It requires only that **the capability-vs-scale curve shifts left** for morphologically rich languages under morphology-aligned tokenization.

### 7.2 The predicted curve shift

Let **N_capability(T, L, tok)** denote the parameter count at which a transformer trained on language L with tokenization regime `tok` reaches capability target T (e.g. a threshold on a multilingual reasoning benchmark such as MGSM, or a target score on a held-out grammatical task).

The framework predicts:

    **N_capability(T, L, morph) = N_capability(T, L, BPE) − α · ρ(L) · H(L)**       [R2]

Equivalently: the capability-vs-scale curve for language L under morphology-aligned tokenization is the BPE curve shifted left by ΔN(L) = α · ρ(L) · H(L) parameters. Whether the curve itself is sharp-stepped (Wei 2022) or smoothly sigmoidal (Schaeffer 2023), the predicted shift has the same form.

### 7.3 The edge-hostability question

Given a target edge profile with parameter budget N_edge (for a contemporary smartphone at 4-bit quantization, N_edge ≈ 5 × 10^8 to 2 × 10^9 params), and a target capability T:

    Edge-hostable capability T in language L is feasible iff N_capability(T, L, morph) ≤ N_edge.

Whether any given (T, L) pair satisfies this is a quantitative question that depends on α, which must be empirically estimated. The framework does not claim edge-hostable reasoning is *demonstrated* — it claims the condition under which it would be *feasible*, and that the condition is more favourable for morphologically rich languages than the English-centric default baseline assumes.

### 7.4 What the framework predicts vs. what it demonstrates

**Predicted:**
- The capability-vs-scale curve shifts left by ΔN(L) ∝ ρ(L) · H(L) under morphology-aligned tokenization.
- Morphologically rich languages cross any fixed capability threshold at smaller parameter counts.
- The feasibility gap for edge-hostable capability is smaller for such languages.

**Demonstrated (at mini scale):**
- The rebate mechanism exists (Phase 1 PPL gradient).
- The rebate is ordered by ρ(L) · H(L) (§5.3).

The gap between the demonstrated mechanism and the predicted edge-hostability claim spans several orders of magnitude of parameter count and is the paper's most ambitious extrapolation. It is framed throughout §7 as a *testable prediction of the framework*, explicitly open to falsification by scaled experiments — which the six additional engines in the repository are ready to support.

---

## 8. Honest limitations (for Discussion §7 of the manuscript)

1. **α constancy**: assumed language-invariant; plausible in principle but only empirically testable across many languages.
2. **ρ(L) estimation**: first-pass values (0.5–1.0) are author judgements informed by the engines. A reproducible ρ metric — e.g. expected mutual information between surface form and feature bundle under a regular decoder — is needed to harden the framework.
3. **Three data points**: the ordinal claim is strong; the magnitude claim is weak. Framework-level, not tokenization-study-level, the paper honestly sits in the former.
4. **Scale extrapolation**: the rebate mechanism is demonstrated at 2M params. Reasoning emerges at 10^10 params. Five orders of magnitude of extrapolation.
5. **Edge profile**: a moving target. 4-bit quantization and other efficiency techniques change N_edge substantially.

---

## 9. What's solid vs what needs work

### Solid

- §1 definitions (SSC, H(L), ρ(L)) — standard information theory, clean.
- §4 explicit-cost calculation — arithmetic, unambiguous.
- §5.3 ordinal validation — Phase 1 data, ordering matches.
- §8 limitations — self-aware.

### Resolved in v2 (2026-04-17)

- **§3.2** — promoted to explicit framework Assumption A1 (dominant-term linearity).
- **§3.3** — replaced author-judgement ρ(L) with the information-theoretic definition ρ(L) = 1 − H(bundle|surface)/H(bundle); computable via `scripts/compute_hl.py`.
- **§5.2** — κ ≈ 2 bits/param anchored to Allen-Zhu & Li (2024); fallback noted.
- **§7** — reframed around capability-vs-scale curve shift; neutral between Wei (2022) sharp-emergence and Schaeffer (2023) smooth-improvement readings.

### Still pending

- Citation verification during Week 1 lit review: Allen-Zhu & Li (κ), Hoffmann/Chinchilla (loss decomposition), Wei/Schaeffer (emergence framing).

### New finding from the α fit (2026-04-17)

- §6.1 α fit run (`scripts/fit_alpha.py`): implied α varies 40× across the three languages under any E choice. A1 linearity fails at Phase 1 scale; the ordinal claim holds. §6.2 documents the two honest readings (non-linear form vs under-trained regime); §6.4 lays out the two follow-up paths that would discriminate between them.

### Dead ends to avoid

- Don't claim the formula matches Phase 1 magnitudes exactly. Ordinal claim only.
- Don't claim α is derivable from first principles. It's empirical.
- Don't claim the edge-reasoning feasibility is demonstrated. It's predicted.

---

## 10. Next concrete actions

1. Write `scripts/compute_hl.py` — compute H_max(L) and corpus-weighted H(L) from each engine; also compute a first-pass ρ(L) as the engine's agreement-prediction accuracy on held-out surface forms.
2. Revisit §3.3 ρ definition once the script output is in hand.
3. Lock citations for κ and N_reason^0 during Week 1 lit review.
4. Compute the §6.1 numerical fit for α; see if it's within an order of magnitude of what §7 requires for edge-reasoning feasibility. This is the single most diagnostic check in the whole derivation.
