# Morphological Efficiency in Multilingual Language Models
**Author:** Sameh AbuRadi
**Governed by:** `experimental_contract.md`
**Status:** Pre-training — pipeline complete, engines tested, ready for Vast.ai

---

## What This Project Is

This project trains and evaluates six language models across three languages — English, Arabic, and Turkish. For each language there are two models: a classically trained baseline and a grammar-aware morphology-informed variant. The experiment tests one question:

> If you teach a model the grammatical structure of its language before it sees any training data, does it learn faster and more efficiently?

Every model shares the same architecture (125M parameters), the same raw training data (2.5 billion tokens), and the same training budget. The only thing that differs is how the text is prepared before the model sees it. The baseline models receive statistically tokenized text with no linguistic knowledge. The morph models receive text that has been analyzed word-by-word through a grammar engine — every word decomposed into its root, its morphological template, and its grammatical tags — before training begins.

The experiment is governed by a frozen scientific contract (`experimental_contract.md`) that was written before any implementation began. Results are reported as-found.

---

## The Six Models

| Model | Language | Type | What it knows before training |
|---|---|---|---|
| en_base | English | Baseline | Nothing — pure BPE frequency statistics |
| en_morph | English | Grammar-aware | Inflectional + derivational morphology |
| ar_base | Arabic | Baseline | Nothing — pure BPE frequency statistics |
| ar_morph | Arabic | Grammar-aware | Root-and-pattern system (النحو والصرف) |
| tr_base | Turkish | Baseline | Nothing — pure BPE frequency statistics |
| tr_morph | Turkish | Grammar-aware | Suffix slot order + vowel harmony (Dilbilgisi) |

---

## The Five Evaluation Metrics

These are the five quantitative measures used to compare baseline vs. morph models. Each one captures a different dimension of what "learning efficiently" means.


### Metric 1 — Perplexity (eval_lm.py)

Perplexity measures how surprised the model is by text it has never seen. Formally it is the exponentiated average negative log-likelihood per token: `PPL = exp(mean(-log P(token_i | context)))`. A model with perplexity 50 is, on average, as uncertain as if it had to choose uniformly among 50 equally likely next tokens. Lower is better.

Perplexity is the primary language modeling metric. It is computed on the held-out test split after training is complete. Both baseline and morph models are evaluated on the same test sentences.

What it tells us: does the morph model assign higher probability to correct continuations? If the morph model has lower perplexity at the same training budget, it has learned a better probability distribution over the language — it has internalized the structure of the language more efficiently.

The comparison is always within-language (en_base vs. en_morph, ar_base vs. ar_morph, tr_base vs. tr_morph). Cross-language perplexity comparisons are not meaningful because the vocabularies and token distributions are different.

Logged to: `logs/training/{lang}_{regime}_timeseries.jsonl` (per step) and `logs/evaluation/{lang}_{regime}_lm_metrics.json` (final).

---

### Metric 2 — Tokens Per Meaning Unit (eval_morphology.py)

This metric measures how efficiently the tokenizer encodes meaning. It asks: how many tokens does it take to represent one unit of meaning?

For baseline models, a "meaning unit" is approximated as a lemma (the dictionary base form of a word). For morph models, a meaning unit is a (root, template) pair — the canonical morphological representation of the word.

The metric is computed as: `TPMU = total_tokens_in_corpus / total_meaning_units_in_corpus`.

A lower TPMU means the tokenizer is more compact — it encodes the same amount of meaning in fewer tokens. This matters because the model's context window is fixed at 1024 tokens. A tokenizer that uses fewer tokens per meaning unit fits more meaning into each context window, which means the model can attend to longer-range dependencies and learn from more context per training step.

For morphologically rich languages like Arabic and Turkish, this metric is expected to show the largest difference. Arabic BPE tokenizers frequently split a single word into 4–6 subword pieces, each carrying a fragment of meaning. The morph tokenizer represents the same word as 1–3 structured tokens (root + template + clitics), each carrying a complete unit of meaning.

Logged to: `logs/evaluation/{lang}_{regime}_morphology_metrics.json`.

---

### Metric 3 — Morphological Agreement Accuracy (eval_morphology.py)

This metric measures whether the model has learned the grammatical agreement rules of the language — the rules that require words in a sentence to match each other in gender, number, case, person, and tense.

