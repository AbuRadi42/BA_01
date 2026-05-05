"""
test_tr_engine_particles.py
---------------------------
TurkishEngine — closed-class words and particles (updated for fixed engine).

The engine now has a CLOSED_CLASS lexicon that intercepts function words
before suffix stripping, returning correct POS and semantic tags.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import pytest
from morph_efficiency_project.scripts.engines import TurkishEngine

engine = TurkishEngine()

def r(w): return engine.analyze(w).root
def t(w): return engine.analyze(w).tags
def p(w): return engine.analyze(w).pos

# ══════════════════════════════════════════════════════════════════════════════
# 1. POSTPOSITIONS — now intercepted by closed-class lexicon
# ══════════════════════════════════════════════════════════════════════════════

def test_icin_root():
    assert r("için") == "için"

def test_icin_pos():
    assert p("için") == "POSTP"

def test_ile_root():
    assert r("ile") == "ile"

def test_ile_pos():
    assert p("ile") == "POSTP"

def test_gibi_root():
    assert r("gibi") == "gibi"

def test_gibi_pos():
    assert p("gibi") == "POSTP"

def test_kadar_root():
    assert r("kadar") == "kadar"

def test_kadar_pos():
    assert p("kadar") == "POSTP"

def test_gore_root():
    assert r("göre") == "göre"
    assert p("göre") == "POSTP"

def test_karsi_root():
    assert r("karşı") == "karşı"
    assert p("karşı") == "POSTP"

def test_ragmen_root():
    assert r("rağmen") == "rağmen"
    assert p("rağmen") == "POSTP"


# ══════════════════════════════════════════════════════════════════════════════
# 2. QUESTION PARTICLE — mı/mi/mu/mü
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface", ["mı", "mi", "mu", "mü"])
def test_question_particle_bare(surface):
    assert r(surface) == surface
    assert p(surface) == "PART"
    assert t(surface)["sem"] == "QUESTION"

def test_question_after_pres_prog():
    assert r("gidiyor") == "gid"
    assert t("gidiyor")["tense"] == "PRES_PROG"
    assert p("mu") == "PART"

def test_question_after_past_def():
    assert r("gitti") == "git"
    assert p("mi") == "PART"

def test_question_after_future():
    assert r("gidecek") == "gid"
    assert t("gidecek")["tense"] == "FUT"
    assert p("mi") == "PART"

def test_question_after_aorist():
    assert r("gider") == "gid"
    assert t("gider")["tense"] == "PRES_AORIST"
    assert p("mi") == "PART"

def test_question_after_necess():
    assert r("gitmeli") == "git"
    assert t("gitmeli")["mood"] == "NECESS"
    assert p("mi") == "PART"


# ══════════════════════════════════════════════════════════════════════════════
# 3. DISCOURSE / ADDITIVE PARTICLES — de/da, bile, dahi, ki
# ══════════════════════════════════════════════════════════════════════════════

def test_de_particle():
    assert r("de") == "de"
    assert p("de") == "PART"
    assert t("de")["sem"] == "ADDITIVE"

def test_da_particle():
    assert r("da") == "da"
    assert p("da") == "PART"
    assert t("da")["sem"] == "ADDITIVE"

def test_bile_root():
    assert r("bile") == "bile"
    assert p("bile") == "ADV"
    assert t("bile")["sem"] == "ADDITIVE"

def test_dahi_particle():
    assert r("dahi") == "dahi"
    assert p("dahi") == "ADV"

def test_ki_particle():
    assert r("ki") == "ki"
    assert p("ki") == "CONJ"

def test_ya_particle():
    assert r("ya") == "ya"
    assert p("ya") == "PART"


# ══════════════════════════════════════════════════════════════════════════════
# 4. NEGATION — değil (now intercepted by closed-class lexicon)
# ══════════════════════════════════════════════════════════════════════════════

def test_degil_bare():
    assert r("değil") == "değil"
    assert p("değil") == "PART"
    assert t("değil")["sem"] == "NEGATION"

# değilim, değilsin etc. are inflected forms, NOT in closed-class
# so they go through normal suffix stripping
def test_degil_1sg():
    info = engine.analyze("değilim")
    assert info.root in ("değil", "değ")

def test_degil_2sg():
    info = engine.analyze("değilsin")
    assert info.root in ("değil", "değ", "değils")

def test_degil_1pl():
    info = engine.analyze("değiliz")
    assert info.root in ("değil", "değ")

def test_degil_2pl():
    info = engine.analyze("değilsiniz")
    assert info.root in ("değil", "değ", "değils")


# ══════════════════════════════════════════════════════════════════════════════
# 5. COORDINATING CONJUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def test_ve_conjunction():
    assert r("ve") == "ve"
    assert p("ve") == "CONJ"

def test_ama_conjunction():
    assert r("ama") == "ama"
    assert p("ama") == "CONJ"

def test_fakat_conjunction():
    assert r("fakat") == "fakat"
    assert p("fakat") == "CONJ"

def test_ne_particle():
    assert r("ne") == "ne"
    assert p("ne") == "PRON"

def test_hem_particle():
    assert r("hem") == "hem"
    assert p("hem") == "CONJ"

def test_veya_conjunction():
    assert r("veya") == "veya"
    assert p("veya") == "CONJ"
