"""
test_base_paths.py
------------------
Tests for the baseline pipeline's path resolution and config contracts.
These run without any data on disk — pure logic tests.

Run: python -m pytest morph_efficiency_project/tests/_base/test_base_paths.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import json
import pytest
from morph_efficiency_project.scripts.preprocess_baseline import get_paths, VOCAB_SIZE, CHAR_COVERAGE

# ── get_paths() contract ──────────────────────────────────────────────────────

@pytest.mark.parametrize("lang", ["en", "ar", "tr"])
def test_get_paths_keys(lang):
    """All required keys must be present."""
    p = get_paths(lang)
    for key in ("train_raw", "val_raw", "test_raw", "tok_dir", "proc_dir", "log_path"):
        assert key in p, f"Missing key {key!r} for lang={lang}"

@pytest.mark.parametrize("lang", ["en", "ar", "tr"])
def test_get_paths_lang_in_values(lang):
    """Every path must contain the language code so paths don't collide."""
    p = get_paths(lang)
    for key, val in p.items():
        assert lang in val, f"[{lang}] path for {key!r} does not contain lang code: {val!r}"

def test_get_paths_no_cross_contamination():
    """Paths for different languages must be distinct."""
    paths = {lang: get_paths(lang) for lang in ("en", "ar", "tr")}
    for key in ("train_raw", "tok_dir", "proc_dir"):
        values = [paths[l][key] for l in ("en", "ar", "tr")]
        assert len(set(values)) == 3, f"Paths for key={key!r} are not unique: {values}"

@pytest.mark.parametrize("lang", ["en", "ar", "tr"])
def test_get_paths_baseline_in_proc_dir(lang):
    """Processed dir must be under the 'baseline' subdirectory."""
    p = get_paths(lang)
    assert "baseline" in p["proc_dir"], (
        f"[{lang}] proc_dir should contain 'baseline': {p['proc_dir']!r}"
    )

@pytest.mark.parametrize("lang", ["en", "ar", "tr"])
def test_get_paths_base_in_tok_dir(lang):
    """Tokenizer dir must be the *_base variant, not *_morph."""
    p = get_paths(lang)
    assert p["tok_dir"].endswith(f"{lang}_base"), (
        f"[{lang}] tok_dir should end with '{lang}_base': {p['tok_dir']!r}"
    )

@pytest.mark.parametrize("lang", ["en", "ar", "tr"])
def test_get_paths_log_is_json(lang):
    """Log path must be a .json file."""
    p = get_paths(lang)
    assert p["log_path"].endswith(".json"), (
        f"[{lang}] log_path should be .json: {p['log_path']!r}"
    )

# ── Tokenizer constants ───────────────────────────────────────────────────────

def test_vocab_size_value():
    """Vocab size must be 32k — matches plan.md §5."""
    assert VOCAB_SIZE == 32_000

def test_char_coverage_range():
    """Character coverage must be in (0, 1]."""
    assert 0.0 < CHAR_COVERAGE <= 1.0

def test_char_coverage_high_enough():
    """Coverage must be ≥ 0.999 to handle Arabic/Turkish Unicode properly."""
    assert CHAR_COVERAGE >= 0.999, (
        f"CHAR_COVERAGE={CHAR_COVERAGE} is too low for Arabic/Turkish scripts"
    )
