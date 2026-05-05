"""
train_tier2_ar.py — Arabic Tier-2 morph training.

Self-contained trainer for the two-tier Arabic experiment described in
§6 and §7.4 of the manuscript. Distinct from train_one.py so the Tier-1
ladder in flight is not disturbed.

Architecture
------------
Tier 1 (baseline of this comparison):   x = tok_emb + feat_emb
Tier 2 (this script):                   x = tok_emb + feat_emb + root_emb

The three streams are summed at the input layer, identical in every other
respect to the Phase 1 MiniGPT.

Inputs (must pre-exist)
----------------------
    mini_experiment/data/ar_morph_{train,val,test}.npy
    mini_experiment/data/ar_morph_feat_{train,val,test}.npy
    mini_experiment/data/ar_morph_root_{train,val,test}.npy   (produced by
                                                              tokenize_tier2_ar.py)
    mini_experiment/tokenizers/ar_morph_vocab.json
    mini_experiment/tokenizers/ar_morph_bundles.json
    mini_experiment/tokenizers/ar_morph_root_vocab.json

Outputs
-------
    mini_experiment/results_ladder/ar_morph_tier2_rung<N>_.../  (same layout
                                                                as Tier-1 runs)

Usage
-----
    python morph_efficiency_project/scripts/train_tier2_ar.py --rung 1
    python morph_efficiency_project/scripts/train_tier2_ar.py --rung 2
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "mini_experiment" / "data"
TOK_DIR = ROOT / "mini_experiment" / "tokenizers"
LADDER_DIR = ROOT / "mini_experiment" / "results_ladder"


# Rung configurations must match run_scale_ladder.py.
RUNGS = {
    1: dict(params_target=250_000,  tokens= 5_000_000, n_layer=2, n_embd=64,  n_head=4, ffn_dim=256),
    2: dict(params_target=500_000,  tokens=10_000_000, n_layer=3, n_embd=96,  n_head=4, ffn_dim=384),
    3: dict(params_target=1_000_000,tokens=20_000_000, n_layer=4, n_embd=128, n_head=4, ffn_dim=512),
    4: dict(params_target=2_000_000,tokens=40_000_000, n_layer=4, n_embd=192, n_head=4, ffn_dim=768),
}

TRAIN = dict(batch_size=16, lr=3e-4, weight_decay=0.01, grad_clip=1.0,
             warmup_steps=200, log_every=100, checkpoint_every=500,
             seq_len=128, dropout=0.0)


# ── helpers ----------------------------------------------------------------

def _iso_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _log_jsonl(path: Path, **fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({**fields, "ts": _iso_now()}, ensure_ascii=False) + "\n")


def _write_json_atomic(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


# ── model + data -----------------------------------------------------------

def build_tier2_model(vocab_size: int, n_feat_bundles: int, root_vocab_size: int, cfg: dict):
    import torch
    import torch.nn as nn

    C = cfg["n_embd"]
    T = cfg["seq_len"]

    class CausalSA(nn.Module):
        def __init__(self):
            super().__init__()
            self.n_head = cfg["n_head"]
            self.hd = C // self.n_head
            self.qkv = nn.Linear(C, 3 * C, bias=False)
            self.proj = nn.Linear(C, C, bias=False)
            self.drop = nn.Dropout(cfg["dropout"])
            self.register_buffer("mask", torch.tril(torch.ones(T, T)).view(1, 1, T, T))

        def forward(self, x):
            B, t, _ = x.shape
            q, k, v = self.qkv(x).split(C, dim=2)
            q = q.view(B, t, self.n_head, self.hd).transpose(1, 2)
            k = k.view(B, t, self.n_head, self.hd).transpose(1, 2)
            v = v.view(B, t, self.n_head, self.hd).transpose(1, 2)
            y = torch.nn.functional.scaled_dot_product_attention(q, k, v, is_causal=True)
            y = y.transpose(1, 2).contiguous().view(B, t, C)
            return self.drop(self.proj(y))

    class Block(nn.Module):
        def __init__(self):
            super().__init__()
            self.ln1 = nn.LayerNorm(C)
            self.attn = CausalSA()
            self.ln2 = nn.LayerNorm(C)
            self.ffn = nn.Sequential(
                nn.Linear(C, cfg["ffn_dim"]), nn.GELU(),
                nn.Linear(cfg["ffn_dim"], C), nn.Dropout(cfg["dropout"]),
            )

        def forward(self, x):
            x = x + self.attn(self.ln1(x))
            x = x + self.ffn(self.ln2(x))
            return x

    class MiniGPTTier2(nn.Module):
        def __init__(self):
            super().__init__()
            self.tok_emb = nn.Embedding(vocab_size, C)
            self.pos_emb = nn.Embedding(T, C)
            self.feat_emb = nn.Embedding(n_feat_bundles, C)
            self.root_emb = nn.Embedding(root_vocab_size, C)
            self.drop = nn.Dropout(cfg["dropout"])
            self.blocks = nn.ModuleList([Block() for _ in range(cfg["n_layer"])])
            self.ln_f = nn.LayerNorm(C)
            self.head = nn.Linear(C, vocab_size, bias=False)
            self.head.weight = self.tok_emb.weight
            self.apply(self._init)

        def _init(self, m):
            if isinstance(m, (nn.Linear, nn.Embedding)):
                nn.init.normal_(m.weight, 0.0, 0.02)
                if hasattr(m, "bias") and m.bias is not None:
                    nn.init.zeros_(m.bias)

        def forward(self, idx, feat, root, targets=None):
            B, t = idx.shape
            pos = torch.arange(t, device=idx.device).unsqueeze(0)
            x = self.tok_emb(idx) + self.pos_emb(pos) + self.feat_emb(feat) + self.root_emb(root)
            x = self.drop(x)
            for blk in self.blocks:
                x = blk(x)
            x = self.ln_f(x)
            logits = self.head(x)
            loss = None
            if targets is not None:
                loss = nn.functional.cross_entropy(
                    logits.view(-1, logits.size(-1)), targets.view(-1), ignore_index=0)
            return logits, loss

    return MiniGPTTier2()


def make_tier2_dataset(tok_path: str, feat_path: str, root_path: str, seq_len: int):
    import torch
    from torch.utils.data import Dataset

    class DS(Dataset):
        def __init__(self):
            self.tok = np.load(tok_path, mmap_mode="r")
            self.feat = np.load(feat_path, mmap_mode="r")
            self.root = np.load(root_path, mmap_mode="r")
            self.n = (min(len(self.tok), len(self.feat), len(self.root)) - 1) // seq_len

        def __len__(self):
            return self.n

        def __getitem__(self, i):
            s = i * seq_len
            return (torch.tensor(self.tok[s:s + seq_len].astype(np.int64)),
                    torch.tensor(self.feat[s:s + seq_len].astype(np.int64)),
                    torch.tensor(self.root[s:s + seq_len].astype(np.int64)),
                    torch.tensor(self.tok[s + 1:s + seq_len + 1].astype(np.int64)))

    return DS()


# ── main -------------------------------------------------------------------

def get_lr(step, total_steps, warmup):
    if step < warmup:
        return TRAIN["lr"] * (step + 1) / warmup
    import math as _m
    progress = (step - warmup) / max(1, total_steps - warmup)
    return TRAIN["lr"] * 0.5 * (1 + _m.cos(_m.pi * progress))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rung", type=int, choices=[1, 2, 3, 4], default=1)
    args = ap.parse_args()

    # Ensure Tier-2 artefacts exist.
    root_vocab_path = TOK_DIR / "ar_morph_root_vocab.json"
    if not root_vocab_path.exists():
        from morph_efficiency_project.scripts import tokenize_tier2_ar
        tokenize_tier2_ar.main()
    root_vocab = json.loads(root_vocab_path.read_text(encoding="utf-8"))

    tok_vocab = json.loads((TOK_DIR / "ar_morph_vocab.json").read_text(encoding="utf-8"))
    bundles = json.loads((TOK_DIR / "ar_morph_bundles.json").read_text(encoding="utf-8"))

    rung = RUNGS[args.rung]
    cfg = {**TRAIN, "n_layer": rung["n_layer"], "n_embd": rung["n_embd"],
           "n_head": rung["n_head"], "ffn_dim": rung["ffn_dim"]}

    run_id = f"ar_morph_tier2_rung{args.rung}_{rung['params_target']}p_{rung['tokens']}t"
    out_dir = LADDER_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "log.jsonl"

    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader

    device = torch.device("cpu")

    _log_jsonl(log_path, event="start", rung=args.rung, cfg=cfg,
               vocab_size=len(tok_vocab), n_bundles=len(bundles),
               n_roots=len(root_vocab))

    model = build_tier2_model(
        vocab_size=len(tok_vocab),
        n_feat_bundles=len(bundles),
        root_vocab_size=len(root_vocab),
        cfg=cfg,
    ).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    _log_jsonl(log_path, event="model_built", n_params=n_params)

    opt = torch.optim.AdamW(
        [
            {"params": [p for n, p in model.named_parameters() if p.requires_grad and p.dim() >= 2],
             "weight_decay": TRAIN["weight_decay"]},
            {"params": [p for n, p in model.named_parameters() if p.requires_grad and p.dim() < 2],
             "weight_decay": 0.0},
        ],
        lr=TRAIN["lr"], betas=(0.9, 0.95),
    )

    ds = make_tier2_dataset(
        str(DATA_DIR / "ar_morph_train.npy"),
        str(DATA_DIR / "ar_morph_feat_train.npy"),
        str(DATA_DIR / "ar_morph_root_train.npy"),
        cfg["seq_len"],
    )
    loader = DataLoader(ds, batch_size=TRAIN["batch_size"], shuffle=True,
                        num_workers=0, drop_last=True)

    tokens_per_step = TRAIN["batch_size"] * cfg["seq_len"]
    total_steps = rung["tokens"] // tokens_per_step
    _log_jsonl(log_path, event="begin", total_steps=total_steps,
               tokens_per_step=tokens_per_step)

    # Resume if checkpoint present.
    ckpt_path = out_dir / "checkpoint_latest.pt"
    start_step = 0
    if ckpt_path.exists():
        ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        model.load_state_dict(ckpt["model"])
        opt.load_state_dict(ckpt["optimizer"])
        start_step = ckpt["step"]
        _log_jsonl(log_path, event="resume", step=start_step)

    model.train()
    step = start_step
    tokens_seen = start_step * tokens_per_step
    t0 = time.time()
    data_iter = iter(loader)
    last_loss = float("nan")

    while step < total_steps:
        try:
            x, f, r, y = next(data_iter)
        except StopIteration:
            data_iter = iter(loader)
            x, f, r, y = next(data_iter)

        lr = get_lr(step, total_steps, TRAIN["warmup_steps"])
        for pg in opt.param_groups:
            pg["lr"] = lr

        opt.zero_grad(set_to_none=True)
        _, loss = model(x, f, r, y)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), TRAIN["grad_clip"])
        opt.step()

        step += 1
        tokens_seen += tokens_per_step
        last_loss = float(loss.item())

        if step % TRAIN["log_every"] == 0:
            ppl = math.exp(min(last_loss, 20))
            _log_jsonl(log_path, event="step", step=step, tokens=tokens_seen,
                       loss=round(last_loss, 4), ppl=round(ppl, 2),
                       lr=round(lr, 8), wall_time_sec=round(time.time() - t0, 1))

        if step % TRAIN["checkpoint_every"] == 0:
            tmp = ckpt_path.with_suffix(".pt.tmp")
            torch.save({"model": model.state_dict(), "optimizer": opt.state_dict(),
                        "step": step, "last_loss": last_loss}, tmp)
            tmp.replace(ckpt_path)

    # Evaluate on test.
    model.eval()
    test_ds = make_tier2_dataset(
        str(DATA_DIR / "ar_morph_test.npy"),
        str(DATA_DIR / "ar_morph_feat_test.npy"),
        str(DATA_DIR / "ar_morph_root_test.npy"),
        cfg["seq_len"],
    )
    test_loader = DataLoader(test_ds, batch_size=32, shuffle=False, num_workers=0)
    total_loss = 0.0
    total_tokens = 0
    with torch.no_grad():
        for x, f, r, y in test_loader:
            _, loss = model(x, f, r, y)
            n = int((y != 0).sum().item())
            total_loss += float(loss.item()) * n
            total_tokens += n

    avg_loss = total_loss / max(total_tokens, 1)
    result = {
        "lang": "ar",
        "regime": "morph_tier2",
        "run_id": run_id,
        "rung": args.rung,
        "n_params": n_params,
        "vocab_size": len(tok_vocab),
        "n_feat_bundles": len(bundles),
        "n_roots": len(root_vocab),
        "final_step": step,
        "test_loss": round(avg_loss, 6),
        "test_ppl": round(math.exp(min(avg_loss, 20)), 4),
        "tokens_scored": total_tokens,
        "elapsed_s": round(time.time() - t0, 1),
    }
    _write_json_atomic(out_dir / "result.json", result)
    _log_jsonl(log_path, event="complete", **{k: v for k, v in result.items()
                                              if k not in ("run_id", "regime")})
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
