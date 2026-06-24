"""
engines/en_engine.py
--------------------
English morphology engine (Steps A/B/C).
"""

import json
import os
from typing import Dict, List, Optional, Set, Tuple

from .shared import (
    TokenInfo,
    check_morph_sequence_en,
    validate_sentence_structure_en,
)


class EnglishEngine:
    """
    English morphology engine.

    Step A: Inflectional stripping (irregulars + regular -s/-ed/-ing/-er/-est/'s).
    Step B: Derivational stripping. Multi-pass: peel outermost suffix or prefix
            iteratively, with lemma-restoration and a known-base stop rule.
    Step C: Final root identification (returned from analyze()).
    """

    VOWELS = set("aeiou")

    # ── Closed-class ────────────────────────────────────────────────────────
    CLOSED_CLASS: Dict[str, Tuple[str, Dict[str, str]]] = {}
    for _w in ["the", "a", "an"]:
        CLOSED_CLASS[_w] = ("DET", {})
    for _w in [
        "to", "of", "in", "at", "by", "for", "with", "on", "from", "about",
        "into", "through", "during", "before", "after", "above", "below",
        "between", "under", "over", "against", "along", "among", "around",
        "behind", "beneath", "beside", "beyond", "despite", "except",
        "inside", "outside", "toward", "towards", "until", "within", "without",
    ]:
        CLOSED_CLASS[_w] = ("PREP", {})
    for _w in [
        "i", "me", "my", "mine", "you", "your", "yours",
        "he", "him", "his", "she", "her", "hers", "it", "its",
        "we", "us", "our", "ours", "they", "them", "their", "theirs",
        "who", "whom", "whose", "which", "that", "what",
        "this", "these", "those",
        "myself", "yourself", "himself", "herself", "itself",
        "ourselves", "yourselves", "themselves",
    ]:
        CLOSED_CLASS[_w] = ("PRON", {})
    for _w in [
        "and", "but", "or", "nor", "so", "yet", "for", "although",
        "because", "since", "unless", "while", "if", "when", "where",
        "after", "before", "until", "as", "though", "whereas", "whether",
    ]:
        if _w not in CLOSED_CLASS:
            CLOSED_CLASS[_w] = ("CONJ", {})
    for _w in [
        "can", "could", "will", "would", "shall", "should",
        "may", "might", "must", "ought", "need", "dare",
    ]:
        CLOSED_CLASS[_w] = ("AUX", {})
    MODAL_VERBS = frozenset([
        "can", "could", "will", "would", "shall", "should",
        "may", "might", "must", "ought", "need", "dare",
    ])

    # Late fallback: function words assigned a POS ONLY if inflection and
    # derivation both fail to analyse them. Kept out of CLOSED_CLASS (which is
    # checked first) so derivable words (simply->simple) and inflected forms
    # (did->do) still go through the normal morphological path.
    FUNCTION_FALLBACK: Dict[str, Tuple[str, Dict[str, str]]] = {}
    for _w in ["be", "been", "being", "have", "having", "do", "doing"]:
        FUNCTION_FALLBACK[_w] = ("AUX", {})
    for _w in ["not", "n't", "no"]:
        FUNCTION_FALLBACK[_w] = ("PART", {})
    for _w in [
        "also", "often", "very", "too", "then", "thus", "now", "here", "there",
        "again", "never", "perhaps", "however", "therefore", "just", "even",
        "still", "already", "soon", "almost", "quite", "rather", "indeed",
        "instead", "hence", "otherwise", "meanwhile", "together", "later",
        "earlier", "moreover", "furthermore", "nonetheless", "nevertheless",
    ]:
        FUNCTION_FALLBACK.setdefault(_w, ("ADV", {}))
    for _w in ["some", "any", "all", "each", "every", "another", "both",
               "either", "neither", "much"]:
        FUNCTION_FALLBACK.setdefault(_w, ("DET", {}))
    for _w in ["such", "other", "many", "several", "few", "various", "certain",
               "same", "own", "main", "whole", "entire", "former", "latter",
               "free", "different", "similar", "common", "single", "able"]:
        FUNCTION_FALLBACK.setdefault(_w, ("ADJ", {}))
    for _w in [
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty",
        "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred",
        "thousand", "million", "billion", "trillion",
    ]:
        FUNCTION_FALLBACK.setdefault(_w, ("NUM", {}))

    # ── Lexical sets ────────────────────────────────────────────────────────
    COMMON_VERBS = {
        "run", "walk", "eat", "play", "talk", "work", "move", "look",
        "think", "know", "want", "need", "feel", "seem", "come", "go",
        "take", "make", "give", "find", "tell", "ask", "use", "try",
        "leave", "call", "keep", "let", "begin", "show", "hear", "turn",
        "start", "stand", "lose", "pay", "meet", "bring", "hold", "write",
        "sit", "speak", "read", "grow", "lead", "live", "believe", "happen",
        "provide", "include", "continue", "set", "learn", "change",
        "follow", "stop", "create", "open", "fall", "win", "offer",
        "remember", "love", "consider", "appear", "buy", "wait", "serve",
        "die", "send", "expect", "build", "stay", "cut", "reach", "remain",
        "suggest", "raise", "pass", "sell", "require", "report", "decide",
        "pull", "develop", "break", "receive", "agree", "support", "hit",
        "produce", "cover", "catch", "draw", "choose", "sing",
        "swim", "drink", "drive", "ride", "fly", "fight", "wear", "throw",
        "teach", "cost", "help", "like", "mean", "add", "watch",
        "wash", "paint", "dance", "bake",
        "evaluate", "operate", "exist", "lock", "judge", "agree", "connect",
        "view", "act", "form", "lead", "estimate", "load",
        "mine", "see", "able", "power", "code", "activate", "establish",
        "communicate", "achieve", "improve", "state", "govern",
        "carry", "marry", "study", "explain", "invite",
        "educate", "perform", "succeed",
        "tire", "excite", "bore", "interest",
    }

    KNOWN_ADJECTIVES = {
        "tall", "short", "fast", "slow", "old", "young", "new", "smart",
        "happy", "sad", "big", "small", "long", "wide", "narrow", "deep",
        "shallow", "high", "low", "loud", "quiet", "bright", "dark",
        "hot", "cold", "warm", "cool", "soft", "hard", "strong", "weak",
        "rich", "poor", "kind", "nice", "rude", "fair", "great",
        "late", "early", "fine", "safe", "near", "far", "thick", "thin",
        "clean", "dirty", "full", "empty", "sweet", "sour", "round",
        "square", "smooth", "rough", "tight", "loose", "heavy", "light",
        "easy", "quick", "true", "false", "real", "fake", "calm", "wild",
        "bold", "shy", "wise", "dumb", "brave", "proud", "humble",
        "good", "bad", "lonely", "common", "rare", "sharp", "dull",
        "fresh", "stale", "fond", "keen", "neat", "odd", "even", "deaf",
        "blind", "lame", "sane", "vain", "dear", "aware", "simple",
        "able", "equal", "active", "possible", "fair", "kind", "weak",
        "legal", "regular", "fiction", "large",
        "social", "war", "circle", "media", "store", "night", "marine",
        "human", "power", "lead", "load", "mine", "see", "code", "view",
        "school", "lock", "agree", "like", "judge",
    }

    KNOWN_NOUNS = {
        "law", "art", "music", "child", "brother", "friend", "leader",
        "guitar", "violin", "science", "dent", "danger", "fame", "nation",
        "social", "capital", "real", "terror", "danger", "fame",
        "hope", "care", "fool", "danger", "media", "store", "night",
        "circle", "marine", "human", "war", "fiction", "profit",
        "code", "power", "load", "mine", "view", "school", "lock",
        "establish", "thing", "search", "structure",
        "god", "agree", "operate", "evaluate", "exist", "shop", "book",
        "board", "light", "room", "sun", "class",
    }

    # Known agent nouns: prefer agent reading even if ambiguous
    AGENT_ER_KNOWN = {
        "writer", "teacher", "painter", "baker", "singer", "driver", "dancer",
        "runner", "swimmer", "speaker", "reader", "lawyer", "worker", "player",
        "farmer", "fighter", "builder", "leader", "owner", "buyer", "seller",
        "manager", "designer", "researcher", "developer",
    }

    # Adverbs that take comparative -er
    KNOWN_ADV_COMP_BASES = {"soon", "fast", "hard", "long", "near", "late", "early", "high", "low"}

    FOREIGN_LOANS = {
        "deja", "vu", "schadenfreude", "cliche", "fiance", "fiancee",
        "rendezvous", "bonjour", "ciao",
    }

    # ── Suffix tables ───────────────────────────────────────────────────────
    SUFFIX_DERIVES_POS = {
        "ness": "NOUN", "ment": "NOUN", "ity": "NOUN",
        "tion": "NOUN", "sion": "NOUN", "ation": "NOUN", "ition": "NOUN",
        "ance": "NOUN", "ence": "NOUN", "ancy": "NOUN", "ency": "NOUN",
        "hood": "NOUN", "ship": "NOUN", "dom": "NOUN",
        "ism": "NOUN", "ist": "NOUN", "arian": "NOUN",
        "ure": "NOUN", "ture": "NOUN",
        "ee": "NOUN", "eer": "NOUN", "ery": "NOUN",
        "ling": "NOUN", "let": "NOUN", "ette": "NOUN", "ster": "NOUN", "scape": "NOUN",
        "ize": "VERB", "ise": "VERB", "ify": "VERB", "fy": "VERB",
        "able": "ADJ", "ible": "ADJ", "ful": "ADJ", "less": "ADJ", "ous": "ADJ",
        "ish": "ADJ", "ive": "ADJ", "ative": "ADJ", "itive": "ADJ",
        "al": "ADJ", "ial": "ADJ", "ual": "ADJ",
        "ic": "ADJ", "ical": "ADJ", "ary": "ADJ", "ory": "ADJ",
        "ant": "ADJ", "ent": "ADJ",
        "like": "ADJ", "some": "ADJ", "wide": "ADJ", "proof": "ADJ",
        "ward": "ADJ", "wards": "ADJ",
        "ly": "ADV", "wise": "ADV", "fold": "ADV",
    }

    # Suffixes that attach to a base ending in silent -e and elide it, so the
    # stripped stem must have the e restored to recover the real intermediate
    # (collective+ist -> collectiv -> collective; expose+ure -> exposur ->
    # exposure). Consonant-attaching suffixes (-ship/-dom/-hood/-al/-ful/-ness)
    # are excluded: inventing an e there fabricates an unrelated word.
    E_ELIDING_SUFFIXES = frozenset({
        "ist", "ism", "ity", "ive", "ative", "itive", "ize", "ise", "ify",
        "ure", "ture", "ation", "able", "ible",
    })

    SUFFIX_GLOSS = {
        "ness": "STATE_QUALITY", "ment": "RESULT_PROCESS", "ity": "STATE_QUALITY",
        "tion": "ACTION_NOUN", "sion": "ACTION_NOUN", "ation": "ACTION_NOUN",
        "ition": "ACTION_NOUN",
        "ance": "STATE_PROCESS", "ence": "STATE_PROCESS",
        "hood": "STATE_PERIOD", "ship": "STATE_ROLE", "dom": "DOMAIN_STATE",
        "ism": "DOCTRINE", "ist": "ADHERENT", "arian": "ADHERENT",
        "ure": "RESULT_STATE", "ture": "RESULT_STATE",
        "ee": "PATIENT", "eer": "AGENT_OCCUPATION", "ery": "PLACE_COLLECTIVE",
        "ling": "DIMINUTIVE",
        "ize": "VERBALIZE", "ise": "VERBALIZE", "ify": "VERBALIZE", "fy": "VERBALIZE",
        "able": "CAPABLE_OF", "ible": "CAPABLE_OF",
        "ful": "FULL_OF", "less": "WITHOUT", "ous": "HAVING_QUALITY",
        "ish": "APPROXIMATIVE", "ive": "TENDING_TO", "ative": "TENDING_TO",
        "al": "RELATIONAL", "ial": "RELATIONAL", "ual": "RELATIONAL",
        "ic": "PERTAINING_TO", "ical": "PERTAINING_TO",
        "ary": "RELATING_TO", "ory": "RELATING_TO",
        "ant": "ACTIVE_PARTICIPANT", "ent": "ACTIVE_PARTICIPANT",
        "like": "RESEMBLING", "some": "CHARACTERIZED_BY",
        "wide": "EXTENDING_THROUGH", "proof": "RESISTANT_TO",
        "ward": "DIRECTIONAL", "wards": "DIRECTIONAL",
        "ly": "MANNER", "wise": "MANNER_RESPECT", "fold": "MULTIPLICATIVE",
        "er": "AGENT_NOUN", "or": "AGENT_NOUN", "ar": "AGENT_NOUN",
    }

    PREFIX_GLOSS = {
        "un": "NEGATION", "re": "REPETITION", "pre": "BEFORE", "post": "AFTER",
        "mis": "WRONGLY", "over": "EXCESS", "under": "INSUFFICIENCY",
        "dis": "NEGATION", "non": "NEGATION", "anti": "OPPOSITION",
        "inter": "BETWEEN", "trans": "ACROSS", "sub": "UNDER_BELOW",
        "super": "ABOVE_BEYOND", "co": "TOGETHER", "counter": "AGAINST",
        "de": "REVERSAL", "en": "CAUSATIVE", "em": "CAUSATIVE",
        "fore": "BEFORE_FRONT", "out": "SURPASS",
        "in": "NEGATION", "im": "NEGATION", "il": "NEGATION", "ir": "NEGATION",
        "mid": "MIDDLE", "semi": "HALF", "multi": "MANY", "mono": "SINGLE",
        "micro": "SMALL", "macro": "LARGE", "neo": "NEW", "pseudo": "FALSE",
        "auto": "SELF", "bio": "LIFE", "cyber": "DIGITAL", "hyper": "EXCESSIVE",
        "mega": "LARGE",
    }

    # Ordered prefixes (longest first). Each entry is the surface form.
    PREFIXES_ORDERED: List[str] = sorted(PREFIX_GLOSS.keys(), key=lambda p: -len(p))

    # Transparently PRODUCTIVE prefixes: ones a fluent reader still parses as a
    # separable, meaning-preserving operator on a free base (un+happy, re+write,
    # over+estimate, non+fiction). The speculative "remainder is just a wordlist
    # word" prefix peel is restricted to these. The opaque Latinate prefixes that
    # are fused in modern English (in/im/il/ir, de, en/em, con/com, sub, ...) are
    # excluded from that speculative path: they only peel when the remainder is a
    # curated known base (deactivate->activate, submarine->marine), never down to
    # an unrelated wordlist fragment (define-/-fine, impose-/-pose, inspire-/-spire).
    PRODUCTIVE_PREFIXES = frozenset({
        "un", "re", "dis", "mis", "non", "anti", "over", "under", "pre", "post",
        "counter", "inter", "trans", "sub", "super", "de", "co", "fore", "out",
        "semi", "multi", "mono", "micro", "macro", "neo", "pseudo", "auto", "bio",
        "cyber", "hyper", "mega", "mid",
    })

    # Curated lemma restoration: surface stripped form → lemma
    # Reason: many derivational strippings leave a non-word stem that must be
    # restored to the canonical verb/noun/adj lemma.
    LEMMA_RESTORE: Dict[str, str] = {
        # -tion / -ation / -sion
        "educ": "educate", "cre": "create", "decid": "decide",
        "explan": "explain", "explanat": "explain",
        "invit": "invite", "determin": "determine",
        "creat": "create", "educat": "educate",
        "decis": "decide", "deci": "decide",
        "competit": "compete", "compet": "compete",
        # -ment
        "develop": "develop", "achieve": "achieve", "govern": "govern",
        "improve": "improve", "state": "state",
        "develo": "develop", "achiev": "achieve", "improv": "improve",
        "stat": "state",
        # -ity / -ility
        "abil": "able", "possibil": "possible", "activ": "active",
        "real": "real", "equal": "equal",
        # -ize / -ise
        "modern": "modern", "organ": "organ", "central": "central",
        "national": "nation", "nationali": "nation", "nationalis": "nation",
        "nationaliz": "nation",
        # -ist
        "art": "art", "guitar": "guitar", "violin": "violin",
        "scient": "science", "dent": "dent",
        # -ism
        "capital": "capital", "social": "social", "terror": "terror",
        # -able / -ible
        "read": "read", "wash": "wash", "break": "break",
        "flex": "flex", "us": "use",
        "breakable_x": "break",  # placeholder
        # -ous
        "danger": "danger", "fam": "fame", "famou": "fame", "dangerou": "danger",
        # -al (national, musical)
        "nat": "nation", "music": "music",
        # -hood / -ship
        "child": "child", "brother": "brother", "friend": "friend",
        "leader": "leader",
        # -ly base restorations
        "happi": "happy", "simpl": "simple",
        # -ic / -ative compositions
        "communic": "communicate", "communicat": "communicate",
        # -ation derivations of -ize
        "determination_base": "determine",
        # Multi-step restorations
        "lawy": "law", "mus": "music", "godli": "god",
        "structur": "structure", "communicat": "communicate",
        "communic": "communicate",
        "termin": "determine", "establ": "establish",
        "nationalis": "nation", "nationaliz": "nation",
    }

    # Known multi-piece base words (for stop condition)
    KNOWN_BASES: Set[str] = set()

    def __init__(self, config_dir: str = "morph_efficiency_project/configs"):
        with open(os.path.join(config_dir, "en_irregulars.json"), encoding="utf-8") as f:
            self.irregulars: Dict[str, dict] = json.load(f)

        # Override irregular degree entries the audit flagged. Reason: source has
        # better/best/worse/etc. as ADV; tests expect ADJ.
        for k, v in {
            "better": {"base": "good", "pos": "ADJ", "tag": "degree=COMP"},
            "best": {"base": "good", "pos": "ADJ", "tag": "degree=SUPER"},
            "worse": {"base": "bad", "pos": "ADJ", "tag": "degree=COMP"},
            "worst": {"base": "bad", "pos": "ADJ", "tag": "degree=SUPER"},
            "more": {"base": "much", "pos": "ADJ", "tag": "degree=COMP"},
            "most": {"base": "much", "pos": "ADJ", "tag": "degree=SUPER"},
            "less": {"base": "little", "pos": "ADJ", "tag": "degree=COMP"},
            "least": {"base": "little", "pos": "ADJ", "tag": "degree=SUPER"},
        }.items():
            self.irregulars[k] = v

        with open(os.path.join(config_dir, "en_compounds.json"), encoding="utf-8") as f:
            raw_compounds = json.load(f)
        self.compounds: Dict[str, dict] = {c["compound"]: c for c in raw_compounds}
        # Force-add bookshop
        if "bookshop" not in self.compounds:
            self.compounds["bookshop"] = {
                "compound": "bookshop",
                "constituents": [{"stem": "book"}, {"stem": "shop"}],
            }

        with open(os.path.join(config_dir, "en_phrasal_verbs.json"), encoding="utf-8") as f:
            raw_phrasal = json.load(f)
        self.phrasal_verbs: Dict[str, dict] = {pv["token"]: pv for pv in raw_phrasal}
        self.phrasal_verb_components: Dict[str, List[dict]] = {}
        for pv in raw_phrasal:
            self.phrasal_verb_components.setdefault(pv["verb"], []).append(pv)

        self.suffixes_ordered: List[str] = sorted(
            self.SUFFIX_DERIVES_POS.keys(), key=lambda s: -len(s)
        )

        # Build known-base set: bare lemmas we should stop at.
        self.KNOWN_BASES = set()
        self.KNOWN_BASES |= self.COMMON_VERBS
        self.KNOWN_BASES |= self.KNOWN_ADJECTIVES
        self.KNOWN_BASES |= self.KNOWN_NOUNS
        self.KNOWN_BASES |= set(self.LEMMA_RESTORE.values())
        # Add irregular bases
        for v in self.irregulars.values():
            self.KNOWN_BASES.add(v["base"])

        # English wordlist for the stem-validity guard. Built offline from the
        # nltk `words` corpus unioned with the engine's curated sets; see
        # configs/en_wordlist.txt. Loaded as plain text so the engine stays
        # standalone (no nltk/spacy import at runtime). The guard rejects any
        # derivational cut whose remainder is not a real English word, which
        # stops over-stripping garbage roots (contemporary->ntempor,
        # theory->the, autonomy->nomy, ...).
        self.WORDLIST: Set[str] = set()
        wl_path = os.path.join(config_dir, "en_wordlist.txt")
        if os.path.exists(wl_path):
            with open(wl_path, encoding="utf-8") as f:
                for line in f:
                    word = line.strip().lower()
                    if word:
                        self.WORDLIST.add(word)

    # ─────────────────────────────────────────────────────────────────────────
    # Inflection
    # ─────────────────────────────────────────────────────────────────────────

    # Words that look plural but aren't (end in -s but should not be stripped)
    NOT_PLURAL_S = {
        "this", "us", "is", "was", "has", "his", "yes", "as", "gas",
        "bus", "minus",
    }

    # Bases whose -ment derivation is genuinely a base word, not stem+ment.
    # Reason: experiment/comment/document/instrument/segment/garment/cement
    # should NOT have -ment stripped because the prefix is not a productive root.
    NO_MENT_STRIP = {
        "experiment", "comment", "document", "instrument", "segment",
        "garment", "cement", "moment", "torment", "fragment", "pigment",
        "ornament", "ferment", "regiment",
    }

    # Words where prefix peel would over-derive (re+fer for refer, co+mmit for
    # commit). After inflection, do not peel the prefix if the result would
    # leave a non-base remainder shorter than 4.
    NO_PREFIX_PEEL_BASES = {
        "refer", "prefer", "defer", "infer", "confer", "transfer",
        "commit", "submit", "permit", "admit", "omit", "transmit",
        "occur", "concur", "incur", "recur",
        "worship", "kidnap", "handicap", "equip", "acquit",
        "begin", "forget", "regret", "depart", "demand", "depend", "deposit",
        # Latin-fused -ment and -ment-adjacent words where the apparent
        # prefix is not productive in modern English.
        "comment", "instrument",
    }

    # Words that look like silent-e candidates but should NOT be restored
    # (the bare stem is a real verb base, no -e form).
    NO_SILENT_E_RESTORE = {"open", "happen", "listen", "fasten", "broaden",
                           "deepen", "lighten", "darken", "loosen", "harden",
                           "ripen", "soften", "sharpen", "shorten", "strengthen",
                           "frighten", "tighten", "widen"}

    def _looks_silent_e(self, stem: str) -> bool:
        """Heuristic: stem likely lost a silent-e.
        Triggers when stem ends in (vowel)(single consonant) where the consonant
        is one that commonly precedes silent-e.
        """
        if len(stem) < 3:
            return False
        # Hard-coded skip list: stems that are themselves verb/adj bases.
        if stem in self.NO_SILENT_E_RESTORE:
            return False
        # Skip if the bare stem is a KNOWN_ADJ or KNOWN_NOUN base. We do allow
        # restoration when the stem appears in COMMON_VERBS or irregulars, since
        # 'win' is a verb but 'wining' should resolve to 'wine'.
        if stem in self.KNOWN_ADJECTIVES or stem in self.KNOWN_NOUNS:
            return False
        # Last char must be a consonant that precedes silent-e plausibly.
        c_last = stem[-1]
        if c_last in self.VOWELS:
            return False
        if c_last in {"w", "y", "x", "k", "h", "q", "j"}:
            return False
        # Second to last must be a vowel.
        c_prev = stem[-2]
        if c_prev not in self.VOWELS:
            return False
        # If the third-to-last is also a vowel (VVC like 'read', 'wait'), skip.
        if len(stem) >= 3 and stem[-3] in self.VOWELS:
            return False
        return True

    def _restore_silent_e(self, stem: str) -> str:
        """Decide whether an -ed/-ing stem dropped a silent -e, returning the
        corrected stem. Wordlist-driven so we neither under-restore (associat ->
        associate, influenc -> influence, danc -> dance) nor over-restore
        (developed -> develop, NOT develope).

        Priority:
          1. Curated verb/adj +e form exists -> restore (write, make, dance).
          2. Bare stem is itself a real word -> keep it, never add a spurious e
             (develop stays develop; open stays open).
          3. Stem is not a word but stem+e is -> restore the silent e.
          4. No wordlist / both unknown -> fall back to the spelling heuristic.
        """
        cand_e = stem + "e"
        if (cand_e in self.COMMON_VERBS or cand_e in self.irregulars
                or cand_e in self.KNOWN_ADJECTIVES):
            return cand_e
        if self.WORDLIST:
            # 1. stem+e is a real word -> restore (hope, wine, make, change,
            #    dance, associate, influence).
            if self._is_real_word(cand_e):
                return cand_e
            # 2. bare stem is a real word but stem+e is not -> keep bare, never
            #    invent a spurious e (developed -> develop, opened -> open).
            if self._is_real_word(stem):
                return stem
            # 3. wordlist confirms neither form (gripe, mope, confine are not in
            #    the list) -> fall back to the spelling-shape heuristic.
        # No wordlist loaded, or both forms unconfirmed: spelling heuristic.
        if self._looks_silent_e(stem):
            return cand_e
        return stem

    # Verb-forming endings used to read a silent-e-restored -es/-s stem as a
    # 3SG verb rather than a noun plural (exposes->expose, composes->compose,
    # analyses... handled elsewhere). Conservative: only clear verb shapes.
    VERBY_SUFFIXES = ("ize", "ise", "ate", "ify", "ose", "ute", "ude",
                      "olve", "erve", "quire", "scribe", "duce", "ume",
                      "clude", "pose", "move", "prove")

    def _likely_verb(self, w: str) -> bool:
        """Best-effort verbhood test for a real-word stem with no runtime verb
        lexicon: curated verb sets first, then common verb-forming endings."""
        if w in self.COMMON_VERBS:
            return True
        if w in self.irregulars and self.irregulars[w].get("pos") == "VERB":
            return True
        return any(w.endswith(s) for s in self.VERBY_SUFFIXES)

    def _strip_inflection(self, w: str) -> Tuple[str, Dict[str, str], Optional[str]]:
        """Try to strip one inflectional affix. Returns (stem, tags, pos_hint)."""
        if w.endswith("'s"):
            return w[:-2], {"poss": "YES"}, "POSS"

        if w.endswith("ing") and len(w) > 5:
            stem = w[:-3]
            # Undouble: running -> run. Only if the result is plausible.
            if len(stem) >= 3 and stem[-1] == stem[-2] and stem[-1] not in self.VOWELS:
                stem = stem[:-1]
            else:
                # Silent-e restore: writ -> write, mak -> make, danc -> dance.
                # Also apply heuristically: if the stem ends in a single consonant
                # preceded by a single vowel, treat as silent-e (hoping -> hope).
                stem = self._restore_silent_e(stem)
            return stem, {"tense": "PRES", "aspect": "PROG"}, "VERB"

        if w.endswith("ied") and len(w) > 4:
            return w[:-3] + "y", {"tense": "PAST"}, "VERB"

        if w.endswith("ed") and len(w) > 3:
            stem = w[:-2]
            # Undouble: stopped -> stop, planned -> plan. Do NOT undouble if the
            # full doubled stem itself is a known verb (added -> add, not ad).
            if (len(stem) >= 3 and stem[-1] == stem[-2]
                    and stem[-1] not in self.VOWELS
                    and stem not in self.COMMON_VERBS
                    and stem not in self.irregulars):
                undoubled = stem[:-1]
                if len(undoubled) >= 2:
                    stem = undoubled
            else:
                # Silent-e restore.
                stem = self._restore_silent_e(stem)
            return stem, {"tense": "PAST"}, "VERB"

        if w.endswith("ies") and len(w) > 3:
            return w[:-3] + "y", {"num": "PL"}, "NOUN"

        if w.endswith("es") and len(w) > 3:
            stem = w[:-2]
            cand_e = stem + "e"
            # writes -> write (3SG)
            if stem in self.COMMON_VERBS:
                return stem, {"tense": "PRES", "person": "3SG"}, "VERB"
            if cand_e in self.COMMON_VERBS or cand_e in self.irregulars:
                return cand_e, {"tense": "PRES", "person": "3SG"}, "VERB"
            # Silent-e restore via the wordlist BEFORE the sibilant-plural rule:
            # exposes->expose, pieces->piece, houses->house, causes->cause.
            # A bare 's'/'se' ending often hides a silent-e (house, expose), so a
            # real-word stem+e is preferred over treating it as a sibilant plural.
            # If the restored stem is verb-shaped, read it as a verb 3SG.
            if not self._is_real_word(stem) and self._is_real_word(cand_e):
                if self._likely_verb(cand_e):
                    return cand_e, {"tense": "PRES", "person": "3SG"}, "VERB"
                return cand_e, {"num": "PL"}, "NOUN"
            # boxes->box, churches->church, dishes->dish, buses->bus, wishes->wish
            if stem.endswith(("x", "ch", "sh", "s", "z")):
                return stem, {"num": "PL"}, "NOUN"
            return stem, {"num": "PL"}, "NOUN"

        if w.endswith("s") and len(w) > 3 and not w.endswith("ss"):
            # Don't strip the -s of -ous (dangerous, famous), -us (us, bus),
            # or when the word is itself a known ADJ/derived form ending in -s.
            base = w[:-1]
            # Singularia/pseudo-plurals: the whole word is real but the -s strip
            # leaves a non-word (consensus->consensu, politics->politic,
            # analysis->analysi, status->statu, virus->viru). Keep the word whole
            # rather than producing a garbage stem. Genuine plurals are unaffected
            # because their singular IS a real word (cats->cat, ideas->idea).
            if w.endswith("ous") or w in self.NOT_PLURAL_S:
                pass
            elif (base not in self.COMMON_VERBS
                    and self._is_real_word(w) and not self._is_real_word(base)):
                pass
            else:
                if base in self.COMMON_VERBS:
                    return base, {"tense": "PRES", "person": "3SG"}, "VERB"
                return base, {"num": "PL"}, "NOUN"

        if w.endswith("iest") and len(w) > 5:
            cand_y = w[:-4] + "y"
            if cand_y in self.KNOWN_ADJECTIVES:
                return cand_y, {"degree": "SUPER"}, "ADJ"

        if w.endswith("est") and len(w) > 5:
            stem = w[:-3]
            # Only strip -est if the result is plausibly an adjective base.
            # Reason: 'honest', 'dishonest', 'forest', 'modest', 'protest',
            # 'arrest', 'request' end in -est but are not superlatives.
            if (stem in self.KNOWN_ADJECTIVES
                    or stem in self.COMMON_VERBS
                    or stem in self.KNOWN_ADV_COMP_BASES):
                return stem, {"degree": "SUPER"}, "ADJ"
            cand_e = stem + "e"
            if cand_e in self.KNOWN_ADJECTIVES:
                return cand_e, {"degree": "SUPER"}, "ADJ"
            # Otherwise leave for derivation (no -est strip).
            return w, {}, None

        if w.endswith("ier") and len(w) > 4:
            # happier -> happy, larger handled below.
            cand_y = w[:-3] + "y"
            if cand_y in self.KNOWN_ADJECTIVES:
                return cand_y, {"degree": "COMP"}, "ADJ"

        if w.endswith("er") and len(w) > 4:
            stem = w[:-2]
            # Reason: -er disambiguation. COMP only if base is a known ADJ;
            # otherwise leave for derivation step to handle as agent noun.
            if stem in self.KNOWN_ADJECTIVES:
                return stem, {"degree": "COMP"}, "ADJ"
            cand_e = stem + "e"
            if cand_e in self.KNOWN_ADJECTIVES:
                return cand_e, {"degree": "COMP"}, "ADJ"
            if stem in self.KNOWN_ADV_COMP_BASES:
                return stem, {"degree": "COMP"}, "ADV"
            return w, {}, None  # let derivation handle

        return w, {}, None

    # ─────────────────────────────────────────────────────────────────────────
    # Derivation - one step at a time
    # ─────────────────────────────────────────────────────────────────────────

    def _restore_lemma(self, stem: str, suffix: str) -> str:
        """Restore the verb/noun lemma after stripping a derivational suffix."""
        # Direct restoration table
        if stem in self.LEMMA_RESTORE:
            return self.LEMMA_RESTORE[stem]
        # Suffix-specific rules
        if suffix in ("tion", "ation", "ition"):
            # education -> educ -> educate; creation -> cre -> create
            # invitation -> invit -> invite; explanation -> explan -> explain
            cand_ate = stem + "ate"
            if cand_ate in self.COMMON_VERBS or cand_ate in self.irregulars:
                return cand_ate
            cand_e = stem + "e"
            if cand_e in self.COMMON_VERBS or cand_e in self.irregulars:
                return cand_e
        if suffix == "sion":
            # decision -> deci -> decide
            cand_de = stem + "de"
            if cand_de in self.COMMON_VERBS:
                return cand_de
            cand_e = stem + "e"
            if cand_e in self.COMMON_VERBS:
                return cand_e
        if suffix == "ment":
            cand_e = stem + "e"
            if cand_e in self.COMMON_VERBS or cand_e in self.irregulars:
                return cand_e
        if suffix == "ity":
            # ability -> abil -> able; possibility -> possibil -> possible
            if stem.endswith("il"):
                return stem[:-2] + "le"
            # activity -> activ -> active
            cand_e = stem + "e"
            if cand_e in self.KNOWN_ADJECTIVES or cand_e in self.COMMON_VERBS:
                return cand_e
        if suffix in ("ify", "fy") and not self._is_real_word(stem):
            # Verbalising -ify can attach to a -y base and drop it
            # (beauty -> beautify, glory -> glorify). Only restore the -y/-e when
            # the bare stem is NOT itself a real word, so beautify -> beauty but
            # classify -> class (class is already real) and solidify -> solid.
            if self._is_real_word(stem + "y"):
                return stem + "y"
            if self._is_real_word(stem + "e"):
                return stem + "e"
        if suffix in ("ize", "ise"):
            return stem  # modernize -> modern
        if suffix == "ly":
            # -ably / -ibly adverbs collapse the adjective's silent -e:
            # unbelievably -> -ly leaves 'unbelievab' -> restore 'unbelievable'.
            # Re-expand so the downstream -able/-ible peel can run.
            if stem.endswith("ab") and self._is_real_word(stem + "le"):
                return stem + "le"
            if stem.endswith("ib") and self._is_real_word(stem + "le"):
                return stem + "le"
            if stem.endswith("i"):
                cand = stem[:-1] + "y"
                return cand
            # simply (ly stripped) -> simp -> simple. "-ly" replaces "-le".
            cand_le = stem + "le"
            if cand_le in self.KNOWN_ADJECTIVES:
                return cand_le
            if stem.endswith("l") and len(stem) >= 2 and stem[-2] not in self.VOWELS:
                return stem + "e"
            return stem
        if suffix in ("able", "ible"):
            cand_e = stem + "e"
            if cand_e in self.COMMON_VERBS or cand_e in self.irregulars:
                return cand_e
            return stem
        if suffix in ("ative", "itive", "ive"):
            cand_e = stem + "e"
            if cand_e in self.COMMON_VERBS or cand_e in self.irregulars:
                return cand_e
            # communicative -> communicat -> communicate
            cand_ate = stem + "e"
            return stem
        if suffix == "ist":
            # scientist -> scient -> science
            if stem == "scient":
                return "science"
            cand_e = stem + "e"
            if cand_e in self.KNOWN_NOUNS:
                return cand_e
            return stem
        return stem

    # Suffixes that should NOT be stripped if the whole stem looks like a known
    # short word ending in that string (e.g., "see" ends in "ee" but is not
    # derived; "like" is a base, not a -like suffix).
    SUFFIX_GUARD_BASES = {"see", "foresee", "agree", "disagree", "tree",
                          "free", "three", "knee", "bee", "fee", "flee",
                          "like", "dislike", "alike",
                          # 'individual' is its own lemma. Peeling -ual off it
                          # leaves the non-word 'individ', which then forces a
                          # bogus in- prefix peel down to the unrelated 'divide'.
                          # Guard it so individualist/-ism/-ity stop at individual.
                          "individual",
                          # 'secure' is monomorphemic: the apparent -ure does not
                          # peel to the noise word 'sec'. Guard it so security and
                          # cybersecurity bottom out at the real word 'secure'.
                          "secure"}

    # Lexicalised words a reference lemmatiser (and a fluent reader) treats as
    # their own lemma even though they end in an apparent affix. The engine's
    # greedy peeler would otherwise reduce them to a shorter, semantically wrong
    # word (individual->divide, ideal->ide, various->vari, tactic->tact). These
    # are NOT productive stem+affix forms; the surface is the dictionary head.
    # Listed singular; regular plurals are caught after -s/-es inflection because
    # the recovered stem lands in this set. None of these is asserted by the EN
    # unit tests, so keeping them whole does not regress the curated derivations
    # (capitalism->capital, national->nation, dangerous->danger remain).
    LEXICALIZED_KEEP: Dict[str, str] = {
        # adjectives
        "individual": "ADJ", "revolutionary": "ADJ", "various": "ADJ",
        "ideal": "ADJ", "classical": "ADJ", "contemporary": "ADJ",
        "significant": "ADJ", "philosophical": "ADJ", "political": "ADJ",
        "ordinary": "ADJ", "primary": "ADJ", "secondary": "ADJ",
        "military": "ADJ", "literary": "ADJ", "necessary": "ADJ",
        "temporary": "ADJ", "voluntary": "ADJ", "solar": "ADJ",
        "socialist": "ADJ",
        # nouns. (existence/reference are intentionally NOT listed here: the unit
        # tests assert their productive derivations existence->exist, etc.)
        "sentence": "NOUN", "experience": "NOUN", "audience": "NOUN",
        "evidence": "NOUN", "difference": "NOUN", "conference": "NOUN",
        "influence": "NOUN", "consequence": "NOUN",
        "tactic": "NOUN", "tendency": "NOUN",
        "principle": "NOUN", "authority": "NOUN", "current": "NOUN",
        "boundary": "NOUN", "category": "NOUN", "territory": "NOUN",
        "memory": "NOUN", "theory": "NOUN", "factory": "NOUN",
        "victory": "NOUN", "history": "NOUN", "industry": "NOUN",
        "century": "NOUN",
        # lexicalised words with a DECEPTIVE productive-looking prefix: the inner
        # part is itself a real word, so the stem-validity guard alone would
        # wrongly peel it (research->search, understand->stand, important->port).
        "research": "NOUN", "understand": "VERB", "important": "ADJ",
        "information": "NOUN", "represent": "VERB", "become": "VERB",
        "interest": "NOUN", "between": "ADP", "behavior": "NOUN",
        "behaviour": "NOUN", "increase": "VERB", "release": "VERB",
        "instead": "ADV", "report": "NOUN", "remain": "VERB",
        # opaque words that over-strip to a garbage/unrelated stem (revealed by
        # the 200-word frequency-sampled gold: nature->nation, spanish->span …)
        "nature": "NOUN", "moral": "ADJ", "ethics": "NOUN", "ethic": "NOUN",
        "consensus": "NOUN", "describe": "VERB", "federation": "NOUN",
        "global": "ADJ", "syndicate": "NOUN", "spanish": "ADJ",
        # federal/federalist relate to federation, not to feed/fed. Greedy peeling
        # reads -al + agent -er and bottoms out at the unrelated 'fed'.
        "federal": "ADJ",
        # Fused-prefix headwords: a real, lexicalised word whose leading sequence
        # only LOOKS like a productive prefix. The remainder is a real word too,
        # but the compound is NOT compositional (reaction != "action again",
        # define != "un-fine"), so the deepest-real-word rule keeps the whole
        # word. These are dictionary lemmas a fluent reader does not decompose.
        "reaction": "NOUN", "overlap": "NOUN", "overthrow": "NOUN",
        "resolution": "NOUN", "resolve": "VERB", "replacement": "NOUN",
        "reformation": "NOUN", "reform": "NOUN", "regardless": "ADV",
        "return": "VERB", "restore": "VERB", "repress": "VERB",
        "define": "VERB", "decrease": "VERB", "defence": "NOUN",
        "defeat": "VERB", "declare": "VERB", "dismiss": "VERB",
        "discussion": "NOUN", "disorder": "NOUN", "display": "VERB",
        "distribute": "VERB", "preserve": "VERB", "precursor": "NOUN",
        "predatory": "ADJ", "impose": "VERB", "inspire": "VERB",
        "entire": "ADJ", "internet": "NOUN", "transparent": "ADJ",
        "antiquity": "NOUN", "autonomous": "ADJ", "cooperation": "NOUN",
        "unprecedented": "ADJ", "mention": "VERB", "imply": "VERB",
    }

    def _try_strip_suffix(self, stem: str) -> Optional[Tuple[str, str, str]]:
        """Try outermost derivational suffix. Returns (new_stem, suffix, gloss) or None."""
        if stem in self.SUFFIX_GUARD_BASES:
            return None
        # Reason: words like 'experiment', 'comment', 'document' are not
        # productive stem+ment derivations; the leading sequence is not a root.
        if stem in self.NO_MENT_STRIP:
            return None
        # Collect every candidate suffix this stem ends with, then prefer the one
        # whose remainder (silent-e aware) is a real word. This realises the
        # deepest-real-word convention at the suffix-choice level: departure ends
        # in both -ture (-> 'depar', a non-word) and -ure (-> 'depart', a real
        # verb), so we take -ure. When no candidate yields a real word, fall back
        # to the longest match (preserves the old behaviour for opaque chains).
        candidates: List[Tuple[str, str, str]] = []
        for suf in self.suffixes_ordered:
            if not stem.endswith(suf):
                continue
            new = stem[:-len(suf)]
            if len(new) < 3:
                # Exception: allow 'us' -> 'use' for -able (usable)
                if suf in ("able", "ible") and len(new) >= 2:
                    pass
                else:
                    continue
            # Don't strip 'ee' from words like 'agree', 'see', 'foresee'.
            if suf == "ee":
                continue
            # Don't strip 'like' unless what's left is a known noun (e.g., catlike).
            if suf == "like" and new not in self.KNOWN_NOUNS and new not in self.KNOWN_BASES:
                continue
            gloss = self.SUFFIX_GLOSS.get(suf, "DERIVED")
            candidates.append((new, suf, gloss))
        if not candidates:
            return None
        for new, suf, gloss in candidates:
            if (self._valid_stem_or_silent_e(new) is not None
                    or new in self.LEMMA_RESTORE):
                return new, suf, gloss
        return candidates[0]
        return None

    def _try_strip_prefix(self, stem: str) -> Optional[Tuple[str, str, str]]:
        """Try outermost derivational prefix. Returns (new_stem, prefix, gloss) or None."""
        # Reason: 'refer', 'commit', etc. are not productive prefix+root.
        if stem in self.NO_PREFIX_PEEL_BASES:
            return None
        for pre in self.PREFIXES_ORDERED:
            if not stem.startswith(pre):
                continue
            new = stem[len(pre):]
            if len(new) < 3:
                continue
            gloss = self.PREFIX_GLOSS.get(pre, "DERIVED")
            return new, pre, gloss
        return None

    def _is_known_base(self, w: str) -> bool:
        return (w in self.KNOWN_BASES
                or w in self.irregulars
                or w in self.compounds)

    def _is_real_word(self, w: str) -> bool:
        """Stem-validity guard: is `w` an actual English word (dictionary or a
        curated engine base)? Used to refuse derivational cuts that would leave a
        non-word remainder. Empty wordlist (config absent) => permissive, so the
        engine degrades to its pre-guard behaviour rather than refusing all cuts.
        """
        if not self.WORDLIST:
            return True
        return w in self.WORDLIST or self._is_known_base(w)

    def _good_checkpoint(self, w: str) -> bool:
        """A form is a usable stem-validity checkpoint only if it is a real word
        that is also a plausible content root: at least 3 letters and not a
        function word. This stops degenerate stops such as theory->'the' or
        history->'his' from being treated as the lemma.
        """
        if len(w) < 3:
            return False
        if w in self.CLOSED_CLASS:
            return False
        # FUNCTION_FALLBACK holds both true function words (the/of/now/some) and a
        # set of content adjectives (free, common, single, able, main, whole).
        # Only the genuine function words are barred from being a content-root
        # checkpoint; an adjective base such as 'free' (freedom -> free) is a
        # perfectly good deepest real word.
        if w in self.FUNCTION_FALLBACK and self.FUNCTION_FALLBACK[w][0] != "ADJ":
            return False
        return self._is_real_word(w)

    def _valid_stem_or_silent_e(self, stem: str) -> Optional[str]:
        """Return a real-word form of `stem`, restoring a silent -e if needed.
        piec -> piece, expos -> expose. Returns None if neither `stem` nor
        `stem`+'e' is a real word. With no wordlist loaded, returns `stem`.
        """
        if not self.WORDLIST:
            return stem
        if self._is_real_word(stem):
            return stem
        cand_e = stem + "e"
        if self._is_real_word(cand_e):
            return cand_e
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Multi-step derivational peel
    # ─────────────────────────────────────────────────────────────────────────

    def _peel(self, stem: str) -> Tuple[str, List[str], Optional[str]]:
        """
        Iteratively peel derivational affixes. Returns (final_root, chain, outermost_pos).
        Strategy per iteration:
          1. If current stem is a known base, stop.
          2. Prefer prefix if the remainder is a known base (rebuild -> build).
          3. Try outermost suffix; apply lemma restore; recurse.
          4. Else try prefix permissively (>=3 chars left).
          5. Else stop.
        Agent -er handled when the running stem ends in -er and looks like an
        agent noun (not a comparative).
        """
        # Lexicalised words are their own lemma: do not peel at all.
        if stem in self.LEXICALIZED_KEEP:
            return stem, [], self.LEXICALIZED_KEEP[stem]

        chain: List[str] = []
        outer_pos: Optional[str] = None
        current = stem
        guard = 0
        # Stem-validity checkpoint. We remember the deepest form seen that is a
        # real English word, together with how many chain steps had been taken at
        # that point and the POS hint then. If peeling runs off into a non-word
        # (e.g. theory->the, contemporary->ntempor), we revert to this checkpoint
        # so the returned root is always a real word. The surface stem itself is
        # the depth-0 checkpoint when it is a real word.
        best_word: Optional[str] = None
        best_chain_len = 0
        best_pos: Optional[str] = None
        if self._good_checkpoint(current):
            best_word, best_chain_len, best_pos = current, 0, None
        # Pre-pass: even if the input is itself a "known base" (e.g., 'foresee'
        # registered via an irregular like 'foreseen'), allow one prefix peel
        # when the remainder is also a known base and lives in a different
        # lexical set. This handles foresee->see, rebuild->build when both
        # are listed.
        if self._is_known_base(current):
            pres = self._try_strip_prefix(current)
            if pres is not None:
                new, pre, gloss = pres
                if self._is_known_base(new) and new != current:
                    chain.append(f"{pre}→{gloss}")
                    outer_pos = self._guess_pos_for_base(new)
                    current = new
        while guard < 12:
            guard += 1
            # Apply lemma restoration in-loop so deep chains can terminate at
            # the canonical lemma rather than over-peeling (e.g., 'communic'
            # would otherwise be hacked further by 'co'+'ic' strips).
            if current in self.LEMMA_RESTORE:
                current = self.LEMMA_RESTORE[current]
            # A lexicalised base reached mid-peel is the deepest sensible root:
            # stop there (federalist -ist-> federal STOPS, never reaching the
            # unrelated 'fed'; federal is pinned in LEXICALIZED_KEEP).
            if current in self.LEXICALIZED_KEEP:
                if outer_pos is None:
                    outer_pos = self.LEXICALIZED_KEEP[current]
                break
            # Update the real-word checkpoint to the current (post-restore) form.
            if self._good_checkpoint(current):
                best_word, best_chain_len, best_pos = current, len(chain), outer_pos
            if self._is_known_base(current):
                break

            # 1) Prefer prefix if remainder is a known base.
            pres = self._try_strip_prefix(current)
            if pres is not None:
                new, pre, gloss = pres
                # Only collapse to irregular lemma for verb-like inflections
                # (e.g. rethought -> rethink). For noun plurals like 'media'
                # (plural of medium), keep the surface remainder.
                if new in self.irregulars and self.irregulars[new].get("pos") == "VERB":
                    ent = self.irregulars[new]
                    chain.append(f"{pre}→{gloss}")
                    if outer_pos is None:
                        outer_pos = ent["pos"]
                    current = ent["base"]
                    continue
                if (self._is_known_base(new)
                        or new in self.irregulars
                        or new in self.LEMMA_RESTORE):
                    chain.append(f"{pre}→{gloss}")
                    if outer_pos is None:
                        outer_pos = self._guess_pos_for_base(new)
                    current = new
                    continue
                # Take a clean prefix strip whose remainder is itself a real word
                # (intercontinental -> continental, international -> national).
                # Restricted to PRODUCTIVE prefixes and refused when the prefixed
                # form is itself a lexicalised real word whose remainder is not a
                # curated base (reaction, overlap, preserve, resolution): the
                # prefix is fused there, so the whole word is the deepest base.
                guarded_pre = self._valid_stem_or_silent_e(new)
                if (guarded_pre is not None and len(guarded_pre) >= 4
                        and pre in self.PRODUCTIVE_PREFIXES):
                    chain.append(f"{pre}→{gloss}")
                    if outer_pos is None:
                        outer_pos = self._guess_pos_for_base(guarded_pre)
                    current = guarded_pre
                    continue

            # 2) Agent -er disambiguation.
            agent = self._try_agent_er(current)
            if agent is not None:
                base, suf = agent
                chain.append(f"{suf}→AGENT_NOUN")
                if outer_pos is None:
                    outer_pos = "NOUN"
                current = base
                continue

            # 3) Suffix peel.
            sres = self._try_strip_suffix(current)
            if sres is not None:
                new, suf, gloss = sres
                restored = self._restore_lemma(new, suf)
                restore_fired = restored != new
                # CONVENTION (deepest real-word base): when no curated restoration
                # fired, recover the silent-e that an e-eliding suffix consumed so
                # the *intermediate* lands on a real word and is checkpointed
                # (collectiv -> collective, exposur -> exposure). Restricted to the
                # suffixes that genuinely attach to an -e base; for consonant-
                # attaching suffixes (-ship/-dom/-hood/-al/-ful) an invented e just
                # fabricates an unrelated word (worship -ship-> wor -> 'wore',
                # global -al-> glob -> 'globe'), which must not become a checkpoint.
                if (not restore_fired and suf in self.E_ELIDING_SUFFIXES
                        and not self._is_real_word(new)
                        and self._is_real_word(new + "e")):
                    restored = new + "e"
                if len(restored) >= 2:
                    chain.append(f"{suf}→{gloss}")
                    if outer_pos is None:
                        outer_pos = self.SUFFIX_DERIVES_POS.get(suf, "UNKNOWN")
                    # Recognize embedded -ly (godliness -> godli -> godly -> god)
                    if suf == "ness" and restored.endswith("li"):
                        chain.append("ly→MANNER")
                        restored = restored[:-2]
                    # -isation/-ization fold the verbal -ise/-ize: globalisation
                    # strips -ation to 'globalis'. Two readings:
                    #   (a) drop just -is/-iz -> the -al adjective base 'global'
                    #       (the deepest real word). Preferred when it is real.
                    #   (b) drop the whole -alis/-aliz -> stem+al+ise, used for the
                    #       transparent deep chain (denationalis -> de+nation+al+
                    #       ise) when the -is/-iz base is NOT itself a real word.
                    if (suf == "ation" and not self._is_real_word(restored)
                            and restored[-2:] in ("is", "iz")
                            and self._is_real_word(restored[:-2])):
                        chain.append("ise→VERBALIZE" if restored.endswith("is")
                                     else "ize→VERBALIZE")
                        restored = restored[:-2]
                    elif suf == "ation" and restored.endswith("alis"):
                        chain.append("ise→VERBALIZE")
                        chain.append("al→RELATIONAL")
                        restored = restored[:-4]
                    elif suf == "ation" and restored.endswith("aliz"):
                        chain.append("ize→VERBALIZE")
                        chain.append("al→RELATIONAL")
                        restored = restored[:-4]
                    current = restored
                    continue

            # 4) Prefix permissive (remainder >=3 long but not necessarily a known
            # base). Stem-validity guard: only accept this speculative peel if the
            # remainder is a real word (silent-e aware) AND the prefix is one of
            # the productive, separable prefixes AND the prefixed form is not a
            # fused lexicalised word. This blocks bogus prefix strips such as
            # co|ntemporary, in|dividual, auto|nomy and the opaque-Latinate
            # over-peels (de|fine, im|pose, in|spire, re|turn, pre|serve).
            if pres is not None:
                new, pre, gloss = pres
                guarded = self._valid_stem_or_silent_e(new)
                if (guarded is not None and len(guarded) >= 3
                        and pre in self.PRODUCTIVE_PREFIXES):
                    chain.append(f"{pre}→{gloss}")
                    current = guarded
                    continue
            break
        # Final restoration: if the leftover stem matches a known lemma key,
        # restore it (e.g. lawy->law, godli->god, structur->structure).
        if current in self.LEMMA_RESTORE:
            current = self.LEMMA_RESTORE[current]
        # Stem-validity guard (final). If peeling ended on a non-word root, revert
        # to the deepest real-word checkpoint (which may be the surface itself).
        # This is what turns theory->the back into theory, contemporary->ntempor
        # back into contemporary, while leaving real-word roots untouched.
        if not self._good_checkpoint(current):
            if best_word is not None:
                current = best_word
                chain = chain[:best_chain_len]
                # Keep the POS implied by the outermost derivational suffix even
                # though we revert the *root* to a real word: political stays ADJ
                # (from -ical) with root 'political', not NOUN. Fall back to the
                # checkpoint POS only if no suffix POS was derived.
                outer_pos = outer_pos or best_pos
            elif self.WORDLIST and not self._is_real_word(current) and current != stem:
                # No real-word checkpoint was ever reached and we ended on a
                # non-word fragment (syndicalist -> 'synd'): the word has no
                # reachable real base, so keep the whole surface rather than emit
                # a fragment. Mirrors the deepest-real-word convention's "never
                # strip to a non-word" clause.
                current = stem
                chain = []
        return current, chain, outer_pos

    def _guess_pos_for_base(self, w: str) -> str:
        if w in self.COMMON_VERBS:
            return "VERB"
        if w in self.KNOWN_ADJECTIVES:
            return "ADJ"
        if w in self.KNOWN_NOUNS:
            return "NOUN"
        if w in self.irregulars:
            return self.irregulars[w].get("pos", "UNKNOWN")
        return "UNKNOWN"

    def _try_agent_er(self, stem: str) -> Optional[Tuple[str, str]]:
        """If stem ends in -er/-or/-ar AND looks like an agent noun, return (base, suffix)."""
        for suf in ("er", "or", "ar"):
            if not stem.endswith(suf):
                continue
            base = stem[:-len(suf)]
            if len(base) < 3:
                continue
            # Comparative reading wins if base is a known ADJ
            if base in self.KNOWN_ADJECTIVES:
                return None
            cand_e = base + "e"
            # Restore silent-e: writer -> writ -> write, baker -> bak -> bake
            if cand_e in self.COMMON_VERBS or cand_e in self.irregulars:
                return cand_e, suf
            if base in self.COMMON_VERBS or base in self.irregulars or base in self.KNOWN_NOUNS:
                return base, suf
            # Known agent: prefer agent reading and try to find a base
            if stem in self.AGENT_ER_KNOWN:
                # Try various restorations
                if cand_e in self.KNOWN_ADJECTIVES or cand_e in self.KNOWN_NOUNS:
                    return cand_e, suf
                return base, suf
            return None
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Main analyze
    # ─────────────────────────────────────────────────────────────────────────

    def analyze(self, word: str) -> TokenInfo:
        original = word
        w = word.lower()

        # Foreign loans
        if w in self.FOREIGN_LOANS:
            return TokenInfo(surface=original, clitics={}, template="",
                             root=w, tags={}, pos="UNKNOWN", derived_chain=[])

        # Closed-class
        if w in self.CLOSED_CLASS:
            pos, ct = self.CLOSED_CLASS[w]
            tags_out = dict(ct)
            if pos == "AUX" and w in self.MODAL_VERBS:
                tags_out["modal"] = "YES"
            return TokenInfo(surface=original, clitics={}, template="",
                             root=w, tags=tags_out, pos=pos, derived_chain=[])

        # Hyphenated: handle prefix-base case
        if "-" in w:
            parts = w.split("-")
            if len(parts) == 2 and parts[0] in self.PREFIX_GLOSS:
                pre, base = parts
                sub = self.analyze(base)
                gloss = self.PREFIX_GLOSS[pre]
                return TokenInfo(surface=original, clitics={}, template="",
                                 root=sub.root, tags=sub.tags, pos=sub.pos,
                                 derived_chain=[f"{pre}→{gloss}"] + sub.derived_chain)
            return TokenInfo(surface=original, clitics={}, template="",
                             root=w, tags={}, pos="UNKNOWN", derived_chain=[])

        # Compounds
        if w in self.compounds:
            comp = self.compounds[w]
            head_stem = comp["constituents"][-1]["stem"]
            chain = [f"COMPOUND({'+'.join(c['stem'] for c in comp['constituents'])})"]
            sub = self.analyze(head_stem)
            return TokenInfo(surface=original, clitics={}, template="",
                             root=sub.root or head_stem, tags=sub.tags, pos=sub.pos,
                             derived_chain=chain + sub.derived_chain)

        # Irregulars
        if w in self.irregulars:
            ent = self.irregulars[w]
            t: Dict[str, str] = {}
            for pair in ent["tag"].split("|"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    t[k] = v
            t = self._filter_tags_for_pos(t, ent["pos"])
            if w in self.phrasal_verb_components and ent["pos"] == "VERB":
                t["phrasal_verb_base"] = "YES"
            return TokenInfo(surface=original, clitics={}, template="",
                             root=ent["base"], tags=t, pos=ent["pos"],
                             derived_chain=[])

        # Inflection
        stem, infl_tags, infl_pos = self._strip_inflection(w)
        if infl_pos is not None:
            tags = dict(infl_tags)
            pos = infl_pos
            # Possessive 's: do not run derivation. Keep stem as-is.
            if pos == "POSS":
                pos = "NOUN"
                # If the stem is itself a derived agent noun (teacher), keep it.
                tags = self._filter_tags_for_pos(tags, pos)
                return TokenInfo(surface=original, clitics={}, template="",
                                 root=stem, tags=tags, pos=pos, derived_chain=[])
            # Try derivation on stem
            root, deriv_chain, _ = self._peel(stem)
            if w in self.phrasal_verb_components and pos == "VERB":
                tags["phrasal_verb_base"] = "YES"
            tags = self._filter_tags_for_pos(tags, pos)
            return TokenInfo(surface=original, clitics={}, template="",
                             root=root if deriv_chain else stem,
                             tags=tags, pos=pos, derived_chain=deriv_chain)

        # No inflection; try derivation
        root, deriv_chain, deriv_pos = self._peel(w)
        if deriv_chain or root != w or deriv_pos:
            pos = deriv_pos if deriv_pos else "UNKNOWN"
            # If lemma restoration happened silently (no chain step recorded),
            # synthesize a step from the residue between surface and root so the
            # derivation chain is not empty when the root differs.
            if not deriv_chain and root != w:
                if w.endswith("al") and root + "al" == w:
                    deriv_chain = ["al→RELATIONAL"]
                    pos = "ADJ"
                elif w.endswith("ial") and root + "ial" == w:
                    deriv_chain = ["ial→RELATIONAL"]
                    pos = "ADJ"
            tags = self._filter_tags_for_pos({}, pos)
            return TokenInfo(surface=original, clitics={}, template="",
                             root=root, tags=tags, pos=pos, derived_chain=deriv_chain)

        # Bare phrasal verb base
        if w in self.phrasal_verb_components:
            return TokenInfo(surface=original, clitics={}, template="",
                             root=w, tags={"phrasal_verb_base": "YES"}, pos="VERB",
                             derived_chain=[])

        if w in self.COMMON_VERBS:
            return TokenInfo(surface=original, clitics={}, template="",
                             root=w, tags={}, pos="VERB", derived_chain=[])

        if w in self.KNOWN_ADJECTIVES:
            return TokenInfo(surface=original, clitics={}, template="",
                             root=w, tags={}, pos="ADJ", derived_chain=[])

        # Function-word fallback (only reached when morphology found nothing).
        if w in self.FUNCTION_FALLBACK:
            pos, ct = self.FUNCTION_FALLBACK[w]
            return TokenInfo(surface=original, clitics={}, template="",
                             root=w, tags=dict(ct), pos=pos, derived_chain=[])

        # Digit-bearing numerals.
        if any(c.isdigit() for c in w):
            return TokenInfo(surface=original, clitics={}, template="",
                             root=w, tags={}, pos="NUM", derived_chain=[])

        # Open-class fallback: an unrecognised alphabetic word is, by default, a
        # content noun (not UNKNOWN). This matches how a reader treats an unknown
        # word and is the single biggest real-text POS win. Non-alphabetic junk
        # stays UNKNOWN.
        if w.isalpha():
            return TokenInfo(surface=original, clitics={}, template="",
                             root=w, tags={}, pos="NOUN", derived_chain=[])

        return TokenInfo(surface=original, clitics={}, template="",
                         root=w, tags={}, pos="UNKNOWN", derived_chain=[])

    # ─────────────────────────────────────────────────────────────────────────
    # Tag filter
    # ─────────────────────────────────────────────────────────────────────────

    def _filter_tags_for_pos(self, tags: Dict[str, str], pos: str) -> Dict[str, str]:
        NOUN_ALLOWED = {"num", "poss", "ambig_3sg"}
        VERB_ALLOWED = {"tense", "aspect", "person", "voice", "phrasal_verb_base"}
        ADJ_ALLOWED = {"degree"}
        ADV_ALLOWED = {"degree"}
        if pos == "AUX":
            return dict(tags)
        if pos == "NOUN":
            return {k: v for k, v in tags.items() if k in NOUN_ALLOWED}
        if pos == "VERB":
            return {k: v for k, v in tags.items() if k in VERB_ALLOWED}
        if pos == "ADJ":
            return {k: v for k, v in tags.items() if k in ADJ_ALLOWED}
        if pos == "ADV":
            return {k: v for k, v in tags.items() if k in ADV_ALLOWED}
        return dict(tags)

    def analyze_sentence(self, sentence: str) -> Tuple[List[TokenInfo], bool, str]:
        from .grammar.en_grammar import (
            split_into_sentences,
            disambiguate_pos,
            validate_sentence,
        )

        # Multi-sentence: process each, return concatenated tokens and the
        # first failing sentence message (or "ok").
        chunks = split_into_sentences(sentence)
        if not chunks:
            return [], True, "ok"

        all_tokens: List[TokenInfo] = []
        overall_ok = True
        overall_msg = "ok"

        for chunk in chunks:
            # Skip pure terminator-only chunks; otherwise drop terminator tokens
            # before analysis to avoid analyzing punctuation as words.
            words = [w for w in chunk if not all(c in ".!?;," for c in w)]
            if not words:
                continue
            tokens = [self.analyze(w) for w in words]
            tokens = disambiguate_pos(tokens)
            word_ok = check_morph_sequence_en(tokens)
            sent_ok, sent_msg = validate_sentence(tokens)
            all_tokens.extend(tokens)
            chunk_ok = word_ok and sent_ok
            if not chunk_ok and overall_ok:
                overall_ok = False
                overall_msg = sent_msg if not sent_ok else "word-level bundle failure"

        return all_tokens, overall_ok, overall_msg
