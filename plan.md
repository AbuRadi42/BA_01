# Implementation Plan
## Morphological Efficiency in Multilingual Language Models
**Author:** Sameh AbuRadi
**Status:** Active — governed by experimental_contract.md

---

## 0. Global Setup

### 0.1 Programming Environment

- Python 3.10+
- pytorch (with CUDA, bfloat16)
- transformers
- datasets
- sentencepiece
- numpy, pandas, matplotlib

Language-specific tools:
- English: spacy or stanza (POS + morphology)
- Arabic: camel_tools or equivalent (Farasa as fallback)
- Turkish: Zeyrek (pure Python port of Zemberek, `pip install zeyrek`)

### 0.2 Model Architecture (identical for all 6 models)

Decoder-only GPT-style transformer.

| Parameter | Value |
|---|---|
| Layers | 24 |
| Hidden size | 1024 |
| Attention heads | 16 |
| FFN dimension | 4096 |
| Context length | 1024 tokens |
| Parameters | ~425M |
| Precision | bfloat16 |

Scale rationale: 425M parameters at 8.4B training tokens sits at the Chinchilla-optimal point (20 tokens/param). This is the minimum scale at which models produce coherent, interactive outputs suitable for demonstration.

**Vocabulary size is NOT a shared fixed parameter across all 6 models.** It is defined differently per regime:

- Baseline models (en_base, ar_base, tr_base): 32k BPE/unigram subword vocabulary, learned statistically from corpus frequency. No linguistic knowledge involved.
- Morph models (en_morph, ar_morph, tr_morph): vocabulary is derived from the grammar of each language. Each language has a structurally different morphological system, so each morph model follows a different vocabulary construction procedure. See section 4 for language-specific details.

For morphology-aware models only:
- Add a second embedding table for morphological feature bundles
- Combine: `combined = token_embedding[token_id] + feature_embedding[feature_id]`

### 0.3 Compute Infrastructure

- Platform: RunPod (A100 80GB, ~$0.79/hr) — primary
- Fallback: Lambda Labs (~$1.10/hr)
- Checkpoint every 1,000 steps to guard against session interruption
- Estimated total compute cost: $1,200–$1,500 for all 6 models

---

## 1. Project Structure

```text
morph_efficiency_project/
  data/
    raw/
      en/
      ar/
      tr/
    processed/
      en/
        baseline/
        morph/
      ar/
        baseline/
        morph/
      tr/
        baseline/
        morph/
  tokenizers/
    en_base/
    en_morph/
    ar_base/
    ar_morph/
    tr_base/
    tr_morph/
  models/
    en_base/
    en_morph/
    ar_base/
    ar_morph/
    tr_base/
    tr_morph/
  scripts/
    download_data.py
    preprocess_baseline.py
    preprocess_morph.py
    train_lm.py
    eval_lm.py
    eval_morphology.py
    eval_downstream.py
    compute_metrics.py
  logs/
    training/
    evaluation/
    summary/
  configs/
    model_config.json
    training_config_en.json
    training_config_ar.json
    training_config_tr.json
    ar_roots.json
    ar_templates.json
    ar_vocab_space.json
    tr_stems.json
    tr_suffixes.json
    tr_derivations.json
    en_irregulars.json
    en_derivations.json
    en_compounds.json
    en_phrasal_verbs.json
  dashboard/
    index.html
    app.js
    styles.css
  notebooks/
    analysis.ipynb
```

---

## 2. Data Collection and Parity

Goal: build a corpus per language shared between baseline and morph variants, with strict split parity.

### 2.1 Data Sources

| Language | Sources |
|---|---|
| English | Wikipedia EN, OPUS (TED/News), CC-100 EN |
| Arabic | Wikipedia AR, OPUS AR, CC-100 AR, OSIAN |
| Turkish | Wikipedia TR, OPUS TR, CC-100 TR |

### 2.2 Target Corpus Size

| Split | Tokens |
|---|---|
| Train | ~8B |
| Validation | ~200M |
| Test | ~200M |

### 2.3 Raw Corpus Files

For each language L in {en, ar, tr}:
- `data/raw/L/train.txt`
- `data/raw/L/val.txt`
- `data/raw/L/test.txt`

Each line is one sentence or short document segment.

### 2.4 Split Parity Rules

- Fix a random seed per language
- Perform the split once
- Reuse identical splits for both baseline and morph regimes

### 2.5 Script

`scripts/download_data.py`:
- Downloads corpora from Wikipedia, OPUS, CC-100
- Creates train/val/test splits per language
- Logs whitespace-based token counts per split

---

## 3. Baseline Tokenization (en_base, ar_base, tr_base only)

Goal: standard statistical subword tokenization with zero morphological awareness. This is the classical approach — the tokenizer learns purely from frequency patterns in the corpus. No grammar, no linguistic rules, no language-specific knowledge injected.

### 3.1 Train Baseline Tokenizer

For each language L in {en, ar, tr}:
- Input: `data/raw/L/train.txt`
- Train SentencePiece BPE tokenizer, vocab size 32k, character coverage 0.9995
- The tokenizer has no knowledge of morpheme boundaries, roots, stems, or grammatical categories
- Save to `tokenizers/L_base/`

### 3.2 Tokenize Splits

For each language L and split S in {train, val, test}:
- Tokenize `data/raw/L/S.txt` using `tokenizers/L_base/`
- Save token IDs to `data/processed/L/baseline/S_tokens.npy`
- Log total tokens and avg tokens per sentence to `logs/evaluation/L_baseline_token_stats.json`

### 3.3 Script

`scripts/preprocess_baseline.py` — runs all of the above for en, ar, tr.

---

## 4. Morphology-Aware Pipelines (en_morph, ar_morph, tr_morph)

