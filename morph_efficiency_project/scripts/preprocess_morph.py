"""
preprocess_morph.py
-------------------
Three-step grammar engine for morphology-aware preprocessing.
Implements the pipeline defined in plan.md §4.0–4.6.

For each word in the corpus:
  Step A — Clitic stripping + surface tagging (inflectional)
  Step B — Template / derivational pattern detection
  Step C — Root / stem identification

Outputs per language L in {en, ar, tr}:
  data/processed/L/morph/train_tokens.npy      — token ID sequence (int32)
  data/processed/L/morph/train_feature_ids.npy — feature bundle ID per token (int32)
  data/processed/L/morph/val_tokens.npy
  data/processed/L/morph/val_feature_ids.npy
  data/processed/L/morph/test_tokens.npy
  data/processed/L/morph/test_feature_ids.npy
  tokenizers/L_morph/vocab.json                — morpheme → token ID
  tokenizers/L_morph/feature_bundles.json      — bundle string → bundle ID
  logs/evaluation/L_morph_token_stats.json
  logs/evaluation/L_morph_foreign_rate.json

Usage:
  python scripts/preprocess_morph.py --language en
  python scripts/preprocess_morph.py --language ar
  python scripts/preprocess_morph.py --language tr
  python scripts/preprocess_morph.py --language all
"""

import argparse
import json
import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

CHUNK_LINES = 100_000  # lines between progress logs

# ── Shared data structure ─────────────────────────────────────────────────────

@dataclass
class TokenInfo:
    surface:  str
    clitics:  Dict[str, List[str]]   # {"pre": [...], "enc": [...]}
    template: str                     # morphological template or FOREIGN/PROPER/UNKNOWN
    root:     str                     # root/stem after template extraction
    tags:     Dict[str, str]          # grammatical tag bundle
    pos:      str                     # NOM/VERB/ADJ/ADV/PART/FOREIGN/PROPER/UNKNOWN
    derived_chain: List[str] = field(default_factory=list)  # derivational affixes

    def feature_bundle_str(self) -> str:
        """Serialize tags to canonical bundle string."""
        if not self.tags:
            return "no_features"
        parts = [f"pos={self.pos}"] + [f"{k}={v}" for k, v in sorted(self.tags.items())]
        return "|".join(parts)

    def token_str(self) -> str:
        """Serialize to the structured token representation."""
        return f"{self.root}.{self.pos}"


# ── Vocabulary / feature bundle registry ─────────────────────────────────────

class MorphVocab:
    """Accumulates morpheme tokens and feature bundles, assigns integer IDs."""

    SPECIAL = ["<pad>", "<unk>", "<s>", "</s>"]

    def __init__(self):
        self.token2id: Dict[str, int] = {}
        self.bundle2id: Dict[str, int] = {"no_features": 0}
        # Pre-populate specials
        for t in self.SPECIAL:
            self._get_token_id(t)

    def _get_token_id(self, token: str) -> int:
        if token not in self.token2id:
            self.token2id[token] = len(self.token2id)
        return self.token2id[token]

    def _get_bundle_id(self, bundle: str) -> int:
        if bundle not in self.bundle2id:
            self.bundle2id[bundle] = len(self.bundle2id)
        return self.bundle2id[bundle]

    def encode(self, token_info: TokenInfo) -> tuple[int, int]:
        tok_id     = self._get_token_id(token_info.token_str())
        bundle_id  = self._get_bundle_id(token_info.feature_bundle_str())
        return tok_id, bundle_id

    def save(self, tok_dir: str):
        os.makedirs(tok_dir, exist_ok=True)
        with open(os.path.join(tok_dir, "vocab.json"), "w", encoding="utf-8") as f:
            json.dump(self.token2id, f, ensure_ascii=False, indent=2)
        with open(os.path.join(tok_dir, "feature_bundles.json"), "w", encoding="utf-8") as f:
            json.dump(self.bundle2id, f, ensure_ascii=False, indent=2)
        log.info(f"Vocab saved: {len(self.token2id)} tokens, "
                 f"{len(self.bundle2id)} feature bundles → {tok_dir}")


# ── Sequence validator ────────────────────────────────────────────────────────

def check_morph_sequence_en(tokens: List[TokenInfo]) -> bool:
    NOUN_ALLOWED  = {"num", "poss"}
    VERB_ALLOWED  = {"tense", "aspect", "person", "voice"}
    ADJ_ALLOWED   = {"degree"}
    ADV_ALLOWED   = {"degree"}
    for t in tokens:
        keys = set(t.tags.keys())
        if t.pos == "NOUN" and not keys.issubset(NOUN_ALLOWED):
            return False
        if t.pos == "VERB":
            if not keys.issubset(VERB_ALLOWED):
                return False
            if t.tags.get("aspect") == "PERF" and t.tags.get("tense") not in ("PAST", "PRES", None):
                return False
        if t.pos == "ADJ" and not keys.issubset(ADJ_ALLOWED):
            return False
        if t.pos == "ADV" and not keys.issubset(ADV_ALLOWED):
            return False
    return True


