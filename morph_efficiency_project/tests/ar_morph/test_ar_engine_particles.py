"""
test_ar_particles.py
--------------------
Tests for:
  - إن وأخواتها (6 sisters + variants)
  - كان وأخواتها (10 sisters including ما-negated forms)
  - لولا / لوما (counterfactual conditionals)
  - All CLOSED_CLASS anomaly tests (words that look like proclitic+root)
  - Loanword behavior

Run: python -m pytest morph_efficiency_project/tests/ar/test_ar_particles.py -v
  or: python morph_efficiency_project/tests/ar/test_ar_particles.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import ArabicEngine
import pytest

engine = ArabicEngine()

# ── إن وأخواتها ───────────────────────────────────────────────────────────────
# The six sisters (الأخوات الست) that govern the accusative (نصب المبتدأ).
# All are in CLOSED_CLASS and must return template=CLOSED_CLASS.
INN_SISTERS = [
    # Voweled forms
    ("إِنَّ",   "إن",   "CLOSED_CLASS",  "inna — emphasis/assertion"),
    ("أَنَّ",   "أن",   "CLOSED_CLASS",  "anna — that (complementizer)"),
    ("كَأَنَّ", "كأن",  "CLOSED_CLASS",  "ka'anna — as if"),
    ("لَكِنَّ", "لكن",  "CLOSED_CLASS",  "lakinna — but (with noun)"),
    ("لَيْتَ",  "ليت",  "CLOSED_CLASS",  "layta — would that (wish)"),
    ("لَعَلَّ", "لعل",  "CLOSED_CLASS",  "la3alla — perhaps"),
    # Undiacritical forms
    ("إن",     "إن",   "CLOSED_CLASS",  "inna undiacritical"),
    ("أن",     "أن",   "CLOSED_CLASS",  "anna undiacritical"),
    ("كأن",    "كأن",  "CLOSED_CLASS",  "ka'anna undiacritical"),
    ("لكن",    "لكن",  "CLOSED_CLASS",  "lakin undiacritical"),
    ("لكنّ",   "لكن",  "CLOSED_CLASS",  "lakinna undiacritical"),
    ("ليت",    "ليت",  "CLOSED_CLASS",  "layta undiacritical"),
    ("لعل",    "لعل",  "CLOSED_CLASS",  "la3alla undiacritical"),
    ("لعلّ",   "لعل",  "CLOSED_CLASS",  "la3alla with shadda"),
    # إِنْ conditional (different from إِنَّ emphasis)
    ("إِنْ",   "إن",   "CLOSED_CLASS",  "in conditional"),
]

# ── كان وأخواتها ──────────────────────────────────────────────────────────────
# The sisters of كان (الأفعال الناقصة) that govern the nominative subject
# and accusative predicate. The main verbs work as regular verbs through
# the engine (root extraction). ليس is CLOSED_CLASS. ما-negated forms are
# CLOSED_CLASS (frozen compounds).
KANA_SISTERS_VERBS = [
    # These work as regular verbs — check root extraction
    ("كَانَ",   "كون",  None,  "kana — was (ajwaf waw)"),
    ("أَصْبَحَ", "صبح",  None,  "asbaha — became (morning)"),
    ("أَمْسَى",  "مسو",  None,  "amsa — became (evening) naqis"),
    ("بَاتَ",   "بيت",  None,  "bata — spent the night (ajwaf ya)"),
    ("أَضْحَى",  "ضحى",  None,  "adha — became (morning) naqis"),
    ("صَارَ",   "صير",  None,  "sara — became (ajwaf ya)"),
    ("ظَلَّ",   "ظلل",  None,  "dhalla — remained (geminate) — FIXED"),
    ("مَا زَالَ", "ازال", "NOM_DERIVED",  "ma zala — still is (two words)"),
    ("مَا دَامَ", "ادام", "NOM_DERIVED",  "ma dama — as long as (two words)"),
    ("مَا بَرِحَ", "برح", None, "ma bariha — has not ceased (two words)"),
]

KANA_SISTERS_CLOSED = [
    # ليس is CLOSED_CLASS (negation particle)
    ("لَيْسَ",  "ليس",  "CLOSED_CLASS",  "laysa — is not"),
    ("ليس",    "ليس",  "CLOSED_CLASS",  "laysa undiacritical"),
    # ما-negated frozen compounds
    ("مازال",   "مازال",  "CLOSED_CLASS",  "mazala frozen compound"),
    ("مَازَالَ", "مازال",  "CLOSED_CLASS",  "mazala voweled frozen"),
    ("مادام",   "مادام",  "CLOSED_CLASS",  "madama frozen compound"),
    ("مَادَامَ", "مادام",  "CLOSED_CLASS",  "madama voweled frozen"),
    ("مابرح",   "مابرح",  "CLOSED_CLASS",  "mabariha frozen compound"),
    ("مَابَرِحَ", "مابرح", "CLOSED_CLASS",  "mabariha voweled frozen"),
    ("مافتئ",   "مافتئ",  "CLOSED_CLASS",  "mafati'a frozen compound"),
    ("مَافَتِئَ", "مافتئ", "CLOSED_CLASS",  "mafati'a voweled frozen"),
    ("ماانفك",  "ماانفك", "CLOSED_CLASS",  "mainfakka frozen compound"),
    ("ماانفكّ", "ماانفك", "CLOSED_CLASS",  "mainfakka with shadda"),
]

# ── لولا / لوما ───────────────────────────────────────────────────────────────
LAWLA = [
    ("لولا",   "لولا",  "CLOSED_CLASS",  "lawla — if it were not for"),
    ("لَوْلَا", "لولا",  "CLOSED_CLASS",  "lawla voweled"),
    ("لوما",   "لوما",  "CLOSED_CLASS",  "lawma — rare variant of lawla"),
    ("لَوْمَا", "لوما",  "CLOSED_CLASS",  "lawma voweled"),
]

# ── Anomaly tests: words that look like proclitic+root but are roots ──────────
ANOMALIES = [
    # Words starting with و (mithal roots, not conjunction)
    ("وَجَدَ",  "وجد",  None,  "ANOM: voweled wa = mithal root"),
    ("وَقَفَ",  "وقف",  None,  "ANOM: voweled wa = mithal root"),
    ("وَصَلَ",  "وصل",  None,  "ANOM: voweled wa = mithal root"),
    ("وَلَدَ",  "ولد",  None,  "ANOM: voweled wa = mithal root"),
    ("وَرَدَ",  "ورد",  None,  "ANOM: voweled wa = mithal root"),
    # Words starting with ف (roots, not conjunction)
    ("فَتَحَ",  "فتح",  "VERB_TRILATERAL_BARE",  "ANOM: voweled fa = root"),
    ("فَهِمَ",  "فهم",  "VERB_TRILATERAL_BARE",  "ANOM: voweled fa = root"),
    ("فَرَّ",   "فرر",  None,  "ANOM: voweled fa = geminate root"),
    # Words starting with ب (roots, not prep)
    ("بَدَأَ",  "بدء",  None,  "ANOM: voweled ba = root"),
    ("بَنَى",   "بنو",  None,  "ANOM: voweled ba = naqis root"),
    ("بَاعَ",   "بيع",  None,  "ANOM: voweled ba = ajwaf root"),
    # Words starting with ل (roots, not prep)
    ("لَبِسَ",  "لبس",  None,  "ANOM: voweled la = root"),
    ("لَعِبَ",  "لعب",  None,  "ANOM: voweled la = root"),
    ("لَقِيَ",  "لقي",  None,  "ANOM: voweled la = naqis root"),
    # Words starting with ك (roots, not prep)
    ("كَتَبَ",  "كتب",  "VERB_TRILATERAL_BARE",  "ANOM: voweled ka = root"),
    ("كَبُرَ",  "كبر",  "VERB_TRILATERAL_BARE",  "ANOM: voweled ka = root"),
    ("كَانَ",   "كون",  None,  "ANOM: voweled ka = ajwaf root"),
    # Words starting with س (roots, not future marker)
    ("سَمِعَ",  "سمع",  "VERB_TRILATERAL_BARE",  "ANOM: voweled sa = root"),
    ("سَارَ",   "سير",  None,  "ANOM: voweled sa = ajwaf root"),
    ("سَأَلَ",  "سءل",  None,  "ANOM: voweled sa = hamzated root"),
    # Unvoweled roots that could be proclitic+root
    ("وصل",    "وصل",  None,  "ANOM: unvoweled wasal mithal root"),
    ("فتح",    "فتح",  None,  "ANOM: unvoweled fatah root"),
    ("بدأ",    "بدء",  None,  "ANOM: unvoweled bada' hamzated root"),
    ("لعب",    "لعب",  None,  "ANOM: unvoweled la3ib root"),
    ("كتب",    "كتب",  None,  "ANOM: unvoweled katab root"),
    ("سمع",    "سمع",  None,  "ANOM: unvoweled sami3 root"),
    # Closed-class words that look like proclitic+root
    ("لكن",    "لكن",  "CLOSED_CLASS",  "ANOM: lakin closed class"),
    ("لكنّ",   "لكن",  "CLOSED_CLASS",  "ANOM: lakinna closed class"),
    ("لأن",    "لأن",  "CLOSED_CLASS",  "ANOM: li'anna closed class"),
    ("لماذا",  "لماذا","CLOSED_CLASS",  "ANOM: limadha closed class"),
    ("لعل",    "لعل",  "CLOSED_CLASS",  "ANOM: la3alla closed class"),
    ("لعلّ",   "لعل",  "CLOSED_CLASS",  "ANOM: la3alla closed class"),
    ("بينما",  "بينما","CLOSED_CLASS",  "ANOM: baynama closed class"),
    ("عندما",  "عندما","CLOSED_CLASS",  "ANOM: 3indama closed class"),
    ("كلما",   "كلما", "CLOSED_CLASS",  "ANOM: kullama closed class"),
    ("مما",    "مما",  "CLOSED_CLASS",  "ANOM: mimma closed class"),
    # Interrogatives
    ("ماذا",   "ماذا", "CLOSED_CLASS",  "ANOM: madha closed class"),
    ("هل",     "هل",   "CLOSED_CLASS",  "ANOM: hal closed class"),
    ("كيف",    "كيف",  "CLOSED_CLASS",  "ANOM: kayfa closed class"),
    ("متى",    "متى",  "CLOSED_CLASS",  "ANOM: mata closed class"),
    ("أين",    "أين",  "CLOSED_CLASS",  "ANOM: ayna closed class"),
    # Negation particles
    ("لا",     "لا",   "CLOSED_CLASS",  "ANOM: la negation"),
    ("لم",     "لم",   "CLOSED_CLASS",  "ANOM: lam negation"),
    ("لن",     "لن",   "CLOSED_CLASS",  "ANOM: lan negation"),
    ("ليس",    "ليس",  "CLOSED_CLASS",  "ANOM: laysa negation"),
    # Discourse particles
    ("قد",     "قد",   "CLOSED_CLASS",  "ANOM: qad discourse"),
    ("إلا",    "إلا",  "CLOSED_CLASS",  "ANOM: illa discourse"),
    ("فقط",    "فقط",  "CLOSED_CLASS",  "ANOM: faqat discourse"),
]

# ── Loanword behavior ─────────────────────────────────────────────────────────
# Engine does not tag loanwords as FOREIGN — it returns the consonant skeleton
# or the first 3 consonants if they happen to be in root_set.
LOANWORDS = [
    ("تِلِفِزْيُون",  "تلف",    None,  "LOAN television — تلف in root_set"),
    ("رَادِيُو",      "ردي",    None,  "LOAN radio — raw skeleton"),
    ("بَنْك",         "بنك",    None,  "LOAN bank — raw skeleton"),
    ("فِيلْم",        "فيل",    None,  "LOAN film — raw skeleton"),
    ("تِلِفُون",      "تلف",    None,  "LOAN telephone — تلف in root_set"),
]

ALL_CASES = (
    [(s, r, t, l) for s, r, t, l in INN_SISTERS]
    + [(s, r, t, l) for s, r, t, l in KANA_SISTERS_VERBS]
    + [(s, r, t, l) for s, r, t, l in KANA_SISTERS_CLOSED]
    + [(s, r, t, l) for s, r, t, l in LAWLA]
    + [(s, r, t, l) for s, r, t, l in ANOMALIES]
    + [(s, r, t, l) for s, r, t, l in LOANWORDS]
)

@pytest.mark.parametrize("surface,exp_root,exp_tmpl,label", ALL_CASES)
def test_ar_particles(surface, exp_root, exp_tmpl, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    if exp_tmpl is not None:
        assert ti.template == exp_tmpl, (
            f"[{label}] template={ti.template!r} expected={exp_tmpl!r}"
        )

if __name__ == "__main__":
    passed = failed = 0
    failures = []
    for surface, exp_root, exp_tmpl, label in ALL_CASES:
        ti = engine.analyze(surface)
        root_ok = ti.root == exp_root
        tmpl_ok = exp_tmpl is None or ti.template == exp_tmpl
        if root_ok and tmpl_ok:
            passed += 1
        else:
            failed += 1
            msgs = []
            if not root_ok:
                msgs.append(f"root={ti.root!r} exp={exp_root!r}")
            if not tmpl_ok:
                msgs.append(f"tmpl={ti.template!r} exp={exp_tmpl!r}")
            failures.append(f"  FAIL  {surface:<22}  {label}  ->  {' | '.join(msgs)}")
    print(f"\n{'='*70}")
    print(f"  Arabic Particles / Closed-Class / Anomaly Test Suite")
    print(f"{'='*70}")
    print(f"  {passed} passed,  {failed} failed  (total {passed+failed})")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f)
    else:
        print("\n  All tests passed.")
    import sys; sys.exit(0 if failed == 0 else 1)
