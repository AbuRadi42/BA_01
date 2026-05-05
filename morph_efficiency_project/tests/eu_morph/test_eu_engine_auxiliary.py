"""
CRITICAL auxiliary lookup tests for the Basque engine.
Tests all four paradigms: NOR, NOR-NORK, NOR-NORI, NOR-NORI-NORK.
Each test verifies the complete agreement decomposition.
"""
import pytest
from morph_efficiency_project.scripts.engines.eu_engine import BasqueEngine

@pytest.fixture(scope="module")
def engine():
    return BasqueEngine()


def _check_aux(engine, form, expected_pos, expected_tags):
    """Helper: analyze form and verify all expected tags."""
    t = engine.analyze(form)
    assert t.pos == expected_pos, f"{form}: expected pos={expected_pos}, got {t.pos}"
    for key, val in expected_tags.items():
        assert t.tags.get(key) == val, (
            f"{form}: expected {key}={val}, got {t.tags.get(key)}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# NOR paradigm (izan -- intransitive)
# ══════════════════════════════════════════════════════════════════════════════

class TestNORPresent:
    """NOR present tense -- all 7 persons."""

    def test_naiz(self, engine):
        _check_aux(engine, "naiz", "AUX", {"agr_obj": "1SG", "tense": "PRES"})

    def test_zara(self, engine):
        _check_aux(engine, "zara", "AUX", {"agr_obj": "2SG", "tense": "PRES", "formality": "FORMAL"})

    def test_haiz(self, engine):
        _check_aux(engine, "haiz", "AUX", {"agr_obj": "2SG", "tense": "PRES", "formality": "INFORMAL"})

    def test_da(self, engine):
        _check_aux(engine, "da", "AUX", {"agr_obj": "3SG", "tense": "PRES"})

    def test_gara(self, engine):
        _check_aux(engine, "gara", "AUX", {"agr_obj": "1PL", "tense": "PRES"})

    def test_zarete(self, engine):
        _check_aux(engine, "zarete", "AUX", {"agr_obj": "2PL", "tense": "PRES"})

    def test_dira(self, engine):
        _check_aux(engine, "dira", "AUX", {"agr_obj": "3PL", "tense": "PRES"})


class TestNORPast:
    """NOR past tense -- all 7 persons."""

    def test_nintzen(self, engine):
        _check_aux(engine, "nintzen", "AUX", {"agr_obj": "1SG", "tense": "PAST"})

    def test_zinen(self, engine):
        _check_aux(engine, "zinen", "AUX", {"agr_obj": "2SG", "tense": "PAST", "formality": "FORMAL"})

    def test_hintzen(self, engine):
        _check_aux(engine, "hintzen", "AUX", {"agr_obj": "2SG", "tense": "PAST", "formality": "INFORMAL"})

    def test_zen(self, engine):
        _check_aux(engine, "zen", "AUX", {"agr_obj": "3SG", "tense": "PAST"})

    def test_ginen(self, engine):
        _check_aux(engine, "ginen", "AUX", {"agr_obj": "1PL", "tense": "PAST"})

    def test_zineten(self, engine):
        _check_aux(engine, "zineten", "AUX", {"agr_obj": "2PL", "tense": "PAST"})

    def test_ziren(self, engine):
        _check_aux(engine, "ziren", "AUX", {"agr_obj": "3PL", "tense": "PAST"})


class TestNORPotential:
    """NOR potential/hypothetical mood."""

    def test_nintzateke(self, engine):
        _check_aux(engine, "nintzateke", "AUX", {"agr_obj": "1SG", "mood": "POT"})

    def test_litzateke(self, engine):
        _check_aux(engine, "litzateke", "AUX", {"agr_obj": "3SG", "mood": "POT"})

    def test_ginateke(self, engine):
        _check_aux(engine, "ginateke", "AUX", {"agr_obj": "1PL", "mood": "POT"})

    def test_lirateke(self, engine):
        _check_aux(engine, "lirateke", "AUX", {"agr_obj": "3PL", "mood": "POT"})


class TestNORImperative:
    """NOR imperative mood."""

    def test_zaitez(self, engine):
        _check_aux(engine, "zaitez", "AUX", {"agr_obj": "2SG", "mood": "IMP"})

    def test_hadi(self, engine):
        _check_aux(engine, "hadi", "AUX", {"agr_obj": "2SG", "mood": "IMP", "formality": "INFORMAL"})

    def test_zaitezte(self, engine):
        _check_aux(engine, "zaitezte", "AUX", {"agr_obj": "2PL", "mood": "IMP"})

    def test_bedi(self, engine):
        _check_aux(engine, "bedi", "AUX", {"agr_obj": "3SG", "mood": "IMP"})

    def test_bitez(self, engine):
        _check_aux(engine, "bitez", "AUX", {"agr_obj": "3PL", "mood": "IMP"})


# ══════════════════════════════════════════════════════════════════════════════
# NOR-NORK paradigm (ukan -- transitive)
# ══════════════════════════════════════════════════════════════════════════════

class TestNORNORKPresentAbs3SG:
    """NOR-NORK present, ABS=3SG (the most common column)."""

    def test_dut(self, engine):
        _check_aux(engine, "dut", "AUX", {"agr_obj": "3SG", "agr_subj": "1SG", "tense": "PRES"})

    def test_duzu(self, engine):
        _check_aux(engine, "duzu", "AUX", {"agr_obj": "3SG", "agr_subj": "2SG", "tense": "PRES"})

    def test_du(self, engine):
        _check_aux(engine, "du", "AUX", {"agr_obj": "3SG", "agr_subj": "3SG", "tense": "PRES"})

    def test_dugu(self, engine):
        _check_aux(engine, "dugu", "AUX", {"agr_obj": "3SG", "agr_subj": "1PL", "tense": "PRES"})

    def test_duzue(self, engine):
        _check_aux(engine, "duzue", "AUX", {"agr_obj": "3SG", "agr_subj": "2PL", "tense": "PRES"})

    def test_dute(self, engine):
        _check_aux(engine, "dute", "AUX", {"agr_obj": "3SG", "agr_subj": "3PL", "tense": "PRES"})


class TestNORNORKPresentAbs3PL:
    """NOR-NORK present, ABS=3PL."""

    def test_ditut(self, engine):
        _check_aux(engine, "ditut", "AUX", {"agr_obj": "3PL", "agr_subj": "1SG", "tense": "PRES"})

    def test_dituzu(self, engine):
        _check_aux(engine, "dituzu", "AUX", {"agr_obj": "3PL", "agr_subj": "2SG", "tense": "PRES"})

    def test_ditu(self, engine):
        _check_aux(engine, "ditu", "AUX", {"agr_obj": "3PL", "agr_subj": "3SG", "tense": "PRES"})

    def test_ditugu(self, engine):
        _check_aux(engine, "ditugu", "AUX", {"agr_obj": "3PL", "agr_subj": "1PL", "tense": "PRES"})

    def test_dituzue(self, engine):
        _check_aux(engine, "dituzue", "AUX", {"agr_obj": "3PL", "agr_subj": "2PL", "tense": "PRES"})

    def test_dituzte(self, engine):
        _check_aux(engine, "dituzte", "AUX", {"agr_obj": "3PL", "agr_subj": "3PL", "tense": "PRES"})


class TestNORNORKPresentAbs1SG:
    """NOR-NORK present, ABS=1SG (someone verbs me)."""

    def test_nau(self, engine):
        _check_aux(engine, "nau", "AUX", {"agr_obj": "1SG", "agr_subj": "3SG", "tense": "PRES"})

    def test_nauzu(self, engine):
        _check_aux(engine, "nauzu", "AUX", {"agr_obj": "1SG", "agr_subj": "2SG", "tense": "PRES"})

    def test_nauzue(self, engine):
        _check_aux(engine, "nauzue", "AUX", {"agr_obj": "1SG", "agr_subj": "2PL", "tense": "PRES"})

    def test_naute(self, engine):
        _check_aux(engine, "naute", "AUX", {"agr_obj": "1SG", "agr_subj": "3PL", "tense": "PRES"})


class TestNORNORKPresentAbs2SGAndPL:
    """NOR-NORK present, ABS=2SG and ABS=1PL."""

    def test_zaitut(self, engine):
        _check_aux(engine, "zaitut", "AUX", {"agr_obj": "2SG", "agr_subj": "1SG", "tense": "PRES"})

    def test_zaitu(self, engine):
        _check_aux(engine, "zaitu", "AUX", {"agr_obj": "2SG", "agr_subj": "3SG", "tense": "PRES"})

    def test_zaituzte(self, engine):
        _check_aux(engine, "zaituzte", "AUX", {"agr_obj": "2SG", "agr_subj": "3PL", "tense": "PRES"})

    def test_gaitu(self, engine):
        _check_aux(engine, "gaitu", "AUX", {"agr_obj": "1PL", "agr_subj": "3SG", "tense": "PRES"})

    def test_gaituzte(self, engine):
        _check_aux(engine, "gaituzte", "AUX", {"agr_obj": "1PL", "agr_subj": "3PL", "tense": "PRES"})

    def test_gaituzu(self, engine):
        _check_aux(engine, "gaituzu", "AUX", {"agr_obj": "1PL", "agr_subj": "2SG", "tense": "PRES"})


class TestNORNORKPastAbs3SG:
    """NOR-NORK past, ABS=3SG."""

    def test_nuen(self, engine):
        _check_aux(engine, "nuen", "AUX", {"agr_obj": "3SG", "agr_subj": "1SG", "tense": "PAST"})

    def test_zenuen(self, engine):
        _check_aux(engine, "zenuen", "AUX", {"agr_obj": "3SG", "agr_subj": "2SG", "tense": "PAST"})

    def test_zuen(self, engine):
        _check_aux(engine, "zuen", "AUX", {"agr_obj": "3SG", "agr_subj": "3SG", "tense": "PAST"})

    def test_genuen(self, engine):
        _check_aux(engine, "genuen", "AUX", {"agr_obj": "3SG", "agr_subj": "1PL", "tense": "PAST"})

    def test_zenuten(self, engine):
        _check_aux(engine, "zenuten", "AUX", {"agr_obj": "3SG", "agr_subj": "2PL", "tense": "PAST"})

    def test_zuten(self, engine):
        _check_aux(engine, "zuten", "AUX", {"agr_obj": "3SG", "agr_subj": "3PL", "tense": "PAST"})


class TestNORNORKPastAbs3PL:
    """NOR-NORK past, ABS=3PL."""

    def test_nituen(self, engine):
        _check_aux(engine, "nituen", "AUX", {"agr_obj": "3PL", "agr_subj": "1SG", "tense": "PAST"})

    def test_zenituen(self, engine):
        _check_aux(engine, "zenituen", "AUX", {"agr_obj": "3PL", "agr_subj": "2SG", "tense": "PAST"})

    def test_zituen(self, engine):
        _check_aux(engine, "zituen", "AUX", {"agr_obj": "3PL", "agr_subj": "3SG", "tense": "PAST"})

    def test_genituen(self, engine):
        _check_aux(engine, "genituen", "AUX", {"agr_obj": "3PL", "agr_subj": "1PL", "tense": "PAST"})

    def test_zenituzten(self, engine):
        _check_aux(engine, "zenituzten", "AUX", {"agr_obj": "3PL", "agr_subj": "2PL", "tense": "PAST"})

    def test_zituzten(self, engine):
        _check_aux(engine, "zituzten", "AUX", {"agr_obj": "3PL", "agr_subj": "3PL", "tense": "PAST"})


class TestNORNORKPastAbs1SG:
    """NOR-NORK past, ABS=1SG (someone verbed me)."""

    def test_ninduen(self, engine):
        _check_aux(engine, "ninduen", "AUX", {"agr_obj": "1SG", "agr_subj": "3SG", "tense": "PAST"})

    def test_ninduzun(self, engine):
        _check_aux(engine, "ninduzun", "AUX", {"agr_obj": "1SG", "agr_subj": "2SG", "tense": "PAST"})

    def test_ninduzuen(self, engine):
        _check_aux(engine, "ninduzuen", "AUX", {"agr_obj": "1SG", "agr_subj": "2PL", "tense": "PAST"})

    def test_ninduten(self, engine):
        _check_aux(engine, "ninduten", "AUX", {"agr_obj": "1SG", "agr_subj": "3PL", "tense": "PAST"})


class TestNORNORKPastAbs2SG:
    """NOR-NORK past, ABS=2SG."""

    def test_zintudan(self, engine):
        _check_aux(engine, "zintudan", "AUX", {"agr_obj": "2SG", "agr_subj": "1SG", "tense": "PAST"})

    def test_zintuen(self, engine):
        _check_aux(engine, "zintuen", "AUX", {"agr_obj": "2SG", "agr_subj": "3SG", "tense": "PAST"})

    def test_zintuzten(self, engine):
        _check_aux(engine, "zintuzten", "AUX", {"agr_obj": "2SG", "agr_subj": "3PL", "tense": "PAST"})


class TestNORNORKPotential:
    """NOR-NORK potential mood."""

    def test_luke(self, engine):
        _check_aux(engine, "luke", "AUX", {"agr_obj": "3SG", "agr_subj": "3SG", "mood": "POT"})

    def test_nuke(self, engine):
        _check_aux(engine, "nuke", "AUX", {"agr_obj": "3SG", "agr_subj": "1SG", "mood": "POT"})

    def test_genuke(self, engine):
        _check_aux(engine, "genuke", "AUX", {"agr_obj": "3SG", "agr_subj": "1PL", "mood": "POT"})

    def test_lukete(self, engine):
        _check_aux(engine, "lukete", "AUX", {"agr_obj": "3SG", "agr_subj": "3PL", "mood": "POT"})


class TestNORNORKImperative:
    """NOR-NORK imperative mood."""

    def test_ezazu(self, engine):
        _check_aux(engine, "ezazu", "AUX", {"agr_obj": "3SG", "agr_subj": "2SG", "mood": "IMP"})

    def test_ezazue(self, engine):
        _check_aux(engine, "ezazue", "AUX", {"agr_obj": "3SG", "agr_subj": "2PL", "mood": "IMP"})


# ══════════════════════════════════════════════════════════════════════════════
# NOR-NORI paradigm (izan + dative)
# ══════════════════════════════════════════════════════════════════════════════

class TestNORNORIPresentAbs3SG:
    """NOR-NORI present, ABS=3SG."""

    def test_zait(self, engine):
        _check_aux(engine, "zait", "AUX", {"agr_obj": "3SG", "agr_iobj": "1SG", "tense": "PRES"})

    def test_zaizu(self, engine):
        _check_aux(engine, "zaizu", "AUX", {"agr_obj": "3SG", "agr_iobj": "2SG", "tense": "PRES"})

    def test_zaio(self, engine):
        _check_aux(engine, "zaio", "AUX", {"agr_obj": "3SG", "agr_iobj": "3SG", "tense": "PRES"})

    def test_zaigu(self, engine):
        _check_aux(engine, "zaigu", "AUX", {"agr_obj": "3SG", "agr_iobj": "1PL", "tense": "PRES"})

    def test_zaizue(self, engine):
        _check_aux(engine, "zaizue", "AUX", {"agr_obj": "3SG", "agr_iobj": "2PL", "tense": "PRES"})

    def test_zaie(self, engine):
        _check_aux(engine, "zaie", "AUX", {"agr_obj": "3SG", "agr_iobj": "3PL", "tense": "PRES"})


class TestNORNORIPresentAbs3PL:
    """NOR-NORI present, ABS=3PL."""

    def test_zaizkit(self, engine):
        _check_aux(engine, "zaizkit", "AUX", {"agr_obj": "3PL", "agr_iobj": "1SG", "tense": "PRES"})

    def test_zaizkizu(self, engine):
        _check_aux(engine, "zaizkizu", "AUX", {"agr_obj": "3PL", "agr_iobj": "2SG", "tense": "PRES"})

    def test_zaizkio(self, engine):
        _check_aux(engine, "zaizkio", "AUX", {"agr_obj": "3PL", "agr_iobj": "3SG", "tense": "PRES"})

    def test_zaizkigu(self, engine):
        _check_aux(engine, "zaizkigu", "AUX", {"agr_obj": "3PL", "agr_iobj": "1PL", "tense": "PRES"})

    def test_zaizkizue(self, engine):
        _check_aux(engine, "zaizkizue", "AUX", {"agr_obj": "3PL", "agr_iobj": "2PL", "tense": "PRES"})

    def test_zaizkie(self, engine):
        _check_aux(engine, "zaizkie", "AUX", {"agr_obj": "3PL", "agr_iobj": "3PL", "tense": "PRES"})


class TestNORNORIPast:
    """NOR-NORI past tense."""

    def test_zitzaidan(self, engine):
        _check_aux(engine, "zitzaidan", "AUX", {"agr_obj": "3SG", "agr_iobj": "1SG", "tense": "PAST"})

    def test_zitzaizun(self, engine):
        _check_aux(engine, "zitzaizun", "AUX", {"agr_obj": "3SG", "agr_iobj": "2SG", "tense": "PAST"})

    def test_zitzaion(self, engine):
        _check_aux(engine, "zitzaion", "AUX", {"agr_obj": "3SG", "agr_iobj": "3SG", "tense": "PAST"})

    def test_zitzaigun(self, engine):
        _check_aux(engine, "zitzaigun", "AUX", {"agr_obj": "3SG", "agr_iobj": "1PL", "tense": "PAST"})

    def test_zitzaizuen(self, engine):
        _check_aux(engine, "zitzaizuen", "AUX", {"agr_obj": "3SG", "agr_iobj": "2PL", "tense": "PAST"})

    def test_zitzaien(self, engine):
        _check_aux(engine, "zitzaien", "AUX", {"agr_obj": "3SG", "agr_iobj": "3PL", "tense": "PAST"})


# ══════════════════════════════════════════════════════════════════════════════
# NOR-NORI-NORK paradigm (ditransitive -- the crown jewel)
# ══════════════════════════════════════════════════════════════════════════════

class TestNNNPresentAbs3SGDat3SG:
    """NOR-NORI-NORK present, ABS=3SG, DAT=3SG."""

    def test_diot(self, engine):
        _check_aux(engine, "diot", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "3SG", "agr_subj": "1SG", "tense": "PRES"})

    def test_diozu(self, engine):
        _check_aux(engine, "diozu", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "3SG", "agr_subj": "2SG", "tense": "PRES"})

    def test_dio(self, engine):
        _check_aux(engine, "dio", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "3SG", "agr_subj": "3SG", "tense": "PRES"})

    def test_diogu(self, engine):
        _check_aux(engine, "diogu", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "3SG", "agr_subj": "1PL", "tense": "PRES"})

    def test_diozue(self, engine):
        _check_aux(engine, "diozue", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "3SG", "agr_subj": "2PL", "tense": "PRES"})

    def test_diote(self, engine):
        _check_aux(engine, "diote", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "3SG", "agr_subj": "3PL", "tense": "PRES"})


