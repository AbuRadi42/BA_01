"""
Real-text engine evaluation harness
-----------------------------------
Scores each bespoke grammar engine against an established reference analyzer on
real Wikipedia sentences, so engine quality is *measured* (not assumed from the
curated unit tests). This is the gate before any AWS spend: the morph streams
(root / POS / features) are what feed the models, so we certify them here.

Reference analyzers (the "gold"):
    EN : spaCy en_core_web_sm   (POS + lemma)
    AR : CAMeL Tools MSA DB     (POS + root + lemma + pattern)
    TR : zeyrek (Zemberek)      (lemma + morpheme tags)
    ZH : jieba                  (segmentation + POS) + engine radical coverage

Outputs a per-language markdown report under
    morph_efficiency_project/logs/summary/realtext_eval/<lang>.md
with headline agreement rates and the worst disagreements (the fix list).

Usage:
    python morph_efficiency_project/scripts/eval_realtext.py --langs en ar tr zh
    python morph_efficiency_project/scripts/eval_realtext.py --langs ar --limit 100
"""
from __future__ import annotations

import argparse
import re
import string
import sys
import unicodedata
from collections import Counter, defaultdict, deque
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from morph_efficiency_project.scripts.engines import (  # noqa: E402
    EnglishEngine, ArabicEngine, TurkishEngine, MandarinEngine,
)

DATA = REPO / "mini_experiment" / "data"
OUT = REPO / "morph_efficiency_project" / "logs" / "summary" / "realtext_eval"
CONFIG = str(REPO / "morph_efficiency_project" / "configs")

_PUNCT = set(string.punctuation) | set("،؛؟…«»“”‘’—–·。！？；：、（）「」")
_AR_DIAC = re.compile(r"[ً-ْٰـ]")  # tashkil + tatweel
_HAMZA_MAP = str.maketrans("أإآؤئ", "ءءءءء")


def _HAMZA(s: str) -> str:
    return (s or "").translate(_HAMZA_MAP)


def _strip_punct(w: str) -> str:
    i, j = 0, len(w)
    while i < j and w[i] in _PUNCT:
        i += 1
    while j > i and w[j - 1] in _PUNCT:
        j -= 1
    return w[i:j]


def words(text: str):
    out = []
    for w in text.split():
        core = _strip_punct(w)
        if core:
            out.append(core)
    return out


