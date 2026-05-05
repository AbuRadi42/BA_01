"""
compositional_generalization_ar.py — Held-out (root × template) evaluation
for Arabic.

Tests whether the Arabic morph model generalises to word forms whose
(root, templatic pattern) combination never appeared in training, while
both the individual root and the individual pattern did. A positive
result would be strong evidence that morphology-aligned tokenization
induces compositional learning of Arabic's root-pattern system, not
merely memorisation of surface--bundle co-occurrences.

Method
------
1. Re-analyse ar_train.txt, ar_test.txt via ArabicEngine.
2. For each word, record its (root, template) pair. (The engine's
   .template field names the wazn pattern — e.g. VERB_TRILATERAL_BARE,
   NOM_DERIVED.)
3. Collect the set of pairs observed in train: train_pairs.
4. For each test-set word, label it as
        - SEEN_PAIR    if (root, template) ∈ train_pairs
        - HELD_OUT     if root ∈ train_roots AND template ∈ train_templates
                       AND (root, template) ∉ train_pairs
        - NOVEL_ATOM   otherwise (new root or new template)
5. Compute per-label word-level loss for each available Arabic model
   (baseline and morph, across rungs), using the model's own tokeniser
   and a single-word forward pass.
6. Report whether morph's advantage over baseline is *larger* on
   HELD_OUT than on SEEN_PAIR — the compositional-learning signal.

Inputs (existing)
-----------------
    mini_experiment/data/ar_{train,test}.txt
    mini_experiment/results_ladder/ar_{baseline,morph}_rung*/
        result.json
        checkpoint_latest.pt

Output
------
    manuscript/compositional_gen_ar.json

Usage
-----
    python morph_efficiency_project/scripts/compositional_generalization_ar.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from morph_efficiency_project.scripts.engines.ar_engine import ArabicEngine  # noqa: E402

DATA_DIR = ROOT / "mini_experiment" / "data"
LADDER_DIR = ROOT / "mini_experiment" / "results_ladder"
OUT = ROOT / "manuscript" / "compositional_gen_ar.json"


def load_split_pairs(path: Path, engine: ArabicEngine, max_words: int | None = None) -> list[tuple[str, str, str]]:
    """Return a list of (word, root, template) for each word in a split."""
    pairs: list[tuple[str, str, str]] = []
    n = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            for word in line.strip().split():
                try:
                    info = engine.analyze(word)
                    pairs.append((word, info.root or word, info.template or ""))
                    n += 1
                    if max_words and n >= max_words:
                        return pairs
                except Exception:
                    continue
    return pairs


def classify_test(test_pairs, train_pairs: set, train_roots: set, train_templates: set) -> dict[str, list[tuple[str, str, str]]]:
    """Bucket test words into SEEN_PAIR, HELD_OUT, NOVEL_ATOM."""
    buckets = {"SEEN_PAIR": [], "HELD_OUT": [], "NOVEL_ATOM": []}
    for w, r, t in test_pairs:
        if (r, t) in train_pairs:
            buckets["SEEN_PAIR"].append((w, r, t))
        elif r in train_roots and t in train_templates:
            buckets["HELD_OUT"].append((w, r, t))
        else:
            buckets["NOVEL_ATOM"].append((w, r, t))
    return buckets


def main() -> int:
    engine = ArabicEngine()

    print("analysing train split...", file=sys.stderr)
    train_pairs_list = load_split_pairs(DATA_DIR / "ar_train.txt", engine, max_words=200_000)
    print(f"  {len(train_pairs_list):,} words", file=sys.stderr)

    print("analysing test split...", file=sys.stderr)
    test_pairs_list = load_split_pairs(DATA_DIR / "ar_test.txt", engine)
    print(f"  {len(test_pairs_list):,} words", file=sys.stderr)

    train_pairs = {(r, t) for _, r, t in train_pairs_list}
    train_roots = {r for _, r, _ in train_pairs_list}
    train_templates = {t for _, _, t in train_pairs_list}

    buckets = classify_test(test_pairs_list, train_pairs, train_roots, train_templates)

    # Counters
    root_counter = Counter(r for _, r, _ in train_pairs_list)
    template_counter = Counter(t for _, _, t in train_pairs_list)

    summary = {
        "train_words": len(train_pairs_list),
        "test_words": len(test_pairs_list),
        "unique_train_pairs": len(train_pairs),
        "unique_train_roots": len(train_roots),
        "unique_train_templates": len(train_templates),
        "test_bucket_counts": {k: len(v) for k, v in buckets.items()},
        "top_10_roots_by_frequency": root_counter.most_common(10),
        "top_10_templates_by_frequency": template_counter.most_common(10),
    }

    # Example words per bucket (first 10 of each for paper-side inspection).
    summary["bucket_examples"] = {
        k: [{"word": w, "root": r, "template": t} for (w, r, t) in v[:10]]
        for k, v in buckets.items()
    }

    # Note: full per-model loss computation is deferred to a follow-up pass
    # because it requires loading each trained model and re-tokenising
    # the held-out set. For now, record the bucketing so the paper can
    # already cite bucket sizes and examples; the loss attribution runs
    # when the ladder completes.
    summary["note_loss_attribution"] = (
        "Per-model loss attribution is a follow-up pass that reloads each "
        "trained Arabic checkpoint (baseline and morph at each rung) and "
        "scores only tokens belonging to each bucket. This script records "
        "bucket definitions and example words; the model-loading pass will "
        "overwrite this field with per-bucket, per-model loss figures."
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(OUT)

    print(f"\nbucket counts: {summary['test_bucket_counts']}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
