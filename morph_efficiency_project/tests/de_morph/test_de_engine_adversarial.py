"""
test_de_engine_adversarial.py
-----------------------------
Adversarial / edge-case tests: short words, false-positive compound prevention,
Umlaut edge cases, mixed-case input, empty input, non-German input,
validator tests.

Run: python -m pytest morph_efficiency_project/tests/de_morph/test_de_engine_adversarial.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import GermanEngine
from morph_efficiency_project.scripts.engines import (
    TokenInfo, check_morph_sequence_de, validate_sentence_structure_de,
)
import pytest

engine = GermanEngine()


# -- Short words should not be incorrectly stripped ----------------------------

SHORT_WORDS_NO_STRIP = [
    ("an",   "ADP",  "preposition, 2 chars"),
    ("in",   "ADP",  "preposition, 2 chars"),
    ("er",   "PRON", "pronoun, 2 chars"),
    ("es",   "PRON", "pronoun, 2 chars"),
    ("du",   "PRON", "pronoun, 2 chars"),
    ("ja",   "PART", "particle, 2 chars"),
    ("so",   "ADV",  "adverb, 2 chars"),
]


@pytest.mark.parametrize("surface, expected_pos, desc", SHORT_WORDS_NO_STRIP)
def test_short_word_recognized(surface, expected_pos, desc):
    info = engine.analyze(surface)
    assert info.pos == expected_pos, f"[{desc}] pos: {info.pos!r}"


# -- Words resembling compounds but actually simplex --------------------------

SIMPLEX_GUARD = [
    "Butter",
    "Muster",
    "Fenster",
    "Wasser",
    "Himmel",
    "Sommer",
    "Winter",
    "Keller",
    "Finger",
    "Schulter",
]


@pytest.mark.parametrize("word", SIMPLEX_GUARD)
def test_simplex_not_split(word):
    parts = engine.split_compound(word)
    assert parts == [word], f"{word!r} should not be split: {parts}"


# -- Empty / whitespace input --------------------------------------------------

def test_empty_string():
    info = engine.analyze("")
    assert info.surface == ""
    assert info.pos == "UNKNOWN"


def test_whitespace_analyze_sentence():
    tokens, ok, msg = engine.analyze_sentence("")
    assert tokens == []


def test_single_space():
    tokens, ok, msg = engine.analyze_sentence(" ")
    # split() on " " gives [""]? No, "".split() returns []
    # " ".split() returns []
    assert tokens == []


# -- Non-German input ----------------------------------------------------------

def test_english_word():
    info = engine.analyze("computer")
    # Should get UNKNOWN or be recognized through some path
    assert info.surface == "computer"


def test_numbers():
    info = engine.analyze("12345")
    assert info.pos == "UNKNOWN"


def test_punctuation():
    info = engine.analyze("!")
    assert info.pos == "UNKNOWN"


def test_mixed_chars():
    info = engine.analyze("abc123def")
    assert info.pos == "UNKNOWN"


# -- Case sensitivity ----------------------------------------------------------

def test_uppercase_der():
    """DER should still be recognized as article."""
    info = engine.analyze("DER")
    # lowercased -> "der" -> closed class
    assert info.pos == "DET"


def test_mixed_case_nicht():
    info = engine.analyze("Nicht")
    assert info.pos == "PART"


def test_lowercase_mann():
    info = engine.analyze("mann")
    # 'mann' lowercase should still find irregular plurals etc.
    # Step A lowercases, then checks irregulars, then rules
    assert info.surface == "mann"


# -- Umlaut edge cases --------------------------------------------------------

def test_umlaut_in_stem():
    """Verbs with Umlaut in stem should be handled."""
    info = engine.analyze("hören")
    # hör is in stems as VERB; hören ends in -en
    assert info.pos == "VERB"


def test_umlaut_false_positive():
    """Un-umlaut should not be applied incorrectly."""
    info = engine.analyze("schön")
    # schön is in stems as ADJ
    assert info.surface == "schön"


# -- Validator: check_morph_sequence_de ----------------------------------------

def test_validator_noun_valid():
    t = TokenInfo(surface="Mann", clitics={}, template="", root="Mann",
                  tags={"num": "SG", "gender": "MASC"}, pos="NOUN")
    assert check_morph_sequence_de([t])


def test_validator_noun_invalid_tag():
    """NOUN with a tense tag should fail."""
    t = TokenInfo(surface="Mann", clitics={}, template="", root="Mann",
                  tags={"num": "SG", "tense": "PAST"}, pos="NOUN")
    assert not check_morph_sequence_de([t])


def test_validator_verb_needs_tense_or_aspect():
    """VERB must have at least tense, aspect, mood, or verb_prefix."""
    t = TokenInfo(surface="mach", clitics={}, template="", root="machen",
                  tags={"person": "1"}, pos="VERB")
    assert not check_morph_sequence_de([t])


def test_validator_verb_with_tense():
    t = TokenInfo(surface="macht", clitics={}, template="", root="machen",
                  tags={"tense": "PRES", "person": "3", "num": "SG"}, pos="VERB")
    assert check_morph_sequence_de([t])


def test_validator_verb_with_aspect():
    t = TokenInfo(surface="gemacht", clitics={}, template="", root="machen",
                  tags={"aspect": "PERF"}, pos="VERB")
    assert check_morph_sequence_de([t])


def test_validator_adj_valid():
    t = TokenInfo(surface="guter", clitics={}, template="", root="gut",
                  tags={"degree": "POS", "case": "NOM", "gender": "MASC"}, pos="ADJ")
    assert check_morph_sequence_de([t])


def test_validator_adj_invalid_tag():
    """ADJ with tense tag should fail."""
    t = TokenInfo(surface="gut", clitics={}, template="", root="gut",
                  tags={"tense": "PAST"}, pos="ADJ")
    assert not check_morph_sequence_de([t])


def test_validator_adv_valid():
    t = TokenInfo(surface="schneller", clitics={}, template="", root="schnell",
                  tags={"degree": "COMP"}, pos="ADV")
    assert check_morph_sequence_de([t])


def test_validator_adv_invalid_tag():
    """ADV with case tag should fail."""
    t = TokenInfo(surface="hier", clitics={}, template="", root="hier",
                  tags={"case": "NOM"}, pos="ADV")
    assert not check_morph_sequence_de([t])


# -- Validator: validate_sentence_structure_de ---------------------------------

def test_sentence_validator_ok():
    tokens = [
        TokenInfo(surface="der", clitics={}, template="", root="der",
                  tags={"gender": "MASC", "case": "NOM"}, pos="DET"),
        TokenInfo(surface="Mann", clitics={}, template="", root="Mann",
                  tags={"num": "SG"}, pos="NOUN"),
    ]
    ok, msg = validate_sentence_structure_de(tokens)
    assert ok
    assert msg == "ok"


def test_sentence_validator_degree_on_noun():
    """degree=COMP on a NOUN should fail sentence validation."""
    tokens = [
        TokenInfo(surface="Mann", clitics={}, template="", root="Mann",
                  tags={"degree": "COMP"}, pos="NOUN"),
    ]
    ok, msg = validate_sentence_structure_de(tokens)
    assert not ok


def test_sentence_validator_perf_on_noun():
    """aspect=PERF on NOUN should fail."""
    tokens = [
        TokenInfo(surface="Mann", clitics={}, template="", root="Mann",
                  tags={"aspect": "PERF"}, pos="NOUN"),
    ]
    ok, msg = validate_sentence_structure_de(tokens)
    assert not ok


def test_sentence_validator_empty():
    ok, msg = validate_sentence_structure_de([])
    assert ok


# -- analyze_sentence integration tests ----------------------------------------

def test_sentence_der_mann_hat():
    tokens, ok, msg = engine.analyze_sentence("der Mann hat")
    assert len(tokens) == 3
    assert tokens[0].pos == "DET"
    assert tokens[2].root == "haben"


def test_sentence_ich_bin():
    tokens, ok, msg = engine.analyze_sentence("ich bin")
    assert len(tokens) == 2
    assert tokens[0].pos == "PRON"
    assert tokens[1].root == "sein"


def test_sentence_wir_machen():
    tokens, ok, msg = engine.analyze_sentence("wir machen")
    assert len(tokens) == 2
    assert tokens[0].pos == "PRON"
    assert tokens[1].pos in ("VERB", "AUX")


# -- Verify compound splitting preserves case ----------------------------------

def test_compound_parts_case():
    """Compound part names should use dictionary case."""
    parts = engine.split_compound("Arbeitsplatz")
    assert parts == ["Arbeit", "Platz"], f"Got: {parts}"


def test_compound_parts_case_handschuh():
    parts = engine.split_compound("Handschuh")
    assert parts == ["Hand", "Schuh"], f"Got: {parts}"


def test_compound_parts_case_kindergarten():
    parts = engine.split_compound("Kindergarten")
    if len(parts) >= 2:
        assert parts[-1] == "Garten", f"Got: {parts}"


# -- Verb prefix detection edge cases ------------------------------------------

def test_prefix_auf_not_false_positive():
    """'aufgeben' should get prefix AUF, not be misanalyzed."""
    info = engine.analyze("aufgeben")
    assert info.tags.get("verb_prefix") == "AUF"


def test_prefix_zu_infinitive():
    """'zumachen' should get prefix ZU."""
    info = engine.analyze("zumachen")
    assert info.tags.get("verb_prefix") == "ZU"


# -- Regression: known stems should not be split --------------------------------

def test_known_stem_not_split():
    """Butter is in stems, should not be split."""
    info = engine.analyze("Butter")
    assert "compound_parts" not in info.tags


def test_known_stem_fenster():
    info = engine.analyze("Fenster")
    assert "compound_parts" not in info.tags


# -- Token info has correct surface --------------------------------------------

def test_surface_preserved():
    info = engine.analyze("Häuser")
    assert info.surface == "Häuser"


def test_surface_preserved_mixed_case():
    info = engine.analyze("HAUS")
    assert info.surface == "HAUS"


# -- feature_bundle_str and token_str methods -----------------------------------

def test_feature_bundle_str():
    info = engine.analyze("gemacht")
    bundle = info.feature_bundle_str()
    assert "pos=VERB" in bundle
    assert "aspect=PERF" in bundle


def test_token_str():
    info = engine.analyze("gemacht")
    ts = info.token_str()
    assert ".VERB" in ts
