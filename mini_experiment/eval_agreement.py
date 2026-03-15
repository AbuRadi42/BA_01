"""
eval_agreement.py — Measure Metric 4: Bundle Agreement Accuracy
================================================================
For each morph model, runs a forward pass on the test set.
At each position, the predicted next token's bundle tag is compared
to the ground-truth bundle ID. Accuracy = fraction of positions where
they match.

This does NOT require retraining — it uses the existing checkpoints.

Usage:
    python mini_experiment/eval_agreement.py
"""

import os, sys, json, math
import numpy as np

LANGS = ["en", "ar", "tr"]

BASE = os.path.dirname(__file__)
DATA_DIR    = os.path.join(BASE, "data")
MODELS_DIR  = os.path.join(BASE, "models")
TOK_DIR     = os.path.join(BASE, "tokenizers")
RESULTS_DIR = os.path.join(BASE, "results")

# ── Replicate model architecture from run_mini.py ────────────────────────────

CFG = {
    "n_layer": 4, "n_embd": 128, "n_head": 4,
    "ffn_dim": 512, "seq_len": 128, "dropout": 0.0,
}

def build_model(vocab_size, n_feat_bundles, morph_mode):
    import torch
    import torch.nn as nn
    C = CFG["n_embd"]
    T = CFG["seq_len"]

    class CausalSA(nn.Module):
        def __init__(self):
            super().__init__()
            self.n_head = CFG["n_head"]
            self.hd = C // self.n_head
            self.qkv  = nn.Linear(C, 3*C, bias=False)
            self.proj = nn.Linear(C, C, bias=False)
            self.drop = nn.Dropout(0.0)
            self.register_buffer("mask", torch.tril(torch.ones(T,T)).view(1,1,T,T))
        def forward(self, x):
            B,t,_ = x.shape
            q,k,v = self.qkv(x).split(C, dim=2)
            q = q.view(B,t,self.n_head,self.hd).transpose(1,2)
            k = k.view(B,t,self.n_head,self.hd).transpose(1,2)
            v = v.view(B,t,self.n_head,self.hd).transpose(1,2)
            if hasattr(torch.nn.functional, "scaled_dot_product_attention"):
                y = torch.nn.functional.scaled_dot_product_attention(q,k,v,is_causal=True)
            else:
                att = (q @ k.transpose(-2,-1)) * (self.hd**-0.5)
                att = att.masked_fill(self.mask[:,:,:t,:t]==0, float("-inf"))
                att = torch.softmax(att,-1)
                y   = att @ v
            y = y.transpose(1,2).contiguous().view(B,t,C)
            return self.drop(self.proj(y))

    class Block(nn.Module):
        def __init__(self):
            super().__init__()
            self.ln1 = nn.LayerNorm(C); self.attn = CausalSA()
            self.ln2 = nn.LayerNorm(C)
            self.ffn = nn.Sequential(nn.Linear(C,CFG["ffn_dim"]),nn.GELU(),
                                     nn.Linear(CFG["ffn_dim"],C),nn.Dropout(0.0))
        def forward(self, x):
            x = x + self.attn(self.ln1(x))
            x = x + self.ffn(self.ln2(x))
            return x

    class MiniGPT(nn.Module):
        def __init__(self):
            super().__init__()
            self.morph_mode = morph_mode
            self.tok_emb  = nn.Embedding(vocab_size, C)
            self.pos_emb  = nn.Embedding(T, C)
            if morph_mode:
                self.feat_emb = nn.Embedding(n_feat_bundles, C)
            self.drop   = nn.Dropout(0.0)
            self.blocks = nn.ModuleList([Block() for _ in range(CFG["n_layer"])])
            self.ln_f   = nn.LayerNorm(C)
            self.head   = nn.Linear(C, vocab_size, bias=False)
            self.head.weight = self.tok_emb.weight
            self.apply(self._init)
        def _init(self, m):
            if isinstance(m, (nn.Linear, nn.Embedding)):
                nn.init.normal_(m.weight, 0.0, 0.02)
                if hasattr(m, "bias") and m.bias is not None:
                    nn.init.zeros_(m.bias)
        def forward(self, idx, feat):
            B,t = idx.shape
            pos = torch.arange(t, device=idx.device).unsqueeze(0)
            x   = self.tok_emb(idx) + self.pos_emb(pos)
            if self.morph_mode:
                x = x + self.feat_emb(feat)
            x = self.drop(x)
            for blk in self.blocks: x = blk(x)
            x = self.ln_f(x)
            return self.head(x)  # (B, T, vocab_size)

    return MiniGPT()


