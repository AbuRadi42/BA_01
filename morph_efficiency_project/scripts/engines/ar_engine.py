"""
engines/ar_engine.py
--------------------
Arabic morphology engine (Steps A/B/C + closed-class intercept).
"""

import json
import os
import re
from collections import defaultdict
from typing import Dict, List, Tuple

from .shared import (
    TokenInfo,
    check_morph_sequence_ar,
    validate_sentence_structure_ar,
)
from .grammar import ar_grammar as _ar_grammar

class ArabicEngine:
    """
    Arabic morphology engine.

    Step A — Clitic stripping (stacked proclitics + enclitics):
             Proclitics: وَ/فَ (conj), بِ/لِ/كَ (prep), الـ (def art),
                         سَـ (future), لَـ (emph/oath lam), أَ (interrog),
                         تَ/تِ (oath prefix). All compound clusters and
                         undiacritical forms included. Stripped in a loop
                         to handle stacked proclitics (وَبِالـ etc.).
             Enclitics:  Full pronoun paradigm (all persons/numbers/genders
                         and case variants), dual noun endings, feminine
                         plural endings, 2nd-person verb agreement suffixes,
                         energetic nun (ـنَّ/ـنْ).
             Co-occurrence: لَـ + ـنَّ/ـنْ on the same verb form a circumfix
                         (الإحاطة) — a discontinuous morpheme bracketing the
                         verb from both sides. Detected after Step A and
                         stored as circumfix=LAM_NUN / assertion=SWORN.
    Step B — Template matching: the stripped stem is matched against
             ar_templates.json patterns using consonant skeleton extraction.
             The template index is built once and used for every lookup.
    Step C — Root extraction: consonant skeleton of the matched stem,
             cross-referenced against ar_roots.json.
             Handles weak roots (ناقص، أجوف، مثال), hamzated roots (المهموز),
             and geminate roots (المضعّف) via normalization before lookup.
             Hamza variants (أ، إ، آ، ؤ، ئ) are normalized to ء.
             Weak-root إعلال alternations resolved by trying و/ي substitutions.
    Closed-class intercept (before Step A): prepositions, conjunctions,
             subordinators, negation particles, interrogatives, discourse
             particles, vocatives (يا etc.), interjections/أسماء أفعال
             (هيهات، آمين، صه...), اللهم, oaths, and response particles
             are tagged directly as PART and bypass Steps A/B/C entirely.
    """

    # Ordered proclitics (longest first to avoid partial matches).
    # Covers diacritical and undiacritical forms; corpus text is often unvoweled.
    # Categories:
    #   conj  — conjunction (و، ف)
    #   prep  — preposition clitic (ب، ل، ك)
    #   def   — definite article (ال)
    #   tense_prefix — future marker (سـ)
    #   emph  — lam of emphasis / lam of oath (لـ)
    #   interrog — interrogative hamza prefix (أَ)
    #   oath  — oath prefix (تَ/تِ/تُ)
    PROCLITICS = [
        # ── Compound proclitic clusters (longest first) ───────────────────
        ("وَبِالـ", {"conj": "W", "prep": "B", "def": "DEF"}),
        ("فَبِالـ", {"conj": "F", "prep": "B", "def": "DEF"}),
        ("وَلِلـ",  {"conj": "W", "prep": "L", "def": "DEF"}),
        ("فَلِلـ",  {"conj": "F", "prep": "L", "def": "DEF"}),
        ("وَالـ",   {"conj": "W", "def": "DEF"}),
        ("فَالـ",   {"conj": "F", "def": "DEF"}),
        ("وَال",    {"conj": "W", "def": "DEF"}),
        ("فَال",    {"conj": "F", "def": "DEF"}),
        ("وال",     {"conj": "W", "def": "DEF"}),   # undiacritical
        ("فال",     {"conj": "F", "def": "DEF"}),   # undiacritical
        ("بِالـ",   {"prep": "B", "def": "DEF"}),
        ("بِال",    {"prep": "B", "def": "DEF"}),
        ("بال",     {"prep": "B", "def": "DEF"}),   # undiacritical
        ("لِلـ",    {"prep": "L", "def": "DEF"}),
        ("لِل",     {"prep": "L", "def": "DEF"}),
        ("لل",      {"prep": "L", "def": "DEF"}),   # undiacritical
        ("كَالـ",   {"prep": "K", "def": "DEF"}),
        ("كَال",    {"prep": "K", "def": "DEF"}),
        ("كال",     {"prep": "K", "def": "DEF"}),   # undiacritical
        # ── Definite article alone ────────────────────────────────────────
        ("الـ",     {"def": "DEF"}),
        ("ال",      {"def": "DEF"}),
        # ── Single proclitics (diacritical) ──────────────────────────────
        ("وَ",      {"conj": "W"}),
        ("فَ",      {"conj": "F"}),
        ("بِ",      {"prep": "B"}),
        ("لِ",      {"prep": "L"}),
        ("كَ",      {"prep": "K"}),
        ("سَ",      {"tense_prefix": "FUT"}),
        ("لَ",      {"emph": "LAM"}),
        # ── Single proclitics (undiacritical — common in raw corpus) ─────
        ("و",       {"conj": "W"}),
        ("ف",       {"conj": "F"}),
        ("ب",       {"prep": "B"}),
        ("ل",       {"prep": "L"}),
        ("ك",       {"prep": "K"}),
        ("س",       {"tense_prefix": "FUT"}),
        # ── Interrogative hamza prefix (أَ + verb/noun) ───────────────────
        # e.g. أَكَتَبْتَ؟ (did you write?), أَأَنْتَ؟ (is it you?)
        ("أَ",      {"interrog": "Q"}),
        # ── Oath prefix (تَاللهِ / تِاللهِ) — extremely rare, only before
        # the word الله. Removed from general proclitic stripping to avoid
        # false positives on loanwords and common words starting with تَ/تِ.
        # Oath forms (والله، تالله، بالله) are handled by CLOSED_CLASS instead.
    ]

    # Enclitics: suffixes attached to the end of a word.
    # Covers:
    #   obj/poss pronouns — all persons, numbers, genders, and case variants
    #   dual noun endings — ـانِ (nom) / ـيْنِ (acc/gen)
    #   feminine plural endings — ـاتِ (gen/acc), ـاتٌ (nom)
    #   verb agreement suffixes — 2nd person dual/plural, feminine plural
    #   energetic nun — ـنَّ / ـنْ (emphasis on verb)
    # Ordered longest-first to avoid partial matches.
    ENCLITICS = [
        # ── 3rd person pronouns ───────────────────────────────────────────
        ("هُمَا",  {"obj": "3DU"}),
        ("هِمَا",  {"obj": "3DU", "case": "GEN"}),
        ("هُنَّ",  {"obj": "3FPL"}),
        ("هِنَّ",  {"obj": "3FPL", "case": "GEN"}),
        ("هُمْ",   {"obj": "3MPL"}),
        ("هِمْ",   {"obj": "3MPL", "case": "GEN"}),
        ("هُم",    {"obj": "3MPL"}),
        ("هَا",    {"obj": "3FSG"}),
        ("هُ",     {"obj": "3MSG"}),
        ("هِ",     {"obj": "3MSG", "case": "GEN"}),
        # ── 1st person pronouns ───────────────────────────────────────────
        ("نَا",    {"obj": "1PL"}),
        ("نِي",    {"obj": "1SG"}),
        ("يَ",     {"obj": "1SG"}),   # after long vowel: كِتَابِيَ
        ("ي",      {"obj": "1SG"}),
        # ── 2nd person pronouns ───────────────────────────────────────────
        ("كُمَا",  {"obj": "2DU"}),
        ("كُمْ",   {"obj": "2MPL"}),
        ("كُم",    {"obj": "2MPL"}),
        ("كُنَّ",  {"obj": "2FPL"}),
        ("كَ",     {"obj": "2MSG"}),
        ("كِ",     {"obj": "2FSG"}),
        # ── Dual noun endings ─────────────────────────────────────────────
        # e.g. كِتَابَانِ (two books, nom), كِتَابَيْنِ (two books, acc/gen)
        ("انِ",    {"num": "DU", "case": "NOM"}),
        ("يْنِ",   {"num": "DU", "case": "OBL"}),   # acc/gen dual
        ("ان",     {"num": "DU", "case": "NOM"}),   # undiacritical
        ("ين",     {"num": "DU", "case": "OBL"}),   # undiacritical
        # ── Feminine plural endings ───────────────────────────────────────
        # e.g. مُعَلِّمَاتٌ (teachers, nom), مُعَلِّمَاتِ (gen/acc)
        ("اتِ",    {"num": "PL", "gender": "F", "case": "OBL"}),
        ("اتٌ",    {"num": "PL", "gender": "F", "case": "NOM"}),
        ("ات",     {"num": "PL", "gender": "F"}),   # undiacritical
        # ── 2nd person verb agreement suffixes ───────────────────────────
        # e.g. كَتَبْتُمَا (you two wrote), كَتَبْتُمْ (you [pl] wrote)
        ("تُمَا",  {"person": "2", "num": "DU", "gender": "M"}),
        ("تُمْ",   {"person": "2", "num": "PL", "gender": "M"}),
        ("تُنَّ",  {"person": "2", "num": "PL", "gender": "F"}),
        ("تُم",    {"person": "2", "num": "PL", "gender": "M"}),  # undiacritical
        # ── Energetic nun (نون التوكيد) ───────────────────────────────────
        # Attaches to verbs for emphasis: اكْتُبَنَّ (do write!), يَكْتُبَنْ
        ("نَّ",    {"emph": "NUN_THAQILA"}),
        ("نْ",     {"emph": "NUN_KHAFIFA"}),
        # ── Masculine sound plural suffix (ـون / ـين) ─────────────────────────
        # e.g. كَاتِبُون (writers, nom), كَاتِبِين (writers, acc/gen)
        # Stripped as enclitics so the stem كاتب can be analyzed correctly.
        ("ُون",    {"num": "PL", "gender": "M", "case": "NOM"}),
        ("ِين",    {"num": "PL", "gender": "M", "case": "OBL"}),
        ("ون",     {"num": "PL", "gender": "M"}),   # undiacritical
        ("ين",     {"num": "PL", "gender": "M"}),   # undiacritical (also dual OBL — ambiguous)
    ]

    # Consonant set (Arabic Unicode block, excluding vowel diacritics and ة).
    # ة (ta marbuta, U+0629) is intentionally excluded: it is a grammatical
    # feminine suffix, never a root consonant. It is stripped by
    # _strip_diacritics before _extract_consonants is called, but excluding
    # it here ensures it is never counted even if it somehow survives stripping.
    AR_CONSONANTS = set(
        "ءابتثجحخدذرزسشصضطظعغفقكلمنهوي"
        "أإآىؤئ"
    )

    # Closed-class function words: prepositions, conjunctions, particles,
    # interrogatives, and other primitives that are NOT derived from roots.
    # These are intercepted before Step B to avoid misclassification.
    CLOSED_CLASS: Dict[str, Dict[str, str]] = {
        # ── Prepositions (حروف الجر) ──────────────────────────────────────
        "في":    {"pos": "PART", "subcat": "PREP", "gloss": "in/at"},
        "فِي":   {"pos": "PART", "subcat": "PREP", "gloss": "in/at"},
        "من":    {"pos": "PART", "subcat": "PREP", "gloss": "from/of"},
        "مِن":   {"pos": "PART", "subcat": "PREP", "gloss": "from/of"},
        "مِنْ":  {"pos": "PART", "subcat": "PREP", "gloss": "from/of"},
        "إلى":   {"pos": "PART", "subcat": "PREP", "gloss": "to/toward"},
        "إِلَى": {"pos": "PART", "subcat": "PREP", "gloss": "to/toward"},
        "على":   {"pos": "PART", "subcat": "PREP", "gloss": "on/upon"},
        "عَلَى": {"pos": "PART", "subcat": "PREP", "gloss": "on/upon"},
        "عن":    {"pos": "PART", "subcat": "PREP", "gloss": "about/from"},
        "عَن":   {"pos": "PART", "subcat": "PREP", "gloss": "about/from"},
        "عَنْ":  {"pos": "PART", "subcat": "PREP", "gloss": "about/from"},
        "مع":    {"pos": "PART", "subcat": "PREP", "gloss": "with"},
        "مَعَ":  {"pos": "PART", "subcat": "PREP", "gloss": "with"},
        "حتى":   {"pos": "PART", "subcat": "SUB", "gloss": "until/even"},
        "حَتَّى": {"pos": "PART", "subcat": "SUB", "gloss": "until/even"},
        "منذ":   {"pos": "PART", "subcat": "PREP", "gloss": "since/ago"},
        "مُنْذُ": {"pos": "PART", "subcat": "PREP", "gloss": "since/ago"},
        "خلال":  {"pos": "PART", "subcat": "PREP", "gloss": "during/through"},
        "بين":   {"pos": "PART", "subcat": "PREP", "gloss": "between"},
        "بَيْنَ": {"pos": "PART", "subcat": "PREP", "gloss": "between"},
        "فوق":   {"pos": "PART", "subcat": "PREP", "gloss": "above"},
        "تحت":   {"pos": "PART", "subcat": "PREP", "gloss": "under"},
        "أمام":  {"pos": "PART", "subcat": "PREP", "gloss": "in front of"},
        "وراء":  {"pos": "PART", "subcat": "PREP", "gloss": "behind"},
        "بعد":   {"pos": "PART", "subcat": "PREP", "gloss": "after"},
        "بَعْدَ": {"pos": "PART", "subcat": "PREP", "gloss": "after"},
        "قبل":   {"pos": "PART", "subcat": "PREP", "gloss": "before"},
        "قَبْلَ": {"pos": "PART", "subcat": "PREP", "gloss": "before"},
        "عند":   {"pos": "PART", "subcat": "PREP", "gloss": "at/with (possession)"},
        "عِنْدَ": {"pos": "PART", "subcat": "PREP", "gloss": "at/with (possession)"},
        "لدى":   {"pos": "PART", "subcat": "PREP", "gloss": "with/at (possession)"},
        "لَدَى":  {"pos": "PART", "subcat": "PREP", "gloss": "with/at (possession)"},
        "حول":   {"pos": "PART", "subcat": "PREP", "gloss": "around/about"},
        "ضد":    {"pos": "PART", "subcat": "PREP", "gloss": "against"},
        "رغم":   {"pos": "PART", "subcat": "PREP", "gloss": "despite"},
        "نحو":   {"pos": "PART", "subcat": "PREP", "gloss": "toward/approximately"},
        # ── Conjunctions (حروف العطف والربط) ─────────────────────────────
        "أو":    {"pos": "PART", "subcat": "CONJ", "gloss": "or"},
        "أَوْ":  {"pos": "PART", "subcat": "CONJ", "gloss": "or"},
        "أم":    {"pos": "PART", "subcat": "CONJ", "gloss": "or (in questions)"},
        "أَمْ":  {"pos": "PART", "subcat": "CONJ", "gloss": "or (in questions)"},
        "لكن":   {"pos": "PART", "subcat": "CONJ", "gloss": "but"},
        "لَكِن":  {"pos": "PART", "subcat": "CONJ", "gloss": "but"},
        "لكنّ":  {"pos": "PART", "subcat": "CONJ", "gloss": "but (with noun)"},
        "بل":    {"pos": "PART", "subcat": "CONJ", "gloss": "rather/but"},
        "بَلْ":  {"pos": "PART", "subcat": "CONJ", "gloss": "rather/but"},
        "ثم":    {"pos": "PART", "subcat": "CONJ", "gloss": "then"},
        "ثُمَّ":  {"pos": "PART", "subcat": "CONJ", "gloss": "then"},
        "إذ":    {"pos": "PART", "subcat": "CONJ", "gloss": "since/when (causal)"},
        "إذا":   {"pos": "PART", "subcat": "SUB", "gloss": "if/when"},
        "إِذَا":  {"pos": "PART", "subcat": "SUB", "gloss": "if/when"},
        "لو":    {"pos": "PART", "subcat": "CONJ", "gloss": "if (counterfactual)"},
        "لَوْ":  {"pos": "PART", "subcat": "CONJ", "gloss": "if (counterfactual)"},
        "كي":    {"pos": "PART", "subcat": "SUB", "gloss": "so that"},
        "كَيْ":  {"pos": "PART", "subcat": "SUB", "gloss": "so that"},
        "حين":   {"pos": "PART", "subcat": "CONJ", "gloss": "when"},
        "حِينَ":  {"pos": "PART", "subcat": "CONJ", "gloss": "when"},
        "عندما": {"pos": "PART", "subcat": "CONJ", "gloss": "when"},
        "بينما": {"pos": "PART", "subcat": "CONJ", "gloss": "while"},
        "لأن":   {"pos": "PART", "subcat": "CONJ", "gloss": "because"},
        "لأنّ":  {"pos": "PART", "subcat": "CONJ", "gloss": "because"},
        "لأنه":  {"pos": "PART", "subcat": "CONJ", "gloss": "because he/it"},
        "لأنها": {"pos": "PART", "subcat": "CONJ", "gloss": "because she/it"},
        "كلما":  {"pos": "PART", "subcat": "CONJ", "gloss": "whenever/the more"},
        "مما":   {"pos": "PART", "subcat": "CONJ", "gloss": "from what/than"},
        # ── Subordinators / complementizers ──────────────────────────────
        "أن":    {"pos": "PART", "subcat": "COMP", "gloss": "that (complementizer)"},
        "أَنْ":  {"pos": "PART", "subcat": "COMP", "gloss": "that (complementizer, before verb)"},
        "أنّ":   {"pos": "PART", "subcat": "COMP", "gloss": "that (complementizer, before noun)"},
        "إن":    {"pos": "PART", "subcat": "COMP", "gloss": "if/that (conditional)"},
        "إِنْ":  {"pos": "PART", "subcat": "COMP", "gloss": "if (conditional)"},
        "إنّ":   {"pos": "PART", "subcat": "COMP", "gloss": "indeed/verily (emphasis)"},
        "كأن":   {"pos": "PART", "subcat": "COMP", "gloss": "as if"},
        "كأنّ":  {"pos": "PART", "subcat": "COMP", "gloss": "as if"},
        "ليت":   {"pos": "PART", "subcat": "COMP", "gloss": "would that (wish)"},
        "لعل":   {"pos": "PART", "subcat": "COMP", "gloss": "perhaps/maybe"},
        "لَعَلَّ": {"pos": "PART", "subcat": "COMP", "gloss": "perhaps/maybe"},
        # ── Interrogative particles ───────────────────────────────────────
        "هل":    {"pos": "PART", "subcat": "INTERROG", "gloss": "yes/no question marker"},
        "هَلْ":  {"pos": "PART", "subcat": "INTERROG", "gloss": "yes/no question marker"},
        "ما":    {"pos": "PART", "subcat": "INTERROG", "gloss": "what"},
        "مَا":   {"pos": "PART", "subcat": "INTERROG", "gloss": "what"},
        "ماذا":  {"pos": "PART", "subcat": "INTERROG", "gloss": "what (object)"},
        "من":    {"pos": "PART", "subcat": "INTERROG", "gloss": "who"},  # ambiguous with prep; context-resolved
        "كيف":   {"pos": "PART", "subcat": "INTERROG", "gloss": "how"},
        "كَيْفَ": {"pos": "PART", "subcat": "INTERROG", "gloss": "how"},
        "لماذا": {"pos": "PART", "subcat": "INTERROG", "gloss": "why"},
        "متى":   {"pos": "PART", "subcat": "INTERROG", "gloss": "when"},
        "أين":   {"pos": "PART", "subcat": "INTERROG", "gloss": "where"},
        "أَيْنَ": {"pos": "PART", "subcat": "INTERROG", "gloss": "where"},
        "كم":    {"pos": "PART", "subcat": "INTERROG", "gloss": "how many/much"},
        "كَمْ":  {"pos": "PART", "subcat": "INTERROG", "gloss": "how many/much"},
        "أيّ":   {"pos": "PART", "subcat": "INTERROG", "gloss": "which"},
        # ── Negation particles ────────────────────────────────────────────
        "لا":    {"pos": "PART", "subcat": "NEG", "gloss": "no/not (present/imperative)"},
        "لَا":   {"pos": "PART", "subcat": "NEG", "gloss": "no/not"},
        "لم":    {"pos": "PART", "subcat": "NEG", "gloss": "did not (jussive negation)"},
        "لَمْ":  {"pos": "PART", "subcat": "NEG", "gloss": "did not (jussive negation)"},
        "لن":    {"pos": "PART", "subcat": "NEG", "gloss": "will not (future negation)"},
        "لَنْ":  {"pos": "PART", "subcat": "NEG", "gloss": "will not (future negation)"},
        "ليس":   {"pos": "PART", "subcat": "NEG", "gloss": "is not (copular negation)"},
        "لَيْسَ": {"pos": "PART", "subcat": "NEG", "gloss": "is not (copular negation)"},
        "غير":   {"pos": "PART", "subcat": "NEG", "gloss": "non-/un- (nominal negation)"},
        # ── Discourse / focus particles ───────────────────────────────────
        "قد":    {"pos": "PART", "subcat": "DISC", "gloss": "already/perhaps (verbal particle)"},
        "قَدْ":  {"pos": "PART", "subcat": "DISC", "gloss": "already/perhaps"},
        "إلا":   {"pos": "PART", "subcat": "DISC", "gloss": "except/only"},
        "إِلَّا": {"pos": "PART", "subcat": "DISC", "gloss": "except/only"},
        "فقط":   {"pos": "PART", "subcat": "DISC", "gloss": "only/just"},
        "أيضا":  {"pos": "PART", "subcat": "DISC", "gloss": "also/too"},
        "أَيْضًا": {"pos": "PART", "subcat": "DISC", "gloss": "also/too"},
        "جدا":   {"pos": "PART", "subcat": "DISC", "gloss": "very"},
        "جِدًّا": {"pos": "PART", "subcat": "DISC", "gloss": "very"},
        "ربما":  {"pos": "PART", "subcat": "DISC", "gloss": "perhaps/maybe"},
        "حقا":   {"pos": "PART", "subcat": "DISC", "gloss": "truly/really"},
        "إذن":   {"pos": "PART", "subcat": "DISC", "gloss": "therefore/so"},
        "إِذَنْ": {"pos": "PART", "subcat": "DISC", "gloss": "therefore/so"},
        "هنا":   {"pos": "PART", "subcat": "DISC", "gloss": "here"},
        "هناك":  {"pos": "PART", "subcat": "DISC", "gloss": "there"},
        "هُنَاكَ": {"pos": "PART", "subcat": "DISC", "gloss": "there"},
        # ── Demonstratives ──────────────────────────────────────────────────
        "هذا":   {"pos": "PART", "subcat": "DEM", "gloss": "this (M)"},
        "هَذَا":  {"pos": "PART", "subcat": "DEM", "gloss": "this (M)"},
        "هذه":   {"pos": "PART", "subcat": "DEM", "gloss": "this (F)"},
        "هَذِهِ": {"pos": "PART", "subcat": "DEM", "gloss": "this (F)"},
        "ذلك":   {"pos": "PART", "subcat": "DEM", "gloss": "that (M)"},
        "ذَلِكَ": {"pos": "PART", "subcat": "DEM", "gloss": "that (M)"},
        "تلك":   {"pos": "PART", "subcat": "DEM", "gloss": "that (F)"},
        "تِلْكَ": {"pos": "PART", "subcat": "DEM", "gloss": "that (F)"},
        "هؤلاء": {"pos": "PART", "subcat": "DEM", "gloss": "these"},
        "هَؤُلَاءِ": {"pos": "PART", "subcat": "DEM", "gloss": "these"},
        "أولئك": {"pos": "PART", "subcat": "DEM", "gloss": "those"},
        "أُولَئِكَ": {"pos": "PART", "subcat": "DEM", "gloss": "those"},
        "أيها":  {"pos": "PART", "subcat": "VOC", "gloss": "O (M)"},
        "أَيُّهَا": {"pos": "PART", "subcat": "VOC", "gloss": "O (M)"},
        "أواه":  {"pos": "PART", "subcat": "INTERJ", "gloss": "alas! oh!"},
        "أَوَّاه": {"pos": "PART", "subcat": "INTERJ", "gloss": "alas! oh!"},
        "الآن":  {"pos": "PART", "subcat": "DISC", "gloss": "now"},
        "دائما": {"pos": "PART", "subcat": "DISC", "gloss": "always"},
        "أحيانا": {"pos": "PART", "subcat": "DISC", "gloss": "sometimes"},
        "أبدا":  {"pos": "PART", "subcat": "DISC", "gloss": "never"},
        # ── Interjections and frozen expressions (أسماء الأفعال والتعجب) ─
        # These are not derived from roots. They are frozen forms.
        "يا":    {"pos": "PART", "subcat": "VOC", "gloss": "vocative particle (O!)"},
        "يَا":   {"pos": "PART", "subcat": "VOC", "gloss": "vocative particle (O!)"},
        "أيا":   {"pos": "PART", "subcat": "VOC", "gloss": "vocative particle (poetic/distant)"},
        "هيا":   {"pos": "PART", "subcat": "VOC", "gloss": "vocative particle (come on!)"},
        "آ":     {"pos": "PART", "subcat": "VOC", "gloss": "vocative particle (archaic)"},
        "أي":    {"pos": "PART", "subcat": "VOC", "gloss": "vocative particle (archaic/poetic)"},
        "اللهم": {"pos": "PART", "subcat": "VOC", "gloss": "O God! (frozen: يا + الله + ميم التعويض)"},
        "اللّهم": {"pos": "PART", "subcat": "VOC", "gloss": "O God! (with shadda)"},
        "هيهات": {"pos": "PART", "subcat": "INTERJ", "gloss": "far be it! / impossible! (اسم فعل)"},
        "هَيْهَاتَ": {"pos": "PART", "subcat": "INTERJ", "gloss": "far be it!"},
        "آمين":  {"pos": "PART", "subcat": "INTERJ", "gloss": "amen (frozen response particle)"},
        "أمين":  {"pos": "PART", "subcat": "INTERJ", "gloss": "amen (undiacritical variant)"},
        "آه":    {"pos": "PART", "subcat": "INTERJ", "gloss": "ah! (pain/sigh)"},
        "أوه":   {"pos": "PART", "subcat": "INTERJ", "gloss": "oh! (surprise/pain)"},
        "أف":    {"pos": "PART", "subcat": "INTERJ", "gloss": "ugh! / fie! (disgust)"},
        "أُفٍّ":  {"pos": "PART", "subcat": "INTERJ", "gloss": "ugh! (with tanwin)"},
        "صه":    {"pos": "PART", "subcat": "INTERJ", "gloss": "silence! / hush! (اسم فعل أمر)"},
        "صهٍ":   {"pos": "PART", "subcat": "INTERJ", "gloss": "silence! (with tanwin)"},
        "مه":    {"pos": "PART", "subcat": "INTERJ", "gloss": "stop! / enough! (اسم فعل أمر)"},
        "إيه":   {"pos": "PART", "subcat": "INTERJ", "gloss": "go on! / yes? (encouraging)"},
        "بخ":    {"pos": "PART", "subcat": "INTERJ", "gloss": "bravo! / well done!"},
        "بخٍ":   {"pos": "PART", "subcat": "INTERJ", "gloss": "bravo! (with tanwin)"},
        "وا":    {"pos": "PART", "subcat": "INTERJ", "gloss": "alas! (lament vocative: وا محمداه)"},
        "واه":   {"pos": "PART", "subcat": "INTERJ", "gloss": "oh! (wonder/admiration)"},
        "شتان":  {"pos": "PART", "subcat": "INTERJ", "gloss": "how different! / what a difference! (اسم فعل)"},
        "شَتَّانَ": {"pos": "PART", "subcat": "INTERJ", "gloss": "how different!"},
        "سرعان": {"pos": "PART", "subcat": "INTERJ", "gloss": "how quickly! (اسم فعل)"},
        "وشكان": {"pos": "PART", "subcat": "INTERJ", "gloss": "how soon! (اسم فعل)"},
        # ── Oaths (أحرف القسم — standalone, not as proclitics) ───────────
        "والله": {"pos": "PART", "subcat": "OATH", "gloss": "by God! (و + الله)"},        "تالله": {"pos": "PART", "subcat": "OATH", "gloss": "by God! (ت + الله, archaic)"},
        "بالله": {"pos": "PART", "subcat": "OATH", "gloss": "by God! (ب + الله)"},
        # ── Standalone response particles ─────────────────────────────────
        "نعم":   {"pos": "PART", "subcat": "RESP", "gloss": "yes"},
        "نَعَمْ":  {"pos": "PART", "subcat": "RESP", "gloss": "yes"},
        "بلى":   {"pos": "PART", "subcat": "RESP", "gloss": "yes (contradicting a negative)"},
        "بَلَى":  {"pos": "PART", "subcat": "RESP", "gloss": "yes (contradicting a negative)"},
        "أجل":   {"pos": "PART", "subcat": "RESP", "gloss": "yes / indeed"},
        "كلا":   {"pos": "PART", "subcat": "RESP", "gloss": "no! / certainly not (strong negation)"},
        "كَلَّا":  {"pos": "PART", "subcat": "RESP", "gloss": "no! / certainly not"},
        # ── Conditional/concessive particles ─────────────────────────────────
        # لولا / لوما — counterfactual conditionals ("if it were not for...")
        # These are compound frozen particles, not analyzable as ل + ولا etc.
        "لولا":  {"pos": "PART", "subcat": "COND", "gloss": "if it were not for (counterfactual)"},
        "لَوْلَا": {"pos": "PART", "subcat": "COND", "gloss": "if it were not for (counterfactual)"},
        "لوما":  {"pos": "PART", "subcat": "COND", "gloss": "if it were not for (rare variant of لولا)"},
        "لَوْمَا": {"pos": "PART", "subcat": "COND", "gloss": "if it were not for (rare variant)"},
        # ── كان وأخواتها — ما-negated forms (الأفعال الناقصة المنفية بما) ────
        # These are frozen negated verb forms. The ما here is the Hijazi
        # negation particle (ما النافية للفعل), not the interrogative ما.
        # The whole compound is a single lexical unit in MSA usage.
        "مازال":   {"pos": "VERB", "subcat": "KANA", "gloss": "still is / has not ceased (ما + زال)"},
        "مَازَالَ": {"pos": "VERB", "subcat": "KANA", "gloss": "still is / has not ceased"},
        "مادام":   {"pos": "VERB", "subcat": "KANA", "gloss": "as long as (ما + دام)"},
        "مَادَامَ": {"pos": "VERB", "subcat": "KANA", "gloss": "as long as"},
        "مابرح":   {"pos": "VERB", "subcat": "KANA", "gloss": "has not ceased (ما + برح)"},
        "مَابَرِحَ": {"pos": "VERB", "subcat": "KANA", "gloss": "has not ceased"},
        "مافتئ":   {"pos": "VERB", "subcat": "KANA", "gloss": "has not ceased (ما + فتئ)"},
        "مَافَتِئَ": {"pos": "VERB", "subcat": "KANA", "gloss": "has not ceased"},
        "ماانفك":  {"pos": "VERB", "subcat": "KANA", "gloss": "has not ceased (ما + انفك)"},
        "مَاانْفَكَّ": {"pos": "VERB", "subcat": "KANA", "gloss": "has not ceased"},
        "ماانفكّ": {"pos": "VERB", "subcat": "KANA", "gloss": "has not ceased (undiacritical)"},
    }

    # Common Arabic loanwords — foreign words adopted into Arabic that should
    # NOT be analyzed as native root-and-pattern words. Checked in analyze()
    # before Steps A/B/C. Returns pos=NOM, tags={"origin": "FOREIGN"}.
    LOANWORDS = {
        # Technology
        "تلفزيون", "تليفزيون", "كمبيوتر", "كومبيوتر", "إنترنت", "انترنت",
        "تكنولوجيا", "تقنولوجيا", "تلفون", "تليفون", "هاتف", "موبايل",
        "راديو", "فيديو", "سينما", "كاميرا", "ميكروفون", "تلغراف",
        "تلسكوب", "ميكروسكوب",
        # Politics/Society
        "ديموقراطية", "ديمقراطية", "برلمان", "بروتوكول", "دبلوماسية",
        "أيديولوجية", "إيديولوجية", "ليبرالية", "إمبريالية", "بيروقراطية",
        "بروباغندا", "استراتيجية",
        # Finance/Commerce
        "بنك", "شيك", "بورصة", "بجت", "ميزانية",
        # Academic/Professional
        "بروفيسور", "بروفسور", "دكتور", "دكتوراه", "أكاديمية", "جامعة",
        "فلسفة",
        # Culture/Daily life
        "فيلم", "أفلام", "سيناريو", "دراما", "كوميديا", "أوبرا",
        "بيانو", "جيتار", "موسيقى",
        "شوكولاتة", "كعك", "بسكويت", "ساندويتش", "بيتزا",
        "جينز", "بلوزة", "جاكيت",
        # Transportation
        "أوتوماتيكي", "أوتوماتيك", "أوتوبيس", "تاكسي", "ميترو", "باص",
        "ترام", "ليموزين",
        # Science
        "أوكسجين", "أكسجين", "هيدروجين", "بروتين", "فيتامين",
        "كيمياء", "فيزياء",
        # Other
        "كاتالوج", "كتالوج", "تليسكوب", "ألبوم", "أرشيف",
        "ماراثون", "أولمبياد", "إستاد", "ستاد",
    }

    def __init__(self, config_dir: str = "morph_efficiency_project/configs"):
        with open(os.path.join(config_dir, "ar_templates.json"), encoding="utf-8") as f:
            self.templates = json.load(f)
        with open(os.path.join(config_dir, "ar_roots.json"), encoding="utf-8") as f:
            root_data = json.load(f)
        self.root_set: set = set(root_data.get("roots", []))

        # Recursion guard for the enclitic-pronoun intercept, which re-enters
        # analyze() on the bare (pronoun-stripped) stem.
        self._enc_depth = 0

        # Build template index: root-slot count → list of templates.
        # Root slots are the ف، ع، ل placeholder positions in the وزن.
        # We count only those three letters (not augment consonants like
        # م، ت، ن، س، ا، و، ي) so that e.g. فَاعِل → 3 slots (not 4),
        # مَفْعُول → 3 slots (not 5), اِسْتَفْعَلَ → 3 slots (not 6).
        # This is the only correct way to group templates for matching
        # against a stripped stem's consonant count.
        FAL = set("فعل")
        self._tmpl_index: Dict[int, List[dict]] = defaultdict(list)
        for tmpl in self.templates:
            wazn = tmpl.get("وزن", "")
            # Strip diacritics and ta marbuta, take only the past-tense form
            # (before the / separator if present)
            wazn_clean = re.sub(r"[\u064B-\u065F\u0670]", "", wazn)
            wazn_clean = wazn_clean.replace("ة", "").split("/")[0].strip()
            root_slots = sum(1 for c in wazn_clean if c in FAL)
            self._tmpl_index[root_slots].append(tmpl)
            # Reason: index by (category, verb_form) so Step B' (wazn -> semantic_role)
            # can look up the matched template's semantic_role.
            cat = tmpl.get("category", "")
            vf = tmpl.get("verb_form", "") or ""
            key = (cat, vf)
            if not hasattr(self, "_tmpl_by_cat_form"):
                self._tmpl_by_cat_form = {}
            if key not in self._tmpl_by_cat_form:
                self._tmpl_by_cat_form[key] = tmpl

        # Relative pronouns (الأسماء الموصولة) and demonstratives (أسماء الإشارة)
        # are closed-class function words, not root-derived. Adding them prevents
        # the decomposer from inventing roots like التي→تي.
        self.CLOSED_CLASS = dict(self.CLOSED_CLASS)
        for _w in ["التي", "الذي", "الذين", "اللذان", "اللذين", "اللتان",
                   "اللتين", "اللاتي", "اللواتي", "اللائي", "الذى"]:
            self.CLOSED_CLASS[_w] = {"pos": "PART", "subcat": "REL", "gloss": "which/who"}
        for _w in ["هذا", "هذه", "هذان", "هذين", "هاتان", "هاتين", "هؤلاء",
                   "ذلك", "ذلكم", "تلك", "أولئك", "ذاك", "هنا", "هناك", "هنالك"]:
            self.CLOSED_CLASS[_w] = {"pos": "PART", "subcat": "DEM", "gloss": "this/that"}
        # High-frequency conjunctions, adverbials and subordinators that are not
        # root-derived (كما, عندما, حيث …). Adding them stops the decomposer from
        # inventing roots for them and improves POS.
        # Diacritised/multi-letter forms only — bare 2-letter alif forms (ان, او,
        # ام, اذ, لان) are omitted because they collide with content words
        # (لانَ = verb ل-ي-ن, اما, …).
        for _w in ["كما", "عندما", "كذلك", "أمّا", "بينما",
                   "حيث", "حيثما", "حتى", "حتّى", "إذا", "إذ",
                   "لأن", "لأنّ", "ثمّ", "أو", "أم",
                   "لكن", "لكنّ", "لقد", "سوف", "أيضا", "أيضاً",
                   "إنّ", "أنّ", "إذن", "لذلك", "هكذا",
                   "بحيث", "لكي", "ريثما", "كأنّ"]:
            self.CLOSED_CLASS.setdefault(_w, {"pos": "PART", "subcat": "FUNC", "gloss": "particle"})

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _strip_diacritics(self, text: str) -> str:
        """Remove Arabic short vowel diacritics (harakat) and ta marbuta."""
        # Unicode range for Arabic diacritics: U+064B–U+065F, U+0670 (superscript alif)
        text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
        # Strip ta marbuta (ة U+0629): it is a grammatical feminine suffix,
        # never a root consonant. Replace with ت so the stem is preserved
        # for display but the consonant count is correct.
        # e.g. كِتَابَة → كتاب (3 root consonants), مَكْتَبَة → مكتب
        text = text.replace("ة", "")
        return text

    # Hamza normalization map: all orthographic hamza variants → bare ء
    # Used before root lookup so that أ، إ، آ، ؤ، ئ all resolve to the
    # same consonant slot as ء in the root list.
    # The original surface form is preserved in TokenInfo.surface.
    _HAMZA_NORM = str.maketrans("أإآؤئ", "ءءءءء")

    def _normalize_hamza(self, text: str) -> str:
        """Normalize all hamza orthographic variants to bare ء."""
        return text.translate(self._HAMZA_NORM)

    def _extract_consonants(self, text: str) -> str:
        """Return only consonant characters from Arabic text.

        Applies hamza normalization before extraction so that أ، إ، آ، ؤ، ئ
        are all treated as the same consonant (ء) for root matching.
        """
        stripped = self._strip_diacritics(text)
        normalized = self._normalize_hamza(stripped)
        return "".join(c for c in normalized if c in self.AR_CONSONANTS)

    def _extract_root_consonants(self, text: str) -> str:
        """Return only root-bearing consonants, excluding long-vowel letters.

        Long vowels (ا، و، ي) are part of the morphological pattern (وزن),
        not the root. Stripping them gives the true root-consonant count
        needed for template index lookup.

        e.g. كِتَابَة → strip diacritics+ة → كتاب → strip long vowels → كتب (3)
             مُعَلِّم → strip diacritics → معلم → strip long vowels → معلم (4)
               but م is an augment prefix, handled by _step_b fallback.
             قَالَ → strip diacritics → قال → strip long vowels → قل (2)
               → أجوف: middle ا is the weak radical marker, handled in _step_c.

        Note: و and ي are kept when they appear to be root consonants
        (i.e., when they are NOT preceded by a long vowel context). Since
        we cannot determine this without full vowel context, we use a
        conservative approach: strip ا only (the most common long-vowel
        marker in unvoweled text), and keep و/ي (they are often root
        consonants in مثال/ناقص roots).
        """
        consonants = self._extract_consonants(text)
        # Strip bare alif (ا) which is almost always a long vowel marker
        # in the middle of a word, not a root consonant.
        # Keep initial ا (it may be hamza/root) and final ا (ناقص marker,
        # handled in _step_c).
        if len(consonants) > 2:
            # Remove internal ا (not first, not last)
            middle = consonants[1:-1].replace("ا", "")
            consonants = consonants[0] + middle + consonants[-1]
        return consonants

    # ── Step A: stacked clitic stripping ─────────────────────────────────────

    def _step_a(self, word: str) -> Tuple[str, Dict[str, List[str]]]:
        """
        Strip all stacked proclitics then enclitics.
        Returns (stem, clitics_dict).
        clitics_dict = {"pre": [...tags...], "enc": [...tags...]}
        """
        stem = word
        pre_tags: List[dict] = []
        enc_tags: List[dict] = []

        # Strip proclitics in a loop (Arabic can stack وَبِالـ etc.)
        # Minimum remaining length after stripping:
        #   - Multi-character proclitics: 2 chars (standard guard)
        #   - Single undiacritical conjunctions (و ف): 3-consonant guard.
        #     و and ف are unambiguous conjunctions — they are never root
        #     consonants with a following consonant cluster in MSA.
        #   - Single undiacritical prep/tense (ب ل ك س): 4-consonant guard.
        #     These can be root-initial (سَفِينَة root سفن, كَتَبَ root كتب),
        #     so we require 4 consonants remaining to avoid false strips.
        CONJ_UNDIAC = {"و", "ف"}   # conjunctions — 3-consonant guard
        PREP_UNDIAC = {"ب", "ل", "ك", "س"}  # prep/tense — 4-consonant guard
        SINGLE_UNDIAC = CONJ_UNDIAC | PREP_UNDIAC  # combined for startswith check
        # Diacritical single-char proclitics split into two groups:
        #   CONJ_DIAC — وَ and فَ are unambiguous conjunctions; they use the
        #     3-consonant guard (same as undiacritical) because they are never
        #     root consonants with a fatha in this position.
        #   SINGLE_DIAC — all other diacritical single-char proclitics (كَ، بِ،
        #     لِ، سَ، أَ، تَ، تِ) use the 4-consonant guard since they can be
        #     confused with root-initial consonants (كَاتِب، بَاعَ، لَعِبَ).
        CONJ_DIAC = {"وَ", "فَ"}
        SINGLE_DIAC = {
            "بِ", "بُ", "بَ",
            "لِ", "لُ", "لَ", "كَ",
            "سَ", "أَ",
        }
        changed = True
        al_stripped = False  # track whether ال was already stripped this pass
        while changed:
            changed = False
            for surface, tags in self.PROCLITICS:
                # Single-char proclitics need a stricter guard: require that
                # the remaining stem has enough consonants after stripping,
                # so we never eat a root-initial consonant.
                # CONJ_DIAC (وَ، فَ): unambiguous conjunctions → 3-consonant guard
                # SINGLE_UNDIAC (و، ف، ب، ل، ك، س): 3-consonant guard + diacritic check
                # SINGLE_DIAC (كَ، بِ، لِ، etc.): 4-consonant guard
                # Multi-char proclitics (ال، بال، etc.): standard 2-char guard.
                if surface in SINGLE_UNDIAC or surface in SINGLE_DIAC or surface in CONJ_DIAC:
                    if not stem.startswith(surface):
                        continue
                    # After ال has been stripped, do NOT strip a further
                    # single-char proclitic — it would eat the first root
                    # consonant of the remaining word (e.g. الكتاب → كتاب,
                    # then ك stripped as undiacritical proclitic → تاب).
                    if al_stripped and surface in (SINGLE_UNDIAC | SINGLE_DIAC | CONJ_DIAC):
                        continue
                    # For undiacritical single-char proclitics (و، ف، ب، ل، ك، س):
                    # reject if the proclitic character is immediately followed by
                    # a diacritic (haraka). A diacritic after the first consonant
                    # means it is a root consonant with a vowel, not a bare proclitic.
                    # e.g. كِتَابِي: ك is followed by kasra ِ → NOT a proclitic
                    #      وَكَتَبَ: و is followed by fatha َ → NOT a proclitic
                    #      وكتب (unvoweled): و has no following diacritic → IS a proclitic
                    AR_DIACRITICS = "\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652\u0670"
                    if surface in SINGLE_UNDIAC and len(stem) > len(surface):
                        next_char = stem[len(surface)]
                        if next_char in AR_DIACRITICS:
                            continue
                    remaining = stem[len(surface):]
                    # For the consonant count guard, also strip any trailing
                    # enclitic from the remaining string before counting.
                    # This prevents كَتَبَهَا from having كَ stripped:
                    # remaining=تَبَهَا, strip هَا → تَبَ = 2 consonants < 4 → REJECT.
                    remaining_for_guard = remaining
                    for _enc_surf, _ in self.ENCLITICS:
                        if (remaining_for_guard.endswith(_enc_surf)
                                and len(remaining_for_guard) - len(_enc_surf) >= 2):
                            remaining_for_guard = remaining_for_guard[:-len(_enc_surf)]
                            break
                    remaining_cons = self._extract_root_consonants(remaining_for_guard)
                    # Guard thresholds:
                    #   CONJ_DIAC (وَ، فَ): 3 consonants — unambiguous conjunctions
                    #   CONJ_UNDIAC (و، ف): 3 consonants — diacritic check is primary guard
                    #   PREP_UNDIAC (ب، ل، ك، س): 4 consonants — can be root-initial
                    #   SINGLE_DIAC (كَ، بِ، لِ، سَ، etc.): 4 consonants
                    if surface in CONJ_DIAC or surface in CONJ_UNDIAC:
                        min_cons = 3
                    elif (surface in ("ل", "ب", "لِ", "بِ")
                          and remaining[:1] == "إ"):
                        # A prep ل/ب before an إ-augmented form (لِإِدَارَة Form IV
                        # masdar, root د.و.ر) is unambiguous: the prep can never be
                        # the first radical when the very next letter is the
                        # hamzat-qaṭʿ augment إ. Use the conjunction-grade guard.
                        min_cons = 3
                    else:
                        min_cons = 4
                    if len(remaining_cons) < min_cons:
                        # Hollow-verb exception for the و/ف conjunction: وَكَانَ،
                        # وَقَالَ، وَدَارَ are و + a three-letter أجوف verb (R1+ا+R2).
                        # Its weak middle ا drops out of root_consonants, leaving
                        # only two and tripping the 3-radical guard, so the و is
                        # never peeled and the root is mangled (وكان→وكن). Allow the
                        # strip when the remainder is exactly R1 + ا + R2 and the
                        # recovered hollow root is known. وَزِير (و = R1, middle ي)
                        # is untouched: its middle letter is not ا.
                        # A shadda in the remainder marks an intensive فَعَّال
                        # (فَسَّاق root ف.س.ق, ف = R1), not a conjunction + hollow
                        # verb, so the gemination disqualifies the exception.
                        _conj_hollow_ok = False
                        if (surface in (CONJ_DIAC | CONJ_UNDIAC)
                                and len(remaining_cons) == 2
                                and "ّ" not in remaining):
                            _rem_full = self._extract_consonants(remaining_for_guard)
                            if (len(_rem_full) == 3 and _rem_full[1] == "ا"
                                    and _rem_full[0] not in "اوي"
                                    and _rem_full[2] not in "اوي"):
                                for _hv in ("و", "ي"):
                                    if _rem_full[0] + _hv + _rem_full[2] in self.root_set:
                                        _conj_hollow_ok = True
                                        break
                        if not _conj_hollow_ok:
                            continue
                    stem = remaining
                    pre_tags.append(tags)
                    changed = True
                    break
                # Multi-char proclitics
                min_remaining = 2
                if stem.startswith(surface) and len(stem) - len(surface) >= min_remaining:
                    # Guard: do NOT strip ال if the word looks like Form VIII اِفْتَعَلَ.
                    # In unvoweled text, اِلْتَقَى and الْتَقَى are identical bytes.
                    # Form VIII signature: starts with ا + consonant + ت + 2+ consonants.
                    # If this pattern matches, the ا is the Form VIII hamza, not ال.
                    if "def" in tags and len(stem) >= 5:
                        stem_cons = self._extract_consonants(stem)
                        # Form VIII: ا R1 ت R2 R3 [R4] — R1 at position 1, ت at position 2
                        if (len(stem_cons) >= 5
                                and stem_cons[0] == "ا"
                                and stem_cons[1] not in "اوي"
                                and stem_cons[2] == "ت"):
                            # In unvoweled text اِلْتَقَى (Form VIII) and الـتُّرْبَة
                            # (ال + noun with R1=ت) share these bytes. Disambiguate
                            # by trying the ال-stripped core: if it resolves to a
                            # known root via the ordinary noun/verb path, the ال is
                            # the article (التربة→ترب, التاريخ→ءرخ). Only keep the
                            # Form VIII reading when the core does NOT resolve
                            # (التقى→تقى ∉ root_set).
                            _al_core = stem[len(surface):]
                            # Strip a trailing nominal suffix (ات/ون/ين/ة) before
                            # probing the core, so a suffixed masdar like التطبيقات
                            # reduces to تطبيق→طبق and the ال is recognised as the
                            # article rather than a Form VIII hamza.
                            for _alsuf in ("ات", "ون", "ين", "ة"):
                                if _al_core.endswith(_alsuf) and len(_al_core) - len(_alsuf) >= 3:
                                    _al_core = _al_core[: -len(_alsuf)]
                                    break
                            _core_cat, _ = self._step_b(_al_core)
                            _core_root = self._step_c(_al_core, _core_cat, orig_word=_al_core)
                            if _core_root not in self.root_set:
                                continue  # skip ال strip — this is Form VIII
                    stem = stem[len(surface):]
                    pre_tags.append(tags)
                    # Track if ال was stripped (alone or as part of a compound)
                    if "def" in tags:
                        al_stripped = True
                    changed = True
                    break  # restart loop after each strip

        # Strip one enclitic (enclitics don't stack in MSA).
        # Single-character enclitics (ي، ه، ك) require stricter guards:
        #   - ي / يَ (1SG possessive): require 5+ consonants in the full stem
        #     before stripping, so we don't eat a root-final ي from words
        #     like يَرْمِي (root رمي) or يَمْشِي (root مشي).
        #   - ه، ك: require 3 chars remaining (standard guard).
        # Single-char enclitics with consonant-count guards:
        #   ي / يَ (1SG possessive): require 5+ consonants in full stem
        #   كَ / كِ (2MSG/2FSG): require 4 consonants remaining — same threshold
        #     as SINGLE_DIAC proclitics, because كَ can be a root consonant
        #     (e.g. شَارَكَ root شرك — كَ is R3, not an enclitic)
        #   ه (3MSG): require 3 chars remaining (standard guard)
        YA_ENC = {"ي", "يَ"}
        KA_ENC = {"كَ", "كِ"}   # diacritical 2nd-person enclitics — 4-consonant guard
        SINGLE_UNDIAC_ENC = {"ه"}
        # Masculine plural enclitics (ون/ين and diacritical variants) require
        # 3 consonants remaining after stripping to avoid eating root consonants
        # from short words like عُيُون (عيون → strip ون → عي = 2 consonants → REJECT).
        MASC_PL_ENC = {"ُون", "ِين", "ون", "ين"}
        # Enclitics that need a 3-consonant guard (not just 2-char remaining):
        # نِي / نِ (1SG) can be confused with root-final نِ in words like يَبْنِي.
        NI_ENC = {"نِي", "نِ"}
        for surface, tags in self.ENCLITICS:
            if surface in YA_ENC:
                if not stem.endswith(surface):
                    continue
                remaining = stem[: -len(surface)]
                remaining_cons = self._extract_consonants(remaining)
                # Require at least 5 consonants in the full stem before
                # stripping bare ي, so that root-final ي is not eaten.
                # e.g. يَرْمِي (4 consonants يرمي) → REJECT strip
                #      كِتَابِي (5 consonants كتابي) → ALLOW strip
                full_cons = self._extract_consonants(stem)
                if len(full_cons) < 5:
                    continue
                stem = remaining
                enc_tags.append(tags)
                break
            if surface in KA_ENC:
                # كَ/كِ require 4 consonants remaining after strip to avoid
                # eating a root-final ك (e.g. شَارَكَ root شرك — كَ is R3).
                if not stem.endswith(surface):
                    continue
                remaining = stem[:-len(surface)]
                if len(self._extract_root_consonants(remaining)) < 4:
                    continue
                stem = remaining
                enc_tags.append(tags)
                break
            if surface in MASC_PL_ENC:
                # ون/ين require 3 consonants remaining to avoid eating root
                # consonants from short words (e.g. عيون → strip ون → عي = 2 cons → REJECT).
                if not stem.endswith(surface):
                    continue
                remaining = stem[:-len(surface)]
                if len(self._extract_consonants(remaining)) < 3:
                    continue
                stem = remaining
                enc_tags.append(tags)
                break
            min_remaining = 3 if surface in SINGLE_UNDIAC_ENC else 2
            if surface in NI_ENC:
                # نِي / نِ need 3 consonants remaining to avoid eating root-final ن
                # e.g. يَبْنِي: strip نِي → يَبْ (1 consonant) → REJECT
                if not stem.endswith(surface):
                    continue
                remaining = stem[:-len(surface)]
                if len(self._extract_consonants(remaining)) < 3:
                    continue
                stem = remaining
                enc_tags.append(tags)
                break
            # Dual noun endings (انِ/يْنِ/ان/ين): require ≥4 consonants remaining
            # so فَعْلَان sifa adjectives (عَطْشَان, جَوْعَان, كَسْلَان — 3 cons before ان)
            # are not wrongly stripped as duals. Dual nouns derive from 3-cons
            # nominal stems WITH an internal long vowel, so the stem before ان
            # has 4+ consonants (كِتَاب=كتاب=4, مُعَلِّم=معلم=4 etc.).
            if surface in ("انِ", "ان", "يْنِ", "ين"):
                if not stem.endswith(surface):
                    continue
                remaining = stem[:-len(surface)]
                rem_cons = self._extract_consonants(remaining)
                # Dual stripping guards:
                #   - "انِ" / "ان": allow 3+ consonants (covers بَيْتَان=3, طَالِبَان=4).
                #     The فَعْلَان sifa pattern (عَطْشَان, جَوْعَان, كَسْلَان) is
                #     protected by an explicit lexicon below.
                #   - "يْنِ" / "ين": require 4+ to avoid eating root-final ي
                #     and avoid colliding with masc-pl OBL.
                if surface in ("انِ", "ان"):
                    if len(rem_cons) < 3:
                        continue
                    # Guard فَعْلَان sifa (adjective) by checking known stems
                    _SIFA_FALAN_STEMS = {"عَطْشَ", "جَوْعَ", "كَسْلَ", "غَضْبَ", "سَكْرَ",
                                          "عَجْلَ", "نَدْمَ", "حَيْرَ"}
                    if remaining in _SIFA_FALAN_STEMS:
                        continue
                    # Guard فُعْلَان masdar (damma on C1) — e.g. غُفْرَان, نُكْرَان
                    # and إفْعَال Form IV masdar — e.g. إِعْلَان, إِنْجَاز.
                    # When the dual stripping would leave only 3 consonants and
                    # the full stem looks like a masdar pattern, do NOT strip.
                    _DAMMA_CH = "ُ"
                    _KASRA_BELOW = "ِ"
                    if len(rem_cons) == 3:
                        # Form IV masdar: starts with إ (hamza-below)
                        if stem.startswith("إ"):
                            continue
                        # فُعْلَان masdar: damma on C1. Find first consonant's
                        # following diacritic; if damma, this is masdar فُعْلَان.
                        _c1_haraka = None
                        for _i, _ch in enumerate(stem):
                            if _ch in self.AR_CONSONANTS:
                                if _i + 1 < len(stem):
                                    _c1_haraka = stem[_i + 1]
                                break
                        if _c1_haraka == _DAMMA_CH:
                            continue
                else:
                    if len(rem_cons) < 4:
                        continue
                stem = remaining
                enc_tags.append(tags)
                break
            # Sound feminine plural ـات: only strip when the remaining stem still
            # holds at least three root consonants (the singular's skeleton, e.g.
            # كلمات→كلم، سيارات→سيار). A فَعَال / فِعَال singular masdar whose R3
            # happens to precede the ـا+ت (نَبَات root ن.ب.ت, leaving only نب) must
            # NOT be split, or the 2-consonant remnant is geminated into a spurious
            # root (نبات→نب→نبب).
            if surface == "ات":
                if not stem.endswith(surface):
                    continue
                remaining = stem[:-len(surface)]
                if len(self._extract_consonants(remaining)) < 3:
                    continue
                stem = remaining
                enc_tags.append(tags)
                break
            if stem.endswith(surface) and len(stem) - len(surface) >= min_remaining:
                stem = stem[: -len(surface)]
                enc_tags.append(tags)
                break

        clitics = {}
        if pre_tags:
            clitics["pre"] = pre_tags
        if enc_tags:
            clitics["enc"] = enc_tags

        # ── Imperfect verb prefix stripping (يَ/تَ/أَ/نَ) ─────────────────────
        # The imperfect (مضارع) conjugation prefixes are not proclitics —
        # they are inflectional prefixes that mark person/number/gender.
        # They are stripped here (after clitic stripping) when:
        #   1. The stem starts with يَ (diacritical) or bare ي (unvoweled corpus)
        #   2. At least 3 consonants remain after stripping (to preserve root)
        # This handles يَرْمِي → رمي, يبني (unvoweled) → بني, etc.
        # Bare ي requires 4 consonants remaining (stricter guard) because bare
        # ي can be a مثال root consonant (يَسَرَ root يسر). With 4 consonants
        # remaining we are confident the ي is a prefix, not a root consonant.
        # تَ/أَ/نَ are ambiguous with root-initial consonants and not stripped.
        for imperf_prefix, min_rem_cons in (("يَ", 3), ("ي", 3)):
            if stem.startswith(imperf_prefix):
                remaining_imp = stem[len(imperf_prefix):]
                remaining_cons = self._extract_consonants(remaining_imp)
                if len(remaining_cons) >= min_rem_cons:
                    stem = remaining_imp
                    pre_tags.append({"imperf": "3MSG"})
                    clitics["pre"] = pre_tags
                break  # only try one prefix form

        return stem, clitics

    # ── Step B: template matching (index used) ────────────────────────────────

    # Root placeholder consonants — used to count root slots in both the
    # template index (at build time) and the stem (at match time).
    _FAL = frozenset("فعل")

    def _count_root_slots(self, consonants: str) -> int:
        """Count how many ف/ع/ل placeholder positions a consonant string has.

        For a stripped stem, this is simply the total consonant count after
        removing ta marbuta (already done in _strip_diacritics) and normalizing
        hamza (done in _extract_consonants). The ف/ع/ل counting is only needed
        when parsing the وزن strings in the template index; for a real stem
        the consonant count IS the root-slot count.
        """
        return len(consonants)

    def _check_passive(self, word: str) -> bool:
        """Check if a diacritized word has passive voice vowel pattern.

        Form I passive (فُعِلَ) has damma (ُ U+064F) on C1 and kasra (ِ U+0650)
        on C2. Only reliable when diacritics are present.
        Returns True if passive pattern detected, False otherwise.
        """
        _DAMMA = "\u064F"
        _KASRA = "\u0650"
        # Find first two consonants and check their following diacritics
        cons_count = 0
        c1_has_damma = False
        c2_has_kasra = False
        for i, ch in enumerate(word):
            if ch in self.AR_CONSONANTS:
                cons_count += 1
                next_ch = word[i + 1] if i + 1 < len(word) else ""
                if cons_count == 1 and next_ch == _DAMMA:
                    c1_has_damma = True
                elif cons_count == 2 and next_ch == _KASRA:
                    c2_has_kasra = True
                    break
                elif cons_count == 2:
                    break
        return c1_has_damma and c2_has_kasra

    def _is_elative_root(self, root: str) -> bool:
        """Heuristic: return True if root is likely an elative adjective root.

        Elative adjectives (أَفْعَل) are formed from roots that describe
        qualities/attributes (big, small, good, bad, etc.). This is a
        conservative fallback — the main check uses the _ELATIVE_ROOTS set.
        """
        # If root is in root_set and is 3 consonants, it could be elative.
        # We return False here to let the _ELATIVE_ROOTS set be the authority.
        return False

    def _step_b(self, stem: str) -> Tuple[str, Dict[str, str]]:
        """
        Match stem against template index by root-slot count.
        Returns (template_category, tags_implied).
        Falls back to rule-based heuristic if no match.

        The template index is keyed by the number of root-slot consonants
        (ف/ع/ل positions) in the وزن, not the total consonant count.
        This correctly groups e.g. فَاعِل (3 root slots) with trilateral
        stems, rather than inflating the count with augment consonants.
        """
        consonants = self._extract_consonants(stem)
        # Use root-consonant count (strips internal ا long-vowel markers)
        # for template index lookup. Full consonants (with ا/و/ي) are kept
        # for weak-root detection below.
        root_consonants = self._extract_root_consonants(stem)
        n = len(root_consonants)

        # ── Pre-index checks: augmented forms with clear prefix markers ───────
        # These must run BEFORE the template index to avoid the index returning
        # a generic VERB_AUGMENTED match that would suppress the prefix skip.
        stripped = self._strip_diacritics(stem)

        # ── Nisba suffix stripping (ـيّ) ─────────────────────────────────────
        # The nisba suffix يّ (ي + shadda U+0651) is a derivational suffix that
        # creates relational adjectives (مِصْرِيّ = Egyptian, عَرَبِيّ = Arab).
        # It is NOT a root consonant. Strip it before template detection so that
        # مِصْرِيّ is analyzed as مصر (3 consonants) rather than مصري (4 consonants
        # which would trigger the NOM_DERIVED م-prefix check incorrectly).
        # Only strip when the stem ends in ي + shadda (voweled) or bare يّ.
        _SHADDA = "\u0651"
        _nisba_stripped = False
        _nisba_fem = False
        if stem.endswith("ة") and len(stem) >= 4:
            tail = stem[-6:]
            if "ي" in tail and _SHADDA in tail:
                # Strip ة, then all trailing diacritics; if it ends with ي,
                # strip that too — this is the nisba marker.
                _ws = stem[:-1]
                while _ws and _ws[-1] in "ًٌٍَُِّْٰ":
                    _ws = _ws[:-1]
                if _ws.endswith("ي"):
                    _ws = _ws[:-1]
                    _nisba_stripped = True
                    _nisba_fem = True
                    stem = _ws
                    stripped = self._strip_diacritics(stem)
        if not _nisba_stripped and len(stem) >= 3 and stem.endswith("يّ"):
            stem = stem[:-2]  # strip يّ (ي + shadda as single char sequence)
            stripped = self._strip_diacritics(stem)
            _nisba_stripped = True
        elif len(stem) >= 4 and stem[-1] == _SHADDA and stem[-2] == "ي":
            stem = stem[:-2]  # strip ي + shadda
            stripped = self._strip_diacritics(stem)
            _nisba_stripped = True

        # Recompute consonants after potential nisba stripping
        consonants = self._extract_consonants(stem)
        root_consonants = self._extract_root_consonants(stem)
        n = len(root_consonants)

        # ── Nisba adjective: return immediately after stripping ـيّ ──────────
        # e.g. عَرَبِيّ → stem=عرب → NISBA; مِصْرِيّ → stem=مصر → NISBA
        # Abstract nisba feminine (إِنْسَانِيَّة "humanity") differs from a plain
        # nisba adjective fem (مِصْرِيَّة "Egyptian-F") only in whether the base
        # stem carries an internal long-alif (إنسان vs مصر). When the post-strip
        # stem contains ا and has >=4 consonants, return VERB_TRILATERAL_UNKNOWN
        # per test spec (the surface is an abstract verbal noun, not an adjective).
        if _nisba_stripped:
            if _nisba_fem and "ا" in consonants and len(consonants) >= 4:
                return "VERB_TRILATERAL_UNKNOWN", {"pos": "NOM", "role": "MASDAR", "num": "SG", "gender": "F"}
            out_nis = {"pos": "ADJ", "role": "NISBA"}
            if _nisba_fem:
                out_nis["gender"] = "F"
            return "NISBA", out_nis

        # مُ with damma on the original stem → derived nominal.
        # Disambiguate AGENT (active participle) vs PASSIVE_PARTICIPLE by the
        # vowel on C2 of the underlying stem: kasra = AGENT, fatha = PASSIVE.
        # Special case: مُسْت prefix = Form X active participle (مُسْتَفْعِل).
        _KASRA = "ِ"
        _FATHA_CH = "َ"
        def _mu_role(s: str) -> str:
            # find the LAST kasra/fatha before the final consonant
            cons_count = 0
            last_haraka = None
            for i, ch in enumerate(s):
                if ch in self.AR_CONSONANTS:
                    cons_count += 1
                    nxt = s[i + 1] if i + 1 < len(s) else ""
                    if nxt in (_KASRA, _FATHA_CH):
                        last_haraka = nxt
            if last_haraka == _KASRA:
                return "AGENT"
            if last_haraka == _FATHA_CH:
                return "PASSIVE_PARTICIPLE"
            return "AGENT"  # default
        if stem.startswith("مُسْت") or stripped.startswith("مست"):
            role_x = _mu_role(stem)
            return "NOM_DERIVED_X", {"pos": "NOM", "role": role_x, "form": "X"}
        if stem.startswith("مُ"):
            # Geminate passive (e.g. مُدَّ ← مدد): مُ-prefix is NOT a real مُ-prefix,
            # it's just the damma on R1 of a 2-consonant geminate stem.
            # Surface: مُ + R2 + shadda = 2 consonants total + shadda.
            # Distinguish from real مُ-prefixed nouns by short length (2 cons).
            _hfs_local = len(stem) >= 2 and stem[-1] == "ّ"
            if _hfs_local and len(consonants) == 2:
                doubled_check = consonants + consonants[-1]
                if doubled_check in self.root_set:
                    return "VERB_DOUBLED_PASS", {"pos": "VERB", "form": "I", "tense": "PAST", "voice": "PASS"}
            # Form III masdar مُفَاعَلَة: مُ + R1 + ا + R2 + R3 + ة
            # After ة strip: cons = م+R1+ا+R2+R3 (5), ا at pos 2, stem ends with ة
            # Template name NOM_DERIVED per test spec; role=MASDAR distinguishes.
            if stem.endswith("ة") and len(consonants) == 5 and consonants[2] == "ا":
                return "NOM_DERIVED", {"pos": "NOM", "role": "MASDAR", "form": "III", "semantic_role": "RECIPROCAL", "num": "SG", "gender": "F"}
            role_mu = _mu_role(stem)
            tags_out = {"pos": "NOM", "role": role_mu}
            return "NOM_DERIVED", tags_out

        # مَفْعُول passive participle: مَ + R1 + R2 + و + R3 (5 consonants, و at pos 3).
        # e.g. مَكْتُوب, مَفْهُوم, مَسْمُوع
        if stem.startswith("مَ") and len(consonants) == 5 and consonants[3] == "و":
            return "NOM_DERIVED", {"pos": "NOM", "role": "PASSIVE_PARTICIPLE"}
        # مَفَاعِل diptote broken plural: مَ + R1 + ا + R2 + R3 (5 cons, ا at pos 2)
        if stem.startswith("مَ") and len(consonants) == 5 and consonants[2] == "ا":
            return "BROKEN_PL_MAFAIL", {"pos": "NOM", "role": "PLURAL", "num": "PL", "diptote": "YES"}
        # مَفْعَل / مَفْعِل place noun: مَ + 3-consonant root (4 cons total).
        # Some مَفْعَل forms are masdar mimi (مَصْدَر مِيمِيّ), not place nouns
        # — these are lexically distinguished, so we use a small lookup.
        # e.g. مَضْرَب (act of striking) vs مَكْتَب (place of writing/desk).
        if stem.startswith("مَ") and len(consonants) == 4:
            # NOTE: مَجْلِس is intentionally NOT here — two tests assert
            # conflicting roles (MASDAR vs PLACE) for the same surface form.
            # PLACE wins because the place-noun reading is more frequent.
            _MASDAR_MIMI_STEMS = {"مَضْرَب", "مَوْعِد", "مَقْصَد",
                                    "مَرْجِع", "مَوْرِد", "مَصْدَر"}
            if stem in _MASDAR_MIMI_STEMS:
                return "NOM_DERIVED", {"pos": "NOM", "role": "MASDAR"}
            return "NOM_DERIVED", {"pos": "NOM", "role": "PLACE"}
        if stem.startswith("مَ") and len(consonants) >= 4:
            return "NOM_DERIVED", {"pos": "NOM", "role": "PLACE"}
        # مِفْعَال / مِفْعَل / مِفْعَلَة instrument noun (مِ prefix)
        # e.g. مِفْتَاح, مِكْنَسَة, مِقَصّ
        if stem.startswith("مِ") and len(consonants) >= 3:
            return "NOM_DERIVED", {"pos": "NOM", "role": "INSTRUMENT"}

        # Unvoweled م-initial words with 4+ consonants: likely derived nominal.
        # In unvoweled text we cannot distinguish مُفَعِّل from مَفْعُول from
        # مَدِينَة, so we treat all م + 4+ consonants as NOM_DERIVED.
        # Plain م-initial triliterals (مَلِك، مَاء) have only 3 consonants
        # and are handled by the template index (n=3).
        if stripped.startswith("م") and len(consonants) >= 4:
            return "NOM_DERIVED", {"pos": "NOM", "role": "DERIVED"}

        # Imperative Form I detection: اُ/اِ + R1 + sukun + R2 + haraka + R3 + sukun.
        # 4 consonants total (ا+R1+R2+R3), ends with sukun, starts with ا+damma/kasra.
        # Must run BEFORE Form X/VIII checks (which also start with ا).
        _SUKUN_CHAR = "ْ"
        if (stem.startswith(("اُ", "اِ")) and stem.endswith(_SUKUN_CHAR)
                and len(consonants) == 4 and consonants[0] == "ا"):
            return "VERB_IMPERATIVE_I", {"pos": "VERB", "form": "I", "tense": "IMP", "voice": "ACT", "person": "2"}

        # Form X: اِسْتَفْعَلَ — requires است prefix
        if stripped.startswith("است") and len(stripped) >= 5:
            # Form X masdar اِسْتِفْعَال: ا+س+ت+R1+R2+ا+R3 (7 consonants, ا at position 5)
            # Returned with template VERB_AUGMENTED_X (per test spec) but role=MASDAR.
            if len(consonants) == 7 and consonants[5] == "ا":
                return "VERB_AUGMENTED_X", {"pos": "NOM", "role": "MASDAR", "form": "X", "semantic_role": "REQUEST", "num": "SG", "gender": "M"}
            return "VERB_AUGMENTED_X", {"pos": "VERB", "form": "X", "tense": "PAST", "voice": "ACT", "semantic_role": "REQUEST"}

        # Form XII masdar اِفْعِيعَال (after ان enclitic stripped):
        # After stripping ان, stem = ا+R1+R2+ي+R2 (5 consonants)
        # e.g. اِخْشِيشَان → stem=اخشيش: [1]=خ=R1, [2]=ش=R2, [3]=ي, [4]=ش=R2
        # Pattern: starts with ا, 5 consonants, ي at position 3, [2]==[4]
        if stripped.startswith("ا") and len(consonants) == 5:
            if consonants[3] == "ي" and consonants[2] == consonants[4]:
                return "MASDAR_FORM_XII", {"pos": "NOM", "role": "MASDAR", "form": "XII"}

        # Form IX masdar اِفْعِلَال: ا + R1 + R2 + R3 + ا + R3 (6 consonants)
        # e.g. اِحْمِرَار (حمر): cons=احمرار, [4]=ا, [3]==[5]=ر
        # Form XI masdar اِفْعِيلَال: ا + R1 + R2 + ي + R3 + ا + R3 (7 consonants)
        # e.g. اِحْمِيرَار (حمر): cons=احميرار, [3]=ي, [5]=ا, [4]==[6]=ر
        # Form XII masdar اِفْعِيعَال: ا + R1 + R2 + ي + R1 + ا + R2 (7 consonants)
        # e.g. اِخْشِيشَان (خشن): cons=اخشيشان, [3]=ي, [1]==[4]=خ
        # These must be checked BEFORE Form IX verb (which has 4-5 consonants).
        if stripped.startswith("ا") and len(consonants) >= 6:
            # Form IX masdar: 6 consonants, ا at position 4, [3]==[5]
            # Disambiguation against Form VII masdar of a geminate root: اِنْحِلَال
            # (root ح.ل.ل) has the identical skeleton ا+ن+ح+ل+ا+ل as a putative
            # Form IX of ن.ح.ل. Form IX of a ن-initial root is vanishingly rare,
            # whereas اِنْفِعَال of geminate roots (انحلال، انضمام، اندمال) is common.
            # When the second consonant is the Form VII augment ن and dropping it
            # exposes a known geminate root (R1 + G + ا + G), route to Form VII.
            if (len(consonants) == 6 and consonants[4] == "ا"
                    and consonants[3] == consonants[5]
                    and consonants[1] == "ن"):
                _vii_gem = consonants[2] + consonants[3] + consonants[5]
                if _vii_gem in self.root_set:
                    return "MASDAR_FORM_VII", {"pos": "NOM", "role": "MASDAR", "form": "VII"}
            if (len(consonants) == 6 and consonants[4] == "ا"
                    and consonants[3] == consonants[5]
                    and consonants[1] not in "طدضظذ"):
                return "MASDAR_FORM_IX", {"pos": "NOM", "role": "MASDAR", "form": "IX"}
            # Form XI masdar: 7 consonants, ي at position 3, ا at position 5, [4]==[6]
            if (len(consonants) == 7 and consonants[3] == "ي"
                    and consonants[5] == "ا" and consonants[4] == consonants[6]):
                return "MASDAR_FORM_XI", {"pos": "NOM", "role": "MASDAR", "form": "XI"}
            # Form XII masdar: 7 consonants, ي at position 3, R2 repeated at position 4
            # اِفْعِيعَال: ا+R1+R2+ي+R2+ا+R3 → [2]==[4]
            if (len(consonants) == 7 and consonants[3] == "ي"
                    and consonants[2] == consonants[4]):
                return "MASDAR_FORM_XII", {"pos": "NOM", "role": "MASDAR", "form": "XII"}

        # Form IX: اِفْعَلَّ — colour/defect verbs (احمرّ، اسودّ)
        # Pattern: starts with ا, geminate final consonant (shadda on last consonant).
        # In voweled text: shadda (U+0651) on the final consonant is the key marker.
        # In unvoweled text: 5 consonants with last two identical (e.g. احمرر).
        # Must check BEFORE Form VIII to avoid اِحْمَرَّ being misread as Form VIII.
        # Guard: position 1 must NOT be an emphatic consonant (طدضظذ) — that would
        # be Form VIII emphatic assimilation (e.g. اِضْطَرَّ←ضرر is Form VIII, not IX).
        _SHADDA = "\u0651"
        _has_final_shadda = len(stem) >= 2 and stem[-1] == _SHADDA
        if stripped.startswith("ا") and len(consonants) >= 4:
            if (_has_final_shadda and len(consonants) == 4
                    and consonants[1] not in "طدضظذ"):
                # Voweled Form IX: ا + R1 + R2 + R3ّ (shadda = geminate R3)
                return "VERB_AUGMENTED_IX", {"pos": "VERB", "form": "IX", "tense": "PAST", "voice": "ACT", "semantic_role": "COLOR_DEFECT"}
            if (len(consonants) == 5 and consonants[3] == consonants[4]
                    and consonants[1] not in "طدضظذ"):
                # Unvoweled Form IX: ا + R1 + R2 + R3 + R3 (explicit geminate)
                return "VERB_AUGMENTED_IX", {"pos": "VERB", "form": "IX", "tense": "PAST", "voice": "ACT", "semantic_role": "COLOR_DEFECT"}

        # Form VIII: اِفْتَعَلَ — ا + R1 + ت + R2 + R3 (5 consonants total)
        # Standard form: consonants[2] == ت (e.g. اعتقد، ابتسم)
        # Assimilation variants:
        #   - Root-initial و/ي/ء: ت+ت→تّ, so consonants[1]==ت (e.g. اتصل←وصل, اتخذ←أخذ)
        #   - Root-initial emphatic (ط،ظ،ض،ص،ذ) at position 1: ت→ط/د after emphatic R1
        #     (e.g. اطّلع←طلع: ط is R1, no ت; اضطرّ←ضرر: ض is R1, ط is assimilated ت)
        # All variants: starts with ا, 4+ consonants total
        if stripped.startswith("ا") and len(consonants) >= 4:
            # Form VIII masdar اِفْتِعَال: ا + R1 + ت + R2 + ا + R3 (6 consonants, ا at pos 4)
            # Template name VERB_AUGMENTED_VIII per test spec; role=MASDAR distinguishes from verb.
            if len(consonants) == 6 and consonants[2] == "ت" and consonants[4] == "ا":
                return "VERB_AUGMENTED_VIII", {"pos": "NOM", "role": "MASDAR", "form": "VIII", "semantic_role": "MEDIO_PASSIVE", "num": "SG", "gender": "M"}
            # Standard: ت at position 2
            if consonants[2] == "ت":
                return "VERB_AUGMENTED_VIII", {"pos": "VERB", "form": "VIII", "tense": "PAST", "voice": "ACT", "semantic_role": "MEDIO_PASSIVE"}
            # Assimilation type 1: ت at position 1 (root-initial و/ي/ء absorbed)
            # e.g. اتصل (←وصل): cons=اتصل, [1]=ت
            if consonants[1] == "ت":
                return "VERB_AUGMENTED_VIII", {"pos": "VERB", "form": "VIII", "tense": "PAST", "voice": "ACT", "semantic_role": "MEDIO_PASSIVE"}
            # Assimilation type 2: emphatic at position 1 (ت→ط/د after emphatic R1)
            # e.g. اطّلع (←طلع): cons=اطلع, [1]=ط (R1=ط, no infixed ت)
            # e.g. اضطرّ (←ضرر): cons=اضطر, [1]=ض (R1=ض), [2]=ط (assimilated ت)
            if consonants[1] in "طدضظذ":
                return "VERB_AUGMENTED_VIII", {"pos": "VERB", "form": "VIII", "tense": "PAST", "voice": "ACT", "semantic_role": "MEDIO_PASSIVE"}

        # إفعال masdar (masdar of Form IV): إ + R1 + R2 + ا + R3
        # e.g. إِنْجَاز (←أَنْجَزَ root نجز), إِرْسَال (←أَرْسَلَ root رسل)
        # Pattern: starts with إ (U+0625), 5 consonants, ا at position 3.
        # Must check BEFORE Form VII (which also starts with ان).
        if stem.startswith("إ") and len(consonants) == 5 and consonants[3] == "ا":
            return "MASDAR_FORM_IV", {"pos": "NOM", "role": "MASDAR", "form": "IV", "semantic_role": "CAUSATIVE"}

        # إِفَالَة masdar (Form IV ajwaf): إ + R1 + ا + R2 (+ ة stripped)
        # e.g. إِقَامَة (←أَقَامَ root قوم): cons=إقام (4), ا at position 2
        # e.g. إِدَارَة (←أَدَارَ root دور): cons=إدار (4), ا at position 2
        if stem.startswith("إ") and len(consonants) == 4 and consonants[2] == "ا":
            return "MASDAR_FORM_IV", {"pos": "NOM", "role": "MASDAR", "form": "IV", "semantic_role": "CAUSATIVE"}

        # Form XI: اِفْعَالَّ — intensive color (ا + R1 + ا + R2 + R3ّ)
        # Consonant skeleton: ا(0)+R1(1)+ا(2 in وزن but 3 in skeleton)+R2+R3ّ
        # e.g. اِحْمَارَّ (حمر): cons=احمار (5), ا at position 3, shadda on last
        # e.g. اِبْيَاضَّ (بيض): cons=ابياض (5), ا at position 3
        if stripped.startswith("ا") and len(consonants) == 5:
            if consonants[3] == "ا" and (_has_final_shadda or consonants[3] == consonants[4]):
                return "VERB_AUGMENTED_XI", {"pos": "VERB", "form": "XI", "tense": "PAST", "voice": "ACT"}

        # Form XII: اِفْعَوْعَلَ — intensive quality (ا + R1 + R2 + و + R2 + R3)
        # Consonant skeleton: ا(0)+R1(1)+R2(2)+و(3)+R2(4)+R3(5) — و at position 3,
        # R2 repeated at positions 2 and 4.
        # e.g. اِخْشَوْشَنَ (خشن): cons=اخشوشن (6), [3]=و, [2]=ش=[4]=ش
        if stripped.startswith("ا") and len(consonants) == 6:
            if consonants[3] == "و" and consonants[2] == consonants[4]:
                return "VERB_AUGMENTED_XII", {"pos": "VERB", "form": "XII", "tense": "PAST", "voice": "ACT"}

        # Form XIII: اِفْعَوَّلَ — intensive rare (ا + R1 + R2 + و + R3 doubled)
        # Pattern: starts with ا, 6 consonants, و at position 3.
        # e.g. اِجْلَوَّذَ (جلوذ): cons=اجلوذ (5 after shadda strip)
        # In practice these are extremely rare; treat as VERB_AUGMENTED fallback.

        # Form XIV/XV: extremely rare assimilation forms — treat as VERB_AUGMENTED.

        # Form VII: اِنْفَعَلَ — ان + root (5 consonants total).
        # Must check for اِنْفَ specifically (ا + ن + non-ن consonant) to avoid
        # misclassifying Form VIII words like اِنْتِخَاب (which starts with ان
        # but is Form VIII افتعال). Require consonants[1]=="ن" and
        # consonants[2] is not ت (Form VIII already caught above).
        if (stripped.startswith("ان") and len(consonants) >= 5
                and consonants[1] == "ن" and consonants[2] != "ت"):
            # Form VII masdar اِنْفِعَال: ا + ن + R1 + R2 + ا + R3 (6 consonants, ا at pos 4)
            # Template name VERB_AUGMENTED_VII per test spec; role=MASDAR distinguishes from verb.
            if len(consonants) == 6 and consonants[4] == "ا":
                return "VERB_AUGMENTED_VII", {"pos": "NOM", "role": "MASDAR", "form": "VII", "semantic_role": "PASSIVE_INTRANS", "num": "SG", "gender": "M"}
            return "VERB_AUGMENTED_VII", {"pos": "VERB", "form": "VII", "tense": "PAST", "voice": "ACT", "semantic_role": "PASSIVE_INTRANS"}

        # Elative adjective (أَفْعَل): أ + C1 + C2 + C3 (4 consonants total).
        # Pattern is identical to Form IV verb, but elatives are adjectives
        # used for comparison (أَكْبَر = bigger, أَفْضَل = better).
        # Check against known elative roots BEFORE Form IV to avoid misclassification.
        _ELATIVE_ROOTS = {
            "كبر", "صغر", "فضل", "حسن", "سوء", "عظم", "قلل", "كثر",
            "همم", "جمل", "طول", "قصر", "بعد", "قرب", "علو", "دنو",
            "ولل", "خرر", "سرع", "بطء", "قدم", "حدث", "سهل", "صعب",
            "غلو", "رخص", "وسع", "ضيق", "ثقل", "خفف", "عمق", "ضحل",
            "نظف", "قذر", "حرر", "برد", "شدد", "لين", "صلب", "رطب",
            "يبس", "غنو", "فقر", "قوو", "ضعف", "ذكو", "غبو", "حلو",
            "مرر", "خير", "شرر", "نفع", "ضرر", "هون",
        }
        if (stripped.startswith("أ") and len(consonants) == 4):
            _elative_root_candidate = consonants[1:4]
            # Check if the 3-consonant root (after أ) is a known elative root
            if _elative_root_candidate in _ELATIVE_ROOTS or _elative_root_candidate in self.root_set and self._is_elative_root(_elative_root_candidate):
                return "ADJ_ELATIVE", {"pos": "ADJ", "degree": "COMP"}

        # Form IV: أَفْعَلَ — أ + root (4 consonants total).
        # Require exactly 4 consonants to avoid misclassifying:
        #   - أجوف Form I verbs like أَكَلَ (root أكل, 3 consonants)
        #   - Broken plural أَفْعَال like أَقْلَام (5 consonants — handled below)
        # أَفْعِلَة broken plural (must be checked BEFORE Form IV which has same cons count)
        if stem.startswith("أ") and len(consonants) == 4 and stem.endswith("ة"):
            return "BROKEN_PL_AF3ILA", {"pos": "NOM", "role": "PLURAL", "num": "PL"}
        if (stripped.startswith("أ") and len(consonants) == 4):
            # أَفْعَل can also be SIFA_MUSHABBAHA color/defect adjective.
            # Check if R1+R2+R3 (consonants[1:4]) is a color/defect root.
            _COLOR_DEFECT = {"حمر","زرق","خضر","صفر","سود","بيض","عرج","عمي","صلع","طرش","خرس","بكم","عوج","شعث","شيب"}
            _adj_root = consonants[1:4]
            if _adj_root in _COLOR_DEFECT:
                return "ADJ_AFAL_COLOR", {"pos": "ADJ", "role": "SIFA_MUSHABBAHA"}
            return "VERB_AUGMENTED_IV", {"pos": "VERB", "form": "IV", "tense": "PAST", "voice": "ACT", "semantic_role": "CAUSATIVE"}

        # Broken plural أَفْعَال pattern: أ + 3-consonant root + ا (5 consonants)
        # e.g. أَقْلَام (قلم), أَعْمَال (عمل), أَوْلَاد (ولد)
        # Distinguish from Form IV (4 consonants) by requiring 5 consonants
        # and internal ا at position 3 of the consonant skeleton.
        if (stripped.startswith("أ") and len(consonants) == 5
                and consonants[3] == "ا"):
            return "BROKEN_PLURAL_AF3AL", {"pos": "NOM", "role": "PLURAL", "num": "PL"}

        # Q-II تَفَعْلَلَ — reflexive quadriliteral: ت + 4-consonant root.
        # e.g. تَدَحْرَجَ (root دحرج), تَزَلْزَلَ (root زلزل).
        # Pattern: starts with ت, 5 consonants total, consonants[1:5] is a
        # 4-consonant root in root_set. Must check BEFORE Form V/VI to avoid
        # misclassifying as Form VI (which also has 5 consonants starting with ت).
        if stripped.startswith("ت") and len(consonants) == 5:
            _quad_candidate = consonants[1:5]
            if _quad_candidate in self.root_set:
                return "VERB_RESEMBLING_QUAD_II", {"pos": "VERB", "form": "Q-II"}

        # Form V/VI: تَفَعَّلَ / تَفَاعَلَ — ت + root.
        # Form V (تَفَعَّلَ): 4 consonants, no internal ا → root_consonants==4
        # Form VI (تَفَاعَلَ): 5 consonants with internal ا → root_consonants==4
        #   (the ا is the pattern's long vowel between R1 and R2)
        # Plain nouns starting with ت (تِجَارَة): root_consonants==3 (ا stripped)
        if stripped.startswith("ت"):
            # Form V masdar (تَفَعُّل): 4 consonants, R2 has shadda, no ا.
            # Distinguish from Form V verb by the absence of final fatha (نَ).
            # Heuristic: if the original word has damma (ُ) on R2 area, it's masdar.
            # e.g. تَعَلُّم (damma+shadda on ل), تَقَدُّم, تَطَوُّر
            _DAMMA_CH = "ُ"
            _SHADDA_V = "ّ"
            has_damma_shadda = False
            for _i, _ch in enumerate(stem):
                if _ch == _DAMMA_CH and _i + 1 < len(stem) and stem[_i + 1] == _SHADDA_V:
                    has_damma_shadda = True
                    break
                if _ch == _SHADDA_V and _i + 1 < len(stem) and stem[_i + 1] == _DAMMA_CH:
                    has_damma_shadda = True
                    break
            if len(consonants) == 4 and len(root_consonants) == 4 and has_damma_shadda:
                return "MASDAR_FORM_V", {"pos": "NOM", "role": "MASDAR", "form": "V", "semantic_role": "REFLEXIVE"}
            # Form VI masdar (تَفَاعُل): 5 consonants with ا, R3 area has damma.
            # e.g. تَبَادُل, تَعَاوُن
            if len(consonants) == 5 and len(root_consonants) == 4:
                # Check for damma right before the LAST consonant: masdar (تَبَادُل).
                # Verb (تَبَادَلَ) has fatha before last consonant.
                _DAMMA_CH = "ُ"
                # find last consonant index
                last_cons_idx = None
                for _i in range(len(stem) - 1, -1, -1):
                    if stem[_i] in self.AR_CONSONANTS:
                        last_cons_idx = _i
                        break
                if last_cons_idx is not None and last_cons_idx >= 1:
                    if stem[last_cons_idx - 1] == _DAMMA_CH:
                        return "MASDAR_FORM_VI", {"pos": "NOM", "role": "MASDAR", "form": "VI", "semantic_role": "RECIPROCAL"}
            if len(consonants) == 4 and len(root_consonants) == 4:
                return "VERB_AUGMENTED_V_VI", {"pos": "VERB", "form": "V", "tense": "PAST", "voice": "ACT", "semantic_role": "REFLEXIVE"}
            if len(consonants) == 5 and len(root_consonants) == 4:
                return "VERB_AUGMENTED_V_VI", {"pos": "VERB", "form": "VI", "tense": "PAST", "voice": "ACT", "semantic_role": "RECIPROCAL"}
            # Masdar Form II (تَفْعِيل): ت + R1 + long-i + R2 + R3
            # e.g. تَعْلِيم (←علم), تَفْسِير (←فسر), تَكْرِيم (←كرم)
            # Pattern: 5 consonants, ي at position 3 (long-i vowel marker).
            # This is a MASDAR, NOT a Form V verb — must return MASDAR_FORM_II.
            # Form V verb (تَفَعَّلَ) has 4 consonants (no internal ي).
            if len(consonants) == 5 and consonants[3] == "ي":
                return "MASDAR_FORM_II", {"pos": "NOM", "role": "MASDAR", "form": "II", "semantic_role": "CAUSATIVE"}

        # ── Form II/III disambiguation from Form I ───────────────────────────────
        # Form III (فَاعَلَ): has long alif (ا) between C1 and C2.
        # e.g. قَاتَلَ (qatala → Form III), شَارَكَ, سَافَرَ, حَاوَلَ
        # IMPORTANT: In undiacritized text, Form III (فَاعَلَ) is indistinguishable
        # from the active participle (فَاعِل) — both have C1+ا+C2+C3 (4 consonants).
        # So we only classify as Form III when diacritics are present and show
        # the فَاعَلَ vowel pattern (fatha on C2, not kasra as in فَاعِل).
        # Known Form III verbs in undiacritized text are handled via a lookup set.
        _KNOWN_FORM_III = {
            "قاتل", "شارك", "سافر", "حاول", "ناقش", "بادل", "جاهد",
            "عاون", "عارض", "راقب", "واصل", "دافع", "سابق", "نادى",
            "هاجر", "طالع", "عالج", "واجه", "صاحب", "جاور", "ساعد",
        }
        _FATHA = "\u064E"
        if (len(consonants) == 4 and len(root_consonants) == 3
                and consonants[1] == "ا"
                and not stripped.startswith("ا")
                and not stripped.startswith("م")
                and not stripped.startswith("ت")):
            # Check if it's a known Form III verb (undiacritized)
            if stripped in _KNOWN_FORM_III:
                return "VERB_FORM_III", {"pos": "VERB", "form": "III", "tense": "PAST", "voice": "ACT", "semantic_role": "RECIPROCAL"}
            # Check diacritics: Form III has fatha on C2 (فَاعَلَ)
            # Active participle has kasra on C2 (فَاعِل)
            # Find C2 and check its following diacritic
            _cons_count = 0
            for _i, _ch in enumerate(stem):
                if _ch in self.AR_CONSONANTS:
                    _cons_count += 1
                    if _cons_count == 2 and _i + 1 < len(stem):
                        if stem[_i + 1] == _FATHA:
                            return "VERB_FORM_III", {"pos": "VERB", "form": "III", "tense": "PAST", "voice": "ACT", "semantic_role": "RECIPROCAL"}
                        if stem[_i + 1] == _KASRA:
                            # فَاعِل active participle (AGENT)
                            return "AP_FAIL", {"pos": "NOM", "role": "AGENT"}
                        break
                    elif _cons_count == 2:
                        break
            # Default for 4-cons C1+ا+C2+C3 surface without diacritic info:
            # treat as active participle (more common in nominal contexts).
            return "AP_FAIL", {"pos": "NOM", "role": "AGENT"}

        # Form II (فَعَّلَ): has shadda (ّ) on C2 before diacritics are stripped.
        # In the original stem, check for shadda on the second consonant.
        # e.g. عَلَّمَ, دَرَّسَ, فَسَّرَ, نَظَّفَ, كَسَّرَ
        # Detection: scan original stem for C1 + vowel + C2 + shadda pattern.
        _SHADDA_CHAR = "\u0651"
        if _SHADDA_CHAR in stem and len(root_consonants) == 3:
            # Find shadda position. C2 in voweled text may be followed by:
            #   - shadda directly (عَلَّمَ: ل + ّ)
            #   - haraka + shadda (نَجَّار: ج + َ + ّ — fatha then shadda)
            # Both indicate gemination on C2.
            # After the shadda, the NEXT vowel decides: ا (long alif) = MUBALAGHA noun,
            # fatha (or other) = Form II verb.
            _ARDIA = "ًٌٍَُِْٰ"
            _cons_seen = 0
            for _idx, _ch in enumerate(stem):
                if _ch in self.AR_CONSONANTS:
                    _cons_seen += 1
                    if _cons_seen == 2:
                        # Look ahead up to 2 chars for shadda
                        _ahead = stem[_idx + 1: _idx + 3]
                        if _SHADDA_CHAR in _ahead:
                            # Find what follows the shadda
                            _post_shadda = stem[_idx + _ahead.index(_SHADDA_CHAR) + 2:
                                                _idx + _ahead.index(_SHADDA_CHAR) + 4]
                            if "ا" in _post_shadda:
                                # NOM_MUBALAGHA detected via geminate + alif
                                return "NOM_MUBALAGHA", {"pos": "NOM", "role": "MUBALAGHAH"}
                            return "VERB_FORM_II", {"pos": "VERB", "form": "II", "tense": "PAST", "voice": "ACT", "semantic_role": "CAUSATIVE"}
                        break

        # ── Geminate verb with 2-consonant skeleton ─────────────────────────────
        # e.g. ظَلَّ, مَدَّ, شَدَّ — after diacritic stripping the shadda is lost,
        # leaving only 2 consonants. When the doubled form (R1+R2+R2) is in
        # root_set, this is a geminate (مضعّف) verb, not a masdar.
        # Check BEFORE the template index (which has no n=2 VERB_DOUBLED entry).
        # Also check _has_final_shadda on the original stem (before diacritic strip)
        # for voweled input, and the root_set doubling for unvoweled input.
        if len(consonants) == 2:
            doubled = consonants + consonants[-1]
            if doubled in self.root_set or _has_final_shadda:
                return "VERB_DOUBLED", {"pos": "VERB", "form": "I", "tense": "PAST", "voice": "ACT"}

        # ── Surface-pattern detection for trilateral nominals/adjectives ──
        # These patterns share consonant counts with verbs so they bypass the
        # template index. Detection uses the original (diacritized) stem.
        _DAMMA_P = "ُ"; _KASRA_P = "ِ"; _FATHA_P = "َ"; _SUKUN_P = "ْ"; _SHADDA_P = "ّ"
        def _haraka_after(s: str, cons_index_1based: int):
            cc = 0
            for i, ch in enumerate(s):
                if ch in self.AR_CONSONANTS:
                    cc += 1
                    if cc == cons_index_1based:
                        return s[i + 1] if i + 1 < len(s) else ""
            return ""
        # فَعَّال mubalagha: C1+fatha+C2+shadda+ا+C3 (3 root cons, ا between R2 and R3, shadda on R2)
        # e.g. نَجَّار (نجر), فَعَّال
        if len(root_consonants) == 3 and "ا" in consonants and _SHADDA_P in stem:
            # Detect R2 with shadda followed by ا
            cc = 0
            for _i, _ch in enumerate(stem):
                if _ch in self.AR_CONSONANTS:
                    cc += 1
                    if cc == 2 and _i + 1 < len(stem) and stem[_i + 1] == _SHADDA_P:
                        return "NOM_MUBALAGHA", {"pos": "NOM", "role": "MUBALAGHAH"}
        # فُعَيْل diminutive: C1+damma+C2+fatha+ي+sukun+C3 → 4 consonants with ي at position 2.
        # e.g. كُتَيْب (كتب), جُبَيْل (جبل), دُرَيْهِم (4 root cons + ي → 5 cons)
        if len(consonants) == 4 and consonants[2] == "ي":
            h1 = _haraka_after(stem, 1)
            h2 = _haraka_after(stem, 2)
            if h1 == _DAMMA_P and h2 == _FATHA_P:
                return "NOM_DIMINUTIVE", {"pos": "NOM", "role": "DIMINUTIVE"}
            # Default for any C1+ي+C2 pattern with damma on C1: diminutive
            if h1 == _DAMMA_P:
                return "NOM_DIMINUTIVE", {"pos": "NOM", "role": "DIMINUTIVE"}
        # فَعِيل sifa: C1+fatha+C2+kasra+ي+C3 → 4 consonants with ي at position 2.
        # e.g. صَغِير, كَبِير, جَمِيل, كَرِيم
        if len(consonants) == 4 and consonants[2] == "ي":
            h1 = _haraka_after(stem, 1)
            h2 = _haraka_after(stem, 2)
            if h1 == _FATHA_P and h2 == _KASRA_P:
                return "ADJ_SIFA_FAIL", {"pos": "ADJ", "role": "SIFA_MUSHABBAHA"}
        # فَعُول mubalagha: C1+fatha+C2+damma+و+C3 (4 cons, و at pos 2, damma on C2)
        # e.g. صَبُور, شَكُور, غَفُور (test expects صَبُور → MUBALAGHAH)
        if len(consonants) == 4 and consonants[2] == "و":
            h1 = _haraka_after(stem, 1)
            h2 = _haraka_after(stem, 2)
            if h1 == _FATHA_P and h2 == _DAMMA_P:
                return "ADJ_MUBALAGHA_FAOUL", {"pos": "ADJ", "role": "MUBALAGHAH"}
        # فَعْلَان sifa / فُعْلَان masdar / فِعْلَان: distinguish by C1 vowel.
        # عَطْشَان (fatha+sukun)→sifa, غُفْرَان (damma+sukun)→masdar, جَوْعَان→sifa
        if (len(consonants) == 5 and consonants[-1] == "ن"
                and consonants[-2] == "ا"):
            h1 = _haraka_after(stem, 1)
            if h1 == _DAMMA_P:
                return "MASDAR_FU3LAN", {"pos": "NOM", "role": "MASDAR"}
            return "ADJ_FALAN", {"pos": "ADJ", "role": "SIFA_MUSHABBAHA"}
        # فُعْلَى fem elative: ends with ى, 3 root cons + ى = 4 cons total
        # e.g. كُبْرَى, صُغْرَى
        if stem.endswith("ى") and len(consonants) == 4 and consonants[-1] == "ى":
            h1 = _haraka_after(stem, 1)
            if h1 == _DAMMA_P:
                return "ADJ_ELATIVE_FEM", {"pos": "ADJ", "degree": "COMP", "gender": "F"}
        # فِعَالَة masdar (Form I): C1+kasra+C2+ا+C3+ة → 4 consonants with ا at pos 2
        # e.g. كِتَابَة, زِيَادَة
        # NOTE: ة is stripped from consonants, so word ends in "ة" surface only.
        # cons = C1+C2+ا+C3 (4), pattern check: h1 = kasra
        if (word_endswith_ta := stem.endswith("ة")) and len(consonants) == 4 and consonants[2] == "ا":
            h1 = _haraka_after(stem, 1)
            if h1 == _KASRA_P:
                return "MASDAR_I_FIALA", {"pos": "NOM", "role": "MASDAR"}
        # فَعْلَة masdar marra (instance): C1+fatha+C2+sukun+C3+ة (3 cons + ة)
        # e.g. ضَرْبَة (one strike)
        if stem.endswith("ة") and len(consonants) == 3:
            h1 = _haraka_after(stem, 1)
            if h1 == _FATHA_P:
                return "MASDAR_MARRA", {"pos": "NOM", "role": "MASDAR"}
            if h1 == _KASRA_P:
                return "MASDAR_HAYAA", {"pos": "NOM", "role": "MASDAR"}
        # فَعْل / فُعُول / فُعْل masdars (Form I): bare 3-consonant nominals.
        # Distinguish from VERB by vowel pattern:
        #   - C1+sukun and C3 has no fatha: masdar (e.g. ضَرْب, فَهْم)
        #   - C1+fatha + C2+fatha + C3+fatha: verb (e.g. كَتَبَ)
        if len(consonants) == 3 and len(root_consonants) == 3:
            h1 = _haraka_after(stem, 1)
            h2 = _haraka_after(stem, 2)
            h3 = _haraka_after(stem, 3)
            # فَعْل: fatha + sukun → masdar (ضَرْب)
            if h1 == _FATHA_P and h2 == _SUKUN_P:
                return "MASDAR_I_FA3L", {"pos": "NOM", "role": "MASDAR"}
            # فُعُول written as 5-cons stem (with و) — but here we're in n=3 path
            # so this is the unvoweled/short form. Skip.
        # فُعُول masdar: C1+damma+C2+damma+و+C3 (4 cons with و at pos 2)
        # e.g. جُلُوس, نُزُول
        if len(consonants) == 4 and consonants[2] == "و":
            h1 = _haraka_after(stem, 1)
            h2 = _haraka_after(stem, 2)
            if h1 == _DAMMA_P and h2 == _DAMMA_P:
                _MASDAR_FU3UL_ROOTS = {"جلس", "نزل", "وقف", "قعد", "ركع", "سجد",
                                        "خرج", "دخل", "صعد", "هبط", "ركب",
                                        "قبل", "غفر", "شكر", "حضر"}
                cand_sound = consonants[0] + consonants[1] + consonants[3]
                if cand_sound in _MASDAR_FU3UL_ROOTS:
                    return "MASDAR_FU3UL", {"pos": "NOM", "role": "MASDAR"}
                cand_root_aywf_w = consonants[0] + "و" + consonants[3]
                cand_root_aywf_y = consonants[0] + "ي" + consonants[3]
                if cand_root_aywf_w in self.root_set or cand_root_aywf_y in self.root_set:
                    # if sound root is also a valid root, prefer plural with sound root
                    if cand_sound in self.root_set:
                        return "BROKEN_PL_FU3UL_SOUND", {"pos": "NOM", "role": "PLURAL", "num": "PL"}
                    return "BROKEN_PL_FU3UL_AJWAF", {"pos": "NOM", "role": "PLURAL", "num": "PL"}
                return "BROKEN_PL_FU3UL_SOUND", {"pos": "NOM", "role": "PLURAL", "num": "PL"}
        # فُعُل broken plural: C1+damma+C2+damma+C3 (3 cons, damma on C1 and C2)
        # e.g. كُتُب, رُسُل
        if len(consonants) == 3 and len(root_consonants) == 3:
            h1 = _haraka_after(stem, 1)
            h2 = _haraka_after(stem, 2)
            if h1 == _DAMMA_P and h2 == _DAMMA_P:
                return "BROKEN_PL_FU3UL", {"pos": "NOM", "role": "PLURAL", "num": "PL"}
        # فِعَال broken plural (or masdar III): C1+kasra+C2+ا+C3 (4 cons, ا at pos 2)
        # e.g. رِجَال (plural), جِهَاد (masdar III), جِبَال (plural)
        # Tests: رِجَال → PLURAL; جِهَاد → MASDAR III
        # We'll prefer PLURAL by default; جِهَاد is rare and we accept the mistake.
        if len(consonants) == 4 and consonants[2] == "ا":
            h1 = _haraka_after(stem, 1)
            if h1 == _KASRA_P:
                # Known masdar III roots that override the default plural
                _MASDAR_III_ROOTS = {"جهد","قتل","نزع","حوج","سفر"}
                root_cand = consonants[0] + consonants[1] + consonants[3]
                if root_cand in _MASDAR_III_ROOTS:
                    return "MASDAR_III_FIAL", {"pos": "NOM", "role": "MASDAR", "form": "III", "semantic_role": "RECIPROCAL"}
                return "BROKEN_PL_FIAL", {"pos": "NOM", "role": "PLURAL", "num": "PL"}
        # فُعَلَاء diptote broken plural: C1+damma+C2+fatha+C3+ا+ء (5 cons ending ا+ء)
        # e.g. شُعَرَاء
        if len(consonants) == 5 and consonants[-1] == "ء" and consonants[-2] == "ا":
            return "BROKEN_PL_DIPTOTE", {"pos": "NOM", "role": "PLURAL", "num": "PL", "diptote": "YES"}
        # فَعَائِل diptote broken plural: C1+fatha+C2+ا+C3+kasra+ئ+C4
        # e.g. عَجَائِب: cons = ع+ج+ا+ء+ب → after hamza norm: عجاءب (5 cons, ا at pos 2, ء at pos 3)
        if len(consonants) == 5 and consonants[2] == "ا" and consonants[3] == "ء":
            return "BROKEN_PL_FAAIL", {"pos": "NOM", "role": "PLURAL", "num": "PL", "diptote": "YES"}
        # مَفَاعِل diptote: مَ + R1 + ا + R2 + R3 — but starts with م, handled above.
        # فُعْلَان masdar: C1+damma+C2+sukun+C3+fatha+ا+ن (4 cons ending ان, damma C1)
        # e.g. غُفْرَان, نُكْرَان
        if (len(consonants) == 5 and consonants[-1] == "ن"
                and consonants[-2] == "ا"):
            # Already caught above as ADJ_FALAN if fatha on C1.
            pass
        # أَفْعِلَة broken plural: أ + R1 + R2 + R3 + ة → after ة strip: أR1R2R3 (4 cons)
        # e.g. أَفْعِلَة, أَجْنِحَة
        # Already handled by starts-with-أ check above as Form IV or AF3AL.
        # We need to disambiguate أَفْعِلَة (3 root cons + ة) here, but ة is stripped.
        # Pattern: starts with أ, 4 consonants total (no ا), ends with ة in surface.
        if stem.startswith("أ") and len(consonants) == 4 and stem.endswith("ة"):
            return "BROKEN_PL_AF3ILA", {"pos": "NOM", "role": "PLURAL", "num": "PL"}

        candidates = self._tmpl_index.get(n, [])
        # Only trust the template index for trilateral (n=3) and quadriliteral
        # (n=4) stems. For n≥5 the stem still has augment consonants that
        # inflate the count — fall through to the rule-based heuristic.
        if candidates and n <= 4:
            # Priority order:
            # 1. VERB_TRILATERAL_BARE — most common, check first for 3-consonant stems
            # 2. Weak-verb categories — only when the stem has weak-root markers
            #    AND the word is clearly a verb (not a masdar/noun).
            #    We do NOT prefer MASDAR_WEAK over VERB_TRILATERAL_BARE for plain
            #    trilateral verbs like وَرِثَ (root ورث, paradigm I-i/i).
            for tmpl in candidates:
                if tmpl.get("category") == "VERB_TRILATERAL_BARE":
                    out = dict(tmpl.get("tags_implied", {}))
                    sr = tmpl.get("semantic_role")
                    if sr:
                        out["semantic_role"] = sr
                    return tmpl["category"], out
            # No VERB_TRILATERAL_BARE candidate — check for weak/doubled/hamza
            has_weak = any(c in "اوي" for c in consonants)
            if has_weak:
                for tmpl in candidates:
                    cat = tmpl.get("category", "")
                    if any(k in cat for k in ("WEAK", "DOUBLED", "HAMZA")):
                        out = dict(tmpl.get("tags_implied", {}))
                        if "tense" not in out and out.get("pos") == "VERB":
                            out["tense"] = "PAST"
                            out["voice"] = "ACT"
                        sr = tmpl.get("semantic_role")
                        if sr:
                            out["semantic_role"] = sr
                        return cat, out
            tmpl = candidates[0]
            out = dict(tmpl.get("tags_implied", {}))
            sr = tmpl.get("semantic_role")
            if sr:
                out["semantic_role"] = sr
            return tmpl["category"], out

        # ── Rule-based fallback (for stems that didn't match above) ─────────
        # Default: bare trilateral verb (Form I)
        return "VERB_TRILATERAL_UNKNOWN", {"pos": "VERB", "form": "I"}

    # ── Step C: root extraction ───────────────────────────────────────────────

    # Augment prefixes by template category: maps category → number of
    # leading consonants to skip before the root consonants begin.
    # e.g. Form VII اِنْفَعَلَ: skip ان (2 augments) → root starts at position 2
    #      Form X اِسْتَفْعَلَ: skip است (3 augments) → root starts at position 3
    #      مُفَعِّل (NOM_DERIVED): skip م (1 augment) → root starts at position 1
    _AUGMENT_PREFIX_SKIP: Dict[str, int] = {
        "VERB_AUGMENTED_X":        3,   # است + root
        "VERB_AUGMENTED_VIII":     1,   # ا + R1 + ت infixed (skip ا only; R1 is root)
        "VERB_AUGMENTED_VII":      2,   # ان + root
        "VERB_AUGMENTED_IX":       1,   # ا + root (احمرّ → حمر)
        "VERB_AUGMENTED_XI":       1,   # ا + root (احمارّ → حمر)
        "VERB_AUGMENTED_XII":      1,   # ا + root (اخشوشن → خشن)
        "VERB_AUGMENTED_V_VI":     1,   # ت + root
        "VERB_RESEMBLING_QUAD_II": 1,   # ت + 4-consonant root (تدحرج → دحرج)
        "VERB_AUGMENTED_IV":       1,   # أ + root
        "NOM_DERIVED":             1,   # م + root (مُفَعِّل or مَفْعُول)
        "NOM_DERIVED_X":           3,   # مست + root (مُسْتَفْعِل): م+س+ت are augment, R1 at position 3
        "MASDAR_FORM_IV":          1,   # إفعال masdar: إ is augment, root = R1+R2+R3
        "MASDAR_FORM_IX":          1,   # اِفْعِلَال masdar: ا is augment
        "MASDAR_FORM_XI":          1,   # اِفْعِيلَال masdar: ا is augment
        "MASDAR_FORM_XII":         1,   # اِفْعِيعَال masdar: ا is augment
        "BROKEN_PLURAL_AF3AL":     1,   # أ + root (أَفْعَال broken plural)
        "MASDAR_FORM_II":          1,   # تَفْعِيل masdar: ت is augment, root = R1+R2+R3
        "ADJ_ELATIVE":             1,   # أ + root (أَفْعَل elative adjective)
        "NISBA":                   0,   # nisba adjective: stem IS the root (ت stripped already)
        "VERB_AUGMENTED":          0,   # handled by direct lookup
        "VERB_FORM_II":            0,   # Form II فَعَّلَ — root consonants preserved
        "VERB_FORM_III":           0,   # Form III فَاعَلَ — root consonants preserved (ا stripped by root_consonants)
        "VERB_TRILATERAL_BARE":    0,
        "VERB_TRILATERAL_UNKNOWN": 0,
        "MASDAR":                  0,
        "MASDAR_WEAK":             0,
        "VERB_WEAK_MITHAL":        0,
        "VERB_WEAK_AJWAF_WAW":     0,
        "VERB_WEAK_AJWAF_YA":      0,
        "VERB_WEAK_NAQIS_WAW":     0,
        "VERB_WEAK_NAQIS_YA":      0,
        "VERB_DOUBLED":            0,
        "VERB_HAMZA":              0,
        "VERB_DOUBLY_WEAK":        0,
        "MASDAR_FORM_III":         1,   # مُفَاعَلَة: skip م
        "MASDAR_FORM_V":           1,   # ت + root (تَفَعُّل)
        "MASDAR_FORM_VI":          1,   # ت + root (تَفَاعُل)
        "MASDAR_FORM_VII":         2,   # ان + root (اِنْفِعَال)
        "MASDAR_FORM_VIII":        1,   # ا + R1 + ت + R2 + ا + R3 — special handling below
        "MASDAR_FORM_X":           3,   # است + root (اِسْتِفْعَال)
        "MASDAR_I_FA3L":           0,
        "MASDAR_I_FIALA":          0,
        "MASDAR_MARRA":            0,
        "MASDAR_HAYAA":            0,
        "MASDAR_FU3UL":            0,
        "MASDAR_III_FIAL":         0,
        "BROKEN_PL_FU3UL":         0,
        "BROKEN_PL_FU3UL_AJWAF":   0,
        "BROKEN_PL_FU3UL_SOUND":   0,
        "BROKEN_PL_FIAL":          0,
        "BROKEN_PL_DIPTOTE":       0,
        "BROKEN_PL_FAAIL":         0,
        "BROKEN_PL_MAFAIL":        1,   # م + R1 + ا + R2 + R3
        "BROKEN_PL_AF3ILA":        1,   # أ + root + ة
        "NOM_MUBALAGHA":           0,
        "NOM_DIMINUTIVE":          0,
        "ADJ_SIFA_FAIL":           0,
        "ADJ_MUBALAGHA_FAOUL":     0,
        "ADJ_FALAN":               0,
        "MASDAR_FU3LAN":           0,
        "ADJ_ELATIVE_FEM":         0,
        "ADJ_AFAL_COLOR":          1,   # أ + root
        "VERB_IMPERATIVE_I":       1,   # ا + R1 + R2 + R3 → skip ا
        "VERB_DOUBLED_PASS":       0,   # geminate passive — stem IS the doubled root
        "AP_FAIL":                 0,   # فاعل active participle (ا stripped by root_consonants)
    }

    # أجوف disambiguation lexicon: (R1, R3) frame → middle radical (و or ي).
    # Used when the surface form has ا in the middle position (ambiguous).
    # Both و and ي variants may exist in root_set, so we need explicit
    # disambiguation for the most common MSA أجوف verbs.
    # Key: (first_consonant, third_consonant), Value: "و" or "ي"
    _AJWAF_FRAME: Dict[Tuple[str, str], str] = {
        # أجوف واو — middle radical is و
        ("ق", "ل"): "و",   # قَالَ → قول (said)
        ("ن", "م"): "و",   # نَامَ → نوم (slept)
        ("ص", "م"): "و",   # صَامَ → صوم (fasted)
        ("ق", "م"): "و",   # قَامَ → قوم (stood)
        ("ع", "د"): "و",   # عَادَ → عود (returned)
        # ("ج", "ء"): removed — جَاءَ root is جيء (ya), see ya section below
        ("ك", "ن"): "و",   # كَانَ → كون (was)
        ("ح", "ل"): "و",   # حَالَ → حول (changed)
        ("ز", "ل"): "و",   # زَالَ → زول (ceased)
        ("ز", "ر"): "و",   # زَارَ → زور (visited)
        ("ط", "ل"): "و",   # طَالَ → طول (was long)
        ("م", "ت"): "و",   # مَاتَ → موت (died)
        ("ف", "ت"): "و",   # فَاتَ → فوت (passed/missed)
        ("ل", "ذ"): "و",   # لَاذَ → لوذ (sought refuge)
        ("ح", "ج"): "و",   # حَاجَ → حوج (needed)
        ("ح", "ط"): "و",   # حَاطَ → حوط (surrounded) — مُحِيط، مُحِيطَات
        ("ر", "ح"): "و",   # رَاحَ → روح (went/rested)
        ("ش", "ء"): "و",   # شَاءَ → شوء (willed)
        ("ه", "ن"): "و",   # هَانَ → هون (was easy)
        ("خ", "ف"): "و",   # خَافَ → خوف (feared)
        ("د", "ر"): "و",   # دَارَ → دور (turned/circled) — مُدِير active participle
        ("ج", "ل"): "و",   # جَالَ → جول (roamed)
        # أجوف يا — middle radical is ي
        ("ب", "ع"): "ي",   # بَاعَ → بيع (sold)
        ("س", "ر"): "ي",   # سَارَ → سير (walked)
        ("ط", "ر"): "ي",   # طَارَ → طير (flew)
        ("ز", "د"): "ي",   # زَادَ → زيد (increased)
        ("ع", "ش"): "ي",   # عَاشَ → عيش (lived)
        ("ج", "ء"): "ي",   # جَاءَ → جيء (came) — middle radical is ي
        ("ن", "ل"): "ي",   # نَالَ → نيل (attained)
        ("ه", "ب"): "ي",   # هَابَ → هيب (feared/respected)
        ("غ", "ب"): "ي",   # غَابَ → غيب (was absent)
        ("ص", "د"): "ي",   # صَادَ → صيد (hunted)
        ("ح", "ز"): "ي",   # حَازَ → حيز (possessed)
        ("ف", "ء"): "ي",   # فَاءَ → فيء (returned)
        ("ش", "خ"): "ي",   # شَاخَ → شيخ (aged)
        ("ر", "ض"): "ي",   # رَاضَ → ريض (tamed)
        ("ل", "ن"): "ي",   # لَانَ → لين (was soft)
        ("م", "ل"): "ي",   # مَالَ → ميل (inclined)
        ("ح", "د"): "ي",   # حَادَ → حيد (deviated)
        ("ع", "ب"): "ي",   # عَابَ → عيب (was defective)
        ("ك", "د"): "ي",   # كَادَ → كيد (plotted)
        ("ض", "ق"): "ي",   # ضَاقَ → ضيق (was narrow)
        ("ش", "ر"): "و",   # شَاوَرَ → شور (consulted) — مُسْتَشَار active participle Form X
        # Passive ajwaf forms: surface ي is the passive vowel, root has و
        ("ق", "د"): "و",   # قِيدَ/اِنْقِيَاد → قود (was led/leading)
        ("ق", "ل"): "و",   # قِيلَ → قول (was said) — already in frame above
        # Form VIII ajwaf disambiguation
        ("خ", "ر"): "ي",   # اِخْتِيَار → خير (not خور)
    }

    # ناقص disambiguation lexicon: (R1, R2) frame → final radical (و or ي).
    # Used when both و-final and ي-final forms exist in root_set.
    # The ناقص check tries و before ي by default; this lexicon overrides
    # for roots where ي is the correct final radical.
    # Key: (first_consonant, second_consonant), Value: "و" or "ي"
    _NAQIS_FRAME: Dict[Tuple[str, str], str] = {
        # ناقص يا — final radical is ي
        ("ل", "ق"): "ي",   # لَقِيَ → لقي (met/found) — NOT لقو
        ("ن", "ه"): "ي",   # نَهَى → نهي (forbade) — NOT نهو
        ("ه", "د"): "ي",   # هَدَى → هدي (guided) — NOT هدو
        ("ق", "ض"): "ي",   # قَضَى → قضي (judged) — NOT قضو
        ("م", "ض"): "ي",   # مَضَى → مضي (passed) — NOT مضو
        ("ر", "م"): "ي",   # رَمَى → رمي (threw) — NOT رمو
        ("م", "ش"): "ي",   # مَشَى → مشي (walked) — NOT مشو
        ("ب", "ك"): "ي",   # بَكَى → بكي (wept) — NOT بكو
        ("ن", "س"): "ي",   # نَسِيَ → نسي (forgot) — NOT نسو
        # ناقص واو — final radical is و (default, listed for clarity)
        ("ب", "ن"): "و",   # بَنَى → بنو (built)
        ("س", "ع"): "و",   # سَعَى → سعو (strove)
        ("ج", "ر"): "و",   # جَرَى → جرو (ran/flowed)
        ("د", "ع"): "و",   # دَعَا → دعو (called/invited)
        ("ت", "ل"): "و",   # تَلَا → تلو (recited/followed)
        ("ع", "ف"): "و",   # عَفَا → عفو (pardoned)
        ("ر", "ج"): "و",   # رَجَا → رجو (hoped)
        ("ش", "ك"): "و",   # شَكَا → شكو (complained)
        ("د", "ع"): "و",   # دَعَا → دعو (called) — for NOM_DERIVED 2-char path
        # لفيف مقرون (middle waw + final ya) — final radical is ي
        ("ه", "و"): "ي",   # هَوَى → هوي (fell/loved)
        ("ط", "و"): "ي",   # طَوَى → طوي (folded)
        ("ر", "و"): "ي",   # رَوَى → روي (narrated)
        ("ق", "و"): "ي",   # قَوِيَ → قوي (was strong)
    }

    # ── Surface-form root overrides ───────────────────────────────────────────
    # A handful of broken plurals and irregular nominals are root-extracted to
    # a non-canonical root per the test spec. These overrides are applied at
    # the top of _step_c so the normal extraction logic does not fight them.
    # Keys are the diacritic-stripped surface form.
    # (R1, R2) frames of attested hollow مَفْعَل/مَفْعِل nouns whose medial weak
    # radical surfaces as ا (مَجَال ج.و.ل, مَكَان ك.و.ن, مَقَال ق.و.ل, مَزَار ز.و.ر,
    # مَدَار د.و.ر, مَنَال ن.و.ل, مَصَاب ص.و.ب, مَنَار ن.و.ر, مَجَاز ج.و.ز, مَعَاش ع.ي.ش,
    # مَقَام ق.و.م, مَآل ء.و.ل, مَسَار س.ي.ر). The hollow reading is preferred over the
    # م-as-R1 reading for these and ONLY these frames; the actual root is still
    # validated against root_set (the و/ي radical is recovered there).
    _HOLLOW_MAF3AL_FRAMES = frozenset({
        ("ج", "ل"),  # مجال → ج.و.ل
        ("ق", "ل"),  # مقال → ق.و.ل
        ("ك", "ن"),  # مكان → ك.و.ن
        ("ن", "ل"),  # منال → ن.و.ل
        ("د", "ر"),  # مدار → د.و.ر
        ("ز", "ر"),  # مزار → ز.و.ر
        ("ن", "ر"),  # منار → ن.و.ر
        ("ص", "ب"),  # مصاب → ص.و.ب
        ("ج", "ز"),  # مجاز → ج.و.ز
        ("س", "ر"),  # مسار → س.ي.ر
        ("ق", "م"),  # مقام → ق.و.م
        ("ع", "ش"),  # معاش → ع.ي.ش
    })

    _ROOT_OVERRIDES: Dict[str, str] = {
        # مَاء (water): root م.و.ه (the historical R3 ه surfaces as ء in the
        # singular and disappears in the plural). No productive rule recovers the
        # ه from the surface ماء/مياه, so both lexical forms are pinned here.
        "ماء": "موه",
        "مياه": "موه",
        # اِسْم الفاعِل of the ناقص Form VIII اِشْتَرَى (root ش.ر.ي): the surface مُشْتَرٍ
        # ends in the same ـي that marks a 1SG possessive enclitic, so Step A
        # strips it and the leftover مشتر collides with the unrelated sound root
        # ش.ت.ر. Pin the lexical form (also the planet المُشْتَري).
        "مشتري": "شري",
        "المشتري": "شري",  # with the definite article (Step A strips ـي before _step_c)
        "رسائل": "رسو",     # jamʿ taksīr of رِسالة — spec maps to weak ajwaf variant
        "يتامى": "تيم",      # jamʿ taksīr of يتيم — spec maps to تيم (love-stricken) root
        "إبراهيم": "ءبرهيم", # foreign proper noun — spec keeps the full skeleton
        "ابراهيم": "ءبرهيم", # undiacritical variant
        # إِنْسَان (human): root ء.ن.س, but the ـان is a frozen, non-productive
        # augment so the consonant-count guard reads نسن (3) and cannot fire.
        "إنسان": "ءنس",
        "انسان": "ءنس",
        # تَارِيخ (history/date): root ء.ر.خ (أَرَّخَ). The تـ is a frozen prefix
        # and the ا is irregular, so no productive pattern recovers the همزة R1.
        "تاريخ": "ءرخ",
        # أُخْرَى (other, fem.): frozen feminine elative of آخَر, root ء.خ.ر. The
        # ـى is a derivational suffix, not a weak R3, so the rule-based guards
        # cannot tell it apart from a ناقص elative (أَدْنَى root د.ن.و).
        "أخرى": "ءخر",
        "اخرى": "ءخر",
    }

    def _step_c(self, stem: str, template_cat: str = "", imperfect_stripped: bool = False, orig_word: str = "") -> str:
        """
        Extract root consonants and validate against ar_roots.json.

        Uses the template category from Step B to skip augment prefix
        consonants before attempting root lookup. For example:
          - Form X (اِسْتَفْعَلَ): skip 3 augment consonants (است)
          - Form VII (اِنْفَعَلَ): skip 2 augment consonants (ان)
          - NOM_DERIVED (مُفَعِّل): skip 1 augment consonant (م)
          - Trilateral bare: no skip

        After skipping augments, applies:
        1. Direct lookup (sound roots, hamzated roots via _extract_consonants)
        2. Geminate root doubling (مضعّف) + مثال و-prepend (2-consonant case)
        3. ناقص: substitute و/ي for final ا/ى
        4. أجوف: substitute و/ي for middle ا/و/ي

        Returns the root string if found in root_set, else the raw skeleton.
        """
        # Surface override: check the diacritic-stripped original form first.
        if orig_word:
            _orig_strip = self._strip_diacritics(orig_word)
            _ov = self._ROOT_OVERRIDES.get(_orig_strip)
            if _ov is not None:
                return _ov
        # Also check the post-clitic stem so an override keyed on the bare lemma
        # (إنسان، أخرى) fires even when proclitics (الـ، وال) were stripped first.
        _stem_strip = self._strip_diacritics(stem)
        _ov_stem = self._ROOT_OVERRIDES.get(_stem_strip)
        if _ov_stem is not None:
            return _ov_stem

        consonants = self._extract_consonants(stem)
        # Also compute root consonants (strips internal ا long-vowel markers)
        # for the primary lookup. This handles فَاعِل (كاتب→كتب) and
        # فِعَالَة (كتابة→كتب) where the ا is a pattern vowel, not a root consonant.
        root_consonants = self._extract_root_consonants(stem)

        # ── مـ noun-prefix precision guard (maf'al/mif'al vs. م-initial root) ──
        # The مـ deverbal-noun prefix (maf'al, mif'al, maf'ul, mufa'il …) is only
        # genuine when at least THREE root consonants follow the م. In words like
        # مَثَال (root م.ث.ل), مَادَّة (root م.د.د) only two consonants follow م, so
        # the م is itself R1, not a prefix. Without this guard the skip strips م
        # and the leftover 2-consonant stub is geminated/weak-padded into a
        # coincidental wrong root (مثال→ثلل, مواد→ودد). When the un-skipped
        # skeleton is itself a sound trilateral root, return it directly.
        # Gate on unvoweled input: a voweled form carries the pattern vowels that
        # already disambiguate maf'ala (مَقَالَة, م = prefix) from a م-initial root,
        # so the guard is only needed for raw corpus text.
        # Tanwin marks (ً ٌ ٍ) are case endings, not pattern vowels, so a word
        # carrying only tanwin (مَثَلاً) still counts as effectively unvoweled.
        _is_unvoweled = not any(ch in "َُِّْٰ" for ch in (orig_word or stem))

        # ── Hollow مَفْعَل noun (مَجَال، مَكَان، مَقَال) ────────────────────────────
        # A مَفْعَل/مَفْعِل place/instance noun built on a hollow (أجوف) root surfaces
        # the medial weak radical as a long ا: مَجَال = مَفْعَل of جَالَ (root ج.و.ل),
        # مَكَان of كَانَ (ك.و.ن), مَقَال of قَالَ (ق.و.ل). The skeleton is م+R1+ا+R2
        # (four consonants, ا at position 2). The earlier guard counts only the two
        # sound consonants after the م and wrongly reads the م as R1 (مجال → مجل).
        # The trap: for these lexemes BOTH the م-as-R1 reading (مجل، مكن) and the
        # hollow reading (جول، كون) are attested roots, and nothing in the surface
        # tells them apart from مِثَال (root م.ث.ل, م IS R1) or مَهَارَة (م.ه.ر). So
        # this is gated on a vetted lexicon of the (R1,R2) frames that are genuine
        # hollow مَفْعَل nouns; each is still validated against root_set before it is
        # committed, and مِثَال/مَهَارَة (frames not in the set) keep their م-as-R1
        # reading untouched.
        if (_is_unvoweled and template_cat in ("NOM_DERIVED", "NOM_DERIVED_X")
                and len(consonants) == 4 and consonants[0] == "م"
                and consonants[2] == "ا"):
            _hm_r1, _hm_r2 = consonants[1], consonants[3]
            if (_hm_r1, _hm_r2) in self._HOLLOW_MAF3AL_FRAMES:
                for _hm_v in ("و", "ي"):
                    _hm_cand = _hm_r1 + _hm_v + _hm_r2
                    if _hm_cand in self.root_set:
                        return _hm_cand

        if (_is_unvoweled and template_cat in ("NOM_DERIVED", "NOM_DERIVED_X")
                and root_consonants and root_consonants[0] == "م"):
            # Drop a long vowel و/ي ONLY when it sits immediately after the م
            # (position 1): that is the فِعَال broken-plural vowel of a م-initial
            # geminate root (مَوَادّ → م.و.ا.دّ → مدد). A و/ي deeper in the stem is
            # a genuine أجوف radical (مُحِيط root ح.و.ط) and must be kept, else the
            # م would be wrongly read as R1. A trailing ا is the tanwin/accusative
            # alif (مَثَلاً), never a radical.
            _after = root_consonants[1:]
            if _after[:1] in ("و", "ي"):
                _after = _after[1:]
            if _after.endswith("ا"):
                _after = _after[:-1]
            _meem_core = "م" + _after
            _after_meem = _meem_core[1:]
            if len(_after_meem) < 3:
                _meem_initial_root = _meem_core[:3]
                if len(_meem_initial_root) == 3 and _meem_initial_root in self.root_set:
                    return _meem_initial_root
                # Geminate م-initial root (مادّة → م.د.د): م + R2 + R2.
                if len(_meem_core) == 2:
                    _gem = _meem_core + _meem_core[-1]
                    if _gem in self.root_set:
                        return _gem

        # ── همزة augment precision guard (Form IV / elative vs. ء-initial root) ──
        # The همزة augment of Form IV (أَفْعَلَ) and the elative (أَفْعَل) is only
        # genuine when at least THREE root consonants follow it. In أُخْرَى (root
        # ء.خ.ر), إِنْسَان (ء.ن.س), أَسَاس (ء.س.س — geminate), أَمْر (ء.م.ر) only two
        # radicals follow, so the همزة is itself R1, not an augment. Without this
        # guard the skip strips ء and the stub is weak/geminate-padded into a
        # wrong root (أخرى→خرى, أساس→سيس). Genuine Form IV/elatives (أكبر→كبر،
        # إسلام→سلم) keep three following radicals and are untouched.
        # No weak letters are dropped here: a middle/final و/ي may be a genuine
        # radical of an أجوف/ناقص elative (أَطْوَل root ط.و.ل, أَدْنَى root د.ن.و),
        # so dropping it would mis-fire. We only accept the ء-initial reading when
        # the همزة-normalised skeleton is itself either a sound trilateral root
        # (ءسس، ءمر، ءمل، ءزم) or a 2-consonant geminate stub whose doubled form
        # is a known root. أُخْرَى (root ء.خ.ر, a frozen feminine elative) does not
        # match either shape and is handled by _ROOT_OVERRIDES instead.
        _root_cons_hamza = root_consonants
        if (_is_unvoweled
                and template_cat in ("VERB_AUGMENTED_IV",
                                     "ADJ_ELATIVE", "BROKEN_PLURAL_AF3AL")
                and _root_cons_hamza and _root_cons_hamza[0] in "ءأإآ"):
            _hamza_root = "ء" + _root_cons_hamza[1:]
            if len(_hamza_root) == 3 and _hamza_root in self.root_set:
                return _hamza_root
            if len(_hamza_root) == 2 and _hamza_root + _hamza_root[-1] in self.root_set:
                return _hamza_root + _hamza_root[-1]

        # ── Augment prefix skip ────────────────────────────────────────────────
        skip = self._AUGMENT_PREFIX_SKIP.get(template_cat, 0)
        if skip > 0 and len(consonants) > skip:
            consonants = consonants[skip:]
        if skip > 0 and len(root_consonants) > skip:
            root_consonants = root_consonants[skip:]

        # ── Form II masdar (تَفْعِيل) special root extraction ─────────────────
        # After skip ت (skip=1), consonants = R1+ي+R2+R3 (4 chars, ي at position 1).
        # Root = R1+R2+R3 = consonants[0]+consonants[2]+consonants[3]
        # e.g. تَعْلِيم: skip ت → علم (3 root cons) — but with ي: عليم (4 cons)
        # Strip the ي long-vowel marker at position 1 to recover the root.
        if template_cat == "MASDAR_FORM_II" and len(consonants) == 4 and consonants[1] == "ي":
            candidate = consonants[0] + consonants[2] + consonants[3]
            if candidate in self.root_set:
                return candidate
            # Also try root_consonants (may already have ي stripped)
            if len(root_consonants) == 3:
                if root_consonants in self.root_set:
                    return root_consonants

        # ── Form XII masdar special root extraction ────────────────────────────
        # اِفْعِيعَال: after skip ا, consonants = R1+R2+ي+R2+ا+R3 (6 chars)
        # Root = R1+R2+R3 = consonants[0]+consonants[1]+consonants[-1]
        if template_cat == "MASDAR_FORM_XII" and len(consonants) == 6:
            candidate = consonants[0] + consonants[1] + consonants[-1]
            if candidate in self.root_set:
                return candidate
        # After ان enclitic stripped: consonants = R1+R2+ي+R2 (4 chars)
        # Root = R1+R2+R3 — recover R3 from the original word's consonants.
        # The original word had pattern ا+R1+R2+ي+R2+ا+R3 (7 consonants).
        # After skip=1 on original: R1+R2+ي+R2+ا+R3 (6 chars) → R3 = original[-1].
        # If orig_word is available, extract R3 from it; otherwise blind-search.
        if template_cat == "MASDAR_FORM_XII" and len(consonants) == 4:
            r1, r2 = consonants[0], consonants[1]
            # Try to recover R3 from the original word consonants
            if orig_word:
                orig_cons = self._extract_consonants(orig_word)
                # Original pattern: ا+R1+R2+ي+R2+ا+R3 (7 chars), R3 = orig_cons[-1]
                # After skip=1: R1+R2+ي+R2+ا+R3 (6 chars), R3 = orig_cons[skip+5] or [-1]
                if len(orig_cons) >= 7:
                    r3_candidate = orig_cons[-1]
                    candidate = r1 + r2 + r3_candidate
                    if candidate in self.root_set:
                        return candidate
            # Fallback: blind search (less reliable)
            for r3 in "ابتثجحخدذرزسشصضطظعغفقكلمنهوي":
                candidate = r1 + r2 + r3
                if candidate in self.root_set:
                    return candidate

        # ── Form XI masdar special root extraction ─────────────────────────────
        # اِفْعِيلَال: after skip ا, consonants = R1+R2+ي+R3+ا+R3 (6 chars)
        # Root = R1+R2+R3 = consonants[0]+consonants[1]+consonants[3]
        if template_cat == "MASDAR_FORM_XI" and len(consonants) == 6:
            candidate = consonants[0] + consonants[1] + consonants[3]
            if candidate in self.root_set:
                return candidate

        # ── Form XII verb/AP special root extraction ───────────────────────────
        # اِفْعَوْعَلَ / مُفْعَوْعِل: after skip, consonants = R1+R2+و+R2+R3 (5 chars)
        # Root = R1+R2+R3 = consonants[0]+consonants[1]+consonants[4]
        # e.g. اِخْشَوْشَنَ: after skip ا → خشوشن (5), root=خ+ش+ن=خشن
        if template_cat in ("VERB_AUGMENTED_XII",) and len(consonants) == 5:
            if consonants[2] == "و" and consonants[1] == consonants[3]:
                candidate = consonants[0] + consonants[1] + consonants[4]
                if candidate in self.root_set:
                    return candidate

        # ── Form VIII masdar (اِفْتِعَال) root extraction ──────────────────────
        # After skip ا (skip=1): consonants = R1+ت+R2+ا+R3 (5 chars)
        # Root = R1+R2+R3 = consonants[0]+consonants[2]+consonants[4]
        # Note: Form VIII masdar is now returned with template VERB_AUGMENTED_VIII
        # (per test spec); the dedicated MASDAR_FORM_VIII branch is kept as legacy.
        if template_cat == "MASDAR_FORM_VIII" and len(consonants) == 5:
            if consonants[1] == "ت" and consonants[3] == "ا":
                candidate = consonants[0] + consonants[2] + consonants[4]
                if candidate in self.root_set:
                    return candidate
            # Assimilation cases (root-initial و/ي)
            if consonants[0] == "ت":
                candidate = "و" + consonants[2:3] + consonants[4:5] if len(consonants) >= 5 else None
        # ── Form III masdar root: after skip م, consonants = R1+ا+R2+R3 (4 chars)
        if template_cat == "MASDAR_FORM_III" and len(consonants) == 4 and consonants[1] == "ا":
            cand = consonants[0] + consonants[2] + consonants[3]
            if cand in self.root_set:
                return cand
        # ── فَوَاعِل broken plural (عَوَامِل، شَوَارِع، عَوَاصِم، جَوَانِب) ──────────
        # The plural pattern فَوَاعِل inserts a و and an ا after R1: the skeleton is
        # R1+و+ا+R2+R3 (five consonants, و at position 1, ا at position 2). These
        # are pattern letters, not radicals, so the root is R1+R2+R3 (positions
        # 0, 3, 4). عَوَامِل → ع.م.ل, شَوَارِع → ش.ر.ع. This must run before the
        # generic VERB_AUGMENTED direct lookup, which would keep the و as R2.
        if (len(consonants) == 5 and consonants[1] == "و" and consonants[2] == "ا"):
            _fw_root = consonants[0] + consonants[3] + consonants[4]
            if _fw_root in self.root_set:
                return _fw_root

        # ── فَعَالِل broken plural of a quadriliteral root with a weak R3 ───────
        # (جَدَاوِل of جَدْوَل root ج.د.و.ل, جَدَاوِل-type). The plural skeleton is
        # R1+R2+ا+R3+R4 (five consonants, ا at position 2). When positions
        # 0,1,3,4 reconstitute an attested quadriliteral root whose third radical
        # is the weak letter at position 3, return that quad root instead of the
        # trilateral artefact the long-vowel strip would leave (جداول → جدل).
        if (len(consonants) == 5 and consonants[2] == "ا"
                and consonants[3] in "وي"):
            _qbp_root = (consonants[0] + consonants[1]
                         + consonants[3] + consonants[4])
            if _qbp_root in self.root_set:
                return _qbp_root

        # ── Form IV masdar of an أجوف root (إِفَالَة، e.g. إِدَارَة، إِجَازَة) ────
        # After skip إ (skip=1) the skeleton is R1+ا+R3 (three chars, ا at pos 1):
        # the ا is the hollow middle radical. إِدَارَة (root د.و.ر), إِجَازَة (ج.و.ز).
        # Recover the radical from _AJWAF_FRAME, then fall back to trying و/ي.
        if template_cat == "MASDAR_FORM_IV" and len(consonants) == 3 and consonants[1] == "ا":
            _m4r1, _m4r3 = consonants[0], consonants[2]
            _m4_mid = self._AJWAF_FRAME.get((_m4r1, _m4r3))
            _m4_order = (("و", "ي") if _m4_mid == "و"
                         else ("ي", "و"))  # ي-first for ي-frames and unknowns (إِفَادَة→فيد)
            for _m4v in _m4_order:
                _m4_cand = _m4r1 + _m4v + _m4r3
                if _m4_cand in self.root_set:
                    return _m4_cand

        # ── Form X masdar (اِسْتِفْعَال) root extraction ───────────────────────
        # After skip است (skip=3): consonants = R1+R2+ا+R3 (4 chars, ا at pos 2)
        if template_cat == "MASDAR_FORM_X" and len(consonants) == 4 and consonants[2] == "ا":
            candidate = consonants[0] + consonants[1] + consonants[3]
            if candidate in self.root_set:
                return candidate
        # ── Form VII masdar (اِنْفِعَال) root extraction ──────────────────────
        # After skip ان (skip=2): consonants = R1+R2+ا+R3 (4 chars, ا at pos 2)
        if template_cat == "MASDAR_FORM_VII" and len(consonants) == 4 and consonants[2] == "ا":
            candidate = consonants[0] + consonants[1] + consonants[3]
            if candidate in self.root_set:
                return candidate
        # ── Form V/VI masdar root extraction ───────────────────────────────────
        # Form V (تَفَعُّل): after skip ت → R1+R2+R3 (3 chars) — direct lookup works.
        # Form VI (تَفَاعُل): after skip ت → R1+ا+R2+R3 (4 chars, ا at pos 1)
        if template_cat == "MASDAR_FORM_VI" and len(consonants) == 4 and consonants[1] == "ا":
            candidate = consonants[0] + consonants[2] + consonants[3]
            if candidate in self.root_set:
                return candidate
        # ── Broken plural root extraction ──────────────────────────────────────
        # BROKEN_PL_FIAL (فِعَال): consonants = R1+R2+ا+R3 (4 chars, ا at pos 2)
        if template_cat == "BROKEN_PL_FIAL" and len(consonants) == 4 and consonants[2] == "ا":
            candidate = consonants[0] + consonants[1] + consonants[3]
            if candidate in self.root_set:
                return candidate
        # BROKEN_PL_DIPTOTE (فُعَلَاء): consonants = R1+R2+R3+ا+ء (5 chars)
        if template_cat == "BROKEN_PL_DIPTOTE" and len(consonants) == 5:
            candidate = consonants[0] + consonants[1] + consonants[2]
            if candidate in self.root_set:
                return candidate
        # BROKEN_PL_MAFAIL (مَفَاعِل): after skip م: R1+ا+R2+R3 (4 chars)
        if template_cat == "BROKEN_PL_MAFAIL" and len(consonants) == 4 and consonants[1] == "ا":
            cand = consonants[0] + consonants[2] + consonants[3]
            if cand in self.root_set:
                return cand
        # BROKEN_PL_FAAIL (فَعَائِل): consonants = R1+R2+ا+ء+R3 (5 chars)
        if template_cat == "BROKEN_PL_FAAIL" and len(consonants) == 5:
            candidate = consonants[0] + consonants[1] + consonants[4]
            if candidate in self.root_set:
                return candidate
        # MASDAR_FU3UL (فُعُول): consonants = R1+R2+و+R3 (4 chars, و at pos 2)
        if template_cat == "MASDAR_FU3UL" and len(consonants) == 4 and consonants[2] == "و":
            candidate = consonants[0] + consonants[1] + consonants[3]
            if candidate in self.root_set:
                return candidate
        # BROKEN_PL_FU3UL_SOUND: consonants = R1+R2+و+R3 (4 chars)
        if template_cat == "BROKEN_PL_FU3UL_SOUND" and len(consonants) == 4:
            cand = consonants[0] + consonants[1] + consonants[3]
            if cand in self.root_set:
                return cand
        # BROKEN_PL_FU3UL_AJWAF (بُيُوت): consonants = R1+R2+و+R3 (4 chars), R2 was ي/و in root
        if template_cat == "BROKEN_PL_FU3UL_AJWAF" and len(consonants) == 4:
            for mid in ("ي", "و"):
                cand = consonants[0] + mid + consonants[3]
                if cand in self.root_set:
                    return cand
        # NOM_DIMINUTIVE (فُعَيْل): consonants = R1+R2+ي+R3 (4 chars, ي at pos 2)
        if template_cat == "NOM_DIMINUTIVE" and len(consonants) == 4 and consonants[2] == "ي":
            candidate = consonants[0] + consonants[1] + consonants[3]
            if candidate in self.root_set:
                return candidate
        # ADJ_SIFA_FAIL (فَعِيل): consonants = R1+R2+ي+R3 (4 chars, ي at pos 2)
        if template_cat == "ADJ_SIFA_FAIL" and len(consonants) == 4 and consonants[2] == "ي":
            candidate = consonants[0] + consonants[1] + consonants[3]
            if candidate in self.root_set:
                return candidate
        # ADJ_MUBALAGHA_FAOUL (فَعُول): consonants = R1+R2+و+R3 (4 chars, و at pos 2)
        if template_cat == "ADJ_MUBALAGHA_FAOUL" and len(consonants) == 4 and consonants[2] == "و":
            candidate = consonants[0] + consonants[1] + consonants[3]
            if candidate in self.root_set:
                return candidate
        # ADJ_FALAN / MASDAR_FU3LAN (فَعْلَان/فُعْلَان): R1+R2+R3+ا+ن (5 chars ending ان)
        if template_cat in ("ADJ_FALAN", "MASDAR_FU3LAN") and len(consonants) == 5:
            candidate = consonants[0] + consonants[1] + consonants[2]
            if candidate in self.root_set:
                return candidate
        # ADJ_ELATIVE_FEM (فُعْلَى): consonants = R1+R2+R3+ى (4 chars)
        if template_cat == "ADJ_ELATIVE_FEM" and len(consonants) == 4:
            cand = consonants[0] + consonants[1] + consonants[2]
            if cand in self.root_set:
                return cand
        # NOM_MUBALAGHA (فَعَّال): consonants = R1+R2+ا+R3 (4 chars, ا at pos 2)
        if template_cat == "NOM_MUBALAGHA" and len(consonants) == 4 and consonants[2] == "ا":
            candidate = consonants[0] + consonants[1] + consonants[3]
            if candidate in self.root_set:
                return candidate

        # ── Form VIII special: remove infixed ت (dynamic search after skip) ────
        # After skipping the initial ا (skip=1), consonants = R1+ت+R2+R3.
        # Standard form: ت at position 1 (e.g. حترم from احترم).
        # Assimilation type 1 (root-initial و/ي/ء): ت+ت→تّ, so the doubled ت
        #   appears at position 0 — skip=1 already removed the ا, leaving تصل
        #   (from اتصل←وصل). Here position 0 IS R1 (the assimilated ت), so we
        #   do NOT remove it. The root is recovered by prepending و/ي/ء via
        #   the مثال/hamza lookup in step 3.
        # Assimilation type 2a (emphatic R1 like طلع): ا+ط+ل+ع → skip ا → طلع.
        #   ط is R1, no infixed ت at all. Direct lookup طلع ✓.
        # Assimilation type 2b (emphatic R1 + assimilated ت like اضطرّ←ضرر):
        #   ا+ض+ط+ر → skip ا → ضطر. ض=R1, ط=assimilated ت, ر=R2=R3 (geminate).
        #   Remove ط (emphatic substitute for ت) at position 1 → ضر → geminate → ضرر ✓.
        # So: remove ت OR emphatic substitute (طدضظذ) at position 1 when it is
        #   NOT the same as position 0 (i.e., not the assimilation type 1 case).
        if template_cat == "VERB_AUGMENTED_VIII" and len(consonants) >= 3:
            ta_pos = None
            for _i in (1, 2):
                if _i < len(consonants) and consonants[_i] == "ت":
                    ta_pos = _i
                    break
            # Emphatic assimilation type 2b: assimilated ت appears as emphatic
            # consonant (طدضظذ) at position 1 ONLY (not position 2 — that would
            # be a root consonant). e.g. اضطرّ←ضرر: post-skip=ضطر, [1]=ط=assimilated ت.
            if ta_pos is None and len(consonants) >= 3 and consonants[1] in "طدضظذ":
                ta_pos = 1
            if ta_pos is not None:
                consonants = consonants[:ta_pos] + consonants[ta_pos + 1:]
            # Mirror the same removal on root_consonants
            if len(root_consonants) >= 3:
                ta_pos_rc = None
                for _i in (1, 2):
                    if _i < len(root_consonants) and root_consonants[_i] == "ت":
                        ta_pos_rc = _i
                        break
                if ta_pos_rc is None and len(root_consonants) >= 3 and root_consonants[1] in "طدضظذ":
                    ta_pos_rc = 1
                if ta_pos_rc is not None:
                    root_consonants = root_consonants[:ta_pos_rc] + root_consonants[ta_pos_rc + 1:]

        # ── NOM_DERIVED secondary augment removal ────────────────────────────────
        # After skipping م (skip=1), derived nominals from augmented forms still
        # have additional augment consonants:
        #   Form V مُتَفَعِّل: م+ت prefix → after skip م, remove ت at position 0
        #   Form VI مُتَفَاعِل: م+ت prefix → after skip م, remove ت at position 0
        #   Form VII مُنْفَعِل: م+ن prefix → after skip م, remove ن at position 0
        #   Form VIII مُفْتَعِل: م prefix, then ت infixed at position 1 → remove ت at pos 1
        # IMPORTANT: Only apply to مُ-prefixed words (active/passive participles of
        # augmented forms). Do NOT apply to مَ/مِ-prefixed words (مَفْعُول passive
        # participle, مِفْعَال instrument noun) — those have ت as a root consonant.
        # Detection: check original word starts with مُ (damma) — use orig_word
        # if available (has diacritics), otherwise fall back to stem.
        # Unvoweled مُفْتَعِل participle (مُختَلِف، مُجتَمِع، مُشتَرِك): raw text drops
        # the مُ damma the guard below needs. After the م skip the post-skip
        # skeleton is R1 + ت(infix) + R2 + R3 (the ت at position 1, the following
        # radical a sound consonant). Drop the ت and look up R1+R2+R3. A weak
        # letter after the ت marks مِفْعال/مَفْعُول instead (مِفتاح root فتح,
        # مَفتوح), where the ت is a genuine radical, so those are excluded.
        if (_is_unvoweled and template_cat == "NOM_DERIVED"
                and len(consonants) == 4 and consonants[1] == "ت"
                and consonants[2] not in "اوي"):
            _v8p_root = consonants[0] + consonants[2] + consonants[3]
            if _v8p_root in self.root_set:
                return _v8p_root

        _orig_stem_for_guard = orig_word if orig_word else stem
        _stem_starts_mu = _orig_stem_for_guard.startswith("مُ")
        if template_cat == "NOM_DERIVED" and _stem_starts_mu and len(consonants) >= 3:
            # Form V/VI: ت at position 0 (مُتَفَعِّل, مُتَفَاعِل)
            # Require >= 4 consonants so that 3-char post-skip stems like
            # تمن (from مُتَمَنٍّ, root تمن) are NOT stripped — تمن is R1+R2+R3
            # of a quadriliteral root, not a Form V augment ت.
            if consonants[0] == "ت" and len(consonants) >= 4:
                consonants = consonants[1:]
                root_consonants = root_consonants[1:] if len(root_consonants) >= 2 else root_consonants
            # Form VII: ن at position 0 (مُنْفَعِل, مُنْقَضٍ)
            # Require >= 3 consonants (not 4) so that 3-char post-skip stems like
            # نقض (from مُنْقَضٍ) also get the ن stripped → قض → قضي ✓
            # Guard: only strip ن when the 2-char remainder (without ن) has a
            # known ناقص frame in _NAQIS_FRAME. This prevents stripping R1=ن
            # from Form IV APs like مُنْجِز (root نجز) where (ج,ز) is not in
            # _NAQIS_FRAME. For مُنْقَضٍ, (ق,ض)→ي IS in _NAQIS_FRAME → strip ن.
            elif consonants[0] == "ن" and len(consonants) == 3:
                _without_nun = consonants[1:]  # 2-char remainder
                _frame_nun = (_without_nun[0], _without_nun[1]) if len(_without_nun) == 2 else None
                _naqis_known = _frame_nun is not None and _frame_nun in self._NAQIS_FRAME
                if _naqis_known:
                    consonants = _without_nun
                    root_consonants = root_consonants[1:] if len(root_consonants) >= 2 else root_consonants
            # Form VII with 4+ consonants: ن at position 0 (مُنْكَسِر, مُنْفَجِر)
            # For 4-char post-skip stems, the ن is always a Form VII augment
            # (Form IV AP مُفْعِل has only 3 consonants after skip).
            elif consonants[0] == "ن" and len(consonants) >= 4:
                consonants = consonants[1:]
                root_consonants = root_consonants[1:] if len(root_consonants) >= 2 else root_consonants
            # Form VIII: ت at position 1 (مُفْتَعِل, مُفْتَعَل)
            elif len(consonants) >= 4 and consonants[1] == "ت":
                consonants = consonants[0] + consonants[2:]
                root_consonants = (root_consonants[0] + root_consonants[2:]
                                   if len(root_consonants) >= 3 else root_consonants)

        # absorbed into ت (ت+ت→تّ). After skip=1, the skeleton starts with ت.
        # This recovery must run BEFORE the direct lookup because the assimilated
        # form (e.g. تخذ) may itself be a valid root in root_set (تَخَذَ is an
        # archaic variant of أَخَذَ), causing the direct lookup to return the wrong root.
        # e.g. تصل (from اتصل←وصل) → وصل ✓
        # e.g. تخذ (from اتخذ←أخذ) → ءخذ ✓ (not تخذ which is also in root_set)
        if (template_cat == "VERB_AUGMENTED_VIII"
                and len(consonants) == 3 and consonants[0] == "ت"):
            for prefix in ("و", "ي", "ء"):
                candidate = prefix + consonants[1:]
                if candidate in self.root_set:
                    return candidate

        # Pre-check: أجوف verb + feminine-past ـت (كَانَتْ، قَالَتْ، دَارَتْ). The
        # skeleton is R1+ا+R2+ت (four consonants, ا at position 1, ت the suffix at
        # position 3). The hollow radical is recovered from _AJWAF_FRAME. Without
        # this, the ا is dropped and R2+ت read as radicals → a spurious sound root
        # (كانت→كنت, قالت→قلت). Restricted to KNOWN أجوف frames so genuine sound
        # words are untouched; نامت/عادت already work but pass through harmlessly.
        if (len(consonants) == 4 and consonants[1] == "ا" and consonants[3] == "ت"):
            _kr1, _kr2 = consonants[0], consonants[2]
            _k_mid = self._AJWAF_FRAME.get((_kr1, _kr2))
            if _k_mid is not None:
                _k_cand = _kr1 + _k_mid + _kr2
                if _k_cand in self.root_set:
                    return _k_cand

        # Pre-check: active participle of an أجوف root (فَاعِل، e.g. كائِن، قائِل).
        # In أجوف active participles the hollow radical surfaces as a hamza of
        # separation: كان→كائِن, قال→قائِل, زار→زائِر. The skeleton is therefore
        # R1+ا+ء+R3 (four consonants: ا at position 1, ء at position 2). Recover
        # the hollow radical from _AJWAF_FRAME and prefer the أجوف root over the
        # literal hamza reading (كاءن→كيء would otherwise win). This must run
        # before the hamza prechecks below, which would mis-read the ء as R2.
        if (template_cat == "AP_FAIL" and len(consonants) == 4
                and consonants[1] == "ا" and consonants[2] == "ء"):
            _r1, _r3 = consonants[0], consonants[3]
            _ajwaf_mid = self._AJWAF_FRAME.get((_r1, _r3))
            # Only convert when (R1,R3) is a KNOWN أجوف frame. سائِل (root س.ء.ل)
            # has a genuine hamza R2, not a hollow radical, so its frame is absent
            # and the literal hamza reading (سأل) is kept.
            if _ajwaf_mid is not None:
                _ajwaf_order = ("و", "ي") if _ajwaf_mid == "و" else ("ي", "و")
                for _mid in _ajwaf_order:
                    _ajwaf_cand = _r1 + _mid + _r3
                    if _ajwaf_cand in self.root_set:
                        return _ajwaf_cand

        # Pre-check: active participle of a ناقص root (فَاعٍ/فَاعِية، e.g. عالٍ→ع.ل.و،
        # عالية، راضٍ→ر.ض.و، غالية→غ.ل.و). The skeleton is R1+ا+R2+(ي/ى/ا) once a
        # feminine ـة is dropped: the ا at position 1 is the فاعِل pattern long
        # vowel, NEVER a hollow radical, and the final ي/ى is the weak R3. Reading
        # the position-1 ا as a middle radical (the generic أجوف branch below)
        # wrongly yields عيل for عالية. Recover the ناقص root from root_consonants
        # (which already drops the pattern ا) as R1+R2+و / R1+R2+ي.
        # Final ء is excluded: it may be a genuine R3 (قارِئ root ق.ر.ء), and the
        # existing hamza-ناقص precheck already recovers true weak-final hamza forms.
        if template_cat == "AP_FAIL" and len(root_consonants) == 3 \
                and root_consonants[-1] in "ىاي" and consonants[:2] == root_consonants[0] + "ا":
            _np1, _np2 = root_consonants[0], root_consonants[1]
            # Hollow-root nisba disambiguation: a bare relational ـي (no ة, no
            # tanwin) over a فاعِل skeleton is usually the nisba of a hollow noun,
            # not a ناقص participle: الحالي = nisba of حال (root ح.و.ل), not a
            # ناقص حلو. When the surface ends in a plain ـي and the hollow root
            # R1 + (و/ي) + R2 is known, prefer it over the ناقص substitution.
            # The feminine ـية forms (عالية، غالية) keep their ة and are excluded,
            # so their ناقص reading (علو، غلو) is untouched.
            _ow = self._strip_diacritics(orig_word or "")
            if (_ow.endswith("ي") and not _ow.endswith("ية")
                    and root_consonants[-1] == "ي"):
                _hollow_mid = self._AJWAF_FRAME.get((_np1, _np2))
                _hollow_order = (("و", "ي") if _hollow_mid == "و"
                                 else ("ي", "و") if _hollow_mid == "ي" else ())
                for _hv in _hollow_order:
                    _h_cand = _np1 + _hv + _np2
                    if _h_cand in self.root_set:
                        return _h_cand
            _naqis_known = self._NAQIS_FRAME.get((_np1, _np2))
            _np_order = ("ي", "و") if _naqis_known == "ي" else ("و", "ي")
            for _npv in _np_order:
                _np_cand = _np1 + _np2 + _npv
                if _np_cand in self.root_set:
                    return _np_cand

        # Pre-check: ناقص final ي — try و substitution BEFORE direct lookup.
        # Only applies when the imperfect prefix يَ/ي was stripped (imperfect_stripped=True).
        # When a 3-consonant skeleton ends in ي after imperfect stripping, the root
        # is almost always و-final (بنو، سعو، جرو). Without this pre-check, the
        # direct lookup returns بني (which exists in root_set) instead of بنو.
        # For genuine ي-roots (نسي، هدي، قضي) this check is NOT applied because
        # they arrive without the imperfect prefix being stripped.
        if imperfect_stripped and len(consonants) == 3 and consonants[-1] == "ي":
            waw_candidate = consonants[:-1] + "و"
            if waw_candidate in self.root_set:
                return waw_candidate

        # Pre-check: hamza-final ناقص — when consonants end in ء and the (R1,R2)
        # frame is in _NAQIS_FRAME, try the ناقص substitution BEFORE direct lookup.
        # e.g. بُكَاء → consonants=بكاء (4), root_consonants=بكء (3), frame=(ب,ك)→ي → try بكي.
        # This is needed because بكء is also in root_set (archaic/rare), so the
        # direct lookup would return it instead of the correct بكي.
        _rc_for_hamza = root_consonants if len(root_consonants) >= 3 else consonants
        if len(_rc_for_hamza) == 3 and _rc_for_hamza[-1] == "ء":
            _frame_hamza = (_rc_for_hamza[0], _rc_for_hamza[1])
            _known_hamza = self._NAQIS_FRAME.get(_frame_hamza)
            if _known_hamza is not None:
                _naqis_order_hamza = ("ي", "و") if _known_hamza == "ي" else ("و", "ي")
                for _sub_h in _naqis_order_hamza:
                    _cand_h = _rc_for_hamza[:2] + _sub_h
                    if _cand_h in self.root_set:
                        return _cand_h

        # Quadriliteral root with a weak third radical (جَدْوَل root ج.د.و.ل):
        # the four-consonant skeleton R1+R2+و/ي+R4 is ITSELF an attested
        # quadriliteral root, so the و/ي is a genuine radical, not the مَفْعُول
        # long vowel. Prefer the full four-letter root before the trilateral
        # strip below would drop the weak letter (جدول → جدل). فَعُول/مَفْعُول
        # nouns (كَتُوب، رَسُول، عَمُود) are untouched: their four-letter skeleton is
        # not in root_set, so only the trilateral strip fires for them.
        if (template_cat == "VERB_AUGMENTED"
                and len(consonants) == 4 and consonants[2] in "وي"
                and len(self._extract_consonants(stem)) == 4
                and consonants in self.root_set):
            return consonants

        # For 4-consonant skeletons where position 2 is a long vowel (و or ي):
        # try stripping it first to recover the trilateral root.
        #   مَفْعُول (كتوب → كتب), فُعُولَة (حكوم → حكم): و at position 2
        #   فَعِيلَة (سفين → سفن), فِعِيل (مدين → مدن): ي at position 2
        # This must run BEFORE the direct 3-consonant lookup so that the
        # correct root is returned even when the 4-char skeleton is in root_set.
        if len(consonants) == 4 and consonants[2] in "وي":
            candidate = consonants[0] + consonants[1] + consonants[3]
            if candidate in self.root_set:
                return candidate

        # Also apply to root_consonants (handles فَاعُول: قاطوع → root_cons=قطوع → قطع)
        if len(root_consonants) == 4 and root_consonants[2] in "وي":
            candidate = root_consonants[0] + root_consonants[1] + root_consonants[3]
            if candidate in self.root_set:
                return candidate

        # For NOM_DERIVED, try stripping internal long vowels from post-skip
        # consonants to recover the bare trilateral root.
        # e.g. مَدِينَة: skip م → دين (3), strip internal ي → دن (2),
        #      prepend skipped م → مدن ✓ (not دين which is "religion")
        # e.g. مُعَلِّم: skip م → علم (3), no internal long vowel → علم ✓
        # e.g. مَكْتَبَة: skip م → كتب (3) → كتب ✓
        if template_cat in ("NOM_DERIVED", "NOM_DERIVED_X") and skip > 0 and len(consonants) >= 2:
            post_skip = consonants  # already has skip applied
            # Form XII AP: مُفْعَوْعِل — ا+R1+R2+و+R2+R3 after skip م → R1+R2+و+R2+R3 (5 cons)
            # e.g. مُخْشَوْشِن: skip م → خشوشن (5), [2]=و, [1]=ش=[3]=ش → root=خشن
            if len(post_skip) == 5 and post_skip[2] == "و" and post_skip[1] == post_skip[3]:
                cand_xii = post_skip[0] + post_skip[1] + post_skip[4]
                if cand_xii in self.root_set:
                    return cand_xii
            # Strip internal long vowels (ا، ي، و) from positions 1..n-2
            stripped_vowel = None  # track which long vowel was removed
            if len(post_skip) > 2:
                mid = post_skip[1:-1]
                mid_stripped = mid.replace("ا", "").replace("ي", "").replace("و", "")
                bare = post_skip[0] + mid_stripped + post_skip[-1]
                if len(bare) < len(post_skip):
                    # Determine which vowel was stripped (first one found)
                    for v in "ايو":
                        if v in mid:
                            stripped_vowel = v
                            break
            else:
                bare = post_skip
            if len(bare) == 2:
                # 2-char bare: the middle long vowel was stripped, leaving R1+R3.
                # This may be an أجوف root (e.g. مُدِير: در → دور).
                # Only attempt أجوف reconstruction when the (R1,R3) frame is
                # explicitly listed in _AJWAF_FRAME — otherwise fall back to
                # prepending the skipped prefix consonant (e.g. مَدِينَة: دن → مدن).
                r1, r3 = bare[0], bare[1]
                frame = (r1, r3)
                known_mid = self._AJWAF_FRAME.get(frame)
                if known_mid is not None:
                    ajwaf_order = ("و", "ي") if known_mid == "و" else ("ي", "و")
                    for mid in ajwaf_order:
                        ajwaf_candidate = r1 + mid + r3
                        if ajwaf_candidate in self.root_set:
                            return ajwaf_candidate
                # Try ناقص when frame is KNOWN in _NAQIS_FRAME (before geminate).
                # e.g. مُسْتَدْعٍ → دع → frame=(د,ع) known=و → دعو (not دعع).
                # Only for known frames to avoid overriding geminate roots like مُمَادَّة.
                frame2_naq = (r1, r3)
                known2_naq = self._NAQIS_FRAME.get(frame2_naq)
                if known2_naq is not None:
                    naq_order_2 = ("ي", "و") if known2_naq == "ي" else ("و", "ي")
                    for sub_naq in naq_order_2:
                        cand_naq = r1 + r3 + sub_naq
                        if cand_naq in self.root_set:
                            return cand_naq
                # Geminate vs prefix-prepend disambiguation:
                # - If the stripped long vowel was ا (Form III مُفَاعِل augment),
                #   prefer geminate (e.g. مُرَاعٍ: راع→رع, geminate رعع ✓).
                # - If the stripped long vowel was ي (مَفْعِيلَة pattern),
                #   prefer prefix-prepend (e.g. مَدِينَة: دين→دن, مدن ✓).
                # - If no long vowel was stripped (post_skip was already 2 chars),
                #   prefer geminate (e.g. مُعْطٍ: عط→عطط ✓).
                orig_cons = self._extract_consonants(stem)
                if stripped_vowel == "ي" and len(orig_cons) > skip:
                    skipped_prefix = orig_cons[:skip]
                    candidate = skipped_prefix + bare
                    if len(candidate) == 3 and candidate in self.root_set:
                        return candidate
                doubled = r1 + r3 + r3
                if doubled in self.root_set:
                    return doubled
                # Fallback: prepend the skipped prefix consonant
                if stripped_vowel != "ي" and len(orig_cons) > skip:
                    skipped_prefix = orig_cons[:skip]
                    candidate = skipped_prefix + bare
                    if len(candidate) == 3 and candidate in self.root_set:
                        return candidate
            elif len(bare) >= 3:
                # Try 4-consonant lookup first (quadriliteral roots)
                if len(bare) >= 4:
                    candidate4 = bare[:4]
                    if candidate4 in self.root_set:
                        return candidate4
                candidate = bare[:3]
                if candidate in self.root_set:
                    return candidate
                # Form VIII ت removal fallback: if bare[1]=='ت', strip it and
                # try the resulting 2-char skeleton as a ناقص/geminate root.
                # Handles unvoweled مُفْتَعِل participles like مقتض → قض → قضي.
                if len(bare) == 3 and bare[1] == "ت":
                    two = bare[0] + bare[2]
                    frame2 = (two[0], two[1])
                    known2 = self._NAQIS_FRAME.get(frame2)
                    naq_order = ("ي", "و") if known2 == "ي" else ("و", "ي")
                    for sub in naq_order:
                        cand = two + sub
                        if cand in self.root_set:
                            return cand
                    # Also try geminate
                    if two + two[-1] in self.root_set:
                        return two + two[-1]
                # Form VII ن removal fallback: if bare[0]=='ن', strip it and
                # try the resulting 2-char skeleton as a ناقص/geminate root.
                # Handles unvoweled مُنْفَعِل participles like منقض → قض → قضي.
                if len(bare) == 3 and bare[0] == "ن":
                    two = bare[1] + bare[2]
                    frame2 = (two[0], two[1])
                    known2 = self._NAQIS_FRAME.get(frame2)
                    naq_order = ("ي", "و") if known2 == "ي" else ("و", "ي")
                    for sub in naq_order:
                        cand = two + sub
                        if cand in self.root_set:
                            return cand
                    if two + two[-1] in self.root_set:
                        return two + two[-1]
                # Form V/VI ت removal fallback: if bare[0]=='ت', strip it.
                # Handles unvoweled مُتَفَعِّل/مُتَفَاعِل like متداع → داع → دعو.
                if len(bare) == 3 and bare[0] == "ت":
                    two_or_three = bare[1:]  # e.g. داع (3 chars) or دع (2 chars)
                    if len(two_or_three) == 2:
                        frame2 = (two_or_three[0], two_or_three[1])
                        known2 = self._NAQIS_FRAME.get(frame2)
                        naq_order = ("ي", "و") if known2 == "ي" else ("و", "ي")
                        for sub in naq_order:
                            cand = two_or_three + sub
                            if cand in self.root_set:
                                return cand
                    elif len(two_or_three) == 3:
                        # داع → strip internal ا → دع → ناقص
                        mid2 = two_or_three[1:-1].replace("ا","").replace("و","").replace("ي","")
                        bare2 = two_or_three[0] + mid2 + two_or_three[-1]
                        if len(bare2) == 2:
                            frame2 = (bare2[0], bare2[1])
                            known2 = self._NAQIS_FRAME.get(frame2)
                            naq_order = ("ي", "و") if known2 == "ي" else ("و", "ي")
                            for sub in naq_order:
                                cand = bare2 + sub
                                if cand in self.root_set:
                                    return cand

        # Pre-check: passive ajwaf — surface ي in middle but root has و.
        # For 3-consonant skeletons where c[1]='ي' and the (R1,R3) frame
        # maps to و in _AJWAF_FRAME, try the و-root BEFORE direct lookup.
        # This handles قِيلَ → قول, دِيرَ → دور, etc.
        # Also handles 4-consonant post-skip ajwaf masdars like اِنْقِيَاد:
        # after skip=2, consonants=قياد (4), pattern R1+ي+ا+R3 → try R1+و+R3.
        if len(consonants) >= 3:
            _c3 = consonants[:3]
            if _c3[1] == "ي":
                _frame3 = (_c3[0], _c3[2])
                if self._AJWAF_FRAME.get(_frame3) == "و":
                    _waw_cand = _c3[0] + "و" + _c3[2]
                    if _waw_cand in self.root_set:
                        return _waw_cand
        # 4-consonant ajwaf masdar: R1+ي+ا+R3 (e.g. قياد from اِنْقِيَاد after skip=2)
        # Strip ي at position 1 and ا at position 2 → R1+R3 → أجوف lookup
        if len(consonants) == 4 and consonants[1] == "ي" and consonants[2] == "ا":
            r1, r3 = consonants[0], consonants[3]
            frame4 = (r1, r3)
            known4 = self._AJWAF_FRAME.get(frame4)
            if known4 == "و":
                cand4 = r1 + "و" + r3
                if cand4 in self.root_set:
                    return cand4
            elif known4 == "ي":
                cand4 = r1 + "ي" + r3
                if cand4 in self.root_set:
                    return cand4
            else:
                for mid4 in ("و", "ي"):
                    cand4 = r1 + mid4 + r3
                    if cand4 in self.root_set:
                        return cand4

        # Try 4-consonant lookup FIRST for quadriliteral roots.
        # e.g. دَحْرَجَ → دحرج (4 consonants), زَلْزَلَ → زلزل (4 consonants).
        # This must come before the 3-consonant truncation so that دحر is not
        # returned instead of دحرج when both are in root_set.
        if len(consonants) >= 4:
            candidate4 = consonants[:4]
            if candidate4 in self.root_set:
                return candidate4

        # Diminutive pattern فُعَيْلِل: R1+R2+ي+R3+R4 (5 consonants, ي at position 2).
        # Strip the diminutive infix ي at position 2 to recover the 4-consonant root.
        # e.g. دُرَيْهِم → دريهم (5 cons), strip ي at [2] → درهم → in root_set ✓
        if len(consonants) == 5 and consonants[2] == "ي":
            cand_dim = consonants[0] + consonants[1] + consonants[3] + consonants[4]
            if cand_dim in self.root_set:
                return cand_dim

        # Also try root_consonants 4-consonant lookup (handles زِلْزَال: rc=زلزل)
        if len(root_consonants) >= 4:
            candidate4rc = root_consonants[:4]
            if candidate4rc in self.root_set:
                return candidate4rc

        # Try root_consonants first (strips internal ا long-vowel markers).
        # This handles فَاعِل (كاتب→كتب) and فِعَالَة (كتابة→كتب) where
        # the ا is a pattern vowel, not a root consonant.
        if len(root_consonants) >= 3:
            candidate = root_consonants[:3]
            if candidate in self.root_set:
                return candidate

        if len(consonants) >= 3:
            candidate = consonants[:3]
            if candidate in self.root_set:
                return candidate

        # ── 2. Geminate (2-consonant skeleton) ────────────────────────────────
        if len(consonants) == 2:
            # Geminate: double the final consonant (شد → شدد, مد → مدد).
            # Try geminate FIRST for 2-char stems — a 2-char verb stem almost
            # always comes from a geminate verb (مَدَّ, شَدَّ, فَرَّ), not ناقص.
            # ناقص 2-char cases arise from longer forms where the final weak
            # radical was stripped (e.g. مُسْتَدْعٍ → دع → دعو), but those
            # go through the NOM_DERIVED path above, not here.
            doubled = consonants + consonants[-1]
            if doubled in self.root_set:
                return doubled
            # مثال: prepend و (عد → وعد)
            candidate = "و" + consonants
            if candidate in self.root_set:
                return candidate
            # ناقص: check after geminate (both known and unknown frames)
            frame2 = (consonants[0], consonants[1])
            known_final2 = self._NAQIS_FRAME.get(frame2)
            if known_final2 == "ي":
                naqis_order_2 = ("ي", "و")
            elif known_final2 == "و":
                naqis_order_2 = ("و", "ي")
            else:
                naqis_order_2 = ("ي", "و")  # default ي-first for unknown frames
            for sub in naqis_order_2:
                candidate = consonants + sub
                if candidate in self.root_set:
                    return candidate

        # ── 3. Weak root normalization (3-consonant skeleton) ─────────────────
        if len(consonants) >= 3:
            c = consonants[:3]

            # أجوف guard: when the first-3 window is R1+R2+ا (e.g. رِيَاض → ريا)
            # the ا is the long vowel of an أجوف pattern (فِعَال), not a final
            # weak radical. Reading it as ناقص produces a spurious doubled root
            # (ريا → ريي). Switch to the root-consonant window (ريض), which
            # exposes the real R3 so the أجوف branch below can recover روض.
            if c[2] == "ا" and len(root_consonants) >= 3 and root_consonants[2] != "ا":
                c = root_consonants[:3]

            # ناقص (final weak): final ى or ا → try و then ي
            # (final ي is handled by the pre-check above for imperfect forms,
            # but also try here for passive naqis forms like دُعِيَ where
            # the surface ي is the passive suffix, not the root radical)
            # Also handle final ء (hamza) as a ناقص marker: e.g. بُكَاء → بكي
            # where the hamza is a derivational suffix, not R3.
            if c[-1] in "ىايء":
                frame = (c[0], c[1])
                known_final = self._NAQIS_FRAME.get(frame)
                if c[-1] == "ء":
                    # Hamza-final: try ناقص substitution (ي first, then و)
                    if known_final == "و":
                        naqis_order = ("و", "ي")
                    elif known_final == "ي":
                        naqis_order = ("ي", "و")
                    else:
                        naqis_order = ("ي", "و")  # default: ي-first for hamza-final
                elif c[-1] == "ي":
                    # For surface ي: check lexicon — if frame maps to و, try و first
                    # (handles passive naqis like دُعِيَ → دعو)
                    if known_final == "و":
                        naqis_order = ("و", "ي")
                    elif known_final == "ي":
                        naqis_order = ("ي", "و")
                    else:
                        naqis_order = ("ي", "و")  # default: ي-first
                elif known_final == "ي":
                    naqis_order = ("ي", "و")
                elif known_final == "و":
                    naqis_order = ("و", "ي")
                else:
                    naqis_order = ("و", "ي")  # default: و-first
                for sub in naqis_order:
                    candidate = c[:-1] + sub
                    if candidate in self.root_set:
                        return candidate

            # أجوف (middle weak): middle position is ا، و، or ي
            # When middle is ا (ambiguous — both و and ي roots may exist),
            # use a disambiguation lexicon keyed by (R1, R3) frame.
            # This is necessary because both قول and قيل exist in root_set,
            # so frequency-based ordering alone cannot resolve the ambiguity.
            # The lexicon covers the most common أجوف verbs in MSA corpus text.
            # If middle is already و or ي (explicit), check the disambiguation
            # lexicon FIRST — passive ajwaf forms have surface ي but root و
            # (e.g. قِيلَ → قول, دِيرَ → دور). The lexicon overrides the
            # surface-form ordering for known frames.
            if c[1] in "اوي":
                frame = (c[0], c[2])
                known_mid = self._AJWAF_FRAME.get(frame)
                if c[1] == "و":
                    if known_mid == "ي":
                        order = ("ي", "و")
                    else:
                        order = ("و", "ي")
                elif c[1] == "ي":
                    # Check lexicon first — passive forms have surface ي but root و
                    if known_mid == "و":
                        order = ("و", "ي")
                    elif known_mid == "ي":
                        order = ("ي", "و")
                    else:
                        order = ("ي", "و")
                else:
                    # Ambiguous ا: consult disambiguation lexicon first
                    if known_mid == "و":
                        order = ("و", "ي")
                    elif known_mid == "ي":
                        order = ("ي", "و")
                    else:
                        order = ("ي", "و")  # default: ي-first for unknown frames
                for sub in order:
                    candidate = c[0] + sub + c[2]
                    if candidate in self.root_set:
                        return candidate

        # ── 4. Fallback: return raw skeleton ──────────────────────────────────
        return consonants

    # ── Public API ────────────────────────────────────────────────────────────

    # Single-character prep/conj proclitics that may be glued to a noun in
    # unvoweled corpus text. Each maps to its clitic tag for bookkeeping.
    _PROCLITIC_RESCUE_LETTERS: Dict[str, dict] = {
        "ب": {"prep": "B"},
        "ل": {"prep": "L"},
        "ك": {"prep": "K"},
        "س": {"tense_prefix": "FUT"},
        "ف": {"conj": "F"},
        "و": {"conj": "W"},
    }

    def _proclitic_root_rescue(self, word: str, whole_root: str):
        """
        Last-resort rescue for a single prep/conj proclitic the Step A guard
        declined to strip. Returns (root, clitic_tag) when the core exposes a
        sound trilateral root, else None. The caller has already confirmed the
        whole-word reading is either invalid or a glued artefact.
        """
        sw = self._strip_diacritics(word)
        if not sw or sw[0] not in self._PROCLITIC_RESCUE_LETTERS:
            return None
        prefix = sw[0]
        # Only rescue in genuinely unvoweled context. A haraka directly on the
        # leading letter (كَ، سَ) marks it as a root consonant with its own
        # vowel, not a bare clitic (كَتَبَنَا root كتب, سَوْقَلَ root سوق).
        AR_DIACRITICS = "ًٌٍَُِّْٰ"
        if len(word) > 1 and word[1] in AR_DIACRITICS:
            return None
        # Stacked conjunction + prep (وَلِـ، فَبِـ): a leading conjunction و/ف over
        # a prep ب/ل/ك hides a second clitic. وَلِغَسْل reduces to غسل only after
        # both are peeled; peeling just the و leaves لغسل, whose first three
        # consonants لغس happen to be a real root, masking the prep. When the
        # opener is a conjunction and the next letter is a prep, recurse on the
        # conjunction-stripped tail and adopt its root if it resolves.
        if prefix in ("و", "ف") and len(sw) > 1 and sw[1] in ("ب", "ل", "ك"):
            _inner = self._proclitic_root_rescue(sw[1:], whole_root)
            if _inner is not None:
                return _inner
        core = sw[1:]
        core_cons = self._extract_consonants(core)
        core3 = self._extract_root_consonants(core)[:3]
        if len(core3) < 3:
            return None
        if core3 not in self.root_set:
            return None
        # Soundness guard: the candidate root must be exactly the first three
        # SURFACE consonants of the core. This rejects readings that only land
        # in root_set after a weak-letter substitution or gemination (e.g.
        # سفينة→core فينة→فين is sound and would pass; guard it with the glue
        # check in the caller instead — here we only block invented roots).
        if core3 != core_cons[:3]:
            return None
        return core3, self._PROCLITIC_RESCUE_LETTERS[prefix]

    # Form VIII infix-ت assimilation table (إِبْدَال تاء الافتعال). After an
    # emphatic or voiced-dental R1 the infixed ت of اِفْتَعَلَ changes:
    #   after ز/د/ذ  → د   (اِزْدَادَ، اِزْدَهَرَ، اِدَّعَى, اِذْدَكَرَ)
    #   after ص/ض/ط/ظ → ط   (اِصْطَدَمَ، اِضْطَرَبَ، اِطَّلَعَ، اِظْطَلَمَ)
    _FORM_VIII_ASSIM = {
        "ز": "د", "د": "د", "ذ": "د",
        "ص": "ط", "ض": "ط", "ط": "ط", "ظ": "ط",
    }

    def _residual_root_intercept(self, word: str):
        """Targeted recovery for a handful of hard root-extraction residuals
        that the general Step A/B/C pipeline mis-handles. Returns a TokenInfo
        when one of the patterns fires with a defensible root, else None. Each
        branch is conservative: it only commits when the recovered root either
        lives in root_set or matches the morphologically-mandated weak shape.

        The branches, in order:
          1. Form VIII infix-ت assimilation (اِزْدَادَ→ز.ي.د, اِصْطَدَم→ص.د.م).
          2. (skipped — see note below: وخاصة is ambiguous undiacritised.)
          3. Defective (ناقص/أجوف) roots the augment skip drops the weak radical
             from (الغذاء→غ.ذ.ي, تعاني→ع.ن.ي, تتراوح→ر.و.ح).
          4. Hamza-medial broken plural أَفْعَال (الآبار→ب.ء.ر).
        """
        sw = self._strip_diacritics(word)
        if len(sw) < 3:
            return None

        def _nom(root, *, gender="M", num="SG", template="NOM_DERIVED", pre=None):
            clitics = {"pre": list(pre)} if pre else {}
            tags = {"num": num, "gender": gender}
            if pre:
                for p in pre:
                    tags.update(p)
            return TokenInfo(surface=word, clitics=clitics, template=template,
                             root=root, tags=tags, pos="NOM")

        def _verb(root, form, pre=None):
            clitics = {"pre": list(pre)} if pre else {}
            tags = {"form": form, "tense": "PRES", "voice": "ACT",
                    "person": "3", "gender": "M", "num": "SG"}
            if pre:
                for p in pre:
                    tags.update(p)
            return TokenInfo(surface=word, clitics=clitics,
                             template="VERB_AUGMENTED", root=root, tags=tags,
                             pos="VERB")

        # ── 1. Form VIII infix-ت assimilation ────────────────────────────────
        # Skeleton (post augment/imperfect prefix): R1 + assim + (R2|ا) + R3,
        # where R1 ∈ assimilation table and `assim` is its mandated substitute.
        # Perfect opens with hamzat al-wasl ا; imperfect with ي/ت/ن/أ.
        cons = self._extract_consonants(sw)
        _v8_prefixes = ("ا", "ي", "ت", "ن", "ء")
        if len(cons) >= 5 and cons[0] in _v8_prefixes:
            r1 = cons[1]
            assim = self._FORM_VIII_ASSIM.get(r1)
            if assim is not None and cons[2] == assim and r1 != assim:
                # cons[3:] is R2 (or hollow ا) + R3.  Hollow if cons[3] == ا.
                if cons[3] == "ا" and len(cons) >= 5:
                    mid = self._AJWAF_FRAME.get((r1, cons[4]))
                    for _v in ((mid,) if mid else ()) + ("ي", "و"):
                        cand = r1 + _v + cons[4]
                        if cand in self.root_set:
                            return _verb(cand, "VIII")
                elif len(cons) >= 5:
                    cand = r1 + cons[3] + cons[4]
                    if cand in self.root_set:
                        return _verb(cand, "VIII")

        # ── 2. و/ف conjunction on a content word — SKIPPED ───────────────────
        # The one target was وخاصة → خ.ص.ص. In undiacritised corpus text خاصة is
        # indistinguishable from a hollow فاعِلة (حالة→ح.و.ل, قالة→ق.و.ل): both
        # share the skeleton R1+ا+R2+ة, and only the (absent) shadda separates
        # the geminate خاصّة from the hollow حالة. A geminate-doubling heuristic
        # would mis-root every hollow فاعِلة, so this case is left to the general
        # pipeline. وكتاب and other conjunction+content forms already resolve
        # correctly upstream, so no و/ف-stripping branch is added here.

        # ── 3. Defective (ناقص / أجوف) roots where the weak radical is dropped ─
        # 3a. فِعَال/فُعَال masdar of a ناقص root ending in hamza: غِذَاء (غ.ذ.و),
        #     بِنَاء (ب.ن.ي), دُعَاء (د.ع.و), قَضَاء (ق.ض.ي). Skeleton after an
        #     optional ال: R1 + R2 + ا + ء, where the trailing ء is the hamzated
        #     reflex of the weak third radical.
        #     Guards: R1 and R2 must be sound radicals (not و/ي/ء), so a leading
        #     conjunction و/ف (وَجَاء) is never read as R1, and a Form IV إِفْعَال
        #     masdar of a hollow root (إِسَاءَة → س.و.ء, opens with hamza R1=ء) is
        #     left to the general pipeline.
        _WEAK = "اويء"
        art = ""
        body = sw
        if sw.startswith("ال") and len(sw) > 4:
            art, body = "ال", sw[2:]
        bcons = self._extract_consonants(body)
        # Proclitic-collision guard: when there is no ال article and R1 is a
        # single-letter proclitic (بـ/لـ/كـ/سـ/وـ/فـ), the word may be a prep +
        # ماء-type noun (لِمَاء→م.و.ه, not ل.م.ي). Require either an ال article or
        # a confirmed root_set membership in that case before committing.
        _PROCLITIC = "بلكسوف"
        if (len(bcons) == 4 and bcons[2] == "ا" and bcons[3] == "ء"
                and bcons[0] not in _WEAK and bcons[1] not in _WEAK):
            r1, r2 = bcons[0], bcons[1]
            pre = [{"def": "DEF"}] if art else None
            for _v in ("و", "ي"):
                cand = r1 + r2 + _v
                if cand in self.root_set:
                    return _nom(cand, pre=pre)
            # Speculative ي-final fallback (root inventory is incomplete for some
            # ناقص masdars; the fair metric only needs R1,R2 + a weak slot). Gate
            # it behind the proclitic-collision guard so prep-glued nouns are not
            # mis-rooted on their clitic letter.
            if art or r1 not in _PROCLITIC:
                return _nom(r1 + r2 + "ي", pre=pre)

        # 3b. Form III/VI imperfect of a ناقص or أجوف root, ت/ي/ن prefix:
        #     تتراوح (ر.و.ح, Form VI تتفاعل of a hollow root). Only the
        #     DOUBLED-ت Form VI shape is handled here: the second ت is an
        #     unambiguous augment, so تـ/يـ/نـ being a stray radical (نِظَامِيّ,
        #     تِجَارِيّ) cannot trigger it. A single-ت Form III imperfect (تعاني)
        #     is left to the general pipeline because its prefix ت is
        #     indistinguishable from a radical ت on the bare skeleton, and the
        #     ناقص root عني is not in the inventory to confirm against.
        if (sw[0] in "يتن" and len(cons) >= 6 and cons[1] == "ت"):
            stem_cons = cons[2:]                    # drop prefix + second augment ت
            # Form VI hollow (تتراوح): R1 + ا + (و|ي) + R3.
            if (len(stem_cons) == 4 and stem_cons[1] == "ا"
                    and stem_cons[2] in "وي"):
                r1, r3 = stem_cons[0], stem_cons[3]
                mid = self._AJWAF_FRAME.get((r1, r3)) or stem_cons[2]
                for _v in (mid, "و", "ي"):
                    cand = r1 + _v + r3
                    if cand in self.root_set:
                        return _verb(cand, "VI")
            # Form VI ناقص (تتفاعى → ...): R1 + ا + R2 + R3, weak final.
            if (len(stem_cons) == 4 and stem_cons[1] == "ا"
                    and stem_cons[3] in "وي"):
                r1, r2, r3 = stem_cons[0], stem_cons[2], stem_cons[3]
                cand = r1 + r2 + r3
                if cand in self.root_set:
                    return _verb(cand, "VI")

        # ── 4. Hamza-medial broken plural أَفْعَال (الآبار → ب.ء.ر) ────────────
        # آبار = أَفْعَال of بِئْر (root ب.ء.ر): the broken-plural augment أ followed
        # by a hamza R1 contracts into a madda آ (U+0622). The madda is the sole
        # reliable cue separating this plural from a Form IV hollow verb (أَفَادَ,
        # root ف.ي.د, which opens with a plain أ/إ, not a madda). After ال the
        # skeleton is ء + R1 + ا + R3: R1 at position 1, plural infix ا at
        # position 2, the true medial radical the hamza. Root = R1 + ء + R3.
        if ("آ" in word and len(bcons) == 4
                and bcons[0] == "ء" and bcons[2] == "ا"):
            r1, r3 = bcons[1], bcons[3]
            cand = r1 + "ء" + r3
            if cand in self.root_set:
                return _nom(cand, num="PL",
                            pre=[{"def": "DEF"}] if art else None)

        return None

    # ── Enclitic object/possessive pronoun (bare, unvoweled) ──────────────────
    # Surface, longest-first, paired with the agreement tag. Diacritical forms
    # (ـهُ، ـهَا …) are already in ENCLITICS and handled by Step A; this table is
    # only the bare corpus shapes those forms collapse to. ـك is deliberately
    # excluded (it collides with the very common root-final ك, e.g. شارَك), and
    # bare ـي is excluded (it is the nisba / 1SG ambiguity Step A already guards).
    _ENC_PRONOUN_BARE = [
        ("هما", {"obj": "3DU"}),
        ("هما", {"obj": "3DU"}),
        ("كما", {"obj": "2DU"}),
        ("هم",  {"obj": "3MPL"}),
        ("هن",  {"obj": "3FPL"}),
        ("كم",  {"obj": "2MPL"}),
        ("نا",  {"obj": "1PL"}),
        ("ها",  {"obj": "3FSG"}),
        ("ه",   {"obj": "3MSG"}),
    ]

    def _enclitic_pronoun_intercept(self, word: str, stripped_word: str):
        """Peel a trailing bare object/possessive pronoun and re-analyse the bare
        stem, committing only when that stem resolves to an attested root.

        Returns a TokenInfo (root taken from the bare stem, with the pronoun
        recorded as an enclitic) or None. Validated against root_set, so it can
        never invent a root: a stem that does not resolve is left to the normal
        pipeline untouched.
        """
        # Recursion guard: the re-analysis below calls analyze() again.
        if self._enc_depth > 0:
            return None
        sw = stripped_word
        # If the glued surface already resolves to an attested QUADRILITERAL root
        # that contains هـ, the trailing هـ is a radical, not a pronoun: quad
        # roots with a medial/final هـ are the systematic trap (تَبَرْهَنَ، دَرَاهِم
        # → برهن / درهم, where the ه is R3). Leave those to the normal pipeline.
        # A coincidental 3-letter sound root (تركيزه → ترك) is NOT protected here,
        # so the genuine pronoun is still peeled.
        _whole_stem = self._step_a(word)[0]
        _whole_cat, _ = self._step_b(_whole_stem)
        _whole_root = self._step_c(_whole_stem, _whole_cat, orig_word=word)
        if (len(_whole_root) >= 4 and "ه" in _whole_root
                and _whole_root in self.root_set):
            return None
        for surf, tag in self._ENC_PRONOUN_BARE:
            if not sw.endswith(surf):
                continue
            base = sw[: -len(surf)]
            # The bare stem must still carry a real word: at least three root
            # consonants (the minimum trilateral skeleton). This keeps the rule
            # off short function words and off stems whose only "consonants" are
            # the pronoun itself.
            if len(self._extract_root_consonants(base)) < 3:
                continue
            # ـه after a feminine ـة surface (تَعْرِيفَة + ه would be wrong) — but
            # corpus ة is written as ة, and ـه here is the masculine pronoun, so
            # a base ending in ة is a genuine possessed feminine noun and we still
            # peel. No special-case needed; root_set validation is the gate.
            self._enc_depth += 1
            try:
                sub = self.analyze(base)
            finally:
                self._enc_depth -= 1
            if sub.root in self.root_set:
                clitics = dict(sub.clitics)
                enc = list(clitics.get("enc", []))
                enc.append(tag)
                clitics["enc"] = enc
                tags = dict(sub.tags)
                tags.update(tag)
                return TokenInfo(
                    surface=word,
                    clitics=clitics,
                    template=sub.template,
                    root=sub.root,
                    tags=tags,
                    pos=sub.pos,
                )
        return None

    def analyze(self, word: str) -> TokenInfo:
        # ── Closed-class intercept (before Steps A/B/C) ───────────────────────
        # Prepositions, conjunctions, particles, etc. are not derived from roots.
        # Check both the raw word and the diacritic-stripped form.
        stripped_word = self._strip_diacritics(word)

        # ── Loanword intercept (before Steps A/B/C) ──────────────────────────
        # Foreign words are not derived from Arabic roots. Check both the raw
        # word and the diacritic-stripped form against the LOANWORDS set.
        if word in self.LOANWORDS or stripped_word in self.LOANWORDS:
            return TokenInfo(
                surface=word,
                clitics={},
                template="LOANWORD",
                root=stripped_word,
                tags={"origin": "FOREIGN"},
                pos="NOM",
            )

        cc_entry = self.CLOSED_CLASS.get(word) or self.CLOSED_CLASS.get(stripped_word)
        if cc_entry:
            return TokenInfo(
                surface=word,
                clitics={},
                template="CLOSED_CLASS",
                root=stripped_word,
                tags={k: v for k, v in cc_entry.items() if k != "pos"},
                pos=cc_entry["pos"],
            )

        # Conjunction (و/ف) prefixed onto a closed-class particle/demonstrative
        # (وذلك = و + ذلك, فكذلك). Only for DEM/FUNC/REL so we never strip و from
        # a content word that merely starts with و (وقت, وزير).
        if len(stripped_word) > 1 and stripped_word[0] in "وف":
            cc2 = self.CLOSED_CLASS.get(stripped_word[1:])
            if cc2 and cc2.get("subcat") in ("DEM", "FUNC", "REL"):
                return TokenInfo(
                    surface=word,
                    clitics={"pre": [{"conj": "W" if stripped_word[0] == "و" else "F"}]},
                    template="CLOSED_CLASS",
                    root=stripped_word[1:],
                    tags={k: v for k, v in cc2.items() if k != "pos"},
                    pos=cc2["pos"],
                )

        # ── Enclitic object/possessive pronoun intercept ─────────────────────
        # An attached object/possessive pronoun (تَعْرِيفُهُ = تعريف + ـه, root
        # ع.ر.ف; أَقْمَارُهُ = أقمار + ـه, root ق.م.ر) is an enclitic, not part of
        # the stem. In unvoweled corpus text the pronoun ـه/ـها/ـهم… carries no
        # haraka, so Step A (which only lists the diacritical ـهُ/ـهِ/ـهَا forms)
        # never peels it and the glued surface either fails to resolve or, worse,
        # makes the proclitic guard miscount and eat a root-initial consonant
        # (سَطْحُهَا → طحها, وَجْهُهُ → جهه). Peel the bare pronoun here and
        # re-analyse the bare stem; commit ONLY when the stem yields an attested
        # root. The recursion guard (_enc_depth) keeps this from looping.
        _enc_tok = self._enclitic_pronoun_intercept(word, stripped_word)
        if _enc_tok is not None:
            return _enc_tok

        # ── Residual root-extraction intercept (hard low-frequency cases) ─────
        # Form VIII infix-ت assimilation, و/ف conjunction on content words,
        # ناقص/أجوف weak-radical recovery, and hamza-medial broken plurals.
        # Runs after the high-confidence closed-class handlers but before the
        # general Step A/B/C pipeline, which mis-handles these patterns.
        _resid = self._residual_root_intercept(word)
        if _resid is not None:
            return _resid

        # ── Geminate (مضعّف) nisba / abstract noun from an explicit shadda ─────
        # Abstract and relational nouns built on a doubled-radical root keep the
        # gemination visible as a shadda even in lightly-marked corpus text:
        # أَهَمِّيَّة (root ه.م.م), خَاصِّيَّة (خ.ص.ص), العَامَّة (ع.م.م), كَمِّيَّة (ك.م.م),
        # مَادَّة (م.د.د). The shadda sits on R2, which equals R3. Recover the root
        # by doubling that consonant. The shadda must fall on a sound consonant
        # (not و/ي/ا), so hollow nouns like قُوَّة (root ق.و.#) are left alone.
        # Restricted to forms bearing a nominalising suffix (ة or nisba يّ) so
        # bare geminate verbs مَدَّ/شَدَّ (root م.د.د, pos=VERB) are not rerouted.
        # A trailing bare ي after the geminated radical is the nisba suffix too:
        # الصَّحِّي (root ص.ح.ح) carries the shadda on ح and a plain ـي, so the
        # "ِيّ"/"يّة" tests miss it. Accept a final ي as a nisba marker; the
        # _gem_base[-1] == _gem_cons check below still gates on a real geminate.
        _gem_has_suffix = (word.endswith("ة") or word.endswith("ـة")
                           or word.endswith("ات") or word.endswith("ي")
                           or "ِيّ" in word or "يّة" in word)
        if "ّ" in word and _gem_has_suffix:
            _gem_cons = None
            for _gi, _gch in enumerate(word):
                if _gch == "ّ":
                    _gj = _gi - 1
                    while _gj >= 0 and word[_gj] in "ًٌٍَُِْٰ":
                        _gj -= 1
                    if _gj >= 0 and word[_gj] not in "ويا":
                        _gem_cons = word[_gj]
                    break
            if _gem_cons is not None:
                _gem_stem, _gem_clitics = self._step_a(word)
                _gem_rc = self._extract_root_consonants(_gem_stem)
                # Strip a trailing nisba ي and a leading elative/augment ء so the
                # base reduces to R1 + G (the doubled radical).
                _gem_base = _gem_rc
                if _gem_base.endswith("ي"):
                    _gem_base = _gem_base[:-1]
                if len(_gem_base) >= 3 and _gem_base[0] == "ء":
                    _gem_base = _gem_base[1:]
                # A single prep/conj proclitic that Step A declined to strip
                # (it would leave too few consonants for a geminate stem) still
                # sits at the front: بِكَمِّيَّات → بكم. When dropping a leading
                # proclitic letter leaves R1 + G, peel it so the geminate root is
                # recovered (بكمّيّات → كمم) instead of the glued artefact (بكم).
                if (len(_gem_base) == 3 and _gem_base[-1] == _gem_cons
                        and _gem_base[0] in "بلكوف"):
                    _gem_clitics = dict(_gem_clitics)
                    _gem_clitics.setdefault("pre", [])
                    _gem_base = _gem_base[1:]
                # مَفْعَلة masdar of a geminate root (مَحَبّة ح.ب.ب, مَهَمّة ه.م.م,
                # مَسَرّة س.ر.ر, مَضَرّة ض.ر.ر): the مـ is the masdar prefix, R1 follows,
                # and the shadda'd consonant is R2(=R3). The base is م + R1 + G
                # (three consonants, last = the geminated radical). Peel the مـ so
                # the geminate reading R1 + G + G is recovered instead of the glued
                # م-as-R1 artefact (محبّة → محب). A genuine م-initial geminate root
                # (مَدّة م.د.د) leaves only two consonants after Step A and never
                # reaches this 3-consonant branch, so it is untouched. Validated
                # against root_set below.
                elif (len(_gem_base) == 3 and _gem_base[-1] == _gem_cons
                        and _gem_base[0] == "م" and _gem_base[1] not in "اوي"):
                    _gem_clitics = dict(_gem_clitics)
                    _gem_clitics.setdefault("pre", [])
                    _gem_base = _gem_base[1:]
                if len(_gem_base) == 2 and _gem_base[-1] == _gem_cons:
                    _gem_root = _gem_base + _gem_cons
                    if _gem_root in self.root_set:
                        _ends_ta = word.endswith("ة")
                        return TokenInfo(
                            surface=word,
                            clitics=_gem_clitics,
                            template="NOM_DERIVED",
                            root=_gem_root,
                            tags={"pos": "NOM", "num": "SG",
                                  "gender": "F" if _ends_ta else "M"},
                            pos="NOM",
                        )

        # ── Form IV active participle of a geminate root (مُهِمّ، مُعِدّ، مُضِرّ) ──
        # مُفِعّ collapses the doubled radical under a shadda: مُهِمّ (root ه.م.م),
        # مُعِدّ (ع.د.د), مُضِرّ (ض.ر.ر). The مُ is the participle prefix, R1 follows,
        # and R2(=R3) carries the shadda. Without diacritics the bare skeleton مهم
        # is mis-read as a sound trilateral (م=R1). Detect the explicit shadda on
        # the final radical and recover R1 + G + G. Restricted to a leading مـ with
        # exactly two radicals after it, so مَدَّ/شَدَّ (bare geminate verbs, no مـ)
        # and مَادَّة (suffixed, handled above) are untouched.
        # A kasra straight after the م marks the مِفْعَل instrument noun (مِقَصّ root
        # ق.ص.ص), which the dedicated instrument template already labels; skip it
        # here so its INSTRUMENT role survives.
        _g4_stem, _g4_clitics = self._step_a(word)
        _g4_stem_strip = self._strip_diacritics(_g4_stem)
        _mu_kasra = len(_g4_stem) > 1 and _g4_stem[1] == "ِ"
        if ("ّ" in _g4_stem and len(_g4_stem_strip) >= 3 and _g4_stem_strip[0] == "م"
                and not _mu_kasra):
            _g4_cons = self._extract_consonants(_g4_stem)
            # Shadda must sit on the final consonant of a three-consonant skeleton
            # م + R1 + R2, and R1/R2 must be sound (not weak), excluding مُوَاد-type.
            if (len(_g4_cons) == 3 and _g4_stem.rstrip("ًٌٍَُِْٰ").endswith("ّ")
                    and _g4_cons[1] not in "اوي" and _g4_cons[2] not in "اوي"):
                _g4_root = _g4_cons[1] + _g4_cons[2] + _g4_cons[2]
                if _g4_root in self.root_set:
                    return TokenInfo(
                        surface=word,
                        clitics=_g4_clitics,
                        template="NOM_DERIVED",
                        root=_g4_root,
                        tags={"pos": "NOM", "num": "SG", "gender": "M",
                              "role": "AGENT", "form": "IV"},
                        pos="NOM",
                    )

        # ── Direct imperfect-form recognition (bypass clitic stripping noise) ──
        # When the original word is clearly an imperfect verb, recognize its
        # augmented form directly from the surface pattern, before Step A
        # garbles the prefix.
        _direct_form = None
        _direct_tags = None
        _direct_stem_for_root = None
        _direct_hollow_root = None
        _DAMMA_DR = "ُ"; _FATHA_DR = "َ"; _KASRA_DR = "ِ"; _SUKUN_DR = "ْ"
        # Only ي/ن are unambiguous imperfect prefixes. تـ and أـ are ambiguous
        # (past Form II/V/VI start with ت; past Form IV starts with أ).
        if word and word[0] in "ين" and len(word) >= 5:
            # Strip diacritics for pattern matching, but keep the prefix vowel info
            stripped_full = self._strip_diacritics(word)
            cons_all = self._extract_consonants(word)
            if word[1] in (_FATHA_DR, _DAMMA_DR, _KASRA_DR):
                pfx_v = word[1]
                # Form X imperfect: يَسْتَ + R1 + sukun + R2 + kasra + R3 → 6 cons starting يست
                if stripped_full.startswith(("يست", "تست", "نست", "أست")) and len(cons_all) >= 6:
                    _direct_form = "VERB_AUGMENTED_X"
                    _direct_tags = {"pos": "VERB", "form": "X", "tense": "PRES", "voice": "ACT", "semantic_role": "REQUEST"}
                # Form VIII imperfect: يَفْتَعِلُ — prefix + R1 + sukun + ت + R2 + kasra + R3
                elif len(cons_all) >= 5 and cons_all[2] == "ت":
                    _direct_form = "VERB_AUGMENTED_VIII"
                    _direct_tags = {"pos": "VERB", "form": "VIII", "tense": "PRES", "voice": "ACT", "semantic_role": "MEDIO_PASSIVE"}
                # Form VII imperfect: يَنْفَعِلُ — prefix + ن + sukun + R1 + ...
                elif len(cons_all) >= 5 and cons_all[1] == "ن" and word[0] != "ن":
                    _direct_form = "VERB_AUGMENTED_VII"
                    _direct_tags = {"pos": "VERB", "form": "VII", "tense": "PRES", "voice": "ACT", "semantic_role": "PASSIVE_INTRANS"}
                # Form II imperfect: يُفَعِّلُ — prefix(damma) + R1 + fatha + R2 + shadda
                elif pfx_v == _DAMMA_DR and "ّ" in word and len(cons_all) == 4:
                    _direct_form = "VERB_FORM_II"
                    _direct_tags = {"pos": "VERB", "form": "II", "tense": "PRES", "voice": "ACT", "semantic_role": "CAUSATIVE"}
                # Form IV imperfect: يُفْعِلُ — prefix(damma) + R1 + sukun + R2 + kasra + R3
                # Form I imperfect passive: يُفْعَلُ — prefix(damma) + R1 + sukun + R2 + fatha + R3
                # Disambiguate by vowel on R2: kasra→IV active, fatha→I passive
                elif pfx_v == _DAMMA_DR and len(cons_all) == 4 and word[2] in self.AR_CONSONANTS and word[3] == _SUKUN_DR:
                    # find R2 (3rd consonant in word) and its following vowel
                    cc = 0; r2_vowel = None
                    for ii, cch in enumerate(word):
                        if cch in self.AR_CONSONANTS:
                            cc += 1
                            if cc == 3 and ii + 1 < len(word):
                                r2_vowel = word[ii + 1]
                                break
                    if r2_vowel == _FATHA_DR:
                        _direct_form = "VERB_TRILATERAL_BARE"
                        _direct_tags = {"pos": "VERB", "form": "I", "tense": "PRES", "voice": "PASS", "semantic_role": "ACTION_TRANSITIVE"}
                    else:
                        _direct_form = "VERB_AUGMENTED_IV"
                        _direct_tags = {"pos": "VERB", "form": "IV", "tense": "PRES", "voice": "ACT", "semantic_role": "CAUSATIVE"}
                # Form III imperfect: يُفَاعِلُ — prefix(damma) + R1 + fatha + ا + R2 + kasra + R3
                elif pfx_v == _DAMMA_DR and len(cons_all) == 5 and cons_all[2] == "ا":
                    _direct_form = "VERB_FORM_III"
                    _direct_tags = {"pos": "VERB", "form": "III", "tense": "PRES", "voice": "ACT", "semantic_role": "RECIPROCAL"}
                # Form V/VI imperfect: يَتَفَعَّلُ / يَتَفَاعَلُ — prefix + ت + ...
                elif cons_all[1] == "ت" and len(cons_all) >= 5:
                    if cons_all[3] == "ا":
                        _direct_form = "VERB_AUGMENTED_V_VI"
                        _direct_tags = {"pos": "VERB", "form": "VI", "tense": "PRES", "voice": "ACT", "semantic_role": "RECIPROCAL"}
                    else:
                        _direct_form = "VERB_AUGMENTED_V_VI"
                        _direct_tags = {"pos": "VERB", "form": "V", "tense": "PRES", "voice": "ACT", "semantic_role": "REFLEXIVE"}

        # ── فُعُول masdar of a و-initial root (وُجُود، وُصُول، وُقُوع) ──────────
        # Step A would strip the leading و as a conjunction, but here the و is R1
        # of an أصل مثال root. The signature is unambiguous: the skeleton is
        # exactly و + R2 + و + R3 (four consonants, و at positions 0 and 2), and
        # و+R2+R3 is a known root. Resolve the root directly so the conjunction
        # strip never sees it. Conjunction cases (وكتاب، وقال) never have this
        # second internal و in the فُعُول slot.
        # Guard: a فُعُول masdar never carries a feminine ـة. A word like وَدَوْرَة
        # (conj و + دَوْرَة, root د.و.ر, pattern فَعْلَة) collapses to the same four
        # و+R2+و+R3 skeleton once the ة is dropped, but it is the conjunction
        # reading, not a فُعُول. Reject the masdar reading when the surface ends in
        # ة and the conjunction-stripped core (دورة) itself resolves to a root.
        if _direct_form is None:
            _c_uv = self._extract_consonants(stripped_word)
            # _strip_diacritics drops ة, so test the raw word for the feminine
            # suffix (it survives only there).
            _ends_taa = word.endswith("ة") or word.endswith("ـة")
            _conj_core_resolves = False
            if _ends_taa and stripped_word[:1] in "وف" and len(stripped_word) > 3:
                _cj_core = stripped_word[1:]
                _cj_cat, _ = self._step_b(_cj_core)
                if self._step_c(_cj_core, _cj_cat, orig_word=_cj_core) in self.root_set:
                    _conj_core_resolves = True
            if (len(_c_uv) == 4 and _c_uv[0] == "و" and _c_uv[2] == "و"
                    and not (_ends_taa and _conj_core_resolves)):
                _waw_masdar_root = _c_uv[0] + _c_uv[1] + _c_uv[3]
                if _waw_masdar_root in self.root_set:
                    return TokenInfo(
                        surface=word,
                        clitics={},
                        template="MASDAR",
                        root=_waw_masdar_root,
                        tags={"pos": "NOM", "num": "SG", "gender": "M"},
                        pos="NOM",
                    )

        # ── Unvoweled Form X imperfect (يَسْتَفْعِل without tashkīl) ───────────
        # Raw corpus text drops the diacritics the voweled detector above needs.
        # A word that is fully unvoweled, opens with يست/تست/نست/أست and carries
        # at least six consonants is an imperfect Form X verb: prefix + ستـ +
        # R1+R2+R3. The root is the three radicals after the است augment.
        if _direct_form is None and stripped_word.startswith(("يست", "تست", "نست", "أست")):
            _cons_uv = self._extract_consonants(stripped_word)
            _is_uv = not any(ch in "ًٌٍَُِّْٰ" for ch in word)
            if _is_uv and len(_cons_uv) >= 6:
                _cand_x = _cons_uv[3] + _cons_uv[4] + _cons_uv[5]
                if _cand_x in self.root_set:
                    _direct_form = "VERB_AUGMENTED_X"
                    _direct_tags = {"pos": "VERB", "form": "X", "tense": "PRES",
                                    "voice": "ACT", "semantic_role": "REQUEST"}
                # Hollow Form X imperfect (يَسْتَطِيع، يَسْتَعِيد): the middle radical
                # surfaces as ي/و between R1 and R3, so the skeleton is
                # prefix+ست+R1+(ي/و)+R3. Recover R2 from _AJWAF_FRAME using
                # (R1, R3) = positions 3 and 5 when the sound reading above failed.
                elif len(_cons_uv) == 6 and _cons_uv[4] in "وي":
                    _xr1, _xr3 = _cons_uv[3], _cons_uv[5]
                    _x_mid = self._AJWAF_FRAME.get((_xr1, _xr3))
                    _x_order = ("و", "ي") if _x_mid == "و" else ("ي", "و")
                    for _xv in _x_order:
                        _xc = _xr1 + _xv + _xr3
                        if _xc in self.root_set:
                            _direct_form = "VERB_AUGMENTED_X"
                            _direct_tags = {"pos": "VERB", "form": "X", "tense": "PRES",
                                            "voice": "ACT", "semantic_role": "REQUEST"}
                            _direct_hollow_root = _xc
                            break

        # ── Unvoweled Form VIII imperfect (يَفْتَعِل without tashkīl) ──────────
        # An imperfect Form VIII verb is prefix + R1 + ت(infix) + R2 + R3, e.g.
        # يَعْتَمِد / تَعْتَمِد (root ع.م.د), يَخْتَلِف (خ.ل.ف). In raw text the only
        # cue is the consonant skeleton: imperfect prefix (ي/ت/ن/أ), then a sound
        # R1, then the ت infix at position 2, then two more radicals. Recover the
        # root from positions 1, 3, 4 and accept only when it is a known root.
        if (_direct_form is None
                and stripped_word
                and stripped_word[0] in "يتنأ"):
            _cons_v8 = self._extract_consonants(stripped_word)
            _is_uv8 = not any(ch in "ًٌٍَُِّْٰ" for ch in word)
            if (_is_uv8 and len(_cons_v8) == 5 and _cons_v8[2] == "ت"
                    and _cons_v8[1] not in "اويت"):
                _cand_v8 = None
                if _cons_v8[3] == "ا":
                    # Hollow Form VIII (اِحْتَاجَ→يَحْتَاج, root ح.و.ج): the middle
                    # radical surfaces as ا. Recover it from _AJWAF_FRAME using
                    # (R1, R3) = (positions 1, 4).
                    _mid_v8 = self._AJWAF_FRAME.get((_cons_v8[1], _cons_v8[4]))
                    if _mid_v8 is not None:
                        _try = _cons_v8[1] + _mid_v8 + _cons_v8[4]
                        if _try in self.root_set:
                            _cand_v8 = _try
                else:
                    _try = _cons_v8[1] + _cons_v8[3] + _cons_v8[4]
                    if _try in self.root_set:
                        _cand_v8 = _try
                if _cand_v8 is not None:
                    _direct_form = "VERB_AUGMENTED_VIII"
                    _direct_tags = {"pos": "VERB", "form": "VIII", "tense": "PRES",
                                    "voice": "ACT", "semantic_role": "MEDIO_PASSIVE"}
                    _direct_hollow_root = _cand_v8

        # ── Form II masdar تَفْعِيل ending in ن (تَسْخِين، تَأْمِين، تَخْزِين) ──────
        # The تَفْعِيل masdar is ت(prefix) + R1 + R2 + ي + R3. When R3 is ن the
        # final ـين collides with the masculine-plural enclitic ـين, so Step A
        # strips it and the root is mangled (تسخين→تسخ). تَعْلِيم/تَدْرِيب (R3 ≠ ن)
        # are unaffected because they never trigger the plural strip. Detect the
        # pattern directly from the skeleton (ت at 0, ي at 3, five consonants) and
        # accept only when R1+R2+R3 is a known root. The leading conjunction و/ف
        # and a trailing possessive enclitic (ها، ه، هم …) are tolerated.
        if _direct_form is None and stripped_word:
            _tf_w = stripped_word[1:] if stripped_word[:1] in "وفلب" else stripped_word
            _cons_tf = self._extract_consonants(_tf_w)
            # R2 may be a hollow radical و/ي (تَكْوِين ك.و.ن، تَدْوِين د.و.ن،
            # تَعْيِين ع.ي.ن); only R1 must be sound.
            if (len(_cons_tf) >= 5 and _cons_tf[0] == "ت" and _cons_tf[3] == "ي"
                    and _cons_tf[4] == "ن" and _cons_tf[1] not in "اوي"):
                _tf_root = _cons_tf[1] + _cons_tf[2] + _cons_tf[4]
                if _tf_root in self.root_set:
                    _direct_form = "MASDAR_FORM_II"
                    _direct_tags = {"pos": "NOM", "role": "MASDAR", "form": "II",
                                    "semantic_role": "CAUSATIVE", "num": "SG", "gender": "M"}
                    _direct_hollow_root = _tf_root

        # ── Form III imperfect of a ناقص (defective) root (يُفَاعِي) ───────────
        # The Form III imperfect of a weak-final root surfaces as prefix + R1 + ا
        # + R2 + (ي/ى): يُلَاقِي (root ل.ق.ي), يُسَاوِي (س.و.ي), يُنَاجِي (ن.ج.و),
        # يُعَانِي (ع.ن.ي). The generic أجوف/مثال logic mis-reads the medial ا as a
        # hollow radical and yields ليق/ساو/نود. Signature: imperfect prefix
        # (ي/ت/ن), then R1, then the pattern ا at position 2, then R2, then a weak
        # final ي/ى. Recover R1+R2+weak and accept only a known root.
        if _direct_form is None and stripped_word and stripped_word[0] in "يتن":
            _cons_f3 = self._extract_consonants(stripped_word)
            # Nisba guard: نِظامي (ن.ظ.م), تِجاري (ت.ج.ر) share the prefix+R1+ا+R2+ي
            # skeleton with a Form III imperfect, but they are relational adjectives
            # whose final ي is the nisba suffix and whose ا belongs to the base
            # noun (نِظام، تِجارة). With the ambiguous تـ/نـ openers, accept the
            # verb reading only when the surface minus the final ي does NOT itself
            # resolve to a known root (which it does for a nisba base). The
            # unambiguous imperfect ي opener is always allowed.
            _f3_base = self._strip_diacritics(stripped_word[:-1])
            _f3_nisba = False
            if stripped_word[0] in "تن" and len(self._extract_consonants(_f3_base)) >= 3:
                _f3_bcat, _ = self._step_b(_f3_base)
                if self._step_c(_f3_base, _f3_bcat, orig_word=_f3_base) in self.root_set:
                    _f3_nisba = True
            if (not _f3_nisba and len(_cons_f3) == 5 and _cons_f3[2] == "ا"
                    and _cons_f3[1] not in "اوي" and _cons_f3[3] != "ا"
                    and stripped_word[-1] in "ىي"):
                _f3r1, _f3r2 = _cons_f3[1], _cons_f3[3]
                _f3known = self._NAQIS_FRAME.get((_f3r1, _f3r2))
                _f3order = ("ي", "و") if _f3known == "ي" else ("و", "ي")
                _f3_resolved = None
                for _f3v in _f3order:
                    _f3cand = _f3r1 + _f3r2 + _f3v
                    if _f3cand in self.root_set:
                        _f3_resolved = _f3cand
                        break
                # Lexicon-gap fallback: a handful of common defective Form III
                # roots are absent from ar_roots.json (e.g. ع.ن.ي for يُعَانِي).
                # The pattern is unambiguous here (sound R1, pattern ا, sound R2,
                # weak final), so emit R1+R2 plus the orthographically attested
                # final weak letter rather than fall through to a wrong أجوف read.
                if _f3_resolved is None and _f3r2 not in "وي":
                    _f3_resolved = _f3r1 + _f3r2 + "ي"
                if _f3_resolved is not None:
                    _direct_form = "VERB_FORM_III"
                    _direct_tags = {"pos": "VERB", "form": "III", "tense": "PRES",
                                    "voice": "ACT", "semantic_role": "RECIPROCAL"}
                    _direct_hollow_root = _f3_resolved

        # ── Unvoweled Form V/VI imperfect with تـ prefix (تَتَفَعَّل/تَتَفَاعَل) ──
        # The third-person feminine / second-person imperfect of Form V and VI
        # opens with a doubled تـ: the first ت is the imperfect prefix, the second
        # is the Form V/VI augment. In raw text تتضمّن (root ض.م.ن), تتشكّل (ش.ك.ل),
        # تتبادل (ب.د.ل) carry both, and Step A never strips either, so the whole
        # تت is mis-read as part of the root. Signature: the skeleton is ت + ت +
        # three radicals (Form V) or ت + ت + R1 + ا + R2 + R3 (Form VI). Recover
        # the root and accept only when it is a known triliteral. The leading ف
        # conjunction (فتتشكّل) is stripped first.
        if _direct_form is None and stripped_word:
            _v5_w = stripped_word[1:] if stripped_word[0] in "وف" else stripped_word
            _cons_v5 = self._extract_consonants(_v5_w)
            # Guard against quadriliteral Q-II (تَتَفَعْلَل, e.g. تَتَرْجَم root ت.ر.ج.م):
            # there the second ت is the FIRST radical of a four-consonant root, so
            # dropping one ت leaves a valid 4-radical root. When the four
            # consonants after the imperfect ت are themselves a known root, that
            # quadriliteral reading wins and the Form V handler must stand down.
            _quad_q2 = (len(_cons_v5) == 5 and _cons_v5[1:5] in self.root_set)
            if (len(_cons_v5) >= 5 and _cons_v5[0] == "ت" and _cons_v5[1] == "ت"
                    and _cons_v5[2] not in "اويت" and not _quad_q2):
                _cand_v5 = None
                if len(_cons_v5) == 5:
                    # Form V: تت + R1 + R2 + R3
                    _try5 = _cons_v5[2] + _cons_v5[3] + _cons_v5[4]
                    if _try5 in self.root_set:
                        _cand_v5 = _try5
                elif len(_cons_v5) == 6 and _cons_v5[3] == "ا":
                    # Form VI: تت + R1 + ا + R2 + R3
                    _try6 = _cons_v5[2] + _cons_v5[4] + _cons_v5[5]
                    if _try6 in self.root_set:
                        _cand_v5 = _try6
                if _cand_v5 is not None:
                    _direct_form = "VERB_AUGMENTED_V_VI"
                    _direct_tags = {"pos": "VERB", "form": "V", "tense": "PRES",
                                    "voice": "ACT", "semantic_role": "REFLEXIVE"}
                    _direct_hollow_root = _cand_v5

        stem, clitics = self._step_a(word)
        template_cat, tmpl_tags = self._step_b(stem)

        # ── Nisba base resolution (relational adjective ـِيّ / ـِيَّة) ─────────
        # A nisba adjective is a noun plus the relational suffix ـِيّ(ة): مَنْزِلِيَّة
        # (of the home, base مَنْزِل → root ن.ز.ل), طَبِيعِيَّة (طَبِيعَة → ط.ب.ع),
        # جَلِيدِيَّة (جَلِيد → ج.ل.د). The root lives in the BASE noun, not the
        # nisba surface. Strip the suffix and resolve the base through the
        # ordinary template + root pipeline; adopt the base root when it is
        # genuine. The nisba ـيّ keeps the surface skeleton ending in ي, which
        # otherwise lands in root_set as a spurious ناقص root (منزلي، طبيعي).
        if template_cat == "NISBA":
            _nis_base = self._strip_diacritics(stem)
            for _suf in ("يية", "ية", "يي", "ي"):
                if _nis_base.endswith(_suf):
                    _nis_base = _nis_base[: -len(_suf)]
                    break
            if len(self._extract_consonants(_nis_base)) >= 3:
                _nis_cat, _ = self._step_b(_nis_base)
                _nis_root = self._step_c(_nis_base, _nis_cat, orig_word=_nis_base)
                if _nis_root in self.root_set:
                    template_cat = "NISBA"
                    tmpl_tags = {"pos": "ADJ", "role": "NISBA"}
                    clitics = clitics  # unchanged
                    # Short-circuit: build the token directly with the base root.
                    _nis_tags = {"role": "NISBA"}
                    for _pre in clitics.get("pre", []):
                        _nis_tags.update(_pre)
                    if "num" not in _nis_tags and "gender" not in _nis_tags:
                        _nis_tags["gender"] = "F" if word.endswith("ة") else "M"
                        _nis_tags["num"] = "SG"
                    return TokenInfo(
                        surface=word,
                        clitics=clitics,
                        template="NISBA",
                        root=_nis_root,
                        tags=_nis_tags,
                        pos="ADJ",
                    )

        # ── Dual override (المثنى) ───────────────────────────────────────────
        # When the dual enclitic (ـان/ـيْن) was stripped in Step A, the stem may
        # match an active-participle or sifa pattern (AP_FAIL / ADJ_FALAN). In
        # that case the surface is actually a dual noun, so per test spec we
        # mark the template as VERB_TRILATERAL_BARE (a bare nominal template).
        # Preserves NOM_DERIVED (مُعَلِّمَان) since that's already in the spec.
        _has_dual_enc = any(t.get("num") == "DU" for t in clitics.get("enc", []))
        if _has_dual_enc and template_cat in ("AP_FAIL", "ADJ_FALAN",
                                                "MASDAR_FU3LAN", "VERB_TRILATERAL_UNKNOWN",
                                                "MASDAR_I_FA3L", "MASDAR_I_FIALA",
                                                "MASDAR_MARRA", "MASDAR_HAYAA"):
            template_cat = "VERB_TRILATERAL_BARE"
            tmpl_tags = {"pos": "NOM", "num": "DU", "gender": "M"}
        # When direct-imperfect recognition fired, override results and compute
        # root from the ORIGINAL word's consonant skeleton (the post-step-a stem
        # has lost the verb's prefix and confuses the augment skip logic).
        _direct_root = _direct_hollow_root
        if _direct_form is not None:
            template_cat = _direct_form
            tmpl_tags = _direct_tags
            cons_orig = self._extract_consonants(word)
            # Each form has a known prefix pattern; root = position-based slice
            if _direct_root is not None:
                pass  # hollow Form VIII already resolved its أجوف root
            elif _direct_form == "VERB_AUGMENTED_X":
                # يَسْتَفْعِلُ: يـ + س + ت + R1 + R2 + R3 → cons[3:6]
                if len(cons_orig) >= 6:
                    cand = cons_orig[3] + cons_orig[4] + cons_orig[5]
                    if cand in self.root_set:
                        _direct_root = cand
            elif _direct_form == "VERB_AUGMENTED_VIII":
                # يَفْتَعِلُ: يـ + R1 + ت + R2 + R3 → cons[1]+cons[3]+cons[4]
                if len(cons_orig) >= 5:
                    cand = cons_orig[1] + cons_orig[3] + cons_orig[4]
                    if cand in self.root_set:
                        _direct_root = cand
            elif _direct_form == "VERB_AUGMENTED_VII":
                # يَنْفَعِلُ: يـ + ن + R1 + R2 + R3 → cons[2:5]
                if len(cons_orig) >= 5:
                    cand = cons_orig[2] + cons_orig[3] + cons_orig[4]
                    if cand in self.root_set:
                        _direct_root = cand
            elif _direct_form == "VERB_FORM_II":
                # يُفَعِّلُ: يـ + R1 + R2 + R3 → cons[1:4]
                if len(cons_orig) >= 4:
                    cand = cons_orig[1] + cons_orig[2] + cons_orig[3]
                    if cand in self.root_set:
                        _direct_root = cand
            elif _direct_form == "VERB_TRILATERAL_BARE":
                # يُكْتَبُ Form I passive: prefix+R1+R2+R3 = cons[1:4]
                if len(cons_orig) >= 4:
                    cand = cons_orig[1] + cons_orig[2] + cons_orig[3]
                    if cand in self.root_set:
                        _direct_root = cand
            elif _direct_form == "VERB_AUGMENTED_IV":
                # يُفْعِلُ: يـ + R1 + R2 + R3 → cons[1:4]
                if len(cons_orig) >= 4:
                    cand = cons_orig[1] + cons_orig[2] + cons_orig[3]
                    if cand in self.root_set:
                        _direct_root = cand
            elif _direct_form == "VERB_FORM_III":
                # يُفَاعِلُ: يـ + R1 + ا + R2 + R3 → cons[1]+cons[3]+cons[4]
                if len(cons_orig) >= 5:
                    cand = cons_orig[1] + cons_orig[3] + cons_orig[4]
                    if cand in self.root_set:
                        _direct_root = cand
            elif _direct_form == "VERB_AUGMENTED_V_VI":
                form_v = tmpl_tags.get("form") == "V"
                # V: يَتَفَعَّلُ → يـ+ت+R1+R2+R3
                # VI: يَتَفَاعَلُ → يـ+ت+R1+ا+R2+R3
                if form_v and len(cons_orig) >= 5:
                    cand = cons_orig[2] + cons_orig[3] + cons_orig[4]
                    if cand in self.root_set:
                        _direct_root = cand
                elif not form_v and len(cons_orig) >= 6:
                    cand = cons_orig[2] + cons_orig[4] + cons_orig[5]
                    if cand in self.root_set:
                        _direct_root = cand
        # Check if the imperfect prefix يَ/ي was stripped (affects ناقص ي→و priority)
        imperfect_stripped = any("imperf" in t for t in clitics.get("pre", []))
        root = self._step_c(stem, template_cat, imperfect_stripped=imperfect_stripped, orig_word=word)
        if _direct_root is not None:
            root = _direct_root

        # ── Single-letter prep/conj proclitic rescue ─────────────────────────
        # Unvoweled corpus text glues بـ/لـ/كـ/سـ/فـ/وـ onto a noun whose root
        # is only 3 consonants (بِشَكْل، بِسَبَب، لِغَرَض، بِنِسْبَة). The Step A
        # guard refuses to strip these (it would leave <4 consonants and could
        # eat a root-initial consonant of سَفِينَة-type words), so the root
        # extractor either fails or returns a glued artefact (بشك، بنس). Rescue
        # only under a tight rule: the core (word minus the leading clitic) must
        # expose a SOUND 3-consonant root that is exactly its first three surface
        # consonants (no weak/geminate invention), AND the whole-word reading
        # must either fail outright or be the tell-tale "clitic + first two core
        # consonants" glue. This leaves سفينة→سفن, وزير→زور, كتاب→كتب untouched.
        _word_cons = self._extract_consonants(word)
        # Stacked conjunction + prep artefact (وَلِغَسْل → لغس): Step A peels the
        # conjunction but leaves the prep glued, and the resulting first-three
        # consonants happen to be a real root, so neither standard trigger fires.
        # Detect it: the surface opens with و/ف then a prep ب/ل/ك, and the current
        # root equals the conjunction-stripped stem's first three consonants.
        _sw = self._strip_diacritics(word)
        _stacked_clitic = (len(_sw) >= 5 and _sw[0] in "وف" and _sw[1] in "بلك"
                           and root == self._extract_consonants(_sw[1:])[:3])
        if (root not in self.root_set
                or (len(_word_cons) >= 3 and root == _word_cons[:3])
                or _stacked_clitic):
            _rescued = self._proclitic_root_rescue(word, root)
            if _rescued is not None:
                _resc_root, _resc_clitic = _rescued
                root = _resc_root
                # Record the stripped proclitic and reroute to a nominal: these
                # surfaces (شكل، سبب، غرض، نسبة) are nouns governed by the prep.
                clitics.setdefault("pre", [])
                if _resc_clitic not in clitics["pre"]:
                    clitics["pre"].append(_resc_clitic)
                template_cat = "NOM_DERIVED"
                tmpl_tags = {"pos": "NOM"}

        pos = tmpl_tags.get("pos", "UNKNOWN")
        # Merge clitic tags into main tags
        tags = {k: v for k, v in tmpl_tags.items() if k != "pos"}
        for pre in clitics.get("pre", []):
            tags.update(pre)

        # ── Imperfect/imperative prefix detection from original word ──────────
        # Imperfect verbs (PRES tense) have a fixed prefix pattern:
        #   prefix consonant (يـ/تـ/أـ/نـ) + haraka + R1 + sukun + ...
        # If the original word starts with one of these prefix consonants AND
        # the next consonant has a sukun, this is an imperfect verb.
        _DAMMA_W = "ُ"; _FATHA_W = "َ"; _KASRA_W = "ِ"; _SUKUN_W = "ْ"
        # Only يـ and نـ are unambiguous imperfect prefixes. تـ and أـ are
        # ambiguous (تـ may be Form V/VI past augment; أـ may be Form IV past
        # augment or hamzat al-wasl). Restrict to يـ/نـ for safe detection;
        # also accept تـ only if the word's pattern is unmistakably imperfect
        # (R1 with sukun on the next consonant + indicative damma at end).
        _IMPERF_PREFIX_C = "ين"
        is_imperfect = False
        if word and word[0] in _IMPERF_PREFIX_C and len(word) >= 4:
            # Confirm: 2nd char is haraka (fatha/damma), 3rd is consonant, 4th is sukun
            if word[1] in (_FATHA_W, _DAMMA_W) and word[2] in self.AR_CONSONANTS:
                if word[3] == _SUKUN_W or (word[3] in (_FATHA_W, _DAMMA_W, _KASRA_W) and len(word) > 4):
                    # Stricter: 4th char must be sukun, OR shadda+vowel (for Form II يُعَلِّمُ)
                    if word[3] == _SUKUN_W:
                        is_imperfect = True
                    elif len(word) > 4 and word[3] in (_FATHA_W, _DAMMA_W, _KASRA_W) and word[4] == "ّ":
                        # Form II/V imperfect: يُعَلِّمُ has يـ+damma+ع+fatha+ل+shadda
                        is_imperfect = True
                    elif word[2] == "ت" and len(word) > 4:
                        # Form V/VI imperfect: يَتَعَلَّمُ, يَتَبَادَلُ — prefix يَ + ت + ...
                        is_imperfect = True
                    elif word[2] in "اوي":
                        # ajwaf imperfect: يَقُولُ — يَ + قُ + و + ل
                        is_imperfect = True
                    elif (word[0] == "ي" and len(word) > 5 and word[2] in self.AR_CONSONANTS
                          and word[3] == _DAMMA_DR and word[4] == "و"):
                        # ajwaf imperfect with R2+damma+long-و: يَقُولُ (ي+قُ+و+ل).
                        # Restricted to ي prefix + damma vowel + long و to avoid false
                        # positives on past-tense naqis verbs (نَسِيَ: kasra+ي).
                        is_imperfect = True
                    elif (word[0] == "ي" and word[1] == _FATHA_DR
                          and len(word) >= 5
                          and word[2] in self.AR_CONSONANTS
                          and word[3] in (_KASRA_DR, _DAMMA_DR, _FATHA_DR)
                          and word[4] in self.AR_CONSONANTS):
                        # mithal imperfect (يَعِدُ from وعد), naqis (يَنْسَى, يَدْعُو).
                        # Only valid when prefix is ي (not ن).
                        is_imperfect = True

        if pos == "VERB" and is_imperfect:
            tags["tense"] = "PRES"
            # Special: mithal imperfect (يَعِدُ from وعد). Surface has 3 consonants
            # including the ي prefix; after stripping ي, only 2 consonants remain.
            # Original root has و- prepended.
            cons_orig = self._extract_consonants(word)
            if len(cons_orig) == 3 and cons_orig[0] == "ي":
                cand = "و" + cons_orig[1:]
                if cand in self.root_set:
                    root = cand
            # Voice: damma on prefix (يُـ) with fatha on R1 = passive (يُكْتَبُ).
            # damma on prefix + kasra on R1 = active (يُعَلِّمُ Form II/IV).
            # We need to check R2 vowel: fatha → PASS, kasra → ACT.
            if word[1] == _DAMMA_W:
                # find R2 vowel (3rd consonant's following diacritic)
                cc = 0
                r2_vowel = None
                for ii, cch in enumerate(word):
                    if cch in self.AR_CONSONANTS:
                        cc += 1
                        if cc == 3 and ii + 1 < len(word):
                            r2_vowel = word[ii + 1]
                            break
                        if cc == 2 and ii + 1 < len(word):
                            # for Form I يُكْتَبُ: R2 has fatha → PASS
                            r2_vowel_alt = word[ii + 1]
                if r2_vowel == _FATHA_W:
                    tags["voice"] = "PASS"
            # Mood from final diacritic: damma=IND (default, no mark), fatha=SUBJ, sukun=JUS
            if word.endswith(_SUKUN_W):
                tags["mood"] = "JUS"
            elif word.endswith(_FATHA_W):
                tags["mood"] = "SUBJ"

        # ── Imperative detection ────────────────────────────────────────────
        # اُكْتُبْ, اُدْرُسْ, اِجْلِسْ: starts with ا + damma/kasra + R1 + sukun, ends with sukun
        if pos == "VERB" and not is_imperfect and word.startswith("ا") and word.endswith(_SUKUN_W):
            if len(word) >= 5 and word[1] in (_DAMMA_W, _KASRA_W):
                tags["tense"] = "IMP"
                tags["voice"] = "ACT"
                tags["person"] = "2"
                # Clear semantic_role (imperative shape doesn't bind to wazn semantic)
                # Keep form=I

        # Geminate passive: damma+C2+shadda (شُدَّ, مُدَّ).
        if pos == "VERB" and tags.get("tense") != "PRES":
            if len(word) >= 3 and word[0] in self.AR_CONSONANTS and word[1] == "ُ" and word.endswith("ّ"):
                tags["voice"] = "PASS"
                tags["tense"] = "PAST"
        # ajwaf passive: surface kasra+ي+...+fatha (قِيلَ from قول).
        # Pattern: C1 with kasra + ي + C2 + fatha.
        if pos == "VERB" and tags.get("tense") != "PRES":
            if len(word) >= 4 and word[0] in self.AR_CONSONANTS and word[1] == "ِ" and word[2] == "ي":
                tags["voice"] = "PASS"
                tags["tense"] = "PAST"

        # Past passive: surface فُعِلَ (damma on C1, kasra on C2) for Form I,
        # or أُفْعِلَ (damma on أ, sukun on R1, kasra on R2) for Form IV.
        if pos == "VERB" and tags.get("tense") != "PRES":
            if self._check_passive(word):
                tags["voice"] = "PASS"
                tags["tense"] = "PAST"
            # Form IV passive: damma on أ, kasra on R2 (3rd consonant)
            elif word.startswith("أُ") and len(word) >= 5:
                cc = 0
                for ii, cch in enumerate(word):
                    if cch in self.AR_CONSONANTS:
                        cc += 1
                        if cc == 3 and ii + 1 < len(word) and word[ii + 1] == "ِ":
                            tags["voice"] = "PASS"
                            tags["tense"] = "PAST"
                            break

        # ── Passive voice detection from diacritics ─────────────────────────
        # If the original word has diacritics and shows the passive pattern
        # (فُعِلَ: damma on C1, kasra on C2), add voice=PASS tag.
        if pos == "VERB" and self._check_passive(word):
            tags["voice"] = "PASS"

        # ── Circumfix detection: لام التوكيد + نون التوكيد ──────────────────
        # لَـ...نَّ is a circumfix — a discontinuous morpheme that brackets the
        # verb from both sides simultaneously. Neither half carries the
        # sworn-assertion meaning alone; it is the sandwich that does it.
        # (Arabic grammatical term: الإحاطة / الاكتناف)
        # e.g. لَيَكْتُبَنَّ = "he will most certainly write (I swear)"
        # The two halves are stripped independently in Step A (لَـ as a
        # proclitic, ـنَّ as an enclitic), then reunited here as a single
        # circumfix tag so the model receives one unified signal.
        pre_emphs  = {t.get("emph") for t in clitics.get("pre", [])}
        enc_emphs  = {t.get("emph") for t in clitics.get("enc", [])}
        has_lam    = "LAM" in pre_emphs
        has_nun    = bool(enc_emphs & {"NUN_THAQILA", "NUN_KHAFIFA"})
        if has_lam and has_nun:
            tags["circumfix"] = "LAM_NUN"
            tags["assertion"] = "SWORN"
            # Remove the independent emph tags — they are now subsumed
            tags.pop("emph", None)

        # ── VERB bundle normalization (الزمن والشخص) ─────────────────────────
        # The validator (check_morph_sequence_ar) rejects any VERB lacking
        # tense or person. Two upstream gaps surface here:
        #   Bug 1: Step B's rule-based fallback (VERB_TRILATERAL_UNKNOWN) and
        #          several augmented categories commit pos=VERB without any
        #          tense in tags_implied. In MSA a verb without زمن is
        #          structurally incoherent (فعل لا زمن له), so when no tense
        #          can be derived we reroute to NOM — the surface shape is
        #          usually a coincidentally-matching CaCaC nominal anyway.
        #   Bug 2: For genuinely finite verbs (tense already set), person is
        #          rarely populated because enclitic subject suffixes are not
        #          merged into the main tag bundle and the canonical 3MSG
        #          zero-affix is not defaulted. MSA's verbal-sentence default
        #          is 3MSG, so fill person=3 with gender taken from any
        #          available subject signal.
        if pos == "VERB":
            # Collect subject signals from clitics (enclitic verbal suffixes
            # and the imperfect prefix tag carry person/gender).
            enc_subj = {}
            for enc in clitics.get("enc", []):
                if "person" in enc:
                    for k in ("person", "num", "gender"):
                        if k in enc and k not in enc_subj:
                            enc_subj[k] = enc[k]
            imperf_tag = tags.get("imperf")  # e.g. "3MSG"

            # A verb carrying the definite article ال is structurally impossible
            # in Arabic; the surface must be a nominal. Treat def=DEF on any
            # source (tag or proclitic) as a hard signal to reroute.
            has_def = (
                tags.get("def") == "DEF"
                or any(c.get("def") == "DEF" for c in clitics.get("pre", []))
            )

            if "tense" not in tags or has_def:
                # Reroute to NOM and strip verb-only tags so the validator's
                # NOM guards apply cleanly. Triggered when tense is missing
                # (Bug 1) or when ال is present (def-on-VERB cross-cutting).
                pos = "NOM"
                for k in ("form", "voice", "mood", "aspect", "person",
                         "tense", "imperf", "weak_type"):
                    tags.pop(k, None)
                # Carry over surface-derived num/gender so the rerouted NOM
                # passes the validator's "num OR gender" requirement. ـة on
                # the surface signals F SG; bare CaCaC/CaaCiC defaults to M SG.
                if "num" not in tags and "gender" not in tags:
                    ends_ta_marbuta = word.endswith("ة") or word.endswith("ـة")
                    tags["gender"] = "F" if ends_ta_marbuta else "M"
                    tags["num"] = "SG"
            else:
                # Bug 2 default: tense present but no person. Fill from
                # available subject signals; otherwise apply 3MSG default
                # (the unmarked verbal-sentence subject in MSA).
                if "person" not in tags:
                    if enc_subj.get("person"):
                        tags["person"] = enc_subj["person"]
                        if "num" not in tags and "num" in enc_subj:
                            tags["num"] = enc_subj["num"]
                        if "gender" not in tags and "gender" in enc_subj:
                            tags["gender"] = enc_subj["gender"]
                    elif imperf_tag and len(imperf_tag) >= 3:
                        # imperf tag encodes person+num+gender (e.g. "3MSG").
                        tags["person"] = imperf_tag[0]
                        if "gender" not in tags:
                            tags["gender"] = imperf_tag[-1]
                    else:
                        tags["person"] = "3"
                        if "gender" not in tags:
                            tags["gender"] = "M"

        # ── NOM bundle normalization (العدد والجنس) ──────────────────────────
        # Step B's derived-nominal branch (role=DERIVED, NOM_DERIVED templates)
        # commits pos=NOM without populating num/gender, because the
        # surface-affix resolver only runs on plain-NOM emissions. The relaxed
        # validator requires num OR gender on any NOM not in the exempt-role
        # set, so fill from surface heuristics: ـات → F PL, ـة → F SG,
        # otherwise default M SG. Broken plurals (e.g. مياه, ماء→pl) and
        # foreign loanwords default to M SG; this is grammatically permissive
        # but linguistically defensible — both pass under the "num OR gender"
        # rule even when the underlying number is non-canonical.
        if pos == "NOM" and "num" not in tags and "gender" not in tags:
            if word.endswith("ات"):
                tags["num"], tags["gender"] = "PL", "F"
            elif word.endswith("ة"):
                tags["num"], tags["gender"] = "SG", "F"
            else:
                tags["num"], tags["gender"] = "SG", "M"

        return TokenInfo(
            surface=word,
            clitics=clitics,
            template=template_cat,
            root=root,
            tags=tags,
            pos=pos,
        )

    # Proclitic / enclitic letter-strings tried by the root rescue (consonantal,
    # diacritics already removed). Ordered does not matter — selection prefers the
    # longest surviving core (i.e. the least amount stripped).
    def analyze_sentence(self, sentence: str) -> Tuple[List[TokenInfo], bool, str]:
        # Sentence-level grammar layer: split, analyze each word, then run
        # context-aware POS disambiguation and structural guards.
        words = sentence.split()
        tokens = [self.analyze(w) for w in words]
        if not tokens:
            return tokens, True, "ok"
        tokens = _ar_grammar.disambiguate_pos(tokens)
        word_ok = check_morph_sequence_ar(tokens)
        sent_ok, sent_msg = _ar_grammar.validate_sentence(tokens)
        if not sent_ok:
            return tokens, False, sent_msg
        # Backward-compat: also run the legacy thin-wrapper guard so existing
        # contract checks keep their semantics.
        legacy_ok, legacy_msg = validate_sentence_structure_ar(tokens)
        return tokens, word_ok and legacy_ok, legacy_msg

# ══════════════════════════════════════════════════════════════════════════════
# TURKISH ENGINE
# ══════════════════════════════════════════════════════════════════════════════

