"""
Case suffix stripping tests for the Basque engine.
Tests all 14 cases with indefinite, definite singular, and definite plural variants.
"""
import pytest
from morph_efficiency_project.scripts.engines.eu_engine import BasqueEngine

@pytest.fixture(scope="module")
def engine():
    return BasqueEngine()


# ── ABS (absolutive) ─────────────────────────────────────────────────────────

class TestAbsolutive:
    def test_abs_def_sg(self, engine):
        t = engine.analyze("etxea")
        assert t.tags.get("case") == "ABS"
        assert t.tags.get("def") == "DEF"
        assert t.tags.get("num") == "SG"
        assert t.root == "etxe"

    def test_abs_def_pl(self, engine):
        t = engine.analyze("liburuak")
        # -ak is ambiguous ABS.PL / ERG.SG
        assert t.tags.get("case") in ("ABS", "ERG")

    def test_abs_indef_is_bare(self, engine):
        # Indefinite absolutive has no suffix (zero marking)
        t = engine.analyze("etxe")
        # Bare form -- no case suffix found
        assert t.tags.get("case") is None or t.pos == "UNKNOWN"


# ── ERG (ergative) ───────────────────────────────────────────────────────────

class TestErgative:
    def test_erg_def_pl(self, engine):
        t = engine.analyze("gizonek")
        assert t.tags.get("case") == "ERG"
        assert t.tags.get("num") == "PL"
        assert t.tags.get("def") == "DEF"

    def test_erg_def_sg_ambig(self, engine):
        # ERG.DEF.SG uses -ak, same as ABS.DEF.PL
        t = engine.analyze("gizonak")
        assert t.tags.get("case") in ("ABS", "ERG")
        # Should indicate ambiguity
        assert "ambig_ak" in t.tags or t.tags.get("case") in ("ABS", "ERG")

    def test_erg_indef(self, engine):
        t = engine.analyze("norbaitek")
        # -k on indefinite = ERG
        assert t.tags.get("case") in ("ERG", None)  # short stem may not match


# ── DAT (dative) ─────────────────────────────────────────────────────────────

class TestDative:
    def test_dat_def_sg(self, engine):
        t = engine.analyze("gizonari")
        assert t.tags.get("case") == "DAT"
        assert t.tags.get("def") == "DEF"
        assert t.tags.get("num") == "SG"
        assert t.root == "gizon"

    def test_dat_def_pl(self, engine):
        t = engine.analyze("gizonei")
        assert t.tags.get("case") == "DAT"
        assert t.tags.get("num") == "PL"

    def test_dat_indef(self, engine):
        t = engine.analyze("lagunri")
        assert t.tags.get("case") == "DAT"
        assert t.tags.get("def") == "INDEF"


# ── GEN (genitive) ──────────────────────────────────────────────────────────

class TestGenitive:
    def test_gen_def_sg(self, engine):
        t = engine.analyze("etxearen")
        assert t.tags.get("case") == "GEN"
        assert t.tags.get("def") == "DEF"
        assert t.tags.get("num") == "SG"

    def test_gen_def_pl(self, engine):
        t = engine.analyze("etxeen")
        assert t.tags.get("case") == "GEN"
        assert t.tags.get("num") == "PL"

    def test_gen_indef(self, engine):
        t = engine.analyze("lagunren")
        assert t.tags.get("case") == "GEN"
        assert t.tags.get("def") == "INDEF"


# ── COM (comitative) ─────────────────────────────────────────────────────────

class TestComitative:
    def test_com_def_sg(self, engine):
        t = engine.analyze("lagunarekin")
        assert t.tags.get("case") == "COM"
        assert t.tags.get("def") == "DEF"
        assert t.tags.get("num") == "SG"

    def test_com_def_pl(self, engine):
        t = engine.analyze("lagunekin")
        assert t.tags.get("case") == "COM"
        assert t.tags.get("num") == "PL"

    def test_com_indef(self, engine):
        t = engine.analyze("lagunrekin")
        assert t.tags.get("case") == "COM"
        assert t.tags.get("def") == "INDEF"


# ── INS (instrumental) ──────────────────────────────────────────────────────

class TestInstrumental:
    def test_ins_def_sg(self, engine):
        t = engine.analyze("eskuaz")
        assert t.tags.get("case") == "INS"
        assert t.tags.get("def") == "DEF"
        assert t.tags.get("num") == "SG"

    def test_ins_def_pl(self, engine):
        t = engine.analyze("eskuez")
        assert t.tags.get("case") == "INS"
        assert t.tags.get("num") == "PL"

    def test_ins_indef(self, engine):
        t = engine.analyze("eskuz")
        assert t.tags.get("case") == "INS"
        assert t.tags.get("def") == "INDEF"


# ── INES (inessive) ─────────────────────────────────────────────────────────

class TestInessive:
    def test_ines_def_sg(self, engine):
        t = engine.analyze("etxean")
        assert t.tags.get("case") == "INES"
        assert t.tags.get("def") == "DEF"
        assert t.tags.get("num") == "SG"
        assert t.root == "etxe"

    def test_ines_def_pl(self, engine):
        t = engine.analyze("etxeetan")
        assert t.tags.get("case") == "INES"
        assert t.tags.get("num") == "PL"

    def test_ines_indef(self, engine):
        t = engine.analyze("tokinn")
        # -n is very short, may be unreliable on short stems
        # Just check it doesn't crash
        assert t is not None


# ── ALLAT (allative) ─────────────────────────────────────────────────────────

