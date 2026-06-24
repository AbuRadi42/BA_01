"""
engines/grammar/en_grammar.py
=============================
English sentence-level grammar layer.

Implements:
  * split_into_sentences: terminator-aware splitter respecting common
    abbreviations.
  * disambiguate_pos: two-pass context-aware POS resolver for ambiguous
    English forms (runs, running, to, that, this, before, after, etc.).
  * validate_sentence: structural validator with top-level helper guards
    for each sentence type (declarative, interrogative, imperative,
    exclamative).
"""

from typing import List, Tuple
import re

from ..shared import TokenInfo
from .common import COMMON_ABBREVIATIONS, LATIN_TERMINATORS


# ----------------------------------------------------------------------------
# 1) Sentence segmentation
# ----------------------------------------------------------------------------

_TERMINATORS = set(".!?;")
_WORD_RE = re.compile(r"\S+")


def split_into_sentences(text: str) -> List[List[str]]:
    """Split `text` into sentences and return a list of token lists.

    Splits on . ! ? ; and on hard newlines. Tokens listed in
    COMMON_ABBREVIATIONS (e.g. "Dr.", "U.S.A.") are not treated as
    sentence-final. A trailing terminator becomes its own token so word-level
    analyzers can ignore punctuation easily.
    """
    if not text or not text.strip():
        return []

    # Normalize newlines as hard sentence breaks.
    paragraphs = re.split(r"\n+", text)
    sentences: List[List[str]] = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        raw_tokens = _WORD_RE.findall(para)
        current: List[str] = []
        for tok in raw_tokens:
            # Abbreviation: keep token glued, do not split.
            if tok in COMMON_ABBREVIATIONS:
                current.append(tok)
                continue

            # Strip trailing terminators (one or more) into a separate marker.
            stripped = tok
            trailing = ""
            while stripped and stripped[-1] in _TERMINATORS:
                trailing = stripped[-1] + trailing
                stripped = stripped[:-1]

            if not trailing:
                current.append(tok)
                continue

            # Re-check: stripped + trailing[0] may form a known abbreviation
            # like "Mr." even when not the literal token (rare; safe-guard).
            candidate = stripped + trailing[0] if trailing else stripped
            if candidate in COMMON_ABBREVIATIONS:
                current.append(candidate)
                # Any remaining terminators are real sentence boundaries.
                if len(trailing) > 1:
                    current.append(trailing[1:])
                    sentences.append(current)
                    current = []
                continue

            if stripped:
                current.append(stripped)
            current.append(trailing)
            sentences.append(current)
            current = []

        if current:
            sentences.append(current)

    return sentences


# ----------------------------------------------------------------------------
# 2) Context-aware POS disambiguation
# ----------------------------------------------------------------------------

_VERB_BASE_FORMS = {
    "run", "walk", "eat", "play", "talk", "work", "move", "look", "think",
    "know", "want", "need", "feel", "seem", "come", "go", "take", "make",
    "give", "find", "tell", "ask", "use", "try", "leave", "call", "keep",
    "let", "begin", "show", "hear", "turn", "start", "stand", "lose", "pay",
    "meet", "bring", "hold", "write", "sit", "speak", "read", "grow", "lead",
    "live", "believe", "happen", "provide", "include", "continue", "set",
    "learn", "change", "follow", "stop", "create", "open", "fall", "win",
    "offer", "remember", "love", "consider", "appear", "buy", "wait", "serve",
    "die", "send", "expect", "build", "stay", "cut", "reach", "remain",
    "suggest", "raise", "pass", "sell", "require", "report", "decide", "pull",
    "develop", "break", "receive", "agree", "support", "hit", "produce",
    "cover", "catch", "draw", "choose", "sing", "swim", "drink", "drive",
    "ride", "fly", "fight", "wear", "throw", "teach", "cost", "help", "like",
    "mean", "add", "watch", "be", "have", "do", "get", "say",
}

_BE_FORMS  = {"be", "am", "is", "are", "was", "were", "been", "being"}
_HAVE_FORMS = {"have", "has", "had", "having"}
_DO_FORMS  = {"do", "does", "did", "doing", "done"}
_MODALS    = {"can", "could", "will", "would", "shall", "should",
              "may", "might", "must", "ought"}

_DETERMINERS_LIKE = {"the", "a", "an", "this", "that", "these", "those",
                     "my", "your", "his", "her", "its", "our", "their",
                     "some", "any", "no", "every", "each", "all", "both"}