class TestNNNPresentAbs3SGDat1SG:
    """NOR-NORI-NORK present, ABS=3SG, DAT=1SG (someone verbs it to me)."""

    def test_dit(self, engine):
        _check_aux(engine, "dit", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "1SG", "agr_subj": "3SG", "tense": "PRES"})

    def test_didazu(self, engine):
        _check_aux(engine, "didazu", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "1SG", "agr_subj": "2SG", "tense": "PRES"})

    def test_didate(self, engine):
        _check_aux(engine, "didate", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "1SG", "agr_subj": "3PL", "tense": "PRES"})


class TestNNNPresentAbs3SGDatOther:
    """NOR-NORI-NORK present, ABS=3SG, various DAT."""

    def test_dizu(self, engine):
        _check_aux(engine, "dizu", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "2SG", "agr_subj": "3SG", "tense": "PRES"})

    def test_digu(self, engine):
        _check_aux(engine, "digu", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "1PL", "agr_subj": "3SG", "tense": "PRES"})

    def test_die(self, engine):
        _check_aux(engine, "die", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "3PL", "agr_subj": "3SG", "tense": "PRES"})

    def test_digute(self, engine):
        _check_aux(engine, "digute", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "1PL", "agr_subj": "3PL", "tense": "PRES"})

    def test_diete(self, engine):
        _check_aux(engine, "diete", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "3PL", "agr_subj": "3PL", "tense": "PRES"})


