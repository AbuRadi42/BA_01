"""
Morphology-Aware Tokenisation: interactive demo
-----------------------------------------------
A small mobile-friendly Flask app. Pick one of the four project languages
(ZH, EN, TR, AR), type a sentence, and see it tokenised two ways:

  1. The classic tokeniser  : the BPE baseline (the SentencePiece model the
     project trains its baseline models on; character-level for Mandarin).
  2. The grammar-aware tokeniser : the project's per-language engine, which
     decomposes each word into its grammatical streams (root, feature bundle,
     plus root + wazn for Arabic, radical + semantic class for Mandarin).

This is a teaching tool: it lets a reader *see* what each method exposes,
which is the heart of the project's methodology.

Run:
    pip install flask sentencepiece
    python webapp/app.py
    # open http://localhost:5000  (use --host 0.0.0.0 to reach it from a phone)
"""
from __future__ import annotations

import argparse
import string
import sys
from pathlib import Path

from flask import Flask, render_template, request

# --- make the project importable ------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from morph_efficiency_project.scripts.engines import (  # noqa: E402
    EnglishEngine, ArabicEngine, TurkishEngine, MandarinEngine,
)

# Canonical project order: isolating -> analytic -> agglutinative -> templatic.
LANGS = [
    {"code": "zh", "name": "Mandarin", "native": "中文",      "type": "isolating",     "rtl": False, "streams": 2},
    {"code": "en", "name": "English",  "native": "English",   "type": "analytic",      "rtl": False, "streams": 2},
    {"code": "tr", "name": "Turkish",  "native": "Türkçe",    "type": "agglutinative", "rtl": False, "streams": 2},
    {"code": "ar", "name": "Arabic",   "native": "العربية",   "type": "templatic",     "rtl": True,  "streams": 4},
]
LANG_BY_CODE = {l["code"]: l for l in LANGS}

EXAMPLES = {
    "zh": "我喜欢学习语言学",
    "en": "The researchers studied the unhappiness of agglutinative languages.",
    "tr": "Evlerinizden geliyorum ve kitaplarımızı okuyoruz.",
    "ar": "اِسْتَخْدَمَ الطَّالِبُ الْكِتَابَ فِي الْمَكْتَبَةِ",
}

TOK_DIR = REPO_ROOT / "mini_experiment" / "tokenizers"
CONFIG_DIR = str(REPO_ROOT / "morph_efficiency_project" / "configs")

# --- load engines + baseline tokenisers once at startup -------------------------
# Absolute config_dir so the app runs from any working directory (e.g. systemd).
ENGINES = {
    "en": EnglishEngine(config_dir=CONFIG_DIR),
    "ar": ArabicEngine(config_dir=CONFIG_DIR),
    "tr": TurkishEngine(config_dir=CONFIG_DIR),
    "zh": MandarinEngine(config_dir=CONFIG_DIR),
}

_SPM = {}
try:
    import sentencepiece as spm
    for code in ("en", "ar", "tr"):
        model = TOK_DIR / f"{code}_base.model"
        if model.exists():
            sp = spm.SentencePieceProcessor()
            sp.load(str(model))
            _SPM[code] = sp
except Exception as exc:  # pragma: no cover - degrade gracefully
    print(f"[warn] sentencepiece baseline unavailable: {exc}")


# --- tokenisation ---------------------------------------------------------------
def baseline_tokens(lang: str, text: str):
    """The classic tokeniser: BPE subword pieces (char-level for Mandarin)."""
    if lang == "zh" or lang not in _SPM:
        # Mandarin baseline is character-level; also the safe fallback.
        return [ch for ch in text if not ch.isspace()]
    pieces = _SPM[lang].encode(text, out_type=str)
    # SentencePiece marks a word boundary with U+2581; render it as a space dot.
    return [p.replace("▁", "·") for p in pieces]


# Punctuation peeled off word edges so the engine sees clean words. Arabic
# tashkil (combining marks) are NOT in this set, so vocalised words stay intact.
_PUNCT = set(string.punctuation) | set("،؛؟…«»“”‘’—–·。！？；：、（）「」")


def _split_punct(tok: str):
    """Peel leading/trailing punctuation into their own tokens, keep the core."""
    i, j = 0, len(tok)
    lead = []
    while i < j and tok[i] in _PUNCT:
        lead.append(tok[i]); i += 1
    trail = []
    while j > i and tok[j - 1] in _PUNCT:
        trail.append(tok[j - 1]); j -= 1
    core = tok[i:j]
    out = list(lead)
    if core:
        out.append(core)
    out.extend(reversed(trail))
    return out


