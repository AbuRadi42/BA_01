"""
engines/grammar/tr_grammar.py
=============================
Turkish sentence-level grammar layer (Dilbilgisi: cumle yapisi).

Provides:
  - split_into_sentences: Latin-terminator splitter, handling Turkish abbreviations.
  - disambiguate_pos:     context-aware POS resolution (izafet vs poss, copular
                          predicates, sentence-final verb bias, postposition NPs).
  - validate_sentence:    SOV/copular/interrogative/imperative/existential/
                          conditional/subordinate sentence structure validation.
"""

from typing import List, Tuple
from ..shared import TokenInfo
from .common import LATIN_TERMINATORS, split_on_punctuation


# Turkish abbreviations that should NOT trigger sentence break.
TR_ABBREVIATIONS = {
    "Dr.", "Prof.", "Doc.", "Av.", "Sn.", "Bay.", "Bn.",
    "vb.", "vs.", "yy.", "yzy.", "a.g.e.", "bkz.", "Cad.", "Sok.",
    "Mah.", "No.", "Tel.", "Fax.", "Apt.", "M.O.", "M.S.",
}


# Postpositions (edatlar) that subcategorise for case-marked NPs.
POSTPOSITIONS = {"icin", "için", "gibi", "ile", "kadar", "gore", "göre",
                 "dogru", "doğru", "karsi", "karşı", "ragmen", "rağmen",
                 "dolayi", "dolayı", "beri", "once", "önce", "sonra"}

# Question particle surfaces.
Q_PARTICLES = {"mi", "mı", "mu", "mü"}

# Existential predicates.
EXISTENTIAL = {"var", "yok"}

# Cardinal numerals (sayilar) are a closed class. The word-level analyzer
# defaults the bare forms to NOUN/UNKNOWN; in Turkish these are always numerals
# (or, for "bir", the indefinite article), never common nouns. Listing the core
# set is a fact about the language, not a fit to any corpus.
CARDINAL_NUMERALS = {
    "bir", "iki", "üç", "uc", "dört", "dort", "beş", "bes", "altı", "alti",
    "yedi", "sekiz", "dokuz", "on", "yirmi", "otuz", "kırk", "kirk", "elli",
    "altmış", "altmis", "yetmiş", "yetmis", "seksen", "doksan", "yüz", "yuz",
    "bin", "milyon", "milyar",
}

# The additive clitic "da" / "de" ("also, too, and") written as a separate
# word is a conjunction (zeyrek tags it Conj). It is distinct from the bound
# locative suffix -da/-de, which never appears as a standalone token.
ADDITIVE_CLITICS = {"da", "de"}

# Copular endings (-y/-i/-ydı/-imiş etc.) on bare noun/adj predicates.
COPULAR_SUFFIXES = ("dir", "dır", "dur", "dür", "tir", "tır", "tur", "tür",
                    "ydi", "ydı", "ydu", "ydü", "ymis", "ymış", "ymis", "ymüs",
                    "ymiş", "ymüş", "yim", "yım", "yum", "yüm",
                    "sin", "sın", "sun", "sün", "iz", "ız", "uz", "üz",
                    "yiz", "yız", "yuz", "yüz")


# ── Sentence splitter ────────────────────────────────────────────────────────

def split_into_sentences(text: str) -> List[List[str]]:
    """Split Turkish text into sentences on . ! ? ; and newlines.

    Honours Turkish abbreviations (Dr., vb., yy., yzy., a.g.e., vs.) so that
    they do not trigger a premature break.
    """
    # Normalise newlines to terminators so split_on_punctuation handles them.
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    # Treat newlines as soft sentence breaks: insert a period if the previous
    # token is not already terminator-ending.
    pieces: List[str] = []
    for chunk in normalised.split("\n"):
        chunk = chunk.strip()
        if chunk:
            pieces.append(chunk)
    sentences: List[List[str]] = []
    for piece in pieces:
        sentences.extend(split_on_punctuation(piece, LATIN_TERMINATORS, TR_ABBREVIATIONS))
    return sentences


# ── POS disambiguation ───────────────────────────────────────────────────────

_VERBAL_TENSE_KEYS = {"tense", "aspect"}
_VERBAL_MOODS = {"IMP", "COND", "NECESS", "OPT"}


