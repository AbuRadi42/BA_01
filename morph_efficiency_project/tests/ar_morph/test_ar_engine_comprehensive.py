"""
test_ar_engine_comprehensive.py
-------------------------------
Edge-case-inclusive Arabic morphology engine test suite.

Coverage targets (each section is one pytest category):
  1. Verbal Forms I-X (الماضي، المضارع، الأمر، المنصوب، المجزوم، المبني للمجهول)
  2. Verbal Forms XI-XII (rare augmented: احمارّ، اخشوشن)
  3. Weak roots: ناقص، أجوف، مثال، مهموز، مضعّف and their derived forms
  4. Masdar patterns: 40+ awzān
  5. Broken plurals (diptote + triptote)
  6. Active / passive participles per form
  7. Derived nominal templates (AGENT, PATIENT, INSTRUMENT, PLACE, SIFA,
     MUBALAGHAH, DIMINUTIVE, ELATIVE, NISBA)
  8. Clitic stacking (proclitic clusters + enclitic pronoun paradigm + circumfix)
  9. Closed-class particles (each subcategory)
 10. Hamza variants (أ، إ، آ، ؤ، ئ -> ء)
 11. Number-like and foreign surfaces
 12. Wazn-semantic-class lookup (ar_templates.json:semantic_role coverage)

Expected values reflect the LINGUISTICALLY CORRECT analysis, not the engine's
current behavior. Failures surface real bugs.

Per case we assert a subset of (pos, root, template, tags subset). A missing
field in the expectation means "do not check". Each case is parametrized so
pytest -v gives a per-case line.

Run:
  python -X utf8 -m pytest morph_efficiency_project/tests/ar_morph/test_ar_engine_comprehensive.py -v
"""
from __future__ import annotations

import os
import sys
from typing import Dict, Optional, Tuple

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from morph_efficiency_project.scripts.engines import ArabicEngine  # noqa: E402

engine = ArabicEngine()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _check(
    surface: str,
    *,
    pos: Optional[str] = None,
    root: Optional[str] = None,
    template: Optional[str] = None,
    template_in: Optional[Tuple[str, ...]] = None,
    tags_subset: Optional[Dict[str, str]] = None,
    tags_absent: Optional[Tuple[str, ...]] = None,
    label: str = "",
):
    """Assert engine output matches the linguistically-correct expectation.

    Any field set to None is skipped. tags_subset requires those k/v pairs
    to be present; tags_absent requires those keys to be missing.
    """
    ti = engine.analyze(surface)
    msgs = []
    if pos is not None and ti.pos != pos:
        msgs.append(f"pos={ti.pos!r} expected {pos!r}")
    if root is not None and ti.root != root:
        msgs.append(f"root={ti.root!r} expected {root!r}")
    if template is not None and ti.template != template:
        msgs.append(f"template={ti.template!r} expected {template!r}")
    if template_in is not None and ti.template not in template_in:
        msgs.append(f"template={ti.template!r} expected one of {template_in!r}")
    if tags_subset:
        for k, v in tags_subset.items():
            if ti.tags.get(k) != v:
                msgs.append(f"tags[{k}]={ti.tags.get(k)!r} expected {v!r}")
    if tags_absent:
        for k in tags_absent:
            if k in ti.tags:
                msgs.append(f"tags[{k}]={ti.tags[k]!r} should be absent")
    assert not msgs, f"[{label or surface}] " + " | ".join(msgs)


# ═════════════════════════════════════════════════════════════════════════════
# 1. VERBAL FORMS I-X across tense, voice, mood
# ═════════════════════════════════════════════════════════════════════════════

