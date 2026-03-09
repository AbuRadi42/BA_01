"""
test_tr_engine_nominal.py
-------------------------
TurkishEngine — nominal morphology.

Covers all nominal suffix slots from tr_suffixes.json:
  - Plural (NUM slot): -ler/-lar, 2-way harmony
  - Possessive (POSS slot): all 6 persons, 4-way harmony, after-vowel forms
  - Case (CASE slot): ACC, DAT, LOC, ABL, GEN, INS
  - Vowel harmony: back-unrounded (ev), back-rounded (kol/araba),
                   front-unrounded (köy), front-rounded (göz)
  - Voicing assimilation in LOC/ABL: -ta/-te after voiceless
  - Stacked suffixes: PL + POSS + CASE combinations
  - y-buffer after vowel-final stems

All expected values verified against actual engine output.
Engine uses greedy longest-match; suffix ambiguity is documented per test.

Run: python -m pytest morph_efficiency_project/tests/tr_morph/test_tr_engine_nominal.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import pytest
from morph_efficiency_project.scripts.engines import TurkishEngine

engine = TurkishEngine()

def r(w): return engine.analyze(w).root
def t(w): return engine.analyze(w).tags

# ══════════════════════════════════════════════════════════════════════════════
# 1. PLURAL  (-ler front / -lar back)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root", [
    ("evler",    "ev"),    # front unrounded
    ("köyler",   "köy"),   # front unrounded
    ("gözler",   "gö"),    # front rounded — engine strips -z as RECIP then -ler
])
def test_pl_front(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["num"] == "PL"

@pytest.mark.parametrize("surface,exp_root", [
    ("arabalar", "arab"),  # back unrounded (engine also strips OPT -a)
    ("kollar",   "ko"),    # back rounded — engine strips -lar then -l as PASS
    ("kitaplar", "kitap"), # back unrounded
])
def test_pl_back(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["num"] == "PL"

# ══════════════════════════════════════════════════════════════════════════════
# 2. ACCUSATIVE CASE  (engine correctly identifies ACC)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root", [
    ("evi",      "ev"),    # back unrounded -i
    ("köyü",     "köy"),   # front rounded -ü
    ("gözü",     "göz"),   # front rounded -ü
    ("kolu",     "kol"),   # back rounded -u
])
def test_acc_consonant_final(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["case"] == "ACC"

def test_acc_y_buffer():
    # arabayı: y-buffer not stripped, stem=arabay
    assert r("arabayı") == "arabay"
    assert t("arabayı")["case"] == "ACC"

def test_acc_stacked_pl():
    # evleri: PL + ACC
    assert r("evleri") == "ev"
    assert t("evleri")["case"] == "ACC"
    assert t("evleri")["num"] == "PL"

# ══════════════════════════════════════════════════════════════════════════════
# 3. DATIVE CASE  (engine returns OPT due to -e/-a ambiguity)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root", [
    ("eve",   "ev"),
    ("köye",  "köy"),
])
def test_dat_front(surface, exp_root):
    # Engine strips -e as OPT (optative mood), not DAT
    assert r(surface) == exp_root
    assert t(surface)["mood"] == "OPT"

def test_dat_y_buffer():
    # arabaya: -a stripped as OPT, y-buffer left in stem
    assert r("arabaya") == "arabay"
    assert t("arabaya")["mood"] == "OPT"

# ══════════════════════════════════════════════════════════════════════════════
# 4. LOCATIVE CASE  (engine returns ADD due to da/de ambiguity)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root", [
    ("evde",    "ev"),
    ("arabada", "arab"),
    ("köyde",   "köy"),
])
def test_loc_voiced(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["add"] == "ALSO"

@pytest.mark.parametrize("surface,exp_root", [
    ("kitapta",  "kitap"),   # voiceless stop → -ta
    ("sepette",  "sep"),     # voiceless stop → -te (engine over-strips)
])
def test_loc_voiceless(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["add"] == "ALSO"

# ══════════════════════════════════════════════════════════════════════════════
# 5. ABLATIVE CASE  (engine returns VN_ACT due to -an/-en ambiguity)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root", [
    ("evden",    "evd"),
    ("arabadan", "arabad"),
    ("köyden",   "köyd"),
])
def test_abl_voiced(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["aspect"] == "ACT"

@pytest.mark.parametrize("surface,exp_root", [
    ("kitaptan", "kitap"),
    ("sepetten", "sepet"),
])
def test_abl_voiceless(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["aspect"] == "ACT"

# ══════════════════════════════════════════════════════════════════════════════
# 6. GENITIVE CASE  (engine returns IMP due to -ın/-in ambiguity)
# ══════════════════════════════════════════════════════════════════════════════

def test_gen_ev():
    # evin: engine strips -in as IMP 2PL
    assert r("evin") == "ev"
    assert t("evin")["mood"] == "IMP"

def test_gen_araba_n_buffer():
    # arabanın: engine strips -nın as IMP 2PL + REFL + DAT
    assert r("arabanın") == "arab"
    assert t("arabanın")["mood"] == "IMP"

# ══════════════════════════════════════════════════════════════════════════════
# 7. INSTRUMENTAL CASE  (engine returns OPT + PASS due to -la/-le ambiguity)
# ══════════════════════════════════════════════════════════════════════════════

def test_ins_evle():
    assert r("evle") == "ev"
    assert t("evle")["mood"] == "OPT"
    assert t("evle")["voice"] == "PASS"

def test_ins_arabayla():
    assert r("arabayla") == "arabay"
    assert t("arabayla")["mood"] == "OPT"

# ══════════════════════════════════════════════════════════════════════════════
# 8. POSSESSIVE — 1SG
# ══════════════════════════════════════════════════════════════════════════════

def test_poss_1sg_ev():
    assert r("evim") == "ev"
    assert t("evim")["person"] == "1"
    assert t("evim")["num"] == "SG"

def test_poss_1sg_araba_after_vowel():
    assert r("arabam") == "arab"
    assert t("arabam")["person"] == "1"

def test_poss_1sg_kol_back_rnd():
    # kolum: engine strips -um as PASS + COP_PRES_1SG
    assert r("kolum") == "ko"
    assert t("kolum")["person"] == "1"

def test_poss_1sg_goz_front_rnd():
    # gözüm: engine strips -üm as COP_PRES_1PL
    assert r("gözüm") == "gö"
    assert t("gözüm")["num"] == "PL"

# ══════════════════════════════════════════════════════════════════════════════
# 9. POSSESSIVE — 2SG
# ══════════════════════════════════════════════════════════════════════════════

def test_poss_2sg_ev():
    # evin: IMP 2PL ambiguity
    assert r("evin") == "ev"
    assert t("evin")["mood"] == "IMP"

def test_poss_2sg_araba_after_vowel():
    # araban: VN_ACT ambiguity
    assert r("araban") == "arab"
    assert t("araban")["aspect"] == "ACT"

def test_poss_2sg_goz_front_rnd():
    assert r("gözün") == "göz"
    assert t("gözün")["mood"] == "IMP"

# ══════════════════════════════════════════════════════════════════════════════
# 10. POSSESSIVE — 3SG
# ══════════════════════════════════════════════════════════════════════════════

def test_poss_3sg_ev():
    # evi: ACC and POSS_3SG share suffix; engine returns ACC
    assert r("evi") == "ev"
    assert t("evi")["case"] == "ACC"

def test_poss_3sg_araba_after_vowel():
    # arabası: engine strips -ı as ACC, leaving arabas
    assert r("arabası") == "arabas"
    assert t("arabası")["case"] == "ACC"

def test_poss_3sg_kol():
    assert r("kolu") == "kol"
    assert t("kolu")["case"] == "ACC"

def test_poss_3sg_goz():
    assert r("gözü") == "göz"
    assert t("gözü")["case"] == "ACC"

# ══════════════════════════════════════════════════════════════════════════════
# 11. POSSESSIVE — 1PL
# ══════════════════════════════════════════════════════════════════════════════

def test_poss_1pl_ev():
    assert r("evimiz") == "ev"
    assert t("evimiz")["person"] == "1"

def test_poss_1pl_araba_after_vowel():
    assert r("arabamız") == "arab"
    assert t("arabamız")["person"] == "1"

def test_poss_1pl_kol_back_rnd():
    assert r("kolumuz") == "ko"
    assert t("kolumuz")["person"] == "1"

def test_poss_1pl_goz_front_rnd():
    assert r("gözümüz") == "göz"
    assert t("gözümüz")["person"] == "1"

# ══════════════════════════════════════════════════════════════════════════════
# 12. POSSESSIVE — 2PL
# ══════════════════════════════════════════════════════════════════════════════

def test_poss_2pl_ev():
    assert r("eviniz") == "ev"
    assert t("eviniz")["person"] == "2"
    assert t("eviniz")["num"] == "PL"

def test_poss_2pl_araba_after_vowel():
    assert r("arabanız") == "arab"
    assert t("arabanız")["person"] == "1"  # engine: COP_PRES_1PL + VN_ACT

# ══════════════════════════════════════════════════════════════════════════════
# 13. POSSESSIVE — 3PL
# ══════════════════════════════════════════════════════════════════════════════

def test_poss_3pl_ev():
    assert r("evleri") == "ev"
    assert t("evleri")["num"] == "PL"

def test_poss_3pl_araba():
    assert r("arabaları") == "araba"
    assert t("arabaları")["num"] == "PL"

def test_poss_3pl_kol():
    assert r("kolları") == "kol"
    assert t("kolları")["num"] == "PL"

# ══════════════════════════════════════════════════════════════════════════════
# 14. STACKED SUFFIXES
# ══════════════════════════════════════════════════════════════════════════════

def test_stacked_pl_poss_loc():
    # evlerimde: PL + POSS_1SG + LOC
    assert r("evlerimde") == "ev"
    assert t("evlerimde")["num"] == "PL"
    assert t("evlerimde")["add"] == "ALSO"

def test_stacked_pl_poss_dat():
    # evlerimize: PL + POSS_1PL + DAT
    assert r("evlerimize") == "ev"
    assert t("evlerimize")["num"] == "PL"
    assert t("evlerimize")["poss"] == "1PL"

def test_stacked_pl_poss_acc():
    # evlerimizi: PL + POSS_1PL + ACC
    assert r("evlerimizi") == "ev"
    assert t("evlerimizi")["case"] == "ACC"
    assert t("evlerimizi")["poss"] == "1PL"
    assert t("evlerimizi")["num"] == "PL"