def check_morph_sequence_ar(tokens: List[TokenInfo]) -> bool:
    for t in tokens:
        keys = set(t.tags.keys())
        if t.pos == "VERB":
            if "tense" not in keys or "person" not in keys:
                return False
            if t.tags.get("tense") == "IMP":
                if t.tags.get("person") != "2" or t.tags.get("voice") != "ACT":
                    return False
            if t.tags.get("voice") == "PASS" and t.tags.get("tense") == "IMP":
                return False
            if t.tags.get("mood") == "JUS" and t.tags.get("tense") != "PRES":
                return False
        if t.pos == "NOM":
            if keys & {"tense", "person", "mood"}:
                return False
    return True


def check_morph_sequence_tr(tokens: List[TokenInfo]) -> bool:
    NOMINAL_ORDER  = ["DERIV", "NUM", "POSS", "CASE"]
    VERBAL_ORDER   = ["DERIV", "VOICE", "NEG", "TENSE", "MOOD", "PERSON_NUM"]
    for t in tokens:
        if t.pos in ("NOUN", "ADJ"):
            slots = [s for s in NOMINAL_ORDER if s in t.tags]
            if slots != sorted(slots, key=lambda s: NOMINAL_ORDER.index(s)):
                return False
        if t.pos == "VERB":
            if t.tags.get("polarity") == "NEG":
                neg_idx  = VERBAL_ORDER.index("NEG")
                tns_idx  = VERBAL_ORDER.index("TENSE")
                if neg_idx > tns_idx:
                    return False
    return True


