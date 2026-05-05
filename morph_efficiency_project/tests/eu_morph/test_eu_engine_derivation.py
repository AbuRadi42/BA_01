"""
Derivational morphology tests for the Basque engine.
Tests suffix and prefix derivation detection.
"""
import pytest
from morph_efficiency_project.scripts.engines.eu_engine import BasqueEngine

@pytest.fixture(scope="module")
def engine():
    return BasqueEngine()


class TestSuffixDerivation:
    """Derivational suffix detection (Step B)."""

    def test_tasun_quality(self, engine):
        t = engine.analyze("edertasun")
        assert "tasun->QUALITY" in t.derived_chain

    def test_garri_worthy(self, engine):
        t = engine.analyze("harrigarri")
        assert any("garri" in d for d in t.derived_chain)

    def test_tzaile_agent(self, engine):
        t = engine.analyze("irakastzaile")
        assert any("tzaile" in d for d in t.derived_chain)

    def test_le_agent(self, engine):
        t = engine.analyze("idazle")
        assert any("le" in d for d in t.derived_chain)

    def test_keta_action(self, engine):
        t = engine.analyze("bilaketa")
        assert any("keta" in d for d in t.derived_chain)

    def test_kuntza_process(self, engine):
        t = engine.analyze("hezkuntza")
        assert any("kuntza" in d for d in t.derived_chain)

    def test_tegi_place(self, engine):
        t = engine.analyze("ikastegi")
        assert any("tegi" in d for d in t.derived_chain)

    def test_tsu_abounding(self, engine):
        t = engine.analyze("indartsu")
        assert any("tsu" in d for d in t.derived_chain)

    def test_kor_prone_to(self, engine):
        t = engine.analyze("beldurkor")
        assert any("kor" in d for d in t.derived_chain)

    def test_dun_possessing(self, engine):
        t = engine.analyze("dirudun")
        assert any("dun" in d for d in t.derived_chain)

    def test_tar_inhabitant(self, engine):
        t = engine.analyze("bilbotar")
        assert any("tar" in d for d in t.derived_chain)

    def test_zko_made_of(self, engine):
        t = engine.analyze("egurrezko")
        assert any("zko" in d for d in t.derived_chain)

    def test_kide_fellow(self, engine):
        t = engine.analyze("lankide")
        assert any("kide" in d for d in t.derived_chain)

    def test_gile_maker(self, engine):
        t = engine.analyze("esnegile")
        assert any("gile" in d for d in t.derived_chain)

    def test_txo_diminutive(self, engine):
        t = engine.analyze("neskatxo")
        assert any("txo" in d for d in t.derived_chain)

    def test_zain_guardian(self, engine):
        t = engine.analyze("atezain")
        assert any("zain" in d for d in t.derived_chain)


class TestPrefixDerivation:
    """Derivational prefix detection."""

    def test_des_reversal(self, engine):
        t = engine.analyze("desagertu")
        # des- prefix should be detected; -tu is perf participle
        # prefix check happens in step_b on the stem after step_a
        assert any("des" in d for d in t.derived_chain) or t.root == "ager"

    def test_bir_repetition(self, engine):
        t = engine.analyze("birsortu")
        assert any("bir" in d for d in t.derived_chain) or t.root == "sor"

    def test_ez_negation(self, engine):
        t = engine.analyze("ezezagun")
        assert any("ez" in d for d in t.derived_chain)


class TestDerivationWithInflection:
    """Derivation combined with inflectional suffixes."""

    def test_edertasunaren(self, engine):
        # edertasunaren = eder + -tasun + -aren (GEN.DEF.SG)
        t = engine.analyze("edertasunaren")
        assert t.tags.get("case") == "GEN"
        assert t.tags.get("def") == "DEF"
        assert any("tasun" in d for d in t.derived_chain)

    def test_indartsuak(self, engine):
        # indartsuak = indar + -tsu + -ak (ABS.DEF.PL / ERG.DEF.SG)
        t = engine.analyze("indartsuak")
        assert t.tags.get("case") in ("ABS", "ERG")

    def test_bilaketan(self, engine):
        # bilaketan = bila + -keta + -an (INES.DEF.SG)
        t = engine.analyze("bilaketan")
        assert t.tags.get("case") == "INES"
        assert any("keta" in d for d in t.derived_chain)

    def test_ikastegian(self, engine):
        # ikastegian = ikas + -tegi + -an
        t = engine.analyze("ikastegian")
        assert t.tags.get("case") == "INES"