VERB_FORMS_I_X = [
    # ── Form I ─────────────────────────────────────────────────────────────
    ("كَتَبَ",     "VERB", "كتب", {"form": "I", "tense": "PAST", "voice": "ACT"},
        "F-I past active"),
    ("يَكْتُبُ",   "VERB", "كتب", {"form": "I", "tense": "PRES", "voice": "ACT"},
        "F-I imperfect indicative"),
    ("كُتِبَ",     "VERB", "كتب", {"form": "I", "tense": "PAST", "voice": "PASS"},
        "F-I past passive"),
    ("يُكْتَبُ",   "VERB", "كتب", {"form": "I", "tense": "PRES", "voice": "PASS"},
        "F-I imperfect passive"),
    ("اُكْتُبْ",   "VERB", "كتب", {"form": "I", "tense": "IMP", "voice": "ACT", "person": "2"},
        "F-I imperative"),
    ("اُدْرُسْ",   "VERB", "درس", {"form": "I", "tense": "IMP", "voice": "ACT", "person": "2"},
        "F-I imperative udrus"),
    ("اِجْلِسْ",   "VERB", "جلس", {"form": "I", "tense": "IMP", "voice": "ACT", "person": "2"},
        "F-I imperative ijlis"),
    ("لَمْ يَكْتُبْ", None, None, None,
        "F-I jussive context (composite, doc-only)"),
    ("يَكْتُبْ",   "VERB", "كتب", {"form": "I", "tense": "PRES", "mood": "JUS"},
        "F-I jussive standalone"),
    ("يَكْتُبَ",   "VERB", "كتب", {"form": "I", "tense": "PRES", "mood": "SUBJ"},
        "F-I subjunctive"),
    # ── Form II ────────────────────────────────────────────────────────────
    ("عَلَّمَ",    "VERB", "علم", {"form": "II", "tense": "PAST", "voice": "ACT"},
        "F-II past active"),
    ("يُعَلِّمُ",  "VERB", "علم", {"form": "II", "tense": "PRES", "voice": "ACT"},
        "F-II imperfect"),
    ("عُلِّمَ",    "VERB", "علم", {"form": "II", "tense": "PAST", "voice": "PASS"},
        "F-II past passive"),
    ("دَرَّسَ",    "VERB", "درس", {"form": "II", "tense": "PAST", "voice": "ACT"},
        "F-II darrasa"),
    # ── Form III ───────────────────────────────────────────────────────────
    ("قَاتَلَ",    "VERB", "قتل", {"form": "III", "tense": "PAST", "voice": "ACT"},
        "F-III qatala"),
    ("يُقَاتِلُ",  "VERB", "قتل", {"form": "III", "tense": "PRES", "voice": "ACT"},
        "F-III imperfect"),
    ("شَارَكَ",    "VERB", "شرك", {"form": "III", "tense": "PAST", "voice": "ACT"},
        "F-III sharaka"),
    # ── Form IV ────────────────────────────────────────────────────────────
    ("أَنْجَزَ",   "VERB", "نجز", {"form": "IV", "tense": "PAST", "voice": "ACT"},
        "F-IV anjaza"),
    ("يُنْجِزُ",   "VERB", "نجز", {"form": "IV", "tense": "PRES", "voice": "ACT"},
        "F-IV imperfect"),
    ("أُنْجِزَ",   "VERB", "نجز", {"form": "IV", "tense": "PAST", "voice": "PASS"},
        "F-IV past passive"),
    # ── Form V ─────────────────────────────────────────────────────────────
    ("تَعَلَّمَ",  "VERB", "علم", {"form": "V", "tense": "PAST", "voice": "ACT"},
        "F-V ta3allama"),
    ("يَتَعَلَّمُ", "VERB", "علم", {"form": "V", "tense": "PRES", "voice": "ACT"},
        "F-V imperfect"),
    ("تَدَرَّبَ",  "VERB", "درب", {"form": "V", "tense": "PAST", "voice": "ACT"},
        "F-V tadarraba"),
    # ── Form VI ────────────────────────────────────────────────────────────
    ("تَبَادَلَ",  "VERB", "بدل", {"form": "VI", "tense": "PAST", "voice": "ACT"},
        "F-VI tabadala"),
    ("يَتَبَادَلُ", "VERB", "بدل", {"form": "VI", "tense": "PRES", "voice": "ACT"},
        "F-VI imperfect"),
    ("تَعَاوَنَ",  "VERB", "عون", {"form": "VI", "tense": "PAST", "voice": "ACT"},
        "F-VI ta3awana ajwaf"),
    # ── Form VII ───────────────────────────────────────────────────────────
    ("اِنْفَجَرَ", "VERB", "فجر", {"form": "VII", "tense": "PAST", "voice": "ACT"},
        "F-VII infajara"),
    ("يَنْفَجِرُ", "VERB", "فجر", {"form": "VII", "tense": "PRES", "voice": "ACT"},
        "F-VII imperfect"),
    ("اِنْسَحَبَ", "VERB", "سحب", {"form": "VII", "tense": "PAST", "voice": "ACT"},
        "F-VII insahaba"),
    # ── Form VIII ──────────────────────────────────────────────────────────
    ("اِجْتَمَعَ", "VERB", "جمع", {"form": "VIII", "tense": "PAST", "voice": "ACT"},
        "F-VIII ijtama3a"),
    ("يَجْتَمِعُ", "VERB", "جمع", {"form": "VIII", "tense": "PRES", "voice": "ACT"},
        "F-VIII imperfect"),
    ("اِعْتَقَدَ", "VERB", "عقد", {"form": "VIII", "tense": "PAST", "voice": "ACT"},
        "F-VIII i3taqada"),
    # ── Form IX ────────────────────────────────────────────────────────────
    ("اِحْمَرَّ",  "VERB", "حمر", {"form": "IX", "tense": "PAST", "voice": "ACT"},
        "F-IX ihmarra"),
    ("اِسْوَدَّ",  "VERB", "سود", {"form": "IX", "tense": "PAST", "voice": "ACT"},
        "F-IX iswadda"),
    # ── Form X ─────────────────────────────────────────────────────────────
    ("اِسْتَخْرَجَ", "VERB", "خرج", {"form": "X", "tense": "PAST", "voice": "ACT"},
        "F-X istakhraja"),
    ("يَسْتَخْرِجُ", "VERB", "خرج", {"form": "X", "tense": "PRES", "voice": "ACT"},
        "F-X imperfect"),
    ("اِسْتَعْمَلَ", "VERB", "عمل", {"form": "X", "tense": "PAST", "voice": "ACT"},
        "F-X ista3mala"),
    ("اِسْتَغْفَرَ", "VERB", "غفر", {"form": "X", "tense": "PAST", "voice": "ACT"},
        "F-X istaghfara"),
]


@pytest.mark.parametrize("surface,pos,root,tags,label", VERB_FORMS_I_X)
def test_verb_forms_I_X(surface, pos, root, tags, label):
    if pos is None:
        pytest.skip(f"composite doc-only: {label}")
    _check(surface, pos=pos, root=root, tags_subset=tags, label=label)


# ═════════════════════════════════════════════════════════════════════════════
# 2. VERBAL FORMS XI-XII (rare augmented)
# ═════════════════════════════════════════════════════════════════════════════

VERB_FORMS_XI_XII = [
    ("اِحْمَارَّ",  "VERB", "حمر", {"form": "XI", "tense": "PAST", "voice": "ACT"},
        "F-XI ihmaarra"),
    ("اِخْشَوْشَنَ", "VERB", "خشن", {"form": "XII", "tense": "PAST", "voice": "ACT"},
        "F-XII ikhshawshana"),
]


