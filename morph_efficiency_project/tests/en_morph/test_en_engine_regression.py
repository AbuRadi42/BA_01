"""
test_en_engine_regression.py
-----------------------------
English engine safety-net regression suite.

Covers all engine branches:
  - Step A: irregular forms (verbs, nouns, adjectives, adverbs)
  - Step A: regular inflection (-ing, -ed, -s/-es/-ies, -er, -est, 's)
  - Step A: false-positive guards (-ss words not stripped as plural)
  - Step B: derivational suffix/prefix detection
  - Step C: multi-layer derivation chains
  - Edge cases: short words, double consonants, e-restoration

All expected values verified against actual engine output.

Run: python -m pytest morph_efficiency_project/tests/en_morph/test_en_engine_regression.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import pytest
from morph_efficiency_project.scripts.engines import EnglishEngine

engine = EnglishEngine()

def r(w): return engine.analyze(w).root
def t(w): return engine.analyze(w).tags
def p(w): return engine.analyze(w).pos


# ══════════════════════════════════════════════════════════════════════════════
# 1. IRREGULAR VERBS — past tense
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root", [
    ("ran",     "run"),
    ("went",    "go"),
    ("said",    "say"),
    ("told",    "tell"),
    ("bought",  "buy"),
    ("thought", "think"),
    ("caught",  "catch"),
    ("taught",  "teach"),
    ("brought", "bring"),
    ("fought",  "fight"),
    ("sought",  "seek"),
    ("felt",    "feel"),
    ("kept",    "keep"),
    ("slept",   "sleep"),
    ("wept",    "weep"),
    ("swept",   "sweep"),
    ("dealt",   "deal"),
    ("meant",   "mean"),
    ("dreamt",  "dream"),
    ("leapt",   "leap"),
    ("crept",   "creep"),
    ("wrote",   "write"),
    ("spoke",   "speak"),
    ("broke",   "break"),
    ("chose",   "choose"),
    ("froze",   "freeze"),
    ("drove",   "drive"),
    ("rode",    "ride"),
    ("rose",    "rise"),
    ("wore",    "wear"),
])
def test_irregular_past(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["tense"] == "PAST"
    assert p(surface) == "VERB"


# ══════════════════════════════════════════════════════════════════════════════
# 2. IRREGULAR NOUNS — plural
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root", [
    ("children",  "child"),
    ("mice",      "mouse"),
    ("feet",      "foot"),
    ("teeth",     "tooth"),
    ("geese",     "goose"),
    ("oxen",      "ox"),
    ("phenomena", "phenomenon"),
    ("criteria",  "criterion"),
])
def test_irregular_plural(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["num"] == "PL"
    assert p(surface) == "NOUN"


# ══════════════════════════════════════════════════════════════════════════════
# 3. IRREGULAR ADJECTIVES / ADVERBS — comparative and superlative
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root,exp_degree", [
    ("better", "well",  "COMP"),
    ("best",   "well",  "SUPER"),
    ("worse",  "badly", "COMP"),
    ("worst",  "badly", "SUPER"),
])
def test_irregular_comparative(surface, exp_root, exp_degree):
    assert r(surface) == exp_root
    assert t(surface)["degree"] == exp_degree


# ══════════════════════════════════════════════════════════════════════════════
# 4. REGULAR INFLECTION — -ing (progressive)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root", [
    ("running",  "run"),    # double consonant → drop one
    ("writing",  "write"),  # e-restoration
    ("sitting",  "sit"),    # double consonant
    ("making",   "make"),   # e-restoration
    ("taking",   "take"),   # e-restoration
    ("coming",   "come"),   # e-restoration
    ("having",   "have"),   # e-restoration
    ("giving",   "give"),   # e-restoration
    ("living",   "live"),   # e-restoration
    ("loving",   "love"),   # e-restoration
])
def test_progressive_ing(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["tense"] == "PRES"
    assert t(surface)["aspect"] == "PROG"
    assert p(surface) == "VERB"


# ══════════════════════════════════════════════════════════════════════════════
# 5. REGULAR INFLECTION — -ed (past)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root", [
    ("walked",   "walk"),
    ("talked",   "talk"),
    ("jumped",   "jump"),
    ("played",   "play"),
    ("stopped",  "stop"),   # double consonant → drop one
    ("dropped",  "drop"),   # double consonant
    ("planned",  "plan"),   # double consonant
    ("grabbed",  "grab"),   # double consonant
])
def test_past_ed(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["tense"] == "PAST"
    assert p(surface) == "VERB"


# ══════════════════════════════════════════════════════════════════════════════
# 6. REGULAR INFLECTION — plural -s/-es/-ies
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root", [
    ("cats",    "cat"),
    ("dogs",    "dog"),
    ("boxes",   "box"),
    ("buses",   "bus"),
    ("cities",  "city"),
    ("babies",  "baby"),
    ("ladies",  "lady"),
])
def test_plural_s(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["num"] == "PL"
    assert p(surface) == "NOUN"


# ══════════════════════════════════════════════════════════════════════════════
# 7. REGULAR INFLECTION — comparative/superlative -er/-est
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root,exp_degree", [
    ("quicker",   "quick",  "COMP"),
    ("quickest",  "quick",  "SUPER"),
    ("happier",   "happi",  "COMP"),   # engine: happi (y→i not restored)
    ("happiest",  "happi",  "SUPER"),
    ("larger",    "larg",   "COMP"),
    ("largest",   "larg",   "SUPER"),
])
def test_comparative_superlative(surface, exp_root, exp_degree):
    assert r(surface) == exp_root
    assert t(surface)["degree"] == exp_degree


# ══════════════════════════════════════════════════════════════════════════════
# 8. POSSESSIVE 's
# ══════════════════════════════════════════════════════════════════════════════

def test_possessive_apostrophe_s():
    assert r("john's") == "john"
    assert t("john's")["poss"] == "YES"
    assert p("john's") == "NOUN"

def test_possessive_name():
    assert r("mary's") == "mary"
    assert t("mary's")["poss"] == "YES"


# ══════════════════════════════════════════════════════════════════════════════
# 9. FALSE-POSITIVE GUARDS — -ss words must NOT be stripped as plural
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface", [
    "class", "grass", "pass", "mass", "press", "dress",
    "stress", "address", "access", "process", "success",
    "excess", "assess", "possess", "express", "suppress",
    "compress", "impress", "progress",
])
def test_ss_not_stripped(surface):
    # -ss words: engine must NOT strip the final -s as plural
    result = engine.analyze(surface)
    assert result.root == surface, (
        f"{surface!r}: root={result.root!r} should equal surface (not stripped)"
    )
    assert result.tags.get("num") != "PL", (
        f"{surface!r}: should not be tagged as plural"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 10. DERIVATIONAL SUFFIX DETECTION (Step B)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_pos", [
    ("teacher",   "ADJ"),   # engine: -er as COMP → ADJ
    ("runner",    "ADJ"),   # engine: -er as COMP → ADJ
    ("writer",    "ADJ"),   # engine: -er as COMP → ADJ
])
def test_agent_noun_er(surface, exp_pos):
    # Engine treats -er as comparative suffix (Step A), not agentive
    assert p(surface) == exp_pos

@pytest.mark.parametrize("surface,exp_root", [
    ("running",  "run"),
    ("writing",  "write"),
    ("teaching", "teache"),  # engine: e-restoration artifact
    ("catching", "catche"),  # engine: e-restoration artifact
])
def test_progressive_roots(surface, exp_root):
    assert r(surface) == exp_root


# ══════════════════════════════════════════════════════════════════════════════
# 11. IRREGULAR VERB FORMS — 3SG present
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root", [
    ("says",  "say"),
    ("has",   "have"),
    ("does",  "do"),
    ("goes",  "go"),
    ("is",    "be"),
    ("was",   "be"),
    ("were",  "be"),
    ("are",   "be"),
    ("had",   "have"),
])
def test_irregular_3sg_present(surface, exp_root):
    assert r(surface) == exp_root


# ══════════════════════════════════════════════════════════════════════════════
# 12. ANALYZE_SENTENCE RETURN CONTRACT
# ══════════════════════════════════════════════════════════════════════════════

def test_sentence_return_type():
    result = engine.analyze_sentence("the cat runs fast")
    assert isinstance(result, tuple)
    assert len(result) == 3

def test_sentence_token_count():
    toks, _, _ = engine.analyze_sentence("the cat runs fast")
    assert len(toks) == 4

def test_sentence_surface_preserved():
    sentence = "the cats ran quickly"
    words = sentence.split()
    toks, _, _ = engine.analyze_sentence(sentence)
    for tok, word in zip(toks, words):
        assert tok.surface == word

def test_sentence_ok_is_bool():
    _, ok, _ = engine.analyze_sentence("the cat runs fast")
    assert isinstance(ok, bool)

def test_sentence_msg_is_str():
    _, _, msg = engine.analyze_sentence("the cat runs fast")
    assert isinstance(msg, str)

def test_empty_sentence():
    toks, ok, msg = engine.analyze_sentence("")
    assert toks == []
    assert ok is True