The evaluation works by presenting the model with sentence contexts that require a specific grammatically agreeing continuation, and measuring how often the model assigns higher probability to the grammatically correct continuation than to an incorrect one.

Examples of what is tested:

- Arabic: does the model prefer a verb that agrees in gender and number with its subject? (الطالبة كتبَت vs. الطالبة كتبَ — the feminine subject requires the feminine verb form)
- Turkish: does the model prefer a suffix chain that respects vowel harmony? (evlerde vs. evlarda — the front-vowel stem requires the front-vowel locative suffix)
- English: does the model prefer the correct past tense form? (she went vs. she goed)

Agreement accuracy is reported as a percentage: what fraction of the test pairs does the model get right?

This metric directly tests whether the grammar prior has been internalized. A morph model that has been trained with explicit grammatical tags should show higher agreement accuracy than a baseline model that had to infer agreement rules from raw statistics alone.

Logged to: `logs/evaluation/{lang}_{regime}_morphology_metrics.json`.

---

### Metric 4 — Learning Efficiency / Steps to Threshold (eval_lm.py + compute_metrics.py)

This metric measures how quickly the model reaches a target performance level. It asks: how many training steps (or tokens) does it take to reach a perplexity of X?

The threshold X is set per language based on a reasonable target for a 125M model trained on 2.5B tokens. The exact threshold is determined after the first baseline run and then held fixed for the comparison.

Learning efficiency is computed from the training time-series logs. Every 100 training steps, the current loss and perplexity are logged. The step at which the model first crosses below the threshold perplexity is the "steps to threshold" value.

If the morph model reaches the threshold in fewer steps than the baseline, it has learned more efficiently — the grammar prior gave it a head start. This is the most direct test of the core research claim.

The metric is also visualized as a learning curve: perplexity vs. tokens processed, with both baseline and morph plotted on the same axes. The area between the two curves (if the morph curve is consistently lower) quantifies the total efficiency gain over the full training run.

Logged to: `logs/training/{lang}_{regime}_timeseries.jsonl` (raw) and `logs/summary/learning_efficiency.json` (aggregated).

---

### Metric 5 — Downstream Task Performance (eval_downstream.py)

This metric measures whether the representations learned by the model are useful for real tasks beyond language modeling. It uses a frozen model + linear probe evaluation: the model's weights are frozen after training, a single linear layer is trained on top of the model's hidden states, and the linear probe's accuracy on a downstream task is reported.

Two downstream tasks are evaluated:

**Text classification:** given a sentence, predict its category (topic, sentiment, or domain). The model's hidden states at the final token position are used as the sentence representation. The linear probe is trained on a small labeled dataset (1000–5000 examples) and evaluated on a held-out test set.

**Morphological probing:** given a word in context, predict its morphological category (e.g., is this verb past tense or present tense? is this noun singular or plural?). This directly tests whether the model's internal representations encode morphological information — even for the baseline model, which was not explicitly trained with morphological labels.

The downstream task evaluation answers a different question than perplexity: not "does the model predict text well" but "does the model understand the language well enough to be useful for something." A model with lower perplexity does not always have better downstream task performance — the two can diverge. Reporting both gives a more complete picture.

FLOPs (floating point operations) are also logged during this evaluation to enable a compute-efficiency comparison: downstream accuracy per unit of compute.

Logged to: `logs/evaluation/{lang}_{regime}_downstream_metrics.json`.

---

## Model Architecture

All six models share the same architecture. The only structural difference between baseline and morph models is the addition of a second embedding table in the morph models.

| Parameter | Value |
|---|---|
| Architecture | Decoder-only GPT-style transformer |
| Parameters | ~125M |
| Layers | 12 |
| Hidden size | 768 |
| Attention heads | 12 |
| FFN dimension | 3072 |
| Context length | 1024 tokens |
| Precision | bfloat16 |
| Training tokens | 2.5B (Chinchilla-optimal for 125M params) |

The original plan called for 425M parameters. This was downgraded to 125M due to compute budget constraints. See `feasibility.md §11` for the full technical record. The scientific comparison is not affected by the scale reduction.

**Baseline models** have one embedding table: `token_embedding[token_id]`.

