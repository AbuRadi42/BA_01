# 4. Framework

**Status:** Manuscript-prose draft v1. Converts the derivation notes in `framework_math.md` into publication-grade text. Target length ≈ 1,800 words. Section numbers align with the manuscript outline in `MANUSCRIPT_PLAN.md`.

---

This section develops a framework for predicting, from a language's grammar alone, the degree to which morphology-aware tokenization reduces the parameter count a transformer requires to reach a fixed capability threshold. The framework is built in five moves. §4.1 defines the **Structural Synthesis Ceiling**, a structural upper bound on the grammatical information a single word form can encode, and distinguishes it from Joseph Greenberg's corpus-averaged Index of Synthesis. §4.2 gives the information-theoretic quantity H(L) — the grammatical Shannon entropy per word form. §4.3 introduces the **structural recoverability coefficient** ρ(L), which measures how much of H(L) is accessible to a regular surface-only parser. §4.4 states the assumption (A1) that links grammatical information to model capacity and frames the *implicit grammar cost* a BPE-tokenized transformer must pay. §4.5 combines these into a closed-form prediction for the **parameter rebate** ΔN(L) that morphology-aligned tokenization delivers relative to BPE, and articulates the corresponding **capability-vs-scale curve shift**. The empirical status of this prediction — ordinal confirmation, magnitude divergence — is the subject of §6.

## 4.1 The Structural Synthesis Ceiling

Consider a language L whose morphology realises grammatical features on word forms through any combination of inflection, derivation, affixation, and non-concatenative processes. For each grammatical category C encoded in L's morphology (tense, aspect, mood, person, number, gender, case, definiteness, possession, polarity, and so on — the inventory varies by language), let V(C) be the set of values that category admits. Let **B(L)** be the set of distinct grammatical feature bundles that L's morphology can simultaneously realise on a single word form, after accounting for syncretism, defectiveness, and paradigm gaps. B(L) is, in effect, the realised subset of the Cartesian product ∏_C V(C) — the structural "address space" of a word form in L.

We define the **Structural Synthesis Ceiling** (SSC) of L as the cardinality of B(L), and its logarithm in bits:

    SSC(L) = |B(L)|,    H_max(L) = log₂ |B(L)|.                (4.1)

H_max(L) is the maximum grammatical information, in bits, a single word form can encode — independent of any corpus, tokenizer, or training run. It is derivable from a language's grammar description alone, and in our implementation is enumerated directly from the feature-bundle registry of each language's grammar engine.

SSC sits within a lineage of typological indices but differs from the best-known prior art. Greenberg (1960) defined the **Index of Synthesis** as the average number of morphemes per word, computed over a corpus. The Index of Synthesis is a *descriptive* typological measure: it tells us how many morphemes are strung together in a representative sample of text. SSC is instead a *structural upper bound*: it tells us how many distinct grammatical specifications the morphology can in principle express on one word, regardless of how frequently each is realised in practice. The Index of Synthesis is empirical and averaged; SSC is combinatorial and peaked. For our purposes — predicting the amount of grammatical information a tokenizer can pre-encode — the structural ceiling is the relevant quantity.

For the three languages this paper tests, SSC spans the morphological typology we set out to cover. English, an analytic language whose grammar is carried largely by word order, has |B(L)| = 23 (H_max ≈ 4.52 bits). Turkish, an agglutinative language whose word forms stack suffixes in a strict slot order, has |B(L)| = 63 (H_max ≈ 5.98 bits). Arabic, a root-and-pattern templatic language whose grammar arises from the interleaving of triconsonantal roots with vowel patterns (**أوزان**, *awzān*), has |B(L)| = 270 (H_max ≈ 8.08 bits) — more than four times Turkish's structural bundle space despite Turkish's combinatorially-spread agglutinative slot system.

A clarification on terminology. |B(L)| throughout this paper denotes the *structural* bundle-space size as enumerated by the grammar engine's feature-bundle registry — the number of distinct grammatical specifications the morphology can in principle realise on a single word form. This is a property of the grammar, not of any corpus. The empirical-distribution support size (the number of distinct `feature_bundle_str()` outputs observed in a given corpus sample) can deviate from |B(L)| in both directions: Arabic's 270 structural bundles surface as roughly 697 distinct strings in a 20,000-sentence Wikipedia sample because the engine serialises tag combinations as distinct strings, while Turkish's 63 structural bundles expand to roughly 1,837 observed strings through the combinatorial spread of slot values. These observed counts enter the H(L) computation in §4.2 — which is distribution-weighted and invariant to such expansion — but the canonical framework quantities remain the structural |B(L)| and its logarithm H_max(L).

