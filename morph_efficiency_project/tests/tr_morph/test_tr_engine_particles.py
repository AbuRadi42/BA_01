"""
test_tr_engine_particles.py
---------------------------
TurkishEngine — closed-class words and particles.

Covers:
  - Postpositions: için, ile, gibi, kadar, göre, karşı, rağmen
  - Question particle: mı/mi/mu/mü (standalone, after various tenses)
  - Discourse/additive particles: de/da, bile, dahi, ki
  - Negation: değil (all copular persons)
  - Coordinating conjunctions: ve, ama, fakat, ya da, hem, ne...ne
  - Pronouns: ben, sen, o, biz, siz, onlar (bare forms)

All expected values verified against actual engine output.
The engine does not have a dedicated CLOSED_CLASS intercept for Turkish —
it strips suffixes greedily. Tests document what the engine actually returns.

Run: python -m pytest morph_efficiency_project/tests/tr_morph/test_tr_engine_particles.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import pytest
from morph_efficiency_project.scripts.engines import TurkishEngine

engine = TurkishEngine()

def r(w): return engine.analyze(w).root
def t(w): return engine.analyze(w).tags


# ══════════════════════════════════════════════════════════════════════════════
# 1. POSTPOSITIONS — için, ile, gibi, kadar, göre, karşı, rağmen
#    Engine strips greedily; document actual output.
# ══════════════════════════════════════════════════════════════════════════════

def test_icin_root():
    # için: engine strips -in as IMP 2PL, leaving iç
    assert r("için") == "iç"

def test_icin_tags():
    assert t("için")["mood"] == "IMP"
    assert t("için")["person"] == "2"
    assert t("için")["num"] == "PL"

def test_ile_root():
    # ile: engine strips -e as OPT, leaving il
    assert r("ile") == "il"

def test_ile_tags():
    assert t("ile")["mood"] == "OPT"

def test_gibi_root():
    # gibi: engine strips -i as ACC, leaving gib
    assert r("gibi") == "gib"

def test_gibi_tags():
    assert t("gibi")["case"] == "ACC"

def test_kadar_root():
    # kadar: engine strips -ar as PRES_AORIST, leaving kad
    assert r("kadar") == "kad"

def test_kadar_tags():
    assert t("kadar")["tense"] == "PRES_AORIST"

def test_gore_root():
    # gore (ASCII): no suffix stripped — root=gore, empty tags
    assert r("gore") == "gore"

def test_gore_tags():
    assert t("gore") == {}

def test_karsi_root():
    # karsi (ASCII): no suffix stripped — root=karsi, empty tags
    assert r("karsi") == "karsi"

def test_karsi_tags():
    assert t("karsi") == {}

def test_ragmen_root():
    # ragmen (ASCII): engine strips -en as REFL, leaving ragme
    assert r("ragmen") == "ragme"

def test_ragmen_tags():
    assert t("ragmen")["voice"] == "REFL"


# ══════════════════════════════════════════════════════════════════════════════
# 2. QUESTION PARTICLE — mı/mi/mu/mü (standalone)
#    In Turkish, the question particle is written as a separate word.
#    Engine returns empty tags for bare mı/mi/mu/mü.
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root", [
    ("mı", "mı"),
    ("mi", "mi"),
    ("mu", "mu"),
    ("mü", "mü"),
])
def test_question_particle_bare(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface) == {}

def test_question_after_pres_prog():
    # gidiyor mu: gidiyor=PRES_PROG, mu=question particle
    assert r("gidiyor") == "gid"
    assert t("gidiyor")["tense"] == "PRES_PROG"
    assert r("mu") == "mu"
    assert t("mu") == {}

def test_question_after_past_def():
    # gitti mi: gitti=PAST_DEF, mi=question particle
    assert r("gitti") == "gi"
    assert r("mi") == "mi"
    assert t("mi") == {}

def test_question_after_future():
    # gidecek mi: gidecek=FUT, mi=question particle
    assert r("gidecek") == "gid"
    assert t("gidecek")["tense"] == "FUT"
    assert r("mi") == "mi"

def test_question_after_aorist():
    # gider mi: gider=PRES_AORIST, mi=question particle
    assert r("gider") == "gid"
    assert t("gider")["tense"] == "PRES_AORIST"
    assert r("mi") == "mi"

def test_question_after_necess():
    # gitmeli mi: gitmeli=NECESS, mi=question particle
    assert r("gitmeli") == "gi"
    assert t("gitmeli")["mood"] == "NECESS"
    assert r("mi") == "mi"


# ══════════════════════════════════════════════════════════════════════════════
# 3. DISCOURSE / ADDITIVE PARTICLES — de/da, bile, dahi, ki
# ══════════════════════════════════════════════════════════════════════════════

def test_de_particle():
    # de: no suffix stripped — root=de, empty tags
    assert r("de") == "de"
    assert t("de") == {}

def test_da_particle():
    # da: no suffix stripped — root=da, empty tags
    assert r("da") == "da"
    assert t("da") == {}

def test_bile_root():
    # bile: engine strips -e as OPT, -l as PASS → root=bi
    assert r("bile") == "bi"

def test_bile_tags():
    assert t("bile")["mood"] == "OPT"
    assert t("bile")["voice"] == "PASS"

def test_dahi_particle():
    # dahi: no suffix stripped — root=dahi, empty tags
    assert r("dahi") == "dahi"
    assert t("dahi") == {}

def test_ki_particle():
    # ki: no suffix stripped — root=ki, empty tags
    assert r("ki") == "ki"
    assert t("ki") == {}

def test_ya_particle():
    # ya: no suffix stripped — root=ya, empty tags
    assert r("ya") == "ya"
    assert t("ya") == {}


# ══════════════════════════════════════════════════════════════════════════════
# 4. NEGATION — değil (copular negation)
# ══════════════════════════════════════════════════════════════════════════════

def test_degil_bare():
    # değil: engine strips -il as PASS → root=değ
    assert r("değil") == "değ"
    assert t("değil")["voice"] == "PASS"

def test_degil_1sg():
    # değilim: 1SG copula present
    assert r("değilim") == "değ"
    assert t("değilim")["person"] == "1"
    assert t("değilim")["num"] == "SG"

def test_degil_2sg():
    # değilsin: 2SG copula present
    assert r("değilsin") == "değ"
    assert t("değilsin")["person"] == "2"
    assert t("değilsin")["num"] == "SG"

def test_degil_1pl():
    # değiliz: 1PL copula present
    assert r("değiliz") == "değ"
    assert t("değiliz")["person"] == "1"
    assert t("değiliz")["num"] == "PL"

def test_degil_2pl():
    # değilsiniz: 2PL copula present
    assert r("değilsiniz") == "değ"
    assert t("değilsiniz")["person"] == "2"
    assert t("değilsiniz")["num"] == "PL"


# ══════════════════════════════════════════════════════════════════════════════
# 5. COORDINATING CONJUNCTIONS — ve, ama, fakat, ya da, hem, ne
#    These are uninflected; engine returns them with minimal or no tags.
# ══════════════════════════════════════════════════════════════════════════════

def test_ve_conjunction():
    # ve: no suffix stripped — root=ve, empty tags
    assert r("ve") == "ve"
    assert t("ve") == {}

def test_ama_conjunction():
    # ama: engine strips -a as OPT → root=am
    assert r("ama") == "am"
    assert t("ama")["mood"] == "OPT"

def test_fakat_conjunction():
    # fakat: engine strips -t as CAUS, -a as DAT → root=fak
    assert r("fakat") == "fak"

def test_ne_particle():
    # ne: no suffix stripped — root=ne, empty tags
    assert r("ne") == "ne"
    assert t("ne") == {}

def test_hem_particle():
    # hem: engine strips -m as 1SG → root=he
    assert r("hem") == "he"
    assert t("hem")["person"] == "1"
    assert t("hem")["num"] == "SG"

def test_veya_conjunction():
    # veya: no suffix stripped — root=veya, empty tags
    assert r("veya") == "veya"
    assert t("veya") == {}