**Morph models** have two embedding tables. The input to the first transformer layer is:
```
x = token_embedding[root_template_id] + feature_embedding[grammatical_bundle_id]
```

The model receives both the semantic identity of the word (what root and template it is) and its grammatical role (what tense, person, number, etc.) as a combined signal from the very first layer. The feature embedding table is the only architectural addition — everything else is identical.


---

## The Full Pipeline — Step by Step

### Stage 0 — Grammar Engine (already complete)

Before any data is downloaded, the grammar engines are built and tested. These are the algorithmic analyzers that will process every word in the corpus for the morph models. They live in `scripts/engines/` and are tested by 2150 pytest tests (0 failures).

The three engines share a common three-step structure:

```
Word
 │
 ▼
Step A: Clitic / Affix Stripping + Surface Tagging
         Detach grammatical particles attached to the word surface.
         Tag the remaining base form with grammatical properties.
 │
 ▼
Step B: Template / Pattern Detection
         Match the base form against the known morphological template
         inventory for that language.
 │
 ▼
Step C: Root / Stem Extraction
         Extract the root or stem using the identified template.
 │
 ▼
TokenInfo(surface, clitics, template, root, tags, pos)
```

The output for each word is a `TokenInfo` object — a fully tagged representation that becomes the input to the morph model's tokenizer.

---

### Stage 1 — Download Corpora (download_data.py)

**Script:** `scripts/download_data.py --language all`

Downloads text from HuggingFace datasets in streaming mode (no full corpus loaded into RAM) and writes train/val/test splits for each language.

Sources:
- English: Wikipedia EN + OPUS books + CC-100 EN
- Arabic: Wikipedia AR + OPUS AR + CC-100 AR
- Turkish: Wikipedia TR + OPUS TR + CC-100 TR

Split targets per language:
- Train: ~2.5B whitespace tokens
- Validation: ~62.5M tokens
- Test: ~62.5M tokens

The split is assigned probabilistically per sentence using a fixed random seed per language (EN=42, AR=43, TR=44). This ensures the baseline and morph models for the same language see exactly the same sentences in the same splits — the only difference is how those sentences are processed.

Outputs:
```
data/raw/en/train.txt   data/raw/en/val.txt   data/raw/en/test.txt
data/raw/ar/train.txt   data/raw/ar/val.txt   data/raw/ar/test.txt
data/raw/tr/train.txt   data/raw/tr/val.txt   data/raw/tr/test.txt
```

Token counts are logged to `logs/evaluation/{lang}_baseline_token_stats.json`.

---

### Stage 2 — Baseline Preprocessing (preprocess_baseline.py)

**Script:** `scripts/preprocess_baseline.py --language all`

Produces the tokenized data for the three baseline models (en_base, ar_base, tr_base).

**Step 2a — Train SentencePiece BPE tokenizer**

For each language, a BPE (Byte Pair Encoding) tokenizer is trained on up to 10M sentences sampled from the training corpus. BPE starts with individual characters and iteratively merges the most frequent adjacent pairs until the vocabulary reaches 32,000 tokens.

The tokenizer has zero linguistic knowledge. It does not know what a verb is, what a root is, or that "running" and "run" are related. It learns purely from which character sequences appear together frequently. The result is a vocabulary of 32,000 statistical subword pieces.

Configuration: vocab_size=32000, character_coverage=0.9995, model_type=bpe, BOS/EOS/PAD/UNK special tokens.

Saved to: `tokenizers/{lang}_base/{lang}_base.model`

**Step 2b — Tokenize all splits**

Every sentence in train/val/test is encoded as a sequence of integer token IDs using the trained tokenizer. BOS (token 2) is prepended and EOS (token 3) is appended to each sentence. The full sequence is saved as a NumPy int32 array.

Outputs:
```
data/processed/en/baseline/train_tokens.npy
data/processed/en/baseline/val_tokens.npy
data/processed/en/baseline/test_tokens.npy
(same for ar and tr)
```

---

### Stage 3 — Morph Preprocessing (preprocess_morph.py)

**Script:** `scripts/preprocess_morph.py --language all`

Produces the tokenized data for the three morph models (en_morph, ar_morph, tr_morph). This is where the grammar engines run over the full corpus.

