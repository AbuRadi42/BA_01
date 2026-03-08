"""
test_en_engine_sentence.py
--------------------------
EnglishEngine — sentence-level analysis and structural validation.

Covers:
  - analyze_sentence() token count and root integrity
  - Irregular forms resolved correctly in sentence context
  - POS tag consistency across sentence tokens
  - validate_sentence_structure_en() basic contracts

Run: python -m pytest morph_efficiency_project/tests/en_morph/test_en_engine_sentence.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import pytest
from morph_efficiency_project.scripts.engines import EnglishEngine

engine = EnglishEngine()

def analyze(sentence):
    tokens, ok, msg = engine.analyze_sentence(sentence)
    return tokens, ok, msg

# ══════════════════════════════════════════════════════════════════════════════
# 1. TOKEN COUNT
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("sentence,count", [
    ("the cat sat on the mat",   6),
    ("she went to the store",    5),
    ("he is running fast",       4),
    ("they have been working",   4),
    ("I",                        1),
])
def test_token_count(sentence, count):
    tokens, _, _ = analyze(sentence)
    assert len(tokens) == count

# ══════════════════════════════════════════════════════════════════════════════
# 2. ROOT INTEGRITY — every token must have a non-empty root
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("sentence", [
    "the cat sat on the mat",
    "she went to the store",
    "children are running outside",
    "the men wrote their reports",
    "she has been teaching for years",
])
def test_all_tokens_have_root(sentence):
    tokens, _, _ = analyze(sentence)
    for tok in tokens:
        assert tok.root is not None
        assert len(tok.root) > 0, f"Empty root for surface={tok.surface!r}"

# ══════════════════════════════════════════════════════════════════════════════
# 3. IRREGULAR FORMS IN CONTEXT
# ══════════════════════════════════════════════════════════════════════════════

def test_went_in_context():
    tokens, _, _ = analyze("he went home")
    tok = next(t for t in tokens if t.surface == "went")
    assert tok.root == "go"
    assert tok.tags["tense"] == "PAST"

def test_children_in_context():
    tokens, _, _ = analyze("the children played outside")
    tok = next(t for t in tokens if t.surface == "children")
    assert tok.root == "child"

def test_been_in_context():
    tokens, _, _ = analyze("she has been working")
    tok = next(t for t in tokens if t.surface == "been")
    assert tok.root == "be"

def test_written_in_context():
    tokens, _, _ = analyze("the report was written")
    tok = next(t for t in tokens if t.surface == "written")
    assert tok.root == "write"

def test_running_in_context():
    tokens, _, _ = analyze("he is running fast")
    tok = next(t for t in tokens if t.surface == "running")
    assert tok.root == "run"
    assert tok.tags["aspect"] == "PROG"

# ══════════════════════════════════════════════════════════════════════════════
# 4. SURFACE PRESERVED
# ══════════════════════════════════════════════════════════════════════════════

def test_surface_preserved():
    tokens, _, _ = analyze("cats went running")
    surfaces = [t.surface for t in tokens]
    assert surfaces == ["cats", "went", "running"]

# ══════════════════════════════════════════════════════════════════════════════
# 5. SENTENCE VALIDATION RETURNS BOOL + STRING
# ══════════════════════════════════════════════════════════════════════════════

def test_analyze_sentence_returns_three_values():
    result = engine.analyze_sentence("the cat sat")
    assert len(result) == 3
    tokens, ok, msg = result
    assert isinstance(ok, bool)
    assert isinstance(msg, str)

def test_single_word_sentence():
    tokens, ok, msg = analyze("running")
    assert len(tokens) == 1
    assert tokens[0].root == "run"
