# 1. Abstract

**Status:** Manuscript-prose draft v1. Target length "approximately 300 words" per Cambridge *Natural Language Processing* guidelines. This draft: ~305 words.

---

Transformer scaling laws — *the empirical curves predicting how language-model performance improves with parameter count and training data* — are fit predominantly on corpora of analytic-leaning languages such as English and Mandarin. This may be because the AI economy is dominated by firms from the Anglophone world and China, or because these two languages happen to be well-suited to probabilistic byte-pair tokenization *(a statistical method that splits text into recurring character fragments without regard to grammatical structure)*. Reasoning-capable language models conventionally emerge at parameter counts well above contemporary edge-hosting budgets *(smartphone- or laptop-class memory)*, though exceptions such as Google's Gemma 4 E4B *(an effective 4-billion-parameter on-device model released in April 2026)* suggest the boundary is being pushed.

This paper asks whether a language's grammatical structure can function as a capacity lever: whether morphology-aware tokenization — encoding grammatical feature bundles *(tense, number, case, person, and so on)* as explicit categorical inputs — rebates a quantifiable portion of a transformer's parameter budget for a given capability.

We develop a framework in which the predicted rebate is proportional to ρ(L) · H(L), where H(L) is the Shannon entropy of grammatical feature bundles per word form *(a bit-valued measure of grammatical information density)* and ρ(L) is their recoverability from surface form *(the fraction extractable from the written word alone)*. Both are computable from a morphological grammar engine *(a rule-based parser decomposing words into roots and grammatical markers)* before any training run.

A six-model Phase 1 experiment at two million parameters and five million tokens, across English, Arabic, and Turkish, confirms the framework's ordinal prediction: test-loss reductions under morphology-aware tokenization are monotonically ordered by ρ(L) · H(L), matching the engine-derived rank order. The magnitude prediction, however, does not hold: the per-bit coefficient α implied by the Hoffmann scaling-law derivative varies by approximately forty-fold across the three languages, with implied α growing super-linearly in ρ · H itself.

We name this pattern the **Agglutinative Compounding Effect** and show it is consistent with two mutually-exclusive interpretations: a genuine super-linearity in the framework's functional form, or a breakdown of English-centric scaling laws applied outside their fit regime. A two-tier Arabic extension decomposes the rebate into surface-recoverable and lexicon-recoverable components, uncovering a companion phenomenon we name the **Templatic Lexical Surplus** — the additional rebate delivered when explicit root-identity access is given to templatic languages *(Semitic languages such as Arabic and Hebrew, whose grammar arises from interleaving consonantal roots with vowel patterns)*.

If the Compounding Effect is real, edge-hostable reasoning becomes plausible for morphologically rich languages at parameter counts English does not reach; if it is a scaling-law artefact, transformer compute estimates require a morphological correction term. The paper specifies the follow-up experiments that would decide.

---

## Keywords (tentative, 5–7)

- morphological tokenization
- transformer scaling laws
- linguistic typology
- information theory in NLP
- edge-hostable language models
- low-resource multilingual NLP
- Agglutinative Compounding Effect
