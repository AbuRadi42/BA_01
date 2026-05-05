"""
compositional_eval_ar.py — Per-model loss attribution on the held-out
(root × template) bucket for Arabic.

The compositional_generalization_ar.py script bucketed Arabic test words
into SEEN_PAIR (216 k), HELD_OUT (4.7 k), and NOVEL_ATOM (13.7 k). This
script reloads each trained Arabic checkpoint at rung 1 and computes the
per-bucket cross-entropy loss, so we can see whether the morph regimes
generalise compositionally — i.e. whether their advantage over baseline
is *larger* on HELD_OUT than on SEEN_PAIR. A positive result is evidence
the morph models have learned to compose roots × patterns, not memorise
surface--bundle co-occurrences.

Models scored
    1. ar_baseline_rung1   (BPE)
    2. ar_morph_rung1      (1st-tier morph)
    3. ar_morph_tier2_rung1 (2nd-tier morph: + explicit root-id stream)

Output
    manuscript/compositional_eval_ar.json

Usage
    python morph_efficiency_project/scripts/compositional_eval_ar.py
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "mini_experiment" / "data"
TOK_DIR = ROOT / "mini_experiment" / "tokenizers"
LADDER_DIR = ROOT / "mini_experiment" / "results_ladder"
OUT = ROOT / "manuscript" / "compositional_eval_ar.json"


# Mirror tokenize_morph_engine.py / tokenize_tier2_ar.py specials.
SPECIALS = {"<pad>": 0, "<unk>": 1, "<s>": 2, "</s>": 3}


def _morph_segment(word: str) -> tuple[str, str]:
    """Mirror run_mini.py's _morph_segment for Arabic."""
    from mini_experiment import run_mini
    return run_mini._morph_segment(word, "ar")


def _classify_arabic_test_word(word: str, train_pairs, train_roots, train_templates):
    from morph_efficiency_project.scripts.engines.ar_engine import ArabicEngine
    eng = ArabicEngine()
    try:
        info = eng.analyze(word)
        r, t = info.root or word, info.template or ""
    except Exception:
        return None
    if (r, t) in train_pairs:
        return "SEEN_PAIR"
    if r in train_roots and t in train_templates:
        return "HELD_OUT"
    return "NOVEL_ATOM"


def build_buckets() -> dict[str, list[str]]:
    """Re-derive bucketed words from compositional_generalization_ar.json."""
    summary = json.loads((ROOT / "manuscript" / "compositional_gen_ar.json").read_text(encoding="utf-8"))
    # We have only example-list snippets there; recompute from corpus.
    from morph_efficiency_project.scripts.engines.ar_engine import ArabicEngine
    eng = ArabicEngine()
    train_pairs: set = set()
    train_roots: set = set()
    train_templates: set = set()
    n = 0
    with (DATA_DIR / "ar_train.txt").open(encoding="utf-8") as f:
        for line in f:
            for w in line.strip().split():
                try:
                    info = eng.analyze(w)
                    r, t = info.root or w, info.template or ""
                except Exception:
                    continue
                train_pairs.add((r, t))
                train_roots.add(r)
                train_templates.add(t)
                n += 1
                if n >= 200_000:
                    break
            if n >= 200_000:
                break
    buckets: dict[str, list[str]] = {"SEEN_PAIR": [], "HELD_OUT": [], "NOVEL_ATOM": []}
    with (DATA_DIR / "ar_test.txt").open(encoding="utf-8") as f:
        for line in f:
            for w in line.strip().split():
                try:
                    info = eng.analyze(w)
                    r, t = info.root or w, info.template or ""
                except Exception:
                    continue
                if (r, t) in train_pairs:
                    buckets["SEEN_PAIR"].append(w)
                elif r in train_roots and t in train_templates:
                    buckets["HELD_OUT"].append(w)
                else:
                    buckets["NOVEL_ATOM"].append(w)
    return buckets


def encode_baseline(words: Iterable[str]) -> list[int]:
    """Encode a sequence of words using the Arabic BPE tokenizer."""
    import sentencepiece as spm
    sp = spm.SentencePieceProcessor()
    sp.load(str(TOK_DIR / "ar_base.model"))
    text = " ".join(words)
    return sp.encode(text, out_type=int)