_SUBJECT_PRONOUNS = {"i", "you", "he", "she", "it", "we", "they",
                     "who", "what", "which"}
_OBJECT_PRONOUNS  = {"me", "him", "her", "us", "them", "whom"}
_ALL_PRONOUNS = _SUBJECT_PRONOUNS | _OBJECT_PRONOUNS | {
    "myself", "yourself", "himself", "herself", "itself",
    "ourselves", "yourselves", "themselves",
}

_WH_WORDS = {"who", "what", "where", "when", "why", "how", "which", "whose"}


def _surface(tok: TokenInfo) -> str:
    return tok.surface.lower() if tok and tok.surface else ""


def _is_terminator_token(s: str) -> bool:
    return bool(s) and all(c in ".!?;," for c in s)


def _is_clause_terminator(tok: TokenInfo) -> bool:
    return _is_terminator_token(_surface(tok))


def _looks_like_noun(tok: TokenInfo) -> bool:
    if not tok:
        return False
    return tok.pos in {"NOUN", "PRON"} or _surface(tok) in _ALL_PRONOUNS


def _looks_like_np_start(tok: TokenInfo) -> bool:
    if not tok:
        return False
    s = _surface(tok)
    if s in _DETERMINERS_LIKE or s in _ALL_PRONOUNS:
        return True
    return tok.pos in {"NOUN", "PRON", "DET", "ADJ"}


def _looks_like_clause_start(tok: TokenInfo, nxt: TokenInfo) -> bool:
    """Heuristic: a finite SVO clause starts with NP then VERB."""
    if tok is None:
        return False
    if _surface(tok) in _SUBJECT_PRONOUNS:
        return True
    if tok.pos in {"NOUN", "PRON"} and nxt is not None and nxt.pos == "VERB":
        return True
    return False


