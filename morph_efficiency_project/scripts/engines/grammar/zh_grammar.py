"""
engines/grammar/zh_grammar.py
=============================
Mandarin Chinese sentence-level grammar layer.

Implements three responsibilities:

1. ``split_into_sentences``: split raw CJK text on Chinese and Latin sentence
   terminators, returning per-sentence character lists (one Han character per
   token, since Mandarin orthography has no word boundaries).
2. ``disambiguate_pos``: walk the token list, using neighbour context to fix
   POS for closed-class polysemy (只, 把, 得, 在, 了, 的, 给) that the engine's
   bigram ``_pick_reading`` cannot fully resolve from immediate neighbours
   alone.
3. ``validate_sentence``: run structural guards covering the nine accepted
   sentence templates (declarative SVO, topic-comment, Ba, Bei, existential,
   comparison, modal, interrogative, imperative).
"""

from typing import List, Tuple
from ..shared import TokenInfo
from .common import CJK_TERMINATORS, LATIN_TERMINATORS


# Surfaces whose POS depends on sentence-window context.
_POLYSEMOUS = {"只", "把", "得", "在", "了", "的", "给", "等", "为", "為"}

# Sentence-final modal / mood particles. Reason: 了/的/吗/呢/吧/啊/呀 in final
# position always re-tag as PART regardless of any earlier reading.
_FINAL_PARTS = {"吗", "呢", "吧", "啊", "呀", "了", "的"}

# Aspect particles that must immediately follow a verb.
_ASPECT_PARTS = {"着", "过", "了"}

# Negation adverbs.
_NEG_ADVERBS = {"不", "没", "没有", "别"}


def split_into_sentences(text: str) -> List[List[str]]:
    """Split raw text on CJK + Latin sentence terminators.

    Returns one list per sentence. Each sentence is a list of character tokens
    (Han characters one-per-token, ASCII whitespace dropped, terminator kept).
    """
    terminators = CJK_TERMINATORS | LATIN_TERMINATORS
    sentences: List[List[str]] = []
    current: List[str] = []
    for ch in text:
        if ch.isspace():
            continue
        current.append(ch)
        if ch in terminators:
            sentences.append(current)
            current = []
    if current:
        sentences.append(current)
    return sentences


# ── POS disambiguation ──────────────────────────────────────────────────────

def _retag(tok: TokenInfo, pos: str, tags: dict) -> None:
    """In-place re-tag preserving surface / root."""
    tok.pos = pos
    tok.tags = dict(tags)