class TestNNNPresentAbs3PL:
    """NOR-NORI-NORK present, ABS=3PL (dizki- forms)."""

    def test_dizkiot(self, engine):
        _check_aux(engine, "dizkiot", "AUX",
                   {"agr_obj": "3PL", "agr_iobj": "3SG", "agr_subj": "1SG", "tense": "PRES"})

    def test_dizkio(self, engine):
        _check_aux(engine, "dizkio", "AUX",
                   {"agr_obj": "3PL", "agr_iobj": "3SG", "agr_subj": "3SG", "tense": "PRES"})

    def test_dizkiogu(self, engine):
        _check_aux(engine, "dizkiogu", "AUX",
                   {"agr_obj": "3PL", "agr_iobj": "3SG", "agr_subj": "1PL", "tense": "PRES"})

    def test_dizkiote(self, engine):
        _check_aux(engine, "dizkiote", "AUX",
                   {"agr_obj": "3PL", "agr_iobj": "3SG", "agr_subj": "3PL", "tense": "PRES"})

    def test_dizkit(self, engine):
        _check_aux(engine, "dizkit", "AUX",
                   {"agr_obj": "3PL", "agr_iobj": "1SG", "agr_subj": "3SG", "tense": "PRES"})

    def test_dizkigu(self, engine):
        _check_aux(engine, "dizkigu", "AUX",
                   {"agr_obj": "3PL", "agr_iobj": "1PL", "agr_subj": "3SG", "tense": "PRES"})

    def test_dizkiete(self, engine):
        _check_aux(engine, "dizkiete", "AUX",
                   {"agr_obj": "3PL", "agr_iobj": "3PL", "agr_subj": "3PL", "tense": "PRES"})


