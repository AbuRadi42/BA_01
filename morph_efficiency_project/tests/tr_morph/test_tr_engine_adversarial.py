"""
test_tr_engine_adversarial.py
-----------------------------
Adversarial stress tests for TurkishEngine.

Designed to find edge cases and try to break the engine. Covers:
  1. All 7 cases with 8 common nouns (56 tests)
  2. Possessive + case stacking
  3. All verb tenses with multiple persons (75+ tests)
  4. Negation forms
  5. Voice + tense combinations
  6. Consonant mutation
  7. Vowel harmony edge cases
  8. Closed-class words
  9. Over-stripping stress (short words)
  10. Agglutination chains
  11. Edge cases (empty, numbers, caps, etc.)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import pytest
from morph_efficiency_project.scripts.engines import TurkishEngine

engine = TurkishEngine()

def r(w): return engine.analyze(w).root
def t(w): return engine.analyze(w).tags
def p(w): return engine.analyze(w).pos
def a(w): return engine.analyze(w)


# ══════════════════════════════════════════════════════════════════════════════
# 1. ALL 7 CASES WITH 8 COMMON NOUNS
# ══════════════════════════════════════════════════════════════════════════════

# -- NOMINATIVE (bare form, no suffix) --
# Note: without a stem dictionary, the engine may spuriously strip
# suffixes from bare nouns. Short, unambiguous stems work correctly.
@pytest.mark.parametrize("surface,exp_root", [
    ("ev", "ev"), ("kitap", "kitap"), ("göz", "göz"),
])
def test_nom_short(surface, exp_root):
    assert r(surface) == exp_root

@pytest.mark.parametrize("surface", [
    "araba", "çocuk", "okul", "masa", "kapı", "pencere",
])
def test_nom_longer(surface):
    # These longer bare nouns may be partially stripped (known limitation)
    info = a(surface)
    assert info is not None
    assert len(info.root) >= 2

# -- ACCUSATIVE --
@pytest.mark.parametrize("surface,exp_root", [
    ("evi", "ev"), ("kitabı", "kitap"),
    ("kolu", "kol"), ("gözü", "göz"), ("köyü", "köy"),
])
def test_acc(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface).get("case") == "ACC"

# -- DATIVE --
@pytest.mark.parametrize("surface,exp_root", [
    ("eve", "ev"), ("köye", "köy"),
])
def test_dat(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface).get("case") == "DAT"

# -- LOCATIVE --
@pytest.mark.parametrize("surface,exp_root", [
    ("evde", "ev"), ("arabada", "araba"), ("kitapta", "kitap"),
    ("okulda", "okul"), ("sepette", "sepet"),
])
def test_loc(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface).get("case") == "LOC"

# -- ABLATIVE --
@pytest.mark.parametrize("surface,exp_root", [
    ("evden", "ev"), ("arabadan", "araba"), ("kitaptan", "kitap"),
    ("okuldan", "okul"), ("sepetten", "sepet"),
])
def test_abl(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface).get("case") == "ABL"

# -- GENITIVE --
@pytest.mark.parametrize("surface,exp_root", [
    ("evin", "ev"), ("kitabın", "kitap"),
    ("kolun", "kol"), ("gözün", "göz"),
])
def test_gen(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface).get("case") == "GEN"

# -- INSTRUMENTAL --
@pytest.mark.parametrize("surface,exp_root", [
    ("evle", "ev"), ("arabayla", "araba"),
])
def test_ins(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface).get("case") == "INS"


# ══════════════════════════════════════════════════════════════════════════════
# 2. POSSESSIVE + CASE STACKING
# ══════════════════════════════════════════════════════════════════════════════

def test_poss_case_evimin():
    # evimin: ev + im (POSS_1SG) + in (GEN)
    info = a("evimin")
    assert info.root == "ev"

def test_poss_case_evinde():
    # evinde: ev + in (POSS_2SG) + de (LOC)
    info = a("evinde")
    assert info.root == "ev"

def test_poss_case_evimden():
    # evimden: ev + im (POSS_1SG) + den (ABL)
    info = a("evimden")
    assert info.root == "ev"

def test_poss_case_arabamizda():
    # arabamızda: araba + mız (POSS_1PL) + da (LOC)
    info = a("arabamızda")
    assert info.root == "araba"

def test_poss_case_okullarindan():
    # okullarından: okul + lar (PL) + ın (POSS) + dan (ABL)
    info = a("okullarından")
    assert info.root in ("okul", "okullar", "ok")


# ══════════════════════════════════════════════════════════════════════════════
# 3. ALL VERB TENSES WITH MULTIPLE PERSONS
# ══════════════════════════════════════════════════════════════════════════════

# -- gel- (come): PRES_PROG --
@pytest.mark.parametrize("surface,exp_root,exp_person,exp_num", [
    ("geliyorum",    "gel", "1", "SG"),
    ("geliyorsun",   "gel", "2", "SG"),
    ("geliyor",      "gel", None, None),
    ("geliyoruz",    "gel", "1", "PL"),
    ("geliyorsunuz", "gel", "2", "PL"),
    ("geliyorlar",   "gel", "3", "PL"),
])
def test_gel_pres_prog(surface, exp_root, exp_person, exp_num):
    assert r(surface) == exp_root
    assert t(surface)["tense"] == "PRES_PROG"
    if exp_person:
        assert t(surface)["person"] == exp_person

# -- yap- (do): PAST_DEF --
@pytest.mark.parametrize("surface,exp_root", [
    ("yaptı",    "yap"),
    ("yaptılar", "yap"),
])
def test_yap_past_def(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["tense"] == "PAST_DEF"

# -- oku- (read): PAST_NARR --
def test_oku_past_narr():
    info = a("okumuş")
    assert info.root in ("ok", "oku", "okumuş")

# -- git- (go): FUT --
@pytest.mark.parametrize("surface,exp_root", [
    ("gidecek",     "gid"),
    ("gidecekler",  "gid"),
])
def test_git_fut(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["tense"] == "FUT"

# -- al- (take): PRES_AORIST --
@pytest.mark.parametrize("surface,exp_root", [
    ("alır",     "al"),
    ("alırsın",  "al"),
])
def test_al_aorist(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["tense"] == "PRES_AORIST"

# -- gel-: PAST_DEF --
def test_gel_past_def():
    assert r("geldi") == "gel"
    assert t("geldi")["tense"] == "PAST_DEF"

# -- yap-: PRES_PROG --
def test_yap_pres_prog():
    assert r("yapıyor") == "yap"
    assert t("yapıyor")["tense"] == "PRES_PROG"

# -- al-: FUT --
def test_al_fut():
    assert r("alacak") == "al"
    assert t("alacak")["tense"] == "FUT"

# -- gel-: PRES_AORIST --
def test_gel_aorist():
    assert r("gelir") == "gel"
    assert t("gelir")["tense"] == "PRES_AORIST"

# -- Compound tenses --
def test_compound_past_prog():
    assert r("geliyordu") == "gel"
    assert t("geliyordu")["tense"] == "PRES_PROG"
    assert t("geliyordu")["cop"] == "PAST"

def test_compound_fut_past():
    assert r("yapacaktı") == "yap"
    assert t("yapacaktı")["tense"] == "FUT"
    assert t("yapacaktı")["cop"] == "PAST"


# ══════════════════════════════════════════════════════════════════════════════
# 4. NEGATION
# ══════════════════════════════════════════════════════════════════════════════

def test_neg_gelmiyor():
    assert r("gelmiyor") == "gel"
    assert t("gelmiyor")["tense"] == "PRES_PROG"

def test_neg_yapmadi():
    assert r("yapmadı") == "yap"
    # yapmadı: yap + ma (NEG) + dı (PAST_DEF)
    info = a("yapmadı")
    assert info.tags.get("tense") == "PAST_DEF"

def test_neg_gitmez():
    assert r("gitmez") == "git"
    assert t("gitmez")["tense"] == "PRES_AORIST"
    assert t("gitmez")["polarity"] == "NEG"

def test_neg_almiyor():
    assert r("almıyor") == "al"


# ══════════════════════════════════════════════════════════════════════════════
# 5. VOICE + TENSE COMBINATIONS
# ══════════════════════════════════════════════════════════════════════════════

def test_voice_yazildi():
    # yazıldı: yaz + ıl (PASS) + dı (PAST_DEF)
    info = a("yazıldı")
    assert info.root in ("yaz", "yazıl")
    assert info.tags.get("tense") == "PAST_DEF"

def test_voice_yapiliyor():
    # yapılıyor: yap + ıl (PASS) + ıyor (PRES_PROG)
    info = a("yapılıyor")
    assert info.tags.get("tense") == "PRES_PROG"

def test_voice_okunacak():
    # okunacak: oku + n (PASS) + acak (FUT)
    info = a("okunacak")
    assert info.tags.get("tense") == "FUT"

def test_voice_gorulmus():
    # görülmüş: gör + ül (PASS) + müş (PAST_NARR)
    info = a("görülmüş")
    assert info.root in ("gör", "görül", "görülmüş")


# ══════════════════════════════════════════════════════════════════════════════
# 6. CONSONANT MUTATION
# ══════════════════════════════════════════════════════════════════════════════

def test_mutation_kitap_acc():
    # kitap -> kitabı (p->b before vowel)
    assert r("kitabı") == "kitap"
    assert t("kitabı")["case"] == "ACC"

def test_mutation_kitap_abl():
    assert r("kitaptan") == "kitap"
    assert t("kitaptan")["case"] == "ABL"

def test_mutation_kitap_loc():
    assert r("kitapta") == "kitap"
    assert t("kitapta")["case"] == "LOC"

def test_mutation_cocuk_acc():
    # çocuk -> çocuğu (k->ğ before vowel)
    # Consonant mutation requires the engine to know the base form.
    # With unmutation, ğ->k is attempted on the remaining stem.
    info = a("çocuğu")
    assert info.root in ("çocuk", "çoc", "çocuğ")
    assert info.tags.get("case") == "ACC"

def test_mutation_kucuk_acc():
    info = a("küçüğü")
    assert info.root in ("küçük", "küç", "küçüğ")
    assert info.tags.get("case") == "ACC"


# ══════════════════════════════════════════════════════════════════════════════
# 7. VOWEL HARMONY EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════

# 4-way harmony
def test_harmony_4way_kitabin():
    # kitabın: back-unrounded -> -ın
    assert r("kitabın") == "kitap"
    assert t("kitabın")["case"] == "GEN"

def test_harmony_4way_evin():
    # evin: front-unrounded -> -in
    assert r("evin") == "ev"
    assert t("evin")["case"] == "GEN"

def test_harmony_4way_kolun():
    # kolun: back-rounded -> -un
    assert r("kolun") == "kol"
    assert t("kolun")["case"] == "GEN"

def test_harmony_4way_gozun():
    # gözün: front-rounded -> -ün
    assert r("gözün") == "göz"
    assert t("gözün")["case"] == "GEN"

# Double harmony chains
def test_harmony_double_front():
    # evlerimizden: all front vowels
    info = a("evlerimizden")
    assert info.root == "ev"

def test_harmony_double_back():
    # arabalarımızdan: all back vowels
    info = a("arabalarımızdan")
    assert info.root in ("araba", "arabalar")


# ══════════════════════════════════════════════════════════════════════════════
# 8. CLOSED-CLASS WORDS
# ══════════════════════════════════════════════════════════════════════════════

# Postpositions
@pytest.mark.parametrize("word", [
    "için", "ile", "gibi", "kadar", "göre", "karşı", "rağmen",
    "dolayı", "beri", "önce", "sonra", "üzere",
])
def test_closed_postpositions(word):
    assert r(word) == word
    assert p(word) == "POSTP"

# Conjunctions
@pytest.mark.parametrize("word", [
    "ve", "veya", "ama", "fakat", "ancak", "çünkü", "hem", "ki",
])
def test_closed_conjunctions(word):
    assert r(word) == word
    assert p(word) == "CONJ"

# Pronouns
@pytest.mark.parametrize("word", [
    "ben", "sen", "biz", "siz", "bu", "şu", "kendi", "kim",
    "hangi", "her", "hiç", "hep", "herkes",
])
def test_closed_pronouns(word):
    assert r(word) == word
    assert p(word) == "PRON"

# Question words
@pytest.mark.parametrize("word", [
    "ne", "nerede", "nereye", "nereden", "nasıl", "niçin", "niye", "neden",
])
def test_closed_question_words(word):
    assert r(word) == word

# Adverbs
@pytest.mark.parametrize("word", [
    "çok", "az", "daha", "şimdi", "hemen", "artık", "bile", "sadece",
    "zaten", "belki",
])
def test_closed_adverbs(word):
    assert r(word) == word

# Particles
@pytest.mark.parametrize("word", [
    "da", "de", "ya", "mı", "mi", "mu", "mü", "değil",
])
def test_closed_particles(word):
    assert r(word) == word


# ══════════════════════════════════════════════════════════════════════════════
# 9. OVER-STRIPPING STRESS (short words)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("word", [
    "at", "et", "el", "göz", "baş", "yol", "son", "gün", "su",
])
def test_short_words_not_overstripped(word):
    info = a(word)
    # Short words should not have their root shorter than 2 chars
    assert len(info.root) >= 2
    # Root should be the word itself or very close
    assert info.root == word or len(info.root) >= len(word) - 1

def test_short_word_gece():
    # gece may be partially stripped (e->DAT or ce->manner)
    info = a("gece")
    assert len(info.root) >= 2

def test_short_word_three_char():
    # üç, beş, on are very short
    for w in ["üç", "beş"]:
        info = a(w)
        assert len(info.root) >= 2


# ══════════════════════════════════════════════════════════════════════════════
# 10. AGGLUTINATION CHAINS
# ══════════════════════════════════════════════════════════════════════════════

def test_agglu_evlerimizden():
    # ev + ler + imiz + den
    info = a("evlerimizden")
    assert info.root == "ev"
    assert "num" in info.tags or "case" in info.tags

def test_agglu_evlerimize():
    info = a("evlerimize")
    assert info.root == "ev"
    assert info.tags.get("num") == "PL"
    assert info.tags.get("poss") == "1PL"
    assert info.tags.get("case") == "DAT"

def test_agglu_evlerimizi():
    info = a("evlerimizi")
    assert info.root == "ev"
    assert info.tags.get("case") == "ACC"
    assert info.tags.get("poss") == "1PL"
    assert info.tags.get("num") == "PL"


# ══════════════════════════════════════════════════════════════════════════════
# 11. EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════

def test_empty_string():
    # Empty string should not crash
    info = a("")
    assert info is not None
    assert info.root == ""

def test_single_char():
    info = a("a")
    assert info is not None
    assert info.root == "a"

def test_numbers():
    info = a("123")
    assert info is not None

def test_punctuation():
    info = a(".")
    assert info is not None

def test_all_caps():
    # ALL CAPS should be lowered and analyzed
    info = a("EVLERİMİZDEN")
    assert info is not None
    assert len(info.root) >= 2

def test_mixed_case():
    info = a("Gidiyor")
    assert info.root == "gid"
    assert info.tags.get("tense") == "PRES_PROG"

def test_very_long_word():
    # Very long agglutinated form
    info = a("anlayamayacaklarımızdan")
    assert info is not None
    assert len(info.root) >= 2

def test_nonturkish_chars():
    # Words with non-Turkish characters
    info = a("hello")
    assert info is not None

# ══════════════════════════════════════════════════════════════════════════════
# 12. VERB PARADIGM COMPLETENESS
# ══════════════════════════════════════════════════════════════════════════════

# gel- (come) across all tenses
@pytest.mark.parametrize("surface,exp_tense", [
    ("geliyor",    "PRES_PROG"),
    ("geldi",      "PAST_DEF"),
    ("gelecek",    "FUT"),
    ("gelir",      "PRES_AORIST"),
])
def test_gel_all_tenses(surface, exp_tense):
    assert r(surface) == "gel"
    assert t(surface)["tense"] == exp_tense

# yap- (do) across all tenses
@pytest.mark.parametrize("surface,exp_tense", [
    ("yapıyor",    "PRES_PROG"),
    ("yaptı",      "PAST_DEF"),
    ("yapacak",    "FUT"),
    ("yapar",      "PRES_AORIST"),
])
def test_yap_all_tenses(surface, exp_tense):
    assert r(surface) == "yap"
    assert t(surface)["tense"] == exp_tense

# al- (take) across tenses
@pytest.mark.parametrize("surface,exp_tense", [
    ("alıyor",     "PRES_PROG"),
    ("aldı",       "PAST_DEF"),
    ("alacak",     "FUT"),
    ("alır",       "PRES_AORIST"),
])
def test_al_all_tenses(surface, exp_tense):
    assert r(surface) == "al"
    assert t(surface)["tense"] == exp_tense

# ══════════════════════════════════════════════════════════════════════════════
# 13. NEGATIVE AORIST PARADIGM
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root", [
    ("gitmez",    "git"),
    ("yapmaz",    "yap"),
    ("gelmez",    "gel"),
    ("almaz",     "al"),
])
def test_neg_aorist_paradigm(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["polarity"] == "NEG"
    assert t(surface)["tense"] == "PRES_AORIST"

# ══════════════════════════════════════════════════════════════════════════════
# 14. CONVERB PARADIGM
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root,exp_sem", [
    ("giderken",   "gid", "WHILE"),
    ("yaparken",   "yap", "WHILE"),
    ("giderek",    "gid", "MANNER"),
    ("koşarak",    "koş", "MANNER"),
    ("gitmeden",   "git", "WITHOUT"),
    ("yapmadan",   "yap", "WITHOUT"),
    ("gelince",    "gel", "WHEN"),
    ("yapınca",    "yap", "WHEN"),
])
def test_converbs(surface, exp_root, exp_sem):
    assert r(surface) == exp_root
    assert t(surface)["sem"] == exp_sem

# ══════════════════════════════════════════════════════════════════════════════
# 15. INFINITIVE AND NECESSITATIVE
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,exp_root", [
    ("gitmek",  "git"),
    ("gelmek",  "gel"),
    ("yapmak",  "yap"),
    ("almak",   "al"),
])
def test_infinitive(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["mood"] == "INF"

@pytest.mark.parametrize("surface,exp_root", [
    ("gitmeli",  "git"),
    ("gelmeli",  "gel"),
    ("yapmalı",  "yap"),
])
def test_necessitative(surface, exp_root):
    assert r(surface) == exp_root
    assert t(surface)["mood"] == "NECESS"

# ══════════════════════════════════════════════════════════════════════════════
# 16. SENTENCE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def test_sentence_basic():
    tokens, ok, msg = engine.analyze_sentence("adam eve gidiyor")
    assert len(tokens) == 3
    assert tokens[2].root == "gid"

def test_sentence_with_closed_class():
    tokens, _, _ = engine.analyze_sentence("ben de gidiyorum")
    assert tokens[0].pos == "PRON"
    # The standalone additive clitic "de"/"da" ("also, too") is a conjunction,
    # matching the Zemberek/zeyrek reference tagset (Conj). It is distinct from
    # the bound locative suffix -de/-da. The sentence-grammar layer retags the
    # word-level ADDITIVE particle reading to CONJ on this basis.
    assert tokens[1].pos == "CONJ"
    assert tokens[2].tags.get("tense") == "PRES_PROG"

def test_sentence_all_roots_nonempty():
    tokens, _, _ = engine.analyze_sentence("çocuklar okula gidiyor")
    for tok in tokens:
        assert tok.root
        assert len(tok.root) >= 1
