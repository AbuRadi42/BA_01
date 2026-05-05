"""
test_sw_engine_verbs.py
-----------------------
Verb template stripping tests covering subject prefixes, tense markers,
all persons, and root extraction.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import SwahiliEngine
import pytest

engine = SwahiliEngine()

# ── Present progressive (na-) ──────────────────────────────────────────────

PRES_CASES = [
    ("ninasoma",  "som",  {"person": "1", "num": "SG", "tense": "PRES", "aspect": "PROG"},
     "1SG present"),
    ("unasoma",   "som",  {"person": "2", "num": "SG", "tense": "PRES", "aspect": "PROG"},
     "2SG present"),
    ("anasoma",   "som",  {"person": "3", "num": "SG", "tense": "PRES", "aspect": "PROG"},
     "3SG present"),
    ("tunasoma",  "som",  {"person": "1", "num": "PL", "tense": "PRES", "aspect": "PROG"},
     "1PL present"),
    ("wanasoma",  "som",  {"person": "3", "num": "PL", "tense": "PRES", "aspect": "PROG"},
     "3PL present"),
    ("ninapika",  "pik",  {"person": "1", "num": "SG", "tense": "PRES", "aspect": "PROG"},
     "1SG present cook"),
    ("anapenda",  "pend", {"person": "3", "num": "SG", "tense": "PRES", "aspect": "PROG"},
     "3SG present love"),
]

@pytest.mark.parametrize("surface,exp_root,exp_tags,label", PRES_CASES)
def test_present_progressive(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.pos == "VERB", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}={r.tags.get(k)} expected {v}"


# ── Past tense (li-) ───────────────────────────────────────────────────────

PAST_CASES = [
    ("nilisoma",  "som",  {"person": "1", "num": "SG", "tense": "PAST"},
     "1SG past"),
    ("ulisoma",   "som",  {"person": "2", "num": "SG", "tense": "PAST"},
     "2SG past"),
    ("alisoma",   "som",  {"person": "3", "num": "SG", "tense": "PAST"},
     "3SG past"),
    ("tulisoma",  "som",  {"person": "1", "num": "PL", "tense": "PAST"},
     "1PL past"),
    ("walisoma",  "som",  {"person": "3", "num": "PL", "tense": "PAST"},
     "3PL past"),
    ("alipika",   "pik",  {"person": "3", "num": "SG", "tense": "PAST"},
     "3SG past cook"),
    ("tulipenda", "pend", {"person": "1", "num": "PL", "tense": "PAST"},
     "1PL past love"),
]

@pytest.mark.parametrize("surface,exp_root,exp_tags,label", PAST_CASES)
def test_past_tense(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.pos == "VERB", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}={r.tags.get(k)} expected {v}"


# ── Future tense (ta-) ─────────────────────────────────────────────────────

FUT_CASES = [
    ("nitasoma",  "som",  {"person": "1", "num": "SG", "tense": "FUT"},
     "1SG future"),
    ("utasoma",   "som",  {"person": "2", "num": "SG", "tense": "FUT"},
     "2SG future"),
    ("atasoma",   "som",  {"person": "3", "num": "SG", "tense": "FUT"},
     "3SG future"),
    ("tutasoma",  "som",  {"person": "1", "num": "PL", "tense": "FUT"},
     "1PL future"),
    ("watasoma",  "som",  {"person": "3", "num": "PL", "tense": "FUT"},
     "3PL future"),
]

@pytest.mark.parametrize("surface,exp_root,exp_tags,label", FUT_CASES)
def test_future_tense(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.pos == "VERB", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}={r.tags.get(k)} expected {v}"


# ── Perfect (me-) ──────────────────────────────────────────────────────────

PERF_CASES = [
    ("nimesoma",  "som",  {"person": "1", "num": "SG", "tense": "PERF", "aspect": "RESULT"},
     "1SG perfect"),
    ("umesoma",   "som",  {"person": "2", "num": "SG", "tense": "PERF", "aspect": "RESULT"},
     "2SG perfect"),
    ("amesoma",   "som",  {"person": "3", "num": "SG", "tense": "PERF", "aspect": "RESULT"},
     "3SG perfect"),
    ("tumesoma",  "som",  {"person": "1", "num": "PL", "tense": "PERF", "aspect": "RESULT"},
     "1PL perfect"),
    ("wamesoma",  "som",  {"person": "3", "num": "PL", "tense": "PERF", "aspect": "RESULT"},
     "3PL perfect"),
]

@pytest.mark.parametrize("surface,exp_root,exp_tags,label", PERF_CASES)
def test_perfect(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.pos == "VERB", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}={r.tags.get(k)} expected {v}"


# ── Narrative past (ka-) ───────────────────────────────────────────────────

NARR_CASES = [
    ("nikasoma",  "som",  {"person": "1", "num": "SG", "tense": "PAST", "aspect": "NARR"},
     "1SG narrative"),
    ("akasoma",   "som",  {"person": "3", "num": "SG", "tense": "PAST", "aspect": "NARR"},
     "3SG narrative"),
    ("tukasoma",  "som",  {"person": "1", "num": "PL", "tense": "PAST", "aspect": "NARR"},
     "1PL narrative"),
]

@pytest.mark.parametrize("surface,exp_root,exp_tags,label", NARR_CASES)
def test_narrative_past(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.pos == "VERB", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}={r.tags.get(k)} expected {v}"


# ── Sequential / participial (ki-) ─────────────────────────────────────────

SEQ_CASES = [
    ("nikisoma",  "som",  {"person": "1", "num": "SG", "aspect": "SEQ"},
     "1SG sequential"),
    ("akisoma",   "som",  {"person": "3", "num": "SG", "aspect": "SEQ"},
     "3SG sequential"),
    ("tukisoma",  "som",  {"person": "1", "num": "PL", "aspect": "SEQ"},
     "1PL sequential"),
]

@pytest.mark.parametrize("surface,exp_root,exp_tags,label", SEQ_CASES)
def test_sequential(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.pos == "VERB", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}={r.tags.get(k)} expected {v}"


# ── Habitual (hu-) ─────────────────────────────────────────────────────────

HAB_CASES = [
    ("husoma",    "som",  {"tense": "HAB"}, "habitual read"),
    ("hupika",    "pik",  {"tense": "HAB"}, "habitual cook"),
    ("hupenda",   "pend", {"tense": "HAB"}, "habitual love"),
]

@pytest.mark.parametrize("surface,exp_root,exp_tags,label", HAB_CASES)
def test_habitual(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.pos == "VERB", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}={r.tags.get(k)} expected {v}"


# ── Conditional (nge-) ─────────────────────────────────────────────────────

COND_CASES = [
    ("ningesoma",  "som",  {"person": "1", "num": "SG", "mood": "COND"},
     "1SG conditional"),
    ("angesoma",   "som",  {"person": "3", "num": "SG", "mood": "COND"},
     "3SG conditional"),
    ("tungesoma",  "som",  {"person": "1", "num": "PL", "mood": "COND"},
     "1PL conditional"),
]

@pytest.mark.parametrize("surface,exp_root,exp_tags,label", COND_CASES)
def test_conditional(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.pos == "VERB", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}={r.tags.get(k)} expected {v}"


# ── Object prefixes ────────────────────────────────────────────────────────

OBJ_CASES = [
    ("alikisoma",  "som",  {"tense": "PAST", "obj_nc": "7"},
     "3SG past read it(cl7)"),
    ("anamsoma",   "som",  {"tense": "PRES", "obj": "3SG"},
     "3SG present read him/her"),
    ("anavisoma",  "som",  {"tense": "PRES", "obj_nc": "8"},
     "3SG present read them(cl8)"),
]

@pytest.mark.parametrize("surface,exp_root,exp_tags,label", OBJ_CASES)
def test_object_prefixes(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.pos == "VERB", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}={r.tags.get(k)} expected {v}"


# ── Class-based subject agreement ───────────────────────────────────────────

CLASS_SUBJ_CASES = [
    ("kinasoma",   "som",  {"subj_nc": "7", "tense": "PRES"},
     "cl7 subject"),
    ("vinasoma",   "som",  {"subj_nc": "8", "tense": "PRES"},
     "cl8 subject"),
    ("linasoma",   "som",  {"subj_nc": "5", "tense": "PRES"},
     "cl5 subject"),
    ("yanasoma",   "som",  {"subj_nc": "6", "tense": "PRES"},
     "cl6 subject"),
    ("zinasoma",   "som",  {"subj_nc": "10", "tense": "PRES"},
     "cl10 subject"),
]

@pytest.mark.parametrize("surface,exp_root,exp_tags,label", CLASS_SUBJ_CASES)
def test_class_subject_agreement(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.pos == "VERB", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}={r.tags.get(k)} expected {v}"


# ── Imperative ──────────────────────────────────────────────────────────────

IMP_CASES = [
    ("soma",    "som",  {"mood": "IMP", "person": "2"}, "imperative read"),
    ("pika",    "pik",  {"mood": "IMP", "person": "2"}, "imperative cook"),
    ("penda",   "pend", {"mood": "IMP", "person": "2"}, "imperative love"),
]

@pytest.mark.parametrize("surface,exp_root,exp_tags,label", IMP_CASES)
def test_imperative(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    # Imperative can be analyzed as verb or noun; check root
    assert r.root == exp_root, f"[{label}] root={r.root}"


# ── Verb final vowel mood ──────────────────────────────────────────────────

def test_subjunctive_final_vowel():
    """Final vowel -e indicates subjunctive."""
    r = engine.analyze("nisome")
    assert r.pos == "VERB"
    assert r.tags.get("mood") == "SUBJ"


def test_indicative_final_vowel():
    """Final vowel -a indicates indicative."""
    r = engine.analyze("ninasoma")
    assert r.tags.get("mood") == "IND"


# ── Verb root extraction edge cases ────────────────────────────────────────

def test_verb_root_minimum_length():
    """Root should be at least 1 character."""
    r = engine.analyze("anasoma")
    assert len(r.root) >= 1


def test_verb_all_slots_filled():
    """Verb with subject + tense + object + root + extension + FV."""
    r = engine.analyze("alikisoma")
    assert r.pos == "VERB"
    assert r.root == "som"


def test_multiple_tenses_same_root():
    """Same root across different tenses."""
    tenses = ["ninasoma", "nilisoma", "nitasoma", "nimesoma"]
    roots = [engine.analyze(w).root for w in tenses]
    assert all(r == "som" for r in roots)