For each word in each sentence, the grammar engine produces a `TokenInfo` object. The `MorphVocab` registry converts this into two integer IDs:
- `token_id` — identifies the word's root+POS (e.g., `كتب.VERB`)
- `bundle_id` — identifies the grammatical tag bundle (e.g., `pos=VERB|tense=PAST|person=3|num=PL|gender=M|voice=ACT`)

Both sequences are saved as NumPy int32 arrays. The morph model's training loop loads both and adds the two embeddings together as its input.

After processing all splits, the vocabulary is saved:
- `tokenizers/{lang}_morph/vocab.json` — maps token strings to IDs
- `tokenizers/{lang}_morph/feature_bundles.json` — maps bundle strings to IDs

Outputs:
```
data/processed/en/morph/train_tokens.npy      data/processed/en/morph/train_feature_ids.npy
data/processed/en/morph/val_tokens.npy        data/processed/en/morph/val_feature_ids.npy
data/processed/en/morph/test_tokens.npy       data/processed/en/morph/test_feature_ids.npy
(same for ar and tr)
```

Stats per split (foreign rate, vocab size, feature bundle count) are logged to `logs/evaluation/{lang}_morph_{split}_stats.json`.

---

### Stage 3 Detail — The Arabic Grammar Engine (ar_engine.py)

Arabic is a root-and-pattern (templatic) language. Every Arabic word is built from a triconsonantal or quadriconsonantal root (جذر) combined with a vowel pattern (وزن). The root carries the core semantic field; the pattern carries the grammatical function. The engine implements النحو والصرف — the formal Arabic grammatical sciences — algorithmically.

**Pre-computed vocabulary space:** Before touching the corpus, the engine crosses 7,142 roots (sourced from the Doha Historical Dictionary of Arabic, معجم الدوحة التاريخي للغة العربية) against the full وزن template inventory. For each (root, template) pair, it applies the root consonants to the template's ف-ع-ل skeleton and checks phonological validity. The result is a grammar-defined closed vocabulary stored in `configs/ar_vocab_space.json`.

**Closed-class particle lookup:** Before any morphological analysis, the engine checks the word against a lookup table of ~120 Arabic function words and frozen expressions (prepositions, conjunctions, negation particles, interrogatives, discourse particles, vocatives, interjections, oaths, response particles). If found, the word is immediately tagged as `PART` with its subcategory and the root-and-pattern pipeline is skipped. This prevents particles like على (two consonants, no matching template) from being misclassified as verbs.

**Step A — Clitic stripping:** Arabic words frequently have grammatical particles glued onto them. The engine strips these in a loop, one at a time, until no more remain.

Proclitics (front): conjunctions وَ/فَ, prepositions بِ/لِ/كَ, definite article الـ, future marker سَـ, emphasis particle لَـ, interrogative أَ, oath prefix تَ, and all compound clusters of the above (وَبِالـ، فَلِلـ etc.), in both diacritical and undiacritical forms.

Enclitics (back): all object/possessive pronoun suffixes (3rd, 2nd, 1st person, all numbers and genders), dual noun endings, feminine plural endings, 2nd person verb agreement suffixes, and energetic nun (نون التوكيد).

Consonant-count guards prevent the engine from eating root consonants:
- Conjunctions (و، ف): require 3+ consonants remaining after stripping
- Prepositions and tense markers (ب، ل، ك، س): require 4+ consonants remaining (these can be root-initial)
- After الـ is stripped, no further single-character proclitic stripping is attempted (prevents الكتاب → كتاب → تاب)
- Form VIII / الـ ambiguity guard: before stripping الـ, the engine checks whether the word matches the Form VIII اِفْتَعَلَ signature (prevents اِلْتَقَى from being misread as الـ + تقى)
- Enclitic ي guard: only stripped when 5+ consonants remain (prevents eating root-final ي from يَرْمِي)
- Enclitic كَ/كِ guard: requires 4+ consonants remaining (prevents eating root-final ك from شَارَكَ)
- Enclitic نِي/نِ guard: requires 3+ consonants remaining (prevents eating root-final ن from يَبْنِي)
- Masculine sound plural guard (ـون/ـين): requires 3+ consonants remaining
- Nisba suffix stripping (ـيّ): detected by ي + shadda at word end; stripped before template matching

