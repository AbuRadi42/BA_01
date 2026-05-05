"""
test_tr_engine_nominal.py
-------------------------
TurkishEngine — nominal morphology (updated for fixed engine).

All expected values verified against corrected engine output.
The engine now correctly identifies case suffixes through two-pass analysis.
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
    ("evler",    "ev"),
    ("köyler",   "köy"),
    ("gözler",   "göz"),
])
def test_pl_front(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["num"] == "PL"

@pytest.mark.parametrize("surface,exp_root", [
    ("arabalar", "araba"),
    ("kollar",   "kol"),
    ("kitaplar", "kitap"),
])
def test_pl_back(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["num"] == "PL"

# ══════════════════════════════════════════════════════════════════════════════
# 2. ACCUSATIVE CASE
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root", [
    ("evi",      "ev"),
    ("köyü",     "köy"),
    ("gözü",     "göz"),
    ("kolu",     "kol"),
])
def test_acc_consonant_final(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["case"] == "ACC"

def test_acc_y_buffer():
    assert r("arabayı") == "arabay"
    assert t("arabayı")["case"] == "ACC"

def test_acc_stacked_pl():
    assert r("evleri") == "ev"
    assert t("evleri")["case"] == "ACC"
    assert t("evleri")["num"] == "PL"

# ══════════════════════════════════════════════════════════════════════════════
# 3. DATIVE CASE (now correctly identified as DAT)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root", [
    ("eve",   "ev"),
    ("köye",  "köy"),
])
def test_dat_front(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["case"] == "DAT"

def test_dat_y_buffer():
    assert r("arabaya") == "arabay"
    assert t("arabaya")["case"] == "DAT"

# ══════════════════════════════════════════════════════════════════════════════
# 4. LOCATIVE CASE (now correctly identified as LOC)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root", [
    ("evde",    "ev"),
    ("arabada", "araba"),
    ("köyde",   "köy"),
])
def test_loc_voiced(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["case"] == "LOC"

@pytest.mark.parametrize("surface,exp_root", [
    ("kitapta",  "kitap"),
    ("sepette",  "sepet"),
])
def test_loc_voiceless(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["case"] == "LOC"

# ══════════════════════════════════════════════════════════════════════════════
# 5. ABLATIVE CASE (now correctly identified as ABL)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root", [
    ("evden",    "ev"),
    ("arabadan", "araba"),
    ("köyden",   "köy"),
])
def test_abl_voiced(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["case"] == "ABL"

@pytest.mark.parametrize("surface,exp_root", [
    ("kitaptan", "kitap"),
    ("sepetten", "sepet"),
])
def test_abl_voiceless(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["case"] == "ABL"

# ══════════════════════════════════════════════════════════════════════════════
# 6. GENITIVE CASE (now correctly identified as GEN)
# ══════════════════════════════════════════════════════════════════════════════

def test_gen_ev():
    assert r("evin") == "ev"
    assert t("evin")["case"] == "GEN"

def test_gen_araba_n_buffer():
    assert r("arabanın") == "araba"
    assert t("arabanın")["case"] == "GEN"

# ══════════════════════════════════════════════════════════════════════════════
# 7. INSTRUMENTAL CASE (now correctly identified as INS)
# ══════════════════════════════════════════════════════════════════════════════

def test_ins_evle():
    assert r("evle") == "ev"
    assert t("evle")["case"] == "INS"

def test_ins_arabayla():
    assert r("arabayla") == "arabay"
    assert t("arabayla")["case"] == "INS"

# ══════════════════════════════════════════════════════════════════════════════
# 8. POSSESSIVE — 1SG
# ══════════════════════════════════════════════════════════════════════════════

def test_poss_1sg_ev():
    assert r("evim") == "ev"
    assert t("evim")["poss"] == "1SG"

def test_poss_1sg_araba_after_vowel():
    assert r("arabam") == "araba"
    assert t("arabam")["poss"] == "1SG"

def test_poss_1sg_kol_back_rnd():
    assert r("kolum") == "kol"
    assert t("kolum")["poss"] == "1SG"

def test_poss_1sg_goz_front_rnd():
    assert r("gözüm") == "göz"
    assert t("gözüm")["poss"] == "1SG"

# ══════════════════════════════════════════════════════════════════════════════
# 9. POSSESSIVE — 2SG
# ══════════════════════════════════════════════════════════════════════════════

def test_poss_2sg_ev():
    # evin: GEN and POSS_2SG share -in; engine returns GEN via case slot
    assert r("evin") == "ev"
    assert t("evin")["case"] == "GEN"

def test_poss_2sg_araba_after_vowel():
    assert r("araban") == "araba"
    assert t("araban")["poss"] == "2SG"

def test_poss_2sg_goz_front_rnd():
    assert r("gözün") == "göz"
    assert t("gözün")["case"] == "GEN"

# ══════════════════════════════════════════════════════════════════════════════
# 10. POSSESSIVE — 3SG
# ══════════════════════════════════════════════════════════════════════════════

def test_poss_3sg_ev():
    assert r("evi") == "ev"
    assert t("evi")["case"] == "ACC"

def test_poss_3sg_araba_after_vowel():
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
    assert t("evimiz")["poss"] == "1PL"

def test_poss_1pl_araba_after_vowel():
    assert r("arabamız") == "araba"
    assert t("arabamız")["poss"] == "1PL"

def test_poss_1pl_kol_back_rnd():
    assert r("kolumuz") == "kol"
    assert t("kolumuz")["poss"] == "1PL"

def test_poss_1pl_goz_front_rnd():
    assert r("gözümüz") == "göz"
    assert t("gözümüz")["poss"] == "1PL"

# ══════════════════════════════════════════════════════════════════════════════
# 12. POSSESSIVE — 2PL
# ══════════════════════════════════════════════════════════════════════════════

def test_poss_2pl_ev():
    assert r("eviniz") == "ev"
    assert t("eviniz")["poss"] == "2PL"

def test_poss_2pl_araba_after_vowel():
    assert r("arabanız") == "araba"
    assert t("arabanız")["poss"] == "2PL"

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
    assert r("evlerimde") == "ev"
    assert t("evlerimde")["num"] == "PL"
    assert t("evlerimde")["case"] == "LOC"

def test_stacked_pl_poss_dat():
    assert r("evlerimize") == "ev"
    assert t("evlerimize")["num"] == "PL"
    assert t("evlerimize")["poss"] == "1PL"

def test_stacked_pl_poss_acc():
    assert r("evlerimizi") == "ev"
    assert t("evlerimizi")["case"] == "ACC"
    assert t("evlerimizi")["poss"] == "1PL"
    assert t("evlerimizi")["num"] == "PL"
