# 7. Discussion

**Status:** Manuscript-prose draft v1. Target length ≈ 900 words.

---

The Agglutinative Compounding Effect, as §6 characterises it, is a three-point observation. Its durability is an empirical question the current study cannot settle. What can be discussed now is the structure of its consequences — how each of the two interpretations introduced in §6.5 would reshape the way the field thinks about ML cost across languages — and the limitations that bound the confidence we can place in the observation itself.

## 7.1 Consequences under Interpretation A

Interpretation A holds that the super-linearity in ρ · H is genuine. Under this reading, morphology-aware tokenization is not a constant-rate efficiency instrument but a compounding one: each additional bit of structurally recoverable grammar buys increasing returns in the parameter count a transformer requires to reach a given capability. The practical implications fall in three areas.

First, **edge deployment for morphologically rich languages** becomes a more plausible near-term prospect than linear readings of equation (4.7) suggest. The capability-vs-scale curve shift of equation (4.8), if it compounds with ρ · H, places the edge-hostability condition (4.9) within reach for agglutinative and highly-synthetic languages at parameter counts well below the English reasoning-emergence threshold. The framework does not demonstrate that reasoning-capable Turkish or Finnish or Quechua models will fit smartphone memory budgets in 2027; it provides the quantitative condition under which they would, and Phase 1's super-linear shape makes the condition easier to satisfy.

Second, **low-resource language modelling** receives a conceptual inversion. The dominant framing treats low-resource languages as a cost problem: data is scarce, compute per language is expensive, and equity arguments turn on redistributing centrally-trained models. Under Interpretation A, some low-resource languages — those whose morphology is both information-dense and structurally recoverable — may be *cheaper* to model to a given capability than English, provided tokenization is aligned to their structure. Equity recommendations would shift correspondingly: from "subsidise training on English-shaped pipelines" to "build grammar-aligned pipelines per typological family."

Third, **Green AI cost accounting** (Schwartz et al. 2020; Strubell et al. 2019) acquires a linguistic axis. A compute budget denominated in FLOPs per capability translates differently into each language under the framework, and Interpretation A amplifies the differences. Reports that account for environmental cost of model training in a language-agnostic way understate gains available from structure-aware tokenization in high-ρ · H languages.

## 7.2 Consequences under Interpretation B

Interpretation B holds that the framework's linear form is fine but the scaling-law derivative used to translate observed Δℒ into implied ΔN is unreliable in Phase 1's data-starved regime. Under this reading, the Agglutinative Compounding Effect dissolves at Chinchilla-optimal training; Assumption A1 becomes defensible; α becomes language-invariant; and the per-bit rebate the framework predicts is a single cross-lingual constant.

This reading is less rhetorically striking but carries its own substantial implication. If Interpretation B is correct, then **the Hoffmann/Chinchilla scaling laws, fit to English-centric corpora, systematically distort cost estimates for other languages in proportion to their typological distance from English.** A morphological correction term — effectively an additional coefficient in equation (4.6) that depends on ρ · H — would be required before the laws could be applied to multilingual training budget planning. Much of the cited scaling literature implicitly treats cross-lingual generalisation as a secondary question; Interpretation B reframes it as a first-order one. Downstream work that estimates the cost of multilingual foundation models would need to revise upward or downward, language by language, from the Hoffmann baseline.

## 7.3 What both interpretations share

Both interpretations share a structural commitment: **language is a quantitative input to ML-economics planning**, not a soft typological variable mentioned in passing. The framework makes H(L) and ρ(L) computable from a grammar engine that exists independently of any training run; downstream cost calculations that ignore them accept a systematic error whose size depends on which interpretation holds. The paper's contribution is not to choose between A and B but to demonstrate that the choice matters and to specify the experiments that would force it.

## 7.4 Limitations

Four limitations bound the confidence the framework warrants at present.

**Three data points.** Phase 1 observes the framework's prediction in English, Arabic, and Turkish — languages spanning analytic, templatic, and agglutinative typology. The ordinal result is robust under this thin evidence base, but functional-form questions (linear? quadratic? threshold-gated?) require more points. §8 scopes the programme that would supply them.

**Phase 1's Chinchilla-suboptimal regime.** All six models are trained at approximately eight-times-suboptimal token-to-parameter ratios. This is the direct source of Interpretation B's plausibility and cannot be resolved within the current experiment.

**Author-native language bias.** The three languages tested are the three the author speaks natively. Engine quality, example selection, and the coarseness of ρ estimation are all likely to reflect this familiarity. The six additional engines in the repository (German, Spanish, Hungarian, Mandarin, Swahili, Basque) are the primary mitigation, but until they are applied, the author-native effect is a real confound.

**ρ as signature proxy.** The structural recoverability coefficient as computed in §4.3 conditions on a signature derived from the engine's own template or root-stripped surface. A more principled estimator — for instance, lexicon-free mutual information between surface affix n-grams and grammatical bundles — would reduce the engine-dependence of ρ and is left to follow-up.

**Semantic storage outside ρ's scope.** The structural recoverability coefficient ρ(L) measures what a surface-only parser can recover, but morphology encodes grammatical information along two axes the framework conflates. The first is the *surface-recoverable* axis ρ captures: how much of B(L) a regular algorithm can decode from the surface string alone. The second is a *lexicon-recoverable* axis: how much additional information becomes recoverable when the parser has access to root meanings and a morphological analyser. For concatenative languages (English, Turkish) these axes nearly coincide, since surface affixation and lexical root largely preserve each other's boundaries. For templatic languages like Arabic they diverge substantially: Arabic's 270-bundle structural space encodes rich semantic and grammatical information per word form, but the non-concatenative fusion that enables this density also makes most of it inaccessible without lexical context. Our framework rewards Arabic for the bits that survive ρ's filter (ρ(Arabic) ≈ 0.59); it does not credit the bits Arabic stores behind that filter, nor the semantic-neighborhood relationships that root-sharing creates across the Arabic lexicon (the *k-t-b* family of writing-related words, the *s-l-m* family of peace- and submission-related words, and so on). A richer decomposition of ρ·H into surface-recoverable and lexicon-recoverable components is a natural extension. It would let the framework differentiate between *morphology a transformer exploits* and *morphology a morphological analyser (or a human reader) exploits*, and would give templatic languages back the credit our current ρ quietly refuses them. §8 scopes a two-tier experiment that would quantify this second axis empirically.

## 7.5 Threats to validity

The principal threat is that the observed Agglutinative Compounding Effect is an artefact of Phase 1's specific training configuration — a 4-layer, 128-dimension, 5M-token run — rather than a property of morphology-aware language modelling more broadly. The two discriminating experiments of §6.5 would expose this if true: replication at smaller training scales across more languages, or at larger scales on the same languages, would either preserve the super-linearity (supporting Interpretation A) or compress it (supporting Interpretation B) or eliminate it entirely (falsifying the framework). Until those experiments are run, the named phenomenon is a hypothesis with empirical support, not a confirmed regularity.

A secondary threat concerns the engines themselves. The decomposition quality of the Arabic engine for nominal forms is imperfect (Form II masdars and *nisba* adjectives are occasionally misclassified), and the Turkish engine's handling of some derivational homographies is conservative. Neither gap is large enough to flip the ordering of ρ · H across the three languages, but both contribute noise to the conditional-entropy estimates. §8 includes engine refinement in the research programme.