## 4.2 Grammatical information content H(L)

H_max(L) is an upper bound. The realised grammatical information content of an average word form depends on how bundles are distributed in naturally occurring text. Let p(b) denote the empirical probability, over a corpus of L, that a given word form carries feature bundle b ∈ B(L). The **grammatical information content** of L, in bits per word form, is the Shannon entropy over this distribution:

    H(L) = − Σ_{b ∈ B(L)} p(b) log₂ p(b).                     (4.2)

H(L) ≤ H_max(L), with equality iff every bundle is equiprobable. In practice, the realised distribution is highly skewed — a few common bundles (third-person singular present in English; nominative singular in Turkish; Form I active perfective in Arabic) dominate, and H(L) falls well below the ceiling. On our 20,000-sentence Wikipedia samples we observe H(L) = 1.43 bits for English, 4.97 bits for Turkish, and 5.44 bits for Arabic.

The ordering of H(L) — English ≪ Turkish ≈ Arabic — already departs from what the SSC alone would predict. Arabic's ceiling is 35 percent higher than Turkish's in bits, but the corpus-weighted entropies are nearly equal. The difference is absorbed by the structural recoverability coefficient introduced next.

## 4.3 Structural recoverability ρ(L)

H(L) quantifies the grammatical information a word form carries. It does not quantify how much of that information is accessible to a surface-only parser — a parser that sees the word's surface string and nothing else, with no lexicon access and no context. The distinction matters because tokenizers (whether BPE or morphology-aligned) operate on surface forms.

We capture this distinction with a single coefficient. Let s ∈ Σ range over surface forms and b ∈ B(L) over feature bundles. The **conditional entropy of the bundle given the surface form** is:

    H(b | s) = Σ_s p(s) · H(b | s = s),                        (4.3)

where H(b | s = s) is the Shannon entropy of the bundle distribution conditional on the specific surface form s, estimated from corpus-observed (s, b) pairs. We define the **structural recoverability coefficient** of L as:

    ρ(L) = 1 − H(b | s) / H(L).                                (4.4)

Equation (4.4) has a direct interpretation. H(b | s) measures the grammatical uncertainty that remains once the surface form has been observed. When the morphology is bijective with respect to its surface realisation — each bundle corresponding to a unique surface string, as in an idealised agglutinative language — H(b | s) = 0 and ρ = 1. When the surface form carries no information about the bundle — the degenerate case of complete ambiguity — H(b | s) = H(L) and ρ = 0. Real languages fall in between.

Two technical points deserve mention. First, the conditional entropy (4.3) is conditioned on the surface string itself, rather than on a "surface signature" obtained by stripping lexical content. For concatenative morphologies (English, Turkish), a lemma-stripped signature differs from the full surface only by lexical root identity, which in principle does not carry grammatical information. For templatic morphologies (Arabic), the grammar engine's explicit **template** field — a categorical label naming the morphological pattern (e.g. `VERB_TRILATERAL_BARE`, `NOM_DERIVED`) — serves this role directly. Details of the signature extraction are provided in Appendix C. Second, ρ(L) is a property of the language's grammar together with its corpus distribution, not of any particular tokenizer. Both BPE and morphology-aligned tokenizers, as surface-only systems, are bounded above in what grammatical information they can recover by H_eff(L) = ρ(L) · H(L).

On the 20,000-sentence samples we find ρ(English) ≈ 0.89, ρ(Turkish) ≈ 0.85, and ρ(Arabic) ≈ 0.59. The ordering reflects the typological character of the three systems. English and Turkish, both fundamentally concatenative, expose most of their grammatical structure on the surface. Arabic's templatic fusion hides roughly 40 percent of the grammatical signal behind ambiguity that would require lexical context or full analysis to resolve. The absolute values are signature-proxy estimates; a more refined estimator — for instance, mutual information between surface suffix n-grams and bundles — is left to follow-up work.

## 4.4 Implicit grammar cost and Assumption A1

A transformer trained under byte-pair tokenization receives no structural information about morphology at its input. Grammatical structure — which bundles co-occur with which lexical contents, which inflections follow which roots, which surface patterns realise which feature combinations — must be learned distributionally from co-occurrence statistics. This learning consumes model capacity.