# ══════════════════════════════════════════════════════════════════════════════
# ENGLISH GRAMMAR ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class EnglishEngine:
    """
    Three-step grammar engine for English (plan.md §4.6).
    Requires: spaCy en_core_web_trf (or en_core_web_sm as fallback)
    """

    def __init__(self, config_dir: str = "morph_efficiency_project/configs"):
        import spacy

        # Load spaCy model
        for model_name in ("en_core_web_trf", "en_core_web_lg", "en_core_web_sm"):
            try:
                self.nlp = spacy.load(model_name, disable=["ner", "parser"])
                log.info(f"[EN] Loaded spaCy model: {model_name}")
                break
            except OSError:
                continue
        else:
            raise OSError(
                "No spaCy English model found. Run:\n"
                "  python -m spacy download en_core_web_sm"
            )

        # Load config files
        with open(os.path.join(config_dir, "en_irregulars.json"), encoding="utf-8") as f:
            self.irregulars = json.load(f)
        with open(os.path.join(config_dir, "en_derivations.json"), encoding="utf-8") as f:
            self.derivations = json.load(f)
        with open(os.path.join(config_dir, "en_compounds.json"), encoding="utf-8") as f:
            raw_compounds = json.load(f)
            self.compounds = {c["compound"]: c for c in raw_compounds}
        with open(os.path.join(config_dir, "en_phrasal_verbs.json"), encoding="utf-8") as f:
            raw_pv = json.load(f)
            # Index by (verb, particle) and by token string
            self.phrasal_verbs = {pv["token"]: pv for pv in raw_pv}
            self.pv_by_verb: Dict[str, List[dict]] = defaultdict(list)
            for pv in raw_pv:
                self.pv_by_verb[pv["verb"]].append(pv)

        # Build suffix lookup for derivations
        self._build_deriv_index()

    def _build_deriv_index(self):
        """Index derivational suffixes by their surface variants for fast lookup."""
        self.suffix_index: Dict[str, dict] = {}
        self.prefix_index: Dict[str, dict] = {}
        for entry in self.derivations:
            for variant in entry["surface_variants"]:
                v = variant.lstrip("-")
                if entry["type"] == "SUFFIX":
                    self.suffix_index[v] = entry
                else:
                    self.prefix_index[v] = entry

    # ── Step A: Inflectional stripping + surface tagging ─────────────────────

    def _step_a(self, surface: str, spacy_token) -> tuple[str, dict, str]:
        """
        Returns (base_form, tags, pos).
        Checks irregular lookup first, then uses spaCy lemma + morph.
        """
        lower = surface.lower()

        # Irregular lookup (highest priority)
        if lower in self.irregulars:
            entry = self.irregulars[lower]
            base  = entry["base"]
            pos   = entry["pos"]
            # Parse tag string into dict
            tags  = dict(kv.split("=") for kv in entry["tag"].split("|") if "=" in kv)
            return base, tags, pos

        # spaCy lemma + morphological features
        base = spacy_token.lemma_ if spacy_token else surface
        pos  = spacy_token.pos_   if spacy_token else "X"
        tags: Dict[str, str] = {}

        if spacy_token and spacy_token.morph:
            morph = spacy_token.morph.to_dict()
            # Map spaCy morph keys to our tag schema
            if "Number" in morph:
                tags["num"] = "PL" if morph["Number"] == "Plur" else "SG"
            if "Tense" in morph:
                tags["tense"] = "PAST" if morph["Tense"] == "Past" else "PRES"
            if "Aspect" in morph:
                asp = morph["Aspect"]
                tags["aspect"] = {"Prog": "PROG", "Perf": "PERF"}.get(asp, asp)
            if "Degree" in morph:
                deg = morph["Degree"]
                tags["degree"] = {"Cmp": "COMP", "Sup": "SUPER", "Pos": "POS"}.get(deg, deg)
            if "Person" in morph and morph.get("Number") == "Sing":
                tags["person"] = "3SG"
            if "Voice" in morph:
                tags["voice"] = "PASS" if morph["Voice"] == "Pass" else "ACT"
            if "Poss" in morph:
                tags["poss"] = "YES"

        # Normalize POS to our schema
        pos_map = {
            "NOUN": "NOUN", "PROPN": "PROPER", "VERB": "VERB",
            "AUX": "VERB",  "ADJ": "ADJ",      "ADV": "ADV",
            "DET": "DET",   "PRON": "PRON",    "ADP": "PREP",
            "CCONJ": "CONJ","SCONJ": "CONJ",   "PART": "PART",
            "NUM": "NUM",   "INTJ": "INTJ",    "X": "UNKNOWN",
            "PUNCT": "PUNCT", "SYM": "SYM",    "SPACE": "SPACE",
        }
        pos = pos_map.get(pos, "UNKNOWN")
        return base, tags, pos

    # ── Step B: Derivational pattern detection ────────────────────────────────

    def _step_b(self, base: str, pos: str) -> tuple[str, List[str], str]:
        """
        Returns (stem, derived_chain, template_label).
        Checks: phrasal verb → compound → prefix → suffix.
        """
        lower = base.lower()

        # Compound check
        if lower in self.compounds:
            c = self.compounds[lower]
            constituents = "+".join(
                f"{p['stem']}.{p['pos']}" for p in c["constituents"]
            )
            return lower, [f"COMPOUND:{constituents}"], "COMPOUND"

        # Prefix check
        for prefix, entry in self.prefix_index.items():
            if lower.startswith(prefix) and len(lower) > len(prefix) + 2:
                stem = lower[len(prefix):]
                return stem, [f"PREFIX:{prefix}:{entry['derives']}"], entry["derives"]

        # Suffix check (longest match wins)
        for suffix in sorted(self.suffix_index.keys(), key=len, reverse=True):
            if lower.endswith(suffix) and len(lower) > len(suffix) + 2:
                stem = lower[: -len(suffix)]
                entry = self.suffix_index[suffix]
                return stem, [f"SUFFIX:{suffix}:{entry['derives']}"], entry["derives"]

        return lower, [], pos

    # ── Step C: Stem identification ───────────────────────────────────────────

    def _step_c(self, stem: str, pos: str) -> str:
        """Returns the canonical stem (lowercased, stripped)."""
        return stem.lower().strip()

    # ── Phrasal verb detection (sentence-level) ───────────────────────────────

    def _detect_phrasal_verbs(self, spacy_doc) -> Dict[int, str]:
        """
        Returns {verb_token_index: phrasal_verb_token_string} for detected PVs.
        Looks ahead up to 3 tokens for a matching particle.
        """
        pv_map: Dict[int, str] = {}
        tokens = list(spacy_doc)
        for i, tok in enumerate(tokens):
            if tok.pos_ not in ("VERB", "AUX"):
                continue
            verb = tok.lemma_.lower()
            if verb not in self.pv_by_verb:
                continue
            candidates = self.pv_by_verb[verb]
            for j in range(i + 1, min(i + 4, len(tokens))):
                particle = tokens[j].text.lower()
                for pv in candidates:
                    if pv["particle"] == particle:
                        pv_map[i] = pv["token"]
                        break
                if i in pv_map:
                    break
        return pv_map

    # ── Public: analyze a sentence ────────────────────────────────────────────

    def analyze(self, sentence: str) -> List[TokenInfo]:
        doc = self.nlp(sentence)
        pv_map = self._detect_phrasal_verbs(doc)
        results: List[TokenInfo] = []
        skip_next: set = set()

        for i, spacy_tok in enumerate(doc):
            if i in skip_next:
                continue
            surface = spacy_tok.text

            # Phrasal verb — merge verb + particle into single token
            if i in pv_map:
                pv_token = pv_map[i]
                pv_entry = self.phrasal_verbs[pv_token]
                # Find and skip the particle token
                for j in range(i + 1, min(i + 4, len(doc))):
                    if doc[j].text.lower() == pv_entry["particle"]:
                        skip_next.add(j)
                        break
                base, tags, pos = self._step_a(spacy_tok.text, spacy_tok)
                tags["tense"] = tags.get("tense", "PRES")
                ti = TokenInfo(
                    surface=surface,
                    clitics={"pre": [], "enc": []},
                    template="PHRASAL_VERB",
                    root=pv_token,
                    tags=tags,
                    pos="VERB",
                    derived_chain=["PHRASAL_VERB"],
                )
                results.append(ti)
                continue

            # Skip punctuation, spaces
            if spacy_tok.pos_ in ("PUNCT", "SPACE", "SYM"):
                continue

            base, tags, pos = self._step_a(surface, spacy_tok)
            stem, derived_chain, template = self._step_b(base, pos)
            stem = self._step_c(stem, pos)

            ti = TokenInfo(
                surface=surface,
                clitics={"pre": [], "enc": []},
                template=template,
                root=stem,
                tags=tags,
                pos=pos,
                derived_chain=derived_chain,
            )
            results.append(ti)

        return results


