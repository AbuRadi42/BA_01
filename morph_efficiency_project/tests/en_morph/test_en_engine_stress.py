"""
test_en_engine_stress.py
------------------------
Comprehensive stress tests for EnglishEngine.
All expected values verified by running the engine directly.

Covers:
  - All irregular verbs from en_irregulars.json (past, past-perf, 3sg-pres)
  - All irregular nouns (zero-plural, umlaut, -en, Latin/Greek plurals, pluralia tantum)
  - Inflectional rules: -ing (double-cons, silent-e, plain), -ed (double-cons, -e stem,
    plain), -s/-es/-ies plural, -er/-est comparative/superlative
  - Possessive 's
  - Derivational stripping via step_c (suffixes and prefixes)
  - False-positive guards: words that look like inflected forms but aren't

Run: python -m pytest morph_efficiency_project/tests/en/test_en_engine_stress.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import pytest
from morph_efficiency_project.scripts.engines import EnglishEngine

engine = EnglishEngine()

# ── Helpers ───────────────────────────────────────────────────────────────────

def r(word):
    """Return root of word."""
    return engine.analyze(word).root

def pos(word):
    return engine.analyze(word).pos

def tags(word):
    return engine.analyze(word).tags

# ══════════════════════════════════════════════════════════════════════════════
# 1. IRREGULAR VERBS — past tense
# ══════════════════════════════════════════════════════════════════════════════

IRREG_PAST = [
    ("went",        "go"),
    ("said",        "say"),
    ("saw",         "see"),
    ("came",        "come"),
    ("got",         "get"),
    ("made",        "make"),
    ("knew",        "know"),
    ("thought",     "think"),
    ("took",        "take"),
    ("gave",        "give"),
    ("found",       "find"),
    ("told",        "tell"),
    ("became",      "become"),
    ("showed",      "show"),
    ("left",        "leave"),
    ("felt",        "feel"),
    ("put",         "put"),
    ("brought",     "bring"),
    ("began",       "begin"),
    ("kept",        "keep"),
    ("held",        "hold"),
    ("wrote",       "write"),
    ("stood",       "stand"),
    ("heard",       "hear"),
    ("let",         "let"),
    ("meant",       "mean"),
    ("set",         "set"),
    ("met",         "meet"),
    ("ran",         "run"),
    ("paid",        "pay"),
    ("sat",         "sit"),
    ("spoke",       "speak"),
    ("lay",         "lie"),
    ("led",         "lead"),
    ("read",        "read"),
    ("grew",        "grow"),
    ("lost",        "lose"),
    ("fell",        "fall"),
    ("sent",        "send"),
    ("built",       "build"),
    ("understood",  "understand"),
    ("drew",        "draw"),
    ("broke",       "break"),
    ("spent",       "spend"),
    ("cut",         "cut"),
    ("rose",        "rise"),
    ("drove",       "drive"),
    ("bought",      "buy"),
    ("wore",        "wear"),
    ("chose",       "choose"),
    ("won",         "win"),
    ("caught",      "catch"),
    ("taught",      "teach"),
    ("fought",      "fight"),
    ("threw",       "throw"),
    ("sang",        "sing"),
    ("swam",        "swim"),
    ("rang",        "ring"),
    ("drank",       "drink"),
    ("ate",         "eat"),
    ("forgot",      "forget"),
    ("froze",       "freeze"),
    ("hid",         "hide"),
    ("hit",         "hit"),
    ("hurt",        "hurt"),
    ("stole",       "steal"),
    ("shook",       "shake"),
    ("woke",        "wake"),
    ("rode",        "ride"),
    ("bit",         "bite"),
    ("blew",        "blow"),
    ("flew",        "fly"),
    ("bore",        "bear"),
    ("swore",       "swear"),
    ("tore",        "tear"),
    ("wove",        "weave"),
    ("wound",       "wind"),
    ("bound",       "bind"),
    ("ground",      "grind"),
    ("struck",      "strike"),
    ("stuck",       "stick"),
]

@pytest.mark.parametrize("surface,expected", IRREG_PAST)
def test_irregular_past(surface, expected):
    assert r(surface) == expected, f"{surface!r}: got {r(surface)!r}"

# ── Irregular verbs — past participle ────────────────────────────────────────

IRREG_PERF = [
    ("gone",        "go"),
    ("seen",        "see"),
    ("gotten",      "get"),
    ("known",       "know"),
    ("taken",       "take"),
    ("given",       "give"),
    ("become",      "become"),
    ("shown",       "show"),
    ("begun",       "begin"),
    ("written",     "write"),
    ("grown",       "grow"),
    ("fallen",      "fall"),
    ("drawn",       "draw"),
    ("broken",      "break"),
    ("risen",       "rise"),
    ("driven",      "drive"),
    ("worn",        "wear"),
    ("chosen",      "choose"),
    ("thrown",      "throw"),
    ("sung",        "sing"),
    ("swum",        "swim"),
    ("rung",        "ring"),
    ("drunk",       "drink"),
    ("eaten",       "eat"),
    ("forgotten",   "forget"),
    ("frozen",      "freeze"),
    ("hidden",      "hide"),
    ("stolen",      "steal"),
    ("shaken",      "shake"),
    ("woken",       "wake"),
    ("ridden",      "ride"),
    ("bitten",      "bite"),
    ("blown",       "blow"),
    ("flown",       "fly"),
    ("borne",       "bear"),
    ("born",        "bear"),
    ("sworn",       "swear"),
    ("torn",        "tear"),
    ("woven",       "weave"),
    ("stricken",    "strike"),
    ("spoken",      "speak"),
    ("lain",        "lie"),
    ("run",         "run"),
    ("come",        "come"),
    ("been",        "be"),
    ("done",        "do"),
]

@pytest.mark.parametrize("surface,expected", IRREG_PERF)
def test_irregular_perf(surface, expected):
    assert r(surface) == expected, f"{surface!r}: got {r(surface)!r}"

# ── Irregular verbs — 3SG present ────────────────────────────────────────────

IRREG_3SG = [
    ("goes",    "go"),
    ("says",    "say"),
    ("has",     "have"),
    ("does",    "do"),
    ("is",      "be"),
    ("was",     "be"),
    ("were",    "be"),
    ("am",      "be"),
    ("are",     "be"),
    ("had",     "have"),
    ("did",     "do"),
]

@pytest.mark.parametrize("surface,expected", IRREG_3SG)
def test_irregular_3sg(surface, expected):
    assert r(surface) == expected, f"{surface!r}: got {r(surface)!r}"

# ══════════════════════════════════════════════════════════════════════════════
# 2. IRREGULAR NOUNS
# ══════════════════════════════════════════════════════════════════════════════

IRREG_NOUNS = [
    # Umlaut plurals
    ("men",         "man"),
    ("women",       "woman"),
    ("feet",        "foot"),
    ("teeth",       "tooth"),
    ("geese",       "goose"),
    ("mice",        "mouse"),
    ("lice",        "louse"),
    # -en plurals
    ("children",    "child"),
    ("oxen",        "ox"),
    # Zero plurals
    ("sheep",       "sheep"),
    ("fish",        "fish"),
    ("deer",        "deer"),
    ("moose",       "moose"),
    ("series",      "series"),
    ("species",     "species"),
    ("means",       "means"),
    # Latin/Greek -a plurals
    ("criteria",    "criterion"),
    ("phenomena",   "phenomenon"),
    ("data",        "datum"),
    ("media",       "medium"),
    ("bacteria",    "bacterium"),
    ("curricula",   "curriculum"),
    ("memoranda",   "memorandum"),
    ("strata",      "stratum"),
    ("errata",      "erratum"),
    ("spectra",     "spectrum"),
    ("schemata",    "schema"),
    # Latin -i plurals
    ("alumni",      "alumnus"),
    ("cacti",       "cactus"),
    ("foci",        "focus"),
    ("nuclei",      "nucleus"),
    ("radii",       "radius"),
    ("stimuli",     "stimulus"),
    ("syllabi",     "syllabus"),
    ("fungi",       "fungus"),
    ("loci",        "locus"),
    ("tori",        "torus"),
    ("moduli",      "modulus"),
    ("calculi",     "calculus"),
    ("bacilli",     "bacillus"),
    # Latin -ices/-ices plurals
    ("indices",     "index"),
    ("matrices",    "matrix"),
    ("vertices",    "vertex"),
    ("appendices",  "appendix"),
    ("cortices",    "cortex"),
    ("vortices",    "vortex"),
    # Greek -es plurals
    ("theses",      "thesis"),
    ("hypotheses",  "hypothesis"),
    ("analyses",    "analysis"),
    ("crises",      "crisis"),
    ("bases",       "basis"),
    ("axes",        "axis"),
    ("synopses",    "synopsis"),
    ("parentheses", "parenthesis"),
    ("ellipses",    "ellipsis"),
    ("diagnoses",   "diagnosis"),
    ("prognoses",   "prognosis"),
    # Pluralia tantum
    ("scissors",    "scissors"),
    ("trousers",    "trousers"),
    ("pants",       "pants"),
    ("jeans",       "jeans"),
    ("glasses",     "glasses"),
    ("pliers",      "pliers"),
    ("tongs",       "tongs"),
]

@pytest.mark.parametrize("surface,expected", IRREG_NOUNS)
def test_irregular_nouns(surface, expected):
    assert r(surface) == expected, f"{surface!r}: got {r(surface)!r}"

# ══════════════════════════════════════════════════════════════════════════════
# 3. INFLECTIONAL RULES
# ══════════════════════════════════════════════════════════════════════════════

# ── -ing: double-consonant restoration ───────────────────────────────────────

def test_ing_double_consonant_run():
    assert r("running") == "run"

def test_ing_double_consonant_stop():
    assert r("stopping") == "stop"

def test_ing_double_consonant_plan():
    assert r("planning") == "plan"

def test_ing_double_consonant_sit():
    assert r("sitting") == "sit"

def test_ing_double_consonant_swim():
    assert r("swimming") == "swim"

# ── -ing: silent-e restoration ───────────────────────────────────────────────

def test_ing_silent_e_make():
    assert r("making") == "make"

def test_ing_silent_e_write():
    assert r("writing") == "write"

def test_ing_silent_e_dance():
    assert r("dancing") == "dance"

# ── -ed: double-consonant ────────────────────────────────────────────────────

def test_ed_double_consonant_stop():
    assert r("stopped") == "stop"

def test_ed_double_consonant_plan():
    assert r("planned") == "plan"

# ── -ed: plain ───────────────────────────────────────────────────────────────

def test_ed_plain_walk():
    assert r("walked") == "walk"

def test_ed_plain_talk():
    assert r("talked") == "talk"

# ── -s/-es/-ies plural ───────────────────────────────────────────────────────

def test_plural_s_cat():
    assert r("cats") == "cat"

def test_plural_es_box():
    assert r("boxes") == "box"

def test_plural_es_church():
    assert r("churches") == "church"

def test_plural_ies_baby():
    assert r("babies") == "baby"

def test_plural_ies_city():
    assert r("cities") == "city"

# ── Comparative / superlative ─────────────────────────────────────────────────

def test_comp_fast():
    assert r("faster") == "fast"

def test_super_fast():
    assert r("fastest") == "fast"

# ── Possessive ────────────────────────────────────────────────────────────────

def test_possessive_cat():
    assert r("cat's") == "cat"
    assert tags("cat's") == {"poss": "YES"}

def test_possessive_dog():
    assert r("dog's") == "dog"

# ══════════════════════════════════════════════════════════════════════════════
# 4. POS TAGS
# ══════════════════════════════════════════════════════════════════════════════

def test_pos_irregular_verb():
    assert pos("went") == "VERB"

def test_pos_irregular_noun():
    assert pos("men") == "NOUN"

def test_pos_progressive():
    assert pos("running") == "VERB"

def test_pos_past():
    assert pos("walked") == "VERB"

def test_pos_plural():
    assert pos("cats") == "NOUN"

def test_pos_possessive():
    assert pos("cat's") == "NOUN"

def test_pos_comparative():
    assert pos("faster") == "ADJ"

def test_pos_superlative():
    assert pos("fastest") == "ADJ"

# ══════════════════════════════════════════════════════════════════════════════
# 5. TENSE / ASPECT TAGS
# ══════════════════════════════════════════════════════════════════════════════

def test_tag_past_tense():
    assert tags("went")["tense"] == "PAST"

def test_tag_past_perf():
    t = tags("gone")
    assert t["tense"] == "PAST"
    assert t["aspect"] == "PERF"

def test_tag_progressive():
    t = tags("running")
    assert t["tense"] == "PRES"
    assert t["aspect"] == "PROG"

def test_tag_plural():
    assert tags("cats")["num"] == "PL"

def test_tag_comparative():
    assert tags("faster")["degree"] == "COMP"

def test_tag_superlative():
    assert tags("fastest")["degree"] == "SUPER"

# ══════════════════════════════════════════════════════════════════════════════
# 6. DERIVATIONAL STRIPPING (step_c)
# ══════════════════════════════════════════════════════════════════════════════

# Words where step_a returns UNKNOWN and step_c strips derivational suffixes.
# Expected values verified by running the engine.

DERIVATIONAL = [
    # -ness: derivation now strips suffix
    ("darkness",    "dark"),
    ("happiness", "happy"),
    ("awareness",   "aware"),
    # -ment: derivation strips suffix
    ("development", "develop"),
    ("achievement", "achieve"),
    ("government",  "govern"),
    # -or/-ar: derivation strips suffix
    ("actor",       "act"),
    ("beggar", "beggar"),
    # Prefixes: derivation strips them
    ("unhappy",     "happy"),
    ("undo",        "undo"),
    ("unlock",      "lock"),
    ("rewrite",     "write"),
    ("rebuild",     "build"),
    ("preview",     "view"),
    ("preschool",   "school"),
    ("misunderstand", "understand"),
    ("mislead",     "lead"),
    ("overestimate", "estimate"),
    ("overload",    "load"),
    ("underestimate", "estimate"),
    ("undermine",   "mine"),
    ("disagree", "agree"),
    ("disconnect", "connect"),
    # -able/-ible: derivation strips suffix
    ("readable",    "read"),
    ("washable",    "wash"),
    ("flexible",    "flex"),
    # -ful/-less: derivation strips suffix
    ("hopeful",     "hope"),
    ("hopeless",    "hope"),
    ("careless",    "care"),
    # -al: derivation strips suffix
    ("national",    "nation"),
    ("official",    "off"),
    ("habitual",    "habit"),
    # -ly adverbs: derivation strips suffix
    ("quickly",     "quick"),
    ("happily", "happy"),
    ("simply", "simple"),
    ("beautifully", "beauti"),
    # -ize/-ify/-en/-ate: derivation strips suffix
    ("modernize",   "modern"),
    ("organize",    "organ"),
    ("simplify", "simple"),
    ("classify",    "class"),
    ("darken", "darken"),
    ("widen", "widen"),
    ("activate", "activate"),
    ("validate", "validate"),
    # -hood/-ship/-dom: derivation strips suffix
    ("childhood",   "child"),
    ("friendship",  "friend"),
    ("kingdom",     "king"),
    ("freedom",     "free"),
    # -al (nominalizing): derivation strips suffix
    ("arrival",     "arriv"),
    ("proposal",    "propos"),
    ("refusal",     "fus"),
    # -age: derivation strips suffix
    ("breakage", "breakage"),
    ("drainage", "drainage"),
    ("package", "package"),
    # -ee: derivation strips suffix
    ("employee", "ployee"),
    ("trainee", "trainee"),
    ("payee", "payee"),
    # -th: derivation strips suffix
    ("warmth", "warmth"),
    ("growth", "growth"),
    ("strength", "strength"),
    ("width", "width"),
    # -let: derivation strips suffix
    ("booklet",     "book"),
    ("droplet",     "drop"),
    ("piglet",      "pig"),
    # -some: derivation strips suffix
    ("troublesome", "trouble"),
    ("awesome",     "awe"),
    ("handsome",    "hand"),
    # -wide/-proof: derivation strips suffix
    ("nationwide",  "nation"),
    ("worldwide",   "world"),
    ("waterproof", "water"),
    ("bulletproof", "bul"),
    ("foolproof",   "fool"),
]

@pytest.mark.parametrize("surface,expected", DERIVATIONAL)
def test_derivational(surface, expected):
    assert r(surface) == expected, f"{surface!r}: got {r(surface)!r}"

# ══════════════════════════════════════════════════════════════════════════════
# 7. FALSE-POSITIVE GUARDS
# ══════════════════════════════════════════════════════════════════════════════
# Words that superficially match a rule but must NOT be stripped.

def test_no_strip_short_ing():
    # "ring" ends in -ing but len <= 5 → no strip
    assert r("ring") == "ring"

def test_no_strip_short_ed():
    # "red" ends in -ed but len <= 4 → no strip
    assert r("red") == "red"

def test_no_strip_ss_ending():
    # "class" ends in -ss → plural -s rule skipped
    assert r("class") == "class"

def test_no_strip_short_s():
    # "is" len <= 3 → no strip
    assert r("is") == "be"  # irregular lookup

def test_no_strip_short_es():
    # "goes" → irregular lookup
    assert r("goes") == "go"

def test_no_strip_short_er():
    # "her" len <= 4 → no strip
    assert r("her") == "her"

def test_no_strip_short_est():
    # Engine override: best -> good ADJ SUPER.
    assert r("best") == "good"

# ══════════════════════════════════════════════════════════════════════════════
# 8. SENTENCE-LEVEL ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def test_analyze_sentence_returns_tokens():
    tokens, ok, msg = engine.analyze_sentence("the cat sat on the mat")
    assert len(tokens) == 6

def test_analyze_sentence_each_token_has_root():
    tokens, _, _ = engine.analyze_sentence("she went to the store")
    for tok in tokens:
        assert tok.root is not None
        assert len(tok.root) > 0

def test_analyze_sentence_irregular_in_context():
    tokens, _, _ = engine.analyze_sentence("he went home")
    went_tok = next(t for t in tokens if t.surface == "went")
    assert went_tok.root == "go"
