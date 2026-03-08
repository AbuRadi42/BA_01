"""
engines/tr_engine.py
--------------------
Turkish morphology engine (Steps A/B/C).
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

class TurkishEngine:
    """
    Turkish morphology engine.

    Turkish is an agglutinative SOV language. Words are built by appending
    suffixes to a stem in a strict slot order:
      NOUN: stem + [DERIV] + [NUM] + [POSS] + [CASE] + [COPULA/Q]
      VERB: stem + [DERIV] + [VOICE] + [ABIL] + [NEG] + [TENSE/MOOD] + [PERSON_NUM] + [EPIST/Q]

    Step A — Suffix stripping: iterate suffix list (longest-first per slot,
             slot order reversed) stripping one suffix per slot.
             Vowel harmony is checked before accepting a match.
    Step B — Derivational suffix detection: after inflectional stripping,
             check for derivational suffixes (slot=DERIV or NONFINITE).
    Step C — Stem identification: remaining form after all stripping.

    Vowel harmony groups:
      Back unrounded:  a, ı
      Back rounded:    o, u
      Front unrounded: e, i
      Front rounded:   ö, ü
    """

    BACK_VOWELS    = set("aıou")
    FRONT_VOWELS   = set("eiöü")
    ALL_VOWELS     = BACK_VOWELS | FRONT_VOWELS
    VOICELESS      = set("çfhkpşst")

    def __init__(self, config_dir: str = "morph_efficiency_project/configs"):
        with open(os.path.join(config_dir, "tr_suffixes.json"), encoding="utf-8") as f:
            raw = json.load(f)
        # Group by slot_order descending (strip outermost slots first)
        self.suffixes_by_slot: Dict[float, List[dict]] = defaultdict(list)
        for entry in raw:
            self.suffixes_by_slot[entry["slot_order"]].append(entry)
        # Sort slot orders descending (outermost first)
        self.slot_orders = sorted(self.suffixes_by_slot.keys(), reverse=True)

    # ── Vowel harmony check ───────────────────────────────────────────────────

    def _last_vowel(self, stem: str) -> Optional[str]:
        for ch in reversed(stem):
            if ch in self.ALL_VOWELS:
                return ch
        return None

    def _harmony_ok(self, stem: str, suffix: str) -> bool:
        """
        Rough vowel harmony check: the first vowel of the suffix must
        agree with the last vowel of the stem in backness.
        """
        lv = self._last_vowel(stem)
        if lv is None:
            return True  # no vowel in stem → accept
        suffix_vowels = [c for c in suffix if c in self.ALL_VOWELS]
        if not suffix_vowels:
            return True  # zero suffix or consonant-only → accept
        sv = suffix_vowels[0]
        stem_back = lv in self.BACK_VOWELS
        suf_back  = sv in self.BACK_VOWELS
        return stem_back == suf_back

    # ── Step A: inflectional suffix stripping ─────────────────────────────────

    def _step_a(self, word: str) -> Tuple[str, Dict[str, str]]:
        """
        Strip inflectional suffixes slot by slot (outermost first).
        Returns (stem, merged_tags).
        """
        stem = word.lower()
        merged_tags: Dict[str, str] = {}

        for slot_order in self.slot_orders:
            entries = self.suffixes_by_slot[slot_order]
            # Sort entries by surface length descending (longest match first)
            entries_sorted = sorted(
                entries,
                key=lambda e: max((len(s) for s in e["surface_variants"] if s != "-∅ (zero)"), default=0),
                reverse=True,
            )
            for entry in entries_sorted:
                for surface in entry["surface_variants"]:
                    if surface in ("-∅ (zero)", ""):
                        continue
                    # Strip leading dash
                    suf = surface.lstrip("-")
                    if (stem.endswith(suf)
                            and len(stem) - len(suf) >= 2
                            and self._harmony_ok(stem[: -len(suf)], suf)):
                        stem = stem[: -len(suf)]
                        merged_tags.update(entry["tags"])
                        break  # one suffix per slot
                else:
                    continue
                break  # move to next slot

        return stem, merged_tags

    # ── Step B: derivational suffix detection ────────────────────────────────

    def _step_b(self, stem: str) -> Tuple[str, List[str]]:
        """
        Detect and strip one derivational suffix (slot=DERIV or NONFINITE).
        Returns (new_stem, chain).
        """
        chain: List[str] = []
        deriv_entries = (
            self.suffixes_by_slot.get(1, [])   # DERIV slot_order=1
            + self.suffixes_by_slot.get(10, []) # NONFINITE slot_order=10
        )
        for entry in sorted(deriv_entries,
                             key=lambda e: max(
                                 (len(s) for s in e["surface_variants"] if s != "-∅ (zero)"),
                                 default=0),
                             reverse=True):
            for surface in entry["surface_variants"]:
                if surface in ("-∅ (zero)", ""):
                    continue
                suf = surface.lstrip("-")
                if (stem.endswith(suf)
                        and len(stem) - len(suf) >= 2
                        and self._harmony_ok(stem[: -len(suf)], suf)):
                    chain.append(f"{suf}→{entry['logical']}")
                    return stem[: -len(suf)], chain
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
        stem, tags = self._step_a(word)
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

