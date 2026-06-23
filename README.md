# Morphology-Aware Tokenization as a Capacity Lever

**A Cross-Linguistic Framework for Parameter-Efficient Language Models**

| | |
|---|---|
| **Author** | Sameh AbuRadi — CODE University of Applied Sciences, Berlin |
| **Supervisor** | Fabian Geier |
| **Target venue** | *Natural Language Processing* (Cambridge University Press) |
| **Compute** | Donated AWS credits ($24,000) from Deniz Sertkan — funds both phases below |
| **Status** | Architecture complete; tokenisation complete on all four languages; AWS deployment is yours to authorise |
| **Phase 2** | Eight-cell proof-of-concept sweep (4 languages × 2 regimes at 30M parameters). Budget ≈ $3-5k. Cambridge submission. |
| **Phase 3** | Native Turkish reasoning-capable small language model, built with the technique Phase 2 proves. Budget ≈ $15-20k. The bulk of the credits goes here. |
| **Governance** | Pre-registered scientific contract at `experimental_contract.md`, frozen before implementation |

---

## The question this project asks

Big language models like ChatGPT or Gemma need enormous brains to learn how a language works. They have to figure out, from billions of examples, that *cats* is the plural of *cat*, that Arabic verbs come from three-letter roots, that Turkish stacks suffixes in a strict order, that Chinese characters carry their semantics in their radicals. They burn megawatts of electricity to reconstruct grammatical knowledge that human linguists have already written down in textbooks.

This project asks one question:

> If we give the model the grammar of the language *before* training begins, encoded as structured input streams that sit alongside the surface text, does it need a smaller brain to reach the same capability?

If the answer is yes, then small grammar-aware models could fit on smartphones, and languages currently under-served by the major foundation models (Arabic, Turkish, the Semitic family, the Turkic family, the languages of South and East Asia) would become much cheaper to model well.

We test this on four languages chosen for their typological diversity:

| Language | Morphological type | Why it's here |
|---|---|---|
| Mandarin (ZH) | Isolating, with radical-semantic structure | Tests the framework's lower bound: a language with almost no inflectional morphology, but a non-concatenative semantic axis (the Kangxi radical inventory) that is the structural analog of Arabic's wazn system |
| English (EN) | Analytic | The control: morphology is sparse, framework predicts the smallest rebate |
| Turkish (TR) | Agglutinative | The framework's predicted strongest case: high grammatical information per word, surface-recoverable |
| Arabic (AR) | Templatic (root-and-pattern) | The decomposition case: grammatical and semantic information sit on three orthogonal axes (surface affixation, root identity, wazn semantic role) |

For each language we will train two small transformers: one classical (BPE baseline), one grammar-aware (multi-stream input). Same architecture, same data, same training budget. The only difference is what the tokeniser exposes.

---

## What has been built so far

The repository contains everything needed to deploy the experiment to AWS, except the actual cloud credentials and the act of pressing *deploy*. The pieces, end to end:

1. **Four grammar engines**, one per language, that decompose each word into its grammatical pieces. Total 4,283 unit tests covering inflection, derivation, prefixation, irregulars, vowel harmony, clitic stacking, broken plurals, weak roots, masdars, awzān, radicals, and the edge cases that surface only on real Wikipedia text.

2. **A sentence-grammar layer** per language that resolves part-of-speech ambiguities using the full sentence window, and validates the sentence against the language's allowed structural templates (الجملة الفعلية and الجملة الاسمية for Arabic, fiil-sonda SOV for Turkish, the 把/被 constructions for Mandarin, SVO for English).

3. **A tokeniser pipeline** that turns raw Wikipedia text into the integer streams the model consumes. Two regimes per language: the BPE baseline (one stream) and the grammar-aware variant (two streams for ZH/EN/TR, four for AR).

4. **A multi-stream transformer architecture** (`MiniGPT`) that supports 1, 2, or 4 input embedding streams summed at the input layer, with a parameter-matched comparison protocol so reviewers cannot dismiss the rebate as a parameter-count artefact.

5. **A trainer** with cosine learning-rate schedule, checkpointing, eval logging, and resume support, verified end-to-end on a local CPU smoke run (50,000 tokens, 27 seconds wall-clock, loss decreased monotonically from 9.31 to 6.95).

6. **An AWS SageMaker launcher** that emits the estimator configuration, the submission script, and the IAM requirements per training run, and can deploy directly via `boto3` when given AWS credentials.

7. **A 60-page manuscript** drafted, polished for linguist-readability, with all four languages' case studies, the architecture documented, every Arabic word vocalised with tashkil, properly bidirectional Arabic rendering, the four-language scope reflected throughout, and a fresh PDF at `manuscript/tex/_build/main.pdf`.

8. **Bundle distribution analysis** with per-language Zipf plots and a combined cross-lingual figure, documenting the structural shape of each language's feature-bundle space at full corpus scale.

