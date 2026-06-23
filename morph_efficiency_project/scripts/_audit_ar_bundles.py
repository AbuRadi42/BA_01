"""
_audit_ar_bundles.py
--------------------
Audit which validator rules reject Arabic engine bundles.

For each unique (POS, frozenset(tags)) emitted by ArabicEngine over the
mini_experiment Arabic corpus, run check_morph_sequence_ar on a singleton
TokenInfo, classify the rejection reason, and collect 2-3 example surface
words per top rejected bundle.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from morph_efficiency_project.scripts.engines import (
    ArabicEngine,
    TokenInfo,
    check_morph_sequence_ar,
)

CORPUS_DIR = ROOT / "mini_experiment" / "data"
SENTENCE_CAP = 20_000


def classify_rejection(pos: str, tags: dict) -> str:
    """Return the FIRST validator rule that rejects this singleton bundle.
    Mirrors the rule order in check_morph_sequence_ar."""
    keys = set(tags.keys())
    if pos == "VERB":
        if "tense" not in keys:
            return "VERB_missing_tense"
        if "person" not in keys:
            return "VERB_missing_person"
        if tags.get("tense") == "IMP":
            if tags.get("person") != "2":
                return "IMP_with_non2_person"
            if tags.get("voice") != "ACT":
                return "IMP_without_ACT_voice"
        if tags.get("voice") == "PASS" and tags.get("tense") == "IMP":
            return "PASS_with_IMP"
        if tags.get("mood") == "JUS" and tags.get("tense") != "PRES":
            return "JUS_without_PRES"
        if "case" in keys:
            return "VERB_with_case_tag"
        if "def" in keys:
            return "VERB_with_def_tag"
    if pos == "NOM":
        if "tense" in keys:
            return "NOM_with_tense"
        if "person" in keys:
            return "NOM_with_person"
        if "mood" in keys:
            return "NOM_with_mood"
        if "num" not in keys:
            return "NOM_missing_num"
        if "gender" not in keys:
            return "NOM_missing_gender"
    if pos == "ADJ":
        if "tense" in keys:
            return "ADJ_with_tense"
        if "person" in keys:
            return "ADJ_with_person"
        if "mood" in keys:
            return "ADJ_with_mood"
    return "ACCEPTED"


def main():
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    engine = ArabicEngine()
    bundles: set = set()
    # Map (pos, frozenset(tags)) -> list of surface examples (max 3)
    examples: dict = defaultdict(list)
    n_sent = n_tok = 0

    for split in ("train", "val", "test"):
        path = CORPUS_DIR / f"ar_{split}.txt"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if n_sent >= SENTENCE_CAP:
                    break
                for w in line.split():
                    if not w.strip():
                        continue
                    try:
                        info = engine.analyze(w)
                    except Exception:
                        continue
                    pos = info.pos or "UNKNOWN"
                    tags = frozenset(info.tags.items()) if info.tags else frozenset()
                    key = (pos, tags)
                    bundles.add(key)
                    if len(examples[key]) < 3 and info.surface not in examples[key]:
                        examples[key].append(info.surface)
                    n_tok += 1
                n_sent += 1
        if n_sent >= SENTENCE_CAP:
            break

    print(f"Scanned {n_sent:,} sentences, {n_tok:,} tokens")
    print(f"Unique observed bundles: {len(bundles):,}")

    rejected = []
    accepted = 0
    for pos, tags_fs in bundles:
        tags = dict(tags_fs)
        ok = check_morph_sequence_ar([TokenInfo(
            surface="x", clitics={}, template="", root="x", tags=tags, pos=pos,
        )])
        if ok:
            accepted += 1
        else:
            reason = classify_rejection(pos, tags)
            rejected.append((reason, pos, tags_fs))

    print(f"Accepted: {accepted}, Rejected: {len(rejected)}")
    print()

    # Histogram
    cat_counter = Counter(r[0] for r in rejected)
    print("=" * 70)
    print("FAILURE CATEGORY HISTOGRAM")
    print("=" * 70)
    for cat, cnt in cat_counter.most_common():
        print(f"  {cat:<32} {cnt:>5}")
    print()

    # Top 10 most frequent rejected bundles per category
    # "Frequent" here = how many tokens in corpus mapped to this bundle.
    # Re-scan to count token frequencies per bundle.
    print("Counting token-level frequencies per bundle...")
    tok_freq: Counter = Counter()
    n_sent = 0
    for split in ("train", "val", "test"):
        path = CORPUS_DIR / f"ar_{split}.txt"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if n_sent >= SENTENCE_CAP:
                    break
                line = line.strip()
                if not line:
                    continue
                for w in line.split():
                    if not w.strip():
                        continue
                    try:
                        info = engine.analyze(w)
                    except Exception:
                        continue
                    pos = info.pos or "UNKNOWN"
                    tags = frozenset(info.tags.items()) if info.tags else frozenset()
                    tok_freq[(pos, tags)] += 1
                n_sent += 1
        if n_sent >= SENTENCE_CAP:
            break

    # Group rejected by category, then sort by token frequency.
    by_cat: dict = defaultdict(list)
    for reason, pos, tags_fs in rejected:
        by_cat[reason].append((pos, tags_fs))

    print()
    print("=" * 70)
    print("TOP 10 REJECTED BUNDLES PER CATEGORY (by corpus token frequency)")
    print("=" * 70)
    for cat, _ in cat_counter.most_common():
        items = by_cat[cat]
        items_ranked = sorted(items, key=lambda x: tok_freq[x], reverse=True)[:10]
        print(f"\n--- {cat} ({len(items)} unique bundles) ---")
        for pos, tags_fs in items_ranked:
            tags = dict(tags_fs)
            ex = examples[(pos, tags_fs)]
            freq = tok_freq[(pos, tags_fs)]
            tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items())) or "(none)"
            print(f"  freq={freq:>5}  {pos}[{tag_str}]  ex: {ex}")


if __name__ == "__main__":
    main()
