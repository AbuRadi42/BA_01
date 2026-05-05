"""
engines/es_engine.py
--------------------
Spanish morphology engine (Steps A/B/C).

Spanish is a regular fusional language. A single verb suffix simultaneously
encodes person, number, tense, and mood, so suffix stripping proceeds by
matching entire paradigm endings rather than peeling slot-by-slot.

Step A -- Inflectional stripping: closed-class intercept, irregular lookup,
          enclitic pronoun stripping, regular verb conjugation matching,
          noun gender/number, adjective agreement, irregular comparatives.
Step B -- Derivational pattern detection via es_derivations.json.
Step C -- Stem identification: iterative Step B (max 4 rounds).
"""

import json
import os
import unicodedata
from typing import Dict, List, Optional, Tuple

from .shared import (
    TokenInfo,
    check_morph_sequence_es,
    validate_sentence_structure_es,
)


def _strip_accents(s: str) -> str:
    """Remove accent marks for lookup, preserving n-tilde."""
    out = []
    for ch in s:
        if ch == '\u00f1':          # n-tilde
            out.append(ch)
            continue
        decomposed = unicodedata.normalize("NFD", ch)
        stripped = "".join(c for c in decomposed
                          if unicodedata.category(c) != "Mn")
        out.append(stripped)
    return "".join(out)


# ── Closed-class dictionary (~165 entries) ───────────────────────────────────

CLOSED_CLASS: Dict[str, Tuple[str, Dict[str, str]]] = {}

# Determiners
for _w, _t in [
    ("el",  {"gender": "MASC", "num": "SG"}),
    ("la",  {"gender": "FEM", "num": "SG"}),
    ("los", {"gender": "MASC", "num": "PL"}),
    ("las", {"gender": "FEM", "num": "PL"}),
    ("lo",  {"gender": "NEUT"}),
    ("un",  {"gender": "MASC", "num": "SG"}),
    ("una", {"gender": "FEM", "num": "SG"}),
    ("unos", {"gender": "MASC", "num": "PL"}),
    ("unas", {"gender": "FEM", "num": "PL"}),
    ("al",  {"contraction": "YES"}),
    ("del", {"contraction": "YES"}),
]:
    CLOSED_CLASS[_w] = ("DET", _t)

# Prepositions
for _w in [
    "a", "ante", "bajo", "cabe", "con", "contra", "desde", "durante",
    "en", "entre", "hacia", "hasta", "mediante", "para", "por", "segun",
    "sin", "sobre", "tras",
]:
    CLOSED_CLASS[_w] = ("ADP", {})

# NOTE: "de" is registered as ADP only if not already set
if "de" not in CLOSED_CLASS:
    CLOSED_CLASS["de"] = ("ADP", {})

# Pronouns — personal subject
for _w, _t in [
    ("yo",        {"person": "1", "num": "SG"}),
    ("tu",        {"person": "2", "num": "SG"}),
    ("ella",      {"person": "3", "num": "SG", "gender": "FEM"}),
    ("usted",     {"person": "3", "num": "SG", "formality": "FORMAL"}),
    ("nosotros",  {"person": "1", "num": "PL", "gender": "MASC"}),
    ("nosotras",  {"person": "1", "num": "PL", "gender": "FEM"}),
    ("vosotros",  {"person": "2", "num": "PL", "gender": "MASC"}),
    ("vosotras",  {"person": "2", "num": "PL", "gender": "FEM"}),
    ("ellos",     {"person": "3", "num": "PL", "gender": "MASC"}),
    ("ellas",     {"person": "3", "num": "PL", "gender": "FEM"}),
    ("ustedes",   {"person": "3", "num": "PL", "formality": "FORMAL"}),
]:
    CLOSED_CLASS[_w] = ("PRON", _t)

