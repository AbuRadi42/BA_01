"""
engines/hu_engine.py
--------------------
Hungarian morphology engine (Steps A/B/C).

Architecture (modeled on the Turkish engine):
  1. Closed-class intercept for ~142 function words
  2. Two-pass analysis resolving nominal/verbal ambiguity
  3. Step A: inflectional suffix stripping (slots 7→6→5→4→3→2)
  4. Step B: derivational suffix/prefix detection
  5. Step C: iterative root extraction (max 3 rounds)

Hungarian-specific features:
  - 18 productive grammatical cases
  - Definite/indefinite verb conjugation (fusional slot 7)
  - Consonant assimilation for instrumental (-val/-vel) and translative (-vá/-vé)
  - Vowel harmony with transparent vowels (i, í) and anti-harmonic stems
  - -lak/-lek (1SG.SUBJ → 2.OBJ) special conjugation
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from .shared import (
    TokenInfo,
    check_morph_sequence_hu,
    validate_sentence_structure_hu,
)

# ── Closed-class lexicon ─────────────────────────────────────────────────────

CLOSED_CLASS: Dict[str, Dict] = {}


def _build_closed_class():
    """Build closed-class word dictionary (~142 entries)."""
    pronouns = {
        "én": {"pos": "PRON", "person": "1", "num": "SG"},
        "te": {"pos": "PRON", "person": "2", "num": "SG"},
        "ő": {"pos": "PRON", "person": "3", "num": "SG"},
        "mi": {"pos": "PRON", "person": "1", "num": "PL"},
        "ti": {"pos": "PRON", "person": "2", "num": "PL"},
        "ők": {"pos": "PRON", "person": "3", "num": "PL"},
        "ez": {"pos": "PRON", "sem": "DEMONSTRATIVE"},
        "az": {"pos": "PRON", "sem": "DEMONSTRATIVE"},
        "ki": {"pos": "PRON", "sem": "INTERROGATIVE"},
        "maga": {"pos": "PRON", "sem": "FORMAL"},
        "ön": {"pos": "PRON", "sem": "FORMAL"},
        "minden": {"pos": "PRON", "sem": "UNIVERSAL"},
        "senki": {"pos": "PRON", "sem": "NEGATIVE"},
        "valaki": {"pos": "PRON", "sem": "INDEFINITE"},
        "néhány": {"pos": "PRON", "sem": "INDEFINITE"},
        "más": {"pos": "PRON", "sem": "OTHER"},
        "egyéb": {"pos": "PRON", "sem": "OTHER"},
        "ilyen": {"pos": "PRON", "sem": "DEMONSTRATIVE"},
        "olyan": {"pos": "PRON", "sem": "DEMONSTRATIVE"},
        "ugyanaz": {"pos": "PRON", "sem": "DEMONSTRATIVE"},
        "mindegyik": {"pos": "PRON", "sem": "UNIVERSAL"},
        "semmi": {"pos": "PRON", "sem": "NEGATIVE"},
    }
    conjunctions = {
        "és": {"pos": "CONJ", "sem": "AND"},
        "vagy": {"pos": "CONJ", "sem": "OR"},
        "de": {"pos": "CONJ", "sem": "BUT"},
        "hanem": {"pos": "CONJ", "sem": "BUT_RATHER"},
        "mert": {"pos": "CONJ", "sem": "BECAUSE"},
        "hogy": {"pos": "CONJ", "sem": "THAT"},
        "ha": {"pos": "CONJ", "sem": "IF"},
        "mint": {"pos": "CONJ", "sem": "THAN"},
        "sem": {"pos": "CONJ", "sem": "NEITHER"},
        "pedig": {"pos": "CONJ", "sem": "HOWEVER"},
        "ugyanis": {"pos": "CONJ", "sem": "NAMELY"},
        "tehát": {"pos": "CONJ", "sem": "THEREFORE"},
        "vagyis": {"pos": "CONJ", "sem": "THAT_IS"},
        "illetve": {"pos": "CONJ", "sem": "RESPECTIVELY"},
        "ám": {"pos": "CONJ", "sem": "BUT"},
        "bár": {"pos": "CONJ", "sem": "ALTHOUGH"},
        "noha": {"pos": "CONJ", "sem": "ALTHOUGH"},
        "holott": {"pos": "CONJ", "sem": "WHEREAS"},
        "amikor": {"pos": "CONJ", "sem": "WHEN"},
        "amíg": {"pos": "CONJ", "sem": "WHILE"},
        "miután": {"pos": "CONJ", "sem": "AFTER"},
        "mielőtt": {"pos": "CONJ", "sem": "BEFORE"},
        "ahogy": {"pos": "CONJ", "sem": "AS"},
        "mivel": {"pos": "CONJ", "sem": "SINCE"},
    }
    question_words = {
        "hol": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "hova": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "honnan": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "mikor": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "hogyan": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "miért": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "melyik": {"pos": "PRON", "sem": "INTERROGATIVE"},
        "mennyi": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "hány": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "milyen": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "merre": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "meddig": {"pos": "ADV", "sem": "INTERROGATIVE"},
    }
    postpositions = {
        "alatt": {"pos": "ADP", "sem": "UNDER"},
        "fölött": {"pos": "ADP", "sem": "ABOVE"},
        "felett": {"pos": "ADP", "sem": "ABOVE"},
        "előtt": {"pos": "ADP", "sem": "BEFORE"},
        "mögött": {"pos": "ADP", "sem": "BEHIND"},
        "mellett": {"pos": "ADP", "sem": "BESIDE"},
        "között": {"pos": "ADP", "sem": "BETWEEN"},
        "körül": {"pos": "ADP", "sem": "AROUND"},
        "helyett": {"pos": "ADP", "sem": "INSTEAD"},
        "nélkül": {"pos": "ADP", "sem": "WITHOUT"},
        "ellen": {"pos": "ADP", "sem": "AGAINST"},
        "felé": {"pos": "ADP", "sem": "TOWARD"},
        "iránt": {"pos": "ADP", "sem": "TOWARD"},
        "szerint": {"pos": "ADP", "sem": "ACCORDING_TO"},
        "számára": {"pos": "ADP", "sem": "FOR"},
        "után": {"pos": "ADP", "sem": "AFTER"},
        "óta": {"pos": "ADP", "sem": "SINCE"},
        "közben": {"pos": "ADP", "sem": "DURING"},
        "végett": {"pos": "ADP", "sem": "FOR_PURPOSE"},
        "révén": {"pos": "ADP", "sem": "BY_MEANS"},
        "folytan": {"pos": "ADP", "sem": "DUE_TO"},
        "gyanánt": {"pos": "ADP", "sem": "AS"},
        "által": {"pos": "ADP", "sem": "BY"},
    }
    particles = {
        "is": {"pos": "PART", "sem": "ALSO"},
        "ne": {"pos": "PART", "sem": "PROHIBITIVE"},
        "nem": {"pos": "PART", "sem": "NEGATION"},
        "se": {"pos": "PART", "sem": "NEITHER"},
        "már": {"pos": "PART", "sem": "ALREADY"},
        "még": {"pos": "PART", "sem": "STILL"},
        "meg": {"pos": "PART", "sem": "PERF"},
        "el": {"pos": "PART", "sem": "AWAY"},
        "fel": {"pos": "PART", "sem": "UP"},
        "föl": {"pos": "PART", "sem": "UP"},
        "le": {"pos": "PART", "sem": "DOWN"},
        "be": {"pos": "PART", "sem": "INTO"},
        "át": {"pos": "PART", "sem": "ACROSS"},
        "vissza": {"pos": "PART", "sem": "BACK"},
        "össze": {"pos": "PART", "sem": "TOGETHER"},
        "szét": {"pos": "PART", "sem": "APART"},
    }
    articles = {
        "a": {"pos": "DET", "sem": "DEF"},
        "az": {"pos": "DET", "sem": "DEF_PREVOCALIC"},
        "egy": {"pos": "DET", "sem": "INDEF"},
    }
    numerals = {
        "kettő": {"pos": "NUM", "sem": "TWO"},
        "három": {"pos": "NUM", "sem": "THREE"},
        "négy": {"pos": "NUM", "sem": "FOUR"},
        "öt": {"pos": "NUM", "sem": "FIVE"},
        "hat": {"pos": "NUM", "sem": "SIX"},
        "hét": {"pos": "NUM", "sem": "SEVEN"},
        "nyolc": {"pos": "NUM", "sem": "EIGHT"},
        "kilenc": {"pos": "NUM", "sem": "NINE"},
        "tíz": {"pos": "NUM", "sem": "TEN"},
        "száz": {"pos": "NUM", "sem": "HUNDRED"},
    }
    adverbs_misc = {
        "itt": {"pos": "ADV", "sem": "HERE"},
        "ott": {"pos": "ADV", "sem": "THERE"},
        "ide": {"pos": "ADV", "sem": "HITHER"},
        "oda": {"pos": "ADV", "sem": "THITHER"},
        "innen": {"pos": "ADV", "sem": "HENCE"},
        "onnan": {"pos": "ADV", "sem": "THENCE"},
        "így": {"pos": "ADV", "sem": "THUS"},
        "úgy": {"pos": "ADV", "sem": "THAT_WAY"},
        "igen": {"pos": "PART", "sem": "YES"},
        "nagyon": {"pos": "ADV", "sem": "VERY"},
        "túl": {"pos": "ADV", "sem": "TOO_MUCH"},
        "elég": {"pos": "ADV", "sem": "ENOUGH"},
        "csak": {"pos": "ADV", "sem": "ONLY"},
        "alig": {"pos": "ADV", "sem": "BARELY"},
        "szinte": {"pos": "ADV", "sem": "ALMOST"},
        "csaknem": {"pos": "ADV", "sem": "ALMOST"},
        "majdnem": {"pos": "ADV", "sem": "ALMOST"},
        "legfeljebb": {"pos": "ADV", "sem": "AT_MOST"},
        "legalább": {"pos": "ADV", "sem": "AT_LEAST"},
        "inkább": {"pos": "ADV", "sem": "RATHER"},
        "sőt": {"pos": "ADV", "sem": "MOREOVER"},
        "mégsem": {"pos": "ADV", "sem": "NEVERTHELESS"},
        "mégis": {"pos": "ADV", "sem": "STILL"},
        "különben": {"pos": "ADV", "sem": "OTHERWISE"},
        "mindig": {"pos": "ADV", "sem": "ALWAYS"},
        "soha": {"pos": "ADV", "sem": "NEVER"},
        "most": {"pos": "ADV", "sem": "NOW"},
        "azonnal": {"pos": "ADV", "sem": "IMMEDIATELY"},
        "rögtön": {"pos": "ADV", "sem": "IMMEDIATELY"},
        "hamar": {"pos": "ADV", "sem": "SOON"},
        "lassan": {"pos": "ADV", "sem": "SLOWLY"},
        "talán": {"pos": "ADV", "sem": "PERHAPS"},
    }
    all_entries = {}
    for d in [pronouns, conjunctions, question_words, postpositions,
              particles, articles, numerals, adverbs_misc]:
        all_entries.update(d)
    return all_entries


CLOSED_CLASS = _build_closed_class()

# ── Hungarian vowel inventory ────────────────────────────────────────────────

BACK_VOWELS = set("aáoóuú")
FRONT_UNROUNDED = set("eéií")
FRONT_ROUNDED = set("öőüű")
FRONT_VOWELS = FRONT_UNROUNDED | FRONT_ROUNDED
ALL_VOWELS = BACK_VOWELS | FRONT_VOWELS
# Transparent vowels: don't determine harmony, let back vowels "show through"
TRANSPARENT_VOWELS = set("ií")


class HungarianEngine:
    """
    Hungarian morphology engine.

    Hungarian is an agglutinative-fusional hybrid. Words are built by appending
    suffixes to a stem in a slot order:
      NOUN: stem + [DERIV] + [NUM] + [POSS] + [CASE]
      VERB: stem + [DERIV] + [TENSE] + [MOOD] + [PERSON+NUM+DEF]

    Step A -- Suffix stripping with two-pass ambiguity resolution.
    Step B -- Derivational suffix/prefix detection.
    Step C -- Iterative root extraction (max 3 rounds).

    Vowel harmony (3-way):
      Back:            a, á, o, ó, u, ú
      Front unrounded: e, é, i, í
      Front rounded:   ö, ő, ü, ű
    """

    # Nominal slot orders (for pass 2): NUM, POSS, CASE
    NOMINAL_SLOTS = {2, 3, 4}

    # Per-slot minimum stem lengths.
    # These prevent over-stripping of short, ambiguous suffixes.
    _SLOT_MIN_STEM = {
        3: 3,   # POSS: single-char suffixes -m, -d, -a
        5: 3,   # TENSE: -t is very short and ambiguous with stem-final t
        7: 3,   # PERSON_DEF: single-char suffixes -m, -d, -k
    }

    def __init__(self, config_dir: str = "morph_efficiency_project/configs"):
        # Load inflectional suffixes
        with open(os.path.join(config_dir, "hu_suffixes.json"),
                  encoding="utf-8") as f:
            raw = json.load(f)

        # Load irregulars
        irreg_path = os.path.join(config_dir, "hu_irregulars.json")
        self.irregulars = {}
        if os.path.exists(irreg_path):
            with open(irreg_path, encoding="utf-8") as f:
                self.irregulars = json.load(f)

        # Build irregular surface form lookup
        self.irregular_surface: Dict[str, dict] = {}
        for surface, info in self.irregulars.get(
                "irregular_surface_forms", {}).items():
            self.irregular_surface[surface.lower()] = info

        # Load derivations
        deriv_path = os.path.join(config_dir, "hu_derivations.json")
        self.derivation_suffixes: List[dict] = []
        self.derivation_prefixes: List[dict] = []
        if os.path.exists(deriv_path):
            with open(deriv_path, encoding="utf-8") as f:
                deriv_raw = json.load(f)
            for entry in deriv_raw:
                if "prefix" in entry:
                    self.derivation_prefixes.append(entry)
                else:
                    self.derivation_suffixes.append(entry)

        # Group inflectional suffixes by slot_order (descending = outermost first)
        self.suffixes_by_slot: Dict[int, List[dict]] = defaultdict(list)
        for entry in raw:
            self.suffixes_by_slot[entry["slot_order"]].append(entry)

        # All slot orders descending
        self.slot_orders = sorted(self.suffixes_by_slot.keys(), reverse=True)

        # Nominal-only slot orders (pass 2): CASE=4, POSS=3, NUM=2
        self.nominal_slot_orders = sorted(
            [s for s in self.slot_orders if s in self.NOMINAL_SLOTS],
            reverse=True,
        )

        # Verbal-only slot orders (pass 1): INF=8, PERSON_DEF=7, MOOD=6, TENSE=5
        self.verbal_slot_orders = sorted(
            [s for s in self.slot_orders if s in {5, 6, 7, 8}],
            reverse=True,
        )

    # ── Vowel harmony ────────────────────────────────────────────────────────

    @staticmethod
    def _classify_vowel(v: str) -> str:
        """Classify a vowel as BACK, FRONT_UNROUND, or FRONT_ROUND."""
        if v in BACK_VOWELS:
            return "BACK"
        if v in FRONT_ROUNDED:
            return "FRONT_ROUND"
        if v in FRONT_UNROUNDED:
            return "FRONT_UNROUND"
        return "UNKNOWN"

    @staticmethod
    def _get_last_harmonic_vowel(stem: str) -> Optional[str]:
        """
        Get the last vowel that determines harmony, skipping transparent
        vowels (i, í) unless they are the only vowels in the stem.
        Returns None if all vowels are transparent (harmony is indeterminate).
        """
        last_transparent = None
        for ch in reversed(stem):
            if ch in ALL_VOWELS:
                if ch not in TRANSPARENT_VOWELS:
                    return ch
                if last_transparent is None:
                    last_transparent = ch
        # All vowels were transparent -- harmony is indeterminate.
        # Return None so harmony check passes trivially. This handles
        # stems like 'ír', 'víz', 'szín' which take either back or
        # front suffixes depending on lexical class.
        return None

    @staticmethod
    def _get_first_vowel(s: str) -> Optional[str]:
        for ch in s:
            if ch in ALL_VOWELS:
                return ch
        return None

    # Suffixes whose harmony_rule is "invariant" -- no harmony check needed.
    # These are identified by having only one surface variant (no back/front
    # alternation) or by containing only transparent/neutral vowels.
    _INVARIANT_SUFFIXES = {
        "ért", "ig", "ként", "nként", "onként", "enként", "önként",
        "ni", "i", "beli", "nyi", "szerű", "féle", "ista", "izmus",
    }

    # Slots where harmony check is skipped because the surface form already
    # encodes the correct harmony variant (compound tense+person suffixes).
    _HARMONY_SKIP_SLOTS = {7}

    def _harmony_ok(self, stem: str, suffix: str,
                    slot_order: int = 0) -> bool:
        """
        Check vowel harmony between stem and suffix.
        For 2-way suffixes: back vs front.
        For 3-way suffixes: also checks rounding.

        Skips the check for:
        - Invariant suffixes (no harmony alternation)
        - Slot 7 compound suffixes (harmony already encoded in surface form)
        """
        # Skip harmony for slot 7 compound suffixes -- the surface form
        # already selects the correct harmony variant
        if slot_order in self._HARMONY_SKIP_SLOTS:
            return True

        # Skip harmony for known invariant suffixes
        if suffix in self._INVARIANT_SUFFIXES:
            return True

        stem_v = self._get_last_harmonic_vowel(stem)
        if stem_v is None:
            return True
        suf_v = self._get_first_vowel(suffix)
        if suf_v is None:
            return True

        stem_class = self._classify_vowel(stem_v)
        suf_class = self._classify_vowel(suf_v)

        if stem_class == suf_class:
            return True

        # For 2-way: both FRONT_UNROUND and FRONT_ROUND count as FRONT
        if stem_class in ("FRONT_UNROUND", "FRONT_ROUND") and \
           suf_class in ("FRONT_UNROUND", "FRONT_ROUND"):
            return True

        return False

    # ── Stem validation ──────────────────────────────────────────────────────

    @staticmethod
    def _stem_plausible(stem: str) -> bool:
        """Stem must be >= 2 chars and contain at least one vowel."""
        if len(stem) < 2:
            return False
        return any(c in ALL_VOWELS for c in stem)

    # ── Consonant assimilation for INS/TRANSL ────────────────────────────────

    @staticmethod
    def _check_assimilation(stem: str, case_type: str) -> Optional[str]:
        """
        For instrumental (-val/-vel) and translative (-vá/-vé), the v-
        assimilates to the stem-final consonant, producing a doubled
        consonant. This method checks if the stem ends in doubled
        consonants and, if so, returns the de-duplicated stem.

        E.g., stem='haz' from surface 'házzal' after stripping -al:
              stem ends in 'zz'? No -- handled differently.

        The actual logic: after stripping the suffix remainder (-al/-el
        or -á/-é), check if the last two chars of the remaining form
        are identical consonants. If so, de-duplicate.
        """
        if len(stem) >= 3 and stem[-1] == stem[-2] and stem[-1] not in ALL_VOWELS:
            return stem[:-1]
        return None

    # ── Step A: inflectional suffix stripping ────────────────────────────────

    def _find_best_match_in_slot(
        self, stem: str, entries: List[dict], slot_order: int = 0
    ) -> Optional[Tuple[str, dict, int]]:
        """
        Find the best matching suffix within a single slot.
        Strategy: longest valid suffix wins.
        Returns (new_stem, entry, suffix_length) or None.
        """
        candidates = []
        for entry in entries:
            for surface in entry["surface_variants"]:
                if surface in ("-∅ (zero)", ""):
                    continue
                suf = surface.lstrip("-")
                if not suf:
                    continue
                suf_len = len(suf)
                if suf_len >= len(stem):
                    continue
                if not stem.endswith(suf):
                    continue
                remaining = stem[:-suf_len]
                # For slot 7 (PERSON_DEF), the elevated minimum of 3 only
                # applies to single-char suffixes (-m, -d, -k etc.) which
                # are highly ambiguous. For multi-char suffixes (>= 2 chars
                # like -tam, -lak), the default minimum of 2 is safe.
                default_min = self._SLOT_MIN_STEM.get(slot_order, 2)
                min_stem = default_min if suf_len < 2 else min(default_min, 2)
                if len(remaining) < min_stem:
                    continue
                if not self._stem_plausible(remaining):
                    continue
                if not self._harmony_ok(remaining, suf, slot_order):
                    continue
                candidates.append((remaining, entry, suf_len))

        if not candidates:
            return None

        # Scoring: longest suffix wins. Among equal-length matches,
        # prefer the one that consumed more of the word (shorter stem).
        # The only exception: a suffix that leaves a 2-char stem should
        # NOT beat a shorter suffix leaving a 3+ char stem when the
        # suffix length difference is very large (5+ vs 3) -- this
        # prevents -talak (5) from beating -lak (3) when the stem
        # difference is 2 vs 3 chars.
        candidates.sort(key=lambda c: c[2], reverse=True)
        return candidates[0]

    def _try_assimilation_match(
        self, stem: str, slot_entries: List[dict]
    ) -> Optional[Tuple[str, dict, int]]:
        """
        Try to match instrumental (-val/-vel) or translative (-vá/-vé)
        with consonant assimilation.

        Pattern: stem ends in CC + al/el/á/é where C is a consonant
        and the doubled C is the assimilated v.
        """
        # INS: -val → -Xal/-Xel where X = stem-final consonant
        # TRANSL: -vá → -Xá/-Xé
        ins_entries = [e for e in slot_entries if e["tags"].get("case") == "INS"]
        transl_entries = [e for e in slot_entries
                         if e["tags"].get("case") == "TRANSL"]

        best = None
        for suffixes, entries in [
            (["al", "el"], ins_entries),
            (["á", "é"], transl_entries),
        ]:
            if not entries:
                continue
            for suf_end in suffixes:
                suf_len = len(suf_end)
                if suf_len >= len(stem):
                    continue
                if not stem.endswith(suf_end):
                    continue
                before = stem[:-suf_len]
                # Check doubled consonant
                if len(before) >= 2 and before[-1] == before[-2] \
                        and before[-1] not in ALL_VOWELS:
                    restored = before[:-1]
                    if self._stem_plausible(restored):
                        total_consumed = suf_len + 1  # +1 for the doubled char
                        entry = entries[0]
                        if best is None or total_consumed > best[2]:
                            best = (restored, entry, total_consumed)

        return best

    def _step_a_single_pass(
        self, word: str, slot_orders: List[int] = None
    ) -> Tuple[str, Dict[str, str]]:
        """
        Strip inflectional suffixes slot by slot (outermost first).
        Returns (stem, merged_tags).
        """
        stem = word.lower()
        merged_tags: Dict[str, str] = {}
        if slot_orders is None:
            slot_orders = self.slot_orders

        for slot_order in slot_orders:
            entries = self.suffixes_by_slot.get(slot_order, [])
            if not entries:
                continue

            match = self._find_best_match_in_slot(stem, entries, slot_order)

            # For CASE slot, also try assimilation
            if slot_order == 4:
                assim_match = self._try_assimilation_match(stem, entries)
                if assim_match is not None:
                    if match is None or assim_match[2] > match[2]:
                        match = assim_match

            if match is not None:
                stem, entry, _ = match
                merged_tags.update(entry["tags"])

        return stem, merged_tags

    def _step_a(self, word: str) -> Tuple[str, Dict[str, str]]:
        """
        Multi-pass suffix stripping.
        Pass 1: Verbal-only slots (PERSON_DEF=7, MOOD=6, TENSE=5)
        Pass 2: Nominal-only slots (CASE=4, POSS=3, NUM=2)
        Selection: pick the analysis with best coverage.
        """
        stem1, tags1 = self._step_a_single_pass(word, self.verbal_slot_orders)
        stem2, tags2 = self._step_a_single_pass(word, self.nominal_slot_orders)

        p1_ok = self._stem_plausible(stem1)
        p2_ok = self._stem_plausible(stem2)

        # Suffix material consumed
        wl = word.lower()
        suf_len_1 = len(wl) - len(stem1)
        suf_len_2 = len(wl) - len(stem2)

        # Check if pass 1 found clear verbal markers.
        # "Clearly verbal" means the analysis found unambiguous verbal morphology
        # that cannot be a nominal suffix: past tense, conditional, subjunctive,
        # infinitive, DEF conjugation, or 2OBJ. Present-tense INDEF person
        # markers (-ok, -unk, -tok, -nak etc.) overlap with nominal suffixes
        # (PL, POSS, DAT) and are NOT considered clearly verbal.
        has_verbal_tense = tags1.get("tense") in ("PAST", "COND")
        has_verbal_mood = tags1.get("mood") in ("SUBJ", "INF")
        has_def_explicit = tags1.get("def") in ("DEF", "2OBJ")
        has_person = "person" in tags1
        clearly_verbal = has_verbal_tense or has_verbal_mood or has_def_explicit

        # Check if pass 2 found nominal markers
        nominal_tags = {"case", "poss", "num"}
        has_nominal_p2 = bool(nominal_tags & set(tags2.keys()))

        # If pass 1 found clear verbal markers and is plausible
        if clearly_verbal and p1_ok:
            # But if pass 2 consumed equal or more suffix material with
            # nominal analysis, prefer nominal. This handles suffix
            # overlap like -nál/-nél (ADESS case vs COND_INDEF_2SG).
            if has_nominal_p2 and p2_ok and suf_len_2 >= suf_len_1:
                # Exception: if pass 1 found a compound suffix (tense+person
                # encoded together, e.g. -tam, -tad, -tuk etc.) and consumed
                # strictly more than pass 2, prefer verbal.
                if suf_len_1 > suf_len_2:
                    return stem1, tags1
                return stem2, tags2
            return stem1, tags1

        # If pass 2 found nominal markers and is plausible
        if has_nominal_p2 and p2_ok:
            # Prefer nominal when:
            # - pass 2 stem >= pass 1 stem (consumed at least as much)
            # - pass 1 stem implausible
            # - pass 1 only found ambiguous present-tense person markers
            #   (which overlap with nominal suffixes)
            if len(stem2) >= len(stem1):
                return stem2, tags2
            if not p1_ok:
                return stem2, tags2
            # If pass 1 has only present-tense person (no PAST/COND/SUBJ),
            # prefer nominal since those suffixes overlap heavily with
            # possessive and plural markers
            if not clearly_verbal:
                return stem2, tags2

        # If pass 1 found anything meaningful, use it
        if p1_ok and tags1:
            return stem1, tags1

        # If pass 2 found anything, use it
        if p2_ok and tags2:
            return stem2, tags2

        return stem1, tags1

    # ── Step B: derivational detection ───────────────────────────────────────

    def _step_b(self, stem: str) -> Tuple[str, List[str]]:
        """
        Detect and strip one derivational suffix or prefix.
        Returns (new_stem, chain).
        """
        chain: List[str] = []

        # Try suffixes first (longest first)
        sorted_derivs = sorted(
            self.derivation_suffixes,
            key=lambda e: max(
                (len(s.lstrip("-")) for s in e.get("surface_variants", [])
                 if s not in ("-∅ (zero)", "")),
                default=0),
            reverse=True,
        )
        for entry in sorted_derivs:
            for surface in entry.get("surface_variants", []):
                if surface in ("-∅ (zero)", ""):
                    continue
                suf = surface.lstrip("-")
                if not suf:
                    continue
                # Derivational suffix stripping constraints:
                # - Long suffixes (>= 3 chars): remaining >= 2 (low risk)
                # - Medium suffixes (2 chars like -ás, -és, -ít, -ul, -at):
                #   remaining >= 2 (productive and specific enough)
                # - Short suffixes (1 char like -i, -s, -ó, -ő, -ú, -ű):
                #   remaining >= 3 (high ambiguity risk)
                if len(suf) >= 2:
                    min_rem = 2
                else:
                    min_rem = 3  # single-char derivational suffixes
                if len(stem) - len(suf) < min_rem:
                    continue
                remaining = stem[:-len(suf)]
                if stem.endswith(suf) \
                        and any(c in ALL_VOWELS for c in remaining) \
                        and self._harmony_ok(remaining, suf):
                    label = entry.get("derives", "UNKNOWN")
                    chain.append(f"{suf}->{label}")
                    return remaining, chain

        # Try prefixes
        sorted_prefixes = sorted(
            self.derivation_prefixes,
            key=lambda e: max(
                (len(s) for s in e.get("surface_variants", [])),
                default=0),
            reverse=True,
        )
        for entry in sorted_prefixes:
            for surface in entry.get("surface_variants", []):
                pfx = surface.lower()
                if not pfx:
                    continue
                if len(pfx) < 2:
                    continue
                if stem.startswith(pfx):
                    remaining = stem[len(pfx):]
                    # Prefixes >= 3 chars are highly specific; allow stem >= 2.
                    # Prefixes of 2 chars (el, ki, be, le, át, rá) are common
                    # and also allow stem >= 2 since they are well-defined.
                    min_rem = 2
                    if len(remaining) >= min_rem and \
                            any(c in ALL_VOWELS for c in remaining):
                        label = entry.get("derives", "UNKNOWN")
                        chain.append(f"{pfx}->{label}")
                        return remaining, chain

        return stem, chain

    # ── Step C: iterative root extraction ────────────────────────────────────

    def _step_c(self, stem: str) -> Tuple[str, List[str]]:
        """Strip up to 3 derivational layers."""
        root = stem
        all_chain: List[str] = []
        for _ in range(3):
            new_root, chain = self._step_b(root)
            if new_root == root:
                break
            all_chain.extend(chain)
            root = new_root
        return root, all_chain

    # ── POS inference ────────────────────────────────────────────────────────

    @staticmethod
    def _infer_pos(tags: Dict[str, str]) -> str:
        if "case" in tags:
            return "NOUN"
        if "poss" in tags:
            return "NOUN"
        if "def" in tags or tags.get("mood") in ("SUBJ", "INF"):
            return "VERB"
        if tags.get("tense") in ("PAST", "COND"):
            return "VERB"
        if "person" in tags:
            return "VERB"
        if "degree" in tags:
            return "ADJ"
        if "num" in tags:
            return "NOUN"
        return "UNKNOWN"

    # ── Public API ───────────────────────────────────────────────────────────

    def analyze(self, word: str) -> TokenInfo:
        lower = word.lower()

        # 1. Check irregular surface forms first
        if lower in self.irregular_surface:
            info = self.irregular_surface[lower]
            return TokenInfo(
                surface=word,
                clitics={},
                template="",
                root=info["root"],
                tags=dict(info.get("tags", {})),
                pos=info.get("pos", "UNKNOWN"),
                derived_chain=[],
            )

        # 2. Check closed-class lexicon
        if lower in CLOSED_CLASS:
            entry = CLOSED_CLASS[lower]
            pos = entry.get("pos", "PART")
            tags = {k: v for k, v in entry.items() if k != "pos"}
            return TokenInfo(
                surface=word,
                clitics={},
                template="",
                root=lower,
                tags=tags,
                pos=pos,
                derived_chain=[],
            )

        # 3. Step A: inflectional stripping
        stem, tags = self._step_a(word)

        # 4. Steps B+C: derivational stripping
        root, derived_chain = self._step_c(stem)

        # 5. POS inference
        pos = self._infer_pos(tags)

        return TokenInfo(
            surface=word,
            clitics={},
            template="",
            root=root,
            tags=tags,
            pos=pos,
            derived_chain=derived_chain,
        )

    def analyze_sentence(self, sentence: str) -> Tuple[List[TokenInfo], bool, str]:
        tokens = [self.analyze(w) for w in sentence.split()]
        word_ok = check_morph_sequence_hu(tokens)
        sent_ok, sent_msg = validate_sentence_structure_hu(tokens)
        return tokens, word_ok and sent_ok, sent_msg


# ══════════════════════════════════════════════════════════════════════════════
# PROCESSING PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def process_text(text: str, engine: HungarianEngine = None) -> List[TokenInfo]:
    """Convenience function to analyze a full text."""
    if engine is None:
        engine = HungarianEngine()
    tokens = []
    for sentence in text.split("."):
        sentence = sentence.strip()
        if not sentence:
            continue
        for word in sentence.split():
            tokens.append(engine.analyze(word))
    return tokens