Goal: replace statistical vocabulary construction with a grammar-first algorithmic analysis layer. Before any token ever reaches the model, each word is passed through a structured linguistic analysis pipeline grounded in the formal grammatical sciences of each language — النحو والصرف for Arabic, Dilbilgisi for Turkish, and morphological word-formation theory for English.

This is not a smarter tokenizer. It is a pre-training grammar engine. The model is taught the structure of the language algorithmically before it learns from statistics.

---

### 4.0 The Three-Step Grammar Engine (shared mechanism, language-specific rules)

Every word in every morph corpus passes through three sequential steps before becoming a token. The steps are the same across all three languages. The rules inside each step are language-specific.

```
Word
 │
 ▼
Step A: Clitic Stripping + Surface Tagging
         Detach grammatical particles that attach to the word surface.
         Tag the remaining base form with grammatical properties:
         POS, case, definiteness, number, gender, tense (if verb).
 │
 ▼
Step B: Template / Pattern Detection
         Match the base form against the known inventory of
         morphological templates for that language.
         If no template matches → tag as FOREIGN or PROPER.
         The template carries semantic and grammatical implications
         beyond what the surface form alone reveals.
 │
 ▼
Step C: Root / Stem Identification
         Extract the root or stem from the base form using the
         identified template.
         The root defines the semantic field and determines
         acceptable syntactic relationships (valency, governed
         prepositions, agreement requirements).
 │
 ▼
Tagged Token Representation:
  surface | clitics[] | template | root | tags{}
```

The output of this engine for each word is a fully tagged token representation. This representation — not a raw subword chunk — is what the morph model receives as input.

---

### 4.1 Shared Data Structure

```python
class TokenInfo:
    def __init__(self, surface, clitics, template, root, tags, pos):
        self.surface   = surface    # original word as it appears in text
        self.clitics   = clitics    # dict: {"pre": [...], "enc": [...]}
        self.template  = template   # morphological template string, or "FOREIGN"/"PROPER"
        self.root      = root       # root/stem string after template extraction
        self.tags      = tags       # dict of grammatical tags (language-specific keys)
        self.pos       = pos        # POS: "NOM" / "VERB" / "ADJ" / "ADV" / "PART" / "FOREIGN"
```

### 4.2 Shared Morpheme Sequence Validator

```python
def check_morph_sequence_L(token_infos: List[TokenInfo]) -> bool:
```

- Validates that each token's tag bundle is consistent with its POS
- Validates template is from the known inventory for that language (or flagged)
- For Turkish: validates suffix slot ordering
- Returns True if sequence is grammatically consistent, False otherwise
- Used for: corpus sanity checking and post-generation agreement evaluation

Per-language POS-to-allowed-tags rules:

**Arabic (`check_morph_sequence_ar`):**

| POS | Required tags | Optional tags | Invalid if present |
|---|---|---|---|
| VERB | tense, person, num, gender, voice | mood | case, def |
| NOM | num, gender | case, def | tense, person, mood |
| ADJ | num, gender | case, def | tense, person, mood |
| PART | — | — | tense, case, num, gender |

Additional Arabic rules:
- If `tense=IMP` (imperative) → `person` must be `2`, `voice` must be `ACT`
- If `voice=PASS` → `tense` cannot be `IMP`
- If `mood=JUS` → `tense` must be `PRES`
- If `def=DEF` → word must have had الـ proclitic or be an إضافة construction

**Turkish (`check_morph_sequence_tr`):**

Validates canonical Dilbilgisi slot order. For each word, the suffix chain must follow:

- Nominal: `[DERIV] → [NUM] → [POSS] → [CASE]` — no slot may appear after a slot that comes later in the order
- Verbal: `[DERIV] → [VOICE] → [NEG] → [TENSE] → [MOOD] → [PERSON+NUM]` — same constraint

Additional Turkish rules:
- If `polarity=NEG` → NEG slot must precede TENSE slot
- If `voice=CAUS` → verb must be transitive or intransitive (not already PASS)
- If `mood=IMP` → PERSON must be `2`, TENSE slot is absent

**English (`check_morph_sequence_en`):**

| POS | Allowed inflectional tags | Invalid combinations |
|---|---|---|
| NOUN | num, poss | tense, aspect, degree, person, voice |
| VERB | tense, aspect, person, voice | num (except via person), degree |
| ADJ | degree | tense, aspect, person, voice |
| ADV | degree | tense, aspect, person, voice, num |

Additional English rules:
- If `aspect=PERF` → `tense` must be `PAST` or `PRES`
- If `voice=PASS` → `aspect` must be `PERF` or `SIMPLE`
- If `degree=COMP` or `degree=SUPER` → POS must be `ADJ` or `ADV`

### 4.3 Shared Feature Tag Bundle

For each TokenInfo, serialize the grammatical tags as a bundle string:

```
"pos=VERB|tense=PAST|num=PL|person=3|gender=M|voice=ACTIVE"
```

- Collect all distinct bundles across the training corpus
- Assign each a unique integer ID
- Store at `tokenizers/L_morph/feature_bundles.json`
- Non-first morphemes of a word receive a `"no_features"` ID

---

### 4.4 ar_morph — Arabic Grammar Engine (النحو والصرف)

Arabic is a root-and-pattern (templatic) language. The grammatical sciences of النحو (syntax/inflection) and الصرف (morphological derivation) together define a complete formal system for analyzing every Arabic word. This pipeline implements that system algorithmically.

**Morphological system:** templatic (root + وزن pattern) + clitics, high morphological density, significant ambiguity without diacritics

**Analyzer:** camel_tools (primary), Farasa (fallback)

**Root lexicon source:** Doha Historical Dictionary of Arabic (معجم الدوحة التاريخي للغة العربية)
- ~300,000 lexical entries organized etymologically by root
- Covers Arabic from earliest attestations (~400 AD) through modern usage
- Explicitly designed to support Arabic NLP and language model development
- Store extracted root list as `configs/ar_roots.json`