The only thing still pending is one local dress-rehearsal smoke run, and the AWS deployment itself.

---

## The framework, in plain terms

Every word in a language carries *grammatical information*. The English *researchers* carries: *this is a noun, it is plural*. The Turkish *evlerinizden* carries: *this is a noun, it is plural, it belongs to you (plural), it is in the ablative case*. The Arabic اسْتَخْدَمَ (*istakhdama*, "he used") carries: *this is a verb, it is in Form X, it is past, active voice, third-person masculine singular, with the semantic role of seeking or requesting*.

We can count the number of distinct grammatical-information packets a language's word forms can express. Call this set `B(L)`. Its size, the **Structural Synthesis Ceiling**, is a property of the language's grammar that we can compute from the grammar engines alone, before any model trains.

Two quantities follow:

- `H(L)`, the **grammatical Shannon entropy** of word forms in `L`. How much information, on average, does a word in this language carry in its grammar? English: 1.43 bits. Mandarin: small. Turkish: 4.97 bits. Arabic: 5.44 bits.

- `ρ(L)`, the **structural recoverability coefficient**. How much of `H(L)` can a surface-only parser recover, just by looking at the word? English: 0.89 (almost everything is on the surface). Turkish: 0.85 (slot-stacked affixes are visible). Arabic: 0.59 (the non-concatenative root-and-pattern fusion hides about 40% of the information behind the consonantal skeleton).

The product `ρ(L) · H(L)` is the **effective grammatical information density**: how much grammatical information a tokeniser can pre-encode for the language. English: 1.28 bits. Mandarin: small. Arabic: 3.20 bits. Turkish: 4.20 bits.

The framework's central prediction is:

> The parameter rebate that morphology-aware tokenisation delivers over a BPE baseline is monotonically ordered by `ρ(L) · H(L)`. Higher `ρ · H` languages get larger savings.

Phase 1 (a six-model preliminary experiment at 2-million-parameter scale on three languages) confirmed the ranking: English smallest rebate, Arabic in the middle, Turkish largest. The magnitudes did not behave as a single linear function; they implied a per-bit coefficient that varied by 40-fold across the three languages. We named this empirical pattern the **Agglutinative Compounding Effect** and identified two readings that Phase 1 evidence cannot distinguish:

- **Interpretation A**: the rebate is genuinely super-linear in `ρ · H`. Languages at the high-recoverability pole get disproportionately large savings.
- **Interpretation B**: the rebate is linear, but the Hoffmann scaling-law derivative used to convert observed test-loss reductions into implied parameter rebates is unreliable in the Chinchilla-suboptimal regime Phase 1 occupied.

Phase 2 — the experiment this repository is now ready to deploy — is designed to discriminate between these interpretations by training at properly-trained Chinchilla-optimal scales across all four languages.

Phase 2 also tests a second prediction added during the project's development. Arabic's morphology stores information on three orthogonal axes:

- **Surface-recoverable**: what `ρ(L)` captures, accessible to any surface-only parser
- **Lexicon-recoverable**: the root identity, accessible only when the parser knows the root inventory
- **Semantic-class-recoverable**: the wazn semantic role (185 classes), accessible only when the parser knows the templatic pattern's semantic function

The **Templatic Lexical Surplus** is the framework's name for the rebate that the second and third axes contribute beyond the first. A preliminary two-tier Arabic experiment in Phase 1 measured the root-axis surplus at +0.082, +0.077, and +0.058 nats across three rungs of a scale ladder, persistent even where the first-tier rebate inverted at higher scales. Phase 2 will measure the wazn-semantic-axis contribution on top of that, completing the three-way decomposition.

---

## The four grammar engines

Each engine is a substantial piece of work. Together they encode the grammatical regularities of four typologically distant languages as Python.

### Mandarin (ZH)

`morph_efficiency_project/scripts/engines/zh_engine.py`

Per character, the engine returns the character itself, its Kangxi radical (one of 214), and a semantic class derived from the radical (e.g. 子 → HUMAN_RELATION, 木 → TREE_WOOD, 水 → WATER_LIQUID). A bigram disambiguation pass resolves the polysemous closed-class words: 只 between a numeral and a noun is a classifier, but between a subject and a verb it is an adverb; 把 in a 我把书读完了 frame is the ADP that introduces a BA-construction, but in 一把刀 it is itself a classifier.

The engine also classifies words by part of speech (NOUN, VERB, ADV, PRON, PART, ADP, CLF, AUX, NUM, DET, CONJ, PUNCT, PROPN, FOREIGN), with an open-class fallback that handles content words the closed-class lexicon does not list.

### English (EN)

`morph_efficiency_project/scripts/engines/en_engine.py`

A recursive multi-pass decomposer. Three passes per word:

