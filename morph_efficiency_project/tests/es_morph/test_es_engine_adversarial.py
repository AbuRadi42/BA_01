"""
test_es_engine_adversarial.py
-----------------------------
Adversarial and edge case tests for the Spanish morphology engine.

Run: python -m pytest morph_efficiency_project/tests/es_morph/test_es_engine_adversarial.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import SpanishEngine
import pytest

engine = SpanishEngine()


# ══════════════════════════════════════════════════════════════════════════════
# EDGE CASES: EMPTY / SHORT INPUTS
# ══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_string(self):
        r = engine.analyze("")
        assert r.surface == ""

    def test_single_char_a(self):
        r = engine.analyze("a")
        assert r.pos == "ADP"  # preposition

    def test_single_char_x(self):
        r = engine.analyze("x")
        # should not crash, returns UNKNOWN or some POS
        assert r.surface == "x"

    def test_single_char_o(self):
        r = engine.analyze("o")
        assert r.pos == "CONJ"  # conjunction

    def test_number_string(self):
        r = engine.analyze("123")
        assert r.pos in ("UNKNOWN", "NUM")

    def test_all_caps(self):
        r = engine.analyze("HABLAR")
        assert r.root == "hablar" and r.pos == "VERB"

    def test_mixed_case(self):
        r = engine.analyze("HaBLaR")
        assert r.root == "hablar" and r.pos == "VERB"

    def test_very_short_word_de(self):
        r = engine.analyze("de")
        assert r.pos == "ADP"

    def test_very_short_word_en(self):
        r = engine.analyze("en")
        assert r.pos == "ADP"

    def test_two_char_unknown(self):
        r = engine.analyze("zz")
        assert r.surface == "zz"


# ══════════════════════════════════════════════════════════════════════════════
# CLOSED-CLASS WORDS
# ══════════════════════════════════════════════════════════════════════════════

class TestClosedClass:
    def test_el(self): assert engine.analyze("el").pos == "DET"
    def test_la(self): assert engine.analyze("la").pos == "DET"
    def test_los(self): assert engine.analyze("los").pos == "DET"
    def test_las(self): assert engine.analyze("las").pos == "DET"
    def test_un(self): assert engine.analyze("un").pos == "DET"
    def test_una(self): assert engine.analyze("una").pos == "DET"
    def test_al(self): assert engine.analyze("al").pos == "DET"
    def test_del(self): assert engine.analyze("del").pos == "DET"

    def test_a(self): assert engine.analyze("a").pos == "ADP"
    def test_con(self): assert engine.analyze("con").pos == "ADP"
    def test_para(self): assert engine.analyze("para").pos == "ADP"
    def test_por(self): assert engine.analyze("por").pos == "ADP"
    def test_sin(self): assert engine.analyze("sin").pos == "ADP"
    def test_sobre(self): assert engine.analyze("sobre").pos == "ADP"

    def test_yo(self): assert engine.analyze("yo").pos == "PRON"
    def test_tu(self): assert engine.analyze("tu").pos == "PRON"
    def test_ella(self): assert engine.analyze("ella").pos == "PRON"
    def test_nosotros(self): assert engine.analyze("nosotros").pos == "PRON"
    def test_ellos(self): assert engine.analyze("ellos").pos == "PRON"
    def test_ustedes(self): assert engine.analyze("ustedes").pos == "PRON"

    def test_y(self): assert engine.analyze("y").pos == "CONJ"
    def test_pero(self): assert engine.analyze("pero").pos == "CONJ"
    def test_porque(self): assert engine.analyze("porque").pos == "CONJ"
    def test_aunque(self): assert engine.analyze("aunque").pos == "CONJ"

    def test_no(self): assert engine.analyze("no").pos == "ADV"
    def test_muy(self): assert engine.analyze("muy").pos == "ADV"
    def test_ya(self): assert engine.analyze("ya").pos == "ADV"
    def test_bien(self): assert engine.analyze("bien").pos == "ADV"
    def test_nunca(self): assert engine.analyze("nunca").pos == "ADV"
    def test_siempre(self): assert engine.analyze("siempre").pos == "ADV"
    def test_aqui(self): assert engine.analyze("aqui").pos == "ADV"

    def test_dos(self): assert engine.analyze("dos").pos == "NUM"
    def test_tres(self): assert engine.analyze("tres").pos == "NUM"
    def test_mil(self): assert engine.analyze("mil").pos == "NUM"

    def test_haber_aux(self): assert engine.analyze("haber").pos == "AUX"
    def test_estar_aux(self): assert engine.analyze("estar").pos == "AUX"


# ══════════════════════════════════════════════════════════════════════════════
# DEMONSTRATIVES AND INDEFINITES
# ══════════════════════════════════════════════════════════════════════════════

class TestDemonstrativesAndIndefinites:
    def test_este_pron(self):
        r = engine.analyze("este")
        # 'este' is registered as demonstrative pronoun (closed class)
        # but also as estar subjunctive in irregulars
        assert r.pos in ("PRON", "VERB")

    def test_ese(self): assert engine.analyze("ese").pos == "PRON"
    def test_aquel(self): assert engine.analyze("aquel").pos == "PRON"
    def test_algo(self): assert engine.analyze("algo").pos == "PRON"
    def test_nada(self): assert engine.analyze("nada").pos == "PRON"
    def test_nadie(self): assert engine.analyze("nadie").pos == "PRON"
    def test_todo(self): assert engine.analyze("todo").pos == "PRON"
    def test_cada(self): assert engine.analyze("cada").pos == "PRON"


# ══════════════════════════════════════════════════════════════════════════════
# WORDS THAT LOOK LIKE VERB FORMS BUT AREN'T
# ══════════════════════════════════════════════════════════════════════════════

class TestFalseVerbs:
    def test_paso_noun(self):
        """'paso' could be NOUN (step) or VERB (I pass). Engine picks VERB."""
        r = engine.analyze("paso")
        # This is an acceptable ambiguity - the engine prefers verb reading
        assert r.pos in ("VERB", "NOUN")

    def test_como_conj(self):
        """'como' is in closed class as conjunction."""
        r = engine.analyze("como")
        assert r.pos == "CONJ"

    def test_porque_conj(self):
        """'porque' is a conjunction, not a verb form."""
        r = engine.analyze("porque")
        assert r.pos == "CONJ"

    def test_cuando_conj(self):
        """'cuando' is a conjunction."""
        r = engine.analyze("cuando")
        assert r.pos == "CONJ"

    def test_donde_conj(self):
        """'donde' is a conjunction."""
        r = engine.analyze("donde")
        assert r.pos == "CONJ"


# ══════════════════════════════════════════════════════════════════════════════
# INVARIANT NOUNS
# ══════════════════════════════════════════════════════════════════════════════

class TestInvariantNouns:
    def test_crisis(self):
        r = engine.analyze("crisis")
        assert r.pos == "NOUN" and r.tags.get("invariant") == "YES"

    def test_lunes(self):
        r = engine.analyze("lunes")
        assert r.pos == "NOUN" and r.tags.get("invariant") == "YES"

    def test_martes(self):
        r = engine.analyze("martes")
        assert r.pos == "NOUN" and r.tags.get("invariant") == "YES"

    def test_miercoles(self):
        r = engine.analyze("miercoles")
        assert r.pos == "NOUN" and r.tags.get("invariant") == "YES"

    def test_jueves(self):
        r = engine.analyze("jueves")
        assert r.pos == "NOUN" and r.tags.get("invariant") == "YES"

    def test_viernes(self):
        r = engine.analyze("viernes")
        assert r.pos == "NOUN" and r.tags.get("invariant") == "YES"

    def test_virus(self):
        r = engine.analyze("virus")
        assert r.pos == "NOUN" and r.tags.get("invariant") == "YES"

    def test_paraguas(self):
        r = engine.analyze("paraguas")
        assert r.pos == "NOUN" and r.tags.get("invariant") == "YES"


# ══════════════════════════════════════════════════════════════════════════════
# GENDER EXCEPTION NOUNS
# ══════════════════════════════════════════════════════════════════════════════

class TestGenderExceptions:
    def test_dia_masc(self):
        r = engine.analyze("dia")
        assert r.pos == "NOUN" and r.tags.get("gender") == "MASC"

    def test_mano_fem(self):
        r = engine.analyze("mano")
        assert r.pos == "NOUN" and r.tags.get("gender") == "FEM"

    def test_mapa_masc(self):
        r = engine.analyze("mapa")
        assert r.pos == "NOUN" and r.tags.get("gender") == "MASC"

    def test_foto_fem(self):
        r = engine.analyze("foto")
        assert r.pos == "NOUN" and r.tags.get("gender") == "FEM"

    def test_planeta_masc(self):
        r = engine.analyze("planeta")
        assert r.pos == "NOUN" and r.tags.get("gender") == "MASC"

    def test_tema_masc(self):
        r = engine.analyze("tema")
        assert r.pos == "NOUN" and r.tags.get("gender") == "MASC"

    def test_problema_masc(self):
        r = engine.analyze("problema")
        assert r.pos == "NOUN" and r.tags.get("gender") == "MASC"

    def test_sistema_masc(self):
        r = engine.analyze("sistema")
        assert r.pos == "NOUN" and r.tags.get("gender") == "MASC"

    def test_programa_masc(self):
        r = engine.analyze("programa")
        assert r.pos == "NOUN" and r.tags.get("gender") == "MASC"


# ══════════════════════════════════════════════════════════════════════════════
# NOUN PLURAL STRIPPING
# ══════════════════════════════════════════════════════════════════════════════

class TestNounPlurals:
    def test_gatos(self):
        r = engine.analyze("gatos")
        assert r.root == "gato" and r.tags.get("num") == "PL"

    def test_flores(self):
        r = engine.analyze("flores")
        assert r.root == "flor" and r.tags.get("num") == "PL"
        # "flor" ends in -or so heuristic assigns MASC (limitation)
        assert r.tags.get("gender") == "MASC"

    def test_felices(self):
        r = engine.analyze("felices")
        assert r.root == "feliz" and r.tags.get("num") == "PL"

    def test_luces(self):
        r = engine.analyze("luces")
        assert r.root == "luz" and r.tags.get("num") == "PL"

    def test_voces(self):
        r = engine.analyze("voces")
        assert r.root == "voz" and r.tags.get("num") == "PL"

    def test_ciudades(self):
        r = engine.analyze("ciudades")
        assert r.root == "ciudad" and r.tags.get("num") == "PL"

    def test_manos_fem_pl(self):
        r = engine.analyze("manos")
        assert r.root == "mano" and r.tags.get("gender") == "FEM" and r.tags.get("num") == "PL"

    def test_dias_masc_pl(self):
        r = engine.analyze("dias")
        assert r.root == "dia" and r.tags.get("gender") == "MASC" and r.tags.get("num") == "PL"


# ══════════════════════════════════════════════════════════════════════════════
# IRREGULAR COMPARATIVES
# ══════════════════════════════════════════════════════════════════════════════

class TestIrregularComparatives:
    def test_mejor(self):
        r = engine.analyze("mejor")
        assert r.root == "bueno" and r.pos == "ADJ" and r.tags.get("degree") == "COMP"

    def test_peor(self):
        r = engine.analyze("peor")
        assert r.root == "malo" and r.pos == "ADJ" and r.tags.get("degree") == "COMP"

    def test_mayor(self):
        r = engine.analyze("mayor")
        assert r.root == "grande" and r.pos == "ADJ" and r.tags.get("degree") == "COMP"

    def test_menor(self):
        r = engine.analyze("menor")
        assert r.root == "pequeno" and r.pos == "ADJ" and r.tags.get("degree") == "COMP"

    def test_superior(self):
        r = engine.analyze("superior")
        assert r.pos == "ADJ" and r.tags.get("degree") == "COMP"

    def test_inferior(self):
        r = engine.analyze("inferior")
        assert r.pos == "ADJ" and r.tags.get("degree") == "COMP"

    def test_mejores_pl(self):
        r = engine.analyze("mejores")
        assert r.root == "bueno" and r.tags.get("num") == "PL"

    def test_peores_pl(self):
        r = engine.analyze("peores")
        assert r.root == "malo" and r.tags.get("num") == "PL"


# ══════════════════════════════════════════════════════════════════════════════
# SENTENCE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

class TestSentenceAnalysis:
    def test_basic_sentence(self):
        tokens, ok, msg = engine.analyze_sentence("yo hablo")
        assert len(tokens) == 2
        assert tokens[0].pos == "PRON"
        assert tokens[1].pos == "VERB"

    def test_sentence_returns_tuple(self):
        result = engine.analyze_sentence("el gato")
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_empty_sentence(self):
        tokens, ok, msg = engine.analyze_sentence("")
        assert tokens == []

    def test_closed_class_bypass(self):
        """Closed-class words should bypass inflectional analysis."""
        tokens, ok, msg = engine.analyze_sentence("en el")
        assert tokens[0].pos == "ADP"
        assert tokens[1].pos == "DET"


# ══════════════════════════════════════════════════════════════════════════════
# VALIDATOR TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestValidators:
    def test_valid_verb_tags(self):
        """Verb with proper tags should pass check_morph_sequence_es."""
        from morph_efficiency_project.scripts.engines.shared import check_morph_sequence_es
        from morph_efficiency_project.scripts.engines.shared import TokenInfo
        t = TokenInfo(surface="hablo", clitics={}, template="", root="hablar",
                      tags={"tense": "PRES", "mood": "IND", "person": "1", "num": "SG"},
                      pos="VERB")
        assert check_morph_sequence_es([t]) is True

    def test_invalid_noun_tags(self):
        """Noun with verb-specific tags should fail."""
        from morph_efficiency_project.scripts.engines.shared import check_morph_sequence_es
        from morph_efficiency_project.scripts.engines.shared import TokenInfo
        t = TokenInfo(surface="gato", clitics={}, template="", root="gato",
                      tags={"num": "SG", "tense": "PRES"},
                      pos="NOUN")
        assert check_morph_sequence_es([t]) is False

    def test_imp_1sg_invalid(self):
        """Imperative 1SG should fail validation."""
        from morph_efficiency_project.scripts.engines.shared import check_morph_sequence_es
        from morph_efficiency_project.scripts.engines.shared import TokenInfo
        t = TokenInfo(surface="hable", clitics={}, template="", root="hablar",
                      tags={"mood": "IMP", "person": "1", "num": "SG"},
                      pos="VERB")
        assert check_morph_sequence_es([t]) is False

    def test_sentence_validator_clitic_on_noun(self):
        """clitic_obj on a non-VERB should fail sentence validation."""
        from morph_efficiency_project.scripts.engines.shared import validate_sentence_structure_es
        from morph_efficiency_project.scripts.engines.shared import TokenInfo
        t = TokenInfo(surface="gato", clitics={}, template="", root="gato",
                      tags={"num": "SG", "clitic_obj": "LO"},
                      pos="NOUN")
        ok, msg = validate_sentence_structure_es([t])
        assert ok is False
        assert "clitic_obj on non-VERB" in msg

    def test_sentence_validator_degree_on_noun(self):
        """degree on non-ADJ should fail."""
        from morph_efficiency_project.scripts.engines.shared import validate_sentence_structure_es
        from morph_efficiency_project.scripts.engines.shared import TokenInfo
        t = TokenInfo(surface="gato", clitics={}, template="", root="gato",
                      tags={"degree": "COMP"},
                      pos="NOUN")
        ok, msg = validate_sentence_structure_es([t])
        assert ok is False
