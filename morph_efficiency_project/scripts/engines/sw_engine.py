"""
engines/sw_engine.py
--------------------
Swahili morphology engine (Steps A/B/C).

Swahili is a Bantu language with a classificatory noun class system that
triggers agreement cascades across the entire clause.  The engine handles:

  1. Closed-class intercept (~95 function words)
  2. Verb template stripping: NEG + SUBJ + TENSE + REL + OBJ + ROOT + EXT + FV
     (stripped in reverse positional order -- outside-in)
  3. Noun class prefix stripping (18 classes, longest-prefix-first)
  4. Adjective agreement prefix stripping
  5. Derivational detection (agent m-, abstract u-, instrument ki-, -ji suffix)
  6. Monosyllabic verb handling (ku- retention)
"""

import json
import os
from typing import Dict, List, Optional, Tuple

from .shared import (
    TokenInfo,
    check_morph_sequence_sw,
    validate_sentence_structure_sw,
)

# ── Closed-class lexicon (~95 entries) ──────────────────────────────────────

CLOSED_CLASS: Dict[str, Dict] = {}


def _build_closed_class() -> Dict[str, Dict]:
    conjunctions = {
        "na": {"pos": "CONJ", "subcat": "CONJ", "gloss": "and/with"},
        "au": {"pos": "CONJ", "subcat": "CONJ", "gloss": "or"},
        "ama": {"pos": "CONJ", "subcat": "CONJ", "gloss": "or_colloquial"},
        "lakini": {"pos": "CONJ", "subcat": "CONJ", "gloss": "but"},
        "bali": {"pos": "CONJ", "subcat": "CONJ", "gloss": "but_rather"},
        "wala": {"pos": "CONJ", "subcat": "CONJ", "gloss": "nor"},
        "ingawa": {"pos": "CONJ", "subcat": "CONJ", "gloss": "although"},
        "ingawaje": {"pos": "CONJ", "subcat": "CONJ", "gloss": "even_though"},
        "ijapokuwa": {"pos": "CONJ", "subcat": "CONJ", "gloss": "even_though"},
        "kama": {"pos": "CONJ", "subcat": "CONJ", "gloss": "if/like"},
        "ili": {"pos": "CONJ", "subcat": "CONJ", "gloss": "so_that"},
        "hata": {"pos": "CONJ", "subcat": "CONJ", "gloss": "even/until"},
        "ila": {"pos": "CONJ", "subcat": "CONJ", "gloss": "except"},
        "halafu": {"pos": "CONJ", "subcat": "CONJ", "gloss": "then"},
        "tena": {"pos": "CONJ", "subcat": "CONJ", "gloss": "again/also"},
        "kwani": {"pos": "CONJ", "subcat": "CONJ", "gloss": "because"},
        "yaani": {"pos": "CONJ", "subcat": "CONJ", "gloss": "meaning"},
        "wala": {"pos": "CONJ", "subcat": "CONJ", "gloss": "nor"},
    }
    prepositions = {
        "kwa": {"pos": "ADP", "subcat": "PREP", "gloss": "with/for/by"},
        "katika": {"pos": "ADP", "subcat": "PREP", "gloss": "in/at/among"},
        "kuhusu": {"pos": "ADP", "subcat": "PREP", "gloss": "about"},
        "bila": {"pos": "ADP", "subcat": "PREP", "gloss": "without"},
        "tangu": {"pos": "ADP", "subcat": "PREP", "gloss": "since"},
        "mpaka": {"pos": "ADP", "subcat": "PREP", "gloss": "until"},
        "kutoka": {"pos": "ADP", "subcat": "PREP", "gloss": "from"},
        "hadi": {"pos": "ADP", "subcat": "PREP", "gloss": "until"},
        "kuelekea": {"pos": "ADP", "subcat": "PREP", "gloss": "toward"},
        "kulingana": {"pos": "ADP", "subcat": "PREP", "gloss": "according_to"},
    }
    question_words = {
        "nani": {"pos": "PRON", "subcat": "INTERROG", "gloss": "who"},
        "nini": {"pos": "PRON", "subcat": "INTERROG", "gloss": "what"},
        "wapi": {"pos": "ADV", "subcat": "INTERROG", "gloss": "where"},
        "lini": {"pos": "ADV", "subcat": "INTERROG", "gloss": "when"},
        "vipi": {"pos": "ADV", "subcat": "INTERROG", "gloss": "how"},
    }
    adverbs = {
        "sana": {"pos": "ADV", "subcat": "ADV", "gloss": "very"},
        "pia": {"pos": "ADV", "subcat": "ADV", "gloss": "also"},
        "tu": {"pos": "ADV", "subcat": "ADV", "gloss": "only"},
        "sasa": {"pos": "ADV", "subcat": "ADV", "gloss": "now"},
        "hapa": {"pos": "ADV", "subcat": "ADV", "gloss": "here"},
        "pale": {"pos": "ADV", "subcat": "ADV", "gloss": "there"},
        "kule": {"pos": "ADV", "subcat": "ADV", "gloss": "over_there"},
        "huko": {"pos": "ADV", "subcat": "ADV", "gloss": "there_cl17"},
        "humu": {"pos": "ADV", "subcat": "ADV", "gloss": "in_here_cl18"},
        "bado": {"pos": "ADV", "subcat": "ADV", "gloss": "still/not_yet"},
        "haraka": {"pos": "ADV", "subcat": "ADV", "gloss": "quickly"},
        "kabisa": {"pos": "ADV", "subcat": "ADV", "gloss": "completely"},
        "labda": {"pos": "ADV", "subcat": "ADV", "gloss": "perhaps"},
        "pengine": {"pos": "ADV", "subcat": "ADV", "gloss": "perhaps"},
        "hasa": {"pos": "ADV", "subcat": "ADV", "gloss": "especially"},
        "mara": {"pos": "ADV", "subcat": "ADV", "gloss": "immediately"},
        "pamoja": {"pos": "ADV", "subcat": "ADV", "gloss": "together"},
        "mbali": {"pos": "ADV", "subcat": "ADV", "gloss": "far"},
        "karibu": {"pos": "ADV", "subcat": "ADV", "gloss": "near/welcome"},
        "hivi": {"pos": "ADV", "subcat": "ADV", "gloss": "like_this"},
        "hivyo": {"pos": "ADV", "subcat": "ADV", "gloss": "like_that"},
    }
    interjections = {
        "lo": {"pos": "PART", "subcat": "INTERJ", "gloss": "oh"},
        "kumbe": {"pos": "PART", "subcat": "INTERJ", "gloss": "so/it_turns_out"},
        "ala": {"pos": "PART", "subcat": "INTERJ", "gloss": "oh_surprise"},
        "basi": {"pos": "PART", "subcat": "INTERJ", "gloss": "well/enough"},
        "haya": {"pos": "PART", "subcat": "INTERJ", "gloss": "okay"},
        "sawa": {"pos": "PART", "subcat": "INTERJ", "gloss": "okay/fine"},
        "pole": {"pos": "PART", "subcat": "INTERJ", "gloss": "sorry"},
        "hodi": {"pos": "PART", "subcat": "INTERJ", "gloss": "may_i_come_in"},
        "starehe": {"pos": "PART", "subcat": "INTERJ", "gloss": "relax"},
        "kwaheri": {"pos": "PART", "subcat": "INTERJ", "gloss": "goodbye"},
        "jambo": {"pos": "PART", "subcat": "INTERJ", "gloss": "hello"},
    }
    copular = {
        "ni": {"pos": "PART", "subcat": "COP", "gloss": "is/am/are"},
        "si": {"pos": "PART", "subcat": "COP", "gloss": "is_not"},
        "ndio": {"pos": "PART", "subcat": "COP", "gloss": "it_is/indeed"},
        "siyo": {"pos": "PART", "subcat": "COP", "gloss": "it_is_not"},
        "hapana": {"pos": "PART", "subcat": "COP", "gloss": "no"},
        "naam": {"pos": "PART", "subcat": "COP", "gloss": "yes_polite"},
    }
    all_entries: Dict[str, Dict] = {}
    for d in [conjunctions, prepositions, question_words, adverbs,
              interjections, copular]:
        all_entries.update(d)
    return all_entries


