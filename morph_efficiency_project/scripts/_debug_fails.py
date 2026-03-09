"""
_debug_fails.py
---------------
Interactive debugger for Arabic engine failures.
Edit the `failing_labels` list to target specific cases.
Keep this file — it's a safety net for future regressions.

Run: python morph_efficiency_project/scripts/_debug_fails.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from morph_efficiency_project.scripts.preprocess_morph import ArabicEngine

e = ArabicEngine()

# ── Edit these to target specific failing cases ───────────────────────────────
PROBE = [
    # (surface, expected_root, label)
    # Add cases here when debugging a regression, e.g.:
    # ("ظَلَّ", "ظلل", "geminate dhalla"),
]

# ── Or run against the full test_ar_engine_core CASES list ───────────────────
def debug_from_core():
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location(
        "test_ar_engine_regression",
        pathlib.Path(__file__).parent.parent / "tests" / "ar_morph" / "test_ar_engine_regression.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CASES

if __name__ == "__main__":
    cases = PROBE if PROBE else debug_from_core()
    fails = 0
    for item in cases:
        surface, exp_root = item[0], item[1]
        label = item[3] if len(item) > 3 else item[2]
        ti = e.analyze(surface)
        stem, clitics = e._step_a(surface)
        ok = ti.root == exp_root
        if not ok:
            fails += 1
        mark = "PASS" if ok else "FAIL"
        print(f"{mark}  {surface:<24} root={ti.root!r:<14} exp={exp_root!r:<14} tmpl={ti.template!r:<26} {label}")
        if not ok:
            print(f"       stem={stem!r}  clitics={clitics}")
            print(f"       cons={e._extract_consonants(stem)!r}")
    print(f"\n{fails} failures / {len(cases)} total")
