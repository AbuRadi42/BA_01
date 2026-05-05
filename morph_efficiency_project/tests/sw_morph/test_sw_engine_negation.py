"""
test_sw_engine_negation.py
--------------------------
Negation pattern tests: ha-, si-, negative tenses, negative final vowels.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import SwahiliEngine
import pytest

engine = SwahiliEngine()

# ── ha- general negation ───────────────────────────────────────────────────

HA_NEG_CASES = [
    ("hatusoma",    "som",  {"polarity": "NEG", "person": "1", "num": "PL"},
     "1PL neg present no tense marker"),
    ("hatutasoma",  "som",  {"polarity": "NEG", "person": "1", "num": "PL", "tense": "FUT"},
     "1PL neg future"),
    ("hawasoma",    "som",  {"polarity": "NEG", "person": "3", "num": "PL"},
     "3PL neg present"),
    ("hawatapika",  "pik",  {"polarity": "NEG", "person": "3", "num": "PL", "tense": "FUT"},
     "3PL neg future"),
]

@pytest.mark.parametrize("surface,exp_root,exp_tags,label", HA_NEG_CASES)
def test_ha_negation(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.pos == "VERB", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}={r.tags.get(k)} expected {v}"


# ── si- 1SG negation ──────────────────────────────────────────────────────

SI_NEG_CASES = [
    ("sisomi",    "som",  {"polarity": "NEG", "person": "1", "num": "SG"},
     "1SG neg present"),
    ("sitasoma",  "som",  {"polarity": "NEG", "person": "1", "num": "SG", "tense": "FUT"},
     "1SG neg future"),
]

@pytest.mark.parametrize("surface,exp_root,exp_tags,label", SI_NEG_CASES)
def test_si_negation(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.pos == "VERB", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}={r.tags.get(k)} expected {v}"


# ── Negative past (ha-...-ku-) ─────────────────────────────────────────────

NEG_PAST_CASES = [
    ("hatukusoma",  "som",  {"polarity": "NEG", "person": "1", "num": "PL", "tense": "PAST"},
     "1PL neg past"),
    ("hawakusoma",  "som",  {"polarity": "NEG", "person": "3", "num": "PL", "tense": "PAST"},
     "3PL neg past"),
    ("sikumsoma",   "som",  {"polarity": "NEG", "person": "1", "num": "SG", "tense": "PAST"},
     "1SG neg past"),
]

@pytest.mark.parametrize("surface,exp_root,exp_tags,label", NEG_PAST_CASES)
def test_negative_past(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.pos == "VERB", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}={r.tags.get(k)} expected {v}"


# ── Negative present final vowel -i ────────────────────────────────────────

def test_neg_present_final_vowel_i():
    """hatusomi: negative present, final vowel -i."""
    r = engine.analyze("hatusomi")
    assert r.pos == "VERB"
    assert r.tags.get("polarity") == "NEG"
    assert r.tags.get("mood") == "NEG_PAST"


def test_neg_present_1sg_final_vowel_i():
    """sisomi: 1SG negative present, final vowel -i."""
    r = engine.analyze("sisomi")
    assert r.pos == "VERB"
    assert r.tags.get("polarity") == "NEG"
    assert r.tags.get("person") == "1"


# ── Negation polarity tag ─────────────────────────────────────────────────

def test_affirmative_has_no_neg():
    """Affirmative verb should not have polarity=NEG."""
    r = engine.analyze("anasoma")
    assert r.tags.get("polarity") != "NEG"


def test_negation_preserves_root():
    """Negation should not alter the root."""
    aff = engine.analyze("anasoma")
    neg = engine.analyze("hatusoma")
    assert aff.root == neg.root == "som"


# ── ha- with class-based subjects ─────────────────────────────────────────

def test_neg_class7():
    """hakisomi: ha- + ki- (cl7) + root + -i"""
    r = engine.analyze("hakisomi")
    assert r.pos == "VERB"
    assert r.tags.get("polarity") == "NEG"
    assert r.tags.get("subj_nc") == "7"


def test_neg_class8():
    """havisomi: ha- + vi- (cl8) + root + -i"""
    r = engine.analyze("havisomi")
    assert r.pos == "VERB"
    assert r.tags.get("polarity") == "NEG"
    assert r.tags.get("subj_nc") == "8"


# ── Negative future ───────────────────────────────────────────────────────

def test_neg_future_3sg():
    """hatasoma: ha- + a- (3SG) + ta- + root + -a"""
    r = engine.analyze("hatasoma")
    assert r.pos == "VERB"
    assert r.tags.get("polarity") == "NEG"
    assert r.tags.get("tense") == "FUT"


def test_neg_future_1pl():
    """hatutasoma: ha- + tu- (1PL) + ta- + root + -a"""
    r = engine.analyze("hatutasoma")
    assert r.pos == "VERB"
    assert r.tags.get("polarity") == "NEG"
    assert r.tags.get("tense") == "FUT"
    assert r.tags.get("person") == "1"
    assert r.tags.get("num") == "PL"
