"""
train_model.py
==============
Trainer for one (language, regime) pair of the morph-efficiency study.

Loads the multi-stream MiniGPT (see mini_experiment.run_mini.make_minigpt),
trains it with AdamW + cosine LR schedule with linear warmup, logs eval loss
and perplexity, and saves checkpoints to ``output_dir/ckpt_step_<N>.pt``.

Stream layout per regime:
  - baseline (all langs): 1 stream  -> tok
  - morph EN, TR        : 2 streams -> tok, feat
  - morph AR            : 4 streams -> tok, feat, root, wazn
  - morph ZH            : 2 streams -> tok, radical

Tokenizer artefacts come from mini_experiment/tokenizers/ and the
already-encoded numpy streams from mini_experiment/data/, both written by
``tokenize_for_training.py``.

CLI example:
    python train_model.py --lang ar --regime morph --model-dim 128 --layers 4 \\
        --max-tokens 5_000_000 --batch-size 32 --seq-len 128 \\
        --eval-every 1000 --save-every 5000 \\
        --output-dir runs/ar_morph_phase1

For smoke tests (tiny budgets, tiny model), see the README.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# Locate repo root so we can import mini_experiment.run_mini.
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from mini_experiment.run_mini import StreamConfig, make_minigpt  # noqa: E402

_DATA_DIR = _REPO_ROOT / "mini_experiment" / "data"
_TOK_DIR = _REPO_ROOT / "mini_experiment" / "tokenizers"

# Canonical language order used in any per-language tables: ZH, EN, TR, AR.
_LANGS = ("zh", "en", "tr", "ar")
_REGIMES = ("baseline", "morph")


# ---------------------------------------------------------------------------
# Stream resolution
# ---------------------------------------------------------------------------

def _streams_for(lang: str, regime: str) -> List[str]:
    """Return ordered stream names. Primary stream is always first."""
    if regime == "baseline":
        return ["tok"]
    if regime == "morph":
        if lang == "ar":
            return ["tok", "feat", "root", "wazn"]
        if lang == "zh":
            return ["tok", "radical"]
        if lang in ("en", "tr"):
            return ["tok", "feat"]
    raise ValueError(f"Unsupported (lang={lang}, regime={regime})")


def _npy_path(lang: str, regime: str, stream: str, split: str) -> Path:
    """Map (lang, regime, stream, split) -> .npy path."""
    if regime == "baseline":
        return _DATA_DIR / f"{lang}_baseline_{split}.npy"
    # morph: primary 'tok' lives at <lang>_morph_<split>.npy; secondaries get
    # the stream name spliced in.
    if stream == "tok":
        return _DATA_DIR / f"{lang}_morph_{split}.npy"
    return _DATA_DIR / f"{lang}_morph_{stream}_{split}.npy"


def _vocab_path(lang: str, regime: str, stream: str) -> Path:
    if regime == "baseline":
        return _TOK_DIR / f"{lang}_baseline_vocab.json"
    if stream == "tok":
        return _TOK_DIR / f"{lang}_morph_vocab.json"
    return _TOK_DIR / f"{lang}_morph_{stream}_vocab.json"


def _vocab_size(lang: str, regime: str, stream: str, fallback_data: np.ndarray) -> int:
    """Vocab size from JSON if present, else max(id)+1 from the data."""
    p = _vocab_path(lang, regime, stream)
    if p.exists():
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        return len(d)
    return int(fallback_data.max()) + 1


def _load_streams(lang: str, regime: str, split: str) -> Tuple[Dict[str, np.ndarray], Dict[str, int]]:
    streams = _streams_for(lang, regime)
    arrs: Dict[str, np.ndarray] = {}
    vocabs: Dict[str, int] = {}
    for s in streams:
        arr = np.load(_npy_path(lang, regime, s, split)).astype(np.int64)
        arrs[s] = arr
        vocabs[s] = _vocab_size(lang, regime, s, arr)
    # All streams must align in length; truncate to shortest.
    n = min(len(a) for a in arrs.values())
    for s in arrs:
        arrs[s] = arrs[s][:n]
    return arrs, vocabs


# ---------------------------------------------------------------------------
# Sampler
# ---------------------------------------------------------------------------

class _StreamSampler:
    """Random-window sampler. For each batch element, draws an offset and
    returns (seq_len) windows from every stream plus next-token targets
    (primary stream shifted by +1)."""

    def __init__(self, arrs: Dict[str, np.ndarray], seq_len: int, primary: str,
                 rng: np.random.Generator):
        self.arrs = arrs
        self.seq_len = seq_len
        self.primary = primary
        self.rng = rng
        self.n = len(arrs[primary])
        if self.n < seq_len + 1:
            raise ValueError(
                f"Split too small for seq_len={seq_len}: have {self.n} tokens")

    def batch(self, bs: int):
        import torch
        T = self.seq_len
        offs = self.rng.integers(0, self.n - T - 1, size=bs)
        out = {}
        for name, a in self.arrs.items():
            stack = np.stack([a[o:o + T] for o in offs], axis=0)
            out[name] = torch.from_numpy(stack).long()
        tgt_stack = np.stack(
            [self.arrs[self.primary][o + 1:o + T + 1] for o in offs], axis=0)
        targets = torch.from_numpy(tgt_stack).long()
        return out, targets


# ---------------------------------------------------------------------------
# LR schedule
# ---------------------------------------------------------------------------

def _cosine_lr(step: int, warmup: int, total: int, peak: float, floor: float) -> float:
    if step < warmup:
        return peak * (step + 1) / max(1, warmup)
    if step >= total:
        return floor
    p = (step - warmup) / max(1, total - warmup)
    return floor + 0.5 * (peak - floor) * (1.0 + math.cos(math.pi * p))


# ---------------------------------------------------------------------------
# Eval
# ---------------------------------------------------------------------------

def _evaluate(model, sampler: _StreamSampler, batch_size: int, n_batches: int, device) -> Tuple[float, float]:
    import torch
    model.eval()
    losses = []
    with torch.no_grad():
        for _ in range(n_batches):
            streams, targets = sampler.batch(batch_size)
            streams = {k: v.to(device) for k, v in streams.items()}
            targets = targets.to(device)
            _, loss = model(streams, targets)
            if loss is not None:
                losses.append(float(loss))
    model.train()
    if not losses:
        return float("nan"), float("nan")
    mean = sum(losses) / len(losses)
    return mean, math.exp(min(mean, 20.0))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--lang", required=True, choices=_LANGS)
    p.add_argument("--regime", required=True, choices=_REGIMES)
    p.add_argument("--model-dim", type=int, default=128)
    p.add_argument("--layers", type=int, default=4)
    p.add_argument("--heads", type=int, default=4)
    p.add_argument("--ffn-dim", type=int, default=None,
                   help="Default 4*model_dim")
    p.add_argument("--dropout", type=float, default=0.0)
    p.add_argument("--max-tokens", type=lambda s: int(float(s.replace("_", ""))),
                   default=5_000_000)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--seq-len", type=int, default=128)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--lr-floor", type=float, default=3e-5)
    p.add_argument("--warmup-steps", type=int, default=100)
    p.add_argument("--weight-decay", type=float, default=0.1)
    p.add_argument("--grad-clip", type=float, default=1.0)
    p.add_argument("--eval-every", type=int, default=1000)
    p.add_argument("--eval-batches", type=int, default=20)
    p.add_argument("--save-every", type=int, default=5000)
    p.add_argument("--log-every", type=int, default=10)
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--resume", type=Path, default=None)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--device", default=None,
                   help="cuda | cpu | mps. Auto-detected if omitted.")
    return p.parse_args(argv)


def _pick_device(requested: Optional[str]):
    import torch
    if requested:
        return torch.device(requested)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def main(argv=None):
    args = _parse_args(argv)
    import torch

    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = args.output_dir / "metrics.jsonl"
    cfg_path = args.output_dir / "run_config.json"

    # ---- Load data + build stream configs --------------------------------
    print(f"[init] lang={args.lang} regime={args.regime}", flush=True)
    train_arrs, vocabs = _load_streams(args.lang, args.regime, "train")
    val_arrs, _vv = _load_streams(args.lang, args.regime, "val")
    streams = _streams_for(args.lang, args.regime)
    primary = streams[0]

    # Smoke-test guard: shrink seq_len if the val split is too short.
    n_val = len(val_arrs[primary])
    seq_len = args.seq_len
    if n_val < seq_len + 1:
        new_sl = max(8, n_val // 2)
        print(f"[warn] val split has only {n_val} tokens; "
              f"reducing seq_len {seq_len} -> {new_sl}", flush=True)
        seq_len = new_sl
    n_train = len(train_arrs[primary])
    if n_train < seq_len + 1:
        new_sl = max(8, n_train // 2)
        print(f"[warn] train split has only {n_train} tokens; "
              f"reducing seq_len {seq_len} -> {new_sl}", flush=True)
        seq_len = new_sl

    print(f"[init] streams={streams} vocabs={vocabs} "
          f"train_tok={n_train} val_tok={n_val} seq_len={seq_len}", flush=True)

    stream_cfgs = [StreamConfig(name=s, vocab_size=vocabs[s],
                                per_stream_dim=args.model_dim) for s in streams]

    # ---- Build model -----------------------------------------------------
    ffn = args.ffn_dim if args.ffn_dim else 4 * args.model_dim
    model = make_minigpt(stream_cfgs, model_dim=args.model_dim,
                         n_layer=args.layers, n_head=args.heads,
                         ffn_dim=ffn, seq_len=seq_len, dropout=args.dropout)
    device = _pick_device(args.device)
    model = model.to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"[init] device={device} params={n_params:,}", flush=True)

    # ---- Optimiser + sched ----------------------------------------------
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr,
                            betas=(0.9, 0.95), weight_decay=args.weight_decay)
    tokens_per_step = args.batch_size * seq_len
    total_steps = max(1, args.max_tokens // tokens_per_step)
    print(f"[init] total_steps={total_steps} tokens_per_step={tokens_per_step} "
          f"max_tokens={args.max_tokens}", flush=True)

    # ---- Resume ----------------------------------------------------------
    start_step = 0
    if args.resume is not None and args.resume.exists():
        ck = torch.load(args.resume, map_location=device)
        model.load_state_dict(ck["model"])
        opt.load_state_dict(ck["optim"])
        start_step = int(ck.get("step", 0))
        print(f"[resume] loaded {args.resume} at step={start_step}", flush=True)

    # ---- Persist run config ---------------------------------------------
    with open(cfg_path, "w", encoding="utf-8") as fh:
        json.dump({
            "lang": args.lang, "regime": args.regime, "streams": streams,
            "vocabs": vocabs, "model_dim": args.model_dim,
            "layers": args.layers, "heads": args.heads, "ffn_dim": ffn,
            "seq_len": seq_len, "batch_size": args.batch_size,
            "max_tokens": args.max_tokens, "total_steps": total_steps,
            "lr": args.lr, "lr_floor": args.lr_floor,
            "warmup_steps": args.warmup_steps,
            "weight_decay": args.weight_decay, "grad_clip": args.grad_clip,
            "seed": args.seed, "n_params": n_params,
            "train_tokens_available": n_train,
            "val_tokens_available": n_val,
        }, fh, indent=2)

    # ---- Samplers --------------------------------------------------------
    rng_train = np.random.default_rng(args.seed)
    rng_val = np.random.default_rng(args.seed + 1)
    train_sampler = _StreamSampler(train_arrs, seq_len, primary, rng_train)
    val_sampler = _StreamSampler(val_arrs, seq_len, primary, rng_val)

    # ---- Train loop ------------------------------------------------------
    model.train()
    t0 = time.time()
    ema_loss = None
    metrics_fh = open(metrics_path, "a", encoding="utf-8")
    last_ckpt_path = None
    try:
        for step in range(start_step, total_steps):
            lr = _cosine_lr(step, args.warmup_steps, total_steps,
                            args.lr, args.lr_floor)
            for g in opt.param_groups:
                g["lr"] = lr

            streams_b, targets = train_sampler.batch(args.batch_size)
            streams_b = {k: v.to(device) for k, v in streams_b.items()}
            targets = targets.to(device)

            _, loss = model(streams_b, targets)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
            opt.step()

            lv = float(loss)
            ema_loss = lv if ema_loss is None else 0.9 * ema_loss + 0.1 * lv

            if (step + 1) % args.log_every == 0 or step == start_step:
                el = time.time() - t0
                print(f"[step {step+1}/{total_steps}] loss={lv:.4f} "
                      f"ema={ema_loss:.4f} lr={lr:.2e} elapsed={el:.1f}s",
                      flush=True)

            if (step + 1) % args.eval_every == 0 or (step + 1) == total_steps:
                eval_loss, ppl = _evaluate(model, val_sampler,
                                           args.batch_size,
                                           args.eval_batches, device)
                rec = {"step": step + 1, "train_loss": lv,
                       "train_ema": ema_loss, "eval_loss": eval_loss,
                       "eval_ppl": ppl, "lr": lr,
                       "tokens_seen": (step + 1) * tokens_per_step}
                metrics_fh.write(json.dumps(rec) + "\n")
                metrics_fh.flush()
                print(f"[eval step {step+1}] eval_loss={eval_loss:.4f} "
                      f"ppl={ppl:.2f}", flush=True)

            if (step + 1) % args.save_every == 0 or (step + 1) == total_steps:
                ckpt_path = args.output_dir / f"ckpt_step_{step+1}.pt"
                torch.save({
                    "model": model.state_dict(),
                    "optim": opt.state_dict(),
                    "step": step + 1,
                    "stream_cfgs": [(s.name, s.vocab_size, s.per_stream_dim)
                                    for s in stream_cfgs],
                    "model_dim": args.model_dim, "layers": args.layers,
                    "heads": args.heads, "ffn_dim": ffn, "seq_len": seq_len,
                }, ckpt_path)
                last_ckpt_path = ckpt_path
                print(f"[ckpt] saved {ckpt_path}", flush=True)
    finally:
        metrics_fh.close()

    print(f"[done] total_steps={total_steps} elapsed={time.time()-t0:.1f}s "
          f"last_ckpt={last_ckpt_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