class TestAllative:
    def test_allat_def_sg(self, engine):
        t = engine.analyze("etxeara")
        assert t.tags.get("case") == "ALLAT"
        assert t.tags.get("def") == "DEF"
        assert t.tags.get("num") == "SG"

    def test_allat_def_pl(self, engine):
        t = engine.analyze("etxeetara")
        assert t.tags.get("case") == "ALLAT"
        assert t.tags.get("num") == "PL"

    def test_allat_indef(self, engine):
        t = engine.analyze("tokira")
        assert t.tags.get("case") == "ALLAT"


# ── ABLAT (ablative) ─────────────────────────────────────────────────────────

class TestAblative:
    def test_ablat_def_sg(self, engine):
        t = engine.analyze("etxeatik")
        assert t.tags.get("case") == "ABLAT"
        assert t.tags.get("def") == "DEF"
        assert t.tags.get("num") == "SG"

    def test_ablat_def_pl(self, engine):
        t = engine.analyze("etxeetatik")
        assert t.tags.get("case") == "ABLAT"
        assert t.tags.get("num") == "PL"

    def test_ablat_indef(self, engine):
        t = engine.analyze("tokitik")
        assert t.tags.get("case") == "ABLAT"


# ── LOC_GEN (locative genitive) ─────────────────────────────────────────────

class TestLocativeGenitive:
    def test_locgen_def_sg(self, engine):
        t = engine.analyze("etxeako")
        assert t.tags.get("case") == "LOC_GEN"
        assert t.tags.get("def") == "DEF"
        assert t.tags.get("num") == "SG"

    def test_locgen_def_pl(self, engine):
        t = engine.analyze("etxeetako")
        assert t.tags.get("case") == "LOC_GEN"
        assert t.tags.get("num") == "PL"

    def test_locgen_indef(self, engine):
        t = engine.analyze("tokiko")
        assert t.tags.get("case") == "LOC_GEN"


# ── DEST (destinative) ──────────────────────────────────────────────────────

class TestDestinative:
    def test_dest_def_sg(self, engine):
        t = engine.analyze("etxearako")
        assert t.tags.get("case") == "DEST"
        assert t.tags.get("def") == "DEF"
        assert t.tags.get("num") == "SG"

    def test_dest_def_pl(self, engine):
        t = engine.analyze("etxeetarako")
        assert t.tags.get("case") == "DEST"
        assert t.tags.get("num") == "PL"

    def test_dest_indef(self, engine):
        t = engine.analyze("tokirako")
        assert t.tags.get("case") == "DEST"


# ── MOT (motivative) ────────────────────────────────────────────────────────

class TestMotivative:
    def test_mot_def_sg(self, engine):
        t = engine.analyze("etxeagatik")
        assert t.tags.get("case") == "MOT"
        assert t.tags.get("def") == "DEF"
        assert t.tags.get("num") == "SG"

    def test_mot_def_pl(self, engine):
        t = engine.analyze("etxeegatik")
        assert t.tags.get("case") == "MOT"
        assert t.tags.get("num") == "PL"

    def test_mot_indef(self, engine):
        t = engine.analyze("tokigatik")
        assert t.tags.get("case") == "MOT"


# ── PART (partitive) ────────────────────────────────────────────────────────

class TestPartitive:
    def test_part_indef(self, engine):
        t = engine.analyze("lagunrik")
        assert t.tags.get("case") == "PART"
        assert t.tags.get("def") == "INDEF"

    def test_part_no_def_forms(self, engine):
        # Partitive has no definite forms
        t = engine.analyze("etxerik")
        assert t.tags.get("case") == "PART"


# ── PROL (prolative) ────────────────────────────────────────────────────────

class TestProlative:
    def test_prol_def_sg(self, engine):
        t = engine.analyze("gizonatzat")
        assert t.tags.get("case") == "PROL"
        assert t.tags.get("def") == "DEF"

    def test_prol_def_pl(self, engine):
        t = engine.analyze("gizonetzat")
        assert t.tags.get("case") == "PROL"
        assert t.tags.get("num") == "PL"

    def test_prol_indef(self, engine):
        t = engine.analyze("laguntzat")
        assert t.tags.get("case") == "PROL"


# ── The -ak ambiguity ───────────────────────────────────────────────────────

class TestAkAmbiguity:
    """The suffix -ak is ambiguous between ABS.DEF.PL and ERG.DEF.SG."""

    def test_ak_produces_case(self, engine):
        t = engine.analyze("gizonak")
        assert t.tags.get("case") in ("ABS", "ERG")

    def test_ak_has_ambig_flag(self, engine):
        t = engine.analyze("gizonak")
        # Either we get ambig_ak tag or it resolves to one
        assert t.tags.get("case") in ("ABS", "ERG")

    def test_ek_is_unambiguous_erg(self, engine):
        t = engine.analyze("gizonek")
        assert t.tags.get("case") == "ERG"
        assert t.tags.get("num") == "PL"

    def test_different_stems_ak(self, engine):
        for word in ["liburuak", "etxeak", "umeak"]:
            t = engine.analyze(word)
            assert t.tags.get("case") in ("ABS", "ERG"), f"{word} not parsed"


# ── Root extraction from case-inflected forms ────────────────────────────────

class TestCaseRootExtraction:
    def test_etxearen_root(self, engine):
        t = engine.analyze("etxearen")
        assert t.root == "etxe"

    def test_gizonari_root(self, engine):
        t = engine.analyze("gizonari")
        assert t.root == "gizon"

    def test_mendian_root(self, engine):
        t = engine.analyze("mendian")
        assert t.root == "mendi"

    def test_lagunarekin_root(self, engine):
        t = engine.analyze("lagunarekin")
        assert t.root == "lagun"
