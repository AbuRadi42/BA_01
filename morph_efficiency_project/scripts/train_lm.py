"""
train_lm.py
-----------
Trains a decoder-only GPT-style language model for one language + regime.
Architecture and hyperparameters from plan.md §5.

Usage:
  python scripts/train_lm.py --language en --regime baseline
  python scripts/train_lm.py --language ar --regime morph
  python scripts/train_lm.py --language tr --regime morph --resume

Saves checkpoints to:  models/{language}_{regime}/
Logs training to:      logs/training/{language}_{regime}_training.json
"""

import argparse
import json
import logging
import math
import os
import time
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Architecture (plan.md §5.1) ───────────────────────────────────────────────
MODEL_CONFIG = {
    "n_layer":                 24,
    "n_embd":                1024,
    "n_head":                  16,
    "ffn_dim":               4096,
    "max_position_embeddings":1024,
    "dropout":                0.1,
}

# ── Training hyperparameters (plan.md §5.2) ───────────────────────────────────
TRAIN_CONFIG = {
    "batch_size":           32,
    "sequence_length":    1024,
    "learning_rate":       3e-4,
    "weight_decay":        0.01,
    "grad_clip":            1.0,
    "warmup_steps":        2000,
    "total_tokens":  8_400_000_000,
    "checkpoint_every":    1000,
}


# ── Dataset ───────────────────────────────────────────────────────────────────

class TokenDataset(Dataset):
    """
    Memory-mapped dataset over a flat .npy token ID array.
    Each item is a (sequence_length,) input slice; target is shifted by 1.
    """
    def __init__(self, tok_path: str, feat_path: Optional[str],
                 seq_len: int):
        self.tokens   = np.load(tok_path,  mmap_mode="r")
        self.features = np.load(feat_path, mmap_mode="r") if feat_path else None
        self.seq_len  = seq_len
        self.n        = (len(self.tokens) - 1) // seq_len

    def __len__(self):
        return self.n

    def __getitem__(self, idx):
        start = idx * self.seq_len
        end   = start + self.seq_len
        x = torch.from_numpy(self.tokens[start:end].astype(np.int64))
        y = torch.from_numpy(self.tokens[start + 1:end + 1].astype(np.int64))
        if self.features is not None:
            f = torch.from_numpy(self.features[start:end].astype(np.int64))
        else:
            f = torch.zeros_like(x)
        return x, f, y


# ── Model ─────────────────────────────────────────────────────────────────────

class CausalSelfAttention(nn.Module):
    def __init__(self, n_embd: int, n_head: int, seq_len: int, dropout: float):
        super().__init__()
        assert n_embd % n_head == 0
        self.n_head  = n_head
        self.n_embd  = n_embd
        self.head_dim = n_embd // n_head
        self.qkv  = nn.Linear(n_embd, 3 * n_embd, bias=False)
        self.proj = nn.Linear(n_embd, n_embd, bias=False)
        self.attn_drop = nn.Dropout(dropout)
        self.resid_drop = nn.Dropout(dropout)
        # Causal mask
        self.register_buffer(
            "mask",
            torch.tril(torch.ones(seq_len, seq_len)).view(1, 1, seq_len, seq_len)
        )

    def forward(self, x):
        B, T, C = x.shape
        q, k, v = self.qkv(x).split(self.n_embd, dim=2)
        q = q.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        k = k.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        v = v.view(B, T, self.n_head, self.head_dim).transpose(1, 2)

        # Use PyTorch 2.x flash attention if available
        if hasattr(torch.nn.functional, "scaled_dot_product_attention"):
            y = torch.nn.functional.scaled_dot_product_attention(
                q, k, v, attn_mask=None, dropout_p=self.attn_drop.p if self.training else 0.0,
                is_causal=True,
            )
        else:
            att = (q @ k.transpose(-2, -1)) * (self.head_dim ** -0.5)
            att = att.masked_fill(self.mask[:, :, :T, :T] == 0, float("-inf"))
            att = torch.softmax(att, dim=-1)
            att = self.attn_drop(att)
            y   = att @ v

        y = y.transpose(1, 2).contiguous().view(B, T, C)
        return self.resid_drop(self.proj(y))


