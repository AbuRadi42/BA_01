"""
test_base_dataset.py
--------------------
Tests for TokenDataset — the memory-mapped dataset used by train_lm.py.
Uses synthetic in-memory .npy arrays; no real corpus needed.

Run: python -m pytest morph_efficiency_project/tests/_base/test_base_dataset.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import tempfile
import numpy as np
import pytest

torch = pytest.importorskip("torch", reason="PyTorch not available — skipping dataset tests")

from morph_efficiency_project.scripts.train_lm import TokenDataset

# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_npy(arr: np.ndarray) -> str:
    """Write array to a temp .npy file and return the path."""
    f = tempfile.NamedTemporaryFile(suffix=".npy", delete=False)
    np.save(f.name, arr)
    f.close()
    return f.name

@pytest.fixture
def token_file():
    """100 tokens, IDs 0–99."""
    arr = np.arange(100, dtype=np.int32)
    path = _make_npy(arr)
    yield path
    os.unlink(path)

@pytest.fixture
def feat_file():
    """100 feature IDs, all zeros."""
    arr = np.zeros(100, dtype=np.int32)
    path = _make_npy(arr)
    yield path
    os.unlink(path)

# ── Length ────────────────────────────────────────────────────────────────────

def test_dataset_length_no_feat(token_file):
    """len = (N-1) // seq_len."""
    ds = TokenDataset(token_file, None, seq_len=10)
    assert len(ds) == (100 - 1) // 10  # == 9

def test_dataset_length_with_feat(token_file, feat_file):
    ds = TokenDataset(token_file, feat_file, seq_len=10)
    assert len(ds) == 9

def test_dataset_length_seq_len_1(token_file):
    ds = TokenDataset(token_file, None, seq_len=1)
    assert len(ds) == 99

def test_dataset_length_seq_len_equals_n(token_file):
    """seq_len == N → only 1 item (needs N+1 tokens, but we have N)."""
    ds = TokenDataset(token_file, None, seq_len=100)
    assert len(ds) == 0  # (100-1)//100 == 0

# ── Item shapes ───────────────────────────────────────────────────────────────

def test_item_shapes_no_feat(token_file):
    ds = TokenDataset(token_file, None, seq_len=10)
    x, f, y = ds[0]
    assert x.shape == (10,)
    assert f.shape == (10,)
    assert y.shape == (10,)

def test_item_shapes_with_feat(token_file, feat_file):
    ds = TokenDataset(token_file, feat_file, seq_len=10)
    x, f, y = ds[0]
    assert x.shape == (10,)
    assert f.shape == (10,)
    assert y.shape == (10,)

# ── Shift-by-one (causal LM contract) ────────────────────────────────────────

def test_y_is_x_shifted_by_one(token_file):
    """y[i] must equal x[i+1] — the core causal LM invariant."""
    ds = TokenDataset(token_file, None, seq_len=10)
    x, _, y = ds[0]
    # x = tokens[0:10], y = tokens[1:11]
    assert torch.equal(y[:-1], x[1:]), "y is not x shifted by 1"

def test_shift_holds_for_all_items(token_file):
    ds = TokenDataset(token_file, None, seq_len=5)
    for i in range(len(ds)):
        x, _, y = ds[i]
        assert torch.equal(y[:-1], x[1:]), f"Shift invariant broken at item {i}"

# ── No-feature fallback ───────────────────────────────────────────────────────

def test_no_feat_returns_zeros(token_file):
    """When feat_path=None, feature tensor must be all zeros."""
    ds = TokenDataset(token_file, None, seq_len=10)
    _, f, _ = ds[0]
    assert f.sum().item() == 0

# ── Dtype ─────────────────────────────────────────────────────────────────────

def test_item_dtype_is_long(token_file):
    """Tokens must be int64 (torch.long) for embedding lookup."""
    ds = TokenDataset(token_file, None, seq_len=10)
    x, f, y = ds[0]
    assert x.dtype == torch.int64
    assert y.dtype == torch.int64

# ── Boundary items ────────────────────────────────────────────────────────────

def test_first_item_values(token_file):
    """First item: x=[0..9], y=[1..10]."""
    ds = TokenDataset(token_file, None, seq_len=10)
    x, _, y = ds[0]
    assert x[0].item() == 0
    assert y[0].item() == 1
    assert x[-1].item() == 9
    assert y[-1].item() == 10

def test_last_item_values(token_file):
    """Last item must not go out of bounds."""
    ds = TokenDataset(token_file, None, seq_len=10)
    last = len(ds) - 1
    x, _, y = ds[last]
    assert x.shape == (10,)
    assert y.shape == (10,)
