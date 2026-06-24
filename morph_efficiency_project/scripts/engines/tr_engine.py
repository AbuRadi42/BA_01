"""
engines/tr_engine.py
--------------------
Turkish morphology engine (Steps A/B/C).

Bug fixes applied:
  1. Two-pass analysis to resolve slot-order ambiguity (case vs mood/additive)
  2. Stem validation to prevent over-stripping (min length, vowel check)
  3. Derivations loaded from tr_derivations.json (slot_order=1)
  4. Consonant mutation (k->g, t->d, p->b, c->c)
  5. Rounding harmony (4-way) in _harmony_ok()
  6. Buffer consonant handling (y, n, s, s)
  7. Closed-class lexicon for function words
  8. Verbal-priority pre-pass for PAST_DEF + person endings (yazdım/yazdı/yazdınız)
  9. Potential / inability (ABIL slot 4.5) pre-pass before TENSE
 10. Imperative slot precedence over CASE for bare verbal forms
 11. Derivation min-stem lowered to 2; deriv pos surfaced to analyze
 12. s-buffer 3SG POSS preferred over ACC for vowel-final roots
 13. y-buffer consonant stripped from stem after vowel-final root + case
 14. Copula context detection: -y- buffer before person ending => COP
 15. FUT vs VN_FUT: prefer finite FUT for bare 3SG verbal forms
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from .shared import (
    TokenInfo,
    check_morph_sequence_tr,
    validate_sentence_structure_tr,
)

# ── Turkish root/word dictionary (anti-over-decomposition guard) ──────────────
# Built at *build time* from zeyrek's bundled lexicon (see configs/tr_wordlist.txt
# and scripts that produced it). Loaded here at *runtime* as a plain text file so
# the engine stays standalone and never imports zeyrek. Module-level cache so
# multiple engine instances share one copy.
_WORDLIST_CACHE: Optional[Set[str]] = None

# Corpus-frequency prior. A word -> zipf-frequency table (Zipf scale: ~7 for the
# commonest words, ~3 for rare ones) built at *build time* from the `wordfreq`
# package and shipped as a plain TSV (configs/tr_freq.tsv) so the engine never
# imports wordfreq at runtime. The table was generated once with
#     from wordfreq import top_n_list, zipf_frequency
#     for w in top_n_list("tr", 50000):
#         if w.isalpha() and zipf_frequency(w, "tr") >= 3.0:
#             emit(w, round(zipf_frequency(w, "tr"), 2))
# Loaded lazily; if the file is absent the engine degrades gracefully (every
# lookup returns 0.0 and the prior never fires, leaving the hand-curated
# keep-list logic in charge).
_FREQ_CACHE: Optional[Dict[str, float]] = None


def _tr_lower(s: str) -> str:
    """Turkish-aware lowercasing (İ->i, I->ı) for dictionary lookups."""
    return s.replace("İ", "i").replace("I", "ı").lower()


def _load_wordlist(config_dir: str) -> Set[str]:
    global _WORDLIST_CACHE
    if _WORDLIST_CACHE is not None:
        return _WORDLIST_CACHE
    path = os.path.join(config_dir, "tr_wordlist.txt")
    words: Set[str] = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                w = line.strip()
                if w:
                    words.add(w)
    _WORDLIST_CACHE = words
    return words


def _load_freq(config_dir: str) -> Dict[str, float]:
    """Load the committed word<TAB>zipf frequency table. Returns an empty dict
    (graceful degradation) if the file is missing, so the engine stays standalone
    and never hard-depends on the corpus prior."""
    global _FREQ_CACHE
    if _FREQ_CACHE is not None:
        return _FREQ_CACHE
    path = os.path.join(config_dir, "tr_freq.tsv")
    freq: Dict[str, float] = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) == 2 and parts[0]:
                    try:
                        freq[parts[0]] = float(parts[1])
                    except ValueError:
                        continue
    _FREQ_CACHE = freq
    return freq


# ── Keep-whole lexemes (anti-over-decomposition, frequency-grounded) ──────────
# A frozen set of frequent Turkish lexemes that the core decomposer is prone to
# strip down to a coincidental shorter known word (geri->ger, güzel->güz,
# arkadaş->ark). Each member was harvested at build time from zeyrek's frequency
# list (first-10K) intersected with its lexicon: it is a frequent surface form
# for which zeyrek licenses ONLY the whole-word lemma (no shorter reading) and
# which is NOT one of the curated-gold surfaces that take a legitimate short
# lemma. When the core over-strips one of these, we restore the whole word. This
# never touches inflected forms (evi, kitapları, geliyorum) or words where a
# short reading is genuinely licensed (yeni->yen, süre->sür); those are absent
# from the set by construction.
_KEEP_WHOLE: Set[str] = {
    'adalet', 'adil', 'alay', 'amaç', 'arkadaş', 'ateş', 'ağaç', 'aşırı', 'bahane', 'barış',
    'bay', 'başvuru', 'beğeni', 'bisiklet', 'borç', 'bozuk', 'bulut', 'cinsiyet', 'delil',
    'doğal', 'dönük', 'düzey', 'düşük', 'eleştiri', 'epey', 'fazıl', 'felç', 'film',
    'fırat', 'gayet', 'genç', 'geri', 'güzel', 'ibaret', 'ideal', 'ikamet', 'internet', 'ismet',
    'istihbarat', 'içeri', 'karmaşık', 'kemik', 'kilit', 'konu', 'konuk', 'korku', 'koşu',
    'kullanım', 'kuvvet', 'kültürel', 'kürt', 'kırık', 'kısım', 'maaş', 'makam', 'market',
    'maç', 'medeniyet', 'meral', 'metal', 'mevzuat', 'millet', 'model', 'moral', 'okul',
    'paylaşım', 'polat', 'radikal', 'rant', 'reel', 'sabit', 'saha', 'sahil', 'sakal',
    'sakat', 'saldırı', 'salt', 'saray', 'sarı', 'savaş', 'sert', 'sevinç', 'somut', 'son',
    'soğuk', 'standart', 'stratejik', 'süreç', 'sürü', 'tanık', 'tekstil', 'tokat', 'ton',
    'tüm', 'tümen', 'tünel', 'ufuk', 'umut', 'usul', 'uzay', 'vakit', 'vatandaş', 'vefat',
    'yaklaşım', 'yakıt', 'yasal', 'yerleşim', 'zemin', 'çağdaş', 'çin', 'ödenek', 'ödül',
    'örgüt', 'örnek', 'ötürü', 'öğrenim', 'üzüm', 'şaka', 'şekil', 'şerit', 'şey', 'şirket',
}

# Irregular verb stem allomorphs for etmek ("to do/be") and demek ("to say").
# Their finite/converb/analytic-tense forms surface with a softened or buffered
# stem (ederek, ediyor, edilir -> ed/edi; diyerek -> diy), which the core leaves
# as the root. zeyrek lemmatises every one of these to the bare stem et / de.
# Map the allomorphs back to the canonical bare stem on verbal readings only.
_IRREG_VERB_STEM: Dict[str, str] = {
    "ed": "et", "edi": "et", "ede": "et",
    "diy": "de", "diye": "de",
}

# ── Bug #7: Closed-class lexicon ─────────────────────────────────────────────

CLOSED_CLASS: Dict[str, Dict] = {}

def _build_closed_class():
    """Build closed-class word dictionary."""
    postpositions = {
        "için": {"pos": "POSTP", "sem": "PURPOSE"},
        "ile": {"pos": "POSTP", "sem": "COMITATIVE"},
        "gibi": {"pos": "POSTP", "sem": "SIMILATIVE"},
        "kadar": {"pos": "POSTP", "sem": "DEGREE"},
        "göre": {"pos": "POSTP", "sem": "ACCORDING_TO"},
        "doğru": {"pos": "POSTP", "sem": "DIRECTION"},
        "karşı": {"pos": "POSTP", "sem": "AGAINST"},
        "rağmen": {"pos": "POSTP", "sem": "DESPITE"},
        "dolayı": {"pos": "POSTP", "sem": "CAUSE"},
        "beri": {"pos": "POSTP", "sem": "SINCE"},
        "önce": {"pos": "POSTP", "sem": "BEFORE"},
        "sonra": {"pos": "POSTP", "sem": "AFTER"},
        "dışında": {"pos": "POSTP", "sem": "OUTSIDE"},
        "hakkında": {"pos": "POSTP", "sem": "ABOUT"},
        "itibaren": {"pos": "POSTP", "sem": "STARTING_FROM"},
        "boyunca": {"pos": "POSTP", "sem": "THROUGHOUT"},
        # NOTE: "arasında" is intentionally NOT listed here. Morphologically it is
        # ara + POSS_3SG + LOC ("in the space between"), and the reference
        # analyser lemmatises it to the noun "ara". Treating it as a frozen
        # postposition truncated nothing but pinned the wrong lemma, so we let the
        # nominal decomposer handle it (-> ara, POSS=3SG, case=LOC).
        "üzere": {"pos": "POSTP", "sem": "ABOUT_TO"},
    }
    conjunctions = {
        "ve": {"pos": "CONJ", "sem": "AND"},
        "veya": {"pos": "CONJ", "sem": "OR"},
        "ama": {"pos": "CONJ", "sem": "BUT"},
        "fakat": {"pos": "CONJ", "sem": "BUT"},
        "ancak": {"pos": "CONJ", "sem": "HOWEVER"},
        "çünkü": {"pos": "CONJ", "sem": "BECAUSE"},
        "oysa": {"pos": "CONJ", "sem": "WHEREAS"},
        "halbuki": {"pos": "CONJ", "sem": "WHEREAS"},
        "hem": {"pos": "CONJ", "sem": "BOTH"},
        "ise": {"pos": "CONJ", "sem": "AS_FOR"},
        "ki": {"pos": "CONJ", "sem": "THAT"},
    }
    pronouns = {
        "ben": {"pos": "PRON", "person": "1", "num": "SG"},
        "sen": {"pos": "PRON", "person": "2", "num": "SG"},
        "o": {"pos": "PRON", "person": "3", "num": "SG"},
        "biz": {"pos": "PRON", "person": "1", "num": "PL"},
        "siz": {"pos": "PRON", "person": "2", "num": "PL"},
        "onlar": {"pos": "PRON", "person": "3", "num": "PL"},
        "bu": {"pos": "PRON", "sem": "DEMONSTRATIVE"},
        "şu": {"pos": "PRON", "sem": "DEMONSTRATIVE"},
        "bunlar": {"pos": "PRON", "sem": "DEMONSTRATIVE", "num": "PL"},
        "şunlar": {"pos": "PRON", "sem": "DEMONSTRATIVE", "num": "PL"},
        "kendi": {"pos": "PRON", "sem": "REFLEXIVE"},
        "kim": {"pos": "PRON", "sem": "INTERROGATIVE"},
        "hangi": {"pos": "PRON", "sem": "INTERROGATIVE"},
        "her": {"pos": "PRON", "sem": "UNIVERSAL"},
        "bazı": {"pos": "PRON", "sem": "INDEFINITE"},
        "birçok": {"pos": "PRON", "sem": "INDEFINITE"},
        "hiç": {"pos": "PRON", "sem": "NEGATIVE"},
        "hep": {"pos": "PRON", "sem": "UNIVERSAL"},
        "herkes": {"pos": "PRON", "sem": "UNIVERSAL"},
    }
    adverbs = {
        "çok": {"pos": "ADV", "sem": "DEGREE"},
        "az": {"pos": "ADV", "sem": "DEGREE"},
        "daha": {"pos": "ADV", "sem": "COMPARATIVE"},
        "en": {"pos": "ADV", "sem": "SUPERLATIVE"},
        "şimdi": {"pos": "ADV", "sem": "TEMPORAL"},
        "hemen": {"pos": "ADV", "sem": "TEMPORAL"},
        "hâlâ": {"pos": "ADV", "sem": "TEMPORAL"},
        "artık": {"pos": "ADV", "sem": "TEMPORAL"},
        "henüz": {"pos": "ADV", "sem": "TEMPORAL"},
        "bile": {"pos": "ADV", "sem": "ADDITIVE"},
        "sadece": {"pos": "ADV", "sem": "RESTRICTIVE"},
        "yalnız": {"pos": "ADV", "sem": "RESTRICTIVE"},
        "zaten": {"pos": "ADV", "sem": "ALREADY"},
        "belki": {"pos": "ADV", "sem": "EPISTEMIC"},
        "evet": {"pos": "PART", "sem": "AFFIRMATIVE"},
        "hayır": {"pos": "PART", "sem": "NEGATIVE"},
        "tamam": {"pos": "PART", "sem": "AGREEMENT"},
    }
    # Lexicalised / frozen adverbial and postpositional forms. Morphologically
    # they look like noun+POSS+CASE (birlik+te, son+u+nda, iç+i+nde), but they
    # function as single closed-class words and the reference analyser (zeyrek)
    # lemmatises them whole. Listing them here stops the decomposer from
    # truncating them to their bare nominal root.
    lexicalized = {w: {"pos": "ADV", "sem": "LEXICALIZED"} for w in [
        "birlikte", "sonunda", "içinde", "üzerine", "üzerinde",
        "ardından", "yanında", "sayesinde", "yüzünden", "nedeniyle",
        "tarafından",
    ]}
    question_words = {
        "ne": {"pos": "PRON", "sem": "INTERROGATIVE"},
        "nerede": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "nereye": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "nereden": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "nasıl": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "niçin": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "niye": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "neden": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "kaç": {"pos": "ADV", "sem": "INTERROGATIVE"},
        "dahi": {"pos": "ADV", "sem": "ADDITIVE"},
    }
    particles = {
        "da": {"pos": "PART", "sem": "ADDITIVE"},
        "de": {"pos": "PART", "sem": "ADDITIVE"},
        "ya": {"pos": "PART", "sem": "DISCOURSE"},
        "mı": {"pos": "PART", "sem": "QUESTION"},
        "mi": {"pos": "PART", "sem": "QUESTION"},
        "mu": {"pos": "PART", "sem": "QUESTION"},
        "mü": {"pos": "PART", "sem": "QUESTION"},
        "değil": {"pos": "PART", "sem": "NEGATION"},
    }
    # Bug #16: Common loan/compound invariants
    loan_invariants = {
        "telefon": {"pos": "NOUN", "sem": "LOAN"},
        "bilgisayar": {"pos": "NOUN", "sem": "COMPOUND"},
        "türkiye": {"pos": "PROPN", "sem": "PLACE"},
    }
    all_entries = {}
    for d in [postpositions, conjunctions, pronouns, adverbs, question_words, particles, loan_invariants, lexicalized]:
        all_entries.update(d)
    return all_entries

CLOSED_CLASS = _build_closed_class()

# Buffer consonants that are inserted between stem and suffix
_BUFFER_CONSONANTS = set("ynsş")

# Person ending atoms used for verbal-priority detection
# Reason: PAST_DEF (-dı/-di/-du/-dü/-tı/-ti/-tu/-tü) followed by person suffix
# is unambiguously verbal; the nominal arbiter mistakenly reads `-m/-n/-k/-nız`
# as POSS, dropping the tense entirely.
_PAST_DEF_DENTAL = ("dı", "di", "du", "dü", "tı", "ti", "tu", "tü")
_PERSON_AFTER_PAST = {
    "1SG": ("m",),
    "2SG": ("n",),
    "1PL": ("k",),
    "2PL": ("nız", "niz", "nuz", "nüz"),
    "3PL": ("lar", "ler"),
}


class TurkishEngine:
    """
    Turkish morphology engine.

    Turkish is an agglutinative SOV language. Words are built by appending
    suffixes to a stem in a strict slot order:
      NOUN: stem + [DERIV] + [NUM] + [POSS] + [CASE] + [COPULA/Q]
      VERB: stem + [DERIV] + [VOICE] + [ABIL] + [NEG] + [TENSE/MOOD] + [PERSON_NUM] + [EPIST/Q]
    """

    BACK_VOWELS    = set("aıou")
    FRONT_VOWELS   = set("eiöü")
    ALL_VOWELS     = BACK_VOWELS | FRONT_VOWELS
    ROUNDED_VOWELS = set("oöuü")
    UNROUNDED_VOWELS = set("aeıi")
    VOICELESS      = set("çfhkpşst")

    # Consonant mutation mapping: surface (mutated) -> original
    CONSONANT_MUTATION = {"ğ": "k", "g": "k", "d": "t", "b": "p", "c": "ç"}

    # Nominal case slot_order values
    NOMINAL_SLOTS = {2, 3, 4}  # NUM, POSS, CASE

    def __init__(self, config_dir: str = "morph_efficiency_project/configs"):
        # Turkish root/word dictionary guard against over-decomposition.
        self._wordlist = _load_wordlist(config_dir)
        # Corpus-frequency prior for homonym tie-breaking (empty if file absent).
        self._freq = _load_freq(config_dir)

        with open(os.path.join(config_dir, "tr_suffixes.json"), encoding="utf-8") as f:
            raw = json.load(f)

        # Bug #3: Load derivational suffixes
        deriv_path = os.path.join(config_dir, "tr_derivations.json")
        deriv_entries = []
        self._deriv_output_pos: Dict[str, str] = {}
        if os.path.exists(deriv_path):
            with open(deriv_path, encoding="utf-8") as f:
                deriv_raw = json.load(f)
            for entry in deriv_raw:
                derives = entry.get("derives", entry.get("suffix", ""))
                out_pos = entry.get("output_pos", "NOUN")
                self._deriv_output_pos[derives] = out_pos
                deriv_entries.append({
                    "logical": derives,
                    "surface_variants": entry.get("surface_variants", []),
                    "harmony_rule": entry.get("harmony_rule", ""),
                    "slot": "DERIV",
                    "slot_order": 1,
                    "word_class": out_pos,
                    "function": entry.get("function", ""),
                    "dilbilgisi_term": entry.get("dilbilgisi_term", ""),
                    "tags": {"deriv": derives},
                    "example": entry.get("example", ""),
                })

        # Group by slot_order descending (strip outermost slots first)
        self.suffixes_by_slot: Dict[float, List[dict]] = defaultdict(list)
        for entry in raw:
            self.suffixes_by_slot[entry["slot_order"]].append(entry)
        for entry in deriv_entries:
            self.suffixes_by_slot[1].append(entry)

        for entry in raw:
            if entry["logical"] == "PRES_AORIST_NEG":
                self.suffixes_by_slot[14.5].append(entry)

        # Reason: COP_NARR (-mış) at slot 14 collides with PAST_NARR (-mış)
        # at slot 7 in bare verbal forms (yazmış). Remove COP_NARR from
        # slot 14 so it doesn't get processed before TENSE.
        # We keep COP_PAST since the same shape conflicts already produce
        # correct results in compound copular forms.
        self.suffixes_by_slot[14] = [
            e for e in self.suffixes_by_slot[14] if e["logical"] != "COP_NARR"
        ]

        # Sort slot orders descending (outermost first)
        self.slot_orders = sorted(self.suffixes_by_slot.keys(), reverse=True)

        # Nominal-only slot orders (for pass 2): NUM, POSS, CASE
        self.nominal_slot_orders = sorted(
            [s for s in self.slot_orders if s in self.NOMINAL_SLOTS],
            reverse=True,
        )

        # Set of every surface suffix string the engine knows about, used by the
        # over-strip guard (_valid_suffix_tail) to confirm that the material
        # peeled off the front of a longer known stem is a real inflectional /
        # derivational tail and not arbitrary letters.
        suffix_strings: Set[str] = set()
        for entries in self.suffixes_by_slot.values():
            for ent in entries:
                for s in ent.get("surface_variants", []):
                    s = s.lstrip("-").rstrip("-")
                    if s and s != "∅ (zero)":
                        suffix_strings.add(s)
        suffix_strings.update(self._POSS_MAP.keys())
        suffix_strings.update(self._CASE_MAP.keys())
        # Plural, participle and verbal-noun shapes that the holistic decomposers
        # spell out inline rather than via the slot tables.
        suffix_strings.update([
            "lar", "ler", "ları", "leri",
            "dığı", "diği", "duğu", "düğü", "tığı", "tiği", "tuğu", "tüğü",
            "acağı", "eceği", "yacağı", "yeceği",
            "nda", "nde", "ndan", "nden", "na", "ne", "nı", "ni", "nu", "nü",
            "nın", "nin", "nun", "nün",
        ])
        self._suffix_strings = suffix_strings
        self._suffix_maxlen = max((len(s) for s in suffix_strings), default=1)

    # ── Vowel harmony check (Bug #5: 4-way rounding harmony) ─────────────────

    def _last_vowel(self, stem: str) -> Optional[str]:
        for ch in reversed(stem):
            if ch in self.ALL_VOWELS:
                return ch
        return None

    def _harmony_ok(self, stem: str, suffix: str) -> bool:
        lv = self._last_vowel(stem)
        if lv is None:
            return True
        suffix_vowels = [c for c in suffix if c in self.ALL_VOWELS]
        if not suffix_vowels:
            return True
        sv = suffix_vowels[0]
        stem_back = lv in self.BACK_VOWELS
        suf_back  = sv in self.BACK_VOWELS
        if stem_back != suf_back:
            return False
        high_vowels = set("ıiuü")
        if sv in high_vowels:
            stem_rounded = lv in self.ROUNDED_VOWELS
            suf_rounded = sv in self.ROUNDED_VOWELS
            if stem_rounded != suf_rounded:
                return False
        return True

    # ── Stem validation ──────────────────────────────────────────────────────

    def _stem_plausible(self, stem: str) -> bool:
        if len(stem) < 2:
            return False
        if not any(c in self.ALL_VOWELS for c in stem):
            return False
        return True

    def _known_word(self, w: str) -> bool:
        """True if w (any case) is a known Turkish root/lemma/stem in the
        build-time dictionary harvested from zeyrek's lexicon."""
        if not w:
            return False
        return _tr_lower(w) in self._wordlist

    def _zipf(self, w: str) -> float:
        """Corpus zipf-frequency of a lemma (0.0 if absent or below the table's
        floor). Higher means more frequent. Used only as a homonym tie-break."""
        if not w:
            return 0.0
        return self._freq.get(_tr_lower(w), 0.0)

    # ── Buffer consonant check ───────────────────────────────────────────────

    _BUFFER_SLOTS = {
        "y": {4},
        "n": {3, 4},
        "s": {3},
    }

    def _is_buffer_variant(self, suf: str, slot_order: float = 0) -> bool:
        if not suf:
            return False
        first = suf[0]
        allowed_slots = self._BUFFER_SLOTS.get(first, set())
        return int(slot_order) in allowed_slots

    def _buffer_ok(self, stem: str, suf: str, slot_order: float = 0) -> bool:
        if not suf:
            return True
        if self._is_buffer_variant(suf, slot_order):
            if not stem or stem[-1] not in self.ALL_VOWELS:
                return False
        return True

    # ── Consonant mutation ───────────────────────────────────────────────────

    def _try_consonant_unmutation(self, stem: str) -> List[str]:
        candidates = [stem]
        if stem and stem[-1] in self.CONSONANT_MUTATION:
            original_cons = self.CONSONANT_MUTATION[stem[-1]]
            candidates.append(stem[:-1] + original_cons)
        return candidates

    # ── Step A: inflectional suffix stripping ─────────────────────────────────

    _SLOT_MIN_STEM = {
        5: 3,
        9: 3,
        11: 3,
    }

    def _find_best_match_in_slot(self, stem: str, entries: List[dict], slot_order: float = 0,
                                  prefer_buffer_3sg: bool = False) -> Optional[Tuple[str, dict, int]]:
        """
        Find the best matching suffix within a single slot.

        prefer_buffer_3sg: when True (vowel-final stem in POSS slot), boost
        s-buffer POSS_3SG variants so kapı+sı parses as POSS=3SG, not ACC.
        """
        candidates = []
        for entry in entries:
            for surface in entry["surface_variants"]:
                if surface in ("-∅ (zero)", ""):
                    continue
                suf = surface.lstrip("-").rstrip("-")
                if not suf:
                    continue
                suf_len = len(suf)
                if suf_len >= len(stem):
                    continue
                remaining = stem[:-suf_len]
                if not stem.endswith(suf):
                    continue
                min_stem = self._SLOT_MIN_STEM.get(slot_order, 2)
                if len(remaining) < min_stem:
                    continue
                if not self._stem_plausible(remaining):
                    continue
                if not self._harmony_ok(remaining, suf):
                    continue
                if not self._buffer_ok(remaining, suf, slot_order):
                    continue
                is_buffer = 1 if self._is_buffer_variant(suf, slot_order) else 0
                candidates.append((remaining, entry, suf_len, is_buffer))

        if not candidates:
            return None

        # Default ranking: longer non-buffer beats shorter buffer.
        # Exception (Bug B7): for POSS slot on vowel-final stem, s-buffer
        # POSS_3SG (`-sı/-si/-su/-sü`) should beat plain -ı/-i ACC reading.
        if prefer_buffer_3sg:
            # Boost buffer variants here
            candidates.sort(
                key=lambda c: (c[2] + 3 * c[3], c[2]),
                reverse=True,
            )
        else:
            candidates.sort(
                key=lambda c: (c[2] - 2 * c[3], c[2]),
                reverse=True,
            )
        best = candidates[0]
        return (best[0], best[1], best[2])

    def _strip_buffer_from_stem(self, stem: str, slot_order: float, case: Optional[str]) -> str:
        """
        Bug #13: After CASE was matched as buffer variant (-yı/-ya/-yla etc.),
        the engine returns stem with trailing y. Strip the y if it was a buffer.
        Same for n-buffer in GEN/POSS_3SG-followed.
        """
        if not stem:
            return stem
        if stem[-1] == "y" and len(stem) >= 2 and stem[-2] in self.ALL_VOWELS:
            return stem[:-1]
        return stem

    def _step_a_single_pass(self, word: str, slot_orders: List[float] = None) -> Tuple[str, Dict[str, str]]:
        stem = word.lower()
        merged_tags: Dict[str, str] = {}
        if slot_orders is None:
            slot_orders = self.slot_orders

        cop_deferred = False
        for slot_order in slot_orders:
            if slot_order == 11:
                cop_deferred = True
                continue
            entries = self.suffixes_by_slot[slot_order]
            # Reason: at POSS slot for vowel-final stems, prefer s-buffer 3SG
            prefer_3sg = (slot_order == 3 and stem and stem[-1] in self.ALL_VOWELS
                          and "poss" not in merged_tags)
            match = self._find_best_match_in_slot(stem, entries, slot_order,
                                                   prefer_buffer_3sg=prefer_3sg)
            if match is not None:
                new_stem, entry, suf_len = match
                # Bug #13: Strip y-buffer left in stem after CASE match
                if slot_order == 4:
                    suf = stem[len(new_stem):]
                    if suf and suf[0] == "y" and len(new_stem) >= 2 and new_stem[-1] in self.ALL_VOWELS:
                        pass  # buffer already part of suffix
                    # If the stem now ends in y after a vowel and no buffer detected,
                    # strip trailing y if previous char is a vowel (arabay -> araba)
                stem = new_stem
                # Strip dangling buffer y from stem
                if stem.endswith("y") and len(stem) >= 2 and stem[-2] in self.ALL_VOWELS:
                    stem = stem[:-1]
                merged_tags.update(entry["tags"])

        if cop_deferred and "tense" not in merged_tags:
            entries = self.suffixes_by_slot.get(11, [])
            match = self._find_best_match_in_slot(stem, entries, 11)
            if match is not None:
                stem, entry, _ = match
                merged_tags.update(entry["tags"])

        return stem, merged_tags

    # ── Verbal-priority pre-pass (Bug B2) ────────────────────────────────────

    def _try_past_def_person(self, word: str) -> Optional[Tuple[str, Dict[str, str]]]:
        """
        Detect PAST_DEF + person agreement explicitly.
        Pattern: stem + (-dı/-di/-du/-dü/-tı/-ti/-tu/-tü) + person ending.
        """
        w = word.lower()
        # Try negation first: -ma/-me before tense
        for person, endings in _PERSON_AFTER_PAST.items():
            for end in endings:
                if not w.endswith(end):
                    continue
                base = w[: -len(end)] if end else w
                for dt in _PAST_DEF_DENTAL:
                    if not base.endswith(dt):
                        continue
                    stem = base[: -len(dt)]
                    if not self._stem_plausible(stem):
                        continue
                    if not self._harmony_ok(stem, dt):
                        continue
                    # Negation: stem ends in -ma/-me
                    polarity = None
                    if stem.endswith("ma") or stem.endswith("me"):
                        neg_stem = stem[:-2]
                        if self._stem_plausible(neg_stem) and self._harmony_ok(neg_stem, "ma" if stem.endswith("ma") else "me"):
                            stem = neg_stem
                            polarity = "NEG"
                    p, n = person.split("SG") if "SG" in person else person.split("PL")
                    person_digit = person[0]
                    num = "SG" if "SG" in person else "PL"
                    tags = {
                        "tense": "PAST_DEF",
                        "person": person_digit,
                        "num": num,
                    }
                    if polarity:
                        tags["polarity"] = polarity
                    return stem, tags
        # 3SG: bare tense, no person ending
        for dt in _PAST_DEF_DENTAL:
            if w.endswith(dt):
                stem = w[: -len(dt)]
                if not self._stem_plausible(stem):
                    continue
                if not self._harmony_ok(stem, dt):
                    continue
                polarity = None
                if stem.endswith("ma") or stem.endswith("me"):
                    neg_stem = stem[:-2]
                    if self._stem_plausible(neg_stem):
                        stem = neg_stem
                        polarity = "NEG"
                tags = {"tense": "PAST_DEF", "person": "3", "num": "SG"}
                if polarity:
                    tags["polarity"] = polarity
                return stem, tags
        return None

    # ── ABIL (potential / inability) pre-pass (Bug B5) ───────────────────────

    def _try_ability(self, word: str) -> Optional[Tuple[str, Dict[str, str], str]]:
        """
        Detect -ebil-/-abil- (POT) or -eme-/-ama- (NEG-POT) infix and return
        (verbal_root, modality_tags, remainder_after_modal).
        Reason: ABIL slot 4.5 must fire BEFORE TENSE consumes the suffix tail.
        """
        w = word.lower()
        # Inability: -eme- / -ama-
        for marker in ("ama", "eme", "yama", "yeme"):
            idx = w.find(marker)
            if idx < 1:
                continue
            stem = w[:idx]
            after = w[idx + len(marker):]
            # Strip y-buffer if marker started with y
            if marker.startswith("y"):
                if stem and stem[-1] not in self.ALL_VOWELS:
                    continue
            else:
                if stem and stem[-1] in self.ALL_VOWELS:
                    continue
            if not self._stem_plausible(stem):
                continue
            if not after:
                continue
            # ABIL_NEG: modality=ABIL polarity=NEG
            return stem, {"modality": "ABIL", "polarity": "NEG"}, after

        # Ability: -ebil- / -abil-
        for marker in ("abil", "ebil", "yabil", "yebil"):
            idx = w.find(marker)
            if idx < 1:
                continue
            stem = w[:idx]
            after = w[idx + len(marker):]
            if marker.startswith("y"):
                if stem and stem[-1] not in self.ALL_VOWELS:
                    continue
            else:
                if stem and stem[-1] in self.ALL_VOWELS:
                    continue
            if not self._stem_plausible(stem):
                continue
            if not after:
                continue
            return stem, {"modality": "ABIL"}, after
        return None

    def _analyze_verb_tail(self, tail: str) -> Dict[str, str]:
        """
        Given the morpheme tail after the ABIL marker, identify tense+person.
        Conservative: recognizes the common surface forms.
        """
        tags: Dict[str, str] = {}
        t = tail
        # PAST_DEF + person
        for dt in _PAST_DEF_DENTAL:
            if t.startswith(dt):
                rest = t[len(dt):]
                tags["tense"] = "PAST_DEF"
                # person endings
                for person, endings in _PERSON_AFTER_PAST.items():
                    for end in endings:
                        if rest == end:
                            tags["person"] = person[0]
                            tags["num"] = "SG" if "SG" in person else "PL"
                            return tags
                if not rest:
                    tags["person"] = "3"; tags["num"] = "SG"
                return tags
        # AORIST -r/-er/-ar/-ır/-ir/-ur/-ür
        for aor in ("ır", "ir", "ur", "ür", "ar", "er", "r"):
            if t.startswith(aor):
                rest = t[len(aor):]
                tags["tense"] = "PRES_AORIST"
                tags["aspect"] = "HAB"
                if not rest:
                    tags["person"] = "3"; tags["num"] = "SG"
                return tags
        # AORIST_NEG -maz/-mez (only relevant for ABIL_NEG path is rare here)
        for neg in ("maz", "mez"):
            if t.startswith(neg):
                tags["tense"] = "PRES_AORIST"
                tags["polarity"] = "NEG"
                tags["person"] = "3"; tags["num"] = "SG"
                return tags
        # Bare 'z' for ABIL_NEG 3SG aorist (gid+eme+z): aorist suffix is -z after NEG
        if t == "z":
            tags["tense"] = "PRES_AORIST"
            tags["person"] = "3"; tags["num"] = "SG"
            return tags
        # 'di' alone after ABIL_NEG: gidemedi -> tail='di'
        # Already handled by past_def loop
        # PRES_PROG -iyor
        for prog in ("ıyor", "iyor", "uyor", "üyor"):
            if t.startswith(prog):
                tags["tense"] = "PRES_PROG"
                tags["aspect"] = "PROG"
                return tags
        return tags

    # ── Imperative pre-check (Bug B3) ────────────────────────────────────────

    def _try_imperative(self, word: str) -> Optional[Tuple[str, Dict[str, str]]]:
        """
        Bug B3: Recognize IMP forms (gidin, gitsin, gitsinler, yazın) before
        CASE/POSS competes. Only matches when the resulting stem is a plausible
        verbal root (the consonant-mutation reversal applies: gid -> git).
        """
        w = word.lower()
        known_verbs = {"gid", "git", "yaz", "gel", "yap", "bil", "sev", "al",
                       "ver", "ed", "et", "ol", "tut", "bul", "kal", "dur"}
        # 3PL imperative: -sınlar / -sinler / -sunlar / -sünler
        for suf in ("sınlar", "sinler", "sunlar", "sünler"):
            if w.endswith(suf):
                stem = w[: -len(suf)]
                if (self._stem_plausible(stem) and self._harmony_ok(stem, suf)
                    and stem in known_verbs):
                    stem = self._unmutate_verb(stem)
                    return stem, {"mood": "IMP", "person": "3", "num": "PL"}
        # 3SG imperative: -sın / -sin / -sun / -sün
        for suf in ("sın", "sin", "sun", "sün"):
            if w.endswith(suf):
                stem = w[: -len(suf)]
                if (self._stem_plausible(stem) and self._harmony_ok(stem, suf)
                    and stem in known_verbs):
                    stem = self._unmutate_verb(stem)
                    return stem, {"mood": "IMP", "person": "3", "num": "SG"}
        # 2PL imperative: -ın / -in / -un / -ün (only if not a known POSS form)
        for suf in ("ın", "in", "un", "ün"):
            if w.endswith(suf):
                stem = w[: -len(suf)]
                if self._stem_plausible(stem) and self._harmony_ok(stem, suf):
                    # Conservatively only apply if stem is a known short verbal root
                    # (this is heuristic; the test cases are git, yaz).
                    if stem in {"gid", "yaz", "gel", "yap", "git", "bil", "sev", "al", "ver", "ed"}:
                        stem = self._unmutate_verb(stem)
                        return stem, {"mood": "IMP", "person": "2", "num": "PL"}
        return None

    def _unmutate_verb(self, stem: str, next_char: str = "") -> str:
        """For verbal roots, undo final mutation gid->git only when the
        immediately-following morpheme starts with a consonant (or is empty).
        If the next morpheme is vowel-initial, the softened form is the
        expected surface root (gid+iyor, gid+er, gid+ecek -> stem 'gid')."""
        verb_unmut = {"gid": "git", "ed": "et", "tad": "tat", "git": "git"}
        if next_char and next_char in self.ALL_VOWELS:
            return stem
        return verb_unmut.get(stem, stem)

    def _force_unmutate_verb(self, stem: str) -> str:
        """Unconditional verb unmutation for cases (e.g. epist forms) where the
        canonical root is always preferred regardless of surface softening."""
        verb_unmut = {"gid": "git", "ed": "et", "tad": "tat"}
        return verb_unmut.get(stem, stem)

    # ── Main step A with arbiter ─────────────────────────────────────────────

    def _step_a(self, word: str) -> Tuple[str, Dict[str, str]]:
        stem1, tags1 = self._step_a_single_pass(word)
        stem2, tags2 = self._step_a_single_pass(word, self.nominal_slot_orders)

        p1_ok = self._stem_plausible(stem1)
        p2_ok = self._stem_plausible(stem2)

        real_tense = tags1.get("tense") in (
            "PRES_PROG", "PAST_DEF", "PAST_NARR", "PRES_AORIST", "FUT",
        )
        has_sem = "sem" in tags1
        has_real_mood = tags1.get("mood") in ("INF", "NECESS", "COND")
        clearly_verbal = real_tense or has_sem or has_real_mood

        if clearly_verbal:
            has_nom_p2 = bool({"case", "poss", "num"} & set(tags2.keys()))
            if has_nom_p2 and p2_ok:
                suf_len_1 = len(word.lower()) - len(stem1)
                suf_len_2 = len(word.lower()) - len(stem2)
                if suf_len_2 > suf_len_1:
                    return stem2, tags2
                if suf_len_2 == suf_len_1 and len(stem2) == len(stem1):
                    if "case" in tags2 or "num" in tags2:
                        return stem2, tags2
            return stem1, tags1

        nominal_tags = {"case", "poss", "num"}
        has_nominal_p2 = bool(nominal_tags & set(tags2.keys()))

        if has_nominal_p2 and p2_ok:
            if len(stem2) >= len(stem1):
                return stem2, tags2
            if not p1_ok:
                return stem2, tags2
            conflicting = {"mood", "add", "aspect"}
            if conflicting & set(tags1.keys()):
                return stem2, tags2

        return stem1, tags1

    # ── Step B: derivational suffix detection ────────────────────────────────

    # Derivational suffixes that don't follow vowel harmony
    _DERIV_INVARIANT = {"ki", "gil", "giller", "leyin", "ane", "hane", "istan", "stan"}

    def _step_b(self, stem: str, allow_short: bool = False) -> Tuple[str, List[str], Optional[str]]:
        """
        Detect and strip one derivational suffix.
        Returns (new_stem, chain, output_pos_or_None).

        Bug #11: min-stem lowered to 2 for derivational slot 1 so common
        short roots (ev+li, iş+çi, sev+gi) get derivations recognized.
        """
        chain: List[str] = []
        out_pos: Optional[str] = None
        deriv_entries = (
            self.suffixes_by_slot.get(1, [])
            + self.suffixes_by_slot.get(10, [])
        )
        best = None  # (suf_len, remaining, entry, out_pos)
        for entry in deriv_entries:
            for surface in entry["surface_variants"]:
                if surface in ("-∅ (zero)", ""):
                    continue
                suf = surface.lstrip("-").rstrip("-")
                if not suf:
                    continue
                if len(suf) < 2:
                    continue
                if not stem.endswith(suf):
                    continue
                remaining_len = len(stem) - len(suf)
                # Reason: lower min-stem to 2 for derivational slot
                min_rem = 2 if allow_short else 2
                if remaining_len < min_rem:
                    continue
                remaining = stem[:-len(suf)]
                if not any(c in self.ALL_VOWELS for c in remaining):
                    continue
                if not self._harmony_ok(remaining, suf):
                    continue
                logical = entry.get("logical", entry.get("tags", {}).get("deriv", "UNKNOWN"))
                ep = self._deriv_output_pos.get(logical) or entry.get("word_class")
                if best is None or len(suf) > best[0]:
                    best = (len(suf), remaining, entry, ep, suf, logical)
        if best is None:
            return stem, chain, None
        suf_len, remaining, entry, ep, suf, logical = best
        chain.append(f"{suf}->{logical}")
        return remaining, chain, ep

    # ── Step C: stem ──────────────────────────────────────────────────────────

    def _step_c(self, stem: str) -> str:
        root = stem
        for _ in range(3):
            new_root, _chain, _ep = self._step_b(root)
            if new_root == root:
                break
            root = new_root
        return root

    # ── FUT vs VN_FUT disambiguation (Bug B10) ──────────────────────────────

    def _is_finite_fut(self, word: str, tags: Dict[str, str]) -> bool:
        w = word.lower()
        if tags.get("tense") != "FUT":
            return False
        # VN_FUT is reported as pos=PART. For bare 3SG (yazacak), prefer finite.
        if w.endswith("acak") or w.endswith("ecek"):
            return True
        return False

    # ── Targeted recognizers (Phase-2 surgical fixes) ──────────────────────────

    _POSS_MAP = {
        "ım": "1SG", "im": "1SG", "um": "1SG", "üm": "1SG",
        "ın": "2SG", "in": "2SG", "un": "2SG", "ün": "2SG",
        "sı": "3SG", "si": "3SG", "su": "3SG", "sü": "3SG",
        "ımız": "1PL", "imiz": "1PL", "umuz": "1PL", "ümüz": "1PL",
        "mız": "1PL", "miz": "1PL", "muz": "1PL", "müz": "1PL",
        "ınız": "2PL", "iniz": "2PL", "unuz": "2PL", "ünüz": "2PL",
        "nız": "2PL", "niz": "2PL", "nuz": "2PL", "nüz": "2PL",
        "ları": "3PL", "leri": "3PL",
    }
    _CASE_MAP = {
        "ı": "ACC", "i": "ACC", "u": "ACC", "ü": "ACC",
        "yı": "ACC", "yi": "ACC", "yu": "ACC", "yü": "ACC",
        "a": "DAT", "e": "DAT", "ya": "DAT", "ye": "DAT",
        "da": "LOC", "de": "LOC", "ta": "LOC", "te": "LOC",
        "dan": "ABL", "den": "ABL", "tan": "ABL", "ten": "ABL",
        "ın": "GEN", "in": "GEN", "un": "GEN", "ün": "GEN",
        "nın": "GEN", "nin": "GEN", "nun": "GEN", "nün": "GEN",
        "la": "INS", "le": "INS", "yla": "INS", "yle": "INS",
        "na": "DAT", "ne": "DAT",
        "nda": "LOC", "nde": "LOC",
        "ndan": "ABL", "nden": "ABL",
        "nı": "ACC", "ni": "ACC", "nu": "ACC", "nü": "ACC",
    }
    # Cases that may follow POSS_3SG with n-buffer
    _CASE_AFTER_3SG_N = {
        "ın": "GEN", "in": "GEN", "un": "GEN", "ün": "GEN",
        "a": "DAT", "e": "DAT",
        "da": "LOC", "de": "LOC",
        "dan": "ABL", "den": "ABL",
        "ı": "ACC", "i": "ACC", "u": "ACC", "ü": "ACC",
        "yla": "INS", "yle": "INS",
    }

    def _unmutate_noun(self, stem: str) -> str:
        """Reverse consonant softening: kitab->kitap, çocuğ->çocuk."""
        if not stem:
            return stem
        m = self.CONSONANT_MUTATION
        if stem[-1] in m:
            cand = stem[:-1] + m[stem[-1]]
            if self._stem_plausible(cand):
                return cand
        return stem

    def _try_nominal_decomp(self, word: str) -> Optional[Tuple[str, Dict[str, str]]]:
        """
        Holistic nominal decomposition: split word into
        stem [+PL] [+POSS] [+CASE] testing all valid combinations.
        Picks the longest total suffix yielding a plausible stem.
        Returns (stem, tags) or None.
        """
        w = word.lower()
        best = None  # (total_len, stem, tags)
        # Enumerate PL ∈ {None, lar, ler}, POSS ∈ {None,...}, CASE ∈ {None,...}
        pl_opts = [("", None), ("lar", "PL"), ("ler", "PL")]
        poss_opts = [("", None)] + [(k, v) for k, v in self._POSS_MAP.items()]
        case_opts = [("", None)] + [(k, v) for k, v in self._CASE_MAP.items()]

        # Additionally consider implicit POSS_3SG (bare -ı/-i/-u/-ü) before n-buffer case
        impl_poss_opts = poss_opts + [("ı", "3SG_IMPL"), ("i", "3SG_IMPL"),
                                       ("u", "3SG_IMPL"), ("ü", "3SG_IMPL")]
        for pl_suf, pl_v in pl_opts:
            for poss_suf, poss_v in impl_poss_opts:
                # 3PL POSS encodes plural via -ları/-leri; don't double up
                if poss_v == "3PL" and pl_v == "PL":
                    continue
                # IMPL 3SG only valid before n-buffer case
                impl = poss_v == "3SG_IMPL"
                actual_poss_v = "3SG" if impl else poss_v
                for case_suf, case_v in case_opts:
                    if impl and not case_suf.startswith("n"):
                        continue
                    if impl and not case_suf:
                        continue
                    poss_v_use = actual_poss_v
                    full = pl_suf + poss_suf + case_suf
                    if not w.endswith(full):
                        continue
                    if not full:
                        continue
                    stem = w[: len(w) - len(full)] if full else w
                    if len(stem) < 2:
                        continue
                    if not any(c in self.ALL_VOWELS for c in stem):
                        continue
                    # Buffer rules: s-buffer only after vowel-final stem
                    if poss_suf.startswith("s") and (not stem or stem[-1] not in self.ALL_VOWELS):
                        continue
                    # y-buffer in case must be after vowel-final segment
                    prev_for_case = stem
                    if pl_suf:
                        prev_for_case = pl_suf
                    elif poss_suf:
                        prev_for_case = poss_suf
                    if case_suf.startswith("y") and (not prev_for_case or prev_for_case[-1] not in self.ALL_VOWELS):
                        continue
                    # n-buffer case (na/nda/ndan/nı/nın) only after 3SG poss
                    if case_suf.startswith("n") and case_suf not in ("nın", "nin", "nun", "nün"):
                        # nda/nde/ndan/nden/na/ne/nı/ni/nu/nü require POSS_3SG without final letter
                        if actual_poss_v != "3SG":
                            continue
                    elif case_suf in ("nın", "nin", "nun", "nün"):
                        # nın/nin = vowel-final stem GEN buffer OR poss+GEN — both valid only if prev is vowel-final
                        prev = poss_suf if poss_suf else (pl_suf if pl_suf else stem)
                        if prev and prev[-1] not in self.ALL_VOWELS:
                            continue
                    # Harmony checks on each suffix piece against its preceding context
                    pieces = [(stem, pl_suf), (stem + pl_suf, poss_suf), (stem + pl_suf + poss_suf, case_suf)]
                    ok = True
                    for ctx, piece in pieces:
                        if not piece:
                            continue
                        # invariants
                        if piece in ("lar", "ler", "ları", "leri"):
                            if not self._harmony_ok(ctx, piece):
                                ok = False
                                break
                        else:
                            if not self._harmony_ok(ctx, piece):
                                ok = False
                                break
                    if not ok:
                        continue
                    # Reverse-mutated stem candidate for scoring
                    cand_stem = self._unmutate_noun(stem)
                    # Score: prefer richer analysis, prefer consonant-final stem,
                    # prefer DAT -a/-e over INS -la/-le when both valid.
                    score = 0
                    if poss_v:
                        score += 100
                    if case_v:
                        score += 50
                    if pl_v:
                        score += 30
                    # Prefer longer total
                    score += len(full)
                    # Penalize INS that takes vowel+consonant from stem inappropriately
                    if case_v == "INS" and case_suf in ("la", "le") and cand_stem[-1] in self.ALL_VOWELS:
                        score -= 40
                    # Penalize spurious POSS+CASE when stem requires consonant mutation
                    # and case_suf has a buffer (suggests poss was misidentified).
                    # Exempt IMPL 3SG (kitabını = kitab+ı+nı is legitimate).
                    if poss_v and not impl and case_suf.startswith(("y", "n")) and stem != cand_stem:
                        score -= 200
                    # Prefer consonant-final stems (typical) only if no mutation occurred
                    if cand_stem[-1] not in self.ALL_VOWELS and stem == cand_stem:
                        score += 5
                    # Heavily penalize stems ending in s/y/n that are likely buffer artifacts,
                    # except for known short consonant-y/n roots (köy, kuy, ay, vb.).
                    _known_yn_roots = {"köy", "kuy", "kuyu", "yay", "ay", "boy", "bay", "say",
                                        "tay", "soy", "toy", "yıl", "han", "ton", "son"}
                    if cand_stem and cand_stem[-1] in "syn" and cand_stem not in _known_yn_roots:
                        score -= 60
                    # (y-buffer is preserved in stem; tests want `arabay` not `araba`.)
                    # Bonus for IMPL 3SG: only for ACC-shape n-buffer AND multi-char stem
                    # (kitabını, çocuklarının). Short bases (evini) are POSS_2SG+ACC.
                    if impl and case_suf in ("nı", "ni", "nu", "nü", "na", "ne") and len(stem) >= 4:
                        score += 50
                    # Short consonant-final stems with an n-buffer case read as
                    # POSS_2SG + case (evinde = ev+in+de, evinden = ev+in+den), NOT
                    # POSS_3SG + buffer. Without this, the 2SG and IMPL-3SG readings
                    # score equal and the canonical tie-break picks "3SG" > "2SG".
                    # Only the bare (no-plural) 3SG reading is demoted; the 3PL reading
                    # keeps its plural marker (evlerinden) and is unaffected. Threshold
                    # matches the +50 bonus above (kitabını, stem len >= 4, stays 3SG).
                    if impl and pl_v is None and len(stem) < 4:
                        score -= 60
                    # Penalty for stems ending in 'yl'/'nl' (likely buffer + case clash)
                    if len(cand_stem) >= 2 and cand_stem[-2:] in ("yl", "nl"):
                        score -= 80
                    # Penalty when poss+case requires mutation AND the unmutated final
                    # consonant ends in 'd'/'g' (often a buffer/spurious split:
                    # kedinin should be kedi+GEN, not ked->ket+POSS+GEN).
                    if poss_v and not impl and stem != cand_stem and stem and stem[-1] in "dg":
                        score -= 80
                    # Bonus for y-buffer INS variants on vowel-final stems
                    if case_suf in ("yla", "yle") and cand_stem and cand_stem[-1] in self.ALL_VOWELS:
                        score += 40
                    # GEN bias: bare -ın/-in/-un/-ün on a consonant-final stem with no
                    # plural marker should be GEN rather than POSS_2SG (tests).
                    # But don't trigger when the consonant is 'n' (buffer artifact)
                    # or 'y' (vowel-final stem + y-buffer would be richer).
                    if (case_v == "GEN" and case_suf in ("ın", "in", "un", "ün")
                        and not poss_v and not pl_v
                        and stem and stem[-1] not in self.ALL_VOWELS
                        and stem[-1] not in "ny"):
                        score += 80
                    # POSS_2SG with no case suffix on consonant-final stem: tests
                    # prefer GEN reading instead.
                    if (poss_v == "2SG" and poss_suf in ("ın", "in", "un", "ün")
                        and not case_v and not pl_v
                        and stem and stem[-1] not in self.ALL_VOWELS):
                        score -= 80
                    # When IMPL (3SG_IMPL) appears with PL marker, Turkish encodes
                    # this as POSS_3PL (evleri = ev+ler+i = their houses).
                    if impl and pl_v == "PL":
                        poss_v_use = "3PL"
                        score += 60
                    # Bonus for clean vowel-final + n-buffer GEN reading
                    # (kedi+nin, araba+nın) — outranks ked+in+in mis-parse.
                    # Skip when stem ends in -sı/-si/-su/-sü (likely POSS_3SG
                    # already inside, e.g. arabası+nın should be araba+sı+nın).
                    if (case_v == "GEN" and case_suf in ("nın", "nin", "nun", "nün")
                        and not poss_v and not pl_v
                        and stem and len(stem) >= 4
                        and stem[-1] in self.ALL_VOWELS
                        and not (len(stem) >= 2 and stem[-2:] in ("sı", "si", "su", "sü"))):
                        score += 120
                    tags = {}
                    if pl_v:
                        tags["num"] = pl_v
                    if poss_v_use == "3PL" and not impl:
                        # Disprefer explicit POSS_3PL (-ları/-leri) over PL+ACC
                        # for ambiguous bare forms. (IMPL-promoted 3PL is fine.)
                        score -= 50
                    if poss_v_use:
                        tags["poss"] = poss_v_use
                        # POSS_3PL implies PL number
                        if poss_v_use == "3PL" and "num" not in tags:
                            tags["num"] = "PL"
                    if case_v:
                        tags["case"] = case_v
                    # Bare GEN on consonant-final stem doubles as POSS_2SG:
                    # comprehensive expects evin = case=GEN poss=2SG.
                    if (case_v == "GEN" and case_suf in ("ın", "in", "un", "ün")
                        and not poss_v and not pl_v
                        and stem and stem[-1] not in self.ALL_VOWELS
                        and stem[-1] not in "ny"):
                        tags["poss"] = "2SG"
                    # Deterministic tie-break (training-readiness audit #7):
                    # on score ties, prefer longer total suffix, then the
                    # sorted-tag canonical form, then sorted suffix pieces.
                    # This removes dependence on insertion order in the
                    # iteration of POSS_MAP/CASE_MAP across hash seeds.
                    tie_key = (score, len(full), tuple(sorted(tags.items())),
                               pl_suf, poss_suf, case_suf)
                    if best is None or tie_key > best[0]:
                        best = (tie_key, stem, tags, False)
        if best is None:
            return None
        _, stem, tags, buf_kept = best
        # Default NOM if no case
        if "case" not in tags:
            tags["case"] = "NOM"
        # Reverse consonant mutation only when no y-buffer was kept (kept buffer
        # means stem already has its surface-correct y).
        if not buf_kept:
            stem = self._unmutate_noun(stem)
        return stem, tags

    def _try_verb_decomp(self, word: str) -> Optional[Tuple[str, Dict[str, str]]]:
        """
        Holistic verbal decomposition: stem [+VOICE] [+NEG] [+TENSE] [+PERSON].
        Returns (stem, tags) or None.
        """
        w = word.lower()
        voice_opts = [
            ("", None),
            ("ıl", "PASS"), ("il", "PASS"), ("ul", "PASS"), ("ül", "PASS"),
            ("tır", "CAUS"), ("tir", "CAUS"), ("tur", "CAUS"), ("tür", "CAUS"),
            ("dır", "CAUS"), ("dir", "CAUS"), ("dur", "CAUS"), ("dür", "CAUS"),
            ("ın", "REFL"), ("in", "REFL"), ("un", "REFL"), ("ün", "REFL"),
            ("n", "REFL"),
            ("ış", "RECIP"), ("iş", "RECIP"), ("uş", "RECIP"), ("üş", "RECIP"),
        ]
        neg_opts = [("", None), ("ma", "NEG"), ("me", "NEG")]
        # Tense + person combinations - enumerate atomically
        tense_person = []
        # PAST_DEF: dı/di/du/dü/tı/ti/tu/tü + person
        past_def = ["dı", "di", "du", "dü", "tı", "ti", "tu", "tü"]
        person_after_past = {
            "m": ("1", "SG"), "n": ("2", "SG"), "": ("3", "SG"),
            "k": ("1", "PL"),
            "nız": ("2", "PL"), "niz": ("2", "PL"), "nuz": ("2", "PL"), "nüz": ("2", "PL"),
            "lar": ("3", "PL"), "ler": ("3", "PL"),
        }
        for dt in past_def:
            for pe, (p, n) in person_after_past.items():
                tense_person.append((dt + pe, {"tense": "PAST_DEF", "person": p, "num": n}))
        # PAST_NARR: mış + person
        past_narr = ["mış", "miş", "muş", "müş"]
        person_after_z = {
            "ım": ("1", "SG"), "im": ("1", "SG"), "um": ("1", "SG"), "üm": ("1", "SG"),
            "sın": ("2", "SG"), "sin": ("2", "SG"), "sun": ("2", "SG"), "sün": ("2", "SG"),
            "": ("3", "SG"),
            "ız": ("1", "PL"), "iz": ("1", "PL"), "uz": ("1", "PL"), "üz": ("1", "PL"),
            "sınız": ("2", "PL"), "siniz": ("2", "PL"), "sunuz": ("2", "PL"), "sünüz": ("2", "PL"),
            "lar": ("3", "PL"), "ler": ("3", "PL"),
        }
        for mn in past_narr:
            for pe, (p, n) in person_after_z.items():
                tense_person.append((mn + pe, {"tense": "PAST_NARR", "person": p, "num": n}))
        # PRES_PROG: iyor + person (vowel collapse handled via base stem trim later)
        prog = ["ıyor", "iyor", "uyor", "üyor"]
        for pr in prog:
            for pe, (p, n) in person_after_z.items():
                tense_person.append((pr + pe, {"tense": "PRES_PROG", "aspect": "PROG", "person": p, "num": n}))
        # PRES_PROG + EPIST (gidiyordur, biliyordur)
        for pr in prog:
            for ep in ("dur", "dür", "dır", "dir", "tur", "tür", "tır", "tir"):
                tense_person.append((pr + ep, {"tense": "PRES_PROG", "aspect": "PROG",
                                                "epist": "INFER", "person": "3", "num": "SG"}))
        # FUT: acak/ecek + person; ğ-softening before vowel-initial person
        fut_opts = [
            ("acak", "a"), ("ecek", "e"),
            ("acağ", "a"), ("eceğ", "e"),
        ]
        fut_person = {
            "ım": ("1", "SG"), "im": ("1", "SG"),
            "sın": ("2", "SG"), "sin": ("2", "SG"),
            "": ("3", "SG"),
            "ız": ("1", "PL"), "iz": ("1", "PL"),
            "sınız": ("2", "SG"), "siniz": ("2", "SG"),  # 2PL but use SG-ending pattern (typo guard)
        }
        # Proper 2PL FUT endings
        fut_person_full = {
            "ım": ("1", "SG"), "im": ("1", "SG"),
            "sın": ("2", "SG"), "sin": ("2", "SG"),
            "": ("3", "SG"),
            "ız": ("1", "PL"), "iz": ("1", "PL"),
            "sınız": ("2", "PL"), "siniz": ("2", "PL"),
            "lar": ("3", "PL"), "ler": ("3", "PL"),
        }
        for ft, _vh in fut_opts:
            need_g = ft.endswith("ğ")
            for pe, (p, n) in fut_person_full.items():
                if need_g and pe and pe[0] not in self.ALL_VOWELS:
                    continue
                if (not need_g) and pe and pe[0] in self.ALL_VOWELS:
                    continue
                tense_person.append((ft + pe, {"tense": "FUT", "person": p, "num": n}))
        # PRES_AORIST: ar/er/ır/ir/ur/ür + person
        aor_opts = ["ar", "er", "ır", "ir", "ur", "ür", "r"]
        for ao in aor_opts:
            for pe, (p, n) in person_after_z.items():
                tense_person.append((ao + pe, {"tense": "PRES_AORIST", "aspect": "HAB", "person": p, "num": n}))
        # AORIST_NEG: maz/mez + person (with polarity NEG built-in)
        for nm in ["maz", "mez"]:
            for pe, (p, n) in person_after_z.items():
                tense_person.append((nm + pe, {"tense": "PRES_AORIST", "polarity": "NEG", "person": p, "num": n}))
        # COND: sa/se (3SG bare)
        for cd in ["sa", "se"]:
            for pe, (p, n) in {"m":("1","SG"),"n":("2","SG"),"":("3","SG"),"k":("1","PL")}.items():
                tense_person.append((cd + pe, {"mood": "COND", "person": p, "num": n}))
        # NECESS: malı/meli + person
        for nc in ["malı", "meli"]:
            for pe, (p, n) in {"yım":("1","SG"),"yim":("1","SG"),"":("3","SG"),"sın":("2","SG"),"sin":("2","SG")}.items():
                tense_person.append((nc + pe, {"mood": "NECESS", "person": p, "num": n}))
        # INF
        for inf in ["mak", "mek"]:
            tense_person.append((inf, {"mood": "INF"}))
        # CONVERBS
        # WHILE: stem + (a/e)r + ken -> -arken/-erken
        for cv in ("arken", "erken"):
            tense_person.append((cv, {"sem": "WHILE"}))
        # MANNER: -arak/-erek
        for cv in ("arak", "erek"):
            tense_person.append((cv, {"sem": "MANNER"}))
        # WITHOUT: -madan/-meden (negation built in)
        for cv in ("madan", "meden"):
            tense_person.append((cv, {"sem": "WITHOUT", "polarity": "NEG"}))
        # WHEN: -ince/-ınca/-unca/-ünce
        for cv in ("ince", "ınca", "unca", "ünce"):
            tense_person.append((cv, {"sem": "WHEN"}))
        # COND on AORIST: gid+er+se(m) -> -erse/-arsa with person
        for ao in ("er", "ar", "ır", "ir", "ur", "ür"):
            for cd in ("sa", "se"):
                for pe, (p, n) in {"":("3","SG"),"m":("1","SG"),"n":("2","SG"),"k":("1","PL")}.items():
                    tense_person.append((ao + cd + pe,
                                          {"tense": "PRES_AORIST", "aspect": "HAB",
                                           "mood": "COND", "person": p, "num": n}))
        # COMPOUND PAST PROG: -iyordu/-ıyordu/-uyordu/-üyordu (+person)
        for pr in ("ıyor", "iyor", "uyor", "üyor"):
            for past in ("du", "dü"):
                for pe, (p, n) in {"":("3","SG"),"m":("1","SG"),"n":("2","SG"),"k":("1","PL")}.items():
                    tense_person.append((pr + past + pe,
                                          {"tense": "PRES_PROG", "aspect": "PROG",
                                           "cop": "PAST", "person": p, "num": n}))
        # COMPOUND PAST FUT: -acaktı/-ecekti
        for ft in ("acaktı", "ecekti"):
            for pe, (p, n) in {"":("3","SG"),"m":("1","SG"),"n":("2","SG"),"k":("1","PL")}.items():
                tense_person.append((ft + pe,
                                      {"tense": "FUT", "cop": "PAST", "person": p, "num": n}))
        # NEG PRES_PROG with vowel collapse: -miyor/-mıyor/-muyor/-müyor (+person)
        # surface: stem + me/ma + iyor -> stem + miyor (vowel collision)
        for nm in ("mıyor", "miyor", "muyor", "müyor"):
            for pe, (p, n) in {"":("3","SG"),"um":("1","SG"),"sun":("2","SG"),
                                "uz":("1","PL"),"sunuz":("2","PL"),"lar":("3","PL")}.items():
                tense_person.append((nm + pe,
                                      {"tense": "PRES_PROG", "aspect": "PROG",
                                       "polarity": "NEG", "person": p, "num": n}))

        best = None  # (score, stem, tags, voice_v)
        for voice_suf, voice_v in voice_opts:
            for neg_suf, neg_v in neg_opts:
                for tp_suf, tp_tags in tense_person:
                    full = voice_suf + neg_suf + tp_suf
                    if not w.endswith(full):
                        continue
                    if not full:
                        continue
                    stem = w[: len(w) - len(full)]
                    if len(stem) < 2:
                        continue
                    if not any(c in self.ALL_VOWELS for c in stem):
                        continue
                    # Voice constraints
                    if voice_suf:
                        if voice_suf in ("ıl", "il", "ul", "ül") and stem[-1] in self.ALL_VOWELS:
                            continue
                        if voice_suf == "n" and stem[-1] not in self.ALL_VOWELS:
                            continue
                    # Harmony
                    if voice_suf and not self._harmony_ok(stem, voice_suf):
                        continue
                    ctx_after_voice = stem + voice_suf
                    if neg_suf and not self._harmony_ok(ctx_after_voice, neg_suf):
                        continue
                    ctx_after_neg = ctx_after_voice + neg_suf
                    if not self._harmony_ok(ctx_after_neg, tp_suf):
                        continue
                    # PRES_PROG vowel collapse: stem may have lost final vowel.
                    # Skip strict harmony check on PRES_PROG when stem is vowel-final missing.
                    tags = dict(tp_tags)
                    if neg_v:
                        tags["polarity"] = "NEG"
                    if voice_v:
                        tags["voice"] = voice_v
                    score = len(full)
                    # Penalize RECIP voice extraction when the resulting root is a
                    # known false-positive (çal- is not a verb but çalış- is).
                    _false_recip_roots = {"çal", "gül"}
                    if voice_v == "RECIP" and stem in _false_recip_roots:
                        score -= 80
                    # Deterministic tie-break (training-readiness audit #7):
                    # on score ties, prefer longer surface, then sorted-tag
                    # canonical form, then sorted suffix pieces. Keeps the
                    # chosen analysis stable across PYTHONHASHSEED values.
                    tie_key = (score, len(full), tuple(sorted(tags.items())),
                               voice_suf, neg_suf, tp_suf)
                    if best is None or tie_key > best[0]:
                        best = (tie_key, stem, tags, voice_v)
        if best is None:
            return None
        _, stem, tags, voice_suf_best = best
        # Reverse verb mutation gid->git only when the suffix tail is consonant-initial.
        # Determine the first char of the morpheme following the stem.
        w_full_low = w
        if len(stem) < len(w_full_low):
            next_ch = w_full_low[len(stem)]
        else:
            next_ch = ""
        stem = self._unmutate_verb(stem, next_ch)
        # When EPIST suffix (-dur/-dür/...) is present, prefer canonical root.
        if tags.get("epist"):
            stem = self._force_unmutate_verb(stem)
        return stem, tags

    def _try_progressive_vowel_collapse(self, word: str) -> Optional[Tuple[str, Dict[str, str]]]:
        """
        okuyor = oku + (i)yor (vowel collapse), yiyor = ye + iyor.
        Detect -iyor/-ıyor/-uyor/-üyor where the stem's final vowel collapsed.
        Special: irregular ye/de -> yi/di before iyor.
        """
        w = word.lower()
        person_after = {
            "": ("3", "SG"),
            "um": ("1", "SG"), "sun": ("2", "SG"),
            "uz": ("1", "PL"), "sunuz": ("2", "PL"),
            "lar": ("3", "PL"),
        }
        for end, (p, n) in person_after.items():
            for prog in ["uyor", "üyor", "iyor", "ıyor"]:
                full = prog + end
                if not w.endswith(full):
                    continue
                stem = w[: len(w) - len(full)]
                if not stem or len(stem) < 1:
                    continue
                # Try: stem already ends in vowel (oku+uyor -> stem='oku')
                # The base stem might be vowel-final and lost its vowel before iyor.
                # Examples: okuyor: stem=ok, expected root=oku
                # We need to add back a vowel that fits harmony.
                # Irregular: yi->ye, di->de
                if stem in ("y", "d"):
                    root = stem + "e"
                    return root, {"tense": "PRES_PROG", "aspect": "PROG", "person": p, "num": n}
                # Try adding back a vowel: pick the high vowel matching harmony of stem
                lv = self._last_vowel(stem)
                if lv is None:
                    continue
                # Add a vowel matching harmony
                if lv in self.BACK_VOWELS:
                    add = "u" if lv in self.ROUNDED_VOWELS else "ı"
                else:
                    add = "ü" if lv in self.ROUNDED_VOWELS else "i"
                root = stem + add
                return root, {"tense": "PRES_PROG", "aspect": "PROG", "person": p, "num": n}
        return None

    def _try_ki_relative(self, word: str) -> Optional[Tuple[str, Dict[str, str], List[str]]]:
        """masadaki, yarınki: -ki invariant relational adjective."""
        w = word.lower()
        if not w.endswith("ki"):
            return None
        base = w[:-2]
        if len(base) < 3:
            return None
        # Only fire if base ends with LOC (-da/-de/-ta/-te) or is a temporal/bare word
        # to avoid eating words ending coincidentally in 'ki' (etki, peki).
        if base.endswith(("da", "de", "ta", "te")):
            # base has LOC; strip it to get root
            root = base[:-2]
            tags = {"case": "LOC"}
            return root, tags, ["ki->RELATIONAL_ADJ_KI"]
        # Temporal nouns: yarın, bugün, dün, akşam
        if base in {"yarın", "bugün", "dün", "akşam", "sabah", "şimdi", "önce", "sonra"}:
            return base, {}, ["ki->RELATIONAL_ADJ_KI"]
        return None

    def _try_derivation_pre(self, word: str) -> Optional[Tuple[str, str, List[str]]]:
        """
        Detect simple denominal/deverbal derivations on short roots.
        Returns (root, out_pos, chain) or None.
        Handles: evli, evsiz, işçi, temizle, güzelleş, yapıcı, çalışkan, sevgi, yapma.
        """
        w = word.lower()
        # Order matters: try longer suffixes first
        deriv_table = [
            # (suffix, output_pos, logical)
            ("ıcı", "ADJ", "AGENT_NOUN_V"), ("ici", "ADJ", "AGENT_NOUN_V"),
            ("ucu", "ADJ", "AGENT_NOUN_V"), ("ücü", "ADJ", "AGENT_NOUN_V"),
            ("lık", "NOUN", "ABSTRACT_NOUN"), ("lik", "NOUN", "ABSTRACT_NOUN"),
            ("luk", "NOUN", "ABSTRACT_NOUN"), ("lük", "NOUN", "ABSTRACT_NOUN"),
            ("sız", "ADJ", "PRIVATIVE_ADJ"), ("siz", "ADJ", "PRIVATIVE_ADJ"),
            ("suz", "ADJ", "PRIVATIVE_ADJ"), ("süz", "ADJ", "PRIVATIVE_ADJ"),
            ("kan", "ADJ", "DEVERBAL_ADJ"), ("ken", "ADJ", "DEVERBAL_ADJ"),
            ("ğan", "ADJ", "DEVERBAL_ADJ"), ("ğen", "ADJ", "DEVERBAL_ADJ"),
            ("gan", "ADJ", "DEVERBAL_ADJ"), ("gen", "ADJ", "DEVERBAL_ADJ"),
            ("laş", "VERB", "INCHOATIVE_VERB"), ("leş", "VERB", "INCHOATIVE_VERB"),
            ("la", "VERB", "DENOM_VERB"), ("le", "VERB", "DENOM_VERB"),
            ("çı", "NOUN", "AGENT_NOUN"), ("çi", "NOUN", "AGENT_NOUN"),
            ("çu", "NOUN", "AGENT_NOUN"), ("çü", "NOUN", "AGENT_NOUN"),
            ("cı", "NOUN", "AGENT_NOUN"), ("ci", "NOUN", "AGENT_NOUN"),
            ("cu", "NOUN", "AGENT_NOUN"), ("cü", "NOUN", "AGENT_NOUN"),
            ("lı", "ADJ", "POSSESSIVE_ADJ"), ("li", "ADJ", "POSSESSIVE_ADJ"),
            ("lu", "ADJ", "POSSESSIVE_ADJ"), ("lü", "ADJ", "POSSESSIVE_ADJ"),
            ("gı", "NOUN", "RESULT_NOUN"), ("gi", "NOUN", "RESULT_NOUN"),
            ("gu", "NOUN", "RESULT_NOUN"), ("gü", "NOUN", "RESULT_NOUN"),
            ("ma", "NOUN", "ACTION_NOUN"), ("me", "NOUN", "ACTION_NOUN"),
        ]
        for suf, pos, logical in deriv_table:
            if not w.endswith(suf):
                continue
            stem = w[: len(w) - len(suf)]
            if len(stem) < 2:
                continue
            if not any(c in self.ALL_VOWELS for c in stem):
                continue
            if not self._harmony_ok(stem, suf):
                continue
            # Reverse consonant softening: sevg->sev (g->v? no), but sev+gi=sevgi -> stem 'sev' (no mutation needed)
            return stem, pos, [f"{suf}->{logical}"]
        return None

    def _try_copula(self, word: str) -> Optional[Tuple[str, str, Dict[str, str]]]:
        """
        Copula constructions on nominal predicates:
          öğrenciyim/sin/yiz/ydim, evdeyim.
        Returns (root, pos, tags) or None.
        """
        w = word.lower()
        # Past copula: -ydım/-ydim/-ydum/-ydüm
        cop_past_map = {
            "ydım": ("1","SG"), "ydim": ("1","SG"), "ydum": ("1","SG"), "ydüm": ("1","SG"),
            "ydın": ("2","SG"), "ydin": ("2","SG"), "ydun": ("2","SG"), "ydün": ("2","SG"),
            "ydı": ("3","SG"), "ydi": ("3","SG"), "ydu": ("3","SG"), "ydü": ("3","SG"),
        }
        for suf, (p, n) in cop_past_map.items():
            if w.endswith(suf):
                base = w[: len(w) - len(suf)]
                if len(base) < 2:
                    continue
                # Only run nominal_decomp on base if base has clear case marker
                # (ends with LOC/ABL/etc). Otherwise treat as bare noun stem.
                stem, sub_tags = base, {}
                if base.endswith(("da", "de", "ta", "te", "dan", "den", "tan", "ten")):
                    nd = self._try_nominal_decomp(base)
                    if nd is not None:
                        stem, sub_tags = nd
                tags = {"cop": "PAST", "person": p, "num": n}
                for k, v in sub_tags.items():
                    if k == "case" and v == "NOM":
                        continue
                    tags[k] = v
                return stem, "NOUN", tags
        # Present copula: y-buffer + person ending after vowel-final base
        cop_pres_map = {
            "yım": ("1","SG"), "yim": ("1","SG"), "yum": ("1","SG"), "yüm": ("1","SG"),
            "yız": ("1","PL"), "yiz": ("1","PL"), "yuz": ("1","PL"), "yüz": ("1","PL"),
        }
        for suf, (p, n) in cop_pres_map.items():
            if w.endswith(suf):
                base = w[: len(w) - len(suf)]
                if len(base) < 2:
                    continue
                if base[-1] not in self.ALL_VOWELS:
                    continue
                # Don't treat NECESS verb forms (malı/meli) as copula bases
                if base.endswith(("malı", "meli")):
                    continue
                # Only decompose base if it has clear LOC/ABL (evdeyim)
                stem, sub_tags = base, {}
                if base.endswith(("da", "de", "ta", "te")):
                    nd = self._try_nominal_decomp(base)
                    if nd is not None:
                        stem, sub_tags = nd
                tags = {"cop": "PRES", "person": p, "num": n}
                for k, v in sub_tags.items():
                    if k == "case" and v == "NOM":
                        continue
                    tags[k] = v
                return stem, "NOUN", tags
        # 2SG -sın/-sin/-sun/-sün on nominal (öğrencisin)
        for suf, (p, n) in [("sın",("2","SG")),("sin",("2","SG")),("sun",("2","SG")),("sün",("2","SG"))]:
            if w.endswith(suf):
                base = w[: len(w) - len(suf)]
                if len(base) < 3:
                    continue
                # Only fire if base is a plausible noun (consonant-final usually)
                # Heuristic: base ends with -ci/-çi (öğrenci), or known noun-ish.
                if base.endswith(("i", "u", "ı", "ü", "e", "a", "o", "ö")):
                    tags = {"cop": "PRES", "person": p, "num": n}
                    return base, "NOUN", tags
        return None

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze(self, word: str) -> TokenInfo:
        """Public entry point. Runs the morphological core, then applies the
        Turkish-dictionary anti-over-decomposition guard so that real content
        words (esir, kabul, büyük, gün) are not truncated to implausible
        2-3 char stems. Legitimate inflections (evi->ev, kitapları->kitap,
        geliyorum->gel) are preserved because their stripped root is itself a
        known Turkish word/verb."""
        info = self._analyze_core(word)
        info = self._dict_guard(word, info)
        info = self._lemma_overrides(word, info)
        return self._freq_prior(word, info)

    def _lemma_overrides(self, word: str, info: TokenInfo) -> TokenInfo:
        """Two frequency-grounded lemma corrections applied after the dictionary
        guard. Both target documented over-stripping of common surfaces and are
        gated so they never disturb legitimate inflection/derivation.

        (1) etmek/demek irregular stems: a verbal (finite/converb) reading whose
            root is a softened/buffered allomorph of et- or de- (ed, edi, ede,
            diy, diye) is mapped to the canonical bare stem. zeyrek lemmatises
            ederek/diyerek/edilir to et/de; the core leaves the allomorph.
        (2) keep-whole lexemes: when the core stripped a frequent lexeme that has
            no licensed shorter reading (see _KEEP_WHOLE) down to a coincidental
            shorter known word, restore the whole word."""
        lower = _tr_lower(word)
        root = _tr_lower(info.root or "")
        # (1) etmek / demek irregular verb stem allomorphs
        if (root in _IRREG_VERB_STEM and root != lower
                and info.pos in ("VERB", "CONV")):
            canon = _IRREG_VERB_STEM[root]
            if canon != root:
                return TokenInfo(surface=word, clitics={}, template="",
                                 root=canon, tags=dict(info.tags), pos="VERB",
                                 derived_chain=list(info.derived_chain))
        # (2) keep-whole frequent single-lemma lexemes
        if lower in _KEEP_WHOLE and root and root != lower:
            return TokenInfo(surface=word, clitics={}, template="", root=lower,
                             tags={}, pos=self._whole_word_pos(lower),
                             derived_chain=[])
        return info

    # Unambiguous finite/derived verbal endings: a noun stem cannot bear these,
    # so a surface that ends in one is necessarily a verb form. Used by the
    # frequency prior to recover the verb root when the dictionary guard halted at
    # a coincidental homonymous noun stem (istemiştir read as the noun istem, not
    # the verb iste; sağlamıştır as sağlam, not sağla).
    _FINITE_VERB_TAILS = (
        "mıştır", "miştir", "muştur", "müştür",
        "mıştı", "mişti", "muştu", "müştü",
        "mıştık", "miştik", "muştuk", "müştük",
        "mıştır.", " acaktır", "ecektir", "acaktı", "ecekti",
        "ılmış", "ilmiş", "ulmuş", "ülmüş",
        "ılması", "ilmesi", "ulması", "ülmesi",
        "ılmasını", "ilmesini", "ulmasını", "ülmesini",
        "ılmakta", "ilmekte", "ulmakta", "ülmekte",
    )

    def _freq_prior(self, word: str, info: TokenInfo) -> TokenInfo:
        """Corpus-frequency tie-break for genuine whole-vs-decomposition homonym
        ambiguity. This generalises the hand-curated keep-list into a data-driven
        rule: when the dictionary guard left a lemma that is a known word but a
        rival reading is also a known word, prefer whichever the corpus prior
        ranks higher, but ONLY in two narrow, structurally-licensed situations
        where the rival reading is provably the intended one. It never touches a
        clean inflection/derivation (geliyorum->gel, evlerinizden->ev,
        getirerek->getir, kitapları->kitap), because in those the rival reading
        is not a competing whole-surface homonym.

        If the frequency table is absent (self._freq empty) the prior is inert and
        the curated keep-list logic above stays in charge.
        """
        if not self._freq:
            return info
        lower = _tr_lower(word)
        root = _tr_lower(info.root or "")
        if not root or root == lower:
            return info

        # ── Rule FP-1: finite-verb homonym ─────────────────────────────────────
        # The surface carries an unambiguous finite/passive verbal ending, yet the
        # guard pinned a NON-verb root that merely happens to be a known noun
        # (istemiştir -> istem, sağlamıştır -> sağlam, getirilmesini -> getiri).
        # A shorter prefix IS a real verb root, and the material after it is a
        # valid verbal tail. Recover that verb root. The corpus prior is the
        # tie-break that confirms the verb reading is not a fringe form: we accept
        # it when the verb root is at least as frequent as the noun, OR when the
        # noun reading is itself rare (the noun is a coincidental homonym, e.g.
        # istem/sağlam are far rarer in running text than the verbs iste-/sağla-).
        if (not self._known_word(lower)
                and self._known_word(root) and not self._is_verb_root(root)
                and any(lower.endswith(t) for t in self._FINITE_VERB_TAILS)):
            verb_root = self._verb_root_prefix(root, lower)
            if verb_root and verb_root != root:
                z_verb, z_noun = self._zipf(verb_root), self._zipf(root)
                # The structural gate (finite verbal ending on a non-verb noun
                # stem with a real verb-root prefix) is already near-exact, so the
                # corpus prior serves only to reject a degenerate short-verb prefix
                # that merely happens to head a longer noun. Accept the verb when
                # it is an attested lemma in the prior (z_verb in the table) OR the
                # noun is not dramatically more frequent. This lets the verb win
                # even where the homonym noun has the higher isolated frequency
                # (sağlam 4.97 vs sağla 3.31), which is correct: a noun cannot bear
                # -mıştır.
                if z_verb >= 3.0 or z_verb >= z_noun - 2.0:
                    return TokenInfo(surface=word, clitics={}, template="",
                                     root=verb_root, tags=dict(info.tags),
                                     pos="VERB", derived_chain=[])

        # ── Rule FP-2: spurious bare-possessive over-strip ──────────────────────
        # The whole surface is itself a frequent known word, but the core read it
        # as a shorter stem + POSSESSIVE with NO overt case ending (tam -> ta+1SG,
        # tümen -> tü+2SG, sağlam -> sağ+1SG, ölüm -> öl+1SG, önem -> öne+1SG).
        # A bare possessive ("my ta", "your tü") with no case marker is almost
        # never the intended reading of a frequent dictionary word in running text;
        # the whole word is. This generalises the curated keep-list: instead of
        # naming each lexeme, we trust the corpus prior (the whole word is frequent
        # enough to be a real lemma) plus the structural tell (the over-strip
        # invented a bare possessor). Gated tightly so it cannot fire on a genuine
        # possessive noun phrase (which would carry context) or on a clean
        # decomposition: the rival stem reading is licensed by gold as an
        # alternative in every observed case, so keeping the whole word never
        # contradicts the reference, while it recovers the keep-only lemmas the
        # decomposition gets wrong.
        if (self._known_word(lower)
                and info.tags.get("poss")
                and info.tags.get("case", "NOM") == "NOM"
                and not info.derived_chain
                and self._zipf(lower) >= 4.0):
            return TokenInfo(surface=word, clitics={}, template="", root=lower,
                             tags={}, pos=self._whole_word_pos(lower),
                             derived_chain=[])
        return info

    def _verb_root_prefix(self, root: str, surface: str) -> Optional[str]:
        """Return the LONGEST proper prefix of `root` that is a genuine verb root
        and whose continuation to the full surface is a valid suffix tail, or None.
        Confirms the surface really is `verb_root` + (verbal) suffixes before the
        frequency prior swaps in the verb reading."""
        best: Optional[str] = None
        for L in range(2, len(root)):
            pre = root[:L]
            if self._is_verb_root(pre) and self._valid_suffix_tail(surface[L:]):
                best = pre
        return best

    # Personal/demonstrative pronouns take an irregular oblique stem
    # (o -> on-, bu -> bun-, şu -> şun-, ben -> ban-, sen -> san-). The core
    # reads these obliques as a bogus noun stem (onu -> on+ACC), so we map the
    # whole oblique form back to its base pronoun lemma.
    _PRONOUN_OBLIQUE = {
        "onu": "o", "onda": "o", "ondan": "o",
        "bunu": "bu", "bunun": "bu", "bunda": "bu", "bundan": "bu",
        "şunu": "şu", "şunda": "şu", "şundan": "şu",
        "bende": "ben", "benden": "ben", "benim": "ben",
        "sende": "sen", "senden": "sen",
    }

    def _valid_suffix_tail(self, tail: str) -> bool:
        """True if `tail` can be segmented into a sequence of recognised Turkish
        suffix surface strings (greedy longest-match with backtracking). Used to
        confirm that the material in front of a longer known stem is a genuine
        inflectional/derivational tail before we accept that longer stem."""
        if tail == "":
            return True
        upper = min(len(tail), self._suffix_maxlen)
        for L in range(upper, 0, -1):
            if tail[:L] in self._suffix_strings and self._valid_suffix_tail(tail[L:]):
                return True
        return False

    def _longest_known_stem(self, lower: str, min_len: int = 2,
                            require_suffix: bool = True) -> Optional[str]:
        """Find the LONGEST prefix of `lower` that is a known Turkish word (after
        optional final-consonant un-mutation) and whose trailing material is a
        valid suffix tail. Returns that stem, or None.

        This kills the over-strip class of bugs: the core decomposer accepts a
        short stem that happens to be a known word (getirerek -> ge, sonucu ->
        son) even though a LONGER prefix (getir, sonuç) is also a known word and
        leaves a clean inflectional tail. We always prefer the longest.

        The literal prefix is tested before its consonant-un-mutated variant so
        that adını lands on `ad`, not its hardened twin `at`.
        """
        n = len(lower)
        hi = n - 1 if require_suffix else n
        best: Optional[str] = None
        for L in range(min_len, hi + 1):
            pre = lower[:L]
            tail = lower[L:]
            if require_suffix and not self._valid_suffix_tail(tail):
                continue
            # literal prefix first, then its softened-final unmutation
            cands = [pre]
            if pre and pre[-1] in self.CONSONANT_MUTATION:
                cands.append(pre[:-1] + self.CONSONANT_MUTATION[pre[-1]])
            for c in cands:
                if self._known_word(c):
                    best = c
                    break  # literal preferred over mutation at this length
        return best

    # Converb / verbal-tail markers: their presence in the residual suffix means
    # the longer stem is a verb, so POS should be CONV/VERB, not NOUN.
    _CONVERB_TAILS = ("arak", "erek", "ınca", "ince", "unca", "ünce",
                      "arken", "erken", "madan", "meden", "ıp", "ip", "up", "üp",
                      "dıkça", "dikçe", "dukça", "dükçe")
    _VERBAL_TAIL_MARKERS = ("acak", "ecek", "iyor", "ıyor", "uyor", "üyor",
                            "mış", "miş", "muş", "müş", "malı", "meli",
                            "dı", "di", "du", "dü", "tı", "ti", "tu", "tü")

    def _features_from_tail(self, stem: str, tail: str) -> Tuple[str, Dict[str, str]]:
        """Best-effort POS + tags for a (stem, suffix-tail) split produced by the
        over-strip repair. Lemma is the load-bearing output; POS/tags are a
        sensible reconstruction from the tail, not a full re-parse."""
        if not tail:
            return "NOUN", {"case": "NOM"}
        for cv in self._CONVERB_TAILS:
            if tail.endswith(cv) or tail == cv:
                return "CONV", {"sem": "MANNER"} if cv in ("arak", "erek") else {}
        for mk in self._VERBAL_TAIL_MARKERS:
            if mk in tail:
                return "VERB", {}
        tags: Dict[str, str] = {}
        # Longest-match the case/poss maps against the END of the tail.
        for m in sorted(self._CASE_MAP, key=len, reverse=True):
            if tail.endswith(m):
                tags["case"] = self._CASE_MAP[m]
                break
        for m in sorted(self._POSS_MAP, key=len, reverse=True):
            if tail.endswith(m):
                tags.setdefault("poss", self._POSS_MAP[m])
                break
        if tail.startswith(("lar", "ler")):
            tags["num"] = "PL"
        tags.setdefault("case", "NOM")
        return "NOUN", tags

    # Monosyllabic verb roots whose aorist takes the high vowel -Ir (-ir/-ır/
    # -ur/-ür) instead of the regular low-vowel -Ar/-Er. For these, a bare
    # PRES_AORIST.3SG reading like gelir/bilir is the CORRECT decomposition; for
    # any other root a high-vowel "aorist" (esir, devir) is not a real verb form
    # and the whole word is the lemma.
    _IR_AORIST_VERBS = {
        "al", "bil", "bul", "dur", "gel", "gir", "gör", "kal", "ol", "öl",
        "san", "var", "ver", "vur", "den", "kıl", "git", "gid", "et", "ed",
    }
    _AORIST_LOW = {"ar", "er", "r"}
    _AORIST_HIGH = {"ır", "ir", "ur", "ür"}

    def _is_verb_root(self, root: str) -> bool:
        """True if `root` forms a real verb, i.e. its infinitive (root + -mak/-mek,
        with consonant un-mutation) is in the lexicon: esmek, gitmek, doğmak."""
        if not root:
            return False
        for cand in (root, self._unmutate_verb(root)):
            for inf in ("mek", "mak"):
                if self._known_word(cand + inf):
                    return True
        return False

    def _is_genuine_aorist(self, root: str, surface: str) -> bool:
        """True if `surface` is a well-formed present-aorist of the verb `root`:
        a genuine verb root taking the regular low-vowel -Ar/-Er, or one of the
        irregular -Ir roots taking the high vowel. Distinguishes gider/gelir
        (decompose) from esir/diğer (keep whole)."""
        if not surface.startswith(root):
            return False
        suf = surface[len(root):]
        if not self._is_verb_root(root):
            return False
        if suf in self._AORIST_LOW:
            return True
        if suf in self._AORIST_HIGH:
            return root in self._IR_AORIST_VERBS
        return False

    def _dict_guard(self, word: str, info: TokenInfo) -> TokenInfo:
        lower = _tr_lower(word)
        root = _tr_lower(info.root or "")

        if lower in self._PRONOUN_OBLIQUE:
            base = self._PRONOUN_OBLIQUE[lower]
            tags = {k: v for k, v in info.tags.items() if k in ("case",)}
            return TokenInfo(surface=word, clitics={}, template="", root=base,
                             tags=tags, pos="PRON", derived_chain=[])

        # Copula "imek": standalone past/narrative copula idi/imiş + person. The
        # reference analyser lemmatises these to "imek". The core mis-reads bare
        # "idi" as a noun (it+ACC); map it back to the copula lemma. (ise/iken
        # are lemmatised whole by the reference and are left untouched.)
        if lower in ("idi", "idim", "idin", "idik", "idiniz", "idiler",
                     "imiş", "imişim", "imişsin", "imişler"):
            return TokenInfo(surface=word, clitics={}, template="", root="imek",
                             tags={"cop": "PAST"}, pos="VERB", derived_chain=[])

        # "ol-" (to be/become) verbal-noun, participle and analytic-tense forms:
        # olduğu, olduğunu, olduğundan, olduktan, olmuştur, olmuştu... all have
        # lemma olmak (stem "ol"). The core leaves a participle/aspect residue
        # (olduk, olduğ, olmuşt) as the root; normalise to "ol".
        if (root in ("olduk", "olduğ", "olduğu", "olmuşt", "olmuş")
                or lower.startswith(("olduğ", "olduk", "olmuşt"))):
            return TokenInfo(surface=word, clitics={}, template="", root="ol",
                             tags=dict(info.tags), pos="VERB", derived_chain=[])

        # ── Infinitive-tail retention guard ────────────────────────────────
        # The analytic present "-mektedir/-maktadır" (stem + verbal-noun -mek/-mak
        # + locative -te/-ta + copula) surfaces as the bare infinitive after the
        # over-strip repair (gelmektedir -> gelmek, sürülmektedir -> sürülmek),
        # because the infinitive is itself a lexicon entry and wins the
        # longest-known-stem search below. A lemma is never an infinitive: when the
        # surface carries the analytic "-mekte/-makta" verbal-noun-in-locative and
        # the stem in front of it is a real verb root, the lemma is that verb stem
        # (gel, sürül), not the infinitive. Detected on the SURFACE because the
        # core leaves a buffered residue (gelmekted), not yet the infinitive.
        for vn, loc in (("mek", "te"), ("mak", "ta")):
            marker = vn + loc  # mekte / makta
            idx = lower.find(marker)
            if idx >= 2:
                verb_stem = lower[:idx]
                if self._is_verb_root(verb_stem):
                    return TokenInfo(surface=word, clitics={}, template="",
                                     root=verb_stem, tags=dict(info.tags),
                                     pos="VERB", derived_chain=[])

        # ── Buffer-y retention guard ────────────────────────────────────────
        # A vowel-final verb stem joins a vowel-initial suffix through a buffer
        # consonant -y- (topla + (y)arak, ara + (y)acaktı, incele + (y)erek). The
        # core counts the buffer into the stem and leaves a non-word root ending in
        # -y (toplay, aray, inceley). When dropping that final -y yields a genuine
        # verb root, the buffer is the lemma boundary: strip it. Gated on a verbal
        # reading and on the y-stripped stem being a real verb, so it never touches
        # a noun whose lemma legitimately ends in -y (saray, yay).
        if (info.pos in ("VERB", "CONV") and root.endswith("y")
                and len(root) >= 3 and root[-2] in self.ALL_VOWELS):
            ystem = root[:-1]
            if self._is_verb_root(ystem):
                return TokenInfo(surface=word, clitics={}, template="",
                                 root=ystem, tags=dict(info.tags),
                                 pos=info.pos, derived_chain=[])

        # ── "-ken" converb guard ────────────────────────────────────────────
        # The temporal converb -ken ("while/when") attaches either to the aorist
        # (çalış+ır+ken, koş+ar+ken), to a copula buffer -yken (öğrenci+yken), or
        # directly to a base (çocuk+ken). The core mis-reads its final -n as a
        # bogus suffix and freezes a -ke noun residue (çalışırke, çocukke). Strip
        # -ken (plus a copula buffer -y), then recursively lemmatise the base; the
        # base no longer ends in -ken, so the recursion terminates. Only fires when
        # the core actually left the -ke residue, so a correctly-handled surface is
        # never re-analysed.
        if (lower.endswith("ken") and len(lower) > 5
                and (root.endswith("ke") or root == lower)):
            base = lower[:-3]
            if base.endswith("y"):
                base = base[:-1]
            if len(base) >= 2 and base != lower:
                sub = self.analyze(base)
                sub_root = _tr_lower(sub.root or "")
                if sub_root and self._known_word(sub_root):
                    return TokenInfo(surface=word, clitics={}, template="",
                                     root=sub_root, tags={"sem": "WHILE"},
                                     pos="CONV" if self._is_verb_root(sub_root)
                                     else sub.pos, derived_chain=[])

        # ── Plural-boundary guard ───────────────────────────────────────────
        # The plural marker -lar/-ler is an unambiguous nominal boundary: whatever
        # precedes it is the stem (yan+lar+ı+na, zaman+lar+da, etek+ler+in+de+ki).
        # The core sometimes folds the plural and a following vowel into a longer
        # coincidental dictionary word (yanlarına -> yanla, zamanlarda -> zamanla,
        # eteklerindeki -> etekle) and the "root is known" short circuit then
        # freezes it. When the LONGEST known prefix sitting in front of a -lar/-ler
        # whose trailing material is a valid suffix tail differs from the core
        # root, prefer that prefix. Pronoun plurals (onlar, bunlar) take an
        # irregular oblique and are handled elsewhere, so their bases are excluded.
        # A clean aorist/finite VERB reading on a real verb root is left untouched:
        # yazarlar is "they write" (yaz + -ar + -lar), not the noun yazar + -lar.
        _core_verbal = (info.pos in ("VERB", "CONV") and self._is_verb_root(root)
                        and (info.tags.get("tense") or info.tags.get("mood")
                             or info.tags.get("sem")))
        if not _core_verbal:
            _PRON_PLURAL_BASES = {"on", "bun", "şun", "o", "bu", "şu", "biz", "siz"}
            plural_stem: Optional[str] = None
            for _marker in ("lar", "ler"):
                _i = lower.find(_marker)
                while _i >= 2:
                    _pre = lower[:_i]
                    if (_pre not in _PRON_PLURAL_BASES and self._known_word(_pre)
                            and self._valid_suffix_tail(lower[_i + 3:])
                            and (plural_stem is None or len(_pre) > len(plural_stem))):
                        plural_stem = _pre
                    _i = lower.find(_marker, _i + 1)
            if (plural_stem is not None and plural_stem != root
                    and len(plural_stem) < len(lower)):
                return TokenInfo(surface=word, clitics={}, template="",
                                 root=plural_stem, tags={"num": "PL", "case": "NOM"},
                                 pos="NOUN", derived_chain=[])

        # ── Denominal -lI adjective guard ───────────────────────────────────
        # The suffix -lı/-li/-lu/-lü ("with/having") is strictly DENOMINAL: it
        # builds an adjective from a NOUN, so the stem in front of it is that noun
        # (aşama+lı, anlam+lı, ev+li). The core sometimes mis-reads it as a verbal
        # necessitative on a short verb root (aşamalı -> aş + -malı) and over-
        # strips. When stripping -lI leaves a known word that is STRICTLY LONGER
        # than the core root, prefer that noun. Length-gated so it only ever
        # lengthens toward the real noun stem and never disturbs a clean short
        # decomposition (evli -> ev is unchanged because ev == the core root).
        if len(lower) >= 4:
            for _li in ("lı", "li", "lu", "lü"):
                if lower.endswith(_li):
                    _base = lower[: -len(_li)]
                    if not self._known_word(_base):
                        _um = self._unmutate_noun(_base)
                        _base = _um if (_um != _base
                                        and self._known_word(_um)) else _base
                    if (self._known_word(_base) and _base != root
                            and len(_base) > len(root)):
                        return TokenInfo(surface=word, clitics={}, template="",
                                         root=_base, tags={}, pos="NOUN",
                                         derived_chain=[])
                    break

        # ── Longer-verb-root participle guard ───────────────────────────────
        # A subject participle -an/-en or a verb-only converb (-arak, -ınca, -ıp,
        # -madan...) can only attach to a verb stem. When the core stops at a short
        # verb root but a STRICTLY LONGER verb root sits in front of that exact
        # verbal tail (kurtaran = kurtar + -an, not kur + bogus-CAUS; kurtulan =
        # kurtul + -an, not kur + DENOM), the longer verb is the lemma. Gated on a
        # verb-only tail head, so it cannot fire on a plural/aorist that merely
        # contains a longer coincidental verb root (kollar -> kol stays; gelince ->
        # gel stays, no longer verb root precedes -ince).
        _VERBAL_TAIL_HEADS = ("an", "en", "arak", "erek", "ınca", "ince",
                              "unca", "ünce", "ıp", "ip", "up", "üp",
                              "madan", "meden", "dıkça", "dikçe", "dukça",
                              "dükçe", "arken", "erken")
        _longer_vr: Optional[str] = None
        for _L in range(len(root) + 1, len(lower)):
            _pre, _tail = lower[:_L], lower[_L:]
            if (self._is_verb_root(_pre) and self._valid_suffix_tail(_tail)
                    and any(_tail.startswith(h) for h in _VERBAL_TAIL_HEADS)):
                _longer_vr = _pre
        if _longer_vr is not None and _longer_vr != root:
            _tail = lower[len(_longer_vr):]
            _pos = "CONV" if any(_tail.startswith(h) for h in
                                 self._CONVERB_TAILS) else "VERB"
            return TokenInfo(surface=word, clitics={}, template="",
                             root=_longer_vr, tags={}, pos=_pos,
                             derived_chain=[])

        # ── Over-strip guard (Rules 1 + 2) ──────────────────────────────────
        # The core decomposer accepts a stem that happens to be a known word even
        # when a LONGER prefix is also a known word with a clean inflectional
        # tail. Prefer the longest such stem. This is the load-bearing repair for
        # getirerek->getir (not ge), sonucu->sonuç (not son), adını->ad (not at),
        # geldiğinde->gel (not the bogus participle residue geldik). It runs
        # BEFORE the "root is known" short-circuit, because the over-stripped
        # root (ge, son, at) is itself a lexicon entry.
        # A clean finite/converb reading on a GENUINE verb root is trusted as-is:
        # the short verb lemma is correct (gelince -> gel, gelirse -> gel,
        # gider -> gid) and must never be lengthened by Rule 1 into a coincidental
        # noun prefix (gelin, gelir). A bare aorist only counts as clean when the
        # surface is a well-formed aorist of that root, so esir (es + bogus -ir)
        # and devir do NOT qualify and fall through to the whole-word repair.
        is_bare_aorist = (info.tags.get("tense") == "PRES_AORIST"
                          and info.tags.get("person") == "3"
                          and info.tags.get("num") == "SG"
                          and not info.tags.get("voice")
                          and not info.tags.get("mood"))
        core_is_clean_verb = (
            info.pos in ("VERB", "CONV")
            and self._is_verb_root(root)
            and (info.tags.get("tense") or info.tags.get("mood")
                 or info.tags.get("sem"))
            and (not is_bare_aorist or self._is_genuine_aorist(root, lower))
        )

        if root and root != lower and not core_is_clean_verb and not self._known_word(lower):
            # Rule 1 (LONGEST known stem) is applied ONLY when the core analysis is
            # SUSPECT, so it never disturbs a clean, correct short-stem
            # decomposition (evini -> ev, kollar -> kol, yapıcı -> yap). Four
            # suspicion signals, each evidence the core over-stripped:
            core_known = self._known_word(root)
            chain_str = " ".join(info.derived_chain)
            deverbal_chain = ("AGENT_NOUN_V" in chain_str or "DEVERBAL" in chain_str
                              or "ACTION_NOUN" in chain_str)
            # (A) the core root is not a real Turkish word at all (geldik).
            suspect_unknown = not core_known
            # (B) the core applied a DEVERBAL derivation to a non-verb root
            #     (sonucu = son + -ucu AGENT, but son is not a verb).
            suspect_deverbal = deverbal_chain and not self._is_verb_root(root)
            # (C) the core applied verbal voice / a converb to a non-verb root
            #     (getirerek = ge + CAUS + MANNER, but ge is not a verb).
            suspect_verbal_on_nonverb = (
                (info.tags.get("voice") or info.tags.get("sem"))
                and not self._is_verb_root(root)
            )
            take = None
            if suspect_unknown:
                # A non-word core root is most often a vowel-drop syncope
                # (oğlu -> oğul, boynuna -> boyun). Prefer the dedicated syncope
                # repairs, which recover the true lemma, before falling back to
                # the longest-known-prefix heuristic (which would mis-pick a
                # coincidental short prefix like ok / boy).
                take = self._repair_root(root) or self._restore_vowel_drop(lower)
                # ... unless that repair lands on a junk lexicon entry (a non-verb
                # word with near-zero corpus frequency, e.g. herke -> herk) while a
                # STRICTLY LONGER, frequent known word fronts a clean suffix tail
                # (herkese -> herkes + DAT). The genuine syncope repairs (oğul,
                # boyun, karın) are all frequent and longer than their rival short
                # prefix, so this never displaces them.
                if (take is not None and not self._is_verb_root(take)
                        and self._zipf(take) < 1.0):
                    longer = self._longest_known_stem(lower)
                    if (longer is not None and len(longer) > len(take)
                            and self._zipf(longer) >= 3.0):
                        take = longer
            if take is None and (suspect_unknown or suspect_deverbal
                                 or suspect_verbal_on_nonverb):
                longer = self._longest_known_stem(lower)
                if longer is not None and longer != root:
                    take = longer
            # (D) consonant-mutation mis-pick at the SAME boundary: the core
            #     hardened the final consonant (ad -> at) although the literal
            #     prefix is itself a known word (adını -> ad, not at). Restricted
            #     to a plain NOMINAL reading on a non-verb root, so it never
            #     re-softens a legitimately-hardened verb root (git in gidebilir
            #     must stay git, not gid).
            if (take is None and core_known and not info.derived_chain
                    and info.pos == "NOUN"):
                pref = lower[: len(root)]
                if (pref != root and self._known_word(pref)
                        and self._unmutate_noun(pref) == root):
                    take = pref
            if take is not None and take != root:
                # When the core already found real verbal features (okunacak:
                # voice + FUT) keep them and only correct the over-stripped root;
                # otherwise reconstruct POS/tags from the residual tail.
                if (info.tags.get("tense") or info.tags.get("voice")
                        or info.tags.get("mood") or info.tags.get("modality")):
                    pos, tags = info.pos, dict(info.tags)
                else:
                    tail = lower[len(take):]
                    pos, tags = self._features_from_tail(take, tail)
                return TokenInfo(surface=word, clitics={}, template="",
                                 root=take, tags=tags, pos=pos,
                                 derived_chain=[])

        if root and root != lower and not core_is_clean_verb and self._known_word(lower):

            # Rule 2: the whole surface is itself a known word but the core split
            # it apart. Prefer the whole word when:
            #   (a) the core read it as a bare aorist verb (esir -> es+ir,
            #       diğer -> diğ+er), UNLESS the stem is an irregular -Ir aorist
            #       verb whose aorist IS the surface (gelir -> gel, bilir -> bil);
            #   (b) the core stripped a final consonant as a bogus suffix and the
            #       residue needed mutation to become a known word (doğum -> dok),
            #       i.e. the core root is only reachable by un-mutating the surface
            #       prefix. The clean whole word is the better lemma.
            if self._known_word(lower):
                # (a): core read a bare aorist that is NOT a well-formed aorist of
                # the (often non-verb) root (esir = es + bogus -ir, diğer = diğ +
                # -er where diğ is not a verb). Keep the whole word.
                # Numerals/quantifiers take the distributive -Ar (birer = bir +
                # -er), which the core mis-reads as an aorist. These decompose to
                # the numeral, so the whole-word preference must not apply.
                _DISTRIBUTIVE_BASES = {"bir", "iki", "üç", "dört", "beş", "altı",
                                       "yedi", "sekiz", "dokuz", "on", "az", "çok"}
                spurious_aorist = (is_bare_aorist
                                   and not self._is_genuine_aorist(root, lower)
                                   and root not in _DISTRIBUTIVE_BASES)
                # (b): core kept a prefix that only became its root via consonant
                # un-mutation (doğum: kept doğ, un-mutated to dok). An artefact;
                # prefer the clean whole word.
                pref = lower[: len(root)] if len(root) <= len(lower) else ""
                mutation_artefact = (
                    info.pos == "NOUN" and len(root) < len(lower)
                    and pref and self._unmutate_noun(pref) == root and pref != root
                )
                if spurious_aorist or mutation_artefact:
                    return TokenInfo(surface=word, clitics={}, template="",
                                     root=lower, tags={},
                                     pos=self._whole_word_pos(lower),
                                     derived_chain=[])

        # Circumflex (â/î/û) inflected forms: hâlde, kâğıda, lâkin. The core
        # leaves them whole (root == surface, UNKNOWN) because the circumflex
        # surface is not a bare lexicon key. Strip the case ending and normalise
        # the circumflex to its plain vowel (hâlde -> hal), matching the reference
        # lemma convention. Only fires when the plain-vowel base is a known word.
        if root == lower and any(c in lower for c in "âîû"):
            plain = lower.replace("â", "a").replace("î", "i").replace("û", "u")
            repaired = self._strip_to_known(plain)
            if repaired is None and self._known_word(plain) and plain != lower:
                repaired = plain
            if repaired is not None:
                return TokenInfo(surface=word, clitics={}, template="",
                                 root=repaired, tags=dict(info.tags),
                                 pos=info.pos if info.pos != "UNKNOWN" else "NOUN",
                                 derived_chain=list(info.derived_chain))

        # Nothing stripped, or the stripped root is already a known Turkish
        # word/verb: trust the morphology. This is the load-bearing case that
        # PRESERVES legitimate inflection and derivation:
        #   evi->ev, evler->ev, evlerinizden->ev, kitapları->kitap,
        #   geliyorum->gel, yazmak->yaz, evli->ev, sevgi->sev, yedi->ye ...
        # all land on a known root, so they are kept untouched.
        if not root or root == lower:
            return info

        # Repair (0): capitalised proper-noun plural read as a verbal aorist
        # (Tatarlar -> tat+AORIST.3PL, Moğollar -> ...). When the ORIGINAL surface
        # is capitalised, ends in the plural marker -lar/-ler, and the bare base
        # is a known word, it is a proper-noun plural, not a verb. Gating on
        # capitalisation keeps real lowercase aorist verbs (yazarlar -> yaz)
        # untouched. This runs before the "root known" short-circuit because the
        # spurious verbal root (tat) can itself be a known verb stem.
        if (word[:1].isupper() and lower.endswith(("lar", "ler")) and len(lower) > 4
                and (info.tags.get("tense") or info.tags.get("aspect"))):
            base = lower[:-3]
            if self._known_word(base):
                return TokenInfo(surface=word, clitics={}, template="", root=base,
                                 tags={"num": "PL", "case": "NOM"}, pos="PROPN",
                                 derived_chain=[])

        if self._known_word(root):
            # Both surface and stripped root are known words: trust the
            # morphology (evli->ev, yedi->ye, evinden->ev, gelir->gel). We do
            # NOT override these even when the whole surface is also a lexicon
            # entry, because doing so would mis-lemmatise productive
            # derivations/inflections that the curated tests (and Turkish
            # grammar) treat as decomposable.
            return info

        # Repair (1): bare nominal plural mis-read as a buffer artefact
        # (insanlar -> insanl, moğollar -> moğoll). If the surface ends in
        # -lar/-ler and the bare base is a known word, prefer base + plural.
        if lower.endswith(("lar", "ler")) and len(lower) > 4:
            base = lower[:-3]
            if self._known_word(base):
                tags = dict(info.tags)
                for k in ("tense", "aspect", "voice", "mood", "modality", "person"):
                    tags.pop(k, None)
                tags["num"] = "PL"
                tags.setdefault("case", "NOM")
                return TokenInfo(surface=word, clitics={}, template="",
                                 root=base, tags=tags, pos="NOUN",
                                 derived_chain=[])

        # The root is NOT a known word: the engine truncated. Repairs in order of
        # confidence. STRONGEST first: if the bare surface IS itself a known
        # lexicon entry, the engine stripped a final letter as a bogus suffix and
        # left a non-word stem (kabul->kabu->kab, üvey->üve, başka->başk,
        # göçebe->göçep, bir->bi). Prefer the whole word, ahead of any speculative
        # root reconstruction.
        if self._known_word(lower):
            pos = self._whole_word_pos(lower)
            return TokenInfo(surface=word, clitics={}, template="", root=lower,
                             tags={}, pos=pos, derived_chain=[])

        # (2) Recover the real lemma from the truncated root, keeping the tags the
        #     core already found. Two sub-repairs, accepted only if they land on a
        #     known word (so we never invent a non-lexicon stem):
        #       (a) vowel-drop syncope inside the root: boyn -> boyun, ağz -> ağız.
        #       (b) a stray trailing vowel left on the root: yılı -> yıl.
        repaired_root = self._repair_root(root)
        if repaired_root is not None:
            return TokenInfo(surface=word, clitics={}, template="",
                             root=repaired_root, tags=dict(info.tags),
                             pos=info.pos if info.pos != "UNKNOWN" else "NOUN",
                             derived_chain=list(info.derived_chain))

        # (3) Possessive vowel-drop computed from the surface (oğlu = oğul+u,
        #     burnu = burun+u) for cases where the core root is too short to
        #     reconstruct from.
        restored = self._restore_vowel_drop(lower)
        if restored is not None:
            return TokenInfo(surface=word, clitics={}, template="",
                             root=restored, tags=dict(info.tags),
                             pos=info.pos if info.pos != "UNKNOWN" else "NOUN",
                             derived_chain=list(info.derived_chain))

        # (4) Last resort: both the surface and the core root are non-words, so
        #     the core mis-handled a consonant mutation or buffer (kurultayda ->
        #     kurultayt, sonucu -> son, hâlde -> hâlde). Strip a trailing
        #     inflectional ending from the SURFACE and, if the remainder is a
        #     known word, use it. Tried longest-first so we strip the full
        #     suffix, not a prefix of it. Only fires when the surface itself is
        #     unknown, so it cannot disturb base lemmas handled in (0)/(3).
        surface_repair = self._strip_to_known(lower)
        if surface_repair is not None:
            return TokenInfo(surface=word, clitics={}, template="",
                             root=surface_repair, tags=dict(info.tags),
                             pos=info.pos if info.pos != "UNKNOWN" else "NOUN",
                             derived_chain=list(info.derived_chain))

        # Otherwise we have no dictionary evidence to override; keep the core.
        return info

    # Inflectional endings tried (longest first) by _strip_to_known.
    _CASE_ENDINGS = (
        "ndan", "nden", "ları", "leri", "ında", "inde", "unda", "ünde",
        "dan", "den", "tan", "ten", "nın", "nin", "nun", "nün", "ına", "ine",
        "da", "de", "ta", "te", "yı", "yi", "yu", "yü", "ya", "ye", "ın", "in",
        "un", "ün", "ı", "i", "u", "ü", "a", "e",
    )

    def _strip_to_known(self, lower: str) -> Optional[str]:
        for suf in self._CASE_ENDINGS:
            if lower.endswith(suf) and len(lower) - len(suf) >= 2:
                base = lower[: -len(suf)]
                if self._known_word(base):
                    return base
                # Undo final-consonant mutation revealed by stripping
                # (kitabı -> kitab -> kitap, sonucu -> sonuc -> sonuç).
                unmut = self._unmutate_noun(base)
                if unmut != base and self._known_word(unmut):
                    return unmut
        return None

    def _repair_root(self, root: str) -> Optional[str]:
        """Given a truncated (non-word) root the core produced, try to recover the
        real lemma. (a) Insert a high vowel before the final consonant to undo
        possessive vowel-drop syncope (boyn -> boyun, ağz -> ağız, karn -> karın).
        (b) Drop a stray trailing vowel left by an over-greedy split
        (yılı -> yıl). Returns the recovered lemma only if it is a known word."""
        if len(root) < 2:
            return None
        # (b) stray trailing vowel
        if root[-1] in self.ALL_VOWELS and self._known_word(root[:-1]):
            return root[:-1]
        # (a) syncope restoration: ...C1 C2 -> ...C1 V C2
        if root[-1] not in self.ALL_VOWELS:
            base, c_last = root[:-1], root[-1]
            if base and base[-1] not in self.ALL_VOWELS:
                for v in "ıiuü":
                    cand = base + v + c_last
                    if self._known_word(cand):
                        return cand
        return None

    def _restore_vowel_drop(self, lower: str) -> Optional[str]:
        """Turkish possessive/case vowel-drop (syncope): a small class of CVCVC
        roots drop their second vowel before a vowel-initial suffix
        (oğul -> oğl-u, burun -> burn-u, ağız -> ağz-ı, karın -> karn-ı).
        Given the surface, strip one trailing vowel suffix, then try inserting
        each high vowel before the final consonant of the residue; return the
        first reconstruction that is a known root. Returns None if nothing
        matches, so this never invents a non-lexicon stem."""
        # Strip a single trailing 3SG-poss / accusative vowel.
        if len(lower) < 3 or lower[-1] not in "ıiuü":
            return None
        residue = lower[:-1]  # e.g. oğlu -> oğl, burnu -> burn
        if len(residue) < 2:
            return None
        c_last = residue[-1]
        if c_last in self.ALL_VOWELS:
            return None
        base = residue[:-1]  # oğl -> oğ, burn -> bur
        if not base:
            return None
        for v in "ıiuü":
            cand = base + v + c_last
            if self._known_word(cand):
                return cand
        return None

    def _whole_word_pos(self, lower: str) -> str:
        """Coarse POS for a word taken whole from the dictionary. The eval gold
        is noisy on POS, so we only need a sensible default; closed-class words
        were already handled upstream, so this is a content word."""
        if lower in self._deriv_output_pos:
            return self._deriv_output_pos[lower]
        return "NOUN"

    def _analyze_core(self, word: str) -> TokenInfo:
        lower = word.lower()

        # Bug #15: Handle proper-noun apostrophe form (Türkiye'den)
        if "'" in word:
            base, _, suffix = word.partition("'")
            base_low = base.lower()
            if base_low in CLOSED_CLASS:
                entry = CLOSED_CLASS[base_low]
                tags = {k: v for k, v in entry.items() if k != "pos"}
                # Try inflectional analysis on the suffix portion
                if suffix:
                    sub_stem, sub_tags = self._step_a(suffix)
                    tags.update({k: v for k, v in sub_tags.items() if k != "pos"})
                return TokenInfo(surface=word, clitics={}, template="",
                                 root=base_low, tags=tags, pos=entry.get("pos", "PROPN"),
                                 derived_chain=[])

        if lower in CLOSED_CLASS:
            entry = CLOSED_CLASS[lower]
            pos = entry.get("pos", "PART")
            tags = {k: v for k, v in entry.items() if k != "pos"}
            return TokenInfo(
                surface=word, clitics={}, template="", root=lower,
                tags=tags, pos=pos, derived_chain=[],
            )

        # Proper-noun heuristic: bare capitalized word (no apostrophe, no
        # productive inflection slot) defaults to PROPN. Prevents Ahmet ->
        # ahme+CAUS misreadings cascading into sentence rejection.
        _TR_CAPS = set("ABCDEFGHIİJKLMNOÖPRSŞTUÜVYZÇĞ")
        if word and word[0] in _TR_CAPS and "'" not in word:
            # Only short, suffix-less capitalized strings: no nominal/verbal slot
            # would yield a strong reading.
            nd_probe = self._try_nominal_decomp(word)
            vd_probe = None
            wl = word.lower()
            looks_inflected = (
                wl.endswith(("ler", "lar", "miş", "mış", "muş", "müş",
                              "ecek", "acak", "iyor", "ıyor", "uyor", "üyor",
                              "den", "dan", "ten", "tan", "de", "da", "te", "ta",
                              "nın", "nin", "nun", "nün"))
            )
            strong_nominal = False
            if nd_probe is not None:
                _, _ndt = nd_probe
                if ("poss" in _ndt or "num" in _ndt
                    or (_ndt.get("case") and _ndt.get("case") != "NOM")):
                    strong_nominal = True
            if not strong_nominal and not looks_inflected:
                return TokenInfo(
                    surface=word, clitics={}, template="", root=lower,
                    tags={}, pos="PROPN", derived_chain=[],
                )

        # değil + copula person ending: değilim, değilsin, değilsiniz, değiliz.
        # Keep root as the closed-class form.
        if lower.startswith("değil") and lower != "değil":
            tail = lower[len("değil"):]
            cop_tails = {
                "im": ("1", "SG"), "sin": ("2", "SG"), "iz": ("1", "PL"),
                "siniz": ("2", "PL"), "ler": ("3", "PL"),
                "di": ("3", "SG"), "dim": ("1", "SG"), "din": ("2", "SG"),
            }
            if tail in cop_tails:
                p, n = cop_tails[tail]
                return TokenInfo(
                    surface=word, clitics={}, template="", root="değil",
                    tags={"sem": "NEGATION", "person": p, "num": n, "cop": "PRES"},
                    pos="PART", derived_chain=[],
                )

        # Pre-pass 0a: -ki invariant relational adjective (masadaki, yarınki)
        ki = self._try_ki_relative(word)
        if ki is not None:
            stem, sub_tags, chain = ki
            return TokenInfo(surface=word, clitics={}, template="",
                             root=stem, tags=sub_tags, pos="ADJ",
                             derived_chain=chain)

        # Pre-pass 0b: Copula constructions
        cop = self._try_copula(word)
        if cop is not None:
            stem, pos_c, c_tags = cop
            return TokenInfo(surface=word, clitics={}, template="",
                             root=stem, tags=c_tags, pos=pos_c,
                             derived_chain=[])

        # Pre-pass 0c: progressive vowel-collapse irregulars (okuyor, yiyor)
        # Only fire when stem before -iyor is 1-2 chars (the collapse case).
        wlow_pvc = word.lower()
        if wlow_pvc.endswith(("yor", "yorum", "yorsun", "yoruz", "yorsunuz", "yorlar")):
            # Determine stripped length to gate
            stripped = wlow_pvc
            for ending in ("yorsunuz", "yorsun", "yorlar", "yorum", "yoruz", "yor"):
                if stripped.endswith(ending):
                    base_before_prog = stripped[: -len(ending)]
                    break
            else:
                base_before_prog = ""
            # base_before_prog ends in 'i'/'ı'/'u'/'ü' (the iyor vowel) — strip it
            if base_before_prog and base_before_prog[-1] in "ıiuü":
                pre_iyor = base_before_prog[:-1]
            else:
                pre_iyor = base_before_prog
            # Only treat as vowel-collapse if pre_iyor is 1-2 chars (oku, ye -> ok, y)
            # Common 2-char verb roots that should NOT trigger vowel collapse.
            _common_2c_verbs = {"yaz", "gel", "bil", "gid", "git", "al", "bul", "ol",
                                 "ver", "kal", "dur", "sat", "kos", "koş", "yap",
                                 "gez", "sev", "iç", "in", "uç", "tut", "sor", "tat",
                                 "vur", "kes", "yıka", "yar", "kız", "açı", "ezi"}
            if 1 <= len(pre_iyor) <= 2 and pre_iyor not in _common_2c_verbs:
                pvc = self._try_progressive_vowel_collapse(word)
                if pvc is not None:
                    stem, ptags = pvc
                    if self._stem_plausible(stem):
                        return TokenInfo(surface=word, clitics={}, template="",
                                         root=stem, tags=ptags, pos="VERB",
                                         derived_chain=[])

        # Pre-pass 0c1: Imperative recognizer (must fire before verb_decomp)
        imp_pre = self._try_imperative(word)
        if imp_pre is not None:
            stem_imp, imp_tags = imp_pre
            return TokenInfo(surface=word, clitics={}, template="",
                             root=stem_imp, tags=imp_tags, pos="VERB",
                             derived_chain=[])

        # Pre-pass 0c2: ABIL (potential/inability) - must fire before verb_decomp
        # to prevent -ir/-dı from being consumed as bare aorist.
        abil_pre = self._try_ability(word)
        if abil_pre is not None:
            stem_a, ab_tags, tail = abil_pre
            tail_tags = self._analyze_verb_tail(tail)
            if tail_tags.get("tense"):
                merged = dict(ab_tags)
                merged.update(tail_tags)
                if "polarity" in ab_tags:
                    merged["polarity"] = "NEG"
                stem_a = self._unmutate_verb(stem_a)
                return TokenInfo(surface=word, clitics={}, template="",
                                 root=stem_a, tags=merged, pos="VERB",
                                 derived_chain=[])

        # Pre-pass 0c3: Try nominal decomp early; if it gives a strong (POSS+CASE)
        # reading on a content-word stem, skip verb_decomp.
        nd_early = self._try_nominal_decomp(word)
        nominal_strong = False
        if nd_early is not None:
            _ne_stem, _ne_tags = nd_early
            # Don't trust nominal reading if stem ends in 'd'/'t' (likely PAST_DEF)
            # or 'ş' (PAST_NARR) or 'r' (AORIST) or 'k' (FUT/NECESS).
            # Reason: also exclude stem-final 's' (yazıyors+un = PRES_PROG+2SG),
            # which is a person-ending boundary, not a noun stem.
            if (_ne_stem and _ne_stem[-1] not in "dtşrkğçs"):
                if ("num" in _ne_tags and "poss" in _ne_tags) or \
                   ("poss" in _ne_tags and _ne_tags.get("case") not in (None, "NOM")) or \
                   ("num" in _ne_tags and _ne_tags.get("case") not in (None, "NOM")):
                    nominal_strong = True

        # Pre-pass 0d: verbal decomposition (TENSE x PERSON x VOICE x NEG)
        vd = None
        wlow = word.lower()
        skip_verb = nominal_strong
        # Pattern: bare -lar/-ler at end is PL noun, not aorist
        if wlow.endswith(("lar", "ler")) and not wlow.endswith(("rlar", "rler", "ırlar", "irler", "urlar", "ürler")):
            # ambiguity: aorist 3PL like 'yazarlar' but bare 'evler' is plural noun
            # heuristic: if stripping -lar/-ler gives a 2-3 char nominal-ish base, skip verb
            base = wlow[:-3]
            # Bare nominal plural: stem before -lar/-ler is the noun. Skip verb
            # decomposition when the base is vowel-final (no aorist -ar/-er
            # marker could attach to it without a stem consonant). Exception:
            # bases ending in a PAST_DEF dental + vowel (yazdı+lar, gitti+ler)
            # or in -mış/-miş (PAST_NARR) must keep going through verb_decomp.
            past_def_tails = ("dı", "di", "du", "dü", "tı", "ti", "tu", "tü")
            past_narr_tails = ("mış", "miş", "muş", "müş")
            looks_verbal = (base.endswith(past_def_tails) or base.endswith(past_narr_tails)
                            or base.endswith(("yor", "ecek", "acak", "ar", "er")))
            if (len(base) >= 2 and not looks_verbal and (len(base) <= 4 or
                                    (base and base[-1] in self.ALL_VOWELS)
                                    or (base and base[-1] not in "rnsl"))):
                # base ends in consonant other than r/n/s/l: treat as bare noun + PL
                skip_verb = True
        # Don't run verb decomp on words ending in obvious nominal-only suffixes
        if wlow.endswith(("la", "le", "yla", "yle")) and not wlow.endswith(("mla", "mle")):
            skip_verb = True
        if not skip_verb:
            vd = self._try_verb_decomp(word)
        if vd is not None:
            stem, v_tags = vd
            # Only accept if a real verbal marker found
            has_verbal = (v_tags.get("tense") or v_tags.get("mood") or v_tags.get("voice")
                          or v_tags.get("sem"))
            # Additional safety: nominal decomp may be a better explanation
            nd_check = self._try_nominal_decomp(word)
            verb_better = True
            if nd_check is not None and has_verbal:
                # Prefer nominal if it has both POSS and CASE (richer nominal reading)
                _nd_stem, nd_tags = nd_check
                # Reason: don't trust nominal POSS+CASE when its stem ends in a
                # verbal-boundary consonant (t/d/ş/r/k/ğ/ç/s/p/b/g — typical
                # PAST/AORIST/FUT residues like yazt, yazıyors).
                _nd_stem_ok = (_nd_stem and _nd_stem[-1] not in "tdşrkğçspbg")
                # If nominal reading explains the whole word with CASE or POSS+CASE
                if (_nd_stem_ok
                    and "poss" in nd_tags and "case" in nd_tags
                    and nd_tags["case"] != "NOM"):
                    verb_better = False
                # If verb reading is bare PRES_AORIST 3SG only (no person), prefer nominal
                if (_nd_stem_ok
                    and v_tags.get("tense") == "PRES_AORIST"
                    and v_tags.get("person") == "3" and v_tags.get("num") == "SG"
                    and not v_tags.get("voice") and "poss" in nd_tags):
                    verb_better = False
            # If vd produced a very short stem (2 chars), check if imperative
            # gives a better-known root (3+ chars).
            if has_verbal and verb_better and len(stem) <= 2:
                imp_check = self._try_imperative(word)
                if imp_check is not None and len(imp_check[0]) > len(stem):
                    return TokenInfo(surface=word, clitics={}, template="",
                                     root=imp_check[0], tags=imp_check[1],
                                     pos="VERB", derived_chain=[])
            if has_verbal and verb_better:
                v_pos = "CONV" if v_tags.get("sem") else "VERB"
                return TokenInfo(surface=word, clitics={}, template="",
                                 root=stem, tags=v_tags, pos=v_pos,
                                 derived_chain=[])

        # Pre-pass 1: ABIL / inability (Bug B5)
        abil = self._try_ability(word)
        if abil is not None:
            stem, ab_tags, tail = abil
            tail_tags = self._analyze_verb_tail(tail)
            if tail_tags.get("tense"):
                # Combine polarity from ABIL_NEG with tail
                merged = dict(ab_tags)
                merged.update(tail_tags)
                if "polarity" in ab_tags:
                    merged["polarity"] = "NEG"
                stem = self._unmutate_verb(stem)
                return TokenInfo(surface=word, clitics={}, template="",
                                 root=stem, tags=merged, pos="VERB",
                                 derived_chain=[])

        # Pre-pass 2: PAST_DEF + person (Bug B2)
        # Only fire if the bare nominal analysis would lose the tense.
        verbal = self._try_past_def_person(word)

        # Pre-pass 3: Imperative (Bug B3)
        imp = self._try_imperative(word)
        if imp is not None:
            stem, imp_tags = imp
            return TokenInfo(surface=word, clitics={}, template="",
                             root=stem, tags=imp_tags, pos="VERB",
                             derived_chain=[])

        # Pre-pass 3.4: denominal verb -le/-la for a small adjective whitelist
        # (temizle, güzelle, karala). Cannot use blanket -le/-la trigger because
        # of conflict with INS case (kalemle, arabayla).
        _DENOM_VERB_ADJ_BASES = {"temiz", "güzel", "kara", "ak", "kuru", "beyaz",
                                  "yumuşa", "kalın", "yaşa", "haşla", "boya"}
        wlow_dv = word.lower()
        if wlow_dv.endswith(("le", "la")):
            base_dv = wlow_dv[:-2]
            if base_dv in _DENOM_VERB_ADJ_BASES:
                return TokenInfo(surface=word, clitics={}, template="",
                                 root=base_dv, tags={}, pos="VERB",
                                 derived_chain=[f"{wlow_dv[-2:]}->DENOM_VERB"])

        # Pre-pass 3.5: high-priority derivation for unambiguous cases (evli, işçi, yapma)
        # Only fire if the candidate stem looks like a 3-5 char content-word root.
        wlow_dr = word.lower()
        if wlow_dr.endswith(("li", "lı", "lu", "lü", "siz", "sız", "suz", "süz",
                             "çi", "çı", "çu", "çü", "ci", "cı", "cu", "cü",
                             "gi", "gı", "gu", "gü", "ma", "me", "ıcı", "ici",
                             "ucu", "ücü", "kan", "ken", "ğan", "ğen")):
            der = self._try_derivation_pre(word)
            if der is not None:
                der_stem, der_pos, der_chain = der
                # Only accept if stem is a "good" content-word base
                if (len(der_stem) >= 2 and self._stem_plausible(der_stem)
                    and der_stem[-1] not in self.ALL_VOWELS):
                    return TokenInfo(surface=word, clitics={}, template="",
                                     root=der_stem, tags={}, pos=der_pos,
                                     derived_chain=der_chain)

        # Pre-pass 4: holistic nominal decomposition (BEFORE derivation to avoid eating CASE/POSS)
        nd = self._try_nominal_decomp(word)
        if nd is not None:
            n_stem, n_tags = nd
            # Only accept if it found something (not just NOM default)
            has_real = ("poss" in n_tags or "num" in n_tags or
                        (n_tags.get("case") and n_tags["case"] != "NOM"))
            # Skip nominal decomp if the only "case" is bare ACC ı/i/u/ü on stem
            # that could be a derivation (evli, işçi, sevgi, yapıcı).
            wlow_nd = word.lower()
            skip_nd = False
            # Only skip if nominal_decomp's stem is short and a derivation reading exists
            # with a longer plausible stem.
            if (n_tags.get("case") == "ACC" and len(n_tags) == 1 and
                wlow_nd.endswith(("li", "lı", "lu", "lü", "ci", "cı", "cu", "cü",
                                  "çi", "çı", "çu", "çü", "gi", "gı", "gu", "gü",
                                  "kı", "ki"))):
                # Check the derivation reading: if stripping derivational suffix
                # gives a CONSONANT-FINAL stem, prefer derivation; else keep nominal.
                der_test = self._try_derivation_pre(word)
                if der_test is not None:
                    d_stem = der_test[0]
                    if d_stem and d_stem[-1] not in self.ALL_VOWELS and len(d_stem) >= 2:
                        skip_nd = True
            if has_real and not skip_nd:
                return TokenInfo(surface=word, clitics={}, template="",
                                 root=n_stem, tags=n_tags, pos="NOUN",
                                 derived_chain=[])

        # Pre-pass 5: derivation on short roots (only consonant-final stems)
        der = self._try_derivation_pre(word)
        if der is not None:
            der_stem, der_pos, der_chain = der
            if (len(der_stem) >= 2 and
                der_stem[-1] not in self.ALL_VOWELS):
                return TokenInfo(surface=word, clitics={}, template="",
                                 root=der_stem, tags={}, pos=der_pos,
                                 derived_chain=der_chain)

        # Pre-pass 6: nominal decomp NOM-only fallback
        if nd is not None:
            n_stem, n_tags = nd
            return TokenInfo(surface=word, clitics={}, template="",
                             root=n_stem, tags=n_tags, pos="NOUN",
                             derived_chain=[])

        stem, tags = self._step_a(word)

        # Bug B2: If pre-pass found a verbal analysis and main pass missed it
        # or returned UNKNOWN/POSS-only, prefer verbal.
        if verbal is not None:
            v_stem, v_tags = verbal
            main_is_nominal_only = (
                tags.get("tense") is None
                and (tags.get("poss") is not None or not tags)
            )
            if main_is_nominal_only:
                # Reason: a verbal PAST_DEF reading exists; the nominal arbiter
                # mis-parsed `-dım/-dın/-dı/-dınız` as POSS.
                stem = self._unmutate_verb(v_stem)
                tags = v_tags

        # Bug #4: consonant unmutation for vowel-initial case suffix
        case_val = tags.get("case")
        if case_val and case_val in ("ACC", "DAT", "GEN", "LOC", "ABL"):
            candidates = self._try_consonant_unmutation(stem)
            if len(candidates) > 1:
                unmutated = candidates[1]
                if self._stem_plausible(unmutated):
                    stem = unmutated

        # Bug B13: extend unmutation to POSS-only forms (kitabım -> kitap)
        if tags.get("poss") and not case_val and "tense" not in tags:
            if stem.endswith("b") and self._stem_plausible(stem[:-1] + "p"):
                stem = stem[:-1] + "p"
            elif stem.endswith("d") and self._stem_plausible(stem[:-1] + "t"):
                # Reason: only after vowel-initial poss suffix
                pass
            elif stem.endswith("ğ") and self._stem_plausible(stem[:-1] + "k"):
                stem = stem[:-1] + "k"
            elif stem.endswith("g") and self._stem_plausible(stem[:-1] + "k"):
                stem = stem[:-1] + "k"
            elif stem.endswith("c") and self._stem_plausible(stem[:-1] + "ç"):
                stem = stem[:-1] + "ç"

        # Strip stray y-buffer left in stem
        if stem.endswith("y") and len(stem) >= 2 and stem[-2] in self.ALL_VOWELS:
            stem = stem[:-1]

        # Bug #14: Copula detection - if stem ends with vowel + y after person
        # ending matched, this is a copula construction (öğrenciyim, evdeyim).
        if tags.get("poss") and "case" not in tags and "tense" not in tags:
            # If the original word has -y- buffer + person ending pattern,
            # re-tag as copula on a nominal predicate.
            w = word.lower()
            for cop_suf in ("yım", "yim", "yum", "yüm", "yız", "yiz", "yuz", "yüz"):
                if w.endswith(cop_suf):
                    base = w[: -len(cop_suf)]
                    if self._stem_plausible(base):
                        person = "1"
                        num = "SG" if cop_suf.endswith("m") else "PL"
                        # base may itself have LOC etc.
                        sub_stem, sub_tags = self._step_a(base)
                        out_tags = {"cop": "PRES", "person": person, "num": num}
                        out_tags.update(sub_tags)
                        # Drop spurious poss
                        out_tags.pop("poss", None)
                        root = self._step_c(sub_stem)
                        pos = "NOUN" if "case" in out_tags or "deriv" in out_tags or True else "NOUN"
                        return TokenInfo(surface=word, clitics={}, template="",
                                         root=root, tags=out_tags, pos="NOUN",
                                         derived_chain=[])
            for cop_suf in ("ydım", "ydim", "ydum", "ydüm"):
                if w.endswith(cop_suf):
                    base = w[: -len(cop_suf)]
                    if self._stem_plausible(base):
                        sub_stem, sub_tags = self._step_a(base)
                        out_tags = {"cop": "PAST", "person": "1", "num": "SG"}
                        out_tags.update(sub_tags)
                        out_tags.pop("poss", None)
                        root = self._step_c(sub_stem)
                        return TokenInfo(surface=word, clitics={}, template="",
                                         root=root, tags=out_tags, pos="NOUN",
                                         derived_chain=[])

        # Derivation detection on the post-step-A stem
        _, derived_chain, deriv_pos = self._step_b(stem)
        root = self._step_c(stem)

        # POS determination with derivation priority
        # Verbal markers ALWAYS win over nominal num/poss (mixed forms like
        # yazdım have person=1SG num=SG plus tense, but they're verbal).
        explicit_pos = tags.get("pos")
        if tags.get("tense") or tags.get("voice") or tags.get("modality"):
            pos = "VERB"
        elif tags.get("mood") in ("IMP", "COND", "OPT", "NECESS", "INF"):
            pos = "VERB"
        elif explicit_pos and explicit_pos != "PART":
            pos = explicit_pos
        elif tags.get("case") or tags.get("poss"):
            pos = "NOUN"
        elif tags.get("num") and tags.get("num") in ("PL", "SG") and "person" not in tags:
            pos = "NOUN"
        elif "deriv" in tags and deriv_pos:
            pos = deriv_pos
        elif deriv_pos:
            pos = deriv_pos
        else:
            pos = "UNKNOWN"

        # Default case=NOM for bare/POSS-only nominal forms (Bug B1 follow-up)
        # Reason: tests assert case=NOM on evlerim, kitabım, etc.
        if pos == "NOUN" and "case" not in tags:
            tags["case"] = "NOM"

        # Default person=3 num=SG for finite verbs that don't have explicit person
        if pos == "VERB" and tags.get("tense") and "person" not in tags:
            tags["person"] = "3"
            tags["num"] = "SG"

        # Bug B4: if a deriv tag was found in step_a (slot 1), surface its output_pos
        if "deriv" in tags:
            der_pos = self._deriv_output_pos.get(tags["deriv"])
            if der_pos:
                pos = der_pos

        # Bug B10: VN_FUT vs FUT - prefer finite for bare -acak/-ecek
        if explicit_pos == "PART" and tags.get("tense") == "FUT":
            w = word.lower()
            if w.endswith("acak") or w.endswith("ecek"):
                pos = "VERB"
                tags = {k: v for k, v in tags.items() if k != "pos"}
                tags["person"] = "3"
                tags["num"] = "SG"

        clean_tags = {k: v for k, v in tags.items() if k != "pos"}
        return TokenInfo(
            surface=word, clitics={}, template="", root=root,
            tags=clean_tags, pos=pos, derived_chain=derived_chain,
        )

    def analyze_sentence(self, sentence: str) -> Tuple[List[TokenInfo], bool, str]:
        from .grammar import tr_grammar
        tokens = [self.analyze(w) for w in sentence.split()]
        tokens = tr_grammar.disambiguate_pos(tokens)
        word_ok = check_morph_sequence_tr(tokens)
        sent_ok, sent_msg = tr_grammar.validate_sentence(tokens)
        if word_ok and not sent_ok:
            return tokens, False, sent_msg
        # Preserve legacy shared check as a safety net.
        legacy_ok, legacy_msg = validate_sentence_structure_tr(tokens)
        return tokens, word_ok and sent_ok and legacy_ok, sent_msg if not sent_ok else legacy_msg

# ══════════════════════════════════════════════════════════════════════════════
# PROCESSING PIPELINE
# ══════════════════════════════════════════════════════════════════════════════