def disambiguate_pos(tokens: List[TokenInfo]) -> List[TokenInfo]:
    """Two-pass context-aware POS resolver.

    Pass 1 anchors unambiguous tokens (already done by analyze()); pass 2
    inspects neighbours and rewrites ambiguous surface forms.
    """
    if not tokens:
        return tokens

    n = len(tokens)

    def prev(i: int) -> TokenInfo:
        return tokens[i - 1] if i - 1 >= 0 else None

    def nxt(i: int) -> TokenInfo:
        return tokens[i + 1] if i + 1 < n else None

    # Pass 2: resolve known ambiguities.
    for i, tok in enumerate(tokens):
        s = _surface(tok)
        p = prev(i)
        nx = nxt(i)

        # ---- "runs" : NOUN-PL vs VERB 3SG --------------------------------
        if s == "runs":
            # NOUN if preceded by DET/ADJ/NOUN-poss/numeral
            if p is not None and (
                _surface(p) in _DETERMINERS_LIKE
                or p.pos in {"DET", "ADJ"}
                or p.tags.get("poss") == "YES"
                or (_surface(p).isdigit() or _surface(p) in {"five", "two",
                                                              "three", "four",
                                                              "many", "few"})
            ):
                tok.pos = "NOUN"
                tok.tags = {"num": "PL"}
                tok.root = "run"
                continue
            # VERB if preceded by subject pronoun / proper-noun-like subject
            if p is not None and (
                _surface(p) in _SUBJECT_PRONOUNS or p.pos in {"NOUN", "PRON"}
            ):
                tok.pos = "VERB"
                tok.tags = {"tense": "PRES", "person": "3SG"}
                tok.root = "run"
                continue

        # ---- "running" : PROG VERB vs GERUND-NOUN -----------------------
        if s == "running":
            if p is not None and _surface(p) in (_BE_FORMS | {"keep", "kept",
                                                               "keeps",
                                                               "keeping"}):
                tok.pos = "VERB"
                tok.tags = {"tense": "PRES", "aspect": "PROG"}
                tok.root = "run"
                continue
            # gerund: clause subject (sentence-initial, followed by verb)
            if i == 0 and nx is not None and nx.pos in {"VERB", "AUX"}:
                tok.pos = "NOUN"
                tok.tags = {}
                tok.root = "run"
                continue

        # ---- "to" : infinitive marker vs preposition --------------------
        if s == "to":
            # Infinitive marker when the next token is a verb: either a known
            # base form, or anything the analyzer already tagged VERB (covers
            # lower-frequency verbs like "describe", "simulate", "oppose" that
            # are not in the base-form list). An NP after "to" keeps it a
            # preposition. The infinitive test is checked first because a verb
            # following "to" is the decisive cue.
            if nx is not None and (
                _surface(nx) in _VERB_BASE_FORMS or nx.pos == "VERB"
            ):
                tok.pos = "PART"
                tok.tags = {"subcat": "INF"}
                continue
            if nx is not None and (
                _surface(nx) in _ALL_PRONOUNS
                or _surface(nx) in _DETERMINERS_LIKE
                or nx.pos in {"NOUN", "PRON", "DET"}
            ):
                tok.pos = "PREP"
                tok.tags = {}
                continue

        # ---- "that" : DET vs COMPLEMENTIZER vs PRON ---------------------
        if s == "that":
            if p is not None and p.pos == "VERB":
                tok.pos = "CONJ"
                tok.tags = {"subcat": "COMP"}
                continue
            if nx is not None and nx.pos in {"NOUN", "UNKNOWN", "ADJ"}:
                tok.pos = "DET"
                tok.tags = {}
                continue

        # ---- "this/these/those" : DET vs PRON ---------------------------
        if s in {"this", "these", "those"}:
            if nx is not None and nx.pos in {"NOUN", "ADJ", "UNKNOWN"}:
                tok.pos = "DET"
                tok.tags = {}
            else:
                tok.pos = "PRON"

        # ---- "before/after" : PREP vs SUBORDINATOR ----------------------
        if s in {"before", "after"}:
            # Subordinator if followed by an SVO clause (NP + VERB)
            if nx is not None and _looks_like_clause_start(nx, tokens[i + 2]
                                                            if i + 2 < n
                                                            else None):
                tok.pos = "CONJ"
                tok.tags = {"subcat": "SUB"}
            elif nx is not None and _looks_like_np_start(nx):
                tok.pos = "PREP"
                tok.tags = {}

        # ---- VERB vs NOUN inside a noun phrase --------------------------
        # Many English forms are noun/verb homographs ("state", "love",
        # "power", "form", "interest", "thought"). The word-level analyzer
        # defaults several of these to VERB. When such a token sits in a
        # nominal slot, i.e. it is introduced by a determiner, a possessive,
        # or an adjective, the finite-verb reading is impossible: a determiner
        # or attributive adjective cannot be immediately followed by a tensed
        # verb, so the token heads a noun phrase and must be a NOUN. The -ing
        # case is excluded so genuine gerund/progressive forms are untouched.
        if tok.pos == "VERB" and not s.endswith("ing") \
                and not tok.tags.get("aspect") == "PROG":
            p_det = p is not None and (
                _surface(p) in _DETERMINERS_LIKE
                or p.pos in {"DET", "ADJ"}
                or p.tags.get("poss") == "YES"
            )
            if p_det:
                tok.pos = "NOUN"
                tok.tags = {}

        # ---- comparative -er vs agent -er : "than" clinches comparative -
        if tok.pos == "NOUN" and _surface(tok).endswith("er"):
            if nx is not None and _surface(nx) == "than":
                tok.pos = "ADJ"
                tok.tags = {"degree": "COMP"}
                # leave root as-is (analyzer already stripped)

        # ---- "more/less" before ADJ/ADV: keep as ADJ but mark COMP ------
        if s in {"more", "less"} and nx is not None and nx.pos in {"ADJ",
                                                                    "ADV"}:
            tok.pos = "ADV"
            tok.tags = {"degree": "COMP"}
        # "more X than" -- comparative quantifier reading
        elif s in {"more", "less"} and any(
            _surface(tokens[k]) == "than" for k in range(i + 1, min(n, i + 4))
        ):
            tok.pos = "ADV"
            tok.tags = {"degree": "COMP"}

    return tokens


# ----------------------------------------------------------------------------
# 3) Sentence-structure validation
# ----------------------------------------------------------------------------

_CONTENT_SKIP = {"FOREIGN", "PUNCT"}


def _content(tokens: List[TokenInfo]) -> List[TokenInfo]:
    out = []
    for t in tokens:
        if t.pos in _CONTENT_SKIP:
            continue
        if _is_clause_terminator(t):
            continue
        out.append(t)
    return out


def _is_main_verb(t: TokenInfo) -> bool:
    return t.pos == "VERB"


