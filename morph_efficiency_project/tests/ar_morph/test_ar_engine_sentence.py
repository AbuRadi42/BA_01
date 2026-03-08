"""
test_ar_engine_sentence.py
--------------------------
Arabic sentence-level analysis.

Covers:
  - analyze_sentence() return contract (tuple of 3: tokens, bool, str)
  - Token count per sentence
  - Root integrity: each token has a non-empty root
  - Template integrity: each token has a non-empty template
  - Proclitic stripping in context (waw/fa/bi/li/al)
  - NOM_DERIVED detection in context (مُ-prefix words)
  - Verbal sentence detection (VERB_TRILATERAL_BARE opener)
  - Augmented verb detection in context (Forms V, VII, X)
  - Closed-class intercept in context (prepositions, negation)
  - Sentence validator ok/fail contract

Run: python -m pytest morph_efficiency_project/tests/ar_morph/test_ar_engine_sentence.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import pytest
from morph_efficiency_project.scripts.engines import ArabicEngine

engine = ArabicEngine()


# ══════════════════════════════════════════════════════════════════════════════
# 1. RETURN CONTRACT
# ══════════════════════════════════════════════════════════════════════════════

def test_return_is_tuple_of_3():
    result = engine.analyze_sentence("كَتَبَ الطَّالِبُ الدَّرْسَ")
    assert isinstance(result, tuple)
    assert len(result) == 3

def test_return_types():
    toks, ok, msg = engine.analyze_sentence("ذَهَبَ الرَّجُلُ")
    assert isinstance(toks, list)
    assert isinstance(ok, bool)
    assert isinstance(msg, str)

def test_empty_sentence():
    toks, ok, msg = engine.analyze_sentence("")
    assert toks == []
    assert ok is True

def test_single_word_sentence():
    toks, ok, msg = engine.analyze_sentence("كَتَبَ")
    assert len(toks) == 1
    assert toks[0].root == "كتب"


# ══════════════════════════════════════════════════════════════════════════════
# 2. TOKEN COUNT
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("sentence,expected_count", [
    ("كَتَبَ الطَّالِبُ الدَّرْسَ",          3),
    ("ذَهَبَ الرَّجُلُ إِلَى الْمَدْرَسَةِ", 4),
    ("الْكِتَابُ مُفِيدٌ",                    2),
    ("يَقْرَأُ الْوَلَدُ الْقِصَّةَ",         3),
    ("تَعَلَّمَ الطُّلَّابُ اللُّغَةَ",       3),
])
def test_token_count(sentence, expected_count):
    toks, _, _ = engine.analyze_sentence(sentence)
    assert len(toks) == expected_count


# ══════════════════════════════════════════════════════════════════════════════
# 3. ROOT INTEGRITY — every token must have a non-empty root
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("sentence", [
    "كَتَبَ الطَّالِبُ الدَّرْسَ",
    "ذَهَبَ الرَّجُلُ إِلَى الْمَدْرَسَةِ",
    "تَعَلَّمَ الطُّلَّابُ اللُّغَةَ",
    "اِسْتَخْدَمَ الْمُعَلِّمُ الْكِتَابَ",
    "اِنْكَسَرَ الزُّجَاجُ",
])
def test_root_integrity(sentence):
    toks, _, _ = engine.analyze_sentence(sentence)
    for t in toks:
        assert t.root, f"empty root for surface={t.surface!r}"
        assert len(t.root) >= 2, f"root too short: {t.root!r} for {t.surface!r}"


# ══════════════════════════════════════════════════════════════════════════════
# 4. TEMPLATE INTEGRITY — every token must have a non-empty template
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("sentence", [
    "كَتَبَ الطَّالِبُ الدَّرْسَ",
    "ذَهَبَ الرَّجُلُ إِلَى الْمَدْرَسَةِ",
    "تَعَلَّمَ الطُّلَّابُ اللُّغَةَ",
])
def test_template_integrity(sentence):
    toks, _, _ = engine.analyze_sentence(sentence)
    for t in toks:
        assert t.template, f"empty template for surface={t.surface!r}"


# ══════════════════════════════════════════════════════════════════════════════
# 5. PROCLITIC STRIPPING IN CONTEXT
# ══════════════════════════════════════════════════════════════════════════════

def test_waw_proclitic_in_sentence():
    # وَكَتَبَ: waw conjunction stripped, root=كتب
    toks, _, _ = engine.analyze_sentence("وَكَتَبَ الطَّالِبُ")
    assert toks[0].root == "كتب"
    assert "W" in str(toks[0].clitics)

def test_fa_proclitic_in_sentence():
    # فَذَهَبَ: fa conjunction stripped, root=ذهب
    toks, _, _ = engine.analyze_sentence("فَذَهَبَ الرَّجُلُ")
    assert toks[0].root == "ذهب"
    assert "F" in str(toks[0].clitics)

def test_bi_al_proclitic_in_sentence():
    # بِالْكِتَابِ: bi+al stripped, root=كتب
    toks, _, _ = engine.analyze_sentence("كَتَبَ بِالْكِتَابِ")
    assert toks[1].root == "كتب"
    assert "B" in str(toks[1].clitics)

def test_li_al_proclitic_in_sentence():
    # لِلطَّالِبِ: li+al stripped, root=طلب
    toks, _, _ = engine.analyze_sentence("ذَهَبَ لِلطَّالِبِ")
    assert toks[1].root == "طلب"

def test_wa_al_proclitic_in_sentence():
    # وَالْمَدْرَسَةُ: wa+al stripped, root=درس
    toks, _, _ = engine.analyze_sentence("وَالْمَدْرَسَةُ كَبِيرَةٌ")
    assert toks[0].root == "درس"


# ══════════════════════════════════════════════════════════════════════════════
# 6. NOM_DERIVED DETECTION IN CONTEXT
# ══════════════════════════════════════════════════════════════════════════════

def test_nom_derived_mu_prefix():
    # مُعَلِّمٌ: NOM_DERIVED, root=علم
    toks, _, _ = engine.analyze_sentence("مُعَلِّمٌ كَبِيرٌ")
    assert toks[0].template == "NOM_DERIVED"
    assert toks[0].root == "علم"

def test_nom_derived_maktub():
    # مَكْتُوبٌ: NOM_DERIVED passive participle, root=كتب
    toks, _, _ = engine.analyze_sentence("الدَّرْسُ مَكْتُوبٌ")
    assert toks[1].template == "NOM_DERIVED"
    assert toks[1].root == "كتب"

def test_nom_derived_madrasa():
    # الْمَدْرَسَةِ: NOM_DERIVED place noun, root=درس
    toks, _, _ = engine.analyze_sentence("ذَهَبَ إِلَى الْمَدْرَسَةِ")
    assert toks[2].template == "NOM_DERIVED"
    assert toks[2].root == "درس"

def test_nom_derived_maktaba():
    # الْمَكْتَبَةِ: NOM_DERIVED, root=كتب
    toks, _, _ = engine.analyze_sentence("ذَهَبَ إِلَى الْمَكْتَبَةِ")
    assert toks[2].template == "NOM_DERIVED"
    assert toks[2].root == "كتب"


# ══════════════════════════════════════════════════════════════════════════════
# 7. VERBAL SENTENCE — VERB_TRILATERAL_BARE opener
# ══════════════════════════════════════════════════════════════════════════════

def test_verbal_sentence_form_i():
    toks, _, _ = engine.analyze_sentence("كَتَبَ الطَّالِبُ الدَّرْسَ")
    assert toks[0].template == "VERB_TRILATERAL_BARE"
    assert toks[0].root == "كتب"

def test_verbal_sentence_form_i_qara():
    toks, _, _ = engine.analyze_sentence("قَرَأَ الْوَلَدُ الْقِصَّةَ")
    assert toks[0].template == "VERB_TRILATERAL_BARE"
    assert toks[0].root == "قرء"

def test_verbal_sentence_form_i_dhahaba():
    toks, _, _ = engine.analyze_sentence("ذَهَبَ الرَّجُلُ إِلَى الْمَدْرَسَةِ")
    assert toks[0].template == "VERB_TRILATERAL_BARE"
    assert toks[0].root == "ذهب"


# ══════════════════════════════════════════════════════════════════════════════
# 8. AUGMENTED VERB DETECTION IN CONTEXT
# ══════════════════════════════════════════════════════════════════════════════

def test_form_v_in_sentence():
    # تَعَلَّمَ: Form V, root=علم
    toks, _, _ = engine.analyze_sentence("تَعَلَّمَ الطُّلَّابُ اللُّغَةَ")
    assert toks[0].template == "VERB_AUGMENTED_V_VI"
    assert toks[0].root == "علم"

def test_form_vii_in_sentence():
    # اِنْكَسَرَ: Form VII, root=كسر
    toks, _, _ = engine.analyze_sentence("اِنْكَسَرَ الزُّجَاجُ")
    assert toks[0].template == "VERB_AUGMENTED_VII"
    assert toks[0].root == "كسر"

def test_form_x_in_sentence():
    # اِسْتَخْدَمَ: Form X, root=خدم
    toks, _, _ = engine.analyze_sentence("اِسْتَخْدَمَ الْمُعَلِّمُ الْكِتَابَ")
    assert toks[0].template == "VERB_AUGMENTED_X"
    assert toks[0].root == "خدم"


# ══════════════════════════════════════════════════════════════════════════════
# 9. CLOSED-CLASS INTERCEPT IN CONTEXT
# ══════════════════════════════════════════════════════════════════════════════

def test_prep_ila_in_sentence():
    # إِلَى: CLOSED_CLASS preposition
    toks, _, _ = engine.analyze_sentence("ذَهَبَ إِلَى الْمَدْرَسَةِ")
    prep = toks[1]
    assert prep.template == "CLOSED_CLASS"
    assert prep.root == "إلى"

def test_neg_lam_in_sentence():
    # لَمْ: CLOSED_CLASS negation
    toks, _, _ = engine.analyze_sentence("لَمْ يَكْتُبْ")
    assert toks[0].template == "CLOSED_CLASS"
    assert toks[0].root == "لم"

def test_neg_la_in_sentence():
    # لَا: CLOSED_CLASS negation
    toks, _, _ = engine.analyze_sentence("لَا يَذْهَبُ")
    assert toks[0].template == "CLOSED_CLASS"
    assert toks[0].root == "لا"

def test_qad_in_sentence():
    # قَدْ: CLOSED_CLASS discourse particle
    toks, _, _ = engine.analyze_sentence("قَدْ كَتَبَ")
    assert toks[0].template == "CLOSED_CLASS"
    assert toks[0].root == "قد"


# ══════════════════════════════════════════════════════════════════════════════
# 10. SENTENCE VALIDATOR CONTRACT
# ══════════════════════════════════════════════════════════════════════════════

def test_validator_returns_string_message():
    _, _, msg = engine.analyze_sentence("كَتَبَ الطَّالِبُ")
    assert isinstance(msg, str)
    assert len(msg) > 0

def test_validator_ok_is_bool():
    _, ok, _ = engine.analyze_sentence("كَتَبَ الطَّالِبُ")
    assert isinstance(ok, bool)

def test_surface_preserved():
    # Each token's .surface must match the original word
    sentence = "كَتَبَ الطَّالِبُ الدَّرْسَ"
    words = sentence.split()
    toks, _, _ = engine.analyze_sentence(sentence)
    for tok, word in zip(toks, words):
        assert tok.surface == word
