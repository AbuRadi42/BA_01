"""
test_de_engine_adjectives.py
----------------------------
Adjective morphology tests: declension endings, comparatives, superlatives,
Umlaut in comparatives.

Run: python -m pytest morph_efficiency_project/tests/de_morph/test_de_engine_adjectives.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import GermanEngine
import pytest

engine = GermanEngine()


# -- Suppletive / irregular comparatives (from irregulars.json) ---------------

IRREGULAR_COMP = [
    ("besser",   "gut",   "COMP",  "gut comparative"),
    ("beste",    "gut",   "SUPER", "gut superlative"),
    ("besten",   "gut",   "SUPER", "gut superlative inflected"),
    ("bestes",   "gut",   "SUPER", "gut superlative neuter"),
    ("bestem",   "gut",   "SUPER", "gut superlative dative"),
    ("mehr",     "viel",  "COMP",  "viel comparative"),
    ("meiste",   "viel",  "SUPER", "viel superlative"),
    ("meisten",  "viel",  "SUPER", "viel superlative inflected"),
    ("weniger",  "wenig", "COMP",  "wenig comparative"),
    ("wenigste", "wenig", "SUPER", "wenig superlative"),
    ("höher",    "hoch",  "COMP",  "hoch comparative"),
    ("höchste",  "hoch",  "SUPER", "hoch superlative"),
    ("höchsten", "hoch",  "SUPER", "hoch superlative inflected"),
    ("näher",    "nah",   "COMP",  "nah comparative"),
    ("nächste",  "nah",   "SUPER", "nah superlative"),
    ("nächsten", "nah",   "SUPER", "nah superlative inflected"),
    ("größer",   "groß",  "COMP",  "groß comparative"),
    ("größte",   "groß",  "SUPER", "groß superlative"),
    ("größten",  "groß",  "SUPER", "groß superlative inflected"),
    ("lieber",   "gern",  "COMP",  "gern comparative"),
    ("liebsten", "gern",  "SUPER", "gern superlative"),
]


@pytest.mark.parametrize("surface, root, degree, desc", IRREGULAR_COMP)
def test_irregular_comparative(surface, root, degree, desc):
    info = engine.analyze(surface)
    assert info.root == root, f"[{desc}] root: {info.root!r} != {root!r}"
    assert info.tags.get("degree") == degree, \
        f"[{desc}] degree: {info.tags.get('degree')!r} != {degree!r}"


# -- Adjective declension endings (strong/weak/mixed) -------------------------

ADJ_DECLENSION = [
    ("guter",   "gut", "ADJ", "strong MASC.NOM"),
    ("gute",    "gut", "ADJ", "strong FEM.NOM"),
    ("gutes",   "gut", "ADJ", "strong NEUT.NOM"),
    ("gutem",   "gut", "ADJ", "strong DAT"),
    ("guten",   "gut", "ADJ", "strong ACC"),
    ("kleine",  "klein", "ADJ", "weak/strong FEM/NEUT.NOM"),
    ("kleiner", "klein", "ADJ", "strong MASC.NOM"),
    ("kleines", "klein", "ADJ", "strong NEUT.NOM"),
    ("kleinem", "klein", "ADJ", "strong DAT"),
    ("kleinen", "klein", "ADJ", "strong ACC/weak"),
]


@pytest.mark.parametrize("surface, root, pos, desc", ADJ_DECLENSION)
def test_adjective_declension(surface, root, pos, desc):
    info = engine.analyze(surface)
    assert info.root == root, f"[{desc}] root: {info.root!r} != {root!r}"
    assert info.pos == pos, f"[{desc}] pos: {info.pos!r}"


# -- Validator: degree tag only on ADJ/ADV ------------------------------------

def test_validator_degree_on_adj():
    """check_morph_sequence_de should accept degree on ADJ."""
    from morph_efficiency_project.scripts.engines import check_morph_sequence_de, TokenInfo
    t = TokenInfo(surface="besser", clitics={}, template="", root="gut",
                  tags={"degree": "COMP"}, pos="ADJ")
    assert check_morph_sequence_de([t])


def test_validator_degree_on_adv():
    """check_morph_sequence_de should accept degree on ADV."""
    from morph_efficiency_project.scripts.engines import check_morph_sequence_de, TokenInfo
    t = TokenInfo(surface="lieber", clitics={}, template="", root="gern",
                  tags={"degree": "COMP"}, pos="ADV")
    assert check_morph_sequence_de([t])
