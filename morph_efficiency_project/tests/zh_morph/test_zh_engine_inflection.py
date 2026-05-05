"""
test_zh_engine_inflection.py
----------------------------
Tests for the 5 inflectional stripping rules in the Mandarin engine.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import MandarinEngine
import pytest

engine = MandarinEngine()


# ── 们 plural on pronouns (closed-class handles full forms) ──────────────────

@pytest.mark.parametrize("surface,person,num", [
    ("我们", "1", "PL"),
    ("你们", "2", "PL"),
    ("他们", "3", "PL"),
    ("她们", "3", "PL"),
    ("它们", "3", "PL"),
])
def test_pronoun_plural_closedclass(surface, person, num):
    """Plural pronouns are in closed-class; they should match directly."""
    r = engine.analyze(surface)
    assert r.pos == "PRON"
    assert r.tags["person"] == person
    assert r.tags["num"] == num


# ── 们 plural on animate nouns (Step A stripping) ────────────────────────────

@pytest.mark.parametrize("surface,expected_root", [
    ("人们", "人"),
    ("孩子们", "孩子"),
    ("同学们", "同学"),
    ("朋友们", "朋友"),
    ("同事们", "同事"),
    ("老师们", "老师"),
    ("学生们", "学生"),
    ("客人们", "客人"),
])
def test_plural_animate_nouns(surface, expected_root):
    r = engine.analyze(surface)
    assert r.root == expected_root
    assert r.tags["num"] == "PL"
    assert r.pos == "NOUN"


# ── 们 should NOT strip on inanimate / unknown bases ─────────────────────────

@pytest.mark.parametrize("surface", [
    "桌们",   # nonsense: table + men
    "书们",   # nonsense: book + men
])
def test_plural_rejected_inanimate(surface):
    """们 should not strip on non-animate bases."""
    r = engine.analyze(surface)
    # Should NOT be NOUN with num=PL -- falls through to aspect stripping or UNKNOWN
    assert r.tags.get("num") != "PL" or r.pos != "NOUN"


# ── Aspect 了 (perfective, attached) ─────────────────────────────────────────

@pytest.mark.parametrize("surface,expected_root", [
    ("做了", "做"),
    ("吃了", "吃"),
    ("去了", "去"),
    ("看了", "看"),
    ("学了", "学"),
])
def test_aspect_le_attached(surface, expected_root):
    r = engine.analyze(surface)
    assert r.root == expected_root
    assert r.tags["aspect"] == "PERF"
    assert r.pos == "VERB"


def test_aspect_le_standalone():
    """Standalone 了 should be PART, not stripped."""
    r = engine.analyze("了")
    assert r.pos == "PART"
    assert r.tags["aspect"] == "PERF"
    assert r.root == "了"  # not stripped


# ── Aspect 着 (durative, attached) ───────────────────────────────────────────

@pytest.mark.parametrize("surface,expected_root", [
    ("看着", "看"),
    ("等着", "等"),
    ("想着", "想"),
    ("听着", "听"),
])
def test_aspect_zhe_attached(surface, expected_root):
    r = engine.analyze(surface)
    assert r.root == expected_root
    assert r.tags["aspect"] == "DUR"
    assert r.pos == "VERB"


def test_aspect_zhe_standalone():
    """Standalone 着 should be PART."""
    r = engine.analyze("着")
    assert r.pos == "PART"


# ── Aspect 过 (experiential, attached) ───────────────────────────────────────

@pytest.mark.parametrize("surface,expected_root", [
    ("去过", "去"),
    ("吃过", "吃"),
    ("看过", "看"),
    ("来过", "来"),
])
def test_aspect_guo_attached(surface, expected_root):
    r = engine.analyze(surface)
    assert r.root == expected_root
    assert r.tags["aspect"] == "EXP"
    assert r.pos == "VERB"


def test_aspect_guo_standalone():
    """Standalone 过 should be PART."""
    r = engine.analyze("过")
    assert r.pos == "PART"


# ── Ordinal prefix 第 ────────────────────────────────────────────────────────

@pytest.mark.parametrize("surface,expected_root", [
    ("第一", "一"),
    ("第二", "二"),
    ("第三", "三"),
    ("第十", "十"),
])
def test_ordinal(surface, expected_root):
    r = engine.analyze(surface)
    assert r.root == expected_root
    assert r.tags["role"] == "ORDINAL"
    assert r.pos == "NUM"
