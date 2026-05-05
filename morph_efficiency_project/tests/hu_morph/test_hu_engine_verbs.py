"""
test_hu_engine_verbs.py
-----------------------
Hungarian verbal paradigm tests: definite/indefinite, present/past/conditional,
subjunctive, and -lak/-lek forms.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import HungarianEngine
import pytest

engine = HungarianEngine()


# ── Past tense indefinite ─────────────────────────────────────────────────

PAST_INDEF = [
    # Back-vowel stem: ír (to write)
    ("írtam",   "ír",  {"person": "1", "num": "SG", "tense": "PAST"},           "past indef 1sg"),
    ("írtál",   "ír",  {"person": "2", "num": "SG", "tense": "PAST", "def": "INDEF"}, "past indef 2sg"),
    ("írtunk",  "ír",  {"person": "1", "num": "PL", "tense": "PAST", "def": "INDEF"}, "past indef 1pl"),
    ("írtak",   "ír",  {"person": "3", "num": "PL", "tense": "PAST", "def": "INDEF"}, "past indef 3pl"),
    # Front-vowel stem: kér (to ask)
    ("kértem",  "kér", {"person": "1", "num": "SG", "tense": "PAST"},           "past indef 1sg front"),
    ("kértél",  "kér", {"person": "2", "num": "SG", "tense": "PAST", "def": "INDEF"}, "past indef 2sg front"),
    ("kértünk", "kér", {"person": "1", "num": "PL", "tense": "PAST", "def": "INDEF"}, "past indef 1pl front"),
    ("kértünk", "kér", {"person": "1", "num": "PL", "tense": "PAST", "def": "INDEF"}, "past indef 1pl front"),
    # Longer stem: mond (to say)
    ("mondtam", "mond", {"person": "1", "num": "SG", "tense": "PAST"},           "past indef 1sg mond"),
    ("mondtál", "mond", {"person": "2", "num": "SG", "tense": "PAST", "def": "INDEF"}, "past indef 2sg mond"),
    ("mondott", "mond", {"person": "3", "num": "SG", "tense": "PAST", "def": "INDEF"}, "past indef 3sg mond"),
    ("mondtunk","mond", {"person": "1", "num": "PL", "tense": "PAST", "def": "INDEF"}, "past indef 1pl mond"),
    ("mondtak", "mond", {"person": "3", "num": "PL", "tense": "PAST", "def": "INDEF"}, "past indef 3pl mond"),
]


@pytest.mark.parametrize("surface,exp_root,exp_tags,label", PAST_INDEF)
def test_past_indef(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.pos == "VERB", f"[{label}] pos: {r.pos!r}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}: got {r.tags.get(k)!r}, exp {v!r}"


# ── Past tense definite ──────────────────────────────────────────────────

PAST_DEF = [
    ("írtad",   "ír",   {"person": "2", "num": "SG", "def": "DEF", "tense": "PAST"}, "past def 2sg"),
    ("írta",    "ír",   {"person": "3", "num": "SG", "def": "DEF", "tense": "PAST"}, "past def 3sg"),
    ("írtuk",   "ír",   {"person": "1", "num": "PL", "def": "DEF", "tense": "PAST"}, "past def 1pl"),
    ("írták",   "ír",   {"person": "3", "num": "PL", "def": "DEF", "tense": "PAST"}, "past def 3pl"),
    ("mondtad", "mond", {"person": "2", "num": "SG", "def": "DEF", "tense": "PAST"}, "past def 2sg mond"),
    ("mondta",  "mond", {"person": "3", "num": "SG", "def": "DEF", "tense": "PAST"}, "past def 3sg mond"),
    ("mondtuk", "mond", {"person": "1", "num": "PL", "def": "DEF", "tense": "PAST"}, "past def 1pl mond"),
    ("mondták", "mond", {"person": "3", "num": "PL", "def": "DEF", "tense": "PAST"}, "past def 3pl mond"),
    ("kérted",  "kér",  {"person": "2", "num": "SG", "def": "DEF", "tense": "PAST"}, "past def 2sg front"),
    ("kérte",   "kér",  {"person": "3", "num": "SG", "def": "DEF", "tense": "PAST"}, "past def 3sg front"),
    ("kértük",  "kér",  {"person": "1", "num": "PL", "def": "DEF", "tense": "PAST"}, "past def 1pl front"),
    ("kérték",  "kér",  {"person": "3", "num": "PL", "def": "DEF", "tense": "PAST"}, "past def 3pl front"),
]


@pytest.mark.parametrize("surface,exp_root,exp_tags,label", PAST_DEF)
def test_past_def(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.pos == "VERB", f"[{label}] pos: {r.pos!r}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}: got {r.tags.get(k)!r}, exp {v!r}"


# ── Present definite ────────────────────────────────────────────────────

PRESENT_DEF = [
    # -juk/-jük overlap with POSS_3PL; engine may prefer nominal.
    # Use unambiguous definite forms with long suffixes.
    ("írjátok", "ír",   {"person": "2", "num": "PL", "def": "DEF"}, "pres def 2pl"),
    ("írják",   "ír",   {"person": "3", "num": "PL", "def": "DEF"}, "pres def 3pl"),
]


@pytest.mark.parametrize("surface,exp_root,exp_tags,label", PRESENT_DEF)
def test_present_def(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.pos == "VERB", f"[{label}] pos: {r.pos!r}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}: got {r.tags.get(k)!r}"


# ── Conditional ─────────────────────────────────────────────────────────

CONDITIONAL = [
    ("írnám",    "ír",   {"tense": "COND", "def": "DEF", "person": "1", "num": "SG"}, "cond def 1sg"),
    ("írnád",    "ír",   {"tense": "COND", "def": "DEF", "person": "2", "num": "SG"}, "cond def 2sg"),
    ("írnánk",   "ír",   {"tense": "COND", "person": "1", "num": "PL"},               "cond 1pl"),
    ("kérnénk",  "kér",  {"tense": "COND", "person": "1", "num": "PL"},               "cond 1pl front"),
    ("írnék",    "ír",   {"tense": "COND", "person": "1", "num": "SG", "def": "INDEF"}, "cond indef 1sg"),
    ("írnának",  "ír",   {"tense": "COND", "person": "3", "num": "PL", "def": "INDEF"}, "cond indef 3pl"),
    ("kérnének", "kér",  {"tense": "COND", "person": "3", "num": "PL", "def": "INDEF"}, "cond indef 3pl front"),
]


@pytest.mark.parametrize("surface,exp_root,exp_tags,label", CONDITIONAL)
def test_conditional(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.pos == "VERB", f"[{label}] pos: {r.pos!r}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}: got {r.tags.get(k)!r}"


# ── Subjunctive/imperative ──────────────────────────────────────────────

SUBJUNCTIVE = [
    ("írjon",    "ír",   {"mood": "SUBJ", "person": "3", "num": "SG", "def": "INDEF"}, "subj indef 3sg"),
    ("kérjen",   "kér",  {"mood": "SUBJ", "person": "3", "num": "SG", "def": "INDEF"}, "subj indef 3sg front"),
    ("írjam",    "ír",   {"mood": "SUBJ", "person": "1", "num": "SG", "def": "DEF"},   "subj def 1sg"),
    ("kérjem",   "kér",  {"mood": "SUBJ", "person": "1", "num": "SG", "def": "DEF"},   "subj def 1sg front"),
]


@pytest.mark.parametrize("surface,exp_root,exp_tags,label", SUBJUNCTIVE)
def test_subjunctive(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.pos == "VERB", f"[{label}] pos: {r.pos!r}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}: got {r.tags.get(k)!r}"


# ── -lak/-lek (1SG subject, 2nd person object) ──────────────────────────

LAK_LEK = [
    ("látlak",   "lát", {"def": "2OBJ", "person": "1", "num": "SG"},                   "2obj pres back"),
    ("kérlek",   "kér", {"def": "2OBJ", "person": "1", "num": "SG"},                   "2obj pres front"),
    ("láttalak", "lát", {"def": "2OBJ", "person": "1", "num": "SG", "tense": "PAST"},  "2obj past back"),
    ("kértelek", "kér", {"def": "2OBJ", "person": "1", "num": "SG", "tense": "PAST"},  "2obj past front"),
]


@pytest.mark.parametrize("surface,exp_root,exp_tags,label", LAK_LEK)
def test_lak_lek(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.pos == "VERB", f"[{label}] pos: {r.pos!r}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}: got {r.tags.get(k)!r}"


# ── Past 1SG ambiguity (def=AMBIG) ──────────────────────────────────────

AMBIG_PAST = [
    ("írtam",   "ír",   "past 1sg back -- AMBIG"),
    ("mondtam", "mond", "past 1sg back mond -- AMBIG"),
    ("kértem",  "kér",  "past 1sg front -- AMBIG"),
]


@pytest.mark.parametrize("surface,exp_root,label", AMBIG_PAST)
def test_past_1sg_ambig(surface, exp_root, label):
    """Past 1SG forms are ambiguous between DEF and INDEF."""
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.tags.get("tense") == "PAST", f"[{label}] tense: {r.tags.get('tense')!r}"
    assert r.tags.get("person") == "1", f"[{label}] person: {r.tags.get('person')!r}"
    assert r.tags.get("num") == "SG", f"[{label}] num: {r.tags.get('num')!r}"
    # def should be AMBIG (engine can't disambiguate without context)
    assert r.tags.get("def") == "AMBIG", f"[{label}] def: {r.tags.get('def')!r}"


# ── Infinitive ──────────────────────────────────────────────────────────

INFINITIVE = [
    ("írni",    "ír",   "inf back"),
    ("kérni",   "kér",  "inf front"),
    ("látni",   "lát",  "inf lát"),
]


@pytest.mark.parametrize("surface,exp_root,label", INFINITIVE)
def test_infinitive(surface, exp_root, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.tags.get("mood") == "INF", f"[{label}] mood: {r.tags.get('mood')!r}"
