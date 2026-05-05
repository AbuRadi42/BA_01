"""
test_tr_engine_sentence.py
--------------------------
TurkishEngine — sentence-level analysis (updated for fixed engine).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import pytest
from morph_efficiency_project.scripts.engines import TurkishEngine

engine = TurkishEngine()

def analyze(sentence):
    return engine.analyze_sentence(sentence)

# ══════════════════════════════════════════════════════════════════════════════
# 1. RETURN CONTRACT
# ══════════════════════════════════════════════════════════════════════════════

def test_returns_three_values():
    result = engine.analyze_sentence("adam gidiyor")
    assert len(result) == 3

def test_returns_correct_types():
    tokens, ok, msg = analyze("adam gidiyor")
    assert isinstance(tokens, list)
    assert isinstance(ok, bool)
    assert isinstance(msg, str)

# ══════════════════════════════════════════════════════════════════════════════
# 2. TOKEN COUNT
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("sentence,count", [
    ("adam gidiyor",              2),
    ("kedi uyudu",                2),
    ("çocuklar okula gidiyor",    3),
    ("biz çalışıyoruz",           2),
    ("kitabı okudum",             2),
    ("gitmek istiyorum",          2),
])
def test_token_count(sentence, count):
    tokens, _, _ = analyze(sentence)
    assert len(tokens) == count

# ══════════════════════════════════════════════════════════════════════════════
# 3. ROOT INTEGRITY
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("sentence", [
    "adam gidiyor",
    "kedi uyudu",
    "çocuklar okula gidiyor",
    "biz çalışıyoruz",
    "kitabı okudum",
    "gitmek istiyorum",
    "çalışmadan başarı olmaz",
])
def test_all_tokens_have_root(sentence):
    tokens, _, _ = analyze(sentence)
    for tok in tokens:
        assert tok.root is not None
        assert len(tok.root) > 0

# ══════════════════════════════════════════════════════════════════════════════
# 4. SURFACE PRESERVED
# ══════════════════════════════════════════════════════════════════════════════

def test_surface_preserved_two_words():
    tokens, _, _ = analyze("adam gidiyor")
    assert [t.surface for t in tokens] == ["adam", "gidiyor"]

def test_surface_preserved_three_words():
    tokens, _, _ = analyze("çocuklar okula gidiyor")
    assert [t.surface for t in tokens] == ["çocuklar", "okula", "gidiyor"]

# ══════════════════════════════════════════════════════════════════════════════
# 5. VERB IN CONTEXT
# ══════════════════════════════════════════════════════════════════════════════

def test_pres_prog_in_context():
    tokens, _, _ = analyze("adam gidiyor")
    tok = next(t for t in tokens if t.surface == "gidiyor")
    assert tok.root == "gid"
    assert tok.tags["tense"] == "PRES_PROG"

def test_pres_prog_plural_in_context():
    tokens, _, _ = analyze("biz çalışıyoruz")
    tok = next(t for t in tokens if t.surface == "çalışıyoruz")
    assert tok.tags["tense"] == "PRES_PROG"
    assert tok.tags["person"] == "1"
    assert tok.tags["num"] == "PL"

def test_fut_in_context():
    tokens, _, _ = analyze("o gelmeyecek")
    tok = next(t for t in tokens if t.surface == "gelmeyecek")
    assert tok.tags["tense"] == "FUT"

def test_inf_in_context():
    tokens, _, _ = analyze("gitmek istiyorum")
    tok = next(t for t in tokens if t.surface == "gitmek")
    assert tok.tags["mood"] == "INF"

def test_acc_case_in_context():
    tokens, _, _ = analyze("kitabı okudum")
    tok = next(t for t in tokens if t.surface == "kitabı")
    assert tok.root == "kitap"
    assert tok.tags["case"] == "ACC"

# ══════════════════════════════════════════════════════════════════════════════
# 6. CONVERB IN CONTEXT
# ══════════════════════════════════════════════════════════════════════════════

def test_conv_without_in_context():
    tokens, _, _ = analyze("çalışmadan başarı olmaz")
    tok = next(t for t in tokens if t.surface == "çalışmadan")
    assert tok.tags["sem"] == "WITHOUT"

def test_conv_pos_in_context():
    tokens, _, _ = analyze("çalışmadan başarı olmaz")
    tok = next(t for t in tokens if t.surface == "çalışmadan")
    assert tok.pos == "CONV"

# ══════════════════════════════════════════════════════════════════════════════
# 7. SINGLE-WORD SENTENCE
# ══════════════════════════════════════════════════════════════════════════════

def test_single_word_verb():
    tokens, ok, msg = analyze("gidiyor")
    assert len(tokens) == 1
    assert tokens[0].root == "gid"
    assert tokens[0].tags["tense"] == "PRES_PROG"

def test_single_word_noun():
    tokens, ok, msg = analyze("kitap")
    assert len(tokens) == 1
    assert tokens[0].root == "kitap"
