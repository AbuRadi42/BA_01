"""
test_hu_engine_adversarial.py
------------------------------
Adversarial and edge-case tests for the Hungarian engine: consonant
assimilation, ambiguous forms, over-stripping prevention, cross-paradigm
suffix overlap, and short stems.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import HungarianEngine
from morph_efficiency_project.scripts.engines.hu_engine import ALL_VOWELS
from morph_efficiency_project.scripts.engines.shared import (
    check_morph_sequence_hu,
    validate_sentence_structure_hu,
    TokenInfo,
)
import pytest

engine = HungarianEngine()


# ── Consonant assimilation reversal ──────────────────────────────────────

ASSIMILATION = [
    ("házzal",   "ház",   "INS",    "z+val -> zzal"),
    ("kézzel",   "kéz",   "INS",    "z+vel -> zzel"),
    ("úttal",    "út",    "INS",    "t+val -> ttal"),
    ("emberrel", "ember", "INS",    "r+vel -> rrel"),
    ("tanárral", "tanár", "INS",    "r+val -> rral"),
    ("házzá",    "ház",   "TRANSL", "z+vá -> zzá"),
    ("kézzé",    "kéz",   "TRANSL", "z+vé -> zzé"),
]


@pytest.mark.parametrize("surface,exp_root,exp_case,label", ASSIMILATION)
def test_consonant_assimilation(surface, exp_root, exp_case, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.tags.get("case") == exp_case, f"[{label}] case: {r.tags.get('case')!r}"


# ── Short stems (2 chars) handled correctly ──────────────────────────────

SHORT_STEMS = [
    ("ír",    "ír",   "UNKNOWN", "bare 2-char stem"),
    ("ad",    "ad",   "UNKNOWN", "bare 2-char stem ad"),
    ("áll",   "áll",  "UNKNOWN", "bare 3-char stem áll"),
]


@pytest.mark.parametrize("surface,exp_root,exp_pos,label", SHORT_STEMS)
def test_short_stem_no_overstrip(surface, exp_root, exp_pos, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"


# ── Single-character words ──────────────────────────────────────────────

SINGLE_CHAR = [
    ("a",  "DET",  "definite article"),
    ("e",  "UNKNOWN", "not a valid word -- should not crash"),
]


@pytest.mark.parametrize("surface,exp_pos,label", SINGLE_CHAR)
def test_single_char(surface, exp_pos, label):
    r = engine.analyze(surface)
    assert r.pos == exp_pos, f"[{label}] pos: {r.pos!r}"


# ── Cross-paradigm suffix overlap ────────────────────────────────────────

def test_nak_nek_overlap():
    """'-nak' can be DAT case or INDEF 3PL. With a noun stem, prefer DAT."""
    r = engine.analyze("háznak")
    assert r.tags.get("case") == "DAT"
    assert r.pos == "NOUN"


def test_tok_tek_overlap():
    """'-tok/-tek' can be POSS_2PL or INDEF_2PL verb. With noun stem, prefer POSS."""
    r = engine.analyze("házatok")
    assert r.tags.get("poss") == "2PL"
    assert r.pos == "NOUN"


def test_k_overlap():
    """'-k' can be PL noun or INDEF 1SG verb. With noun stem, prefer PL."""
    r = engine.analyze("házak")
    assert r.tags.get("num") == "PL"
    assert r.pos == "NOUN"


def test_m_overlap():
    """'-m' can be POSS_1SG or DEF_1SG verb. With noun stem, prefer POSS."""
    r = engine.analyze("házam")
    assert r.tags.get("poss") == "1SG"
    assert r.pos == "NOUN"


def test_d_overlap():
    """'-d' can be POSS_2SG or SUBJ_DEF_2SG verb. With noun stem, prefer POSS."""
    r = engine.analyze("házad")
    assert r.tags.get("poss") == "2SG"
    assert r.pos == "NOUN"


# ── Irregular verb forms ────────────────────────────────────────────────

IRREGULAR_VERBS = [
    ("volt",     "van",   {"tense": "PAST"},  "van past 3sg"),
    ("voltam",   "van",   {"tense": "PAST"},  "van past 1sg"),
    ("voltál",   "van",   {"tense": "PAST"},  "van past 2sg"),
    ("voltunk",  "van",   {"tense": "PAST"},  "van past 1pl"),
    ("voltak",   "van",   {"tense": "PAST"},  "van past 3pl"),
    ("vagyok",   "van",   {"tense": "PRES"},  "van pres 1sg"),
    ("vagy",     "van",   {"tense": "PRES"},  "van pres 2sg"),
    ("legyen",   "van",   {"mood": "SUBJ"},   "van subj 3sg"),
    ("ment",     "megy",  {"tense": "PAST"},  "megy past 3sg"),
    ("mentem",   "megy",  {"tense": "PAST"},  "megy past 1sg"),
    ("jött",     "jön",   {"tense": "PAST"},  "jön past 3sg"),
    ("jöttem",   "jön",   {"tense": "PAST"},  "jön past 1sg"),
    ("ettem",    "eszik", {"tense": "PAST"},  "eszik past 1sg"),
    ("ittam",    "iszik", {"tense": "PAST"},  "iszik past 1sg"),
    ("tettem",   "tesz",  {"tense": "PAST"},  "tesz past 1sg"),
    ("vettem",   "vesz",  {"tense": "PAST"},  "vesz past 1sg"),
]


@pytest.mark.parametrize("surface,exp_root,exp_tags,label", IRREGULAR_VERBS)
def test_irregular_verbs(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.pos == "VERB", f"[{label}] pos: {r.pos!r}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}: got {r.tags.get(k)!r}, exp {v!r}"


# ── Irregular plural nouns ──────────────────────────────────────────────

IRREGULAR_PLURALS = [
    ("lovak",  "ló",  {"num": "PL"}, "ló->lovak"),
    ("kövek",  "kő",  {"num": "PL"}, "kő->kövek"),
    ("tavak",  "tó",  {"num": "PL"}, "tó->tavak"),
    ("szavak", "szó", {"num": "PL"}, "szó->szavak"),
    ("csövek", "cső", {"num": "PL"}, "cső->csövek"),
    ("füvek",  "fű",  {"num": "PL"}, "fű->füvek"),
]


@pytest.mark.parametrize("surface,exp_root,exp_tags,label", IRREGULAR_PLURALS)
def test_irregular_plurals(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.pos == "NOUN", f"[{label}] pos: {r.pos!r}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}: got {r.tags.get(k)!r}"


# ── Closed-class intercept ──────────────────────────────────────────────

CLOSED_CLASS = [
    ("és",     "CONJ",  "conjunction"),
    # "vagy" is in irregular_surface as van.PRES.2SG, takes priority
    # over closed-class CONJ entry. This is a known ambiguity.
    ("de",     "CONJ",  "conjunction but"),
    ("nem",    "PART",  "negation"),
    ("igen",   "PART",  "affirmative"),
    ("a",      "DET",   "definite article"),
    ("az",     "DET",   "definite article prevocalic"),
    ("egy",    "DET",   "indefinite article"),
    ("én",     "PRON",  "pronoun 1sg"),
    ("te",     "PRON",  "pronoun 2sg"),
    ("ő",      "PRON",  "pronoun 3sg"),
    ("mi",     "PRON",  "pronoun 1pl"),
    ("ti",     "PRON",  "pronoun 2pl"),
    ("ők",     "PRON",  "pronoun 3pl"),
    ("alatt",  "ADP",   "postposition under"),
    ("szerint","ADP",   "postposition according_to"),
    ("itt",    "ADV",   "adverb here"),
    ("ott",    "ADV",   "adverb there"),
    ("mindig", "ADV",   "adverb always"),
    ("soha",   "ADV",   "adverb never"),
    ("három",  "NUM",   "numeral three"),
    ("tíz",    "NUM",   "numeral ten"),
]


@pytest.mark.parametrize("surface,exp_pos,label", CLOSED_CLASS)
def test_closed_class(surface, exp_pos, label):
    r = engine.analyze(surface)
    assert r.pos == exp_pos, f"[{label}] pos: {r.pos!r}"
    # Closed-class words should have no derived chain
    assert r.derived_chain == [], f"[{label}] chain: {r.derived_chain}"


# ── Morph sequence validator ────────────────────────────────────────────

def test_valid_noun_sequence():
    tokens = [engine.analyze("házamban")]
    assert check_morph_sequence_hu(tokens) is True


def test_invalid_poss_on_verb():
    """Possessive tag on a VERB should be invalid."""
    fake = TokenInfo(
        surface="test", clitics={}, template="", root="test",
        tags={"poss": "1SG", "tense": "PAST"},
        pos="VERB", derived_chain=[],
    )
    assert check_morph_sequence_hu([fake]) is False


def test_cond_subj_mutual_exclusion():
    """COND + SUBJ on same verb should be invalid."""
    fake = TokenInfo(
        surface="test", clitics={}, template="", root="test",
        tags={"tense": "COND", "mood": "SUBJ", "person": "3", "num": "SG", "def": "INDEF"},
        pos="VERB", derived_chain=[],
    )
    assert check_morph_sequence_hu([fake]) is False


# ── Sentence-level validator ────────────────────────────────────────────

def test_sentence_validation():
    tokens, ok, msg = engine.analyze_sentence("a ház nagy")
    assert ok is True, f"msg: {msg}"


def test_sentence_nominal_slot_order():
    tokens = [engine.analyze("házamban")]
    ok, msg = validate_sentence_structure_hu(tokens)
    assert ok is True, f"msg: {msg}"


# ── Empty and whitespace input ──────────────────────────────────────────

def test_empty_sentence():
    tokens, ok, msg = engine.analyze_sentence("")
    assert tokens == []
    assert ok is True


def test_single_word_sentence():
    tokens, ok, msg = engine.analyze_sentence("ház")
    assert len(tokens) == 1
    assert tokens[0].root == "ház"


# ── Additional POS inference tests ──────────────────────────────────────

def test_pos_noun_from_case():
    """Token with case tag should be NOUN."""
    r = engine.analyze("házban")
    assert r.pos == "NOUN"


def test_pos_noun_from_poss():
    """Token with poss tag should be NOUN."""
    r = engine.analyze("házam")
    assert r.pos == "NOUN"


def test_pos_verb_from_past():
    """Token with past tense should be VERB."""
    r = engine.analyze("írtam")
    assert r.pos == "VERB"


def test_pos_verb_from_def():
    """Token with def=DEF should be VERB."""
    r = engine.analyze("írjátok")
    assert r.pos == "VERB"


def test_pos_unknown_bare_stem():
    """Bare stem with no inflection should be UNKNOWN."""
    r = engine.analyze("tanár")
    assert r.pos == "UNKNOWN"


def test_feature_bundle_str():
    """TokenInfo.feature_bundle_str() produces expected format."""
    r = engine.analyze("házban")
    bundle = r.feature_bundle_str()
    assert "pos=NOUN" in bundle
    assert "case=INESS" in bundle


def test_token_str():
    """TokenInfo.token_str() produces root.POS format."""
    r = engine.analyze("házban")
    assert r.token_str() == "ház.NOUN"


def test_irregular_precedence_over_analysis():
    """Irregular surface forms should take precedence over productive analysis."""
    r = engine.analyze("volt")
    assert r.root == "van"
    # Should not attempt to strip suffixes from 'volt'
    assert r.tags.get("tense") == "PAST"
