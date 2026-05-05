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

    # ── Bug 9: Closed-class dictionary ───────────────────────────────────────
    CLOSED_CLASS: Dict[str, Tuple[str, Dict[str, str]]] = {}

    # Determiners
    for _w in ["the", "a", "an"]:
        CLOSED_CLASS[_w] = ("DET", {})

    # Prepositions
    for _w in [
        "to", "of", "in", "at", "by", "for", "with", "on", "from", "about",
        "into", "through", "during", "before", "after", "above", "below",
        "between", "under", "over", "against", "along", "among", "around",
        "behind", "beneath", "beside", "beyond", "despite", "except",
        "inside", "outside", "toward", "towards", "until", "within", "without",
    ]:
        CLOSED_CLASS[_w] = ("PREP", {})

    # Pronouns
    for _w in [
        "i", "me", "my", "mine", "you", "your", "yours",
        "he", "him", "his", "she", "her", "hers", "it", "its",
        "we", "us", "our", "ours", "they", "them", "their", "theirs",
        "who", "whom", "whose", "which", "that", "what",
        "this", "these", "those",
        "myself", "yourself", "himself", "herself", "itself",
        "ourselves", "yourselves", "themselves",
    ]:
        CLOSED_CLASS[_w] = ("PRON", {})

    # Conjunctions
    for _w in [
        "and", "but", "or", "nor", "so", "yet", "for", "although",
        "because", "since", "unless", "while", "if", "when", "where",
        "after", "before", "until", "as", "though", "whereas", "whether",
    ]:
        # "for", "after", "before", "until" may already be set as PREP;
        # conjunctions share those entries — keep the first assignment
        if _w not in CLOSED_CLASS:
            CLOSED_CLASS[_w] = ("CONJ", {})

    # Auxiliary / modal verbs
    for _w in [
        "can", "could", "will", "would", "shall", "should",
        "may", "might", "must", "ought", "need", "dare",
    ]:
        CLOSED_CLASS[_w] = ("AUX", {"modal": "YES"})

    # Auxiliary forms that are already in irregulars (do/does/did, have/has/had,
    # am/is/are/was/were/be/been/being) are handled there; no need to duplicate.

    # ── Bug 3: Common verbs set for 3SG disambiguation ───────────────────────
    COMMON_VERBS = {
        "run", "walk", "eat", "play", "talk", "work", "move", "look",
        "think", "know", "want", "need", "feel", "seem", "come", "go",
        "take", "make", "give", "find", "tell", "ask", "use", "try",
        "leave", "call", "keep", "let", "begin", "show", "hear", "turn",
        "start", "stand", "lose", "pay", "meet", "bring", "hold", "write",
        "sit", "speak", "read", "grow", "lead", "live", "believe", "happen",
        "provide", "include", "continue", "set", "learn", "change",
        "follow", "stop", "create", "open", "fall", "win", "offer",
        "remember", "love", "consider", "appear", "buy", "wait", "serve",
        "die", "send", "expect", "build", "stay", "cut", "reach", "remain",
        "suggest", "raise", "pass", "sell", "require", "report", "decide",
        "pull", "develop", "break", "receive", "agree", "support", "hit",
        "produce", "eat", "cover", "catch", "draw", "choose", "sing",
        "swim", "drink", "drive", "ride", "fly", "fight", "wear", "throw",
        "teach", "cost", "help", "like", "mean", "add", "watch",
    }

    def __init__(self, config_dir: str = "morph_efficiency_project/configs"):
        with open(os.path.join(config_dir, "en_irregulars.json"), encoding="utf-8") as f:
            self.irregulars: Dict[str, dict] = json.load(f)
        with open(os.path.join(config_dir, "en_derivations.json"), encoding="utf-8") as f:
            raw_derivs = json.load(f)

        # Bug 1: Strip hyphens from surface variants so matching works
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

        # Bug 7: Load compounds config
        with open(os.path.join(config_dir, "en_compounds.json"), encoding="utf-8") as f:
            raw_compounds = json.load(f)
        self.compounds: Dict[str, dict] = {
            c["compound"]: c for c in raw_compounds
        }

        # Bug 8: Load phrasal verbs config
        with open(os.path.join(config_dir, "en_phrasal_verbs.json"), encoding="utf-8") as f:
            raw_phrasal = json.load(f)
        self.phrasal_verbs: Dict[str, dict] = {
            pv["token"]: pv for pv in raw_phrasal
        }
        # Also index by verb for quick lookup
        self.phrasal_verb_components: Dict[str, List[dict]] = {}
        for pv in raw_phrasal:
            self.phrasal_verb_components.setdefault(pv["verb"], []).append(pv)

    def _step_a(self, word: str) -> Tuple[str, Dict[str, str], str]:
        w = word.lower()

        # Bug 9: Check closed-class words first
        if w in self.CLOSED_CLASS:
            pos, tags = self.CLOSED_CLASS[w]
            return w, dict(tags), pos

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
            # Bug 5: Double-consonant undoubling with safety check
            if len(stem) >= 2 and stem[-1] == stem[-2] and stem[-1] not in self.VOWELS:
                undoubled = stem[:-1]
                # Only undouble if result is > 2 chars (prevents "add" -> "ad")
                if len(undoubled) > 2:
                    stem = undoubled
                # else keep doubled form (e.g., "add" stays "add")
            # Bug 2: Silent-e restoration for -ed
            # Only restore "e" when stem ends in VC (vowel then consonant),
            # indicating a silent-e root like lov->love, hop->hope, bak->bake.
            # Do NOT add "e" for stems ending in CC like "walk", "talk", "jump".
            # Exclude 'y' ending (played->play, not playe).
            elif (len(stem) >= 2
                  and stem[-1] not in self.VOWELS
                  and stem[-1] != "y"
                  and stem[-2] in self.VOWELS):
                stem = stem + "e"
            # Bug 4: Remove aspect=PERF from default -ed tags
            return stem, {"tense": "PAST"}, "VERB"
        if w.endswith("ies") and len(w) > 4:
            return w[:-3] + "y", {"num": "PL"}, "NOUN"
        if w.endswith("es") and len(w) > 4:
            return w[:-2], {"num": "PL"}, "NOUN"
        if w.endswith("s") and len(w) > 3 and not w.endswith("ss"):
            base = w[:-1]
            # Bug 3: Check for 3SG verb ambiguity
            if base in self.COMMON_VERBS:
                return base, {"num": "PL", "ambig_3sg": "YES"}, "NOUN"
            return base, {"num": "PL"}, "NOUN"
        if w.endswith("est") and len(w) > 5:
            return w[:-3], {"degree": "SUPER"}, "ADJ"
        if w.endswith("er") and len(w) > 4:
            return w[:-2], {"degree": "COMP"}, "ADJ"
        return w, {}, "UNKNOWN"

    def _step_b(self, stem: str) -> Tuple[str, List[str]]:
        chain: List[str] = []

        # Bug 7: Check compounds first
        if stem in self.compounds:
            compound = self.compounds[stem]
            head = compound["constituents"][-1]  # head is last constituent
            chain.append(f"COMPOUND({'+'.join(c['stem'] for c in compound['constituents'])})")
            return head["stem"], chain

        for surface, deriv in self.suffixes:
            if stem.endswith(surface) and len(stem) - len(surface) >= 3:
                chain.append(f"{surface}\u2192{deriv['derives']}")
                return stem[:-len(surface)], chain
        for surface, deriv in self.prefixes:
            if stem.startswith(surface) and len(stem) - len(surface) >= 3:
                chain.append(f"{surface}\u2192{deriv['derives']}")
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

        # Only run derivational stripping on words where step_a could not
        # determine inflection (UNKNOWN pos). For known inflected forms,
        # the stem from step_a IS the root — do not further strip it.
        if pos == "UNKNOWN":
            _, derived_chain = self._step_b(stem)
            root = self._step_c(stem)
        else:
            derived_chain = []
            root = stem

        # Bug 8: Tag phrasal verb components
        w_lower = word.lower()
        if w_lower in self.phrasal_verb_components:
            tags["phrasal_verb_base"] = "YES"

        return TokenInfo(
            surface=word, clitics={}, template="",
            root=root, tags=tags, pos=pos, derived_chain=derived_chain,
        )

    def analyze_sentence(self, sentence: str) -> Tuple[List[TokenInfo], bool, str]:
        tokens = [self.analyze(w) for w in sentence.split()]
        word_ok = check_morph_sequence_en(tokens)
        sent_ok, sent_msg = validate_sentence_structure_en(tokens)
        return tokens, word_ok and sent_ok, sent_msg