CLOSED_CLASS = _build_closed_class()

# ── Singular noun classes (for number inference) ────────────────────────────

_SG_CLASSES = {"1", "3", "5", "7", "9", "11", "14"}
_PL_CLASSES = {"2", "4", "6", "8", "10"}
_NO_NUM_CLASSES = {"15", "16", "17", "18"}

# ── Known human stems for Class 1 vs Class 3 disambiguation ────────────────

_HUMAN_STEMS = {
    "tu", "toto", "zee", "gojwa", "geni", "ke", "me",
    "alim", "alimu", "bishi", "chezaji", "fundishi",
    "zazi", "zee", "fumwa", "tawa", "hindi", "zung",
    "zungu", "ganda", "swahili", "temi", "falme",
    "katili", "askari", "daktari", "fundi",
    "anafunzi",  # mwanafunzi = student
}

# ── Monosyllabic verb roots ────────────────────────────────────────────────

_MONOSYLLABIC_ROOTS = {"la", "nywa", "ja", "fa", "enda", "wa", "pa"}

# ── Adjective stems ────────────────────────────────────────────────────────

_ADJ_STEMS = {
    "zuri", "kubwa", "dogo", "refu", "fupi", "pya", "zima", "baya",
    "ingine", "ote", "gumu", "epesi", "embamba", "nene", "eupe",
    "eusi", "ekundu", "chache", "ingi", "zee",
}

# ── Subject prefix table (longest first for matching) ──────────────────────

_SUBJ_PREFIXES = [
    ("ngali", {"mood": "COND", "tense": "PAST"}),
    ("wa", {"person": "3", "num": "PL", "subj_nc": "2"}),
    ("tu", {"person": "1", "num": "PL"}),
    ("ni", {"person": "1", "num": "SG"}),
    ("mu", {"subj_nc": "18"}),
    ("ku", {"subj_nc": "15"}),
    ("pa", {"subj_nc": "16"}),
    ("vi", {"subj_nc": "8"}),
    ("ki", {"subj_nc": "7"}),
    ("zi", {"subj_nc": "10"}),
    ("ya", {"subj_nc": "6"}),
    ("li", {"subj_nc": "5"}),
    ("a", {"person": "3", "num": "SG", "subj_nc": "1"}),
    ("u", {"person": "2", "num": "SG"}),
    ("i", {"subj_nc": "4"}),
    ("m", {"person": "2", "num": "PL"}),
]

# ── Tense marker table (longest first) ────────────────────────────────────

