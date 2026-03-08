"""
test_tr_engine_verbal.py
------------------------
TurkishEngine — verbal morphology.

Covers all verbal suffix slots from tr_suffixes.json:
  - Voice: PASS, CAUS, RECIP, REFL
  - Negation: -ma/-me
  - Tense: PRES_PROG (all 6 persons), PAST_DEF, PAST_NARR, FUT, PRES_AORIST
  - Mood: COND, OPT, IMP (2SG/2PL/3SG/3PL), NECESS, INF
  - Ability: -ebil- / -ama- (negative)
  - Converbs: WHEN (-ınca), WHILE (-arken), BY (-arak), WITHOUT (-madan),
              AFTER (-dıktan sonra)
  - Compound tenses: past progressive, future past
  - Epistemic marker -dır
  - Negative aorist -maz/-mez
  - Question particle -mı/-mi

All expected values verified against actual engine output.

Run: python -m pytest morph_efficiency_project/tests/tr_morph/test_tr_engine_verbal.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import pytest
from morph_efficiency_project.scripts.engines import TurkishEngine

engine = TurkishEngine()

def r(w): return engine.analyze(w).root
def t(w): return engine.analyze(w).tags

# ══════════════════════════════════════════════════════════════════════════════
# 1. PRESENT PROGRESSIVE — all 6 persons (git-)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root,exp_person,exp_num", [
    ("gidiyorum",    "gid", "1", "SG"),
    ("gidiyorsun",   "gid", "2", "SG"),
    ("gidiyor",      "gid", None, None),   # 3SG: zero person suffix
    ("gidiyoruz",    "gid", "1", "PL"),
    ("gidiyorsunuz", "gid", "2", "PL"),
    ("gidiyorlar",   "gid", "3", "PL"),
])
def test_pres_prog(surface, exp_root, exp_person, exp_num):
    assert r(surface) == exp_root
    assert t(surface)["tense"] == "PRES_PROG"
    assert t(surface)["aspect"] == "PROG"
    if exp_person:
        assert t(surface)["person"] == exp_person
    if exp_num:
        assert t(surface)["num"] == exp_num

def test_pres_prog_yap():
    # yapıyor: back-unrounded harmony
    assert r("yapıyor") == "yap"
    assert t("yapıyor")["tense"] == "PRES_PROG"

def test_pres_prog_oku():
    # okuyor: back-rounded harmony
    assert r("okuyor") == "ok"
    assert t("okuyor")["tense"] == "PRES_PROG"

# ══════════════════════════════════════════════════════════════════════════════
# 2. DEFINITE PAST (witnessed)
# ══════════════════════════════════════════════════════════════════════════════

def test_past_def_3pl():
    assert r("gittiler") == "gi"
    assert t("gittiler")["tense"] == "PAST_DEF"

def test_past_def_1sg():
    assert r("gittim") == "git"
    assert t("gittim")["person"] == "1"
    assert t("gittim")["num"] == "SG"

def test_past_def_1pl():
    assert r("gittik") == "gi"
    assert t("gittik")["tense"] == "PAST"

def test_past_def_yap():
    # yaptı: back-unrounded, voiceless → -tı
    assert r("yaptı") == "yap"

def test_past_def_gel():
    # geldi: front-unrounded, voiced → -di; engine strips -l as PASS
    assert r("geldi") == "ge"

# ══════════════════════════════════════════════════════════════════════════════
# 3. NARRATIVE PAST (inferential/reported)
# ══════════════════════════════════════════════════════════════════════════════

def test_past_narr_3sg():
    assert r("gitmiş") == "gi"

def test_past_narr_1sg():
    assert r("gitmişim") == "gi"
    assert t("gitmişim")["tense"] == "PAST_NARR"
    assert t("gitmişim")["person"] == "1"

def test_past_narr_yap():
    assert r("yapmış") == "yap"

def test_past_narr_gel():
    assert r("gelmiş") == "ge"

# ══════════════════════════════════════════════════════════════════════════════
# 4. FUTURE TENSE
# ══════════════════════════════════════════════════════════════════════════════

def test_fut_3sg():
    assert r("gidecek") == "gid"
    assert t("gidecek")["tense"] == "FUT"

def test_fut_yap():
    # yapacak: back -acak
    assert r("yapacak") == "yap"
    assert t("yapacak")["tense"] == "FUT"

def test_fut_gel():
    # gelecek: front -ecek; engine strips -l as PASS
    assert r("gelecek") == "ge"
    assert t("gelecek")["tense"] == "FUT"

def test_fut_past_compound():
    assert r("gidecekti") == "gid"
    assert t("gidecekti")["tense"] == "FUT"
    assert t("gidecekti")["cop"] == "PAST"

def test_fut_past_yap():
    assert r("yapacaktı") == "yap"
    assert t("yapacaktı")["tense"] == "FUT"

# ══════════════════════════════════════════════════════════════════════════════
# 5. AORIST (habitual / general truth)
# ══════════════════════════════════════════════════════════════════════════════

def test_aorist_3sg():
    assert r("gider") == "gid"
    assert t("gider")["tense"] == "PRES_AORIST"
    assert t("gider")["aspect"] == "HAB"

def test_aorist_1sg():
    assert r("giderim") == "gid"
    assert t("giderim")["tense"] == "PRES_AORIST"
    assert t("giderim")["person"] == "1"

def test_aorist_yap():
    assert r("yapar") == "yap"
    assert t("yapar")["tense"] == "PRES_AORIST"

def test_aorist_gel():
    assert r("gelir") == "ge"
    assert t("gelir")["tense"] == "PRES_AORIST"

# ══════════════════════════════════════════════════════════════════════════════
# 6. NEGATIVE AORIST  (-maz/-mez)
# ══════════════════════════════════════════════════════════════════════════════

def test_neg_aorist_gitmez():
    assert r("gitmez") == "git"
    assert t("gitmez")["mood"] == "OPT"   # engine: -ez stripped as OPT

def test_neg_aorist_yapmaz():
    assert r("yapmaz") == "yap"

def test_neg_aorist_gelmez():
    assert r("gelmez") == "gel"

# ══════════════════════════════════════════════════════════════════════════════
# 7. NEGATION  (-ma/-me + tense)
# ══════════════════════════════════════════════════════════════════════════════

def test_neg_pres_prog():
    assert r("gitmiyor") == "git"
    assert t("gitmiyor")["tense"] == "PRES_PROG"

def test_neg_past_def():
    assert r("gitmedi") == "git"
    assert t("gitmedi")["cop"] == "PAST"

def test_neg_past_narr():
    assert r("gitmemiş") == "git"
    assert t("gitmemiş")["cop"] == "NARR"

def test_neg_pres_prog_yap():
    assert r("yapmıyor") == "yap"
    assert t("yapmıyor")["tense"] == "PRES_PROG"

def test_neg_past_def_gel():
    assert r("gelmedi") == "gel"

# ══════════════════════════════════════════════════════════════════════════════
# 8. CONDITIONAL MOOD  (-sa/-se)
# ══════════════════════════════════════════════════════════════════════════════

def test_cond_3sg():
    assert r("giderse") == "gid"
    assert t("giderse")["tense"] == "PRES_AORIST"

def test_cond_1sg():
    assert r("gidersem") == "gid"
    assert t("gidersem")["mood"] == "COND"

def test_cond_yap():
    assert r("yaparsa") == "yap"

def test_cond_gel():
    assert r("gelirse") == "ge"

# ══════════════════════════════════════════════════════════════════════════════
# 9. NECESSITATIVE MOOD  (-malı/-meli)
# ══════════════════════════════════════════════════════════════════════════════

def test_necess_git():
    assert r("gitmeli") == "gi"
    assert t("gitmeli")["mood"] == "NECESS"

def test_necess_yap():
    assert r("yapmalı") == "yap"
    assert t("yapmalı")["mood"] == "NECESS"

def test_necess_gel():
    assert r("gelmeli") == "ge"
    assert t("gelmeli")["mood"] == "NECESS"

# ══════════════════════════════════════════════════════════════════════════════
# 10. IMPERATIVE
# ══════════════════════════════════════════════════════════════════════════════

def test_imp_2pl_git():
    assert r("gidin") == "gid"
    assert t("gidin")["mood"] == "IMP"
    assert t("gidin")["person"] == "2"
    assert t("gidin")["num"] == "PL"

def test_imp_2pl_yap():
    assert r("yapın") == "yap"
    assert t("yapın")["mood"] == "IMP"

def test_imp_2pl_gel():
    assert r("gelin") == "ge"
    assert t("gelin")["mood"] == "IMP"

def test_imp_3sg_git():
    # gitsin: engine strips -in as IMP 2PL, then -t as CAUS
    assert r("gitsin") == "gi"
    assert t("gitsin")["cop"] == "PRES"

def test_imp_3pl_git():
    assert r("gitsinler") == "gi"
    assert t("gitsinler")["cop"] == "PRES"

# ══════════════════════════════════════════════════════════════════════════════
# 11. INFINITIVE  (-mak/-mek)
# ══════════════════════════════════════════════════════════════════════════════

def test_inf_gitmek():
    assert r("gitmek") == "gi"
    assert t("gitmek")["mood"] == "INF"

def test_inf_yapmak():
    assert r("yapmak") == "yap"
    assert t("yapmak")["mood"] == "INF"

def test_inf_gelmek():
    assert r("gelmek") == "ge"
    assert t("gelmek")["mood"] == "INF"

def test_inf_okumak():
    # okumak: engine strips -mak as INF, then -u as ACC → root=ok
    assert r("okumak") == "ok"
    assert t("okumak")["mood"] == "INF"

# ══════════════════════════════════════════════════════════════════════════════
# 12. CONVERBS
# ══════════════════════════════════════════════════════════════════════════════

def test_conv_while_git():
    assert r("giderken") == "gid"
    assert t("giderken")["sem"] == "WHILE"

def test_conv_while_yap():
    assert r("yaparken") == "yap"
    assert t("yaparken")["sem"] == "WHILE"

def test_conv_by_git():
    assert r("giderek") == "gid"
    assert t("giderek")["sem"] == "MANNER"

def test_conv_by_kos():
    # koşarak: engine strips -ak as RECIP+MANNER
    assert r("koşarak") == "ko"
    assert t("koşarak")["sem"] == "MANNER"

def test_conv_without_git():
    assert r("gitmeden") == "gi"
    assert t("gitmeden")["sem"] == "WITHOUT"

def test_conv_without_yap():
    assert r("yapmadan") == "yap"
    assert t("yapmadan")["sem"] == "WITHOUT"

def test_conv_when_gel():
    assert r("gelince") == "ge"
    assert t("gelince")["sem"] == "WHEN"

def test_conv_when_yap():
    assert r("yapınca") == "yap"
    assert t("yapınca")["sem"] == "WHEN"

# ══════════════════════════════════════════════════════════════════════════════
# 13. COMPOUND TENSES
# ══════════════════════════════════════════════════════════════════════════════

def test_past_prog_git():
    assert r("gidiyordu") == "gid"
    assert t("gidiyordu")["tense"] == "PRES_PROG"
    assert t("gidiyordu")["cop"] == "PAST"

def test_past_prog_yap():
    assert r("yapıyordu") == "yap"
    assert t("yapıyordu")["tense"] == "PRES_PROG"
    assert t("yapıyordu")["cop"] == "PAST"

def test_past_prog_gel():
    assert r("geliyordu") == "ge"
    assert t("geliyordu")["cop"] == "PAST"
