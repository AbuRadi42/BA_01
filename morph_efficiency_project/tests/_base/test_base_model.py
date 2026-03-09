"""
test_base_model.py
------------------
Tests for GPTModel — architecture contracts, forward pass shapes,
loss computation, weight tying, and LR schedule.
CPU-only; no GPU or corpus required.

Run: python -m pytest morph_efficiency_project/tests/_base/test_base_model.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import math
import pytest

torch = pytest.importorskip("torch", reason="PyTorch not available — skipping model tests")

from morph_efficiency_project.scripts.train_lm import (
    GPTModel, MODEL_CONFIG, TRAIN_CONFIG, get_lr,
)

# Small config for fast CPU tests
SMALL_CFG = {
    "n_layer":                  2,
    "n_embd":                  64,
    "n_head":                   4,
    "ffn_dim":                256,
    "max_position_embeddings": 32,
    "dropout":                0.0,  # deterministic
}
VOCAB  = 256
N_FEAT = 16
B, T   = 2, 16  # batch=2, seq_len=16

@pytest.fixture
def base_model():
    return GPTModel(VOCAB, N_FEAT, SMALL_CFG, morph_mode=False).eval()

@pytest.fixture
def morph_model():
    return GPTModel(VOCAB, N_FEAT, SMALL_CFG, morph_mode=True).eval()

def _batch(vocab=VOCAB, n_feat=N_FEAT):
    idx  = torch.randint(0, vocab,  (B, T))
    feat = torch.randint(0, n_feat, (B, T))
    tgt  = torch.randint(0, vocab,  (B, T))
    return idx, feat, tgt

# ── Output shapes ─────────────────────────────────────────────────────────────

def test_logits_shape_base(base_model):
    idx, feat, _ = _batch()
    logits, loss = base_model(idx, feat)
    assert logits.shape == (B, T, VOCAB)
    assert loss is None

def test_logits_shape_morph(morph_model):
    idx, feat, _ = _batch()
    logits, loss = morph_model(idx, feat)
    assert logits.shape == (B, T, VOCAB)

def test_loss_is_scalar(base_model):
    idx, feat, tgt = _batch()
    _, loss = base_model(idx, feat, tgt)
    assert loss is not None
    assert loss.shape == ()  # scalar

def test_loss_is_positive(base_model):
    idx, feat, tgt = _batch()
    _, loss = base_model(idx, feat, tgt)
    assert loss.item() > 0

def test_loss_finite(base_model):
    idx, feat, tgt = _batch()
    _, loss = base_model(idx, feat, tgt)
    assert math.isfinite(loss.item())

# ── return_hidden ─────────────────────────────────────────────────────────────

def test_return_hidden_shape(base_model):
    idx, feat, tgt = _batch()
    logits, loss, hidden = base_model(idx, feat, tgt, return_hidden=True)
    assert hidden.shape == (B, T, SMALL_CFG["n_embd"])

def test_return_hidden_false_gives_two_outputs(base_model):
    idx, feat, tgt = _batch()
    out = base_model(idx, feat, tgt, return_hidden=False)
    assert len(out) == 2

# ── Weight tying ──────────────────────────────────────────────────────────────

def test_weight_tying(base_model):
    """head.weight and tok_emb.weight must be the same tensor."""
    assert base_model.head.weight is base_model.tok_emb.weight

# ── Morph mode: feat_emb exists iff morph_mode=True ──────────────────────────

def test_base_model_has_no_feat_emb(base_model):
    assert not hasattr(base_model, "feat_emb")

def test_morph_model_has_feat_emb(morph_model):
    assert hasattr(morph_model, "feat_emb")

def test_morph_feat_emb_shape(morph_model):
    w = morph_model.feat_emb.weight
    assert w.shape == (N_FEAT, SMALL_CFG["n_embd"])

# ── Causal masking: future tokens must not affect past positions ──────────────

def test_causal_masking(base_model):
    """
    Perturbing token at position T-1 must not change logits at position 0.
    """
    idx, feat, _ = _batch()
    with torch.no_grad():
        logits_orig, _ = base_model(idx, feat)

    idx2 = idx.clone()
    idx2[:, -1] = (idx2[:, -1] + 1) % VOCAB  # change last token
    with torch.no_grad():
        logits_new, _ = base_model(idx2, feat)

    # Position 0 logits must be identical
    assert torch.allclose(logits_orig[:, 0, :], logits_new[:, 0, :]), (
        "Causal masking broken: position 0 changed when position T-1 was perturbed"
    )

# ── Parameter count sanity ────────────────────────────────────────────────────

def test_param_count_reasonable(base_model):
    n = sum(p.numel() for p in base_model.parameters())
    # Small config should be well under 1M params
    assert n < 1_000_000, f"Unexpectedly large model: {n:,} params"

def test_full_config_param_count():
    """125M-param model must be in [100M, 150M] range."""
    model = GPTModel(32_000, 1, MODEL_CONFIG, morph_mode=False)
    n = sum(p.numel() for p in model.parameters())
    assert 100_000_000 <= n <= 150_000_000, (
        f"Full model param count out of expected range: {n:,}"
    )

# ── LR schedule ───────────────────────────────────────────────────────────────

def test_lr_warmup_starts_near_zero():
    lr = get_lr(step=0, warmup=100, total_steps=1000, max_lr=3e-4)
    assert lr == 0.0

def test_lr_warmup_linear():
    """LR at step=warmup//2 should be ~half of max_lr."""
    lr = get_lr(step=50, warmup=100, total_steps=1000, max_lr=3e-4)
    assert abs(lr - 1.5e-4) < 1e-6

def test_lr_at_warmup_end_equals_max():
    lr = get_lr(step=100, warmup=100, total_steps=1000, max_lr=3e-4)
    assert abs(lr - 3e-4) < 1e-8

def test_lr_cosine_decay_after_warmup():
    """LR must decrease monotonically after warmup."""
    lrs = [get_lr(s, 100, 1000, 3e-4) for s in range(100, 1001, 50)]
    for i in range(len(lrs) - 1):
        assert lrs[i] >= lrs[i + 1], f"LR not monotonically decreasing at step {100+i*50}"

def test_lr_ends_near_zero():
    lr = get_lr(step=1000, warmup=100, total_steps=1000, max_lr=3e-4)
    assert lr < 1e-5

def test_lr_never_negative():
    for step in range(0, 1001, 10):
        lr = get_lr(step, 100, 1000, 3e-4)
        assert lr >= 0.0, f"Negative LR at step {step}: {lr}"

# ── Gradient flow ─────────────────────────────────────────────────────────────

def test_gradients_flow_to_all_params():
    """After one backward pass, every parameter must have a gradient."""
    model = GPTModel(VOCAB, N_FEAT, SMALL_CFG, morph_mode=False).train()
    idx, feat, tgt = _batch()
    _, loss = model(idx, feat, tgt)
    loss.backward()
    for name, p in model.named_parameters():
        if p.requires_grad:
            assert p.grad is not None, f"No gradient for {name}"
            assert not torch.isnan(p.grad).any(), f"NaN gradient for {name}"

# ── Determinism ───────────────────────────────────────────────────────────────

def test_deterministic_eval(base_model):
    """Same input → same output in eval mode (dropout=0)."""
    idx, feat, _ = _batch()
    with torch.no_grad():
        out1, _ = base_model(idx, feat)
        out2, _ = base_model(idx, feat)
    assert torch.equal(out1, out2)
