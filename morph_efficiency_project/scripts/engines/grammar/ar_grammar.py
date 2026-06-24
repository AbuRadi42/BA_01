"""
engines/grammar/ar_grammar.py
=============================
Arabic sentence-level grammar layer (النحو على مستوى الجملة).

Implements:
    - split_into_sentences: punctuation-based splitter (Latin + Arabic).
    - disambiguate_pos:    neighbour-context POS / case resolution using
                           نواسخ، أدوات تعريف، حروف عطف، أدوات شرط، أدوات استفهام.
    - validate_sentence:   structural guards covering الجملة الفعلية،
                           الجملة الاسمية، النواسخ، الإضافة، الصفة والموصوف،
                           الحال، والعطف.
"""

from typing import List, Tuple
from copy import deepcopy
from ..shared import TokenInfo
from .common import (
    LATIN_TERMINATORS,
    ARABIC_TERMINATORS,
    split_on_punctuation,
)


# ── Closed-class lexica (الحروف والأدوات) ──────────────────────────────────────

# الحروف الناسخة — assign ACC to following مبتدأ, NOM to خبر.
NASEKH_HARF = {"إنّ", "إن", "أنّ", "أن", "كأنّ", "لكنّ", "لكن", "ليت", "لعلّ"}

# الأفعال الناسخة — assign NOM to اسمها (the subject) and ACC to خبرها.
NASEKH_VERB = {"كان", "أصبح", "أمسى", "صار", "ليس", "ظلّ", "بات", "أضحى"}

# أدوات الاستفهام
INTERROG = {"هل", "أ", "ما", "من", "متى", "أين", "كيف", "لماذا", "كم"}

# أدوات الشرط
COND = {"إذا", "إن", "لو", "كلما", "متى"}

# أدوات النصب على الفعل المضارع
SUBJUNCTIVE = {"أن", "لن", "كي", "لكي", "حتى", "إذًا"}

# أدوات الجزم على الفعل المضارع
JUSSIVE = {"لم", "لما", "لا"}

# أدوات النفي
NEG = {"لا", "ما", "لم", "لن", "ليس"}

# حروف العطف
CONJ = {"و", "ف", "ثم", "أو", "بل", "لكن", "حتى"}

# أدوات التبعيض / الكلية — followed by مضاف إليه مجرور.
QUANT = {"كل", "بعض", "جميع", "كلا", "كلتا", "نصف", "ربع"}

# الضمائر المنفصلة — the independent personal pronouns. A closed class: these
# surfaces are pronouns, never verbs. The word-level analyzer mis-reads several
# of them (هو، هي، أنا …) as hollow past verbs, so the sentence layer anchors
# them back to PRON. This is a fact about the language, not a corpus fit.
PERSONAL_PRONOUNS = {
    "أنا", "نحن", "أنت", "أنتِ", "أنتما", "أنتم", "أنتنّ", "أنتن",
    "هو", "هي", "هما", "هم", "هنّ", "هن",
}


def _strip_diac(s: str) -> str:
    """Remove Arabic diacritics for matching closed-class tokens."""
    if not s:
        return s
    out = []
    for ch in s:
        # Arabic diacritics block: 0x064B..0x0652, and shadda/sukun/superscript alef.
        if 0x064B <= ord(ch) <= 0x0652 or ord(ch) in (0x0670, 0x0640):
            continue
        out.append(ch)
    return "".join(out)


def _strip_leading_clitic(s: str) -> str:
    """Drop a leading و / ف if present, for matching naked words."""
    if not s:
        return s
    if s[0] in ("و", "ف") and len(s) > 1:
        return s[1:]
    return s


# ── 1. Sentence splitter ───────────────────────────────────────────────────────

def split_into_sentences(text: str) -> List[List[str]]:
    """Split `text` into a list of sentences on Latin + Arabic terminators.

    Handles also embedded newlines by treating each line as already split.
    """
    terminators = LATIN_TERMINATORS | ARABIC_TERMINATORS
    sentences: List[List[str]] = []
    for line in text.splitlines() if text else []:
        line = line.strip()
        if not line:
            continue
        sentences.extend(split_on_punctuation(line, terminators))
    if not sentences and text:
        sentences = split_on_punctuation(text, terminators)
    return sentences


# ── 2. Context-aware POS disambiguation ───────────────────────────────────────

