# Manuscript Plan — Cambridge NLP Submission

**Target venue:** *Natural Language Processing*, Cambridge University Press (see `PUBLICATION_CHECKLIST.md`).
**Author:** Sameh AbuRadi.
**Supervisor:** Fabian Geier.
**Hard deadline:** Mid-May 2026 (coursework completion).
**Today:** 2026-04-17.
**Timeline:** ~4 working weeks.

---

## 0. Working title (pick one, refine later)

- **The Agglutinative Compounding Effect: When Morphological Structure Rebates Transformer Parameters Faster Than Bits Predict**
- **Grammar Predicts Order, Not Magnitude: A Cross-Disciplinary Framework and an Open Puzzle in Morphology-Aware Language Modelling**
- **When Scaling Laws Meet Morphology: The Case for a Grammatical Correction Term**

---

## 1. The central claim

The paper's central contribution is a two-part finding:

> **(i) Grammar predicts the ordering of the parameter rebate.** A simple information-theoretic measure ρ(L) · H(L), computable from a morphological grammar engine alone, correctly orders the efficiency gain that morphology-aware tokenization produces over a BPE baseline across English, Arabic, and Turkish.
>
> **(ii) Grammar does not predict the magnitude.** Under any reasonable choice of scaling-law parameters, the implied parameter rebate per unit of grammatical information varies by more than an order of magnitude across the three languages. The gain appears to scale *super-linearly* with ρ · H — tentatively named here the **Agglutinative Compounding Effect**.

Two mutually exclusive interpretations are consistent with Phase 1 evidence, and the paper takes no side between them:

- **Interpretation A.** The framework's linear functional form is wrong; the true relationship is super-linear. Morphological structure compounds — more recoverable grammar delivers accelerating, not constant, returns in parameter savings.
- **Interpretation B.** The functional form is linear, but the Hoffmann/Chinchilla scaling law needs a morphological correction term when applied to languages whose information density differs substantially from the English corpora those scaling laws were fit on.

The paper's contribution is therefore cross-disciplinary: information theory (Shannon entropy on grammatical feature space) × typological linguistics (Greenberg's synthesis indices, morphological richness) × transformer scaling laws (Kaplan 2020, Hoffmann/Chinchilla 2022) × edge-ML economics.

The capstone contribution is the **practical math** that makes the prediction quantitative, the small-scale empirical evidence that distinguishes the ordinal from the magnitude claim, and a specific research programme capable of discriminating Interpretation A from Interpretation B.

### 1.1 Edge-hostable reasoning as conditional motivation

Edge-hostable reasoning — reasoning-capable language models that fit under smartphone-class parameter budgets — is the motivation for asking whether grammar is a capacity lever. It is **not** claimed as a result of this paper. It is framed as a conditional: *if the Agglutinative Compounding Effect persists at scale, morphologically rich languages cross the edge-hostable reasoning threshold at parameter counts English does not reach.* Whether that "if" holds is an empirical question the paper's research programme would answer.

---

## 2. What changes from the last plan iteration

| | Previous plan | This plan |
|---|---|---|
| Target metric | PPL improvement gradient | Parameter rebate → edge-hostable capability |
| Scientific object | "Two-factor framework" | Single mathematical object: grammatical entropy H(L) in bits, functioning as a capacity lever |
| Framing | Theoretical extension of a tokenization study | Cross-disciplinary framework spanning linguistics, information theory, ML scaling, and edge-ML economics |
| Empirical role of Phase 1 | Central result | Small-scale proof the rebate mechanism exists and varies by grammar |
| Audience | NLP readers interested in morphology | NLP + Green AI + linguistic equity + edge-ML readers |

The scope (English, Arabic, Turkish) and the 4-week schedule are unchanged. The contract addendum (`experimental_contract_addendum.md`) still covers this framing — the "pre-training predictive framework" it permits is exactly what this plan formalises.

---

## 3. The practical math — what needs to be worked out

### 3.1 The object of measurement

**Structural Synthesis Ceiling (SSC)**, building on Greenberg's Index of Synthesis. Formally:

- Let B(L) be the set of distinct grammatical feature bundles a language's morphology can simultaneously encode on a single word form, after accounting for syncretism, defectiveness, and paradigm gaps.
- The **information content** a word form can carry, in bits:
  - Upper bound: **H(L) = log₂ |B(L)|**
  - Realised (corpus-weighted): **H(L) = −Σ p(b) log₂ p(b)** over b ∈ B(L)