@pytest.mark.parametrize("surface,pos,root,tags,label", VERB_FORMS_XI_XII)
def test_verb_forms_XI_XII(surface, pos, root, tags, label):
    _check(surface, pos=pos, root=root, tags_subset=tags, label=label)


# ═════════════════════════════════════════════════════════════════════════════
# 3. WEAK-ROOT PARADIGMS
# ═════════════════════════════════════════════════════════════════════════════

WEAK_ROOTS = [
    # ── ناقص (final-weak) ─────────────────────────────────────────────────
    ("دَعَا",   "VERB", "دعو", {"form": "I", "tense": "PAST", "voice": "ACT"}, "naqis da3a"),
    ("رَمَى",   "VERB", "رمي", {"form": "I", "tense": "PAST", "voice": "ACT"}, "naqis rama"),
    ("نَسِيَ",  "VERB", "نسي", {"form": "I", "tense": "PAST", "voice": "ACT"}, "naqis nasiya"),
    ("بَقِيَ",  "VERB", "بقي", {"form": "I", "tense": "PAST", "voice": "ACT"}, "naqis baqiya"),
    ("يَدْعُو", "VERB", "دعو", {"form": "I", "tense": "PRES", "voice": "ACT"}, "naqis imperfect yad3u"),
    ("يَرْمِي", "VERB", "رمي", {"form": "I", "tense": "PRES", "voice": "ACT"}, "naqis imperfect yarmi"),
    ("يَنْسَى", "VERB", "نسي", {"form": "I", "tense": "PRES", "voice": "ACT"}, "naqis imperfect yansa"),
    # ── أجوف (hollow) ─────────────────────────────────────────────────────
    ("قَالَ",   "VERB", "قول", {"form": "I", "tense": "PAST", "voice": "ACT"}, "ajwaf qala"),
    ("بَاعَ",   "VERB", "بيع", {"form": "I", "tense": "PAST", "voice": "ACT"}, "ajwaf ba3a"),
    ("نَامَ",   "VERB", "نوم", {"form": "I", "tense": "PAST", "voice": "ACT"}, "ajwaf nama"),
    ("قِيلَ",   "VERB", "قول", {"form": "I", "tense": "PAST", "voice": "PASS"}, "ajwaf passive qila"),
    ("أُقِيمَ", "VERB", "قوم", {"form": "IV", "tense": "PAST", "voice": "PASS"}, "F-IV passive uqima"),
    ("يَقُولُ", "VERB", "قول", {"form": "I", "tense": "PRES", "voice": "ACT"}, "ajwaf imperfect yaqul"),
    # ── مثال (initial-w/y) ────────────────────────────────────────────────
    ("وَعَدَ",  "VERB", "وعد", {"form": "I", "tense": "PAST", "voice": "ACT"}, "mithal wa3ada"),
    ("وَجَدَ",  "VERB", "وجد", {"form": "I", "tense": "PAST", "voice": "ACT"}, "mithal wajada"),
    ("وَرِثَ",  "VERB", "ورث", {"form": "I", "tense": "PAST", "voice": "ACT"}, "mithal waritha"),
    ("يَعِدُ",  "VERB", "وعد", {"form": "I", "tense": "PRES", "voice": "ACT"}, "mithal imperfect ya3id (waw elided)"),
    ("يَجِدُ",  "VERB", "وجد", {"form": "I", "tense": "PRES", "voice": "ACT"}, "mithal imperfect yajid"),
    ("يَرِثُ",  "VERB", "ورث", {"form": "I", "tense": "PRES", "voice": "ACT"}, "mithal imperfect yarith"),
    # ── مهموز (hamzated) ──────────────────────────────────────────────────
    ("أَخَذَ",  "VERB", "ءخذ", {"form": "I", "tense": "PAST", "voice": "ACT"}, "hamzated initial akhadha"),
    ("سَأَلَ",  "VERB", "سءل", {"form": "I", "tense": "PAST", "voice": "ACT"}, "hamzated medial sa'ala"),
    ("قَرَأَ",  "VERB", "قرء", {"form": "I", "tense": "PAST", "voice": "ACT"}, "hamzated final qara'a"),
    # ── مضعّف (geminate) ──────────────────────────────────────────────────
    ("مَدَّ",   "VERB", "مدد", {"form": "I", "tense": "PAST", "voice": "ACT"}, "geminate madda"),
    ("شَدَّ",   "VERB", "شدد", {"form": "I", "tense": "PAST", "voice": "ACT"}, "geminate shadda"),
    ("رَدَّ",   "VERB", "ردد", {"form": "I", "tense": "PAST", "voice": "ACT"}, "geminate radda"),
    ("مُدَّ",   "VERB", "مدد", {"form": "I", "tense": "PAST", "voice": "PASS"}, "geminate passive mudda"),
    ("شُدَّ",   "VERB", "شدد", {"form": "I", "tense": "PAST", "voice": "PASS"}, "geminate passive shudda"),
]


@pytest.mark.parametrize("surface,pos,root,tags,label", WEAK_ROOTS)
def test_weak_roots(surface, pos, root, tags, label):
    _check(surface, pos=pos, root=root, tags_subset=tags, label=label)


# ═════════════════════════════════════════════════════════════════════════════
# 4. MASDAR PATTERNS (40+)
# ═════════════════════════════════════════════════════════════════════════════

