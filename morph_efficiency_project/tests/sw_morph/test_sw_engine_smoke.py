"""
test_sw_engine_smoke.py
-----------------------
Swahili morphology engine smoke tests.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import SwahiliEngine
import pytest

engine = SwahiliEngine()

# ── Basic root extraction across POS ────────────────────────────────────────

ROOT_CASES = [
    ("anasoma",   "som",     "VERB",  "3SG present progressive"),
    ("kitabu",    "tabu",    "NOUN",  "class 7 noun"),
    ("watoto",    "toto",    "NOUN",  "class 2 noun"),
    ("mzuri",     "zuri",    "ADJ",   "class 1 adjective"),
    ("vizuri",    "zuri",    "ADJ",   "class 8 adjective"),
    ("lakini",    "lakini",  "CONJ",  "conjunction"),
    ("sana",      "sana",    "ADV",   "adverb closed-class"),
    ("ni",        "ni",      "PART",  "copular particle"),
    ("husoma",    "som",     "VERB",  "habitual"),
    ("tunasoma",  "som",     "VERB",  "1PL present"),
    ("amesoma",   "som",     "VERB",  "3SG perfect"),
    ("atasoma",   "som",     "VERB",  "3SG future"),
    ("wanasoma",  "som",     "VERB",  "3PL present"),
    ("ninakula",  "la",      "VERB",  "1SG present monosyllabic eat"),
    ("vitabu",    "tabu",    "NOUN",  "class 8 noun plural"),
]

@pytest.mark.parametrize("surface,exp_root,exp_pos,label", ROOT_CASES)
def test_root_extraction(surface, exp_root, exp_pos, label):
    result = engine.analyze(surface)
    assert result.root == exp_root, (
        f"[{label}] root: got {result.root!r}, expected {exp_root!r}"
    )
    assert result.pos == exp_pos, (
        f"[{label}] pos: got {result.pos!r}, expected {exp_pos!r}"
    )


# ── Sentence analysis ──────────────────────────────────────────────────────

def test_sentence_analysis_basic():
    tokens, ok, msg = engine.analyze_sentence("kitabu kinasoma")
    assert len(tokens) == 2
    assert tokens[0].pos == "NOUN"
    assert tokens[1].pos == "VERB"


def test_sentence_returns_list():
    tokens, ok, msg = engine.analyze_sentence("na au lakini")
    assert len(tokens) == 3
    for t in tokens:
        assert t.pos == "CONJ"


def test_analyze_returns_token_info():
    result = engine.analyze("anasoma")
    assert result.surface == "anasoma"
    assert isinstance(result.tags, dict)
    assert isinstance(result.derived_chain, list)


def test_empty_word():
    """Single character / very short words should not crash."""
    result = engine.analyze("a")
    assert result is not None


def test_unknown_word():
    """Unknown words get a fallback analysis."""
    result = engine.analyze("xyzzy")
    assert result is not None
    assert result.root is not None


# ── Closed-class coverage ──────────────────────────────────────────────────

CLOSED_CASES = [
    ("na",       "CONJ"),
    ("au",       "CONJ"),
    ("lakini",   "CONJ"),
    ("kwa",      "ADP"),
    ("katika",   "ADP"),
    ("bila",     "ADP"),
    ("nani",     "PRON"),
    ("nini",     "PRON"),
    ("sana",     "ADV"),
    ("pia",      "ADV"),
]

@pytest.mark.parametrize("surface,exp_pos", CLOSED_CASES)
def test_closed_class(surface, exp_pos):
    result = engine.analyze(surface)
    assert result.pos == exp_pos, (
        f"closed-class {surface!r}: got {result.pos!r}, expected {exp_pos!r}"
    )


if __name__ == "__main__":
    passed = failed = 0
    for surface, exp_root, exp_pos, label in ROOT_CASES:
        result = engine.analyze(surface)
        ok = result.root == exp_root and result.pos == exp_pos
        if ok:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL  {surface:<20s}  {label}  ->  root={result.root!r} pos={result.pos!r}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