# Unstressed object clitics (freestanding)
for _w, _t in [
    ("me",  {"subcat": "CLITIC", "person": "1", "num": "SG"}),
    ("te",  {"subcat": "CLITIC", "person": "2", "num": "SG"}),
    ("le",  {"subcat": "CLITIC", "person": "3", "num": "SG", "case": "DAT"}),
    ("nos", {"subcat": "CLITIC", "person": "1", "num": "PL"}),
    ("os",  {"subcat": "CLITIC", "person": "2", "num": "PL"}),
    ("les", {"subcat": "CLITIC", "person": "3", "num": "PL", "case": "DAT"}),
    ("se",  {"subcat": "CLITIC", "person": "3"}),
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("PRON", _t)

# Prepositional pronouns
for _w, _t in [
    ("mi",       {"subcat": "PREP_PRON", "person": "1"}),
    ("ti",       {"subcat": "PREP_PRON", "person": "2"}),
    ("si",       {"subcat": "PREP_PRON", "person": "3"}),
    ("conmigo",  {"subcat": "PREP_PRON", "person": "1"}),
    ("contigo",  {"subcat": "PREP_PRON", "person": "2"}),
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("PRON", _t)

# Relative / interrogative pronouns
for _w, _t in [
    ("que",   {"subcat": "REL"}),
    ("quien", {"subcat": "REL"}),
    ("cual",  {"subcat": "REL"}),
    ("cuyo",  {"subcat": "REL"}),
    ("cuya",  {"subcat": "REL"}),
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("PRON", _t)

# Demonstrative pronouns
for _w, _t in [
    ("este",     {"subcat": "DEM", "gender": "MASC", "num": "SG", "distance": "PROX"}),
    ("esta",     {"subcat": "DEM", "gender": "FEM", "num": "SG", "distance": "PROX"}),
    ("estos",    {"subcat": "DEM", "gender": "MASC", "num": "PL", "distance": "PROX"}),
    ("estas",    {"subcat": "DEM", "gender": "FEM", "num": "PL", "distance": "PROX"}),
    ("ese",      {"subcat": "DEM", "gender": "MASC", "num": "SG", "distance": "MED"}),
    ("esa",      {"subcat": "DEM", "gender": "FEM", "num": "SG", "distance": "MED"}),
    ("esos",     {"subcat": "DEM", "gender": "MASC", "num": "PL", "distance": "MED"}),
    ("esas",     {"subcat": "DEM", "gender": "FEM", "num": "PL", "distance": "MED"}),
    ("aquel",    {"subcat": "DEM", "gender": "MASC", "num": "SG", "distance": "DIST"}),
    ("aquella",  {"subcat": "DEM", "gender": "FEM", "num": "SG", "distance": "DIST"}),
    ("aquellos", {"subcat": "DEM", "gender": "MASC", "num": "PL", "distance": "DIST"}),
    ("aquellas", {"subcat": "DEM", "gender": "FEM", "num": "PL", "distance": "DIST"}),
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("PRON", _t)

# Indefinite pronouns
for _w, _t in [
    ("algo",    {"subcat": "INDEF"}),
    ("alguien", {"subcat": "INDEF"}),
    ("nada",    {"subcat": "INDEF"}),
    ("nadie",   {"subcat": "INDEF"}),
    ("todo",    {"subcat": "INDEF", "gender": "MASC", "num": "SG"}),
    ("toda",    {"subcat": "INDEF", "gender": "FEM", "num": "SG"}),
    ("todos",   {"subcat": "INDEF", "gender": "MASC", "num": "PL"}),
    ("todas",   {"subcat": "INDEF", "gender": "FEM", "num": "PL"}),
    ("cada",    {"subcat": "INDEF"}),
    ("otro",    {"subcat": "INDEF", "gender": "MASC", "num": "SG"}),
    ("otra",    {"subcat": "INDEF", "gender": "FEM", "num": "SG"}),
    ("otros",   {"subcat": "INDEF", "gender": "MASC", "num": "PL"}),
    ("otras",   {"subcat": "INDEF", "gender": "FEM", "num": "PL"}),
    ("mismo",   {"subcat": "INDEF"}),
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("PRON", _t)

# Conjunctions — coordinating
for _w, _t in [
    ("y",    {"subcat": "COORD"}),
    ("e",    {"subcat": "COORD"}),
    ("o",    {"subcat": "COORD"}),
    ("u",    {"subcat": "COORD"}),
    ("ni",   {"subcat": "COORD"}),
    ("pero", {"subcat": "COORD"}),
    ("sino", {"subcat": "COORD"}),
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("CONJ", _t)

# Conjunctions — subordinating
for _w, _t in [
    ("mas",      {"subcat": "SUBORD"}),
    ("aunque",   {"subcat": "SUBORD"}),
    ("porque",   {"subcat": "SUBORD"}),
    ("pues",     {"subcat": "SUBORD"}),
    ("como",     {"subcat": "SUBORD"}),
    ("cuando",   {"subcat": "SUBORD"}),
    ("donde",    {"subcat": "SUBORD"}),
    ("mientras", {"subcat": "SUBORD"}),
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("CONJ", _t)

# Adverbs
for _w, _t in [
    ("muy",      {"subcat": "DEGREE"}),
    ("menos",    {"subcat": "DEGREE"}),
    ("tan",      {"subcat": "DEGREE"}),
    ("ya",       {"subcat": "TEMP"}),
    ("hoy",      {"subcat": "TEMP"}),
    ("ayer",     {"subcat": "TEMP"}),
    ("manana",   {"subcat": "TEMP"}),
    ("siempre",  {"subcat": "TEMP"}),
    ("nunca",    {"subcat": "NEG"}),
    ("jamas",    {"subcat": "NEG"}),
    ("no",       {"subcat": "NEG"}),
    ("tambien",  {"subcat": "NEG"}),
    ("tampoco",  {"subcat": "NEG"}),
    ("aqui",     {"subcat": "SPATIAL"}),
    ("ahi",      {"subcat": "SPATIAL"}),
    ("alli",     {"subcat": "SPATIAL"}),
    ("quizas",   {"subcat": "EPIST"}),
    ("acaso",    {"subcat": "EPIST"}),
    ("bien",     {"subcat": "MANNER"}),
    ("mal",      {"subcat": "MANNER"}),
    ("asi",      {"subcat": "MANNER"}),
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("ADV", _t)

# Auxiliary verbs (infinitive forms only — prevents derivational analysis)
for _w in ["haber", "estar"]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("AUX", {})

# Particles / interjections
for _w in ["oye", "mira", "ole", "ay", "eh", "ah", "oh"]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("PART", {})

# Numerals
for _w in [
    "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho",
    "nueve", "diez", "once", "doce", "trece", "catorce", "quince",
    "cien", "ciento", "mil", "millon", "primer",
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("NUM", {})


# ── Enclitic pronoun inventory (for stripping from verb forms) ───────────────

_ENCLITICS = [
    "se", "me", "te", "nos", "os", "le", "les", "lo", "la", "los", "las",
]
# Sort longest-first for greedy matching
_ENCLITICS_SORTED = sorted(_ENCLITICS, key=len, reverse=True)


# ── Gender exception nouns (Greek -ma nouns are masculine) ───────────────────

_GENDER_EXCEPTIONS: Dict[str, str] = {
    "dia": "MASC", "mano": "FEM", "mapa": "MASC", "foto": "FEM",
    "moto": "FEM", "radio": "FEM", "planeta": "MASC", "tema": "MASC",
    "problema": "MASC", "sistema": "MASC", "programa": "MASC",
    "idioma": "MASC", "clima": "MASC", "poema": "MASC", "drama": "MASC",
    "fantasma": "MASC", "telegrama": "MASC",
}


# ── Verb suffix paradigm tables ─────────────────────────────────────────────
#
# Each entry: (suffix, conj_class, tags_dict, min_stem_len)
# conj_class tells us which infinitive ending to reconstruct.
# Sorted longest-first at engine init time for greedy matching.

_VERB_PARADIGMS: List[Tuple[str, str, Dict[str, str], int]] = []


def _add(suf: str, cc: str, tags: Dict[str, str], min_stem: int = 2):
    _VERB_PARADIGMS.append((suf, cc, tags, min_stem))


# ── Gerund (distinctive, unambiguous) ──
_add("ando", "ar", {"aspect": "PROG", "form": "GER"})
_add("iendo", "er", {"aspect": "PROG", "form": "GER"})
# iendo also for -ir verbs, but we return "er" and handle it later

# ── Past participle (gender/number variants first — longer) ──
for suf, g, n in [("ados", "MASC", "PL"), ("adas", "FEM", "PL"),
                   ("ado", "MASC", "SG"), ("ada", "FEM", "SG")]:
    _add(suf, "ar", {"aspect": "PERF", "form": "PTCP", "gender": g, "num": n})
for suf, g, n in [("idos", "MASC", "PL"), ("idas", "FEM", "PL"),
                   ("ido", "MASC", "SG"), ("ida", "FEM", "SG")]:
    _add(suf, "er", {"aspect": "PERF", "form": "PTCP", "gender": g, "num": n})
# base participle (no gender)
_add("ado", "ar", {"aspect": "PERF", "form": "PTCP"})
_add("ido", "er", {"aspect": "PERF", "form": "PTCP"})

# ── Imperfect subjunctive -ra ──
for suf, p, n in [("aramos", "1", "PL"), ("arais", "2", "PL"),
                   ("aras", "2", "SG"), ("aran", "3", "PL"),
                   ("ara", "1", "SG"), ("ara", "3", "SG")]:
    _add(suf, "ar", {"tense": "PAST_IMPERF", "mood": "SUBJ",
                     "person": p, "num": n, "subj_form": "RA"})
for suf, p, n in [("ieramos", "1", "PL"), ("ierais", "2", "PL"),
                   ("ieras", "2", "SG"), ("ieran", "3", "PL"),
                   ("iera", "1", "SG"), ("iera", "3", "SG")]:
    _add(suf, "er", {"tense": "PAST_IMPERF", "mood": "SUBJ",
                     "person": p, "num": n, "subj_form": "RA"})

# ── Imperfect subjunctive -se ──
for suf, p, n in [("asemos", "1", "PL"), ("aseis", "2", "PL"),
                   ("ases", "2", "SG"), ("asen", "3", "PL"),
                   ("ase", "1", "SG"), ("ase", "3", "SG")]:
    _add(suf, "ar", {"tense": "PAST_IMPERF", "mood": "SUBJ",
                     "person": p, "num": n, "subj_form": "SE"})
for suf, p, n in [("iesemos", "1", "PL"), ("ieseis", "2", "PL"),
                   ("ieses", "2", "SG"), ("iesen", "3", "PL"),
                   ("iese", "1", "SG"), ("iese", "3", "SG")]:
    _add(suf, "er", {"tense": "PAST_IMPERF", "mood": "SUBJ",
                     "person": p, "num": n, "subj_form": "SE"})

# ── Future subjunctive (archaic) ──
for suf, p, n in [("aremos", "1", "PL"), ("areis", "2", "PL"),
                   ("ares", "2", "SG"), ("aren", "3", "PL"),
                   ("are", "1", "SG"), ("are", "3", "SG")]:
    _add(suf, "ar", {"tense": "FUT", "mood": "SUBJ", "person": p, "num": n})
for suf, p, n in [("ieremos", "1", "PL"), ("iereis", "2", "PL"),
                   ("ieres", "2", "SG"), ("ieren", "3", "PL"),
                   ("iere", "1", "SG"), ("iere", "3", "SG")]:
    _add(suf, "er", {"tense": "FUT", "mood": "SUBJ", "person": p, "num": n})

# ── Preterite (simple past) — distinctive long endings first ──
for suf, p, n in [("asteis", "2", "PL"), ("aste", "2", "SG"),
                   ("aron", "3", "PL"), ("amos", "1", "PL")]:
    _add(suf, "ar", {"tense": "PAST_SIMPLE", "mood": "IND",
                     "person": p, "num": n})
for suf, p, n in [("isteis", "2", "PL"), ("iste", "2", "SG"),
                   ("ieron", "3", "PL"), ("imos", "1", "PL"),
                   ("io", "3", "SG")]:
    _add(suf, "er", {"tense": "PAST_SIMPLE", "mood": "IND",
                     "person": p, "num": n})

# ── Imperfect indicative ──
for suf, p, n in [("abamos", "1", "PL"), ("abais", "2", "PL"),
                   ("abas", "2", "SG"), ("aban", "3", "PL"),
                   ("aba", "1", "SG"), ("aba", "3", "SG")]:
    _add(suf, "ar", {"tense": "PAST_IMPERF", "mood": "IND",
                     "person": p, "num": n})
for suf, p, n in [("iamos", "1", "PL"), ("iais", "2", "PL"),
                   ("ias", "2", "SG"), ("ian", "3", "PL"),
                   ("ia", "1", "SG"), ("ia", "3", "SG")]:
    _add(suf, "er", {"tense": "PAST_IMPERF", "mood": "IND",
                     "person": p, "num": n})

# ── Present indicative (longer suffixes first) ──
for suf, p, n in [("amos", "1", "PL"), ("ais", "2", "PL"),
                   ("as", "2", "SG"), ("an", "3", "PL"),
                   ("a", "3", "SG"), ("o", "1", "SG")]:
    _add(suf, "ar", {"tense": "PRES", "mood": "IND",
                     "person": p, "num": n}, min_stem=3)
for suf, p, n in [("emos", "1", "PL"), ("eis", "2", "PL"),
                   ("es", "2", "SG"), ("en", "3", "PL"),
                   ("e", "3", "SG"), ("o", "1", "SG")]:
    _add(suf, "er", {"tense": "PRES", "mood": "IND",
                     "person": p, "num": n}, min_stem=3)
for suf, p, n in [("imos", "1", "PL"), ("is", "2", "PL"),
                   ("es", "2", "SG"), ("en", "3", "PL"),
                   ("e", "3", "SG"), ("o", "1", "SG")]:
    _add(suf, "ir", {"tense": "PRES", "mood": "IND",
                     "person": p, "num": n}, min_stem=3)

# ── Imperative (2PL distinctive forms) ──
_add("ad", "ar", {"mood": "IMP", "person": "2", "num": "PL"}, min_stem=3)
_add("ed", "er", {"mood": "IMP", "person": "2", "num": "PL"}, min_stem=3)
_add("id", "ir", {"mood": "IMP", "person": "2", "num": "PL"}, min_stem=3)

# ── Future (full infinitive + suffix) ──
# Added AFTER subjunctive paradigms so that ambiguous forms like
# hablaras prefer subjunctive reading over future.
for _inf_end in ("ar", "er", "ir"):
    for _suf, _p, _n in [("emos", "1", "PL"), ("eis", "2", "PL"),
                          ("as", "2", "SG"), ("an", "3", "PL"),
                          ("a", "3", "SG"), ("e", "1", "SG")]:
        _add(_inf_end + _suf, _inf_end,
             {"tense": "FUT", "mood": "IND", "person": _p, "num": _n})

# ── Conditional (full infinitive + suffix) ──
for _inf_end in ("ar", "er", "ir"):
    for _suf, _p, _n in [("iamos", "1", "PL"), ("iais", "2", "PL"),
                          ("ias", "2", "SG"), ("ian", "3", "PL"),
                          ("ia", "1", "SG"), ("ia", "3", "SG")]:
        _add(_inf_end + _suf, _inf_end,
             {"tense": "COND", "mood": "IND", "person": _p, "num": _n})


class SpanishEngine:
    """
    Spanish morphology engine.

    Step A -- Inflectional stripping: closed-class intercept, irregular form
              lookup, enclitic stripping, regular verb conjugation matching
              (3 classes x 14+ paradigms), noun gender/number, adjective
              agreement, irregular comparatives.
    Step B -- Derivational pattern detection via es_derivations.json.
    Step C -- Stem identification (iterative Step B, max 4 rounds).
    """

    VOWELS = set("aeiou")

    def __init__(self, config_dir: str = "morph_efficiency_project/configs"):
        with open(os.path.join(config_dir, "es_irregulars.json"),
                  encoding="utf-8") as f:
            self.irregulars: Dict[str, dict] = json.load(f)

        with open(os.path.join(config_dir, "es_derivations.json"),
                  encoding="utf-8") as f:
            raw_derivs = json.load(f)

        # Strip hyphens from surface variants (learned from en_engine bug)
        self.suffixes: List[Tuple[str, dict]] = sorted(
            [(v.strip("-"), d) for d in raw_derivs if d["type"] == "SUFFIX"
             for v in d["surface_variants"]],
            key=lambda x: -len(x[0])
        )
        self.prefixes: List[Tuple[str, dict]] = sorted(
            [(v.strip("-"), d) for d in raw_derivs if d["type"] == "PREFIX"
             for v in d["surface_variants"]],
            key=lambda x: -len(x[0])
        )

        # Sort paradigms longest-suffix-first for greedy matching
        self._paradigms = sorted(_VERB_PARADIGMS,
                                 key=lambda x: -len(x[0]))

    # ── Accent stripping ────────────────────────────────────────────────────

    @staticmethod
    def _normalize(word: str) -> str:
        """Lowercase and strip accents for lookup."""
        return _strip_accents(word.lower())

    @staticmethod
    def _parse_tag_string(tag_str: str) -> Dict[str, str]:
        """Parse pipe-delimited key=value tag string."""
        tags: Dict[str, str] = {}
        for pair in tag_str.split("|"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                tags[k] = v
        return tags

    # ── Infinitive recognition ──────────────────────────────────────────────

    @staticmethod
    def _is_infinitive(w: str) -> Optional[str]:
        """Check if word is an infinitive. Returns the word if yes, else None."""
        # Spanish infinitives: -ar, -er, -ir. Minimum 3 chars (dar, ver, ir).
        # "ir" (2 chars) is a special case handled in irregulars.
        if len(w) >= 3:
            for ending in ("ar", "er", "ir"):
                if w.endswith(ending):
                    return w
        return None

    # ── Enclitic stripping ──────────────────────────────────────────────────

    def _strip_enclitics(self, w: str) -> Tuple[str, List[str]]:
        """
        Strip enclitic pronouns from the end of a word.
        Returns (stem, list_of_clitics) or (w, []) if none found.
        Tries 3-clitic, 2-clitic, then 1-clitic sequences.
        """
        for n_clitics in (3, 2, 1):
            result = self._try_strip_n_clitics(w, n_clitics)
            if result is not None:
                stem, clitic_list = result
                # Verify stem looks like a verb form (min length, has vowel)
                if len(stem) >= 2 and any(c in self.VOWELS for c in stem):
                    # Strip accent from stem (accent restoration)
                    stem = _strip_accents(stem)
                    return stem, clitic_list
        return w, []

    def _try_strip_n_clitics(self, w: str, n: int
                             ) -> Optional[Tuple[str, List[str]]]:
        """Try to strip exactly n clitics from end of word."""
        if n == 0:
            return None
        remaining = w
        found: List[str] = []
        for _ in range(n):
            matched = False
            for cl in _ENCLITICS_SORTED:
                if remaining.endswith(cl) and len(remaining) > len(cl):
                    found.insert(0, cl)
                    remaining = remaining[:-len(cl)]
                    matched = True
                    break
            if not matched:
                return None
        if len(remaining) < 2:
            return None
        return remaining, found

    def _validate_clitic_stem(self, stem: str) -> bool:
        """
        Verify that the stem remaining after clitic stripping is plausibly
        a verb form (infinitive, gerund, imperative, or conjugated).
        Must be strict to prevent false positives like "rapidamen" + "te".
        """
        # Check irregular lookup
        if stem in self.irregulars:
            entry = self.irregulars[stem]
            return entry["pos"] == "VERB"
        # Check if it's an infinitive
        if self._is_infinitive(stem) is not None and len(stem) >= 3:
            return True
        # Check if it ends like a gerund
        if (stem.endswith("ando") or stem.endswith("iendo")) and len(stem) >= 5:
            return True
        # Check if it matches a distinctive verb suffix (only long ones)
        for suffix, conj_class, tags, min_stem in self._paradigms:
            if len(suffix) < 3:
                continue  # skip short ambiguous suffixes
            if stem.endswith(suffix) and len(stem) - len(suffix) >= min_stem:
                return True
        return False

    # ── Verb conjugation matching ───────────────────────────────────────────

    def _match_verb_long(self, w: str) -> Optional[Tuple[str, Dict[str, str], str]]:
        """
        Match word against verb paradigm tables — long suffix mode.
        Only accepts suffixes >= 3 characters to catch distinctive
        verb endings without ambiguity with future/conditional.
        """
        for suffix, conj_class, tags, min_stem in self._paradigms:
            if len(suffix) < 3:
                continue
            if not w.endswith(suffix):
                continue
            stem = w[:-len(suffix)] if suffix else w
            if len(stem) < min_stem:
                continue
            return stem, dict(tags), conj_class
        return None

    def _match_verb_strict(self, w: str) -> Optional[Tuple[str, Dict[str, str], str]]:
        """
        Match word against verb paradigm tables — strict mode.
        Only accepts suffixes >= 2 characters to avoid single-char false
        positives (-o, -a, -e) that clash with noun gender endings.
        """
        for suffix, conj_class, tags, min_stem in self._paradigms:
            if len(suffix) < 2:
                continue
            if not w.endswith(suffix):
                continue
            stem = w[:-len(suffix)] if suffix else w
            if len(stem) < min_stem:
                continue
            return stem, dict(tags), conj_class
        return None

    def _match_verb(self, w: str) -> Optional[Tuple[str, Dict[str, str], str]]:
        """
        Match word against verb paradigm tables — relaxed mode.
        Returns (stem, tags, conjugation_class) or None.
        Only accepts matches where stem >= min_stem_len.
        """
        for suffix, conj_class, tags, min_stem in self._paradigms:
            if not w.endswith(suffix):
                continue
            stem = w[:-len(suffix)] if suffix else w

            if len(stem) < min_stem:
                continue

            return stem, dict(tags), conj_class

        return None

    # ── Future / conditional matching ───────────────────────────────────────

    def _match_future_conditional(self, w: str
                                  ) -> Optional[Tuple[str, Dict[str, str]]]:
        """
        Match future/conditional tenses which attach to full infinitive.
        Only match suffixes that are at least 2 characters to avoid
        false positives (e.g., hablara should NOT match as hablar + a).
        """
        # Future suffixes (added to infinitive) — only >= 2 char suffixes
        # to avoid false positives (e.g., hablara should NOT match as
        # hablar + a). Single-char suffixes -e and -a are excluded.
        _FUT = [
            ("emos", "1", "PL"), ("eis", "2", "PL"),
            ("as", "2", "SG"), ("an", "3", "PL"),
        ]
        # Conditional suffixes
        _COND = [
            ("iamos", "1", "PL"), ("iais", "2", "PL"),
            ("ias", "2", "SG"), ("ian", "3", "PL"),
            ("ia", "1", "SG"), ("ia", "3", "SG"),
        ]
        # 1SG future (-e) and 3SG future (-a) are too short / ambiguous
        # with subjunctive forms; handled by paradigm tables instead.

        for inf_end in ("ar", "er", "ir"):
            for suf, person, num in _FUT:
                full_suf = inf_end + suf
                if w.endswith(full_suf) and len(w) > len(full_suf) + 1:
                    stem = w[:-len(suf)]  # keep the infinitive ending
                    return (stem, {"tense": "FUT", "mood": "IND",
                                   "person": person, "num": num})

            for suf, person, num in _COND:
                full_suf = inf_end + suf
                if w.endswith(full_suf) and len(w) > len(full_suf) + 1:
                    stem = w[:-len(suf)]
                    return (stem, {"tense": "COND", "mood": "IND",
                                   "person": person, "num": num})

        return None

    # ── Noun gender/number matching ─────────────────────────────────────────

    def _match_noun(self, w: str) -> Optional[Tuple[str, Dict[str, str],
                                                     str, Dict]]:
        """
        Match noun gender/number patterns.
        Returns (stem, tags, pos, clitics) or None.
        """
        clitics: Dict[str, List[str]] = {}

        # Check nouns in irregulars
        if w in self.irregulars:
            entry = self.irregulars[w]
            if entry["pos"] == "NOUN":
                tags = self._parse_tag_string(entry["tag"])
                return entry["base"], tags, "NOUN", clitics

        # Plural stripping
        # 1. -ces -> -z
        if w.endswith("ces") and len(w) > 4:
            singular = w[:-3] + "z"
            tags = {"num": "PL"}
            gender = self._assign_gender(singular)
            if gender:
                tags["gender"] = gender
            return singular, tags, "NOUN", clitics

        # 2. -es (after consonant) — require stem >= 3 chars to avoid
        #    matching short verb forms like "comes" (com + es)
        if w.endswith("es") and len(w) > 5:
            stem = w[:-2]
            if stem and stem[-1] not in self.VOWELS and len(stem) >= 3:
                tags = {"num": "PL"}
                gender = self._assign_gender(stem)
                if gender:
                    tags["gender"] = gender
                return stem, tags, "NOUN", clitics

        # 3. -s (after vowel) — only for -os/-as patterns (clear noun plurals)
        #    to avoid matching verb forms like "hablas", "comes" as nouns.
        if w.endswith("os") and len(w) > 3:
            stem = w[:-1]
            tags = {"num": "PL"}
            gender = self._assign_gender(stem)
            if gender:
                tags["gender"] = gender
            return stem, tags, "NOUN", clitics
        if w.endswith("as") and len(w) > 4:
            stem = w[:-1]
            # Only match -as as noun plural if the singular form is known
            # (in irregulars or gender exceptions) to avoid matching verb
            # forms like "hablas" as nouns
            if stem in self.irregulars or stem in _GENDER_EXCEPTIONS:
                tags = {"num": "PL"}
                gender = self._assign_gender(stem)
                if gender:
                    tags["gender"] = gender
                return stem, tags, "NOUN", clitics

        # Singular — only return as noun if the word is not likely to be a
        # verb form (words ending in -o/-a/-e are ambiguous). Only match
        # as singular noun when there's no other interpretation possible
        # (handled by the UNKNOWN fallback and relaxed verb matching).
        # Do NOT match singular nouns here to avoid blocking verb detection.
        return None

    @staticmethod
    def _assign_gender(w: str) -> Optional[str]:
        """Assign grammatical gender based on word ending."""
        # Exception list first
        if w in _GENDER_EXCEPTIONS:
            return _GENDER_EXCEPTIONS[w]

        # Ending-based heuristics
        if w.endswith("o"):
            return "MASC"
        if w.endswith("a"):
            return "FEM"
        # Feminine endings
        for suf in ("cion", "sion", "dad", "tad", "tud", "umbre"):
            if w.endswith(suf):
                return "FEM"
        # Masculine endings
        for suf in ("or", "aje", "men"):
            if w.endswith(suf):
                return "MASC"

        return None

    # ── Step A: Inflectional stripping ──────────────────────────────────────

    def _step_a(self, word: str) -> Tuple[str, Dict[str, str], str,
                                          Dict[str, List[str]]]:
        """
        Returns (stem, tags, pos, clitics).
        """
        w = self._normalize(word)
        clitics: Dict[str, List[str]] = {}

        # 1. Closed-class lookup
        if w in CLOSED_CLASS:
            pos, tags = CLOSED_CLASS[w]
            return w, dict(tags), pos, clitics

        # 2. Irregular form lookup
        if w in self.irregulars:
            entry = self.irregulars[w]
            tags = self._parse_tag_string(entry["tag"])
            return entry["base"], tags, entry["pos"], clitics

        # 3. -mente adverbs (transparently segmentable, fully productive)
        if w.endswith("mente") and len(w) > 7:
            return w, {}, "ADV", clitics

        # 4. Infinitive recognition (before clitic/verb stripping)
        if self._is_infinitive(w) is not None and len(w) >= 3:
            return w, {"form": "INF"}, "VERB", clitics

        # 4. Enclitic stripping (try before regular conjugation)
        stem_after_clitic, clitic_list = self._strip_enclitics(w)
        if clitic_list and self._validate_clitic_stem(stem_after_clitic):
            # Re-check irregular lookup on stripped stem
            if stem_after_clitic in self.irregulars:
                entry = self.irregulars[stem_after_clitic]
                tags = self._parse_tag_string(entry["tag"])
                tags["clitic_obj"] = "+".join(
                    c.upper() for c in clitic_list)
                clitics = {"enclitic": clitic_list}
                return entry["base"], tags, entry["pos"], clitics

            # Check infinitive
            if self._is_infinitive(stem_after_clitic) is not None:
                tags: Dict[str, str] = {"form": "INF"}
                tags["clitic_obj"] = "+".join(
                    c.upper() for c in clitic_list)
                clitics = {"enclitic": clitic_list}
                return stem_after_clitic, tags, "VERB", clitics

            # Try matching stripped stem as conjugated verb
            result = self._match_verb(stem_after_clitic)
            if result is not None:
                stem, tags, conj = result
                tags["clitic_obj"] = "+".join(
                    c.upper() for c in clitic_list)
                clitics = {"enclitic": clitic_list}
                infinitive = stem + conj
                return infinitive, tags, "VERB", clitics

        # 5. Regular verb conjugation — long suffixes only (>= 3 chars).
        #    Catches imperfect subjunctive, preterite, imperfect,
        #    gerund, participle, etc. without ambiguity.
        result = self._match_verb_long(w)
        if result is not None:
            stem, tags, conj = result
            infinitive = stem + conj
            return infinitive, tags, "VERB", clitics

        # 6. Future / conditional (attach to full infinitive).
        fut_result = self._match_future_conditional(w)
        if fut_result is not None:
            return fut_result[0], fut_result[1], "VERB", clitics

        # 7. Noun gender/number (checked before short verb suffixes
        #    to prevent -es plural nouns from matching as verbs)
        noun_result = self._match_noun(w)
        if noun_result is not None:
            return noun_result

        # 8. Regular verb conjugation — medium suffixes (>= 2 chars).
        result = self._match_verb_strict(w)
        if result is not None:
            stem, tags, conj = result
            infinitive = stem + conj
            return infinitive, tags, "VERB", clitics

        # 9. Verb matching — relaxed (single-char suffixes -o, -a, -e)
        result = self._match_verb(w)
        if result is not None:
            stem, tags, conj = result
            infinitive = stem + conj
            return infinitive, tags, "VERB", clitics

        # 8. Default
        return w, {}, "UNKNOWN", clitics

    # ── Step B: Derivational detection ──────────────────────────────────────

    def _step_b(self, stem: str) -> Tuple[str, List[str]]:
        """Strip one layer of derivational morphology."""
        chain: List[str] = []

        for surface, deriv in self.suffixes:
            if stem.endswith(surface) and len(stem) - len(surface) >= 3:
                chain.append(f"{surface}\u2192{deriv['derives']}")
                return stem[:-len(surface)], chain

        for surface, deriv in self.prefixes:
            if stem.startswith(surface) and len(stem) - len(surface) >= 3:
                chain.append(f"{surface}\u2192{deriv['derives']}")
                return stem[len(surface):], chain

        return stem, chain

    # ── Step C: Root extraction ─────────────────────────────────────────────

    def _step_c(self, stem: str) -> str:
        """Iteratively apply Step B up to 4 times."""
        root = stem
        for _ in range(4):
            new_root, _ = self._step_b(root)
            if new_root == root:
                break
            root = new_root
        return root

    # ── Public API ──────────────────────────────────────────────────────────

    def analyze(self, word: str) -> TokenInfo:
        """Analyze a single word and return its TokenInfo."""
        stem, tags, pos, clitics = self._step_a(word)

        # Derivational analysis only on UNKNOWN pos
        if pos == "UNKNOWN":
            _, derived_chain = self._step_b(stem)
            root = self._step_c(stem)
        else:
            derived_chain = []
            root = stem

        return TokenInfo(
            surface=word, clitics=clitics, template="",
            root=root, tags=tags, pos=pos,
            derived_chain=derived_chain,
        )

    def analyze_sentence(self, sentence: str
                         ) -> Tuple[List[TokenInfo], bool, str]:
        """Analyze a sentence and validate morphological consistency."""
        tokens = [self.analyze(w) for w in sentence.split()]
        word_ok = check_morph_sequence_es(tokens)
        sent_ok, sent_msg = validate_sentence_structure_es(tokens)
        return tokens, word_ok and sent_ok, sent_msg