MASDARS = [
    # ── Form I masdars ────────────────────────────────────────────────────
    ("ضَرْب",      "NOM", "ضرب", {"role": "MASDAR"}, "masdar I fa3l"),
    ("فَهْم",      "NOM", "فهم", {"role": "MASDAR"}, "masdar I fa3l"),
    ("كِتَابَة",   "NOM", "كتب", {"role": "MASDAR"}, "masdar I fi3ala"),
    ("جُلُوس",     "NOM", "جلس", {"role": "MASDAR"}, "masdar I fu3ul"),
    ("نُزُول",     "NOM", "نزل", {"role": "MASDAR"}, "masdar I fu3ul"),
    ("غُفْرَان",   "NOM", "غفر", {"role": "MASDAR"}, "masdar I fu3lan"),
    # ── Form II: تَفْعِيل ─────────────────────────────────────────────────
    ("تَعْلِيم",   "NOM", "علم", {"role": "MASDAR", "form": "II"}, "masdar II taf3il"),
    ("تَفْسِير",   "NOM", "فسر", {"role": "MASDAR", "form": "II"}, "masdar II tafsir"),
    ("تَدْرِيس",   "NOM", "درس", {"role": "MASDAR", "form": "II"}, "masdar II tadris"),
    # ── Form III: مُفَاعَلَة / فِعَال ────────────────────────────────────
    ("مُشَارَكَة", "NOM", "شرك", {"role": "MASDAR", "form": "III"}, "masdar III mufa3ala"),
    ("مُقَاتَلَة", "NOM", "قتل", {"role": "MASDAR", "form": "III"}, "masdar III muqatala"),
    ("جِهَاد",     "NOM", "جهد", {"role": "MASDAR", "form": "III"}, "masdar III fi3al"),
    # ── Form IV: إِفْعَال ────────────────────────────────────────────────
    ("إِنْجَاز",   "NOM", "نجز", {"role": "MASDAR", "form": "IV"}, "masdar IV if3al"),
    ("إِعْلَان",   "NOM", "علن", {"role": "MASDAR", "form": "IV"}, "masdar IV if3al"),
    ("إِكْرَام",   "NOM", "كرم", {"role": "MASDAR", "form": "IV"}, "masdar IV if3al"),
    # ── Form V: تَفَعُّل ─────────────────────────────────────────────────
    ("تَعَلُّم",   "NOM", "علم", {"role": "MASDAR", "form": "V"}, "masdar V tafa33ul"),
    ("تَقَدُّم",   "NOM", "قدم", {"role": "MASDAR", "form": "V"}, "masdar V tafa33ul"),
    ("تَطَوُّر",   "NOM", "طور", {"role": "MASDAR", "form": "V"}, "masdar V tafa33ul"),
    # ── Form VI: تَفَاعُل ────────────────────────────────────────────────
    ("تَبَادُل",   "NOM", "بدل", {"role": "MASDAR", "form": "VI"}, "masdar VI tafa3ul"),
    ("تَعَاوُن",   "NOM", "عون", {"role": "MASDAR", "form": "VI"}, "masdar VI tafa3ul"),
    # ── Form VII: اِنْفِعَال ─────────────────────────────────────────────
    ("اِنْفِجَار", "NOM", "فجر", {"role": "MASDAR", "form": "VII"}, "masdar VII infi3al"),
    ("اِنْكِسَار", "NOM", "كسر", {"role": "MASDAR", "form": "VII"}, "masdar VII infi3al"),
    # ── Form VIII: اِفْتِعَال ────────────────────────────────────────────
    ("اِجْتِمَاع", "NOM", "جمع", {"role": "MASDAR", "form": "VIII"}, "masdar VIII ifti3al"),
    ("اِنْتِخَاب", "NOM", "نخب", {"role": "MASDAR", "form": "VIII"}, "masdar VIII ifti3al"),
    # ── Form IX: اِفْعِلَال ──────────────────────────────────────────────
    ("اِحْمِرَار", "NOM", "حمر", {"role": "MASDAR", "form": "IX"}, "masdar IX if3ilal"),
    # ── Form X: اِسْتِفْعَال ─────────────────────────────────────────────
    ("اِسْتِعْمَال", "NOM", "عمل", {"role": "MASDAR", "form": "X"}, "masdar X istif3al"),
    ("اِسْتِخْرَاج", "NOM", "خرج", {"role": "MASDAR", "form": "X"}, "masdar X istif3al"),
    ("اِسْتِغْفَار", "NOM", "غفر", {"role": "MASDAR", "form": "X"}, "masdar X istif3al"),
    # ── مصدر مرّة / هيئة / ميمي ──────────────────────────────────────────
    ("ضَرْبَة",   "NOM", "ضرب", {"role": "MASDAR"}, "masdar marra fa3la"),
    ("جِلْسَة",   "NOM", "جلس", {"role": "MASDAR"}, "masdar hay'a fi3la"),
    ("مَضْرَب",   "NOM", "ضرب", {"role": "MASDAR"}, "masdar mimi maf3al"),
    # NOTE: مَجْلِس (maf3il pattern) is classified as PLACE in this engine spec,
    # not MASDAR. In modern Arabic the place-noun reading (council, sitting place)
    # dominates over the rare classical masdar mimi reading. See PLACE section
    # below and parallel test in test_ar_engine_templates.py.
]


@pytest.mark.parametrize("surface,pos,root,tags,label", MASDARS)
def test_masdars(surface, pos, root, tags, label):
    _check(surface, pos=pos, root=root, tags_subset=tags, label=label)


# ═════════════════════════════════════════════════════════════════════════════
# 5. BROKEN PLURALS (diptote + triptote)
# ═════════════════════════════════════════════════════════════════════════════

