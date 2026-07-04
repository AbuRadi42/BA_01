"""
test_he_engine_units.py
-----------------------
Hand-written unit cases for the Hebrew (עברית) morphology engine, mirroring the
style of the Arabic engine's comprehensive tests. Each case asserts a subset of
(pos, root, binyan, tags). A field left as None means "do not check".

These are LINGUISTICALLY CORRECT target analyses. Cases the milestone-1 engine
is known to get wrong (because the unpointed surface is genuinely ambiguous, or
because a feature needs lexical context the engine does not yet have) are marked
with pytest.mark.xfail with an explicit reason, so the honest coverage boundary
is visible in the test report rather than hidden.

Gold morphology is cross-checked against Universal Dependencies UD_Hebrew-HTB.
There is no native Hebrew speaker on this project; UD is the ground truth for
everything it annotates. The shoresh (root) is NOT annotated in UD, so root
assertions here are the author's hand analysis and are the weakest-validated.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from morph_efficiency_project.scripts.engines import HebrewEngine  # noqa: E402

engine = HebrewEngine()


def _check(surface, *, pos=None, root=None, binyan=None, tags_subset=None):
    info = engine.analyze(surface)
    if pos is not None:
        assert info.pos == pos, f"{surface}: pos {info.pos} != {pos}"
    if root is not None:
        assert info.root == root, f"{surface}: root {info.root} != {root}"
    if binyan is not None:
        assert info.tags.get("binyan") == binyan, \
            f"{surface}: binyan {info.tags.get('binyan')} != {binyan}"
    if tags_subset:
        for k, v in tags_subset.items():
            assert info.tags.get(k) == v, \
                f"{surface}: tag {k}={info.tags.get(k)} != {v}"


# ── The seven binyanim, clear surface signatures ─────────────────────────────

@pytest.mark.parametrize("surface,binyan", [
    ("התקרב", "HITPAEL"),      # he drew near
    ("מתגורר", "HITPAEL"),     # residing (participle)
    ("נסגר", "NIFAL"),          # was closed
    ("נמצא", "NIFAL"),          # is found
    ("הגיש", "HIFIL"),          # he submitted
    ("מסביר", "HIFIL"),         # explaining (participle)
    ("הורד", "HUFAL"),          # was brought down
    ("מבקש", "PIEL"),           # requesting (participle)
])
def test_binyan_clear_signatures(surface, binyan):
    _check(surface, binyan=binyan)


@pytest.mark.parametrize("surface", ["ביקש", "שוחרר", "טופל"])
@pytest.mark.xfail(reason="PIEL/PUAL past has no surface prefix; unpointed it is "
                          "indistinguishable from PAAL. Defaults to PAAL.",
                   strict=False)
def test_binyan_ambiguous_piel_pual(surface):
    # These are PIEL/PUAL but carry no niqqud-free signal, so the engine
    # honestly falls back to PAAL. Documented, not hidden.
    info = engine.analyze(surface)
    assert info.tags.get("binyan") in ("PIEL", "PUAL")


# ── Verb inflection (tense / person / number) ────────────────────────────────

def test_past_first_singular():
    _check("כתבתי", pos="VERB", tags_subset={"tense": "PAST", "person": "1", "num": "SG"})

def test_past_first_plural():
    _check("כתבנו", pos="VERB", tags_subset={"tense": "PAST", "person": "1", "num": "PL"})

def test_infinitive():
    _check("להתקרב", pos="VERB", binyan="HITPAEL", tags_subset={"verbform": "INF"})


# ── Nominal number / gender ──────────────────────────────────────────────────

def test_masc_plural():
    _check("ילדים", pos="NOUN", tags_subset={"num": "PL", "gender": "M"})

def test_fem_plural():
    _check("דלתות", pos="NOUN", tags_subset={"num": "PL", "gender": "F"})

def test_dual():
    _check("רגליים", pos="NOUN", tags_subset={"num": "DU"})

def test_fem_singular():
    _check("פרה", pos="NOUN", tags_subset={"num": "SG", "gender": "F"})


@pytest.mark.parametrize("surface", ["מלכה", "מכוניות", "מקום"])
@pytest.mark.xfail(reason="A מ-initial nominal (root-מ or mishkal maqtel) is not "
                          "separable context-free from a מ-participle; the "
                          "engine over-predicts VERB here. Needs the sentence "
                          "grammar layer (milestone 2).",
                   strict=False)
def test_mem_initial_noun_ambiguity(surface):
    assert engine.analyze(surface).pos == "NOUN"


# ── Closed class ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("surface,pos", [
    ("הוא", "PRON"), ("היא", "PRON"), ("אני", "PRON"),
    ("של", "ADP"), ("על", "ADP"), ("עם", "ADP"),
    ("אבל", "CCONJ"), ("כי", "SCONJ"),
    ("לא", "ADV"), ("מאוד", "ADV"),
    ("היה", "AUX"), ("אין", "AUX"),
])
def test_closed_class(surface, pos):
    _check(surface, pos=pos)


def test_pronoun_features():
    _check("הוא", pos="PRON", tags_subset={"person": "3", "num": "SG", "gender": "M"})


# ── Shoresh extraction (weakest stream; author hand-gold, not UD) ─────────────

@pytest.mark.parametrize("surface,root", [
    ("כתבתי", "כתב"),
    ("נסגרו", "סגר"),
    ("התקרב", "קרב"),
    ("מדבר", "דבר"),
])
def test_root_clean_triliteral(surface, root):
    _check(surface, root=root)


@pytest.mark.parametrize("surface", ["ילדים", "שולחן"])
@pytest.mark.xfail(reason="Weak/quadriliteral roots and I-yod nouns are not "
                          "reconstructed by the milestone-1 heuristic root peeler.",
                   strict=False)
def test_root_known_gaps(surface):
    # ילד root is י-ל-ד but the heuristic drops the mater-lectionis yod;
    # documented gap for milestone 2.
    assert engine.analyze(surface).root in ("ילד", "שלחן")


# ── Non-Hebrew / numerals / punctuation ──────────────────────────────────────

def test_number():
    _check("2020", pos="NUM")

def test_punct():
    assert engine.analyze(".").pos == "PUNCT"

def test_latin_is_x():
    assert engine.analyze("Google").pos == "X"
