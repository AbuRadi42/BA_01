"""
test_zh_engine_derivation.py
----------------------------
Tests for derivational prefix/suffix detection in the Mandarin engine.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import MandarinEngine
import pytest

engine = MandarinEngine()


# ── Prefix 老 (familiar) ─────────────────────────────────────────────────────

@pytest.mark.parametrize("surface,expected_root", [
    ("老师", "师"),
    ("老虎", "虎"),
    ("老鼠", "鼠"),
    ("老板", "板"),
])
def test_prefix_lao(surface, expected_root):
    r = engine.analyze(surface)
    assert r.root == expected_root
    assert any("FAMILIAR_PREFIX" in d for d in r.derived_chain)


# ── Prefix 小 (diminutive) ───────────────────────────────────────────────────

@pytest.mark.parametrize("surface,expected_root", [
    ("小姐", "姐"),
    ("小心", "心"),
    ("小时", "时"),
])
def test_prefix_xiao(surface, expected_root):
    r = engine.analyze(surface)
    assert r.root == expected_root
    assert any("DIMINUTIVE_PREFIX" in d for d in r.derived_chain)


# ── Prefix 阿 (familiar) ─────────────────────────────────────────────────────

def test_prefix_a_yi():
    r = engine.analyze("阿姨")
    assert r.root == "姨"
    assert any("FAMILIAR_PREFIX" in d for d in r.derived_chain)


# ── Suffix 子 (nominalizer) ──────────────────────────────────────────────────

@pytest.mark.parametrize("surface,expected_root", [
    ("桌子", "桌"),
    ("杯子", "杯"),
    ("椅子", "椅"),
    ("房子", "房"),
])
def test_suffix_zi(surface, expected_root):
    r = engine.analyze(surface)
    assert r.root == expected_root
    assert any("NOMINALIZER" in d for d in r.derived_chain)


# ── Suffix 儿 (erhua diminutive) ─────────────────────────────────────────────

@pytest.mark.parametrize("surface,expected_root", [
    ("花儿", "花"),
    ("鸟儿", "鸟"),
])
def test_suffix_er(surface, expected_root):
    r = engine.analyze(surface)
    assert r.root == expected_root
    assert any("ERHUA_DIM" in d for d in r.derived_chain)


# ── Suffix 头 (nominalizer) ──────────────────────────────────────────────────

def test_suffix_tou_stone():
    r = engine.analyze("石头")
    assert r.root == "石"
    assert any("NOMINALIZER" in d for d in r.derived_chain)


# ── Suffix 家 (agent/expert) ─────────────────────────────────────────────────

def test_suffix_jia_scientist():
    r = engine.analyze("科学家")
    assert r.root == "科学"
    assert any("AGENT_EXPERT" in d for d in r.derived_chain)

def test_suffix_jia_writer():
    r = engine.analyze("作家")
    assert r.root == "作"
    assert any("AGENT_EXPERT" in d for d in r.derived_chain)


# ── Suffix 员 (agent/member) ─────────────────────────────────────────────────

def test_suffix_yuan_actor():
    r = engine.analyze("演员")
    assert r.root == "演"
    assert any("AGENT_MEMBER" in d for d in r.derived_chain)


# ── Suffix 化 (verbalizer) ───────────────────────────────────────────────────

def test_suffix_hua_modernize():
    r = engine.analyze("现代化")
    assert r.root == "现代"
    assert any("VERBALIZER" in d for d in r.derived_chain)
    assert r.pos == "VERB"


# ── Suffix 性 (quality noun) ─────────────────────────────────────────────────

def test_suffix_xing_possibility():
    r = engine.analyze("可能性")
    assert r.root == "可能"
    assert any("QUALITY_NOUN" in d for d in r.derived_chain)


# ── Suffix 者 (agent/person) ─────────────────────────────────────────────────

def test_suffix_zhe_reader():
    r = engine.analyze("读者")
    assert r.root == "读"
    assert any("AGENT_PERSON" in d for d in r.derived_chain)


# ── Suffix 式 (style) ────────────────────────────────────────────────────────

def test_suffix_shi_chinese_style():
    r = engine.analyze("中式")
    assert r.root == "中"
    assert any("STYLE_ADJ" in d for d in r.derived_chain)
    assert r.pos == "ADJ"
