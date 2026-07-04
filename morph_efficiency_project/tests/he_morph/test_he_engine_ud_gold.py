"""
test_he_engine_ud_gold.py
-------------------------
Aggregate validation of the Hebrew engine against Universal Dependencies gold
(UD_Hebrew-HTB). A 400-sentence sample of the UD dev split is bundled offline at
fixtures/he_htb_sample.conllu so this test runs with no network.

These thresholds are REGRESSION GUARDS pinned a few points below the measured
milestone-1 accuracy. They are deliberately honest: they encode what the engine
actually achieves, not an aspiration. If a change pushes accuracy below the
guard, the test fails and the drop must be explained.

Measured on the bundled sample (milestone 1):
    POS     0.629      gender 0.926     number 0.856
    tense   0.755      binyan 0.702 (raw classifier over gold verbs)

Validation boundary:
  - POS, gender, number, tense, definiteness, HebBinyan are UD-annotated -> real
    gold comparison.
  - The shoresh (root) is NOT in UD; it is not scored here.
  - Only standalone (non multiword-token) words are scored. UD segments every
    productive proclitic (ה/ב/ל/כ/מ/ו/ש) into its own token; the milestone-1
    engine does not split those, so scoring the glued MWT surfaces would test
    an unbuilt feature. That segmentation is an explicit milestone-2 gap.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from morph_efficiency_project.scripts.engines import HebrewEngine  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "he_htb_sample.conllu")

_GENDER = {"Masc": "M", "Fem": "F"}
_NUMBER = {"Sing": "SG", "Plur": "PL", "Dual": "DU"}
_TENSE = {"Past": "PAST", "Fut": "FUT", "Pres": "PRES"}


def _read_standalone(path):
    """Yield (surface, gold_pos, feats) for standalone words (skip MWT parts)."""
    skip_until = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                skip_until = 0
                continue
            c = line.rstrip("\n").split("\t")
            if len(c) < 6:
                continue
            if "-" in c[0]:
                skip_until = int(c[0].split("-")[1])
                continue
            if "." in c[0]:
                continue
            if int(c[0]) <= skip_until:
                continue
            feats = dict(x.split("=") for x in c[5].split("|") if "=" in x)
            yield c[1], c[3], feats


@pytest.fixture(scope="module")
def scores():
    engine = HebrewEngine()
    n = pos_ok = 0
    g = [0, 0]
    num = [0, 0]
    tn = [0, 0]
    binyan = [0, 0]
    for surface, gpos, feats in _read_standalone(FIXTURE):
        if gpos in ("PUNCT", "X", "PROPN", "SYM", "INTJ"):
            continue
        info = engine.analyze(surface)
        n += 1
        if info.pos == gpos:
            pos_ok += 1
        if "Gender" in feats and "gender" in info.tags:
            g[1] += 1
            g[0] += info.tags["gender"] == _GENDER.get(feats["Gender"].split(",")[0])
        if "Number" in feats and "num" in info.tags:
            num[1] += 1
            num[0] += info.tags["num"] == _NUMBER.get(feats["Number"].split(",")[0])
        if "Tense" in feats and "tense" in info.tags:
            tn[1] += 1
            tn[0] += info.tags["tense"] == _TENSE.get(feats["Tense"])
        if "HebBinyan" in feats:
            stem, _ = engine._strip_proclitics(surface)
            binyan[1] += 1
            binyan[0] += engine._classify_binyan(stem) == feats["HebBinyan"]
    return {
        "n": n,
        "pos": pos_ok / n,
        "gender": g[0] / g[1],
        "number": num[0] / num[1],
        "tense": tn[0] / tn[1],
        "binyan": binyan[0] / binyan[1],
    }


def test_sample_is_loaded(scores):
    assert scores["n"] > 3000, "UD fixture did not load enough tokens"


def test_pos_accuracy(scores):
    assert scores["pos"] >= 0.58, f"POS regressed: {scores['pos']:.3f}"


def test_gender_accuracy(scores):
    assert scores["gender"] >= 0.88, f"gender regressed: {scores['gender']:.3f}"


def test_number_accuracy(scores):
    assert scores["number"] >= 0.80, f"number regressed: {scores['number']:.3f}"


def test_tense_accuracy(scores):
    assert scores["tense"] >= 0.68, f"tense regressed: {scores['tense']:.3f}"


def test_binyan_accuracy(scores):
    assert scores["binyan"] >= 0.63, f"binyan regressed: {scores['binyan']:.3f}"
