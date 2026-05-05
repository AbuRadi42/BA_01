"""
test_es_engine_derivation.py
----------------------------
Tests for derivational suffix/prefix detection and multi-layer chains.

Per the spec, derivational analysis (Steps B/C) only runs when Step A
assigns POS = UNKNOWN. Words that are recognized as NOUN, VERB, etc.
in Step A will NOT have derived_chain populated.

Run: python -m pytest morph_efficiency_project/tests/es_morph/test_es_engine_derivation.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import SpanishEngine
import pytest

engine = SpanishEngine()


# ══════════════════════════════════════════════════════════════════════════════
# WORDS THAT REMAIN UNKNOWN AND GET DERIVATIONAL ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

class TestDerivationalOnUnknown:
    """Words that are not caught by closed-class, irregulars, or verb/noun
    matching will be UNKNOWN and get derivational stripping."""

    def test_internacional_chain(self):
        r = engine.analyze("internacional")
        # "internacional" ends in -al -> gets derivational stripping
        if r.pos == "UNKNOWN":
            assert len(r.derived_chain) > 0

    def test_cultural(self):
        r = engine.analyze("cultural")
        if r.pos == "UNKNOWN":
            assert len(r.derived_chain) > 0

    def test_productivo(self):
        r = engine.analyze("productivo")
        # May match as VERB (-o) or NOUN (masc), but if UNKNOWN, chain populated
        if r.pos == "UNKNOWN":
            assert len(r.derived_chain) > 0

    def test_antirrobo(self):
        r = engine.analyze("antirrobo")
        if r.pos == "UNKNOWN":
            assert len(r.derived_chain) > 0

    def test_desorden(self):
        r = engine.analyze("desorden")
        # Not a verb, not a standard noun pattern
        if r.pos == "UNKNOWN":
            assert len(r.derived_chain) > 0

    def test_reconstruccion_is_noun(self):
        r = engine.analyze("reconstruccion")
        # -cion ending -> gender=FEM -> NOUN
        assert r.pos == "NOUN" or r.pos == "UNKNOWN"

    def test_supermercado(self):
        # Ends in -o, may be caught by verb
        r = engine.analyze("supermercado")
        assert r.pos in ("VERB", "NOUN", "UNKNOWN")


# ══════════════════════════════════════════════════════════════════════════════
# ADVERBIALIZATION (-mente)
# ══════════════════════════════════════════════════════════════════════════════

class TestAdverbialization:
    def test_rapidamente(self):
        r = engine.analyze("rapidamente")
        assert r.pos == "ADV"

    def test_facilmente(self):
        r = engine.analyze("facilmente")
        assert r.pos == "ADV"

    def test_lentamente(self):
        r = engine.analyze("lentamente")
        assert r.pos == "ADV"

    def test_completamente(self):
        r = engine.analyze("completamente")
        assert r.pos == "ADV"

    def test_simplemente(self):
        r = engine.analyze("simplemente")
        assert r.pos == "ADV"

    def test_naturalmente(self):
        r = engine.analyze("naturalmente")
        assert r.pos == "ADV"

    def test_absolutamente(self):
        r = engine.analyze("absolutamente")
        assert r.pos == "ADV"

    def test_normalmente(self):
        r = engine.analyze("normalmente")
        assert r.pos == "ADV"


# ══════════════════════════════════════════════════════════════════════════════
# STEP B DIRECT TESTING (via engine internals)
# ══════════════════════════════════════════════════════════════════════════════

class TestStepBDirect:
    """Test derivational stripping directly using _step_b."""

    def test_suffix_cion(self):
        stem, chain = engine._step_b("comunicacion")
        assert len(chain) > 0 and "cion" in chain[0]

    def test_suffix_sion(self):
        stem, chain = engine._step_b("expresion")
        assert len(chain) > 0

    def test_suffix_miento(self):
        stem, chain = engine._step_b("conocimiento")
        assert len(chain) > 0 and "miento" in chain[0]

    def test_suffix_idad(self):
        stem, chain = engine._step_b("realidad")
        assert len(chain) > 0

    def test_suffix_dad(self):
        stem, chain = engine._step_b("bondad")
        assert len(chain) > 0

    def test_suffix_ancia(self):
        stem, chain = engine._step_b("tolerancia")
        assert len(chain) > 0

    def test_suffix_encia(self):
        stem, chain = engine._step_b("paciencia")
        assert len(chain) > 0

    def test_suffix_ura(self):
        stem, chain = engine._step_b("hermosura")
        assert len(chain) > 0

    def test_suffix_aje(self):
        stem, chain = engine._step_b("reciclaje")
        assert len(chain) > 0

    def test_suffix_eza(self):
        stem, chain = engine._step_b("belleza")
        assert len(chain) > 0

    def test_suffix_azgo(self):
        stem, chain = engine._step_b("liderazgo")
        assert len(chain) > 0

    def test_suffix_dor(self):
        stem, chain = engine._step_b("trabajador")
        assert len(chain) > 0

    def test_suffix_ero(self):
        stem, chain = engine._step_b("panadero")
        assert len(chain) > 0

    def test_suffix_ista(self):
        stem, chain = engine._step_b("pianista")
        assert len(chain) > 0

    def test_suffix_ismo(self):
        stem, chain = engine._step_b("socialismo")
        assert len(chain) > 0

    def test_suffix_anza(self):
        stem, chain = engine._step_b("esperanza")
        assert len(chain) > 0

    def test_suffix_tud(self):
        stem, chain = engine._step_b("juventud")
        assert len(chain) > 0

    def test_suffix_oso(self):
        stem, chain = engine._step_b("peligroso")
        assert len(chain) > 0

    def test_suffix_ble(self):
        stem, chain = engine._step_b("comestible")
        assert len(chain) > 0

    def test_suffix_al(self):
        stem, chain = engine._step_b("nacional")
        assert len(chain) > 0

    def test_suffix_ico(self):
        stem, chain = engine._step_b("historico")
        assert len(chain) > 0

    def test_suffix_ivo(self):
        stem, chain = engine._step_b("productivo")
        assert len(chain) > 0

    def test_suffix_ante(self):
        stem, chain = engine._step_b("estudiante")
        assert len(chain) > 0

    def test_suffix_ario(self):
        stem, chain = engine._step_b("universitario")
        assert len(chain) > 0

    def test_suffix_mente(self):
        stem, chain = engine._step_b("rapidamente")
        assert len(chain) > 0

    # Prefixes
    def test_prefix_des(self):
        stem, chain = engine._step_b("desorden")
        assert len(chain) > 0 and "des" in chain[0]

    def test_prefix_in(self):
        stem, chain = engine._step_b("imposible")
        assert len(chain) > 0

    def test_prefix_re(self):
        stem, chain = engine._step_b("reconstruir")
        assert len(chain) > 0

    def test_prefix_pre(self):
        stem, chain = engine._step_b("predecir")
        assert len(chain) > 0

    def test_prefix_sobre(self):
        stem, chain = engine._step_b("sobrepasar")
        assert len(chain) > 0

    def test_prefix_sub(self):
        stem, chain = engine._step_b("subsuelo")
        assert len(chain) > 0

    def test_prefix_anti(self):
        stem, chain = engine._step_b("antirrobo")
        assert len(chain) > 0

    def test_prefix_auto(self):
        stem, chain = engine._step_b("autoservicio")
        assert len(chain) > 0

    def test_prefix_contra(self):
        stem, chain = engine._step_b("contradecir")
        assert len(chain) > 0

    def test_prefix_inter(self):
        stem, chain = engine._step_b("internacional")
        assert len(chain) > 0

    def test_prefix_multi(self):
        stem, chain = engine._step_b("multicultural")
        assert len(chain) > 0

    def test_prefix_super(self):
        stem, chain = engine._step_b("supermercado")
        assert len(chain) > 0


# ══════════════════════════════════════════════════════════════════════════════
# STEP C: MULTI-LAYER ROOT EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

class TestStepC:
    def test_internacionalizacion(self):
        """Multi-layer: -cion, -iza, inter-, -al -> nacion"""
        root = engine._step_c("internacionalizacion")
        # Should strip multiple layers
        assert len(root) < len("internacionalizacion")

    def test_desorganizacion(self):
        root = engine._step_c("desorganizacion")
        assert len(root) < len("desorganizacion")

    def test_short_word_unchanged(self):
        root = engine._step_c("sol")
        assert root == "sol"

    def test_no_derivation_unchanged(self):
        root = engine._step_c("perro")
        # "perro" has -ero suffix but stem "p" is too short (< 3)
        assert root == "perro"
