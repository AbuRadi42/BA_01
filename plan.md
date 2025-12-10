You are Kiro, an AI implementation agent.

Your task is to design, train, and evaluate six toy-scale language models:

- English: en_base (baseline), en_morph (morphology-aware)
- Arabic: ar_base (baseline), ar_morph (morphology-aware)
- Turkish: tr_base (baseline), tr_morph (morphology-aware)

For each language, the baseline and morphology-aware models must:
- Share the same architecture and training budget
- Use the same raw corpus and data splits
- Differ only in the tokenization and use of morphological information

Follow the instructions below step by step.

---

## 0. Global setup

0.1 Programming environment

- Use Python
- Required libraries:
  - pytorch (with CUDA if available)
  - transformers
  - datasets
  - sentencepiece (or tokenizers)
  - numpy
  - pandas
  - matplotlib

- Language specific tools:
  - English: spacy or stanza with POS + morphology
  - Arabic: camel_tools or another Arabic morphological analyzer
  - Turkish: a Turkish morphological analyzer or segmenter (for example Zemberek via wrapper or any python-based tool)

0.2 Model architecture (shared across all 6 models)

For every model (baseline and morph, all languages), use:

- Decoder-only transformer (GPT style)
- Number of layers: 6
- Hidden size: 256
- Number of attention heads: 4
- Feed-forward dimension: 1024
- Context length: 256 tokens
- Vocabulary size per tokenizer: 8000 to 12000 (fixed within each language, same for base and morph)
- Precision: bfloat16 or float16 if supported, otherwise float32

You will parametrize vocabulary size per tokenizer but keep model architecture identical within each language pair.

---

## 1. Project structure

Create the following directory layout:

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
    compute_metrics.py
  logs/
    training/
    evaluation/
  configs/
    model_config.json
    training_config_en.json
    training_config_ar.json
    training_config_tr.json
  notebooks/
    analysis.ipynb
````

---

## 2. Data collection and parity

Goal: For each language (en, ar, tr) build a corpus that is shared between baseline and morphology-aware variants, with strict split parity.

2.1 Data sources per language

* For each of en, ar, tr:

  * Collect modern, standard text from open corpora such as:

    * Wikipedia dumps
    * OPUS (TED talks, news, etc.)
    * Tatoeba sentences or similar resources
  * Target size (rough guideline):

    * Training: around 10 million tokens
    * Validation: around 1 million tokens
    * Test: around 1 million tokens

2.2 Raw corpus files

For each language L in {en, ar, tr}:

* Save line-based text files:

  * `data/raw/L/train.txt`
  * `data/raw/L/val.txt`
  * `data/raw/L/test.txt`
* Each line is one sentence or short document segment.

2.3 Split parity

* Use the same raw files for baseline and morphology-aware experiments.
* When shuffling and splitting:

  * Fix a random seed per language
  * Perform the split once
  * Reuse these same splits for both tokenization regimes

2.4 Script

Implement `scripts/download_data.py` that:

* Downloads or reads the needed corpora
* Creates `train.txt`, `val.txt`, `test.txt` for each language
* Logs approximate token count (whitespace based) for sanity

---

## 3. Baseline tokenization per language

Goal: Standard subword tokenization without awareness of morphology.

3.1 Train baseline tokenizer

For each language L:

* Input: `data/raw/L/train.txt`
* Train a SentencePiece (unigram or BPE) tokenizer with:

  * Vocabulary size: 8000 to 12000
  * Character coverage: 0.9995
* Save tokenizer model and config to:

  * `tokenizers/L_base/`

3.2 Tokenize splits

For each language L and split S in {train, val, test}:

* Load `tokenizers/L_base/` tokenizer
* Tokenize all sentences in `data/raw/L/S.txt`
* Save token ids in a format suitable for training, for example:

  * `data/processed/L/baseline/S_tokens.npy` (numpy array)
  * or a Hugging Face `datasets` arrow file with tokenized data
* Record:

  * Total number of tokens in each split
  * Average tokens per sentence

Store these statistics in a JSON file, for example:
`logs/evaluation/L_baseline_token_stats.json`.

3.3 Script

Implement `scripts/preprocess_baseline.py` to perform all the above for en, ar, tr.

---

## 4. Morphology-aware pipeline per language

Goal: Incorporate morphological segmentation and features into the tokenization and embeddings.