BROKEN_PLURALS = [
    ("كُتُب",     "NOM", "كتب", {"role": "PLURAL", "num": "PL"}, "fu3ul kutub"),
    ("أَوْلَاد",  "NOM", "ولد", {"role": "PLURAL", "num": "PL"}, "af3al awlad"),
    ("أَقْلَام",  "NOM", "قلم", {"role": "PLURAL", "num": "PL"}, "af3al aqlam"),
    ("أَفْعَال",  "NOM", "فعل", {"role": "PLURAL", "num": "PL"}, "af3al schema"),
    ("رِجَال",    "NOM", "رجل", {"role": "PLURAL", "num": "PL"}, "fi3al rijal"),
    ("بُيُوت",    "NOM", "بيت", {"role": "PLURAL", "num": "PL"}, "fu3ul buyut"),
    ("عُيُون",    "NOM", "عين", {"role": "PLURAL", "num": "PL"}, "fu3ul 3uyun"),
    ("شُعَرَاء",  "NOM", "شعر", {"role": "PLURAL", "num": "PL", "diptote": "YES"}, "fu3ala' diptote"),
    ("عَجَائِب",  "NOM", "عجب", {"role": "PLURAL", "num": "PL", "diptote": "YES"}, "fa3a'il diptote"),
    ("مَدَارِس",  "NOM", "درس", {"role": "PLURAL", "num": "PL", "diptote": "YES"}, "mafa3il diptote madaris"),
    ("مَفَاعِل",  "NOM", "فعل", {"role": "PLURAL", "num": "PL", "diptote": "YES"}, "mafa3il schema"),
    ("أَفْعِلَة", "NOM", "فعل", {"role": "PLURAL", "num": "PL"}, "af3ila schema"),
    ("فُعُول",    "NOM", "فعل", {"role": "PLURAL", "num": "PL"}, "fu3ul schema"),
]


@pytest.mark.parametrize("surface,pos,root,tags,label", BROKEN_PLURALS)
def test_broken_plurals(surface, pos, root, tags, label):
    _check(surface, pos=pos, root=root, tags_subset=tags, label=label)


# ═════════════════════════════════════════════════════════════════════════════
# 6. ACTIVE / PASSIVE PARTICIPLES PER FORM
# ═════════════════════════════════════════════════════════════════════════════

PARTICIPLE_CASES = [
    # Form I: فاعل / مفعول
    ("كَاتِب",      "NOM", "كتب", {"role": "AGENT"}, "AP F-I katib"),
    ("قَارِئ",      "NOM", "قرء", {"role": "AGENT"}, "AP F-I qari'"),
    ("مَكْتُوب",    "NOM", "كتب", {"role": "PASSIVE_PARTICIPLE"}, "PP F-I maktub"),
    ("مَفْهُوم",    "NOM", "فهم", {"role": "PASSIVE_PARTICIPLE"}, "PP F-I mafhum"),
    ("مَسْمُوع",    "NOM", "سمع", {"role": "PASSIVE_PARTICIPLE"}, "PP F-I masmu3"),
    # Form II: مفعِّل / مفعَّل
    ("مُعَلِّم",    "NOM", "علم", {"role": "AGENT"}, "AP F-II mu3allim"),
    ("مُعَلَّم",    "NOM", "علم", {"role": "PASSIVE_PARTICIPLE"}, "PP F-II mu3allam"),
    ("مُدَرِّس",    "NOM", "درس", {"role": "AGENT"}, "AP F-II mudarris"),
    # Form III: مفاعِل / مفاعَل
    ("مُقَاتِل",    "NOM", "قتل", {"role": "AGENT"}, "AP F-III muqatil"),
    ("مُشَارِك",    "NOM", "شرك", {"role": "AGENT"}, "AP F-III musharik"),
    ("مُسَافِر",    "NOM", "سفر", {"role": "AGENT"}, "AP F-III musafir"),
    # Form IV: مفعِل / مفعَل
    ("مُنْجِز",     "NOM", "نجز", {"role": "AGENT"}, "AP F-IV munjiz"),
    ("مُحْسِن",     "NOM", "حسن", {"role": "AGENT"}, "AP F-IV muhsin"),
    # Form VIII: مفتعِل
    ("مُجْتَمِع",   "NOM", "جمع", {"role": "AGENT"}, "AP F-VIII mujtami3"),
    ("مُعْتَقِد",   "NOM", "عقد", {"role": "AGENT"}, "AP F-VIII mu3taqid"),
    # Form X: مستفعِل / مستفعَل
    ("مُسْتَقْبِل", "NOM", "قبل", {"role": "AGENT"}, "AP F-X mustaqbil"),
    ("مُسْتَشَار",  "NOM", "شور", {"role": "PASSIVE_PARTICIPLE"}, "PP F-X mustashar"),
]


@pytest.mark.parametrize("surface,pos,root,tags,label", PARTICIPLE_CASES)
def test_participles(surface, pos, root, tags, label):
    _check(surface, pos=pos, root=root, tags_subset=tags, label=label)


# ═════════════════════════════════════════════════════════════════════════════
# 7. DERIVED NOMINAL TEMPLATES (instrument, place, sifa, mubalagha, etc.)
# ═════════════════════════════════════════════════════════════════════════════

