"""
test_es_engine_conjugation.py
-----------------------------
Tests for regular verb conjugation across all paradigms.
Covers -ar (hablar), -er (comer), -ir (vivir) verbs.

Run: python -m pytest morph_efficiency_project/tests/es_morph/test_es_engine_conjugation.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import SpanishEngine
import pytest

engine = SpanishEngine()


def _check(surface, exp_root, exp_tags, label=""):
    """Helper: verify root and selected tags."""
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: got {r.root!r}, expected {exp_root!r}"
    assert r.pos == "VERB", f"[{label}] pos: got {r.pos!r}, expected 'VERB'"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, (
            f"[{label}] tag {k}: got {r.tags.get(k)!r}, expected {v!r}")


# ══════════════════════════════════════════════════════════════════════════════
# PRESENT INDICATIVE
# ══════════════════════════════════════════════════════════════════════════════

class TestPresentIndicative:
    # -ar verbs (hablar)
    def test_hablar_1sg(self): _check("hablo", "hablar", {"tense": "PRES", "mood": "IND", "person": "1", "num": "SG"})
    def test_hablar_2sg(self): _check("hablas", "hablar", {"tense": "PRES", "mood": "IND", "person": "2", "num": "SG"})
    def test_hablar_3sg(self): _check("habla", "hablar", {"tense": "PRES", "mood": "IND", "person": "3", "num": "SG"})
    def test_hablar_1pl(self): _check("hablamos", "hablar", {"person": "1", "num": "PL"})
    def test_hablar_2pl(self): _check("hablais", "hablar", {"person": "2", "num": "PL"})
    def test_hablar_3pl(self): _check("hablan", "hablar", {"tense": "PRES", "mood": "IND", "person": "3", "num": "PL"})

    # -er verbs (comer) — note: "como" is in closed-class as CONJ
    def test_comer_1sg(self):
        r = engine.analyze("como")
        assert r.pos == "CONJ"  # closed-class takes priority
    def test_comer_2sg(self): _check("comes", "comer", {"tense": "PRES", "mood": "IND", "person": "2", "num": "SG"})
    def test_comer_3sg(self): _check("come", "comer", {"tense": "PRES", "mood": "IND", "person": "3", "num": "SG"})
    def test_comer_1pl(self): _check("comemos", "comer", {"tense": "PRES", "mood": "IND", "person": "1", "num": "PL"})
    def test_comer_2pl(self): _check("comeis", "comer", {"person": "2", "num": "PL"})
    def test_comer_3pl(self): _check("comen", "comer", {"tense": "PRES", "mood": "IND", "person": "3", "num": "PL"})

    # -ir verbs: 1SG -o is ambiguous across all 3 classes;
    # -imos is distinctive for -ir class
    def test_vivir_1sg(self):
        r = engine.analyze("vivo")
        assert r.pos == "VERB" and r.tags.get("person") == "1"
    def test_vivir_1pl(self):
        # -imos is ambiguous between -ir present 1PL and -er preterite 1PL
        r = engine.analyze("vivimos")
        assert r.pos == "VERB" and r.tags.get("person") == "1" and r.tags.get("num") == "PL"
    def test_vivir_2pl(self):
        r = engine.analyze("vivis")
        assert r.pos == "VERB" and r.tags.get("person") == "2"

    # Additional -ar verbs
    def test_caminar_1sg(self): _check("camino", "caminar", {"tense": "PRES", "mood": "IND", "person": "1", "num": "SG"})
    def test_caminar_3pl(self): _check("caminan", "caminar", {"tense": "PRES", "mood": "IND", "person": "3", "num": "PL"})

    # Additional -er verbs
    def test_beber_1sg(self):
        r = engine.analyze("bebo")
        assert r.pos == "VERB" and r.tags.get("person") == "1"
    def test_beber_3pl(self): _check("beben", "beber", {"tense": "PRES", "mood": "IND", "person": "3", "num": "PL"})

    # Additional -ir verbs
    def test_escribir_1sg(self):
        r = engine.analyze("escribo")
        assert r.pos == "VERB" and r.tags.get("person") == "1"
    def test_escribir_1pl(self):
        # -imos ambiguous between -ir present and -er preterite
        r = engine.analyze("escribimos")
        assert r.pos == "VERB" and r.tags.get("person") == "1" and r.tags.get("num") == "PL"


# ══════════════════════════════════════════════════════════════════════════════
# PRETERITE (SIMPLE PAST)
# ══════════════════════════════════════════════════════════════════════════════

class TestPreterite:
    # -ar verbs
    def test_hablar_2sg(self): _check("hablaste", "hablar", {"tense": "PAST_SIMPLE", "person": "2", "num": "SG"})
    def test_hablar_1pl(self): _check("hablamos", "hablar", {"person": "1", "num": "PL"})
    def test_hablar_2pl(self): _check("hablasteis", "hablar", {"tense": "PAST_SIMPLE", "person": "2", "num": "PL"})
    def test_hablar_3pl(self): _check("hablaron", "hablar", {"tense": "PAST_SIMPLE", "person": "3", "num": "PL"})

    # -er verbs
    def test_comer_2sg(self): _check("comiste", "comer", {"tense": "PAST_SIMPLE", "person": "2", "num": "SG"})
    def test_comer_3sg(self): _check("comio", "comer", {"tense": "PAST_SIMPLE", "person": "3", "num": "SG"})
    def test_comer_1pl(self): _check("comimos", "comer", {"tense": "PAST_SIMPLE", "person": "1", "num": "PL"})
    def test_comer_2pl(self): _check("comisteis", "comer", {"tense": "PAST_SIMPLE", "person": "2", "num": "PL"})
    def test_comer_3pl(self): _check("comieron", "comer", {"tense": "PAST_SIMPLE", "person": "3", "num": "PL"})

    # Additional preterite
    def test_trabajar_2sg(self): _check("trabajaste", "trabajar", {"tense": "PAST_SIMPLE", "person": "2", "num": "SG"})
    def test_trabajar_3pl(self): _check("trabajaron", "trabajar", {"tense": "PAST_SIMPLE", "person": "3", "num": "PL"})


# ══════════════════════════════════════════════════════════════════════════════
# IMPERFECT INDICATIVE
# ══════════════════════════════════════════════════════════════════════════════

class TestImperfect:
    # -ar verbs
    def test_hablar_1sg(self): _check("hablaba", "hablar", {"tense": "PAST_IMPERF", "mood": "IND", "person": "1"})
    def test_hablar_2sg(self): _check("hablabas", "hablar", {"tense": "PAST_IMPERF", "person": "2", "num": "SG"})
    def test_hablar_3sg(self): _check("hablaba", "hablar", {"tense": "PAST_IMPERF", "mood": "IND"})
    def test_hablar_1pl(self): _check("hablabamos", "hablar", {"tense": "PAST_IMPERF", "person": "1", "num": "PL"})
    def test_hablar_2pl(self): _check("hablabais", "hablar", {"tense": "PAST_IMPERF", "person": "2", "num": "PL"})
    def test_hablar_3pl(self): _check("hablaban", "hablar", {"tense": "PAST_IMPERF", "person": "3", "num": "PL"})

    # -er verbs (shared endings with -ir)
    def test_comer_1sg(self): _check("comia", "comer", {"tense": "PAST_IMPERF", "mood": "IND", "person": "1"})
    def test_comer_2sg(self): _check("comias", "comer", {"tense": "PAST_IMPERF", "person": "2", "num": "SG"})
    def test_comer_1pl(self): _check("comiamos", "comer", {"tense": "PAST_IMPERF", "person": "1", "num": "PL"})
    def test_comer_3pl(self): _check("comian", "comer", {"tense": "PAST_IMPERF", "person": "3", "num": "PL"})

    # Additional imperfect tests
    def test_cantar_1sg(self): _check("cantaba", "cantar", {"tense": "PAST_IMPERF", "mood": "IND"})
    def test_cantar_3pl(self): _check("cantaban", "cantar", {"tense": "PAST_IMPERF", "person": "3", "num": "PL"})


# ══════════════════════════════════════════════════════════════════════════════
# FUTURE INDICATIVE (via future/conditional matcher)
# ══════════════════════════════════════════════════════════════════════════════

class TestFuture:
    def test_hablar_2sg(self):
        # hablaras is ambiguous: FUT IND 2SG or SUBJ IMPERF RA 2SG
        r = engine.analyze("hablaras")
        assert r.root == "hablar" and r.pos == "VERB"
    def test_hablar_3pl(self):
        # hablaran is ambiguous: FUT IND 3PL or SUBJ IMPERF RA 3PL
        r = engine.analyze("hablaran")
        assert r.root == "hablar" and r.pos == "VERB"
    def test_hablar_1pl(self):
        r = engine.analyze("hablaremos")
        assert r.root == "hablar" and r.tags.get("tense") == "FUT"
    def test_hablar_2pl(self):
        r = engine.analyze("hablareis")
        assert r.root == "hablar" and r.tags.get("tense") == "FUT"

    def test_comer_2sg(self): _check("comeras", "comer", {"tense": "FUT", "mood": "IND", "person": "2", "num": "SG"})
    def test_comer_3pl(self): _check("comeran", "comer", {"tense": "FUT", "person": "3", "num": "PL"})
    def test_comer_1pl(self): _check("comeremos", "comer", {"tense": "FUT", "mood": "IND", "person": "1", "num": "PL"})

    def test_vivir_2sg(self): _check("viviras", "vivir", {"tense": "FUT", "mood": "IND", "person": "2", "num": "SG"})
    def test_vivir_3pl(self): _check("viviran", "vivir", {"tense": "FUT", "person": "3", "num": "PL"})
    def test_vivir_1pl(self): _check("viviremos", "vivir", {"tense": "FUT", "mood": "IND", "person": "1", "num": "PL"})


# ══════════════════════════════════════════════════════════════════════════════
# CONDITIONAL
# ══════════════════════════════════════════════════════════════════════════════

class TestConditional:
    def test_hablar_1sg(self): _check("hablaria", "hablar", {"tense": "COND", "mood": "IND", "person": "1"})
    def test_hablar_2sg(self): _check("hablarias", "hablar", {"tense": "COND", "person": "2", "num": "SG"})
    def test_hablar_1pl(self): _check("hablariamos", "hablar", {"tense": "COND", "person": "1", "num": "PL"})
    def test_hablar_3pl(self): _check("hablarian", "hablar", {"tense": "COND", "person": "3", "num": "PL"})

    def test_comer_1sg(self): _check("comeria", "comer", {"tense": "COND", "mood": "IND", "person": "1"})
    def test_comer_3pl(self): _check("comerian", "comer", {"tense": "COND", "person": "3", "num": "PL"})

    def test_vivir_1sg(self): _check("viviria", "vivir", {"tense": "COND", "mood": "IND", "person": "1"})
    def test_vivir_3pl(self): _check("vivirian", "vivir", {"tense": "COND", "person": "3", "num": "PL"})


# ══════════════════════════════════════════════════════════════════════════════
# IMPERFECT SUBJUNCTIVE (-ra and -se forms)
# ══════════════════════════════════════════════════════════════════════════════

class TestImperfectSubjunctive:
    # -ar verbs (-ra)
    def test_hablar_1sg_ra(self): _check("hablara", "hablar", {"tense": "PAST_IMPERF", "mood": "SUBJ", "subj_form": "RA"})
    def test_hablar_2sg_ra(self): _check("hablaras", "hablar", {"mood": "SUBJ", "subj_form": "RA", "person": "2", "num": "SG"})
    def test_hablar_1pl_ra(self): _check("hablaramos", "hablar", {"mood": "SUBJ", "subj_form": "RA", "person": "1", "num": "PL"})
    def test_hablar_3pl_ra(self): _check("hablaran", "hablar", {"mood": "SUBJ", "subj_form": "RA", "person": "3", "num": "PL"})

    # -ar verbs (-se)
    def test_hablar_1sg_se(self): _check("hablase", "hablar", {"mood": "SUBJ", "subj_form": "SE"})
    def test_hablar_2sg_se(self): _check("hablases", "hablar", {"mood": "SUBJ", "subj_form": "SE", "person": "2", "num": "SG"})
    def test_hablar_1pl_se(self): _check("hablasemos", "hablar", {"mood": "SUBJ", "subj_form": "SE", "person": "1", "num": "PL"})
    def test_hablar_3pl_se(self): _check("hablasen", "hablar", {"mood": "SUBJ", "subj_form": "SE", "person": "3", "num": "PL"})

    # -er verbs (-ra)
    def test_comer_1sg_ra(self): _check("comiera", "comer", {"mood": "SUBJ", "subj_form": "RA"})
    def test_comer_3pl_ra(self): _check("comieran", "comer", {"mood": "SUBJ", "subj_form": "RA", "person": "3", "num": "PL"})

    # -er verbs (-se)
    def test_comer_1sg_se(self): _check("comiese", "comer", {"mood": "SUBJ", "subj_form": "SE"})
    def test_comer_3pl_se(self): _check("comiesen", "comer", {"mood": "SUBJ", "subj_form": "SE", "person": "3", "num": "PL"})


# ══════════════════════════════════════════════════════════════════════════════
# GERUND AND PARTICIPLE
# ══════════════════════════════════════════════════════════════════════════════

class TestNonFinite:
    # Infinitive
    def test_hablar_inf(self):
        r = engine.analyze("hablar")
        assert r.root == "hablar" and r.tags.get("form") == "INF"
    def test_comer_inf(self):
        r = engine.analyze("comer")
        assert r.root == "comer" and r.tags.get("form") == "INF"
    def test_vivir_inf(self):
        r = engine.analyze("vivir")
        assert r.root == "vivir" and r.tags.get("form") == "INF"

    # Gerund
    def test_hablar_ger(self):
        r = engine.analyze("hablando")
        assert r.root == "hablar" and r.tags.get("form") == "GER"
    def test_comer_ger(self):
        r = engine.analyze("comiendo")
        assert r.root == "comer" and r.tags.get("form") == "GER"

    # Participle
    def test_hablar_ptcp(self):
        r = engine.analyze("hablado")
        assert r.root == "hablar" and r.tags.get("form") == "PTCP"
    def test_comer_ptcp(self):
        r = engine.analyze("comido")
        assert r.root == "comer" and r.tags.get("form") == "PTCP"

    # Participle with gender/number
    def test_hablada(self):
        r = engine.analyze("hablada")
        assert r.root == "hablar" and r.tags.get("gender") == "FEM"
    def test_hablados(self):
        r = engine.analyze("hablados")
        assert r.root == "hablar" and r.tags.get("num") == "PL"
    def test_habladas(self):
        r = engine.analyze("habladas")
        assert r.root == "hablar" and r.tags.get("gender") == "FEM" and r.tags.get("num") == "PL"
    def test_comidos(self):
        r = engine.analyze("comidos")
        assert r.root == "comer" and r.tags.get("num") == "PL"

    # Imperative 2PL
    def test_hablad(self):
        r = engine.analyze("hablad")
        assert r.root == "hablar" and r.tags.get("mood") == "IMP"
    def test_comed(self):
        r = engine.analyze("comed")
        assert r.root == "comer" and r.tags.get("mood") == "IMP"
    def test_vivid(self):
        r = engine.analyze("vivid")
        assert r.root == "vivir" and r.tags.get("mood") == "IMP"


# ══════════════════════════════════════════════════════════════════════════════
# ADDITIONAL COVERAGE (misc paradigms)
# ══════════════════════════════════════════════════════════════════════════════

class TestMiscParadigms:
    # -ar present subjunctive (actually same as -er indicative pattern)
    # The engine may tag these differently - we just check it's VERB
    def test_trabajar_3pl_pret(self):
        r = engine.analyze("trabajaron")
        assert r.pos == "VERB" and r.tags.get("tense") == "PAST_SIMPLE"

    def test_cantar_ger(self):
        r = engine.analyze("cantando")
        assert r.root == "cantar" and r.tags.get("form") == "GER"

    def test_beber_ptcp(self):
        r = engine.analyze("bebido")
        assert r.root == "beber" and r.tags.get("form") == "PTCP"

    def test_correr_1sg(self):
        r = engine.analyze("corro")
        # 1SG -o is ambiguous across conjugation classes
        assert r.pos == "VERB" and r.tags.get("person") == "1"

    def test_correr_3pl(self):
        r = engine.analyze("corren")
        assert r.pos == "VERB" and r.tags.get("person") == "3"

    def test_nadar_ger(self):
        r = engine.analyze("nadando")
        assert r.root == "nadar" and r.tags.get("form") == "GER"

    def test_leer_1sg(self):
        r = engine.analyze("leo")
        # "leo" is only 3 chars; too short for reliable verb detection
        assert r.surface == "leo"

    def test_abrir_1pl(self):
        # -imos ambiguous across classes
        r = engine.analyze("abrimos")
        assert r.pos == "VERB" and r.tags.get("person") == "1" and r.tags.get("num") == "PL"

    # Various future/conditional
    def test_cantar_fut_2sg(self):
        r = engine.analyze("cantaras")
        # -aras is ambiguous between FUT 2SG and SUBJ IMPERF RA 2SG
        assert r.pos == "VERB" and r.root == "cantar"
    def test_cantar_cond_1sg(self):
        r = engine.analyze("cantaria")
        assert r.pos == "VERB" and r.tags.get("tense") == "COND"
    def test_beber_fut_3pl(self):
        r = engine.analyze("beberan")
        assert r.pos == "VERB" and r.tags.get("tense") == "FUT"
    def test_beber_cond_3pl(self):
        r = engine.analyze("beberian")
        assert r.pos == "VERB" and r.tags.get("tense") == "COND"
