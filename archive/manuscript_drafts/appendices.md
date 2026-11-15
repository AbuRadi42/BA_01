# Appendices

**Status:** Manuscript-prose draft v1. Four appendices (A–D) in one file for convenience; will split into separate sections in LaTeX.

---

## Appendix A — Phase 1 raw results

Phase 1 trained six decoder-only transformer models — English, Arabic, and Turkish, each under byte-pair and morphology-aligned tokenization — under identical architecture (4 layers, 128-dimensional embeddings, 4 attention heads, 128-token context), training budget (5 × 10^6 tokens per model, AdamW, cosine learning-rate schedule with 200-step warmup), and data source (wikimedia/wikipedia dumps sampled per language). Resulting parameter counts are approximately 2 × 10^6 per model. The morphology-aligned variants receive an additional bundle-embedding table summed into the input representation; its capacity cost is of order 10 megabytes, three to four orders below the model itself, and is treated as negligible in §4.4.

**Table A.1.** Phase 1 test results on held-out validation corpora. *Δ-PPL %* is the fractional perplexity reduction of the morph model relative to its baseline.

| Language | Regime   | Test loss (nats) | Test PPL | Tokens | TPMU  | Unk rate | Bundle accuracy | Δ-PPL % |
|----------|----------|-----------------:|---------:|-------:|------:|---------:|----------------:|--------:|
| English  | baseline | 5.8029 | 331.27  | 318,976 | —     | —       | —      | —      |
| English  | morph    | 5.7922 | 327.72  | 190,976 | 14.59 | 10.68 % | 45.91 %| 1.07 %  |
| Arabic   | baseline | 6.4131 | 609.78  | 418,944 | —     | —       | —      | —      |
| Arabic   | morph    | 6.2634 | 525.03  | 244,992 | 12.46 | 19.09 % | 9.28 % | 13.90 % |
| Turkish  | baseline | 4.1866 |  65.80  | 101,888 | —     | —       | —      | —      |
| Turkish  | morph    | 3.3439 |  28.33  |  60,800 | 12.21 | 15.78 % | 43.92 %| 56.94 % |

The unknown-token rate on the morph models reflects a vocabulary cap applied during training and is discussed as a known bias in §7.4 (limitations). Test-loss Δ is the primary quantity used in §6's magnitude analysis; it is not affected by the vocabulary cap in the same direction as perplexity.

---

## Appendix B — Engine highlights per language

Each language's grammar engine decomposes a surface word form into a `(root, feature-bundle)` pair by applying rules specific to the language's morphological type. All three engines share a common `TokenInfo` interface defined in `scripts/engines/shared.py`. Engines are fully deterministic over their input.

**Table B.1.** Engine size and scope for the three languages tested in Phase 1.

| Language | Engine module | Lines of Python | Feature-bundle inventory size \|B(L)\| | Test suites (categories) |
|----------|---------------|----------------:|---------------------------------------:|--------------------------|
| English  | `en_engine.py` | 256  |  23 | smoke, inflection, derivation, sentence, regression, stress, adversarial |
| Arabic   | `ar_engine.py` | 1,906 | 270 | smoke, templates, particles, sentence, regression, adversarial, fixes |
| Turkish  | `tr_engine.py` | 592  |  63 | smoke, nominal, verbal, particles, sentence, stress, adversarial |

Test suites across the three engines total several hundred unit cases at the time of Phase 1; all pass on the engine versions used for the analyses of §5 and §6.

**Design highlights.**

- **English engine.** Three-step analysis: inflectional stripping against a standard English inflection inventory (plural `-s`, past `-ed`, progressive `-ing`, comparatives, superlatives, possessive `'s`), derivational pattern detection against a curated affix table, and stem identification on the residue. Irregular forms (suppletive verbs, mutated nouns) resolved through a lookup table (`en_irregulars.json`). Closed-class lexicon for determiners, prepositions, pronouns, and auxiliaries.

- **Arabic engine.** Root-and-pattern decomposition: triconsonantal (and occasionally quadriconsonantal) root extraction, pattern (*wazn*) identification against a template inventory of approximately thirty categorical classes, and feature-bundle assignment parameterised by the pattern. Handles concatenative affixation (definite article *al-*, person/number/gender markers, case markers) alongside the non-concatenative root-pattern interleaving. Draws on the Buckwalter morphological transliteration standard for surface normalisation.

- **Turkish engine.** Suffix-chain parsing against a slot-ordered grammar. Nominal and verbal paradigms each exposed as ordered sequences of grammatical slots (number, possession, case for nouns; voice, tense/aspect/mood, person for verbs). Vowel-harmony variants of each suffix normalised to a single grammatical tag at feature-bundle assignment time. Derivational suffixes handled explicitly, producing a derived-chain annotation on the root.

Complete engine specifications — including feature-bundle registries, test fixtures, and design notes — are held in the project repository at `docs/engine_specs/` and are reproducible without reference to any training artefact.

---

## Appendix C — Computation of H(L) and ρ(L)

The grammatical information content H(L) and the structural recoverability coefficient ρ(L) are computed by the script `scripts/compute_hl.py`, which streams a per-language text corpus through the corresponding grammar engine, records `(surface, bundle)` pairs for each analysable word form, and produces Shannon entropies from the resulting empirical distributions. Results are written to `manuscript/hl_metrics.json`.

**C.1 Algorithm.** For each language L:

1. Stream words from a line-per-sentence text file up to a configurable sentence budget.
2. For each word, apply `engine.analyze()` to obtain a `TokenInfo`; skip on exception.
3. Record the grammatical bundle `info.feature_bundle_str()` and a surface signature (defined below).
4. Build three Counters: `bundles` (marginal distribution over bundles), `by_surface` (bundle distribution per surface), `by_signature` (bundle distribution per signature).
5. Compute H_max(L) = log₂ |B_observed(L)|, H(L) = Shannon entropy of `bundles`, H(b | surface) = expected conditional entropy over `by_surface`, H(b | signature) over `by_signature`.
6. Derive ρ_surface = 1 − H(b | surface) / H(L) and ρ_signature = 1 − H(b | signature) / H(L). ρ_surface is reported for auditability; it is degenerate (=1) because engines are deterministic over their input. ρ_signature is the working measurement.

**C.2 Surface signature by language.**

- **English, Turkish (concatenative).** Signature = surface string with the identified root substring replaced by a single placeholder. If the root is not a substring of the surface (e.g. suppletive forms), the full surface is used.
- **Arabic (templatic).** Signature = the engine's categorical `template` field (e.g. `VERB_TRILATERAL_BARE`, `NOM_DERIVED`). If the template is empty, the fallback is the surface with root consonants masked.

The signature is intended to simulate what a regular surface-only parser without lexicon access would see: it preserves the grammatically-visible structure of the word form while abstracting away lexical identity.

**C.3 Sample-stability check.** Running at 5,000 and 20,000 sentences per language (`--max-sentences 5000` and default):

| Language | Sample | Tokens | \|B\| observed | H | H(b | sig) | ρ_sig | ρ·H |
|----------|-------:|-------:|--------------:|---:|-----------:|------:|----:|
| English  | 5k     | 248,891 |    22 | 1.45 | 0.16 | 0.889 | 1.29 |
| English  | 20k    | 985,492 |    22 | 1.43 | 0.16 | 0.892 | 1.28 |
| Arabic   | 5k     | 239,289 |   548 | 5.45 | 2.22 | 0.592 | 3.23 |
| Arabic   | 20k    | 901,068 |   697 | 5.44 | 2.23 | 0.589 | 3.20 |
| Turkish  | 5k     | 187,934 | 1,254 | 5.16 | 0.79 | 0.847 | 4.37 |
| Turkish  | 20k    | 573,281 | 1,837 | 4.97 | 0.77 | 0.846 | 4.20 |

All entropies and the ρ·H products stabilise by the fourth significant figure at the 20k-sentence scale. The ordinal relationship exploited in §6.2 — ρ·H(EN) < ρ·H(AR) < ρ·H(TR) — is preserved at both sample sizes.

**C.4 Caveats.** ρ(L) as computed here depends on the engine's signature derivation. A more principled estimator — for instance, mutual information between surface affix n-grams and grammatical bundles under a lexicon-free regular decoder — would reduce engine-dependence and is scoped as follow-up work in §8.

---

## Appendix D — α-fit sensitivity analysis

The per-language coefficient α of equation (4.7) is estimated by converting each observed Phase 1 test-loss reduction Δℒ into an implied parameter rebate ΔN via the Hoffmann scaling-law derivative:

    ΔN(L) = Δℒ · N / [α_N · (ℒ_BPE − E)],

with N = 2 × 10^6, α_N = 0.34, and Δℒ the observed difference between BPE and morph test losses in nats. The implied α(L) = ΔN(L) / [ρ(L) · H(L)] is then a per-language quantity which Assumption A1 predicts should be constant across L.

The irreducible entropy floor E is not directly measured by the six Phase 1 runs. We report under three values covering the plausible range:

- **E₀ = 0.** A crude lower bound; treats the entire cross-entropy as reducible loss.
- **E_Chinchilla = 1.7 nats.** The conventional Chinchilla-era estimate for English.
- **E_local = ℒ_BPE − 1.** A language-specific floor that pins the denominator at 1 nat; a stress test of derivative sensitivity.

**Table D.1.** Per-language implied α (parameters per bit of ρ·H) under each E.

| Language | ℒ_BPE | ℒ_morph | Δℒ | ρ·H | ΔN(E₀) | ΔN(E_Chn) | α(E₀) | α(E_Chn) | α(E_local) |
|----------|------:|--------:|----:|----:|-------:|----------:|------:|---------:|-----------:|
| English  | 5.803 | 5.792 | 0.0107 | 1.28 | 10,847 | 15,341 | 8,479 | 11,992 | 49,201 |
| Arabic   | 6.413 | 6.263 | 0.1497 | 3.20 | 137,311 | 186,838 | 42,845 | 58,299 | 331,692 |
| Turkish  | 4.187 | 3.344 | 0.8427 | 4.20 | 1,184,030 | 1,993,509 | 281,720 | 474,322 | 1,179,450 |

**Table D.2.** Dispersion of implied α across languages, by E.

| E choice     | min α  | max α     | spread (max/min) |
|--------------|-------:|----------:|-----------------:|
| E₀           |  8,479 |   281,720 | 33.2× |
| E_Chinchilla | 11,992 |   474,322 | 39.6× |
| E_local      | 49,201 | 1,179,450 | 24.0× |

**Table D.3.** Ordinary-least-squares fit of ΔN = α · ρ · H through the origin on the three data points.

| E choice     | OLS α   | Residual RMSE |
|--------------|--------:|--------------:|
| E₀           | 183,632 |       375,826 |
| E_Chinchilla | 304,242 |       651,155 |
| E_local      | 802,683 |     1,449,020 |

The residual RMSE is approximately twice the OLS α itself under every E choice — an indication that no single α value fits the three languages jointly within noise. The spread and shape of the deviation (implied α rising monotonically with ρ·H itself) is the empirical content of the Agglutinative Compounding Effect named in §6.4; the robustness of that pattern under the three E values is the principal evidence that the effect is not an artefact of a particular entropy-floor estimate.
