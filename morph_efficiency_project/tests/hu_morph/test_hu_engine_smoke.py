"""
test_hu_engine_smoke.py
-----------------------
Hungarian morphology engine smoke tests.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import HungarianEngine
import pytest

engine = HungarianEngine()


# ── Basic nominal cases ────────────────────────────────────────────────────

NOMINAL_CASES = [
    ("házban",  "ház",   "NOUN", {"case": "INESS"},  "inessive"),
    ("házból",  "ház",   "NOUN", {"case": "ELAT"},   "elative"),
    ("házba",   "ház",   "NOUN", {"case": "ILLAT"},  "illative"),
    ("házra",   "ház",   "NOUN", {"case": "SUBLAT"}, "sublative"),
    ("házról",  "ház",   "NOUN", {"case": "DELAT"},  "delative"),
    ("házon",   "ház",   "NOUN", {"case": "SUPER"},  "superessive"),
    ("házhoz",  "ház",   "NOUN", {"case": "ALLAT"},  "allative"),
    ("háztól",  "ház",   "NOUN", {"case": "ABLAT"},  "ablative"),
    ("házzal",  "ház",   "NOUN", {"case": "INS"},    "instrumental assimil"),
    ("házat",   "ház",   "NOUN", {"case": "ACC"},    "accusative"),
    ("háznak",  "ház",   "NOUN", {"case": "DAT"},    "dative"),
    ("háznál",  "ház",   "NOUN", {"case": "ADESS"},  "adessive"),
    ("házért",  "ház",   "NOUN", {"case": "CAUSAL"}, "causal"),
    ("házig",   "ház",   "NOUN", {"case": "TERMIN"}, "terminative"),
    ("házként", "ház",   "NOUN", {"case": "FORMAL"}, "formal"),
    ("házak",   "ház",   "NOUN", {"num": "PL"},      "plural"),
    ("házam",   "ház",   "NOUN", {"poss": "1SG"},    "possessive 1SG"),
]


@pytest.mark.parametrize("surface,exp_root,exp_pos,exp_tags,label", NOMINAL_CASES)
def test_nominal_basic(surface, exp_root, exp_pos, exp_tags, label):
    result = engine.analyze(surface)
    assert result.root == exp_root, f"[{label}] root: got {result.root!r}, expected {exp_root!r}"
    assert result.pos == exp_pos, f"[{label}] pos: got {result.pos!r}, expected {exp_pos!r}"
    for k, v in exp_tags.items():
        assert result.tags.get(k) == v, (
            f"[{label}] tag {k}: got {result.tags.get(k)!r}, expected {v!r}"
        )


# ── Basic verbal forms ─────────────────────────────────────────────────────

VERBAL_CASES = [
    ("írtam",  "ír",   "VERB", {"tense": "PAST"},                "past 1SG"),
    ("írtad",  "ír",   "VERB", {"tense": "PAST", "def": "DEF"},  "past 2SG DEF"),
    ("mondtam","mond", "VERB", {"tense": "PAST"},                 "past 1SG mond"),
    ("mondta", "mond", "VERB", {"tense": "PAST", "def": "DEF"},  "past 3SG DEF"),
    ("látlak", "lát",  "VERB", {"def": "2OBJ"},                  "2OBJ present"),
    ("kérlek", "kér",  "VERB", {"def": "2OBJ"},                  "2OBJ present front"),
]


@pytest.mark.parametrize("surface,exp_root,exp_pos,exp_tags,label", VERBAL_CASES)
def test_verbal_basic(surface, exp_root, exp_pos, exp_tags, label):
    result = engine.analyze(surface)
    assert result.root == exp_root, f"[{label}] root: got {result.root!r}"
    assert result.pos == exp_pos, f"[{label}] pos: got {result.pos!r}"
    for k, v in exp_tags.items():
        assert result.tags.get(k) == v, f"[{label}] tag {k}: got {result.tags.get(k)!r}"


# ── Irregular forms ────────────────────────────────────────────────────────

IRREGULAR_CASES = [
    ("volt",    "van",  "VERB", "past of van"),
    ("ment",    "megy", "VERB", "past of megy"),
    ("jött",    "jön",  "VERB", "past of jön"),
    ("lovak",   "ló",   "NOUN", "plural of ló"),
    ("kövek",   "kő",   "NOUN", "plural of kő"),
    ("tavak",   "tó",   "NOUN", "plural of tó"),
    ("szavak",  "szó",  "NOUN", "plural of szó"),
]


@pytest.mark.parametrize("surface,exp_root,exp_pos,label", IRREGULAR_CASES)
def test_irregular(surface, exp_root, exp_pos, label):
    result = engine.analyze(surface)
    assert result.root == exp_root, f"[{label}] root: got {result.root!r}"
    assert result.pos == exp_pos, f"[{label}] pos: got {result.pos!r}"


# ── Derivation smoke ────────────────────────────────────────────────────

DERIV_CASES = [
    ("szépség",  "szép",  "derivation szépség"),
    ("írható",   "ír",    "derivation írható"),
    ("megír",    "ír",    "prefix megír"),
    ("leír",     "ír",    "prefix leír"),
    ("beír",     "ír",    "prefix beír"),
]


@pytest.mark.parametrize("surface,exp_root,label", DERIV_CASES)
def test_derivation_smoke(surface, exp_root, label):
    result = engine.analyze(surface)
    assert result.root == exp_root, f"[{label}] root: got {result.root!r}"


# ── Sentence smoke ─────────────────────────────────────────────────────

def test_sentence_smoke():
    tokens, ok, msg = engine.analyze_sentence("a ház nagy volt")
    assert len(tokens) == 4
    assert ok is True


def test_engine_constructor():
    """Engine can be constructed with default config path."""
    eng = HungarianEngine()
    assert eng is not None
    assert len(eng.suffixes_by_slot) > 0


if __name__ == "__main__":
    passed = failed = 0
    for suite in [NOMINAL_CASES, VERBAL_CASES]:
        for t in suite:
            r = engine.analyze(t[0])
            ok = r.root == t[1] and r.pos == t[2]
            if ok:
                passed += 1
            else:
                failed += 1
                print(f"  FAIL  {t[0]:<15s}  {t[-1]}  ->  root={r.root!r} pos={r.pos}")
    for t in IRREGULAR_CASES:
        r = engine.analyze(t[0])
        ok = r.root == t[1] and r.pos == t[2]
        if ok:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL  {t[0]:<15s}  {t[-1]}  ->  root={r.root!r} pos={r.pos}")
    print(f"\n{passed} passed, {failed} failed")
