"""Tests for the multi-stream MiniGPT architecture.

Covers Tier 1 #2 + Tier 2 #5 of the AWS-readiness roadmap.
Run: pytest mini_experiment/test_minigpt_multistream.py -v
"""
import os, sys
import pytest

# Make the mini_experiment package importable when run from repo root.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

torch = None
try:
    import torch as _torch
    torch = _torch
    HAS_TORCH = True
except Exception:
    HAS_TORCH = False

from run_mini import StreamConfig, make_minigpt  # noqa: E402

# Shared config knobs (match run_mini CFG defaults so the legacy code path is exercised too).
MODEL_DIM = 128
N_LAYER = 4
N_HEAD = 4
FFN_DIM = 512
SEQ_LEN = 128

# Analytical non-embedding (transformer blocks + pos_emb + final layernorm) param count
# for the config above. Computed once; assertions reuse it.
#   per block: qkv 128*384 + proj 128*128 + 2*LN(256) + ffn1 (128*512+512) + ffn2 (512*128+128)
#            = 49152 + 16384 + 512 + 66048 + 65664 = 197760
#   4 blocks = 791040
#   pos_emb  = SEQ_LEN * MODEL_DIM = 128 * 128 = 16384
#   ln_f     = 256
#   ---------------------------------
#   NON_EMB_PARAMS = 807680
NON_EMB_PARAMS = 4 * (49152 + 16384 + 512 + 66048 + 65664) + 128 * 128 + 256
assert NON_EMB_PARAMS == 807_680


def _mk(streams):
    return make_minigpt(streams, model_dim=MODEL_DIM, n_layer=N_LAYER,
                        n_head=N_HEAD, ffn_dim=FFN_DIM, seq_len=SEQ_LEN,
                        dropout=0.0)


@pytest.mark.skipif(not HAS_TORCH, reason="torch not installed")
def test_single_stream_baseline_param_count():
    """1-stream BPE baseline: 32k * 128 + non-embedding = 4,903,680."""
    streams = [StreamConfig("tok", 32_000, MODEL_DIM)]
    model = _mk(streams)
    expected_emb = 32_000 * MODEL_DIM
    expected_total = expected_emb + NON_EMB_PARAMS
    bd = model.parameter_breakdown()
    assert bd["embeddings_total"] == expected_emb
    assert bd["transformer_blocks"] == 4 * 197_760
    assert bd["head_extra"] == 0  # weight-tied
    assert bd["total"] == expected_total
    # Cross-check via direct param sum.
    assert sum(p.numel() for p in model.parameters()) == expected_total


@pytest.mark.skipif(not HAS_TORCH, reason="torch not installed")
def test_two_stream_en_morph_param_count():
    """2-stream EN morph: 32k surface + 29 bundles. +29*128 = 3,712 extra."""
    streams = [
        StreamConfig("tok",  32_000, MODEL_DIM),
        StreamConfig("feat",     29, MODEL_DIM),
    ]
    model = _mk(streams)
    baseline_total = 32_000 * MODEL_DIM + NON_EMB_PARAMS
    expected_total = baseline_total + 29 * MODEL_DIM
    bd = model.parameter_breakdown()
    assert bd["embeddings_per_stream"]["feat"] == 29 * MODEL_DIM
    assert bd["embeddings_total"] == (32_000 + 29) * MODEL_DIM
    assert bd["total"] == expected_total


@pytest.mark.skipif(not HAS_TORCH, reason="torch not installed")
def test_four_stream_ar_morph_param_count_and_block_parity():
    """4-stream AR morph: 32k + 1147 + 7142 + 185.

    Transformer block sizes MUST equal the baseline's (parameter parity
    everywhere except embeddings).
    """
    streams = [
        StreamConfig("tok",     32_000, MODEL_DIM),
        StreamConfig("root",     1_147, MODEL_DIM),
        StreamConfig("wazn",     7_142, MODEL_DIM),
        StreamConfig("radical",    185, MODEL_DIM),
    ]
    model = _mk(streams)
    baseline = _mk([StreamConfig("tok", 32_000, MODEL_DIM)])

    bd = model.parameter_breakdown()
    bd_base = baseline.parameter_breakdown()

    # Block parity.
    assert bd["transformer_blocks"] == bd_base["transformer_blocks"]
    assert bd["pos_embedding"] == bd_base["pos_embedding"]
    assert bd["final_layernorm"] == bd_base["final_layernorm"]

    # Embedding totals.
    extra_vocab = 1_147 + 7_142 + 185  # = 8474
    assert bd["embeddings_total"] == (32_000 + extra_vocab) * MODEL_DIM
    assert bd["total"] == bd_base["total"] + extra_vocab * MODEL_DIM


@pytest.mark.skipif(not HAS_TORCH, reason="torch not installed")
def test_forward_pass_shape():
    """Random integer streams, forward, output shape (B, T, V_primary)."""
    streams = [
        StreamConfig("tok",  500, MODEL_DIM),
        StreamConfig("feat",  29, MODEL_DIM),
    ]
    model = _mk(streams)
    model.eval()
    B, T = 2, 16
    stream_ids = {
        "tok":  torch.randint(0, 500, (B, T)),
        "feat": torch.randint(0,  29, (B, T)),
    }
    with torch.no_grad():
        logits, loss = model(stream_ids)
    assert logits.shape == (B, T, 500)
    assert loss is None


@pytest.mark.skipif(not HAS_TORCH, reason="torch not installed")
def test_backward_grads_flow_into_all_streams():
    """Loss, backward, and check every stream's embedding has nonzero grads."""
    streams = [
        StreamConfig("tok",  500, MODEL_DIM),
        StreamConfig("root",  64, MODEL_DIM),
        StreamConfig("wazn", 128, MODEL_DIM),
    ]
    model = _mk(streams)
    model.train()
    B, T = 2, 16
    stream_ids = {
        "tok":  torch.randint(1, 500, (B, T)),  # avoid pad id 0
        "root": torch.randint(1,  64, (B, T)),
        "wazn": torch.randint(1, 128, (B, T)),
    }
    targets = torch.randint(1, 500, (B, T))
    logits, loss = model(stream_ids, targets=targets)
    assert loss is not None
    assert torch.isfinite(loss)
    loss.backward()
    for sc in streams:
        grad = model.stream_emb[sc.name].weight.grad
        assert grad is not None, f"No grad for stream {sc.name}"
        assert torch.any(grad != 0), f"Zero gradient for stream {sc.name}"