def encode_morph(words: Iterable[str], tier2: bool) -> tuple[list[int], list[int], list[int] | None]:
    """Encode words via the morph tokeniser, matching training exactly.

    Important: training in run_mini.tokenize_morph uses the *shallow*
    _morph_segment (affix-based) for the surface_bundle_id and bundle_id
    streams. Tier-2 layers an engine-derived pure-root stream on top.
    Mismatching this format causes every token to map to <unk>.
    """
    vocab = json.loads((TOK_DIR / "ar_morph_vocab.json").read_text(encoding="utf-8"))
    bundles = json.loads((TOK_DIR / "ar_morph_bundles.json").read_text(encoding="utf-8"))
    if tier2:
        root_vocab = json.loads((TOK_DIR / "ar_morph_root_vocab.json").read_text(encoding="utf-8"))
        from morph_efficiency_project.scripts.engines.ar_engine import ArabicEngine
        eng = ArabicEngine()
    from mini_experiment.run_mini import _morph_segment as shallow_segment

    tok_ids: list[int] = [SPECIALS["<s>"]]
    feat_ids: list[int] = [0]
    root_ids: list[int] | None = [0] if tier2 else None
    for w in words:
        # Streams 1 & 2: shallow segmentation, matching training.
        try:
            shallow_root, shallow_tag = shallow_segment(w, "ar")
        except Exception:
            shallow_root, shallow_tag = w, "ROOT"
        shallow_surface = f"{shallow_root}+{shallow_tag}"
        tok_ids.append(vocab.get(shallow_surface, SPECIALS["<unk>"]))
        feat_ids.append(bundles.get(shallow_tag, 0))
        # Stream 3 (tier-2 only): engine-derived pure root.
        if tier2:
            try:
                engine_root = eng.analyze(w).root or w
            except Exception:
                engine_root = w
            root_ids.append(root_vocab.get(engine_root, SPECIALS["<unk>"]))
    tok_ids.append(SPECIALS["</s>"])
    feat_ids.append(0)
    if tier2:
        root_ids.append(0)
    return tok_ids, feat_ids, root_ids


def score_baseline(words: list[str], n_layer: int, n_embd: int, n_head: int, ffn_dim: int) -> float:
    """Average per-token cross-entropy of the baseline model on the given words."""
    import torch
    from mini_experiment import run_mini
    # Configure run_mini's CFG to match the rung-1 baseline architecture.
    run_mini.CFG.update(dict(n_layer=n_layer, n_embd=n_embd, n_head=n_head,
                             ffn_dim=ffn_dim, seq_len=128, dropout=0.0))
    ckpt_path = LADDER_DIR / "ar_baseline_rung1_250000p_5000000t" / "checkpoint_latest.pt"
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    import sentencepiece as spm
    sp = spm.SentencePieceProcessor()
    sp.load(str(TOK_DIR / "ar_base.model"))
    model = run_mini.build_model(sp.get_piece_size(), 1, morph_mode=False)
    model.load_state_dict(ckpt["model"])
    model.eval()

    # Encode all words as one stream, then chunk to seq_len.
    ids = encode_baseline(words)
    return _stream_ce_baseline(model, ids, seq_len=128)


def _stream_ce_baseline(model, ids: list[int], seq_len: int) -> float:
    import torch
    if len(ids) < 2:
        return float("nan")
    arr = np.array(ids, dtype=np.int64)
    total_loss = 0.0
    total_n = 0
    with torch.no_grad():
        for i in range(0, len(arr) - 1, seq_len):
            chunk = arr[i:i + seq_len + 1]
            if len(chunk) < 2:
                continue
            x = torch.tensor(chunk[:-1].copy(), dtype=torch.long).unsqueeze(0)
            f = torch.zeros_like(x)
            y = torch.tensor(chunk[1:].copy(), dtype=torch.long).unsqueeze(0)
            _, loss = model(x, f, y)
            n = int((y != 0).sum().item())
            total_loss += float(loss.item()) * n
            total_n += n
    return total_loss / max(total_n, 1)


def score_morph(words: list[str], tier2: bool) -> float:
    import torch
    from mini_experiment import run_mini
    run_mini.CFG.update(dict(n_layer=2, n_embd=64, n_head=4, ffn_dim=256,
                             seq_len=128, dropout=0.0))

    if tier2:
        from morph_efficiency_project.scripts.train_tier2_ar import build_tier2_model
        ckpt_path = LADDER_DIR / "ar_morph_tier2_rung1_250000p_5000000t" / "checkpoint_latest.pt"
        ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        vocab = json.loads((TOK_DIR / "ar_morph_vocab.json").read_text(encoding="utf-8"))
        bundles = json.loads((TOK_DIR / "ar_morph_bundles.json").read_text(encoding="utf-8"))
        root_vocab = json.loads((TOK_DIR / "ar_morph_root_vocab.json").read_text(encoding="utf-8"))
        cfg = dict(n_layer=2, n_embd=64, n_head=4, ffn_dim=256, seq_len=128, dropout=0.0)
        model = build_tier2_model(len(vocab), len(bundles), len(root_vocab), cfg)
        model.load_state_dict(ckpt["model"])
        model.eval()
    else:
        ckpt_path = LADDER_DIR / "ar_morph_rung1_250000p_5000000t" / "checkpoint_latest.pt"
        ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        vocab = json.loads((TOK_DIR / "ar_morph_vocab.json").read_text(encoding="utf-8"))
        bundles = json.loads((TOK_DIR / "ar_morph_bundles.json").read_text(encoding="utf-8"))
        model = run_mini.build_model(len(vocab), len(bundles), morph_mode=True)
        model.load_state_dict(ckpt["model"])
        model.eval()

    tok, feat, root = encode_morph(words, tier2=tier2)
    return _stream_ce_morph(model, tok, feat, root if tier2 else None, seq_len=128)