DERIVED_NOMS = [
    # Instrument (مِفْعَال، مِفْعَلَة، مِفْعَل)
    ("مِفْتَاح",    "NOM", "فتح", {"role": "INSTRUMENT"}, "instrument miftah"),
    ("مِكْنَسَة",   "NOM", "كنس", {"role": "INSTRUMENT"}, "instrument miknasa"),
    ("مِقَصّ",      "NOM", "قصص", {"role": "INSTRUMENT"}, "instrument miqass"),
    # Place / time (مَفْعَل، مَفْعِل، مَفْعَلَة)
    ("مَكْتَب",     "NOM", "كتب", {"role": "PLACE"}, "place maktab"),
    ("مَلْعَب",     "NOM", "لعب", {"role": "PLACE"}, "place mal3ab"),
    ("مَسْبَح",     "NOM", "سبح", {"role": "PLACE"}, "place masbah"),
    ("مَجْلِس",     "NOM", "جلس", {"role": "PLACE"}, "place majlis"),
    ("مَدْرَسَة",   "NOM", "درس", {"role": "PLACE", "gender": "F"}, "place madrasa"),
    ("مَطْبَخ",     "NOM", "طبخ", {"role": "PLACE"}, "place matbakh"),
    # Sifa mushabbaha (فَعِل، أَفْعَل، فَعْلَان)
    ("صَغِير",      "ADJ", "صغر", {"role": "SIFA_MUSHABBAHA"}, "sifa saghir"),
    ("كَبِير",      "ADJ", "كبر", {"role": "SIFA_MUSHABBAHA"}, "sifa kabir"),
    ("أَحْمَر",     "ADJ", "حمر", {"role": "SIFA_MUSHABBAHA"}, "color af3al ahmar"),
    ("أَزْرَق",     "ADJ", "زرق", {"role": "SIFA_MUSHABBAHA"}, "color azraq"),
    ("عَطْشَان",    "ADJ", "عطش", {"role": "SIFA_MUSHABBAHA"}, "sifa fa3lan 3atshan"),
    ("جَوْعَان",    "ADJ", "جوع", {"role": "SIFA_MUSHABBAHA"}, "sifa fa3lan jaw3an"),
    ("كَسْلَان",    "ADJ", "كسل", {"role": "SIFA_MUSHABBAHA"}, "sifa fa3lan kaslan"),
    # Mubalaghah (فَعَّال، مِفْعَال، فَعُول، فَعِيل)
    ("فَعَّال",     "NOM", "فعل", {"role": "MUBALAGHAH"}, "mubalagha fa33al schema"),
    ("نَجَّار",     "NOM", "نجر", {"role": "MUBALAGHAH"}, "mubalagha najjar"),
    ("صَبُور",      "ADJ", "صبر", {"role": "MUBALAGHAH"}, "mubalagha fa3ul sabur"),
    # Diminutive (فُعَيْل)
    ("كُتَيْب",     "NOM", "كتب", {"role": "DIMINUTIVE"}, "diminutive kutayb"),
    ("جُبَيْل",     "NOM", "جبل", {"role": "DIMINUTIVE"}, "diminutive jubayl"),
    # Elative / comparative (أَفْعَل)
    ("أَكْبَر",     "ADJ", "كبر", {"degree": "COMP"}, "elative akbar"),
    ("أَصْغَر",     "ADJ", "صغر", {"degree": "COMP"}, "elative asghar"),
    ("أَحْسَن",     "ADJ", "حسن", {"degree": "COMP"}, "elative ahsan"),
    ("كُبْرَى",     "ADJ", "كبر", {"degree": "COMP", "gender": "F"}, "fem elative kubra"),
    # Nisba (-ي / -يّة)
    ("عَرَبِيّ",    "ADJ", "عرب", {"role": "NISBA"}, "nisba 3arabi"),
    ("مِصْرِيّ",    "ADJ", "مصر", {"role": "NISBA"}, "nisba misri"),
    ("مِصْرِيَّة",  "ADJ", "مصر", {"role": "NISBA", "gender": "F"}, "nisba fem misriyya"),
]


@pytest.mark.parametrize("surface,pos,root,tags,label", DERIVED_NOMS)
def test_derived_nominal_templates(surface, pos, root, tags, label):
    _check(surface, pos=pos, root=root, tags_subset=tags, label=label)


# ═════════════════════════════════════════════════════════════════════════════
# 8. CLITIC STACKING (proclitics + enclitics + circumfix)
# ═════════════════════════════════════════════════════════════════════════════

CLITICS = [
    # Stacked proclitics
    ("وَبِالْكِتَابِ", "NOM", "كتب", "wa+bi+al triple proclitic"),
    ("فَبِالْعِلْمِ",  "NOM", "علم", "fa+bi+al triple proclitic"),
    ("وَلِلْمَدْرَسَةِ", "NOM", "درس", "wa+li+al stacked"),
    ("كَالْأَسَدِ",    "NOM", "ءسد", "ka+al + hamzated noun"),
    ("بِالْبَيْتِ",    "NOM", "بيت", "bi+al stacked"),
    ("سَيَكْتُبُ",     "VERB", "كتب", "sa+ prefix future"),
    # Object pronoun enclitics
    ("كَتَبَهُ",       "VERB", "كتب", "enclitic 3MSG hu"),
    ("كَتَبَهَا",      "VERB", "كتب", "enclitic 3FSG ha"),
    ("كَتَبَهُمْ",     "VERB", "كتب", "enclitic 3MPL hum"),
    ("كَتَبَهُنَّ",    "VERB", "كتب", "enclitic 3FPL hunna"),
    ("كَتَبَهُمَا",    "VERB", "كتب", "enclitic 3DU huma"),
    ("كَتَبَكَ",       "VERB", "كتب", "enclitic 2MSG ka"),
    ("كَتَبَكُمْ",     "VERB", "كتب", "enclitic 2MPL kum"),
    ("كَتَبَكُنَّ",    "VERB", "كتب", "enclitic 2FPL kunna"),
    ("كَتَبَكُمَا",    "VERB", "كتب", "enclitic 2DU kuma"),
    ("كَتَبَنِي",      "VERB", "كتب", "enclitic 1SG ni"),
    ("كَتَبَنَا",      "VERB", "كتب", "enclitic 1PL na"),
    # Dual / fem-plural noun endings
    ("كِتَابَانِ",     "NOM", "كتب", "dual nominative -ani"),
    ("كِتَابَيْنِ",    "NOM", "كتب", "dual oblique -ayni"),
    ("مُعَلِّمَات",    "NOM", "علم", "fem plural -at"),
    # Energetic nun + circumfix لَـ...ـنّ
    ("لَيَكْتُبَنَّ",  "VERB", "كتب", "circumfix LAM_NUN on kataba"),
    ("لَيَذْهَبَنَّ",  "VERB", "ذهب", "circumfix LAM_NUN on dhahaba"),
    ("لَيَضْرِبَنَّ",  "VERB", "ضرب", "circumfix LAM_NUN on daraba"),
]


