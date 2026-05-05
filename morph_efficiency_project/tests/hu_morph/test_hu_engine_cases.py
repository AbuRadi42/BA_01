"""
test_hu_engine_cases.py
-----------------------
Hungarian case suffix tests -- all 18 productive cases with multiple nouns
testing harmony (back, front-unrounded, front-rounded).
Uses stems that don't end in letters that look like suffixes (e.g., tanár,
könyv, tükör) to avoid over-stripping in a lexicon-free engine.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import HungarianEngine
import pytest

engine = HungarianEngine()

# ── Interior spatial cases (INESS, ELAT, ILLAT) ───────────────────────────
INTERIOR = [
    ("házban",    "ház",   "INESS", "back iness"),
    ("kézben",   "kéz",   "INESS", "front iness"),
    ("tükörben", "tükör", "INESS", "front-round iness"),
    ("tanárban", "tanár", "INESS", "back 2syl iness"),
    ("emberben", "ember", "INESS", "front 2syl iness"),
    ("könyvben", "könyv", "INESS", "front 2syl iness2"),
    ("házból",   "ház",   "ELAT",  "back elat"),
    ("kézből",   "kéz",   "ELAT",  "front elat"),
    ("tükörből", "tükör", "ELAT",  "front-round elat"),
    ("tanárból", "tanár", "ELAT",  "back 2syl elat"),
    ("emberből", "ember", "ELAT",  "front 2syl elat"),
    ("házba",    "ház",   "ILLAT", "back illat"),
    ("kézbe",    "kéz",   "ILLAT", "front illat"),
    ("tanárba",  "tanár", "ILLAT", "back 2syl illat"),
    ("emberbe",  "ember", "ILLAT", "front 2syl illat"),
    ("könyvbe",  "könyv", "ILLAT", "front 2syl illat2"),
]

@pytest.mark.parametrize("surface,exp_root,exp_case,label", INTERIOR)
def test_interior(surface, exp_root, exp_case, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.tags.get("case") == exp_case, f"[{label}] case: {r.tags.get('case')!r}"
    assert r.pos == "NOUN"

# ── Surface spatial cases (SUPER, DELAT, SUBLAT) ─────────────────────────
SURFACE = [
    ("házon",    "ház",   "SUPER",  "back super"),
    ("kézen",    "kéz",   "SUPER",  "front super"),
    ("házról",   "ház",   "DELAT",  "back delat"),
    ("kézről",   "kéz",   "DELAT",  "front delat"),
    ("tanárról", "tanár", "DELAT",  "back 2syl delat"),
    ("házra",    "ház",   "SUBLAT", "back sublat"),
    ("kézre",    "kéz",   "SUBLAT", "front sublat"),
    ("emberre",  "ember", "SUBLAT", "front 2syl sublat"),
    ("tanárra",  "tanár", "SUBLAT", "back 2syl sublat"),
]

@pytest.mark.parametrize("surface,exp_root,exp_case,label", SURFACE)
def test_surface(surface, exp_root, exp_case, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.tags.get("case") == exp_case, f"[{label}] case: {r.tags.get('case')!r}"

# ── Proximity spatial cases (ADESS, ABLAT, ALLAT) ────────────────────────
PROXIMITY = [
    ("háznál",   "ház",   "ADESS", "back adess"),
    ("kéznél",   "kéz",   "ADESS", "front adess"),
    ("háztól",   "ház",   "ABLAT", "back ablat"),
    ("kéztől",   "kéz",   "ABLAT", "front ablat"),
    ("embertől", "ember", "ABLAT", "front 2syl ablat"),
    ("tanártól", "tanár", "ABLAT", "back 2syl ablat"),
    ("házhoz",   "ház",   "ALLAT", "back allat"),
    ("kézhez",   "kéz",   "ALLAT", "front-unrnd allat"),
    ("tükörhöz", "tükör", "ALLAT", "front-round allat"),
    ("emberhez", "ember", "ALLAT", "front 2syl allat"),
    ("tanárhoz", "tanár", "ALLAT", "back 2syl allat"),
]

@pytest.mark.parametrize("surface,exp_root,exp_case,label", PROXIMITY)
def test_proximity(surface, exp_root, exp_case, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.tags.get("case") == exp_case, f"[{label}] case: {r.tags.get('case')!r}"

# ── Structural cases (ACC, DAT, INS) ─────────────────────────────────────
STRUCTURAL = [
    ("házat",    "ház",   "ACC", "back acc"),
    ("tanárt",   "tanár", "ACC", "back 2syl acc"),
    ("embert",   "ember", "ACC", "front acc"),
    ("háznak",   "ház",   "DAT", "back dat"),
    ("kéznek",   "kéz",   "DAT", "front dat"),
    ("tanárnak", "tanár", "DAT", "back 2syl dat"),
    ("embernek", "ember", "DAT", "front 2syl dat"),
    ("házzal",   "ház",   "INS", "back ins assim z"),
    ("kézzel",   "kéz",   "INS", "front ins assim z"),
    ("emberrel", "ember", "INS", "front ins assim r"),
    ("úttal",    "út",    "INS", "back ins assim t"),
]

@pytest.mark.parametrize("surface,exp_root,exp_case,label", STRUCTURAL)
def test_structural(surface, exp_root, exp_case, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.tags.get("case") == exp_case, f"[{label}] case: {r.tags.get('case')!r}"

# ── Abstract/semantic cases ──────────────────────────────────────────────
ABSTRACT = [
    ("házért",   "ház",   "CAUSAL", "causal back"),
    ("kézért",   "kéz",   "CAUSAL", "causal front"),
    ("tanárért", "tanár", "CAUSAL", "causal 2syl"),
    ("házig",    "ház",   "TERMIN", "termin back"),
    ("végig",    "vég",   "TERMIN", "termin front"),
    ("házként",  "ház",   "FORMAL", "formal back"),
    ("kézként",  "kéz",   "FORMAL", "formal front"),
    ("házzá",    "ház",   "TRANSL", "transl back"),
    ("kézzé",    "kéz",   "TRANSL", "transl front"),
]

@pytest.mark.parametrize("surface,exp_root,exp_case,label", ABSTRACT)
def test_abstract(surface, exp_root, exp_case, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.tags.get("case") == exp_case, f"[{label}] case: {r.tags.get('case')!r}"

# ── Plural + case stacking ──────────────────────────────────────────────
PLURAL_CASE = [
    ("házakban",   "ház",   "INESS", "PL", "pl+iness"),
    ("házakra",    "ház",   "SUBLAT","PL", "pl+sublat"),
    ("házakhoz",   "ház",   "ALLAT", "PL", "pl+allat"),
    ("tanároknak", "tanár", "DAT",   "PL", "pl+dat 2syl"),
]

@pytest.mark.parametrize("surface,exp_root,exp_case,exp_num,label", PLURAL_CASE)
def test_plural_case(surface, exp_root, exp_case, exp_num, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.tags.get("case") == exp_case, f"[{label}] case: {r.tags.get('case')!r}"
    assert r.tags.get("num") == exp_num, f"[{label}] num: {r.tags.get('num')!r}"

# ── Assimilation with different consonants ────────────────────────────────
ASSIMILATION = [
    ("házzal",   "ház",   "INS",    "z+val=zzal"),
    ("kézzel",   "kéz",   "INS",    "z+vel=zzel"),
    ("úttal",    "út",    "INS",    "t+val=ttal"),
    ("emberrel", "ember", "INS",    "r+vel=rrel"),
    ("házzá",    "ház",   "TRANSL", "z+vá=zzá"),
    ("kézzé",    "kéz",   "TRANSL", "z+vé=zzé"),
]

@pytest.mark.parametrize("surface,exp_root,exp_case,label", ASSIMILATION)
def test_assimilation(surface, exp_root, exp_case, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.tags.get("case") == exp_case, f"[{label}] case: {r.tags.get('case')!r}"
    assert r.pos == "NOUN"

# ── All 16 productive case labels present ────────────────────────────────
ALL_CASES = {
    "ACC": "házat", "DAT": "háznak", "INS": "házzal",
    "CAUSAL": "házért", "TRANSL": "házzá",
    "INESS": "házban", "ELAT": "házból", "ILLAT": "házba",
    "SUPER": "házon", "DELAT": "házról", "SUBLAT": "házra",
    "ADESS": "háznál", "ABLAT": "háztól", "ALLAT": "házhoz",
    "TERMIN": "házig", "FORMAL": "házként",
}

@pytest.mark.parametrize("case_name", ALL_CASES.keys())
def test_case_coverage(case_name):
    surface = ALL_CASES[case_name]
    r = engine.analyze(surface)
    assert r.tags.get("case") == case_name, f"{case_name}: got {r.tags}"
