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
            # Diptotes, masdars, and broken plurals are honestly num/gender underspecified in MSA.
            nom_role = t.tags.get("role")
            exempt_roles = {"MASDAR", "VERBAL_NOUN", "PLURAL", "PROPER"}
            is_exempt = nom_role in exempt_roles or t.tags.get("diptote") == "YES"
            if not is_exempt:
                if "num" not in keys and "gender" not in keys:
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
    """Thin wrapper delegating to engines.grammar.en_grammar.validate_sentence.

    Kept for backwards compatibility with code (and tests) that import from
    shared.py directly. The real implementation lives in the grammar module.
    """
    from .grammar.en_grammar import validate_sentence
    return validate_sentence(tokens)

def validate_sentence_structure_ar(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """Thin wrapper kept for backward compatibility.

    The authoritative Arabic sentence-level validator now lives in
    ``engines.grammar.ar_grammar.validate_sentence`` (covers الجملة الفعلية،
    الجملة الاسمية، النواسخ، الإضافة، الصفة، الحال، والعطف). This wrapper
    retains the legacy checks (tense/person on verbal opener, nominative on
    nominal subject, jussive-mood constraints, dual case) used by the older
    sentence test suite.
    """
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
        # Skip the nominative-subject check if the sentence is opened by a
        # حرف ناسخ (إنّ-class), since these assign ACC to the مبتدأ. The
        # grammar-layer guard `nasekh_case_assignment` handles that case.
        _NASEKH_HARF = {"إنّ", "إن", "أنّ", "أن", "كأنّ", "لكنّ", "لكن", "ليت", "لعلّ"}
        leading_naasekh = False
        for t in tokens:
            if t is first:
                break
            surf = t.surface or ""
            # strip diacritics for matching
            naked = "".join(c for c in surf if not (0x064B <= ord(c) <= 0x0652
                                                   or ord(c) in (0x0670, 0x0640)))
            if naked in _NASEKH_HARF:
                leading_naasekh = True
                break
        if not leading_naasekh and first.tags.get("case") not in ("NOM", None):
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
    # Radical-class tags can attach to any Han character regardless of POS, so
    # they are universally allowed across the POS-specific whitelists below.
    RADICAL_TAGS  = {"radical", "radical_class", "kangxi_index"}
    NOUN_ALLOWED  = {"num"} | RADICAL_TAGS
    VERB_ALLOWED  = {"aspect", "role"} | RADICAL_TAGS
    ADV_ALLOWED   = {"negation", "degree", "aspect", "subcat"} | RADICAL_TAGS
    PRON_ALLOWED  = {"person", "num", "gender", "deixis", "interrog", "reflex",
                     "register", "subcat"} | RADICAL_TAGS
    PART_ALLOWED  = {"aspect", "role", "particle_type"} | RADICAL_TAGS
    ADP_ALLOWED   = {"construction", "voice", "role", "subcat"} | RADICAL_TAGS
    CLF_ALLOWED   = {"classifier"} | RADICAL_TAGS
    AUX_ALLOWED   = {"modal"} | RADICAL_TAGS
    NUM_ALLOWED   = {"role"} | RADICAL_TAGS
    DET_ALLOWED   = {"subcat", "interrog", "num"} | RADICAL_TAGS
    CONJ_ALLOWED  = {"subcat"} | RADICAL_TAGS
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
    """Thin wrapper: delegate to grammar.zh_grammar.validate_sentence.

    Kept for backward compatibility with callers that import the validator
    directly from shared. New code should use ``zh_grammar.validate_sentence``.
    """
    from .grammar import zh_grammar
    return zh_grammar.validate_sentence(tokens)


def validate_sentence_structure_tr(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """Thin wrapper around engines.grammar.tr_grammar.validate_sentence.

    The full sentence-structure logic now lives in the grammar layer.
    """
    try:
        from .grammar.tr_grammar import validate_sentence as _tr_validate
        return _tr_validate(tokens)
    except Exception:
        return True, "ok"