- **Inflection peel**: -s, -ed, -ing, -er, -est, possessive 's
- **Derivational suffix peel**: -er (agent), -ing (gerund), -ness, -ment, -ity, -ation, -ize, -ist, -ism, -able, -ful, -less, -ous, -ish, -al, -hood, -ship, -ic, and others
- **Derivational prefix peel**: re-, un-, dis-, mis-, pre-, post-, anti-, sub-, super-, non-, in-/im-/il-/ir-, de-, en-/em-, over-, under-, out-, fore-, mid-, semi-, multi-, mega-

With guards that prevent over-stripping. `NO_MENT_STRIP` protects Latin-fused words like *experiment*, *document*, *segment*, *garment*, *cement*, *moment* from losing their final syllable. `NO_PREFIX_PEEL_BASES` protects *comment*, *instrument*, *refer*, *commit*, and other words whose initial syllable looks like a productive prefix but is not. The agent-vs-comparative `-er` disambiguation checks whether the bare stem is a known adjective: *taller* → adjective comparative, *writer* → noun agent.

Irregular forms (*went* → *go*, *children* → *child*, *was* → *be*, *better* → *good*) are resolved through a lookup table. POS is preserved through each derivation step: `-ness` → NOUN, `-ize` → VERB, `-ly` → ADV, `-able` → ADJ.

### Turkish (TR)

`morph_efficiency_project/scripts/engines/tr_engine.py`

A holistic decomposer that, for each word, enumerates candidate analyses in parallel across six branches (nominal-decomp, verbal-decomp, derivation pre-pass, copular, progressive vowel-collapse, `-ki` relational adjective) and picks the highest-scoring one using deterministic tie-breaks.

The nominal slot stack is `root → DERIV → NUM → POSS → CASE`, enforced strictly. The verbal stack is `root → DERIV → VOICE → NEG → TENSE → MOOD → PERSON_NUM`. Vowel harmony is normalised so `-den` and `-dan` both emit `case=ABL`. Buffer consonants (the `y` between vowel-final stems and vowel-initial suffixes, the `n` in 3SG-poss izafet constructions, the `s` in vowel-final possessive forms) are properly handled rather than left in the stem.

Capitalised Turkish words that do not match a productive inflection are recognised as proper nouns: *Ahmet*, *İstanbul*, *Türkiye* → POS = PROPN with empty tag bundle, rather than the bogus VERB analyses earlier versions of the engine produced.

The engine also resolves the genuinely ambiguous surface forms with neighbour context: *evin* before a noun-with-POSS suffix is genitive (an izafet construction), but sentence-final or before a verb it is a 2SG-possessive subject.

### Arabic (AR)

`morph_efficiency_project/scripts/engines/ar_engine.py`

The largest engine, ~1,900 lines. Four steps per word:

- **Step A: clitic stripping**. Proclitics (the conjunctions و and ف, the prepositions ب, ل, ك, the definite article ال, the future marker سـ, the emphasis لـ, the interrogative أ) and enclitics (object pronouns, dual and feminine plural endings, second-person verb agreement, the energetic nun) are recognised as separate tag values. The circumfix لَـ ... ـنَّ is reunited as a single SWORN_ASSERTION feature after both halves have been stripped independently.

- **Step B: template matching**. The consonantal skeleton of the stem is matched against 348 awzān in `configs/ar_templates.json`. Output is a templatic category (FORM_VII_PASSIVE_INTRANS, NOM_DERIVED, MASDAR_FORM_X, and so on).

- **Step B′: wazn-class lookup**. Each matched template is annotated with its `semantic_role` value from the templates configuration. There are 185 distinct semantic roles spanning verbal-form classes (FORM_I_BARE through FORM_XII_INTENSIVE_HABITUAL), derived nominal classes (اسْم الْفَاعِل, اسْم الْمَفْعُول, اسْم الْآلَة, اسْم الزَّمَان وَالْمَكَان, the masdar inventory, الصِّفَة الْمُشَبَّهَة, صِيغَة الْمُبَالَغَة, النِّسْبَة, اسْم التَّفْضِيل), broken-plural classes, and a long tail of weakness-specific variants that distinguish ناقص from أجوف from مثال from مهموز from مضعّف instances of the same logical pattern. This is what makes the wazn-class stream possible.

- **Step C: root extraction**. The consonant skeleton is matched against 7,142 roots in `configs/ar_roots.json`, with weak-root resolution that prepends و for مثال roots, substitutes the right middle radical for أجوف, restores the final radical for ناقص, geminates for مضعّف, and normalises hamza variants (أ، إ، آ، ؤ، ئ) to ء.

The engine emits all four pieces as separate input streams: the surface, the feature bundle, the root, and the wazn class. Sentence-level guards then enforce the rules of النحو والصرف: that the حروف الناسخة (إنّ, أنّ, كأنّ, لكنّ, ليت, لعلّ) assign the accusative case to المبتدأ; that the أفعال الناسخة (كان, أصبح, ليس, etc.) assign nominative to اسمها and accusative to خبرها; that الإضافة requires the مضاف to be indefinite and the مضاف إليه to be definite-genitive; that الحال is نكرة منصوبة.

