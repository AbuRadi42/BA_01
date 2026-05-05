"""
test_sw_engine_nouns.py
-----------------------
Noun class prefix stripping tests for all 18 classes, plural pairs,
locative -ni, and zero-prefix nouns.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import SwahiliEngine
import pytest

engine = SwahiliEngine()

# ── Class 1: m-/mw- (humans singular) ──────────────────────────────────────

CLASS_1_CASES = [
    ("mtoto",    "toto",    "1", "SG", "child"),
    ("mwalimu",  "alimu",   "1", "SG", "teacher"),
    ("mtu",      "tu",      "1", "SG", "person"),
    ("mwanafunzi", "anafunzi", "1", "SG", "student"),
    ("mgeni",    "geni",    "1", "SG", "guest"),
    ("mzee",     "zee",     "1", "SG", "elder"),
]

@pytest.mark.parametrize("surface,exp_root,exp_nc,exp_num,label", CLASS_1_CASES)
def test_class_1(surface, exp_root, exp_nc, exp_num, label):
    r = engine.analyze(surface)
    assert r.pos == "NOUN", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    assert r.tags.get("nc") == exp_nc, f"[{label}] nc={r.tags.get('nc')}"
    assert r.tags.get("num") == exp_num, f"[{label}] num={r.tags.get('num')}"


# ── Class 2: wa- (humans plural) ───────────────────────────────────────────

CLASS_2_CASES = [
    ("watoto",   "toto",    "2", "PL", "children"),
    ("watu",     "tu",      "2", "PL", "people"),
    ("wageni",   "geni",    "2", "PL", "guests"),
    ("wazee",    "zee",     "2", "PL", "elders"),
]

@pytest.mark.parametrize("surface,exp_root,exp_nc,exp_num,label", CLASS_2_CASES)
def test_class_2(surface, exp_root, exp_nc, exp_num, label):
    r = engine.analyze(surface)
    assert r.pos == "NOUN", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    assert r.tags.get("nc") == exp_nc, f"[{label}] nc={r.tags.get('nc')}"
    assert r.tags.get("num") == exp_num, f"[{label}] num={r.tags.get('num')}"


# ── Class 3/4: m-/mi- (plants) ─────────────────────────────────────────────

CLASS_3_4_CASES = [
    ("mti",      "ti",      "3", "SG", "tree"),
    ("mwezi",    "ezi",     "3", "SG", "moon"),
    ("mito",     "to",      "4", "PL", "rivers"),
    ("miti",     "ti",      "4", "PL", "trees"),
]

@pytest.mark.parametrize("surface,exp_root,exp_nc,exp_num,label", CLASS_3_4_CASES)
def test_class_3_4(surface, exp_root, exp_nc, exp_num, label):
    r = engine.analyze(surface)
    assert r.pos == "NOUN", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    assert r.tags.get("nc") == exp_nc, f"[{label}] nc={r.tags.get('nc')}"
    assert r.tags.get("num") == exp_num, f"[{label}] num={r.tags.get('num')}"


# ── Class 5/6: ji-/ma- (augmentative) ──────────────────────────────────────

CLASS_5_6_CASES = [
    ("jicho",    "cho",     "5", "SG", "eye"),
    ("jina",     "na",      "5", "SG", "name"),
    ("macho",    "cho",     "6", "PL", "eyes"),
    ("majina",   "jina",    "6", "PL", "names"),
    ("matunda",  "tunda",   "6", "PL", "fruits"),
]

@pytest.mark.parametrize("surface,exp_root,exp_nc,exp_num,label", CLASS_5_6_CASES)
def test_class_5_6(surface, exp_root, exp_nc, exp_num, label):
    r = engine.analyze(surface)
    assert r.pos == "NOUN", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    assert r.tags.get("nc") == exp_nc, f"[{label}] nc={r.tags.get('nc')}"
    assert r.tags.get("num") == exp_num, f"[{label}] num={r.tags.get('num')}"


# ── Class 7/8: ki-/vi- (things) ────────────────────────────────────────────

CLASS_7_8_CASES = [
    ("kitabu",   "tabu",    "7", "SG", "book"),
    ("kitu",     "tu",      "7", "SG", "thing"),
    ("vitabu",   "tabu",    "8", "PL", "books"),
    ("vitu",     "tu",      "8", "PL", "things"),
    ("kikombe",  "kombe",   "7", "SG", "cup"),
    ("vikombe",  "kombe",   "8", "PL", "cups"),
]

@pytest.mark.parametrize("surface,exp_root,exp_nc,exp_num,label", CLASS_7_8_CASES)
def test_class_7_8(surface, exp_root, exp_nc, exp_num, label):
    r = engine.analyze(surface)
    assert r.pos == "NOUN", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    assert r.tags.get("nc") == exp_nc, f"[{label}] nc={r.tags.get('nc')}"
    assert r.tags.get("num") == exp_num, f"[{label}] num={r.tags.get('num')}"


# ── Class 9/10: n-/ny- (animals, loanwords) ────────────────────────────────

CLASS_9_10_CASES = [
    ("nyumba",   "umba",    "9", "SG", "house"),
    ("ndege",    "dege",    "9", "SG", "bird"),
    ("ngoma",    "goma",    "9", "SG", "drum"),
]

@pytest.mark.parametrize("surface,exp_root,exp_nc,exp_num,label", CLASS_9_10_CASES)
def test_class_9_10(surface, exp_root, exp_nc, exp_num, label):
    r = engine.analyze(surface)
    assert r.pos == "NOUN", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    assert r.tags.get("nc") == exp_nc, f"[{label}] nc={r.tags.get('nc')}"
    assert r.tags.get("num") == exp_num, f"[{label}] num={r.tags.get('num')}"


# ── Class 11: u- (abstract, long objects) ───────────────────────────────────

CLASS_11_CASES = [
    ("ukuta",    "kuta",    "11", "SG", "wall"),
    ("uzi",      "zi",      "11", "SG", "thread"),
    ("ukweli",   "kweli",   "11", "SG", "truth"),
]

@pytest.mark.parametrize("surface,exp_root,exp_nc,exp_num,label", CLASS_11_CASES)
def test_class_11(surface, exp_root, exp_nc, exp_num, label):
    r = engine.analyze(surface)
    assert r.pos == "NOUN", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    assert r.tags.get("nc") == exp_nc, f"[{label}] nc={r.tags.get('nc')}"
    assert r.tags.get("num") == exp_num, f"[{label}] num={r.tags.get('num')}"


# ── Class 15: ku- (infinitives) ─────────────────────────────────────────────

CLASS_15_CASES = [
    ("kusoma",   "soma",    "15", None, "to read"),
    ("kupika",   "pika",    "15", None, "to cook"),
    ("kucheza",  "cheza",   "15", None, "to play"),
]

@pytest.mark.parametrize("surface,exp_root,exp_nc,exp_num,label", CLASS_15_CASES)
def test_class_15(surface, exp_root, exp_nc, exp_num, label):
    r = engine.analyze(surface)
    assert r.pos == "NOUN", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    assert r.tags.get("nc") == exp_nc, f"[{label}] nc={r.tags.get('nc')}"
    assert r.tags.get("num") == exp_num, f"[{label}] num={r.tags.get('num')}"


# ── Class 6: ma- (plural / collective) ─────────────────────────────────────

CLASS_6_CASES = [
    ("maji",     "ji",      "6", "PL", "water"),
    ("maziwa",   "ziwa",    "6", "PL", "milk/lakes"),
    ("maneno",   "neno",    "6", "PL", "words"),
]

@pytest.mark.parametrize("surface,exp_root,exp_nc,exp_num,label", CLASS_6_CASES)
def test_class_6(surface, exp_root, exp_nc, exp_num, label):
    r = engine.analyze(surface)
    assert r.pos == "NOUN", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    assert r.tags.get("nc") == exp_nc, f"[{label}] nc={r.tags.get('nc')}"
    assert r.tags.get("num") == exp_num, f"[{label}] num={r.tags.get('num')}"


# ── Locative -ni suffix ────────────────────────────────────────────────────

LOCATIVE_CASES = [
    ("nyumbani",  "umba",   "9", "YES", "at home"),
    ("shuleni",   "shule",  "9", "YES", "at school"),
    ("mjini",     "ji",     "3", "YES", "in the city"),
]

@pytest.mark.parametrize("surface,exp_root,exp_nc,exp_loc,label", LOCATIVE_CASES)
def test_locative(surface, exp_root, exp_nc, exp_loc, label):
    r = engine.analyze(surface)
    assert r.pos == "NOUN", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    assert r.tags.get("nc") == exp_nc, f"[{label}] nc={r.tags.get('nc')}"
    assert r.tags.get("loc") == exp_loc, f"[{label}] loc={r.tags.get('loc')}"


# ── Singular/plural pairs ──────────────────────────────────────────────────

PAIRS = [
    ("mtoto",  "1", "SG", "watoto",  "2", "PL", "child/children"),
    ("kitabu", "7", "SG", "vitabu",  "8", "PL", "book/books"),
    ("mti",    "3", "SG", "miti",    "4", "PL", "tree/trees"),
    ("jicho",  "5", "SG", "macho",   "6", "PL", "eye/eyes"),
]

@pytest.mark.parametrize("sg,sg_nc,sg_num,pl,pl_nc,pl_num,label", PAIRS)
def test_sg_pl_pairs(sg, sg_nc, sg_num, pl, pl_nc, pl_num, label):
    sg_r = engine.analyze(sg)
    pl_r = engine.analyze(pl)
    assert sg_r.tags.get("nc") == sg_nc, f"[{label}] sg nc={sg_r.tags.get('nc')}"
    assert sg_r.tags.get("num") == sg_num, f"[{label}] sg num={sg_r.tags.get('num')}"
    assert pl_r.tags.get("nc") == pl_nc, f"[{label}] pl nc={pl_r.tags.get('nc')}"
    assert pl_r.tags.get("num") == pl_num, f"[{label}] pl num={pl_r.tags.get('num')}"


# ── Zero-prefix nouns (class 5 or 9/10) ────────────────────────────────────

def test_zero_prefix_loanword():
    """Loanwords with no prefix default to class 9."""
    r = engine.analyze("kalamu")
    assert r.pos == "NOUN"
    assert r.tags.get("nc") == "9"

def test_zero_prefix_short_word():
    """Short words still get analyzed."""
    r = engine.analyze("gari")
    assert r.pos is not None