def disambiguate_pos(tokens: List[TokenInfo]) -> List[TokenInfo]:
    """Second-pass disambiguation using full-sentence window context.

    Mandarin-specific rules. Walks twice: first pass anchors closed-class
    function words from their neighbours; second pass resolves remaining
    ambiguities once their context tokens have settled.
    """
    n = len(tokens)
    if n == 0:
        return tokens

    def pos_at(i: int) -> str:
        return tokens[i].pos if 0 <= i < n else ""

    def is_subject_like(i: int) -> bool:
        return pos_at(i) in {"PRON", "NOUN", "PROPN"}

    # Two passes to allow downstream context to settle.
    for _ in range(2):
        for i, tok in enumerate(tokens):
            s = tok.surface
            if s not in _POLYSEMOUS and s not in _FINAL_PARTS:
                continue
            prev_pos = pos_at(i - 1)
            next_pos = pos_at(i + 1)
            is_final = (i == n - 1) or pos_at(i + 1) == "PUNCT"

            if s == "只":
                # NUM ... NOUN window → CLF (一只猫). Subject + VERB → ADV.
                if prev_pos == "NUM" and next_pos in {"NOUN", "PROPN"}:
                    # Preserve any classifier-class already set by _pick_reading.
                    if tok.pos != "CLF":
                        _retag(tok, "CLF", {"classifier": "GENERIC"})
                elif is_subject_like(i - 1) and next_pos in {"VERB", "ADV", "AUX"}:
                    _retag(tok, "ADV", {"subcat": "RESTRICTIVE"})

            elif s == "把":
                # SUBJECT 把 OBJECT VERB → ADP/BA. NUM 把 NOUN → CLF (一把刀).
                if prev_pos == "NUM" and next_pos in {"NOUN", "PROPN"}:
                    if tok.pos != "CLF":
                        _retag(tok, "CLF", {"classifier": "GRASPABLE"})
                elif is_subject_like(i - 1) and next_pos in {"NOUN", "PROPN", "PRON", "DET"}:
                    _retag(tok, "ADP", {"construction": "BA"})

            elif s == "得":
                # VERB 得 ... → PART (de complement). Otherwise AUX (must).
                if prev_pos == "VERB":
                    _retag(tok, "PART", {"particle_type": "COMPLEMENT"})
                elif next_pos in {"VERB", "AUX"}:
                    _retag(tok, "AUX", {"modal": "NECESSITY"})

            elif s == "在":
                # 在 + VERB → ADV/PROG. 在 + NOUN → ADP/LOC.
                if next_pos in {"VERB", "AUX"}:
                    _retag(tok, "ADV", {"aspect": "PROG"})
                elif next_pos in {"NOUN", "PROPN", "PRON", "DET"}:
                    _retag(tok, "ADP", {"role": "LOC"})

            elif s == "了":
                # Sentence-final → modal PART. After VERB but not final → PERF.
                if is_final:
                    _retag(tok, "PART", {"particle_type": "MODAL"})
                elif prev_pos == "VERB":
                    _retag(tok, "PART", {"aspect": "PERF", "particle_type": "ASPECT"})

            elif s == "的":
                # Between NP and NOUN → DE possessive. Sentence-final → modal.
                if is_final:
                    _retag(tok, "PART", {"particle_type": "MODAL"})
                elif prev_pos in {"NOUN", "PROPN", "PRON", "ADJ"} and next_pos in {"NOUN", "PROPN"}:
                    _retag(tok, "PART", {"particle_type": "DE", "role": "POSSESSIVE"})

            elif s == "给":
                # SUBJECT 给 NP VERB → ADP (benefactive). VERB 给 NP → DAT marker.
                if prev_pos == "VERB":
                    _retag(tok, "ADP", {"role": "DATIVE"})
                elif is_subject_like(i - 1) and next_pos in {"NOUN", "PROPN", "PRON"}:
                    _retag(tok, "ADP", {"role": "BENEFACTIVE"})

            elif s == "等":
                # Enumeration particle ("X, Y 等" = "X, Y, etc."): closes a list
                # and therefore follows a common or proper noun (or a numeral).
                # The lexical verb 等 ("to wait") takes a subject pronoun, so the
                # PRON-subject case is left as the verb reading; after a true
                # noun the enumeration particle is the dominant reading.
                if prev_pos in {"NOUN", "PROPN", "NUM"}:
                    _retag(tok, "PART", {"particle_type": "ENUMERATION"})

            elif s in {"为", "為"}:
                # Coverb / preposition ("for, as, by") when it introduces a
                # nominal: SUBJECT 为 NP ... . Kept as the verb reading ("to be,
                # to act as") only when it is not introducing an NP object.
                if is_subject_like(i - 1) and next_pos in {"NOUN", "PROPN", "PRON", "DET"}:
                    _retag(tok, "ADP", {"role": "PURPOSE"})

    return tokens


# ── Sentence-structure validation ──────────────────────────────────────────

def _has_predicate(content: List[TokenInfo]) -> Tuple[bool, str]:
    if any(t.pos in {"VERB", "AUX"} for t in content):
        return True, ""
    if any(t.pos == "ADJ" for t in content):
        return True, ""
    return False, "句子缺少谓语"


def _svo_order(content: List[TokenInfo]) -> Tuple[bool, str]:
    # Skip when a special construction (BA / BEI) is present.
    if any(t.tags.get("construction") in {"BA", "BEI"} for t in content):
        return True, ""
    first_verb = next((i for i, t in enumerate(content) if t.pos == "VERB"), -1)
    if first_verb <= 0:
        return True, ""
    pre = content[:first_verb]
    # Imperative exemption: subject-drop is licensed when the preverbal field
    # is only negation / prohibitive (别, 不, 没) or modal auxiliaries.
    if all(t.pos in {"ADV", "AUX"} for t in pre):
        return True, ""
    if not any(t.pos in {"PRON", "NOUN", "PROPN"} for t in pre):
        return False, "主语应在动词之前"
    return True, ""