---

## The sentence-grammar layer

A late addition to the architecture. Each grammar engine analyses words one at a time and proposes part-of-speech assignments based on the word's own morphology. But some ambiguities can only be resolved by looking at neighbouring words. *Run* in English is a noun or a verb depending on what precedes and what follows. *Evin* in Turkish is a genitive or a possessive depending on what comes next. *把* in Mandarin is a classifier or an ADP depending on whether a verb follows. *مَدْرَسَة* in Arabic is a place noun or a feminine teacher noun depending on context.

The sentence-grammar layer lives at `morph_efficiency_project/scripts/engines/grammar/`. It contains:

- A shared `common.py` with sentence-segmentation helpers (handles `.`, `!`, `?`, `;`, `؟`, `؛`, Chinese `。！？；…`, common abbreviations like *Dr.*, *vb.*, *yy.*)
- `en_grammar.py`, `ar_grammar.py`, `tr_grammar.py`, `zh_grammar.py`, each exposing three functions:
  - `split_into_sentences(text)`: segment the input on punctuation
  - `disambiguate_pos(tokens)`: walk the sentence, use neighbour context to resolve POS ambiguities the morphology alone could not settle
  - `validate_sentence(tokens)`: check the token sequence against the language's allowed structural templates, return (True, "ok") or (False, "rejection reason in the language's own grammatical terminology")

The rejection messages use the host language's own grammar tradition: Arabic guards raise `"إنّ تنصب المبتدأ"`, `"الفعل يطلب فاعلًا يليه"`; Turkish raises `"bildirme cümlesinde fiil sonda olmalı"`, `"ad öbeği sırası yanlış"`; Mandarin raises `"把构式：把后需有宾语再接动词"`. A linguist can audit the encoded grammar by reading the function names and the messages alone.

151 new tests cover the sentence-grammar layer, all passing.

---

## The multi-stream MiniGPT

`mini_experiment/run_mini.py`

A small decoder-only transformer that supports N input embedding streams summed at the input layer:

```python
x = sum(stream_embedding[name][token_ids[name]] for name in stream_configs)
```

Stream layouts per regime:

| Regime | Streams |
|---|---|
| Baseline (all languages) | 1: `tok` |
| EN morph, TR morph | 2: `tok` + `feat` |
| ZH morph | 2: `char` + `radical_class` |
| AR morph | 4: `tok` + `feat` + `root` + `wazn` |

The transformer downstream is identical across all regimes: same number of layers, same model dimension, same attention heads, same feed-forward dimension. Only the embedding tables differ. A `parameter_breakdown()` method returns the per-stream embedding parameter count, the transformer-block parameter count, and the head parameter count, so the parameter-matched comparison can be verified at training time.

Five tests confirm the architecture is correct (1-stream baseline matches expected parameter count, 2-stream EN morph adds exactly `29 * model_dim` extra parameters, 4-stream AR morph keeps all transformer-block sizes identical to baseline, forward pass produces the expected output shape, backward pass produces non-zero gradients for every stream).

---

## The tokenisation pipeline

`morph_efficiency_project/scripts/tokenize_for_training.py`

Reads each language's Wikipedia training corpus, runs each token through the appropriate engine, and writes per-stream integer arrays to disk along with their vocabulary tables. The script is idempotent and supports `--smoke` for fast verification on 100 lines per split and `--full --force` for full-corpus production runs.

Includes a per-language analyse-result cache so the engine is not re-invoked for the same surface form across the vocab-build and encoding passes. Cuts Turkish full-corpus wall-clock from a projected 30+ hours to 16 minutes.

Final full-corpus vocabulary sizes (after specials):

| Language | Stream | Vocab size | Notes |
|---|---|---:|---|
| ZH | baseline | 32,000 | character-level BPE cap |
| ZH | morph_surface | 32,000 | character + radical composite |
| ZH | morph_bundle | 131 | observed feature bundles |
| ZH | morph_radical | 214 | full Kangxi inventory |
| EN | baseline | 32,000 | BPE cap |
| EN | morph_surface | 2,558 | engine-emitted composite tokens |
| EN | morph_bundle | 21 | observed feature bundles |
| TR | baseline | 32,000 | BPE cap |
| TR | morph_surface | 32,000 | engine-emitted composite tokens |
| TR | morph_bundle | 469 | observed feature bundles |
| AR | baseline | 32,000 | BPE cap |
| AR | morph_surface | 32,000 | engine-emitted composite tokens |
| AR | morph_bundle | 1,450 | observed feature bundles |
| AR | morph_root | 7,142 | closed set from `ar_roots.json` |
| AR | morph_wazn | 185 | closed set from `ar_templates.json:semantic_role` |