def _stream_ce_morph(model, tok_ids, feat_ids, root_ids, seq_len):
    import torch
    arr = np.array(tok_ids, dtype=np.int64)
    feat_arr = np.array(feat_ids, dtype=np.int64)
    root_arr = np.array(root_ids, dtype=np.int64) if root_ids is not None else None
    total_loss = 0.0
    total_n = 0
    with torch.no_grad():
        for i in range(0, len(arr) - 1, seq_len):
            chunk = arr[i:i + seq_len + 1]
            fchunk = feat_arr[i:i + seq_len + 1]
            if len(chunk) < 2:
                continue
            x = torch.tensor(chunk[:-1].copy(), dtype=torch.long).unsqueeze(0)
            f = torch.tensor(fchunk[:-1].copy(), dtype=torch.long).unsqueeze(0)
            y = torch.tensor(chunk[1:].copy(), dtype=torch.long).unsqueeze(0)
            if root_arr is not None:
                rchunk = root_arr[i:i + seq_len + 1]
                r = torch.tensor(rchunk[:-1].copy(), dtype=torch.long).unsqueeze(0)
                _, loss = model(x, f, r, y)
            else:
                _, loss = model(x, f, y)
            n = int((y != 0).sum().item())
            total_loss += float(loss.item()) * n
            total_n += n
    return total_loss / max(total_n, 1)


def main() -> int:
    print("recomputing buckets from corpus...", file=sys.stderr)
    buckets = build_buckets()
    for k, v in buckets.items():
        print(f"  {k:12s} {len(v):>7,} words", file=sys.stderr)

    # For tractability on CPU, sample fixed-size subsets per bucket.
    SAMPLE = 2000
    rng = np.random.default_rng(42)
    sampled = {k: list(rng.choice(v, size=min(SAMPLE, len(v)), replace=False))
               for k, v in buckets.items() if v}

    results: dict[str, dict[str, float]] = defaultdict(dict)
    for bucket, words in sampled.items():
        words = [str(w) for w in words]
        print(f"\nbucket {bucket} ({len(words)} sampled words)", file=sys.stderr)

        print("  scoring baseline...", file=sys.stderr)
        results[bucket]["baseline"] = score_baseline(
            words, n_layer=2, n_embd=64, n_head=4, ffn_dim=256,
        )
        print(f"    L = {results[bucket]['baseline']:.4f}", file=sys.stderr)

        print("  scoring 1st-tier morph...", file=sys.stderr)
        results[bucket]["morph_tier1"] = score_morph(words, tier2=False)
        print(f"    L = {results[bucket]['morph_tier1']:.4f}", file=sys.stderr)

        print("  scoring 2nd-tier morph...", file=sys.stderr)
        results[bucket]["morph_tier2"] = score_morph(words, tier2=True)
        print(f"    L = {results[bucket]['morph_tier2']:.4f}", file=sys.stderr)

    # Δℒ vs baseline per bucket.
    summary: dict = {}
    for bucket, r in results.items():
        summary[bucket] = {
            **r,
            "delta_L_tier1_vs_baseline": r["baseline"] - r["morph_tier1"],
            "delta_L_tier2_vs_baseline": r["baseline"] - r["morph_tier2"],
            "delta_L_tier2_vs_tier1":    r["morph_tier1"] - r["morph_tier2"],
            "n_sampled": len(sampled[bucket]),
            "n_population": len(buckets[bucket]),
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "buckets": summary,
        "sample_size_per_bucket": SAMPLE,
        "random_seed": 42,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print(f"{'Bucket':<14} {'baseline':>9} {'tier1':>9} {'tier2':>9} {'Δt1-base':>9} {'Δt2-base':>9} {'Δt2-t1':>9}")
    for k, r in summary.items():
        print(f"{k:<14} {r['baseline']:>9.4f} {r['morph_tier1']:>9.4f} {r['morph_tier2']:>9.4f}"
              f" {r['delta_L_tier1_vs_baseline']:>9.4f} {r['delta_L_tier2_vs_baseline']:>9.4f}"
              f" {r['delta_L_tier2_vs_tier1']:>9.4f}")

    print(f"\nWrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
