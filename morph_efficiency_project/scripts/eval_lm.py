"""
eval_lm.py
----------
Evaluates a trained language model on val and test splits.
Computes average cross-entropy loss and perplexity per token.

Usage:
  python scripts/eval_lm.py --language en --regime baseline
  python scripts/eval_lm.py --language ar --regime morph
  python scripts/eval_lm.py --language all --regime all

Reads checkpoints from:  models/{language}_{regime}/
Reads data from:         data/processed/{language}/{regime}/
Saves to:                logs/evaluation/{language}_{regime}_lm.json
"""

import argparse
import json
import logging
import math
import os
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

# Re-use model and dataset definitions from train_lm
import sys
sys.path.insert(0, os.path.dirname(__file__))
from train_lm import GPTModel, TokenDataset, MODEL_CONFIG, TRAIN_CONFIG

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

def load_model(lang: str, regime: str, device: torch.device) -> tuple[GPTModel, int]:
    """Load the latest checkpoint for (lang, regime). Returns (model, step)."""
    morph_mode = (regime == "morph")
    model_dir  = os.path.join("models", f"{lang}_{regime}")

    if not os.path.isdir(model_dir):
        raise FileNotFoundError(
            f"No model directory found: {model_dir}\n"
            f"Run train_lm.py --language {lang} --regime {regime} first."
        )

    ckpts = sorted(
        [f for f in os.listdir(model_dir) if f.startswith("ckpt_step")],
        key=lambda x: int(x.split("step")[1].split(".")[0])
    )
    if not ckpts:
        raise FileNotFoundError(f"No checkpoints found in {model_dir}")

    ckpt_path = os.path.join(model_dir, ckpts[-1])
    step = int(ckpts[-1].split("step")[1].split(".")[0])
    log.info(f"[{lang}/{regime}] Loading checkpoint: {ckpt_path} (step {step})")

    # Resolve vocab sizes
    if morph_mode:
        vocab_path = os.path.join("tokenizers", f"{lang}_morph", "vocab.json")
        feat_path  = os.path.join("tokenizers", f"{lang}_morph", "feature_bundles.json")
        with open(vocab_path, encoding="utf-8") as f:
            vocab_size = len(json.load(f))
        with open(feat_path, encoding="utf-8") as f:
            n_feat_bundles = len(json.load(f))
    else:
        import sentencepiece as spm
        sp = spm.SentencePieceProcessor()
        sp.load(os.path.join("tokenizers", f"{lang}_base", f"{lang}_base.model"))
        vocab_size     = sp.get_piece_size()
        n_feat_bundles = 1

    model = GPTModel(vocab_size, n_feat_bundles, MODEL_CONFIG, morph_mode).to(device)
    if device.type == "cuda":
        model = model.to(torch.bfloat16)

    ckpt = torch.load(ckpt_path, map_location=device)
    model.load_state_dict(ckpt["model"])
    model.eval()
    return model, step

@torch.no_grad()
def evaluate_split(model: GPTModel, loader: DataLoader,
                   device: torch.device) -> tuple[float, float, int]:
    """Returns (avg_loss, perplexity, num_tokens)."""
    total_loss   = 0.0
    total_tokens = 0

    for x, feat, y in loader:
        x, feat, y = x.to(device), feat.to(device), y.to(device)
        with torch.autocast(device_type=device.type, dtype=torch.bfloat16):
            _, loss = model(x, feat, y)

        # loss is mean over non-pad tokens in the batch
        n_tokens = (y != 0).sum().item()
        total_loss   += loss.item() * n_tokens
        total_tokens += n_tokens

    avg_loss = total_loss / max(total_tokens, 1)
    ppl      = math.exp(min(avg_loss, 20))
    return avg_loss, ppl, total_tokens

def evaluate(lang: str, regime: str):
    morph_mode = (regime == "morph")
    log_path   = os.path.join("logs", "evaluation", f"{lang}_{regime}_lm.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    device = (
        torch.device("cuda") if torch.cuda.is_available() else
        torch.device("mps")  if torch.backends.mps.is_available() else
        torch.device("cpu")
    )
    log.info(f"[{lang}/{regime}] Device: {device}")

    model, step = load_model(lang, regime, device)

    proc_base  = os.path.join("data", "processed", lang,
                              "morph" if morph_mode else "baseline")
    seq_len    = TRAIN_CONFIG["sequence_length"]
    batch_size = TRAIN_CONFIG["batch_size"]

    results = {
        "language": lang,
        "regime":   regime,
        "step":     step,
    }

    for split in ("val", "test"):
        tok_path  = os.path.join(proc_base, f"{split}_tokens.npy")
        feat_path = os.path.join(proc_base, f"{split}_feature_ids.npy") if morph_mode else None

        if not os.path.exists(tok_path):
            log.warning(f"[{lang}/{regime}] {split} data not found: {tok_path} — skipping.")
            continue

        ds     = TokenDataset(tok_path, feat_path, seq_len)
        loader = DataLoader(ds, batch_size=batch_size, shuffle=False,
                            num_workers=2, pin_memory=True, drop_last=False)

        log.info(f"[{lang}/{regime}] Evaluating {split} ({len(ds):,} sequences)...")
        avg_loss, ppl, n_tokens = evaluate_split(model, loader, device)

        log.info(f"[{lang}/{regime}] {split}: loss={avg_loss:.4f} ppl={ppl:.2f} "
                 f"tokens={n_tokens:,}")

        results[f"{split}_loss"]   = round(avg_loss, 4)
        results[f"{split}_ppl"]    = round(ppl, 4)
        results[f"num_tokens_{split}"] = n_tokens

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    log.info(f"[{lang}/{regime}] Results saved → {log_path}")

def main():
    parser = argparse.ArgumentParser(description="Evaluate language model perplexity.")
    parser.add_argument("--language", choices=["en", "ar", "tr", "all"], required=True)
    parser.add_argument("--regime",   choices=["baseline", "morph", "all"], required=True)
    args = parser.parse_args()

    langs   = ["en", "ar", "tr"] if args.language == "all" else [args.language]
    regimes = ["baseline", "morph"] if args.regime == "all" else [args.regime]

    for lang in langs:
        for regime in regimes:
            evaluate(lang, regime)

if __name__ == "__main__":
    main()