The integer streams (`.npy` files in `mini_experiment/data/`) are gitignored because they are derived from the raw `.txt` corpora and rebuildable. The vocabulary tables (`.json` files in `mini_experiment/tokenizers/`) are committed.

---

## The trainer and the AWS launcher

`morph_efficiency_project/scripts/train_model.py` is the trainer. CLI:

```bash
python train_model.py --lang ar --regime morph --model-dim 128 --layers 4 \
    --max-tokens 5_000_000 --batch-size 32 --seq-len 128 \
    --eval-every 1000 --save-every 5000 \
    --output-dir runs/ar_morph_phase1
```

It loads the per-stream `.npy` files for the requested (language, regime) pair, builds the corresponding multi-stream MiniGPT, trains with AdamW under a cosine learning-rate schedule with linear warmup, logs training loss every 50 steps, evaluation loss every 1,000 steps, and saves a full checkpoint every 5,000 steps. Supports `--resume` to pick up from a checkpoint after interruption.

`morph_efficiency_project/scripts/aws/launch_run.py` is the cloud launcher. CLI:

```bash
# Dry run: writes the SageMaker estimator config, requirements.txt, and a
# hand-runnable submit.py to scripts/aws/_generated/<tag>/, prints the
# cost estimate, S3 paths, and IAM requirements. No AWS calls made.
python launch_run.py --lang ar --regime morph --model-dim 128 \
    --instance ml.g5.xlarge --max-tokens 5_000_000 \
    --tag phase1-ar-morph

# Real deploy (requires boto3, sagemaker, and AWS credentials configured)
python launch_run.py --deploy --lang ar --regime morph --model-dim 128 \
    --instance ml.g5.xlarge --max-tokens 5_000_000 \
    --tag phase1-ar-morph
```

`morph_efficiency_project/scripts/aws/README.md` documents the deployment: IAM role setup, S3 bucket layout, dry-run vs deploy, the eight `(lang, regime)` cell tags in canonical order, monitoring via CloudWatch, retrieval via `aws s3 sync`, troubleshooting.

Cost estimate for the headline rung at 30 million parameters and Chinchilla-optimal token-to-parameter ratio (~600 million training tokens per cell): on `ml.g5.xlarge` at $1.41/hour, approximately $420 per cell, $3,400 for the full eight-cell sweep. On `ml.g5.12xlarge` at $7.09/hour with 3× faster turnaround, approximately $640 per cell, $5,100 for the sweep. Both well inside the $24,000 credit budget.

---

## The test suite

4,283 tests across the four languages, all passing.

```bash
# Run the whole project test suite
cd C:/Users/Sameh\ AbuRadi/Desktop/BA_01
python -X utf8 -m pytest morph_efficiency_project/tests/ -q
```

Per language:

| Language | Tests | Pass | Coverage |
|---|---:|---:|---|
| ZH | 551 | 551 | Comprehensive engine + sentence-grammar + adversarial + smoke + radical-class layer |
| EN | 1,563 | 1,563 | Inflection, derivation (multi-pass), prefix, irregular, agent-vs-comparative -er, Latin-fused -ment, derivation-chain POS preservation, sentence-grammar, regression, stress, adversarial |
| TR | 662 | 662 | Strict slot order, vowel harmony, all CASE × all POSS, TAM, voice, negation, mood, derivational morphology, irregular verbs, copular and existential, proper-noun fallback, deterministic tie-breaks |
| AR | 1,455 | 1,455 | All Forms I–XII, weak roots (ناقص، أجوف، مثال، مهموز، مضعّف), all masdar patterns, broken plurals, active and passive participles, derived nominal templates, clitic stacking, closed-class particles, hamza normalisation, sentence-grammar with نواسخ, idafa, hal-clause, and adjective agreement guards |

Plus the multi-stream MiniGPT architecture tests: 5 tests confirming parameter accounting, forward pass shape, and backward gradient flow into every stream.

---

## The manuscript

`manuscript/tex/` contains the Cambridge submission draft. Eight sections:

1. **Abstract** — friendly tone, every paragraph polished for linguist accessibility
2. **Introduction** — sets up the puzzle, sketches the framework, names the contributions
3. **Related work** — morphological typology, BPE and morph-aware tokenisation, scaling laws, emergence, Green AI and equity. Plus paragraphs added for Chinese sub-character literature (Sun, Shi, Cao) and Arabic computational morphology (Buckwalter, Habash and Roth's MADA, Pasha's MADAMIRA).
4. **Framework** — the math definitions of ρ(L), H(L), the rebate equation, the curve-shift prediction. Plus an architecture subsection documenting the engine + sentence-grammar two-layer composition, the four engines and their stream counts, the 185-class wazn taxonomy, and the input-embedding sum.
5. **Case studies** — Mandarin (added), English, Turkish, Arabic. Each one walks through the morphology, gives a worked decomposition, reports |B(L)|, H(L), ρ(L), ρ·H.
6. **Results** — Phase 1 numbers and the three-rung scale ladder. The numerical content will be replaced when the Phase 2 AWS run completes.
7. **Discussion** — Interpretation A vs B, consequences under each, limitations, threats to validity.
8. **Conclusion** — what the paper establishes; what has been built since the original draft (wazn-class layer, sentence-grammar layer, Mandarin engine); the research programme of remaining follow-ups (Cross-Semitic transfer, per-model loss attribution on the Arabic compositional bucket, low-resource edge-deployment showcase).

