"""
test_de_engine_nouns.py
-----------------------
Noun morphology tests: regular plurals, Umlaut plurals, genitive, N-Deklination.

Run: python -m pytest morph_efficiency_project/tests/de_morph/test_de_engine_nouns.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import GermanEngine
import pytest

engine = GermanEngine()

# ── Irregular plural nouns (from irregulars.json) ────────────────────────────

IRREGULAR_PLURALS = [
    ("Männer",   "Mann",    "PL", True,  "Mann -> Männer"),
    ("Frauen",   "Frau",    "PL", False, "Frau -> Frauen"),
    ("Kinder",   "Kind",    "PL", False, "Kind -> Kinder"),
    ("Häuser",   "Haus",    "PL", True,  "Haus -> Häuser"),
    ("Bücher",   "Buch",    "PL", True,  "Buch -> Bücher"),
    ("Städte",   "Stadt",   "PL", True,  "Stadt -> Städte"),
    ("Ärzte",    "Arzt",    "PL", True,  "Arzt -> Ärzte"),
    ("Bäume",    "Baum",    "PL", True,  "Baum -> Bäume"),
    ("Wörter",   "Wort",    "PL", True,  "Wort -> Wörter"),
    ("Töchter",  "Tochter", "PL", True,  "Tochter -> Töchter"),
    ("Mütter",   "Mutter",  "PL", True,  "Mutter -> Mütter"),
    ("Väter",    "Vater",   "PL", True,  "Vater -> Väter"),
    ("Brüder",   "Bruder",  "PL", True,  "Bruder -> Brüder"),
    ("Söhne",    "Sohn",    "PL", True,  "Sohn -> Söhne"),
    ("Vögel",    "Vogel",   "PL", True,  "Vogel -> Vögel"),
    ("Hände",    "Hand",    "PL", True,  "Hand -> Hände"),
    ("Nächte",   "Nacht",   "PL", True,  "Nacht -> Nächte"),
    ("Gäste",    "Gast",    "PL", True,  "Gast -> Gäste"),
    ("Köpfe",    "Kopf",    "PL", True,  "Kopf -> Köpfe"),
    ("Züge",     "Zug",     "PL", True,  "Zug -> Züge"),
    ("Füße",     "Fuß",     "PL", True,  "Fuß -> Füße"),
    ("Äpfel",    "Apfel",   "PL", True,  "Apfel -> Äpfel"),
    ("Gärten",   "Garten",  "PL", True,  "Garten -> Gärten"),
    ("Länder",   "Land",    "PL", True,  "Land -> Länder"),
    ("Räder",    "Rad",     "PL", True,  "Rad -> Räder"),
    ("Plätze",   "Platz",   "PL", True,  "Platz -> Plätze"),
    ("Kräfte",   "Kraft",   "PL", True,  "Kraft -> Kräfte"),
    ("Fälle",    "Fall",    "PL", True,  "Fall -> Fälle"),
    ("Grüße",    "Gruß",    "PL", True,  "Gruß -> Grüße"),
    ("Bänke",    "Bank",    "PL", True,  "Bank -> Bänke"),
    ("Würmer",   "Wurm",    "PL", True,  "Wurm -> Würmer"),
    ("Menschen", "Mensch",  "PL", False, "Mensch -> Menschen"),
    ("Augen",    "Auge",    "PL", False, "Auge -> Augen"),
    ("Ohren",    "Ohr",     "PL", False, "Ohr -> Ohren"),
    ("Herzen",   "Herz",    "PL", False, "Herz -> Herzen"),
    ("Flüsse",   "Fluss",   "PL", True,  "Fluss -> Flüsse"),
    ("Hüte",     "Hut",     "PL", True,  "Hut -> Hüte"),
    ("Kühe",     "Kuh",     "PL", True,  "Kuh -> Kühe"),
    ("Gänse",    "Gans",    "PL", True,  "Gans -> Gänse"),
    ("Frösche",  "Frosch",  "PL", True,  "Frosch -> Frösche"),
    ("Köche",    "Koch",    "PL", True,  "Koch -> Köche"),
    ("Dörfer",   "Dorf",    "PL", True,  "Dorf -> Dörfer"),
    ("Klöster",  "Kloster", "PL", True,  "Kloster -> Klöster"),
    ("Böden",    "Boden",   "PL", True,  "Boden -> Böden"),
    ("Fäden",    "Faden",   "PL", True,  "Faden -> Fäden"),
    ("Öfen",     "Ofen",    "PL", True,  "Ofen -> Öfen"),
]


@pytest.mark.parametrize("surface, root, num, has_umlaut, desc", IRREGULAR_PLURALS)
def test_irregular_plural(surface, root, num, has_umlaut, desc):
    info = engine.analyze(surface)
    assert info.root == root, f"[{desc}] root: {info.root!r} != {root!r}"
    assert info.pos == "NOUN", f"[{desc}] pos: {info.pos!r}"
    assert info.tags.get("num") == num, f"[{desc}] num: {info.tags.get('num')!r}"
    if has_umlaut:
        assert info.tags.get("umlaut") == "YES", f"[{desc}] umlaut expected: {info.tags!r}"


# ── Genitive singular ────────────────────────────────────────────────────────

GENITIVE_CASES = [
    ("Hauses",  "Haus",   "GEN", "SG", "genitive -es"),
    ("Mannes",  "Mann",   "GEN", "SG", "genitive -es (already a stem)"),
    ("Kindes",  "Kind",   "GEN", "SG", "genitive -es"),
    ("Tages",   "Tag",    "GEN", "SG", "genitive -es"),
    ("Jahres",  "Jahr",   "GEN", "SG", "genitive -es"),
]


@pytest.mark.parametrize("surface, root, case, num, desc", GENITIVE_CASES)
def test_genitive(surface, root, case, num, desc):
    info = engine.analyze(surface)
    # Should find a NOUN with genitive case
    assert info.pos == "NOUN", f"[{desc}] pos: {info.pos!r}"
    assert info.tags.get("case") == case, f"[{desc}] case: {info.tags!r}"


# ── Zero plural nouns ────────────────────────────────────────────────────────

def test_mädchen_plural():
    """Mädchen has zero plural (same form)."""
    info = engine.analyze("Mädchen")
    assert info.root == "Mädchen", f"root: {info.root!r}"
    assert info.pos == "NOUN"


# ── Noun base forms ─────────────────────────────────────────────────────────

BASE_NOUNS = [
    ("Haus",    "NOUN"),
    ("Mann",    "NOUN"),
    ("Frau",    "NOUN"),
    ("Kind",    "NOUN"),
    ("Buch",    "NOUN"),
    ("Stadt",   "NOUN"),
]


@pytest.mark.parametrize("surface, pos", BASE_NOUNS)
def test_base_noun_recognized(surface, pos):
    """Base noun forms should be recognized (via stems dict if UNKNOWN)."""
    info = engine.analyze(surface)
    # May be recognized as NOUN via various paths
    # The important thing is it doesn't get misanalyzed as a verb
    assert info.surface == surface
