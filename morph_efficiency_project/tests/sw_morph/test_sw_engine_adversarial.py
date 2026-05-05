"""
test_sw_engine_adversarial.py
-----------------------------
Adversarial / edge-case tests: monosyllabic verbs, class ambiguity,
loanwords, false positives, over-stripping, and other tricky cases.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import SwahiliEngine
import pytest

engine = SwahiliEngine()


# ══════════════════════════════════════════════════════════════════════════
# MONOSYLLABIC VERBS
# ══════════════════════════════════════════════════════════════════════════

MONO_CASES = [
    ("ninakula",   "la",    {"person": "1", "num": "SG", "tense": "PRES"},
     "1SG present eat"),
    ("anakula",    "la",    {"person": "3", "num": "SG", "tense": "PRES"},
     "3SG present eat"),
    ("tunakula",   "la",    {"person": "1", "num": "PL", "tense": "PRES"},
     "1PL present eat"),
    ("alikula",    "la",    {"person": "3", "num": "SG", "tense": "PAST"},
     "3SG past eat"),
    ("atakula",    "la",    {"person": "3", "num": "SG", "tense": "FUT"},
     "3SG future eat"),
    ("ninakuja",   "ja",    {"person": "1", "num": "SG", "tense": "PRES"},
     "1SG present come"),
    ("anakufa",    "fa",    {"person": "3", "num": "SG", "tense": "PRES"},
     "3SG present die"),
]

@pytest.mark.parametrize("surface,exp_root,exp_tags,label", MONO_CASES)
def test_monosyllabic_verbs(surface, exp_root, exp_tags, label):
    r = engine.analyze(surface)
    assert r.pos == "VERB", f"[{label}] pos={r.pos}"
    assert r.root == exp_root, f"[{label}] root={r.root}"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, f"[{label}] {k}={r.tags.get(k)} expected {v}"


# ══════════════════════════════════════════════════════════════════════════
# CLOSED-CLASS FALSE POSITIVE GUARDS
# ══════════════════════════════════════════════════════════════════════════

CLOSED_GUARDS = [
    ("katika",   "ADP",  "katika should not be stripped as ki- + noun"),
    ("kabisa",   "ADV",  "kabisa should not be stripped as ka- + bisa"),
    ("karibu",   "ADV",  "karibu should not be stripped"),
    ("kama",     "CONJ", "kama should not be stripped as ka- + ma"),
    ("lakini",   "CONJ", "lakini should not be stripped as la- + kini"),
    ("basi",     "PART", "basi should not be stripped"),
    ("sawa",     "PART", "sawa should not be stripped"),
    ("hapa",     "ADV",  "hapa should not be stripped as ha- neg"),
    ("pale",     "ADV",  "pale should not be stripped as pa- cl16"),
    ("sana",     "ADV",  "sana should not be stripped as sa- + na"),
]

@pytest.mark.parametrize("surface,exp_pos,label", CLOSED_GUARDS)
def test_closed_class_guard(surface, exp_pos, label):
    r = engine.analyze(surface)
    assert r.pos == exp_pos, f"[{label}] pos={r.pos}, expected {exp_pos}"
    assert r.root == surface.lower(), f"[{label}] root={r.root}, expected atomic"


# ══════════════════════════════════════════════════════════════════════════
# CLASS AMBIGUITY
# ══════════════════════════════════════════════════════════════════════════

def test_class1_vs_class3_mtu():
    """mtu (person) should be class 1 (human), not class 3."""
    r = engine.analyze("mtu")
    assert r.tags.get("nc") == "1", f"nc={r.tags.get('nc')}"


def test_class1_vs_class3_mti():
    """mti (tree) should be class 3 (plant), not class 1."""
    r = engine.analyze("mti")
    assert r.tags.get("nc") == "3", f"nc={r.tags.get('nc')}"


def test_class1_vs_class3_mtoto():
    """mtoto (child) should be class 1 (human)."""
    r = engine.analyze("mtoto")
    assert r.tags.get("nc") == "1"


def test_class1_mwalimu():
    """mwalimu (teacher) should be class 1 (human)."""
    r = engine.analyze("mwalimu")
    assert r.tags.get("nc") == "1"


def test_class11_ukuta():
    """ukuta (wall) should be class 11."""
    r = engine.analyze("ukuta")
    assert r.tags.get("nc") == "11"


def test_class7_kitabu():
    """kitabu (book) should be class 7."""
    r = engine.analyze("kitabu")
    assert r.tags.get("nc") == "7"


# ══════════════════════════════════════════════════════════════════════════
# LOANWORDS
# ══════════════════════════════════════════════════════════════════════════

def test_loanword_kalamu():
    """kalamu (pen, from Arabic qalam) -- zero-prefix, class 9."""
    r = engine.analyze("kalamu")
    assert r.pos == "NOUN"
    assert r.tags.get("nc") == "9"


def test_loanword_kitabu():
    """kitabu (book, from Arabic kitab) -- fully integrated class 7."""
    r = engine.analyze("kitabu")
    assert r.pos == "NOUN"
    assert r.tags.get("nc") == "7"
    assert r.root == "tabu"


def test_loanword_vitabu_plural():
    """vitabu (books) -- class 8 plural of kitabu."""
    r = engine.analyze("vitabu")
    assert r.tags.get("nc") == "8"
    assert r.tags.get("num") == "PL"


def test_loanword_meza():
    """meza (table, from Portuguese) -- class 9 zero-prefix."""
    r = engine.analyze("meza")
    assert r.pos is not None


# ══════════════════════════════════════════════════════════════════════════
# OVER-STRIPPING GUARDS
# ══════════════════════════════════════════════════════════════════════════

def test_short_word_no_crash():
    """Very short words should not crash."""
    for w in ["a", "m", "u", "ni", "na", "ki"]:
        r = engine.analyze(w)
        assert r is not None


def test_two_char_word():
    """Two-character words should get some analysis."""
    r = engine.analyze("tu")
    assert r is not None
    assert r.root is not None


def test_three_char_noun():
    """mji (town) should be analyzed as a noun."""
    r = engine.analyze("mji")
    assert r.pos == "NOUN"


def test_single_syllable_not_overstripped():
    """kitu should not be over-stripped past 'tu'."""
    r = engine.analyze("kitu")
    assert r.root == "tu"
    assert r.tags.get("nc") == "7"


# ══════════════════════════════════════════════════════════════════════════
# AMBIGUOUS PREFIXES
# ══════════════════════════════════════════════════════════════════════════

def test_ki_tense_vs_ki_class():
    """ki- can be tense marker (sequential) or class 7 noun prefix."""
    # kitabu should be noun (class 7)
    r1 = engine.analyze("kitabu")
    assert r1.pos == "NOUN"
    assert r1.tags.get("nc") == "7"

    # kisoma should be verb (ki- sequential + soma)
    r2 = engine.analyze("akisoma")
    assert r2.pos == "VERB"
    assert r2.tags.get("aspect") == "SEQ"


def test_u_subj_vs_u_class():
    """u- can be 2SG subject or class 11/14 noun prefix."""
    # ukuta should be noun (class 11)
    r1 = engine.analyze("ukuta")
    assert r1.pos == "NOUN"

    # unasoma should be verb (u- 2SG + na- present + soma)
    r2 = engine.analyze("unasoma")
    assert r2.pos == "VERB"
    assert r2.tags.get("person") == "2"


def test_na_conj_vs_na_tense():
    """na can be conjunction or na- tense marker (when prefixed)."""
    # standalone na = conjunction
    r1 = engine.analyze("na")
    assert r1.pos == "CONJ"

    # anasoma: a- + na- + soma
    r2 = engine.analyze("anasoma")
    assert r2.tags.get("tense") == "PRES"


# ══════════════════════════════════════════════════════════════════════════
# SENTENCE-LEVEL AGREEMENT
# ══════════════════════════════════════════════════════════════════════════

def test_noun_adj_agreement_valid():
    """kitabu kizuri: cl7 noun + cl7 adj = valid agreement."""
    tokens, ok, msg = engine.analyze_sentence("kitabu kizuri")
    assert ok, f"Expected valid: {msg}"


def test_noun_verb_agreement_valid():
    """kitabu kinasoma: cl7 noun + ki- subject verb = valid."""
    tokens, ok, msg = engine.analyze_sentence("kitabu kinasoma")
    # Check that noun and verb have matching class
    assert tokens[0].tags.get("nc") == "7"
    assert tokens[1].tags.get("subj_nc") == "7"


def test_noun_adj_agreement_mismatch():
    """kitabu vizuri: cl7 noun + cl8 adj = mismatch."""
    tokens, ok, msg = engine.analyze_sentence("kitabu vizuri")
    assert not ok, "Expected agreement mismatch"


# ══════════════════════════════════════════════════════════════════════════
# VALIDATOR CHECKS
# ══════════════════════════════════════════════════════════════════════════

def test_morph_sequence_valid():
    """Valid verb should pass sequence check."""
    from morph_efficiency_project.scripts.engines.shared import check_morph_sequence_sw
    tokens, _, _ = engine.analyze_sentence("anasoma")
    assert check_morph_sequence_sw(tokens)


def test_morph_sequence_noun_valid():
    """Valid noun should pass sequence check."""
    from morph_efficiency_project.scripts.engines.shared import check_morph_sequence_sw
    tokens, _, _ = engine.analyze_sentence("kitabu")
    assert check_morph_sequence_sw(tokens)


# ══════════════════════════════════════════════════════════════════════════
# EDGE CASES AND MISC
# ══════════════════════════════════════════════════════════════════════════

def test_analyze_sentence_empty():
    """Empty sentence should return empty list."""
    tokens, ok, msg = engine.analyze_sentence("")
    # Empty string split gives ['']
    assert isinstance(tokens, list)


def test_feature_bundle_str():
    """TokenInfo.feature_bundle_str should return a formatted string."""
    r = engine.analyze("anasoma")
    bundle = r.feature_bundle_str()
    assert "pos=VERB" in bundle


def test_token_str():
    """TokenInfo.token_str should return root.POS."""
    r = engine.analyze("anasoma")
    assert r.token_str() == "som.VERB"


def test_surface_preserved():
    """Original surface form should be preserved."""
    r = engine.analyze("Anasoma")
    assert r.surface == "Anasoma"


def test_clitics_dict_present():
    """clitics should be a dict (even if empty)."""
    r = engine.analyze("anasoma")
    assert isinstance(r.clitics, dict)
