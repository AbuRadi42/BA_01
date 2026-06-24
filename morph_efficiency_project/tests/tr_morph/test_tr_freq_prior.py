"""
test_tr_freq_prior.py
---------------------
Contract for the corpus-frequency prior added to homonym disambiguation.

The prior is a data-driven tie-break that generalises the hand-curated keep-list.
It fires in two structurally-licensed situations only:

  FP-1  A surface carries an unambiguous finite/passive verbal ending but the
        dictionary guard pinned a coincidental homonymous NOUN stem. The verb
        root is recovered (istemiştir -> iste, not the noun istem;
        sağlamıştır -> sağla, not the adjective sağlam).

  FP-2  A frequent whole word is over-stripped into a shorter stem + a bare
        POSSESSIVE with no overt case ending (an implausible "my X" reading).
        The whole word is restored (tam -> tam, not ta; ölüm -> ölüm, not öl).

The prior must NEVER disturb legitimate inflection or derivation, and the
frequency table is optional: with it absent the engine must still run.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import TurkishEngine
import pytest

engine = TurkishEngine()


# FP-1: finite verbal ending overrides a homonymous noun stem.
FP1_VERB_CASES = [
    ("istemiştir",    "iste",   "noun istem vs verb iste"),
    ("istemişti",     "iste",   "noun istem vs verb iste"),
    ("sağlamıştır",   "sağla",  "adj sağlam vs verb sağla (verb rarer in isolation)"),
    ("toplamıştır",   "topla",  "noun toplam vs verb topla"),
    ("başarmıştı",    "başar",  "noun başarım vs verb başar"),
    ("söylemişti",    "söyle",  "noun söylem vs verb söyle"),
    ("getirilmesini", "getir",  "passive nominalisation -> verb root getir"),
    ("vermişti",      "ver",    "noun verim vs verb ver"),
    ("görmüştü",      "gör",    "noun görüm vs verb gör"),
]


@pytest.mark.parametrize("surface,expected,why", FP1_VERB_CASES)
def test_fp1_finite_verb_overrides_noun_homonym(surface, expected, why):
    assert engine.analyze(surface).root == expected, why


# FP-2: frequent whole word restored over a bare-possessive over-strip.
FP2_WHOLE_CASES = [
    ("tam",  "tam",  "ta+1SG is spurious; tam is the lemma"),
    ("ölüm", "ölüm", "öl+1SG is spurious; ölüm is the lemma"),
    ("önem", "önem", "öne+1SG is spurious; önem is the lemma"),
]


@pytest.mark.parametrize("surface,expected,why", FP2_WHOLE_CASES)
def test_fp2_restores_frequent_whole_word(surface, expected, why):
    assert engine.analyze(surface).root == expected, why


# The prior must not regress clean inflection/derivation.
NO_REGRESSION_CASES = [
    ("geliyorum",    "gel",   "present continuous, verb root preserved"),
    ("evlerinizden", "ev",    "stacked nominal inflection"),
    ("getirerek",    "getir", "converb, verb root preserved"),
    ("kitapları",    "kitap", "plural+accusative"),
    ("yazmıştır",    "yaz",   "finite verb whose root is already a verb"),
    ("olmuştur",     "ol",    "ol- analytic tense"),
]


@pytest.mark.parametrize("surface,expected,why", NO_REGRESSION_CASES)
def test_prior_does_not_regress_inflection(surface, expected, why):
    assert engine.analyze(surface).root == expected, why


def test_engine_runs_without_frequency_table(tmp_path):
    """The prior is optional: an engine pointed at a config dir with no
    tr_freq.tsv must still construct and analyse (graceful degradation)."""
    import json, shutil
    src = os.path.join(os.path.dirname(__file__), "..", "..", "configs")
    dst = tmp_path / "configs"
    dst.mkdir()
    for fn in os.listdir(src):
        if fn == "tr_freq.tsv":
            continue  # deliberately omit the frequency table
        s = os.path.join(src, fn)
        if os.path.isfile(s):
            shutil.copy(s, dst / fn)
    # Reset the module-level frequency cache so the omission takes effect.
    import morph_efficiency_project.scripts.engines.tr_engine as M
    saved = M._FREQ_CACHE
    M._FREQ_CACHE = None
    try:
        eng = M.TurkishEngine(config_dir=str(dst))
        assert eng._freq == {}
        # Without the prior the engine still analyses; the verb-homonym is left
        # at the dictionary-guard reading rather than crashing.
        assert eng.analyze("geliyorum").root == "gel"
        assert eng.analyze("istemiştir").root  # no exception, some lemma
    finally:
        M._FREQ_CACHE = saved