Special construction — لام التوكيد + نون التوكيد: this is a circumfix (الإحاطة) — a discontinuous morpheme where لَـ at the front and ـنَّ/ـنْ at the back bracket the verb together to form the sworn-assertion construction (جواب القسم المؤكد بالنون). Example: لَيَكْتُبَنَّ = "he will most certainly write, I swear it." The engine strips both halves independently then detects the co-occurrence and reunites them as a single `circumfix=LAM_NUN, assertion=SWORN` tag.

Imperfect prefix يَ: after clitic stripping, if the stem starts with يَ (diacritical) or bare ي (unvoweled) and 3+ consonants remain after removing it, the imperfect 3rd-person masculine prefix is stripped.

**Step B — Template matching:** The stripped base form is matched against the Arabic pattern inventory. The engine runs pre-index checks for augmented verb forms and derived nominals before consulting the template index. Each check has a precise consonant-count condition:

| Prefix marker | Condition | Form detected |
|---|---|---|
| مُسْت | any | Form X active participle (NOM_DERIVED_X) |
| اِسْت | 5+ chars remaining | Form X verb (اِسْتَفْعَلَ) |
| اِ + any + ت at position 2 | 4+ consonants | Form VIII (اِفْتَعَلَ) |
| اِنْ + consonants[2] ≠ ت | 5+ consonants | Form VII (اِنْفَعَلَ) |
| إ + 5 consonants + ا at position 3 | exactly 5 | إفعال masdar (Form IV masdar) |
| أ | exactly 4 consonants | Form IV (أَفْعَلَ) |
| أ + ا at position 3 | exactly 5 | Broken plural أَفْعَال |
| ت | exactly 4 consonants, no internal ا | Form V (تَفَعَّلَ) |
| ت | 5 consonants, root_consonants==4 | Form VI (تَفَاعَلَ) |
| ت | 5 consonants, ي at position 3 | Masdar Form II (تَفْعِيل) |
| اِ + geminate final | 4 consonants (voweled) or 5 (unvoweled) | Form IX (اِفْعَلَّ) |
| مُ (damma) | any | Derived nominal (NOM_DERIVED) |
| مَ (fatha) | 4+ consonants | Derived nominal (مَفْعُول / place noun) |

**Step C — Root extraction:** Once the template is identified, the engine extracts the root by mapping the word's consonants back onto the template's ف-ع-ل positions. Augment prefix consonants are skipped (skip counts: Form X = 3, Form VIII = 1, Form VII = 2, Form V/VI = 1, Form IV = 1, NOM_DERIVED = 1, NOM_DERIVED_X = 3).

Form VIII specifically: after skipping the initial اِ, the infixed ت is searched dynamically at positions 1 or 2 of the remaining consonants. Three assimilation variants are handled: root-initial و/ي/ء (doubled ت, recovery by prepending و/ي/ء), emphatic R1 (ت absorbed into emphatic, no removal needed), and emphatic R1 + geminate (emphatic substitute at position 1 is removed).

Phonological normalizations applied before root lookup:
- Hamza normalization: all hamza variants (أ، إ، آ، ؤ، ئ) normalized to bare ء
- ناقص (final weak radical): final ا or ى substituted with و then ي; disambiguation lexicon keyed by (R1, R2) frame resolves ambiguous pairs
- أجوف (middle weak radical): disambiguation lexicon keyed by (R1, R3) frame determines whether middle radical is و or ي
- مثال (initial و-drop): if 2 consonants remain after augment skipping, و is prepended as a candidate
- مضعّف (geminate): if 2 consonants remain, final consonant is doubled as a candidate
- Long-vowel ا in patterns (فَاعِل, فِعَالَة etc.): internal ا stripped before lookup
- مَفْعُول / فُعُولَة / فَعِيلَة patterns: internal و or ي at position 2 stripped before lookup
- Diminutive pattern (فُعَيْعِل): ي at position 2 stripped to recover quadriliteral root

Form VII ن removal uses a context-sensitive rule: for 3-consonant post-skip stems, ن is only stripped if the 2-char remainder is a known ناقص frame in the disambiguation lexicon; for 4+ consonant post-skip stems, ن is always stripped.

The extracted root is validated against `configs/ar_roots.json`. If found → confirmed. If not → flagged as `UNVERIFIED_ROOT` and logged.


