"""
test_en_engine_comprehensive.py
-------------------------------
EnglishEngine edge-case-inclusive audit suite.

Unlike the existing test files (which were tuned to record actual engine
output for regression purposes), this file asserts the LINGUISTICALLY
CORRECT analysis for every case. Tests that fail expose real engine bugs.

Categories:
  1.  Inflectional morphology (noun, verb, adjective, adverb, voice)
  2.  Derivational suffixes
  3.  Derivational prefixes
  4.  Multi-step derivation (recursive decomposition)
  5.  Phrasal verbs
  6.  Compounds
  7.  Edge cases (numerals, abbreviations, hyphenations, loans)
  8.  The -er agent vs comparative disambiguation bug

Each test asserts on the engine's actual public output: pos, root, tags,
and derived_chain.

Run:
  python -X utf8 -m pytest morph_efficiency_project/tests/en_morph/test_en_engine_comprehensive.py -v
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import EnglishEngine  # noqa: E402

engine = EnglishEngine()


def info(w):
    return engine.analyze(w)


def root(w):
    return engine.analyze(w).root


def pos(w):
    return engine.analyze(w).pos


def tags(w):
    return engine.analyze(w).tags


def chain(w):
    return engine.analyze(w).derived_chain


def chain_str(w):
    return " | ".join(engine.analyze(w).derived_chain)


# ============================================================================
# 1. INFLECTIONAL MORPHOLOGY
# ============================================================================

# 1a. Regular noun plural
@pytest.mark.parametrize("surface,lemma", [
    ("cats", "cat"),
    ("dogs", "dog"),
    ("books", "book"),
    ("boxes", "box"),
    ("churches", "church"),
    ("dishes", "dish"),
    ("babies", "baby"),
    ("cities", "city"),
    ("buses", "bus"),
    ("wishes", "wish"),
])
def test_plural_regular(surface, lemma):
    i = info(surface)
    assert i.root == lemma, f"{surface}: root={i.root!r} expected {lemma!r}"
    assert i.pos == "NOUN"
    assert i.tags.get("num") == "PL"


# 1b. Irregular noun plural
@pytest.mark.parametrize("surface,lemma", [
    ("children", "child"),
    ("oxen", "ox"),
    ("feet", "foot"),
    ("teeth", "tooth"),
    ("mice", "mouse"),
    ("geese", "goose"),
    ("men", "man"),
    ("women", "woman"),
    ("lice", "louse"),
    ("people", "person"),
])
def test_plural_irregular(surface, lemma):
    i = info(surface)
    assert i.root == lemma, f"{surface}: root={i.root!r} expected {lemma!r}"
    assert i.pos == "NOUN"
    assert i.tags.get("num") == "PL"


# 1c. Possessive 's
@pytest.mark.parametrize("surface,lemma", [
    ("cat's", "cat"),
    ("dog's", "dog"),
    ("teacher's", "teacher"),
    ("child's", "child"),
    ("John's", "john"),
])
def test_possessive(surface, lemma):
    i = info(surface)
    assert i.root == lemma
    assert i.tags.get("poss") == "YES"
    assert i.pos == "NOUN"


# 1d. Verb tense (regular past)
@pytest.mark.parametrize("surface,lemma", [
    ("walked", "walk"),
    ("talked", "talk"),
    ("jumped", "jump"),
    ("helped", "help"),
    ("opened", "open"),
    ("stopped", "stop"),
    ("planned", "plan"),
])
def test_past_regular(surface, lemma):
    i = info(surface)
    assert i.root == lemma
    assert i.pos == "VERB"
    assert i.tags.get("tense") == "PAST"


# 1e. Verb tense (irregular past)
@pytest.mark.parametrize("surface,lemma", [
    ("went", "go"),
    ("ate", "eat"),
    ("drank", "drink"),
    ("swam", "swim"),
    ("saw", "see"),
    ("took", "take"),
    ("gave", "give"),
    ("broke", "break"),
    ("ran", "run"),
    ("wrote", "write"),
])
def test_past_irregular(surface, lemma):
    i = info(surface)
    assert i.root == lemma
    assert i.pos == "VERB"
    assert i.tags.get("tense") == "PAST"


# 1f. Verb aspect: progressive
@pytest.mark.parametrize("surface,lemma", [
    ("running", "run"),
    ("swimming", "swim"),
    ("writing", "write"),
    ("making", "make"),
    ("taking", "take"),
    ("dancing", "dance"),
    ("walking", "walk"),
    ("talking", "talk"),
])
def test_aspect_progressive(surface, lemma):
    i = info(surface)
    assert i.root == lemma, f"{surface}: root={i.root!r} expected {lemma!r}"
    assert i.pos == "VERB"
    assert i.tags.get("aspect") == "PROG"


# 1g. Verb aspect: perfect (past participle)
@pytest.mark.parametrize("surface,lemma", [
    ("eaten", "eat"),
    ("written", "write"),
    ("taken", "take"),
    ("given", "give"),
    ("broken", "break"),
    ("seen", "see"),
    ("done", "do"),
    ("gone", "go"),
])
def test_aspect_perfect(surface, lemma):
    i = info(surface)
    assert i.root == lemma
    assert i.pos == "VERB"
    assert i.tags.get("aspect") == "PERF"


# 1h. Verb person 3SG present
@pytest.mark.parametrize("surface,lemma", [
    ("walks", "walk"),
    ("runs", "run"),
    ("eats", "eat"),
    ("writes", "write"),
    ("goes", "go"),
    ("plays", "play"),
    ("works", "work"),
])
def test_3sg_present(surface, lemma):
    i = info(surface)
    assert i.root == lemma, f"{surface}: root={i.root!r} expected {lemma!r}"
    assert i.pos == "VERB", f"{surface}: pos={i.pos!r} expected VERB"
    assert i.tags.get("person") == "3SG" or i.tags.get("num") == "SG", (
        f"{surface}: tags={i.tags!r}"
    )


# 1i. Passive voice (analyzed as past participle for now)
@pytest.mark.parametrize("surface,lemma", [
    ("eaten", "eat"),
    ("written", "write"),
    ("broken", "break"),
    ("taken", "take"),
    ("given", "give"),
])
def test_passive_participle(surface, lemma):
    i = info(surface)
    assert i.root == lemma
    assert i.pos == "VERB"


# 1j. Adjective degree (regular)
@pytest.mark.parametrize("surface,lemma,degree", [
    ("taller", "tall", "COMP"),
    ("tallest", "tall", "SUPER"),
    ("faster", "fast", "COMP"),
    ("fastest", "fast", "SUPER"),
    ("slower", "slow", "COMP"),
    ("slowest", "slow", "SUPER"),
    ("smarter", "smart", "COMP"),
    ("smartest", "smart", "SUPER"),
])
def test_degree_regular(surface, lemma, degree):
    i = info(surface)
    assert i.root == lemma
    assert i.pos == "ADJ"
    assert i.tags.get("degree") == degree


# 1k. Adjective degree (irregular)
@pytest.mark.parametrize("surface,lemma,degree", [
    ("better", "good", "COMP"),
    ("best", "good", "SUPER"),
    ("worse", "bad", "COMP"),
    ("worst", "bad", "SUPER"),
    ("more", "much", "COMP"),
    ("most", "much", "SUPER"),
    ("less", "little", "COMP"),
    ("least", "little", "SUPER"),
])
def test_degree_irregular(surface, lemma, degree):
    i = info(surface)
    assert i.root == lemma, f"{surface}: root={i.root!r} expected {lemma!r}"
    assert i.pos == "ADJ"
    assert i.tags.get("degree") == degree


# ============================================================================
# 2. DERIVATIONAL SUFFIXES
# ============================================================================

# 2a. agent -er (NOUN, not COMP-ADJ)
AGENT_ER_CASES = [
    ("writer", "write"),
    ("teacher", "teach"),
    ("painter", "paint"),
    ("baker", "bake"),
    ("singer", "sing"),
    ("driver", "drive"),
    ("dancer", "dance"),
    ("lawyer", "law"),
]


@pytest.mark.parametrize("surface,base", AGENT_ER_CASES)
def test_agent_er_noun(surface, base):
    i = info(surface)
    assert i.pos == "NOUN", (
        f"{surface}: pos={i.pos!r} expected NOUN (agent -er, not COMP)"
    )
    assert i.root == base, f"{surface}: root={i.root!r} expected {base!r}"
    assert i.tags.get("degree") != "COMP", (
        f"{surface}: degree=COMP — agent -er misanalyzed as comparative"
    )


# 2b. -ing nominal / gerund (distinct from progressive)
@pytest.mark.parametrize("surface,base", [
    ("building", "build"),    # noun: a building
    ("meaning", "mean"),
    ("painting", "paint"),
    ("reading", "read"),
    ("writing", "write"),
])
def test_gerund_or_deverbal_noun(surface, base):
    # The engine currently always tags -ing as PROG verb, but the gerund
    # interpretation is a noun. We accept either; what we will NOT accept is
    # a wrong root or no -ing recognition at all.
    i = info(surface)
    assert i.root == base, f"{surface}: root={i.root!r} expected {base!r}"


# 2c. -ed deverbal adjective (e.g., "tired", "excited")
@pytest.mark.parametrize("surface,base", [
    ("tired", "tire"),
    ("excited", "excite"),
    ("bored", "bore"),
    ("interested", "interest"),
])
def test_ed_deverbal_adj(surface, base):
    i = info(surface)
    assert i.root == base


# 2d. -ly ADV from ADJ
@pytest.mark.parametrize("surface,base", [
    ("quickly", "quick"),
    ("slowly", "slow"),
    ("happily", "happy"),
    ("badly", "bad"),
    ("nicely", "nice"),
    ("loudly", "loud"),
    ("simply", "simple"),
])
def test_ly_adv(surface, base):
    i = info(surface)
    assert i.pos == "ADV", f"{surface}: pos={i.pos!r} expected ADV"
    assert i.root == base
    assert any("ly" in c for c in i.derived_chain), (
        f"{surface}: chain={i.derived_chain!r} expected -ly step"
    )


# 2e. -ness STATE_QUALITY
@pytest.mark.parametrize("surface,base", [
    ("darkness", "dark"),
    ("happiness", "happy"),
    ("kindness", "kind"),
    ("awareness", "aware"),
    ("sadness", "sad"),
    ("weakness", "weak"),
])
def test_ness(surface, base):
    i = info(surface)
    assert i.pos == "NOUN", f"{surface}: pos={i.pos!r} expected NOUN"
    assert i.root == base, f"{surface}: root={i.root!r} expected {base!r}"
    assert any("ness" in c for c in i.derived_chain)


# 2f. -ment
@pytest.mark.parametrize("surface,base", [
    ("development", "develop"),
    ("achievement", "achieve"),
    ("government", "govern"),
    ("improvement", "improve"),
    ("statement", "state"),
])
def test_ment(surface, base):
    i = info(surface)
    assert i.pos == "NOUN"
    assert i.root == base


# 2g. -ity
@pytest.mark.parametrize("surface,base", [
    ("reality", "real"),
    ("equality", "equal"),
    # Deepest-real-word convention: -ity peels to the real adjective base, in line
    # with reality->real, possibility->possible, activity->active. 'able' is a real
    # word (via LEMMA_RESTORE abil->able), so ability->able, consistent with the
    # rest of this block. OLD kept it whole, which was inconsistent.
    ("ability", "able"),
    ("possibility", "possible"),
    ("activity", "active"),
])
def test_ity(surface, base):
    i = info(surface)
    assert i.pos == "NOUN"
    assert i.root == base


# 2h. -ation / -tion / -sion ACTION_NOUN
@pytest.mark.parametrize("surface,base", [
    ("education", "educate"),
    ("creation", "create"),
    ("decision", "decide"),
    ("explanation", "explain"),
    ("invitation", "invite"),
])
def test_ation_tion(surface, base):
    i = info(surface)
    assert i.pos == "NOUN"
    assert i.root == base


# 2i. -ize / -ise CAUSATIVE verb
@pytest.mark.parametrize("surface,base", [
    ("modernize", "modern"),
    ("organize", "organ"),
    ("realize", "real"),
    ("nationalise", "nation"),
    ("centralize", "central"),
])
def test_ize_ise(surface, base):
    i = info(surface)
    assert i.pos == "VERB"
    assert i.root == base


# 2j. -ist AGENT
@pytest.mark.parametrize("surface,base", [
    ("artist", "art"),
    ("guitarist", "guitar"),
    ("violinist", "violin"),
    ("scientist", "science"),
    ("dentist", "dent"),
])
def test_ist(surface, base):
    i = info(surface)
    assert i.pos == "NOUN"
    assert i.root == base


# 2k. -ism DOCTRINE
@pytest.mark.parametrize("surface,base", [
    ("capitalism", "capital"),
    ("socialism", "social"),
    ("terrorism", "terror"),
    ("realism", "real"),
])
def test_ism(surface, base):
    i = info(surface)
    assert i.pos == "NOUN"
    assert i.root == base


# 2l. -able / -ible
@pytest.mark.parametrize("surface,base", [
    ("readable", "read"),
    ("washable", "wash"),
    ("breakable", "break"),
    ("flexible", "flex"),
    ("usable", "use"),
])
def test_able_ible(surface, base):
    i = info(surface)
    assert i.pos == "ADJ"
    assert i.root == base


# 2m. -ful, -less, -ous, -ish, -al, -hood, -ship
@pytest.mark.parametrize("surface,base,pos_exp", [
    ("hopeful", "hope", "ADJ"),
    ("careful", "care", "ADJ"),
    ("hopeless", "hope", "ADJ"),
    ("careless", "care", "ADJ"),
    ("dangerous", "danger", "ADJ"),
    ("famous", "fame", "ADJ"),
    ("childish", "child", "ADJ"),
    ("foolish", "fool", "ADJ"),
    ("national", "nation", "ADJ"),
    ("musical", "music", "ADJ"),
    ("childhood", "child", "NOUN"),
    ("brotherhood", "brother", "NOUN"),
    ("friendship", "friend", "NOUN"),
    ("leadership", "leader", "NOUN"),
])
def test_misc_deriv_suffix(surface, base, pos_exp):
    i = info(surface)
    assert i.root == base, f"{surface}: root={i.root!r} expected {base!r}"
    assert i.pos == pos_exp, f"{surface}: pos={i.pos!r} expected {pos_exp}"


# ============================================================================
# 3. DERIVATIONAL PREFIXES
# ============================================================================

@pytest.mark.parametrize("surface,base,prefix_label", [
    # re-
    ("rewrite", "write", "re"),
    ("rebuild", "build", "re"),
    ("rerun", "run", "re"),
    # un-
    ("unhappy", "happy", "un"),
    ("unfair", "fair", "un"),
    ("unlock", "lock", "un"),
    # dis-
    ("disagree", "agree", "dis"),
    ("disconnect", "connect", "dis"),
    ("dislike", "like", "dis"),
    # mis-
    ("mislead", "lead", "mis"),
    ("misjudge", "judge", "mis"),
    # pre-, post-
    ("preview", "view", "pre"),
    ("preschool", "school", "pre"),
    ("postwar", "war", "post"),
    # anti-
    ("antiwar", "war", "anti"),
    ("antisocial", "social", "anti"),
    # sub-, super-
    ("submarine", "marine", "sub"),
    ("superhuman", "human", "super"),
    # non-
    ("nonfiction", "fiction", "non"),
    ("nonprofit", "profit", "non"),
    # in-/im-/il-/ir-
    ("inactive", "active", "in"),
    ("impossible", "possible", "im"),
    ("illegal", "legal", "il"),
    ("irregular", "regular", "ir"),
    # de-
    ("deactivate", "activate", "de"),
    ("decode", "code", "de"),
    # en-/em-
    # Deepest-real-word convention: en- is the causative ("make ADJ"); enable =
    # "make able", and 'able' is a real adjective base (cf. ability->able,
    # disable, unable). So enable->able, consistent with empower->power.
    ("enable", "able", "en"),
    ("empower", "power", "em"),
    # over-, under-
    ("overload", "load", "over"),
    # Updated (stem-validity guard): 'undermine' is its own lemma; the guard does
    # not peel under- down to the pronoun 'mine'. OLD expected "mine".
    ("undermine", "undermine", "under"),
    # out-, fore-, mid-
    ("outrun", "run", "out"),
    ("foresee", "see", "fore"),
    ("midnight", "night", "mid"),
    # semi-, multi-, mega-
    ("semicircle", "circle", "semi"),
    ("multimedia", "media", "multi"),
    ("megastore", "store", "mega"),
])
def test_prefix(surface, base, prefix_label):
    i = info(surface)
    assert i.root == base, f"{surface}: root={i.root!r} expected {base!r}"


# ============================================================================
# 4. MULTI-STEP DERIVATION
# ============================================================================

@pytest.mark.parametrize("surface,base,min_chain_len,must_include", [
    # 'research' is lexicalised (kept whole; re- is fused), so its agent/plural
    # forms bottom out at 'research', NOT the deeper 'search'. The deepest-real-
    # word rule respects the lexicalised keep-list. OLD expected 'search'.
    ("researchers", "research", 1, ["er"]),
    ("researcher", "research", 1, ["er"]),
    # ungodliness -> un + god + ly + ness
    ("ungodliness", "god", 3, ["un", "ly", "ness"]),
    # rethought -> re + think (PAST_PARTICIPLE)
    ("rethought", "think", 1, ["re"]),
    # denationalisation -> de + nation + al + ise + ation
    ("denationalisation", "nation", 4, ["de", "al", "ation"]),
    # restructuring -> re + structure + ing(PROG)
    ("restructuring", "structure", 1, ["re"]),
    # non + communic(ate) + ative
    ("noncommunicative", "communicate", 2, ["non", "ative"]),
    # anti + establish + ment + arian + ism
    ("antiestablishmentarianism", "establish", 4,
     ["anti", "ment", "ism"]),
    # pre + determine + ation
    ("predetermination", "determine", 2, ["pre", "ation"]),
])
def test_multistep_derivation(surface, base, min_chain_len, must_include):
    i = info(surface)
    assert i.root == base, (
        f"{surface}: root={i.root!r} expected {base!r}; "
        f"chain={i.derived_chain!r}"
    )
    assert len(i.derived_chain) >= min_chain_len, (
        f"{surface}: chain too short: {i.derived_chain!r} "
        f"(expected >= {min_chain_len} steps)"
    )
    flat = " ".join(i.derived_chain).lower()
    for piece in must_include:
        assert piece in flat, (
            f"{surface}: chain {i.derived_chain!r} missing {piece!r}"
        )


# ============================================================================
# 5. PHRASAL VERBS
# ============================================================================

@pytest.mark.parametrize("verb,particle", [
    ("pick", "up"),
    ("give", "up"),
    ("run", "into"),
    ("look", "after"),
    ("break", "down"),
    ("take", "off"),
    ("turn", "on"),
    ("put", "out"),
])
def test_phrasal_verb_base(verb, particle):
    # The engine tags verb component with phrasal_verb_base=YES.
    i = info(verb)
    # At minimum, the verb form should be recognized as a VERB and not crash.
    # Strong assertion: phrasal_verb_base tag should appear for known PVs.
    assert i.tags.get("phrasal_verb_base") == "YES", (
        f"{verb}: tags={i.tags!r}; expected phrasal_verb_base=YES "
        f"(particle={particle})"
    )


# ============================================================================
# 6. COMPOUNDS
# ============================================================================

@pytest.mark.parametrize("surface,head_or_root", [
    ("bookshop", "shop"),
    ("blackboard", "board"),
    ("notebook", "book"),
    ("sunlight", "light"),
    ("classroom", "room"),
])
def test_compound_solid(surface, head_or_root):
    i = info(surface)
    # Either the compound is recognized (chain contains COMPOUND) and root
    # is the head, OR the root equals the head form directly.
    has_compound = any("COMPOUND" in c for c in i.derived_chain)
    assert has_compound or i.root == head_or_root, (
        f"{surface}: not recognized as compound; "
        f"root={i.root!r}, chain={i.derived_chain!r}"
    )


@pytest.mark.parametrize("surface", [
    "well-known",
    "son-in-law",
    "runner-up",
    "mother-in-law",
])
def test_hyphenated_compound(surface):
    i = info(surface)
    # Should not crash; should produce some non-empty surface.
    assert i.surface == surface


# ============================================================================
# 7. EDGE CASES
# ============================================================================

@pytest.mark.parametrize("surface", [
    "twenty-first",
    "thirty-second",
    "one-hundred",
])
def test_numerals(surface):
    i = info(surface)
    assert i.surface == surface  # should not crash


@pytest.mark.parametrize("surface", [
    "USA",
    "NATO",
    "NASA",
    "UN",
])
def test_abbreviations(surface):
    i = info(surface)
    # Should be recognized as NOUN (proper) or at least not crash badly.
    assert i.pos in {"NOUN", "UNKNOWN"}


@pytest.mark.parametrize("surface,prefix,base", [
    ("re-evaluate", "re", "evaluate"),
    ("co-operate", "co", "operate"),
    ("pre-existing", "pre", "exist"),
])
def test_hyphenated_prefix(surface, prefix, base):
    i = info(surface)
    # The engine should treat the hyphenated prefix as a derivational step.
    assert base in i.root or i.root == base, (
        f"{surface}: root={i.root!r} expected something like {base!r}"
    )


@pytest.mark.parametrize("surface", [
    "deja",
    "vu",
    "schadenfreude",
    "cliche",
])
def test_foreign_loans(surface):
    i = info(surface)
    # Loans typically have no recognizable English morphology; engine
    # should leave them mostly unchanged and not strip them aggressively.
    assert i.surface == surface


# ============================================================================
# 8. THE -er AGENT vs COMPARATIVE DISAMBIGUATION BUG
# ============================================================================

AGENT_VS_COMP = [
    # (surface, expected_pos, expected_root, kind)
    ("writer", "NOUN", "write", "agent"),
    ("writers", "NOUN", "write", "agent-plural"),
    ("taller", "ADJ", "tall", "comp"),
    ("faster", "ADJ", "fast", "comp"),
    ("lawyer", "NOUN", "law", "agent"),
    ("sooner", "ADV", "soon", "comp-adv"),
    ("painter", "NOUN", "paint", "agent"),
    ("older", "ADJ", "old", "comp"),
]


@pytest.mark.parametrize("surface,exp_pos,exp_root,kind", AGENT_VS_COMP)
def test_er_disambiguation(surface, exp_pos, exp_root, kind):
    i = info(surface)
    assert i.pos == exp_pos, (
        f"{surface} [{kind}]: pos={i.pos!r} expected {exp_pos!r}"
    )
    assert i.root == exp_root, (
        f"{surface} [{kind}]: root={i.root!r} expected {exp_root!r}"
    )
    if kind.startswith("comp"):
        assert i.tags.get("degree") == "COMP"
    if kind.startswith("agent"):
        # Agent nouns must NOT carry a degree=COMP tag.
        assert i.tags.get("degree") != "COMP", (
            f"{surface}: agent noun mis-tagged as COMP"
        )