One number per language. All other candidate factors (bundle cardinality, slot count, fusion, paradigm density) are absorbed into B(L) or its distribution.

Phase 1 engine outputs give first-pass upper bounds:
- English: log₂ 23 ≈ 4.5 bits/word
- Turkish: log₂ 63 ≈ 6.0 bits/word
- Arabic: log₂ 270 ≈ 8.1 bits/word

### 3.2 The bridge — H(L) to parameter rebate

This is the section that needs to be *constructed*, not just reported. It's the hardest and most novel part. Working sketch:

A transformer of N parameters trained on D tokens has some total learned capacity, roughly C_total(N, D) bits (see Kaplan 2020, Hoffmann 2022 for the empirical shape). Some fraction of that capacity is spent re-learning grammatical regularities that were discarded by byte-pair tokenization. Call this the **implicit grammar cost**:

**C_grammar(L, BPE) ≈ H(L) · D · k** bits — k the per-token cost of reconstructing grammar from distribution.

When tokenization is morphology-aligned, H(L) is delivered to the model as explicit structure at input, and the implicit grammar cost collapses to the size of the bundle embedding table, which is tiny:

**C_grammar(L, morph) ≈ |B(L)| · d_emb** bits — a few KB, not GB.

The **parameter rebate** for language L:

**ΔN(L) ∝ H(L)** (with a fitting constant α to be derived from scaling-law coefficients and validated against the Phase 1 gradient)

This is the target formula. It needs to:
- Be dimensionally honest.
- Connect to published scaling-law coefficients so reviewers can follow the derivation.
- Predict the Phase 1 ordering (Turkish > Arabic > English in efficiency gain) when combined with the observation that Turkish has the highest H(L) among fully-concatenative (structurally recoverable) grammars — Arabic's templatic fusion hides some bits, which the formula must account for.

### 3.3 The edge-hostability test

Let N_edge be the maximum parameter count that fits the target edge profile (say, 4GB phone RAM → ~500M params at 4-bit quantization). Let N_reason be the minimum parameter count at which reasoning-capable behaviour emerges in standard training (current evidence: ~7B for English; Wei 2022, Schaeffer 2023).

**Edge-hostable reasoning is feasible for language L if: N_reason − ΔN(L) ≤ N_edge.**

The paper's quantitative prediction is that this inequality holds for Turkish and Arabic at plausible α, and does not hold for English — explaining *why* edge-deployable reasoning has been harder for English and offering a concrete path for morphologically rich languages.

---

## 4. Manuscript structure (Cambridge NLP Article)

Target: **8,000–10,000 words** body (confirm via the email to `NLP@cambridge.org`). LaTeX via Cambridge Overleaf template. Author-Date citations.

### Section outline

1. **Abstract** (~300 words) — lead with the puzzle: ordinal prediction confirmed, magnitude diverges 40× across three languages, the named **Agglutinative Compounding Effect**, the two interpretations, edge-hostable reasoning as conditional motivation.

2. **Introduction** (~900 words)
   - The reasoning / edge-deployment tension: reasoning emerges at 10^10+ params; edge budgets cap well below that.
   - The unexamined assumption: ML cost is implicitly language-neutral; scaling laws are fit to English-centric corpora.
   - The question: is grammar a capacity lever?
   - Two-part contribution preview: (i) a grammar-only predictive framework that orders three languages correctly; (ii) a magnitude divergence that names a phenomenon and opens a puzzle.
   - Edge-hostable reasoning flagged explicitly as *conditional motivation*, not a result of this paper.

3. **Related Work** (~900 words) — *five neighbourhoods, tightly cited*
   - Morphological typology (Greenberg 1960; Comrie 1989; Haspelmath & Sims 2010).
   - Tokenization and morphology in NLP (Kudo & Richardson 2018; morpheme-aware tokenizers).
   - Transformer scaling laws (Kaplan 2020; Hoffmann/Chinchilla 2022; Allen-Zhu & Li 2024).
   - Emergence framing (Wei 2022; Schaeffer 2023).
   - Green AI, linguistic equity, edge ML (Schwartz 2020; Strubell 2019; Ahia 2023; Bender 2021).