---

### Stage 3 Detail — The English Grammar Engine (en_engine.py)

English is an analytic language with shallow inflectional morphology but a rich derivational system. The engine is grounded in Quirk et al. (1985) and Huddleston & Pullum (2002).

**Step A — Inflectional stripping:** The engine first checks the word against `configs/en_irregulars.json` — a lookup table of all irregular English forms (went→go, mice→mouse, better→good, been→be, children→child, etc.). Irregular forms cannot be handled by pattern matching and must be resolved by lookup.

If the word is not irregular, pattern-based stripping is applied:

| Pattern | Signal | Example |
|---|---|---|
| -ing | Progressive verb | running → run, tense=PRES, aspect=PROG |
| -ed | Past tense / past participle | walked → walk, tense=PAST |
| -s / -es | Plural noun or 3sg verb | cats → cat, num=PL |
| -ies | Plural of -y words | cities → city, num=PL |
| 's | Possessive | cat's → cat, poss=YES |
| -er | Comparative | faster → fast, degree=COMP |
| -est | Superlative | fastest → fast, degree=SUPER |

Spelling rules are applied in reverse: double-consonant restoration (running → run, not runn), silent-e restoration (making → make, not mak).

Tags assigned: pos (NOUN/VERB/ADJ/ADV/DET/PRON/PREP/CONJ/PART), num (SG/PL), tense (PAST/PRES), aspect (PERF/PROG), voice (ACT/PASS), degree (COMP/SUPER), poss (YES).

**Step B — Derivational detection:** After inflectional stripping, the engine checks whether the remaining stem has a derivational affix using `configs/en_derivations.json`. The engine strips one derivational layer at a time and records the chain.

Examples of derivational patterns handled:
- Verb → Noun: -tion/-sion/-ation (education), -ment (development), -ure (failure), -er/-or (teacher)
- Adj → Noun: -ness (darkness), -ity (reality), -ism (capitalism)
- Noun/Adj → Verb: -ize/-ise (modernize), -ify (simplify), -en (darken)
- Noun → Adj: -ful (hopeful), -less (hopeless), -able/-ible (readable), -ous (dangerous), -al (national), -ic (historic)
- Prefixes: un- (negation/reversal), re- (repetition), dis- (negation), over- (excess), pre- (before), mis- (wrongly)

Example chain: "modernization" → strip -ation → "modernize" (V→N recorded) → strip -ize → "modern" (N/ADJ→V recorded) → root: "modern", derived_chain: ["-ation→ACTION_NOUN", "-ize→VERBALIZE"]

Phrasal verbs (`configs/en_phrasal_verbs.json`) and compound words (`configs/en_compounds.json`) are handled via lookup before the stripping pipeline, since their semantics are not compositional (give up ≠ give + up).

**Step C — Root identification:** Whatever remains after stripping up to four derivational layers is the root/stem — the core semantic unit.

---

### Stage 3 Detail — The Turkish Grammar Engine (tr_engine.py)

Turkish is an agglutinative language. Words are built by stacking suffixes onto a stem in a strict, predictable order defined by Dilbilgisi (Turkish grammar). A single Turkish word can encode what English expresses in a full clause. The engine implements the canonical Dilbilgisi suffix slot order algorithmically.

**Pre-computed vocabulary space:** The engine builds a theoretical map from the Turkish suffix inventory (`configs/tr_suffixes.json`) and derivational suffix inventory (`configs/tr_derivations.json`). Each suffix entry records its logical name, surface variants (vowel harmony forms), slot position, and grammatical tags.

**Vowel harmony:** Turkish suffixes change their vowels to match the vowels in the stem. Two harmony dimensions operate simultaneously:
- Back/front harmony: back vowels (a, ı, o, u) in stem → suffix takes back variant; front vowels (e, i, ö, ü) → front variant
- Rounding harmony: rounded vowels (o, u, ö, ü) → high vowel in suffix becomes rounded; unrounded → unrounded

The same suffix has multiple surface forms: plural is -lar after back vowels, -ler after front vowels. The engine validates that each stripped suffix's surface form is consistent with the vowel harmony of the remaining stem.

