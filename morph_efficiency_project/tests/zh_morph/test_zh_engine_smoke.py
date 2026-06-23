"""
test_zh_engine_smoke.py
-----------------------
Basic smoke tests for the Mandarin Chinese morphology engine.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import MandarinEngine
import pytest

engine = MandarinEngine()


# ── Particles ────────────────────────────────────────────────────────────────

def test_aspect_particle_le():
    r = engine.analyze("了")
    assert r.pos == "PART"
    assert r.tags["aspect"] == "PERF"

def test_aspect_particle_zhe():
    r = engine.analyze("着")
    assert r.pos == "PART"
    assert r.tags["aspect"] == "DUR"

def test_aspect_particle_guo():
    r = engine.analyze("过")
    assert r.pos == "PART"
    assert r.tags["aspect"] == "EXP"

def test_structural_de():
    r = engine.analyze("的")
    assert r.pos == "PART"
    assert r.tags["role"] == "ATTR"

def test_structural_di():
    r = engine.analyze("地")
    assert r.pos == "PART"
    assert r.tags["role"] == "ADVL"

def test_structural_de_comp():
    r = engine.analyze("得")
    assert r.pos == "PART"  # 得 as structural PART wins (registered before AUX)

def test_question_ma():
    r = engine.analyze("吗")
    assert r.pos == "PART"
    assert r.tags["particle_type"] == "QUESTION"


# ── Pronouns ─────────────────────────────────────────────────────────────────

def test_pronoun_wo():
    r = engine.analyze("我")
    assert r.pos == "PRON"
    assert r.tags["person"] == "1"
    assert r.tags["num"] == "SG"

def test_pronoun_ta_masc():
    r = engine.analyze("他")
    assert r.pos == "PRON"
    assert r.tags["gender"] == "MASC"

def test_pronoun_ta_fem():
    r = engine.analyze("她")
    assert r.pos == "PRON"
    assert r.tags["gender"] == "FEM"


# ── Classifiers ──────────────────────────────────────────────────────────────

def test_classifier_ge():
    r = engine.analyze("个")
    assert r.pos == "CLF"
    assert r.tags["classifier"] == "GEN"

def test_classifier_ben():
    r = engine.analyze("本")
    assert r.pos == "CLF"
    assert r.tags["classifier"] == "BOOKS"


# ── Numbers ──────────────────────────────────────────────────────────────────

def test_number_yi():
    r = engine.analyze("一")
    assert r.pos == "NUM"

def test_number_shi():
    r = engine.analyze("十")
    assert r.pos == "NUM"


# ── Prepositions ─────────────────────────────────────────────────────────────

def test_prep_zai():
    r = engine.analyze("在")
    assert r.pos == "ADP"

def test_prep_ba():
    r = engine.analyze("把")
    assert r.pos == "ADP"
    assert r.tags["construction"] == "BA"


# ── Content words resolved by open-class fallback (comprehensive spec) ───────

def test_content_word_unknown():
    r = engine.analyze("电脑")
    assert r.pos == "NOUN"
    assert r.tags == {}

def test_content_word_verb_unknown():
    r = engine.analyze("学习")
    assert r.pos == "VERB"


# ── Sentence analysis ────────────────────────────────────────────────────────

def test_sentence_basic():
    tokens, ok, msg = engine.analyze_sentence("我 喜欢 中文")
    assert len(tokens) == 3
    assert tokens[0].pos == "PRON"
    assert ok is True
