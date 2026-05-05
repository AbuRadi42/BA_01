"""
test_sw_engine_derivation.py
----------------------------
Derivational detection tests: agent m-, abstract u-, instrument ki-, -ji suffix.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import SwahiliEngine
import pytest

engine = SwahiliEngine()

# ── Agent nouns (m- prefix, class 1) ───────────────────────────────────────

def test_agent_noun_mpishi():
    """mpishi = m- + pishi (cook/chef)."""
    r = engine.analyze("mpishi")
    assert r.pos == "NOUN"
    assert r.tags.get("nc") in ("1", "3")


def test_agent_noun_mwalimu():
    """mwalimu = mw- + alimu (teacher)."""
    r = engine.analyze("mwalimu")
    assert r.pos == "NOUN"
    assert r.tags.get("nc") == "1"


def test_agent_noun_msomaji():
    """msomaji = m- + soma + ji (reader)."""
    r = engine.analyze("msomaji")
    assert r.pos == "NOUN"
    assert "AGENT" in str(r.tags.get("derived", "")) or "ji" in str(r.derived_chain)


def test_agent_noun_mchezaji():
    """mchezaji = m- + cheza + ji (player)."""
    r = engine.analyze("mchezaji")
    assert r.pos == "NOUN"


# ── Abstract nouns (u- prefix, class 14) ───────────────────────────────────

def test_abstract_uzuri():
    """uzuri = u- + zuri (beauty)."""
    r = engine.analyze("uzuri")
    assert r.pos == "NOUN"
    assert r.tags.get("nc") in ("11", "14")


def test_abstract_uhuru():
    """uhuru = u- + huru (freedom)."""
    r = engine.analyze("uhuru")
    assert r.pos == "NOUN"
    assert r.tags.get("nc") in ("11", "14")


def test_abstract_utoto():
    """utoto = u- + toto (childhood)."""
    r = engine.analyze("utoto")
    assert r.pos == "NOUN"
    assert r.tags.get("nc") in ("11", "14")


def test_abstract_ubaya():
    """ubaya = u- + baya (badness)."""
    r = engine.analyze("ubaya")
    assert r.pos == "NOUN"
    assert r.tags.get("nc") in ("11", "14")


# ── Instrument nouns (ki- prefix, class 7) ─────────────────────────────────

def test_instrument_kifunguo():
    """kifunguo = ki- + funguo (key)."""
    r = engine.analyze("kifunguo")
    assert r.pos == "NOUN"
    assert r.tags.get("nc") == "7"


def test_instrument_kipigo():
    """kipigo = ki- + pigo (blow)."""
    r = engine.analyze("kipigo")
    assert r.pos == "NOUN"
    assert r.tags.get("nc") == "7"


# ── Agentive -ji suffix ───────────────────────────────────────────────────

def test_ji_suffix_detection():
    """Words ending in -ji get agentive derivation detected."""
    r = engine.analyze("msomaji")
    assert r.pos == "NOUN"
    # Should detect -ji suffix
    has_ji = any("ji" in step for step in r.derived_chain) or r.tags.get("suffix") == "ji"
    assert has_ji, f"chain={r.derived_chain} tags={r.tags}"


def test_ji_suffix_root_extraction():
    """After -ji stripping, root should be the verb root."""
    r = engine.analyze("msomaji")
    # root should be som (after m- prefix and -ji suffix stripping)
    assert "som" in r.root or r.root == "soma"


# ── Derivation chain tracking ─────────────────────────────────────────────

def test_derived_chain_nonempty():
    """Derived nouns should have non-empty derived_chain."""
    r = engine.analyze("msomaji")
    assert len(r.derived_chain) > 0


def test_derived_chain_contains_type():
    """Derived chain should indicate the derivation type."""
    r = engine.analyze("msomaji")
    chain_str = " ".join(r.derived_chain)
    assert "AGENT" in chain_str or "ji" in chain_str


# ── Non-derived nouns ─────────────────────────────────────────────────────

def test_non_derived_noun_kitabu():
    """kitabu is not a derived noun (it's a loanword)."""
    r = engine.analyze("kitabu")
    assert r.pos == "NOUN"
    assert r.root == "tabu"