Every Arabic word in the manuscript is vocalised with tashkil for unambiguous reading. The bidirectional rendering is handled by `polyglossia`. The Chinese characters use SimSun. The build is reproducible with `tectonic main.tex --outdir _build`.

Title:
> **Morphology-Aware Tokenization as a Capacity Lever**
> A Cross-Linguistic Framework for Parameter-Efficient Language Models

---

## Bundle distribution analysis

`morph_efficiency_project/logs/summary/bundle_distribution_report.md`

For each language, the report counts how often each grammatical bundle appears in 20,000 training sentences and plots the frequency distribution on log-log axes (Zipf form).

| Language | Unique bundles | Zipf exponent | Distribution health |
|---|---:|---:|---|
| Mandarin (ZH) | 136 | 2.04 | Single bundle dominates (60.2% of mass) — consistent with Mandarin being isolating and low-H; the model's grammar signal in the ZH-morph regime comes from the radical-class stream, not the feature-bundle stream |
| English (EN) | 29 | 2.58 | Steep, heavy head with thin tail (normal Zipf-like shape) |
| Turkish (TR) | 1,837 | 2.71 | Steep (normal) |
| Arabic (AR) | 1,147 | 2.40 | Steep (normal) |

The Mandarin finding is a real architectural signal, not a problem: the framework predicts a small `ρ·H` for Mandarin because of its low H, and the bundle distribution confirms that the feature-bundle stream carries little information. The lexicon-semantic signal (the radical-class stream) is where the rebate, if any, will come from.

---

## How to reproduce

```bash
# 1. Clone and install
git clone <repo>
cd BA_01
pip install -r requirements.txt   # if you have one; otherwise: pip install numpy torch matplotlib pytest

# 2. Run the engine test suite
python -X utf8 -m pytest morph_efficiency_project/tests/ -q

# 3. Download the four-language Wikipedia corpora
python morph_efficiency_project/scripts/download_corpora.py

# 4. Tokenise on full corpus (writes .npy + vocab.json files)
python -u -X utf8 morph_efficiency_project/scripts/tokenize_for_training.py --full --force

# 5. Optionally rebuild the bundle distribution plots
python morph_efficiency_project/scripts/_plot_bundle_distribution.py

# 6. Local CPU smoke test (verifies the trainer works end-to-end)
python morph_efficiency_project/scripts/train_model.py \
    --lang en --regime baseline --model-dim 64 --layers 2 \
    --max-tokens 50000 --batch-size 4 --seq-len 32 \
    --eval-every 100 --save-every 500 \
    --output-dir /tmp/smoke_en_baseline

# 7. Build the manuscript PDF
cd manuscript/tex
tectonic main.tex --outdir _build

# 8. (When ready) Deploy to AWS
# Set up IAM role and S3 bucket per scripts/aws/README.md, then:
export MORPH_S3_BUCKET=morph-efficiency-<your-suffix>
export MORPH_SM_ROLE_ARN=arn:aws:iam::<account>:role/MorphEfficiencyTrainingRole
python morph_efficiency_project/scripts/aws/launch_run.py \
    --deploy --lang ar --regime morph --model-dim 128 \
    --instance ml.g5.xlarge --max-tokens 5_000_000 \
    --tag phase1-ar-morph
```

---

## Project structure

