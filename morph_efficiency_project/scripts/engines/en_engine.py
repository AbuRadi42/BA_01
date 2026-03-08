"""
engines/en_engine.py
--------------------
English morphology engine (Steps A/B/C).
"""

import json
import os
from typing import Dict, List, Tuple

from .shared import (
    TokenInfo,
    check_morph_sequence_en,
    validate_sentence_structure_en,
)


class EnglishEngine:
    """
    English morphology engine.

    Step A — Inflectional stripping: plural -s/-es, 3SG -s, past -ed,
             progressive -ing, comparative -er, superlative -est,
             possessive 's. Irregular forms resolved via en_irregulars.json.
    Step B — Derivational pattern detection via en_derivations.json.
             Strips known suffixes/prefixes and records the derivation chain.
    Step C — Stem identification: after stripping, the remaining form is
             the stem/root.
    """

    VOWELS = set("aeiou")

    def __init__(self, config_dir: str = "morph_efficiency_project/configs"):
        with open(os.path.join(config_dir, "en_irregulars.json"), encoding="utf-8") as f:
            self.irregulars: Dict[str, dict] = json.load(f)
        with open(os.path.join(config_dir, "en_derivations.json"), encoding="utf-8") as f:
            raw_derivs = json.load(f)
        self.suffixes: List[Tuple[str, dict]] = sorted(
            [(v, d) for d in raw_derivs if d["type"] == "SUFFIX"
             for v in d["surface_variants"]],
            key=lambda x: -len(x[0])
        )
        self.prefixes: List[Tuple[str, dict]] = sorted(
            [(v, d) for d in raw_derivs if d["type"] == "PREFIX"
             for v in d["surface_variants"]],
            key=lambda x: -len(x[0])
        )

    def _step_a(self, word: str) -> Tuple[str, Dict[str, str], str]:
        w = word.lower()
        if w in self.irregulars:
            entry = self.irregulars[w]
            tags = {}
            for pair in entry["tag"].split("|"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    tags[k] = v
            return entry["base"], tags, entry["pos"]
        if w.endswith("'s"):
            return w[:-2], {"poss": "YES"}, "NOUN"
        if w.endswith("ing") and len(w) > 5:
            stem = w[:-3]
            if len(stem) >= 2 and stem[-1] == stem[-2] and stem[-1] not in self.VOWELS:
                stem = stem[:-1]
            elif len(stem) >= 2 and stem[-1] not in self.VOWELS:
                stem = stem + "e"
            return stem, {"tense": "PRES", "aspect": "PROG"}, "VERB"
        if w.endswith("ed") and len(w) > 4:
            stem = w[:-2]
            if len(stem) >= 2 and stem[-1] == stem[-2] and stem[-1] not in self.VOWELS:
                stem = stem[:-1]
            return stem, {"tense": "PAST", "aspect": "PERF"}, "VERB"
        if w.endswith("ies") and len(w) > 4:
            return w[:-3] + "y", {"num": "PL"}, "NOUN"
        if w.endswith("es") and len(w) > 4:
            return w[:-2], {"num": "PL"}, "NOUN"
        if w.endswith("s") and len(w) > 3 and not w.endswith("ss"):
            return w[:-1], {"num": "PL"}, "NOUN"
        if w.endswith("est") and len(w) > 5:
            return w[:-3], {"degree": "SUPER"}, "ADJ"
        if w.endswith("er") and len(w) > 4:
            return w[:-2], {"degree": "COMP"}, "ADJ"
        return w, {}, "UNKNOWN"

    def _step_b(self, stem: str) -> Tuple[str, List[str]]:
        chain: List[str] = []
        for surface, deriv in self.suffixes:
            if stem.endswith(surface) and len(stem) - len(surface) >= 2:
                chain.append(f"{surface}→{deriv['derives']}")
                return stem[:-len(surface)], chain
        for surface, deriv in self.prefixes:
            if stem.startswith(surface) and len(stem) - len(surface) >= 2:
                chain.append(f"{surface}→{deriv['derives']}")
                return stem[len(surface):], chain
        return stem, chain

    def _step_c(self, stem: str) -> str:
        root = stem
        for _ in range(4):
            new_root, _ = self._step_b(root)
            if new_root == root:
                break
            root = new_root
        return root

    def analyze(self, word: str) -> TokenInfo:
        stem, tags, pos = self._step_a(word)
        _, derived_chain = self._step_b(stem)
        root = self._step_c(stem)
        return TokenInfo(
            surface=word, clitics={}, template="",
            root=root, tags=tags, pos=pos, derived_chain=derived_chain,
        )

    def analyze_sentence(self, sentence: str) -> Tuple[List[TokenInfo], bool, str]:
        tokens = [self.analyze(w) for w in sentence.split()]
        word_ok = check_morph_sequence_en(tokens)
        sent_ok, sent_msg = validate_sentence_structure_en(tokens)
        return tokens, word_ok and sent_ok, sent_msg
