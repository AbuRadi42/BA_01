# 3. Related Work

**Status:** Manuscript-prose draft v1. Target length ≈ 900 words. Five neighbourhoods, tightly cited. Citation verification is on the Week 1 lit-review checklist; items marked [verify] need final confirmation before submission.

---

The framework developed in §4 sits at a junction of five literatures. Each contributes an input or a constraint; none individually asks the question the paper poses.

## 3.1 Morphological typology

The typological classification of languages by the way they organise grammatical information on word forms is a century-old project. Greenberg (1960) introduced a family of quantitative indices — most prominently the **Index of Synthesis** (morphemes per word, corpus-averaged) and the **Index of Agglutination** (ratio of agglutinative to fusional morpheme boundaries) — that placed analytic, agglutinative, and fusional languages on continuous rather than categorical scales. Comrie (1989) and Haspelmath and Sims (2010) extend the typological framework with richer treatments of inflection, derivation, and the interaction of morphological and syntactic systems. These works describe how much grammatical information languages encode, and how they encode it. They do not, in general, ask what consequences the encoding has for computational models of the language.

The Structural Synthesis Ceiling introduced in §4.1 stands explicitly in this lineage. It differs from Greenberg's Index of Synthesis in being a structural upper bound rather than a corpus average — the maximum grammatical information a word form can express in principle, rather than the empirical mean of what it does express in a given sample. We need this distinction because the framework's prediction target is the capacity a tokenizer can *pre-encode* — bounded by what the morphology permits, not by what a particular text realises.

## 3.2 Morphology-aware tokenization in NLP

Byte-pair encoding and its variants (Sennrich et al. 2016; Kudo and Richardson 2018) have become the default tokenization approach in large language modelling because of their simplicity, robustness, and lack of linguistic commitment. This last property is also their limitation: BPE fragments are the outputs of a statistical compression algorithm, and morphemes — the units of grammatical meaning — appear in the resulting vocabulary only coincidentally.

A recurring strand of work in multilingual NLP has attempted to align tokenization more closely with morphology, particularly for agglutinative and templatic languages where BPE's statistical segmentation performs poorly relative to morphological analysis. Representative examples include morpheme-aware subword models for Turkish and Hungarian [verify specific cites], and studies of tokenizer quality in Arabic under different segmentation schemes [verify]. These works demonstrate that morphology-aware tokenization can improve intrinsic metrics (perplexity, vocabulary coverage) and some extrinsic tasks for specific languages. Their framing, however, is almost uniformly empirical: *does this tokenizer work better for this language on this task?* The framework of §4 asks a structurally different question — *how much grammatical information does this language permit a tokenizer to pre-encode, and what does that imply for the parameter count a transformer requires?* — and answers it with inputs computable without reference to any training run.

## 3.3 Transformer scaling laws

Kaplan et al. (2020) characterised the relationship between transformer test loss and parameter count, training tokens, and compute as a set of power laws with specific empirical exponents. Hoffmann et al. (2022), best known for the Chinchilla compute-optimal result, refined the relationship into the form ℒ(N, D) = E + A · N^(−α_N) + B · D^(−α_D) and identified the compute-optimal token-to-parameter ratio of approximately twenty. More recent work has extended these laws into the capacity-per-parameter regime; Allen-Zhu and Li (2024) [verify title], in a study of transformer knowledge-storage ceilings, report a bits-per-parameter saturation coefficient of approximately two across architectures and training configurations. Equation (4.5) of §4 uses this coefficient as its working value of κ.

This literature is the source of the quantitative machinery that §6 applies to convert observed test-loss reductions into implied parameter rebates. It is also the source of Interpretation B in §6.5: the scaling laws are fit on predominantly English corpora, and their applicability to morphologically distant languages is an open question. The framework's empirical result — that a single α fails to fit three languages under these laws — is directly germane to that question.

## 3.4 Emergence and capability-scale curves

The question of how capabilities appear as transformers scale is actively contested. Wei et al. (2022) reported that certain abilities — chain-of-thought reasoning, in particular — emerge sharply at parameter counts above specific thresholds, typically in the 10^10 to 10^11 range for English models. Schaeffer et al. (2023) responded that much of what is reported as emergence is a measurement artefact of discontinuous scoring metrics (exact-match, thresholded accuracy); under continuous metrics, capability-vs-scale curves are typically smooth and sigmoidal. The framework of §4 is neutral between these readings. Equation (4.8) predicts a left-shift of the capability-vs-scale curve under morphology-aligned tokenization; whether the curve itself is sharp or smooth does not affect the prediction's form.

## 3.5 Green AI, linguistic equity, and edge ML

A fifth literature frames ML cost as an economic, environmental, and equity concern rather than a purely technical one. Strubell et al. (2019) quantified the energy and carbon cost of training large language models; Schwartz et al. (2020) proposed Green AI as a research orientation that treats efficiency as a first-order goal rather than an afterthought. Bender et al. (2021), in the Stochastic Parrots paper, raised concerns about the linguistic scope of the models the field is building, noting that the cost and data requirements of the dominant paradigm systematically disadvantage languages outside the high-resource English-centric mainstream. Ahia et al. (2023) [verify] quantified the per-language compute gap in multilingual NLP directly.

The framework of §4 contributes to these concerns a specific quantitative channel through which language structure enters cost accounting. Whether morphologically rich languages are *more* expensive to model (the common assumption, derived from lower data availability and higher surface diversity) or *less* expensive (the Interpretation-A reading of §6, derived from their higher ρ · H) is a question the framework makes tractable. The answer bears directly on how research compute, data collection, and model-sharing agreements should be allocated across the world's languages.