4.1 Define data structures

Define a python data structure for morphological analysis:

```python
class TokenInfo:
    def __init__(self, surface, lemma, morphemes, features, pos):
        self.surface = surface        # original word
        self.lemma = lemma            # lemma or stem
        self.morphemes = morphemes    # list of morpheme strings in order
        self.features = features      # dict, e.g. {"num": "PL", "case": "ACC", ...}
        self.pos = pos                # coarse POS tag, e.g. "NOUN"
```

4.2 Morphological analyzers per language

For each language L implement:

```python
def analyze_sentence_L(sentence: str) -> List[TokenInfo]:
    ...
```

* Use language specific tools as follows:

English:

* Use spacy or stanza with English models.
* Extract:

  * lemma
  * POS
  * basic features such as number (singular/plural) and tense.

Arabic:

* Use camel_tools or another Arabic analyzer.
* Extract:

  * lemma
  * POS
  * features such as gender, number, case, person, tense, mood.

Turkish:

* Use a Turkish morphological analyzer (for example Zemberek bindings or any equivalent).
* Extract:

  * lemma
  * POS
  * features such as case, number, person, tense, aspect, mood.
  * morpheme sequence representing stems plus suffix chain.

For each sentence:

* Split into surface tokens (words)
* Call the analyzer tool for each word
* Convert analyzer output to a list of TokenInfo instances

4.3 Finite state like checks (light constraints)

Implement a simple rule checker per language:

```python
def check_morph_sequence_L(token_infos: List[TokenInfo]) -> bool:
    ...
```

Rules:

* Maintain a small set of allowed POS tags: {"NOUN", "VERB", "ADJ", "DET", "PRON"} plus others if needed.
* For each POS define allowed feature keys.

  * Example:

    * NOUN: number, case, gender
    * VERB: person, number, tense, aspect, mood
* Optionally, for Turkish, enforce approximate suffix order (case after number, etc.)
* For each TokenInfo:

  * If it has POS outside the allowed set, accept but flag.
  * If it has features inconsistent with POS, mark as invalid.
* Return True if no invalid tokens detected, False otherwise.

You will use this function later for:

* Sanity checking input data
* Evaluating generated sequences for agreement correctness

4.4 Morph-aligned tokenization (training tokenizer)

For each language L:

1. Generate morpheme-level training text:

   * For each sentence in `data/raw/L/train.txt`:

     * Run `analyze_sentence_L`
     * For each TokenInfo:

       * Use `morphemes` list
       * Join morphemes with a special separator that will mark morpheme boundaries.
         Example: use `"@"` between morphemes and `" "` between words.
     * Save this new string as one line in a morpheme-level training file, for example:

       * `data/processed/L/morph/train_morphemes.txt`

2. Train a SentencePiece tokenizer on `train_morphemes.txt` with:

   * Same vocabulary size as baseline tokenizer for that language
   * Treat the morpheme boundary marker such that merges do not cross it. A simple approach:

     * Treat "@" as a normal character but pre-tokenize so that merges primarily happen inside morphemes.
     * Or mark morpheme boundaries as separate tokens and configure SentencePiece to respect them.
   * Save tokenizer to `tokenizers/L_morph/`.

4.5 Morph-aligned tokenization (encoding data)

* For each split S in {train, val, test}:

  * Read `data/raw/L/S.txt`
  * For each sentence:

    * Run `analyze_sentence_L` to get TokenInfo list
    * Construct morpheme-level text exactly as for training
    * Encode with `tokenizers/L_morph/` tokenizer
    * Store:

      * token ids
      * optionally a mapping to underlying TokenInfo and morphemes for evaluation

* Save to:

  * `data/processed/L/morph/S_tokens.npy`
  * plus any needed metadata for evaluation.

* Record:

  * total tokens per split for morph regime
  * average tokens per sentence

Store these stats in `logs/evaluation/L_morph_token_stats.json`.

4.6 Feature serialization for model inputs

For morphology-aware models, you must supply both token ids and morphological features.

Design:

* Build a finite vocabulary of feature bundles.

  * For each TokenInfo, build a string like: `"pos=NOUN|num=PL|case=ACC"`
  * Collect all distinct bundles across the training corpus for that language.
* Assign each bundle a unique id.

In the model:

* For each token position, you will:

  * Associate a feature bundle id.
  * For tokens that are not the first morpheme of a word, you can:

    * Reuse the same feature bundle as the first morpheme of that word
    * Or use a special "no features" id
* The model input will consist of:

  * Token embeddings from the tokenizer ids
  * Feature embeddings from the feature bundle ids
  * Combine them by summation or concatenation followed by a linear projection

Store feature bundle vocabularies under:

* `tokenizers/L_morph/feature_bundles.json`

4.7 Script

Implement `scripts/preprocess_morph.py` to perform all morphology-aware preprocessing, including:

* Analyzing sentences
* Constructing morpheme-level text
* Training morph tokenizers
* Encoding splits
* Building feature bundles and ids

---

## 5. Model and training implementation

5.1 Model definition

* Implement a GPT-style decoder-only transformer model in PyTorch or use Hugging Face `AutoModelForCausalLM` with a custom config.
* Configuration:

  * `n_layer = 6`
  * `n_embd = 256`
  * `n_head = 4`
  * `ffn_dim = 1024`
  * `max_position_embeddings = 256`
* For baseline models:

  * Use standard embedding for tokens
* For morphology-aware models:

  * Define two embedding tables:

    * `token_embedding` for token ids
    * `feature_embedding` for feature bundle ids
  * Combine them at each position as:

    * `combined = token_embedding[token_id] + feature_embedding[feature_id]`

5.2 Training configuration

Define training hyperparameters common to all six models:

* batch size: choose a fixed value (for example 64 sequences) that fits GPU memory
* sequence length: 256 tokens
* optimizer: AdamW
* learning rate: 3e-4
* learning rate schedule: warmup for first N steps (for example 2000), then cosine decay
* weight decay: small value such as 0.01
* gradient clipping: optional, for example 1.0
* training steps:

  * either a fixed number of steps (for example 100k)
  * or a fixed total number of tokens processed (for example 500 million tokens per model)

Apply identical training budget for baseline and morph models of the same language.

5.3 Training script

Implement `scripts/train_lm.py` with arguments:

* `--language` one of {en, ar, tr}
* `--regime` one of {baseline, morph}
* `--config` path to language specific training config

Functionality:

* Load model config
* Load tokenizer and processed data for specified language and regime
* Instantiate model
* Run training loop:

  * For each step:

    * Sample a batch of token sequences (and feature bundles for morph regime)
    * Compute language modeling loss (cross entropy over next token)
    * Backpropagate and update parameters
    * Log:

      * step
      * loss
      * perplexity (exp(loss))
      * number of tokens processed so far
      * wall clock time
      * GPU memory usage if available
* Save:

  * final model weights
  * tokenizer
  * training logs to `logs/training/{language}_{regime}_training.json`

Train all six combinations:

* (en, baseline), (en, morph)
* (ar, baseline), (ar, morph)
* (tr, baseline), (tr, morph)

---

## 6. Core evaluation

6.1 Language modeling evaluation

Implement `scripts/eval_lm.py` which:

* Loads a trained model and tokenizer
* Evaluates on `val` and `test` splits for that language and regime
* Computes:

  * Average loss per token
  * Perplexity (exp(loss))
* Outputs a JSON report:

  * `logs/evaluation/{language}_{regime}_lm.json` with:

    * `val_loss`, `val_ppl`
    * `test_loss`, `test_ppl`
    * `num_tokens_val`, `num_tokens_test`

Run this for all six models.

---

## 7. Downstream tasks (simple)

Goal: Check whether morphology-aware models show advantages on simple tasks beyond next token prediction.

7.1 Task selection

Choose at least two task types that exist or can be approximated for all three languages:

1. Text classification (for example sentiment or topic):

   * Use or construct small labeled datasets per language with a similar label space.
   * For toy scale, some thousands of examples per language are enough.

2. Question answering or short summarization:

   * Use simple QA pairs or short summarization tasks per language.

7.2 Evaluation method

For each task and model:

* Option A: fine-tune the model with a classification head or QA head.
* Option B: keep model frozen and train a shallow classifier on top of the final hidden state.

Pick one method and use it consistently for all models.

7.3 Implementation

Extend `scripts/eval_lm.py` or create a separate `scripts/eval_downstream.py` to:

* Load model and tokenizer
* Load task dataset
* Train task head or probe
* Evaluate on task test set
* Log metrics:

  * Classification: accuracy, F1
  * QA or summarization: exact match, BLEU or ROUGE
  * Inference latency per example (average)

