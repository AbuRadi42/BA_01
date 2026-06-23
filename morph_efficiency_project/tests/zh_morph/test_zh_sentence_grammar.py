"""
Sentence-level grammar tests for Mandarin Chinese.

Covers:
  * Sentence splitting on CJK + Latin terminators (。！？；…)
  * POS disambiguation for polysemous closed-class words
    (只 / 把 / 得 / 在 / 了 / 的 / 给)
  * Valid sentence templates (SVO, Ba, Bei, modal, comparison, existential)
  * Invalid sentences and the Chinese error messages they produce
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import MandarinEngine  # noqa: E402
from morph_efficiency_project.scripts.engines.grammar import zh_grammar  # noqa: E402


engine = MandarinEngine()


# =============================================================================
# 1. Sentence splitting
# =============================================================================

def test_split_single_period():
    sents = zh_grammar.split_into_sentences("我吃饭。")
    assert len(sents) == 1
    assert sents[0] == list("我吃饭。")


def test_split_multiple_cjk_terminators():
    sents = zh_grammar.split_into_sentences("我吃饭。你呢？他不来！")
    assert len(sents) == 3
    assert sents[0][-1] == "。"
    assert sents[1][-1] == "？"
    assert sents[2][-1] == "！"


def test_split_semicolon_and_ellipsis():
    sents = zh_grammar.split_into_sentences("我去；你留…")
    assert len(sents) == 2


def test_split_drops_whitespace():
    sents = zh_grammar.split_into_sentences("我 吃 饭。")
    assert sents[0] == list("我吃饭。")


def test_split_no_terminator():
    sents = zh_grammar.split_into_sentences("我吃饭")
    assert len(sents) == 1
    assert sents[0] == list("我吃饭")


def test_split_latin_terminator():
    sents = zh_grammar.split_into_sentences("OK.Next")
    assert len(sents) == 2


# =============================================================================
# 2. POS disambiguation
# =============================================================================

def _find(tokens, surface):
    return next(t for t in tokens if t.surface == surface)


def test_disambig_zhi_as_classifier_after_num():
    tokens, _, _ = engine.analyze_sentence("我 有 一 只 猫")
    zhi = _find(tokens, "只")
    assert zhi.pos == "CLF"


def test_disambig_zhi_as_adverb_before_verb():
    tokens, _, _ = engine.analyze_sentence("我 只 看了 一 本 书")
    zhi = _find(tokens, "只")
    assert zhi.pos == "ADV"


def test_disambig_ba_as_adp_with_subject():
    tokens, _, _ = engine.analyze_sentence("我 把 书 读 完了")
    ba = _find(tokens, "把")
    assert ba.pos == "ADP"
    assert ba.tags.get("construction") == "BA"


def test_disambig_de_complement_after_verb():
    tokens, _, _ = engine.analyze_sentence("他 跑 得 很 快")
    de = _find(tokens, "得")
    assert de.pos == "PART"


def test_disambig_de_as_modal_aux():
    tokens, _, _ = engine.analyze_sentence("我 得 吃饭")
    de = _find(tokens, "得")
    assert de.pos == "AUX"


def test_disambig_zai_progressive_before_verb():
    tokens, _, _ = engine.analyze_sentence("他 在 吃饭")
    zai = _find(tokens, "在")
    assert zai.pos == "ADV"
    assert zai.tags.get("aspect") == "PROG"


def test_disambig_zai_locative_before_noun():
    tokens, _, _ = engine.analyze_sentence("书 在 桌子")
    zai = _find(tokens, "在")
    assert zai.pos == "ADP"


def test_disambig_le_sentence_final_modal():
    tokens, _, _ = engine.analyze_sentence("我 吃 了")
    le = _find(tokens, "了")
    assert le.pos == "PART"
    assert le.tags.get("particle_type") == "MODAL"


def test_disambig_de_possessive_between_np_and_noun():
    tokens, _, _ = engine.analyze_sentence("我 的 书")
    de = _find(tokens, "的")
    assert de.pos == "PART"
    assert de.tags.get("particle_type") == "DE"


def test_disambig_gei_dative_after_verb():
    tokens, _, _ = engine.analyze_sentence("我 送 给 他")
    gei = _find(tokens, "给")
    assert gei.pos == "ADP"
    assert gei.tags.get("role") == "DATIVE"


# =============================================================================
# 3. Valid sentence structures
# =============================================================================

def test_valid_svo():
    _, ok, _ = engine.analyze_sentence("我 喜欢 中文")
    assert ok is True


def test_valid_ba_construction():
    _, ok, _ = engine.analyze_sentence("我 把 书 读 完了")
    assert ok is True


def test_valid_bei_construction():
    _, ok, _ = engine.analyze_sentence("书 被 我 读 完了")
    assert ok is True


def test_valid_modal_sentence():
    _, ok, _ = engine.analyze_sentence("我 想 吃饭")
    assert ok is True


def test_valid_imperative_with_negation():
    # 别 去 is a prohibitive imperative; should validate.
    _, ok, _ = engine.analyze_sentence("别 去")
    assert ok is True


def test_valid_negation_before_verb():
    _, ok, _ = engine.analyze_sentence("我 不 吃")
    assert ok is True


# =============================================================================
# 4. Invalid sentences with Chinese error messages
# =============================================================================

def test_invalid_ba_without_verb():
    _, ok, msg = engine.analyze_sentence("我 把 书")
    assert ok is False
    assert "把" in msg


def test_invalid_bei_without_verb():
    _, ok, msg = engine.analyze_sentence("书 被 我")
    assert ok is False
    assert "被" in msg


def test_invalid_dangling_negation():
    # "我 不" has no predicate; validator rejects with a Chinese message.
    _, ok, msg = engine.analyze_sentence("我 不")
    assert ok is False
    # Either the negation-position guard or the missing-predicate guard fires.
    assert any(s in msg for s in ("不", "动词", "谓语"))


# =============================================================================
# 5. Regression
# =============================================================================

def test_regression_existing_comprehensive_still_runs():
    # Smoke check: the engine still answers the canonical short sentence.
    tokens, ok, _ = engine.analyze_sentence("我 喜欢 中文")
    assert len(tokens) == 3
    assert tokens[0].pos == "PRON"
    assert ok is True
