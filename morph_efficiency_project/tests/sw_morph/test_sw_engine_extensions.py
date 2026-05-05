"""
test_sw_engine_extensions.py
----------------------------
Verb extension stripping tests: each extension type and stacking combos.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import SwahiliEngine
import pytest

engine = SwahiliEngine()

# ── Causative (-ish-/-esh-) ─────────────────────────────────────────────────

CAUS_CASES = [
    ("pikisha",    "pik",  "CAUS",  "make cook"),
    ("someshwa",   "som",  "CAUS",  "cause to read (passive)"),
    ("pendeza",    "pend", "CAUS",  "cause to love (alternate)"),
]

@pytest.mark.parametrize("surface,exp_root,exp_ext,label", CAUS_CASES)
def test_causative(surface, exp_root, exp_ext, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root={r.root}"
    assert "CAUS" in r.derived_chain or r.tags.get("voice") == "CAUS", (
        f"[{label}] chain={r.derived_chain} tags={r.tags}"
    )


# ── Applicative (-i-/-e-/-li-/-le-) ────────────────────────────────────────

APPL_CASES = [
    ("pikia",     "pik",  "APPL", "cook for"),
    ("somea",     "som",  "APPL", "read for"),
    ("andikia",   "andik", "APPL", "write for"),
]

@pytest.mark.parametrize("surface,exp_root,exp_ext,label", APPL_CASES)
def test_applicative(surface, exp_root, exp_ext, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root={r.root}"
    assert "APPL" in r.derived_chain or r.tags.get("valence") == "APPL", (
        f"[{label}] chain={r.derived_chain} tags={r.tags}"
    )


# ── Passive (-w-) ──────────────────────────────────────────────────────────

PASS_CASES = [
    ("pikwa",     "pik",  "PASS", "be cooked"),
    ("somwa",     "som",  "PASS", "be read"),
    ("pendwa",    "pend", "PASS", "be loved"),
]

@pytest.mark.parametrize("surface,exp_root,exp_ext,label", PASS_CASES)
def test_passive(surface, exp_root, exp_ext, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root={r.root}"
    assert "PASS" in r.derived_chain or r.tags.get("voice") == "PASS", (
        f"[{label}] chain={r.derived_chain} tags={r.tags}"
    )


# ── Reciprocal (-an-) ──────────────────────────────────────────────────────

RECIP_CASES = [
    ("pendana",   "pend", "RECIP", "love each other"),
    ("pigana",    "pig",  "RECIP", "fight each other"),
    ("saidiana",  "saidi", "RECIP", "help each other"),
]

@pytest.mark.parametrize("surface,exp_root,exp_ext,label", RECIP_CASES)
def test_reciprocal(surface, exp_root, exp_ext, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root={r.root}"
    assert "RECIP" in r.derived_chain or r.tags.get("voice") == "RECIP", (
        f"[{label}] chain={r.derived_chain} tags={r.tags}"
    )


# ── Stative (-ik-/-ek-) ────────────────────────────────────────────────────

STAT_CASES = [
    ("pikika",    "pik",  "STAT", "be cookable"),
    ("someka",    "som",  "STAT", "be readable"),
    ("vunjika",   "vunj", "STAT", "be breakable"),
]

@pytest.mark.parametrize("surface,exp_root,exp_ext,label", STAT_CASES)
def test_stative(surface, exp_root, exp_ext, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root={r.root}"
    assert "STAT" in r.derived_chain or r.tags.get("valence") == "STAT", (
        f"[{label}] chain={r.derived_chain} tags={r.tags}"
    )


# ── Reversive (-u-/-o-) ────────────────────────────────────────────────────

REV_CASES = [
    ("fungua",    "fung",  "REV", "open/untie"),
    ("zibua",     "zib",   "REV", "unblock"),
]

@pytest.mark.parametrize("surface,exp_root,exp_ext,label", REV_CASES)
def test_reversive(surface, exp_root, exp_ext, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root={r.root}"
    assert "REV" in r.derived_chain or r.tags.get("valence") == "REV", (
        f"[{label}] chain={r.derived_chain} tags={r.tags}"
    )


# ── Stacking: CAUS + PASS ──────────────────────────────────────────────────

def test_caus_pass_stack():
    """pikishwa = pik + CAUS(-ish-) + PASS(-w-) + FV(-a)"""
    r = engine.analyze("pikishwa")
    assert r.root == "pik"
    assert "PASS" in r.derived_chain
    assert "CAUS" in r.derived_chain


def test_caus_pass_tags():
    """Both voice=CAUS and voice_2=PASS should be present."""
    r = engine.analyze("pikishwa")
    voices = [v for k, v in r.tags.items() if k.startswith("voice")]
    assert "CAUS" in voices
    assert "PASS" in voices


# ── Stacking: APPL + PASS ──────────────────────────────────────────────────

def test_appl_pass_stack():
    """pikiwa = pik + APPL(-i-) + PASS(-w-) + FV(-a)"""
    r = engine.analyze("pikiwa")
    assert r.root == "pik"
    assert "PASS" in r.derived_chain
    assert "APPL" in r.derived_chain


# ── Stacking: CAUS + APPL + PASS ───────────────────────────────────────────

def test_caus_appl_pass_stack():
    """pikishiwa = pik + CAUS(-ish-) + APPL(-i-) + PASS(-w-) + FV(-a)"""
    r = engine.analyze("pikishiwa")
    assert r.root == "pik"
    assert "PASS" in r.derived_chain
    assert "CAUS" in r.derived_chain


# ── Extensions in conjugated verbs ─────────────────────────────────────────

def test_extension_with_subject_tense():
    """anapikisha = a-na-pikish-a (3SG present causative cook)"""
    r = engine.analyze("anapikisha")
    assert r.pos == "VERB"
    assert r.root == "pik"
    assert r.tags.get("voice") == "CAUS"
    assert r.tags.get("tense") == "PRES"


def test_passive_with_subject_tense():
    """anapikwa = a-na-pik-w-a (3SG present passive cook)"""
    r = engine.analyze("anapikwa")
    assert r.pos == "VERB"
    assert r.root == "pik"
    assert r.tags.get("voice") == "PASS"


def test_reciprocal_with_subject_tense():
    """wanapendana = wa-na-pend-an-a (3PL present reciprocal love)"""
    r = engine.analyze("wanapendana")
    assert r.pos == "VERB"
    assert r.root == "pend"
    assert r.tags.get("voice") == "RECIP"


def test_stative_with_subject_tense():
    """inapikika = i-na-pik-ik-a (cl4/9 present stative cook)"""
    r = engine.analyze("inapikika")
    assert r.pos == "VERB"
    assert r.root == "pik"
    assert r.tags.get("valence") == "STAT"


def test_extension_chain_order():
    """Extensions should be in stripping order (outermost first)."""
    r = engine.analyze("pikishwa")
    # PASS stripped first (outermost), then CAUS
    assert r.derived_chain[0] == "PASS"
    assert r.derived_chain[1] == "CAUS"


# ── Extension minimum root guard ───────────────────────────────────────────

def test_extension_no_overstrip():
    """Short roots should not be over-stripped by extension matching."""
    r = engine.analyze("pika")
    # 'pik' is the root after FV stripping; should not try to strip further
    assert r.root == "pik"


def test_extension_preserves_root():
    """Extension stripping should leave at least 2 chars as root."""
    r = engine.analyze("somwa")
    assert len(r.root) >= 2
