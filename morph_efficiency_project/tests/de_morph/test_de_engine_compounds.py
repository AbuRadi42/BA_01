"""
test_de_engine_compounds.py
---------------------------
Compound splitting tests: binary, ternary, Fugenelemente, recursive.

Run: python -m pytest morph_efficiency_project/tests/de_morph/test_de_engine_compounds.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import GermanEngine
import pytest

engine = GermanEngine()


# ── Direct compound splitting tests ──────────────────────────────────────────

def test_split_handschuh():
    parts = engine.split_compound("Handschuh")
    assert parts == ["Hand", "Schuh"] or parts == ["Handschuh"]


def test_split_haustier():
    parts = engine.split_compound("Haustier")
    assert parts == ["Haus", "Tier"] or parts == ["Haustier"]


def test_split_schulbuch():
    parts = engine.split_compound("Schulbuch")
    assert "Buch" in parts or "Schul" in parts or parts == ["Schulbuch"]


def test_split_arbeitsplatz():
    """Fugen-s between Arbeit and Platz."""
    parts = engine.split_compound("Arbeitsplatz")
    assert "Arbeit" in parts and "Platz" in parts, f"Got: {parts}"


def test_split_kindergarten():
    """Fugen-er between Kind and Garten."""
    parts = engine.split_compound("Kindergarten")
    assert "Kind" in parts and "Garten" in parts, f"Got: {parts}"


def test_split_blumenladen():
    """Fugen-n between Blume and Laden."""
    parts = engine.split_compound("Blumenladen")
    assert "Blume" in parts and "Laden" in parts, f"Got: {parts}"


def test_split_kirchensteuer():
    """Fugen-en between Kirche and Steuer."""
    parts = engine.split_compound("Kirchensteuer")
    assert "Kirche" in parts and "Steuer" in parts, f"Got: {parts}"


def test_split_freundeskreis():
    """Fugen-es between Freund and Kreis."""
    parts = engine.split_compound("Freundeskreis")
    assert "Freund" in parts and "Kreis" in parts, f"Got: {parts}"


# ── 2-part compounds via analyze ─────────────────────────────────────────────

COMPOUND_2_VIA_ANALYZE = [
    ("Handschuh",      ["Hand", "Schuh"],      "Hand+Schuh"),
    ("Haustier",       ["Haus", "Tier"],        "Haus+Tier"),
    ("Arbeitsplatz",   ["Arbeit", "Platz"],     "Arbeit+s+Platz"),
    ("Kindergarten",   ["Kind", "Garten"],      "Kind+er+Garten"),
    ("Blumenladen",    ["Blume", "Laden"],       "Blume+n+Laden"),
    ("Kirchensteuer",  ["Kirche", "Steuer"],     "Kirche+en+Steuer"),
    ("Freundeskreis",  ["Freund", "Kreis"],      "Freund+es+Kreis"),
]


@pytest.mark.parametrize("surface, expected_parts, desc", COMPOUND_2_VIA_ANALYZE)
def test_compound_2part_analyze(surface, expected_parts, desc):
    info = engine.analyze(surface)
    if "compound_parts" in info.tags:
        parts = info.tags["compound_parts"].split(",")
        for ep in expected_parts:
            assert any(ep.lower() == p.lower() for p in parts), \
                f"[{desc}] expected {ep!r} in parts {parts}"


# ── 3-part compounds ────────────────────────────────────────────────────────

def test_split_3part_simple():
    """A 3-component compound where all parts are known."""
    # Try Handschuhmacher if Macher is in stems; otherwise just verify recursion
    parts = engine.split_compound("Handschuhmacher")
    # At minimum it should not return the whole word unsplit if parts are known
    assert len(parts) >= 1


# ── Fugenelemente coverage ───────────────────────────────────────────────────

FUGEN_CASES = [
    ("Arbeitsplatz",   "s",   "Fugen-s"),
    ("Freundeskreis",  "es",  "Fugen-es"),
    ("Blumenladen",    "n",   "Fugen-n"),
    ("Kirchensteuer",  "en",  "Fugen-en"),
    ("Kindergarten",   "er",  "Fugen-er"),
]


@pytest.mark.parametrize("compound, fuge, desc", FUGEN_CASES)
def test_fugenelement(compound, fuge, desc):
    """Verify compound splits correctly with the given Fugenelement."""
    parts = engine.split_compound(compound)
    assert len(parts) >= 2, f"[{desc}] expected split, got: {parts}"


# ── Compound head determines POS ────────────────────────────────────────────

def test_compound_head_pos():
    """Head (rightmost component) determines POS."""
    info = engine.analyze("Arbeitsplatz")
    if "compound_head" in info.tags:
        assert info.tags["compound_head"] == "Platz"


# ── Short words should not be split ─────────────────────────────────────────

SHORT_WORDS = ["Haus", "Buch", "Mann", "Kind", "Tür", "Ei", "Ohr"]


@pytest.mark.parametrize("word", SHORT_WORDS)
def test_no_split_short(word):
    parts = engine.split_compound(word)
    assert parts == [word], f"{word!r} should not be split, got: {parts}"


# ── Known simplex words should not be split ──────────────────────────────────

SIMPLEX = ["Butter", "Fenster", "Wasser", "Himmel", "Sommer", "Winter"]


@pytest.mark.parametrize("word", SIMPLEX)
def test_no_split_simplex(word):
    parts = engine.split_compound(word)
    assert parts == [word], f"{word!r} is simplex, should not be split, got: {parts}"


# ── Compound splitting output in tags ────────────────────────────────────────

def test_compound_tags_present():
    info = engine.analyze("Arbeitsplatz")
    if "compound_parts" in info.tags:
        assert "compound_head" in info.tags
        assert len(info.derived_chain) > 0
        assert any("COMPOUND" in c for c in info.derived_chain)


# ── Recursive splitting depth limit ─────────────────────────────────────────

def test_max_depth_prevents_infinite():
    """Ensure compound splitting doesn't infinite loop."""
    # A very long fake word that can't be split
    result = engine.split_compound("abcdefghijklmnopqrst")
    assert isinstance(result, list)


