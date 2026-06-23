"""
test_ar_sentence_grammar.py
---------------------------
Arabic sentence-level grammar tests (اختبارات النحو على مستوى الجملة).

Covers:
  - split_into_sentences: تقسيم النص إلى جمل على علامات الترقيم.
  - disambiguate_pos:    تمييز الفاعل/المبتدأ/الخبر/المضاف إليه/الحال بالسياق.
  - validate_sentence:   حراس بنية الجملة (الفعلية، الاسمية، النواسخ، الإضافة،
                         الصفة، الحال، العطف) مع رسائل رفض بالمصطلحات النحوية.

Run: python -m pytest morph_efficiency_project/tests/ar_morph/test_ar_sentence_grammar.py -v
"""
import os
import sys

import pytest

# add project root to sys.path so we can import the engine module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from morph_efficiency_project.scripts.engines import ArabicEngine
from morph_efficiency_project.scripts.engines.shared import TokenInfo
from morph_efficiency_project.scripts.engines.grammar import ar_grammar


engine = ArabicEngine()


def _tok(surface, pos, **tags):
    return TokenInfo(surface=surface, clitics={}, template="",
                     root="", tags=dict(tags), pos=pos)


# ══════════════════════════════════════════════════════════════════════════════
# 1. SENTENCE SPLITTING
# ══════════════════════════════════════════════════════════════════════════════

def test_split_empty_text_returns_empty_list():
    assert ar_grammar.split_into_sentences("") == []


def test_split_single_sentence_no_terminator():
    sents = ar_grammar.split_into_sentences("كَتَبَ الطالب الدرس")
    assert len(sents) == 1
    assert sents[0] == ["كَتَبَ", "الطالب", "الدرس"]


def test_split_on_arabic_question_mark():
    sents = ar_grammar.split_into_sentences("هل الطالب مجتهد؟ نعم هو كذلك.")
    assert len(sents) == 2


def test_split_on_arabic_semicolon():
    sents = ar_grammar.split_into_sentences("كتب الطالب الدرس؛ ثم ذهب.")
    assert len(sents) == 2


def test_split_on_latin_period():
    sents = ar_grammar.split_into_sentences("ذهب الولد. عاد الرجل.")
    assert len(sents) == 2


def test_split_on_newline():
    sents = ar_grammar.split_into_sentences("كتب الطالب\nعاد الرجل")
    assert len(sents) == 2


# ══════════════════════════════════════════════════════════════════════════════
# 2. POS DISAMBIGUATION — ~25 contextual cases
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("sentence,word_idx,expected_pos", [
    # — الجملة الفعلية: الفعل ثم الفاعل (NOM)
    ("كَتَبَ الطالب الدرس", 0, "VERB"),
    ("كَتَبَ الطالب الدرس", 1, "NOM"),
    # — حرف ناسخ + NOM ⇒ NOM (لا VERB)
    ("إنّ الطالبَ مجتهد", 1, "NOM"),
    # — كان + NOM ⇒ NOM
    ("كان الطالب مجتهدًا", 1, "NOM"),
    # — استفهام + NOM ⇒ NOM
    ("هل الطالب مجتهد", 1, "NOM"),
    # — أداة نفي + فعل ⇒ VERB
    ("لم يكتب الولد", 1, "VERB"),
    # — أداة نفي للفعل المضارع
    ("لن يذهب الرجل", 1, "VERB"),
    # — ال + اسم ⇒ NOM
    ("الكتاب مفيد", 0, "NOM"),
    # — جملة اسمية: مبتدأ NOM
    ("الطالب مجتهد", 0, "NOM"),
    # — بعد كل ⇒ مضاف إليه
    ("كل الطلاب حاضرون", 1, "NOM"),
    # — جملة شرطية
    ("إذا اجتهد الطالب نجح", 1, "VERB"),
    # — حال نكرة منصوبة
    ("جاء الطالب مسرعًا", 0, "VERB"),
    # — صفة بعد الموصوف
    ("الكتاب الجديد مفيد", 1, "ADJ"),
])
def test_disambiguate_pos_cases(sentence, word_idx, expected_pos):
    toks, _, _ = engine.analyze_sentence(sentence)
    assert toks[word_idx].pos == expected_pos, (
        f"expected {expected_pos} at idx {word_idx} of {sentence!r}, "
        f"got {toks[word_idx].pos} (tags={toks[word_idx].tags})"
    )


def test_naasekh_harf_assigns_acc_to_mubtada():
    toks, _, _ = engine.analyze_sentence("إنّ الطالبَ مجتهد")
    assert toks[1].tags.get("case") == "ACC"
    assert toks[1].tags.get("role") == "MUBTADA"


def test_kana_assigns_nom_to_ism_acc_to_khabar():
    toks, _, _ = engine.analyze_sentence("كان الطالب مجتهدًا")
    assert toks[1].tags.get("case") == "NOM"
    assert toks[1].tags.get("role") == "ISM_NASEKH"
    assert toks[2].tags.get("case") == "ACC"
    assert toks[2].tags.get("role") == "KHABAR"


def test_quantifier_assigns_gen_to_mudaf_ilayh():
    toks, _, _ = engine.analyze_sentence("كل الطلاب حاضرون")
    assert toks[1].tags.get("case") == "GEN"
    assert toks[1].tags.get("role") == "MUDAF_ILAYH"