4. **Framework** (~1,800 words) — *the scaffolding for §6*
   - 4.1 Structural Synthesis Ceiling — definition, relationship to Greenberg's Index of Synthesis, computation from a grammar engine.
   - 4.2 Grammatical information content H(L) in bits — upper bound and corpus-weighted.
   - 4.3 Structural recoverability ρ(L) — information-theoretic definition via H(bundle | signature).
   - 4.4 Implicit grammar cost under BPE (Assumption A1, dominant-term linearity).
   - 4.5 The parameter rebate ΔN(L) = α · ρ(L) · H(L) and the capability-vs-scale curve shift; the quantitative prediction the framework makes.

5. **Case studies** (~1,800 words)
   - 5.1 English (analytic) — low H(L) ≈ 1.43 bits, ρ ≈ 0.89; smallest ρ · H.
   - 5.2 Arabic (templatic) — large |B(L)| but ρ ≈ 0.59 from templatic fusion; middle ρ · H.
   - 5.3 Turkish (agglutinative) — moderate |B(L)|, ρ ≈ 0.85; largest ρ · H and the disproportionate rebate that motivates §6.
   - Each ends with worked examples from the engine and the corresponding bit count.

6. **Empirical Results — the Agglutinative Compounding Effect** (~1,500 words) — *the headline finding*
   - 6.1 Phase 1 design and metrics (six models, 2M params, 5M tokens, identical architecture, tokenization as the only variable).
   - 6.2 Ordinal validation: Phase 1 Δℒ is monotonically ordered by ρ · H. Framework prediction confirmed.
   - 6.3 Magnitude analysis: the implied α from the Hoffmann scaling-law derivative varies by 40× across languages under any reasonable E choice. Linear form [R1] fails.
   - 6.4 Naming the phenomenon — the **Agglutinative Compounding Effect** — the tendency of structurally-recoverable grammar to deliver disproportionately large parameter savings.
   - 6.5 The two interpretations (A: framework non-linearity; B: scaling-law correction term for morphology) and the evidence that would discriminate between them.

7. **Discussion** (~900 words)
   - If Interpretation A holds: morphology is a compounding capacity lever; edge-hostable reasoning plausibly feasible in morphologically rich languages at parameter counts English does not reach.
   - If Interpretation B holds: transformer scaling laws need a morphological correction term; low-resource NLP cost estimates are systematically mis-priced.
   - Either resolution reshapes ML-economics intuition: language structure is a quantitative input to cost planning, not a soft typological variable.
   - Limitations: three data points, mini scale, author-native language bias, ρ signature-proxy coarseness, E sensitivity in the scaling-law derivative.
   - Threats to validity.

8. **Conclusion and Research Programme** (~500 words)
   - Framework and ordinal result and the named phenomenon — these are the contribution.
   - Research programme: the six additional engines (de/es/hu/sw/eu/zh) already in the repository; a scale ladder through small (20M/100M) and medium (60M/1.2B) regimes — sufficient to discriminate Interpretation A from B.

9. **References** (Author-Date, Cambridge style).

10. **Appendices** — A. Phase 1 raw results. B. Engine highlights per language. C. H(L) and ρ(L) computation details. D. α-fit sensitivity analysis (E, scaling-law parameters).

---

## 5. Week-by-week schedule (unchanged from previous iteration, refocused content)

**Assumption:** full-time focus; buffer for supervisor feedback.

### Week 1 — 2026-04-18 to 2026-04-24 — Framework and the bridge math

- [ ] Confirm contract addendum with Fabian (existing `experimental_contract_addendum.md` still applies).
- [ ] Literature deep-dive: Greenberg 1960, Kaplan 2020, Hoffmann 2022, Schwartz 2020, Ahia 2023, Wei 2022.
- [ ] Formalise H(L) and the implicit-grammar-cost argument (§3 above); derive ΔN(L) ∝ H(L) with honest scaling-law coefficients.
- [ ] Compute H(L) upper bound and corpus-weighted value per engine; tabulate.
- [ ] Write §4 Framework draft (the hardest section — do it first).

### Week 2 — 2026-04-25 to 2026-05-01 — Case studies

- [ ] §5.1 English — low H(L), small rebate, anchors the baseline.
- [ ] §5.2 Arabic — templatic; the interesting case where raw H(L) overstates the rebate because fusion hides bits.
- [ ] §5.3 Turkish — agglutinative; the paper's strongest demonstration.
- [ ] Each ends with engine-derived worked examples and bit counts.

### Week 3 — 2026-05-02 to 2026-05-08 — Empirical, Intro, Related Work