_TENSE_MARKERS = [
    ("ngali", {"mood": "COND", "tense": "PAST"}),
    ("nge", {"mood": "COND"}),
    ("na", {"tense": "PRES", "aspect": "PROG"}),
    ("li", {"tense": "PAST"}),
    ("ta", {"tense": "FUT"}),
    ("me", {"tense": "PERF", "aspect": "RESULT"}),
    ("ki", {"aspect": "SEQ"}),
    ("ka", {"tense": "PAST", "aspect": "NARR"}),
    ("ku", {"tense": "PAST", "polarity": "NEG"}),
    ("si", {"polarity": "NEG", "mood": "SUBJ"}),
]

# ── Extension patterns (longest surface first per extension) ───────────────

_EXTENSIONS = [
    # (suffix_str, name, tags)
    ("ish", "CAUS", {"voice": "CAUS"}),
    ("esh", "CAUS", {"voice": "CAUS"}),
    ("iz", "CAUS", {"voice": "CAUS"}),
    ("ez", "CAUS", {"voice": "CAUS"}),
    ("li", "APPL", {"valence": "APPL"}),
    ("le", "APPL", {"valence": "APPL"}),
    ("an", "RECIP", {"voice": "RECIP"}),
    ("ik", "STAT", {"valence": "STAT"}),
    ("ek", "STAT", {"valence": "STAT"}),
    ("w", "PASS", {"voice": "PASS"}),
    ("i", "APPL", {"valence": "APPL"}),
    ("e", "APPL", {"valence": "APPL"}),
    ("u", "REV", {"valence": "REV"}),
    ("o", "REV", {"valence": "REV"}),
]

# ── Object prefix table (longest first) ───────────────────────────────────

_OBJ_PREFIXES = [
    ("ni", {"obj": "1SG"}),
    ("ku", {"obj": "2SG"}),
    ("tu", {"obj": "1PL"}),
    ("wa", {"obj": "2PL"}),
    ("mw", {"obj": "3SG", "obj_nc": "1"}),
    ("mu", {"obj_nc": "18"}),
    ("vi", {"obj_nc": "8"}),
    ("ki", {"obj_nc": "7"}),
    ("zi", {"obj_nc": "10"}),
    ("ya", {"obj_nc": "6"}),
    ("li", {"obj_nc": "5"}),
    ("pa", {"obj_nc": "16"}),
    ("ji", {"obj": "REFL"}),
    ("m", {"obj": "3SG", "obj_nc": "1"}),
    ("i", {"obj_nc": "9"}),
    ("u", {"obj_nc": "3"}),
]

# ── Relative markers (longest first) ──────────────────────────────────────

_REL_MARKERS = [
    ("cho", {"rel": "YES", "rel_nc": "7"}),
    ("vyo", {"rel": "YES", "rel_nc": "8"}),
    ("ye", {"rel": "YES", "rel_nc": "1"}),
    ("lo", {"rel": "YES", "rel_nc": "5"}),
    ("yo", {"rel": "YES", "rel_nc": "6"}),
    ("zo", {"rel": "YES", "rel_nc": "10"}),
    ("po", {"rel": "YES", "rel_nc": "16"}),
    ("ko", {"rel": "YES", "rel_nc": "17"}),
    ("mo", {"rel": "YES", "rel_nc": "18"}),
    ("o", {"rel": "YES", "rel_nc": "2"}),
]

# ── Noun class prefixes (for stripping) ───────────────────────────────────
# Ordered longest-first within each class to prevent partial matches.
# Each entry: (prefix_str, class_number)

_NOUN_PREFIXES: List[Tuple[str, str]] = [
    ("mw", "1"),  # mw- before vowel for class 1
    ("wa", "2"),
    ("mi", "4"),
    ("my", "4"),  # before vowel
    ("ji", "5"),
    ("ma", "6"),
    ("ki", "7"),
    ("ch", "7"),  # before vowel
    ("vi", "8"),
    ("vy", "8"),  # before vowel
    ("ny", "9"),
    ("mu", "18"),
    ("ku", "15"),
    ("pa", "16"),
    ("n", "9"),
    ("m", "1"),   # m- for class 1 (or 3 -- disambiguated later)
    ("u", "11"),
    ("j", "5"),   # j- before vowel class 5
]

# Prefix mapping for adjective agreement (class -> list of prefixes longest first)
_ADJ_PREFIXES: List[Tuple[str, str]] = [
    ("mw", "1"),
    ("wa", "2"),
    ("mi", "4"),
    ("my", "4"),
    ("ma", "6"),
    ("ki", "7"),
    ("ch", "7"),
    ("vi", "8"),
    ("vy", "8"),
    ("ny", "9"),
    ("mu", "18"),
    ("ku", "15"),
    ("pa", "16"),
    ("n", "9"),
    ("m", "1"),  # also 3, 11
    ("ji", "5"),
    ("j", "5"),
]

# ── Derivation patterns ───────────────────────────────────────────────────

_DERIV_SUFFIXES = [
    ("ji", "AGENT", {"derived": "AGENT", "suffix": "ji"}),
    ("shi", "AGENT", {"derived": "AGENT", "suffix": "shi"}),
]

_DERIV_PREFIXES = [
    ("m", "1", "AGENT", {"derived": "AGENT"}),
    ("u", "14", "ABSTRACT", {"derived": "ABSTRACT"}),
    ("ki", "7", "INSTRUMENT", {"derived": "INSTRUMENT"}),
]