**Pre-computed vocabulary space:**

Before any corpus is processed, cross the root lexicon with the full وزن inventory to pre-compute the theoretical Arabic word space:

```python
# Pseudocode
for root in ar_roots:
    for template in ar_templates:
        candidate = apply_template(root, template)
        if is_phonologically_valid(candidate):
            theoretical_vocab.add((root, template, candidate))
```

**`apply_template(root, template)`** — maps root consonants onto the F-A-L skeleton of the template:

- Arabic templates use ف-ع-ل as positional placeholders for root consonants
- First root consonant → replaces ف, second → replaces ع, third → replaces ل
- For quadriliteral roots: ف-ع-ل-ل (four positions)
- All vowels, diacritics (harakat), shadda, and sukun from the template are preserved exactly
- Weak roots (roots containing و، ي، ء) require special handling:
  - و or ي in root position may assimilate, elide, or change to a long vowel depending on template position
  - These alternations follow standard Arabic morphophonological rules (إعلال وإبدال)
  - If a weak root produces an irregular alternation in a given template, the alternated form is stored, not the raw substitution
- Implementation: iterate over template characters, replace ف/ع/ل with corresponding root consonant, preserve all other characters

**`is_phonologically_valid(candidate)`** — filters out phonologically impossible forms:

A candidate form is considered invalid if any of the following hold:

1. Two identical adjacent consonants with no intervening vowel (unless it is a valid geminate with shadda)
2. Word begins with a sukun (consonant cluster at word start is not permitted in Arabic)
3. The form contains no vowel at all (every Arabic word must have at least one vowel)
4. A weak consonant (و، ي) appears in a position where it would normally elide but has not been elided — raw substitution without applying إعلال
5. Hamza (ء) appears in a position that violates standard hamza orthography rules (e.g., ء after a long vowel should be ئ or ؤ)

Valid forms that pass all checks are added to the theoretical vocabulary space.

This gives a grammar-defined closed vocabulary. Every word encountered in the corpus is either:
- In the (root × template) space → fully analyzed
- A clitic-bearing form of the above → stripped and analyzed
- A proper noun → tagged `PROPER`
- A loanword/Arabized foreign word → tagged `FOREIGN`

The corpus filters the theoretical space down to attested forms. Unattested (root × template) combinations are valid but simply never appear — they don't pollute the vocabulary.

Store pre-computed space in `configs/ar_vocab_space.json`.

#### Step A — Clitic Stripping + Surface Tagging (النحو)

Proclitics to detect and strip (in order):
- Conjunctions: وَ، فَ (and, so/then)
- Prepositions: بِ، لِ، كَ (by/with, for/to, like)
- Definite article: الـ (marks definiteness — معرفة)

Enclitics to detect and strip:
- Pronoun suffixes: هُ، هَا، هُم، هُمَا، كَ، نَا etc. (attached object/possessive pronouns)

Tags assigned to the base form after stripping:

| Tag | Values | Arabic term |
|---|---|---|
| `pos` | NOM / VERB / ADJ / PART / FOREIGN | اسم / فعل / صفة / حرف |
| `case` | NOM / ACC / GEN | رفع / نصب / جر |
| `def` | DEF / INDEF | معرفة / نكرة |
| `num` | SG / DU / PL | مفرد / مثنى / جمع |
| `gender` | M / F | مذكر / مؤنث |
| `tense` | PAST / PRES / IMP / — | ماضي / مضارع / أمر |
| `person` | 1 / 2 / 3 / — | متكلم / مخاطب / غائب |
| `mood` | IND / SUBJ / JUS / — | مرفوع / منصوب / مجزوم |
| `voice` | ACT / PASS / — | معلوم / مجهول |

Note on diacritics: train and evaluate on diacritized text where available. Diacritics resolve most case and tense ambiguity. Log diacritization coverage rate per corpus.

#### Step B — Template Detection (الصرف — أوزان الصرف)

Match the stripped base form against the canonical inventory of Arabic morphological templates (أوزان). Each وزن carries grammatical and semantic implications beyond the surface form.

Core template inventory (non-exhaustive, to be fully enumerated in `configs/ar_templates.json`):

| Template (وزن) | Typical meaning | Example |
|---|---|---|
| فَعَلَ | basic past verb | كَتَبَ (wrote) |
| فَعِلَ | stative verb | عَلِمَ (knew) |
| فَاعِل | active participle / agent | كَاتِب (writer) |
| مَفْعُول | passive participle / patient | مَكْتُوب (written) |
| فِعَال | verbal noun (masdar) | كِتَاب (book/writing) |
| تَفْعِيل | verbal noun of Form II | تَعْلِيم (teaching) |
| اِفْتِعَال | verbal noun of Form VIII | اِكْتِسَاب (acquisition) |
| فَعَّال | intensive agent | عَلَّام (very knowledgeable) |
| مَفْعَلَة | place/instrument noun | مَكْتَبَة (library) |

If no template matches:
- Check against a proper noun list → tag `PROPER`
- Otherwise → tag `FOREIGN` (Arabized loanword, e.g., تِلِفِزْيُون)
- Both are valid tokens but flagged for separate analysis

#### Step C — Root Extraction (الجذر)

Once the template is identified, extract the triconsonantal or quadriconsonantal root by mapping the surface consonants onto the template's فاء-عين-لام (F-A-L) skeleton.

Example: كَاتِب → template فَاعِل → root ك-ت-ب (k-t-b)

Validate the extracted root against `configs/ar_roots.json` (sourced from the Doha Dictionary):
- Root found → confirmed, proceed
- Root not found → flag as `UNVERIFIED_ROOT`, log for review
- This validation step is only possible because of the pre-computed root lexicon — it's what makes the Doha Dictionary integration meaningful