class FFN(nn.Module):
    def __init__(self, n_embd: int, ffn_dim: int, dropout: float):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_embd, ffn_dim),
            nn.GELU(),
            nn.Linear(ffn_dim, n_embd),
            nn.Dropout(dropout),
        )

    def forward(self, x):
        return self.net(x)


class TransformerBlock(nn.Module):
    def __init__(self, n_embd: int, n_head: int, ffn_dim: int,
                 seq_len: int, dropout: float):
        super().__init__()
        self.ln1  = nn.LayerNorm(n_embd)
        self.attn = CausalSelfAttention(n_embd, n_head, seq_len, dropout)
        self.ln2  = nn.LayerNorm(n_embd)
        self.ffn  = FFN(n_embd, ffn_dim, dropout)

    def forward(self, x):
        x = x + self.attn(self.ln1(x))
        x = x + self.ffn(self.ln2(x))
        return x


class GPTModel(nn.Module):
    """
    Decoder-only GPT. Morph regime adds a feature_embedding table
    combined with token_embedding (plan.md §5.1).
    """
    def __init__(self, vocab_size: int, n_feat_bundles: int,
                 cfg: dict, morph_mode: bool = False):
        super().__init__()
        C   = cfg["n_embd"]
        T   = cfg["max_position_embeddings"]
        self.morph_mode = morph_mode

        self.tok_emb  = nn.Embedding(vocab_size, C)
        self.pos_emb  = nn.Embedding(T, C)
        if morph_mode:
            self.feat_emb = nn.Embedding(n_feat_bundles, C)
        self.drop     = nn.Dropout(cfg["dropout"])
        self.blocks   = nn.ModuleList([
            TransformerBlock(C, cfg["n_head"], cfg["ffn_dim"], T, cfg["dropout"])
            for _ in range(cfg["n_layer"])
        ])
        self.ln_f     = nn.LayerNorm(C)
        self.head     = nn.Linear(C, vocab_size, bias=False)
        # Weight tying
        self.head.weight = self.tok_emb.weight

        self.apply(self._init_weights)
        log.info(f"GPT: {sum(p.numel() for p in self.parameters()):,} parameters")

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, idx: torch.Tensor, feat: torch.Tensor,
                targets: Optional[torch.Tensor] = None,
                return_hidden: bool = False):
        B, T = idx.shape
        pos  = torch.arange(T, device=idx.device).unsqueeze(0)
        x    = self.tok_emb(idx) + self.pos_emb(pos)
        if self.morph_mode:
            x = x + self.feat_emb(feat)
        x = self.drop(x)
        for block in self.blocks:
            x = block(x)
        hidden = x  # pre-projection hidden states (B, T, C)
        x      = self.ln_f(x)
        logits = self.head(x)

        loss = None
        if targets is not None:
            loss = nn.functional.cross_entropy(
                logits.view(-1, logits.size(-1)),
                targets.view(-1),
                ignore_index=0,  # <pad>
            )
        if return_hidden:
            return logits, loss, hidden
        return logits, loss


# ── LR schedule ───────────────────────────────────────────────────────────────

def get_lr(step: int, warmup: int, total_steps: int, max_lr: float) -> float:
    if step < warmup:
        return max_lr * step / warmup
    progress = (step - warmup) / max(total_steps - warmup, 1)
    return max_lr * 0.5 * (1.0 + math.cos(math.pi * progress))


# ── Checkpoint helpers ────────────────────────────────────────────────────────

