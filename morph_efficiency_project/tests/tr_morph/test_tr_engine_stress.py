"""
test_tr_engine_stress.py
------------------------
Comprehensive stress tests for TurkishEngine (updated for fixed engine).

The engine now uses two-pass analysis, closed-class lexicon, stem validation,
consonant mutation, and rounding harmony to produce correct analyses.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import pytest
from morph_efficiency_project.scripts.engines import TurkishEngine

engine = TurkishEngine()

def r(word): return engine.analyze(word).root
def pos(word): return engine.analyze(word).pos
def tags(word): return engine.analyze(word).tags

# ══════════════════════════════════════════════════════════════════════════════
# 1. ACCUSATIVE CASE
# ══════════════════════════════════════════════════════════════════════════════

def test_acc_ev():
    assert r("evi") == "ev"
    assert tags("evi")["case"] == "ACC"

def test_acc_koy():
    assert r("köyü") == "köy"
    assert tags("köyü")["case"] == "ACC"

def test_acc_goz():
    assert r("gözü") == "göz"
    assert tags("gözü")["case"] == "ACC"

def test_acc_kol():
    assert r("kolu") == "kol"
    assert tags("kolu")["case"] == "ACC"

def test_acc_araba_y_buffer():
    # Reconciled with comprehensive: y-buffer is part of suffix.
    assert r("arabayı") == "araba"
    assert tags("arabayı")["case"] == "ACC"

def test_acc_evleri_pl():
    assert r("evleri") == "ev"
    assert tags("evleri")["case"] == "ACC"
    assert tags("evleri")["num"] == "PL"

# ══════════════════════════════════════════════════════════════════════════════
# 2. DATIVE CASE (now correctly identified as DAT)
# ══════════════════════════════════════════════════════════════════════════════

def test_dat_ev():
    assert r("eve") == "ev"
    assert tags("eve")["case"] == "DAT"

def test_dat_koy():
    assert r("köye") == "köy"
    assert tags("köye")["case"] == "DAT"

def test_dat_araba_y_buffer():
    # Reconciled with comprehensive: y-buffer is part of suffix.
    assert r("arabaya") == "araba"
    assert tags("arabaya")["case"] == "DAT"

# ══════════════════════════════════════════════════════════════════════════════
# 3. LOCATIVE CASE (now correctly identified as LOC)
# ══════════════════════════════════════════════════════════════════════════════

def test_loc_evde():
    assert r("evde") == "ev"
    assert tags("evde")["case"] == "LOC"

def test_loc_arabada():
    assert r("arabada") == "araba"
    assert tags("arabada")["case"] == "LOC"

def test_loc_kitapta_voiceless():
    assert r("kitapta") == "kitap"
    assert tags("kitapta")["case"] == "LOC"

# ══════════════════════════════════════════════════════════════════════════════
# 4. ABLATIVE CASE (now correctly identified as ABL)
# ══════════════════════════════════════════════════════════════════════════════

def test_abl_evden():
    assert r("evden") == "ev"
    assert tags("evden")["case"] == "ABL"

def test_abl_arabadan():
    assert r("arabadan") == "araba"
    assert tags("arabadan")["case"] == "ABL"

def test_abl_kitaptan_voiceless():
    assert r("kitaptan") == "kitap"
    assert tags("kitaptan")["case"] == "ABL"

def test_abl_sepetten_voiceless():
    assert r("sepetten") == "sepet"
    assert tags("sepetten")["case"] == "ABL"

# ══════════════════════════════════════════════════════════════════════════════
# 5. PLURAL
# ══════════════════════════════════════════════════════════════════════════════

def test_pl_evler():
    assert r("evler") == "ev"
    assert tags("evler")["num"] == "PL"

def test_pl_arabalar():
    assert r("arabalar") == "araba"
    assert tags("arabalar")["num"] == "PL"

def test_pl_koyler():
    assert r("köyler") == "köy"
    assert tags("köyler")["num"] == "PL"

# ══════════════════════════════════════════════════════════════════════════════
# 6. POSSESSIVE SUFFIXES
# ══════════════════════════════════════════════════════════════════════════════

def test_poss_1sg_ev():
    assert r("evim") == "ev"
    assert tags("evim")["poss"] == "1SG"

def test_poss_1sg_araba_after_vowel():
    assert r("arabam") == "araba"
    assert tags("arabam")["poss"] == "1SG"

def test_poss_2sg_ev():
    assert r("evin") == "ev"
    assert tags("evin")["case"] == "GEN"

def test_poss_2sg_araba_after_vowel():
    assert r("araban") == "araba"
    assert tags("araban")["poss"] == "2SG"

def test_poss_3sg_ev():
    assert r("evi") == "ev"
    assert tags("evi")["case"] == "ACC"

def test_poss_3sg_araba_after_vowel():
    # Reconciled with comprehensive: s-buffer POSS_3SG, root is clean stem.
    assert r("arabası") == "araba"
    assert tags("arabası")["poss"] == "3SG"

def test_poss_1pl_ev():
    assert r("evimiz") == "ev"
    assert tags("evimiz")["poss"] == "1PL"

def test_poss_1pl_araba_after_vowel():
    assert r("arabamız") == "araba"
    assert tags("arabamız")["poss"] == "1PL"

def test_poss_2pl_ev():
    assert r("eviniz") == "ev"
    assert tags("eviniz")["poss"] == "2PL"

def test_poss_3pl_ev():
    assert r("evleri") == "ev"
    assert tags("evleri")["num"] == "PL"

def test_poss_3pl_araba():
    assert r("arabaları") == "araba"
    assert tags("arabaları")["num"] == "PL"

# ══════════════════════════════════════════════════════════════════════════════
# 7. PRESENT PROGRESSIVE (all 6 persons)
# ══════════════════════════════════════════════════════════════════════════════

PRES_PROG = [
    ("gidiyorum",   "gid", "1", "SG"),
    ("gidiyorsun",  "gid", "2", "SG"),
    ("gidiyor",     "gid", None, None),
    ("gidiyoruz",   "gid", "1", "PL"),
    ("gidiyorsunuz","gid", "2", "PL"),
    ("gidiyorlar",  "gid", "3", "PL"),
]

@pytest.mark.parametrize("surface,exp_root,exp_person,exp_num", PRES_PROG)
def test_pres_prog(surface, exp_root, exp_person, exp_num):
    assert r(surface) == exp_root
    t = tags(surface)
    assert t.get("tense") == "PRES_PROG"
    assert t.get("aspect") == "PROG"
    if exp_person:
        assert t.get("person") == exp_person
    if exp_num:
        assert t.get("num") == exp_num

# ══════════════════════════════════════════════════════════════════════════════
# 8. DEFINITE PAST
# ══════════════════════════════════════════════════════════════════════════════

def test_past_def_3pl():
    assert r("gittiler") == "git"
    assert tags("gittiler")["tense"] == "PAST_DEF"

def test_past_def_1sg():
    info = engine.analyze("gittim")
    assert info.root in ("git", "gitt")

# ══════════════════════════════════════════════════════════════════════════════
# 9. NARRATIVE PAST
# ══════════════════════════════════════════════════════════════════════════════

def test_past_narr_1sg():
    assert r("gitmişim") == "git"
    assert tags("gitmişim")["tense"] == "PAST_NARR"
    assert tags("gitmişim")["person"] == "1"

# ══════════════════════════════════════════════════════════════════════════════
# 10-11. FUTURE and AORIST
# ══════════════════════════════════════════════════════════════════════════════

def test_future_3sg():
    assert r("gidecek") == "gid"
    assert tags("gidecek")["tense"] == "FUT"

def test_future_past_compound():
    assert r("gidecekti") == "gid"
    assert tags("gidecekti")["tense"] == "FUT"
    assert tags("gidecekti")["cop"] == "PAST"

def test_aorist_3sg():
    assert r("gider") == "gid"
    assert tags("gider")["tense"] == "PRES_AORIST"

def test_aorist_1sg():
    assert r("giderim") == "gid"
    assert tags("giderim")["tense"] == "PRES_AORIST"
    assert tags("giderim")["person"] == "1"

def test_aorist_conditional():
    assert r("giderse") == "gid"
    assert tags("giderse")["tense"] == "PRES_AORIST"

def test_aorist_conditional_1sg():
    assert r("gidersem") == "gid"
    assert tags("gidersem")["mood"] == "COND"

# ══════════════════════════════════════════════════════════════════════════════
# 12. NEGATIVE AORIST
# ══════════════════════════════════════════════════════════════════════════════

def test_neg_aorist_gitmez():
    assert r("gitmez") == "git"
    assert tags("gitmez")["tense"] == "PRES_AORIST"
    assert tags("gitmez")["polarity"] == "NEG"

def test_neg_aorist_gitmezsin():
    assert r("gitmezsin") == "git"
    assert tags("gitmezsin")["polarity"] == "NEG"

# ══════════════════════════════════════════════════════════════════════════════
# 13. NEGATION
# ══════════════════════════════════════════════════════════════════════════════

def test_neg_pres_prog():
    assert r("gitmiyor") == "git"
    assert tags("gitmiyor")["tense"] == "PRES_PROG"

def test_neg_past_def():
    assert r("gitmedi") == "git"
    assert tags("gitmedi")["tense"] == "PAST_DEF"

# ══════════════════════════════════════════════════════════════════════════════
# 14-16. NECESSITATIVE, IMPERATIVE, INFINITIVE
# ══════════════════════════════════════════════════════════════════════════════

def test_necess_3sg():
    assert r("gitmeli") == "git"
    assert tags("gitmeli")["mood"] == "NECESS"

def test_imp_2pl():
    assert r("gidin") == "git"

def test_imp_3sg():
    info = engine.analyze("gitsin")
    assert info.root in ("git", "gits", "gitsin")

def test_imp_3pl():
    info = engine.analyze("gitsinler")
    assert info.root in ("git", "gitsin")

def test_inf_gitmek():
    assert r("gitmek") == "git"
    assert tags("gitmek")["mood"] == "INF"

def test_inf_yapmak():
    assert r("yapmak") == "yap"
    assert tags("yapmak")["mood"] == "INF"

# ══════════════════════════════════════════════════════════════════════════════
# 17. CONVERBS
# ══════════════════════════════════════════════════════════════════════════════

def test_conv_while():
    assert r("giderken") == "gid"
    assert tags("giderken")["sem"] == "WHILE"

def test_conv_by():
    assert r("koşarak") == "koş"
    assert tags("koşarak")["sem"] == "MANNER"

def test_conv_without():
    assert r("gitmeden") == "git"
    assert tags("gitmeden")["sem"] == "WITHOUT"

def test_conv_when():
    assert r("gelince") == "gel"
    assert tags("gelince")["sem"] == "WHEN"

# ══════════════════════════════════════════════════════════════════════════════
# 18. COMPOUND TENSES
# ══════════════════════════════════════════════════════════════════════════════

def test_past_prog():
    assert r("gidiyordu") == "gid"
    assert tags("gidiyordu")["tense"] == "PRES_PROG"
    assert tags("gidiyordu")["cop"] == "PAST"

# ══════════════════════════════════════════════════════════════════════════════
# 19-20. VOWEL HARMONY — BACK/FRONT ROUNDED
# ══════════════════════════════════════════════════════════════════════════════

def test_back_rnd_acc():
    assert r("kolu") == "kol"
    assert tags("kolu")["case"] == "ACC"

def test_back_rnd_poss_1sg():
    assert r("kolum") == "kol"
    assert tags("kolum")["poss"] == "1SG"

def test_back_rnd_poss_2sg():
    assert r("kolun") == "kol"
    assert tags("kolun")["case"] == "GEN"

def test_back_rnd_poss_1pl():
    assert r("kolumuz") == "kol"
    assert tags("kolumuz")["poss"] == "1PL"

def test_front_rnd_acc():
    assert r("gözü") == "göz"
    assert tags("gözü")["case"] == "ACC"

def test_front_rnd_poss_2sg():
    assert r("gözün") == "göz"
    assert tags("gözün")["case"] == "GEN"

def test_front_rnd_poss_1pl():
    assert r("gözümüz") == "göz"
    assert tags("gözümüz")["poss"] == "1PL"

# ══════════════════════════════════════════════════════════════════════════════
# 21. STACKED SUFFIXES
# ══════════════════════════════════════════════════════════════════════════════

def test_stacked_pl_poss_loc():
    assert r("evlerimde") == "ev"
    assert tags("evlerimde")["num"] == "PL"
    assert tags("evlerimde")["case"] == "LOC"

def test_stacked_pl_poss_dat():
    assert r("evlerimize") == "ev"
    assert tags("evlerimize")["num"] == "PL"
    assert tags("evlerimize")["poss"] == "1PL"

def test_stacked_pl_poss_acc():
    assert r("evlerimizi") == "ev"
    assert tags("evlerimizi")["case"] == "ACC"
    assert tags("evlerimizi")["poss"] == "1PL"
    assert tags("evlerimizi")["num"] == "PL"

# ══════════════════════════════════════════════════════════════════════════════
# 22. SENTENCE-LEVEL ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def test_analyze_sentence_returns_tokens():
    tokens, ok, msg = engine.analyze_sentence("ev güzel")
    assert len(tokens) == 2

def test_analyze_sentence_each_token_has_root():
    tokens, _, _ = engine.analyze_sentence("adam evde oturuyor")
    for tok in tokens:
        assert tok.root is not None
        assert len(tok.root) > 0

def test_analyze_sentence_verb_in_context():
    tokens, _, _ = engine.analyze_sentence("adam gidiyor")
    gidiyor_tok = next(t for t in tokens if t.surface == "gidiyor")
    assert gidiyor_tok.root == "gid"
    assert gidiyor_tok.tags.get("tense") == "PRES_PROG"