The root determines:
- Semantic field (all words from ك-ت-ب relate to writing/recording)
- Acceptable prepositions and particles (تعدية الفعل)
- Whether the verb is transitive/intransitive and what cases it governs

Store root in TokenInfo. Root + template together form the core of the tagged token representation.

**Vocabulary construction:**
- Vocabulary tokens are: individual morphemes (root-in-template units) + clitics as separate tokens
- Each unique (root, template) realization is a vocabulary entry, drawn from the pre-computed space
- Clitics (وَ، فَ، بِ، الـ، هُ etc.) are a small closed-class vocabulary (~30–50 items)
- Vocabulary size is bounded by the pre-computed (root × template) space, filtered to corpus-attested forms
- Expected range: 20k–40k unique tokens

**Text construction:**
- Serialize each word as: `[PROCLITIC@]ROOT.TEMPLATE.TAGS[@ENCLITIC]`
- Example: وَكَتَبُوهَا → `وَ @ كتب.فَعَلَ.VERB.PAST.3.PL.M.ACT @ هَا`
- Train tokenizer on this structured representation
- Save to `tokenizers/ar_morph/`

---

### 4.5 tr_morph — Turkish Grammar Engine (Dilbilgisi)

Turkish is an agglutinative language. Its formal grammatical science, Dilbilgisi, defines a complete and largely unambiguous system for decomposing any Turkish word into its stem and an ordered chain of suffix slots. Unlike Arabic's templatic system, Turkish morphology is strictly concatenative — meaning is built by appending suffixes in a canonical left-to-right order, each slot carrying a specific grammatical function. A single Turkish word can encode what English expresses in a full clause.

**Morphological system:** agglutinative, strictly ordered suffix chaining, vowel harmony governs surface forms, highly productive, low structural ambiguity

**Analyzer:** Zeyrek (pure Python port of Zemberek — no JVM required)
- Install: `pip install zeyrek`
- Provides: morphological analysis, lemmatization, root extraction, suffix chain decomposition
- Internally uses Zemberek's stem lexicon and suffix inventory
- Preferred over raw Zemberek bindings for Python pipeline compatibility

**Stem lexicon source:** Zeyrek's internal stem lexicon (inherited from Zemberek)
- Contains the full inventory of native Turkish stems
- Queried directly at runtime via `analyzer.lexicon` — not serialized to disk
- A JSON dump would be 700k+ lines with no benefit since Zeyrek is already a pipeline dependency

**Formal reference:** Dilbilgisi — Turkish Grammar (Türk Dil Kurumu), Kornfilt (1997) *Turkish*, Lewis (1967) *Turkish Grammar*

**Pre-computed vocabulary space:**

Before corpus processing, extract Zeyrek's stem lexicon and cross it with the canonical suffix slot inventory to establish a closed, grammar-defined vocabulary boundary:

```python
# Pseudocode
for stem in zeyrek_stem_lexicon:
    for suffix_chain in valid_suffix_combinations(stem.pos):
        if obeys_vowel_harmony(stem, suffix_chain):
            theoretical_vocab.add((stem, suffix_chain))
```

Unlike Arabic, Turkish productivity is extremely high — the theoretical space is very large and not fully enumerable. The value here is establishing a validated stem list and a closed suffix inventory so that every corpus word is either:
- A known stem + valid suffix chain → fully analyzed
- A loanword stem + valid suffix chain → stem tagged `FOREIGN`, suffixes analyzed normally
- A proper noun → tagged `PROPER`
- An unanalyzable form → tagged `UNKNOWN`

Store validated suffix slot inventory in `configs/tr_suffixes.json`.

#### Vowel Harmony — Pre-processing Rule

Before any suffix analysis, vowel harmony must be understood as a surface realization rule, not a separate morpheme. Every suffix in Turkish has a canonical logical form and multiple surface variants determined by the last vowel of the preceding syllable.

Two harmony systems operate simultaneously:

Back/Front harmony:
- If the last vowel of the stem/preceding suffix is a back vowel (a, ı, o, u) → suffix takes back variant
- If front vowel (e, i, ö, ü) → suffix takes front variant

Rounding harmony (applies to high vowels in suffixes):
- If the last vowel is rounded (o, u, ö, ü) → high vowel in suffix becomes rounded (u/ü)
- If unrounded → high vowel becomes unrounded (ı/i)

Normalization rule: all surface suffix variants are normalized to their canonical logical form before template matching. Surface variant is stored separately in TokenInfo for reconstruction.

| Logical suffix | Surface variants | Function |
|---|---|---|
| `PL` | -lar / -ler | plural |
| `LOC` | -da / -de / -ta / -te | locative case |
| `ABL` | -dan / -den / -tan / -ten | ablative case |
| `DAT` | -a / -e | dative case |
| `ACC` | -ı / -i / -u / -ü | accusative case |
| `GEN` | -ın / -in / -un / -ün | genitive case |
| `PAST` | -dı / -di / -du / -dü / -tı / -ti | definite past tense |
| `NEG` | -ma / -me | negation |
| `PROG` | -iyor | present progressive |
| `FUT` | -acak / -ecek | future tense |
| `COND` | -sa / -se | conditional mood |
| `CAUS` | -tır / -tir / -dır / -dir | causative voice |

#### Step A — Suffix Stripping + Surface Tagging

Suffixes are stripped from right to left. The stripping order follows the reverse of the canonical Dilbilgisi slot order. Each stripped suffix is normalized to its logical form and its grammatical function is recorded as a tag.

**Inflectional suffixes** (purely grammatical, stripped in Step A):

