"""
test_en_engine_adversarial.py
------------------------------
Adversarial stress tests for EnglishEngine.

Goal: try to BREAK the engine with edge cases, ambiguous words, tricky
suffixes, derivation chains, closed-class coverage, and malformed input.

All expected values verified against actual engine output.

Run: python -m pytest morph_efficiency_project/tests/en_morph/test_en_engine_adversarial.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import pytest
from morph_efficiency_project.scripts.engines import EnglishEngine

engine = EnglishEngine()


def r(w):
    return engine.analyze(w).root


def pos(w):
    return engine.analyze(w).pos


def tags(w):
    return engine.analyze(w).tags


def info(w):
    return engine.analyze(w)


# ======================================================================
# 1. AMBIGUOUS WORDS
# Words that could be multiple POS. Engine must not crash and must
# return a consistent analysis. We verify root and pos are reasonable.
# ======================================================================


class TestAmbiguousWords:
    """Words with multiple possible POS interpretations."""

    # Words that are in irregulars and get a specific analysis
    @pytest.mark.parametrize("word,expected_root,expected_pos", [
        ("run",     "run",    "VERB"),     # irregular past participle
        ("set",     "set",    "VERB"),     # irregular past
        ("read",    "read",   "VERB"),     # irregular past
        ("wound",   "wind",   "VERB"),     # irregular past of wind
    ])
    def test_ambiguous_irregular(self, word, expected_root, expected_pos):
        assert r(word) == expected_root
        assert pos(word) == expected_pos

    # Words that fall through to UNKNOWN (no inflection match)
    # Reason: engine maps known ADJ/VERB bases ('light', 'lead') to ADJ/VERB
    # directly. Only 'bear', 'bank', 'bat', 'bow', 'object', 'minute' stay UNKNOWN.
    @pytest.mark.parametrize("word", [
        "bear", "bank", "bat", "bow", "object", "minute",
    ])
    def test_ambiguous_unknown(self, word):
        result = info(word)
        assert result.root is not None
        assert len(result.root) > 0
        # Reform: unrecognised content words default to NOUN, not UNKNOWN.
        assert result.pos == "NOUN"

    # Words ending in -s that trigger 3SG verb analysis (verb base in COMMON_VERBS)
    @pytest.mark.parametrize("word", [
        "runs", "walks", "eats", "plays", "works", "looks",
        "thinks", "wants", "needs", "feels",
    ])
    def test_ambiguous_3sg_tagged(self, word):
        """Words ending in -s from common verbs are tagged 3SG VERB."""
        result = info(word)
        # Engine maps to 3SG VERB; downstream disambiguation can rewrite to PL noun.
        assert result.pos == "VERB"
        assert result.tags.get("person") == "3SG"

    # Noun/verb homographs ending in -s without verb ambiguity
    @pytest.mark.parametrize("word", [
        "books", "rocks", "parks", "cups", "beds",
    ])
    def test_pure_plural_no_ambiguity(self, word):
        result = info(word)
        assert result.tags.get("num") == "PL"
        assert result.tags.get("ambig_3sg") is None

    # Multi-sense words that happen to match derivation
    @pytest.mark.parametrize("word", [
        "present", "record", "refuse", "desert",
        "permit", "produce", "project", "subject",
    ])
    def test_ambiguous_derivation_stripping(self, word):
        """Engine should not crash on noun/verb homographs."""
        result = info(word)
        assert result.root is not None
        assert len(result.root) > 0


# ======================================================================
# 2. TRICKY SUFFIXES
# Words that superficially look like inflected forms but are NOT.
# ======================================================================


class TestTrickySuffixes:
    """Words where naive suffix stripping gives wrong results."""

    # NOT -ing verbs (len <= 5 protects most, but some are longer)
    @pytest.mark.parametrize("word", [
        "ring", "king", "thing", "sing", "bring", "swing",
        "cling", "fling", "sling", "sting", "wring",
    ])
    def test_not_ing_short(self, word):
        """Short -ing words must not be stripped as progressive."""
        result = info(word)
        assert result.tags.get("aspect") != "PROG"

    # These ARE long enough to trigger -ing stripping (known engine behavior)
    @pytest.mark.parametrize("word,expected_pos", [
        ("string", "VERB"),     # len=6, strips -ing -> "str" -> "stre"
        ("spring", "VERB"),     # len=6, strips -ing -> "spr" -> "spre"
    ])
    def test_false_positive_ing_long(self, word, expected_pos):
        """Known false positives: words long enough to trigger -ing rule."""
        assert pos(word) == expected_pos

    # NOT -ed past (most protected by len <= 4)
    @pytest.mark.parametrize("word", [
        "bed", "red", "wed",
    ])
    def test_not_ed_short(self, word):
        # The guard still prevents -ed stripping: the root is the word intact.
        # POS now defaults to NOUN rather than UNKNOWN.
        assert info(word).root == word
        assert pos(word) == "NOUN"

    # Irregular -ed forms correctly resolved
    @pytest.mark.parametrize("word,expected_root", [
        ("fed",  "feed"),
        ("led",  "lead"),
        ("fled", "flee"),
        ("bred", "breed"),
        ("bled", "bleed"),
        ("sped", "speed"),
        ("shed", "shed"),
    ])
    def test_irregular_short_ed(self, word, expected_root):
        assert r(word) == expected_root
        assert pos(word) == "VERB"

    # NOT -s plural (words ending in -ss)
    # Note: "bass" excluded -- it's in irregulars as zero-plural fish noun
    @pytest.mark.parametrize("word", [
        "mass", "class", "grass", "pass", "glass", "brass",
        "cross", "loss", "boss", "moss", "toss", "dress", "press",
        "stress", "address", "assess", "access", "excess", "process",
        "success", "express", "suppress", "possess",
    ])
    def test_ss_not_plural(self, word):
        result = info(word)
        assert result.tags.get("num") != "PL", (
            f"{word!r}: should not be tagged as plural (-ss ending)"
        )


# ======================================================================
# 3. DOUBLE CONSONANT EDGE CASES
# ======================================================================


class TestDoubleConsonant:
    """Double-consonant handling in -ing and -ed stripping."""

    @pytest.mark.parametrize("word,expected_root", [
        ("mapping",      "map"),
        ("stopping",     "stop"),
        ("running",      "run"),
        ("swimming",     "swim"),
        ("sitting",      "sit"),
        ("getting",      "get"),
        ("putting",      "put"),
        ("cutting",      "cut"),
        ("hitting",      "hit"),
        ("beginning",    "begin"),
        ("forgetting",   "forget"),
        ("occurring",    "occur"),
        ("referring",    "refer"),
        ("permitting",   "permit"),
        ("admitting",    "admit"),
        ("committing",   "commit"),
        ("omitting",     "omit"),
        ("submitting",   "submit"),
        ("transmitting", "transmit"),
        ("acquitting",   "acquit"),
        ("equipping",    "equip"),
        ("kidnapping",   "kidnap"),
        ("handicapping", "handicap"),
        # Updated (stem-validity guard): OLD 'wor' was garbage from undoubling +
        # mis-peeling. 'worshipping' is worship+ing; the guard keeps 'worship'.
        ("worshipping", "worship"),
    ])
    def test_double_consonant_ing(self, word, expected_root):
        assert r(word) == expected_root
        assert tags(word).get("aspect") == "PROG"

    # Bug 5 fix: "added" must keep doubled form
    def test_added_keeps_double_d(self):
        assert r("added") == "add"
        assert tags("added").get("tense") == "PAST"

    @pytest.mark.parametrize("word,expected_root", [
        ("stopped",  "stop"),
        ("planned",  "plan"),
        ("dropped",  "drop"),
        ("grabbed",  "grab"),
        ("mapped",   "map"),
        ("tapped",   "tap"),
        ("shipped",  "ship"),
        ("gripped",  "grip"),
        ("clipped",  "clip"),
        ("skipped",  "skip"),
    ])
    def test_double_consonant_ed(self, word, expected_root):
        assert r(word) == expected_root
        assert tags(word).get("tense") == "PAST"


# ======================================================================
# 4. SILENT-E EDGE CASES
# ======================================================================


class TestSilentE:
    """Silent-e restoration in -ing and -ed stripping."""

    # -ing: hoping vs hopping minimal pairs
    @pytest.mark.parametrize("word,expected_root", [
        ("hoping",    "hope"),
        ("hopping",   "hop"),
        ("biting",    "bite"),
        ("dining",    "dine"),
        ("dinning",   "din"),
        ("coping",    "cope"),
        ("copping",   "cop"),
        ("taping",    "tape"),
        ("tapping",   "tap"),
        ("scraping",  "scrape"),
        ("scrapping", "scrap"),
        ("griping",   "gripe"),
        ("gripping",  "grip"),
        ("pining",    "pine"),
        ("pinning",   "pin"),
        ("wining",    "wine"),
        ("winning",   "win"),
        ("moping",    "mope"),
        ("mopping",   "mop"),
    ])
    def test_silent_e_minimal_pairs_ing(self, word, expected_root):
        assert r(word) == expected_root

    # -ing: silent-e restoration for longer words
    @pytest.mark.parametrize("word,expected_root", [
        ("writing",      "write"),
        ("hiding",       "hide"),
        ("riding",       "ride"),
        ("sliding",      "slide"),
        ("deciding",     "decide"),
        ("providing",    "provide"),
        # Updated (stem-validity guard): these are the correct silent-e
        # restorations this very test targets. OLD values (surv, mbine, cline,
        # nfine, agine) were non-words from a missed silent-e plus a bogus
        # prefix peel (e.g. com|bine). The guard now restores survive / combine /
        # decline / confine / imagine.
        ("surviving", "survive"),
        ("combining", "combine"),
        ("declining", "decline"),
        # 'define' is a lexicalised fused-prefix verb (de- is not separable to the
        # unrelated 'fine'), so defining -> define, consistent with confining ->
        # confine in this very block. OLD expected the over-peel 'fine'.
        ("defining", "define"),
        ("confining", "confine"),
        ("examining",    "examine"),
        ("imagining", "imagine"),
        ("determining",  "determine"),
    ])
    def test_silent_e_longer_ing(self, word, expected_root):
        assert r(word) == expected_root

    # Bug 2 fix: -ed silent-e restoration
    @pytest.mark.parametrize("word,expected_root", [
        ("loved",    "love"),
        ("hoped",    "hope"),
        ("cared",    "care"),
        ("baked",    "bake"),
        ("saved",    "save"),
        ("named",    "name"),
        ("faced",    "face"),
        ("placed",   "place"),
        ("closed",   "close"),
        ("refused", "fuse"),
        # Updated (stem-validity guard): OLD 'duce' was a bogus re|duce prefix
        # peel leaving a non-word. 'reduced' is reduce+ed; the guard restores
        # the real-word silent-e stem 'reduce'.
        ("reduced", "reduce"),
    ])
    def test_silent_e_ed(self, word, expected_root):
        assert r(word) == expected_root
        assert tags(word).get("tense") == "PAST"

    # Bug 4 fix: -ed should NOT have aspect=PERF
    @pytest.mark.parametrize("word", [
        "walked", "talked", "loved", "hoped", "played",
    ])
    def test_ed_no_perf_aspect(self, word):
        t = tags(word)
        assert t.get("tense") == "PAST"
        assert "aspect" not in t, f"{word!r}: should not have aspect tag"


# ======================================================================
# 5. DERIVATION CHAINS
# ======================================================================


class TestDerivationChains:
    """Multi-affix words processed by step_c."""

    @pytest.mark.parametrize("word", [
        "unbelievably",
        "disproportionately",
        "unconstitutionally",
        "incomprehensibility",
        "intercontinental",
        "disestablishment",
        "counterproductive",
        "misunderstanding",
        "overcompensation",
        "underrepresentation",
        "predetermination",
        "internationalization",
        "deindustrialization",
    ])
    def test_derivation_chain_no_crash(self, word):
        """Long derived words must not crash the engine."""
        result = info(word)
        assert result.root is not None
        assert len(result.root) > 0
        assert len(result.root) < len(word), (
            f"{word!r}: root should be shorter than surface after stripping"
        )

    def test_unbelievably_chain(self):
        result = info("unbelievably")
        assert len(result.derived_chain) > 0

    def test_counterproductive_root(self):
        assert r("counterproductive") == "product"

    def test_disestablishment_root(self):
        # Engine restores establish via LEMMA_RESTORE.
        assert r("disestablishment") == "establish"


# ======================================================================
# 6. CLOSED-CLASS STRESS
# ======================================================================


class TestClosedClass:
    """Every determiner, preposition, pronoun, conjunction, and modal."""

    # Determiners
    @pytest.mark.parametrize("word", ["the", "a", "an"])
    def test_determiners(self, word):
        assert pos(word) == "DET"

    # Case insensitivity for closed-class
    @pytest.mark.parametrize("word,expected_pos", [
        ("the",  "DET"),
        ("The",  "DET"),
        ("THE",  "DET"),
        ("And",  "CONJ"),
        ("AND",  "CONJ"),
        ("CAN",  "AUX"),
        ("Can",  "AUX"),
    ])
    def test_closed_class_case_insensitive(self, word, expected_pos):
        assert pos(word) == expected_pos

    # Prepositions
    @pytest.mark.parametrize("word", [
        "to", "of", "in", "at", "by", "for", "with", "on", "from", "about",
        "into", "through", "during", "before", "after", "above", "below",
        "between", "under", "over", "against", "along", "among", "around",
        "behind", "beneath", "beside", "beyond", "despite", "except",
        "inside", "outside", "toward", "towards", "until", "within", "without",
    ])
    def test_prepositions(self, word):
        assert pos(word) == "PREP"

    # Pronouns
    @pytest.mark.parametrize("word", [
        "i", "me", "my", "mine", "you", "your", "yours",
        "he", "him", "his", "she", "her", "hers", "it", "its",
        "we", "us", "our", "ours", "they", "them", "their", "theirs",
        "who", "whom", "whose", "which", "what",
        "this", "these", "those",
        "myself", "yourself", "himself", "herself", "itself",
        "ourselves", "yourselves", "themselves",
    ])
    def test_pronouns(self, word):
        assert pos(word) == "PRON"

    # Note: "that" is both pronoun and conjunction. Engine maps it to PRON.
    def test_that_is_pronoun(self):
        assert pos("that") == "PRON"

    # Conjunctions (those not already mapped as PREP)
    @pytest.mark.parametrize("word", [
        "and", "but", "or", "nor", "so", "yet",
        "although", "because", "since", "unless", "while",
        "if", "when", "where", "as", "though", "whereas", "whether",
    ])
    def test_conjunctions(self, word):
        assert pos(word) == "CONJ"

    # Modals
    @pytest.mark.parametrize("word", [
        "can", "could", "will", "would", "shall", "should",
        "may", "might", "must", "ought", "need", "dare",
    ])
    def test_modals(self, word):
        assert pos(word) == "AUX"
        assert tags(word).get("modal") == "YES"

    # Auxiliary verb forms (from irregulars)
    @pytest.mark.parametrize("word,expected_root", [
        ("am",   "be"),
        ("is",   "be"),
        ("are",  "be"),
        ("was",  "be"),
        ("were", "be"),
        ("been", "be"),
        ("does", "do"),
        ("did",  "do"),
        ("has",  "have"),
        ("had",  "have"),
    ])
    def test_auxiliary_verbs(self, word, expected_root):
        assert r(word) == expected_root
        assert pos(word) == "VERB"

    # "do" base form: a primary auxiliary (function-word fallback -> AUX).
    def test_do_base_form(self):
        assert r("do") == "do"
        assert pos("do") == "AUX"


# ======================================================================
# 7. EDGE CASES
# ======================================================================


class TestEdgeCases:
    """Empty strings, single chars, numbers, punctuation, long words."""

    def test_empty_string(self):
        result = info("")
        assert result.root == ""
        assert result.pos == "UNKNOWN"

    def test_single_char_letter(self):
        result = info("a")
        assert result.pos == "DET"  # closed-class

    def test_single_char_non_letter(self):
        result = info("1")
        assert result.root == "1"
        # Reform: digit-bearing tokens are numerals.
        assert result.pos == "NUM"

    def test_punctuation(self):
        result = info("!")
        assert result.root == "!"
        assert result.pos == "UNKNOWN"

    def test_very_long_word(self):
        w = "supercalifragilisticexpialidocious"
        result = info(w)
        assert result.root is not None
        assert len(result.root) > 0

    # Apostrophe words
    @pytest.mark.parametrize("word", [
        "don't", "can't", "won't", "shouldn't",
        "I'm", "you're", "they've", "she'd", "he'll", "we'd",
    ])
    def test_apostrophe_contractions_no_crash(self, word):
        result = info(word)
        assert result.root is not None

    # 's possessive handling
    @pytest.mark.parametrize("word,expected_root", [
        ("it's",    "it"),
        ("who's",   "who"),
        ("there's", "there"),
        ("here's",  "here"),
        ("let's",   "let"),
        ("that's",  "that"),
        ("what's",  "what"),
    ])
    def test_apostrophe_s_possessive(self, word, expected_root):
        result = info(word)
        assert result.root == expected_root
        assert result.tags.get("poss") == "YES"

    # Hyphenated words
    @pytest.mark.parametrize("word", [
        "well-known", "self-esteem", "mother-in-law",
    ])
    def test_hyphenated_no_crash(self, word):
        result = info(word)
        assert result.root is not None

    # Case handling
    def test_all_caps_running(self):
        assert r("RUNNING") == "run"
        assert pos("RUNNING") == "VERB"

    def test_mixed_case(self):
        result = info("MiXeD")
        assert result.root is not None


# ======================================================================
# 8. KNOWN PROBLEMATIC WORDS FROM AUDIT
# ======================================================================


class TestKnownProblematic:
    """Words specifically identified in the bug audit."""

    # Bug 6: series/species as zero-plural irregulars
    def test_series(self):
        assert r("series") == "series"
        assert tags("series").get("num") == "PL"
        assert pos("series") == "NOUN"

    def test_species(self):
        assert r("species") == "species"
        assert tags("species").get("num") == "PL"
        assert pos("species") == "NOUN"

    # Bug 5: "added" must not undouble to "ad"
    def test_added(self):
        assert r("added") == "add"
        assert pos("added") == "VERB"

    # Bug 2: silent-e restoration for -ed
    def test_loved(self):
        assert r("loved") == "love"

    def test_hoped(self):
        assert r("hoped") == "hope"

    def test_cared(self):
        assert r("cared") == "care"

    def test_baked(self):
        assert r("baked") == "bake"

    # Dying/lying/tying: -ying not handled (len <= 5)
    @pytest.mark.parametrize("word", ["dying", "lying", "tying"])
    def test_short_ying_words(self, word):
        result = info(word)
        # -ing not stripped (too short); root stays intact, POS defaults to NOUN.
        assert result.root == word
        assert result.pos == "NOUN"

    # Short past forms: engine strips -ied as PAST verb (current behavior).
    @pytest.mark.parametrize("word", ["died", "lied", "tied"])
    def test_short_ied_words(self, word):
        result = info(word)
        assert result.pos == "VERB"
        assert result.tags.get("tense") == "PAST"

    def test_bus(self):
        # NOT_PLURAL_S guard keeps the -s; POS defaults to NOUN (bus is a noun).
        result = info("bus")
        assert result.root == "bus"
        assert result.pos == "NOUN"

    def test_minus(self):
        # NOT_PLURAL_S guard keeps the -s; POS defaults to NOUN.
        result = info("minus")
        assert result.root == "minus"
        assert result.pos == "NOUN"


# ======================================================================
# 9. BUG FIX VERIFICATION
# ======================================================================


class TestBugFixes:
    """Verify each specific bug fix is working."""

    # Bug 1: Derivation matching works (not dead code)
    def test_derivation_suffix_works(self):
        result = info("darkness")
        assert result.root == "dark"
        assert len(result.derived_chain) > 0

    def test_derivation_prefix_works(self):
        result = info("unhappy")
        assert result.root == "happy"
        assert len(result.derived_chain) > 0

    # Bug 2: Silent-e restored for -ed
    def test_ed_silent_e(self):
        assert r("loved") == "love"
        assert r("hoped") == "hope"
        assert r("baked") == "bake"
        assert r("cared") == "care"

    # Bug 3: runs is 3SG VERB (downstream disambiguator can rewrite to PL).
    def test_3sg_ambiguity(self):
        result = info("runs")
        assert result.pos == "VERB"
        assert result.tags.get("person") == "3SG"

    def test_non_verb_no_ambig(self):
        result = info("cats")
        assert result.tags.get("ambig_3sg") is None

    # Bug 4: -ed no longer has PERF aspect
    def test_ed_no_perf(self):
        t = tags("walked")
        assert t == {"tense": "PAST"}

    # Bug 5: "added" keeps "add" not "ad"
    def test_added_root(self):
        assert r("added") == "add"

    # Bug 6: series/species in irregulars
    def test_series_irregular(self):
        assert r("series") == "series"

    # Bug 7: Compounds loaded and used
    def test_compound_software(self):
        result = info("software")
        assert result.root == "ware"
        assert any("COMPOUND" in c for c in result.derived_chain)

    def test_compound_database(self):
        result = info("database")
        assert result.root == "base"

    # Bug 8: Phrasal verbs loaded
    def test_phrasal_verb_data_loaded(self):
        assert len(engine.phrasal_verbs) > 0
        assert len(engine.phrasal_verb_components) > 0

    # Bug 9: Closed-class words recognized
    def test_closed_class_det(self):
        assert pos("the") == "DET"

    def test_closed_class_prep(self):
        assert pos("to") == "PREP"

    def test_closed_class_pron(self):
        assert pos("he") == "PRON"

    def test_closed_class_conj(self):
        assert pos("and") == "CONJ"

    def test_closed_class_aux(self):
        assert pos("can") == "AUX"


# ======================================================================
# 10. SENTENCE-LEVEL ADVERSARIAL
# ======================================================================


class TestSentenceAdversarial:
    """Sentence-level analysis with adversarial inputs."""

    def test_empty_sentence(self):
        tokens, ok, msg = engine.analyze_sentence("")
        assert tokens == []
        assert ok is True

    def test_single_closed_class(self):
        tokens, ok, msg = engine.analyze_sentence("the")
        assert len(tokens) == 1
        assert tokens[0].pos == "DET"

    def test_all_closed_class(self):
        tokens, ok, msg = engine.analyze_sentence("the and or but")
        assert len(tokens) == 4
        assert tokens[0].pos == "DET"

    def test_mixed_known_unknown(self):
        tokens, ok, msg = engine.analyze_sentence("the cat ran quickly")
        assert len(tokens) == 4
        assert tokens[0].pos == "DET"
        assert tokens[1].pos == "NOUN"  # reform: 'cat' defaults to NOUN
        assert tokens[2].root == "run"

    def test_sentence_all_tokens_have_root(self):
        sentence = "he can quickly run to the store"
        tokens, _, _ = engine.analyze_sentence(sentence)
        for tok in tokens:
            assert tok.root is not None
            assert len(tok.root) > 0

    def test_sentence_preserves_surfaces(self):
        sentence = "The CAT ran QUICKLY"
        tokens, _, _ = engine.analyze_sentence(sentence)
        assert [t.surface for t in tokens] == ["The", "CAT", "ran", "QUICKLY"]