@pytest.mark.parametrize("surface,pos,root,label", CLITICS)
def test_clitic_stacking(surface, pos, root, label):
    _check(surface, pos=pos, root=root, label=label)


# ═════════════════════════════════════════════════════════════════════════════
# 9. CLOSED-CLASS PARTICLES
# ═════════════════════════════════════════════════════════════════════════════

PARTICLE_CASES = [
    # Prepositions
    ("فِي",     "PART", {"subcat": "PREP"}, "prep fi"),
    ("مِنْ",    "PART", {"subcat": "PREP"}, "prep min"),
    ("إِلَى",   "PART", {"subcat": "PREP"}, "prep ila"),
    ("عَلَى",   "PART", {"subcat": "PREP"}, "prep 3ala"),
    ("عَنْ",    "PART", {"subcat": "PREP"}, "prep 3an"),
    ("مَعَ",    "PART", {"subcat": "PREP"}, "prep ma3"),
    ("عِنْدَ",  "PART", {"subcat": "PREP"}, "prep 3inda"),
    ("تَحْتَ",  "PART", {"subcat": "PREP"}, "prep tahta"),
    ("فَوْقَ",  "PART", {"subcat": "PREP"}, "prep fawqa"),
    # Conjunctions
    ("ثُمَّ",   "PART", {"subcat": "CONJ"}, "conj thumma"),
    ("أَوْ",    "PART", {"subcat": "CONJ"}, "conj aw"),
    ("أَمْ",    "PART", {"subcat": "CONJ"}, "conj am (in questions)"),
    ("لَكِنْ",  "PART", {"subcat": "CONJ"}, "conj lakin"),
    ("بَلْ",    "PART", {"subcat": "CONJ"}, "conj bal"),
    # Subordinators / complementizers
    ("أَنْ",    "PART", {"subcat": "COMP"}, "comp an"),
    ("إِذَا",   "PART", {"subcat": "SUB"}, "sub idha"),
    ("حَتَّى",  "PART", {"subcat": "SUB"}, "sub hatta"),
    ("كَيْ",    "PART", {"subcat": "SUB"}, "sub kay"),
    # Negation
    ("لَا",     "PART", {"subcat": "NEG"}, "neg la"),
    ("لَمْ",    "PART", {"subcat": "NEG"}, "neg lam (jussive)"),
    ("لَنْ",    "PART", {"subcat": "NEG"}, "neg lan (future)"),
    ("لَيْسَ",  "PART", {"subcat": "NEG"}, "neg laysa (copular)"),
    # Interrogatives
    ("هَلْ",    "PART", {"subcat": "INTERROG"}, "interrog hal"),
    ("أَيْنَ",  "PART", {"subcat": "INTERROG"}, "interrog ayna"),
    ("مَتَى",   "PART", {"subcat": "INTERROG"}, "interrog mata"),
    ("كَيْفَ",  "PART", {"subcat": "INTERROG"}, "interrog kayfa"),
    ("لِمَاذَا", "PART", {"subcat": "INTERROG"}, "interrog limadha"),
    ("مَاذَا",  "PART", {"subcat": "INTERROG"}, "interrog madha"),
    # Demonstratives
    ("هَذَا",   "PART", {"subcat": "DEM"}, "dem hadha"),
    ("هَذِهِ",  "PART", {"subcat": "DEM"}, "dem hadhihi"),
    ("ذَلِكَ",  "PART", {"subcat": "DEM"}, "dem dhalika"),
    ("تِلْكَ",  "PART", {"subcat": "DEM"}, "dem tilka"),
    ("هَؤُلَاءِ", "PART", {"subcat": "DEM"}, "dem ha'ula'i"),
    ("أُولَئِكَ", "PART", {"subcat": "DEM"}, "dem ula'ika"),
    # Vocatives
    ("يَا",     "PART", {"subcat": "VOC"}, "voc ya"),
    ("أَيُّهَا", "PART", {"subcat": "VOC"}, "voc ayyuha"),
    # Interjections / أسماء أفعال
    ("هَيْهَات", "PART", {"subcat": "INTERJ"}, "ism fi3l hayhat"),
    ("آمِين",   "PART", {"subcat": "INTERJ"}, "amen"),
    ("صَه",     "PART", {"subcat": "INTERJ"}, "ism fi3l amr sah"),
    ("أَوَّاه", "PART", {"subcat": "INTERJ"}, "ism fi3l awwah"),
]


@pytest.mark.parametrize("surface,pos,tags,label", PARTICLE_CASES)
def test_closed_class_particles(surface, pos, tags, label):
    _check(surface, pos=pos, tags_subset=tags, label=label)


