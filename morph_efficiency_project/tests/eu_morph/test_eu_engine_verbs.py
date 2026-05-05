"""
Non-finite verb form tests for the Basque engine.
Tests participle, imperfective, and prospective forms.
"""
import pytest
from morph_efficiency_project.scripts.engines.eu_engine import BasqueEngine

@pytest.fixture(scope="module")
def engine():
    return BasqueEngine()


class TestImperfective:
    """Imperfective forms (-tzen/-ten)."""

    def test_ikusten(self, engine):
        t = engine.analyze("ikusten")
        assert t.pos == "VERB"
        assert t.tags["aspect"] == "IMPERF"
        assert t.root == "ikus"

    def test_egiten(self, engine):
        t = engine.analyze("egiten")
        assert t.tags["aspect"] == "IMPERF"
        assert t.root == "egi"

    def test_irakurtzen(self, engine):
        t = engine.analyze("irakurtzen")
        assert t.tags["aspect"] == "IMPERF"
        assert t.root == "irakur"

    def test_jaten(self, engine):
        t = engine.analyze("jaten")
        assert t.tags["aspect"] == "IMPERF"
        assert t.root == "ja"

    def test_etortzen(self, engine):
        t = engine.analyze("etortzen")
        assert t.tags["aspect"] == "IMPERF"
        assert t.root == "etor"

    def test_idazten(self, engine):
        t = engine.analyze("idazten")
        assert t.tags["aspect"] == "IMPERF"
        assert t.root == "idaz"

    def test_jolasten(self, engine):
        t = engine.analyze("jolasten")
        assert t.tags["aspect"] == "IMPERF"
        assert t.root == "jolas"

    def test_saltzen(self, engine):
        t = engine.analyze("saltzen")
        assert t.tags["aspect"] == "IMPERF"
        assert t.root == "sal"

    def test_erosten(self, engine):
        t = engine.analyze("erosten")
        assert t.tags["aspect"] == "IMPERF"
        assert t.root == "eros"


class TestProspective:
    """Prospective forms (-ko/-go)."""

    def test_ikusiko(self, engine):
        t = engine.analyze("ikusiko")
        assert t.tags.get("aspect") == "PROSP"

    def test_egingo(self, engine):
        t = engine.analyze("egingo")
        assert t.tags.get("aspect") == "PROSP"

    def test_irakurriko(self, engine):
        t = engine.analyze("irakurriko")
        assert t.tags.get("aspect") == "PROSP"

    def test_joango(self, engine):
        t = engine.analyze("joango")
        assert t.tags.get("aspect") == "PROSP"

    def test_etorriko(self, engine):
        t = engine.analyze("etorriko")
        assert t.tags.get("aspect") == "PROSP"

    def test_emango(self, engine):
        t = engine.analyze("emango")
        assert t.tags.get("aspect") == "PROSP"


class TestPerfectiveParticiple:
    """Perfective participle forms (-tu/-du)."""

    def test_garbitu(self, engine):
        t = engine.analyze("garbitu")
        assert t.tags.get("aspect") == "PERF"
        assert t.root == "garbi"

    def test_saldu(self, engine):
        t = engine.analyze("saldu")
        assert t.tags.get("aspect") == "PERF"
        assert t.root == "sal"

    def test_lortu(self, engine):
        t = engine.analyze("lortu")
        assert t.tags.get("aspect") == "PERF"
        assert t.root == "lor"

    def test_hartu(self, engine):
        t = engine.analyze("hartu")
        assert t.tags.get("aspect") == "PERF"
        assert t.root == "har"

    def test_sortu(self, engine):
        t = engine.analyze("sortu")
        assert t.tags.get("aspect") == "PERF"
        assert t.root == "sor"

    def test_bildu(self, engine):
        t = engine.analyze("bildu")
        assert t.tags.get("aspect") == "PERF"
        assert t.root == "bil"


class TestSyntheticVerbForms:
    """Synthetic verb forms (from aux lookup)."""

    def test_dator_present(self, engine):
        t = engine.analyze("dator")
        assert t.pos == "VERB"
        assert t.tags["tense"] == "PRES"
        assert t.tags["agr_obj"] == "3SG"

    def test_zetorren_past(self, engine):
        t = engine.analyze("zetorren")
        assert t.pos == "VERB"
        assert t.tags["tense"] == "PAST"

    def test_dago_egon(self, engine):
        t = engine.analyze("dago")
        assert t.pos == "VERB"
        assert t.root == "egon"

    def test_daude_egon_pl(self, engine):
        t = engine.analyze("daude")
        assert t.pos == "VERB"
        assert t.tags["agr_obj"] == "3PL"

    def test_doa_joan(self, engine):
        t = engine.analyze("doa")
        assert t.pos == "VERB"
        assert t.root == "joan"

    def test_nator_1sg(self, engine):
        t = engine.analyze("nator")
        assert t.tags["agr_obj"] == "1SG"

    def test_daki_jakin(self, engine):
        t = engine.analyze("daki")
        assert t.pos == "VERB"
        assert t.root == "jakin"

    def test_dakit_jakin_1sg(self, engine):
        t = engine.analyze("dakit")
        assert t.tags["agr_obj"] == "3SG"
        assert t.tags["agr_subj"] == "1SG"

    def test_dabil_ibili(self, engine):
        t = engine.analyze("dabil")
        assert t.pos == "VERB"
        assert t.root == "ibili"
