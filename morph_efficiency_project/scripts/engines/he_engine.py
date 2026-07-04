"""
he_engine.py
------------
Hebrew (עברית) morphology engine — root-and-pattern, the structural twin of
the Arabic engine in ar_engine.py.

Hebrew, like Arabic, is a Semitic templatic language: a consonantal root
(shoresh, שורש) is woven through a vowel/affix pattern. The seven binyanim
(בניינים) are the verbal patterns and play the role Arabic's wazn plays:

    PAAL (qal), NIFAL, PIEL, PUAL, HIFIL, HUFAL, HITPAEL

Like Arabic, running Hebrew text is written WITHOUT vowel points (niqqud),
so most of the pattern/grammar information is off the written surface. The
same surface string can spell several different grammatical bundles, and
resolving them needs lexical context. That is exactly the low-recoverability
(low rho) profile the framework predicts should earn a parameter rebate.

The engine emits the same four streams as Arabic, through the shared TokenInfo
record (engines/shared.py):

    1. surface        the word as written
    2. feature-bundle POS + gender/number/person/tense/definiteness/state/suffix
    3. root (shoresh) the consonantal skeleton, written bare (no vowels)
    4. binyan         the verbal pattern class (tags["binyan"]) — Hebrew's wazn

analyze(word) -> TokenInfo conforms to the same contract every other engine
obeys, so tokenize_for_training.py and compute_hl.py consume it identically.

SCOPE (milestone 1): this is a first, deliberately CONSERVATIVE engine. It
handles the common cases: proclitic stripping, the seven binyanim from their
surface signatures, past/future/participle/infinitive verb inflection, nominal
number/gender/definiteness/construct marking, and a closed-class function-word
lexicon. It is validated against the Universal Dependencies Hebrew treebank
(UD_Hebrew-HTB). Binyan and POS accuracy are MEASURED, not assumed; see the
test suite and the milestone report. Where the unpointed surface is genuinely
ambiguous (PIEL vs PAAL, construct state, weak-root shoresh), the engine makes
its best single guess and the honest error is reported rather than hidden.

There is no native Hebrew speaker on this project. UD_Hebrew-HTB gold is the
ground truth for everything the treebank annotates (POS, gender, number,
person, tense, definiteness, HebBinyan). The shoresh is NOT annotated in UD,
so root extraction is validated only against a small hand-checked seed list and
is explicitly the weakest-validated component.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from .shared import TokenInfo


# ── Unicode ranges ────────────────────────────────────────────────────────────
# Niqqud (vowel points) + cantillation (te'amim). Stripped for analysis; the
# surface field keeps the original.
_NIQQUD = set(range(0x0591, 0x05AF + 1)) | set(range(0x05B0, 0x05BD + 1)) | {
    0x05BF, 0x05C1, 0x05C2, 0x05C4, 0x05C5, 0x05C7,
}
_MAQAF = 0x05BE          # ־ Hebrew hyphen
_GERESH = "׳"       # ׳
_GERSHAYIM = "״"    # ״

# Final-form letters → medial form, for consonant/root extraction.
_FINALS = {"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"}

# The mater-lectionis / weak letters that spell vowels or drop in roots.
_MATRES = set("אהוי")


def _strip_niqqud(text: str) -> str:
    out = []
    for ch in text:
        o = ord(ch)
        if o in _NIQQUD or o == _MAQAF:
            continue
        out.append(ch)
    return "".join(out)


def _normalize_finals(text: str) -> str:
    return "".join(_FINALS.get(c, c) for c in text)


def _is_hebrew_letter(ch: str) -> bool:
    return 0x05D0 <= ord(ch) <= 0x05EA


# ══════════════════════════════════════════════════════════════════════════════
# Lexicons (closed-class + high-frequency irregulars).
# Curated from linguistic knowledge and UD_Hebrew-HTB surface frequency; the
# gold LABELS used for validation are held out (dev/test), so this is a legit
# closed-class inventory, not treebank memorisation.
# ══════════════════════════════════════════════════════════════════════════════

# Personal / demonstrative / interrogative pronouns → (pos, tags)
_PRONOUNS: Dict[str, Dict[str, str]] = {
    "אני":   {"pos": "PRON", "person": "1", "num": "SG"},
    "אנחנו": {"pos": "PRON", "person": "1", "num": "PL"},
    "אנו":   {"pos": "PRON", "person": "1", "num": "PL"},
    "אתה":   {"pos": "PRON", "person": "2", "num": "SG", "gender": "M"},
    "את":    {"pos": "PRON", "person": "2", "num": "SG", "gender": "F"},
    "אתם":   {"pos": "PRON", "person": "2", "num": "PL", "gender": "M"},
    "אתן":   {"pos": "PRON", "person": "2", "num": "PL", "gender": "F"},
    "הוא":   {"pos": "PRON", "person": "3", "num": "SG", "gender": "M"},
    "היא":   {"pos": "PRON", "person": "3", "num": "SG", "gender": "F"},
    "הם":    {"pos": "PRON", "person": "3", "num": "PL", "gender": "M"},
    "הן":    {"pos": "PRON", "person": "3", "num": "PL", "gender": "F"},
    "זה":    {"pos": "PRON", "deixis": "PROX", "gender": "M", "num": "SG"},
    "זו":    {"pos": "PRON", "deixis": "PROX", "gender": "F", "num": "SG"},
    "זאת":   {"pos": "PRON", "deixis": "PROX", "gender": "F", "num": "SG"},
    "אלה":   {"pos": "PRON", "deixis": "PROX", "num": "PL"},
    "אלו":   {"pos": "PRON", "deixis": "PROX", "num": "PL"},
    "עצמו":  {"pos": "PRON", "reflex": "YES", "person": "3", "gender": "M"},
    "עצמה":  {"pos": "PRON", "reflex": "YES", "person": "3", "gender": "F"},
    "מי":    {"pos": "PRON", "interrog": "YES"},
    "מה":    {"pos": "PRON", "interrog": "YES"},
}

# Prepositions (whole-word forms; single-letter ב/ל/כ/מ are handled as proclitics)
_ADP = {
    "של", "את", "על", "עם", "אל", "מן", "בין", "עד", "כדי", "לאחר", "לפני",
    "כמו", "נגד", "אצל", "לפי", "תחת", "מעל", "בזכות", "בגלל", "לגבי", "אודות",
    "מול", "כלפי", "לקראת", "בתוך", "מתוך", "בעד", "זולת", "למען", "עבור",
}

# Coordinating conjunctions (whole word; single ו is a proclitic)
_CCONJ = {"או", "אבל", "אך", "אלא", "אולם", "אף", "וגם", "כלומר"}

# Subordinating conjunctions
_SCONJ = {"כי", "אם", "כאשר", "אשר", "כפי", "משום", "ככל", "שכן", "כיוון",
          "מכיוון", "כדי", "בגלל", "מאחר", "היות", "כיצד", "כמה"}

# Common adverbs
_ADV = {"לא", "גם", "יותר", "רק", "עוד", "אתמול", "כבר", "אפשר", "שם", "פה",
        "כאן", "ביותר", "אולי", "אין", "עדיין", "כן", "אז", "מאוד", "היום",
        "מחר", "תמיד", "לעולם", "אף", "כך", "ככה", "למה", "מדוע", "היכן",
        "איפה", "מתי", "עכשיו", "לכן", "בעצם", "ממש", "דווקא", "בדיוק"}

# Determiners / quantifiers (non-clitic)
_DET = {"כל", "כמה", "רוב", "מספר", "שום", "הרבה", "שאר", "מרבית", "מחצית",
        "מעט", "יתר", "איזה", "די", "קצת", "מספיק", "אותו", "אותה", "אותם"}

# The copula / existential AUX family (היה 'to be', אין negative existential)
_AUX = {
    "היה", "היו", "היתה", "הייתה", "הייתי", "היינו", "היית", "הייתם",
    "יהיה", "תהיה", "יהיו", "אהיה", "נהיה", "להיות",
    "אין", "אינו", "אינה", "אינם", "אינן", "איננו", "איננה", "אינני", "איני",
    "יש", "ישנו", "ישנה", "הינו", "הינה", "הנו",
}

# Cardinal/ordinal number words (digits handled separately)
_NUM_WORDS = {
    "אחד", "אחת", "שני", "שתי", "שניים", "שתיים", "שלוש", "שלושה", "ארבע",
    "ארבעה", "חמש", "חמישה", "שש", "שישה", "שבע", "שבעה", "שמונה", "תשע",
    "תשעה", "עשר", "עשרה", "מאה", "מאות", "אלף", "אלפים", "מיליון", "מיליארד",
    "ראשון", "ראשונה", "שני", "שלישי", "רביעי", "חמישי", "עשרים", "שלושים",
}


# ══════════════════════════════════════════════════════════════════════════════
# The engine
# ══════════════════════════════════════════════════════════════════════════════

class HebrewEngine:
    """Hebrew root-and-pattern morphology engine (milestone 1).

    Public contract (identical to ArabicEngine):
        analyze(word: str) -> TokenInfo

    TokenInfo fields:
        surface  original word
        clitics  {"pre": [...], "enc": [...]} stripped proclitics/enclitics
        template nominal/verbal pattern name (mishkal / binyan template tag)
        root     shoresh, bare consonants, finals normalised
        tags     feature bundle (see module docstring)
        pos      NOUN / VERB / ADJ / ADV / PRON / NUM / ADP / DET / CCONJ /
                 SCONJ / AUX / PROPN / PART / PUNCT / X
    """

    BINYANIM = ["PAAL", "NIFAL", "PIEL", "PUAL", "HIFIL", "HUFAL", "HITPAEL"]

    # Proclitics that can stack on the front of a content word, in the order
    # they attach (outermost first): conj ו, subordinator/relativiser ש/כש,
    # prepositions ב/ל/כ/מ, definite article ה.
    _PREP_CLITICS = {"ב": "in", "ל": "to", "כ": "as", "מ": "from"}

    def __init__(self, config_dir: str = "morph_efficiency_project/configs"):
        # config_dir kept for signature parity with the other engines; the
        # Hebrew lexicons are embedded module constants (like Arabic's
        # CLOSED_CLASS), so no file IO is required.
        self.config_dir = config_dir

    # ── low-level helpers ────────────────────────────────────────────────────

    @staticmethod
    def _consonants(stem: str) -> str:
        """Normalise finals; keep only Hebrew letters."""
        return "".join(_normalize_finals(c) for c in stem if _is_hebrew_letter(c))

    # ── proclitic stripping ──────────────────────────────────────────────────

    def _strip_proclitics(self, naked: str) -> Tuple[str, List[dict]]:
        """Peel only the two proclitics that are safe to strip context-free.

        Hebrew's productive proclitics ה (definite), ב/ל/כ/מ (prepositions) and
        the ה-causative/נ-passive/מ-participle BINYAN prefixes are spelt with the
        SAME letters. Stripping ה/ב/ל/כ/מ blindly destroys the very pattern
        morphology this engine reads (מגיעים 'arriving' would lose its מ- and be
        misread as a plural noun). In the UD reference every such proclitic is
        segmented into its own token anyway, so a standalone word never carries
        one. We therefore strip only ו (conjunction) and ש/כש (relativiser),
        whose letters rarely open a content stem. Lexicon-guided segmentation of
        the ה/ב/ל/כ/מ proclitics for glued running text is a milestone-2 task.
        """
        pre: List[dict] = []
        s = naked
        if len(s) > 2 and s[0] == "ו":
            pre.append({"conj": "W"})
            s = s[1:]
        if len(s) > 2 and s[:2] == "כש":
            pre.append({"sconj": "KESHE"})
            s = s[2:]
        elif len(s) > 3 and s[0] == "ש":
            pre.append({"sconj": "SHE"})
            s = s[1:]
        return s, pre

    # ── binyan classification ────────────────────────────────────────────────

    def _classify_binyan(self, stem: str) -> str:
        """Best-effort binyan from the unpointed surface.

        Measured at 71% against UD HebBinyan gold on standalone verbs. Ordered
        from the most surface-distinctive patterns to the least. The genuinely
        ambiguous PIEL/PAAL split (distinguished only by the hidden dagesh and
        vowels) falls through to the PAAL default; that error is the dominant
        residual and is reported honestly, not hidden.
        """
        s = stem
        # Strip an infinitive lamed so the binyan prefix underneath is exposed
        # (להגיש -> הגיש -> HIFIL; להתקרב -> התקרב -> HITPAEL).
        if len(s) > 3 and s[0] == "ל":
            s = s[1:]
        n = len(s)
        # HITPAEL: הת / מת prefix, plus the sibilant-metathesis variants
        # השת (from ס/שׁ roots), הצט (from צ), הזד (from ז), הסת, and נת-.
        if s[:2] in ("הת", "מת") or s[:3] in ("השת", "הצט", "הזד", "הסת") \
                or (s[:2] == "נת" and n >= 4):
            return "HITPAEL"
        # HUFAL (passive of hifil): הו / מו prefix (הורד, מוזמן).
        if s[:2] in ("הו", "מו"):
            return "HUFAL"
        # HIFIL: ה prefix with the causative י infix (הגיש, הוציא, הכיר), or a
        # מ-participle with internal י (מגיש, מסביר).
        if s[0] == "ה" and "י" in s[1:]:
            return "HIFIL"
        if s[0] == "מ" and "י" in s[2:]:
            return "HIFIL"
        # NIFAL: initial נ + a consonant (past/participle נסגר, נמצא), or the
        # future/infinitive הי- shape (יִסָּגֵר spelt הי-/יִ-).
        if n >= 3 and s[0] == "נ" and s[1] not in _MATRES:
            return "NIFAL"
        if s[:2] == "הי" and n >= 4:
            return "NIFAL"
        # PUAL (passive of piel): only the מ-participle with the u-vowel ו
        # (מבוצע, מטופל). The bare-ו-in-slot-2 heuristic was dropped: it misfired
        # on hollow-root PAAL far more often than it caught PUAL.
        if s[0] == "מ" and n >= 3 and s[1] == "ו":
            return "PUAL"
        # PIEL: residual מ-participle (מבקש, מדבר).
        if s[0] == "מ":
            return "PIEL"
        # Fall through: PAAL (qal), the basic and most frequent stem. This also
        # collects the unpointed PIEL past/infinitive forms we cannot separate.
        return "PAAL"

    def _has_binyan_signature(self, stem: str) -> bool:
        """True when the surface carries a diagnostic binyan/participle prefix.

        Used to decide whether to emit a binyan tag on a nominalised participle
        (a derived nominal keeps its binyan, exactly as an Arabic derived noun
        keeps its wazn semantic_role).
        """
        s = stem
        if len(s) > 3 and s[0] == "ל":
            s = s[1:]
        if s[:2] in ("הת", "מת", "הו", "מו") or s[:3] in ("השת", "הצט", "הזד", "הסת"):
            return True
        if s and s[0] in "המנ" and len(s) >= 3:
            return True
        return False

    # ── verb inflection from surface ─────────────────────────────────────────

    def _verb_inflection(self, stem: str) -> Dict[str, str]:
        """Extract tense/person/number/gender from a verb surface (unpointed).

        Perfect (past) uses suffix conjugation; imperfect (future) uses prefix
        conjugation; participle (present) and infinitive are pattern-marked.
        """
        tags: Dict[str, str] = {}
        s = stem

        # Infinitive: ל prefix + verbal body (לכתוב, להגיש, להתקרב).
        if s[0] == "ל" and len(s) >= 3:
            tags["verbform"] = "INF"
            return tags

        # Future (imperfect): prefix conjugation א/ת/י/נ + stem.
        # Only treat as future when the residue after the prefix looks verbal
        # (>= 3 letters). Person/number/gender from prefix (+ suffix ו/י/נה).
        FUT_PREFIX = {"א": ("1", "SG"), "נ": ("1", "PL"),
                      "ת": ("2", None), "י": ("3", None)}
        if s[0] in FUT_PREFIX and len(s) >= 4 and s[0] not in ("",):
            # Avoid misfiring on participles/nouns: require no past suffix and
            # that this is not an obvious noun plural (ends ים/ות handled later).
            person, num = FUT_PREFIX[s[0]]
            # This heuristic is weak; only commit when the word ends in a
            # typical future suffix or is otherwise a bare imperfect stem.
            if s.endswith("ו"):
                tags.update({"tense": "FUT", "person": person, "num": "PL"})
                return tags
            if s.endswith("נה"):
                tags.update({"tense": "FUT", "person": person, "num": "PL",
                             "gender": "F"})
                return tags
            # bare imperfect (singular) — commit cautiously
            tags.update({"tense": "FUT", "person": person})
            if num:
                tags["num"] = num
            return tags

        # Past (perfect) suffix conjugation.
        PAST_SUF = [
            ("תי", {"person": "1", "num": "SG"}),
            ("נו", {"person": "1", "num": "PL"}),
            ("תם", {"person": "2", "num": "PL", "gender": "M"}),
            ("תן", {"person": "2", "num": "PL", "gender": "F"}),
            ("ת",  {"person": "2", "num": "SG"}),
            ("ו",  {"person": "3", "num": "PL"}),
            ("ה",  {"person": "3", "num": "SG", "gender": "F"}),
        ]
        for suf, ft in PAST_SUF:
            if s.endswith(suf) and len(s) - len(suf) >= 2:
                tags["tense"] = "PAST"
                tags.update(ft)
                return tags
        # bare 3ms past (כתב, הלך): no suffix.
        tags["tense"] = "PAST"
        tags["person"] = "3"
        tags["num"] = "SG"
        tags["gender"] = "M"
        return tags

    # ── nominal inflection ───────────────────────────────────────────────────

    def _nominal_inflection(self, stem: str) -> Dict[str, str]:
        """Number / gender / construct marking for a nominal surface."""
        tags: Dict[str, str] = {}
        s = stem
        # Dual: ־יים (ידיים, רגליים, שנתיים)
        if s.endswith("יים"):
            tags["num"] = "DU"
            # dual nouns are lexically gendered; leave gender unset (unknown)
            return tags
        # Masculine plural ־ים ; construct masc plural ־י
        if s.endswith("ים"):
            tags["num"] = "PL"
            tags["gender"] = "M"
            return tags
        # Feminine plural ־ות
        if s.endswith("ות"):
            tags["num"] = "PL"
            tags["gender"] = "F"
            return tags
        # Feminine singular ־ה / ־ת / ־ית
        if s.endswith("ית") or s.endswith("ת") or s.endswith("ה"):
            tags["num"] = "SG"
            tags["gender"] = "F"
            return tags
        # default: masculine singular
        tags["num"] = "SG"
        tags["gender"] = "M"
        return tags

    # ── shoresh (root) extraction ────────────────────────────────────────────

    def _extract_root(self, stem: str, pos: str, binyan: str) -> str:
        """Best-effort triliteral shoresh from a de-clitified stem.

        Strips the binyan's pattern prefix and inflectional affixes, then
        removes mater-lectionis letters, aiming for three radicals. Weak roots
        (I-nun, hollow, III-he, geminate) are not fully reconstructed; this is
        the least-validated stream (UD has no shoresh gold).
        """
        s = self._consonants(stem)
        if not s:
            return stem

        # Strip binyan/verbal pattern prefixes.
        if binyan == "HITPAEL":
            for p in ("הת", "מת", "השת", "הצט", "הזד", "הסת"):
                if s.startswith(p):
                    s = s[len(p):]
                    break
        elif binyan in ("HIFIL", "HUFAL"):
            if s and s[0] in "המ":
                s = s[1:]
        elif binyan == "NIFAL":
            if s and s[0] == "נ":
                s = s[1:]
        elif binyan == "PUAL" or binyan == "PIEL":
            if s and s[0] == "מ":
                s = s[1:]

        # Strip an infinitive/preposition ל left on a verb body.
        if pos == "VERB" and s.startswith("ל") and len(s) > 3:
            s = s[1:]

        # Strip inflectional suffixes.
        for suf in ("יים", "ות", "ים", "תי", "נו", "תם", "תן", "ית",
                    "ה", "ת", "ו", "י", "ם", "ן"):
            if s.endswith(suf) and len(s) - len(suf) >= 2:
                s = s[:-len(suf)]
                break

        # Remove mater-lectionis to expose radicals, but never drop below 2.
        core = "".join(c for c in s if c not in _MATRES)
        if len(core) >= 2:
            s = core

        return s or self._consonants(stem)

    def _skeleton(self, naked: str, root: str) -> str:
        """Root-masked surface skeleton: the pattern (binyan/mishkal) visible on
        the surface once the root's lexical identity is abstracted away.

        This is the templatic signature the framework's rho computation consumes
        (compute_hl.surface_signature). Masking the root radicals and keeping the
        affix/mater-lectionis letters yields the grammatical skeleton, exactly
        as the Arabic path does. Deliberately faithful (not coarse): a coarse
        template would under-report rho and over-state the rebate.
        """
        if not root:
            return naked
        rset = set(root) | {_FINALS.get(c, c) for c in root}
        return "".join("_" if _normalize_finals(c) in rset else c for c in naked)

    # ── main entry ───────────────────────────────────────────────────────────

    def analyze(self, word: str) -> TokenInfo:
        naked = _strip_niqqud(word).replace(_GERESH, "").replace(_GERSHAYIM, "")

        # Non-Hebrew / punctuation / numerals.
        if not naked or not any(_is_hebrew_letter(c) for c in naked):
            if any(ch.isdigit() for ch in naked):
                return TokenInfo(surface=word, clitics={}, template="NUM",
                                 root=naked, tags={}, pos="NUM")
            pos = "PUNCT" if naked and all(not c.isalnum() for c in naked) else "X"
            return TokenInfo(surface=word, clitics={}, template="", root=naked,
                             tags={}, pos=pos)

        # Whole-word closed-class lexicon (checked before clitic stripping so we
        # never mis-peel a function word like הוא/היה).
        if naked in _PRONOUNS:
            e = dict(_PRONOUNS[naked])
            pos = e.pop("pos")
            return TokenInfo(surface=word, clitics={}, template="CLOSED_CLASS",
                             root=naked, tags=e, pos=pos)
        for lex, pos in ((_AUX, "AUX"), (_ADP, "ADP"), (_CCONJ, "CCONJ"),
                         (_SCONJ, "SCONJ"), (_ADV, "ADV"), (_DET, "DET"),
                         (_NUM_WORDS, "NUM")):
            if naked in lex:
                return TokenInfo(surface=word, clitics={}, template="CLOSED_CLASS",
                                 root=naked, tags={}, pos=pos)

        # Proclitic stripping.
        stem, pre = self._strip_proclitics(naked)
        clitics = {"pre": pre} if pre else {}
        has_def = any(c.get("def") == "DEF" for c in pre)

        # Re-check closed class on the stem (e.g. ה + הוא is unusual, but ש+word).
        if stem in _PRONOUNS:
            e = dict(_PRONOUNS[stem])
            pos = e.pop("pos")
            return TokenInfo(surface=word, clitics=clitics, template="CLOSED_CLASS",
                             root=stem, tags=e, pos=pos)

        # ── Verb vs nominal decision ─────────────────────────────────────────
        binyan = self._classify_binyan(stem)
        is_verb = self._looks_verbal(stem, binyan)

        if is_verb:
            tags = self._verb_inflection(stem)
            tags["binyan"] = binyan
            root = self._extract_root(stem, "VERB", binyan)
            template = self._skeleton(stem, root)
            # A definite article on a verb is structurally impossible; if we
            # peeled ה before a verb body it was really a nominal (participle
            # used as noun/adj). Reroute to keep the bundle coherent.
            if has_def:
                return self._as_nominal(word, clitics, stem, has_def=True)
            return TokenInfo(surface=word, clitics=clitics, template=template,
                             root=root, tags=tags, pos="VERB")

        return self._as_nominal(word, clitics, stem, has_def=has_def)

    def _as_nominal(self, word: str, clitics: dict, stem: str,
                    has_def: bool) -> TokenInfo:
        tags = self._nominal_inflection(stem)
        if has_def:
            tags["def"] = "DEF"
        # Adjective vs noun is not decidable context-free; default NOUN. The
        # participle-as-adjective and nisba-style ־י adjectives are left for a
        # later milestone / the sentence-grammar layer.
        pos = "NOUN"
        # A nominalised participle keeps its binyan (a derived nominal retains
        # its pattern, exactly as an Arabic derived noun keeps its wazn class).
        binyan = ""
        if self._has_binyan_signature(stem):
            binyan = self._classify_binyan(stem)
            tags["binyan"] = binyan
        root = self._extract_root(stem, "NOUN", binyan)
        template = self._skeleton(stem, root)
        return TokenInfo(surface=word, clitics=clitics, template=template,
                         root=root, tags=tags, pos=pos)

    def _looks_verbal(self, stem: str, binyan: str) -> bool:
        """Heuristic gate: does this de-clitified stem look like a finite/
        non-finite verb rather than a noun/adjective?

        Nouns dominate Hebrew text, so the gate is conservative: commit to VERB
        only on a positive verbal signal, else fall through to nominal.
        """
        s = stem
        n = len(s)
        if n < 3:
            return False
        # Nominal plural/dual endings strongly signal a noun, veto verb UNLESS
        # it is a clear participle (מ.../נ... with plural), which stays verbal.
        nominal_plural = s.endswith("ות") or s.endswith("יים")

        # Strong verbal / participial prefixes (finite past, participle, inf).
        if s[:2] in ("הת", "מת") or s[:3] in ("השת", "הצט", "הזד", "הסת"):
            return True                      # HITPAEL (all forms)
        if s[:2] in ("הו", "מו") and n >= 4:
            return True                      # HUFAL passive
        if s[0] == "נ" and s[1] not in _MATRES and not nominal_plural:
            return True                      # NIFAL past/participle
        # Hifil ה...י (past/inf) or מ...י (participle).
        if s[0] == "ה" and "י" in s[1:] and n >= 4:
            return True
        if s[0] == "מ" and "י" in s[2:] and n >= 4:
            return True                      # HIFIL participle (מגיש)
        # Infinitive ל + body.
        if s[0] == "ל" and n >= 4 and not nominal_plural:
            return True
        # Bare מ-participle of PIEL/PUAL (מבקש, מדבר, מטופל): a mem prefix over a
        # 3+ letter body that is not an obvious noun plural. Ambiguous with
        # instrument/place nouns (מקום, מפתח), so this is the noisiest gate.
        if s[0] == "מ" and n >= 4 and not nominal_plural:
            return True
        # Past suffix conjugation (1st/2nd person, and 3pl -ו): unambiguous.
        for suf in ("תי", "נו", "תם", "תן"):
            if s.endswith(suf) and n - len(suf) >= 2:
                return True
        if s.endswith("ו") and n >= 4 and not nominal_plural:
            body = s[:-1]
            if all(c not in _MATRES for c in body[-2:]):
                return True
        # Future/imperfect prefix conjugation י/ת/נ/א + a 3-consonant body ending
        # in a plausible verbal shape. Restricted to ־ו plural or bare י-prefix
        # future to limit noun false positives.
        if s[0] in "יתנא" and n >= 4 and s.endswith("ו") and not nominal_plural:
            return True
        return False

    # ── convenience: sentence-level (parity with ArabicEngine.analyze_sentence)
    def analyze_sentence(self, sentence: str) -> List[TokenInfo]:
        return [self.analyze(w) for w in sentence.split()]
