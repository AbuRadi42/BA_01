"""
test_hu_engine_sentence.py
---------------------------
Sentence-level analysis and validation tests.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import HungarianEngine
from morph_efficiency_project.scripts.engines.shared import (
    check_morph_sequence_hu,
    validate_sentence_structure_hu,
    TokenInfo,
)
import pytest

engine = HungarianEngine()


# ── analyze_sentence produces correct token count ────────────────────────

SENTENCES = [
    ("a ház nagy",             3, "3-word sentence"),
    ("én írtam",               2, "2-word sentence"),
    ("volt",                   1, "1-word sentence"),
    ("",                       0, "empty sentence"),
    ("a nagy házban lakunk",    4, "4-word sentence"),
    ("nem írtam",              2, "negation + verb"),
]


@pytest.mark.parametrize("sentence,exp_count,label", SENTENCES)
def test_sentence_token_count(sentence, exp_count, label):
    tokens, ok, msg = engine.analyze_sentence(sentence)
    assert len(tokens) == exp_count, f"[{label}] count: {len(tokens)}"


# ── Sentence validation passes for well-formed input ─────────────────────

VALID_SENTENCES = [
    "a ház nagy",
    "én írtam",
    "házban lakunk",
    "nem volt",
    "a tanár mondta",
    "itt vagyok",
]


@pytest.mark.parametrize("sentence", VALID_SENTENCES)
def test_valid_sentence(sentence):
    tokens, ok, msg = engine.analyze_sentence(sentence)
    assert ok is True, f"sentence: {sentence!r}, msg: {msg}"


# ── Token-level checks within sentences ──────────────────────────────────

def test_sentence_closed_class_not_decomposed():
    """Closed-class words in sentences should not be decomposed."""
    tokens, ok, msg = engine.analyze_sentence("nem volt itt")
    assert tokens[0].pos == "PART"   # nem
    assert tokens[1].root == "van"   # volt (irregular)
    assert tokens[2].pos == "ADV"    # itt


def test_sentence_mixed_pos():
    """Sentence with mixed POS types."""
    tokens, ok, msg = engine.analyze_sentence("a tanár írtam")
    assert tokens[0].pos == "DET"    # a
    assert tokens[1].root == "tanár"
    assert tokens[2].tags.get("tense") == "PAST"


def test_sentence_plural_noun():
    """Plural noun in sentence context."""
    tokens, ok, msg = engine.analyze_sentence("házak")
    assert tokens[0].tags.get("num") == "PL"
    assert tokens[0].root == "ház"


# ── Morph sequence validation edge cases ─────────────────────────────────

def test_morph_valid_noun_with_case():
    tok = TokenInfo("házban", {}, "", "ház", {"case": "INESS"}, "NOUN", [])
    assert check_morph_sequence_hu([tok]) is True


def test_morph_valid_verb_with_tense():
    tok = TokenInfo("írtam", {}, "", "ír",
                    {"tense": "PAST", "person": "1", "num": "SG", "def": "AMBIG"},
                    "VERB", [])
    assert check_morph_sequence_hu([tok]) is True


def test_morph_invalid_cond_plus_subj():
    tok = TokenInfo("x", {}, "", "x",
                    {"tense": "COND", "mood": "SUBJ", "person": "1", "num": "SG", "def": "INDEF"},
                    "VERB", [])
    assert check_morph_sequence_hu([tok]) is False


def test_morph_invalid_poss_on_verb():
    tok = TokenInfo("x", {}, "", "x",
                    {"poss": "1SG", "tense": "PAST"},
                    "VERB", [])
    assert check_morph_sequence_hu([tok]) is False


def test_morph_valid_adj_with_degree():
    tok = TokenInfo("nagyobb", {}, "", "nagy", {"degree": "COMP"}, "ADJ", [])
    assert check_morph_sequence_hu([tok]) is True


def test_morph_adj_rejects_verbal_tags():
    tok = TokenInfo("x", {}, "", "x", {"degree": "COMP", "tense": "PAST"}, "ADJ", [])
    assert check_morph_sequence_hu([tok]) is False


# ── Sentence structure validator ─────────────────────────────────────────

def test_sentence_structure_empty():
    ok, msg = validate_sentence_structure_hu([])
    assert ok is True


def test_sentence_structure_single_noun():
    tok = TokenInfo("ház", {}, "", "ház", {"case": "NOM"}, "NOUN", [])
    ok, msg = validate_sentence_structure_hu([tok])
    assert ok is True


def test_sentence_structure_nominal_order_ok():
    """num -> poss -> case is valid order."""
    tok = TokenInfo("házaimban", {}, "", "ház",
                    {"num": "PL", "poss": "1SG", "case": "INESS"},
                    "NOUN", [])
    ok, msg = validate_sentence_structure_hu([tok])
    assert ok is True
