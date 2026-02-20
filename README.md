# Morphological Efficiency in Multilingual Language Models
**Author:** Sameh AbuRadi  
**Governed by:** `experimental_contract.md`

This project trains and evaluates six language models across three languages — English, Arabic, and Turkish — each with a classically trained baseline and a grammar-aware morphology-informed variant. The experiment tests whether teaching a model the grammatical structure of its language before training reduces learning cost and improves linguistic understanding.

---

## Directory Structure

### `data/`
All corpus data, raw and processed.

- `data/raw/en/` — Raw English text corpus (train.txt, val.txt, test.txt). Source: Wikipedia EN, OPUS, CC-100.
- `data/raw/ar/` — Raw Arabic text corpus. Source: Wikipedia AR, OPUS AR, CC-100 AR, OSIAN.
- `data/raw/tr/` — Raw Turkish text corpus. Source: Wikipedia TR, OPUS TR, CC-100 TR.
- `data/processed/en/baseline/` — English corpus tokenized using the classical BPE tokenizer (no grammar knowledge). Stored as token ID arrays.
- `data/processed/en/morph/` — English corpus processed through the grammar engine and encoded with the morphology-aware tokenizer. Includes token IDs and feature bundle IDs.
- `data/processed/ar/baseline/` — Arabic corpus tokenized classically.
- `data/processed/ar/morph/` — Arabic corpus processed through the النحو والصرف grammar engine (clitic stripping, وزن detection, root extraction) and encoded with the morphology-aware tokenizer.
- `data/processed/tr/baseline/` — Turkish corpus tokenized classically.
- `data/processed/tr/morph/` — Turkish corpus processed through the Dilbilgisi grammar engine (suffix chain decomposition, vowel harmony normalization) and encoded with the morphology-aware tokenizer.

---

### `tokenizers/`
Trained tokenizer models, one per model variant.

- `tokenizers/en_base/` — Classical BPE tokenizer for English (32k vocab, learned from corpus frequency).
- `tokenizers/en_morph/` — English morphology-aware tokenizer (vocab derived from stem inventory + derivational affix set). Also contains `feature_bundles.json`.
- `tokenizers/ar_base/` — Classical BPE tokenizer for Arabic (32k vocab).
- `tokenizers/ar_morph/` — Arabic morphology-aware tokenizer (vocab derived from Doha Dictionary root list × وزن template inventory). Also contains `feature_bundles.json`.
- `tokenizers/tr_base/` — Classical BPE tokenizer for Turkish (32k vocab).
- `tokenizers/tr_morph/` — Turkish morphology-aware tokenizer (vocab derived from Zeyrek stem lexicon × suffix slot inventory). Also contains `feature_bundles.json`.

---

### `models/`
Trained model weights and checkpoints, one directory per model.

- `models/en_base/` — Classically trained English baseline model (~425M params).
- `models/en_morph/` — Grammar-informed English model. Same architecture, different tokenization and feature embeddings.
- `models/ar_base/` — Classically trained Arabic baseline model.
- `models/ar_morph/` — Grammar-informed Arabic model, trained with النحو والصرف prior.
- `models/tr_base/` — Classically trained Turkish baseline model.
- `models/tr_morph/` — Grammar-informed Turkish model, trained with Dilbilgisi prior.

---

### `scripts/`
All executable Python scripts for the full pipeline.

- `download_data.py` — Downloads and splits corpora for all three languages. Outputs train/val/test.txt per language.
- `preprocess_baseline.py` — Trains classical BPE tokenizers and encodes all splits for en_base, ar_base, tr_base.
- `preprocess_morph.py` — Runs the three-step grammar engine per language and encodes all splits for en_morph, ar_morph, tr_morph.
- `train_lm.py` — Trains a single model. Accepts `--language` and `--regime` arguments. Used for all six models.
- `eval_lm.py` — Evaluates a trained model on val and test splits. Computes loss and perplexity.
- `eval_morphology.py` — Computes morphology-specific metrics: tokens per meaning unit, agreement accuracy, lemma+bundle accuracy, nats per morpheme.
- `eval_downstream.py` — Evaluates models on downstream tasks (text classification, QA/summarization) using a frozen model + shallow probe.
- `compute_metrics.py` — Aggregates all evaluation logs into summary tables and plots.

---

### `logs/`
All output logs from training and evaluation.

- `logs/training/` — Per-step training logs for each model (loss, perplexity, tokens processed, wall time, GPU memory).
- `logs/evaluation/` — Evaluation results per model: LM metrics, compute metrics, morphology metrics, downstream task metrics, token stats.
- `logs/summary/` — Aggregated comparison tables (CSV), plots (PNG), and the final `conclusion.md`.

---

### `configs/`
Configuration files for models, training, and grammar engine resources.

- `model_config.json` — Shared model architecture config (24 layers, hidden 1024, 16 heads, FFN 4096, context 1024).
- `training_config_en.json` — Training hyperparameters for English models.
- `training_config_ar.json` — Training hyperparameters for Arabic models.
- `training_config_tr.json` — Training hyperparameters for Turkish models.
- `ar_roots.json` — Arabic root lexicon containing 7,142 roots sourced from the [Doha Historical Dictionary of Arabic](https://www.dohadictionary.org/root) (معجم الدوحة التاريخي للغة العربية), organized by triconsonantal/quadriconsonantal structure.
- `ar_templates.json` — Full inventory of Arabic morphological templates (أوزان الصرف) with semantic annotations.
- `ar_vocab_space.json` — Pre-computed Arabic vocabulary space: all valid (root × template) combinations, filtered to phonologically valid forms.
- `tr_stems.json` — Not stored on disk. Zeyrek's internal stem lexicon (`analyzer.lexicon`) is queried directly at runtime in `preprocess_morph.py`. Serializing 67k entries to JSON is redundant when the library is already a dependency.
- `tr_suffixes.json` — Canonical Turkish suffix slot inventory with logical forms and vowel harmony variant mappings.
- `tr_derivations.json` — Turkish derivational suffix inventory with category-change annotations.
- `en_irregulars.json` — English irregular inflection lookup table (irregular plurals, past tenses, comparatives).
- `en_derivations.json` — English derivational pattern inventory (suffixal and prefixal word-formation rules).
- `en_compounds.json` — English compound word lexicon with constituent stem annotations.
- `en_phrasal_verbs.json` — English phrasal verb lexicon (semantically opaque verb+particle combinations).

---

### `dashboard/`
Browser-based presentation dashboard for non-technical audiences.

- `index.html` — Main dashboard page. Opens directly in a browser, no server required.
- `app.js` — Loads experiment metrics from JSON logs and renders all charts and comparisons.
- `styles.css` — Tailwind CSS styling.

The dashboard presents all findings neutrally. No conclusions are pre-written — the data is displayed as measured.

---

### `notebooks/`
- `analysis.ipynb` — Jupyter notebook for exploratory analysis, ad-hoc metric inspection, and visualization during development.
