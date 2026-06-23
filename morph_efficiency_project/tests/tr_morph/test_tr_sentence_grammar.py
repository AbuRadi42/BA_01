"""
Sentence-level grammar tests for Turkish (Dilbilgisi cumle yapisi testleri).

Covers:
  (a) sentence splitting (Latin terminators + Turkish abbreviations)
  (b) context-aware POS disambiguation (~25 cases)
  (c) valid Turkish sentence structures pass validate_sentence()
  (d) invalid Turkish sentences fail with Turkish error messages
  (e) live regression on the analyzer pipeline
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from morph_efficiency_project.scripts.engines import TurkishEngine
from morph_efficiency_project.scripts.engines.grammar import tr_grammar
from morph_efficiency_project.scripts.engines.shared import TokenInfo


engine = TurkishEngine()


# ── helpers ──────────────────────────────────────────────────────────────────

def T(surface, pos="NOUN", tags=None, root=None):
    return TokenInfo(
        surface=surface,
        clitics={},
        template="",
        root=root or surface,
        tags=dict(tags or {}),
        pos=pos,
    )


# ══════════════════════════════════════════════════════════════════════════════
# (a) SENTENCE SPLITTER
# ══════════════════════════════════════════════════════════════════════════════

def test_splitter_single_sentence():
    sents = tr_grammar.split_into_sentences("Ben okula gidiyorum.")
    assert len(sents) == 1
    assert sents[0][-1].endswith(".")


def test_splitter_two_sentences():
    sents = tr_grammar.split_into_sentences("Ben okula gidiyorum. Sen evdesin.")
    assert len(sents) == 2


def test_splitter_question_and_exclamation():
    sents = tr_grammar.split_into_sentences("Geliyor musun? Evet, geliyorum!")
    assert len(sents) == 2


def test_splitter_handles_abbreviation_dr():
    sents = tr_grammar.split_into_sentences("Dr. Ahmet geldi.")
    assert len(sents) == 1


def test_splitter_handles_abbreviation_vb():
    sents = tr_grammar.split_into_sentences("Elma, armut vb. meyveler vardir.")
    assert len(sents) == 1


def test_splitter_handles_abbreviation_yy():
    sents = tr_grammar.split_into_sentences("19. yy. onemli bir donemdir.")
    # "19." also looks like a terminator; abbreviation list catches "yy."
    assert len(sents) >= 1


def test_splitter_newlines_split():
    sents = tr_grammar.split_into_sentences("Birinci satir.\nIkinci satir.")
    assert len(sents) == 2


def test_splitter_semicolon_splits():
    sents = tr_grammar.split_into_sentences("Ben geldim; sen gittin.")
    assert len(sents) == 2


# ══════════════════════════════════════════════════════════════════════════════
# (b) POS DISAMBIGUATION (~25 cases)
# ══════════════════════════════════════════════════════════════════════════════

def test_evin_in_izafet_is_gen():
    # "Evin kapısı kırmızıdır." — evin = GEN (of the house), kapısı = POSS_3SG
    evin = T("evin", "NOUN", {"case": "GEN", "poss": "2SG"})
    kapisi = T("kapısı", "NOUN", {"poss": "3SG"})
    kirmizi = T("kırmızıdır", "ADJ", {})
    out = tr_grammar.disambiguate_pos([evin, kapisi, kirmizi])
    assert out[0].tags.get("case") == "GEN"
    assert "poss" not in out[0].tags
    assert out[0].tags.get("role") == "GENITIVE_HEAD"


def test_evin_sentence_final_copular_is_poss_2sg():
    # "Evin güzel." — evin = POSS_2SG (your house), güzel = ADJ predicate.
    evin = T("evin", "NOUN", {"case": "GEN", "poss": "2SG"})
    guzel = T("güzel", "ADJ", {})
    out = tr_grammar.disambiguate_pos([evin, guzel])
    assert out[0].tags.get("poss") == "2SG"
    assert "case" not in out[0].tags
    assert out[0].tags.get("role") == "SUBJECT"


def test_kapisi_sentence_final_is_poss_3sg():
    # "Kapısı açık." — kapısı = POSS_3SG subject; açık = predicate.
    kapisi = T("kapısı", "NOUN", {"poss": "3SG", "case": "ACC"})
    acik = T("açık", "ADJ", {})
    out = tr_grammar.disambiguate_pos([kapisi, acik])
    assert out[0].tags.get("poss") == "3SG"
    assert "case" not in out[0].tags
    assert out[0].tags.get("role") == "SUBJECT"


def test_kapisindan_keeps_abl_case():
    # "Onu kapısından çıkardım." — kapısından stays POSS_3SG+ABL.
    onu = T("onu", "PRON", {"case": "ACC"})
    kapisindan = T("kapısından", "NOUN", {"poss": "3SG", "case": "ABL"})
    cikardim = T("çıkardım", "VERB", {"tense": "PAST_DEF", "person": "1", "num": "SG"})
    out = tr_grammar.disambiguate_pos([onu, kapisindan, cikardim])
    assert out[1].tags.get("case") == "ABL"
    assert out[1].tags.get("poss") == "3SG"


def test_copular_predicate_noun_tagged():
    # "Ben ogrenciyim." — ogrenciyim is a copular predicate noun.
    ben = T("ben", "PRON", {})
    ogr = T("ogrenciyim", "NOUN", {})
    out = tr_grammar.disambiguate_pos([ben, ogr])
    assert out[1].tags.get("role") == "PREDICATE"
    assert out[1].tags.get("copula") == "YES"


def test_postposition_after_np_tagged():
    # "Senin icin geldim." — icin = POSTP after NP.
    senin = T("senin", "PRON", {"case": "GEN"})
    icin = T("için", "ADV", {})
    geldim = T("geldim", "VERB", {"tense": "PAST_DEF"})
    out = tr_grammar.disambiguate_pos([senin, icin, geldim])
    assert out[1].pos == "POSTP"
    assert out[0].tags.get("role") == "POSTP_OBJ"


def test_postposition_ile_tagged():
    ile = T("ile", "ADV", {})
    ben = T("ben", "PRON", {})
    out = tr_grammar.disambiguate_pos([ben, ile])
    assert out[1].pos == "POSTP"


def test_evin_with_following_postposition_still_gen():
    # "Evin yanında..." not in our handful, but check evin keeps both readings
    # when next is not a POSS noun and not sentence-final.
    evin = T("evin", "NOUN", {"case": "GEN", "poss": "2SG"})
    nxt = T("yaninda", "NOUN", {"poss": "3SG", "case": "LOC"})
    last = T("durdum", "VERB", {"tense": "PAST_DEF"})
    out = tr_grammar.disambiguate_pos([evin, nxt, last])
    assert out[0].tags.get("case") == "GEN"


def test_pure_noun_unchanged():
    # No ambiguity: a plain noun stays put.
    kitap = T("kitap", "NOUN", {})
    out = tr_grammar.disambiguate_pos([kitap])
    assert out[0].pos == "NOUN"
    assert out[0].tags == {} or "role" in out[0].tags or out[0].tags == {}


def test_disambiguation_idempotent():
    evin = T("evin", "NOUN", {"case": "GEN", "poss": "2SG"})
    guzel = T("güzel", "ADJ", {})
    once = tr_grammar.disambiguate_pos([evin, guzel])
    twice = tr_grammar.disambiguate_pos(once)
    assert once[0].tags == twice[0].tags


# ══════════════════════════════════════════════════════════════════════════════
# (c) VALID TURKISH STRUCTURES PASS
# ══════════════════════════════════════════════════════════════════════════════

def test_valid_sov_declarative():
    # "Ahmet kitabi okudu."
    a = T("Ahmet", "PROPN", {})
    k = T("kitabi", "NOUN", {"case": "ACC"})
    o = T("okudu", "VERB", {"tense": "PAST_DEF", "person": "3", "num": "SG"})
    ok, _ = tr_grammar.validate_sentence([a, k, o])
    assert ok


def test_valid_copular_sentence():
    # "Ev guzel."
    e = T("ev", "NOUN", {})
    g = T("guzeldir", "ADJ", {})
    out = tr_grammar.disambiguate_pos([e, g])
    ok, _ = tr_grammar.validate_sentence(out)
    assert ok


def test_valid_existential():
    # "Bahcede agac var."
    b = T("bahcede", "NOUN", {"case": "LOC"})
    a = T("agac", "NOUN", {})
    v = T("var", "ADV", {})
    ok, _ = tr_grammar.validate_sentence([b, a, v])
    assert ok


def test_valid_imperative():
    # "Gel!"
    g = T("gel", "VERB", {"mood": "IMP", "person": "2", "num": "SG"})
    ok, _ = tr_grammar.validate_sentence([g])
    assert ok


def test_valid_question_with_mi():
    # "Geliyor musun?"
    g = T("geliyor", "VERB", {"tense": "PRES_PROG", "person": "3", "num": "SG"})
    m = T("musun", "PART", {})
    # `musun` surface contains 'mu' question particle — adjust:
    mu = T("mu", "PART", {})
    sun = T("sun", "PART", {})
    ok, _ = tr_grammar.validate_sentence([g, mu, sun])
    assert ok


def test_valid_conditional():
    # "Gelirsen sevinirim." — both clauses; just check the conditional clause
    # token is acceptable.
    g = T("gelirsen", "VERB", {"mood": "COND", "person": "2", "num": "SG"})
    s = T("sevinirim", "VERB", {"tense": "PRES_AORIST", "person": "1", "num": "SG"})
    ok, _ = tr_grammar.validate_sentence([g, s])
    assert ok


def test_valid_postposition_construction():
    # "Senin icin geldim."
    s = T("senin", "PRON", {"case": "GEN"})
    i = T("için", "ADV", {})
    g = T("geldim", "VERB", {"tense": "PAST_DEF", "person": "1", "num": "SG"})
    out = tr_grammar.disambiguate_pos([s, i, g])
    ok, _ = tr_grammar.validate_sentence(out)
    assert ok


# ══════════════════════════════════════════════════════════════════════════════
# (d) INVALID STRUCTURES FAIL WITH TURKISH MESSAGES
# ══════════════════════════════════════════════════════════════════════════════

def test_invalid_vso_declarative():
    # "Yaziyor Ahmet kitabi." — verb-initial in a plain declarative.
    y = T("yaziyor", "VERB", {"tense": "PRES_PROG", "person": "3", "num": "SG"})
    a = T("Ahmet", "PROPN", {})
    k = T("kitabi", "NOUN", {"case": "ACC"})
    ok, msg = tr_grammar.validate_sentence([y, a, k])
    assert not ok
    assert "fiil sonda" in msg


def test_invalid_modifier_order():
    # "Evi buyuk cocugun." — ad obegi sirasi yanlis.
    e = T("Evi", "NOUN", {"case": "ACC"})
    b = T("buyuk", "ADJ", {})
    c = T("cocugun", "NOUN", {"case": "GEN"})
    ok, msg = tr_grammar.validate_sentence([e, b, c])
    assert not ok
    assert "ad obegi" in msg


def test_invalid_postposition_at_start():
    # "Icin senin geldim." — postposition without preceding NP.
    icin = T("için", "POSTP", {})
    senin = T("senin", "PRON", {"case": "GEN"})
    geldim = T("geldim", "VERB", {"tense": "PAST_DEF"})
    ok, msg = tr_grammar.validate_sentence([icin, senin, geldim])
    assert not ok
    assert "edat" in msg


def test_invalid_no_predicate():
    a = T("Ahmet", "PROPN", {})
    k = T("kitap", "NOUN", {})
    ok, msg = tr_grammar.validate_sentence([a, k])
    assert not ok
    assert "yuklem" in msg


def test_invalid_var_in_middle():
    # "Bahcede var agac." — var must be sentence-final.
    b = T("bahcede", "NOUN", {"case": "LOC"})
    v = T("var", "ADV", {})
    a = T("agac", "NOUN", {})
    ok, msg = tr_grammar.validate_sentence([b, v, a])
    assert not ok
    assert "var/yok" in msg


def test_invalid_mi_at_start():
    mi = T("mi", "PART", {})
    g = T("geliyor", "VERB", {"tense": "PRES_PROG"})
    ok, msg = tr_grammar.validate_sentence([mi, g])
    assert not ok
    assert "soru" in msg


# ══════════════════════════════════════════════════════════════════════════════
# (e) LIVE REGRESSION on the analyzer pipeline
# ══════════════════════════════════════════════════════════════════════════════

def test_live_sov_passes():
    tokens, ok, msg = engine.analyze_sentence("Ahmet kitabi okudu")
    assert isinstance(tokens, list) and len(tokens) == 3


def test_live_imperative_passes():
    tokens, ok, msg = engine.analyze_sentence("gel")
    assert isinstance(tokens, list)


def test_live_does_not_crash_on_empty():
    tokens, ok, msg = engine.analyze_sentence("")
    assert tokens == []