```
BA_01/
├── README.md                        (you are here)
├── experimental_contract.md         (pre-registered, frozen)
├── pipeline_diagrams.html           (illustrated overview of each engine pipeline)
├── morph_efficiency_project/
│   ├── configs/                     (per-language config: roots, templates, suffixes, irregulars, etc.)
│   │   ├── ar_roots.json            (7,142 Arabic roots)
│   │   ├── ar_templates.json        (348 awzān with semantic_role annotations)
│   │   ├── ar_vocab_space.json
│   │   ├── en_irregulars.json       (irregular English forms)
│   │   ├── en_derivations.json
│   │   ├── en_phrasal_verbs.json
│   │   ├── en_compounds.json
│   │   ├── tr_suffixes.json
│   │   ├── tr_derivations.json
│   │   ├── zh_classifiers.json
│   │   ├── zh_particles.json
│   │   ├── zh_radicals.json         (Kangxi radical to semantic class map)
│   │   ├── model_config.json
│   │   └── training_config_*.json
│   ├── docs/engine_specs/           (per-language engine design docs)
│   ├── scripts/
│   │   ├── engines/
│   │   │   ├── ar_engine.py         (~1,900 lines)
│   │   │   ├── en_engine.py
│   │   │   ├── tr_engine.py
│   │   │   ├── zh_engine.py
│   │   │   ├── shared.py            (TokenInfo, MorphVocab, per-token validators)
│   │   │   ├── grammar/
│   │   │   │   ├── ar_grammar.py
│   │   │   │   ├── en_grammar.py
│   │   │   │   ├── tr_grammar.py
│   │   │   │   ├── zh_grammar.py
│   │   │   │   └── common.py
│   │   │   └── __init__.py
│   │   ├── aws/
│   │   │   ├── launch_run.py        (SageMaker estimator launcher)
│   │   │   └── README.md            (deployment guide)
│   │   ├── tokenize_for_training.py (the production tokeniser pipeline)
│   │   ├── train_model.py           (the trainer)
│   │   ├── compute_bundle_space.py  (audits possible / validated / observed bundle counts per language)
│   │   ├── _audit_ar_bundles.py     (audits Arabic engine-validator agreement)
│   │   ├── _audit_training_readiness.py
│   │   ├── _plot_bundle_distribution.py
│   │   ├── make_figures.py
│   │   ├── verify_tex.py
│   │   ├── compute_hl.py
│   │   ├── download_corpora.py      (Hugging Face Wikipedia loader)
│   │   ├── tokenize_morph_engine.py (legacy phase-1 tokeniser)
│   │   ├── tokenize_tier2_ar.py     (legacy Arabic 2-tier tokeniser)
│   │   ├── train_tier2_ar.py        (legacy phase-1 trainer)
│   │   ├── run_scale_ladder.py
│   │   ├── eval_lm.py
│   │   ├── eval_morphology.py
│   │   ├── eval_downstream.py
│   │   ├── fit_alpha.py
│   │   ├── aggregate_ladder.py      (in legacy/)
│   │   ├── make_ladder_figures.py   (in legacy/)
│   │   ├── _audit.py
│   │   └── _smoke_pipeline.py
│   ├── tests/
│   │   ├── ar_morph/
│   │   │   ├── test_ar_engine_comprehensive.py
│   │   │   ├── test_ar_engine_templates.py
│   │   │   ├── test_ar_engine_regression.py
│   │   │   ├── test_ar_sentence_grammar.py
│   │   │   └── (etc.)
│   │   ├── en_morph/
│   │   │   ├── test_en_engine_comprehensive.py
│   │   │   ├── test_en_engine_adversarial.py
│   │   │   ├── test_en_engine_derivation.py
│   │   │   ├── test_en_engine_inflection.py
│   │   │   ├── test_en_engine_regression.py
│   │   │   ├── test_en_engine_smoke.py
│   │   │   ├── test_en_engine_stress.py
│   │   │   └── test_en_sentence_grammar.py
│   │   ├── tr_morph/
│   │   │   ├── test_tr_engine_comprehensive.py
│   │   │   ├── test_tr_engine_adversarial.py
│   │   │   ├── test_tr_engine_nominal.py
│   │   │   ├── test_tr_engine_stress.py
│   │   │   ├── test_tr_engine_verbal.py
│   │   │   └── test_tr_sentence_grammar.py
│   │   ├── zh_morph/
│   │   │   ├── test_zh_engine_comprehensive.py
│   │   │   ├── test_zh_engine_adversarial.py
│   │   │   ├── test_zh_engine_derivation.py
│   │   │   ├── test_zh_engine_smoke.py
│   │   │   └── test_zh_sentence_grammar.py
│   │   ├── conftest.py
│   │   └── _base/
│   ├── logs/summary/
│   │   ├── ar_engine_audit.md
│   │   ├── en_engine_audit.md
│   │   ├── tr_engine_audit.md
│   │   ├── zh_engine_audit.md
│   │   ├── ar_bundle_gap_report.md
│   │   ├── training_readiness_audit.md
│   │   ├── bundle_distribution_report.md
│   │   ├── bundle_space.json
│   │   ├── bundle_dist_zh.png
│   │   ├── bundle_dist_en.png
│   │   ├── bundle_dist_tr.png
│   │   ├── bundle_dist_ar.png
│   │   └── bundle_dist_combined.png
│   └── legacy/                      (phase-1 scripts that are no longer in the active path)
│       ├── aggregate_ladder.py
│       ├── make_ladder_figures.py
│       └── run_scale_ladder.py
├── mini_experiment/
│   ├── run_mini.py                  (the multi-stream MiniGPT model + Phase 1 training loop)
│   ├── test_minigpt_multistream.py
│   ├── eval_agreement.py
│   ├── tokenizers/                  (per-language vocabulary tables in JSON, committed)
│   └── data/                        (raw .txt corpora and .npy integer streams; gitignored, rebuildable)
└── manuscript/
    └── tex/
        ├── main.tex
        ├── references.bib
        └── sections/
            ├── sec_01_abstract.tex
            ├── sec_02_introduction.tex
            ├── sec_03_related_work.tex
            ├── sec_04_framework.tex
            ├── sec_05_case_studies.tex
            ├── sec_06_results.tex
            ├── sec_07_discussion.tex
            └── sec_08_conclusion.tex
```