def disambiguate_pos(tokens: List[TokenInfo]) -> List[TokenInfo]:
    """Walk the sentence and refine POS / case / role using neighbour context.

    Mutates a deep copy and returns it so caller's tokens are untouched.
    """
    if not tokens:
        return tokens

    out = [deepcopy(t) for t in tokens]

    # Helper: bare form (no diacritics, no leading و/ف) for closed-class match.
    def bare(tok: TokenInfo) -> str:
        return _strip_leading_clitic(_strip_diac(tok.surface))

    n = len(out)
    for i, tok in enumerate(out):
        surf_bare = bare(tok)
        prev = out[i - 1] if i > 0 else None
        prev_bare = bare(prev) if prev is not None else ""

        # Mark sentence opener if first content position OR preceded by و/ف/ث.
        is_opener = (i == 0) or (prev_bare in CONJ)

        # Rule 0: independent personal pronoun → PRON (closed class). Overrides
        # the analyzer's spurious hollow-verb reading of هو/هي/أنا/…
        if _strip_diac(surf_bare) in {_strip_diac(p) for p in PERSONAL_PRONOUNS}:
            tok.pos = "PRON"
            for k in ("tense", "voice", "person", "form", "imperf",
                      "semantic_role"):
                tok.tags.pop(k, None)
            continue

        # Rule A: ال + ... → DEF NOM/ADJ; never VERB.
        if tok.surface.startswith("ال") or tok.surface.startswith("الْ"):
            if tok.pos == "VERB":
                tok.pos = "NOM"
                tok.tags.pop("tense", None)
                tok.tags.pop("voice", None)
                tok.tags.pop("person", None)
                tok.tags.pop("imperf", None)
            tok.tags["def"] = "DEF"

        # Rule B: تنوين on end (ـٌ/ـٍ/ـً) → INDF NOM.
        if tok.surface and tok.surface[-1] in ("ٌ", "ٍ", "ً"):
            if tok.pos in ("NOM", "ADJ") or tok.pos == "VERB":
                if tok.pos == "VERB":
                    # Tanwin disambiguates against verb: it's a nominal.
                    tok.pos = "NOM"
                    tok.tags.pop("tense", None)
                    tok.tags.pop("voice", None)
                    tok.tags.pop("person", None)
                tok.tags.setdefault("def", "INDF")
                if tok.surface[-1] == "ٌ":
                    tok.tags["case"] = "NOM"
                elif tok.surface[-1] == "ٍ":
                    tok.tags["case"] = "GEN"
                elif tok.surface[-1] == "ً":
                    tok.tags["case"] = "ACC"

        # Rule C: ال + ـة-final → DEF F NOM (resolve verb misanalysis).
        if (tok.surface.startswith("ال") or tok.surface.startswith("الْ")) and \
           (tok.surface.endswith("ة") or tok.surface.endswith("ةُ") or
            tok.surface.endswith("ةَ") or tok.surface.endswith("ةِ")):
            tok.pos = "NOM"
            tok.tags["def"] = "DEF"
            tok.tags["gender"] = "F"
            tok.tags.setdefault("num", "SG")

        # Rule D: sentence opener → if VERB-likely keep VERB; otherwise we keep
        # whatever the analyzer said. We *do* annotate opener position via
        # an internal tag for the validator to inspect.
        if is_opener:
            tok.tags.setdefault("_position", "opener")

        # Rule E: after حرف ناسخ (إنّ/أنّ/…) → next NOM is مبتدأ منصوب (ACC).
        if prev is not None and bare(prev) in NASEKH_HARF:
            if tok.pos == "NOM":
                tok.tags["case"] = "ACC"
                tok.tags["role"] = "MUBTADA"

        # Rule F: after فعل ناسخ (كان/أصبح/…) → اسمها NOM; the FOLLOWING NOM is خبر منصوب.
        if prev is not None and bare(prev) in NASEKH_VERB:
            if tok.pos == "NOM":
                tok.tags["case"] = "NOM"
                tok.tags["role"] = "ISM_NASEKH"
        if i >= 2 and bare(out[i - 2]) in NASEKH_VERB and tok.pos == "NOM":
            # second NOM after a كان-class verb is خبر in accusative
            if out[i - 1].pos == "NOM":
                tok.tags["case"] = "ACC"
                tok.tags["role"] = "KHABAR"

        # Rule G: after كل/بعض/جميع → next definite NOM is مضاف إليه مجرور.
        if prev is not None and bare(prev) in QUANT and tok.pos == "NOM":
            tok.tags["case"] = "GEN"
            tok.tags["role"] = "MUDAF_ILAYH"

        # Rule H: after subordinator (أن/لن/كي/حتى/لكي) → next VERB is مضارع منصوب.
        if prev is not None and bare(prev) in SUBJUNCTIVE and tok.pos == "VERB":
            tok.tags["mood"] = "SUBJ"
            tok.tags.setdefault("tense", "PRES")

        # Rule I: after لم/لما → next VERB is مضارع مجزوم.
        if prev is not None and bare(prev) in JUSSIVE and tok.pos == "VERB":
            tok.tags["mood"] = "JUS"
            tok.tags["tense"] = "PRES"

        # Rule J: AGENT NOM right after VERB in verbal sentence → فاعل مرفوع.
        if prev is not None and prev.pos == "VERB" and tok.pos == "NOM":
            if tok.tags.get("role") not in ("MUBTADA", "KHABAR", "ISM_NASEKH"):
                tok.tags.setdefault("role", "FAIL")  # الفاعل
                tok.tags.setdefault("case", "NOM")

        # Rule K: NOM after another NOM, both DEF, in NOMINAL sentence (no verb
        # earlier in the sentence) → second is صفة (adjective) if it agrees in
        # gender/number. We skip in verbal sentences because the second NOM
        # there is usually المفعول به, not a صفة.
        if (prev is not None and prev.pos == "NOM" and tok.pos == "NOM"
                and prev.tags.get("def") == "DEF" and tok.tags.get("def") == "DEF"):
            earlier_has_verb = any(x.pos == "VERB" for x in out[:i])
            if (not earlier_has_verb
                    and prev.tags.get("gender") == tok.tags.get("gender")
                    and prev.tags.get("num") == tok.tags.get("num")):
                tok.pos = "ADJ"
                tok.tags["role"] = "SIFAH"

        # Rule L: حال — indefinite + ACC, immediately after a complete VSO core.
        if tok.tags.get("def") == "INDF" and tok.tags.get("case") == "ACC":
            tok.tags.setdefault("role", "HAL")

    return out


