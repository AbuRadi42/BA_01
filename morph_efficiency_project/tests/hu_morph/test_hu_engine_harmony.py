"""
test_hu_engine_harmony.py
--------------------------
Vowel harmony tests: back, front-unrounded, front-rounded, transparent
vowels, and anti-harmonic stems.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import HungarianEngine
from morph_efficiency_project.scripts.engines.hu_engine import (
    ALL_VOWELS, BACK_VOWELS, FRONT_UNROUNDED, FRONT_ROUNDED,
    TRANSPARENT_VOWELS,
)
import pytest

engine = HungarianEngine()


# ── Back-vowel stems select back suffixes ────────────────────────────────

BACK_STEMS = [
    ("házban",   "ház",    "INESS", "back: ház+ban"),
    ("házból",   "ház",    "ELAT",  "back: ház+ból"),
    ("tanárban", "tanár",  "INESS", "back: tanár+ban"),
    ("tanárból", "tanár",  "ELAT",  "back: tanár+ból"),
    ("házra",    "ház",    "SUBLAT","back: ház+ra"),
    ("háztól",   "ház",    "ABLAT", "back: ház+tól"),
    ("házhoz",   "ház",    "ALLAT", "back: ház+hoz"),
    ("háznak",   "ház",    "DAT",   "back: ház+nak"),
]


@pytest.mark.parametrize("surface,exp_root,exp_case,label", BACK_STEMS)
def test_back_harmony(surface, exp_root, exp_case, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.tags.get("case") == exp_case, f"[{label}] case: {r.tags.get('case')!r}"


# ── Front-unrounded stems select front suffixes ─────────────────────────

FRONT_UNRND = [
    ("kézben",   "kéz",    "INESS", "front-unrnd: kéz+ben"),
    ("kézből",   "kéz",    "ELAT",  "front-unrnd: kéz+ből"),
    ("kézre",    "kéz",    "SUBLAT","front-unrnd: kéz+re"),
    ("kéztől",   "kéz",    "ABLAT", "front-unrnd: kéz+től"),
    ("kézhez",   "kéz",    "ALLAT", "front-unrnd: kéz+hez"),
    ("kéznek",   "kéz",    "DAT",   "front-unrnd: kéz+nek"),
    ("emberben", "ember",  "INESS", "front-unrnd: ember+ben"),
    ("embernek", "ember",  "DAT",   "front-unrnd: ember+nek"),
]


@pytest.mark.parametrize("surface,exp_root,exp_case,label", FRONT_UNRND)
def test_front_unrnd_harmony(surface, exp_root, exp_case, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.tags.get("case") == exp_case, f"[{label}] case: {r.tags.get('case')!r}"


# ── Front-rounded stems select front-rounded suffixes ────────────────────

FRONT_ROUND = [
    ("tükörben", "tükör",  "INESS", "front-round: tükör+ben"),
    ("tükörből", "tükör",  "ELAT",  "front-round: tükör+ből"),
    ("tükörhöz", "tükör",  "ALLAT", "front-round: tükör+höz"),
]


@pytest.mark.parametrize("surface,exp_root,exp_case,label", FRONT_ROUND)
def test_front_round_harmony(surface, exp_root, exp_case, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    assert r.tags.get("case") == exp_case, f"[{label}] case: {r.tags.get('case')!r}"


# ── Transparent vowel handling ──────────────────────────────────────────

def test_transparent_vowels_defined():
    """Transparent vowels should be i and i-acute."""
    assert "i" in TRANSPARENT_VOWELS
    assert "í" in TRANSPARENT_VOWELS


def test_harmony_classifies_all_vowels():
    """Every vowel in ALL_VOWELS should be classifiable."""
    for v in ALL_VOWELS:
        cls = engine._classify_vowel(v)
        assert cls in ("BACK", "FRONT_UNROUND", "FRONT_ROUND"), f"vowel {v!r} -> {cls}"


def test_transparent_vowel_stem_accepts_both():
    """Stems with only transparent vowels accept any harmony."""
    # 'ír' has only í (transparent). Engine returns None from
    # _get_last_harmonic_vowel, so harmony passes trivially.
    assert engine._get_last_harmonic_vowel("ír") is None
    assert engine._harmony_ok("ír", "ban") is True
    assert engine._harmony_ok("ír", "ben") is True
    assert engine._harmony_ok("ír", "höz") is True


# ── Anti-harmonic stem handling ─────────────────────────────────────────

ANTI_HARMONIC = [
    # Front-vowel stems that take back suffixes (from irregulars)
    ("híd",  "BACK"),
    ("cél",  "BACK"),
    ("nyíl", "BACK"),
    ("díj",  "BACK"),
    ("sír",  "BACK"),
    ("tél",  "BACK"),
    ("dél",  "BACK"),
    ("fél",  "BACK"),
]


@pytest.mark.parametrize("stem,exp_harmony", ANTI_HARMONIC)
def test_anti_harmonic_listed(stem, exp_harmony):
    """Anti-harmonic stems should be listed in the irregulars file."""
    ah = engine.irregulars.get("anti_harmonic_nouns", {})
    assert stem in ah, f"{stem} not in anti_harmonic_nouns"
    assert ah[stem].get("harmony") == exp_harmony


# ── Harmony rejection: wrong variant should not match ────────────────────

def test_back_stem_rejects_front_suffix():
    """A back-vowel stem like 'ház' should reject a front suffix like '-ben'."""
    assert engine._harmony_ok("ház", "ben") is False


def test_front_stem_rejects_back_suffix():
    """A front-vowel stem like 'kéz' should reject a back suffix like '-ban'."""
    assert engine._harmony_ok("kéz", "ban") is False


def test_front_round_rejects_back():
    """A front-rounded stem like 'tükör' rejects back suffix '-hoz'."""
    assert engine._harmony_ok("tükör", "hoz") is False


def test_front_round_accepts_front_unround():
    """For 2-way suffixes, front-round and front-unround are compatible."""
    assert engine._harmony_ok("tükör", "ben") is True
    assert engine._harmony_ok("kéz", "ben") is True


# ── Slot 7 harmony bypass ──────────────────────────────────────────────

def test_slot7_harmony_bypass():
    """Slot 7 (PERSON_DEF) skips harmony check."""
    # -tam is back-harmonic, but should match any stem in slot 7
    assert engine._harmony_ok("kér", "tam", slot_order=7) is True
    assert engine._harmony_ok("tükör", "tam", slot_order=7) is True


# ── Invariant suffix harmony bypass ──────────────────────────────────────

def test_invariant_suffix_bypass():
    """Invariant suffixes skip harmony check regardless of slot."""
    assert engine._harmony_ok("kéz", "ért") is True  # CAUSAL
    assert engine._harmony_ok("kéz", "ig") is True   # TERMIN
    assert engine._harmony_ok("kéz", "ként") is True  # FORMAL