def eval_bundle_accuracy(lang):
    import torch
    from torch.utils.data import DataLoader, Dataset

    print(f"\n[{lang}] Computing bundle accuracy...")

    # Load vocab and bundle mappings
    vocab_path   = os.path.join(TOK_DIR, f"{lang}_morph_vocab.json")
    bundles_path = os.path.join(TOK_DIR, f"{lang}_morph_bundles.json")

    with open(vocab_path)   as f: token2id  = json.load(f)
    with open(bundles_path) as f: bundle2id = json.load(f)

    # Build reverse map: token_id -> bundle_id
    # token surface form is "root+TAG", so we extract the tag part
    id2bundle = {}
    for surface, tid in token2id.items():
        if "+" in surface:
            tag = surface.split("+", 1)[1]
        else:
            tag = "ROOT"
        bid = bundle2id.get(tag, 0)
        id2bundle[tid] = bid

    # Special tokens map to bundle 0 (O)
    for special_id in [0, 1, 2, 3]:
        id2bundle[special_id] = 0

    vocab_size   = len(token2id)
    n_bundles    = len(bundle2id)

    # Load checkpoint
    model_path = os.path.join(MODELS_DIR, f"{lang}_morph.pt")
    ckpt = torch.load(model_path, map_location="cpu", weights_only=False)
    model = build_model(vocab_size, n_bundles, morph_mode=True)
    model.load_state_dict(ckpt["model"])
    model.eval()

    # Load test arrays
    tok_path  = os.path.join(DATA_DIR, f"{lang}_morph_test.npy")
    feat_path = os.path.join(DATA_DIR, f"{lang}_morph_feat_test.npy")
    toks  = np.load(tok_path,  mmap_mode="r")
    feats = np.load(feat_path, mmap_mode="r")

    # Build id2bundle as a numpy array for fast lookup
    max_id = max(id2bundle.keys()) + 1
    id2bundle_arr = np.zeros(max_id, dtype=np.int32)
    for tid, bid in id2bundle.items():
        if tid < max_id:
            id2bundle_arr[tid] = bid

    class DS(Dataset):
        def __init__(self):
            self.n = (len(toks) - 1) // CFG["seq_len"]
        def __len__(self): return self.n
        def __getitem__(self, i):
            s = i * CFG["seq_len"]
            e = s + CFG["seq_len"]
            x = torch.from_numpy(toks[s:e].astype(np.int64))
            f = torch.from_numpy(feats[s:e].astype(np.int64))
            y = torch.from_numpy(toks[s+1:e+1].astype(np.int64))   # target tokens
            fy = torch.from_numpy(feats[s+1:e+1].astype(np.int64)) # target bundles
            return x, f, y, fy

    loader = DataLoader(DS(), batch_size=32, shuffle=False, num_workers=0)

    correct = 0; total = 0
    with torch.no_grad():
        for x, f, y_tok, y_feat in loader:
            logits = model(x, f)                          # (B, T, V)
            pred_tok = logits.argmax(dim=-1)              # (B, T) — predicted next token IDs

            # Map predicted token IDs to bundle IDs
            pred_np = pred_tok.numpy().flatten()
            pred_np = np.clip(pred_np, 0, max_id - 1)
            pred_bundles = id2bundle_arr[pred_np]         # predicted bundle IDs

            gt_bundles = y_feat.numpy().flatten()         # ground truth bundle IDs

            # Only count non-padding positions (ignore pad=0 targets)
            mask = (y_tok.numpy().flatten() != 0)
            correct += int((pred_bundles[mask] == gt_bundles[mask]).sum())
            total   += int(mask.sum())

    accuracy = correct / max(total, 1)
    print(f"[{lang}] bundle_accuracy = {accuracy:.4f}  ({correct}/{total})")
    return accuracy


def main():
    try:
        import torch
    except ImportError:
        print("ERROR: PyTorch not installed.")
        sys.exit(1)

    results = {}
    for lang in LANGS:
        acc = eval_bundle_accuracy(lang)
        results[lang] = acc

        # Update the per-model eval JSON
        eval_path = os.path.join(RESULTS_DIR, f"{lang}_morph_eval.json")
        with open(eval_path) as f:
            data = json.load(f)
        data["bundle_accuracy"] = round(acc, 4)
        with open(eval_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[{lang}] Updated {eval_path}")

    # Update mini_summary.json
    summary_path = os.path.join(RESULTS_DIR, "mini_summary.json")
    with open(summary_path) as f:
        summary = json.load(f)

    for lang in LANGS:
        if lang in summary.get("by_lang", {}):
            summary["by_lang"][lang]["bundle_accuracy"] = round(results[lang], 4)

    # Also update results list entries
    for r in summary.get("results", []):
        if r["regime"] == "morph" and r["language"] in results:
            r["bundle_accuracy"] = round(results[r["language"]], 4)

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nUpdated {summary_path}")

    print("\n=== Bundle Accuracy Summary ===")
    for lang, acc in results.items():
        print(f"  {lang}: {acc:.2%}")


if __name__ == "__main__":
    main()