**Step A — Suffix stripping (outermost-first):** Suffixes are stripped from right to left, following the reverse of the canonical Dilbilgisi slot order. Each stripped suffix is normalized to its logical form and its grammatical function is recorded as a tag.

Canonical slot order for nominal words: `STEM → [DERIV] → [NUM] → [POSS] → [CASE]`
Canonical slot order for verbal words: `STEM → [DERIV] → [VOICE] → [NEG] → [TENSE] → [MOOD] → [PERSON+NUM]`

Tags assigned: pos (NOUN/VERB/ADJ/ADV/POSTP), num (SG/PL), poss (1SG/2SG/3SG/1PL/2PL/3PL), case (NOM/ACC/DAT/LOC/ABL/GEN/INS), voice (PASS/CAUS/RECIP/REFL), polarity (NEG), tense (PAST_DEF/PAST_NARR/PRES_PROG/PRES_AORIST/FUT), mood (COND/OPT/IMP/NECESS/INF), person (1/2/3), modality (ABIL), epist (INFER), q (YES_NO).

The two past tense values are linguistically significant: PAST_DEF (-dı, witnessed past — "I saw it happen") vs. PAST_NARR (-mış, narrative/reported past — "I heard it happened"). This evidential distinction is grammatically encoded in Turkish and is preserved as a tag.