---

## How this evolved

The project did not start in the shape it is in now. Worth saying out loud what changed and why.

**Phase 1 covered three languages.** The original experiment trained six small models for English, Arabic, and Turkish at 2-million-parameter scale, observed the ranking prediction holding and the magnitudes diverging by 40-fold, and named the Agglutinative Compounding Effect. That was the Phase 1 manuscript.

**Five other engines existed but did not make the cut.** German (fusional), Spanish (regular fusional), Hungarian (agglutinative-fusional), Swahili (classificatory), and Basque (polypersonal ergative isolate) had grammar engines in the repository but were not in the experimental contract's headline scope. To keep the experimental phase focused, those five engines were removed (commits document the deletions) and the project narrowed to the four typologically-most-distinct languages.

**Mandarin was added.** The original plan covered analytic (English), agglutinative (Turkish), and templatic (Arabic). Mandarin was added as the fourth language to give the framework an isolating endpoint, and because the Kangxi radical system turned out to be the structural analog of Arabic's wazn at a different scale: a non-concatenative semantic-class signal that sits behind the surface form.

**The engines went through a sustained quality push.** Comprehensive test suites were written for each language. Initial pass rates were around 50%. Across several rounds of agent-coordinated engine fixes, the rates climbed: ZH 100%, EN 100%, TR 99.85% (one self-contradiction in the test spec, not the engine), AR 99.93% (one masdar/place ambiguity in the test spec). After test-spec reconciliation, all four reached 100%.

**The sentence-grammar layer was added in response to a specific concern.** The architecture as originally designed did per-word morphological analysis only, leaving POS ambiguity for the model to resolve from neighbour context. A late design pass added the per-language grammar layer described above: context-aware POS resolution plus structural validation with native-language rejection messages.

**The wazn-class layer was added when the Arabic engine's full taxonomy surfaced.** The original 2nd-tier Arabic experiment used a 3-stream architecture: surface, bundle, root. During the engine quality push, the 185 distinct `semantic_role` values in `ar_templates.json` were properly propagated through Step B′ of the engine and exposed as a fourth input stream. This is what makes the four-stream Arabic architecture in the current manuscript.

**The TR engine got cached at the eleventh hour.** The Turkish full-corpus tokenisation was projected to take 30+ hours because the engine's worst-case decomposition path runs at ~25 ms per word. Adding a per-(language, surface) memoisation pass cut wall-clock to 16 minutes. The memoisation is now in `tokenize_for_training.py` and helps all four languages, not just Turkish.

**Every Arabic word in the manuscript got vocalised.** A late editorial pass added tashkil to every Arabic word that lacked it, so Arabic-reading reviewers can read the awzān unambiguously. The `polyglossia` package was added to the preamble so the script flows right-to-left.

**The manuscript voice was deliberately polished.** Each section had a tone pass to lead with what something IS before naming it, to replace CS-only jargon with linguist-readable equivalents, and to keep the writing accessible to a reader whose home discipline is linguistics rather than machine learning. Reviewers in the target venue (Cambridge NLP Press) are mostly linguistically trained; the voice matches.

---

## Acknowledgements

Compute funded by Deniz Sertkan's $24,000 AWS credit donation. This experiment could not run without it. The credits cover two phases: the four-language proof-of-concept this manuscript reports, and the downstream phase of building a native Turkish reasoning-capable small language model using the technique once it is proven.

Supervised by Fabian Geier at CODE University of Applied Sciences, Berlin. The framework and its empirical predictions are the work of the corresponding author. The architecture, code, tests, audits, manuscript revisions, and many of the linguistic decisions involved extensive collaboration with the Claude Code agent across hundreds of dispatches; the design choices are the author's, the implementation work was shared.

The cross-linguistic scope of this work owes a debt to the morphological-typology tradition (Greenberg, Comrie, Haspelmath) and to the long line of computational morphology systems that made it tractable to build per-language grammar engines as standalone Python modules (Buckwalter's Arabic stem dictionary, the MADA / MADAMIRA tradition, the Unicode Unihan project for the Kangxi radical inventory, the Universal Dependencies project for cross-linguistic POS conventions).

---

## License

To be added. Until then, please treat this repository as a research preview associated with the corresponding author's pending submission. If you want to use the engines or the framework, contact the author.