# ══════════════════════════════════════════════════════════════════════════════
# ARABIC GRAMMAR ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class ArabicEngine:
    """
    Three-step grammar engine for Arabic (plan.md §4.4).
    Requires: camel_tools (primary), Farasa (fallback).
    """

    # Proclitics stripped in order (conjunction → preposition → definite article)
    PROCLITICS = [
        ("وَ",  "CONJ",  "wa"),
        ("فَ",  "CONJ",  "fa"),
        ("بِ",  "PREP",  "bi"),
        ("لِ",  "PREP",  "li"),
        ("كَ",  "PREP",  "ka"),
        ("الْ", "DEF",   "al"),
        ("ال",  "DEF",   "al"),
    ]

    # Enclitics (pronoun suffixes)
    ENCLITICS = [
        ("هُم",  {"person": "3", "num": "PL",  "gender": "M"}),
        ("هُمَا", {"person": "3", "num": "DU",  "gender": "M"}),
        ("هُنَّ", {"person": "3", "num": "PL",  "gender": "F"}),
        ("هُ",   {"person": "3", "num": "SG",  "gender": "M"}),
        ("هَا",  {"person": "3", "num": "SG",  "gender": "F"}),
        ("كُم",  {"person": "2", "num": "PL",  "gender": "M"}),
        ("كُمَا", {"person": "2", "num": "DU",  "gender": "M"}),
        ("كِ",   {"person": "2", "num": "SG",  "gender": "F"}),
        ("كَ",   {"person": "2", "num": "SG",  "gender": "M"}),
        ("نَا",  {"person": "1", "num": "PL",  "gender": "M"}),
        ("ي",   {"person": "1", "num": "SG",  "gender": "M"}),
    ]

    def __init__(self, config_dir: str = "morph_efficiency_project/configs"):
        # Load root and template inventories
        with open(os.path.join(config_dir, "ar_roots.json"), encoding="utf-8") as f:
            raw = json.load(f)
            # ar_roots.json structure: {"roots": [...], ...} or flat list
            if isinstance(raw, dict):
                self.roots = set(raw.get("roots", []))
            else:
                self.roots = set(raw)

        with open(os.path.join(config_dir, "ar_templates.json"), encoding="utf-8") as f:
            raw = json.load(f)
            if isinstance(raw, list):
                self.templates = raw
            else:
                self.templates = raw.get("templates", [])

        # Build template pattern index for fast matching
        self._build_template_index()

        # Try to load camel_tools analyzer
        self.analyzer = None
        try:
            from camel_tools.morphology.database import MorphologyDB
            from camel_tools.morphology.analyzer import Analyzer
            db = MorphologyDB.builtin_db()
            self.analyzer = Analyzer(db)
            log.info("[AR] camel_tools analyzer loaded.")
        except Exception as e:
            log.warning(f"[AR] camel_tools not available ({e}). Using rule-based fallback.")

    def _build_template_index(self):
        """Index templates by their وزن string for lookup."""
        self.template_map: Dict[str, dict] = {}
        for t in self.templates:
            wazn = t.get("wazn") or t.get("template") or t.get("pattern", "")
            if wazn:
                self.template_map[wazn] = t

    # ── Step A: Clitic stripping + surface tagging ────────────────────────────

    def _strip_clitics(self, word: str) -> tuple[str, List[str], List[str]]:
        """Returns (base, proclitics_stripped, enclitics_stripped)."""
        pre = []
        enc = []

        # Strip proclitics (left to right)
        for surface, ctype, logical in self.PROCLITICS:
            if word.startswith(surface):
                word = word[len(surface):]
                pre.append(logical)
                break  # one proclitic at a time per pass; loop handles chaining

        # Strip enclitics (right to left, longest match first)
        for surface, _ in sorted(self.ENCLITICS, key=lambda x: len(x[0]), reverse=True):
            if word.endswith(surface) and len(word) > len(surface) + 1:
                word = word[: -len(surface)]
                enc.append(surface)
                break

        return word, pre, enc

    def _camel_analyze(self, word: str) -> Optional[dict]:
        """Returns best camel_tools analysis or None."""
        if not self.analyzer:
            return None
        try:
            analyses = self.analyzer.analyze(word)
            if analyses:
                return analyses[0]  # highest-ranked
        except Exception:
            pass
        return None

    def _tags_from_camel(self, analysis: dict) -> tuple[str, dict, str]:
        """Extract (template, tags, pos) from a camel_tools analysis dict."""
        pos_map = {
            "noun": "NOM", "verb": "VERB", "adj": "ADJ",
            "part": "PART", "adv": "ADV", "pron": "PRON",
            "prep": "PREP", "conj": "CONJ",
        }
        raw_pos = analysis.get("pos", "noun").lower()
        pos = pos_map.get(raw_pos, "NOM")

        tags: Dict[str, str] = {}
        if "num" in analysis:
            tags["num"] = {"s": "SG", "d": "DU", "p": "PL"}.get(analysis["num"], "SG")
        if "gen" in analysis:
            tags["gender"] = {"m": "M", "f": "F"}.get(analysis["gen"], "M")
        if "cas" in analysis:
            tags["case"] = {"n": "NOM", "a": "ACC", "g": "GEN"}.get(analysis["cas"], "NOM")
        if "asp" in analysis:
            tags["tense"] = {"p": "PAST", "i": "PRES", "c": "IMP"}.get(analysis["asp"], "PRES")
        if "per" in analysis:
            tags["person"] = {"1": "1", "2": "2", "3": "3"}.get(str(analysis["per"]), "3")
        if "vox" in analysis:
            tags["voice"] = "ACT" if analysis["vox"] == "a" else "PASS"
        if "mod" in analysis:
            tags["mood"] = {"i": "IND", "s": "SUBJ", "j": "JUS"}.get(analysis["mod"], "IND")

        template = analysis.get("pattern", analysis.get("form", "UNKNOWN"))
        return template, tags, pos

    # ── Step B: Template detection ────────────────────────────────────────────

    def _step_b(self, base: str, camel_analysis: Optional[dict]) -> tuple[str, dict, str]:
        if camel_analysis:
            return self._tags_from_camel(camel_analysis)
        # Fallback: return base with minimal tags
        return "UNKNOWN", {}, "NOM"

    # ── Step C: Root extraction ───────────────────────────────────────────────

    def _step_c(self, base: str, camel_analysis: Optional[dict]) -> str:
        if camel_analysis:
            root = camel_analysis.get("root", "")
            if root:
                return root
        # Fallback: return base consonants (strip vowel diacritics)
        diacritics = "َُِّْٰٕٓٔ"
        return "".join(c for c in base if c not in diacritics)

    # ── Public: analyze a sentence ────────────────────────────────────────────

    def analyze(self, sentence: str) -> List[TokenInfo]:
        results: List[TokenInfo] = []
        words = sentence.split()
        for word in words:
            if not word.strip():
                continue
            base, pre, enc = self._strip_clitics(word)
            analysis = self._camel_analyze(base)
            template, tags, pos = self._step_b(base, analysis)
            root = self._step_c(base, analysis)

            # Validate root against lexicon
            if root and root not in self.roots:
                template = template if template != "UNKNOWN" else "UNVERIFIED_ROOT"

            ti = TokenInfo(
                surface=word,
                clitics={"pre": pre, "enc": enc},
                template=template,
                root=root or base,
                tags=tags,
                pos=pos,
            )
            results.append(ti)
        return results


