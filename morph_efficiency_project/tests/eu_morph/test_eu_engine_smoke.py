"""
Smoke tests for the Basque morphology engine.
Basic sanity checks: auxiliary lookup, noun cases, verb forms, closed-class.
"""
import pytest
from morph_efficiency_project.scripts.engines.eu_engine import BasqueEngine

@pytest.fixture(scope="module")
def engine():
    return BasqueEngine()


class TestAuxiliaryBasic:
    """Basic auxiliary lookup smoke tests."""

    def test_dut_is_aux(self, engine):
        t = engine.analyze("dut")
        assert t.pos == "AUX"

    def test_dut_agr_obj(self, engine):
        t = engine.analyze("dut")
        assert t.tags["agr_obj"] == "3SG"

    def test_dut_agr_subj(self, engine):
        t = engine.analyze("dut")
        assert t.tags["agr_subj"] == "1SG"

    def test_dut_tense(self, engine):
        t = engine.analyze("dut")
        assert t.tags["tense"] == "PRES"

    def test_naiz_intransitive(self, engine):
        t = engine.analyze("naiz")
        assert t.pos == "AUX"
        assert t.tags["agr_obj"] == "1SG"
        assert "agr_subj" not in t.tags

    def test_dio_ditransitive(self, engine):
        t = engine.analyze("dio")
        assert t.pos == "AUX"
        assert t.tags["agr_obj"] == "3SG"
        assert t.tags["agr_subj"] == "3SG"
        assert t.tags["agr_iobj"] == "3SG"

    def test_zait_nor_nori(self, engine):
        t = engine.analyze("zait")
        assert t.pos == "AUX"
        assert t.tags["agr_obj"] == "3SG"
        assert t.tags["agr_iobj"] == "1SG"
        assert "agr_subj" not in t.tags


class TestNounCaseBasic:
    """Basic noun case stripping smoke tests."""

    def test_etxea_abs_def_sg(self, engine):
        t = engine.analyze("etxea")
        assert t.tags.get("case") == "ABS"
        assert t.tags.get("def") == "DEF"
        assert t.root == "etxe"

    def test_etxean_ines(self, engine):
        t = engine.analyze("etxean")
        assert t.tags.get("case") == "INES"
        assert t.root == "etxe"

    def test_gizonari_dat(self, engine):
        t = engine.analyze("gizonari")
        assert t.tags.get("case") == "DAT"
        assert t.root == "gizon"

    def test_liburuak_ambig(self, engine):
        t = engine.analyze("liburuak")
        assert t.tags.get("case") in ("ABS", "ERG")

    def test_gizonek_erg_pl(self, engine):
        t = engine.analyze("gizonek")
        assert t.tags.get("case") == "ERG"
        assert t.tags.get("num") == "PL"


class TestVerbFormBasic:
    """Basic non-finite verb form smoke tests."""

    def test_ikusten_imperf(self, engine):
        t = engine.analyze("ikusten")
        assert t.pos == "VERB"
        assert t.tags["aspect"] == "IMPERF"
        assert t.root == "ikus"

    def test_ikasiko_prosp(self, engine):
        t = engine.analyze("ikasiko")
        assert t.tags.get("aspect") == "PROSP"

    def test_garbitu_perf(self, engine):
        t = engine.analyze("garbitu")
        assert t.tags.get("aspect") == "PERF"


class TestClosedClass:
    """Closed-class intercept smoke tests."""

    def test_eta_conj(self, engine):
        t = engine.analyze("eta")
        assert t.pos == "CONJ"

    def test_ez_particle(self, engine):
        t = engine.analyze("ez")
        assert t.pos == "PART"
        assert t.tags.get("sem") == "NEG"

    def test_ni_pronoun(self, engine):
        t = engine.analyze("ni")
        assert t.pos == "PRON"
        assert t.tags.get("person") == "1"

    def test_hemen_adv(self, engine):
        t = engine.analyze("hemen")
        assert t.pos == "ADV"

    def test_bat_det(self, engine):
        t = engine.analyze("bat")
        assert t.pos == "DET"


class TestSyntheticVerbs:
    """Synthetic verb form smoke tests."""

    def test_dator_etorri(self, engine):
        t = engine.analyze("dator")
        assert t.pos == "VERB"
        assert t.root == "etorri"
        assert t.tags["agr_obj"] == "3SG"

    def test_dago_egon(self, engine):
        t = engine.analyze("dago")
        assert t.pos == "VERB"
        assert t.root == "egon"

    def test_doa_joan(self, engine):
        t = engine.analyze("doa")
        assert t.pos == "VERB"
        assert t.root == "joan"
