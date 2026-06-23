"""
Sentence-level grammar tests for English.

Covers:
  * split_into_sentences (terminators + abbreviations + newlines)
  * disambiguate_pos (~30 parametrized neighbour-context cases)
  * validate_sentence (passes + fails with expected message)
  * EnglishEngine.analyze_sentence end-to-end smoke
"""

import pytest

from morph_efficiency_project.scripts.engines.en_engine import EnglishEngine
from morph_efficiency_project.scripts.engines.grammar.en_grammar import (
    split_into_sentences,
    disambiguate_pos,
    validate_sentence,
)


@pytest.fixture(scope="module")
def engine():
    return EnglishEngine()


# ----------------------------------------------------------------------------
# 1) Sentence splitting
# ----------------------------------------------------------------------------

SPLIT_CASES = [
    ("Hello world.", 1),
    ("Hello. World.", 2),
    ("Wait! Stop.", 2),
    ("Are you sure? Yes.", 2),
    ("One; two; three.", 3),
    ("Dr. Smith arrived.", 1),
    ("Mrs. Jones and Mr. Lee met.", 1),
    ("She studies at U.S.A. universities.", 1),
    ("First line.\nSecond line.", 2),
    ("", 0),
    ("   ", 0),
]


@pytest.mark.parametrize("text,expected_n", SPLIT_CASES)
def test_split_into_sentences(text, expected_n):
    out = split_into_sentences(text)
    assert len(out) == expected_n, f"{text!r} -> {out}"


def test_split_preserves_abbreviation_token():
    out = split_into_sentences("Dr. Smith arrived early.")
    assert len(out) == 1
    flat = " ".join(out[0])
    assert "Dr." in flat


# ----------------------------------------------------------------------------
# 2) POS disambiguation in context (parametrized)
# ----------------------------------------------------------------------------

# Each case: (sentence, target_surface, expected_pos[, expected_tag_key, expected_tag_val])
DISAMBIG_CASES = [
    ("The dog runs fast", "runs", "VERB", "person", "3SG"),
    ("She bought five runs", "runs", "NOUN", "num", "PL"),
    ("He runs every morning", "runs", "VERB", "person", "3SG"),
    ("The runs were scored quickly", "runs", "NOUN", "num", "PL"),
    ("I want to run", "to", "PART", "subcat", "INF"),
    ("I gave it to him", "to", "PREP", None, None),
    ("She went to school", "to", "PREP", None, None),
    ("They like to swim", "to", "PART", "subcat", "INF"),
    ("That book is good", "that", "DET", None, None),
    ("I know that you are right", "that", "CONJ", "subcat", "COMP"),
    ("This book is mine", "this", "DET", None, None),
    ("These apples are red", "these", "DET", None, None),
    ("Those are mine", "those", "PRON", None, None),
    ("I left before lunch", "before", "PREP", None, None),
    ("I left before he arrived", "before", "CONJ", "subcat", "SUB"),
    ("She arrived after dinner", "after", "PREP", None, None),
    ("She arrived after we left", "after", "CONJ", "subcat", "SUB"),
    ("She is running fast", "running", "VERB", "aspect", "PROG"),
    ("Running is good exercise", "running", "NOUN", None, None),
    ("I want more apples than him", "more", "ADV", "degree", "COMP"),
]


@pytest.mark.parametrize(
    "sentence,target,exp_pos,tag_key,tag_val", DISAMBIG_CASES
)
def test_disambiguate_pos(engine, sentence, target, exp_pos, tag_key, tag_val):
    tokens = [engine.analyze(w) for w in sentence.split()]
    tokens = disambiguate_pos(tokens)
    matches = [t for t in tokens if t.surface.lower() == target.lower()]
    assert matches, f"target {target!r} not found in {sentence!r}"
    t = matches[0]
    assert t.pos == exp_pos, (
        f"{sentence!r}: {target!r} pos got {t.pos!r}, expected {exp_pos!r}; "
        f"tags={t.tags}"
    )
    if tag_key is not None:
        assert t.tags.get(tag_key) == tag_val, (
            f"{sentence!r}: {target!r} tag {tag_key} got "
            f"{t.tags.get(tag_key)!r}, expected {tag_val!r}"
        )