| Tag | Values | Dilbilgisi category |
|---|---|---|
| `pos` | NOUN / VERB / ADJ / ADV / POSTP / CONJ | İsim / Fiil / Sıfat / Zarf |
| `num` | SG / PL | Tekil / Çoğul |
| `case` | NOM / ACC / DAT / LOC / ABL / GEN / INS | Yalın / Belirtme / Yönelme / Bulunma / Uzaklaşma / İlgi / Araç |
| `poss` | NONE / 1SG / 2SG / 3SG / 1PL / 2PL / 3PL | İyelik ekleri |
| `person` | 1 / 2 / 3 | Şahıs |
| `tense` | PAST_DEF / PAST_NARR / PRES_PROG / PRES_AORIST / FUT | Zaman |
| `aspect` | PERF / IMPERF / PROG / HAB | Görünüş |
| `mood` | IND / COND / OPT / IMP / NECESS / INF | Kip |
| `polarity` | POS / NEG | Olumlu / Olumsuz |
| `voice` | ACT / PASS / CAUS / RECIP / REFL | Çatı |

Note on tense: Turkish distinguishes definite past (-dı, witnessed) from narrative past (-mış, reported/inferred). This evidentiality distinction is linguistically significant and must be preserved as a tag — it affects meaning, not just form.

**Derivational suffixes** (change stem class or meaning, handled in Step B):
- These are not stripped in Step A — they are identified as part of the template in Step B
- Examples: -lık/-lik (forms abstract nouns: iyi → iyilik, goodness), -cı/-ci (forms agent nouns: araba → arabacı, driver), -laş (forms verbs from nouns: insan → insanlaşmak, to become human)

#### Step B — Suffix Chain Template Validation (Dilbilgisi slot order)

The "template" for Turkish is not a fixed pattern like Arabic أوزان — it is the canonical slot order defined by Dilbilgisi. Step B validates that the extracted suffix chain conforms to this order and identifies any derivational morphology present.

Canonical slot order for nominal words:
```
STEM → [DERIV] → [NUM] → [POSS] → [CASE]
```

Canonical slot order for verbal words:
```
STEM → [DERIV] → [VOICE] → [NEG] → [TENSE/ASPECT] → [MOOD] → [PERSON+NUM]
```

Derivational suffix inventory (to be fully enumerated in `configs/tr_derivations.json`):

| Suffix | Derives | Example |
|---|---|---|
| -lık / -lik | Noun → Abstract noun | iyi → iyilik (goodness) |
| -cı / -ci | Noun → Agent noun | araba → arabacı (driver) |
| -lı / -li | Noun → Adjective | su → sulu (watery) |
| -sız / -siz | Noun → Privative adj | su → susuz (waterless) |
| -laş | Noun/Adj → Verb | insan → insanlaşmak (to humanize) |
| -landır | Noun → Causative verb | güç → güçlendirmek (to strengthen) |
| -ış / -iş | Verb → Action noun | gel → geliş (coming, arrival) |
| -mak / -mek | Verb → Infinitive | git → gitmek (to go) |

If the suffix chain violates canonical slot order → flag via `check_morph_sequence_tr`, log, and mark token as `MALFORMED`.