def save_checkpoint(model, optimizer, step: int, loss: float, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"ckpt_step{step:07d}.pt")
    torch.save({
        "step":       step,
        "loss":       loss,
        "model":      model.state_dict(),
        "optimizer":  optimizer.state_dict(),
    }, path)
    # Keep only the last 3 checkpoints to save disk space
    ckpts = sorted(
        [f for f in os.listdir(out_dir) if f.startswith("ckpt_step")],
        key=lambda x: int(x.split("step")[1].split(".")[0])
    )
    for old in ckpts[:-3]:
        os.remove(os.path.join(out_dir, old))
    log.info(f"Checkpoint saved: {path}")


def load_latest_checkpoint(model, optimizer, out_dir: str) -> int:
    ckpts = sorted(
        [f for f in os.listdir(out_dir) if f.startswith("ckpt_step")],
        key=lambda x: int(x.split("step")[1].split(".")[0])
    )
    if not ckpts:
        return 0
    path = os.path.join(out_dir, ckpts[-1])
    ckpt = torch.load(path, map_location="cpu")
    model.load_state_dict(ckpt["model"])
    optimizer.load_state_dict(ckpt["optimizer"])
    step = ckpt["step"]
    log.info(f"Resumed from {path} (step {step})")
    return step


# ── Main training loop ────────────────────────────────────────────────────────