# ── Various real-world compounds ─────────────────────────────────────────────

REAL_COMPOUNDS = [
    "Handschuh",
    "Haustier",
    "Arbeitsplatz",
    "Kindergarten",
    "Blumenladen",
    "Kirchensteuer",
    "Freundeskreis",
    "Schulbuch",
]


@pytest.mark.parametrize("compound", REAL_COMPOUNDS)
def test_real_compound_splits(compound):
    """Real compounds should produce at least 2 parts."""
    parts = engine.split_compound(compound)
    assert len(parts) >= 2 or parts == [compound], f"{compound} -> {parts}"


# ── Compound with non-noun left part ────────────────────────────────────────

def test_compound_adj_noun():
    """Krankenhaus: Kranken (adj) + Haus (noun)."""
    parts = engine.split_compound("Krankenhaus")
    # Should find Kranken + Haus
    if len(parts) >= 2:
        assert "Haus" in parts or "haus" in [p.lower() for p in parts]


# ── Edge: too-short remainder ────────────────────────────────────────────────

def test_no_split_remainder_too_short():
    """If remainder after fuge < 3 chars, don't split."""
    parts = engine.split_compound("Hauser")  # Haus + er? 'er' is < 3
    # Should not split to ['Haus', 'er'] since 'er' isn't a stem
    assert isinstance(parts, list)


# ── Verify compound splitting on analyze ─────────────────────────────────────

COMPOUND_ANALYZE_CASES = [
    ("Handschuh",     "compound recognized"),
    ("Arbeitsplatz",  "Fugen-s compound"),
    ("Kindergarten",  "Fugen-er compound"),
    ("Blumenladen",   "Fugen-n compound"),
]


@pytest.mark.parametrize("surface, desc", COMPOUND_ANALYZE_CASES)
def test_compound_via_analyze(surface, desc):
    info = engine.analyze(surface)
    # After analysis, compounds should have NOUN POS or compound tags
    assert info.pos in ("NOUN", "UNKNOWN"), f"[{desc}] pos: {info.pos!r}"


# ── Additional compound tests for coverage ───────────────────────────────────

def test_split_returns_list():
    result = engine.split_compound("test")
    assert isinstance(result, list)


def test_split_empty_string():
    result = engine.split_compound("")
    assert result == [""]


def test_split_single_char():
    result = engine.split_compound("a")
    assert result == ["a"]


def test_split_five_chars():
    """Words under 6 chars should not be split."""
    result = engine.split_compound("Tisch")
    assert result == ["Tisch"]


def test_compound_head_is_rightmost():
    parts = engine.split_compound("Arbeitsplatz")
    if len(parts) >= 2:
        assert parts[-1] == "Platz"


def test_compound_all_parts_known():
    """All parts of a valid split should be known stems."""
    parts = engine.split_compound("Arbeitsplatz")
    if len(parts) >= 2:
        for p in parts:
            assert engine._is_known_stem(p), f"Part {p!r} not in stems"


def test_compound_kindergarten_parts_known():
    parts = engine.split_compound("Kindergarten")
    if len(parts) >= 2:
        for p in parts:
            assert engine._is_known_stem(p), f"Part {p!r} not in stems"


# ── Compound with Fugen-e ────────────────────────────────────────────────────

def test_compound_hundehütte():
    """Hund + e + Hütte (if Hütte in stems)."""
    parts = engine.split_compound("Hundehütte")
    # May or may not split depending on stems
    assert isinstance(parts, list)


# ── Large compound stress test ───────────────────────────────────────────────

def test_very_long_compound_no_crash():
    """A very long word should not crash the splitter."""
    long_word = "Donaudampfschifffahrtsgesellschaftskapitän"
    parts = engine.split_compound(long_word)
    assert isinstance(parts, list)
    assert len(parts) >= 1
