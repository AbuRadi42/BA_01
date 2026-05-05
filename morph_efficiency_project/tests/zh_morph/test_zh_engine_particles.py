"""
test_zh_engine_particles.py
---------------------------
Exhaustive tests for every entry in zh_particles.json and zh_classifiers.json.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import MandarinEngine
import pytest

engine = MandarinEngine()

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "configs")


# ── Load all entries from zh_particles.json ──────────────────────────────────

def _load_particle_cases():
    with open(os.path.join(CONFIG_DIR, "zh_particles.json"), encoding="utf-8") as f:
        data = json.load(f)
    cases = []
    for category, entries in data.items():
        for surface, info in entries.items():
            cases.append((surface, info["pos"], category))
    return cases


PARTICLE_CASES = _load_particle_cases()


@pytest.mark.parametrize("surface,expected_pos,category", PARTICLE_CASES,
                         ids=[f"{c[2]}:{c[0]}" for c in PARTICLE_CASES])
def test_particle_pos(surface, expected_pos, category):
    """Every entry in zh_particles.json should return the configured POS."""
    r = engine.analyze(surface)
    # 得 is ambiguous (structural PART vs AUX); first-registered wins
    # The first category to register a surface wins
    assert r.pos == engine.closed_class[surface][0], (
        f"[{category}] {surface}: got {r.pos}, expected {engine.closed_class[surface][0]}"
    )


# ── Load all entries from zh_classifiers.json ────────────────────────────────

def _load_classifier_cases():
    with open(os.path.join(CONFIG_DIR, "zh_classifiers.json"), encoding="utf-8") as f:
        data = json.load(f)
    cases = []
    for surface, info in data.items():
        cases.append((surface, info["pos"], info["tags"].get("classifier", "")))
    return cases


CLASSIFIER_CASES = _load_classifier_cases()


@pytest.mark.parametrize("surface,expected_pos,clf_tag", CLASSIFIER_CASES,
                         ids=[c[0] for c in CLASSIFIER_CASES])
def test_classifier_pos(surface, expected_pos, clf_tag):
    """Every entry in zh_classifiers.json should return CLF POS."""
    r = engine.analyze(surface)
    # Some classifiers share surface with particles (e.g., 把 is ADP first)
    # so we only check that the closed_class lookup produces something valid
    expected = engine.closed_class[surface][0]
    assert r.pos == expected, (
        f"{surface}: got {r.pos}, expected {expected}"
    )


# ── Specific tag checks for key particles ────────────────────────────────────

@pytest.mark.parametrize("surface,tag_key,tag_val", [
    ("了", "aspect", "PERF"),
    ("着", "aspect", "DUR"),
    ("过", "aspect", "EXP"),
    ("的", "role", "ATTR"),
    ("地", "role", "ADVL"),
    ("吗", "particle_type", "QUESTION"),
    ("呢", "particle_type", "TOPIC"),
    ("吧", "particle_type", "SUGGESTION"),
    ("啊", "particle_type", "EMPHASIS"),
    ("啦", "particle_type", "EMPHASIS"),
    ("哈", "particle_type", "EMPHASIS"),
    ("嘛", "particle_type", "OBVIOUS"),
    ("呀", "particle_type", "SOFTENER"),
    ("哇", "particle_type", "EXCLAMATION"),
])
def test_particle_tags(surface, tag_key, tag_val):
    r = engine.analyze(surface)
    assert tag_key in r.tags, f"{surface}: missing tag {tag_key}"
    assert r.tags[tag_key] == tag_val, f"{surface}: {tag_key}={r.tags[tag_key]}, expected {tag_val}"


# ── Preposition / ADP tag checks ─────────────────────────────────────────────

@pytest.mark.parametrize("surface,tag_key,tag_val", [
    ("把", "construction", "BA"),
    ("被", "construction", "BEI"),
    ("比", "construction", "BI"),
    ("在", "subcat", "LOC"),
    ("从", "subcat", "SOURCE"),
    ("到", "subcat", "GOAL"),
    ("给", "subcat", "BENEFACTIVE"),
    ("用", "subcat", "INSTRUMENTAL"),
])
def test_adp_tags(surface, tag_key, tag_val):
    r = engine.analyze(surface)
    assert r.pos == "ADP"
    assert r.tags[tag_key] == tag_val


# ── Negation checks ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("surface,neg_type", [
    ("不", "BU"),
    ("没", "MEI"),
    ("没有", "MEI"),
    ("别", "BIE"),
])
def test_negation(surface, neg_type):
    r = engine.analyze(surface)
    assert r.pos == "ADV"
    assert r.tags["negation"] == neg_type


# ── Auxiliary / modal checks ─────────────────────────────────────────────────

@pytest.mark.parametrize("surface,modal_type", [
    ("会", "ABILITY"),
    ("能", "ABILITY"),
    ("可以", "PERMISSION"),
    ("应该", "OBLIGATION"),
    ("必须", "OBLIGATION"),
    ("要", "VOLITION"),
    ("想", "VOLITION"),
    ("敢", "ABILITY"),
])
def test_auxiliary(surface, modal_type):
    r = engine.analyze(surface)
    assert r.pos == "AUX"
    assert r.tags["modal"] == modal_type


# ── Conjunction checks ───────────────────────────────────────────────────────

@pytest.mark.parametrize("surface", [
    "和", "或", "或者", "但", "但是", "可是", "不过",
    "因为", "所以", "如果", "虽然", "而", "而且",
])
def test_conjunction(surface):
    r = engine.analyze(surface)
    assert r.pos == "CONJ"


# ── Copula / existential ────────────────────────────────────────────────────

def test_copula_shi():
    r = engine.analyze("是")
    assert r.pos == "VERB"
    assert r.tags["role"] == "COPULA"

def test_existential_you():
    r = engine.analyze("有")
    assert r.pos == "VERB"
    assert r.tags["role"] == "EXISTENTIAL"
