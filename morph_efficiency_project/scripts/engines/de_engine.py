"""
engines/de_engine.py
--------------------
German morphology engine (Steps A/B/C).

German is an irregular fusional language. A single word form can encode person,
number, tense, mood (verbs), or case, gender, number (nouns/adjectives) via
inflectional suffixes and stem alternations. The most distinctive feature is
productive compounding: multiple stems are concatenated into single orthographic
words with optional linking elements (Fugenelemente).

Step A -- Inflectional stripping: closed-class intercept, irregular lookup,
          Partizip II/I detection, verb conjugation, noun declension,
          adjective declension, comparative/superlative, separable prefixes.
Step B -- Derivational pattern detection via de_derivations.json.
Step C -- Stem identification: iterative Step B + compound splitting (max 4).
"""

import json
import os
from typing import Dict, List, Optional, Tuple

from .shared import (
    TokenInfo,
    check_morph_sequence_de,
    validate_sentence_structure_de,
)


# ── Closed-class dictionary (~240 entries) ──────────────────────────────────

CLOSED_CLASS: Dict[str, Tuple[str, Dict[str, str]]] = {}

# Definite articles
for _w, _t in [
    ("der", {"gender": "MASC", "case": "NOM", "num": "SG"}),
    ("die", {"gender": "FEM", "case": "NOM", "num": "SG"}),
    ("das", {"gender": "NEUT", "case": "NOM", "num": "SG"}),
    ("dem", {"gender": "MASC", "case": "DAT", "num": "SG", "ambig": "YES"}),
    ("den", {"gender": "MASC", "case": "ACC", "num": "SG", "ambig": "YES"}),
    ("des", {"gender": "MASC", "case": "GEN", "num": "SG", "ambig": "YES"}),
]:
    CLOSED_CLASS[_w] = ("DET", _t)