# ══════════════════════════════════════════════════════════════════════════════
# TURKISH GRAMMAR ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class TurkishEngine:
    """
    Three-step grammar engine for Turkish (plan.md §4.5).
    Requires: zeyrek (pip install zeyrek)
    """

    # Canonical slot order for validation
    NOMINAL_SLOT_ORDER  = ["DERIV", "NUM", "POSS", "CASE"]
    VERBAL_SLOT_ORDER   = ["DERIV", "VOICE", "NEG", "TENSE", "MOOD", "PERSON_NUM"]

    def __init__(self, config_dir: str = "morph_efficiency_project/configs"):
        try:
            import zeyrek
            self.analyzer = zeyrek.MorphAnalyzer()
            log.info("[TR] Zeyrek analyzer loaded.")
        except ImportError:
            raise ImportError("pip install zeyrek")

        with open(os.path.join(config_dir, "tr_suffixes.json"), encoding="utf-8") as f:
            self.suffixes = json.load(f)
        with open(os.path.join(config_dir, "tr_derivations.json"), encoding="utf-8") as f:
            self.derivations = json.load(f)

        # Build suffix slot lookup: logical_name → entry
        self.suffix_map: Dict[str, dict] = {s["logical"]: s for s in self.suffixes}
        # Build derivation lookup: suffix string → entry
        self.deriv_map: Dict[str, dict] = {}
        for d in self.derivations:
            for v in d.get("surface_variants", []):
                self.deriv_map[v.lstrip("-")] = d

    # ── Vowel harmony normalization ───────────────────────────────────────────

    BACK_VOWELS  = set("aıouAIOU")
    FRONT_VOWELS = set("eiöüEİÖÜ")
    ROUND_VOWELS = set("ouöüOUÖÜ")

    def _last_vowel(self, stem: str) -> Optional[str]:
        for ch in reversed(stem):
            if ch in self.BACK_VOWELS | self.FRONT_VOWELS:
                return ch
        return None

    def _harmony_type(self, stem: str) -> str:
        v = self._last_vowel(stem)
        if v is None:
            return "back"
        return "front" if v in self.FRONT_VOWELS else "back"

    # ── Zeyrek result parsing ─────────────────────────────────────────────────

    def _parse_zeyrek(self, analysis) -> tuple[str, dict, str, List[str]]:
        """
        Parse a Zeyrek analysis result into (stem, tags, pos, derived_chain).
        Zeyrek returns MorphemeState objects with .morpheme.name attributes.
        """
        tags: Dict[str, str] = {}
        derived_chain: List[str] = []
        stem = ""
        pos  = "NOUN"

        try:
            # analysis is a SingleAnalysis object
            # .stem gives the root stem string
            stem = analysis.stem if hasattr(analysis, "stem") else str(analysis)

            # .morphemes gives list of (surface, morpheme) pairs
            morphemes = analysis.morphemes if hasattr(analysis, "morphemes") else []

            for surface, morpheme in morphemes:
                name = morpheme.name if hasattr(morpheme, "name") else str(morpheme)

                # POS from first morpheme
                if name in ("Noun", "Verb", "Adj", "Adv", "Postp", "Conj", "Pron"):
                    pos_map = {
                        "Noun": "NOUN", "Verb": "VERB", "Adj": "ADJ",
                        "Adv": "ADV",  "Postp": "POSTP", "Conj": "CONJ",
                        "Pron": "PRON",
                    }
                    pos = pos_map.get(name, "NOUN")

                # Inflectional tags
                elif name == "Plural":
                    tags["num"] = "PL"
                elif name in ("Pnon", "P1sg", "P2sg", "P3sg", "P1pl", "P2pl", "P3pl"):
                    poss_map = {
                        "Pnon": "NONE", "P1sg": "1SG", "P2sg": "2SG",
                        "P3sg": "3SG",  "P1pl": "1PL", "P2pl": "2PL", "P3pl": "3PL",
                    }
                    tags["poss"] = poss_map[name]
                elif name in ("Nom", "Acc", "Dat", "Loc", "Abl", "Gen", "Ins"):
                    tags["case"] = name.upper()
                elif name == "Past":
                    tags["tense"] = "PAST_DEF"
                elif name == "Narr":
                    tags["tense"] = "PAST_NARR"
                elif name == "Prog1":
                    tags["tense"] = "PRES_PROG"
                elif name == "Aor":
                    tags["tense"] = "PRES_AORIST"
                elif name == "Fut":
                    tags["tense"] = "FUT"
                elif name == "Neg":
                    tags["polarity"] = "NEG"
                elif name in ("Caus", "Pass", "Recip", "Reflex"):
                    voice_map = {"Caus": "CAUS", "Pass": "PASS",
                                 "Recip": "RECIP", "Reflex": "REFL"}
                    tags["voice"] = voice_map[name]
                elif name == "Cond":
                    tags["mood"] = "COND"
                elif name == "Opt":
                    tags["mood"] = "OPT"
                elif name == "Imp":
                    tags["mood"] = "IMP"
                elif name == "Neces":
                    tags["mood"] = "NECESS"
                elif name in ("A1sg", "A2sg", "A3sg", "A1pl", "A2pl", "A3pl"):
                    person_map = {
                        "A1sg": "1SG", "A2sg": "2SG", "A3sg": "3SG",
                        "A1pl": "1PL", "A2pl": "2PL", "A3pl": "3PL",
                    }
                    tags["person_num"] = person_map[name]

                # Derivational morphemes
                elif name not in ("Punc", "Unknown"):
                    derived_chain.append(f"DERIV:{name}:{surface}")

        except Exception as e:
            log.debug(f"[TR] Zeyrek parse error: {e}")

        return stem, tags, pos, derived_chain

    # ── Public: analyze a sentence ────────────────────────────────────────────

    def analyze(self, sentence: str) -> List[TokenInfo]:
        results: List[TokenInfo] = []
        words = sentence.split()

        for word in words:
            word = word.strip()
            if not word:
                continue

            # Zeyrek analysis
            try:
                analyses = self.analyzer.analyze(word)
                if analyses and analyses[0]:
                    # analyses[0] is a list of SingleAnalysis for the word
                    best = analyses[0][0] if analyses[0] else None
                else:
                    best = None
            except Exception:
                best = None

            if best is None:
                ti = TokenInfo(
                    surface=word,
                    clitics={"pre": [], "enc": []},
                    template="UNKNOWN",
                    root=word,
                    tags={},
                    pos="UNKNOWN",
                )
                results.append(ti)
                continue

            stem, tags, pos, derived_chain = self._parse_zeyrek(best)

            ti = TokenInfo(
                surface=word,
                clitics={"pre": [], "enc": []},
                template="SUFFIX_CHAIN",
                root=stem or word,
                tags=tags,
                pos=pos,
                derived_chain=derived_chain,
            )
            results.append(ti)

        return results


