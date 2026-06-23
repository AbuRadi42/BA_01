"""
test_en_engine_inflection.py
----------------------------
EnglishEngine — Step A: inflectional morphology.

Covers:
  - All irregular verbs (past, past-participle, 3SG-present)
  - All irregular nouns (umlaut, -en, zero-plural, Latin/Greek, pluralia tantum)
  - Regular -ing (double-consonant, silent-e, plain)
  - Regular -ed (double-consonant, plain)
  - Regular plural -s / -es / -ies
  - Comparative -er / superlative -est
  - Possessive 's
  - POS and tense/aspect/number tag assertions

Run: python -m pytest morph_efficiency_project/tests/en_morph/test_en_engine_inflection.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import pytest
from morph_efficiency_project.scripts.engines import EnglishEngine

engine = EnglishEngine()

def r(w):   return engine.analyze(w).root
def pos(w): return engine.analyze(w).pos
def t(w):   return engine.analyze(w).tags

# ══════════════════════════════════════════════════════════════════════════════
# 1. IRREGULAR VERBS — past tense
# ══════════════════════════════════════════════════════════════════════════════

IRREG_PAST = [
    ("went",       "go"),    ("said",       "say"),   ("saw",        "see"),
    ("came",       "come"),  ("got",        "get"),   ("made",       "make"),
    ("knew",       "know"),  ("thought",    "think"), ("took",       "take"),
    ("gave",       "give"),  ("found",      "find"),  ("told",       "tell"),
    ("became",     "become"),("showed",     "show"),  ("left",       "leave"),
    ("felt",       "feel"),  ("put",        "put"),   ("brought",    "bring"),
    ("began",      "begin"), ("kept",       "keep"),  ("held",       "hold"),
    ("wrote",      "write"), ("stood",      "stand"), ("heard",      "hear"),
    ("let",        "let"),   ("meant",      "mean"),  ("set",        "set"),
    ("met",        "meet"),  ("ran",        "run"),   ("paid",       "pay"),
    ("sat",        "sit"),   ("spoke",      "speak"), ("lay",        "lie"),
    ("led",        "lead"),  ("read",       "read"),  ("grew",       "grow"),
    ("lost",       "lose"),  ("fell",       "fall"),  ("sent",       "send"),
    ("built",      "build"), ("understood", "understand"), ("drew",  "draw"),
    ("broke",      "break"), ("spent",      "spend"), ("cut",        "cut"),
    ("rose",       "rise"),  ("drove",      "drive"), ("bought",     "buy"),
    ("wore",       "wear"),  ("chose",      "choose"),("won",        "win"),
    ("caught",     "catch"), ("taught",     "teach"), ("fought",     "fight"),
    ("threw",      "throw"), ("sang",       "sing"),  ("swam",       "swim"),
    ("rang",       "ring"),  ("drank",      "drink"), ("ate",        "eat"),
    ("forgot",     "forget"),("froze",      "freeze"),("hid",        "hide"),
    ("hit",        "hit"),   ("hurt",       "hurt"),  ("stole",      "steal"),
    ("shook",      "shake"), ("woke",       "wake"),  ("rode",       "ride"),
    ("bit",        "bite"),  ("blew",       "blow"),  ("flew",       "fly"),
    ("bore",       "bear"),  ("swore",      "swear"), ("tore",       "tear"),
    ("wove",       "weave"), ("wound",      "wind"),  ("bound",      "bind"),
    ("ground",     "grind"), ("struck",     "strike"),("stuck",      "stick"),
]

@pytest.mark.parametrize("surface,expected", IRREG_PAST)
def test_irreg_past(surface, expected):
    assert r(surface) == expected
    assert t(surface)["tense"] == "PAST"
    assert pos(surface) == "VERB"

# ══════════════════════════════════════════════════════════════════════════════
# 2. IRREGULAR VERBS — past participle
# ══════════════════════════════════════════════════════════════════════════════

IRREG_PERF = [
    ("gone",      "go"),    ("seen",      "see"),   ("gotten",    "get"),
    ("known",     "know"),  ("taken",     "take"),  ("given",     "give"),
    ("become",    "become"),("shown",     "show"),  ("begun",     "begin"),
    ("written",   "write"), ("grown",     "grow"),  ("fallen",    "fall"),
    ("drawn",     "draw"),  ("broken",    "break"), ("risen",     "rise"),
    ("driven",    "drive"), ("worn",      "wear"),  ("chosen",    "choose"),
    ("thrown",    "throw"), ("sung",      "sing"),  ("swum",      "swim"),
    ("rung",      "ring"),  ("drunk",     "drink"), ("eaten",     "eat"),
    ("forgotten", "forget"),("frozen",    "freeze"),("hidden",    "hide"),
    ("stolen",    "steal"), ("shaken",    "shake"), ("woken",     "wake"),
    ("ridden",    "ride"),  ("bitten",    "bite"),  ("blown",     "blow"),
    ("flown",     "fly"),   ("borne",     "bear"),  ("born",      "bear"),
    ("sworn",     "swear"), ("torn",      "tear"),  ("woven",     "weave"),
    ("stricken",  "strike"),("spoken",    "speak"), ("lain",      "lie"),
    ("run",       "run"),   ("come",      "come"),  ("been",      "be"),
    ("done",      "do"),
]

@pytest.mark.parametrize("surface,expected", IRREG_PERF)
def test_irreg_perf(surface, expected):
    assert r(surface) == expected
    assert t(surface)["tense"] == "PAST"
    assert t(surface)["aspect"] == "PERF"
    assert pos(surface) == "VERB"

# ══════════════════════════════════════════════════════════════════════════════
# 3. IRREGULAR VERBS — 3SG present / auxiliaries
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,expected", [
    ("goes", "go"), ("says", "say"), ("has", "have"), ("does", "do"),
    ("is",   "be"), ("was",  "be"),  ("were","be"),   ("am",   "be"),
    ("are",  "be"), ("had",  "have"),("did", "do"),
])
def test_irreg_aux(surface, expected):
    assert r(surface) == expected
    assert pos(surface) == "VERB"

# ══════════════════════════════════════════════════════════════════════════════
# 4. IRREGULAR NOUNS
# ══════════════════════════════════════════════════════════════════════════════

IRREG_NOUNS = [
    # Umlaut
    ("men","man"), ("women","woman"), ("feet","foot"), ("teeth","tooth"),
    ("geese","goose"), ("mice","mouse"), ("lice","louse"),
    # -en
    ("children","child"), ("oxen","ox"),
    # Zero-plural
    ("sheep","sheep"), ("fish","fish"), ("deer","deer"), ("moose","moose"),
    ("series","series"), ("species","species"), ("means","means"),
    # Latin -a
    ("criteria","criterion"), ("phenomena","phenomenon"), ("data","datum"),
    ("media","medium"), ("bacteria","bacterium"), ("curricula","curriculum"),
    ("memoranda","memorandum"), ("strata","stratum"), ("errata","erratum"),
    ("spectra","spectrum"), ("schemata","schema"),
    # Latin -i
    ("alumni","alumnus"), ("cacti","cactus"), ("foci","focus"),
    ("nuclei","nucleus"), ("radii","radius"), ("stimuli","stimulus"),
    ("syllabi","syllabus"), ("fungi","fungus"), ("loci","locus"),
    ("tori","torus"), ("moduli","modulus"), ("calculi","calculus"),
    ("bacilli","bacillus"),
    # Latin -ices
    ("indices","index"), ("matrices","matrix"), ("vertices","vertex"),
    ("appendices","appendix"), ("cortices","cortex"), ("vortices","vortex"),
    # Greek -es
    ("theses","thesis"), ("hypotheses","hypothesis"), ("analyses","analysis"),
    ("crises","crisis"), ("bases","basis"), ("axes","axis"),
    ("synopses","synopsis"), ("parentheses","parenthesis"),
    ("ellipses","ellipsis"), ("diagnoses","diagnosis"), ("prognoses","prognosis"),
    # Pluralia tantum
    ("scissors","scissors"), ("trousers","trousers"), ("pants","pants"),
    ("jeans","jeans"), ("glasses","glasses"), ("pliers","pliers"),
    ("tongs","tongs"),
]

@pytest.mark.parametrize("surface,expected", IRREG_NOUNS)
def test_irreg_nouns(surface, expected):
    assert r(surface) == expected
    assert t(surface)["num"] == "PL"
    assert pos(surface) == "NOUN"

# ══════════════════════════════════════════════════════════════════════════════
# 5. REGULAR -ing
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,expected,label", [
    # Double-consonant restoration
    ("running",   "run",   "double-cons run"),
    ("stopping",  "stop",  "double-cons stop"),
    ("planning",  "plan",  "double-cons plan"),
    ("sitting",   "sit",   "double-cons sit"),
    ("swimming",  "swim",  "double-cons swim"),
    ("hitting",   "hit",   "double-cons hit"),
    ("cutting",   "cut",   "double-cons cut"),
    ("getting",   "get",   "double-cons get"),
    # Silent-e restoration
    ("making",    "make",  "silent-e make"),
    ("writing",   "write", "silent-e write"),
    ("dancing",   "dance", "silent-e dance"),
    ("taking",    "take",  "silent-e take"),
    ("giving",    "give",  "silent-e give"),
    # Plain
    ("walking", "walk", "plain walk"),
    ("talking", "talk", "plain talk"),
    ("reading", "read", "plain read"),
])
def test_ing(surface, expected, label):
    assert r(surface) == expected, f"[{label}] got {r(surface)!r}"
    assert t(surface) == {"tense": "PRES", "aspect": "PROG"}
    assert pos(surface) == "VERB"

# ══════════════════════════════════════════════════════════════════════════════
# 6. REGULAR -ed
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,expected,label", [
    # Double-consonant
    ("stopped",  "stop",  "double-cons stop"),
    ("planned",  "plan",  "double-cons plan"),
    ("dropped",  "drop",  "double-cons drop"),
    ("grabbed",  "grab",  "double-cons grab"),
    # Plain
    ("walked",   "walk",  "plain walk"),
    ("talked",   "talk",  "plain talk"),
    ("jumped",   "jump",  "plain jump"),
    ("helped",   "help",  "plain help"),
])
def test_ed(surface, expected, label):
    assert r(surface) == expected, f"[{label}] got {r(surface)!r}"
    assert t(surface)["tense"] == "PAST"
    assert pos(surface) == "VERB"

# ══════════════════════════════════════════════════════════════════════════════
# 7. REGULAR PLURAL
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,expected,label", [
    ("cats",     "cat",    "-s"),
    ("dogs",     "dog",    "-s"),
    ("books",    "book",   "-s"),
    ("boxes",    "box",    "-es"),
    ("churches", "church", "-es"),
    ("dishes",   "dish",   "-es"),
    ("babies",   "baby",   "-ies"),
    ("cities",   "city",   "-ies"),
    ("ladies",   "lady",   "-ies"),
    ("flies",    "fly",    "-ies"),
])
def test_plural(surface, expected, label):
    assert r(surface) == expected, f"[{label}] got {r(surface)!r}"
    assert t(surface)["num"] == "PL"
    assert pos(surface) == "NOUN"

# ══════════════════════════════════════════════════════════════════════════════
# 8. COMPARATIVE / SUPERLATIVE
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,expected,degree", [
    ("faster",   "fast",  "COMP"),
    ("slower",   "slow",  "COMP"),
    ("taller",   "tall",  "COMP"),
    ("fastest",  "fast",  "SUPER"),
    ("slowest",  "slow",  "SUPER"),
    ("tallest",  "tall",  "SUPER"),
])
def test_comparative(surface, expected, degree):
    assert r(surface) == expected
    assert t(surface)["degree"] == degree
    assert pos(surface) == "ADJ"

# ══════════════════════════════════════════════════════════════════════════════
# 9. POSSESSIVE
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,expected", [
    ("cat's",    "cat"),
    ("dog's",    "dog"),
    ("teacher's","teacher"),
    ("child's",  "child"),
])
def test_possessive(surface, expected):
    assert r(surface) == expected
    assert t(surface) == {"poss": "YES"}
    assert pos(surface) == "NOUN"

# ══════════════════════════════════════════════════════════════════════════════
# 10. FALSE-POSITIVE GUARDS
# ══════════════════════════════════════════════════════════════════════════════

def test_no_strip_ring():
    assert r("ring") == "ring"   # -ing but len <= 5

def test_no_strip_red():
    assert r("red") == "red"     # -ed but len <= 4

def test_no_strip_class():
    assert r("class") == "class" # -ss ending, no plural strip

def test_no_strip_her():
    assert r("her") == "her"     # -er but len <= 4

def test_irreg_best():
    assert r("best") == "good"   # engine override: best -> good ADJ SUPER