def load_sents(lang: str, limit: int):
    p = DATA / f"{lang}_realtext_eval.txt"
    if not p.exists():
        sys.exit(f"missing eval corpus: {p} (run fetch_eval_corpus first)")
    lines = [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    return lines[:limit]


# --- context POS lookup ---------------------------------------------------------
def context_pos_map(engine, sentence: str, key=str.lower, proj=None):
    """Run the engine's sentence-grammar layer once and return an ordered,
    surface-keyed map of the *context-disambiguated* POS for every token.

    The map value is a deque so repeated surfaces in a sentence are consumed
    left-to-right as the caller aligns gold tokens by surface string. This is
    the bridge that lets POS scoring see `engine.analyze_sentence()` instead of
    the context-free `engine.analyze(word)`. Root/lemma/radical scoring does not
    use this and is unaffected.

    `proj(token) -> str` optionally projects a token to its POS string (e.g. to
    read a finer-grained subcategory tag); defaults to the token's `.pos`.
    """
    out = defaultdict(deque)
    try:
        tokens, _ok, _msg = engine.analyze_sentence(sentence)
    except Exception:
        return out
    for t in tokens:
        surf = getattr(t, "surface", None)
        if not surf:
            continue
        out[key(surf)].append(proj(t) if proj else t.pos)
    return out


def take_ctx_pos(cmap, surface, fallback, key=str.lower):
    """Pop the next context POS for `surface` (consuming it), else `fallback`."""
    dq = cmap.get(key(surface))
    if dq:
        return dq.popleft()
    return fallback


# --- coarse POS normalisation ---------------------------------------------------
def coarse(tag: str, lump_adj: bool = False) -> str:
    """Normalise a POS tag to a coarse common set. lump_adj=True folds ADJ into
    NOMINAL (used only for Arabic, whose engine cannot separate noun from adj)."""
    t = (tag or "").upper()
    m = {
        "NOUN": "NOMINAL", "PROPN": "NOMINAL", "NOM": "NOMINAL",
        "NOUN_PROP": "NOMINAL", "NOUN_NUM": "NUM",
        "ADJ": "ADJ", "ADJ_COMP": "ADJ",
        "VERB": "VERB", "VERB_PSEUDO": "VERB", "AUX": "VERB",
        "ADV": "ADV", "ADP": "ADP", "PREP": "ADP", "PART": "PART",
        "PRON": "PRON", "DET": "DET", "NUM": "NUM",
        "CONJ": "CONJ", "CCONJ": "CONJ", "SCONJ": "CONJ", "CONJ_SUB": "CONJ",
        "PUNCT": "PUNCT", "CLF": "PART",
    }
    c = m.get(t, "OTHER")
    if lump_adj and c == "ADJ":
        return "NOMINAL"
    return c


def norm_ar_root(camel_root: str):
    """CAMeL root 'ك.ت.ب' / 'ل.غ.#' -> list of strong radicals (drop '#', weak)."""
    parts = [p for p in camel_root.split(".") if p and p != "#"]
    return [_AR_DIAC.sub("", p) for p in parts]


def ar_root_skeleton(s: str):
    s = _AR_DIAC.sub("", s or "")
    s = s.replace("أ", "ء").replace("إ", "ء").replace("آ", "ء").replace("ؤ", "ء").replace("ئ", "ء")
    return [c for c in s if c not in "اوي"]  # drop weak letters for tolerant match


# --- per-language evaluators ----------------------------------------------------
def eval_en(sents):
    import spacy
    nlp = spacy.load("en_core_web_sm")
    eng = EnglishEngine(config_dir=CONFIG)
    pos_ok = pos_n = lem_ok = lem_n = 0
    iso_pos_ok = 0  # context-free baseline, for before/after reporting
    bad_pos, bad_lem = Counter(), Counter()
    for s in sents:
        doc = nlp(s)
        cmap = context_pos_map(eng, s)
        for t in doc:
            if not t.is_alpha:
                continue
            gi = eng.analyze(t.text)
            # POS: use the context-disambiguated tag (analyze_sentence), aligned
            # to the gold token by surface string. Falls back to the context-free
            # tag when the engine's sentence tokeniser did not emit this surface.
            ctx_pos = take_ctx_pos(cmap, t.text, gi.pos)
            gp, ep = coarse(t.pos_), coarse(ctx_pos)
            pos_n += 1
            if gp == ep:
                pos_ok += 1
            else:
                bad_pos[f"{t.text}: gold={t.pos_} eng={ctx_pos}"] += 1
            if gp == coarse(gi.pos):
                iso_pos_ok += 1
            # LEMMA: unchanged context-free metric (must not regress).
            lem_n += 1
            if (gi.root or "").lower() == t.lemma_.lower():
                lem_ok += 1
            else:
                bad_lem[f"{t.text}: gold_lemma={t.lemma_} eng_root={gi.root}"] += 1
    return {
        "metrics": [("POS agreement (context)", pos_ok, pos_n),
                    ("POS agreement (isolated)", iso_pos_ok, pos_n),
                    ("Lemma agreement", lem_ok, lem_n)],
        "bad": {"POS mismatches": bad_pos, "Lemma mismatches": bad_lem},
    }


def eval_ar(sents):
    from camel_tools.morphology.database import MorphologyDB
    from camel_tools.morphology.analyzer import Analyzer
    an = Analyzer(MorphologyDB.builtin_db())
    eng = ArabicEngine(config_dir=CONFIG)
    root_ok = root_skel_ok = root_n = pos_ok = pos_n = 0
    iso_pos_ok = 0  # context-free baseline, for before/after reporting
    bad_root, bad_pos = Counter(), Counter()
    _arkey = lambda x: _strip_punct(x)

    # The Arabic engine labels every function word POS=PART but carries the
    # actual function in tags['subcat'] (PREP, CONJ, COMP, ...). The reference
    # tagset (CAMeL) and standard grammar treat حرف الجر as a preposition (ADP)
    # and حرف العطف / المصدرية as a conjunction (CONJ). Projecting the engine's
    # subcat to that coarse class measures what the engine actually analysed
    # rather than collapsing it to a bare particle. This refines measurement;
    # it never relaxes a match (an honest PART would still miss an ADP gold).
    _AR_SUBCAT = {"PREP": "ADP", "CONJ": "CONJ", "COMP": "CONJ"}

    def _ar_proj(t):
        if t.pos == "PART":
            sc = (t.tags or {}).get("subcat", "")
            return _AR_SUBCAT.get(sc, t.pos)
        return t.pos

    for s in sents:
        # Feed the engine the same punctuation-stripped word list we score, so
        # trailing punctuation never corrupts the final token's analysis and
        # surfaces align one-to-one with the gold loop.
        cmap = context_pos_map(eng, " ".join(words(s)), key=_arkey, proj=_ar_proj)
        for w in words(s):
            if not any("؀" <= c <= "ۿ" for c in w):
                continue
            res = an.analyze(w)
            if not res:
                continue
            gi = eng.analyze(w)
            en = _HAMZA(_AR_DIAC.sub("", gi.root or ""))
            e_skel = ar_root_skeleton(gi.root or "")
            FUNC = {"PRON", "PART", "ADP", "CONJ", "DET", "OTHER"}
            all_pos = {coarse(a.get("pos", ""), lump_adj=True) for a in res}

            # ROOT — only for genuine content words. Exclude any surface that has
            # a function-word reading among CAMeL's analyses (كما, ذلك, عندما …):
            # those are not root-derived even when CAMeL's top parse picks a
            # content homograph. '#' is a wildcard (weak radical). Accept a match
            # against ANY content analysis (CAMeL's first parse is arbitrary).
            content = []
            for a in res:
                craw = a.get("root", "")
                slots = [_HAMZA(s) for s in craw.split(".") if s]
                strong = [s for s in slots if s != "#"]
                if craw != "NTWS" and len(strong) >= 2 \
                        and coarse(a.get("pos", ""), lump_adj=True) in ("NOMINAL", "VERB"):
                    content.append((slots, strong))
            if content and gi.pos != "PART" \
                    and not (all_pos & {"PRON", "PART", "ADP", "CONJ", "DET"}):
                root_n += 1
                fair = any(len(slots) == len(en)
                           and all(s == "#" or s == en[i] for i, s in enumerate(slots))
                           for slots, _ in content)
                skel = any(all(r in e_skel for r in strong) for _, strong in content)
                if fair:
                    root_ok += 1
                if skel:
                    root_skel_ok += 1
                if not fair:
                    bad_root[f"{w}: gold={res[0].get('root')} eng={gi.root}"] += 1

            # POS — accept a match against ANY CAMeL analysis (fair). Use the
            # context-disambiguated tag from analyze_sentence, aligned by surface.
            ctx_pos = take_ctx_pos(cmap, w, gi.pos, key=_arkey)
            pos_n += 1
            if coarse(ctx_pos, lump_adj=True) in all_pos:
                pos_ok += 1
            else:
                bad_pos[f"{w}: gold={sorted(all_pos)} eng={ctx_pos}"] += 1
            if coarse(gi.pos, lump_adj=True) in all_pos:
                iso_pos_ok += 1
    return {
        "metrics": [("Root agreement (fair: weak=wildcard)", root_ok, root_n),
                    ("Root agreement (skeleton)", root_skel_ok, root_n),
                    ("POS-class agreement (context)", pos_ok, pos_n),
                    ("POS-class agreement (isolated)", iso_pos_ok, pos_n)],
        "bad": {"Root mismatches": bad_root, "POS mismatches": bad_pos},
    }


def eval_tr(sents):
    import logging
    logging.disable(logging.CRITICAL)  # zeyrek spams "APPENDING RESULT" at info
    import zeyrek
    za = zeyrek.MorphAnalyzer()
    eng = TurkishEngine(config_dir=CONFIG)
    lem_ok = lem_n = pos_ok = pos_n = 0
    iso_pos_ok = 0  # context-free baseline, for before/after reporting
    bad_lem, bad_pos = Counter(), Counter()
    _trkey = lambda x: _strip_punct(x).lower()
    for s in sents:
        # Feed the punctuation-stripped word list (trailing punctuation otherwise
        # makes the engine tag the final token UNKNOWN); surfaces then align.
        cmap = context_pos_map(eng, " ".join(words(s)), key=_trkey)
        for w in words(s):
            if not w.isalpha():
                continue
            try:
                parses = za.analyze(w)
            except Exception:
                continue
            if not parses or not parses[0]:
                continue
            gi = eng.analyze(w)
            # zeyrek returns MANY analyses per word; grading against an arbitrary
            # first one is unfair (it has no sentence context to pick). Accept a
            # match against ANY of its parses — the engine's single answer just
            # has to be among zeyrek's licensed readings.
            cand = parses[0]
            def _norm_lemma(lem):
                lem = (lem or "").lower()
                if len(lem) > 4 and lem.endswith(("mak", "mek")):
                    lem = lem[:-3]
                return lem
            gold_lemmas = {_norm_lemma(p.lemma) for p in cand if p.lemma and p.lemma != "Unk"}
            if gold_lemmas:
                lem_n += 1
                if (gi.root or "").lower() in gold_lemmas:
                    lem_ok += 1
                else:
                    bad_lem[f"{w}: gold={sorted(gold_lemmas)} eng={gi.root}"] += 1
            gold_pos = {coarse(p.morphemes[0]) for p in cand if p.morphemes}
            if gold_pos:
                ctx_pos = take_ctx_pos(cmap, w, gi.pos, key=_trkey)
                pos_n += 1
                if coarse(ctx_pos) in gold_pos:
                    pos_ok += 1
                else:
                    bad_pos[f"{w}: gold={sorted(gold_pos)} eng={ctx_pos}"] += 1
                if coarse(gi.pos) in gold_pos:
                    iso_pos_ok += 1
    return {
        "metrics": [("Lemma agreement", lem_ok, lem_n),
                    ("POS agreement (context)", pos_ok, pos_n),
                    ("POS agreement (isolated)", iso_pos_ok, pos_n)],
        "bad": {"Lemma mismatches": bad_lem, "POS mismatches": bad_pos},
    }


def eval_zh(sents):
    import jieba.posseg as pseg
    eng = MandarinEngine(config_dir=CONFIG)
    rad_have = rad_n = pos_ok = pos_n = 0
    iso_pos_ok = 0  # context-free baseline, for before/after reporting
    bad_pos = Counter()
    jmap = {"n": "NOMINAL", "nr": "NOMINAL", "ns": "NOMINAL", "nt": "NOMINAL",
            "nz": "NOMINAL", "v": "VERB", "vn": "VERB", "a": "NOMINAL", "ad": "ADV",
            "d": "ADV", "r": "PRON", "p": "ADP", "c": "CONJ", "u": "PART", "m": "NUM",
            "q": "PART", "t": "NOMINAL", "f": "NOMINAL"}
    for s in sents:
        # Feed the engine the jieba segmentation (space-joined) so its
        # sentence-grammar layer sees the same tokenisation we score against,
        # then align the context-disambiguated POS back by surface.
        seg_words = [w for w, _f in pseg.cut(s)]
        cmap = context_pos_map(eng, " ".join(seg_words), key=lambda x: x)
        for word, flag in pseg.cut(s):
            if not word.strip() or all(c in _PUNCT for c in word):
                continue
            # radical coverage: per Han char (unchanged, context-free).
            for ch in word:
                if "一" <= ch <= "鿿":
                    rad_n += 1
                    if eng.analyze(ch).tags.get("radical"):
                        rad_have += 1
            # POS only for single-char tokens (granularity matches engine)
            if len(word) == 1 and "一" <= word <= "鿿":
                gi = eng.analyze(word)
                ctx_pos = take_ctx_pos(cmap, word, gi.pos, key=lambda x: x)
                gp = jmap.get(flag, "OTHER")
                if gp != "OTHER":
                    pos_n += 1
                    if gp == coarse(ctx_pos):
                        pos_ok += 1
                    else:
                        bad_pos[f"{word}: gold={flag}->{gp} eng={ctx_pos}"] += 1
                    if gp == coarse(gi.pos):
                        iso_pos_ok += 1
    return {
        "metrics": [("Radical coverage", rad_have, rad_n),
                    ("POS agreement (1-char, context)", pos_ok, pos_n),
                    ("POS agreement (1-char, isolated)", iso_pos_ok, pos_n)],
        "bad": {"POS mismatches": bad_pos},
    }


EVALS = {"en": eval_en, "ar": eval_ar, "tr": eval_tr, "zh": eval_zh}


def pct(a, b):
    return f"{100*a/b:.1f}%" if b else "n/a"


def write_report(lang, res, n_sents):
    OUT.mkdir(parents=True, exist_ok=True)
    lines = [f"# Real-text eval: {lang.upper()}", "",
             f"Sample: {n_sents} real Wikipedia sentences.", "", "## Agreement vs gold", "",
             "| Metric | Agree | Total | Rate |", "|---|---:|---:|---:|"]
    for name, a, b in res["metrics"]:
        lines.append(f"| {name} | {a} | {b} | {pct(a, b)} |")
    for title, counter in res["bad"].items():
        lines += ["", f"## Top {title}", ""]
        for item, c in counter.most_common(25):
            lines.append(f"- ({c}×) {item}")
    (OUT / f"{lang}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", nargs="+", default=["en", "ar", "tr", "zh"])
    ap.add_argument("--limit", type=int, default=250)
    args = ap.parse_args()
    summary = []
    for lang in args.langs:
        sents = load_sents(lang, args.limit)
        print(f"[{lang}] scoring {len(sents)} sentences ...", flush=True)
        res = EVALS[lang](sents)
        write_report(lang, res, len(sents))
        head = " · ".join(f"{n}={pct(a,b)}" for n, a, b in res["metrics"])
        print(f"[{lang}] {head}")
        summary.append((lang, res))
    print("\n=== SUMMARY ===")
    for lang, res in summary:
        print(f"{lang}: " + " · ".join(f"{n}={pct(a,b)}" for n, a, b in res["metrics"]))


if __name__ == "__main__":
    main()
