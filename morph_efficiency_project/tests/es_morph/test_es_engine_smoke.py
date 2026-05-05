"""
test_es_engine_smoke.py
-----------------------
Basic sanity checks for the Spanish morphology engine.

Run: python -m pytest morph_efficiency_project/tests/es_morph/test_es_engine_smoke.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import SpanishEngine
import pytest

engine = SpanishEngine()

# ── Root extraction tests ────────────────────────────────────────────────────

ROOT_CASES = [
    # Regular verbs
    ("hablar",    "hablar",  "VERB",  "infinitive -ar"),
    ("comer",     "comer",   "VERB",  "infinitive -er"),
    ("vivir",     "vivir",   "VERB",  "infinitive -ir"),
    ("hablando",  "hablar",  "VERB",  "gerund -ar"),
    ("comiendo",  "comer",   "VERB",  "gerund -er"),
    ("hablo",     "hablar",  "VERB",  "present 1SG -ar"),
    # Irregular verbs
    ("soy",       "ser",     "VERB",  "irregular ser"),
    ("voy",       "ir",      "VERB",  "irregular ir"),
    ("tengo",     "tener",   "VERB",  "irregular tener"),
    ("hago",      "hacer",   "VERB",  "irregular hacer"),
    ("digo",      "decir",   "VERB",  "irregular decir"),
    # Nouns
    ("gatos",     "gato",    "NOUN",  "plural noun -os"),
    ("flores",    "flor",    "NOUN",  "plural noun -es"),
    # Adjectives
    ("mejor",     "bueno",   "ADJ",   "irregular comparative"),
    ("peor",      "malo",    "ADJ",   "irregular comparative"),
    # Closed class
    ("el",        "el",      "DET",   "definite article"),
    ("en",        "en",      "ADP",   "preposition"),
    ("yo",        "yo",      "PRON",  "pronoun"),
    ("y",         "y",       "CONJ",  "conjunction"),
    ("no",        "no",      "ADV",   "adverb"),
    # Invariant nouns
    ("crisis",    "crisis",  "NOUN",  "invariant noun"),
    ("lunes",     "lunes",   "NOUN",  "day of week"),
    # Gender exceptions
    ("dia",       "dia",     "NOUN",  "masculine -a noun"),
    # Participles
    ("dicho",     "decir",   "VERB",  "irregular participle"),
    ("hecho",     "hacer",   "VERB",  "irregular participle"),
    ("visto",     "ver",     "VERB",  "irregular participle"),
    ("escrito",   "escribir","VERB",  "irregular participle"),
    # Clitics
    ("hacerlo",   "hacer",   "VERB",  "infinitive + clitic"),
    ("darselo",   "dar",     "VERB",  "infinitive + double clitic"),
]

@pytest.mark.parametrize("surface,exp_root,exp_pos,label", ROOT_CASES)
def test_root_and_pos(surface, exp_root, exp_pos, label):
    result = engine.analyze(surface)
    assert result.root == exp_root, (
        f"[{label}] root: got {result.root!r}, expected {exp_root!r}")
    assert result.pos == exp_pos, (
        f"[{label}] pos: got {result.pos!r}, expected {exp_pos!r}")
