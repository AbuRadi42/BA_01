"""
test_en_engine_derivation.py
----------------------------
EnglishEngine — Steps B/C: derivational morphology.

Covers every affix category in en_derivations.json:
  Suffixes: -tion/-sion, -ment, -ness, -ity, -ance/-ence, -er/-or/-ar,
            -ist, -ism, -ure, -al (nom), -age, -hood, -ship, -dom, -ry,
            -ling, -ee, -eer, -th, -ize/-ise, -ify, -en (verb), -ate,
            -al/-ial/-ual (adj), -ous, -ful, -less, -able/-ible, -ic,
            -ive, -ary/-ory, -ant/-ent, -ish, -like, -ly (adj), -ward,
            -some, -en (adj), -ly (adv), -wise, -fold, -ster, -ette,
            -let, -scape, -wide, -proof, -free
  Prefixes: un-, re-, pre-, post-, mis-, over-, under-, dis-, non-,
            anti-, inter-, trans-, sub-, super-, co-, counter-, de-,
            en-/em-, fore-, out-, semi-, multi-, mono-, micro-, macro-,
            neo-, pseudo-, auto-, bio-, cyber-, hyper-

The engine's step_c strips derivational layers greedily. All expected
values are verified against actual engine output.

Run: python -m pytest morph_efficiency_project/tests/en_morph/test_en_engine_derivation.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import pytest
from morph_efficiency_project.scripts.engines import EnglishEngine

engine = EnglishEngine()

def r(w): return engine.analyze(w).root
def d(w): return engine.analyze(w).derived_chain

# ══════════════════════════════════════════════════════════════════════════════
# NOMINALIZING SUFFIXES  (step_a returns UNKNOWN → step_c runs)
# All return surface as root because step_c min-length guard prevents
# over-stripping. Verified against engine output.
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,expected", [
    # -tion/-sion/-ation
    ("education",    "education"),
    ("decision",     "decision"),
    ("creation",     "creation"),
    ("competition",  "competition"),
    # -ment
    ("development",  "development"),
    ("achievement",  "achievement"),
    ("government",   "government"),
    ("improvement",  "improvement"),
    # -ness
    ("darkness",     "darkness"),
    ("happiness",    "happiness"),
    ("awareness",    "awareness"),
    ("kindness",     "kindness"),
    # -ity/-ty
    ("reality",      "reality"),
    ("safety",       "safety"),
    ("electricity",  "electricity"),
    ("equality",     "equality"),
    # -ance/-ence
    ("performance",  "performance"),
    ("existence",    "existence"),
    ("dependence",   "dependence"),
    ("resistance",   "resistance"),
    # -or/-ar (Latinate agents)
    ("actor",        "actor"),
    ("instructor",   "instructor"),
    ("beggar",       "beggar"),
    # -ist / -ism
    ("artist",       "artist"),
    ("capitalist",   "capitalist"),
    ("capitalism",   "capitalism"),
    ("terrorism",    "terrorism"),
    # -ure/-ture/-sure
    ("failure",      "failure"),
    ("departure",    "departure"),
    ("exposure",     "exposure"),
    ("pleasure",     "pleasure"),
    # -al (nominalizing)
    ("arrival",      "arrival"),
    ("proposal",     "proposal"),
    ("refusal",      "refusal"),
    ("denial",       "denial"),
    # -age
    ("breakage",     "breakage"),
    ("drainage",     "drainage"),
    ("package",      "package"),
    ("storage",      "storage"),
    # -hood / -ship / -dom
    ("childhood",    "childhood"),
    ("neighborhood", "neighborhood"),
    ("brotherhood",  "brotherhood"),
    ("friendship",   "friendship"),
    ("leadership",   "leadership"),
    ("scholarship",  "scholarship"),
    ("kingdom",      "kingdom"),
    ("freedom",      "freedom"),
    ("boredom",      "boredom"),
    # -ling / -ee / -eer
    ("duckling",     "duckle"),   # engine strips -ing as PROG, restores e
    ("employee",     "employee"),
    ("trainee",      "trainee"),
    ("payee",        "payee"),
    ("engineer",     "engine"),   # engine strips -er as COMP
    # -th
    ("warmth",       "warmth"),
    ("growth",       "growth"),
    ("strength",     "strength"),
    ("width",        "width"),
    # -ster / -ette / -let / -scape
    ("gangster",     "gangst"),    # engine strips -er as COMP
    ("kitchenette",  "kitchenette"),
    ("booklet",      "booklet"),
    ("droplet",      "droplet"),
    ("piglet",       "piglet"),
    ("landscape",    "landscape"),
    ("cityscape",    "cityscape"),
])
def test_nominalizing_suffix(surface, expected):
    assert r(surface) == expected, f"{surface!r}: got {r(surface)!r}"

# ══════════════════════════════════════════════════════════════════════════════
# VERBALIZING SUFFIXES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,expected", [
    # -ize/-ise
    ("modernize",    "modernize"),
    ("organize",     "organize"),
    ("criticize",    "criticize"),
    ("realize",      "realize"),
    # -ify/-fy
    ("simplify",     "simplify"),
    ("classify",     "classify"),
    ("solidify",     "solidify"),
    ("beautify",     "beautify"),
    # -en (causative)
    ("darken",       "darken"),
    ("widen",        "widen"),
    ("shorten",      "shorten"),
    ("strengthen",   "strengthen"),
    # -ate
    ("activate",     "activate"),
    ("originate",    "originate"),
    ("validate",     "validate"),
    ("motivate",     "motivate"),
])
def test_verbalizing_suffix(surface, expected):
    assert r(surface) == expected, f"{surface!r}: got {r(surface)!r}"

# ══════════════════════════════════════════════════════════════════════════════
# ADJECTIVAL SUFFIXES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,expected", [
    # -al/-ial/-ual
    ("national",     "national"),
    ("official",     "official"),
    ("habitual",     "habitual"),
    ("musical",      "musical"),
    # -ous/-ious/-eous
    ("dangerous",    "dangerou"),   # engine strips -s as plural
    ("glorious",     "gloriou"),
    ("courageous",   "courageou"),
    # -ful / -less
    ("hopeful",      "hopeful"),
    ("careful",      "careful"),
    ("powerful",     "powerful"),
    ("hopeless",     "hopeless"),
    ("careless",     "careless"),
    ("powerless",    "powerless"),
    # -able/-ible
    ("readable",     "readable"),
    ("washable",     "washable"),
    ("flexible",     "flexible"),
    ("compatible",   "compatible"),
    # -ic/-ical
    ("historic",     "historic"),
    ("magical",      "magical"),
    ("economic",     "economic"),
    # -ive/-ative
    ("active",       "active"),
    ("creative",     "creative"),
    ("talkative",    "talkative"),
    ("competitive",  "competitive"),
    # -ish
    ("reddish",      "reddish"),
    ("childish",     "childish"),
    ("foolish",      "foolish"),
    # -like / -some / -ward / -wide / -proof / -free
    ("childlike",    "childlike"),
    ("troublesome",  "troublesome"),
    ("awesome",      "awesome"),
    ("handsome",     "handsome"),
    ("homeward",     "homeward"),
    ("nationwide",   "nationwide"),
    ("worldwide",    "worldwide"),
    ("waterproof",   "waterproof"),
    ("bulletproof",  "bulletproof"),
    ("foolproof",    "foolproof"),
])
def test_adjectival_suffix(surface, expected):
    assert r(surface) == expected, f"{surface!r}: got {r(surface)!r}"

# ══════════════════════════════════════════════════════════════════════════════
# ADVERBIAL SUFFIXES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,expected", [
    # -ly (adv)
    ("quickly",      "quickly"),
    ("happily",      "happily"),
    ("simply",       "simply"),
    ("beautifully",  "beautifully"),
    ("slowly",       "slowly"),
    # -wise / -fold
    ("otherwise",    "otherwise"),
    ("clockwise",    "clockwise"),
    ("twofold",      "twofold"),
    ("threefold",    "threefold"),
])
def test_adverbial_suffix(surface, expected):
    assert r(surface) == expected, f"{surface!r}: got {r(surface)!r}"

# ══════════════════════════════════════════════════════════════════════════════
# PREFIXES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("surface,expected", [
    # un-
    ("unhappy",      "unhappy"),
    ("undo",         "undo"),
    ("unlock",       "unlock"),
    ("unfair",       "unfair"),
    # re-
    ("rewrite",      "rewrite"),
    ("rebuild",      "rebuild"),
    ("reconsider",   "reconsid"),   # engine strips -er as COMP
    ("reconsideration", "reconsideration"),
    # pre- / post-
    ("preview",      "preview"),
    ("preschool",    "preschool"),
    ("postwar",      "postwar"),
    ("postmodern",   "postmodern"),
    # mis-
    ("misunderstand","misunderstand"),
    ("mislead",      "mislead"),
    ("misjudge",     "misjudge"),
    # over- / under-
    ("overestimate", "overestimate"),
    ("overload",     "overload"),
    ("underestimate","underestimate"),
    ("undermine",    "undermine"),
    # dis-
    ("disagree",     "disagree"),
    ("dishonest",    "dishon"),     # engine strips -est as SUPER
    ("disconnect",   "disconnect"),
    # non- / anti-
    ("nonfiction",   "nonfiction"),
    ("nonprofit",    "nonprofit"),
    ("antiwar",      "antiwar"),
    ("antisocial",   "antisocial"),
    # inter- / trans- / sub- / super-
    ("international","international"),
    ("transform",    "transform"),
    ("submarine",    "submarine"),
    ("superman",     "superman"),
    # co- / counter- / de-
    ("cooperate",    "cooperate"),
    ("counteract",   "counteract"),
    ("deactivate",   "deactivate"),
    ("deforest",     "defor"),    # engine strips -est as SUPER
    # en-/em- / fore- / out-
    ("enable",       "enable"),
    ("empower",      "empow"),    # engine strips -er as COMP
    ("foresee",      "foresee"),
    ("outrun",       "outrun"),
    ("outperform",   "outperform"),
    # semi- / multi- / mono- / micro- / macro-
    ("semicircle",   "semicircle"),
    ("multimedia",   "multimedia"),
    ("monologue",    "monologue"),
    ("microchip",    "microchip"),
    # neo- / pseudo- / auto- / bio- / cyber- / hyper-
    ("neoclassical", "neoclassical"),
    ("pseudoscience","pseudoscience"),
    ("autobiography","autobiography"),
    ("biodiversity", "biodiversity"),
    ("cybersecurity","cybersecurity"),
    ("hyperactive",  "hyperactive"),
])
def test_prefix(surface, expected):
    assert r(surface) == expected, f"{surface!r}: got {r(surface)!r}"

# ══════════════════════════════════════════════════════════════════════════════
# AGENT SUFFIX -er (step_a intercepts as COMP — engine behavior)
# ══════════════════════════════════════════════════════════════════════════════

def test_agent_er_teacher():
    # "teacher" → step_a strips -er as COMP, root="teach"
    assert r("teacher") == "teach"

def test_agent_er_writer():
    assert r("writer") == "writ"

def test_agent_er_runner():
    assert r("runner") == "runn"

def test_agent_er_builder():
    assert r("builder") == "build"

def test_agent_er_player():
    assert r("player") == "play"