**Step B — Dilbilgisi slot order validation and derivational detection:** After stripping, the engine validates that the suffix sequence respects the canonical slot order. Violations are flagged as `MALFORMED` and logged. Derivational suffixes (those that change the word's category or create a new word) are identified and recorded in the derivation chain.

Derivational suffixes handled: -lık/-lik (noun/adj → abstract noun: iyi → iyilik), -cı/-ci (noun → agent noun: araba → arabacı), -lı/-li (noun → adjective: su → sulu), -sız/-siz (noun → privative adj: su → susuz), -laş (noun/adj → verb: modern → modernleşmek), -ış/-iş (verb → action noun: gel → geliş), and others from `configs/tr_derivations.json`.

**Step C — Stem identification, valency, and compound detection:** After all suffix layers are stripped, the remaining stem is looked up in the Zeyrek stem lexicon (queried at runtime via `analyzer.lexicon`). Verbal stems are checked for valency (transitive/intransitive). Compound stems (başbakan = baş + bakan) are detected and both component stems are recorded.

---

### Stage 4 — Training (train_lm.py)

**Script:** `scripts/train_lm.py --language {en|ar|tr} --regime {baseline|morph}`

Trains one model. Run six times total (or split across two Vast.ai instances for parallel training).

The training loop:
1. Loads the processed token arrays from `data/processed/{lang}/{regime}/`
2. For morph regime, also loads the feature ID arrays
3. Instantiates the GPT model (125M params)
4. Trains with AdamW optimizer, cosine LR schedule with 2000-step warmup, gradient clipping at 1.0
5. Every 100 steps: logs loss, perplexity, tokens processed, wall time, GPU memory, LR to `logs/training/{lang}_{regime}_timeseries.jsonl`
6. Every 1000 steps: saves a checkpoint to `models/{lang}_{regime}/ckpt_step{N}.pt` (keeps last 3)

Resume from checkpoint: add `--resume` flag. The script finds the latest checkpoint automatically.

Throughput estimate on A100 80GB: ~80,000–100,000 tokens/sec. At 2.5B tokens per model: ~7–9 GPU hours per model, ~42–54 GPU hours total for all six.

---

### Stage 5 — Evaluation

**eval_lm.py** — computes final perplexity on val and test splits for each model.
```bash
python scripts/eval_lm.py --language all --regime all
```
Outputs: `logs/evaluation/{lang}_{regime}_lm_metrics.json`

**eval_morphology.py** — computes tokens-per-meaning-unit, morphological agreement accuracy, lemma+bundle accuracy, nats per morpheme.
```bash
python scripts/eval_morphology.py --language all --regime all
```
Outputs: `logs/evaluation/{lang}_{regime}_morphology_metrics.json`

**eval_downstream.py** — frozen model + linear probe on text classification and morphological probing tasks. Also logs FLOPs.
```bash
python scripts/eval_downstream.py --language all --regime all
```
Outputs: `logs/evaluation/{lang}_{regime}_downstream_metrics.json`

---

### Stage 6 — Aggregation and Presentation

**compute_metrics.py** — reads all evaluation logs, computes summary tables, learning efficiency comparisons, and writes `logs/summary/conclusion.md`.
```bash
python scripts/compute_metrics.py
```

Open `presentation/index.html` in a browser to view the full slide presentation. It loads the JSON logs directly and renders all charts and comparisons. No server required.

---

## Quick Start

Install dependencies:
```bash
pip install torch sentencepiece datasets numpy matplotlib
```

Run the pipeline in order (all commands from workspace root):
```bash
# 1. Download corpora (~hours on Vast.ai)
python morph_efficiency_project/scripts/download_data.py --language all

# 2. Baseline tokenization
python morph_efficiency_project/scripts/preprocess_baseline.py --language all

# 3. Morph preprocessing (grammar engines over full corpus)
python morph_efficiency_project/scripts/preprocess_morph.py --language all

# 4. Train all six models (sequential; add --resume to continue from checkpoint)
python morph_efficiency_project/scripts/train_lm.py --language en --regime baseline
python morph_efficiency_project/scripts/train_lm.py --language en --regime morph
python morph_efficiency_project/scripts/train_lm.py --language ar --regime baseline
python morph_efficiency_project/scripts/train_lm.py --language ar --regime morph
python morph_efficiency_project/scripts/train_lm.py --language tr --regime baseline
python morph_efficiency_project/scripts/train_lm.py --language tr --regime morph

# 5. Evaluate
python morph_efficiency_project/scripts/eval_lm.py --language all --regime all
python morph_efficiency_project/scripts/eval_morphology.py --language all --regime all
python morph_efficiency_project/scripts/eval_downstream.py --language all --regime all

# 6. Aggregate
python morph_efficiency_project/scripts/compute_metrics.py
```

Smoke test the pipeline locally (no GPU, no full corpus, synthetic data):
```bash
python morph_efficiency_project/scripts/_smoke_pipeline.py --lang all
```

Run the grammar engine tests:
```bash
python -m pytest morph_efficiency_project/tests/ -q
# Expected: 2150 passed, 2 skipped, 0 failed
```

---

## Directory Structure

```
morph_efficiency_project/
  configs/           Grammar engine resources + model/training configs
  data/
    raw/             Downloaded corpora (en/, ar/, tr/)
    processed/       Tokenized arrays (baseline/ and morph/ per language)
  logs/
    training/        Per-step training logs (JSONL timeseries)
    evaluation/      Per-model evaluation results (JSON)
    summary/         Aggregated comparison tables + conclusion.md
  models/            Trained model checkpoints (en_base/, en_morph/, etc.)
  notebooks/         analysis.ipynb
  presentation/      Browser-based slide presentation (index.html, app.js, styles.css)
  scripts/
    engines/         Grammar engine subpackage (ar_engine.py, en_engine.py, tr_engine.py, shared.py)
    download_data.py
    preprocess_baseline.py
    preprocess_morph.py
    train_lm.py
    eval_lm.py
    eval_morphology.py
    eval_downstream.py
    compute_metrics.py
    _audit.py        Development safety net — not part of training pipeline
    _debug_fails.py  Development safety net — not part of training pipeline
    _smoke_pipeline.py  End-to-end pipeline smoke test (no GPU required)
  tests/
    _base/           Infrastructure tests (paths, dataset loading, model instantiation)
    ar_morph/        Arabic engine tests (particles, templates, sentence structure, regression)
    en_morph/        English engine tests (inflection, derivation, sentence structure, regression)
    tr_morph/        Turkish engine tests (particles, suffixes, sentence structure, regression)
    conftest.py
tokenizers/          Trained tokenizer models (en_base/, en_morph/, ar_base/, ar_morph/, tr_base/, tr_morph/)
experimental_contract.md
feasibility.md
```

---

## Compute

Platform: Vast.ai (spot A100 80GB instances, ~$0.35–$0.70/hr)

Estimated cost: $60–$100 total for all six models including preprocessing, reruns, and evaluation. See `feasibility.md` for the full cost breakdown and the rationale for choosing Vast.ai over RunPod and Colab.

Checkpoints are saved every 1000 steps. If a spot instance is preempted, resume with `--resume` and training continues from the last checkpoint with no data loss.