Let **C_implicit(L)** denote the model capacity (in bits) a BPE-trained transformer must allocate to reconstructing H_eff(L) from distribution, at a capability threshold to be specified. Under morphology-aligned tokenization, the same grammatical information is instead delivered as an explicit categorical input — a bundle-embedding table indexed by b ∈ B(L), summed into the model's input representation alongside the root embedding. The capacity cost of the explicit path is simply the embedding table's storage:

    C_explicit(L) = |B(L)| · d_embed · (bits per weight).      (4.5)

For the Phase 1 configuration (d_embed = 128, 32-bit precision, |B(L)| at most ~1,800 on our Turkish 20k sample), C_explicit is of order 10 MB — three or four orders of magnitude below a 100M-parameter model. For the purposes of the rebate argument we treat C_explicit(L) as zero.

The harder quantity to characterise is C_implicit(L). A precise derivation from first principles would require a theory of how transformers allocate parameters to distributional pattern-learning, which does not yet exist in tractable form. We therefore promote a functional form to a stated assumption, to be examined empirically in §6.

> **Assumption A1 (dominant-term linearity).** The capacity a BPE-trained transformer allocates to implicitly reconstructing grammatical structure is, to first order, linear in the effective grammatical information content ρ(L) · H(L):
>
>     C_implicit(L) = α · ρ(L) · H(L) + O(lower-order terms).   (4.6)

The coefficient α absorbs factors that we take to be language-invariant at fixed architecture, data scale, and tokenizer family: the inefficiency of BPE fragments as morphological units, the effective vocabulary over which the grammatical association must be learned, and the bits-per-parameter capacity of the underlying transformer (Allen-Zhu and Li 2024). A1 is the simplest non-trivial hypothesis about how grammatical information translates to model capacity. It is not a theorem; it is the prediction the framework commits to, to be tested.

## 4.5 The parameter rebate and the capability-vs-scale curve shift

Combining (4.4), (4.5), and Assumption A1, the **parameter rebate** that morphology-aligned tokenization delivers for language L — the reduction in parameter count required to reach a fixed capability threshold — is:

    ΔN(L) = [C_implicit(L) − C_explicit(L)] / κ ≈ α · ρ(L) · H(L),  (4.7)

where κ is the bits-per-parameter coefficient of the underlying architecture. The language-invariant constants are absorbed into a single α in equation (4.7), and the framework's prediction reduces to a single expression: the rebate is proportional to a language's effective grammatical information content.

Equation (4.7) implies a corresponding prediction at capability level. Let **N_capability(T, L, tok)** denote the parameter count at which a transformer trained on language L with tokenization regime *tok* first reaches capability target T — a target which may be defined on any continuous or discrete metric (loss threshold, task score, accuracy on a held-out probe). The framework predicts:

    N_capability(T, L, morph) = N_capability(T, L, BPE) − α · ρ(L) · H(L).  (4.8)

Equation (4.8) is neutral between the two live views of how capability scales with parameter count. Under the sharp-emergence reading (Wei et al. 2022), (4.8) shifts the threshold at which a capability first appears. Under the smooth-improvement reading (Schaeffer et al. 2023, arguing that apparent sharpness is a measurement artefact of discontinuous metrics), (4.8) shifts the entire continuous capability-vs-scale curve left by ΔN(L). Both readings predict the same directional effect; they differ only in the shape of the curve being shifted. The framework does not need to pick between them.

Equation (4.8) is also the formal statement of the *edge-hostable reasoning* motivation discussed in §1.1. Let N_edge denote the parameter budget of a target edge profile, and T_reason denote a capability threshold associated with reasoning. The condition for edge-hostable reasoning in language L under morphology-aligned tokenization is:

    N_capability(T_reason, L, morph) ≤ N_edge.                 (4.9)

Whether any given language–capability pair satisfies (4.9) depends on α — on the quantitative strength of the rebate — which (4.7) and (4.8) leave as the empirical unknown the framework hands to the experiment in §6. The framework provides the functional form, the computable inputs (H(L) and ρ(L)), and the interpretive scaffolding. What it does not provide, and cannot provide from structural considerations alone, is the value of α.

§6 reports the result of estimating α from Phase 1 observations. The ordinal prediction of (4.7) — that the rebate orders the three languages — is confirmed. The magnitude prediction — that a single α fits all three — is not. This combination of outcomes is the substantive empirical content of the paper, and we return to it under the name **Agglutinative Compounding Effect** in §6.4.
