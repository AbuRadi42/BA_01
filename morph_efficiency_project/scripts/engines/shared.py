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
    NOUN_ALLOWED = {"num", "poss"}
    VERB_ALLOWED = {"tense", "aspect", "person", "voice"}
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