def train(lang: str, regime: str, resume: bool = False):
    morph_mode = (regime == "morph")
    model_dir  = os.path.join("models", f"{lang}_{regime}")
    log_path   = os.path.join("logs", "training", f"{lang}_{regime}_training.json")
    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    # ── Resolve data paths ────────────────────────────────────────────────────
    proc_base = os.path.join("data", "processed", lang,
                             "morph" if morph_mode else "baseline")
    train_tok  = os.path.join(proc_base, "train_tokens.npy")
    val_tok    = os.path.join(proc_base, "val_tokens.npy")
    train_feat = os.path.join(proc_base, "train_feature_ids.npy") if morph_mode else None
    val_feat   = os.path.join(proc_base, "val_feature_ids.npy")   if morph_mode else None

    for p in [train_tok, val_tok]:
        if not os.path.exists(p):
            raise FileNotFoundError(
                f"Processed data not found: {p}\n"
                f"Run preprocess_{'morph' if morph_mode else 'baseline'}.py first."
            )

    # ── Vocab size ────────────────────────────────────────────────────────────
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

    log.info(f"[{lang}/{regime}] vocab_size={vocab_size}, "
             f"feat_bundles={n_feat_bundles}, morph_mode={morph_mode}")

    # ── Device ────────────────────────────────────────────────────────────────
    device = (
        torch.device("cuda")  if torch.cuda.is_available()  else
        torch.device("mps")   if torch.backends.mps.is_available() else
        torch.device("cpu")
    )
    log.info(f"Device: {device}")

    # ── Model ─────────────────────────────────────────────────────────────────
    model = GPTModel(vocab_size, n_feat_bundles, MODEL_CONFIG, morph_mode).to(device)
    if device.type == "cuda":
        model = model.to(torch.bfloat16)

    # ── Optimizer ─────────────────────────────────────────────────────────────
    # Separate weight decay: apply only to 2D params (weights), not biases/norms
    decay_params   = [p for n, p in model.named_parameters()
                      if p.requires_grad and p.dim() >= 2]
    nodecay_params = [p for n, p in model.named_parameters()
                      if p.requires_grad and p.dim() < 2]
    optimizer = torch.optim.AdamW([
        {"params": decay_params,   "weight_decay": TRAIN_CONFIG["weight_decay"]},
        {"params": nodecay_params, "weight_decay": 0.0},
    ], lr=TRAIN_CONFIG["learning_rate"], betas=(0.9, 0.95), fused=device.type == "cuda")

    # ── Resume ────────────────────────────────────────────────────────────────
    start_step = 0
    if resume and os.path.isdir(model_dir):
        start_step = load_latest_checkpoint(model, optimizer, model_dir)

    # ── Datasets ──────────────────────────────────────────────────────────────
    seq_len = TRAIN_CONFIG["sequence_length"]
    train_ds = TokenDataset(train_tok, train_feat, seq_len)
    val_ds   = TokenDataset(val_tok,   val_feat,   seq_len)

    train_loader = DataLoader(train_ds, batch_size=TRAIN_CONFIG["batch_size"],
                              shuffle=True, num_workers=4, pin_memory=True,
                              drop_last=True)
    val_loader   = DataLoader(val_ds,   batch_size=TRAIN_CONFIG["batch_size"],
                              shuffle=False, num_workers=2, pin_memory=True,
                              drop_last=False)

    # ── Total steps ───────────────────────────────────────────────────────────
    tokens_per_step = TRAIN_CONFIG["batch_size"] * seq_len
    total_steps     = TRAIN_CONFIG["total_tokens"] // tokens_per_step
    log.info(f"[{lang}/{regime}] total_steps={total_steps:,}, "
             f"tokens_per_step={tokens_per_step:,}")

    # ── Training log ──────────────────────────────────────────────────────────
    training_log = []
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as f:
            try:
                training_log = json.load(f)
            except json.JSONDecodeError:
                training_log = []

    # ── Loop ──────────────────────────────────────────────────────────────────
    model.train()
    step           = start_step
    tokens_seen    = step * tokens_per_step
    t0             = time.time()
    data_iter      = iter(train_loader)

    while step < total_steps:
        # Refill iterator if exhausted (corpus smaller than total_tokens budget)
        try:
            x, feat, y = next(data_iter)
        except StopIteration:
            data_iter = iter(train_loader)
            x, feat, y = next(data_iter)

        x, feat, y = x.to(device), feat.to(device), y.to(device)

        # LR update
        lr = get_lr(step, TRAIN_CONFIG["warmup_steps"], total_steps,
                    TRAIN_CONFIG["learning_rate"])
        for pg in optimizer.param_groups:
            pg["lr"] = lr

        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type=device.type, dtype=torch.bfloat16):
            _, loss = model(x, feat, y)

        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), TRAIN_CONFIG["grad_clip"])
        optimizer.step()

        step        += 1
        tokens_seen += tokens_per_step

        # ── Logging ───────────────────────────────────────────────────────────
        if step % 100 == 0:
            elapsed = time.time() - t0
            ppl     = math.exp(min(loss.item(), 20))
            mem_gb  = (torch.cuda.memory_allocated() / 1e9
                       if device.type == "cuda" else 0.0)
            log.info(
                f"step={step:7d} | loss={loss.item():.4f} | ppl={ppl:.1f} | "
                f"lr={lr:.2e} | tokens={tokens_seen:,} | "
                f"elapsed={elapsed:.0f}s | gpu_mem={mem_gb:.1f}GB"
            )
            entry = {
                "step":             step,
                "loss":             round(loss.item(), 4),
                "ppl":              round(ppl, 2),
                "tokens_processed": tokens_seen,
                "wall_time_sec":    round(elapsed, 1),
                "gpu_memory_gb":    round(mem_gb, 2),
                "lr":               lr,
            }
            training_log.append(entry)

        # ── Checkpoint ────────────────────────────────────────────────────────
        if step % TRAIN_CONFIG["checkpoint_every"] == 0:
            save_checkpoint(model, optimizer, step, loss.item(), model_dir)
            # Flush log
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(training_log, f, indent=2)

    # ── Final save ────────────────────────────────────────────────────────────
    save_checkpoint(model, optimizer, step, loss.item(), model_dir)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(training_log, f, indent=2)
    log.info(f"[{lang}/{regime}] Training complete. {step:,} steps, "
             f"{tokens_seen:,} tokens.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Train language model.")
    parser.add_argument("--language", choices=["en", "ar", "tr"], required=True)
    parser.add_argument("--regime",   choices=["baseline", "morph"], required=True)
    parser.add_argument("--resume",   action="store_true",
                        help="Resume from latest checkpoint.")
    args = parser.parse_args()
    train(args.language, args.regime, args.resume)


if __name__ == "__main__":
    main()