def test_subordinator_assigns_subjunctive():
    toks, _, _ = engine.analyze_sentence("يجب أن يدرس الطالب")
    assert toks[2].tags.get("mood") == "SUBJ"


def test_jussive_after_lam():
    toks, _, _ = engine.analyze_sentence("لم يكتب الولد")
    assert toks[1].tags.get("mood") == "JUS"
    assert toks[1].tags.get("tense") == "PRES"


def test_definite_article_blocks_verb_reading():
    # الكتاب must never be analysed as VERB
    toks, _, _ = engine.analyze_sentence("الكتاب جديد")
    assert toks[0].pos != "VERB"
    assert toks[0].tags.get("def") == "DEF"


def test_fail_after_verb_is_nominative():
    toks, _, _ = engine.analyze_sentence("كَتَبَ الطالب الدرس")
    assert toks[1].tags.get("case") == "NOM"
    assert toks[1].tags.get("role") in ("AGENT", "FAIL")


# ══════════════════════════════════════════════════════════════════════════════
# 3. VALID SENTENCE TYPES PASS
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("sentence", [
    "كَتَبَ الطالب الدرس",          # جملة فعلية
    "الطالب مجتهد",                 # جملة اسمية بسيطة
    "إنّ الطالبَ مجتهد",            # ناسخ حرفي
    "كان الطالب مجتهدًا",           # ناسخ فعلي
    "هل الطالب مجتهد",              # استفهام
    "لم يكتب الولد",                # نفي بالجزم
    "إذا اجتهد الطالب نجح",         # شرط
    "ذَهَبَ الرَّجُلُ إِلَى الْمَدْرَسَةِ",
])
def test_valid_sentences_pass(sentence):
    _, ok, msg = engine.analyze_sentence(sentence)
    assert ok, f"sentence rejected unexpectedly: {sentence!r} → {msg}"


# ══════════════════════════════════════════════════════════════════════════════
# 4. INVALID SENTENCES FAIL WITH ARABIC-TERMINOLOGY MESSAGES
# ══════════════════════════════════════════════════════════════════════════════

def test_inna_with_nominative_mubtada_is_rejected():
    # إنّ تنصب المبتدأ → if مبتدأ is marked NOM the guard must reject.
    toks = [
        _tok("إنّ", "PART"),
        _tok("الطالبُ", "NOM", case="NOM", def_="DEF"),
        _tok("مجتهدٌ", "NOM", case="NOM"),
    ]
    ok, msg = ar_grammar.validate_sentence(toks)
    assert not ok
    assert "إنّ تنصب المبتدأ" in msg


def test_kana_with_nominative_khabar_is_rejected():
    # كان ترفع الاسم وتنصب الخبر → if الخبر is NOM, reject.
    toks = [
        _tok("كان", "VERB"),
        _tok("الطالب", "NOM", case="NOM"),
        _tok("مجتهدٌ", "NOM", case="NOM"),
    ]
    ok, msg = ar_grammar.validate_sentence(toks)
    assert not ok
    assert "كان تنصب الخبر" in msg


def test_verbal_sentence_without_subject_is_rejected():
    # الفعل يطلب فاعلًا يليه → reject VERB followed by non-NOM/PROPER/PRON
    toks = [
        _tok("كَتَبَ", "VERB", tense="PAST", person="3"),
        _tok("بسرعة", "ADV"),
    ]
    ok, msg = ar_grammar.validate_sentence(toks)
    assert not ok
    assert "الفعل يطلب فاعلًا" in msg


def test_empty_sentence_is_ok():
    ok, msg = ar_grammar.validate_sentence([])
    assert ok and msg == "ok"


def test_hal_must_be_indf_acc():
    # If we mark role=HAL but make it DEF → الحال نكرة منصوبة rejection.
    toks = [
        _tok("جاء", "VERB", tense="PAST", person="3"),
        _tok("الطالب", "NOM", case="NOM"),
        _tok("المسرع", "NOM", case="ACC", role="HAL", def_value="DEF"),
    ]
    # Convert key def_value → def (Python keyword)
    toks[2].tags["def"] = "DEF"
    del toks[2].tags["def_value"]
    ok, msg = ar_grammar.validate_sentence(toks)
    assert not ok
    assert "الحال" in msg


def test_conjunction_balanced_rejects_case_mismatch():
    toks = [
        _tok("الطالبُ", "NOM", case="NOM"),
        _tok("ثم", "PART"),
        _tok("المعلمَ", "NOM", case="ACC"),
    ]
    ok, msg = ar_grammar.validate_sentence(toks)
    assert not ok
    assert "المعطوف" in msg


# ══════════════════════════════════════════════════════════════════════════════
# 5. REGRESSION — earlier sentence test suite must still pass
# ══════════════════════════════════════════════════════════════════════════════

def test_regression_classic_verbal_sentence():
    toks, ok, _ = engine.analyze_sentence("كَتَبَ الطَّالِبُ الدَّرْسَ")
    assert ok
    assert len(toks) == 3
    assert toks[0].root == "كتب"


def test_regression_classic_nominal_sentence():
    toks, ok, _ = engine.analyze_sentence("الْكِتَابُ مُفِيدٌ")
    assert ok
    assert len(toks) == 2


def test_regression_proclitic_stripping_preserved():
    toks, _, _ = engine.analyze_sentence("وَكَتَبَ الطَّالِبُ")
    assert toks[0].root == "كتب"
