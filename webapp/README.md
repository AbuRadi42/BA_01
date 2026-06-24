# Tokenisation demo (Flask)

A small mobile-friendly web app that shows a sentence tokenised two ways, side by
side, so a reader can *see* the project's methodology:

1. **Classic tokeniser** : the BPE baseline (the SentencePiece model the project
   trains its baseline models on; character-level for Mandarin, which has no
   subword model).
2. **Grammar-aware tokeniser** : the project's per-language engine, which
   decomposes each word into its grammatical streams.

Stream counts per language match the architecture: ZH/EN/TR expose 2 streams,
Arabic exposes 4 (surface, feature bundle, root, wazn class).

## Run

```bash
pip install flask sentencepiece
python webapp/app.py                 # http://127.0.0.1:5000
python webapp/app.py --host 0.0.0.0  # reach it from a phone on the same network
```

Then open the URL, pick a language (ZH → EN → TR → AR), and type or load an
example sentence.

## Notes

- The four engines load from `morph_efficiency_project/scripts/engines`; the
  baseline models load from `mini_experiment/tokenizers/{en,ar,tr}_base.model`.
  No corpus or `.npy` data is needed.
- Arabic renders right-to-left; vocalisation (tashkil) is preserved.
- Punctuation is peeled off word edges so words analyse cleanly; the classic
  panel still shows every BPE piece.
- This is a teaching/demo tool. It shows the engines' real output, including
  their occasional over-stripping, rather than an idealised decomposition.