def _is_copula(t: TokenInfo) -> bool:
    return _surface(t) in _BE_FORMS


def _is_aux(t: TokenInfo) -> bool:
    s = _surface(t)
    return (t.pos == "AUX"
            or s in _BE_FORMS or s in _HAVE_FORMS or s in _DO_FORMS
            or s in _MODALS)


def has_main_verb_or_copula(content: List[TokenInfo]) -> Tuple[bool, str]:
    for t in content:
        if _is_main_verb(t) or _is_copula(t) or _is_aux(t):
            return True, "ok"
    return False, "no main verb or copula"


def subject_precedes_main_verb(content: List[TokenInfo]) -> Tuple[bool, str]:
    """For declaratives: a subject NP/PRON (or DET+head) must precede the
    first main verb. UNKNOWN tokens count as candidate NP heads because the
    word analyzer leaves many common nouns unclassified."""
    subj_idx = -1
    verb_idx = -1
    for i, t in enumerate(content):
        if subj_idx < 0 and (t.pos in {"NOUN", "PRON", "DET", "UNKNOWN"}
                              or _surface(t) in _SUBJECT_PRONOUNS):
            subj_idx = i
        if verb_idx < 0 and _is_main_verb(t):
            verb_idx = i
    if verb_idx < 0:
        return True, "ok"
    if subj_idx < 0:
        return False, "missing subject before main verb"
    if subj_idx > verb_idx:
        return False, "subject does not precede main verb"
    return True, "ok"


def aux_or_wh_fronted(content: List[TokenInfo]) -> Tuple[bool, str]:
    """Interrogative: starts with AUX or wh-word."""
    if not content:
        return True, "ok"
    first = content[0]
    if _is_aux(first) or _surface(first) in _WH_WORDS:
        return True, "ok"
    return False, "interrogative requires aux- or wh-fronting"


def determiner_precedes_noun(content: List[TokenInfo]) -> Tuple[bool, str]:
    """If a DET appears, the next non-ADJ token must look like an NP head.

    UNKNOWN is permitted because the morphology analyzer leaves many common
    nouns unclassified; treating them as NP heads keeps the validator from
    over-rejecting otherwise well-formed sentences.
    """
    for i, t in enumerate(content):
        if t.pos != "DET":
            continue
        j = i + 1
        while j < len(content) and content[j].pos == "ADJ":
            j += 1
        if j >= len(content):
            return False, f"determiner '{t.surface}' without noun"
        if content[j].pos not in {"NOUN", "PRON", "UNKNOWN"}:
            return False, (f"determiner '{t.surface}' not followed by noun: "
                           f"{content[j].surface}")
    return True, "ok"


def preposition_precedes_np(content: List[TokenInfo]) -> Tuple[bool, str]:
    """Each PREP must be followed eventually by an NP head."""
    for i, t in enumerate(content):
        if t.pos != "PREP":
            continue
        if i + 1 >= len(content):
            return False, f"preposition '{t.surface}' without object"
        # Look ahead for a noun/pronoun head, allowing DETs and ADJs between.
        j = i + 1
        found = False
        while j < len(content):
            nxt = content[j]
            if nxt.pos in {"NOUN", "PRON"}:
                found = True
                break
            if nxt.pos in {"DET", "ADJ"}:
                j += 1
                continue
            break
        if not found:
            return False, f"preposition '{t.surface}' without NP object"
    return True, "ok"


def aspect_consistency(content: List[TokenInfo]) -> Tuple[bool, str]:
    """PROG aspect requires a BE aux; PERF aspect requires a HAVE aux.

    Reason for the surface-form gate: the word-level analyzer occasionally
    over-tags bare base forms (e.g. 'run') with PERF because the irregular
    table conflates 'ran/run' past participle with the base form. Apply the
    PERF check only when the token surface is a participle (ends in -en, -ed
    or known irregular past participle), so we do not over-reject bare
    infinitives in 'to run', 'to be', etc.
    """
    have_be = any(_surface(t) in _BE_FORMS for t in content)
    have_have = any(_surface(t) in _HAVE_FORMS for t in content)
    for t in content:
        if t.tags.get("aspect") == "PROG" and not have_be:
            return False, f"PROG without BE aux: {t.surface}"
        if t.tags.get("aspect") == "PERF" and not have_have:
            s = _surface(t)
            # only flag when the surface really looks participial
            if s.endswith("en") or s.endswith("ed"):
                return False, f"PERF without HAVE aux: {t.surface}"
    return True, "ok"


