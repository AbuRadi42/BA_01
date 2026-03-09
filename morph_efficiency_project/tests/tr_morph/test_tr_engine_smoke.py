"""
test_tr_engine.py
-----------------
Turkish morphology engine smoke tests.

Run: python -m pytest morph_efficiency_project/tests/tr/test_tr_engine.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import TurkishEngine
import pytest

engine = TurkishEngine()

# Format: (surface, expected_root, label)
CASES = [
    # Nominal suffixes
    ("evler",     "ev",    "plural -ler"),
    ("evde",      "ev",    "locative -de"),
    ("evden",     "evd",   "ablative -den"),
    ("evi",       "ev",    "accusative -i"),
    ("eve",       "ev",    "dative -e"),
    # Possessive
    ("evim",      "ev",    "1sg poss -im"),
    ("evin",      "ev",    "2sg poss -in"),
    # Verbal suffixes
    ("gidiyorum", "gid",   "present continuous 1sg"),
    ("gitti",     "gi",    "past 3sg"),
    ("gidecek",   "gid",   "future"),
    # Negation
    ("gitmiyor",  "git",   "negative present"),
    ("gitmedi",   "git",   "negative past"),
]

@pytest.mark.parametrize("surface,exp_root,label", CASES)
def test_tr_engine(surface, exp_root, label):
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
