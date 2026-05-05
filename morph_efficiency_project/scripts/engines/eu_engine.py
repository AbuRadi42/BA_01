"""
engines/eu_engine.py
--------------------
Basque (Euskara) morphology engine -- the polypersonal outlier.

Basque is an ergative-absolutive language isolate with tri-personal verb
agreement. The auxiliary verb system encodes up to three agreement slots
(NOR/absolutive, NORK/ergative, NORI/dative) in a single fusional word form.

Architecture:
  1. Closed-class intercept (~82 entries)
  2. Auxiliary lookup table (O(1) -- bypasses Steps A/B/C)
  3. Step A -- Inflectional stripping (non-finite verbs, noun declension)
  4. Step B -- Derivational suffix/prefix detection
  5. Step C -- Iterative root extraction (max 3 rounds)
"""

import json
import os
from typing import Dict, List, Optional, Tuple

from .shared import (
    TokenInfo,
    check_morph_sequence_eu,
    validate_sentence_structure_eu,
)

# ── Closed-class lexicon (~82 entries) ───────────────────────────────────────

CLOSED_CLASS: Dict[str, Dict] = {}


def _build_closed_class():
    conjunctions = {
        "eta": {"pos": "CONJ", "sem": "AND"},
        "edo": {"pos": "CONJ", "sem": "OR"},
        "baina": {"pos": "CONJ", "sem": "BUT"},
        "baizik": {"pos": "CONJ", "sem": "BUT_RATHER"},
        "ezta": {"pos": "CONJ", "sem": "NOR"},
        "beraz": {"pos": "CONJ", "sem": "THEREFORE"},
        "orduan": {"pos": "CONJ", "sem": "THEN"},
        "gainera": {"pos": "CONJ", "sem": "MOREOVER"},
        "bestalde": {"pos": "CONJ", "sem": "ON_THE_OTHER_HAND"},
        "hala ere": {"pos": "CONJ", "sem": "NEVERTHELESS"},
        "nahiz eta": {"pos": "CONJ", "sem": "ALTHOUGH"},
        "baldin eta": {"pos": "CONJ", "sem": "IF"},
    }
    question_words = {
        "nor": {"pos": "PRON", "sem": "INTERROGATIVE_WHO"},
        "zer": {"pos": "PRON", "sem": "INTERROGATIVE_WHAT"},
        "non": {"pos": "ADV", "sem": "INTERROGATIVE_WHERE"},
        "nora": {"pos": "ADV", "sem": "INTERROGATIVE_WHERE_TO"},
        "nondik": {"pos": "ADV", "sem": "INTERROGATIVE_WHERE_FROM"},
        "noiz": {"pos": "ADV", "sem": "INTERROGATIVE_WHEN"},
        "nola": {"pos": "ADV", "sem": "INTERROGATIVE_HOW"},
        "zergatik": {"pos": "ADV", "sem": "INTERROGATIVE_WHY"},
        "zein": {"pos": "PRON", "sem": "INTERROGATIVE_WHICH"},
        "zenbat": {"pos": "ADV", "sem": "INTERROGATIVE_HOW_MANY"},
    }
    pronouns = {
        "ni": {"pos": "PRON", "person": "1", "num": "SG"},
        "zu": {"pos": "PRON", "person": "2", "num": "SG", "formality": "FORMAL"},
        "hi": {"pos": "PRON", "person": "2", "num": "SG", "formality": "INFORMAL"},
        "hura": {"pos": "PRON", "person": "3", "num": "SG"},
        "gu": {"pos": "PRON", "person": "1", "num": "PL"},
        "zuek": {"pos": "PRON", "person": "2", "num": "PL"},
        "haiek": {"pos": "PRON", "person": "3", "num": "PL"},
        "hau": {"pos": "PRON", "sem": "DEM_PROX"},
        "hori": {"pos": "PRON", "sem": "DEM_MED"},
        "bera": {"pos": "PRON", "sem": "REFLEXIVE"},
        "elkar": {"pos": "PRON", "sem": "RECIPROCAL"},
        "zerbait": {"pos": "PRON", "sem": "INDEF_THING"},
        "norbait": {"pos": "PRON", "sem": "INDEF_PERSON"},
        "ezer": {"pos": "PRON", "sem": "NEG_THING"},
        "inor": {"pos": "PRON", "sem": "NEG_PERSON"},
        "dena": {"pos": "PRON", "sem": "UNIVERSAL_THING"},
        "denak": {"pos": "PRON", "sem": "UNIVERSAL_PERSON"},
        "beste": {"pos": "PRON", "sem": "OTHER"},
        "bata": {"pos": "PRON", "sem": "ONE_OF"},
        "bestea": {"pos": "PRON", "sem": "THE_OTHER"},
    }
    postpositions = {
        "aurretik": {"pos": "ADP", "sem": "BEFORE"},
        "ondoren": {"pos": "ADP", "sem": "AFTER"},
        "gainean": {"pos": "ADP", "sem": "ON_TOP"},
        "azpian": {"pos": "ADP", "sem": "UNDER"},
        "artean": {"pos": "ADP", "sem": "BETWEEN"},
        "inguruan": {"pos": "ADP", "sem": "AROUND"},
        "barruan": {"pos": "ADP", "sem": "INSIDE"},
        "kanpoan": {"pos": "ADP", "sem": "OUTSIDE"},
        "alde": {"pos": "ADP", "sem": "SIDE"},
        "kontra": {"pos": "ADP", "sem": "AGAINST"},
        "buruz": {"pos": "ADP", "sem": "ABOUT"},
        "gabe": {"pos": "ADP", "sem": "WITHOUT"},
        "bidez": {"pos": "ADP", "sem": "BY_MEANS_OF"},
        "zehar": {"pos": "ADP", "sem": "THROUGH"},
    }
    adverbs = {
        "oso": {"pos": "ADV", "sem": "VERY"},
        "ere": {"pos": "ADV", "sem": "ALSO"},
        "bakarrik": {"pos": "ADV", "sem": "ONLY"},
        "hemen": {"pos": "ADV", "sem": "HERE_PROX"},
        "hor": {"pos": "ADV", "sem": "HERE_MED"},
        "han": {"pos": "ADV", "sem": "THERE_DIST"},
        "orain": {"pos": "ADV", "sem": "NOW"},
        "gero": {"pos": "ADV", "sem": "LATER"},
        "lehen": {"pos": "ADV", "sem": "BEFORE"},
        "beti": {"pos": "ADV", "sem": "ALWAYS"},
        "inoiz": {"pos": "ADV", "sem": "NEVER"},
        "askotan": {"pos": "ADV", "sem": "OFTEN"},
        "gutxitan": {"pos": "ADV", "sem": "RARELY"},
        "ondo": {"pos": "ADV", "sem": "WELL"},
        "gaizki": {"pos": "ADV", "sem": "BADLY"},
        "azkar": {"pos": "ADV", "sem": "FAST"},
    }
    particles = {
        "ez": {"pos": "PART", "sem": "NEG"},
        "al": {"pos": "PART", "sem": "Q_PARTICLE"},
        "ote": {"pos": "PART", "sem": "WONDER"},
        "bide": {"pos": "PART", "sem": "APPARENTLY"},
        "ba": {"pos": "PART", "sem": "AFF_COND"},
    }
    determiners = {
        "bat": {"pos": "DET", "sem": "INDEF_SG"},
        "batzuk": {"pos": "DET", "sem": "INDEF_PL"},
        "hainbat": {"pos": "DET", "sem": "SEVERAL"},
        "asko": {"pos": "DET", "sem": "MANY"},
        "gutxi": {"pos": "DET", "sem": "FEW"},
    }
    all_entries = {}
    for d in [conjunctions, question_words, pronouns, postpositions,
              adverbs, particles, determiners]:
        all_entries.update(d)
    return all_entries


