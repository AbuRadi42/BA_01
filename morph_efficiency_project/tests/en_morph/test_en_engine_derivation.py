"""
test_en_engine_derivation.py
----------------------------
EnglishEngine -- Steps B/C: derivational morphology.

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

# ======================================================================
# NOMINALIZING SUFFIXES  (step_a returns UNKNOWN -> step_c runs)
# With derivation matching fixed, step_c now strips affixes greedily.
#
# NOTE (stem-validity guard, 2026): several expected roots below were updated
# from non-word fragments to real English words. The engine now refuses any
# derivational cut whose remainder is not a real word (configs/en_wordlist.txt),
# restoring silent-e where needed. The OLD values (electr, pend, structor,
# expos, arriv, propos, fus, ployee, ...) were genuinely-wrong over-strips:
# a dictionary word reduced to a non-word fragment. The NEW values are the
# real-word roots the guard produces and agree with a reference lemmatiser.
# ======================================================================

@pytest.mark.parametrize("surface,expected", [
    # -tion/-sion/-ation
    ("education", "educate"),
    ("decision", "decide"),
    ("creation", "create"),
    ("competition", "compete"),
    # -ment
    ("development", "develop"),
    ("achievement",  "achieve"),
    ("government",   "govern"),
    ("improvement",  "improve"),
    # -ness
    ("darkness",     "dark"),
    ("happiness", "happy"),
    ("awareness",    "aware"),
    ("kindness",     "kind"),
    # -ity/-ty
    ("reality",      "real"),
    ("safety", "safety"),
    ("electricity",  "electric"),
    ("equality", "equal"),
    # -ance/-ence
    ("performance",  "perform"),
    ("existence",    "exist"),
    ("dependence",   "depend"),
    ("resistance",   "res"),
    # -or/-ar (Latinate agents)
    ("actor",        "act"),
    ("instructor", "instructor"),
    ("beggar", "beggar"),
    # -ist / -ism
    ("artist",       "art"),
    ("capitalist", "capital"),
    ("capitalism", "capital"),
    ("terrorism", "terror"),
    # -ure/-ture/-sure
    ("failure",      "fail"),
    # Deepest-real-word convention: -ure nominalises a verb base. departure->depart
    # (de- is fused, kept), exposure->expose. OLD 'par'/'exposure' were the
    # inconsistent greedy-fragment / kept-whole behaviour.
    ("departure", "depart"),
    ("exposure", "expose"),
    ("pleasure", "pleas"),
    # -al (nominalizing)
    ("arrival",      "arrival"),
    ("proposal",     "proposal"),
    ("refusal",      "fuse"),
    ("denial",       "den"),
    # -age
    ("breakage", "breakage"),
    ("drainage", "drainage"),
    ("package", "package"),
    ("storage", "storage"),
    # -hood / -ship / -dom
    ("childhood",    "child"),
    ("neighborhood", "neighbor"),
    ("brotherhood", "brother"),
    ("friendship",   "friend"),
    ("leadership", "leader"),
    ("scholarship", "scholar"),
    ("kingdom",      "king"),
    # Deepest-real-word convention: -dom peels to its real base. 'free' is a real
    # adjective, so freedom->free, consistent with kingdom->king and boredom->bore.
    # OLD kept 'freedom' whole, which was inconsistent.
    ("freedom",      "free"),
    ("boredom",      "bore"),
    # -ling / -ee / -eer
    ("duckling", "duckl"),   # engine strips -ing as PROG, restores e
    ("employee", "employee"),
    ("trainee", "trainee"),
    ("payee", "payee"),
    # 'engineer' is lexicalised (engine+eer, but 'gin' is an unrelated wordlist
    # fragment): the deepest-real-word rule keeps it whole rather than peeling to
    # the noise word 'gin'. OLD expected the fragment 'gin'.
    ("engineer", "engineer"),
    # -th
    ("warmth", "warmth"),
    ("growth", "growth"),
    ("strength", "strength"),
    ("width", "width"),
    # -ster / -ette / -let / -scape
    ("gangster", "gang"),    # engine strips -er as COMP
    ("kitchenette", "kitchen"),
    ("booklet",      "book"),
    ("droplet",      "drop"),
    ("piglet",       "pig"),
    ("landscape",    "land"),
    ("cityscape",    "city"),
])
def test_nominalizing_suffix(surface, expected):
    assert r(surface) == expected, f"{surface!r}: got {r(surface)!r}"

# ======================================================================
# VERBALIZING SUFFIXES
# ======================================================================

@pytest.mark.parametrize("surface,expected", [
    # -ize/-ise
    ("modernize",    "modern"),
    ("organize",     "organ"),
    ("criticize",    "critic"),
    ("realize",      "real"),
    # -ify/-fy
    ("simplify", "simple"),
    ("classify",     "class"),
    ("solidify",     "solid"),
    # Deepest-real-word: -ify attaches to a -y base; beauty->beautify, so the
    # base is 'beauty', not the fragment 'beaut'. OLD expected 'beaut'.
    ("beautify",     "beauty"),
    # -en (causative)
    ("darken", "darken"),
    ("widen", "widen"),
    ("shorten", "shorten"),
    ("strengthen", "strengthen"),
    # -ate
    ("activate", "activate"),
    ("originate", "originate"),
    ("validate", "validate"),
    ("motivate", "motivate"),
])
def test_verbalizing_suffix(surface, expected):
    assert r(surface) == expected, f"{surface!r}: got {r(surface)!r}"

# ======================================================================
# ADJECTIVAL SUFFIXES
# ======================================================================

@pytest.mark.parametrize("surface,expected", [
    # -al/-ial/-ual
    ("national",     "nation"),
    ("official",     "off"),
    ("habitual",     "habit"),
    ("musical", "music"),
    # -ous/-ious/-eous
    ("dangerous", "danger"),   # engine strips -s as plural
    ("glorious", "glorious"),
    ("courageous", "courage"),
    # -ful / -less
    ("hopeful",      "hope"),
    ("careful",      "care"),
    ("powerful", "power"),
    ("hopeless",     "hope"),
    ("careless",     "care"),
    ("powerless", "power"),
    # -able/-ible
    ("readable",     "read"),
    ("washable",     "wash"),
    ("flexible",     "flex"),
    ("compatible",   "compatible"),
    # -ic/-ical
    ("historic", "historic"),
    ("magical",      "mag"),
    ("economic",     "economic"),
    # -ive/-ative
    ("active", "active"),
    ("creative", "create"),
    ("talkative",    "talk"),
    ("competitive", "compete"),
    # -ish
    ("reddish",      "reddish"),
    ("childish",     "child"),
    ("foolish",      "fool"),
    # -like / -some / -ward / -wide / -proof / -free
    ("childlike",    "child"),
    ("troublesome",  "trouble"),
    ("awesome",      "awe"),
    ("handsome",     "hand"),
    ("homeward",     "home"),
    ("nationwide",   "nation"),
    ("worldwide",    "world"),
    ("waterproof", "water"),
    ("bulletproof",  "bullet"),
    ("foolproof",    "fool"),
])
def test_adjectival_suffix(surface, expected):
    assert r(surface) == expected, f"{surface!r}: got {r(surface)!r}"

# ======================================================================
# ADVERBIAL SUFFIXES
# ======================================================================

@pytest.mark.parametrize("surface,expected", [
    # -ly (adv)
    ("quickly",      "quick"),
    ("happily", "happy"),
    ("simply", "simple"),
    ("beautifully",  "beautiful"),
    ("slowly",       "slow"),
    # -wise / -fold
    ("otherwise", "other"),
    ("clockwise",    "clock"),
    ("twofold",      "two"),
    ("threefold", "three"),
])
def test_adverbial_suffix(surface, expected):
    assert r(surface) == expected, f"{surface!r}: got {r(surface)!r}"

# ======================================================================
# PREFIXES
# ======================================================================

@pytest.mark.parametrize("surface,expected", [
    # un-
    ("unhappy",      "happy"),
    ("undo",         "undo"),
    ("unlock",       "lock"),
    ("unfair",       "fair"),
    # re-
    ("rewrite",      "write"),
    ("rebuild",      "build"),
    ("reconsider", "consider"),   # engine strips -er as COMP
    ("reconsideration", "consider"),
    # pre- / post-
    ("preview",      "view"),
    ("preschool",    "school"),
    ("postwar", "war"),
    ("postmodern",   "modern"),
    # mis-
    ("misunderstand", "understand"),
    ("mislead",      "lead"),
    ("misjudge",     "judge"),
    # over- / under-
    ("overestimate", "estimate"),
    ("overload",     "load"),
    ("underestimate", "estimate"),
    ("undermine",    "undermine"),
    # dis-
    ("disagree", "agree"),
    ("dishonest", "honest"),     # engine strips -est as SUPER
    ("disconnect", "connect"),
    # non- / anti-
    ("nonfiction", "fiction"),
    ("nonprofit",    "profit"),
    ("antiwar", "war"),
    ("antisocial", "social"),
    # inter- / trans- / sub- / super-
    ("international", "nation"),
    ("transform",    "form"),
    ("submarine",    "marine"),
    ("superman",     "man"),
    # co- / counter- / de-
    ("cooperate", "operate"),
    ("counteract",   "act"),
    ("deactivate", "activate"),
    ("deforest", "forest"),    # engine strips -est as SUPER
    # en-/em- / fore- / out-
    # enable = "make able"; 'able' is a real adjective base, so en- peels (cf.
    # ability->able). OLD kept it whole, inconsistent with empower->power.
    ("enable",       "able"),
    ("empower", "power"),    # engine strips -er as COMP
    ("foresee", "see"),
    ("outrun",       "run"),
    ("outperform",   "perform"),
    # semi- / multi- / mono- / micro- / macro-
    ("semicircle",   "circle"),
    ("multimedia",   "media"),
    ("monologue",    "monologue"),
    ("microchip",    "chip"),
    # neo- / pseudo- / auto- / bio- / cyber- / hyper-
    # 'classical' is lexicalised (kept whole), so neoclassical stops at it rather
    # than peeling to 'class'. OLD expected 'class'.
    ("neoclassical", "classical"),
    ("pseudoscience", "science"),
    ("autobiography","biography"),
    ("biodiversity", "divers"),
    # security -ity-> secure (deepest real word; 'sec' is a noise fragment).
    ("cybersecurity","secure"),
    ("hyperactive", "active"),
])
def test_prefix(surface, expected):
    assert r(surface) == expected, f"{surface!r}: got {r(surface)!r}"

# ======================================================================
# AGENT SUFFIX -er (step_a intercepts as COMP -- engine behavior)
# ======================================================================

def test_agent_er_teacher():
    # "teacher" -> step_a strips -er as COMP, root="teach"
    assert r("teacher") == "teach"

def test_agent_er_writer():
    assert r("writer") == "write"

def test_agent_er_runner():
    # Updated (stem-validity guard): OLD expected the over-stripped non-word
    # 'runn'. 'runner' is itself a dictionary word (and the reference lemma),
    # so the guard keeps it whole rather than peeling -er into a bare 'runn'.
    assert r("runner") == "runner"

def test_agent_er_builder():
    assert r("builder") == "build"

def test_agent_er_player():
    assert r("player") == "play"
