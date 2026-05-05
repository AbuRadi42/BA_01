"""
test_hu_engine_derivation.py
-----------------------------
Hungarian derivational suffix and prefix tests.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import HungarianEngine
import pytest

engine = HungarianEngine()


# ── Nominal derivations ────────────────────────────────────────────────

NOMINAL_DERIVS = [
    ("szépség",   "szép",     "QUALITY_NOUN",  "ság/ség: szépség"),
    ("emberség",  "ember",    "QUALITY_NOUN",  "ság/ség: emberség"),
    ("írás",      "ír",       "VERBAL_NOUN",   "ás/és: írás"),
    ("kérés",     "kér",      "VERBAL_NOUN",   "ás/és: kérés"),
    ("tanító",    "tanít",    "AGENT_NOUN",    "ó/ő: tanító"),
]


@pytest.mark.parametrize("surface,exp_root,exp_derives,label", NOMINAL_DERIVS)
def test_nominal_derivation(surface, exp_root, exp_derives, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    # Check chain contains the expected derivation
    found = any(exp_derives in c for c in r.derived_chain)
    assert found, f"[{label}] chain {r.derived_chain} missing {exp_derives}"


# ── Adjectival derivations ──────────────────────────────────────────────

ADJ_DERIVS = [
    ("írható",    "ír",      "POSSIBILITY_ADJ", "ható/hető: írható"),
    ("kérhető",   "kér",     "POSSIBILITY_ADJ", "ható/hető: kérhető"),
    ("erős",      "erő",     "POSSESSIVE_ADJ",  "s: erős"),
]


@pytest.mark.parametrize("surface,exp_root,exp_derives,label", ADJ_DERIVS)
def test_adj_derivation(surface, exp_root, exp_derives, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    found = any(exp_derives in c for c in r.derived_chain)
    assert found, f"[{label}] chain {r.derived_chain} missing {exp_derives}"


# ── Verbal derivations ─────────────────────────────────────────────────

VERBAL_DERIVS = [
    # -hat/-het possibility derivation: test via írhat which is handled
    # at the derivational level (Step B finds -hat as POSSIBILITY_V suffix
    # or -ható as POSSIBILITY_ADJ suffix).
    ("írható",  "ír",  "POSSIBILITY_ADJ",  "ható/hető: írható (also in adj)"),
]


@pytest.mark.parametrize("surface,exp_root,exp_derives,label", VERBAL_DERIVS)
def test_verbal_derivation(surface, exp_root, exp_derives, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    found = any(exp_derives in c for c in r.derived_chain)
    assert found, f"[{label}] chain {r.derived_chain} missing {exp_derives}"


# ── Prefix derivations ─────────────────────────────────────────────────

PREFIX_DERIVS = [
    ("megír",     "ír",    "PERF",    "meg- prefix"),
    ("leír",      "ír",    "DOWN",    "le- prefix"),
    ("visszamegy","megy",  "BACK",    "vissza- prefix"),
    ("visszaír",  "ír",    "BACK",    "vissza- prefix short stem"),
    ("beír",      "ír",    "IN",      "be- prefix"),
]


@pytest.mark.parametrize("surface,exp_root,exp_derives,label", PREFIX_DERIVS)
def test_prefix_derivation(surface, exp_root, exp_derives, label):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: {r.root!r}"
    found = any(exp_derives in c for c in r.derived_chain)
    assert found, f"[{label}] chain {r.derived_chain} missing {exp_derives}"


# ── Multi-layer derivation (Step C iterative) ──────────────────────────

def test_multi_layer_prefix_suffix():
    """megírtam: prefix meg- + past 1SG -> root ír."""
    r = engine.analyze("megírtam")
    assert r.root == "ír", f"root: {r.root!r}"
    assert r.tags.get("tense") == "PAST"
    assert any("PERF" in c for c in r.derived_chain)


def test_multi_layer_deriv_inflection():
    """szépségben: szépség (deriv) + -ben (iness) -> root szép."""
    r = engine.analyze("szépségben")
    assert r.root == "szép", f"root: {r.root!r}"
    assert r.tags.get("case") == "INESS"


def test_prefix_stripped_in_step_c():
    """beírtam: prefix be- + past 1SG. Step C peels be-."""
    r = engine.analyze("beírtam")
    assert r.root == "ír", f"root: {r.root!r}"
    assert r.tags.get("tense") == "PAST"


# ── Derivation does not over-strip ──────────────────────────────────────

def test_derivation_preserves_short_stems():
    """Short stems should not have derivation stripped below 2 chars."""
    r = engine.analyze("ír")
    assert r.derived_chain == [], f"chain: {r.derived_chain}"
    assert r.root == "ír"


def test_derivation_not_applied_to_closed_class():
    """Closed-class words should not undergo derivation."""
    r = engine.analyze("nem")
    assert r.derived_chain == []
    assert r.pos == "PART"