# ═════════════════════════════════════════════════════════════════════════════
# 10. HAMZA VARIANTS - normalization to ء
# ═════════════════════════════════════════════════════════════════════════════

HAMZA_VARIANTS = [
    ("أَمَرَ",    "ءمر", "hamza alif-above amara"),
    ("إِبْرَاهِيم", "ءبرهيم", "hamza alif-below ibrahim (loanish)"),
    ("آمَنَ",     "ءمن", "hamza madda amana"),
    ("سُؤَال",    "سءل", "hamza on waw su'al"),
    ("سَائِل",    "سءل", "hamza on ya sa'il"),
    ("قَرَأَ",    "قرء", "hamza final qara'a"),
    ("نَشَأَ",    "نشء", "hamza final nasha'a"),
    ("بَدَأَ",    "بدء", "hamza final bada'a"),
    ("سَأَلَ",    "سءل", "hamza medial sa'ala"),
    ("أَخَذَ",    "ءخذ", "hamza initial akhadha"),
]


@pytest.mark.parametrize("surface,exp_root,label", HAMZA_VARIANTS)
def test_hamza_normalization(surface, exp_root, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected {exp_root!r}"


# ═════════════════════════════════════════════════════════════════════════════
# 11. NUMBER-LIKE AND FOREIGN SURFACES
# ═════════════════════════════════════════════════════════════════════════════

FOREIGN_AND_NUMBERS = [
    # Number-like + chemical formulas: should be diptote NOM (loanword)
    ("H2O",            "NOM", None, "chemical formula H2O"),
    ("71%",            "NOM", None, "percentage"),
    ("COVID",          "NOM", None, "acronym COVID"),
    # Loanwords in Arabic script
    ("أَكْسِجِين",     "NOM", {"origin": "FOREIGN"}, "loanword oksijin"),
    ("هَيْدْرُوجِين",  "NOM", {"origin": "FOREIGN"}, "loanword haidrojin"),
    ("بِيَانُو",       "NOM", {"origin": "FOREIGN"}, "loanword piano"),
    ("كُومْبْيُوتَر",   "NOM", {"origin": "FOREIGN"}, "loanword computer"),
]


@pytest.mark.parametrize("surface,pos,tags,label", FOREIGN_AND_NUMBERS)
def test_foreign_and_number_surfaces(surface, pos, tags, label):
    _check(surface, pos=pos, tags_subset=tags, label=label)


# ═════════════════════════════════════════════════════════════════════════════
# 12. WAZN-SEMANTIC-CLASS LOOKUP (Step B')
#
# Verifies that the engine surfaces a `semantic_role` (or `role`) consistent
# with `ar_templates.json:semantic_role` for canonical surfaces of each wazn.
# These tests probe whether Step B' has been wired up for each template
# family. The expectation is the LINGUISTICALLY CORRECT semantic role.
# ═════════════════════════════════════════════════════════════════════════════

WAZN_SEMANTIC_ROLES = [
    # Verb templates -> action class
    ("كَتَبَ",       {"semantic_role": "ACTION_TRANSITIVE"}, "wazn F-I fa3ala class"),
    ("عَلَّمَ",      {"semantic_role": "CAUSATIVE"},          "wazn F-II tafilla class"),
    ("قَاتَلَ",      {"semantic_role": "RECIPROCAL"},         "wazn F-III mufa3ala class"),
    ("أَنْجَزَ",     {"semantic_role": "CAUSATIVE"},          "wazn F-IV if3al class"),
    ("تَعَلَّمَ",    {"semantic_role": "REFLEXIVE"},          "wazn F-V tafa33ul class"),
    ("تَبَادَلَ",    {"semantic_role": "RECIPROCAL"},         "wazn F-VI tafa3ul class"),
    ("اِنْفَجَرَ",   {"semantic_role": "PASSIVE_INTRANS"},    "wazn F-VII infa3al class"),
    ("اِجْتَمَعَ",   {"semantic_role": "MEDIO_PASSIVE"},      "wazn F-VIII ifta3al class"),
    ("اِحْمَرَّ",    {"semantic_role": "COLOR_DEFECT"},       "wazn F-IX if3all class"),
    ("اِسْتَخْرَجَ", {"semantic_role": "REQUEST"},            "wazn F-X istaf3al class"),
    # Nominal templates -> semantic role
    ("كَاتِب",       {"role": "AGENT"},                       "AP -> AGENT"),
    ("مَكْتُوب",     {"role": "PASSIVE_PARTICIPLE"},          "PP -> PASSIVE_PARTICIPLE"),
    ("مِفْتَاح",     {"role": "INSTRUMENT"},                  "instrument -> INSTRUMENT"),
    ("مَكْتَب",      {"role": "PLACE"},                       "place -> PLACE"),
    ("نَجَّار",      {"role": "MUBALAGHAH"},                  "fa33al -> MUBALAGHAH"),
    ("كُتَيْب",      {"role": "DIMINUTIVE"},                  "fu3ayl -> DIMINUTIVE"),
    ("عَرَبِيّ",     {"role": "NISBA"},                       "nisba -> NISBA"),
]


@pytest.mark.parametrize("surface,tags,label", WAZN_SEMANTIC_ROLES)
def test_wazn_semantic_class_lookup(surface, tags, label):
    _check(surface, tags_subset=tags, label=label)


# ─────────────────────────────────────────────────────────────────────────────
# CLI runner: prints per-section pass/fail counts.
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys as _sys
    raise SystemExit(pytest.main([__file__, "-v", "--tb=short"]))
