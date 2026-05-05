"""
engines/zh_engine.py
--------------------
Mandarin Chinese morphology engine (control language).

Deliberately simple -- Mandarin has near-zero morphology.
The engine's main job is closed-class lookup; inflectional and
derivational stripping are minimal.
"""

import json
import os
from typing import Dict, List, Tuple

from .shared import (
    TokenInfo,
    check_morph_sequence_zh,
    validate_sentence_structure_zh,
)

# Number characters used for ordinal-prefix validation
_NUMBERS = set("一二两三四五六七八九十百千万亿零")

# Animate bases that accept 们 (plural marker)
_ANIMATE_BASES = {
    "我", "你", "您", "他", "她", "它",
    "人", "孩子", "同学", "朋友", "同事",
    "老师", "学生", "客人", "女士", "先生",
}


class MandarinEngine:
    """
    Mandarin morphology engine.

    Step A -- Inflectional stripping (5 rules only):
        1. 们 plural on animate nouns / pronouns
        2. 了 perfective aspect suffix
        3. 着 durative aspect suffix
        4. 过 experiential aspect suffix
        5. 第 ordinal prefix
    Step B -- Derivational detection (~13 patterns, mostly lexicalized)
    Step C -- Root extraction (max 2 iterations of Step B)
    """

    def __init__(self, config_dir: str = "morph_efficiency_project/configs"):
        # Load particles config (grouped by category)
        with open(os.path.join(config_dir, "zh_particles.json"), encoding="utf-8") as f:
            raw_particles = json.load(f)

        # Load classifiers config (flat dict)
        with open(os.path.join(config_dir, "zh_classifiers.json"), encoding="utf-8") as f:
            raw_classifiers = json.load(f)

        # Merge everything into a single closed-class lookup: surface -> (pos, tags)
        self.closed_class: Dict[str, Tuple[str, Dict[str, str]]] = {}

        # Particles file: each top-level key is a category containing a dict
        for _category, entries in raw_particles.items():
            for surface, info in entries.items():
                if surface not in self.closed_class:
                    self.closed_class[surface] = (info["pos"], dict(info["tags"]))

        # Classifiers file: flat dict of surface -> {pos, tags}
        for surface, info in raw_classifiers.items():
            if surface not in self.closed_class:
                self.closed_class[surface] = (info["pos"], dict(info["tags"]))

    # ── Step A: Inflectional stripping ──────────────────────────────────────

    def _step_a(self, word: str) -> Tuple[str, Dict[str, str], str]:
        # 1. Closed-class intercept
        if word in self.closed_class:
            pos, tags = self.closed_class[word]
            return word, dict(tags), pos

        # 2. Plural 们 (animate nouns / pronouns only)
        if len(word) >= 2 and word.endswith("们"):
            base = word[:-1]
            if base in _ANIMATE_BASES:
                return base, {"num": "PL"}, "NOUN"

        # 3. Perfective 了 (attached to verb, len >= 2)
        if len(word) >= 2 and word.endswith("了"):
            return word[:-1], {"aspect": "PERF"}, "VERB"

        # 4. Durative 着 (attached to verb, len >= 2)
        if len(word) >= 2 and word.endswith("着"):
            return word[:-1], {"aspect": "DUR"}, "VERB"

        # 5. Experiential 过 (attached to verb, len >= 2)
        if len(word) >= 2 and word.endswith("过"):
            return word[:-1], {"aspect": "EXP"}, "VERB"

        # 6. Ordinal prefix 第
        if len(word) >= 2 and word.startswith("第"):
            remainder = word[1:]
            if all(ch in _NUMBERS for ch in remainder):
                return remainder, {"role": "ORDINAL"}, "NUM"

        # 7. Default
        return word, {}, "UNKNOWN"

    # ── Step B: Derivational detection ──────────────────────────────────────

    # Prefixes: (prefix_char, label)
    _PREFIXES = [
        ("老", "FAMILIAR_PREFIX"),
        ("小", "DIMINUTIVE_PREFIX"),
        ("阿", "FAMILIAR_PREFIX"),
    ]

    # Suffixes: (suffix_char, label, pos)
    _SUFFIXES = [
        ("子", "NOMINALIZER", "NOUN"),
        ("儿", "ERHUA_DIM", "NOUN"),
        ("头", "NOMINALIZER", "NOUN"),
        ("家", "AGENT_EXPERT", "NOUN"),
        ("员", "AGENT_MEMBER", "NOUN"),
        ("者", "AGENT_PERSON", "NOUN"),
        ("化", "VERBALIZER", "VERB"),
        ("性", "QUALITY_NOUN", "NOUN"),
        ("式", "STYLE_ADJ", "ADJ"),
        ("学", "STUDY_OF", "NOUN"),
    ]

    def _step_b(self, stem: str, pos: str) -> Tuple[str, List[str], str]:
        chain: List[str] = []

        # Check prefixes (stem must have >= 2 chars, remainder >= 1 char)
        for prefix, label in self._PREFIXES:
            if stem.startswith(prefix) and len(stem) >= 2:
                chain.append(f"{prefix}->{label}")
                return stem[len(prefix):], chain, "NOUN"

        # Check suffixes (stem must have >= 2 chars, remainder >= 1 char)
        for suffix, label, deriv_pos in self._SUFFIXES:
            if stem.endswith(suffix) and len(stem) >= 2:
                chain.append(f"{suffix}->{label}")
                return stem[:-len(suffix)], chain, deriv_pos

        return stem, chain, pos

    # ── Step C: Root extraction ─────────────────────────────────────────────

    def _step_c(self, stem: str, pos: str) -> Tuple[str, str]:
        root = stem
        cur_pos = pos
        for _ in range(2):
            new_root, _, new_pos = self._step_b(root, cur_pos)
            if new_root == root:
                break
            root = new_root
            cur_pos = new_pos
        return root, cur_pos

    # ── Public API ──────────────────────────────────────────────────────────

    def analyze(self, word: str) -> TokenInfo:
        stem, tags, pos = self._step_a(word)

        # Only run derivational stripping on UNKNOWN POS words
        if pos == "UNKNOWN":
            root, derived_chain, deriv_pos = self._step_b(stem, pos)
            if derived_chain:
                pos = deriv_pos
        else:
            derived_chain = []
            root = stem

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
        word_ok = check_morph_sequence_zh(tokens)
        sent_ok, sent_msg = validate_sentence_structure_zh(tokens)
        return tokens, word_ok and sent_ok, sent_msg