def _looks_verbal(tok: TokenInfo) -> bool:
    if tok.pos == "VERB":
        return True
    if _VERBAL_TENSE_KEYS & set(tok.tags.keys()):
        return True
    if tok.tags.get("mood") in _VERBAL_MOODS:
        return True
    return False


def _has_poss(tok: TokenInfo) -> bool:
    return "poss" in tok.tags


def _has_case(tok: TokenInfo, *cases) -> bool:
    if not cases:
        return "case" in tok.tags
    return tok.tags.get("case") in cases


def _ends_with_copular(surface: str) -> bool:
    s = surface.lower()
    return any(s.endswith(suf) for suf in COPULAR_SUFFIXES)


def disambiguate_pos(tokens: List[TokenInfo]) -> List[TokenInfo]:
    """Resolve POS using neighbour context (Turkish-specific).

    Heuristics applied (in order):
      1. Sentence-final position biases VERB (Turkish SOV).
      2. `evin` (GEN vs POSS_2SG): if the next noun bears POSS, treat as GEN
         in an izafet construction; otherwise (bare VERB or copular ending),
         keep as POSS_2SG subject.
      3. `kapisi` (POSS_3SG vs ACC): sentence-final or before a VERB without
         ACC slot, treat as POSS_3SG subject; otherwise leave alone.
      4. Copular predicates: bare NOUN/ADJ followed by a copular surface ending
         is re-tagged as predicate (pos kept, role=PREDICATE).
      5. Postpositions (icin, gibi, ile, kadar): preceding NP must be case-marked
         (informational; we annotate role=POSTP_OBJ when adjacent).
    """
    if not tokens:
        return tokens

    n = len(tokens)
    last_idx = n - 1

    # Forward anchor pass: find unambiguous verb / postposition positions.
    verb_positions = {i for i, t in enumerate(tokens) if _looks_verbal(t)}
    # If no anchored verb but final token looks verbal-ish, bias it.
    if not verb_positions and last_idx >= 0:
        t = tokens[last_idx]
        # Bare existential predicate counts.
        if t.surface.lower() in EXISTENTIAL:
            verb_positions.add(last_idx)

    for i, tok in enumerate(tokens):
        surface = tok.surface.lower()
        tags = dict(tok.tags)

        # Rule 0a: closed-class cardinal numerals. The bare numeral forms are
        # numerals (or the indefinite article for "bir"), never common nouns.
        # Only retag the nominal/unknown default; never override a numeral that
        # already inflected into a derived noun reading carrying case/poss.
        if surface in CARDINAL_NUMERALS and tok.pos in ("NOUN", "UNKNOWN") \
                and not tags.get("case") and not tags.get("poss"):
            tok.pos = "NUM"
            continue

        # Rule 0b: standalone additive clitic "da"/"de" → conjunction.
        if surface in ADDITIVE_CLITICS and tok.pos == "PART" \
                and tok.tags.get("sem") == "ADDITIVE":
            tok.pos = "CONJ"
            continue

        # Rule 5: postpositions
        if surface in POSTPOSITIONS:
            tok.pos = "POSTP"
            if i > 0:
                prev = tokens[i - 1]
                # Annotate prev as postposition-object when it carries a case.
                if _has_case(prev) or prev.pos in ("NOUN", "PRON", "PROPN"):
                    prev.tags.setdefault("role", "POSTP_OBJ")
            continue

        # Rule 4: copular predicate detection on bare NOUN/ADJ.
        if tok.pos in ("NOUN", "ADJ") and _ends_with_copular(surface):
            # Only treat as predicate if no full case marker (NOM is fine).
            if tags.get("case") in (None, "NOM"):
                tok.tags.setdefault("role", "PREDICATE")
                tok.tags.setdefault("copula", "YES")

        # Rule 2: GEN vs POSS_2SG ambiguity (-in)
        # Token has GEN case AND poss=2SG ambiguity in TR analyzer; if next
        # token carries POSS, treat this as GEN (izafet).
        if tags.get("case") == "GEN" and tags.get("poss") == "2SG":
            if i + 1 < n and _has_poss(tokens[i + 1]):
                # Izafet: this is GEN, drop the POSS_2SG reading.
                tok.tags.pop("poss", None)
                tok.tags["role"] = "GENITIVE_HEAD"
            else:
                # Sentence-final, before VERB, or before a bare ADJ/NOUN
                # predicate (copular construction): POSS_2SG subject.
                drop_gen = (i == last_idx)
                if not drop_gen and i + 1 < n:
                    nxt = tokens[i + 1]
                    if _looks_verbal(nxt):
                        drop_gen = True
                    elif nxt.pos in ("ADJ", "NOUN") and not _has_poss(nxt):
                        drop_gen = True
                if drop_gen:
                    tok.tags.pop("case", None)
                    tok.tags["role"] = "SUBJECT"

        # Rule 3: POSS_3SG vs ACC ambiguity (-i)
        if tags.get("poss") == "3SG" and tags.get("case") == "ACC":
            # If sentence-final or before VERB with no need for ACC: keep POSS.
            following_verb = any(j in verb_positions for j in range(i + 1, n))
            if i == last_idx or not following_verb:
                tok.tags.pop("case", None)
                tok.tags["role"] = "SUBJECT"

        # Rule 1: sentence-final bias toward VERB for ambiguous unknowns.
        if i == last_idx and tok.pos == "UNKNOWN":
            if _looks_verbal(tok):
                tok.pos = "VERB"

    return tokens


