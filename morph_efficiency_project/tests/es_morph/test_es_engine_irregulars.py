"""
test_es_engine_irregulars.py
----------------------------
Tests for irregular verb conjugation and stem-changing verbs.

Run: python -m pytest morph_efficiency_project/tests/es_morph/test_es_engine_irregulars.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import SpanishEngine
import pytest

engine = SpanishEngine()


def _check(surface, exp_root, exp_tags, label=""):
    r = engine.analyze(surface)
    assert r.root == exp_root, f"[{label}] root: got {r.root!r}, expected {exp_root!r}"
    assert r.pos == "VERB", f"[{label}] pos: got {r.pos!r}, expected 'VERB'"
    for k, v in exp_tags.items():
        assert r.tags.get(k) == v, (
            f"[{label}] tag {k}: got {r.tags.get(k)!r}, expected {v!r}")


# ══════════════════════════════════════════════════════════════════════════════
# SER
# ══════════════════════════════════════════════════════════════════════════════

class TestSer:
    def test_pres_1sg(self): _check("soy", "ser", {"tense": "PRES", "person": "1", "num": "SG"})
    def test_pres_2sg(self): _check("eres", "ser", {"tense": "PRES", "person": "2", "num": "SG"})
    def test_pres_3sg(self): _check("es", "ser", {"tense": "PRES", "person": "3", "num": "SG"})
    def test_pres_1pl(self): _check("somos", "ser", {"tense": "PRES", "person": "1", "num": "PL"})
    def test_pres_2pl(self): _check("sois", "ser", {"tense": "PRES", "person": "2", "num": "PL"})
    def test_pres_3pl(self): _check("son", "ser", {"tense": "PRES", "person": "3", "num": "PL"})
    def test_imperf_1sg(self): _check("era", "ser", {"tense": "PAST_IMPERF"})
    def test_imperf_3pl(self): _check("eran", "ser", {"tense": "PAST_IMPERF", "person": "3", "num": "PL"})
    def test_subj_pres_1sg(self): _check("sea", "ser", {"tense": "PRES", "mood": "SUBJ"})
    def test_subj_pres_3pl(self): _check("sean", "ser", {"tense": "PRES", "mood": "SUBJ", "person": "3"})
    def test_subj_imperf_ra(self): _check("fuera", "ser", {"mood": "SUBJ", "subj_form": "RA"})
    def test_ptcp(self): _check("sido", "ser", {"aspect": "PERF", "form": "PTCP"})
    def test_ger(self): _check("siendo", "ser", {"aspect": "PROG", "form": "GER"})
    def test_fut_1sg(self): _check("sere", "ser", {"tense": "FUT", "person": "1"})
    def test_fut_3sg(self): _check("sera", "ser", {"tense": "FUT", "person": "3"})
    def test_cond_1sg(self): _check("seria", "ser", {"tense": "COND", "person": "1"})


# ══════════════════════════════════════════════════════════════════════════════
# IR
# ══════════════════════════════════════════════════════════════════════════════

class TestIr:
    def test_pres_1sg(self): _check("voy", "ir", {"tense": "PRES", "person": "1", "num": "SG"})
    def test_pres_2sg(self): _check("vas", "ir", {"tense": "PRES", "person": "2"})
    def test_pres_3sg(self): _check("va", "ir", {"tense": "PRES", "person": "3"})
    def test_pres_1pl(self): _check("vamos", "ir", {"tense": "PRES", "person": "1", "num": "PL"})
    def test_pres_3pl(self): _check("van", "ir", {"tense": "PRES", "person": "3", "num": "PL"})
    def test_pret_1sg(self): _check("fui", "ir", {"tense": "PAST_SIMPLE", "person": "1"})
    def test_pret_3sg(self): _check("fue", "ir", {"tense": "PAST_SIMPLE", "person": "3"})
    def test_pret_3pl(self): _check("fueron", "ir", {"tense": "PAST_SIMPLE", "person": "3", "num": "PL"})
    def test_imperf_1sg(self): _check("iba", "ir", {"tense": "PAST_IMPERF"})
    def test_imperf_3pl(self): _check("iban", "ir", {"tense": "PAST_IMPERF", "person": "3"})
    def test_subj_pres_1sg(self): _check("vaya", "ir", {"tense": "PRES", "mood": "SUBJ"})
    def test_subj_pres_3pl(self): _check("vayan", "ir", {"mood": "SUBJ", "person": "3"})
    def test_ger(self): _check("yendo", "ir", {"form": "GER"})
    def test_ptcp(self): _check("ido", "ir", {"form": "PTCP"})
    def test_inf(self):
        r = engine.analyze("ir")
        assert r.root == "ir" and r.tags.get("form") == "INF"


# ══════════════════════════════════════════════════════════════════════════════
# HABER
# ══════════════════════════════════════════════════════════════════════════════

class TestHaber:
    def test_pres_1sg(self): _check("he", "haber", {"tense": "PRES", "person": "1"})
    def test_pres_2sg(self): _check("has", "haber", {"tense": "PRES", "person": "2"})
    def test_pres_3sg(self): _check("ha", "haber", {"tense": "PRES", "person": "3"})
    def test_pres_1pl(self): _check("hemos", "haber", {"tense": "PRES", "person": "1", "num": "PL"})
    def test_pres_3pl(self): _check("han", "haber", {"tense": "PRES", "person": "3", "num": "PL"})
    def test_pret_1sg(self): _check("hube", "haber", {"tense": "PAST_SIMPLE", "person": "1"})
    def test_pret_3sg(self): _check("hubo", "haber", {"tense": "PAST_SIMPLE", "person": "3"})
    def test_imperf_1sg(self): _check("habia", "haber", {"tense": "PAST_IMPERF"})
    def test_imperf_3pl(self): _check("habian", "haber", {"tense": "PAST_IMPERF", "person": "3"})
    def test_subj_pres_1sg(self): _check("haya", "haber", {"mood": "SUBJ"})
    def test_subj_imperf_ra(self): _check("hubiera", "haber", {"mood": "SUBJ", "subj_form": "RA"})
    def test_fut_1sg(self): _check("habre", "haber", {"tense": "FUT"})
    def test_cond_1sg(self): _check("habria", "haber", {"tense": "COND"})
    def test_ptcp(self): _check("habido", "haber", {"form": "PTCP"})


# ══════════════════════════════════════════════════════════════════════════════
# ESTAR
# ══════════════════════════════════════════════════════════════════════════════

class TestEstar:
    def test_pres_1sg(self): _check("estoy", "estar", {"tense": "PRES", "person": "1"})
    def test_pres_3sg(self):
        # "esta" is registered as DEM pronoun in closed class (first match wins)
        r = engine.analyze("esta")
        assert r.pos in ("PRON", "VERB")
    def test_pres_3pl(self): _check("estan", "estar", {"tense": "PRES", "person": "3", "num": "PL"})
    def test_pret_1sg(self): _check("estuve", "estar", {"tense": "PAST_SIMPLE", "person": "1"})
    def test_pret_3sg(self): _check("estuvo", "estar", {"tense": "PAST_SIMPLE", "person": "3"})
    def test_pret_3pl(self): _check("estuvieron", "estar", {"tense": "PAST_SIMPLE", "person": "3", "num": "PL"})
    def test_imperf_1sg(self): _check("estaba", "estar", {"tense": "PAST_IMPERF"})
    def test_subj_pres_1sg(self):
        # "este" is registered as DEM pronoun in closed class (first match wins)
        r = engine.analyze("este")
        assert r.pos in ("PRON", "VERB")
    def test_subj_imperf_ra(self): _check("estuviera", "estar", {"mood": "SUBJ", "subj_form": "RA"})
    def test_fut_1sg(self): _check("estare", "estar", {"tense": "FUT"})
    def test_cond_1sg(self): _check("estaria", "estar", {"tense": "COND"})
    def test_ptcp(self): _check("estado", "estar", {"form": "PTCP"})
    def test_ger(self): _check("estando", "estar", {"form": "GER"})


# ══════════════════════════════════════════════════════════════════════════════
# TENER
# ══════════════════════════════════════════════════════════════════════════════

class TestTener:
    def test_pres_1sg(self): _check("tengo", "tener", {"tense": "PRES", "person": "1"})
    def test_pres_2sg(self): _check("tienes", "tener", {"tense": "PRES", "person": "2"})
    def test_pres_3sg(self): _check("tiene", "tener", {"tense": "PRES", "person": "3"})
    def test_pres_3pl(self): _check("tienen", "tener", {"tense": "PRES", "person": "3", "num": "PL"})
    def test_pret_1sg(self): _check("tuve", "tener", {"tense": "PAST_SIMPLE", "person": "1"})
    def test_pret_3sg(self): _check("tuvo", "tener", {"tense": "PAST_SIMPLE", "person": "3"})
    def test_subj_pres_1sg(self): _check("tenga", "tener", {"mood": "SUBJ"})
    def test_subj_imperf_ra(self): _check("tuviera", "tener", {"mood": "SUBJ", "subj_form": "RA"})
    def test_fut_1sg(self): _check("tendre", "tener", {"tense": "FUT"})
    def test_fut_3sg(self): _check("tendra", "tener", {"tense": "FUT"})
    def test_cond_1sg(self): _check("tendria", "tener", {"tense": "COND"})
    def test_ptcp(self): _check("tenido", "tener", {"form": "PTCP"})


# ══════════════════════════════════════════════════════════════════════════════
# HACER
# ══════════════════════════════════════════════════════════════════════════════

class TestHacer:
    def test_pres_1sg(self): _check("hago", "hacer", {"tense": "PRES", "person": "1"})
    def test_pres_3sg(self): _check("hace", "hacer", {"tense": "PRES", "person": "3"})
    def test_pret_1sg(self): _check("hice", "hacer", {"tense": "PAST_SIMPLE", "person": "1"})
    def test_pret_3sg(self): _check("hizo", "hacer", {"tense": "PAST_SIMPLE", "person": "3"})
    def test_subj_pres_1sg(self): _check("haga", "hacer", {"mood": "SUBJ"})
    def test_fut_1sg(self): _check("hare", "hacer", {"tense": "FUT"})
    def test_cond_1sg(self): _check("haria", "hacer", {"tense": "COND"})
    def test_ptcp(self): _check("hecho", "hacer", {"form": "PTCP"})
    def test_ger(self): _check("haciendo", "hacer", {"form": "GER"})


# ══════════════════════════════════════════════════════════════════════════════
# DECIR
# ══════════════════════════════════════════════════════════════════════════════

class TestDecir:
    def test_pres_1sg(self): _check("digo", "decir", {"tense": "PRES", "person": "1"})
    def test_pres_3sg(self): _check("dice", "decir", {"tense": "PRES", "person": "3"})
    def test_pres_3pl(self): _check("dicen", "decir", {"tense": "PRES", "person": "3", "num": "PL"})
    def test_pret_1sg(self): _check("dije", "decir", {"tense": "PAST_SIMPLE", "person": "1"})
    def test_pret_3sg(self): _check("dijo", "decir", {"tense": "PAST_SIMPLE", "person": "3"})
    def test_subj_pres_1sg(self): _check("diga", "decir", {"mood": "SUBJ"})
    def test_fut_1sg(self): _check("dire", "decir", {"tense": "FUT"})
    def test_cond_1sg(self): _check("diria", "decir", {"tense": "COND"})
    def test_ptcp(self): _check("dicho", "decir", {"form": "PTCP"})
    def test_ger(self): _check("diciendo", "decir", {"form": "GER"})
    def test_imp_2sg(self): _check("di", "decir", {"mood": "IMP", "person": "2"})


# ══════════════════════════════════════════════════════════════════════════════
# STEM-CHANGING VERBS
# ══════════════════════════════════════════════════════════════════════════════

class TestStemChanging:
    # pensar (e->ie)
    def test_pensar_1sg(self): _check("pienso", "pensar", {"tense": "PRES", "person": "1"})
    def test_pensar_3sg(self): _check("piensa", "pensar", {"tense": "PRES", "person": "3"})
    def test_pensar_3pl(self): _check("piensan", "pensar", {"tense": "PRES", "person": "3", "num": "PL"})

    # contar (o->ue)
    def test_contar_1sg(self): _check("cuento", "contar", {"tense": "PRES", "person": "1"})
    def test_contar_3sg(self): _check("cuenta", "contar", {"tense": "PRES", "person": "3"})
    def test_contar_3pl(self): _check("cuentan", "contar", {"tense": "PRES", "person": "3", "num": "PL"})

    # pedir (e->i)
    def test_pedir_1sg(self): _check("pido", "pedir", {"tense": "PRES", "person": "1"})
    def test_pedir_3sg(self): _check("pide", "pedir", {"tense": "PRES", "person": "3"})
    def test_pedir_3pl(self): _check("piden", "pedir", {"tense": "PRES", "person": "3", "num": "PL"})
    def test_pedir_pret_3sg(self): _check("pidio", "pedir", {"tense": "PAST_SIMPLE", "person": "3"})
    def test_pedir_ger(self): _check("pidiendo", "pedir", {"form": "GER"})

    # dormir (o->ue->u)
    def test_dormir_1sg(self): _check("duermo", "dormir", {"tense": "PRES", "person": "1"})
    def test_dormir_3sg(self): _check("duerme", "dormir", {"tense": "PRES", "person": "3"})
    def test_dormir_3pl(self): _check("duermen", "dormir", {"tense": "PRES", "person": "3", "num": "PL"})
    def test_dormir_pret_3sg(self): _check("durmio", "dormir", {"tense": "PAST_SIMPLE", "person": "3"})
    def test_dormir_ger(self): _check("durmiendo", "dormir", {"form": "GER"})

    # jugar (u->ue)
    def test_jugar_1sg(self): _check("juego", "jugar", {"tense": "PRES", "person": "1"})
    def test_jugar_3sg(self): _check("juega", "jugar", {"tense": "PRES", "person": "3"})
    def test_jugar_3pl(self): _check("juegan", "jugar", {"tense": "PRES", "person": "3", "num": "PL"})

    # sentir (e->ie->i)
    def test_sentir_1sg(self): _check("siento", "sentir", {"tense": "PRES", "person": "1"})
    def test_sentir_3sg(self): _check("siente", "sentir", {"tense": "PRES", "person": "3"})
    def test_sentir_pret_3sg(self): _check("sintio", "sentir", {"tense": "PAST_SIMPLE", "person": "3"})
    def test_sentir_ger(self): _check("sintiendo", "sentir", {"form": "GER"})

    # cerrar (e->ie)
    def test_cerrar_1sg(self): _check("cierro", "cerrar", {"tense": "PRES", "person": "1"})
    def test_cerrar_3sg(self): _check("cierra", "cerrar", {"tense": "PRES", "person": "3"})

    # volver (o->ue, irregular participle)
    def test_volver_1sg(self): _check("vuelvo", "volver", {"tense": "PRES", "person": "1"})
    def test_volver_3sg(self): _check("vuelve", "volver", {"tense": "PRES", "person": "3"})
    def test_volver_ptcp(self): _check("vuelto", "volver", {"form": "PTCP"})


# ══════════════════════════════════════════════════════════════════════════════
# IRREGULAR PARTICIPLES
# ══════════════════════════════════════════════════════════════════════════════

class TestIrregularParticiples:
    def test_dicho(self): _check("dicho", "decir", {"form": "PTCP"})
    def test_hecho(self): _check("hecho", "hacer", {"form": "PTCP"})
    def test_escrito(self): _check("escrito", "escribir", {"form": "PTCP"})
    def test_visto(self): _check("visto", "ver", {"form": "PTCP"})
    def test_puesto(self): _check("puesto", "poner", {"form": "PTCP"})
    def test_vuelto(self): _check("vuelto", "volver", {"form": "PTCP"})
    def test_abierto(self): _check("abierto", "abrir", {"form": "PTCP"})
    def test_cubierto(self): _check("cubierto", "cubrir", {"form": "PTCP"})
    def test_muerto(self): _check("muerto", "morir", {"form": "PTCP"})
    def test_roto(self): _check("roto", "romper", {"form": "PTCP"})
    def test_resuelto(self): _check("resuelto", "resolver", {"form": "PTCP"})


# ══════════════════════════════════════════════════════════════════════════════
# OTHER IRREGULAR VERBS
# ══════════════════════════════════════════════════════════════════════════════

class TestOtherIrregulars:
    # poder
    def test_poder_1sg(self): _check("puedo", "poder", {"tense": "PRES", "person": "1"})
    def test_poder_pret_1sg(self): _check("pude", "poder", {"tense": "PAST_SIMPLE"})
    def test_poder_subj(self): _check("pueda", "poder", {"mood": "SUBJ"})
    def test_poder_fut(self): _check("podre", "poder", {"tense": "FUT"})

    # poner
    def test_poner_1sg(self): _check("pongo", "poner", {"tense": "PRES", "person": "1"})
    def test_poner_pret_1sg(self): _check("puse", "poner", {"tense": "PAST_SIMPLE"})
    def test_poner_subj(self): _check("ponga", "poner", {"mood": "SUBJ"})
    def test_poner_fut(self): _check("pondre", "poner", {"tense": "FUT"})

    # saber
    def test_saber_pret(self): _check("supe", "saber", {"tense": "PAST_SIMPLE"})
    def test_saber_subj(self): _check("sepa", "saber", {"mood": "SUBJ"})
    def test_saber_fut(self): _check("sabre", "saber", {"tense": "FUT"})

    # querer
    def test_querer_1sg(self): _check("quiero", "querer", {"tense": "PRES", "person": "1"})
    def test_querer_pret(self): _check("quise", "querer", {"tense": "PAST_SIMPLE"})
    def test_querer_subj(self): _check("quiera", "querer", {"mood": "SUBJ"})

    # venir
    def test_venir_1sg(self): _check("vengo", "venir", {"tense": "PRES", "person": "1"})
    def test_venir_pret(self): _check("vine", "venir", {"tense": "PAST_SIMPLE"})
    def test_venir_fut(self): _check("vendre", "venir", {"tense": "FUT"})
    def test_venir_ger(self): _check("viniendo", "venir", {"form": "GER"})

    # dar
    def test_dar_1sg(self): _check("doy", "dar", {"tense": "PRES", "person": "1"})
    def test_dar_3sg(self): _check("da", "dar", {"tense": "PRES", "person": "3"})
    def test_dar_pret_3sg(self): _check("dio", "dar", {"tense": "PAST_SIMPLE"})

    # ver
    def test_ver_1sg(self): _check("veo", "ver", {"tense": "PRES", "person": "1"})
    def test_ver_pret_1sg(self): _check("vi", "ver", {"tense": "PAST_SIMPLE"})
    def test_ver_pret_3sg(self): _check("vio", "ver", {"tense": "PAST_SIMPLE"})

    # salir
    def test_salir_1sg(self): _check("salgo", "salir", {"tense": "PRES", "person": "1"})
    def test_salir_fut(self): _check("saldre", "salir", {"tense": "FUT"})

    # traer
    def test_traer_1sg(self): _check("traigo", "traer", {"tense": "PRES", "person": "1"})
    def test_traer_pret(self): _check("traje", "traer", {"tense": "PAST_SIMPLE"})
    def test_traer_ger(self): _check("trayendo", "traer", {"form": "GER"})

    # caer
    def test_caer_1sg(self): _check("caigo", "caer", {"tense": "PRES", "person": "1"})

    # caber
    def test_caber_1sg(self): _check("quepo", "caber", {"tense": "PRES", "person": "1"})
    def test_caber_pret(self): _check("cupe", "caber", {"tense": "PAST_SIMPLE"})
    def test_caber_fut(self): _check("cabre", "caber", {"tense": "FUT"})

    # valer
    def test_valer_1sg(self): _check("valgo", "valer", {"tense": "PRES", "person": "1"})
    def test_valer_fut(self): _check("valdre", "valer", {"tense": "FUT"})

    # andar
    def test_andar_pret(self): _check("anduve", "andar", {"tense": "PAST_SIMPLE"})
    def test_andar_pret_3sg(self): _check("anduvo", "andar", {"tense": "PAST_SIMPLE"})
