"""
compute_bundle_space.py
-----------------------
Compute three bundle-space indicators per language:

    |B|_possible   theoretical cross-product of slot values per POS
                   (purely combinatorial, before any constraint check)

    |B|_validated  subset of |B|_possible that the language's validator
                   (check_morph_sequence_<lang>) accepts when each bundle
                   is wrapped in a singleton-token sequence

    |B|_observed   distinct bundles the engine actually emits on the
                   train+val+test corpus (mini_experiment/data/<lang>_*.txt)

The relationship is observed ≤ validated ≤ possible.

Outputs a JSON report to morph_efficiency_project/logs/summary/bundle_space.json
and prints a Markdown table to stdout.

Usage:
    python morph_efficiency_project/scripts/compute_bundle_space.py
    python morph_efficiency_project/scripts/compute_bundle_space.py --langs zh,en
    python morph_efficiency_project/scripts/compute_bundle_space.py --sentence-cap 5000
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from itertools import product
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from morph_efficiency_project.scripts.engines import (
    ArabicEngine,
    EnglishEngine,
    MandarinEngine,
    TokenInfo,
    TurkishEngine,
    check_morph_sequence_ar,
    check_morph_sequence_en,
    check_morph_sequence_tr,
    check_morph_sequence_zh,
)

# Project-wide canonical language order: ZH → EN → TR → AR.
LANG_ORDER = ("zh", "en", "tr", "ar")

ENGINES = {
    "zh": MandarinEngine,
    "en": EnglishEngine,
    "tr": TurkishEngine,
    "ar": ArabicEngine,
}

VALIDATORS = {
    "zh": check_morph_sequence_zh,
    "en": check_morph_sequence_en,
    "tr": check_morph_sequence_tr,
    "ar": check_morph_sequence_ar,
}

CORPUS_DIR = ROOT / "mini_experiment" / "data"
OUT_PATH = ROOT / "morph_efficiency_project" / "logs" / "summary" / "bundle_space.json"

# ── Theoretical slot-value spaces ─────────────────────────────────────────────
# Derived from the validators in engines/shared.py (allowed-key sets per POS)
# and the engine sources (emitted value sets). A value of None represents the
# "tag absent" case, since bundles are sparse (most positions have most tags
# missing). Open-vocabulary tags (e.g. `phrasal_verb_base`) are excluded from
# the combinatorial count — they would explode the space without adding a
# closed-form indicator.

POSSIBLE_SLOTS: Dict[str, Dict[str, Dict[str, List]]] = {
    "zh": {
        "NOUN":  {"num":          [None, "PL"]},
        "VERB":  {"aspect":       [None, "PERF", "DUR", "EXP", "PROG"],
                  "role":         [None, "PREDICATE", "COMPLEMENT"]},
        "ADV":   {"negation":     [None, "BU", "MEI", "BIE"],
                  "degree":       [None, "VERY", "RATHER"],
                  "aspect":       [None, "PERF", "DUR", "EXP", "PROG"]},
        "PRON":  {"person":       [None, "1", "2", "3"],
                  "num":          [None, "SG", "PL"],
                  "gender":       [None, "M", "F"],
                  "deixis":       [None, "PROX", "DIST"],
                  "interrog":     [None, "YES"],
                  "reflex":       [None, "YES"]},
        "PART":  {"aspect":       [None, "PERF", "DUR", "EXP"],
                  "particle_type":[None, "QUESTION", "MOOD"]},
        "ADP":   {"construction": [None, "BA", "BEI"],
                  "voice":        [None, "PASS"]},
        "CLF":   {"classifier":   [None, "GE"]},   # closed set is large; cardinality token
        "AUX":   {"modal":        [None, "HUI", "NENG", "YAO", "BIXU", "YING"]},
        "NUM":   {"role":         [None, "QUANT", "ORDINAL"]},
        "DET":   {"subcat":       [None, "DEM", "QUANT"],
                  "interrog":     [None, "YES"]},
        "CONJ":  {"subcat":       [None, "COORD", "SUBORD"]},
    },

    "en": {
        "NOUN":  {"num":          [None, "SG", "PL"],
                  "poss":         [None, "YES"],
                  "ambig_3sg":    [None, "YES"]},
        "VERB":  {"tense":        [None, "PAST", "PRES"],
                  "aspect":       [None, "PERF", "PROG", "SIMPLE"],
                  "person":       [None, "3SG"],
                  "voice":        [None, "ACT", "PASS"]},
        "ADJ":   {"degree":       [None, "COMP", "SUPER"]},
        "ADV":   {"degree":       [None, "COMP", "SUPER"]},
        "PRON":  {},
        "DET":   {},
        "ADP":   {},
        "PART":  {},
        "PROPER":{},
    },

    "tr": {
        # Strict-slot Cartesian product. Validator enforces order, not which
        # slots co-occur, so the possible count is the full product per POS.
        "NOUN":  {"NUM":          [None, "SG", "PL"],
                  "POSS":         [None, "1SG", "2SG", "3SG", "1PL", "2PL", "3PL"],
                  "CASE":         [None, "NOM", "ACC", "GEN", "DAT", "LOC", "ABL", "INS"]},
        "ADJ":   {"NUM":          [None, "SG", "PL"],
                  "POSS":         [None, "1SG", "2SG", "3SG", "1PL", "2PL", "3PL"],
                  "CASE":         [None, "NOM", "ACC", "GEN", "DAT", "LOC", "ABL", "INS"]},
        "VERB":  {"VOICE":        [None, "ACT", "PASS", "CAUS", "REFL", "RECIP"],
                  "polarity":     [None, "NEG"],
                  "TENSE":        [None, "PAST_DEF", "PAST_NARR", "PRES", "FUT",
                                   "AOR", "PROG", "NECESS"],
                  "MOOD":         [None, "IND", "IMP", "COND", "OPT", "NECC"],
                  "PERSON_NUM":   [None, "1SG", "2SG", "3SG", "1PL", "2PL", "3PL"]},
        "ADV":   {},
        "PRON":  {"person":       [None, "1", "2", "3"],
                  "num":          [None, "SG", "PL"]},
        "PART":  {},
    },

    "ar": {
        "VERB":  {"form":         [None, "I", "II", "III", "IV", "V", "VI",
                                   "VII", "VIII", "IX", "X"],
                  "tense":        [None, "PAST", "PRES", "IMP"],
                  "person":       [None, "1", "2", "3"],
                  "num":          [None, "SG", "DU", "PL"],
                  "gender":       [None, "M", "F"],
                  "voice":        [None, "ACT", "PASS"],
                  "mood":         [None, "IND", "JUS", "SUB"]},
        "NOM":   {"num":          [None, "SG", "DU", "PL"],
                  "gender":       [None, "M", "F"],
                  "case":         [None, "NOM", "ACC", "GEN", "OBL"],
                  "def":          [None, "DEF", "INDF"],
                  "role":         [None, "DERIVED", "PASSIVE_PARTICIPLE", "PROPER"]},
        "ADJ":   {"num":          [None, "SG", "DU", "PL"],
                  "gender":       [None, "M", "F"],
                  "case":         [None, "NOM", "ACC", "GEN", "OBL"],
                  "def":          [None, "DEF", "INDF"]},
        "PART":  {"subcat":       [None, "PREP", "CONJ", "NEG", "INTERROG",
                                   "VOCATIVE", "DISCOURSE", "OATH", "RESPONSE"]},
        "PROPER":{},
        "FOREIGN":{"origin":      [None, "FOREIGN"]},
    },
}


def enumerate_possible(lang: str) -> set:
    """Enumerate the theoretical bundle space as a set of (POS, frozenset(tags))."""
    bundles = set()
    for pos, slots in POSSIBLE_SLOTS[lang].items():
        if not slots:
            bundles.add((pos, frozenset()))
            continue
        keys = list(slots.keys())
        value_lists = [slots[k] for k in keys]
        for combo in product(*value_lists):
            tag_dict = {k: v for k, v in zip(keys, combo) if v is not None}
            bundles.add((pos, frozenset(tag_dict.items())))
    return bundles


def bundle_to_tokeninfo(pos: str, tags_frozen: frozenset) -> TokenInfo:
    tags = dict(tags_frozen)
    return TokenInfo(
        surface="x",
        clitics={},
        template="",
        root="x",
        tags=tags,
        pos=pos,
    )


def filter_validated(lang: str, bundles: set) -> set:
    """Keep only bundles whose singleton sequence passes the validator."""
    validator = VALIDATORS[lang]
    valid = set()
    for pos, tags_frozen in bundles:
        t = bundle_to_tokeninfo(pos, tags_frozen)
        try:
            ok = validator([t])
        except Exception:
            ok = False
        if ok:
            valid.add((pos, tags_frozen))
    return valid


def observe_from_corpus(lang: str, sentence_cap: int) -> Tuple[set, int, int]:
    """Run engine over the corpus; return (unique_bundles, n_sentences, n_tokens)."""
    engine = ENGINES[lang]()
    bundles: set = set()
    n_sent = 0
    n_tok = 0
    for split in ("train", "val", "test"):
        path = CORPUS_DIR / f"{lang}_{split}.txt"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if n_sent >= sentence_cap:
                    return bundles, n_sent, n_tok
                # ZH analyse() is per-character; the others are per-word.
                # All engines accept space-split tokens via analyze().
                words = line.split() if lang != "zh" else list(line)
                for w in words:
                    if not w.strip():
                        continue
                    try:
                        info = engine.analyze(w)
                    except Exception:
                        continue
                    pos = info.pos or "UNKNOWN"
                    tags = frozenset(info.tags.items()) if info.tags else frozenset()
                    bundles.add((pos, tags))
                    n_tok += 1
                n_sent += 1
        if n_sent >= sentence_cap:
            break
    return bundles, n_sent, n_tok


def fmt(n: int) -> str:
    return f"{n:,}"


def main():
    parser = argparse.ArgumentParser(description="Compute bundle-space indicators per language.")
    parser.add_argument("--langs", default=",".join(LANG_ORDER),
                        help=f"Comma-separated subset; default {','.join(LANG_ORDER)}")
    parser.add_argument("--sentence-cap", type=int, default=20_000,
                        help="Max sentences scanned per language (default 20,000 matches case-study scale).")
    parser.add_argument("--no-observed", action="store_true",
                        help="Skip the corpus scan; report only possible & validated.")
    parser.add_argument("--out", type=Path, default=OUT_PATH,
                        help="JSON output path.")
    args = parser.parse_args()

    target_langs = [l for l in args.langs.split(",") if l.strip()]
    report: Dict[str, dict] = {}

    print(f"{'lang':<5} {'possible':>12} {'validated':>12} "
          f"{'observed':>12} {'obs_validated':>14}  {'sentences':>10} {'tokens':>10}")
    print("-" * 84)

    for lang in target_langs:
        t0 = time.time()
        possible = enumerate_possible(lang)
        validated = filter_validated(lang, possible)

        if args.no_observed:
            observed: set = set()
            obs_validated: set = set()
            n_sent = n_tok = 0
        else:
            observed, n_sent, n_tok = observe_from_corpus(lang, args.sentence_cap)
            obs_validated = filter_validated(lang, observed)

        elapsed = time.time() - t0
        print(f"{lang:<5} {fmt(len(possible)):>12} {fmt(len(validated)):>12} "
              f"{fmt(len(observed)):>12} {fmt(len(obs_validated)):>14}  "
              f"{fmt(n_sent):>10} {fmt(n_tok):>10}  ({elapsed:.1f}s)")

        report[lang] = {
            "possible":             len(possible),
            "validated":            len(validated),
            "observed":             len(observed),
            "observed_validated":   len(obs_validated),
            "sentences_scanned":    n_sent,
            "tokens_scanned":       n_tok,
            "sentence_cap":         args.sentence_cap,
            "elapsed_seconds":      round(elapsed, 1),
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport written to {args.out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