def _word_tokens(lang: str, text: str):
    if lang == "zh":
        return [ch for ch in text if not ch.isspace()]
    toks = []
    for w in text.split():
        toks.extend(_split_punct(w))
    return [t for t in toks if t]


import dataclasses as _dc
from morph_efficiency_project.scripts.engines.grammar import (  # noqa: E402
    en_grammar, ar_grammar, tr_grammar, zh_grammar,
)
_DISAMBIG = {"en": en_grammar.disambiguate_pos, "ar": ar_grammar.disambiguate_pos,
             "tr": tr_grammar.disambiguate_pos, "zh": zh_grammar.disambiguate_pos}


def morph_tokens(lang: str, text: str):
    """The grammar-aware tokeniser: per-word decomposition into streams, with the
    same sentence-context disambiguation the training tokeniser now uses."""
    engine = ENGINES[lang]
    surfaces = _word_tokens(lang, text)
    # Analyse the whole sequence, then resolve POS from neighbours (context).
    infos = []
    for w in surfaces:
        try:
            infos.append(engine.analyze(w))
        except Exception:
            infos.append(None)
    seq = [_dc.replace(i, tags=dict(i.tags)) for i in infos if i is not None]
    try:
        seq = _DISAMBIG[lang](seq)
    except Exception:
        pass
    it = iter(seq)
    infos = [next(it) if i is not None else None for i in infos]

    units = []
    for tok, info in zip(surfaces, infos):
        if info is None or all(ch in _PUNCT for ch in tok):
            continue  # punctuation carries no morphology; the classic panel shows it
        tags = dict(info.tags or {})
        rows = []
        if lang == "zh":
            radical = tags.pop("radical", None)
            rclass = tags.pop("radical_class", None)
            rows.append(("radical", radical or "—"))
            rows.append(("semantic class", rclass or "—"))
        elif lang == "ar":
            rows.append(("root", info.root or "—"))
            wazn = tags.pop("semantic_role", None) or tags.pop("wazn_class", None)
            rows.append(("wazn class", wazn or "—"))
            if info.template:
                rows.append(("template", info.template))
            feats = _feat_str(info.pos, tags)
            rows.append(("features", feats))
        else:  # en, tr
            rows.append(("root", info.root or "—"))
            feats = _feat_str(info.pos, tags)
            rows.append(("features", feats))
        units.append({"surface": info.surface or tok, "pos": info.pos, "rows": rows})
    return units


def _feat_str(pos: str, tags: dict) -> str:
    items = [f"{k}={v}" for k, v in sorted(tags.items())]
    return " · ".join(items) if items else "no inflectional features"


# --- routes ---------------------------------------------------------------------
app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    lang = request.values.get("lang", "en")
    if lang not in LANG_BY_CODE:
        lang = "en"
    text = request.values.get("text", "")
    result = None
    if text.strip():
        meta = LANG_BY_CODE[lang]
        classic = baseline_tokens(lang, text)
        morph = morph_tokens(lang, text)
        valid_ok, valid_msg = _structural_check(lang, text)
        result = {
            "classic": classic,
            "classic_count": len(classic),
            "morph": morph,
            "morph_count": len(morph),
            "valid_ok": valid_ok,
            "valid_msg": valid_msg,
            "rtl": meta["rtl"],
            "streams": meta["streams"],
        }
    return render_template(
        "index.html",
        langs=LANGS,
        sel_lang=lang,
        text=text,
        example=EXAMPLES.get(lang, ""),
        examples=EXAMPLES,
        result=result,
        sel_meta=LANG_BY_CODE[lang],
    )


def _structural_check(lang: str, text: str):
    """Best-effort sentence-grammar validity, shown as an extra signal."""
    engine = ENGINES[lang]
    fn = getattr(engine, "analyze_sentence", None)
    if fn is None:
        return None, None
    try:
        out = fn(text)
        if isinstance(out, tuple) and len(out) == 3:
            _, ok, msg = out
            return bool(ok), msg
    except Exception:
        return None, None
    return None, None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    print(f"Baseline SentencePiece loaded for: {sorted(_SPM) or 'none (char-level only)'}")
    app.run(host=args.host, port=args.port, debug=args.debug)
