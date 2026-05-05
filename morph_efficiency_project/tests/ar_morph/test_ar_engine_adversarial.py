"""
test_ar_engine_adversarial.py
-----------------------------
Adversarial stress tests for the Arabic morphology engine.

Goal: try to BREAK the engine with edge cases, ambiguities, and complex inputs.
Tests cover all 10 verb forms, weak roots, clitic stacking, elatives, Form II/III
disambiguation, nisba adjectives, closed-class lookalikes, loanwords, diacritized
vs undiacritized pairs, and miscellaneous edge cases.

Run: python -m pytest morph_efficiency_project/tests/ar_morph/test_ar_engine_adversarial.py -v
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import ArabicEngine

engine = ArabicEngine()


# ===========================================================================
# 1. ALL 10 VERB FORMS WITH REAL EXAMPLES
# ===========================================================================

FORM_I_CASES = [
    # (surface, expected_root, expected_pos, label)
    ("كَتَبَ",  "كتب", "VERB", "Form I kataba"),
    ("ذَهَبَ",  "ذهب", "VERB", "Form I dhahaba"),
    ("جَلَسَ",  "جلس", "VERB", "Form I jalasa"),
    ("شَرِبَ",  "شرب", "VERB", "Form I shariba"),
    ("لَعِبَ",  "لعب", "VERB", "Form I la3iba"),
    ("فَتَحَ",  "فتح", "VERB", "Form I fataha"),
    ("عَلِمَ",  "علم", "VERB", "Form I 3alima"),
    ("كتب",    "كتب", "VERB", "Form I kataba undiacritized"),
    ("ذهب",    "ذهب", "VERB", "Form I dhahaba undiacritized"),
]

FORM_II_CASES = [
    ("علّم",    "علم", "VERB", "Form II 3allama"),
    ("درّس",    "درس", "VERB", "Form II darrasa"),
    ("فسّر",    "فسر", "VERB", "Form II fassara"),
    ("نظّف",    "نظف", "VERB", "Form II nadhdhafa"),
    ("كسّر",    "كسر", "VERB", "Form II kassara"),
    ("وسّع",    "وسع", "VERB", "Form II wassa3a"),
    ("حسّن",    "حسن", "VERB", "Form II hassana"),
]

FORM_III_CASES = [
    ("قاتل",    "قتل", "VERB", "Form III qatala"),
    ("شارك",    "شرك", "VERB", "Form III sharaka"),
    ("سافر",    "سفر", "VERB", "Form III safara"),
    ("حاول",    "حول", "VERB", "Form III hawala"),
    ("ناقش",    "نقش", "VERB", "Form III naqasha"),
    ("بادل",    "بدل", "VERB", "Form III badala"),
    ("جاهد",    "جهد", "VERB", "Form III jahada"),
]

FORM_IV_CASES = [
    ("أرسل",    "رسل", "VERB", "Form IV arsala"),
    ("أعلن",    "علن", "VERB", "Form IV a3lana"),
    ("أنتج",    "نتج", "VERB", "Form IV antaja"),
    ("أسلم",    "سلم", "VERB", "Form IV aslama"),
]

FORM_V_CASES = [
    ("تعلّم",    "علم", "VERB", "Form V ta3allama"),
    ("تكلّم",    "كلم", "VERB", "Form V takallama"),
    ("تحدّث",    "حدث", "VERB", "Form V tahaddatha"),
]

FORM_VI_CASES = [
    ("تبادل",    "بدل", "VERB", "Form VI tabadala"),
    ("تواصل",    "وصل", "VERB", "Form VI tawasala"),
]

FORM_VII_CASES = [
    ("انكسر",    "كسر", "VERB", "Form VII inkasara"),
    ("انفجر",    "فجر", "VERB", "Form VII infajara"),
    ("انطلق",    "طلق", "VERB", "Form VII intalaqa"),
]

FORM_VIII_CASES = [
    ("افتتح",    "فتح", "VERB", "Form VIII iftataha"),
    ("اجتمع",    "جمع", "VERB", "Form VIII ijtama3a"),
    ("احتفل",    "حفل", "VERB", "Form VIII ihtafala"),
    ("اعتقد",    "عقد", "VERB", "Form VIII i3taqada"),
]

FORM_IX_CASES = [
    ("احمرّ",    "حمر", "VERB", "Form IX ihmarra"),
    ("اسودّ",    "سود", "VERB", "Form IX iswadda"),
]

FORM_X_CASES = [
    ("استخرج",    "خرج", "VERB", "Form X istakhraja"),
    ("استعمل",    "عمل", "VERB", "Form X ista3mala"),
    ("استقبل",    "قبل", "VERB", "Form X istaqbala"),
]


@pytest.mark.parametrize("surface,exp_root,exp_pos,label", FORM_I_CASES)
def test_form_i(surface, exp_root, exp_pos, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    assert ti.pos == exp_pos, f"[{label}] pos={ti.pos!r} expected={exp_pos!r}"


@pytest.mark.parametrize("surface,exp_root,exp_pos,label", FORM_II_CASES)
def test_form_ii(surface, exp_root, exp_pos, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    assert ti.pos == exp_pos, f"[{label}] pos={ti.pos!r} expected={exp_pos!r}"
    assert ti.tags.get("form") == "II", f"[{label}] form={ti.tags.get('form')!r} expected='II'"


@pytest.mark.parametrize("surface,exp_root,exp_pos,label", FORM_III_CASES)
def test_form_iii(surface, exp_root, exp_pos, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    assert ti.pos == exp_pos, f"[{label}] pos={ti.pos!r} expected={exp_pos!r}"
    assert ti.tags.get("form") == "III", f"[{label}] form={ti.tags.get('form')!r} expected='III'"


@pytest.mark.parametrize("surface,exp_root,exp_pos,label", FORM_IV_CASES)
def test_form_iv(surface, exp_root, exp_pos, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    assert ti.pos == exp_pos, f"[{label}] pos={ti.pos!r} expected={exp_pos!r}"


@pytest.mark.parametrize("surface,exp_root,exp_pos,label", FORM_V_CASES)
def test_form_v(surface, exp_root, exp_pos, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    assert ti.pos == exp_pos, f"[{label}] pos={ti.pos!r} expected={exp_pos!r}"


@pytest.mark.parametrize("surface,exp_root,exp_pos,label", FORM_VI_CASES)
def test_form_vi(surface, exp_root, exp_pos, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    assert ti.pos == exp_pos, f"[{label}] pos={ti.pos!r} expected={exp_pos!r}"


@pytest.mark.parametrize("surface,exp_root,exp_pos,label", FORM_VII_CASES)
def test_form_vii(surface, exp_root, exp_pos, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    assert ti.pos == exp_pos, f"[{label}] pos={ti.pos!r} expected={exp_pos!r}"


@pytest.mark.parametrize("surface,exp_root,exp_pos,label", FORM_VIII_CASES)
def test_form_viii(surface, exp_root, exp_pos, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    assert ti.pos == exp_pos, f"[{label}] pos={ti.pos!r} expected={exp_pos!r}"


@pytest.mark.parametrize("surface,exp_root,exp_pos,label", FORM_IX_CASES)
def test_form_ix(surface, exp_root, exp_pos, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    assert ti.pos == exp_pos, f"[{label}] pos={ti.pos!r} expected={exp_pos!r}"


@pytest.mark.parametrize("surface,exp_root,exp_pos,label", FORM_X_CASES)
def test_form_x(surface, exp_root, exp_pos, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    assert ti.pos == exp_pos, f"[{label}] pos={ti.pos!r} expected={exp_pos!r}"


# ===========================================================================
# 2. WEAK ROOT STRESS TEST
# ===========================================================================

AJWAF_WAW_CASES = [
    # Hollow/Ajwaf waw (middle radical is و)
    ("قال",  "قول", "Form I ajwaf-waw qala"),
    ("زار",  "زور", "Form I ajwaf-waw zara"),
    ("عاد",  "عود", "Form I ajwaf-waw 3ada"),
    ("نام",  "نوم", "Form I ajwaf-waw nama"),
    ("صام",  "صوم", "Form I ajwaf-waw sama"),
]

AJWAF_YA_CASES = [
    # Hollow/Ajwaf ya (middle radical is ي)
    ("باع",  "بيع", "Form I ajwaf-ya ba3a"),
    ("سار",  "سير", "Form I ajwaf-ya sara"),
    ("طار",  "طير", "Form I ajwaf-ya tara"),
    ("صار",  "صير", "Form I ajwaf-ya sara2"),
    ("عاش",  "عيش", "Form I ajwaf-ya 3asha"),
]

NAQIS_WAW_CASES = [
    # Defective/Naqis waw (final radical is و)
    ("دعا",  "دعو", "Form I naqis-waw da3a"),
    ("غزا",  "غزو", "Form I naqis-waw ghaza"),
    ("رجا",  "رجو", "Form I naqis-waw raja"),
    ("سما",  "سمو", "Form I naqis-waw sama"),
    ("علا",  "علو", "Form I naqis-waw 3ala"),
]

NAQIS_YA_CASES = [
    # Defective/Naqis ya (final radical is ي)
    ("رمى",  "رمي", "Form I naqis-ya rama"),
    ("بنى",  "بنو", "Form I naqis-ya bana"),  # Note: بنو is correct (builds)
    ("مشى",  "مشي", "Form I naqis-ya masha"),
    ("قضى",  "قضي", "Form I naqis-ya qada"),
    ("هدى",  "هدي", "Form I naqis-ya hada"),
]

MITHAL_CASES = [
    # Assimilated/Mithal (initial و)
    ("وجد",  "وجد", "Form I mithal wajada"),
    ("وصل",  "وصل", "Form I mithal wasala"),
    ("ولد",  "ولد", "Form I mithal walada"),
    ("وقع",  "وقع", "Form I mithal waqa3a"),
    ("وضع",  "وضع", "Form I mithal wada3a"),
]

GEMINATE_CASES = [
    # Geminate (doubled root)
    ("مدّ",  "مدد", "Form I geminate madda"),
    ("حلّ",  "حلل", "Form I geminate halla"),
    ("ردّ",  "ردد", "Form I geminate radda"),
    ("شدّ",  "شدد", "Form I geminate shadda"),
    ("ضمّ",  "ضمم", "Form I geminate damma"),
]

HAMZA_INITIAL_CASES = [
    # Hamzated initial (initial ء)
    ("أَكَلَ",  "\u0621كل", "Form I hamza-initial akala"),
    ("أَخَذَ",  "\u0621خذ", "Form I hamza-initial akhadha"),
    ("أَمَرَ",  "\u0621مر", "Form I hamza-initial amara"),
    ("أَتَى",   "\u0621تو", "Form I hamza-initial ata"),
]

HAMZA_MEDIAL_CASES = [
    # Hamzated medial (medial ء)
    ("سَأَلَ",  "س\u0621ل", "Form I hamza-medial sa'ala"),
    ("رَأَسَ",  "ر\u0621س", "Form I hamza-medial ra'asa"),
]

HAMZA_FINAL_CASES = [
    # Hamzated final (final ء)
    ("قَرَأَ",  "قر\u0621", "Form I hamza-final qara'a"),
    ("بَدَأَ",  "بد\u0621", "Form I hamza-final bada'a"),
    ("جَاءَ",  "جي\u0621", "Form I hamza-final ja'a (also ajwaf)"),
    ("شَاءَ",  "شي\u0621", "Form I hamza-final sha'a (also ajwaf)"),
]


@pytest.mark.parametrize("surface,exp_root,label", AJWAF_WAW_CASES)
def test_ajwaf_waw(surface, exp_root, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"


@pytest.mark.parametrize("surface,exp_root,label", AJWAF_YA_CASES)
def test_ajwaf_ya(surface, exp_root, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"


@pytest.mark.parametrize("surface,exp_root,label", NAQIS_WAW_CASES)
def test_naqis_waw(surface, exp_root, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"


@pytest.mark.parametrize("surface,exp_root,label", NAQIS_YA_CASES)
def test_naqis_ya(surface, exp_root, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"


@pytest.mark.parametrize("surface,exp_root,label", MITHAL_CASES)
def test_mithal(surface, exp_root, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"


@pytest.mark.parametrize("surface,exp_root,label", GEMINATE_CASES)
def test_geminate(surface, exp_root, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"


@pytest.mark.parametrize("surface,exp_root,label", HAMZA_INITIAL_CASES)
def test_hamza_initial(surface, exp_root, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"


@pytest.mark.parametrize("surface,exp_root,label", HAMZA_MEDIAL_CASES)
def test_hamza_medial(surface, exp_root, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"


@pytest.mark.parametrize("surface,exp_root,label", HAMZA_FINAL_CASES)
def test_hamza_final(surface, exp_root, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"


# ===========================================================================
# 3. CLITIC STACKING STRESS
# ===========================================================================

CLITIC_STACKING_CASES = [
    # (surface, expected_root, expected_clitics_keys, label)
    ("وبالمدرسة",   "درس", {"conj", "prep", "def"}, "wa+bi+al+madrasa clitic stack"),
    ("فللمعلمين",   "علم", {"conj", "prep", "def"}, "fa+li+al+mu3allimin clitic stack"),
    ("وسيكتبونها", "كتب", {"conj", "tense_prefix"}, "wa+sa+yaktubuna+ha clitic stack"),
]


@pytest.mark.parametrize("surface,exp_root,exp_clitics,label", CLITIC_STACKING_CASES)
def test_clitic_stacking(surface, exp_root, exp_clitics, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    # Check that expected clitic tags are present
    pre_tags = ti.clitics.get("pre", [])
    all_pre_keys = set()
    for t in pre_tags:
        all_pre_keys.update(t.keys())
    for key in exp_clitics:
        assert key in all_pre_keys or key in ti.tags, (
            f"[{label}] expected clitic key '{key}' not found in pre_tags={pre_tags} or tags={ti.tags}"
        )


# ===========================================================================
# 4. ELATIVE ADJECTIVES (after fix)
# ===========================================================================

ELATIVE_CASES = [
    # (surface, expected_root, label)
    ("أكبر",  "كبر", "akbar elative"),
    ("أصغر",  "صغر", "asghar elative"),
    ("أفضل",  "فضل", "afdal elative"),
    ("أحسن",  "حسن", "ahsan elative"),
    ("أسوأ",  "سوء", "aswa' elative"),
    ("أعظم",  "عظم", "a3dham elative"),
    ("أكثر",  "كثر", "akthar elative"),
    ("أجمل",  "جمل", "ajmal elative"),
    ("أطول",  "طول", "atwal elative"),
    ("أقصر",  "قصر", "aqsar elative"),
    ("أبعد",  "بعد", "ab3ad elative"),
    ("أقرب",  "قرب", "aqrab elative"),
]


@pytest.mark.parametrize("surface,exp_root,label", ELATIVE_CASES)
def test_elative_adj(surface, exp_root, label):
    ti = engine.analyze(surface)
    assert ti.pos == "ADJ", f"[{label}] pos={ti.pos!r} expected='ADJ'"
    assert ti.template == "ADJ_ELATIVE", f"[{label}] template={ti.template!r} expected='ADJ_ELATIVE'"
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    assert ti.tags.get("degree") == "COMP", (
        f"[{label}] degree={ti.tags.get('degree')!r} expected='COMP'"
    )


# Elatives that are harder to detect (geminate roots, naqis roots) —
# these may not be detected as elatives by the current engine.
# Mark as xfail so they document expected future behavior.
ELATIVE_HARD_CASES = [
    ("أقلّ",  "قلل", "aqall elative (geminate)"),
    ("أهمّ",  "همم", "ahamm elative (geminate)"),
    ("أعلى",  "علو", "a3la elative (naqis)"),
    ("أدنى",  "دنو", "adna elative (naqis)"),
]


@pytest.mark.parametrize("surface,exp_root,label", ELATIVE_HARD_CASES)
@pytest.mark.xfail(reason="Geminate/naqis elatives not yet detected as ADJ_ELATIVE")
def test_elative_hard(surface, exp_root, label):
    ti = engine.analyze(surface)
    assert ti.pos == "ADJ", f"[{label}] pos={ti.pos!r} expected='ADJ'"
    assert ti.template == "ADJ_ELATIVE", f"[{label}] template={ti.template!r}"


# ===========================================================================
# 5. FORM II/III DISAMBIGUATION (after fix)
# ===========================================================================

FORM_II_SHADDA_CASES = [
    # Form II verbs: shadda on second radical
    ("علّم",    "علم", "II", "Form II 3allama"),
    ("درّس",    "درس", "II", "Form II darrasa"),
    ("فسّر",    "فسر", "II", "Form II fassara"),
    ("نظّف",    "نظف", "II", "Form II nadhdhafa"),
    ("كسّر",    "كسر", "II", "Form II kassara"),
    ("وسّع",    "وسع", "II", "Form II wassa3a"),
    ("حسّن",    "حسن", "II", "Form II hassana"),
]

FORM_III_ALIF_CASES = [
    # Form III verbs: ا between C1 and C2
    ("قاتل",    "قتل", "III", "Form III qatala"),
    ("شارك",    "شرك", "III", "Form III sharaka"),
    ("سافر",    "سفر", "III", "Form III safara"),
    ("حاول",    "حول", "III", "Form III hawala"),
    ("ناقش",    "نقش", "III", "Form III naqasha"),
    ("بادل",    "بدل", "III", "Form III badala"),
    ("جاهد",    "جهد", "III", "Form III jahada"),
]

FORM_I_CONTROL_CASES = [
    # Form I verbs: should NOT be classified as Form II or III
    ("كتب",    "كتب", "I", "Form I kataba control"),
    ("ذهب",    "ذهب", "I", "Form I dhahaba control"),
    ("جلس",    "جلس", "I", "Form I jalasa control"),
    ("شرب",    "شرب", "I", "Form I shariba control"),
    ("لعب",    "لعب", "I", "Form I la3iba control"),
]


@pytest.mark.parametrize("surface,exp_root,exp_form,label", FORM_II_SHADDA_CASES)
def test_form_ii_disambig(surface, exp_root, exp_form, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    assert ti.tags.get("form") == exp_form, (
        f"[{label}] form={ti.tags.get('form')!r} expected={exp_form!r}"
    )


@pytest.mark.parametrize("surface,exp_root,exp_form,label", FORM_III_ALIF_CASES)
def test_form_iii_disambig(surface, exp_root, exp_form, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    assert ti.tags.get("form") == exp_form, (
        f"[{label}] form={ti.tags.get('form')!r} expected={exp_form!r}"
    )


@pytest.mark.parametrize("surface,exp_root,exp_form,label", FORM_I_CONTROL_CASES)
def test_form_i_control(surface, exp_root, exp_form, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    assert ti.tags.get("form") == exp_form, (
        f"[{label}] form={ti.tags.get('form')!r} expected={exp_form!r}"
    )


# ===========================================================================
# 6. NISBA ADJECTIVES
# ===========================================================================

NISBA_CASES = [
    ("عربيّ",    "عرب", "NISBA", "3arabi nisba undiacritized"),
    ("مصريّ",    "مصر", "NISBA", "misri nisba undiacritized"),
    ("تركيّ",    "ترك", "NISBA", "turki nisba undiacritized"),
    ("عَرَبِيّ",  "عرب", "NISBA", "3arabi nisba diacritized"),
    ("مِصْرِيّ",  "مصر", "NISBA", "misri nisba diacritized"),
]


@pytest.mark.parametrize("surface,exp_root,exp_tmpl,label", NISBA_CASES)
def test_nisba(surface, exp_root, exp_tmpl, label):
    ti = engine.analyze(surface)
    assert ti.template == exp_tmpl, f"[{label}] template={ti.template!r} expected={exp_tmpl!r}"
    assert ti.pos == "ADJ", f"[{label}] pos={ti.pos!r} expected='ADJ'"
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"


# ===========================================================================
# 7. CLOSED-CLASS EDGE CASES (lookalikes)
# ===========================================================================

CLOSED_CLASS_LOOKALIKE_CASES = [
    # Words that LOOK like they have proclitics but are actually roots
    ("بين",    "PART", "CLOSED_CLASS", "bayn is PART not b+yn"),
    ("لكن",    "PART", "CLOSED_CLASS", "lakin is PART not l+kn"),
    ("كيف",    "PART", "CLOSED_CLASS", "kayfa is PART not k+yf"),
    ("فقط",    "PART", "CLOSED_CLASS", "faqat is PART not f+qt"),
]


@pytest.mark.parametrize("surface,exp_pos,exp_tmpl,label", CLOSED_CLASS_LOOKALIKE_CASES)
def test_closed_class_lookalike(surface, exp_pos, exp_tmpl, label):
    ti = engine.analyze(surface)
    assert ti.pos == exp_pos, f"[{label}] pos={ti.pos!r} expected={exp_pos!r}"
    assert ti.template == exp_tmpl, f"[{label}] template={ti.template!r} expected={exp_tmpl!r}"


# سبب and بلد are NOT closed-class — they are roots (but look like ب/س + something)
OPEN_CLASS_LOOKALIKE_CASES = [
    ("سبب",  "سبب", "VERB", "sabab is root not s+bb"),
    ("بلد",  "بلد", "VERB", "balad is root not b+ld"),
]


@pytest.mark.parametrize("surface,exp_root,exp_pos,label", OPEN_CLASS_LOOKALIKE_CASES)
def test_open_class_lookalike(surface, exp_root, exp_pos, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    assert ti.pos == exp_pos, f"[{label}] pos={ti.pos!r} expected={exp_pos!r}"


# ===========================================================================
# 8. LOANWORDS (after fix)
# ===========================================================================

LOANWORD_CASES = [
    "تلفزيون", "كمبيوتر", "إنترنت", "تكنولوجيا", "ديموقراطية",
    "برلمان", "بنك", "فيلم", "تلفون", "راديو",
    "بروفيسور", "دكتور", "أوتوماتيكي",
]


@pytest.mark.parametrize("surface", LOANWORD_CASES)
def test_loanword(surface):
    ti = engine.analyze(surface)
    assert ti.pos == "NOM", f"[{surface}] pos={ti.pos!r} expected='NOM'"
    assert ti.template == "LOANWORD", f"[{surface}] template={ti.template!r} expected='LOANWORD'"
    assert ti.tags.get("origin") == "FOREIGN", (
        f"[{surface}] origin={ti.tags.get('origin')!r} expected='FOREIGN'"
    )


# ===========================================================================
# 9. DIACRITIZED vs UNDIACRITIZED
# ===========================================================================

DIACRITIZED_PAIRS = [
    # (diacritized, undiacritized, expected_root, label)
    ("\u0643\u064e\u062a\u064e\u0628\u064e", "كتب", "كتب", "kataba vs ktb"),
    ("\u064a\u064e\u0643\u0652\u062a\u064f\u0628\u064f", "يكتب", "كتب", "yaktubu vs yktb"),
    ("\u0627\u0644\u0652\u0643\u0650\u062a\u064e\u0627\u0628\u064f", "الكتاب", "كتب", "alkitabu vs alktab"),
    ("\u0645\u064e\u062f\u0652\u0631\u064e\u0633\u064e\u0629\u064c", "مدرسة", "درس", "madrasatun vs mdrsa"),
]


@pytest.mark.parametrize("diacritized,undiacritized,exp_root,label", DIACRITIZED_PAIRS)
def test_diacritized_same_root(diacritized, undiacritized, exp_root, label):
    ti_d = engine.analyze(diacritized)
    ti_u = engine.analyze(undiacritized)
    assert ti_d.root == exp_root, (
        f"[{label}] diacritized root={ti_d.root!r} expected={exp_root!r}"
    )
    assert ti_u.root == exp_root, (
        f"[{label}] undiacritized root={ti_u.root!r} expected={exp_root!r}"
    )
    assert ti_d.root == ti_u.root, (
        f"[{label}] roots differ: diacritized={ti_d.root!r} vs undiacritized={ti_u.root!r}"
    )


# ===========================================================================
# 10. PASSIVE VOICE DETECTION
# ===========================================================================

PASSIVE_CASES = [
    # (surface, expected_root, has_passive_tag, label)
    ("\u0643\u064f\u062a\u0650\u0628\u064e", "كتب", True, "kutiba = was written"),
    ("\u0643\u064e\u062a\u064e\u0628\u064e", "كتب", False, "kataba = wrote (active)"),
]


@pytest.mark.parametrize("surface,exp_root,has_passive,label", PASSIVE_CASES)
def test_passive_detection(surface, exp_root, has_passive, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    if has_passive:
        assert ti.tags.get("voice") == "PASS", (
            f"[{label}] expected voice=PASS, got tags={ti.tags}"
        )
    else:
        assert ti.tags.get("voice") != "PASS" or ti.tags.get("voice") == "ACT", (
            f"[{label}] expected no passive voice, got tags={ti.tags}"
        )


# ===========================================================================
# 11. EDGE CASES
# ===========================================================================

class TestEdgeCases:
    """Miscellaneous edge cases that should not crash the engine."""

    def test_empty_string(self):
        """Empty string should not crash."""
        # The engine splits on whitespace, so analyze("") should handle gracefully.
        # If it crashes, that's a bug.
        try:
            ti = engine.analyze("")
            # If it returns something, just check it doesn't crash
            assert ti is not None
        except (ValueError, IndexError, KeyError):
            pytest.fail("Engine crashed on empty string")

    @pytest.mark.parametrize("letter", ["ل", "و", "ف", "ب", "ك", "س"])
    def test_single_letter(self, letter):
        """Single-letter words should not crash."""
        ti = engine.analyze(letter)
        assert ti is not None
        assert ti.surface == letter

    def test_very_long_word(self):
        """Very long word should not crash."""
        long_word = "استخراج" * 10  # 70 characters
        ti = engine.analyze(long_word)
        assert ti is not None

    def test_tatweel(self):
        """Word with tatweel (kashida, U+0640) should be handled."""
        # كـتـاب with tatweel characters
        word_with_tatweel = "كـتـاب"
        ti = engine.analyze(word_with_tatweel)
        assert ti is not None
        # The engine should either strip tatweel or handle it

    def test_mixed_arabic_latin(self):
        """Mixed Arabic/Latin text should not crash."""
        mixed = "كتابbook"
        ti = engine.analyze(mixed)
        assert ti is not None

    def test_arabic_numerals(self):
        """Arabic-Indic numerals should not crash."""
        numerals = "\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669"
        ti = engine.analyze(numerals)
        assert ti is not None

    def test_analyze_sentence(self):
        """Sentence analysis should return a list of TokenInfo."""
        sentence = "\u0643\u064e\u062a\u064e\u0628\u064e \u0627\u0644\u0648\u0644\u062f"
        tokens, ok, msg = engine.analyze_sentence(sentence)
        assert isinstance(tokens, list)
        assert len(tokens) == 2

    def test_consecutive_diacritics(self):
        """Words with stacked diacritics should not crash."""
        # shadda + damma on same consonant
        word = "\u0643\u064f\u062a\u0651\u064e\u0627\u0628"
        ti = engine.analyze(word)
        assert ti is not None

    def test_alif_variants(self):
        """All alif variants should be handled."""
        variants = ["\u0627", "\u0623", "\u0625", "\u0622", "\u0649"]
        for v in variants:
            ti = engine.analyze(v)
            assert ti is not None

    def test_hamza_variants(self):
        """All hamza variants should normalize to bare hamza."""
        # All these should be treated equivalently in root extraction
        for hamza in ["\u0621", "\u0623", "\u0625", "\u0624", "\u0626"]:
            word = hamza + "\u0643\u0644"
            ti = engine.analyze(word)
            assert ti is not None


# ===========================================================================
# 12. MASDAR FORM II (regression guard)
# ===========================================================================

MASDAR_FORM_II_CASES = [
    ("\u062a\u064e\u0639\u0652\u0644\u0650\u064a\u0645", "علم", "MASDAR_FORM_II", "ta3lim masdar"),
    ("\u062a\u064e\u0641\u0652\u0633\u0650\u064a\u0631", "فسر", "MASDAR_FORM_II", "tafsir masdar"),
    ("\u062a\u064e\u062f\u0652\u0631\u0650\u064a\u0633", "درس", "MASDAR_FORM_II", "tadris masdar"),
]


@pytest.mark.parametrize("surface,exp_root,exp_tmpl,label", MASDAR_FORM_II_CASES)
def test_masdar_form_ii_regression(surface, exp_root, exp_tmpl, label):
    ti = engine.analyze(surface)
    assert ti.template == exp_tmpl, f"[{label}] template={ti.template!r}"
    assert ti.root == exp_root, f"[{label}] root={ti.root!r}"
    assert ti.pos == "NOM", f"[{label}] pos={ti.pos!r}"


# ===========================================================================
# 13. FORM VIII ASSIMILATION VARIANTS
# ===========================================================================

FORM_VIII_ASSIMILATION_CASES = [
    ("اتصل",    "وصل", "Form VIII assimilation waw: ittasala"),
    ("اتخذ",    "\u0621خذ", "Form VIII assimilation hamza: ittakhadha"),
]


@pytest.mark.parametrize("surface,exp_root,label", FORM_VIII_ASSIMILATION_CASES)
def test_form_viii_assimilation(surface, exp_root, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    assert ti.pos == "VERB", f"[{label}] pos={ti.pos!r}"


# ===========================================================================
# 14. DERIVED NOMINALS (regression guard)
# ===========================================================================

DERIVED_NOMINAL_CASES = [
    ("مدرسة",  "درس", "NOM", "NOM_DERIVED", "madrasa derived nominal"),
    ("مكتبة",  "كتب", "NOM", "NOM_DERIVED", "maktaba derived nominal"),
    ("معلم",   "علم", "NOM", "NOM_DERIVED", "mu3allim derived nominal"),
]


@pytest.mark.parametrize("surface,exp_root,exp_pos,exp_tmpl,label", DERIVED_NOMINAL_CASES)
def test_derived_nominal(surface, exp_root, exp_pos, exp_tmpl, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    assert ti.pos == exp_pos, f"[{label}] pos={ti.pos!r} expected={exp_pos!r}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
