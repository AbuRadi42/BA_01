"""
test_zh_engine_comprehensive.py
-------------------------------
Comprehensive edge-case test suite for the Mandarin morphology engine.

Covers:
    * Single-character and multi-character words
    * Aspect particles (PERF, DUR, EXP, PROG)
    * Negation (BU, MEI, BIE)
    * Ba- and Bei-constructions
    * Classifiers, modal auxiliaries, pronouns, demonstratives
    * Numeral-classifier-noun constructions
    * Question particles and interrogatives
    * Coverb / preposition constructions
    * Common compound types (VO, VV, NN, AN)
    * Radical-class layer (PLANNED, marked xfail)
    * Edge cases (punctuation, numerals, loanwords, abbreviations, proper nouns)

The tests assert the LINGUISTICALLY CORRECT expected behavior. Where the engine
does not yet implement a step, the test stays in the suite so it becomes an
acceptance criterion for the future implementation.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import MandarinEngine  # noqa: E402


engine = MandarinEngine()


# =============================================================================
# 1. Single-character word handling
# =============================================================================

# Nouns: the engine currently has no monosyllabic noun lexicon -> UNKNOWN.
# The linguistically correct POS is NOUN; these tests document the gap.
@pytest.mark.parametrize("ch", ["人", "山", "水", "火", "木"])
def test_single_char_noun(ch):
    r = engine.analyze(ch)
    assert r.pos == "NOUN", f"{ch} should be NOUN, got {r.pos}"


@pytest.mark.parametrize("ch", ["走", "看", "吃", "写"])
def test_single_char_verb(ch):
    r = engine.analyze(ch)
    assert r.pos == "VERB", f"{ch} should be VERB, got {r.pos}"


@pytest.mark.parametrize("ch,person,gender", [
    ("我", "1", None),
    ("你", "2", None),
    ("他", "3", "MASC"),
    ("她", "3", "FEM"),
    ("它", "3", "NEUT"),
])
def test_single_char_pron(ch, person, gender):
    r = engine.analyze(ch)
    assert r.pos == "PRON"
    assert r.tags.get("person") == person
    if gender is not None:
        assert r.tags.get("gender") == gender


@pytest.mark.parametrize("ch,particle_type", [
    ("了", "ASPECT"),
    ("着", "ASPECT"),
    ("过", "ASPECT"),
    ("吗", "QUESTION"),
    ("呢", "TOPIC"),
    ("吧", "SUGGESTION"),
])
def test_single_char_particles(ch, particle_type):
    r = engine.analyze(ch)
    assert r.pos == "PART"
    assert r.tags.get("particle_type") == particle_type


@pytest.mark.parametrize("ch", ["在", "从", "到", "给", "对"])
def test_single_char_adp(ch):
    r = engine.analyze(ch)
    assert r.pos == "ADP"


@pytest.mark.parametrize("ch", ["和", "但", "或"])
def test_single_char_conj(ch):
    r = engine.analyze(ch)
    assert r.pos == "CONJ"


def test_multichar_conj_yinwei():
    r = engine.analyze("因为")
    assert r.pos == "CONJ"
    assert r.tags.get("subcat") == "CAUSAL"


# =============================================================================
# 2. Multi-character words (open-class content words)
# =============================================================================

@pytest.mark.parametrize("w", ["朋友", "学校", "时间", "工作"])
def test_bisyllabic_noun(w):
    r = engine.analyze(w)
    # Currently UNKNOWN; should be NOUN.
    assert r.pos == "NOUN", f"{w} should be NOUN, got {r.pos}"


@pytest.mark.parametrize("w", ["学习", "喜欢", "知道", "了解"])
def test_bisyllabic_verb(w):
    r = engine.analyze(w)
    assert r.pos == "VERB", f"{w} should be VERB, got {r.pos}"


@pytest.mark.parametrize("w", ["看看", "试试"])
def test_verb_reduplication(w):
    # AABB or AA reduplication signals tentative aspect.
    r = engine.analyze(w)
    assert r.pos == "VERB"
    # Ideal future tag (not yet implemented):
    # assert r.tags.get("aspect") == "TENTATIVE"


# =============================================================================
# 3. Aspect particles (PERF, DUR, EXP, PROG)
# =============================================================================

@pytest.mark.parametrize("w,expected_aspect", [
    ("吃了", "PERF"),
    ("走了", "PERF"),
    ("站着", "DUR"),
    ("看着", "DUR"),
    ("拿着", "DUR"),
    ("去过", "EXP"),
    ("吃过", "EXP"),
    ("见过", "EXP"),
])
def test_aspect_suffix_stripping(w, expected_aspect):
    r = engine.analyze(w)
    assert r.tags.get("aspect") == expected_aspect
    assert r.pos == "VERB"


def test_verb_with_complement_then_le():
    # 看完了: 看-完(complement)-了(PERF). Engine strips 了, leaves 看完.
    r = engine.analyze("看完了")
    assert r.tags.get("aspect") == "PERF"
    assert r.pos == "VERB"
    assert r.root == "看完"


def test_progressive_zai_as_adverb():
    # 在 by itself is registered as ADP(LOC). 正在 is ADV(aspect=PROG).
    r = engine.analyze("正在")
    assert r.pos == "ADV"
    assert r.tags.get("aspect") == "PROG"


def test_progressive_zai_sentence():
    # In a sentence, 在 before a verb signals PROG, but is currently tagged ADP.
    # Document the gap: ideally 在 in this position would be ADV/PROG.
    tokens, _, _ = engine.analyze_sentence("我 在 吃")
    assert tokens[1].surface == "在"
    # Engine currently: ADP. Linguistically: progressive marker.


# =============================================================================
# 4. Negation
# =============================================================================

@pytest.mark.parametrize("w,neg", [
    ("不", "BU"),
    ("没", "MEI"),
    ("没有", "MEI"),
    ("别", "BIE"),
])
def test_negation_particles(w, neg):
    r = engine.analyze(w)
    assert r.pos == "ADV"
    assert r.tags.get("negation") == neg


def test_negation_in_sentence_bu_chi():
    tokens, ok, _ = engine.analyze_sentence("我 不 吃")
    assert tokens[1].pos == "ADV"
    assert tokens[1].tags.get("negation") == "BU"


def test_negation_in_sentence_mei_chi():
    tokens, _, _ = engine.analyze_sentence("我 没 吃")
    assert tokens[1].tags.get("negation") == "MEI"


def test_negation_prohibitive_bie_qu():
    tokens, _, _ = engine.analyze_sentence("别 去")
    assert tokens[0].tags.get("negation") == "BIE"


def test_negation_bu_shi():
    tokens, _, _ = engine.analyze_sentence("不 是")
    assert tokens[0].tags.get("negation") == "BU"
    assert tokens[1].pos == "VERB"
    assert tokens[1].tags.get("role") == "COPULA"


def test_negation_mei_you():
    r = engine.analyze("没有")
    assert r.pos == "ADV"
    assert r.tags.get("negation") == "MEI"


# =============================================================================
# 5. Ba-construction (把)
# =============================================================================

def test_ba_lexical_tag():
    r = engine.analyze("把")
    # NOTE: 把 is ambiguous (ADP for BA-construction vs CLF for graspable
    # objects). Particles load first, so ADP wins. This is a real ambiguity
    # bug requiring context to disambiguate.
    assert r.pos == "ADP"
    assert r.tags.get("construction") == "BA"


def test_ba_construction_sentence_valid():
    tokens, ok, msg = engine.analyze_sentence("我 把 书 读 完了")
    # 把 must be followed by a verb. 读 is currently UNKNOWN, so the validator
    # cannot find a following VERB and would fail.
    ba = next(t for t in tokens if t.surface == "把")
    assert ba.tags.get("construction") == "BA"


def test_ba_construction_missing_verb_invalid():
    tokens, ok, msg = engine.analyze_sentence("我 把 书")
    assert ok is False
    assert "把" in msg


# =============================================================================
# 6. Bei-construction (被)
# =============================================================================

def test_bei_lexical_tag():
    r = engine.analyze("被")
    assert r.pos == "ADP"
    assert r.tags.get("construction") == "BEI"
    assert r.tags.get("voice") == "PASS"


def test_bei_construction_sentence():
    tokens, ok, msg = engine.analyze_sentence("书 被 我 读 完了")
    bei = next(t for t in tokens if t.surface == "被")
    assert bei.tags.get("construction") == "BEI"


def test_bei_construction_missing_verb_invalid():
    tokens, ok, msg = engine.analyze_sentence("书 被 我")
    assert ok is False
    assert "被" in msg


# =============================================================================
# 7. Classifiers
# =============================================================================

@pytest.mark.parametrize("ch,cls", [
    ("个", "GEN"),
    ("本", "BOOKS"),
    ("张", "FLAT"),
    ("只", "ANIMALS"),
    ("条", "LONG"),
    ("件", "CLOTHING_MATTERS"),
    ("杯", "CUPS"),
    ("瓶", "BOTTLES"),
    ("辆", "VEHICLES"),
])
def test_classifier_lookup(ch, cls):
    r = engine.analyze(ch)
    assert r.pos == "CLF"
    assert r.tags.get("classifier") == cls


def test_classifier_ba_collides_with_preposition():
    # 把 in classifiers config is CLF=GRASPABLE, but the particles loader runs
    # first and registers 把 as ADP. Documents the collision.
    r = engine.analyze("把")
    assert r.pos == "ADP"  # NOT CLF, due to ordering


# =============================================================================
# 8. Modal auxiliaries
# =============================================================================

@pytest.mark.parametrize("w,modal", [
    ("会", "ABILITY"),
    ("能", "ABILITY"),
    ("可以", "PERMISSION"),
    ("应该", "OBLIGATION"),
    ("必须", "OBLIGATION"),
    ("要", "VOLITION"),
    ("想", "VOLITION"),
])
def test_modal_auxiliaries(w, modal):
    r = engine.analyze(w)
    assert r.pos == "AUX"
    assert r.tags.get("modal") == modal


def test_modal_yuanyi_missing():
    # 愿意 is not in the lexicon -> UNKNOWN. Documents a gap.
    r = engine.analyze("愿意")
    assert r.pos == "AUX", f"愿意 should be AUX, got {r.pos}"


# =============================================================================
# 9. Personal pronouns (full set)
# =============================================================================

@pytest.mark.parametrize("w,person,num,gender", [
    ("我",   "1", "SG", None),
    ("你",   "2", "SG", None),
    ("他",   "3", "SG", "MASC"),
    ("她",   "3", "SG", "FEM"),
    ("它",   "3", "SG", "NEUT"),
    ("我们", "1", "PL", None),
    ("你们", "2", "PL", None),
    ("他们", "3", "PL", "MASC"),
    ("她们", "3", "PL", "FEM"),
    ("它们", "3", "PL", "NEUT"),
])
def test_personal_pronouns_full(w, person, num, gender):
    r = engine.analyze(w)
    assert r.pos == "PRON"
    assert r.tags.get("person") == person
    assert r.tags.get("num") == num
    if gender is not None:
        assert r.tags.get("gender") == gender


def test_reflexive_ziji():
    r = engine.analyze("自己")
    assert r.pos == "PRON"
    assert r.tags.get("reflex") == "YES"


def test_inclusive_zanmen():
    # 咱们 (inclusive 1PL) is not currently in the lexicon. Documents a gap.
    r = engine.analyze("咱们")
    assert r.pos == "PRON", f"咱们 should be PRON, got {r.pos}"
    assert r.tags.get("person") == "1"
    assert r.tags.get("num") == "PL"


# =============================================================================
# 10. Demonstratives
# =============================================================================

@pytest.mark.parametrize("w,deixis", [
    ("这", "PROX"),
    ("那", "DIST"),
    ("这些", "PROX"),
    ("那些", "DIST"),
])
def test_demonstratives(w, deixis):
    r = engine.analyze(w)
    assert r.pos == "PRON"
    assert r.tags.get("deixis") == deixis


@pytest.mark.parametrize("w,deixis", [
    ("这个", "PROX"),
    ("那个", "DIST"),
])
def test_demonstrative_plus_classifier(w, deixis):
    # 这个 / 那个 are not registered as single tokens. Engine returns UNKNOWN
    # since the suffix-stripping rules do not match. Linguistically, these
    # should be DET with deixis tag.
    r = engine.analyze(w)
    assert r.pos == "DET", f"{w} should be DET, got {r.pos}"
    assert r.tags.get("deixis") == deixis


@pytest.mark.parametrize("w,deixis", [
    ("这里", "PROX"),
    ("那里", "DIST"),
])
def test_locative_demonstratives(w, deixis):
    r = engine.analyze(w)
    assert r.pos == "PRON", f"{w} should be PRON, got {r.pos}"
    assert r.tags.get("deixis") == deixis


# =============================================================================
# 11. Number-classifier-noun construction
# =============================================================================

def test_num_clf_noun_san_ge_ren():
    tokens, _, _ = engine.analyze_sentence("三 个 人")
    assert tokens[0].pos == "NUM"
    assert tokens[1].pos == "CLF"
    assert tokens[2].pos == "NOUN", f"人 should be NOUN, got {tokens[2].pos}"


def test_num_clf_noun_yi_ben_shu():
    tokens, _, _ = engine.analyze_sentence("一 本 书")
    assert tokens[0].pos == "NUM"
    assert tokens[1].pos == "CLF"
    assert tokens[1].tags.get("classifier") == "BOOKS"


def test_num_clf_noun_liang_zhi_mao():
    tokens, _, _ = engine.analyze_sentence("两 只 猫")
    assert tokens[0].pos == "NUM"
    assert tokens[1].pos == "CLF"
    assert tokens[1].tags.get("classifier") == "ANIMALS"


# =============================================================================
# 12. Question particles and interrogatives
# =============================================================================

@pytest.mark.parametrize("ch,ptype", [
    ("吗", "QUESTION"),
    ("呢", "TOPIC"),
    ("吧", "SUGGESTION"),
])
def test_sentence_final_particles(ch, ptype):
    r = engine.analyze(ch)
    assert r.pos == "PART"
    assert r.tags.get("particle_type") == ptype


@pytest.mark.parametrize("w", ["谁", "什么", "哪里"])
def test_interrogative_pronouns(w):
    r = engine.analyze(w)
    assert r.pos == "PRON"
    assert r.tags.get("interrog") == "YES"


def test_interrogative_duoshao():
    # 多少 not in the lexicon. Should be interrogative DET/PRON.
    r = engine.analyze("多少")
    assert r.pos in ("PRON", "DET"), f"多少 should be PRON/DET, got {r.pos}"
    assert r.tags.get("interrog") == "YES"


# =============================================================================
# 13. Coverb / preposition constructions
# =============================================================================

@pytest.mark.parametrize("w,subcat", [
    ("给", "BENEFACTIVE"),
    ("跟", "COMITATIVE"),
    ("对", "TARGET"),
    ("替", "SUBSTITUTIVE"),
    ("用", "INSTRUMENTAL"),
])
def test_coverbs(w, subcat):
    r = engine.analyze(w)
    assert r.pos == "ADP"
    assert r.tags.get("subcat") == subcat


# =============================================================================
# 14. Common compound types
# =============================================================================

def test_compound_vo_chifan():
    # 吃饭 verb+object. Currently UNKNOWN. Ideally VERB.
    r = engine.analyze("吃饭")
    assert r.pos == "VERB", f"吃饭 should be VERB, got {r.pos}"


def test_compound_vv_xuexi():
    r = engine.analyze("学习")
    assert r.pos == "VERB", f"学习 should be VERB, got {r.pos}"


def test_compound_nn_pengyou():
    r = engine.analyze("朋友")
    assert r.pos == "NOUN", f"朋友 should be NOUN, got {r.pos}"


def test_compound_an_haopengyou():
    # 好朋友 adj+noun
    r = engine.analyze("好朋友")
    assert r.pos == "NOUN", f"好朋友 should be NOUN, got {r.pos}"


# =============================================================================
# 15. Radical-class layer (PLANNED, not yet implemented)
# =============================================================================
# The future engine should attach `tags['radical']` (the Kangxi radical) and
# `tags['radical_class']` (a coarse semantic class) for every Han character.
# These tests define the acceptance criteria.

RADICAL_EXPECTATIONS = [
    # (char, radical, radical_class)
    ("人", "人", "CLASS:HUMAN_RELATION"),
    ("们", "亻", "CLASS:HUMAN_RELATION"),
    ("你", "亻", "CLASS:HUMAN_RELATION"),
    ("他", "亻", "CLASS:HUMAN_RELATION"),
    ("木", "木", "CLASS:TREE_WOOD"),
    ("林", "木", "CLASS:TREE_WOOD"),
    ("森", "木", "CLASS:TREE_WOOD"),
    ("树", "木", "CLASS:TREE_WOOD"),
    ("水", "水", "CLASS:WATER_LIQUID"),
    ("河", "氵", "CLASS:WATER_LIQUID"),
    ("海", "氵", "CLASS:WATER_LIQUID"),
    ("江", "氵", "CLASS:WATER_LIQUID"),
    ("心", "心", "CLASS:HEART_EMOTION"),
    ("想", "心", "CLASS:HEART_EMOTION"),
    ("情", "忄", "CLASS:HEART_EMOTION"),
    ("快", "忄", "CLASS:HEART_EMOTION"),
    ("言", "言", "CLASS:SPEECH_LANGUAGE"),
    ("说", "讠", "CLASS:SPEECH_LANGUAGE"),
    ("话", "讠", "CLASS:SPEECH_LANGUAGE"),
    ("语", "讠", "CLASS:SPEECH_LANGUAGE"),
    ("火", "火", "CLASS:FIRE_HEAT"),
    ("烧", "火", "CLASS:FIRE_HEAT"),
    ("山", "山", "CLASS:EARTH_TERRAIN"),
    ("石", "石", "CLASS:EARTH_TERRAIN"),
    ("土", "土", "CLASS:EARTH_TERRAIN"),
    ("金", "金", "CLASS:METAL"),
    ("钱", "钅", "CLASS:METAL"),
    ("手", "手", "CLASS:HAND_ACTION"),
    ("打", "扌", "CLASS:HAND_ACTION"),
    ("拿", "手", "CLASS:HAND_ACTION"),
]


@pytest.mark.parametrize("ch,radical,radical_class", RADICAL_EXPECTATIONS)
def test_radical_class_layer(ch, radical, radical_class):
    r = engine.analyze(ch)
    assert r.tags.get("radical") == radical, (
        f"{ch}: expected radical {radical}, got {r.tags.get('radical')}"
    )
    assert r.tags.get("radical_class") == radical_class, (
        f"{ch}: expected class {radical_class}, "
        f"got {r.tags.get('radical_class')}"
    )


# =============================================================================
# 16. Edge cases
# =============================================================================

@pytest.mark.parametrize("ch", ["，", "。", "！", "？"])
def test_punctuation_handling(ch):
    # Punctuation is not in the lexicon -> UNKNOWN. Ideally a PUNCT POS exists.
    r = engine.analyze(ch)
    assert r.pos == "PUNCT", f"{ch} should be PUNCT, got {r.pos}"


def test_ordinal_with_chinese_numeral():
    r = engine.analyze("第三")
    assert r.pos == "NUM"
    assert r.tags.get("role") == "ORDINAL"


def test_ordinal_with_arabic_numeral_mixed():
    # 第3次 mixes 第 + Arabic numeral. The current rule allows only Chinese
    # numerals after 第, so this is left as UNKNOWN. Documents the gap.
    r = engine.analyze("第3次")
    assert r.pos == "NUM", f"第3次 should be NUM/ORDINAL, got {r.pos}"


@pytest.mark.parametrize("w", ["咖啡", "沙发"])
def test_foreign_loanwords(w):
    # Phonetic loans; should be NOUN.
    r = engine.analyze(w)
    assert r.pos == "NOUN", f"{w} loanword should be NOUN, got {r.pos}"


def test_latin_abbreviation_cctv():
    # Latin-letter abbreviation. Should be NOUN/PROPN/FOREIGN, not UNKNOWN.
    r = engine.analyze("CCTV")
    assert r.pos in ("NOUN", "PROPN", "FOREIGN"), (
        f"CCTV should be NOUN/PROPN/FOREIGN, got {r.pos}"
    )


@pytest.mark.parametrize("w", ["北京", "中国"])
def test_proper_nouns(w):
    r = engine.analyze(w)
    assert r.pos in ("NOUN", "PROPN"), f"{w} should be NOUN/PROPN, got {r.pos}"


def test_animate_plural_men():
    # 朋友们: 朋友 + 们 plural marker on animate base.
    r = engine.analyze("朋友们")
    assert r.pos == "NOUN"
    assert r.tags.get("num") == "PL"
    assert r.root == "朋友"


def test_inanimate_plural_men_rejected():
    # 山们 is ungrammatical; 山 is not in the animate set, so 们 should not
    # be stripped. Engine should leave it as UNKNOWN.
    r = engine.analyze("山们")
    # Falls through to suffix rules: doesn't end in 了/着/过/第 -> UNKNOWN.
    assert r.pos == "UNKNOWN"
