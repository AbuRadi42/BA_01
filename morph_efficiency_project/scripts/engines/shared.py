"""
engines/shared.py
-----------------
Shared data structures and validators used by all three grammar engines.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

log = logging.getLogger(__name__)

# ── Shared data structure ─────────────────────────────────────────────────────

@dataclass
class TokenInfo:
    surface:       str
    clitics:       Dict[str, List[str]]
    template:      str
    root:          str
    tags:          Dict[str, str]
    pos:           str
    derived_chain: List[str] = field(default_factory=list)

    def feature_bundle_str(self) -> str:
        if not self.tags:
            return "no_features"
        parts = [f"pos={self.pos}"] + [f"{k}={v}" for k, v in sorted(self.tags.items())]
        return "|".join(parts)

    def token_str(self) -> str:
        return f"{self.root}.{self.pos}"

# ── Vocabulary / feature bundle registry ─────────────────────────────────────

class MorphVocab:
    SPECIAL = ["<pad>", "<unk>", "<s>", "</s>"]

    def __init__(self):
        self.token2id:  Dict[str, int] = {}
        self.bundle2id: Dict[str, int] = {"no_features": 0}
        for t in self.SPECIAL:
            self._get_token_id(t)

    def _get_token_id(self, token: str) -> int:
        if token not in self.token2id:
            self.token2id[token] = len(self.token2id)
        return self.token2id[token]

    def _get_bundle_id(self, bundle: str) -> int:
        if bundle not in self.bundle2id:
            self.bundle2id[bundle] = len(self.bundle2id)
        return self.bundle2id[bundle]

    def encode(self, token_info: TokenInfo) -> Tuple[int, int]:
        tok_id    = self._get_token_id(token_info.token_str())
        bundle_id = self._get_bundle_id(token_info.feature_bundle_str())
        return tok_id, bundle_id

    def save(self, tok_dir: str):
        os.makedirs(tok_dir, exist_ok=True)
        with open(os.path.join(tok_dir, "vocab.json"), "w", encoding="utf-8") as f:
            json.dump(self.token2id, f, ensure_ascii=False, indent=2)
        with open(os.path.join(tok_dir, "feature_bundles.json"), "w", encoding="utf-8") as f:
            json.dump(self.bundle2id, f, ensure_ascii=False, indent=2)
        log.info(
            f"Vocab: {len(self.token2id)} tokens, "
            f"{len(self.bundle2id)} feature bundles → {tok_dir}"
        )

# ══════════════════════════════════════════════════════════════════════════════
# WORD-LEVEL SEQUENCE VALIDATORS
# ══════════════════════════════════════════════════════════════════════════════

def check_morph_sequence_en(tokens: List[TokenInfo]) -> bool:
    """Validate per-token tag bundles for English."""
    NOUN_ALLOWED = {"num", "poss", "ambig_3sg"}
    VERB_ALLOWED = {"tense", "aspect", "person", "voice", "phrasal_verb_base"}
    ADJ_ALLOWED  = {"degree"}
    ADV_ALLOWED  = {"degree"}
    for t in tokens:
        keys = set(t.tags.keys())
        if t.pos == "NOUN" and not keys.issubset(NOUN_ALLOWED):
            return False
        if t.pos == "VERB":
            if not keys.issubset(VERB_ALLOWED):
                return False
            if t.tags.get("aspect") == "PERF" and t.tags.get("tense") not in ("PAST", "PRES", None):
                return False
            if t.tags.get("voice") == "PASS" and t.tags.get("aspect") not in ("PERF", "SIMPLE", None):
                return False
        if t.pos == "ADJ" and not keys.issubset(ADJ_ALLOWED):
            return False
        if t.pos == "ADV" and not keys.issubset(ADV_ALLOWED):
            return False
    return True

def check_morph_sequence_ar(tokens: List[TokenInfo]) -> bool:
    """Validate per-token tag bundles for Arabic (النحو والصرف rules)."""
    for t in tokens:
        keys = set(t.tags.keys())
        if t.pos == "VERB":
            if "tense" not in keys or "person" not in keys:
                return False
            if t.tags.get("tense") == "IMP":
                if t.tags.get("person") != "2" or t.tags.get("voice") != "ACT":
                    return False
            if t.tags.get("voice") == "PASS" and t.tags.get("tense") == "IMP":
                return False
            if t.tags.get("mood") == "JUS" and t.tags.get("tense") != "PRES":
                return False
            if keys & {"case", "def"}:
                return False
        if t.pos == "NOM":
            if keys & {"tense", "person", "mood"}:
                return False
            if "num" not in keys or "gender" not in keys:
                return False
        if t.pos == "ADJ":
            if keys & {"tense", "person", "mood"}:
                return False
    return True

def check_morph_sequence_tr(tokens: List[TokenInfo]) -> bool:
    """Validate suffix slot ordering for Turkish (Dilbilgisi rules)."""
    NOMINAL_ORDER = ["DERIV", "NUM", "POSS", "CASE"]
    VERBAL_ORDER  = ["DERIV", "VOICE", "NEG", "TENSE", "MOOD", "PERSON_NUM"]
    for t in tokens:
        if t.pos in ("NOUN", "ADJ"):
            present = [s for s in NOMINAL_ORDER if s in t.tags]
            if present != sorted(present, key=lambda s: NOMINAL_ORDER.index(s)):
                return False
        if t.pos == "VERB":
            if t.tags.get("polarity") == "NEG":
                neg_idx = VERBAL_ORDER.index("NEG")
                tns_idx = VERBAL_ORDER.index("TENSE")
                if neg_idx > tns_idx:
                    return False
            if t.tags.get("mood") == "IMP":
                if t.tags.get("person") not in ("2", None):
                    return False
            if t.tags.get("voice") == "CAUS":
                if t.tags.get("voice_base") == "PASS":
                    return False
    return True

# ══════════════════════════════════════════════════════════════════════════════
# SENTENCE-LEVEL STRUCTURE VALIDATORS
# ══════════════════════════════════════════════════════════════════════════════

def validate_sentence_structure_en(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """English SVO sentence structure validation."""
    for t in tokens:
        if t.tags.get("degree") in ("COMP", "SUPER") and t.pos not in ("ADJ", "ADV"):
            return False, f"degree tag on non-ADJ/ADV: {t.surface}"
    for t in tokens:
        if t.tags.get("aspect") == "PERF" and t.tags.get("tense") not in ("PAST", "PRES", None):
            return False, f"PERF aspect without valid tense: {t.surface}"
    for t in tokens:
        if t.tags.get("poss") == "YES" and t.pos != "NOUN":
            return False, f"possessive on non-NOUN: {t.surface}"
    return True, "ok"

def validate_sentence_structure_ar(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """Arabic VSO / nominal sentence structure validation."""
    content = [t for t in tokens if t.pos not in ("PART", "FOREIGN", "PROPER", "UNKNOWN")]
    if not content:
        return True, "ok"
    first = content[0]
    if first.pos == "VERB":
        if "tense" not in first.tags:
            return False, f"verbal sentence opener missing tense: {first.surface}"
        if "person" not in first.tags:
            return False, f"verbal sentence opener missing person: {first.surface}"
    if first.pos == "NOM":
        if first.tags.get("case") not in ("NOM", None):
            return False, f"nominal sentence subject not in nominative: {first.surface}"
    for t in content:
        if t.pos == "VERB":
            if t.tags.get("voice") == "PASS" and t.tags.get("tense") == "IMP":
                return False, f"passive imperative is invalid: {t.surface}"
            if t.tags.get("mood") == "JUS" and t.tags.get("tense") != "PRES":
                return False, f"jussive mood outside present tense: {t.surface}"
    for t in content:
        if t.pos == "NOM" and t.tags.get("num") == "DU":
            if "case" not in t.tags:
                return False, f"dual noun missing case tag: {t.surface}"
    return True, "ok"

def check_morph_sequence_zh(tokens: List[TokenInfo]) -> bool:
    """Validate per-token tag bundles for Mandarin Chinese."""
    NOUN_ALLOWED  = {"num"}
    VERB_ALLOWED  = {"aspect", "role"}
    ADV_ALLOWED   = {"negation", "degree", "aspect", "subcat"}
    PRON_ALLOWED  = {"person", "num", "gender", "deixis", "interrog", "reflex",
                     "register", "subcat"}
    PART_ALLOWED  = {"aspect", "role", "particle_type"}
    ADP_ALLOWED   = {"construction", "voice", "role", "subcat"}
    CLF_ALLOWED   = {"classifier"}
    AUX_ALLOWED   = {"modal"}
    NUM_ALLOWED   = {"role"}
    DET_ALLOWED   = {"subcat", "interrog", "num"}
    CONJ_ALLOWED  = {"subcat"}
    VALID_ASPECT  = {"PERF", "DUR", "EXP", "PROG"}
    VALID_NEG     = {"BU", "MEI", "BIE"}

    for t in tokens:
        keys = set(t.tags.keys())
        if t.pos == "NOUN" and not keys.issubset(NOUN_ALLOWED):
            return False
        if t.pos == "VERB" and not keys.issubset(VERB_ALLOWED):
            return False
        if t.pos == "ADV" and not keys.issubset(ADV_ALLOWED):
            return False
        if t.pos == "PRON" and not keys.issubset(PRON_ALLOWED):
            return False
        if t.pos == "PART" and not keys.issubset(PART_ALLOWED):
            return False
        if t.pos == "ADP" and not keys.issubset(ADP_ALLOWED):
            return False
        if t.pos == "CLF" and not keys.issubset(CLF_ALLOWED):
            return False
        if t.pos == "AUX" and not keys.issubset(AUX_ALLOWED):
            return False
        if t.pos == "NUM" and not keys.issubset(NUM_ALLOWED):
            return False
        if t.pos == "DET" and not keys.issubset(DET_ALLOWED):
            return False
        if t.pos == "CONJ" and not keys.issubset(CONJ_ALLOWED):
            return False
        # Cross-field checks
        if "aspect" in keys and t.tags["aspect"] not in VALID_ASPECT:
            return False
        if "negation" in keys and t.tags["negation"] not in VALID_NEG:
            return False
    return True


def validate_sentence_structure_zh(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """Mandarin SVO sentence structure validation."""
    content = [t for t in tokens if t.pos not in ("UNKNOWN", "PUNCT")]
    if not content:
        return True, "ok"

    # Ba-construction: 把 must be followed by a verb somewhere
    for i, t in enumerate(content):
        if t.tags.get("construction") == "BA":
            has_verb = any(c.pos == "VERB" for c in content[i + 1:])
            if not has_verb:
                return False, "把 without following verb"

    # Bei-construction: 被 must be followed by a verb somewhere
    for i, t in enumerate(content):
        if t.tags.get("construction") == "BEI":
            has_verb = any(c.pos == "VERB" for c in content[i + 1:])
            if not has_verb:
                return False, "被 without following verb"

    # Aspect particle attachment: aspect PART should follow a verb
    for i, t in enumerate(content):
        if t.pos == "PART" and "aspect" in t.tags:
            preceding = [c for c in content[:i] if c.pos == "VERB"]
            if not preceding and i > 0:
                return False, f"aspect particle not preceded by verb: {t.surface}"

    return True, "ok"


def check_morph_sequence_es(tokens: List[TokenInfo]) -> bool:
    """Validate per-token tag bundles for Spanish."""
    NOUN_ALLOWED = {"num", "gender", "invariant"}
    VERB_ALLOWED = {"tense", "mood", "person", "num", "aspect", "form",
                    "formality", "subj_form", "clitic_obj", "ambig_ser_ir"}
    ADJ_ALLOWED  = {"num", "gender", "degree"}
    ADV_ALLOWED  = {"degree", "subcat"}
    for t in tokens:
        keys = set(t.tags.keys())
        if t.pos == "NOUN":
            if not keys.issubset(NOUN_ALLOWED):
                return False
            if t.tags.get("invariant") == "YES" and t.tags.get("num") != "SG":
                return False
        if t.pos == "VERB":
            if not keys.issubset(VERB_ALLOWED):
                return False
            if t.tags.get("mood") == "IMP" and t.tags.get("person") == "1":
                return False
            if (t.tags.get("mood") == "SUBJ"
                    and t.tags.get("tense") == "PAST_IMPERF"
                    and "subj_form" in keys
                    and t.tags["subj_form"] not in ("RA", "SE")):
                return False
            if t.tags.get("form") == "INF":
                for k in ("tense", "person", "num", "mood"):
                    if k in keys:
                        return False
            if t.tags.get("form") == "GER":
                for k in ("tense", "person", "num", "mood"):
                    if k in keys:
                        return False
            if (t.tags.get("form") == "PTCP"
                    and "gender" in keys and "num" not in keys):
                return False
        if t.pos == "ADJ" and not keys.issubset(ADJ_ALLOWED):
            return False
        if t.pos == "ADV" and not keys.issubset(ADV_ALLOWED):
            return False
    return True


def validate_sentence_structure_es(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """Spanish SVO sentence structure validation."""
    # 1. Gender/number agreement (noun-adjective adjacency)
    for i in range(len(tokens) - 1):
        a, b = tokens[i], tokens[i + 1]
        if {a.pos, b.pos} == {"NOUN", "ADJ"}:
            if (a.tags.get("gender") and b.tags.get("gender")
                    and a.tags["gender"] != b.tags["gender"]):
                return (False,
                        f"gender/number disagreement between noun and "
                        f"adjective: {a.surface} / {b.surface}")
            if (a.tags.get("num") and b.tags.get("num")
                    and a.tags["num"] != b.tags["num"]):
                return (False,
                        f"gender/number disagreement between noun and "
                        f"adjective: {a.surface} / {b.surface}")

    for t in tokens:
        # 2. Finite verb must have person + num
        if t.pos == "VERB" and t.tags.get("mood") in ("IND", "SUBJ"):
            if "person" not in t.tags or "num" not in t.tags:
                return (False,
                        f"finite verb missing person or number: {t.surface}")

        # 3. Clitic on non-verb
        if "clitic_obj" in t.tags and t.pos != "VERB":
            return False, f"clitic_obj on non-VERB: {t.surface}"

        # 4. Degree on non-adjective
        if t.tags.get("degree") in ("COMP", "SUPER") and t.pos != "ADJ":
            return False, f"degree tag on non-ADJ: {t.surface}"

    return True, "ok"


def check_morph_sequence_hu(tokens: List[TokenInfo]) -> bool:
    """Validate per-token tag bundles for Hungarian."""
    NOMINAL_ALLOWED = {"num", "case", "poss", "poss_num", "degree"}
    VERBAL_ALLOWED  = {"tense", "mood", "person", "num", "def"}
    ADJ_ALLOWED     = {"degree", "num", "case"}
    for t in tokens:
        keys = set(t.tags.keys())
        if t.pos == "NOUN":
            if not keys.issubset(NOMINAL_ALLOWED):
                return False
        if t.pos == "VERB":
            if not keys.issubset(VERBAL_ALLOWED):
                return False
            if t.tags.get("tense") == "COND" and t.tags.get("mood") == "SUBJ":
                return False
        if t.pos == "ADJ" and not keys.issubset(ADJ_ALLOWED):
            return False
        if "poss" in keys and t.pos not in ("NOUN", "UNKNOWN"):
            return False
    return True


def validate_sentence_structure_hu(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """Hungarian flexible word order (topic-focus-verb) validation."""
    content = [t for t in tokens if t.pos not in ("UNKNOWN", "PUNCT")]
    if not content:
        return True, "ok"
    NOMINAL_SLOT_ORDER = ["num", "poss", "case"]
    for t in content:
        if t.pos == "NOUN":
            present_slots = [s for s in NOMINAL_SLOT_ORDER if s in t.tags]
            if present_slots != sorted(
                present_slots,
                key=lambda s: NOMINAL_SLOT_ORDER.index(s)
            ):
                return False, f"nominal slot order violation: {t.surface}"
    return True, "ok"


def check_morph_sequence_de(tokens: List[TokenInfo]) -> bool:
    """Validate per-token tag bundles for German."""
    NOUN_ALLOWED = {"num", "gender", "case", "umlaut", "compound_parts",
                    "compound_head"}
    VERB_ALLOWED = {"tense", "mood", "person", "num", "aspect", "voice",
                    "verb_prefix", "mood_ambig", "ambig", "infinitive_marker"}
    ADJ_ALLOWED  = {"degree", "case", "gender", "num", "declension",
                    "umlaut", "adj_ambig"}
    ADV_ALLOWED  = {"degree", "subcat"}
    for t in tokens:
        keys = set(t.tags.keys())
        if t.pos == "NOUN":
            if not keys.issubset(NOUN_ALLOWED):
                return False
        if t.pos == "VERB":
            if not keys.issubset(VERB_ALLOWED):
                return False
            # Partizip needs aspect, conjugated needs tense or mood
            has_aspect = "aspect" in keys
            has_tense = "tense" in keys
            has_mood = "mood" in keys
            has_prefix = "verb_prefix" in keys
            if not (has_aspect or has_tense or has_mood or has_prefix):
                return False
        if t.pos == "ADJ" and not keys.issubset(ADJ_ALLOWED):
            return False
        if t.pos == "ADV" and not keys.issubset(ADV_ALLOWED):
            return False
    return True


def validate_sentence_structure_de(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """German SVO/V2 sentence structure validation."""
    content = [t for t in tokens if t.pos not in ("UNKNOWN", "PUNCT", "PART")]
    if not content:
        return True, "ok"

    # Degree tag on non-adjective/adverb
    for t in content:
        if t.tags.get("degree") in ("COMP", "SUPER") and t.pos not in ("ADJ", "ADV"):
            return False, f"degree tag on non-ADJ/ADV: {t.surface}"

    # PERF aspect should only be on VERB
    for t in content:
        if t.tags.get("aspect") == "PERF" and t.pos != "VERB":
            return False, f"PERF aspect on non-VERB: {t.surface}"

    return True, "ok"


def validate_sentence_structure_tr(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """Turkish SOV sentence structure validation."""
    content = [t for t in tokens if t.pos not in ("UNKNOWN", "FOREIGN", "PUNCT")]
    if not content:
        return True, "ok"
    for t in content:
        if t.pos == "VERB" and t.tags.get("mood") == "IMP":
            if t.tags.get("person") not in ("2", None):
                return False, f"imperative with non-2nd person: {t.surface}"
    for t in content:
        if t.pos == "VERB":
            if t.tags.get("tense") == "PAST_DEF" and "PAST_NARR" in str(t.derived_chain):
                return False, f"mixed evidentiality: {t.surface}"
    NOMINAL_SLOT_ORDER = ["NUM", "POSS", "CASE"]
    for t in content:
        if t.pos in ("NOUN", "ADJ"):
            present_slots = [s for s in NOMINAL_SLOT_ORDER if s in t.tags]
            if present_slots != sorted(present_slots,
                                       key=lambda s: NOMINAL_SLOT_ORDER.index(s)):
                return False, f"nominal slot order violation: {t.surface}"
    return True, "ok"


def check_morph_sequence_sw(tokens: List[TokenInfo]) -> bool:
    """Validate per-token tag bundles for Swahili."""
    _SG_CLASSES = {"1", "3", "5", "7", "9", "11", "14"}
    _PL_CLASSES = {"2", "4", "6", "8", "10"}
    NOUN_ALLOWED = {"nc", "num", "loc", "derived", "derived_from", "suffix",
                    "subcat", "gloss"}
    VERB_ALLOWED = {"person", "num", "tense", "aspect", "mood", "polarity",
                    "voice", "valence", "obj", "obj_nc", "rel", "rel_nc",
                    "subj_nc", "note", "subcat", "gloss",
                    "voice_2", "voice_3", "valence_2", "valence_3"}
    ADJ_ALLOWED = {"nc"}

    for t in tokens:
        keys = set(t.tags.keys())
        if t.pos == "VERB":
            if not keys.issubset(VERB_ALLOWED):
                return False
            has_subj = "person" in keys or "subj_nc" in keys
            has_tense = "tense" in keys or "aspect" in keys
            # Verbs should have subject agreement (except habitual hu-)
            if has_tense and not has_subj:
                if t.tags.get("tense") != "HAB":
                    return False
            # Imperative only for 2nd person
            if t.tags.get("mood") == "IMP":
                if t.tags.get("person") not in ("2", None):
                    return False
            # PASS and RECIP cannot co-occur
            if t.tags.get("voice") == "PASS":
                if any(t.tags.get(k) == "RECIP" for k in ("voice",)):
                    pass  # already checked
            if "PASS" in t.derived_chain and "RECIP" in t.derived_chain:
                return False
        if t.pos == "NOUN":
            if not keys.issubset(NOUN_ALLOWED):
                return False
            if keys & {"tense", "person", "mood"}:
                return False
            nc = t.tags.get("nc")
            num = t.tags.get("num")
            if nc and num:
                if nc in _SG_CLASSES and num != "SG":
                    return False
                if nc in _PL_CLASSES and num != "PL":
                    return False
        if t.pos == "ADJ":
            if not keys.issubset(ADJ_ALLOWED):
                return False
            if keys & {"tense", "person", "mood"}:
                return False
    return True


def validate_sentence_structure_sw(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """Swahili SVO sentence structure and noun class agreement validation."""
    content = [t for t in tokens if t.pos not in ("UNKNOWN", "PUNCT")]
    if not content:
        return True, "ok"

    # 1. Noun-adjective agreement: ADJ following NOUN must match nc
    for i in range(len(content) - 1):
        noun, adj = content[i], content[i + 1]
        if noun.pos == "NOUN" and adj.pos == "ADJ":
            noun_nc = noun.tags.get("nc")
            adj_nc = adj.tags.get("nc")
            if noun_nc and adj_nc and noun_nc != adj_nc:
                return (False,
                        f"noun-adjective class disagreement: "
                        f"{noun.surface} (nc={noun_nc}) / "
                        f"{adj.surface} (nc={adj_nc})")

    # 2. Noun-verb subject agreement: VERB following NOUN
    for i in range(len(content) - 1):
        noun, verb = content[i], content[i + 1]
        if noun.pos == "NOUN" and verb.pos == "VERB":
            noun_nc = noun.tags.get("nc")
            verb_nc = verb.tags.get("subj_nc")
            if noun_nc and verb_nc and noun_nc != verb_nc:
                return (False,
                        f"noun-verb subject class disagreement: "
                        f"{noun.surface} (nc={noun_nc}) / "
                        f"{verb.surface} (subj_nc={verb_nc})")

    # 3. Verb validity checks
    for t in content:
        if t.pos == "VERB":
            if t.tags.get("mood") == "IMP":
                if t.tags.get("person") not in ("2", None):
                    return False, f"imperative with non-2nd person: {t.surface}"

    return True, "ok"


# ══════════════════════════════════════════════════════════════════════════════
# BASQUE VALIDATORS
# ══════════════════════════════════════════════════════════════════════════════

def check_morph_sequence_eu(tokens: List[TokenInfo]) -> bool:
    """Validate per-token tag bundles for Basque."""
    AUX_ALLOWED = {"agr_obj", "agr_subj", "agr_iobj", "tense", "mood",
                   "polarity", "formality", "allocutive_gender"}
    VERB_ALLOWED = {"aspect", "tense", "mood", "polarity", "agr_obj",
                    "agr_subj", "formality"}
    NOUN_ALLOWED = {"case", "num", "def", "ambig_ak"}
    ADJ_ALLOWED = {"degree", "case", "num", "def"}
    for t in tokens:
        keys = set(t.tags.keys())
        if t.pos == "AUX":
            if not keys.issubset(AUX_ALLOWED):
                return False
            if "agr_obj" not in keys:
                return False
        if t.pos == "VERB" and not keys.issubset(VERB_ALLOWED):
            return False
        if t.pos == "NOUN" and not keys.issubset(NOUN_ALLOWED):
            return False
        if t.pos == "ADJ" and not keys.issubset(ADJ_ALLOWED):
            return False
    return True


def validate_sentence_structure_eu(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """Basque SOV sentence structure validation with ergativity checks."""
    content = [t for t in tokens if t.pos not in ("UNKNOWN", "PUNCT", "PART")]
    if not content:
        return True, "ok"

    # Check: if an ERG-marked noun is present, auxiliary should be transitive
    has_erg = any(
        t.pos == "NOUN" and t.tags.get("case") == "ERG"
        for t in content
    )
    aux_tokens = [t for t in content if t.pos == "AUX"]
    if has_erg and aux_tokens:
        for aux in aux_tokens:
            if "agr_subj" not in aux.tags:
                return (False,
                        f"ERG subject present but auxiliary lacks agr_subj: "
                        f"{aux.surface}")

    # Check: AUX must always have agr_obj
    for t in content:
        if t.pos == "AUX" and "agr_obj" not in t.tags:
            return False, f"auxiliary missing agr_obj: {t.surface}"

    return True, "ok"
