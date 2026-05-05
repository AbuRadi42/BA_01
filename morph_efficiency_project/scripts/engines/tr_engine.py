"""
engines/tr_engine.py
--------------------
Turkish morphology engine (Steps A/B/C).

Bug fixes applied:
  1. Two-pass analysis to resolve slot-order ambiguity (case vs mood/additive)
  2. Stem validation to prevent over-stripping (min length, vowel check)
  3. Derivations loaded from tr_derivations.json (slot_order=1)
  4. Consonant mutation (k->g, t->d, p->b, c->c)
  5. Rounding harmony (4-way) in _harmony_ok()
  6. Buffer consonant handling (y, n, s, s)
  7. Closed-class lexicon for function words
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from .shared import (
    TokenInfo,
    check_morph_sequence_tr,
    validate_sentence_structure_tr,
)

# ── Bug #7: Closed-class lexicon ─────────────────────────────────────────────

CLOSED_CLASS: Dict[str, Dict] = {}

def _build_closed_class():
    """Build closed-class word dictionary."""
    postpositions = {
        "için": {"pos": "POSTP", "sem": "PURPOSE"},
        "ile": {"pos": "POSTP", "sem": "COMITATIVE"},
        "gibi": {"pos": "POSTP", "sem": "SIMILATIVE"},
        "kadar": {"pos": "POSTP", "sem": "DEGREE"},
        "göre": {"pos": "POSTP", "sem": "ACCORDING_TO"},
        "doğru": {"pos": "POSTP", "sem": "DIRECTION"},
        "karşı": {"pos": "POSTP", "sem": "AGAINST"},
        "rağmen": {"pos": "POSTP", "sem": "DESPITE"},
        "dolayı": {"pos": "POSTP", "sem": "CAUSE"},
        "beri": {"pos": "POSTP", "sem": "SINCE"},
        "önce": {"pos": "POSTP", "sem": "BEFORE"},
        "sonra": {"pos": "POSTP", "sem": "AFTER"},
        "dışında": {"pos": "POSTP", "sem": "OUTSIDE"},
        "hakkında": {"pos": "POSTP", "sem": "ABOUT"},
        "itibaren": {"pos": "POSTP", "sem": "STARTING_FROM"},
        "boyunca": {"pos": "POSTP", "sem": "THROUGHOUT"},
        "arasında": {"pos": "POSTP", "sem": "BETWEEN"},
        "üzere": {"pos": "POSTP", "sem": "ABOUT_TO"},
    }
    conjunctions = {
        "ve": {"pos": "CONJ", "sem": "AND"},
        "veya": {"pos": "CONJ", "sem": "OR"},
        "ama": {"pos": "CONJ", "sem": "BUT"},
        "fakat": {"pos": "CONJ", "sem": "BUT"},
        "ancak": {"pos": "CONJ", "sem": "HOWEVER"},
        "çünkü": {"pos": "CONJ", "sem": "BECAUSE"},
        "oysa": {"pos": "CONJ", "sem": "WHEREAS"},
        "halbuki": {"pos": "CONJ", "sem": "WHEREAS"},
        "hem": {"pos": "CONJ", "sem": "BOTH"},
        "ise": {"pos": "CONJ", "sem": "AS_FOR"},
        "ki": {"pos": "CONJ", "sem": "THAT"},
    }
    pronouns = {
        "ben": {"pos": "PRON", "person": "1", "num": "SG"},
        "sen": {"pos": "PRON", "person": "2", "num": "SG"},
        "o": {"pos": "PRON", "person": "3", "num": "SG"},
        "biz": {"pos": "PRON", "person": "1", "num": "PL"},
        "siz": {"pos": "PRON", "person": "2", "num": "PL"},
        "onlar": {"pos": "PRON", "person": "3", "num": "PL"},
        "bu": {"pos": "PRON", "sem": "DEMONSTRATIVE"},
        "şu": {"pos": "PRON", "sem": "DEMONSTRATIVE"},
        "bunlar": {"pos": "PRON", "sem": "DEMONSTRATIVE", "num": "PL"},
        "şunlar": {"pos": "PRON", "sem": "DEMONSTRATIVE", "num": "PL"},
        "kendi": {"pos": "PRON", "sem": "REFLEXIVE"},
        "kim": {"pos": "PRON", "sem": "INTERROGATIVE"},
        "hangi": {"pos": "PRON", "sem": "INTERROGATIVE"},
        "her": {"pos": "PRON", "sem": "UNIVERSAL"},
        "bazı": {"pos": "PRON", "sem": "INDEFINITE"},
        "birçok": {"pos": "PRON", "sem": "INDEFINITE"},
        "hiç": {"pos": "PRON", "sem": "NEGATIVE"},
        "hep": {"pos": "PRON", "sem": "UNIVERSAL"},
        "herkes": {"pos": "PRON", "sem": "UNIVERSAL"},
    }
    adverbs = {
        "çok": {"pos": "ADV", "sem": "DEGREE"},
        "az": {"pos": "ADV", "sem": "DEGREE"},
        "daha": {"pos": "ADV", "sem": "COMPARATIVE"},
        "en": {"pos": "ADV", "sem": "SUPERLATIVE"},
        "şimdi": {"pos": "ADV", "sem": "TEMPORAL"},
        "hemen": {"pos": "ADV", "sem": "TEMPORAL"},
        "hâlâ": {"pos": "ADV", "sem": "TEMPORAL"},
        "artık": {"pos": "ADV", "sem": "TEMPORAL"},
        "henüz": {"pos": "ADV", "sem": "TEMPORAL"},
        "bile": {"pos": "ADV", "sem": "ADDITIVE"},
        "sadece": {"pos": "ADV", "sem": "RESTRICTIVE"},
        "yalnız": {"pos": "ADV", "sem": "RESTRICTIVE"},
        "zaten": {"pos": "ADV", "sem": "ALREADY"},
        "belki": {"pos": "ADV", "sem": "EPISTEMIC"},
        "evet": {"pos": "PART", "sem": "AFFIRMATIVE"},
        "hayır": {"pos": "PART", "sem": "NEGATIVE"},
        "tamam": {"pos": "PART", "sem": "AGREEMENT"},
    }
    question_words = {
        "ne": {"pos": "PRON", "sem": "INTERROGATIVE"},
        "nerede": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "nereye": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "nereden": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "nasıl": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "niçin": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "niye": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "neden": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "kaç": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "dahi": {"pos": "ADV", "sem": "ADDITIVE"},
    }
    particles = {
        "da": {"pos": "PART", "sem": "ADDITIVE"},
        "de": {"pos": "PART", "sem": "ADDITIVE"},
        "ya": {"pos": "PART", "sem": "DISCOURSE"},
        "mı": {"pos": "PART", "sem": "QUESTION"},
        "mi": {"pos": "PART", "sem": "QUESTION"},
        "mu": {"pos": "PART", "sem": "QUESTION"},
        "mü": {"pos": "PART", "sem": "QUESTION"},
        "değil": {"pos": "PART", "sem": "NEGATION"},
    }
    all_entries = {}
    for d in [postpositions, conjunctions, pronouns, adverbs, question_words, particles]:
        all_entries.update(d)
    return all_entries

CLOSED_CLASS = _build_closed_class()

# Buffer consonants that are inserted between stem and suffix
_BUFFER_CONSONANTS = set("ynsş")


class TurkishEngine:
    """
    Turkish morphology engine.

    Turkish is an agglutinative SOV language. Words are built by appending
    suffixes to a stem in a strict slot order:
      NOUN: stem + [DERIV] + [NUM] + [POSS] + [CASE] + [COPULA/Q]
      VERB: stem + [DERIV] + [VOICE] + [ABIL] + [NEG] + [TENSE/MOOD] + [PERSON_NUM] + [EPIST/Q]

    Step A -- Suffix stripping with two-pass ambiguity resolution.
              Within each slot, the longest matching suffix wins.
              Buffer-consonant variants (y/n/s) only match after vowel stems.
    Step B -- Derivational suffix detection (from tr_derivations.json).
    Step C -- Stem identification.

    Vowel harmony groups (4-way):
      Back unrounded:  a, i (dotless)
      Back rounded:    o, u
      Front unrounded: e, i
      Front rounded:   o (umlaut), u (umlaut)
    """

    BACK_VOWELS    = set("aıou")
    FRONT_VOWELS   = set("eiöü")
    ALL_VOWELS     = BACK_VOWELS | FRONT_VOWELS
    ROUNDED_VOWELS = set("oöuü")
    UNROUNDED_VOWELS = set("aeıi")
    VOICELESS      = set("çfhkpşst")

    # Consonant mutation mapping: surface (mutated) -> original
    CONSONANT_MUTATION = {"ğ": "k", "g": "k", "d": "t", "b": "p", "c": "ç"}

    # Nominal case slot_order values
    NOMINAL_SLOTS = {2, 3, 4}  # NUM, POSS, CASE

    def __init__(self, config_dir: str = "morph_efficiency_project/configs"):
        with open(os.path.join(config_dir, "tr_suffixes.json"), encoding="utf-8") as f:
            raw = json.load(f)

        # Bug #3: Load derivational suffixes
        deriv_path = os.path.join(config_dir, "tr_derivations.json")
        deriv_entries = []
        if os.path.exists(deriv_path):
            with open(deriv_path, encoding="utf-8") as f:
                deriv_raw = json.load(f)
            for entry in deriv_raw:
                deriv_entries.append({
                    "logical": entry.get("derives", entry.get("suffix", "")),
                    "surface_variants": entry.get("surface_variants", []),
                    "harmony_rule": entry.get("harmony_rule", ""),
                    "slot": "DERIV",
                    "slot_order": 1,
                    "word_class": entry.get("output_pos", "NOUN"),
                    "function": entry.get("function", ""),
                    "dilbilgisi_term": entry.get("dilbilgisi_term", ""),
                    "tags": {"deriv": entry.get("derives", "UNKNOWN")},
                    "example": entry.get("example", ""),
                })

        # Group by slot_order descending (strip outermost slots first)
        self.suffixes_by_slot: Dict[float, List[dict]] = defaultdict(list)
        for entry in raw:
            self.suffixes_by_slot[entry["slot_order"]].append(entry)
        for entry in deriv_entries:
            self.suffixes_by_slot[1].append(entry)

        # Promote PRES_AORIST_NEG (-maz/-mez) to a pre-pass slot (14.5)
        # so it's tried before person/mood slots can consume its parts.
        # Similarly, promote NARR_COND and other compound suffixes that
        # span NEG+TENSE boundaries.
        for entry in raw:
            if entry["logical"] == "PRES_AORIST_NEG":
                self.suffixes_by_slot[14.5].append(entry)

        # Sort slot orders descending (outermost first)
        self.slot_orders = sorted(self.suffixes_by_slot.keys(), reverse=True)

        # Nominal-only slot orders (for pass 2): NUM, POSS, CASE
        self.nominal_slot_orders = sorted(
            [s for s in self.slot_orders if s in self.NOMINAL_SLOTS],
            reverse=True,
        )

    # ── Vowel harmony check (Bug #5: 4-way rounding harmony) ─────────────────

    def _last_vowel(self, stem: str) -> Optional[str]:
        for ch in reversed(stem):
            if ch in self.ALL_VOWELS:
                return ch
        return None

    def _harmony_ok(self, stem: str, suffix: str) -> bool:
        """
        Vowel harmony check: the first vowel of the suffix must agree with
        the last vowel of the stem in backness. For high vowels (i,i,u,u)
        in the suffix, also check rounding harmony.
        """
        lv = self._last_vowel(stem)
        if lv is None:
            return True
        suffix_vowels = [c for c in suffix if c in self.ALL_VOWELS]
        if not suffix_vowels:
            return True
        sv = suffix_vowels[0]
        # Check backness harmony
        stem_back = lv in self.BACK_VOWELS
        suf_back  = sv in self.BACK_VOWELS
        if stem_back != suf_back:
            return False
        # Check rounding harmony for high vowels (i, i, u, u)
        high_vowels = set("ıiuü")
        if sv in high_vowels:
            stem_rounded = lv in self.ROUNDED_VOWELS
            suf_rounded = sv in self.ROUNDED_VOWELS
            if stem_rounded != suf_rounded:
                return False
        return True

    # ── Stem validation (Bug #2: prevent over-stripping) ─────────────────────

    def _stem_plausible(self, stem: str) -> bool:
        """
        Check if a stem is a plausible Turkish word stem.
        Must be at least 2 characters and contain at least one vowel.
        """
        if len(stem) < 2:
            return False
        if not any(c in self.ALL_VOWELS for c in stem):
            return False
        return True

    # ── Buffer consonant check (Bug #6) ──────────────────────────────────────

    # Known buffer-consonant suffix patterns.
    # Key: first char of the suffix. Value: set of slots where this is a buffer.
    # Only these specific slot+char combinations are treated as buffer variants.
    _BUFFER_SLOTS = {
        "y": {4},       # y-buffer in CASE (ACC: -yı, DAT: -ya, INS: -yla)
        "n": {3, 4},    # n-buffer in POSS (araban -> -n after vowel) and GEN (-nın)
        "s": {3},       # s-buffer in POSS_3SG (arabası -> -sı after vowel)
    }

    def _is_buffer_variant(self, suf: str, slot_order: float = 0) -> bool:
        """
        Check if the suffix is a buffer-consonant variant for the given slot.
        """
        if not suf:
            return False
        first = suf[0]
        allowed_slots = self._BUFFER_SLOTS.get(first, set())
        return int(slot_order) in allowed_slots

    def _buffer_ok(self, stem: str, suf: str, slot_order: float = 0) -> bool:
        """
        If suffix is a buffer variant for this slot, check that stem ends
        in a vowel (buffer consonants are inserted after vowels).
        """
        if not suf:
            return True
        if self._is_buffer_variant(suf, slot_order):
            if not stem or stem[-1] not in self.ALL_VOWELS:
                return False
        return True

    # ── Consonant mutation (Bug #4) ──────────────────────────────────────────

    def _try_consonant_unmutation(self, stem: str) -> List[str]:
        """
        If stem ends in a soft consonant that could be from consonant mutation,
        return possible original stem(s). E.g., 'kitab' -> 'kitap'
        """
        candidates = [stem]
        if stem and stem[-1] in self.CONSONANT_MUTATION:
            original_cons = self.CONSONANT_MUTATION[stem[-1]]
            candidates.append(stem[:-1] + original_cons)
        return candidates

    # ── Step A: inflectional suffix stripping ─────────────────────────────────

    # Minimum remaining stem length after stripping, per slot.
    # For ambiguous short suffixes in VOICE/PERSON slots, require longer stems.
    _SLOT_MIN_STEM = {
        5: 3,    # VOICE: -l, -n, -t etc. are very short and ambiguous
        9: 3,    # PERSON_NUM: -m, -z, -n are short
        11: 3,   # COPULA: short suffixes
    }

    def _find_best_match_in_slot(self, stem: str, entries: List[dict], slot_order: float = 0) -> Optional[Tuple[str, dict, int]]:
        """
        Find the best matching suffix within a single slot.

        Strategy: collect all valid matches, then pick the best one.
        Primary: longest suffix wins (longest match = most specific).
        Exception: buffer-consonant variants (y/n/s prefixed) are penalized
        so that the non-buffer version is preferred when it also matches.
        This prevents eating stem-final y/n/s as buffer consonants.

        Buffer consonant variants only match after vowel-final stems.

        Returns (new_stem, entry, suffix_length) or None.
        """
        candidates = []
        for entry in entries:
            for surface in entry["surface_variants"]:
                if surface in ("-∅ (zero)", ""):
                    continue
                suf = surface.lstrip("-").rstrip("-")
                if not suf:
                    continue
                suf_len = len(suf)
                if suf_len >= len(stem):
                    continue
                remaining = stem[:-suf_len]
                if not stem.endswith(suf):
                    continue
                min_stem = self._SLOT_MIN_STEM.get(slot_order, 2)
                if len(remaining) < min_stem:
                    continue
                if not self._stem_plausible(remaining):
                    continue
                if not self._harmony_ok(remaining, suf):
                    continue
                if not self._buffer_ok(remaining, suf, slot_order):
                    continue
                is_buffer = 1 if self._is_buffer_variant(suf, slot_order) else 0
                candidates.append((remaining, entry, suf_len, is_buffer))

        if not candidates:
            return None

        # Sort: longest suffix first, but penalize buffer variants.
        # A buffer variant (suf starts with y/n/s/s) is penalized by 2
        # so that e.g., -yü (len 2, buffer) gets score 0 and loses to
        # -ü (len 1, non-buffer) with score 1.
        # This prevents eating stem-final y/n/s as buffer consonants
        # when the non-buffer variant also produces a valid match.
        candidates.sort(
            key=lambda c: (c[2] - 2 * c[3], c[2]),
            reverse=True,
        )
        best = candidates[0]
        return (best[0], best[1], best[2])

    def _step_a_single_pass(self, word: str, slot_orders: List[float] = None) -> Tuple[str, Dict[str, str]]:
        """
        Strip inflectional suffixes slot by slot (outermost first).
        Within each slot, pick the longest matching suffix.

        Special handling: COP slot (11) is deferred until after TENSE (7).
        If a tense marker was found, COP is skipped (it would be redundant
        and produces wrong results for verbal past forms like gitti).
        If no tense was found, COP is attempted after all other slots.

        Returns (stem, merged_tags).
        """
        stem = word.lower()
        merged_tags: Dict[str, str] = {}
        if slot_orders is None:
            slot_orders = self.slot_orders

        cop_deferred = False
        for slot_order in slot_orders:
            # Defer COP (slot 11) - try it later if no tense found
            if slot_order == 11:
                cop_deferred = True
                continue
            entries = self.suffixes_by_slot[slot_order]
            match = self._find_best_match_in_slot(stem, entries, slot_order)
            if match is not None:
                stem, entry, _ = match
                merged_tags.update(entry["tags"])

        # Now try COP if deferred and no tense was found
        if cop_deferred and "tense" not in merged_tags:
            entries = self.suffixes_by_slot.get(11, [])
            match = self._find_best_match_in_slot(stem, entries, 11)
            if match is not None:
                stem, entry, _ = match
                merged_tags.update(entry["tags"])

        return stem, merged_tags

    def _step_a(self, word: str) -> Tuple[str, Dict[str, str]]:
        """
        Multi-pass suffix stripping to resolve slot-order ambiguity.

        Pass 1: Full slot stripping (outermost first) -- original approach
        Pass 2: Nominal-only slots (NUM=2, POSS=3, CASE=4)

        Selection logic picks the analysis with the best (longest, most
        plausible) stem while respecting morphological consistency.
        """
        stem1, tags1 = self._step_a_single_pass(word)
        stem2, tags2 = self._step_a_single_pass(word, self.nominal_slot_orders)

        p1_ok = self._stem_plausible(stem1)
        p2_ok = self._stem_plausible(stem2)

        # Detect if pass 1 found clear verbal markers
        real_tense = tags1.get("tense") in (
            "PRES_PROG", "PAST_DEF", "PAST_NARR", "PRES_AORIST", "FUT",
        )
        has_sem = "sem" in tags1  # converbs
        has_real_mood = tags1.get("mood") in ("INF", "NECESS", "COND")
        clearly_verbal = real_tense or has_sem or has_real_mood

        if clearly_verbal:
            # Check for false positive: if pass2 (nominal) also found tags
            # and the total suffix consumed by pass1 is LESS than or equal
            # to what pass2 consumed, the verbal match is likely spurious
            # (e.g., evler: -er AORIST vs -ler PL)
            has_nom_p2 = bool({"case", "poss", "num"} & set(tags2.keys()))
            if has_nom_p2 and p2_ok:
                suf_len_1 = len(word.lower()) - len(stem1)
                suf_len_2 = len(word.lower()) - len(stem2)
                # If pass2 consumed more total suffix chars, it's a more
                # complete match and should be preferred
                if suf_len_2 > suf_len_1:
                    return stem2, tags2
                # If equal consumption but pass1 tense suffix is very short
                # (AORIST -r, -er, -ar = 1-2 chars), and pass2 has case/num
                # tags, prefer pass2 as the verbal match is less specific
                if suf_len_2 == suf_len_1 and len(stem2) == len(stem1):
                    if "case" in tags2 or "num" in tags2:
                        return stem2, tags2
            return stem1, tags1

        # Detect if pass 2 found nominal markers
        nominal_tags = {"case", "poss", "num"}
        has_nominal_p2 = bool(nominal_tags & set(tags2.keys()))

        if has_nominal_p2 and p2_ok:
            # Prefer pass 2 if it produces a longer or equal stem
            if len(stem2) >= len(stem1):
                return stem2, tags2
            # Prefer pass 2 if pass 1 stem is implausible
            if not p1_ok:
                return stem2, tags2
            # Prefer pass 2 if pass 1 has ambiguous tags (mood/add/aspect
            # that are probably misidentified case/poss markers)
            conflicting = {"mood", "add", "aspect"}
            if conflicting & set(tags1.keys()):
                return stem2, tags2

        return stem1, tags1

    # ── Step B: derivational suffix detection ────────────────────────────────

    def _step_b(self, stem: str) -> Tuple[str, List[str]]:
        """
        Detect and strip one derivational suffix (slot_order=1 or 10).
        Only strip if the resulting stem is at least 3 chars (conservative).
        Returns (new_stem, chain).
        """
        chain: List[str] = []
        deriv_entries = (
            self.suffixes_by_slot.get(1, [])   # DERIV slot_order=1
            + self.suffixes_by_slot.get(10, []) # NONFINITE slot_order=10
        )
        for entry in sorted(deriv_entries,
                             key=lambda e: max(
                                 (len(s) for s in e["surface_variants"] if s not in ("-∅ (zero)", "")),
                                 default=0),
                             reverse=True):
            for surface in entry["surface_variants"]:
                if surface in ("-∅ (zero)", ""):
                    continue
                suf = surface.lstrip("-").rstrip("-")
                if not suf:
                    continue
                # Be conservative for derivational stripping:
                # - Remaining stem must be >= 3 chars
                # - Suffix must be >= 2 chars (single-char derivational
                #   suffixes like -a/-e are too ambiguous)
                if len(suf) < 2:
                    continue
                remaining_len = len(stem) - len(suf)
                if remaining_len < 3:
                    continue
                remaining = stem[:-len(suf)]
                if (stem.endswith(suf)
                        and any(c in self.ALL_VOWELS for c in remaining)
                        and self._harmony_ok(remaining, suf)):
                    chain.append(f"{suf}->{entry.get('logical', entry.get('tags', {}).get('deriv', 'UNKNOWN'))}")
                    return remaining, chain
        return stem, chain

    # ── Step C: stem ──────────────────────────────────────────────────────────

    def _step_c(self, stem: str) -> str:
        """Return root after stripping up to 3 derivational layers."""
        root = stem
        for _ in range(3):
            new_root, chain = self._step_b(root)
            if new_root == root:
                break
            root = new_root
        return root

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze(self, word: str) -> TokenInfo:
        # Bug #7: Check closed-class lexicon first
        lower = word.lower()
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

        stem, tags = self._step_a(word)

        # Bug #4: Try consonant unmutation, but only if we stripped a
        # vowel-initial case suffix (ACC, DAT, GEN, etc.) which could
        # have triggered consonant softening. E.g., kitab+ı -> kitap.
        case_val = tags.get("case")
        if case_val and case_val in ("ACC", "DAT", "GEN", "LOC", "ABL"):
            candidates = self._try_consonant_unmutation(stem)
            if len(candidates) > 1:
                unmutated = candidates[1]
                if self._stem_plausible(unmutated):
                    stem = unmutated

        _, derived_chain = self._step_b(stem)
        root = self._step_c(stem)
        pos = tags.get("pos", "NOUN" if tags.get("case") else "VERB" if tags.get("tense") else "UNKNOWN")
        clean_tags = {k: v for k, v in tags.items() if k != "pos"}
        return TokenInfo(
            surface=word,
            clitics={},
            template="",
            root=root,
            tags=clean_tags,
            pos=pos,
            derived_chain=derived_chain,
        )

    def analyze_sentence(self, sentence: str) -> Tuple[List[TokenInfo], bool, str]:
        tokens = [self.analyze(w) for w in sentence.split()]
        word_ok = check_morph_sequence_tr(tokens)
        sent_ok, sent_msg = validate_sentence_structure_tr(tokens)
        return tokens, word_ok and sent_ok, sent_msg

# ══════════════════════════════════════════════════════════════════════════════
# PROCESSING PIPELINE
# ══════════════════════════════════════════════════════════════════════════════
