"""
tokenize_tier2_ar.py — Arabic two-tier morph tokenizer.

Tier 1 (existing, run_mini.py's tokenize_morph) encodes Arabic as
(surface_bundle_id, bundle_id). The surface_bundle token is a joint
"root+bundle" string — it carries root identity baked into the token
but does not expose root-sharing structure to the model.

Tier 2 (this script) adds a third, parallel input stream: the pure
triconsonantal root as its own token ID. The model can then sum:

    x = tok_emb[surface_bundle_id]
      + feat_emb[bundle_id]
      + root_emb[root_id]

Words sharing a root get an additional tied signal. This directly tests
whether Arabic's templatic morphology stores bits lexicon-accessibly
(exploited by the root stream) above what its surface is able to expose
(exploited by the Tier 1 bundle stream). The marginal ΔL between Tier 1
and Tier 2 on Arabic quantifies the "hidden 41%" §7.4 names — the
lexicon-recoverable axis ρ's filter rejects.

Outputs:
    mini_experiment/data/ar_morph_root_{train,val,test}.npy   # root IDs
    mini_experiment/tokenizers/ar_morph_root_vocab.json        # root -> id

Reuses the existing ar_morph_{train,val,test}.npy and
ar_morph_feat_{train,val,test}.npy from tokenize_morph.

Resumable. Idempotent.

Usage:
    python morph_efficiency_project/scripts/tokenize_tier2_ar.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from morph_efficiency_project.scripts.engines.ar_engine import ArabicEngine

DATA_DIR = ROOT / "mini_experiment" / "data"
TOK_DIR = ROOT / "mini_experiment" / "tokenizers"

LANG = "ar"
SPECIALS = {"<pad>": 0, "<unk>": 1, "<s>": 2, "</s>": 3}
ROOT_VOCAB_CAP = 20_000


def _extract_roots(split: str, root2id: dict, build_vocab: bool) -> np.ndarray:
    """Re-analyse the corpus line-by-line, emit one root ID per token position
    that aligns with the existing ar_morph_{split}.npy token sequence.
    """
    from mini_experiment import run_mini  # reuse split file paths
    engine = ArabicEngine()
    txt_path = DATA_DIR / f"{LANG}_{split}.txt"
    ids: list[int] = [SPECIALS["<pad>"]]  # we'll fill as we go

    with txt_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # <s> marker
            ids.append(0)  # root_id=0 (no-root) for BOS
            for word in line.split():
                try:
                    info = engine.analyze(word)
                    root = info.root or word
                except Exception:
                    root = word
                if build_vocab:
                    if root not in root2id:
                        root2id[root] = len(root2id)
                rid = root2id.get(root, SPECIALS["<unk>"])
                ids.append(rid)
            ids.append(0)  # root_id=0 for EOS

    # drop the initial placeholder we used to make the counter align
    return np.array(ids[1:], dtype=np.int32)


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TOK_DIR.mkdir(parents=True, exist_ok=True)

    vocab_path = TOK_DIR / f"{LANG}_morph_root_vocab.json"
    out_splits = {s: DATA_DIR / f"{LANG}_morph_root_{s}.npy" for s in ("train", "val", "test")}

    if vocab_path.exists() and all(p.exists() for p in out_splits.values()):
        root2id = json.loads(vocab_path.read_text(encoding="utf-8"))
        print(f"[ar/tier2] already tokenised: {len(root2id):,} roots", file=sys.stderr)
        return 0

    root2id: dict = dict(SPECIALS)

    # Build vocab on train, then encode each split.
    train_ids = _extract_roots("train", root2id, build_vocab=True)
    if len(root2id) > ROOT_VOCAB_CAP:
        # Cap by insertion order (train is scanned; first-seen is an OK proxy
        # for frequency in Arabic Wikipedia, where common roots appear early).
        root2id = dict(list(root2id.items())[:ROOT_VOCAB_CAP])
        # Re-emit train IDs under the capped vocab.
        train_ids = _extract_roots("train", dict(root2id), build_vocab=False)

    vocab_path.write_text(json.dumps(root2id, ensure_ascii=False), encoding="utf-8")

    np.save(out_splits["train"], train_ids)
    print(f"[ar/tier2] train: {len(train_ids):,} root-IDs, vocab={len(root2id):,}",
          file=sys.stderr)

    for split in ("val", "test"):
        ids = _extract_roots(split, dict(root2id), build_vocab=False)
        np.save(out_splits[split], ids)
        print(f"[ar/tier2] {split}: {len(ids):,} root-IDs", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