# ── Sentence structure guards (return (bool, reason)) ────────────────────────

def has_predicate(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """Every Turkish sentence must have a predicate (yüklem)."""
    for t in tokens:
        if t.pos == "VERB":
            return True, "ok"
        if t.surface.lower() in EXISTENTIAL:
            return True, "ok"
        if t.tags.get("role") == "PREDICATE":
            return True, "ok"
        if t.tags.get("copula") == "YES":
            return True, "ok"
    return False, "yuklem eksik"


def verb_final_in_declarative(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """In a plain declarative SOV clause, the finite verb must come last
    (modulo trailing question particle / discourse clitic)."""
    content = [t for t in tokens
               if t.pos not in ("PUNCT", "UNKNOWN", "FOREIGN")
               and t.surface.lower() not in Q_PARTICLES]
    if not content:
        return True, "ok"

    verb_idx = [i for i, t in enumerate(content) if t.pos == "VERB"]
    if not verb_idx:
        return True, "ok"

    # If any verb is not in the final position AND there is no subordinator
    # construction visible, fail.
    last_verb = verb_idx[-1]
    if last_verb != len(content) - 1:
        # Allow trailing copular noun/adj predicate after verb.
        tail = content[last_verb + 1:]
        if all(t.tags.get("role") == "PREDICATE" for t in tail):
            return True, "ok"
        # Allow trailing existentials.
        if all(t.surface.lower() in EXISTENTIAL for t in tail):
            return True, "ok"
        return False, "bildirme cumlesinde fiil sonda olmali"

    # Check: was the verb placed before some bare NP (VS ordering)?
    pre_verb = content[:last_verb]
    if any(t.pos == "VERB" for t in pre_verb):
        return False, "bildirme cumlesinde fiil sonda olmali"

    return True, "ok"


def postpositions_follow_NP(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """Postpositions must follow an NP (noun, pronoun, or case-marked nominal)."""
    for i, t in enumerate(tokens):
        if t.pos == "POSTP":
            if i == 0:
                return False, "edat ad obeginden sonra gelir"
            prev = tokens[i - 1]
            if prev.pos not in ("NOUN", "PRON", "PROPN", "ADJ", "NUM"):
                return False, "edat ad obeginden sonra gelir"
    return True, "ok"


def modifiers_precede_head(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """In a noun phrase, modifiers precede their head.
    A bare ADJ followed by a non-nominal/non-verb (e.g. a GEN noun without
    POSS afterwards) flags an ordering issue.
    """
    n = len(tokens)
    for i, t in enumerate(tokens):
        if t.pos == "NOUN" and i + 1 < n:
            nxt = tokens[i + 1]
            # NOUN ADJ NOUN-final ordering (e.g. "Evi buyuk cocugun") is wrong.
            if nxt.pos == "ADJ" and i + 2 < n:
                last = tokens[i + 2]
                if last.tags.get("case") == "GEN":
                    return False, "ad obegi sirasi yanlis"
    return True, "ok"


def mi_particle_position(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """The interrogative particle (mi/mı/mu/mü) attaches after the focused
    constituent, typically sentence-final in yes/no questions.
    """
    for i, t in enumerate(tokens):
        if t.surface.lower() in Q_PARTICLES:
            if i == 0:
                return False, "soru eki cumle sonunda veya odaklanan ogeden hemen sonra"
    return True, "ok"


def subordinate_clause_uses_participle(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """Subordinate (yan) clauses in Turkish are formed with non-finite
    participial morphology (-ki, -dik, -ecek, -an). This is a soft check:
    if a token carries a subordinator tag but is finite, flag it.
    """
    for t in tokens:
        if t.tags.get("sub") == "YES" and t.pos == "VERB" and "tense" in t.tags:
            # subordinated tokens should be non-finite (participial).
            if t.tags.get("mood") not in ("PART", "VN", None):
                return False, "yan cumlede cekimsiz fiil"
    return True, "ok"


def existential_var_yok_at_end(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """Existential predicates 'var' / 'yok' should appear at sentence end."""
    for i, t in enumerate(tokens):
        if t.surface.lower() in EXISTENTIAL:
            tail = [u for u in tokens[i + 1:]
                    if u.pos not in ("PUNCT", "UNKNOWN")
                    and u.surface.lower() not in Q_PARTICLES]
            if tail:
                return False, "var/yok yapisi cumle sonunda"
    return True, "ok"


# ── Sentence validator ───────────────────────────────────────────────────────

def _is_question(tokens: List[TokenInfo]) -> bool:
    return any(t.surface.lower() in Q_PARTICLES for t in tokens)


def _is_imperative(tokens: List[TokenInfo]) -> bool:
    return any(t.tags.get("mood") == "IMP" for t in tokens)


def _is_copular(tokens: List[TokenInfo]) -> bool:
    return any(t.tags.get("copula") == "YES" or t.tags.get("role") == "PREDICATE"
               for t in tokens)


def _is_existential(tokens: List[TokenInfo]) -> bool:
    return any(t.surface.lower() in EXISTENTIAL for t in tokens)


def _is_conditional(tokens: List[TokenInfo]) -> bool:
    return any(t.tags.get("mood") == "COND" for t in tokens)


def validate_sentence(tokens: List[TokenInfo]) -> Tuple[bool, str]:
    """Top-level Turkish sentence validator.

    Recognised sentence types:
      1. Declarative SOV
      2. Interrogative (mi-particle or wh)
      3. Imperative
      4. Copular (NOUN/ADJ + copula)
      5. Existential (var/yok)
      6. Conditional (-se/-sa)
      7. Subordinate (-ki, -dik, -ecek, -an participles)
    """
    content = [t for t in tokens if t.pos not in ("PUNCT",)]
    if not content:
        return True, "ok"

    # Structural ordering checks first (catch malformed NPs before
    # complaining about the missing predicate).
    ok, msg = modifiers_precede_head(content)
    if not ok:
        return False, msg

    # Run common guards.
    ok, msg = has_predicate(content)
    if not ok:
        return False, msg

    ok, msg = postpositions_follow_NP(content)
    if not ok:
        return False, msg

    ok, msg = mi_particle_position(content)
    if not ok:
        return False, msg

    ok, msg = subordinate_clause_uses_participle(content)
    if not ok:
        return False, msg

    # Type-conditional guards.
    if _is_existential(content):
        ok, msg = existential_var_yok_at_end(content)
        if not ok:
            return False, msg
        return True, "ok"

    if _is_copular(content):
        # Copular sentences: the copular predicate should occupy the final slot.
        # No SOV verb-final check (no finite verb required).
        return True, "ok"

    if _is_imperative(content):
        # Imperatives: structural ordering relaxed; person guard already
        # handled by shared.check_morph_sequence_tr.
        return True, "ok"

    if _is_question(content):
        # Question: mi-particle position already checked. Optional verb-final.
        return True, "ok"

    if _is_conditional(content):
        # Conditional: allow flexible ordering.
        return True, "ok"

    # Declarative SOV: verb must be final.
    ok, msg = verb_final_in_declarative(content)
    if not ok:
        return False, msg

    return True, "ok"
