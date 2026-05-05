"""
Adversarial and edge case tests for the Basque engine.
Tests ambiguous forms, auxiliary edge cases, ergativity, closed-class, etc.
"""
import pytest
from morph_efficiency_project.scripts.engines.eu_engine import BasqueEngine

@pytest.fixture(scope="module")
def engine():
    return BasqueEngine()


class TestAmbiguousForms:
    """Forms that are ambiguous between different analyses."""

    def test_ak_ambiguity_abs_vs_erg(self, engine):
        # -ak: ABS.DEF.PL or ERG.DEF.SG
        t = engine.analyze("gizonak")
        assert t.tags.get("case") in ("ABS", "ERG")

    def test_en_ambiguity_gen_vs_super(self, engine):
        # -en could be GEN.DEF.PL or superlative
        # For a long word, case stripping should win
        t = engine.analyze("etxeen")
        assert t.tags.get("case") == "GEN"

    def test_da_as_auxiliary_not_noun(self, engine):
        # "da" is AUX (is) -- should not be stripped as a noun
        t = engine.analyze("da")
        assert t.pos == "AUX"
        assert t.tags.get("agr_obj") == "3SG"

    def test_du_as_auxiliary(self, engine):
        t = engine.analyze("du")
        assert t.pos == "AUX"
        assert t.tags["agr_subj"] == "3SG"

    def test_zen_as_auxiliary(self, engine):
        t = engine.analyze("zen")
        assert t.pos == "AUX"
        assert t.tags["tense"] == "PAST"

    def test_bat_as_determiner(self, engine):
        t = engine.analyze("bat")
        assert t.pos == "DET"

    def test_hori_as_pronoun(self, engine):
        t = engine.analyze("hori")
        assert t.pos == "PRON"

    def test_ko_suffix_ambiguity(self, engine):
        # -ko could be LOC_GEN or prospective aspect
        # On a word like "tokiko" it should be LOC_GEN
        t = engine.analyze("tokiko")
        assert t.tags.get("case") == "LOC_GEN"


class TestAuxiliaryEdgeCases:
    """Edge cases in auxiliary lookup."""

    def test_case_insensitive(self, engine):
        t = engine.analyze("Dut")
        assert t.pos == "AUX"

    def test_allocutive_duk(self, engine):
        t = engine.analyze("duk")
        assert t.pos == "AUX"
        assert t.tags.get("allocutive_gender") == "MASC"

    def test_allocutive_dun(self, engine):
        t = engine.analyze("dun")
        assert t.pos == "AUX"
        assert t.tags.get("allocutive_gender") == "FEM"

    def test_all_aux_have_agr_obj(self, engine):
        """Every auxiliary form must have agr_obj (absolutive agreement)."""
        for form, info in engine.aux_lookup.items():
            if info.get("paradigm") == "SYNTHETIC":
                continue
            t = engine.analyze(form)
            assert "agr_obj" in t.tags, f"{form} missing agr_obj"

    def test_nor_nork_have_agr_subj(self, engine):
        """Every NOR-NORK form must have agr_subj."""
        for form, info in engine.aux_lookup.items():
            if info.get("paradigm") in ("NOR-NORK", "NOR-NORI-NORK"):
                t = engine.analyze(form)
                assert "agr_subj" in t.tags, f"{form} missing agr_subj"

    def test_nor_nori_nork_have_agr_iobj(self, engine):
        """Every NOR-NORI-NORK form must have agr_iobj."""
        for form, info in engine.aux_lookup.items():
            if info.get("paradigm") == "NOR-NORI-NORK":
                t = engine.analyze(form)
                assert "agr_iobj" in t.tags, f"{form} missing agr_iobj"

    def test_nor_nori_have_agr_iobj(self, engine):
        """Every NOR-NORI form must have agr_iobj."""
        for form, info in engine.aux_lookup.items():
            if info.get("paradigm") == "NOR-NORI":
                t = engine.analyze(form)
                assert "agr_iobj" in t.tags, f"{form} missing agr_iobj"

    def test_intransitive_no_agr_subj(self, engine):
        """NOR forms must NOT have agr_subj."""
        for form, info in engine.aux_lookup.items():
            if info.get("paradigm") == "NOR":
                t = engine.analyze(form)
                assert "agr_subj" not in t.tags, f"{form} has spurious agr_subj"


class TestErgativityScenarios:
    """Test ergativity alignment via sentence analysis."""

    def test_intransitive_sentence(self, engine):
        # Umea lo dago = child-ABS sleep is
        tokens, ok, msg = engine.analyze_sentence("umea lo dago")
        assert ok, msg

    def test_transitive_sentence(self, engine):
        # gizonak liburua irakurtzen du = man-ERG book-ABS read-IMPERF AUX
        tokens, ok, msg = engine.analyze_sentence("gizonak liburua irakurtzen du")
        assert ok, msg

    def test_erg_requires_transitive_aux(self, engine):
        # ERG noun + intransitive aux should fail validation
        tokens, ok, msg = engine.analyze_sentence("gizonek da")
        # gizonek is ERG.PL, da is NOR (intransitive) -- should flag
        assert not ok or "agr_subj" in msg