CLOSED_CLASS = _build_closed_class()

# Multi-word closed-class entries (checked via lookahead)
MULTI_WORD_CLOSED = {
    "hala ere": {"pos": "CONJ", "sem": "NEVERTHELESS"},
    "nahiz eta": {"pos": "CONJ", "sem": "ALTHOUGH"},
    "baldin eta": {"pos": "CONJ", "sem": "IF"},
}

# ── Basque vowels ────────────────────────────────────────────────────────────

ALL_VOWELS = set("aeiou")


class BasqueEngine:
    """
    Basque morphology engine.

    Basque is an ergative-absolutive language isolate with polypersonal
    agreement. The auxiliary verb system encodes up to three agreement
    slots (NOR, NORK, NORI) in a single fusional word.

    The engine processes words in this order:
      1. Closed-class intercept
      2. Auxiliary lookup (O(1) -- the crown jewel)
      3. Step A: inflectional stripping (case suffixes, verb non-finite forms)
      4. Step B: derivational affix detection
      5. Step C: iterative root extraction (max 3 rounds)
    """

    def __init__(self, config_dir: str = "morph_efficiency_project/configs"):
        self.config_dir = config_dir

        # Load auxiliary lookup table
        aux_path = os.path.join(config_dir, "eu_auxiliary.json")
        with open(aux_path, encoding="utf-8") as f:
            raw_aux = json.load(f)
        # Flatten into {surface_form: info_dict}
        self.aux_lookup: Dict[str, Dict] = {}
        for form, info in raw_aux.items():
            if form.startswith("_"):
                continue
            self.aux_lookup[form] = info

        # Load case suffix table
        cases_path = os.path.join(config_dir, "eu_cases.json")
        with open(cases_path, encoding="utf-8") as f:
            raw_cases = json.load(f)
        self.case_suffixes = self._build_case_suffix_table(raw_cases)

        # Load derivational rules
        deriv_path = os.path.join(config_dir, "eu_derivations.json")
        with open(deriv_path, encoding="utf-8") as f:
            self.derivations = json.load(f)

        # Sort derivations: longest affix first
        self.suffix_derivations = sorted(
            [d for d in self.derivations if d["type"] == "suffix"],
            key=lambda d: len(d["affix"]),
            reverse=True,
        )
        self.prefix_derivations = sorted(
            [d for d in self.derivations if d["type"] == "prefix"],
            key=lambda d: len(d["affix"]),
            reverse=True,
        )

    # ── Case suffix table builder ────────────────────────────────────────────

    def _build_case_suffix_table(self, raw_cases: List[dict]) -> List[dict]:
        """
        Build a flat list of case suffixes with tags, sorted longest first.
        Each entry: {"suffix": str, "case": str, "def": str, "num": str}
        """
        entries = []
        for c in raw_cases:
            case_name = c["case"]

            # Definite plural
            if c.get("def_pl") and c["def_pl"].startswith("-"):
                suf = c["def_pl"][1:]  # strip leading -
                entry = {"suffix": suf, "case": case_name, "def": "DEF", "num": "PL"}
                # Handle -ak ambiguity
                if case_name == "ABS" and suf == "ak":
                    entry["ambig_ak"] = True
                entries.append(entry)

            # Definite singular
            if c.get("def_sg") and c["def_sg"].startswith("-"):
                suf = c["def_sg"][1:]
                entry = {"suffix": suf, "case": case_name, "def": "DEF", "num": "SG"}
                if case_name == "ERG" and suf == "ak":
                    entry["ambig_ak"] = True
                entries.append(entry)

            # Indefinite
            if c.get("indef") and c["indef"].startswith("-"):
                suf = c["indef"][1:]
                entries.append({
                    "suffix": suf, "case": case_name,
                    "def": "INDEF", "num": "",
                })

        # Sort by suffix length descending (longest match first)
        entries.sort(key=lambda e: len(e["suffix"]), reverse=True)
        return entries

    # ── Stem validation ──────────────────────────────────────────────────────

    def _stem_plausible(self, stem: str) -> bool:
        """Stem must be >= 2 chars and contain at least one vowel."""
        if len(stem) < 2:
            return False
        return any(c in ALL_VOWELS for c in stem)

    # ── Auxiliary lookup (the crown jewel) ───────────────────────────────────

    def _try_auxiliary(self, word: str) -> Optional[TokenInfo]:
        """
        O(1) lookup in the auxiliary table. If found, return TokenInfo
        with full agreement decomposition, bypassing Steps A/B/C.
        """
        lower = word.lower()
        info = self.aux_lookup.get(lower)
        if info is None:
            return None

        paradigm = info.get("paradigm", "")
        tags: Dict[str, str] = {}

        # Map JSON fields to TokenInfo tags
        if "tense" in info:
            tags["tense"] = info["tense"]
        if "mood" in info:
            tags["mood"] = info["mood"]
        if "polarity" in info:
            tags["polarity"] = info["polarity"]

        # Agreement slots
        if "abs" in info:
            tags["agr_obj"] = info["abs"]
        if "erg" in info:
            tags["agr_subj"] = info["erg"]
        if "dat" in info:
            tags["agr_iobj"] = info["dat"]

        # Formality (zu vs hi distinction)
        if "formality" in info:
            tags["formality"] = info["formality"]
        # Allocutive gender
        if "allocutive_gender" in info:
            tags["allocutive_gender"] = info["allocutive_gender"]

        # POS: VERB for synthetic forms, AUX for auxiliary paradigms
        if paradigm == "SYNTHETIC":
            pos = "VERB"
            root = info.get("verb", lower)
        else:
            pos = "AUX"
            root = "izan" if paradigm in ("NOR", "NOR-NORI") else "ukan"

        return TokenInfo(
            surface=word,
            clitics={},
            template="",
            root=root,
            tags=tags,
            pos=pos,
            derived_chain=[],
        )

    # ── Step A: Inflectional stripping ───────────────────────────────────────

    def _strip_verb_nonfinite(self, word: str) -> Optional[Tuple[str, Dict[str, str]]]:
        """
        Try to strip non-finite verb suffixes.
        Returns (stem, tags) or None.
        """
        lower = word.lower()

        # Imperfective: -tzen, -ten (try longest first)
        for suf, tag in [("tzen", "IMPERF"), ("ten", "IMPERF")]:
            if lower.endswith(suf):
                stem = lower[:-len(suf)]
                if self._stem_plausible(stem):
                    return stem, {"aspect": tag}

        # Prospective: -ko, -go
        for suf, tag in [("ko", "PROSP"), ("go", "PROSP")]:
            if lower.endswith(suf):
                stem = lower[:-len(suf)]
                if self._stem_plausible(stem):
                    # Check this isn't a case suffix match (LOC_GEN -ko)
                    # Heuristic: verb stems with -ko/-go often end in -i/-tu
                    # We accept it but mark it
                    return stem, {"aspect": tag}

        # Perfective participle: -tu, -du (only if stem is plausible)
        for suf, tag in [("tu", "PERF"), ("du", "PERF")]:
            if lower.endswith(suf):
                stem = lower[:-len(suf)]
                if self._stem_plausible(stem):
                    return stem, {"aspect": tag}

        return None

    def _strip_adjective_degree(self, word: str) -> Tuple[str, Dict[str, str]]:
        """Strip comparative/superlative/excessive suffixes.
        Guard against -egi matching -tegi (place derivation)."""
        lower = word.lower()
        for suf, tag in [("ago", "COMP"), ("egi", "EXCESS"), ("en", "SUPER")]:
            if lower.endswith(suf) and len(lower) > len(suf) + 2:
                # Guard: don't strip -egi if -tegi (PLACE) derivation applies
                if suf == "egi" and lower.endswith("tegi"):
                    continue
                stem = lower[:-len(suf)]
                if self._stem_plausible(stem):
                    return stem, {"degree": tag}
        return lower, {}

    def _stem_has_derivation(self, stem: str) -> bool:
        """Check if a stem (or stem + restored vowel) contains a known
        derivational suffix, hinting at richer morphological structure."""
        # Direct match
        for rule in self.suffix_derivations:
            dsuf = rule["affix"]
            if len(dsuf) < 3:
                continue
            if stem.endswith(dsuf):
                remaining = stem[:-len(dsuf)]
                if self._stem_plausible(remaining):
                    return True
        # Vowel restoration: stem may have lost a trailing vowel to
        # case stripping (e.g., bilaket -> bilaketa has -keta)
        for vowel in ("a", "e", "i", "o"):
            extended = stem + vowel
            for rule in self.suffix_derivations:
                dsuf = rule["affix"]
                if len(dsuf) < 3:
                    continue
                if extended.endswith(dsuf):
                    remaining = extended[:-len(dsuf)]
                    if self._stem_plausible(remaining):
                        return True
        return False

    def _strip_case(self, word: str) -> Tuple[str, Dict[str, str]]:
        """
        Try to strip case suffix. Longest match first, but if a longer
        case suffix leaves a stem with no derivational structure while a
        shorter suffix for the same case does, prefer the shorter one.

        For short (1-char) indefinite case suffixes (-n, -k, -z),
        require a longer minimum stem to avoid over-stripping derivational
        endings like -tasun, -garri, -zain, etc.
        Returns (stem, tags).
        """
        lower = word.lower()

        # Collect all valid case matches
        candidates: List[Tuple[str, Dict[str, str]]] = []
        for entry in self.case_suffixes:
            suf = entry["suffix"]
            if not suf:
                continue
            if lower.endswith(suf):
                stem = lower[:-len(suf)]
                if not self._stem_plausible(stem):
                    continue
                # Short suffixes (1-2 chars) are aggressive. Check if the
                # word ends in a known derivational suffix that subsumes
                # the case suffix.
                if len(suf) <= 2:
                    blocked = False
                    for drule in self.suffix_derivations:
                        dsuf = drule["affix"]
                        if len(dsuf) >= 3 and lower.endswith(dsuf):
                            drem = lower[:-len(dsuf)]
                            if self._stem_plausible(drem):
                                blocked = True
                                break
                    if blocked:
                        continue
                tags: Dict[str, str] = {"case": entry["case"]}
                if entry["def"]:
                    tags["def"] = entry["def"]
                if entry["num"]:
                    tags["num"] = entry["num"]
                if entry.get("ambig_ak"):
                    tags["ambig_ak"] = "YES"
                candidates.append((stem, tags))

        # Check for bare definite article -a (ABS.DEF.SG)
        if lower.endswith("a") and len(lower) > 2:
            blocked = False
            for drule in self.suffix_derivations:
                dsuf = drule["affix"]
                if len(dsuf) >= 2 and lower.endswith(dsuf):
                    drem = lower[:-len(dsuf)]
                    if self._stem_plausible(drem):
                        blocked = True
                        break
            if not blocked:
                stem = lower[:-1]
                if self._stem_plausible(stem):
                    candidates.append(
                        (stem, {"case": "ABS", "def": "DEF", "num": "SG"})
                    )

        if not candidates:
            return lower, {}

        # If there's only one candidate, return it
        if len(candidates) == 1:
            return candidates[0]

        # The first candidate (longest suffix) is the default.
        # But if a shorter suffix for the SAME case leaves a stem with
        # derivational structure while the longer one doesn't, prefer it.
        # This handles cases like bilaketan where -etan (INES DEF PL) gives
        # stem "bilak" (no derivation) but -an (INES DEF SG) gives "bilaket"
        # which has -keta via vowel restoration.
        first_stem, first_tags = candidates[0]
        first_case = first_tags.get("case")
        if not self._stem_has_derivation(first_stem):
            for stem, tags in candidates[1:]:
                if tags.get("case") == first_case and self._stem_has_derivation(stem):
                    return stem, tags

        return candidates[0]

    def _is_verb_stem_for_prosp(self, stem: str) -> bool:
        """
        Check if a stem looks like a Basque verb citation form that would
        take -ko/-go prospective suffix. Basque verb participles typically
        end in -i and are >= 5 chars (ikusi, ikasi, irakurri, etorri).
        Shorter stems ending in -i (like toki=4) are typically nouns.

        Also matches stems ending in -n (egon, joan, izan) for -go forms.
        """
        if not self._stem_plausible(stem):
            return False
        # Verb participles ending in -i are >= 5 chars
        if stem.endswith("i") and len(stem) >= 5:
            return True
        # Verb stems ending in -n (for -go prospective: joango, egongo)
        if stem.endswith("n") and len(stem) >= 3:
            return True
        return False

    def _has_derivation_subsuming_case(self, word: str) -> bool:
        """
        Check if a derivational suffix subsumes the case suffix at the
        end of the word. E.g., 'egurrezko' ends in -ko (LOC_GEN) but
        the real morpheme is -zko (MADE_OF derivation).
        """
        for rule in self.suffix_derivations:
            dsuf = rule["affix"]
            if len(dsuf) >= 3 and word.endswith(dsuf):
                remaining = word[:-len(dsuf)]
                if self._stem_plausible(remaining):
                    return True
        return False

    def _step_a(self, word: str) -> Tuple[str, Dict[str, str]]:
        """
        Inflectional stripping for non-auxiliary words.

        Priority:
          1. Imperfective verb forms (-tzen, -ten) -- unambiguous
          1b. Prospective verb forms (-ko, -go) when the stem looks like
              a verb citation form (ends in -i or -n). This must come
              BEFORE case stripping since -ko overlaps with LOC_GEN.
          2. Case suffix stripping (14 cases x definiteness x number)
             Blocked if a derivational suffix subsumes the case suffix.
          3. Prospective: -ko, -go (fallback if case stripping didn't match)
          4. Perfective participle (-tu, -du)
          5. Adjective degree (-ago, -en, -egi)
        """
        lower = word.lower()

        # 1. Imperfective: -tzen, -ten are unambiguous verb markers
        for suf, tag in [("tzen", "IMPERF"), ("ten", "IMPERF")]:
            if lower.endswith(suf):
                stem = lower[:-len(suf)]
                if self._stem_plausible(stem):
                    return stem, {"aspect": tag}

        # 1b. Prospective -ko/-go: check BEFORE case stripping when the
        #     stem looks like a verb citation form (ends in -i or -n).
        for suf, tag in [("ko", "PROSP"), ("go", "PROSP")]:
            if lower.endswith(suf):
                stem = lower[:-len(suf)]
                if self._is_verb_stem_for_prosp(stem):
                    return stem, {"aspect": tag}

        # 2. Case stripping (longest suffix first -- handles -etarako, -arekin, etc.)
        #    But block case stripping if a derivational suffix subsumes the case suffix
        #    (e.g., -zko MADE_OF subsumes -ko LOC_GEN).
        if self._has_derivation_subsuming_case(lower):
            # Return the full word as stem with no inflectional tags.
            # Step B/C will peel the derivational suffix.
            return lower, {}

        stem, case_tags = self._strip_case(word)
        if case_tags:
            return stem, case_tags

        # 3. Prospective: -ko, -go (fallback if case stripping didn't match)
        for suf, tag in [("ko", "PROSP"), ("go", "PROSP")]:
            if lower.endswith(suf):
                stem = lower[:-len(suf)]
                if self._stem_plausible(stem):
                    return stem, {"aspect": tag}

        # 4. Perfective participle: -tu, -du
        for suf, tag in [("tu", "PERF"), ("du", "PERF")]:
            if lower.endswith(suf):
                stem = lower[:-len(suf)]
                if self._stem_plausible(stem):
                    return stem, {"aspect": tag}

        # 5. Adjective degree
        stem, deg_tags = self._strip_adjective_degree(word)
        if deg_tags:
            return stem, deg_tags

        return lower, {}

    # ── Step B: Derivational affix detection ─────────────────────────────────

    def _step_b(self, stem: str) -> Tuple[str, List[str]]:
        """
        Detect and strip one derivational affix.
        Suffix must be >= 2 chars, remaining stem >= 2 chars with a vowel.
        Returns (new_stem, chain_entries).

        Also tries vowel restoration: if the stem ended in a vowel that was
        consumed by case stripping (e.g., bilaketa -> bilaket after -an),
        try stem + vowel to match derivational suffixes.
        """
        chain: List[str] = []

        # Try suffix derivations (longest first)
        for rule in self.suffix_derivations:
            suf = rule["affix"]
            if len(suf) < 2:
                continue
            if stem.endswith(suf):
                remaining = stem[:-len(suf)]
                if self._stem_plausible(remaining):
                    chain.append(f"{suf}->{rule['function']}")
                    return remaining, chain

        # Try prefix derivations BEFORE vowel restoration (longest first).
        # This prevents spurious vowel-restored suffix matches from masking
        # real prefix derivations (e.g., des- in desager).
        for rule in self.prefix_derivations:
            pfx = rule["affix"]
            if len(pfx) < 2:
                continue
            if stem.startswith(pfx):
                remaining = stem[len(pfx):]
                if self._stem_plausible(remaining):
                    chain.append(f"{pfx}->{rule['function']}")
                    return remaining, chain

        # Vowel restoration (last resort): try stem + {a, e, i, o} to recover
        # derivational suffixes whose final vowel was consumed by case
        # stripping.  E.g., bilaket + a -> bilaketa -> finds -keta.
        for vowel in ("a", "e", "i", "o"):
            extended = stem + vowel
            for rule in self.suffix_derivations:
                suf = rule["affix"]
                if len(suf) < 3:
                    continue
                if extended.endswith(suf):
                    remaining = extended[:-len(suf)]
                    if self._stem_plausible(remaining):
                        chain.append(f"{suf}->{rule['function']}")
                        return remaining, chain

        return stem, chain

    # ── Step C: Iterative root extraction ────────────────────────────────────

    def _step_c(self, stem: str) -> Tuple[str, List[str]]:
        """Peel up to 3 derivational layers."""
        root = stem
        full_chain: List[str] = []
        for _ in range(3):
            new_root, chain = self._step_b(root)
            if new_root == root:
                break
            full_chain.extend(chain)
            root = new_root
        return root, full_chain

    # ── POS inference ────────────────────────────────────────────────────────

    def _infer_pos(self, tags: Dict[str, str], derived_chain: List[str]) -> str:
        """Infer POS from tags."""
        if "aspect" in tags:
            return "VERB"
        if "case" in tags:
            return "NOUN"
        if "degree" in tags:
            return "ADJ"
        # Check derivation chain for target POS hints
        if derived_chain:
            last = derived_chain[-1]
            for rule in self.derivations:
                if rule["function"] in last:
                    return rule.get("target_pos", "UNKNOWN")
        return "UNKNOWN"

    # ── Public API ───────────────────────────────────────────────────────────

    def analyze(self, word: str) -> TokenInfo:
        """Analyze a single Basque word."""
        lower = word.lower()

        # 1. Closed-class intercept
        if lower in CLOSED_CLASS:
            entry = CLOSED_CLASS[lower]
            pos = entry.get("pos", "PART")
            tags = {k: v for k, v in entry.items() if k != "pos"}
            return TokenInfo(
                surface=word, clitics={}, template="",
                root=lower, tags=tags, pos=pos, derived_chain=[],
            )

        # 2. Auxiliary lookup (O(1))
        aux_result = self._try_auxiliary(word)
        if aux_result is not None:
            return aux_result

        # 3. Step A: inflectional stripping
        stem, tags = self._step_a(word)

        # 4/5. Steps B/C: derivational + iterative root extraction
        root, derived_chain = self._step_c(stem)

        # 6. POS inference
        pos = self._infer_pos(tags, derived_chain)

        return TokenInfo(
            surface=word, clitics={}, template="",
            root=root, tags=tags, pos=pos, derived_chain=derived_chain,
        )

    def analyze_sentence(self, sentence: str) -> Tuple[List[TokenInfo], bool, str]:
        """Analyze a full sentence."""
        words = sentence.split()

        # Multi-word closed-class lookahead
        tokens: List[TokenInfo] = []
        i = 0
        while i < len(words):
            matched_multi = False
            # Try 3-word, then 2-word multi-word entries
            for span in (3, 2):
                if i + span <= len(words):
                    phrase = " ".join(words[i:i + span]).lower()
                    if phrase in MULTI_WORD_CLOSED:
                        entry = MULTI_WORD_CLOSED[phrase]
                        pos = entry.get("pos", "CONJ")
                        tags = {k: v for k, v in entry.items() if k != "pos"}
                        tokens.append(TokenInfo(
                            surface=" ".join(words[i:i + span]),
                            clitics={}, template="",
                            root=phrase, tags=tags, pos=pos,
                            derived_chain=[],
                        ))
                        i += span
                        matched_multi = True
                        break
            if not matched_multi:
                tokens.append(self.analyze(words[i]))
                i += 1

        word_ok = check_morph_sequence_eu(tokens)
        sent_ok, sent_msg = validate_sentence_structure_eu(tokens)
        return tokens, word_ok and sent_ok, sent_msg