If the stem is not found in `configs/tr_stems.json` (Zeyrek's lexicon) → flag as `FOREIGN`.

#### Step C — Stem Identification and Valency

After stripping all inflectional suffixes and identifying derivational morphology, the remaining base is the stem. Identify:

- Stem class: nominal (isim), verbal (fiil), adjectival (sıfat)
- For verbal stems: valency — what case(s) the verb governs
  - Intransitive (nesnesiz): no accusative object
  - Transitive (geçişli): takes accusative (-ı) object
  - Ditransitive: takes both accusative and dative (-a) objects
- Whether the stem is native Turkish or a loanword (`FOREIGN`)
- Compound stems: Turkish forms compounds by juxtaposition (e.g., başbakan = baş + bakan, prime minister) — detect and tag as `COMPOUND` with constituent stems listed

**Vocabulary construction:**
- Vocabulary tokens are: stems + individual logical suffix values as separate tokens
- Derivational suffixes are vocabulary tokens (they change meaning)
- Inflectional suffixes are tag carriers (they express grammatical relations)
- Suffix token vocabulary is small and closed (~150–200 logical suffix types), fully enumerated in `configs/tr_suffixes.json`
- Stem inventory validated against `configs/tr_stems.json` (Zeyrek's lexicon)
- Total expected range: 25k–50k unique tokens

**Text construction:**
- Serialize each word as: `STEM.POS[.DERIV] @ SUFFIX1.TAG @ SUFFIX2.TAG ...`
- Example: evlerden → `ev.NOUN @ PL @ ABL`
- Example: gitmeyecekler → `git.VERB @ NEG @ FUT @ 3PL`
- Example: iyilikten → `iyi.ADJ @ lık.DERIV.NOUN @ ABL`
- Example: arabacılar → `araba.NOUN @ cı.DERIV.AGENT @ PL`
- Train tokenizer on this suffix-chain representation, respecting `@` boundaries
- Save to `tokenizers/tr_morph/`

---

### 4.6 en_morph — English Grammar Engine

English is an analytic language. Its morphology is shallow compared to Arabic and Turkish — most grammatical relationships are expressed through word order and function words rather than inflection. However, English has a rich derivational morphology (word-formation) that is well-documented and formally enumerable. The grammar engine for English is grounded in the tradition of English descriptive grammar (Quirk et al. *A Comprehensive Grammar of the English Language*, Huddleston & Pullum *The Cambridge Grammar of the English Language*) and morphological word-formation theory.

The key distinction for English is between inflectional morphology (purely grammatical, does not change the word's category or core meaning) and derivational morphology (changes category or meaning, creates new lexical items). These are handled in different steps.

**Morphological system:** concatenative, low inflectional complexity, rich derivational system, significant irregular form inventory, productive compounding

**Analyzer:** spaCy (en_core_web_trf) or stanza

**Formal reference:** Quirk et al. (1985), Huddleston & Pullum (2002), Bauer (1983) *English Word-Formation*

#### Step A — Inflectional Stripping + Surface Tagging

Inflectional morphology in English is small and closed. Strip only inflectional affixes in Step A — these express grammatical relations without changing the word's category.

English inflectional inventory (complete):

| Affix | Function | Example |
|---|---|---|
| -s / -es | Noun plural | cat → cats |
| -'s | Possessive | cat → cat's |
| -s (3sg) | Verb 3rd person singular present | run → runs |
| -ed | Past tense / past participle | walk → walked |
| -ing | Present participle / gerund | run → running |
| -er | Comparative adjective/adverb | fast → faster |
| -est | Superlative adjective/adverb | fast → fastest |

**Irregular forms** — English has a significant inventory of irregular inflections that do not follow the above patterns. These must be handled via lookup table, not pattern matching:

| Category | Examples |
|---|---|
| Irregular plurals | mouse→mice, child→children, foot→feet, ox→oxen |
| Irregular past tense | go→went, be→was/were, have→had, do→did, see→saw |
| Irregular past participle | go→gone, be→been, write→written, break→broken |
| Suppletive comparatives | good→better→best, bad→worse→worst, far→further→furthest |

Store irregular form lookup table in `configs/en_irregulars.json`. If a word matches an irregular form, resolve it to its base and tag accordingly before proceeding.

Tags assigned after inflectional stripping:

| Tag | Values |
|---|---|
| `pos` | NOUN / VERB / ADJ / ADV / DET / PRON / PREP / CONJ / PART |
| `num` | SG / PL / — |
| `tense` | PAST / PRES / — |
| `aspect` | SIMPLE / PROG / PERF / PERF_PROG / — |
| `degree` | POS / COMP / SUPER / — |
| `person` | 3SG / NON3SG / — |
| `voice` | ACT / PASS / — |
| `poss` | YES / NO |

#### Step B — Derivational Pattern Detection (Word-Formation)

After inflectional stripping, the base form is matched against English derivational word-formation patterns. Derivational morphology creates new lexical items — it changes the word's category or core meaning.

**Suffixal derivation** (to be fully enumerated in `configs/en_derivations.json`):

| Pattern | Derives | Semantic function | Example |
|---|---|---|---|
| STEM + -tion / -sion / -ation | V → N | action/process nominalization | educate → education |
| STEM + -ness | ADJ → N | state/quality nominalization | dark → darkness |
| STEM + -ity / -ty | ADJ → N | state/quality nominalization | real → reality |
| STEM + -ment | V → N | result/process nominalization | develop → development |
| STEM + -er / -or / -ar | V/N → N | agent / instrument | teach → teacher |
| STEM + -ist | N → N | adherent / practitioner | art → artist |
| STEM + -ism | N → N | doctrine / system | capital → capitalism |
| STEM + -ize / -ise | N/ADJ → V | verbalization | modern → modernize |
| STEM + -ify | N/ADJ → V | verbalization | simple → simplify |
| STEM + -ly | ADJ → ADV | adverbialization | quick → quickly |
| STEM + -al / -ial | N → ADJ | relational adjective | nation → national |
| STEM + -ous / -ious | N → ADJ | having quality of | danger → dangerous |
| STEM + -ful | N → ADJ | full of | hope → hopeful |
| STEM + -less | N → ADJ | without | hope → hopeless |
| STEM + -able / -ible | V → ADJ | capable of being | read → readable |
| STEM + -ing | V → ADJ | active/ongoing quality | interest → interesting |
| STEM + -ed | V → ADJ | passive/resultant quality | interest → interested |

**Prefixal derivation:**

| Pattern | Derives | Semantic function | Example |
|---|---|---|---|
| un- + STEM | ADJ/V → ADJ/V | negation / reversal | happy → unhappy |
| re- + STEM | V → V | repetition | write → rewrite |
| pre- + STEM | V/N → V/N | before | view → preview |
| mis- + STEM | V → V | wrongly | understand → misunderstand |
| over- + STEM | V/ADJ → V/ADJ | excess | estimate → overestimate |
| under- + STEM | V/ADJ → V/ADJ | insufficiency | estimate → underestimate |
| dis- + STEM | V/ADJ → V/ADJ | negation / reversal | agree → disagree |
| non- + STEM | N/ADJ → N/ADJ | negation | standard → non-standard |
| anti- + STEM | N/ADJ → N/ADJ | opposition | war → anti-war |
| inter- + STEM | N/ADJ → N/ADJ | between | national → international |

**Compounding** — English productively forms new words by combining two or more stems:
- Noun + Noun: software, blackboard, database, keyboard
- Adj + Noun: greenhouse, blackbird, blueprint
- Verb + Noun: breakfast, drawback
- Detect compounds using a compound lexicon + heuristic (two known stems concatenated or hyphenated)
- Tag as `COMPOUND`, store constituent stems: `software → soft.ADJ + ware.NOUN`
- Store compound lexicon in `configs/en_compounds.json`

**Phrasal verbs and multi-word expressions:**
- English has a large inventory of phrasal verbs (give up, look into, take off) where the particle changes the verb's meaning entirely
- These are semantically opaque — `give up` ≠ `give` + `up`
- Detect using a phrasal verb lexicon
- Tag as `PHRASAL_VERB`, store as a single token with the particle: `give_up.VERB`
- Store lexicon in `configs/en_phrasal_verbs.json`

If no derivational pattern matches and the word is not a known stem:
- Check proper noun list → tag `PROPER`
- Check loanword/foreign word list → tag `FOREIGN`
- Otherwise → tag `UNKNOWN` and log for review

#### Step C — Base Form / Stem Identification and Argument Structure

After inflectional stripping and derivational pattern identification, the base form is the vocabulary stem. Identify:

- Syntactic category of the base (NOUN / VERB / ADJ / ADV)
- For verbal stems: argument structure
  - Intransitive: no object (sleep, arrive, fall)
  - Transitive: takes NP object (eat, write, see)
  - Ditransitive: takes two objects (give, send, show)
  - Copular: takes predicative complement (be, seem, become)
  - Clausal complement: takes that-clause or infinitive (believe, want, expect)
- For nominal stems: countability (count noun vs mass noun) — affects number tagging

**Vocabulary construction:**
- Vocabulary tokens are: base stems + derivational affixes as separate tokens + phrasal verb units
- Inflectional affixes are tag carriers only, not vocabulary tokens
- Derivational affixes are vocabulary tokens (~150–200 types)
- Compound constituents are separate tokens
- Vocabulary size = attested stem inventory + derivational affix set + phrasal verb lexicon
- Expected range: 15k–25k unique tokens

**Text construction:**
- Serialize each word as: `BASE.POS[.DERIV_CHAIN] @ INFL_TAG1 @ INFL_TAG2 ...`
- Inflectional tags follow the base; derivational structure is encoded in the base representation
- Example: running (progressive) → `run.VERB @ PROG`
- Example: unhappiness → `happy.ADJ @ un.NEG_PREFIX @ ness.NOM_SUFFIX`
- Example: teachers → `teach.VERB @ er.AGENT_SUFFIX @ PL`
- Example: gave up → `give_up.PHRASAL_VERB @ PAST`
- Example: databases → `data.NOUN+base.NOUN.COMPOUND @ PL`
- Train tokenizer on this structured representation, respecting `@` boundaries
- Save to `tokenizers/en_morph/`

---

### 4.7 Script

`scripts/preprocess_morph.py` — runs the three-step grammar engine for the specified language.

```
python scripts/preprocess_morph.py --language {en,ar,tr}
```

Outputs per language:
- `data/processed/L/morph/S_tokens.npy` for each split
- `data/processed/L/morph/S_feature_ids.npy` (feature bundle IDs aligned to tokens)
- `tokenizers/L_morph/` tokenizer
- `tokenizers/L_morph/feature_bundles.json`
- `configs/ar_roots.json` (Arabic — root lexicon from Doha Dictionary)
- `configs/ar_vocab_space.json` (Arabic — pre-computed root × template space)
- `configs/ar_templates.json` (Arabic — full وزن inventory)
- `configs/tr_stems.json` (Turkish — stem lexicon from Zeyrek)
- `configs/tr_suffixes.json` (Turkish — canonical suffix slot inventory)
- `configs/tr_derivations.json` (Turkish — derivational suffix inventory)
- `configs/en_derivations.json` (English — derivational pattern inventory)
- `configs/en_irregulars.json` (English — irregular inflection lookup table)
- `configs/en_compounds.json` (English — compound lexicon)
- `configs/en_phrasal_verbs.json` (English — phrasal verb lexicon)
- `logs/evaluation/L_morph_token_stats.json`
- `logs/evaluation/L_morph_foreign_rate.json` (rate of FOREIGN/PROPER/UNKNOWN tags per language)

---

## 5. Model and Training

### 5.1 Model Definition

Use Hugging Face `AutoModelForCausalLM` with custom GPT config or implement directly in PyTorch.

Config (all 6 models — shared architecture):
```json
{
  "n_layer": 24,
  "n_embd": 1024,
  "n_head": 16,
  "ffn_dim": 4096,
  "max_position_embeddings": 1024
}
```

Vocabulary size per model:
- `en_base`, `ar_base`, `tr_base`: `vocab_size = 32000` (fixed BPE)
- `en_morph`: `vocab_size` = size of attested morpheme inventory (expected 15k–25k)
- `ar_morph`: `vocab_size` = size of attested (root × pattern) + clitic space (expected 20k–40k)
- `tr_morph`: `vocab_size` = size of attested (stem × suffix chain) space (expected 25k–50k)

Vocab size for morph models is determined after preprocessing and logged before training begins.

Morph models additionally define:
- `feature_embedding` table (size: number of feature bundles × 1024)
- Combined input: `token_embedding[id] + feature_embedding[bundle_id]`

### 5.2 Training Hyperparameters

| Hyperparameter | Value |
|---|---|
| Batch size | 32 sequences (adjust to fit A100 80GB) |
| Sequence length | 1024 tokens |
| Optimizer | AdamW |
| Learning rate | 3e-4 |
| LR schedule | Linear warmup 2000 steps, then cosine decay |
| Weight decay | 0.01 |
| Gradient clipping | 1.0 |
| Total tokens | 8.4B per model |
| Checkpoint interval | Every 1,000 steps |

Identical budget applied to baseline and morph models within each language.

### 5.3 Training Script

`scripts/train_lm.py --language {en,ar,tr} --regime {baseline,morph} --config configs/training_config_L.json`

Logs per step: loss, perplexity, tokens processed, wall clock time, GPU memory
Saves to: `logs/training/{language}_{regime}_training.json`

---

## 6. Core Evaluation

`scripts/eval_lm.py` — for each model:
- Evaluate on val and test splits
- Compute average loss per token and perplexity
- Save to `logs/evaluation/{language}_{regime}_lm.json`

Fields: `val_loss`, `val_ppl`, `test_loss`, `test_ppl`, `num_tokens_val`, `num_tokens_test`

---

## 7. Computational Economics Metrics

### 7.1 Compute Cost Metrics

For each model:
- Estimate FLOPs per forward pass
- Estimate FLOPs per token
- Measure inference latency (ms/sample)
- Measure training steps to reach a fixed validation loss threshold

### 7.2 Attention Distribution Metrics

On test set:
- Gini coefficient of attention weights (per head, averaged across layers)
- Shannon entropy of attention weights (per head, averaged across layers)

Save to: `logs/evaluation/{language}_{regime}_compute.json`

---

## 8. Morphology-Specific Evaluation

`scripts/eval_morphology.py` — for each language and regime:

### 8.1 Tokens per Meaning Unit

- Meaning unit = content word (noun/verb/adj) with its inflection
- Count meaning units and model tokens over 10k test sentences
- `avg_tokens_per_unit = total_tokens / total_meaning_units`

### 8.2 Agreement Accuracy

- Construct evaluation cases for subject-verb agreement, case marking, number agreement
- Use `check_morph_sequence_L` to verify model outputs
- Report fraction of items where model produces or prefers the correct form

### 8.3 Lemma + Feature Bundle Accuracy

- Extract ground truth (lemma, feature bundle) pairs from reference sentences
- Map model outputs back to (lemma, bundle) via analyzer
- `bundle_accuracy = correct_pairs / total_pairs`

### 8.4 Nats per Morpheme

- Morph regime: total loss (nats) / number of underlying morphemes
- Baseline: distribute token loss across morphemes proportionally

Save to: `logs/evaluation/{language}_{regime}_morph.json`

---

## 9. Downstream Tasks

`scripts/eval_downstream.py` — at least two tasks per language:

1. Text classification (sentiment or topic) — accuracy, F1
2. Short QA or summarization — exact match, BLEU or ROUGE

Concrete dataset sources per language:

| Language | Classification | QA / Summarization |
|---|---|---|
| English | SST-2 (sentiment, HuggingFace `datasets`) | SQuAD v1.1 (extractive QA, HuggingFace `datasets`) |
| Arabic | HARD (hotel reviews sentiment, available on HuggingFace as `hard`) | ARCD (Arabic Reading Comprehension Dataset, HuggingFace `datasets`) |
| Turkish | TTC-3600 (Turkish text classification, topic labels) | MLQA Turkish subset (HuggingFace `datasets`, `mlqa`, `mlqa.tr.tr`) |

All datasets are freely available and loadable via `datasets.load_dataset()`. No manual download required.

Method: frozen model + shallow probe (single linear layer) trained on final hidden state — consistent across all six models.

Log inference latency per example.
Save to: `logs/evaluation/{language}_{regime}_task_{task_name}.json`

---

## 10. Metrics Aggregation

`scripts/compute_metrics.py` — reads all JSON logs and produces:

Summary table per language:

| Model | Params | Train Tokens | Train Time | Test PPL | Tokens/Unit | Agreement Acc | Bundle Acc | FLOPs/Token | Latency |
|---|---|---|---|---|---|---|---|---|---|

Plots:
- Loss vs tokens (learning curves, baseline vs morph per language)
- Tokens per meaning unit (bar, baseline vs morph)
- Agreement accuracy (bar)
- FLOPs vs accuracy (Pareto view)

Save CSVs and PNGs to `logs/summary/`.

---

## 11. Optional: Compute-Penalized Variant (English Only)

Train two additional English models:
- `en_base_lambda`
- `en_morph_lambda`

Modified loss: `L_total = L_task + λ * C_compute`

Where `C_compute = L1 norm of attention weights + L1 norm of FFN activations`

Try λ ∈ {1e-5, 1e-4}. Evaluate accuracy vs FLOPs tradeoff.

---

## 12. Presentation Dashboard

A browser-based dashboard (`dashboard/index.html`) built with HTML, Tailwind CSS, and JavaScript (Chart.js):

- Loads experiment metrics from JSON output files
- Learning curves per language (baseline vs morph)
- Side-by-side efficiency comparisons
- Tokens per meaning unit, agreement accuracy, FLOPs/token visualized as charts
- Plain-language labels for non-technical audiences
- Runs locally — no server required, open in browser

The dashboard presents findings neutrally. No conclusions are pre-written. The data is displayed as measured.

**Expected JSON schema the dashboard reads from:**

`logs/evaluation/{language}_{regime}_lm.json`:
```json
{
  "language": "ar",
  "regime": "morph",
  "val_loss": 2.31,
  "val_ppl": 10.07,
  "test_loss": 2.34,
  "test_ppl": 10.38,
  "num_tokens_val": 200000000,
  "num_tokens_test": 200000000
}
```

`logs/training/{language}_{regime}_training.json` (array of step entries):
```json
[
  {
    "step": 1000,
    "loss": 4.21,
    "ppl": 67.4,
    "tokens_processed": 32000000,
    "wall_time_sec": 3600,
    "gpu_memory_gb": 74.2
  }
]
```

`logs/evaluation/{language}_{regime}_morph.json`:
```json
{
  "language": "ar",
  "regime": "morph",
  "tokens_per_meaning_unit": 1.43,
  "agreement_accuracy": 0.87,
  "bundle_accuracy": 0.79,
  "nats_per_morpheme": 1.12
}
```

`logs/evaluation/{language}_{regime}_compute.json`:
```json
{
  "language": "ar",
  "regime": "morph",
  "flops_per_token": 850000000,
  "inference_latency_ms": 12.4,
  "attn_gini": 0.61,
  "attn_entropy": 2.83
}
```

`logs/evaluation/{language}_{regime}_task_{task_name}.json`:
```json
{
  "language": "ar",
  "regime": "morph",
  "task": "sentiment",
  "accuracy": 0.83,
  "f1": 0.82,
  "inference_latency_ms": 11.1
}
```

The dashboard aggregates all of the above into a single view per language pair.

---

## 13. Final Output

`logs/summary/conclusion.md`

For each language (en, ar, tr): a short paragraph reporting measured comparisons across perplexity, downstream performance, and morphology metrics.

Final section addresses:
1. Does morphology-aware preprocessing reduce tokens per meaning unit?
2. Does it reduce compute cost at equal performance?
3. Do Arabic and Turkish benefit more than English?
4. Is the efficiency gain significant enough to justify scaling research?

Only quantified findings are reported. No interpretation beyond the data.