Store outputs in:

* `logs/evaluation/{language}_{regime}_task_{task_name}.json`

---

## 8. Morphology-specific evaluation

Goal: Quantify effects related to morphological richness and structure.

8.1 Tokens per meaning unit

Define a meaning unit as a content word (noun, verb, adjective) with its core inflectional features.

Procedure per language and regime:

* Take a subset of the test set (for example 10k sentences).
* For each sentence:

  * Run the morphological analyzer to get TokenInfo for each word.
  * Count the number of meaning units.
  * Count the number of tokens used by the model's tokenizer for that sentence.
* Compute:

  * Average tokens per meaning unit:
    `avg_tokens_per_unit = total_tokens / total_meaning_units`

Compare baseline vs morph for each language.

8.2 Agreement and inflection accuracy

Construct or use an evaluation set that tests:

* Subject verb agreement
* Case marking and number agreement for nouns
* Other language specific inflection properties

Procedure:

* For each evaluation sentence:

  * Treat the gold sentence as reference.
  * Option 1: ask the model to score the reference sentence and possibly corrupted variants.
  * Option 2: ask the model to generate continuations where agreement is needed.
* For outputs or scored candidates:

  * Use the morphological analyzer and `check_morph_sequence_L` to verify:

    * Is subject verb agreement correct?
    * Are required morphological features present and consistent?

Compute:

* Agreement accuracy per model:

  * fraction of items where the model prefers the correct form or generates the correct form.

8.3 Lemma plus feature bundle accuracy

* For a set of sentences:

  * Use ground truth morphological analysis of reference sentence to extract pairs (lemma, feature bundle) for target positions (for example verbs, core nouns).
  * Evaluate model outputs:

    * Map each generated or most likely word at those positions back to (lemma, feature bundle) using the analyzer.
  * Count correct matches of (lemma, feature bundle).

Compute:

* Accuracy per model and language:

  * `bundle_accuracy = correct_pairs / total_pairs`

8.4 Nats per morpheme

For a subset of evaluation sentences:

* For the morph regime:

  * Compute total loss (in nats) over tokens and divide by number of morphemes underlying those tokens.
* For baseline:

  * Use the analyzer to map surface words to morphemes and approximate loss per morpheme by distributing token loss across morphemes proportionally or equally.

Compute:

* Average nats per morpheme for baseline and morph.

8.5 Script

Implement `scripts/eval_morphology.py` that:

* For every language and regime:

  * Computes:

    * tokens per meaning unit
    * agreement and inflection accuracy
    * lemma plus feature bundle accuracy
    * nats per morpheme
  * Saves results to:

    * `logs/evaluation/{language}_{regime}_morph.json`

---

## 9. Metrics aggregation and comparison

Implement `scripts/compute_metrics.py` to read all JSON logs and produce:

9.1 Summary tables

* A table per language, with rows:

  * baseline model
  * morph model

* Columns for each of:

  * model size (number of parameters)
  * total tokens processed in training
  * total training wall time
  * validation and test perplexity
  * downstream task metrics
  * morphology metrics:

    * tokens per meaning unit
    * agreement accuracy
    * bundle accuracy
    * nats per morpheme

* A global table comparing:

  * en_base vs en_morph
  * ar_base vs ar_morph
  * tr_base vs tr_morph

9.2 Plots

* Learning curves:

  * loss vs tokens for baseline and morph per language
* Bar plots:

  * tokens per meaning unit (baseline vs morph for each language)
  * agreement accuracy (baseline vs morph)
  * bundle accuracy
  * nats per morpheme

Save numerical tables in CSV and plots as PNG into a folder such as `logs/summary/`.

---

## 10. Final summary artifact

Create a plain text or markdown file:

* `logs/summary/conclusion.md`

Contents:

* For each language (en, ar, tr):

  * A short paragraph summarizing:

    * How morphology-aware models compare to baselines in:

      * perplexity
      * downstream performance
      * morphology metrics
    * Whether morphology-aware training appears to give a measurable advantage per unit of compute.

* A final section answering:

  * Do Arabic and Turkish, as morphologically richer languages, show larger benefits from morphology-aware training than English?
  * Based on these toy-scale experiments, is it justified to invest in scaling up this research?

This completes the implementation plan.