- [ ] §6 Empirical validation — Phase 1 numbers reinterpreted through the rebate lens.
- [ ] §2 Introduction and §3 Related Work.
- [ ] Edge-hostability inequality worked out with plausible N_edge and N_reason values.
- [ ] First complete draft end of week; send to Fabian.
- [ ] Email `NLP@cambridge.org` on the four open checklist questions.

### Week 4 — 2026-05-09 to 2026-05-15 — Polish, Discussion, format

- [ ] §7 Discussion — tie the math to Green AI, linguistic equity, edge ML.
- [ ] §8 Conclusion and research programme.
- [ ] §1 Abstract (write last).
- [ ] LaTeX formatting in Cambridge Overleaf template; Author-Date bibliography.
- [ ] Integrate Fabian's feedback.
- [ ] AI use disclosure, competing interests, ORCID.
- [ ] Figures + alt-text; tables sized for 247 × 174 mm.

### Buffer — 2026-05-16 onwards

- Last-round supervisor comments, final proofread, ScholarOne submission prep.

---

## 6. Dependencies and open questions

- **Blocking:** Contract addendum sign-off (Fabian).
- **Blocking:** Fabian's answer on DEAL / institutional APC coverage.
- **Blocking:** The bridge math (§3.2) needs to hold up to review. If the scaling-law coefficient derivation turns out thinner than hoped, fall back to: *"The rebate is ordinally predicted by H(L); full magnitude calibration left to follow-up work at larger scale."*
- **Non-blocking:** Decide whether to use the upper-bound H(L) = log₂|B(L)| or the corpus-weighted entropy. Recommendation: report both; use the latter in the formula, the former for the Structural Synthesis Ceiling definition.

---

## 7. Artifacts to produce (ordered)

1. `experimental_contract_addendum.md` — already drafted; needs signature.
2. `scripts/compute_hl.py` — computes H(L) per engine, upper bound and corpus-weighted.
3. `manuscript/` directory — LaTeX source, figures, bibliography.
4. Revised `report.html` — pruned back from 9-language framing to 3 to match the manuscript scope.
5. Updated `PUBLICATION_CHECKLIST.md` — reflect the scaled-down scope and the new framing.

---

## 8. Risks and how to manage them

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Reviewers reject the edge-reasoning claim on 2M-parameter evidence. | Major. | Frame the edge-reasoning case as a *quantitative prediction* of the framework, not a demonstrated capability. The demonstrated thing is the rebate mechanism; reasoning is the implication. |
| Bridge math (§3.2) is under-derived or hand-wavy. | Major. | Spend Week 1 on this; if it doesn't hold, retreat to an ordinal claim (rebate ordering, not magnitude) — still publishable. |
| "Structural Synthesis Ceiling" dismissed as rebranded Greenberg. | Moderate. | §4.1 explicitly positions SSC as a structural upper bound, contrasted with Greenberg's corpus-averaged index; lineage is cited, differentiation is one clean paragraph. |
| Three data points too thin for a theoretical claim. | Moderate. | Position as framework + small validation + research programme; cite the six additional engines ready for follow-up. |
| Cross-disciplinary framing (linguistics + info theory + scaling laws + edge ML) too sprawling for reviewers. | Moderate. | Tight Related Work (§3) with four clearly demarcated neighbourhoods; one paragraph each; no dangling side arguments. |
| Timeline slips past mid-May. | Capstone fails. | Strict weekly milestones. If Week 1 slips, §4.5 edge-hostability section is cut first; §6 is cut second. §4 Framework, §5 Case Studies, and §6 Empirical are not negotiable. |

---

## 9. Out of scope for this submission

- Running experiments at scales where reasoning emerges (7B+). Cited as research programme only.
- Mandarin/German/Spanish/Hungarian/Swahili/Basque engines. Retained in the repo; cited as future validation targets.
- Quantization / inference-engine engineering for actual edge deployment. Framework only.
- Downstream task evaluation — consistent with the parent contract.

---

## 10. First three concrete actions

1. Get Fabian's signature on the existing contract addendum (the framing it permits is what this plan formalises).
2. Start §4.2 bridge math — work out the scaling-law connection that turns H(L) into ΔN(L). This is the keystone; the rest of the paper rests on it.
3. Write `scripts/compute_hl.py` — H(L) upper bound and corpus-weighted entropy per engine. Produces the numbers Week 1 needs.

Tell me which to start with.