_SUBORDINATORS = {"because", "although", "since", "unless", "while", "if",
                  "when", "where", "as", "though", "whereas", "whether",
                  "until", "before", "after"}


def subordinator_takes_clause(content: List[TokenInfo]) -> Tuple[bool, str]:
    """A subordinating CONJ must be followed by a clause (NP + finite verb
    downstream). Detect by tag (subcat=SUB) or by surface form."""
    for i, t in enumerate(content):
        is_sub = (t.tags.get("subcat") == "SUB"
                  or (t.pos == "CONJ" and _surface(t) in _SUBORDINATORS))
        if not is_sub:
            continue
        tail = content[i + 1:]
        has_subj = any(c.pos in {"NOUN", "PRON", "UNKNOWN", "DET"}
                       or _surface(c) in _SUBJECT_PRONOUNS for c in tail)
        has_verb = any(_is_main_verb(c) or _is_aux(c) for c in tail)
        if not (has_subj and has_verb):
            return False, f"subordinator '{t.surface}' without clause"
    return True, "ok"


_COORDINATORS = {"and", "but", "or", "nor", "yet", "so"}


def conjunction_balanced(content: List[TokenInfo]) -> Tuple[bool, str]:
    """A coordinating CONJ may not be sentence-initial or sentence-final.

    Only enforced for true coordinators; wh-words and subordinators that
    happen to share the CONJ tag are exempt because they legitimately open
    or close clauses in other constructions.
    """
    if not content:
        return True, "ok"
    first, last = content[0], content[-1]
    if (first.pos == "CONJ"
            and _surface(first) in _COORDINATORS
            and first.tags.get("subcat") != "SUB"):
        return False, f"sentence starts with coordinator '{first.surface}'"
    if last.pos == "CONJ" and _surface(last) in _COORDINATORS:
        return False, f"sentence ends with conjunction '{last.surface}'"
    return True, "ok"


def _classify(tokens: List[TokenInfo], content: List[TokenInfo]) -> str:
    """Return one of: declarative, interrogative, imperative, exclamative."""
    if not tokens:
        return "declarative"
    last = tokens[-1]
    if _surface(last).endswith("?"):
        return "interrogative"
    if _surface(last).endswith("!"):
        return "exclamative"
    if content:
        first = content[0]
        first_s = _surface(first)
        # Wh-fronted or aux-fronted: interrogative even without '?'
        if first_s in _WH_WORDS:
            return "interrogative"
        if _is_aux(first) and len(content) > 1:
            return "interrogative"
        # Imperative: starts with a verb (no subject NP in front).
        if _is_main_verb(first) and first_s in _VERB_BASE_FORMS:
            return "imperative"
    return "declarative"


def validate_sentence(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """Apply structural guards. Returns (ok, message)."""
    content = _content(tokens)
    if not content:
        return True, "ok"

    sent_type = _classify(tokens, content)

    # Universal guards (subordinator check before determiner check so the
    # message is more informative for sentences ending in a dangling subord.)
    for guard in (has_main_verb_or_copula,
                  subordinator_takes_clause,
                  determiner_precedes_noun,
                  preposition_precedes_np,
                  aspect_consistency,
                  conjunction_balanced):
        ok, msg = guard(content)
        if not ok:
            return False, msg

    if sent_type == "declarative":
        ok, msg = subject_precedes_main_verb(content)
        if not ok:
            return False, msg
    elif sent_type == "interrogative":
        ok, msg = aux_or_wh_fronted(content)
        if not ok:
            return False, msg
    # imperative / exclamative: no extra guard required beyond universals

    # Legacy bundle checks ported from shared.validate_sentence_structure_en
    for t in content:
        if t.tags.get("degree") in ("COMP", "SUPER") and t.pos not in (
            "ADJ", "ADV"
        ):
            return False, f"degree tag on non-ADJ/ADV: {t.surface}"
        if t.tags.get("aspect") == "PERF" and t.tags.get("tense") not in (
            "PAST", "PRES", None
        ):
            return False, f"PERF aspect without valid tense: {t.surface}"
        if t.tags.get("poss") == "YES" and t.pos != "NOUN":
            return False, f"possessive on non-NOUN: {t.surface}"

    return True, "ok"