# ── 3. Sentence-structure validation guards ───────────────────────────────────

def _content_tokens(tokens: List[TokenInfo]) -> List[TokenInfo]:
    return [t for t in tokens
            if t.pos not in ("PART", "FOREIGN", "PROPER", "UNKNOWN")]


def has_predicate(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """Every sentence must have a predicate (خبر in الاسمية، فعل in الفعلية)."""
    content = _content_tokens(tokens)
    if not content:
        return True, "ok"
    if any(t.pos == "VERB" for t in content):
        return True, "ok"
    if len(content) >= 2:
        return True, "ok"
    return False, "الجملة بلا خبر"


def verbal_sentence_VSO_order(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """If sentence opens with VERB, it must be followed by a فاعل (NOM/PROPER)."""
    content = _content_tokens(tokens)
    if not content:
        return True, "ok"
    # find first content position
    first = content[0]
    if first.pos != "VERB":
        return True, "ok"
    # second content token must be NOM (الفاعل) — propers/pronouns also OK.
    all_content = [t for t in tokens
                   if t.pos not in ("PART", "FOREIGN", "UNKNOWN")]
    if len(all_content) < 2:
        return True, "ok"  # one-word verbal sentence (subject pronoun implicit)
    nxt = all_content[1]
    if nxt.pos not in ("NOM", "PROPER", "PRON"):
        return False, "الفعل يطلب فاعلًا يليه"
    return True, "ok"


def nominal_sentence_subject_nominative(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """If the sentence is nominal (opens with NOM, no نواسخ), المبتدأ must be NOM."""
    content = _content_tokens(tokens)
    if not content:
        return True, "ok"
    # Skip if any leading particle is a naasekh.
    leading_particles = []
    for t in tokens:
        if t.pos in ("NOM", "VERB"):
            break
        leading_particles.append(_strip_leading_clitic(_strip_diac(t.surface)))
    if any(p in NASEKH_HARF for p in leading_particles):
        return True, "ok"  # handled by nasekh_case_assignment
    first = content[0]
    if first.pos != "NOM":
        return True, "ok"
    case = first.tags.get("case")
    if case is not None and case != "NOM":
        return False, "المبتدأ مرفوع"
    return True, "ok"


def nasekh_case_assignment(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """Validate إنّ/كان-class case assignment."""
    for i, t in enumerate(tokens):
        bare = _strip_leading_clitic(_strip_diac(t.surface))
        # Look for an immediate nominal target.
        if bare in NASEKH_HARF:
            # Next NOM must be ACC.
            for nxt in tokens[i + 1:]:
                if nxt.pos == "NOM":
                    if nxt.tags.get("case") not in ("ACC", None):
                        return False, "إنّ تنصب المبتدأ"
                    break
        if bare in NASEKH_VERB:
            noms = [x for x in tokens[i + 1:] if x.pos == "NOM"]
            if len(noms) >= 1:
                if noms[0].tags.get("case") not in ("NOM", None):
                    return False, "كان ترفع الاسم"
            if len(noms) >= 2:
                if noms[1].tags.get("case") not in ("ACC", None):
                    return False, "كان تنصب الخبر"
    return True, "ok"


def idafa_construction(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """المضاف نكرة (no ال, no تنوين); المضاف إليه معرفة مجرور."""
    for i in range(len(tokens) - 1):
        a, b = tokens[i], tokens[i + 1]
        # Detect potential إضافة: NOM-NOM where first is bare (no ال, no tanwin)
        # and second is DEF.
        if a.pos == "NOM" and b.pos == "NOM":
            a_def = a.tags.get("def")
            if a_def == "DEF":
                continue  # the first is definite → not مضاف
            if a.surface and a.surface[-1] in ("ٌ", "ٍ", "ً"):
                continue  # tanwin → not مضاف
            if b.tags.get("def") == "DEF":
                # this looks like إضافة; second should be GEN if case marked.
                b_case = b.tags.get("case")
                if b_case is not None and b_case != "GEN":
                    # Tolerate; but if a quantifier triggered it, must be GEN.
                    prev = tokens[i - 1] if i > 0 else None
                    if prev is not None and _strip_leading_clitic(
                            _strip_diac(prev.surface)) in QUANT:
                        return False, "المضاف إليه مجرور"
    return True, "ok"


def adjective_agreement(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """الصفة تتبع الموصوف في التذكير/التأنيث/العدد/التعريف/الإعراب."""
    for i in range(1, len(tokens)):
        t = tokens[i]
        if t.tags.get("role") != "SIFAH":
            continue
        prev = tokens[i - 1]
        if prev.tags.get("gender") and t.tags.get("gender") \
                and prev.tags.get("gender") != t.tags.get("gender"):
            return False, "الصفة تتبع الموصوف"
        if prev.tags.get("num") and t.tags.get("num") \
                and prev.tags.get("num") != t.tags.get("num"):
            return False, "الصفة تتبع الموصوف"
        if prev.tags.get("def") and t.tags.get("def") \
                and prev.tags.get("def") != t.tags.get("def"):
            return False, "الصفة تتبع الموصوف"
    return True, "ok"


def hal_clause_indf_acc(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """الحال نكرة منصوبة — when role=HAL, must be INDF + ACC."""
    for t in tokens:
        if t.tags.get("role") != "HAL":
            continue
        if t.tags.get("def") and t.tags["def"] != "INDF":
            return False, "الحال نكرة منصوبة"
        if t.tags.get("case") and t.tags["case"] != "ACC":
            return False, "الحال نكرة منصوبة"
    return True, "ok"


def conjunction_balanced(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """المعطوف والمعطوف عليه نفس الإعراب — when ثم/أو/بل sits between two NOMs,
    they must share case if both are case-marked.
    """
    for i in range(1, len(tokens) - 1):
        bare = _strip_leading_clitic(_strip_diac(tokens[i].surface))
        if bare not in {"ثم", "أو", "بل"}:
            continue
        prev = tokens[i - 1]
        nxt = tokens[i + 1]
        if prev.pos == "NOM" and nxt.pos == "NOM":
            pc, nc = prev.tags.get("case"), nxt.tags.get("case")
            if pc and nc and pc != nc:
                return False, "المعطوف والمعطوف عليه نفس الإعراب"
    return True, "ok"


GUARDS = [
    has_predicate,
    verbal_sentence_VSO_order,
    nominal_sentence_subject_nominative,
    nasekh_case_assignment,
    idafa_construction,
    adjective_agreement,
    hal_clause_indf_acc,
    conjunction_balanced,
]


def validate_sentence(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """Run all guards; return first failure or (True, 'ok')."""
    if not tokens:
        return True, "ok"
    for guard in GUARDS:
        ok, msg = guard(tokens)
        if not ok:
            return False, msg
    return True, "ok"