class TestNNNPast:
    """NOR-NORI-NORK past tense forms."""

    def test_nion(self, engine):
        _check_aux(engine, "nion", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "3SG", "agr_subj": "1SG", "tense": "PAST"})

    def test_zion(self, engine):
        _check_aux(engine, "zion", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "3SG", "agr_subj": "3SG", "tense": "PAST"})

    def test_genion(self, engine):
        _check_aux(engine, "genion", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "3SG", "agr_subj": "1PL", "tense": "PAST"})

    def test_zioten(self, engine):
        _check_aux(engine, "zioten", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "3SG", "agr_subj": "3PL", "tense": "PAST"})

    def test_zidan(self, engine):
        _check_aux(engine, "zidan", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "1SG", "agr_subj": "3SG", "tense": "PAST"})

    def test_zidaten(self, engine):
        _check_aux(engine, "zidaten", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "1SG", "agr_subj": "3PL", "tense": "PAST"})

    def test_zigun(self, engine):
        _check_aux(engine, "zigun", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "1PL", "agr_subj": "3SG", "tense": "PAST"})

    def test_zien(self, engine):
        _check_aux(engine, "zien", "AUX",
                   {"agr_obj": "3SG", "agr_iobj": "3PL", "agr_subj": "3SG", "tense": "PAST"})

    def test_zizkion(self, engine):
        _check_aux(engine, "zizkion", "AUX",
                   {"agr_obj": "3PL", "agr_iobj": "3SG", "agr_subj": "3SG", "tense": "PAST"})

    def test_zizkioten(self, engine):
        _check_aux(engine, "zizkioten", "AUX",
                   {"agr_obj": "3PL", "agr_iobj": "3SG", "agr_subj": "3PL", "tense": "PAST"})

    def test_zizkidan(self, engine):
        _check_aux(engine, "zizkidan", "AUX",
                   {"agr_obj": "3PL", "agr_iobj": "1SG", "agr_subj": "3SG", "tense": "PAST"})

    def test_zizkien(self, engine):
        _check_aux(engine, "zizkien", "AUX",
                   {"agr_obj": "3PL", "agr_iobj": "3PL", "agr_subj": "3SG", "tense": "PAST"})

    def test_zizkieten(self, engine):
        _check_aux(engine, "zizkieten", "AUX",
                   {"agr_obj": "3PL", "agr_iobj": "3PL", "agr_subj": "3PL", "tense": "PAST"})
