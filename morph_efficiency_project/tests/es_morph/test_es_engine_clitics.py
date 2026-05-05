"""
test_es_engine_clitics.py
-------------------------
Tests for enclitic pronoun stripping.

Run: python -m pytest morph_efficiency_project/tests/es_morph/test_es_engine_clitics.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import SpanishEngine
import pytest

engine = SpanishEngine()


# ══════════════════════════════════════════════════════════════════════════════
# SINGLE CLITICS ON INFINITIVES
# ══════════════════════════════════════════════════════════════════════════════

class TestSingleCliticInfinitive:
    def test_hacerlo(self):
        r = engine.analyze("hacerlo")
        assert r.root == "hacer" and r.pos == "VERB"
        assert r.tags.get("clitic_obj") == "LO"
        assert r.tags.get("form") == "INF"

    def test_hacerla(self):
        r = engine.analyze("hacerla")
        assert r.root == "hacer" and r.tags.get("clitic_obj") == "LA"

    def test_decirle(self):
        r = engine.analyze("decirle")
        assert r.root == "decir" and r.tags.get("clitic_obj") == "LE"

    def test_verme(self):
        r = engine.analyze("verme")
        assert r.root == "ver" and r.tags.get("clitic_obj") == "ME"

    def test_comerse(self):
        r = engine.analyze("comerse")
        assert r.root == "comer" and r.tags.get("clitic_obj") == "SE"

    def test_hablarle(self):
        r = engine.analyze("hablarle")
        assert r.root == "hablar" and r.tags.get("clitic_obj") == "LE"

    def test_vivirlo(self):
        r = engine.analyze("vivirlo")
        assert r.root == "vivir" and r.tags.get("clitic_obj") == "LO"

    def test_darlo(self):
        r = engine.analyze("darlo")
        assert r.root == "dar" and r.tags.get("clitic_obj") == "LO"

    def test_hacernos(self):
        r = engine.analyze("hacernos")
        assert r.root == "hacer" and r.tags.get("clitic_obj") == "NOS"

    def test_decirte(self):
        r = engine.analyze("decirte")
        assert r.root == "decir" and r.tags.get("clitic_obj") == "TE"

    def test_verlos(self):
        r = engine.analyze("verlos")
        assert r.root == "ver" and r.tags.get("clitic_obj") == "LOS"

    def test_verlas(self):
        r = engine.analyze("verlas")
        assert r.root == "ver" and r.tags.get("clitic_obj") == "LAS"

    def test_darles(self):
        r = engine.analyze("darles")
        assert r.root == "dar" and r.tags.get("clitic_obj") == "LES"


# ══════════════════════════════════════════════════════════════════════════════
# SINGLE CLITICS ON GERUNDS
# ══════════════════════════════════════════════════════════════════════════════

class TestSingleCliticGerund:
    def test_viendome(self):
        r = engine.analyze("viendome")
        assert r.root == "ver" and r.tags.get("form") == "GER"
        assert r.tags.get("clitic_obj") == "ME"

    def test_haciendolo(self):
        r = engine.analyze("haciendolo")
        assert r.root == "hacer" and r.tags.get("form") == "GER"
        assert r.tags.get("clitic_obj") == "LO"

    def test_diciendole(self):
        r = engine.analyze("diciendole")
        assert r.root == "decir" and r.tags.get("form") == "GER"
        assert r.tags.get("clitic_obj") == "LE"

    def test_dandose(self):
        r = engine.analyze("dandose")
        assert r.root == "dar" and r.tags.get("form") == "GER"
        assert r.tags.get("clitic_obj") == "SE"

    def test_hablandoles(self):
        r = engine.analyze("hablandoles")
        assert r.root == "hablar" and r.tags.get("form") == "GER"
        assert r.tags.get("clitic_obj") == "LES"


# ══════════════════════════════════════════════════════════════════════════════
# DOUBLE CLITICS
# ══════════════════════════════════════════════════════════════════════════════

class TestDoubleClitics:
    def test_darselo(self):
        r = engine.analyze("darselo")
        assert r.root == "dar" and r.pos == "VERB"
        assert r.tags.get("clitic_obj") == "SE+LO"

    def test_diciendoselo(self):
        r = engine.analyze("diciendoselo")
        assert r.root == "decir" and r.pos == "VERB"
        assert r.tags.get("clitic_obj") == "SE+LO"
        assert r.tags.get("form") == "GER"

    def test_hacermelo(self):
        r = engine.analyze("hacermelo")
        assert r.root == "hacer" and r.tags.get("clitic_obj") == "ME+LO"

    def test_decirtelo(self):
        r = engine.analyze("decirtelo")
        assert r.root == "decir" and r.tags.get("clitic_obj") == "TE+LO"

    def test_darsela(self):
        r = engine.analyze("darsela")
        assert r.root == "dar" and r.tags.get("clitic_obj") == "SE+LA"

    def test_escribirselo(self):
        r = engine.analyze("escribirselo")
        assert r.root == "escribir" and r.tags.get("clitic_obj") == "SE+LO"

    def test_hablandoselo(self):
        r = engine.analyze("hablandoselo")
        assert r.root == "hablar" and r.tags.get("clitic_obj") == "SE+LO"


# ══════════════════════════════════════════════════════════════════════════════
# CLITIC FIELD STRUCTURE
# ══════════════════════════════════════════════════════════════════════════════

class TestCliticFieldStructure:
    def test_clitics_dict_has_enclitic_key(self):
        r = engine.analyze("hacerlo")
        assert "enclitic" in r.clitics
        assert r.clitics["enclitic"] == ["lo"]

    def test_double_clitics_list(self):
        r = engine.analyze("darselo")
        assert r.clitics["enclitic"] == ["se", "lo"]

    def test_no_clitics_on_plain_verb(self):
        r = engine.analyze("hablar")
        assert r.clitics == {}


# ══════════════════════════════════════════════════════════════════════════════
# FALSE CLITIC REJECTION
# ══════════════════════════════════════════════════════════════════════════════

class TestFalseCliticRejection:
    def test_rapidamente_no_clitic(self):
        """'rapidamente' should NOT be analyzed as verb + 'te' clitic."""
        r = engine.analyze("rapidamente")
        assert "clitic_obj" not in r.tags

    def test_problema_no_clitic(self):
        """'problema' should NOT be analyzed with 'la' stripped."""
        r = engine.analyze("problema")
        assert "clitic_obj" not in r.tags

    def test_sistema_no_clitic(self):
        """'sistema' should NOT be analyzed with 'ma' stripped."""
        r = engine.analyze("sistema")
        assert "clitic_obj" not in r.tags

    def test_grande_no_clitic(self):
        """'grande' should NOT have a clitic."""
        r = engine.analyze("grande")
        assert "clitic_obj" not in r.tags
