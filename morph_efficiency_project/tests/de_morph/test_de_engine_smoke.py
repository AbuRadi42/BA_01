"""
test_de_engine_smoke.py
-----------------------
Basic sanity checks for the German morphology engine.

Run: python -m pytest morph_efficiency_project/tests/de_morph/test_de_engine_smoke.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import GermanEngine
import pytest

engine = GermanEngine()

# ── Root extraction tests ────────────────────────────────────────────────────

ROOT_CASES = [
    # Regular weak verbs
    ("machen",    "machen",    "VERB",  "infinitive"),
    ("gemacht",   "machen",    "VERB",  "Partizip II weak"),
    # Strong verbs (irregular)
    ("sang",      "singen",    "VERB",  "strong verb past"),
    ("gesungen",  "singen",    "VERB",  "strong verb Partizip II"),
    ("gegeben",   "geben",     "VERB",  "strong verb Partizip II"),
    ("ging",      "gehen",     "VERB",  "irregular past"),
    ("gegangen",  "gehen",     "VERB",  "irregular Partizip II"),
    # Auxiliary/modal
    ("bin",       "sein",      "VERB",  "sein present 1SG"),
    ("hat",       "haben",     "VERB",  "haben present 3SG"),
    ("wird",      "werden",    "VERB",  "werden present 3SG"),
    ("kann",      "können",    "AUX",   "modal können"),
    # Irregular nouns
    ("Männer",    "Mann",      "NOUN",  "Umlaut plural"),
    ("Häuser",    "Haus",      "NOUN",  "Umlaut plural"),
    ("Kinder",    "Kind",      "NOUN",  "irregular plural"),
    # Closed class
    ("der",       "der",       "DET",   "definite article"),
    ("die",       "die",       "DET",   "definite article"),
    ("ich",       "ich",       "PRON",  "personal pronoun"),
    ("und",       "und",       "CONJ",  "conjunction"),
    ("nicht",     "nicht",     "PART",  "negation particle"),
    ("in",        "in",        "ADP",   "preposition"),
    # Adjective comparatives
    ("besser",    "gut",       "ADJ",   "suppletive comparative"),
    ("größer",    "groß",      "ADJ",   "irregular comparative"),
    # Mixed verbs
    ("dachte",    "denken",    "VERB",  "mixed verb past"),
    ("gebracht",  "bringen",   "VERB",  "mixed verb Partizip II"),
    ("gekannt",   "kennen",    "VERB",  "mixed verb Partizip II"),
]


@pytest.mark.parametrize("surface, expected_root, expected_pos, desc", ROOT_CASES)
def test_root_extraction(surface, expected_root, expected_pos, desc):
    info = engine.analyze(surface)
    assert info.root == expected_root, f"[{desc}] root: {info.root!r} != {expected_root!r}"
    assert info.pos == expected_pos, f"[{desc}] pos: {info.pos!r} != {expected_pos!r}"


# ── POS assignment tests ────────────────────────────────────────────────────

POS_CASES = [
    ("der",    "DET"),
    ("ich",    "PRON"),
    ("und",    "CONJ"),
    ("in",     "ADP"),
    ("nicht",  "PART"),
    ("sehr",   "ADV"),
    ("bin",    "VERB"),
    ("kann",   "AUX"),
]


@pytest.mark.parametrize("surface, expected_pos", POS_CASES)
def test_pos_assignment(surface, expected_pos):
    info = engine.analyze(surface)
    assert info.pos == expected_pos, f"POS for {surface!r}: {info.pos!r} != {expected_pos!r}"


def test_analyze_returns_token_info():
    info = engine.analyze("Haus")
    assert hasattr(info, "surface")
    assert hasattr(info, "root")
    assert hasattr(info, "pos")
    assert hasattr(info, "tags")
    assert hasattr(info, "derived_chain")
    assert info.surface == "Haus"


def test_analyze_sentence_basic():
    tokens, ok, msg = engine.analyze_sentence("der Mann hat")
    assert len(tokens) == 3
    assert isinstance(ok, bool)
    assert isinstance(msg, str)
