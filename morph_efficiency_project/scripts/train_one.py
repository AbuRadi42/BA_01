"""
train_one.py — Programmatic trainer for a single (lang, regime, rung) run.

Wraps the existing mini_experiment/run_mini.py helpers (corpus download,
tokenizer, baseline/morph encoding, MiniGPT model) with a per-run
parameterized training loop and clean output directory semantics.

Used by scripts/run_scale_ladder.py to execute the scale ladder described
in MANUSCRIPT_PLAN.md §6.7.

Key properties
--------------
- Resumable: reads/writes checkpoint_latest.pt in the caller-provided
  out_dir; resume on restart from the last saved step.
- Logged: writes a JSONL training-step log to out_dir/log.jsonl, one
  line per logging interval.
- Caller-controlled output: no globals leaked; tokenizer and tokenized
  arrays are cached per language under mini_experiment/tokenizers and
  mini_experiment/data (same paths run_mini.py uses, shared across rungs).
- Parameterized model & training config: model_cfg and train_cfg dicts
  override run_mini's module-level defaults for the duration of the call.

Entry point:
    result = train_one_model(
        lang="en",
        regime="baseline",
        model_cfg={"n_layer": 2, "n_embd": 64, "n_head": 4, "ffn_dim": 256,
                   "seq_len": 128, "dropout": 0.0},
        train_cfg={"total_tokens": 5_000_000, "batch_size": 16,
                   "lr": 3e-4, "weight_decay": 0.01, "grad_clip": 1.0,
                   "warmup_steps": 200, "log_every": 100,
                   "checkpoint_every": 500},
        out_dir=Path("mini_experiment/results_ladder/en_baseline_rung1_..."),
        log_callback=lambda **ev: None,   # optional
    )
"""

from __future__ import annotations

import json
import math
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from mini_experiment import run_mini  # type: ignore  # noqa: E402


@contextmanager
def _override_cfgs(model_cfg: dict, train_cfg: dict):
    """Swap run_mini's module-level CFG and TRAIN dicts for this run."""
    saved_cfg = dict(run_mini.CFG)
    saved_train = dict(run_mini.TRAIN)
    run_mini.CFG.clear()
    run_mini.CFG.update(saved_cfg)   # start from defaults
    run_mini.CFG.update(model_cfg)   # apply overrides
    run_mini.TRAIN.clear()
    run_mini.TRAIN.update(saved_train)
    run_mini.TRAIN.update(train_cfg)
    try:
        yield
    finally:
        run_mini.CFG.clear()
        run_mini.CFG.update(saved_cfg)
        run_mini.TRAIN.clear()
        run_mini.TRAIN.update(saved_train)


def _jsonl_append(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _log(log_cb: Callable[..., None] | None, path: Path, event: str, **fields: Any) -> None:
    record = {"event": event, **fields}
    _jsonl_append(path, record)
    if log_cb is not None:
        try:
            log_cb(event=event, **fields)
        except Exception:
            pass  # never let logging crash training


def _prepare_data(lang: str, regime: str) -> dict:
    """Ensure corpus + tokenizer + tokenized arrays exist. Returns paths dict."""
    # Download corpus (skipped if already cached).
    run_mini.download_corpus(lang, run_mini.N_TRAIN, run_mini.N_VAL, run_mini.N_TEST)

    if regime == "baseline":
        sp = run_mini.train_or_load_tokenizer(lang)
        paths = run_mini.tokenize_baseline(lang, sp)
        vocab_size = sp.get_piece_size()
        n_feat_bundles = 1  # unused under baseline
        # tokenize_baseline returns {split: tok_path}; adapt to (tok, None) tuples
        paths = {split: (paths[split], None) for split in paths}
    else:
        paths, vocab_size, n_feat_bundles = run_mini.tokenize_morph(lang)

    return {"paths": paths, "vocab_size": vocab_size, "n_feat_bundles": n_feat_bundles}


def _build_optimizer(model, weight_decay: float, lr: float):
    import torch
    decay = [p for _, p in model.named_parameters() if p.requires_grad and p.dim() >= 2]
    nodecay = [p for _, p in model.named_parameters() if p.requires_grad and p.dim() < 2]
    return torch.optim.AdamW(
        [
            {"params": decay, "weight_decay": weight_decay},
            {"params": nodecay, "weight_decay": 0.0},
        ],
        lr=lr,
        betas=(0.9, 0.95),
    )


def _training_loop(
    model,
    tok_path: str,
    feat_path: str | None,
    train_cfg: dict,
    model_cfg: dict,
    out_dir: Path,
    log_path: Path,
    log_cb: Callable[..., None] | None,
):
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader

    ckpt_path = out_dir / "checkpoint_latest.pt"

    opt = _build_optimizer(model, train_cfg["weight_decay"], train_cfg["lr"])

    ds = run_mini.make_dataset(tok_path, feat_path)
    loader = DataLoader(ds, batch_size=train_cfg["batch_size"], shuffle=True,
                        num_workers=0, drop_last=True)

    tokens_per_step = train_cfg["batch_size"] * model_cfg["seq_len"]
    total_steps = train_cfg["total_tokens"] // tokens_per_step

    # Resume if checkpoint present.
    start_step = 0
    if ckpt_path.exists():
        ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        model.load_state_dict(ckpt["model"])
        opt.load_state_dict(ckpt["optimizer"])
        start_step = ckpt["step"]
        _log(log_cb, log_path, "resume", step=start_step, total_steps=total_steps)
    else:
        _log(log_cb, log_path, "begin", total_steps=total_steps,
             tokens_per_step=tokens_per_step)

    if start_step >= total_steps:
        _log(log_cb, log_path, "already_complete", step=start_step)
        return start_step

    model.train()
    step = start_step
    tokens_seen = start_step * tokens_per_step
    t0 = time.time()
    data_iter = iter(loader)
    last_loss = float("nan")

    while step < total_steps:
        try:
            x, f, y = next(data_iter)
        except StopIteration:
            data_iter = iter(loader)
            x, f, y = next(data_iter)

        lr = run_mini.get_lr(step, total_steps)
        for pg in opt.param_groups:
            pg["lr"] = lr

        opt.zero_grad(set_to_none=True)
        _, loss = model(x, f, y)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), train_cfg["grad_clip"])
        opt.step()

        step += 1
        tokens_seen += tokens_per_step
        last_loss = float(loss.item())

        if step % train_cfg["log_every"] == 0:
            ppl = math.exp(min(last_loss, 20))
            elapsed = time.time() - t0
            _log(log_cb, log_path, "step",
                 step=step, tokens=tokens_seen, loss=round(last_loss, 4),
                 ppl=round(ppl, 2), lr=round(lr, 8),
                 wall_time_sec=round(elapsed, 1))

        if step % train_cfg["checkpoint_every"] == 0:
            tmp = ckpt_path.with_suffix(".pt.tmp")
            torch.save({
                "model": model.state_dict(),
                "optimizer": opt.state_dict(),
                "step": step,
                "last_loss": last_loss,
            }, tmp)
            tmp.replace(ckpt_path)
            _log(log_cb, log_path, "checkpoint", step=step, loss=round(last_loss, 4))

    # final checkpoint
    tmp = ckpt_path.with_suffix(".pt.tmp")
    import torch as _torch
    _torch.save({
        "model": model.state_dict(),
        "optimizer": opt.state_dict(),
        "step": step,
        "last_loss": last_loss,
    }, tmp)
    tmp.replace(ckpt_path)
    _log(log_cb, log_path, "train_complete", step=step, loss=round(last_loss, 4),
         wall_time_sec=round(time.time() - t0, 1))
    return step


