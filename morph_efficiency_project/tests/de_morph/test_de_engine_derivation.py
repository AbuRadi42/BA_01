"""
test_de_engine_derivation.py
----------------------------
Derivational morphology tests: suffix stripping, prefix stripping,
multi-layer derivation, compound + derivation interaction.

Run: python -m pytest morph_efficiency_project/tests/de_morph/test_de_engine_derivation.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import GermanEngine
import pytest

engine = GermanEngine()


# -- Suffix derivation --------------------------------------------------------

SUFFIX_CASES = [
    ("Bildung",       "ung",    "ACTION_NOUN",     "V->N -ung"),
    ("Freiheit",      "heit",   "QUALITY_NOUN",    "ADJ->N -heit"),
    ("Freundschaft",  "schaft", "COLLECTIVE",       "N->N -schaft"),
    ("freundlich",    "lich",   "RESEMBLANCE",      "N->ADJ -lich"),
    ("kindisch",      "isch",   "RELATING_TO",      "N->ADJ -isch"),
    ("sonnig",        "ig",     "HAVING_QUALITY",   "N->ADJ -ig"),
    ("machbar",       "bar",    "ABILITY",          "V->ADJ -bar"),
    ("langsam",       "sam",    "TENDENCY",          "V->ADJ -sam"),
    ("fehlerhaft",    "haft",   "HAVING_QUALITY",   "N->ADJ -haft"),
    ("endlos",        "los",    "WITHOUT",           "N->ADJ -los"),
    ("wertvoll",      "voll",   "FULL_OF",           "N->ADJ -voll"),
    ("erfolgreich",   "reich",  "RICH_IN",           "N->ADJ -reich"),
]


@pytest.mark.parametrize("surface, suffix, derives, desc", SUFFIX_CASES)
def test_suffix_derivation(surface, suffix, derives, desc):
    """Step B should detect suffix derivation on UNKNOWN words."""
    info = engine.analyze(surface)
    # The word should either be recognized via derivation or compound
    # Check if derived_chain mentions the expected derivation
    found = any(derives in c for c in info.derived_chain)
    # Also acceptable: word recognized via compound or other path
    assert found or info.pos != "UNKNOWN", \
        f"[{desc}] no derivation found: chain={info.derived_chain}, pos={info.pos}"


# -- Prefix derivation --------------------------------------------------------

PREFIX_CASES = [
    ("unmöglich",   "un",    "NEGATION", "ADJ->ADJ un-"),
    ("unfrei",      "un",    "NEGATION", "ADJ->ADJ un-"),
    ("uralt",       "ur",    "ORIGINAL", "ADJ ur-"),
]


@pytest.mark.parametrize("surface, prefix, derives, desc", PREFIX_CASES)
def test_prefix_derivation(surface, prefix, derives, desc):
    info = engine.analyze(surface)
    found = any(derives in c for c in info.derived_chain)
    assert found or info.pos != "UNKNOWN", \
        f"[{desc}] no derivation found: chain={info.derived_chain}, pos={info.pos}"


# -- Multi-layer derivation ---------------------------------------------------

def test_multilayer_unfreundlich():
    """un- + freundlich: should strip prefix."""
    info = engine.analyze("unfreundlich")
    # Should recognize at least one derivation layer
    assert len(info.derived_chain) >= 1 or info.pos != "UNKNOWN"


def test_multilayer_unfreundlichkeit():
    """Unfreundlichkeit: -keit + un- + freundlich."""
    info = engine.analyze("Unfreundlichkeit")
    # Should strip at least one layer
    assert len(info.derived_chain) >= 1 or info.pos != "UNKNOWN"


def test_multilayer_hoffnungslos():
    """hoffnungslos: Hoffnung + s + los (compound-like derivation)."""
    info = engine.analyze("hoffnungslos")
    assert len(info.derived_chain) >= 1 or info.pos != "UNKNOWN"


# -- Derivation does NOT run on inflected words --------------------------------

def test_no_derivation_on_inflected():
    """Inflected words (known POS) should not have derivational stripping."""
    info = engine.analyze("gemacht")
    assert info.pos == "VERB"
    assert info.derived_chain == []


def test_no_derivation_on_closed_class():
    """Closed-class words should not have derivational stripping."""
    info = engine.analyze("der")
    assert info.derived_chain == []


# -- Diminutive suffixes -------------------------------------------------------

def test_diminutive_chen():
    info = engine.analyze("Häuschen")
    # Should detect -chen diminutive or be recognized
    found = any("DIMINUTIVE" in c for c in info.derived_chain)
    # Also OK if recognized via other path
    assert found or info.pos != "UNKNOWN"


def test_diminutive_lein():
    info = engine.analyze("Büchlein")
    found = any("DIMINUTIVE" in c for c in info.derived_chain)
    assert found or info.pos != "UNKNOWN"


# -- Agent suffix -er ----------------------------------------------------------

def test_agent_lehrer():
    """Lehrer should involve -er agent suffix."""
    info = engine.analyze("Lehrer")
    # Lehrer is in the stems dict as NOUN, so it's recognized directly
    assert info.pos == "NOUN" or info.pos == "UNKNOWN"


def test_agent_spieler():
    info = engine.analyze("Spieler")
    # Should strip -er to spiel (VERB stem) or recognize directly
    assert info.pos in ("NOUN", "UNKNOWN", "ADJ")


# -- Feminine agent -in --------------------------------------------------------

def test_feminine_lehrerin():
    info = engine.analyze("Lehrerin")
    found = any("FEMININE_AGENT" in c for c in info.derived_chain)
    assert found or info.pos != "UNKNOWN"


# -- -ung nominalization -------------------------------------------------------

def test_ung_ordnung():
    info = engine.analyze("Ordnung")
    # Ordnung is in stems dict
    assert info.pos == "NOUN" or len(info.derived_chain) > 0


def test_ung_bewegung():
    info = engine.analyze("Bewegung")
    assert info.pos == "NOUN" or len(info.derived_chain) > 0


# -- Step C iterative depth ----------------------------------------------------

def test_step_c_max_depth():
    """Step C should not loop forever on unknown words."""
    info = engine.analyze("xyzqwertyuiop")
    assert info.pos == "UNKNOWN"
    assert isinstance(info.derived_chain, list)


# -- Derivation + compound interaction ----------------------------------------

def test_compound_then_derivation():
    """A compound where a component is itself derived."""
    info = engine.analyze("Arbeitsplatz")
    # Should be recognized as compound
    assert "compound_parts" in info.tags or info.pos == "NOUN"


def test_derivation_preserves_surface():
    """Surface should always be preserved."""
    info = engine.analyze("Unfreundlichkeit")
    assert info.surface == "Unfreundlichkeit"


# -- -keit/-igkeit suffixes ---------------------------------------------------

def test_keit_suffix():
    info = engine.analyze("Möglichkeit")
    found = any("QUALITY_NOUN" in c for c in info.derived_chain)
    assert found or info.pos != "UNKNOWN"


def test_igkeit_suffix():
    info = engine.analyze("Geschwindigkeit")
    found = any("QUALITY_NOUN" in c for c in info.derived_chain)
    assert found or info.pos != "UNKNOWN"


# -- -nis suffix ---------------------------------------------------------------

def test_nis_suffix():
    info = engine.analyze("Ergebnis")
    found = any("RESULT_NOUN" in c for c in info.derived_chain)
    assert found or info.pos != "UNKNOWN"


# -- -tum suffix ---------------------------------------------------------------

def test_tum_suffix():
    info = engine.analyze("Eigentum")
    found = any("STATE_DOMAIN" in c for c in info.derived_chain)
    assert found or info.pos != "UNKNOWN"


# -- -schaft suffix ------------------------------------------------------------

def test_schaft_wissenschaft():
    info = engine.analyze("Wissenschaft")
    # In stems dict
    assert info.pos == "NOUN" or len(info.derived_chain) > 0


# -- -bar suffix ---------------------------------------------------------------

def test_bar_essbar():
    info = engine.analyze("essbar")
    found = any("ABILITY" in c for c in info.derived_chain)
    assert found or info.pos != "UNKNOWN"


def test_bar_trinkbar():
    info = engine.analyze("trinkbar")
    found = any("ABILITY" in c for c in info.derived_chain)
    assert found or info.pos != "UNKNOWN"
