"""
test_en_engine.py
-----------------
English morphology engine smoke tests.

Run: python -m pytest morph_efficiency_project/tests/en/test_en_engine.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import EnglishEngine
import pytest

engine = EnglishEngine()

# Format: (surface, expected_root, label)
CASES = [
    # Regular inflections
    ("running",   "run",       "gerund"),
    ("walked",    "walk",      "past tense"),
    ("cats",      "cat",       "plural"),
    ("happily",   "happi",     "adverb — derivation strips -ly"),
    # Irregular verbs
    ("went",      "go",        "irregular past"),
    ("children",  "child",     "irregular plural"),
    ("better",    "well",      "comparative"),
    # Derivational — engine strips known affixes
    ("happiness", "happi",     "derivation -ness stripped"),
    ("quickly",   "quick",     "derivation -ly stripped"),
    ("unkind",    "kind",      "prefix un- stripped"),
    # Compounds — split via en_compounds.json
    ("notebook",  "book",      "compound — head extracted"),
    ("football",  "ball",      "compound — head extracted"),
]

@pytest.mark.parametrize("surface,exp_root,label", CASES)
def test_en_engine(surface, exp_root, label):
    result = engine.analyze(surface)
    assert result.root == exp_root, (
        f"[{label}] root: got {result.root!r}, expected {exp_root!r}"
    )

if __name__ == "__main__":
    passed = failed = 0
    for surface, exp_root, label in CASES:
        result = engine.analyze(surface)
        ok = result.root == exp_root
        if ok:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL  {surface:<20s}  {label}  →  root={result.root!r} (exp {exp_root!r})")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