def _evaluate(model, tok_path: str, feat_path: str | None, batch_size: int = 32) -> dict:
    import torch
    from torch.utils.data import DataLoader

    ds = run_mini.make_dataset(tok_path, feat_path)
    loader = DataLoader(ds, batch_size=batch_size, shuffle=False, num_workers=0)

    model.eval()
    total_loss = 0.0
    total_tokens = 0
    with torch.no_grad():
        for x, f, y in loader:
            _, loss = model(x, f, y)
            n = int((y != 0).sum().item())
            total_loss += float(loss.item()) * n
            total_tokens += n

    avg_loss = total_loss / max(total_tokens, 1)
    return {
        "test_loss": round(avg_loss, 6),
        "test_ppl": round(math.exp(min(avg_loss, 20)), 4),
        "tokens_scored": total_tokens,
    }


def train_one_model(
    *,
    lang: str,
    regime: str,
    model_cfg: dict,
    train_cfg: dict,
    out_dir: Path,
    log_callback: Callable[..., None] | None = None,
) -> dict:
    """Train a single model and return its evaluation result as a dict."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "log.jsonl"

    if regime not in ("baseline", "morph"):
        raise ValueError(f"unknown regime: {regime!r}")

    with _override_cfgs(model_cfg, train_cfg):
        prep = _prepare_data(lang, regime)
        _log(log_callback, log_path, "data_ready",
             vocab_size=prep["vocab_size"], n_feat_bundles=prep["n_feat_bundles"])

        train_tok, train_feat = prep["paths"]["train"]
        test_tok, test_feat = prep["paths"]["test"]

        model = run_mini.build_model(
            vocab_size=prep["vocab_size"],
            n_feat_bundles=prep["n_feat_bundles"],
            morph_mode=(regime == "morph"),
        )
        n_params = sum(p.numel() for p in model.parameters())
        _log(log_callback, log_path, "model_built",
             n_params=n_params, morph_mode=(regime == "morph"))

        final_step = _training_loop(
            model=model,
            tok_path=train_tok,
            feat_path=train_feat,
            train_cfg=train_cfg,
            model_cfg=model_cfg,
            out_dir=out_dir,
            log_path=log_path,
            log_cb=log_callback,
        )

        eval_result = _evaluate(model, test_tok, test_feat)
        _log(log_callback, log_path, "eval_complete", **eval_result)

    return {
        "lang": lang,
        "regime": regime,
        "model_cfg": model_cfg,
        "train_cfg": train_cfg,
        "n_params": n_params,
        "vocab_size": prep["vocab_size"],
        "n_feat_bundles": prep["n_feat_bundles"],
        "final_step": final_step,
        **eval_result,
    }


if __name__ == "__main__":
    # Quick smoke-test when called directly.
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="en", choices=["en", "ar", "tr"])
    ap.add_argument("--regime", default="baseline", choices=["baseline", "morph"])
    ap.add_argument("--out-dir", type=Path, default=ROOT / "mini_experiment" / "results_ladder" / "smoke_test")
    args = ap.parse_args()

    smoke_model_cfg = {"n_layer": 2, "n_embd": 64, "n_head": 4, "ffn_dim": 256,
                       "seq_len": 128, "dropout": 0.0}
    smoke_train_cfg = {"total_tokens": 200_000, "batch_size": 16, "lr": 3e-4,
                       "weight_decay": 0.01, "grad_clip": 1.0, "warmup_steps": 50,
                       "log_every": 20, "checkpoint_every": 100}

    result = train_one_model(
        lang=args.lang, regime=args.regime,
        model_cfg=smoke_model_cfg, train_cfg=smoke_train_cfg,
        out_dir=args.out_dir,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