# Indefinite articles
for _w, _t in [
    ("ein", {"gender": "MASC", "case": "NOM", "num": "SG", "ambig": "YES"}),
    ("eine", {"gender": "FEM", "case": "NOM", "num": "SG"}),
    ("einem", {"gender": "MASC", "case": "DAT", "num": "SG", "ambig": "YES"}),
    ("einen", {"gender": "MASC", "case": "ACC", "num": "SG"}),
    ("einer", {"gender": "FEM", "case": "DAT", "num": "SG", "ambig": "YES"}),
    ("eines", {"gender": "MASC", "case": "GEN", "num": "SG", "ambig": "YES"}),
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("DET", _t)

# Prepositions (accusative)
for _w in ["bis", "durch", "für", "fuer", "gegen", "ohne", "um"]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("ADP", {"case_gov": "ACC"})

# Prepositions (dative)
for _w in ["aus", "bei", "mit", "nach", "seit", "von", "zu",
           "außer", "ausser", "gegenüber", "gegenueber"]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("ADP", {"case_gov": "DAT"})

# Two-way prepositions (acc or dat)
for _w in ["an", "auf", "hinter", "in", "neben",
           "über", "ueber", "unter", "vor", "zwischen"]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("ADP", {"case_gov": "ACC_DAT"})

# Genitive prepositions
for _w in ["während", "waehrend", "wegen", "trotz", "statt",
           "gemäß", "gemaess", "laut", "mangels", "mittels",
           "samt", "entlang"]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("ADP", {"case_gov": "GEN"})

# Personal pronouns
for _w, _t in [
    ("ich",    {"person": "1", "num": "SG", "case": "NOM"}),
    ("du",     {"person": "2", "num": "SG", "case": "NOM"}),
    ("er",     {"person": "3", "num": "SG", "case": "NOM", "gender": "MASC"}),
    ("sie",    {"person": "3", "num": "SG", "case": "NOM", "gender": "FEM", "ambig": "YES"}),
    ("es",     {"person": "3", "num": "SG", "case": "NOM", "gender": "NEUT"}),
    ("wir",    {"person": "1", "num": "PL", "case": "NOM"}),
    ("ihr",    {"person": "2", "num": "PL", "case": "NOM", "ambig": "YES"}),
    ("mich",   {"person": "1", "num": "SG", "case": "ACC"}),
    ("dich",   {"person": "2", "num": "SG", "case": "ACC"}),
    ("ihn",    {"person": "3", "num": "SG", "case": "ACC", "gender": "MASC"}),
    ("uns",    {"person": "1", "num": "PL", "case": "ACC", "ambig": "YES"}),
    ("euch",   {"person": "2", "num": "PL", "case": "ACC", "ambig": "YES"}),
    ("mir",    {"person": "1", "num": "SG", "case": "DAT"}),
    ("dir",    {"person": "2", "num": "SG", "case": "DAT"}),
    ("ihm",    {"person": "3", "num": "SG", "case": "DAT", "gender": "MASC", "ambig": "YES"}),
    ("ihnen",  {"person": "3", "num": "PL", "case": "DAT"}),
    ("sich",   {"person": "3", "subcat": "REFL"}),
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("PRON", _t)

# Possessive pronouns (base forms)
for _w, _t in [
    ("mein",   {"person": "1", "num": "SG", "subcat": "POSS"}),
    ("dein",   {"person": "2", "num": "SG", "subcat": "POSS"}),
    ("sein",   {"person": "3", "num": "SG", "subcat": "POSS", "gender": "MASC"}),
    ("unser",  {"person": "1", "num": "PL", "subcat": "POSS"}),
    ("euer",   {"person": "2", "num": "PL", "subcat": "POSS"}),
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("PRON", _t)

# Interrogative pronouns
for _w, _t in [
    ("wer",    {"subcat": "INTERR", "case": "NOM"}),
    ("wen",    {"subcat": "INTERR", "case": "ACC"}),
    ("wem",    {"subcat": "INTERR", "case": "DAT"}),
    ("wessen", {"subcat": "INTERR", "case": "GEN"}),
    ("was",    {"subcat": "INTERR"}),
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("PRON", _t)

# Demonstrative pronouns
for _w, _t in [
    ("dieser", {"subcat": "DEM", "gender": "MASC", "case": "NOM", "num": "SG"}),
    ("diese",  {"subcat": "DEM", "gender": "FEM", "case": "NOM", "num": "SG", "ambig": "YES"}),
    ("dieses", {"subcat": "DEM", "gender": "NEUT", "case": "NOM", "num": "SG"}),
    ("jener",  {"subcat": "DEM", "gender": "MASC", "case": "NOM", "num": "SG"}),
    ("jene",   {"subcat": "DEM", "gender": "FEM", "case": "NOM", "num": "SG", "ambig": "YES"}),
    ("jenes",  {"subcat": "DEM", "gender": "NEUT", "case": "NOM", "num": "SG"}),
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("PRON", _t)

# Indefinite pronouns
for _w, _t in [
    ("man",     {"subcat": "INDEF"}),
    ("jeder",   {"subcat": "INDEF", "gender": "MASC", "num": "SG"}),
    ("jede",    {"subcat": "INDEF", "gender": "FEM", "num": "SG"}),
    ("jedes",   {"subcat": "INDEF", "gender": "NEUT", "num": "SG"}),
    ("alle",    {"subcat": "INDEF", "num": "PL"}),
    ("manche",  {"subcat": "INDEF", "num": "PL"}),
    ("einige",  {"subcat": "INDEF", "num": "PL"}),
    ("kein",    {"subcat": "INDEF", "gender": "MASC", "num": "SG"}),
    ("keine",   {"subcat": "INDEF", "num": "SG", "ambig": "YES"}),
    ("etwas",   {"subcat": "INDEF"}),
    ("nichts",  {"subcat": "INDEF"}),
    ("jemand",  {"subcat": "INDEF"}),
    ("niemand", {"subcat": "INDEF"}),
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("PRON", _t)

# Coordinating conjunctions
for _w, _t in [
    ("und",     {"subcat": "COORD"}),
    ("oder",    {"subcat": "COORD"}),
    ("aber",    {"subcat": "COORD"}),
    ("sondern", {"subcat": "COORD"}),
    ("denn",    {"subcat": "COORD"}),
    ("doch",    {"subcat": "COORD"}),
    ("jedoch",  {"subcat": "COORD"}),
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("CONJ", _t)

# Subordinating conjunctions
for _w, _t in [
    ("weil",    {"subcat": "SUBORD"}),
    ("dass",    {"subcat": "SUBORD"}),
    ("wenn",    {"subcat": "SUBORD"}),
    ("als",     {"subcat": "SUBORD"}),
    ("ob",      {"subcat": "SUBORD"}),
    ("obwohl",  {"subcat": "SUBORD"}),
    ("damit",   {"subcat": "SUBORD"}),
    ("bevor",   {"subcat": "SUBORD"}),
    ("nachdem", {"subcat": "SUBORD"}),
    ("seitdem", {"subcat": "SUBORD"}),
    ("falls",   {"subcat": "SUBORD"}),
    ("indem",   {"subcat": "SUBORD"}),
    ("sobald",  {"subcat": "SUBORD"}),
    ("solange", {"subcat": "SUBORD"}),
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("CONJ", _t)

# Correlative conjunctions
for _w, _t in [
    ("weder",    {"subcat": "CORREL"}),
    ("noch",     {"subcat": "CORREL"}),
    ("entweder", {"subcat": "CORREL"}),
    ("sowohl",   {"subcat": "CORREL"}),
    ("zwar",     {"subcat": "CORREL"}),
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("CONJ", _t)

# Particles and adverbs
for _w, _t in [
    ("nicht",   {"subcat": "NEG"}),
    ("ja",      {"subcat": "MODAL_PART"}),
    ("nein",    {"subcat": "NEG"}),
    ("schon",   {"subcat": "MODAL_PART"}),
    ("mal",     {"subcat": "MODAL_PART"}),
    ("halt",    {"subcat": "MODAL_PART"}),
    ("eben",    {"subcat": "MODAL_PART"}),
    ("wohl",    {"subcat": "MODAL_PART"}),
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("PART", _t)

# Fixed adverbs
for _w, _t in [
    ("hier",    {"subcat": "SPATIAL"}),
    ("dort",    {"subcat": "SPATIAL"}),
    ("heute",   {"subcat": "TEMP"}),
    ("gestern", {"subcat": "TEMP"}),
    ("morgen",  {"subcat": "TEMP"}),
    ("immer",   {"subcat": "TEMP"}),
    ("nie",     {"subcat": "TEMP"}),
    ("niemals", {"subcat": "TEMP"}),
    ("sehr",    {"subcat": "DEGREE"}),
    ("auch",    {"subcat": "FOCUS"}),
    ("nur",     {"subcat": "FOCUS"}),
    ("so",      {"subcat": "MANNER"}),
    ("dann",    {"subcat": "TEMP"}),
    ("schon",   {"subcat": "TEMP"}),
    ("noch",    {"subcat": "TEMP"}),
    ("ganz",    {"subcat": "DEGREE"}),
    ("fast",    {"subcat": "DEGREE"}),
    ("etwa",    {"subcat": "DEGREE"}),
]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("ADV", _t)

# Auxiliary verb forms (sein, haben, werden are in irregulars;
# these are listed here so closed-class intercept catches the
# infinitive forms used as auxiliaries)
for _w in ["sein", "haben", "werden"]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("AUX", {"aux": "YES"})

# Modal infinitive forms
for _w in ["können", "müssen", "dürfen", "sollen", "wollen", "mögen"]:
    if _w not in CLOSED_CLASS:
        CLOSED_CLASS[_w] = ("AUX", {"modal": "YES"})


# ── Separable & non-separable prefixes ─────────────────────────────────────

SEPARABLE_PREFIXES = [
    "zurück", "zurueck", "zusammen", "weiter", "empor",
    "nieder", "heraus", "hinaus", "heran", "herein", "hinein",
    "herauf", "hinauf", "herab", "hinab", "hervor", "herum",
    "hinweg", "hierher", "dahin", "fort", "fest", "frei",
    "heim", "los", "weg", "dar",
    "ab", "an", "auf", "aus", "bei", "ein", "mit",
    "nach", "vor", "zu", "hin", "her", "um",
]
# Sort longest-first for greedy matching
SEPARABLE_PREFIXES.sort(key=len, reverse=True)

NON_SEPARABLE_PREFIXES = ["be", "emp", "ent", "er", "ge", "miss", "ver", "zer"]


class GermanEngine:
    """
    German morphology engine.

    Step A -- Inflectional stripping: closed-class intercept, irregular
              form lookup, Partizip II/I detection, verb conjugation
              stripping, noun declension, adjective declension,
              comparative/superlative, separable prefix detection.
    Step B -- Derivational pattern detection via de_derivations.json.
    Step C -- Stem identification: iterative Step B + compound splitting
              (max 4 rounds).
    """

    VOWELS = set("aeiouäöü")

    def __init__(self, config_dir: str = "morph_efficiency_project/configs"):
        with open(os.path.join(config_dir, "de_irregulars.json"),
                  encoding="utf-8") as f:
            self.irregulars: Dict[str, dict] = json.load(f)

        with open(os.path.join(config_dir, "de_derivations.json"),
                  encoding="utf-8") as f:
            raw_derivs = json.load(f)

        with open(os.path.join(config_dir, "de_stems.json"),
                  encoding="utf-8") as f:
            self.stems: Dict[str, str] = json.load(f)

        # Build case-insensitive stem lookup
        self._stems_lower: Dict[str, str] = {
            k.lower(): v for k, v in self.stems.items()
        }

        # Derivation rules sorted longest-first
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

    # ── Utility ────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_tag_string(tag_str: str) -> Dict[str, str]:
        tags: Dict[str, str] = {}
        for pair in tag_str.split("|"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                tags[k] = v
        return tags

    @staticmethod
    def _un_umlaut(s: str) -> Optional[str]:
        """Try to reverse Umlaut on the last umlautable vowel."""
        _map = {"ä": "a", "ö": "o", "ü": "u"}
        chars = list(s)
        # Right-to-left: find last umlauted vowel
        for i in range(len(chars) - 1, -1, -1):
            if chars[i] in _map:
                chars[i] = _map[chars[i]]
                return "".join(chars)
        return None

    def _is_known_stem(self, stem: str) -> bool:
        return stem in self.stems or stem.lower() in self._stems_lower

    def _canonical_stem(self, stem: str) -> str:
        """Return the dictionary-case form of a stem, or the input if unknown."""
        if stem in self.stems:
            return stem
        low = stem.lower()
        if low in self._stems_lower:
            # Find original-case key
            for k in self.stems:
                if k.lower() == low:
                    return k
        return stem

    # ── Compound splitting ─────────────────────────────────────────────────

    _FUGENELEMENTE = ["", "s", "es", "n", "en", "er", "e"]

    def split_compound(self, word: str, max_depth: int = 3) -> List[str]:
        """
        Attempt to split a compound word into known stems.
        Returns list of component stems, or [word] if no valid split.
        """
        if len(word) < 6:
            return [word]
        if self._is_known_stem(word):
            return [word]
        if max_depth <= 0:
            return [word]

        candidates: List[Tuple[List[str], str, int]] = []

        for split_pos in range(3, len(word) - 2):
            left = word[:split_pos]
            remainder = word[split_pos:]

            for fuge in self._FUGENELEMENTE:
                if not remainder.startswith(fuge):
                    continue
                right = remainder[len(fuge):]
                if len(right) < 3:
                    continue

                if self._is_known_stem(left):
                    right_parts = self.split_compound(right, max_depth - 1)
                    if all(self._is_known_stem(p) for p in right_parts):
                        canon_left = self._canonical_stem(left)
                        canon_right = [self._canonical_stem(p)
                                       for p in right_parts]
                        parts = [canon_left] + canon_right
                        score = sum(len(p) for p in parts)
                        candidates.append((parts, fuge, score))

        if not candidates:
            return [word]

        # Prefer fewer parts, then longer first component
        best = max(candidates, key=lambda c: (
            -len(c[0]),   # fewer parts preferred
            len(c[0][0])  # longer first component preferred
        ))
        return best[0]

    # ── Step A: Inflectional stripping ─────────────────────────────────────

    def _step_a(self, word: str) -> Tuple[str, Dict[str, str], str]:
        w = word.lower()

        # 1. Closed-class lookup
        if w in CLOSED_CLASS:
            pos, tags = CLOSED_CLASS[w]
            return w, dict(tags), pos

        # 2. Irregular form lookup
        if word in self.irregulars:
            entry = self.irregulars[word]
            return entry["base"], self._parse_tag_string(entry["tag"]), entry["pos"]
        if w in self.irregulars:
            entry = self.irregulars[w]
            return entry["base"], self._parse_tag_string(entry["tag"]), entry["pos"]

        # 3. Partizip II detection
        result = self._try_partizip_ii(w)
        if result is not None:
            return result

        # 4. Partizip I detection (-end)
        if w.endswith("end") and len(w) > 5:
            stem = w[:-3]
            return stem + "en", {"aspect": "PROG"}, "VERB"

        # 5. Separable prefix + infinitive (aufmachen, einladen)
        result = self._try_separable_infinitive(w)
        if result is not None:
            return result

        # 6. Verb conjugation stripping
        result = self._try_verb_conjugation(w)
        if result is not None:
            return result

        # 7. Adjective comparative/superlative
        result = self._try_comparative_superlative(w)
        if result is not None:
            return result

        # 8. Adjective declension
        result = self._try_adjective_declension(w)
        if result is not None:
            return result

        # 9. Noun declension (genitive -s/-es, dative plural -n)
        result = self._try_noun_declension(w)
        if result is not None:
            return result

        return w, {}, "UNKNOWN"

    def _try_partizip_ii(self, w: str) -> Optional[Tuple[str, Dict[str, str], str]]:
        """Detect Partizip II forms: ge-...-t, ge-...-en, separable+ge-."""
        tags: Dict[str, str] = {"aspect": "PERF"}

        # Pattern C: separable prefix + ge- + stem + -t/-en
        for prefix in SEPARABLE_PREFIXES:
            if w.startswith(prefix + "ge"):
                rest = w[len(prefix) + 2:]
                # weak: -t
                if rest.endswith("t") and len(rest) > 2:
                    stem = rest[:-1]
                    if rest.endswith("et") and len(rest) > 3:
                        stem = rest[:-2]
                    tags["verb_prefix"] = prefix.upper()
                    return stem + "en", tags, "VERB"
                # strong: -en
                if rest.endswith("en") and len(rest) > 3:
                    stem = rest[:-2]
                    tags["verb_prefix"] = prefix.upper()
                    # Try to find the infinitive via irregulars
                    return stem + "en", tags, "VERB"

        # Pattern D: non-separable prefix, no ge-
        for prefix in NON_SEPARABLE_PREFIXES:
            if w.startswith(prefix) and prefix != "ge":
                rest = w[len(prefix):]
                if rest.endswith("t") and len(rest) >= 3 and len(w) > 5:
                    stem = rest[:-1]
                    if rest.endswith("et") and len(rest) > 3:
                        stem = rest[:-2]
                    return prefix + stem + "en", tags, "VERB"

        # Pattern A: ge-...-t (weak)
        if w.startswith("ge") and w.endswith("t") and len(w) > 5:
            rest = w[2:-1]
            if rest.endswith("e") and len(rest) > 2:
                rest = rest[:-1]
            if len(rest) >= 2:
                return rest + "en", tags, "VERB"

        # Pattern B: ge-...-en (strong)
        if w.startswith("ge") and w.endswith("en") and len(w) > 6:
            rest = w[2:-2]
            if len(rest) >= 2:
                # The Partizip II stem may differ from infinitive
                # Check irregulars for the full ge-form first (already done above)
                return rest + "en", tags, "VERB"

        return None

    def _try_separable_infinitive(self, w: str
                                  ) -> Optional[Tuple[str, Dict[str, str], str]]:
        """Detect separable prefix + infinitive: aufmachen -> machen."""
        if not w.endswith("en") or len(w) < 6:
            return None
        for prefix in SEPARABLE_PREFIXES:
            if w.startswith(prefix):
                rest = w[len(prefix):]
                if len(rest) >= 4 and rest.endswith("en"):
                    # Check that the base verb part looks plausible
                    stem = rest[:-2]
                    if len(stem) >= 2 and any(c in self.VOWELS for c in stem):
                        return rest, {"verb_prefix": prefix.upper()}, "VERB"
        return None

    def _try_verb_conjugation(self, w: str
                              ) -> Optional[Tuple[str, Dict[str, str], str]]:
        """Strip regular verb conjugation suffixes."""
        # Weak Präteritum patterns (longest first)
        # The dental suffix -te- must not be confused with stems ending
        # in -t/-d which use an epenthetic -e- in the Präsens instead.
        _PRAT_ENDINGS = [
            ("test", {"tense": "PAST", "person": "2", "num": "SG"}),
            ("tet",  {"tense": "PAST", "person": "2", "num": "PL"}),
            ("ten",  {"tense": "PAST", "person": "1", "num": "PL"}),
            ("te",   {"tense": "PAST", "person": "1", "num": "SG"}),
        ]
        for suf, tags in _PRAT_ENDINGS:
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                stem = w[:-len(suf)]
                if any(c in self.VOWELS for c in stem):
                    # Guard: only accept as Präteritum if the verb stem
                    # is recognized. Otherwise the Präsens rules with
                    # different suffix splits will handle it.
                    if self._is_known_stem(stem):
                        return stem + "en", dict(tags), "VERB"

        # Präsens patterns (longest first)
        _PRES_ENDINGS = [
            ("est", {"tense": "PRES", "person": "2", "num": "SG"}),
            ("et",  {"tense": "PRES", "person": "3", "num": "SG", "ambig": "YES"}),
            ("st",  {"tense": "PRES", "person": "2", "num": "SG"}),
            ("en",  {"tense": "PRES", "person": "1", "num": "PL"}),
            ("t",   {"tense": "PRES", "person": "3", "num": "SG", "ambig": "YES"}),
            ("e",   {"tense": "PRES", "person": "1", "num": "SG"}),
        ]
        for suf, tags in _PRES_ENDINGS:
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                stem = w[:-len(suf)]
                if any(c in self.VOWELS for c in stem):
                    # Guard: for ambiguous short suffixes, check plausibility.
                    if suf in ("en", "e", "t", "er", "es", "et", "em", "st"):
                        stem_pos = self._stems_lower.get(stem.lower())
                        # If stem is a known non-verb, skip verb parse
                        if stem_pos and stem_pos != "VERB":
                            continue
                        # If stem is unknown and the suffix is short,
                        # require the stem to be a known verb stem for
                        # long words to avoid false positives on nouns.
                        if suf in ("en", "t") and len(w) > 8:
                            if not self._is_known_stem(stem):
                                continue
                        # For -er suffix: if the WHOLE word is a known
                        # NOUN stem, prefer the noun reading.
                        if suf == "er" and self._is_known_stem(w):
                            word_pos = self._stems_lower.get(w.lower())
                            if word_pos == "NOUN":
                                continue
                    return stem + "en", dict(tags), "VERB"

        return None

    def _try_comparative_superlative(self, w: str
                                     ) -> Optional[Tuple[str, Dict[str, str], str]]:
        """Detect comparative -er and superlative -st/-est patterns."""
        # Superlative: -sten, -sten (inflected)
        if w.endswith("sten") and len(w) > 6:
            stem = w[:-4]
            tags = {"degree": "SUPER"}
            if self._is_known_stem(stem):
                return stem, tags, "ADJ"
            un = self._un_umlaut(stem)
            if un and self._is_known_stem(un):
                tags["umlaut"] = "YES"
                return un, tags, "ADJ"

        # Superlative: -ste (uninflected)
        if w.endswith("ste") and len(w) > 5:
            stem = w[:-3]
            tags = {"degree": "SUPER"}
            if self._is_known_stem(stem):
                return stem, tags, "ADJ"
            un = self._un_umlaut(stem)
            if un and self._is_known_stem(un):
                tags["umlaut"] = "YES"
                return un, tags, "ADJ"

        # Superlative: -est (before declension ending)
        if w.endswith("est") and len(w) > 5:
            stem = w[:-3]
            tags = {"degree": "SUPER"}
            if self._is_known_stem(stem):
                return stem, tags, "ADJ"

        # Comparative: -er (but only if stem is known or un-umlauted stem is)
        if w.endswith("er") and len(w) > 4:
            stem = w[:-2]
            tags = {"degree": "COMP"}
            if self._is_known_stem(stem) and self._stems_lower.get(stem.lower()) == "ADJ":
                return stem, tags, "ADJ"
            un = self._un_umlaut(stem)
            if un and self._is_known_stem(un) and self._stems_lower.get(un.lower()) == "ADJ":
                tags["umlaut"] = "YES"
                return un, tags, "ADJ"

        return None

    def _try_adjective_declension(self, w: str
                                  ) -> Optional[Tuple[str, Dict[str, str], str]]:
        """Strip adjective declension endings."""
        # Ordered longest-first: -em, -en, -er, -es, -e
        _ADJ_ENDINGS = [
            ("em", {"case": "DAT", "adj_ambig": "YES"}),
            ("en", {"case": "ACC", "adj_ambig": "YES"}),
            ("er", {"case": "NOM", "gender": "MASC", "adj_ambig": "YES"}),
            ("es", {"case": "NOM", "gender": "NEUT", "adj_ambig": "YES"}),
            ("e",  {"case": "NOM", "adj_ambig": "YES"}),
        ]
        for suf, tags in _ADJ_ENDINGS:
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                stem = w[:-len(suf)]
                if self._is_known_stem(stem) and self._stems_lower.get(stem.lower()) == "ADJ":
                    return stem, dict(tags), "ADJ"
                # Try un-umlaut
                un = self._un_umlaut(stem)
                if un and self._is_known_stem(un) and self._stems_lower.get(un.lower()) == "ADJ":
                    t = dict(tags)
                    t["umlaut"] = "YES"
                    return un, t, "ADJ"
        return None

    def _try_noun_declension(self, w: str
                             ) -> Optional[Tuple[str, Dict[str, str], str]]:
        """Strip noun declension: genitive -s/-es, dative -n, plural patterns."""
        # Genitive -es
        if w.endswith("es") and len(w) > 4:
            stem = w[:-2]
            if self._is_known_stem(stem) and self._stems_lower.get(stem.lower()) == "NOUN":
                return stem, {"case": "GEN", "num": "SG"}, "NOUN"

        # Genitive -s
        if w.endswith("s") and len(w) > 4 and not w.endswith("ss"):
            stem = w[:-1]
            if self._is_known_stem(stem) and self._stems_lower.get(stem.lower()) == "NOUN":
                return stem, {"case": "GEN", "num": "SG"}, "NOUN"

        # Dative plural -n (if stem is a known plural or known stem)
        if w.endswith("n") and len(w) > 4:
            stem = w[:-1]
            if self._is_known_stem(stem) and self._stems_lower.get(stem.lower()) == "NOUN":
                return stem, {"case": "DAT", "num": "PL"}, "NOUN"

        # Plural -en
        if w.endswith("en") and len(w) > 4:
            stem = w[:-2]
            if self._is_known_stem(stem) and self._stems_lower.get(stem.lower()) == "NOUN":
                return stem, {"num": "PL"}, "NOUN"

        # Plural -e
        if w.endswith("e") and len(w) > 3:
            stem = w[:-1]
            if self._is_known_stem(stem) and self._stems_lower.get(stem.lower()) == "NOUN":
                return stem, {"num": "PL"}, "NOUN"
            # Try un-umlaut
            un = self._un_umlaut(stem)
            if un and self._is_known_stem(un) and self._stems_lower.get(un.lower()) == "NOUN":
                return un, {"num": "PL", "umlaut": "YES"}, "NOUN"

        # Plural -er
        if w.endswith("er") and len(w) > 4:
            stem = w[:-2]
            if self._is_known_stem(stem) and self._stems_lower.get(stem.lower()) == "NOUN":
                return stem, {"num": "PL"}, "NOUN"
            un = self._un_umlaut(stem)
            if un and self._is_known_stem(un) and self._stems_lower.get(un.lower()) == "NOUN":
                return un, {"num": "PL", "umlaut": "YES"}, "NOUN"

        # Plural -s
        if w.endswith("s") and len(w) > 4:
            stem = w[:-1]
            if self._is_known_stem(stem) and self._stems_lower.get(stem.lower()) == "NOUN":
                return stem, {"num": "PL"}, "NOUN"

        return None

    # ── Step B: Derivational stripping ─────────────────────────────────────

    def _step_b(self, stem: str) -> Tuple[str, List[str]]:
        chain: List[str] = []

        # Try compound splitting first
        parts = self.split_compound(stem)
        if len(parts) > 1:
            head = parts[-1]
            chain.append(f"COMPOUND({'+'.join(parts)})")
            return head, chain

        # Suffix stripping
        w = stem.lower()
        for surface, deriv in self.suffixes:
            if w.endswith(surface) and len(w) - len(surface) >= 3:
                chain.append(f"{surface}\u2192{deriv['derives']}")
                new_stem = w[:-len(surface)]
                # Try un-umlaut for suffixes that trigger it
                if surface in ("chen", "lein", "lich", "e"):
                    un = self._un_umlaut(new_stem)
                    if un and self._is_known_stem(un):
                        return un, chain
                return new_stem, chain

        # Prefix stripping
        for surface, deriv in self.prefixes:
            if w.startswith(surface) and len(w) - len(surface) >= 3:
                chain.append(f"{surface}\u2192{deriv['derives']}")
                return w[len(surface):], chain

        return stem, chain

    # ── Step C: Root extraction ────────────────────────────────────────────

    def _step_c(self, stem: str) -> Tuple[str, List[str]]:
        root = stem
        full_chain: List[str] = []
        for _ in range(4):
            new_root, chain = self._step_b(root)
            full_chain.extend(chain)
            if new_root == root:
                break
            root = new_root
        return root, full_chain

    # ── Main API ───────────────────────────────────────────────────────────

    def analyze(self, word: str) -> TokenInfo:
        stem, tags, pos = self._step_a(word)

        derived_chain: List[str] = []
        root = stem

        if pos == "UNKNOWN":
            root, derived_chain = self._step_c(stem)

            # If compound splitting found parts, update tags
            for entry in derived_chain:
                if entry.startswith("COMPOUND("):
                    inner = entry[9:-1]
                    parts = inner.split("+")
                    tags["compound_parts"] = ",".join(parts)
                    tags["compound_head"] = parts[-1]
                    # Determine POS from head
                    head_pos = self._stems_lower.get(parts[-1].lower())
                    if head_pos:
                        pos = head_pos
                    else:
                        pos = "NOUN"  # compounds are usually nouns
                    break

            # If derivation chain found derivational morphology, infer POS
            # from the derivation direction (e.g., V->N means NOUN).
            if pos == "UNKNOWN" and derived_chain:
                for entry in derived_chain:
                    if "\u2192" in entry:
                        derives_type = entry.split("\u2192")[1]
                        if derives_type in ("ACTION_NOUN", "QUALITY_NOUN",
                                            "RESULT_NOUN", "COLLECTIVE",
                                            "STATE_DOMAIN", "PERSON",
                                            "AGENT", "FEMININE_AGENT",
                                            "DIMINUTIVE", "RESULT",
                                            "QUALITY_ABSTRACT"):
                            pos = "NOUN"
                            break
                        if derives_type in ("RESEMBLANCE", "RELATING_TO",
                                            "HAVING_QUALITY", "ABILITY",
                                            "TENDENCY", "WITHOUT",
                                            "FULL_OF", "RICH_IN",
                                            "LOW_IN", "NEGATION",
                                            "ORIGINAL", "EXCESSIVE"):
                            pos = "ADJ"
                            break
                        if derives_type in ("VERBALIZE",):
                            pos = "VERB"
                            break

            # If still UNKNOWN after step C, check if root is a known stem
            if pos == "UNKNOWN" and self._is_known_stem(root):
                pos = self._stems_lower.get(root.lower(), "UNKNOWN")

        return TokenInfo(
            surface=word, clitics={}, template="",
            root=root, tags=tags, pos=pos, derived_chain=derived_chain,
        )

    def analyze_sentence(self, sentence: str) -> Tuple[List[TokenInfo], bool, str]:
        tokens = [self.analyze(w) for w in sentence.split()]
        word_ok = check_morph_sequence_de(tokens)
        sent_ok, sent_msg = validate_sentence_structure_de(tokens)
        return tokens, word_ok and sent_ok, sent_msg