class SwahiliEngine:
    """
    Swahili morphology engine.

    Swahili is a Bantu language whose noun class system (18 classes)
    triggers agreement cascades across verbs, adjectives, possessives,
    and demonstratives.  The verb template is:

        NEG + SUBJ + TENSE + REL + OBJ + ROOT + EXT + FV

    Step A -- Inflectional stripping (verb template reverse order;
              noun class prefix stripping; adjective agreement).
    Step B -- Derivational detection (agent m-, abstract u-,
              instrument ki-, -ji suffix).
    Step C -- Root extraction (iterative, max 2 rounds).
    """

    def __init__(self, config_dir: str = "morph_efficiency_project/configs"):
        # Load noun class table
        cls_path = os.path.join(config_dir, "sw_classes.json")
        with open(cls_path, encoding="utf-8") as f:
            self.class_table: Dict[str, Dict] = json.load(f)

        # Load verb extensions
        ext_path = os.path.join(config_dir, "sw_extensions.json")
        with open(ext_path, encoding="utf-8") as f:
            self.extensions: List[Dict] = json.load(f)

        # Load irregulars / monosyllabic verbs
        irr_path = os.path.join(config_dir, "sw_irregulars.json")
        with open(irr_path, encoding="utf-8") as f:
            self.irregulars: Dict[str, Dict] = json.load(f)

        # Build monosyllabic root set from irregulars
        self.mono_roots = {
            v["root"] for v in self.irregulars.values()
        }

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _strip_prefix(word: str, prefix: str) -> Optional[str]:
        """Strip prefix from word, return remainder or None."""
        if word.startswith(prefix) and len(word) > len(prefix):
            return word[len(prefix):]
        return None

    # ── Verb analysis ────────────────────────────────────────────────────

    def _strip_final_vowel(self, stem: str) -> Tuple[str, Dict[str, str]]:
        """Strip final vowel and tag mood."""
        if not stem:
            return stem, {}
        last = stem[-1]
        if last == "a":
            return stem[:-1], {"mood": "IND"}
        elif last == "e":
            return stem[:-1], {"mood": "SUBJ"}
        elif last == "i":
            return stem[:-1], {"mood": "NEG_PAST"}
        return stem, {}

    def _strip_extensions(self, stem: str) -> Tuple[str, Dict[str, str], List[str]]:
        """
        Strip verb extensions from right-to-left (longest first).
        Returns (remaining_stem, merged_tags, derived_chain).
        Extensions can stack: voice and valence tags are accumulated.
        If multiple extensions share the same tag key (e.g., voice=PASS
        then voice=CAUS), earlier values are preserved with _N suffix.
        """
        tags: Dict[str, str] = {}
        chain: List[str] = []
        stripped_ext_lens: List[int] = []  # track lengths of stripped extensions
        changed = True
        iterations = 0
        while changed and iterations < 5:
            changed = False
            iterations += 1
            for ext_str, ext_name, ext_tags in _EXTENSIONS:
                # Minimum remaining root length after extension stripping:
                # - Multi-char extensions: min 2 chars remaining
                # - Single-char extensions: min 3 chars remaining, and not
                #   allowed after a multi-char extension (avoids saidi+an -> said+i+an)
                # Additional guard: after a single-char vowel extension is stripped,
                # don't allow a multi-char extension that starts with the same char
                # family (e.g., after APPL "i", don't strip STAT "ik")
                min_root = 2
                if len(ext_str) == 1:
                    has_multichar_ext = any(n >= 2 for n in stripped_ext_lens)
                    if has_multichar_ext:
                        continue
                    min_root = 3
                elif chain and stripped_ext_lens and stripped_ext_lens[-1] == 1:
                    # Multi-char extension after single-char: the single-char
                    # extension may have removed the exact suffix this multi-char
                    # would start with (e.g., "i" removed, then "ik" tries to match).
                    # Block STAT after APPL (they occupy the same morphological slot)
                    last_chain_name = chain[-1]
                    if ext_name == "STAT" and last_chain_name == "APPL":
                        continue
                if stem.endswith(ext_str) and len(stem) - len(ext_str) >= min_root:
                    stem = stem[:-len(ext_str)]
                    # Merge extension tags, handling stacking
                    for k, v in ext_tags.items():
                        if k in tags:
                            # Already have this tag; store previous as _N
                            existing = tags[k]
                            # Find next available suffix
                            idx = 2
                            while f"{k}_{idx}" in tags:
                                idx += 1
                            tags[f"{k}_{idx}"] = existing
                        tags[k] = v
                    chain.append(ext_name)
                    stripped_ext_lens.append(len(ext_str))
                    changed = True
                    break  # restart from longest
        return stem, tags, chain

    def _strip_obj_prefix(self, stem: str) -> Tuple[str, Dict[str, str]]:
        """Attempt to strip an object prefix from the start of stem."""
        for prefix, obj_tags in _OBJ_PREFIXES:
            if stem.startswith(prefix) and len(stem) - len(prefix) >= 2:
                # Check for monosyllabic: ku- + mono root
                remainder = stem[len(prefix):]
                if prefix == "ku" and remainder in self.mono_roots:
                    # ku- is part of the monosyllabic root, not an object prefix
                    return stem, {}
                return remainder, dict(obj_tags)
        return stem, {}

    def _strip_rel_marker(self, stem: str) -> Tuple[str, Dict[str, str]]:
        """Attempt to strip a relative marker from the start of stem."""
        for marker, rel_tags in _REL_MARKERS:
            if stem.startswith(marker) and len(stem) - len(marker) >= 2:
                return stem[len(marker):], dict(rel_tags)
        return stem, {}

    def _strip_tense(self, stem: str, has_neg: bool = False) -> Tuple[str, Dict[str, str]]:
        """Strip tense/aspect marker from the start of stem."""
        for marker, tense_tags in _TENSE_MARKERS:
            if marker == "ku" and not has_neg:
                # -ku- as neg past only valid with ha- negation
                continue
            if marker == "si":
                # -si- subjunctive negation handled separately
                continue
            if stem.startswith(marker) and len(stem) - len(marker) >= 1:
                return stem[len(marker):], dict(tense_tags)
        return stem, {}

    def _strip_subj_prefix(self, stem: str) -> Tuple[str, Dict[str, str]]:
        """Strip subject agreement prefix from the start of stem."""
        for prefix, subj_tags in _SUBJ_PREFIXES:
            if stem.startswith(prefix) and len(stem) - len(prefix) >= 1:
                return stem[len(prefix):], dict(subj_tags)
        return stem, {}

    def _try_verb_analysis(self, word: str) -> Optional[TokenInfo]:
        """
        Attempt to analyze word as a verb using the template:
        [NEG] + [SUBJ] + [TENSE] + [REL] + [OBJ] + ROOT + [EXT] + [FV]

        Strip in reverse order (outside-in from right).
        """
        lower = word.lower()
        all_tags: Dict[str, str] = {}
        chain: List[str] = []

        # 1. Must end in a valid final vowel
        if not lower or lower[-1] not in "aei":
            return None

        stem = lower

        # 1. Strip final vowel
        stem, fv_tags = self._strip_final_vowel(stem)
        if not fv_tags:
            return None
        all_tags.update(fv_tags)

        if len(stem) < 2:
            return None

        # NOTE: Extensions are stripped AFTER prefix stripping so that
        # extension patterns don't consume characters that belong to the root.
        # (e.g. "pik" should NOT have "ik" stripped as STAT extension)

        # Now we work on the prefix side of stem:
        # [NEG] + [SUBJ] + [TENSE] + [REL] + [OBJ] + ROOT + [EXT]
        prefix_stem = stem

        # 3. Check for habitual hu- (no subject prefix)
        if prefix_stem.startswith("hu") and len(prefix_stem) >= 3:
            # Habitual: hu- + ROOT + [EXT] (no subject prefix)
            root_candidate = prefix_stem[2:]
            # Check if remainder looks like a root (at least 1 char)
            if len(root_candidate) >= 1:
                # Check for monosyllabic: hu + ku + mono
                fv_char = lower[-1] if lower[-1] in "aei" else ""
                if root_candidate.startswith("ku") and len(root_candidate) > 2 and (
                    root_candidate[2:] in self.mono_roots or
                    root_candidate[2:] + fv_char in self.mono_roots
                ):
                    all_tags["tense"] = "HAB"
                    root = root_candidate[2:]
                    return TokenInfo(
                        surface=word, clitics={}, template="hu-ku-ROOT-EXT-FV",
                        root=root, tags=all_tags, pos="VERB",
                        derived_chain=chain,
                    )
                # Strip extensions from root_candidate
                root_candidate, ext_tags, ext_chain = self._strip_extensions(root_candidate)
                all_tags.update(ext_tags)
                chain.extend(ext_chain)
                # Regular habitual
                all_tags["tense"] = "HAB"
                return TokenInfo(
                    surface=word, clitics={}, template="hu-ROOT-EXT-FV",
                    root=root_candidate, tags=all_tags, pos="VERB",
                    derived_chain=chain,
                )

        # 4. Check for negation prefix
        has_neg = False
        neg_fused_subj: Dict[str, str] = {}

        if prefix_stem.startswith("hawa") and len(prefix_stem) >= 5:
            # ha- + wa- (3PL neg)
            has_neg = True
            prefix_stem = prefix_stem[4:]
            all_tags["polarity"] = "NEG"
            neg_fused_subj = {"person": "3", "num": "PL", "subj_nc": "2"}
        elif prefix_stem.startswith("hatu") and len(prefix_stem) >= 5:
            # ha- + tu- (1PL neg)
            has_neg = True
            prefix_stem = prefix_stem[4:]
            all_tags["polarity"] = "NEG"
            neg_fused_subj = {"person": "1", "num": "PL"}
        elif prefix_stem.startswith("haki") and len(prefix_stem) >= 5:
            # ha- + ki- (cl7 neg)
            has_neg = True
            prefix_stem = prefix_stem[4:]
            all_tags["polarity"] = "NEG"
            neg_fused_subj = {"subj_nc": "7"}
        elif prefix_stem.startswith("havi") and len(prefix_stem) >= 5:
            # ha- + vi- (cl8 neg)
            has_neg = True
            prefix_stem = prefix_stem[4:]
            all_tags["polarity"] = "NEG"
            neg_fused_subj = {"subj_nc": "8"}
        elif prefix_stem.startswith("ha") and len(prefix_stem) >= 3:
            # ha- general negation (ha- + subj)
            has_neg = True
            prefix_stem = prefix_stem[2:]
            all_tags["polarity"] = "NEG"

            # Check for fused ha+a = ha (3SG): after stripping "ha",
            # if next char starts a tense marker, the subject is 3SG
            # (ha- absorbed the a- subject prefix)
        elif prefix_stem.startswith("si") and len(prefix_stem) >= 3:
            # si- = fused 1SG negation (ha- + ni-)
            has_neg = True
            prefix_stem = prefix_stem[2:]
            all_tags["polarity"] = "NEG"
            neg_fused_subj = {"person": "1", "num": "SG"}

        # 5. Strip subject prefix (unless already fused with negation)
        subj_tags: Dict[str, str] = {}
        _pre_subj_len = len(prefix_stem)
        if neg_fused_subj:
            subj_tags = neg_fused_subj
        else:
            prefix_stem, subj_tags = self._strip_subj_prefix(prefix_stem)

        # For ha- negation without fused subject and no subject prefix found,
        # check if the ha- absorbed the 3SG a- prefix (ha + a -> ha)
        if has_neg and not neg_fused_subj and not subj_tags:
            # Assume 3SG (ha- fused with a-)
            subj_tags = {"person": "3", "num": "SG", "subj_nc": "1"}

        if not subj_tags and not has_neg:
            # No subject prefix found and not a negated form -- probably not a verb
            # Exception: very short words that might be imperatives
            if len(lower) <= 3:
                return None
            # Try as imperative (2SG): just ROOT + [EXT] + FV
            # Imperatives have no subject prefix
            if len(stem) >= 2:
                all_tags["mood"] = "IMP"
                all_tags["person"] = "2"
                all_tags["num"] = "SG"
                root = stem
                # Strip extensions from root
                root, ext_tags, ext_chain = self._strip_extensions(root)
                all_tags.update(ext_tags)
                chain.extend(ext_chain)
                # Check monosyllabic
                if root.startswith("ku") and root[2:] in self.mono_roots:
                    root = root[2:]
                return TokenInfo(
                    surface=word, clitics={}, template="ROOT-EXT-FV",
                    root=root, tags=all_tags, pos="VERB",
                    derived_chain=chain,
                )
            return None

        all_tags.update(subj_tags)

        # 6. Strip tense marker
        prefix_stem, tense_tags = self._strip_tense(prefix_stem, has_neg=has_neg)
        all_tags.update(tense_tags)

        # 7. Strip relative marker (optional)
        prefix_stem, rel_tags = self._strip_rel_marker(prefix_stem)
        all_tags.update(rel_tags)

        # 8. Strip object prefix (optional)
        prefix_stem, obj_tags = self._strip_obj_prefix(prefix_stem)
        all_tags.update(obj_tags)

        # What remains is ROOT + [EXT] -- strip extensions now
        root = prefix_stem
        root, ext_tags, ext_chain = self._strip_extensions(root)
        all_tags.update(ext_tags)
        chain.extend(ext_chain)

        # Handle monosyllabic verbs: if root starts with ku and remainder
        # (with final vowel restored) is a mono root
        fv_char = lower[-1] if lower[-1] in "aei" else ""
        if root.startswith("ku") and len(root) > 2:
            remainder = root[2:]
            remainder_with_fv = remainder + fv_char
            if remainder in self.mono_roots:
                root = remainder
            elif remainder_with_fv in self.mono_roots:
                root = remainder_with_fv

        if len(root) < 1:
            return None

        # If no tense/aspect was found, try re-analyzing as imperative.
        # The subject prefix may have been a false match (e.g., "zibua"
        # zi- is not a subject prefix, "andikia" a- is not a subject prefix).
        # Only try this when the matched subject prefix was short (1 char),
        # to avoid misinterpreting multi-char prefixes like "ku", "ki", "wa".
        # Determine the length of the matched subject prefix
        _subj_prefix_len = _pre_subj_len - len(prefix_stem) if subj_tags and not neg_fused_subj else 0
        # Try imperative re-analysis when:
        # - no tense was found (subject prefix may be false match)
        # - for short (1-char) subject prefixes: always try
        # - for longer subject prefixes: only try if root is short (<= 2)
        _try_imp_fallback = (
            not tense_tags and not has_neg and len(lower) >= 4
            and (_subj_prefix_len <= 1 or len(root) <= 2)
        )
        if _try_imp_fallback:
            # Retry as imperative using the full stem
            imp_root = stem
            imp_tags = dict(fv_tags)
            imp_chain: List[str] = []
            imp_root, imp_ext_tags, imp_ext_chain = self._strip_extensions(imp_root)
            imp_tags.update(imp_ext_tags)
            imp_chain.extend(imp_ext_chain)
            # Prefer imperative if it found extensions OR root was too short
            if len(imp_root) >= 2 and (imp_ext_chain or len(root) < 2):
                imp_tags["mood"] = "IMP"
                imp_tags["person"] = "2"
                imp_tags["num"] = "SG"
                return TokenInfo(
                    surface=word, clitics={}, template="ROOT-EXT-FV",
                    root=imp_root, tags=imp_tags, pos="VERB",
                    derived_chain=imp_chain,
                )

        template = "NEG-SUBJ-TENSE-REL-OBJ-ROOT-EXT-FV"
        return TokenInfo(
            surface=word, clitics={}, template=template,
            root=root, tags=all_tags, pos="VERB",
            derived_chain=chain,
        )

    # ── Noun analysis ────────────────────────────────────────────────────

    def _try_noun_core(self, word: str, stem_for_prefix: str,
                       has_loc: bool) -> Optional[TokenInfo]:
        """Core noun analysis on a given stem (with or without -ni stripped)."""
        lower = word.lower()
        tags: Dict[str, str] = {}

        # Try noun class prefix stripping (longest first)
        matched_class = None
        matched_prefix = ""
        root = stem_for_prefix
        for prefix, nc in _NOUN_PREFIXES:
            remainder_len = len(stem_for_prefix) - len(prefix)
            # Allow single-char roots for short nouns (e.g. mti->ti, uzi->zi, jina->na)
            if stem_for_prefix.startswith(prefix) and remainder_len >= 1:
                matched_class = nc
                matched_prefix = prefix
                root = stem_for_prefix[len(prefix):]
                break

        if matched_class is None:
            # Could be a zero-prefix class 5 or class 9/10 noun
            if has_loc and len(stem_for_prefix) >= 3:
                tags["loc"] = "YES"
                tags["nc"] = "9"  # default zero-prefix to class 9
                tags["num"] = "SG"
                return TokenInfo(
                    surface=word, clitics={}, template="ROOT-ni",
                    root=stem_for_prefix, tags=tags, pos="NOUN",
                )
            # No prefix found, not locative -> not clearly a noun
            # Try zero-prefix (class 5 or 9)
            if len(lower) >= 3:
                tags["nc"] = "9"
                tags["num"] = "SG"
                return TokenInfo(
                    surface=word, clitics={}, template="ROOT",
                    root=lower, tags=tags, pos="NOUN",
                )
            return None

        # Disambiguate Class 1 vs Class 3 (both use m-/mw-)
        if matched_class == "1" and matched_prefix in ("m", "mw"):
            if root in _HUMAN_STEMS:
                matched_class = "1"
            else:
                # Default to class 3 (plant/inanimate) for both m- and mw-
                # unless the stem is a known human stem
                matched_class = "3"

        tags["nc"] = matched_class
        if matched_class in _SG_CLASSES:
            tags["num"] = "SG"
        elif matched_class in _PL_CLASSES:
            tags["num"] = "PL"

        if has_loc:
            tags["loc"] = "YES"

        template = "PREFIX-ROOT" + ("-ni" if has_loc else "")
        return TokenInfo(
            surface=word, clitics={}, template=template,
            root=root, tags=tags, pos="NOUN",
        )

    def _try_noun_analysis(self, word: str) -> Optional[TokenInfo]:
        """
        Attempt to analyze word as a noun via class prefix stripping.
        Tries both with and without locative -ni suffix stripping,
        preferring the interpretation with the longer root.
        """
        lower = word.lower()

        # Try without locative first
        result_no_loc = self._try_noun_core(word, lower, has_loc=False)

        # Try with locative -ni if applicable
        result_loc = None
        if lower.endswith("ni") and len(lower) >= 4:
            stem_loc = lower[:-2]
            result_loc = self._try_noun_core(word, stem_loc, has_loc=True)

        # Choose the best interpretation
        if result_loc is not None and result_no_loc is not None:
            # Prefer non-locative if:
            # 1. The non-locative root is a known human stem (e.g. mgeni -> geni)
            # 2. The non-locative interpretation has no prefix (zero-prefix noun)
            #    but the locative does (suggests the word naturally ends in -ni)
            # Prefer locative otherwise (real locative suffix)
            noloc_root = result_no_loc.root
            if noloc_root in _HUMAN_STEMS:
                return result_no_loc
            # If non-loc has a class prefix and root ends with "ni",
            # prefer locative (the -ni is a suffix)
            if "PREFIX" in result_no_loc.template and noloc_root.endswith("ni"):
                return result_loc
            # Default: prefer non-locative for roots that don't end in "ni"
            # (suggests the word naturally ends that way, e.g. mgeni)
            if not noloc_root.endswith("ni"):
                return result_no_loc
            return result_loc
        return result_loc or result_no_loc

    # ── Adjective analysis ───────────────────────────────────────────────

    def _try_adj_analysis(self, word: str) -> Optional[TokenInfo]:
        """
        Attempt to analyze word as an adjective with class agreement prefix.
        """
        lower = word.lower()

        for prefix, nc in _ADJ_PREFIXES:
            if lower.startswith(prefix):
                stem = lower[len(prefix):]
                if stem in _ADJ_STEMS:
                    # Guard: if the stem is a known human noun root,
                    # skip adjective interpretation to avoid false positives
                    # (e.g. "mzee" = elder/noun, not m+zee/adj;
                    #  "wazee" = elders/noun, not wa+zee/adj)
                    if stem in _HUMAN_STEMS:
                        continue
                    tags = {"nc": nc}
                    return TokenInfo(
                        surface=word, clitics={}, template="AGR-ADJ",
                        root=stem, tags=tags, pos="ADJ",
                    )

        # Check bare adjective stem (zero prefix, e.g., class 5/9/10)
        if lower in _ADJ_STEMS:
            return TokenInfo(
                surface=word, clitics={}, template="ADJ",
                root=lower, tags={}, pos="ADJ",
            )

        return None

    # ── Step B: Derivational detection ───────────────────────────────────

    def _step_b(self, token: TokenInfo) -> TokenInfo:
        """
        Detect derivational morphology on nouns.
        Agent m-, abstract u-, instrument ki-, -ji suffix.
        """
        if token.pos != "NOUN":
            return token

        root = token.root
        tags = dict(token.tags)
        chain = list(token.derived_chain)

        # Check for agentive -ji suffix
        for suf, deriv_name, deriv_tags in _DERIV_SUFFIXES:
            if root.endswith(suf) and len(root) - len(suf) >= 2:
                root = root[:-len(suf)]
                tags.update(deriv_tags)
                chain.append(f"-{suf}->{deriv_name}")
                break

        # Check derivational prefix based on noun class
        nc = tags.get("nc", "")
        if nc in ("1", "3") and token.surface.lower().startswith("m"):
            # Agent noun from verb root (m- + verb root)
            tags["derived"] = "AGENT"
            chain.append(f"m->{nc}_AGENT")
        elif nc == "14" and token.surface.lower().startswith("u"):
            tags["derived"] = "ABSTRACT"
            chain.append("u->ABSTRACT")
        elif nc == "7" and token.surface.lower().startswith("ki"):
            tags["derived"] = "INSTRUMENT"
            chain.append("ki->INSTRUMENT")

        return TokenInfo(
            surface=token.surface, clitics=token.clitics,
            template=token.template, root=root, tags=tags,
            pos=token.pos, derived_chain=chain,
        )

    # ── Step C: Iterative root extraction ────────────────────────────────

    def _step_c(self, token: TokenInfo) -> TokenInfo:
        """
        Iterative derivational stripping, max 2 rounds.
        """
        result = token
        for _ in range(2):
            new_result = self._step_b(result)
            if new_result.root == result.root:
                break
            result = new_result
        return result

    # ── Public API ───────────────────────────────────────────────────────

    def analyze(self, word: str) -> TokenInfo:
        """Analyze a single Swahili word."""
        lower = word.lower()

        # 1. Closed-class intercept
        if lower in CLOSED_CLASS:
            entry = CLOSED_CLASS[lower]
            pos = entry.get("pos", "PART")
            tags = {k: v for k, v in entry.items() if k != "pos"}
            return TokenInfo(
                surface=word, clitics={}, template="",
                root=lower, tags=tags, pos=pos,
            )

        # 2. Try adjective analysis first (small closed set, reliable)
        adj_result = self._try_adj_analysis(word)
        if adj_result is not None:
            return adj_result

        # 3. If word ends in -ni, try noun analysis first (locative nouns)
        noun_result = None
        if lower.endswith("ni") and len(lower) >= 5:
            noun_result = self._try_noun_analysis(word)
            if noun_result is not None and noun_result.tags.get("loc") == "YES":
                return self._step_c(noun_result)
            # Reset for later comparison
            noun_result = None

        # 4. Try verb analysis (most morphologically complex)
        verb_result = self._try_verb_analysis(word)

        # 5. Try noun analysis
        noun_result = self._try_noun_analysis(word)

        # 6. Decide between verb and noun
        if verb_result is not None and noun_result is not None:
            # Prefer verb if it found subject+tense markers
            v_tags = verb_result.tags
            has_subj = "person" in v_tags or "subj_nc" in v_tags
            has_tense = "tense" in v_tags or "aspect" in v_tags
            has_mood_only = "mood" in v_tags
            is_habitual = v_tags.get("tense") == "HAB"
            is_imperative = v_tags.get("mood") == "IMP"
            has_polarity = "polarity" in v_tags
            has_voice_ext = "voice" in v_tags or "valence" in v_tags
            # Verb needs a real tense/aspect marker (not just FV mood)
            # to beat a noun interpretation
            # Only count mood markers from the tense slot (COND from nge-/ngali-)
            # not FV-based moods like SUBJ (-e), NEG_PAST (-i), IND (-a)
            has_tense_slot_mood = "mood" in v_tags and v_tags["mood"] in ("COND",)
            # Check if noun has a multi-char class prefix (strong noun signal)
            # A strong prefix is one that's at least 2 chars long, or the noun
            # has an explicit class prefix in its template
            n_template = noun_result.template
            # Determine actual prefix length used for the noun
            noun_prefix_len = 0
            if "PREFIX" in n_template and noun_result.root != lower:
                noun_prefix_len = len(lower) - len(noun_result.root)
                if noun_result.tags.get("loc") == "YES":
                    noun_prefix_len -= 2  # subtract -ni suffix
            noun_has_strong_prefix = "PREFIX" in n_template and noun_prefix_len >= 2
            if has_subj and has_tense:
                return verb_result
            if has_subj and has_tense_slot_mood:
                # COND from nge-/ngali- are real tense-slot markers
                return verb_result
            if is_habitual:
                return verb_result
            if (is_imperative and has_voice_ext and not noun_has_strong_prefix
                    and len(verb_result.root) >= 3):
                return verb_result
            # Imperatives only win over nouns that have NO class prefix
            # (zero-prefix / template=ROOT). If noun has any prefix, prefer noun.
            noun_has_any_prefix = "PREFIX" in n_template
            if is_imperative and not noun_has_any_prefix:
                return verb_result
            if has_polarity and has_subj:
                return verb_result
            # For SUBJ mood (-e) verbs with subject prefix but no tense:
            # prefer verb only if noun doesn't have a strong class prefix
            # AND the verb root is long enough to be plausible (>= 3 chars)
            if (has_subj and v_tags.get("mood") == "SUBJ"
                    and not noun_has_strong_prefix
                    and len(verb_result.root) >= 3):
                return verb_result
            # Prefer noun otherwise (e.g. "ukuta" should be noun class 11,
            # not verb with just subject prefix + FV mood)
            return self._step_c(noun_result)

        if verb_result is not None:
            return verb_result

        if noun_result is not None:
            return self._step_c(noun_result)

        # 7. Fallback: UNKNOWN
        return TokenInfo(
            surface=word, clitics={}, template="",
            root=lower, tags={}, pos="UNKNOWN",
        )

    def analyze_sentence(self, sentence: str) -> Tuple[List[TokenInfo], bool, str]:
        """Analyze a sentence and validate structure."""
        tokens = [self.analyze(w) for w in sentence.split()]
        word_ok = check_morph_sequence_sw(tokens)
        sent_ok, sent_msg = validate_sentence_structure_sw(tokens)
        return tokens, word_ok and sent_ok, sent_msg
