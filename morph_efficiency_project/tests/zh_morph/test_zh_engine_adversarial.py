"""
test_zh_engine_adversarial.py
-----------------------------
Adversarial and edge-case tests for the Mandarin Chinese engine.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import MandarinEngine
import pytest

engine = MandarinEngine()


# ── Standalone vs attached particles ─────────────────────────────────────────

def test_le_standalone_is_particle():
    r = engine.analyze("了")
    assert r.pos == "PART"
    assert r.root == "了"

def test_le_attached_is_verb():
    r = engine.analyze("做了")
    assert r.pos == "VERB"
    assert r.root == "做"

def test_zhe_standalone_is_particle():
    r = engine.analyze("着")
    assert r.pos == "PART"

def test_zhe_attached_is_verb():
    r = engine.analyze("看着")
    assert r.pos == "VERB"
    assert r.root == "看"

def test_guo_standalone_is_particle():
    r = engine.analyze("过")
    assert r.pos == "PART"

def test_guo_attached_is_verb():
    r = engine.analyze("去过")
    assert r.pos == "VERB"
    assert r.root == "去"


# ── Numbers ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("surface", [
    "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
    "百", "千", "万", "亿", "零", "两",
])
def test_numbers(surface):
    r = engine.analyze(surface)
    assert r.pos == "NUM"


# ── Empty string ─────────────────────────────────────────────────────────────

def test_empty_string():
    r = engine.analyze("")
    assert r.pos == "UNKNOWN"
    assert r.root == ""
    assert r.tags == {}


# ── Punctuation ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("punct", ["。", "，", "！", "？", "、", "；", "："])
def test_punctuation(punct):
    r = engine.analyze(punct)
    # Engine recognises CJK punctuation as PUNCT (comprehensive spec authoritative).
    assert r.pos == "PUNCT"


# ── Latin characters ────────────────────────────────────────────────────────

def test_latin_chars():
    r = engine.analyze("hello")
    assert r.pos == "UNKNOWN"

def test_mixed_latin_chinese():
    r = engine.analyze("A股")
    assert r.pos == "UNKNOWN"


# ── Single-character content words ───────────────────────────────────────────

def test_single_char_content():
    """Single-char content noun resolved by open-class fallback (comprehensive spec)."""
    r = engine.analyze("猫")  # cat
    assert r.pos == "NOUN"

def test_single_char_verb():
    """Single-char content verb resolved by open-class fallback (comprehensive spec)."""
    r = engine.analyze("吃")  # eat
    assert r.pos == "VERB"


# ── Ambiguous characters ────────────────────────────────────────────────────

def test_zhi_as_adv():
    """只 is ambiguous (CLF for animals vs ADV restrictive). Engine resolves to CLF."""
    r = engine.analyze("只")
    assert r.pos == "CLF"

def test_ba_as_adp():
    """把 is registered as ADP (BA construction) in closed-class."""
    r = engine.analyze("把")
    assert r.pos == "ADP"

def test_zai_as_adp():
    """在 is registered as ADP (locative) in closed-class."""
    r = engine.analyze("在")
    assert r.pos == "ADP"


# ── Sentence-level tests ────────────────────────────────────────────────────

def test_sentence_svo():
    """Basic SVO: I like Chinese."""
    tokens, ok, msg = engine.analyze_sentence("我 喜欢 中文")
    assert len(tokens) == 3
    assert tokens[0].pos == "PRON"
    assert ok is True

def test_sentence_with_aspect():
    """Sentence with aspect particle: I ate rice."""
    tokens, ok, msg = engine.analyze_sentence("我 吃了 饭")
    assert tokens[1].pos == "VERB"
    assert tokens[1].tags["aspect"] == "PERF"

def test_sentence_ba_construction():
    """Ba construction: He BA the book read-PERF."""
    tokens, ok, msg = engine.analyze_sentence("他 把 书 看了")
    assert ok is True

def test_sentence_ba_without_verb():
    """Ba without verb should fail validation."""
    tokens, ok, msg = engine.analyze_sentence("他 把 书")
    assert ok is False
    assert "把" in msg

def test_sentence_bei_construction():
    """Bei (passive): The book BEI him read-PERF."""
    tokens, ok, msg = engine.analyze_sentence("书 被 他 看了")
    assert ok is True

def test_sentence_bei_without_verb():
    """Bei without verb should fail validation."""
    tokens, ok, msg = engine.analyze_sentence("书 被 他")
    assert ok is False
    assert "被" in msg

def test_sentence_empty():
    tokens, ok, msg = engine.analyze_sentence("")
    # empty sentence splits into [""] which produces one UNKNOWN token
    assert ok is True

def test_sentence_all_particles():
    tokens, ok, msg = engine.analyze_sentence("的 了 吗")
    assert len(tokens) == 3
    assert all(t.pos == "PART" for t in tokens)

def test_sentence_with_negation():
    tokens, ok, msg = engine.analyze_sentence("我 不 喜欢")
    assert tokens[1].pos == "ADV"
    assert tokens[1].tags["negation"] == "BU"


# ── Ordinal edge cases ──────────────────────────────────────────────────────

def test_ordinal_compound_number():
    """第十 should be ordinal."""
    r = engine.analyze("第十")
    assert r.pos == "NUM"
    assert r.tags["role"] == "ORDINAL"

def test_di_alone():
    """第 alone (len=1) should not trigger ordinal rule."""
    r = engine.analyze("第")
    assert r.pos == "UNKNOWN"


# ── Validator checks ─────────────────────────────────────────────────────────

def test_morph_sequence_valid():
    tokens, ok, _ = engine.analyze_sentence("我 很 喜欢 你")
    assert ok is True

def test_content_words_no_features():
    """Content words should produce no_features bundle."""
    r = engine.analyze("电脑")
    assert r.feature_bundle_str() == "no_features"

def test_feature_bundle_pronoun():
    r = engine.analyze("我")
    bundle = r.feature_bundle_str()
    assert "pos=PRON" in bundle
    assert "person=1" in bundle

def test_feature_bundle_aspect():
    r = engine.analyze("做了")
    bundle = r.feature_bundle_str()
    assert "pos=VERB" in bundle
    assert "aspect=PERF" in bundle


# ── Words that look segmentable but should not be ────────────────────────────

def test_compound_not_split_diannao():
    """电脑 (computer) should not be split; open-class fallback labels it NOUN."""
    r = engine.analyze("电脑")
    assert r.root == "电脑"
    assert r.pos == "NOUN"

def test_compound_not_split_huoche():
    """火车 (train) should not be split."""
    r = engine.analyze("火车")
    assert r.root == "火车"

def test_compound_not_split_shouji():
    """手机 (cellphone) should not be split."""
    r = engine.analyze("手机")
    assert r.root == "手机"