# ══════════════════════════════════════════════════════════════════════════════
# CORPUS PROCESSING PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

ENGINES = {"en": EnglishEngine, "ar": ArabicEngine, "tr": TurkishEngine}
VALIDATORS = {
    "en": check_morph_sequence_en,
    "ar": check_morph_sequence_ar,
    "tr": check_morph_sequence_tr,
}


def get_paths(lang: str) -> dict:
    return {
        "train_raw":  os.path.join("data", "raw", lang, "train.txt"),
        "val_raw":    os.path.join("data", "raw", lang, "val.txt"),
        "test_raw":   os.path.join("data", "raw", lang, "test.txt"),
        "proc_dir":   os.path.join("data", "processed", lang, "morph"),
        "tok_dir":    os.path.join("tokenizers", f"{lang}_morph"),
        "log_stats":  os.path.join("logs", "evaluation", f"{lang}_morph_token_stats.json"),
        "log_foreign":os.path.join("logs", "evaluation", f"{lang}_morph_foreign_rate.json"),
    }


def process_split(lang: str, split: str, raw_path: str, proc_dir: str,
                  engine, vocab: MorphVocab, validator) -> dict:
    """
    Processes one split: analyzes each sentence, encodes tokens + feature bundles,
    saves .npy arrays. Returns stats.
    """
    tok_path     = os.path.join(proc_dir, f"{split}_tokens.npy")
    feat_path    = os.path.join(proc_dir, f"{split}_feature_ids.npy")

    if os.path.exists(tok_path) and os.path.exists(feat_path):
        log.info(f"[{lang}/{split}] Already processed — skipping.")
        arr = np.load(tok_path, mmap_mode="r")
        return {"split": split, "num_tokens": len(arr), "skipped": True}

    log.info(f"[{lang}/{split}] Processing {raw_path} ...")

    all_tok_ids:  List[int] = []
    all_feat_ids: List[int] = []

    line_count    = 0
    token_count   = 0
    foreign_count = 0
    proper_count  = 0
    unknown_count = 0
    invalid_seq   = 0

    BOS_ID = vocab.token2id.get("<s>",  2)
    EOS_ID = vocab.token2id.get("</s>", 3)

    with open(raw_path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue

            try:
                token_infos = engine.analyze(line)
            except Exception as e:
                log.debug(f"[{lang}/{split}] Analysis error on line {line_count}: {e}")
                token_infos = []

            if not token_infos:
                continue

            # Sequence validation
            if not validator(token_infos):
                invalid_seq += 1

            # BOS
            all_tok_ids.append(BOS_ID)
            all_feat_ids.append(0)  # no_features

            for ti in token_infos:
                tok_id, feat_id = vocab.encode(ti)
                all_tok_ids.append(tok_id)
                all_feat_ids.append(feat_id)
                token_count += 1

                # Track foreign/proper/unknown rates
                if ti.pos == "FOREIGN" or ti.template == "FOREIGN":
                    foreign_count += 1
                elif ti.pos == "PROPER":
                    proper_count += 1
                elif ti.pos == "UNKNOWN" or ti.template == "UNKNOWN":
                    unknown_count += 1

            # EOS
            all_tok_ids.append(EOS_ID)
            all_feat_ids.append(0)

            line_count += 1
            if line_count % CHUNK_LINES == 0:
                log.info(f"  [{lang}/{split}] {line_count:,} lines | "
                         f"{token_count:,} tokens | "
                         f"foreign={foreign_count} proper={proper_count} "
                         f"unknown={unknown_count}")

    # Save arrays
    os.makedirs(proc_dir, exist_ok=True)
    np.save(tok_path,  np.array(all_tok_ids,  dtype=np.int32))
    np.save(feat_path, np.array(all_feat_ids, dtype=np.int32))

    stats = {
        "split":         split,
        "num_lines":     line_count,
        "num_tokens":    token_count,
        "foreign_count": foreign_count,
        "proper_count":  proper_count,
        "unknown_count": unknown_count,
        "invalid_sequences": invalid_seq,
        "foreign_rate":  round(foreign_count / max(token_count, 1), 4),
        "proper_rate":   round(proper_count  / max(token_count, 1), 4),
        "unknown_rate":  round(unknown_count / max(token_count, 1), 4),
    }
    log.info(f"[{lang}/{split}] Done. {token_count:,} tokens → {tok_path}")
    return stats


def process_language(lang: str):
    paths = get_paths(lang)

    if not os.path.exists(paths["train_raw"]):
        raise FileNotFoundError(
            f"Raw corpus not found: {paths['train_raw']}\n"
            f"Run download_data.py --language {lang} first."
        )

    log.info(f"=== [{lang}] Morph preprocessing ===")
    os.makedirs(paths["proc_dir"], exist_ok=True)
    os.makedirs(paths["tok_dir"],  exist_ok=True)
    os.makedirs(os.path.dirname(paths["log_stats"]), exist_ok=True)

    # Initialize engine and shared vocab
    engine    = ENGINES[lang]()
    vocab     = MorphVocab()
    validator = VALIDATORS[lang]

    all_stats = {}
    for split, raw_path in [
        ("train", paths["train_raw"]),
        ("val",   paths["val_raw"]),
        ("test",  paths["test_raw"]),
    ]:
        stats = process_split(lang, split, raw_path, paths["proc_dir"],
                              engine, vocab, validator)
        all_stats[split] = stats

    # Save vocab after all splits (so IDs are consistent across splits)
    vocab.save(paths["tok_dir"])

    # Write logs
    with open(paths["log_stats"], "w", encoding="utf-8") as f:
        json.dump({
            "language": lang,
            "vocab_size": len(vocab.token2id),
            "num_feature_bundles": len(vocab.bundle2id),
            "splits": all_stats,
        }, f, ensure_ascii=False, indent=2)

    foreign_stats = {
        "language": lang,
        "splits": {
            s: {
                "foreign_rate": all_stats[s].get("foreign_rate", 0),
                "proper_rate":  all_stats[s].get("proper_rate",  0),
                "unknown_rate": all_stats[s].get("unknown_rate", 0),
            }
            for s in all_stats if not all_stats[s].get("skipped")
        }
    }
    with open(paths["log_foreign"], "w", encoding="utf-8") as f:
        json.dump(foreign_stats, f, ensure_ascii=False, indent=2)

    log.info(f"=== [{lang}] Morph preprocessing complete. "
             f"Vocab size: {len(vocab.token2id):,} tokens, "
             f"{len(vocab.bundle2id):,} feature bundles ===\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Morphology-aware preprocessing.")
    parser.add_argument(
        "--language",
        choices=["en", "ar", "tr", "all"],
        required=True,
    )
    args = parser.parse_args()
    langs = ["en", "ar", "tr"] if args.language == "all" else [args.language]
    for lang in langs:
        process_language(lang)


if __name__ == "__main__":
    main()