class TestClosedClassEdgeCases:
    """Closed-class edge cases."""

    def test_all_conjunctions(self, engine):
        for word in ["eta", "edo", "baina", "beraz", "orduan"]:
            t = engine.analyze(word)
            assert t.pos == "CONJ", f"{word} not CONJ"

    def test_all_particles(self, engine):
        for word in ["ez", "al", "ote", "ba"]:
            t = engine.analyze(word)
            assert t.pos == "PART", f"{word} not PART"

    def test_question_words(self, engine):
        for word in ["nor", "zer", "non", "noiz", "nola", "zergatik"]:
            t = engine.analyze(word)
            assert t.pos in ("PRON", "ADV"), f"{word} unexpected pos={t.pos}"

    def test_pronouns(self, engine):
        for word in ["ni", "zu", "hi", "hura", "gu", "zuek", "haiek"]:
            t = engine.analyze(word)
            assert t.pos == "PRON", f"{word} not PRON"

    def test_postpositions(self, engine):
        for word in ["aurretik", "ondoren", "gainean", "kontra", "zehar"]:
            t = engine.analyze(word)
            assert t.pos == "ADP", f"{word} not ADP"

    def test_determiners(self, engine):
        for word in ["bat", "batzuk", "hainbat", "asko", "gutxi"]:
            t = engine.analyze(word)
            assert t.pos == "DET", f"{word} not DET"


class TestMultiWordExpressions:
    """Multi-word closed-class expressions."""

    def test_hala_ere(self, engine):
        tokens, _, _ = engine.analyze_sentence("hala ere")
        assert len(tokens) == 1
        assert tokens[0].pos == "CONJ"

    def test_nahiz_eta(self, engine):
        tokens, _, _ = engine.analyze_sentence("nahiz eta")
        assert len(tokens) == 1
        assert tokens[0].pos == "CONJ"

    def test_baldin_eta(self, engine):
        tokens, _, _ = engine.analyze_sentence("baldin eta gizona")
        assert tokens[0].pos == "CONJ"
        assert tokens[0].root == "baldin eta"


class TestEdgeCases:
    """Various edge cases."""

    def test_very_short_word(self, engine):
        t = engine.analyze("a")
        assert t is not None

    def test_unknown_word(self, engine):
        t = engine.analyze("xyzqwert")
        assert t.pos == "UNKNOWN"

    def test_empty_string_sentence(self, engine):
        tokens, ok, msg = engine.analyze_sentence("")
        assert tokens == []
        assert ok

    def test_single_aux_sentence(self, engine):
        tokens, ok, msg = engine.analyze_sentence("da")
        assert len(tokens) == 1
        assert tokens[0].pos == "AUX"

    def test_mixed_case_input(self, engine):
        t = engine.analyze("NAIZ")
        assert t.pos == "AUX"

    def test_synthetic_verb_is_verb_not_aux(self, engine):
        for form in ["dator", "dago", "doa", "daki", "dabil"]:
            t = engine.analyze(form)
            assert t.pos == "VERB", f"{form} should be VERB, got {t.pos}"

    def test_aux_root_izan_for_nor(self, engine):
        t = engine.analyze("naiz")
        assert t.root == "izan"

    def test_aux_root_ukan_for_nor_nork(self, engine):
        t = engine.analyze("dut")
        assert t.root == "ukan"

    def test_aux_root_izan_for_nor_nori(self, engine):
        t = engine.analyze("zait")
        assert t.root == "izan"

    def test_aux_root_ukan_for_nnn(self, engine):
        t = engine.analyze("diot")
        assert t.root == "ukan"


class TestValidators:
    """Test the Basque-specific validators."""

    def test_valid_aux_bundle(self, engine):
        from morph_efficiency_project.scripts.engines.shared import check_morph_sequence_eu
        tokens = [engine.analyze("dut")]
        assert check_morph_sequence_eu(tokens)

    def test_valid_noun_bundle(self, engine):
        from morph_efficiency_project.scripts.engines.shared import check_morph_sequence_eu
        tokens = [engine.analyze("etxean")]
        assert check_morph_sequence_eu(tokens)

    def test_valid_verb_bundle(self, engine):
        from morph_efficiency_project.scripts.engines.shared import check_morph_sequence_eu
        tokens = [engine.analyze("ikusten")]
        assert check_morph_sequence_eu(tokens)

    def test_sentence_validator_ok(self, engine):
        from morph_efficiency_project.scripts.engines.shared import validate_sentence_structure_eu
        tokens = [engine.analyze(w) for w in ["ikusten", "dut"]]
        ok, msg = validate_sentence_structure_eu(tokens)
        assert ok

    def test_all_aux_pass_validator(self, engine):
        from morph_efficiency_project.scripts.engines.shared import check_morph_sequence_eu
        for form in list(engine.aux_lookup.keys())[:50]:
            tokens = [engine.analyze(form)]
            assert check_morph_sequence_eu(tokens), f"validator failed for {form}"


class TestFeatureBundleStr:
    """Test feature bundle string generation."""

    def test_aux_bundle_str_contains_agr(self, engine):
        t = engine.analyze("dut")
        bundle = t.feature_bundle_str()
        assert "agr_obj=3SG" in bundle
        assert "agr_subj=1SG" in bundle

    def test_noun_bundle_str_contains_case(self, engine):
        t = engine.analyze("etxean")
        bundle = t.feature_bundle_str()
        assert "case=INES" in bundle

    def test_ditransitive_bundle_str(self, engine):
        t = engine.analyze("diot")
        bundle = t.feature_bundle_str()
        assert "agr_obj=3SG" in bundle
        assert "agr_subj=1SG" in bundle
        assert "agr_iobj=3SG" in bundle

    def test_token_str(self, engine):
        t = engine.analyze("dut")
        assert t.token_str() == "ukan.AUX"

    def test_synthetic_token_str(self, engine):
        t = engine.analyze("dator")
        assert t.token_str() == "etorri.VERB"