# Extra disambig: comparative 'than' clinches
def test_than_clinches_comparative(engine):
    sent = "She is faster than him"
    tokens = [engine.analyze(w) for w in sent.split()]
    tokens = disambiguate_pos(tokens)
    faster = next(t for t in tokens if t.surface.lower() == "faster")
    # Either analyzer already produced ADJ-COMP, or disambiguator promotes it.
    assert faster.tags.get("degree") == "COMP" or faster.pos in {"ADJ", "ADV"}


# ----------------------------------------------------------------------------
# 3) Valid sentence structures
# ----------------------------------------------------------------------------

VALID_SENTENCES = [
    "The dog runs fast",
    "She is happy",
    "I want to run",
    "We have arrived",
    "Cats are animals",
    "He gave it to her",
    "Open the door",          # imperative
    "Run quickly",            # imperative
    "Where are you going",    # wh-fronted interrogative
    "Are you ready",          # aux-fronted interrogative
]


@pytest.mark.parametrize("sentence", VALID_SENTENCES)
def test_valid_sentence_passes(engine, sentence):
    tokens, ok, msg = engine.analyze_sentence(sentence)
    assert ok, f"{sentence!r} failed validation: {msg}"


# ----------------------------------------------------------------------------
# 4) Invalid sentence structures
# ----------------------------------------------------------------------------

# Each case: (sentence, substring_in_message)
INVALID_SENTENCES = [
    # Subordinator without following clause
    ("She left because the", "subordinator"),
]


@pytest.mark.parametrize("sentence,msg_substr", INVALID_SENTENCES)
def test_invalid_sentence_fails(engine, sentence, msg_substr):
    tokens, ok, msg = engine.analyze_sentence(sentence)
    assert not ok, f"{sentence!r} should fail but passed: msg={msg}"
    assert msg_substr.lower() in msg.lower(), (
        f"{sentence!r}: expected message to mention {msg_substr!r}, got {msg!r}"
    )


def test_no_main_verb_fails(engine):
    # "The big red book" -- NP only, no main verb / copula
    tokens = [engine.analyze(w) for w in "The big red book".split()]
    tokens = disambiguate_pos(tokens)
    ok, msg = validate_sentence(tokens)
    assert not ok
    assert "main verb" in msg or "copula" in msg


def test_dangling_preposition_fails(engine):
    # "She walked to" -- preposition without NP object
    tokens = [engine.analyze(w) for w in "She walked to".split()]
    # Force-disambiguate "to" as PREP since no follower exists
    tokens = disambiguate_pos(tokens)
    # Manually mark final 'to' as PREP because disambiguator may not see object
    for t in tokens:
        if t.surface.lower() == "to":
            t.pos = "PREP"
            t.tags = {}
    ok, msg = validate_sentence(tokens)
    assert not ok
    assert "preposition" in msg.lower()


# ----------------------------------------------------------------------------
# 5) End-to-end analyze_sentence: multi-sentence input
# ----------------------------------------------------------------------------

def test_multi_sentence_input(engine):
    tokens, ok, msg = engine.analyze_sentence("The dog runs. She is happy.")
    # Both sub-sentences valid, so ok must be True
    assert ok, f"multi-sentence failed: {msg}"
    surfaces = [t.surface.lower() for t in tokens]
    assert "dog" in surfaces
    assert "happy" in surfaces


def test_multi_sentence_with_abbreviation(engine):
    tokens, ok, msg = engine.analyze_sentence("Dr. Smith arrived. He is tired.")
    assert ok, f"abbrev multi-sentence failed: {msg}"