def _ba_requires_object(content: List[TokenInfo]) -> Tuple[bool, str]:
    for i, t in enumerate(content):
        if t.tags.get("construction") == "BA":
            tail = content[i + 1:]
            has_obj = any(c.pos in {"NOUN", "PROPN", "PRON"} for c in tail)
            has_verb = any(c.pos == "VERB" for c in tail)
            if not has_verb:
                return False, "把构式：把后需有宾语再接动词"
            if not has_obj:
                return False, "把构式：把后需有宾语再接动词"
            obj_idx = next(j for j, c in enumerate(tail) if c.pos in {"NOUN", "PROPN", "PRON"})
            verb_idx = next(j for j, c in enumerate(tail) if c.pos == "VERB")
            if obj_idx >= verb_idx:
                return False, "把构式：把后需有宾语再接动词"
    return True, ""


def _bei_requires_verb(content: List[TokenInfo]) -> Tuple[bool, str]:
    for i, t in enumerate(content):
        if t.tags.get("construction") == "BEI":
            if not any(c.pos == "VERB" for c in content[i + 1:]):
                return False, "被构式需有动词"
    return True, ""


def _classifier_between_num_and_noun(content: List[TokenInfo]) -> Tuple[bool, str]:
    for i, t in enumerate(content):
        if t.pos == "NUM" and i + 1 < len(content):
            nxt = content[i + 1]
            if nxt.pos in {"NOUN", "PROPN"}:
                return False, "数词和名词之间需要量词"
    return True, ""


def _modifier_precedes_head(content: List[TokenInfo]) -> Tuple[bool, str]:
    # DE-possessive particle should not be sentence-initial.
    for i, t in enumerate(content):
        if t.tags.get("particle_type") == "DE" and t.tags.get("role") == "POSSESSIVE":
            if i == 0 or i == len(content) - 1:
                return False, "修饰语在中心语之前"
    return True, ""


def _aspect_particle_attaches_to_verb(content: List[TokenInfo]) -> Tuple[bool, str]:
    for i, t in enumerate(content):
        if t.pos == "PART" and t.tags.get("particle_type") == "ASPECT":
            # Sentence-modal 了 is exempt (it's MODAL, not ASPECT, after disamb).
            if i == 0:
                return False, "体标记紧跟动词"
            prev = content[i - 1]
            if prev.pos != "VERB":
                return False, "体标记紧跟动词"
    return True, ""


def _sentence_final_particle_last(content: List[TokenInfo]) -> Tuple[bool, str]:
    for i, t in enumerate(content):
        if t.tags.get("particle_type") == "MODAL":
            if i != len(content) - 1:
                return False, "句末语气词位置错误"
    return True, ""


def _negation_position(content: List[TokenInfo]) -> Tuple[bool, str]:
    for i, t in enumerate(content):
        if t.pos == "ADV" and t.tags.get("negation") in {"BU", "MEI", "BIE"}:
            # Must precede something verbal (VERB/AUX/ADJ) somewhere ahead.
            tail = content[i + 1:]
            if not tail:
                return False, "不/没 应在动词前"
            if not any(c.pos in {"VERB", "AUX", "ADJ", "ADV"} for c in tail):
                return False, "不/没 应在动词前"
    return True, ""


_GUARDS = [
    # Specific construction checks first: they give targeted Chinese messages
    # (e.g. "把构式...") rather than the generic "missing predicate" fallback.
    _ba_requires_object,
    _bei_requires_verb,
    _has_predicate,
    _svo_order,
    _classifier_between_num_and_noun,
    _modifier_precedes_head,
    _aspect_particle_attaches_to_verb,
    _sentence_final_particle_last,
    _negation_position,
]


def validate_sentence(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """Run structural guards on the disambiguated token list.

    Returns (ok, message). Message is Chinese on failure, "ok" on success.
    """
    content = [t for t in tokens if t.pos not in {"UNKNOWN", "PUNCT"}]
    if not content:
        return True, "ok"
    for guard in _GUARDS:
        ok, msg = guard(content)
        if not ok:
            return False, msg
    return True, "ok"
