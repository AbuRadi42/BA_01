"""
eval_downstream.py
------------------
Downstream task evaluation (plan.md §9) + compute metrics (§7).

Tasks per language:
  English:  SST-2 (sentiment), SQuAD v1.1 (extractive QA)
  Arabic:   HARD (sentiment), ARCD (reading comprehension)
  Turkish:  TTC-3600 (topic classification), MLQA-tr (QA)

Method: frozen model + single linear probe on final hidden state.

Usage:
  python scripts/eval_downstream.py --language en --regime baseline
  python scripts/eval_downstream.py --language all --regime all

Saves to: logs/evaluation/{language}_{regime}_task_{task_name}.json
          logs/evaluation/{language}_{regime}_compute.json
"""

import argparse
import json
import logging
import os
import time
from typing import Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

import sys
sys.path.insert(0, os.path.dirname(__file__))
from train_lm import GPTModel, MODEL_CONFIG, TRAIN_CONFIG

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Task registry
# ---------------------------------------------------------------------------

TASK_REGISTRY = {
    "en": [
        {"name": "sentiment",      "type": "classification",
         "hf_args": ("sst2",),
         "text_col": "sentence",   "label_col": "label", "n_labels": 2},
        {"name": "qa",             "type": "qa",
         "hf_args": ("squad",),
         "context_col": "context", "question_col": "question",
         "answers_col": "answers"},
    ],
    "ar": [
        {"name": "sentiment",      "type": "classification",
         "hf_args": ("hard",),
         "text_col": "text",       "label_col": "label", "n_labels": 2},
        {"name": "qa",             "type": "qa",
         "hf_args": ("arcd",),
         "context_col": "context", "question_col": "question",
         "answers_col": "answers"},
    ],
    "tr": [
        {"name": "classification", "type": "classification",
         "hf_args": ("ttc3600",),
         "text_col": "text",       "label_col": "label", "n_labels": 6},
        {"name": "qa",             "type": "qa",
         "hf_args": ("mlqa", "mlqa.tr.tr"),
         "context_col": "context", "question_col": "question",
         "answers_col": "answers"},
    ],
}

# ---------------------------------------------------------------------------
# Tokenizer helpers
# ---------------------------------------------------------------------------

def load_tokenizer(lang: str, regime: str):
    """Returns a callable: text -> List[int]."""
    if regime == "morph":
        vocab_path = os.path.join("tokenizers", f"{lang}_morph", "vocab.json")
        with open(vocab_path, encoding="utf-8") as f:
            vocab = json.load(f)
        def tokenize(text: str) -> List[int]:
            return [vocab.get(t, vocab.get("<unk>", 1)) for t in text.split()]
        return tokenize
    else:
        import sentencepiece as spm
        sp = spm.SentencePieceProcessor()
        sp.load(os.path.join("tokenizers", f"{lang}_base", f"{lang}_base.model"))
        return lambda text: sp.encode(text, out_type=int)


# ---------------------------------------------------------------------------
# Probe datasets
# ---------------------------------------------------------------------------

class ClassificationDataset(Dataset):
    def __init__(self, texts: List[str], labels: List[int], tokenize, seq_len: int):
        self.labels    = labels
        self.seq_len   = seq_len
        self.encodings = [tokenize(t)[:seq_len] for t in texts]

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        ids = self.encodings[idx]
        ids = ids + [0] * (self.seq_len - len(ids))
        return torch.tensor(ids, dtype=torch.long), torch.tensor(self.labels[idx], dtype=torch.long)


class QADataset(Dataset):
    def __init__(self, contexts: List[str], questions: List[str],
                 answers: List[Dict], tokenize, seq_len: int):
        self.answers   = answers
        self.seq_len   = seq_len
        combined       = [f"{q} [SEP] {c}" for q, c in zip(questions, contexts)]
        self.encodings = [tokenize(t)[:seq_len] for t in combined]

    def __len__(self):
        return len(self.answers)

    def __getitem__(self, idx):
        ids = self.encodings[idx]
        ids = ids + [0] * (self.seq_len - len(ids))
        return torch.tensor(ids, dtype=torch.long), self.answers[idx]


# ---------------------------------------------------------------------------
# Linear probe
# ---------------------------------------------------------------------------

class LinearProbe(nn.Module):
    def __init__(self, hidden_size: int, n_labels: int):
        super().__init__()
        self.fc = nn.Linear(hidden_size, n_labels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc(x)


# ---------------------------------------------------------------------------
# Hidden state extraction
# ---------------------------------------------------------------------------

@torch.no_grad()
def extract_mean_hidden(model: GPTModel, input_ids: torch.Tensor,
                        device: torch.device) -> torch.Tensor:
    """Mean-pool non-pad token hidden states (pre-projection)."""
    input_ids = input_ids.to(device)
    feat_ids  = torch.zeros_like(input_ids)
    with torch.autocast(device_type=device.type, dtype=torch.bfloat16):
        _, _, hidden = model(input_ids, feat_ids, None, return_hidden=True)
    mask   = (input_ids != 0).unsqueeze(-1).float()
    pooled = (hidden.float() * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
    return pooled


# ---------------------------------------------------------------------------
# Classification task
# ---------------------------------------------------------------------------

def run_classification(model: GPTModel, task: Dict, lang: str, regime: str,
                       device: torch.device, tokenize) -> Dict:
    from datasets import load_dataset

    log.info(f"[{lang}/{regime}] Loading {task['hf_args']}")
    try:
        ds = load_dataset(*task["hf_args"])
    except Exception as e:
        log.warning(f"[{lang}/{regime}] Dataset load failed: {e}")
        return {"language": lang, "regime": regime, "task": task["name"], "error": str(e)}

    split = "validation" if "validation" in ds else "test"
    data  = ds[split]

    texts  = [str(row[task["text_col"]]) for row in data]
    labels = [int(row[task["label_col"]]) for row in data]

    seq_len = TRAIN_CONFIG["sequence_length"]
    dataset = ClassificationDataset(texts, labels, tokenize, seq_len)
    loader  = DataLoader(dataset, batch_size=32, shuffle=False)

    log.info(f"[{lang}/{regime}] Extracting hidden states ({len(dataset)} samples)...")
    all_h, all_y = [], []
    for ids, lbls in loader:
        all_h.append(extract_mean_hidden(model, ids, device).cpu())
        all_y.append(lbls)

    X = torch.cat(all_h)
    y = torch.cat(all_y)

    n_train = int(0.8 * len(X))
    X_tr, X_te = X[:n_train].to(device), X[n_train:].to(device)
    y_tr, y_te = y[:n_train].to(device), y[n_train:].to(device)

    probe     = LinearProbe(X.shape[-1], task["n_labels"]).to(device)
    optimizer = torch.optim.Adam(probe.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()

    probe.train()
    for _ in range(10):
        optimizer.zero_grad()
        criterion(probe(X_tr), y_tr).backward()
        optimizer.step()

    probe.eval()
    t0 = time.perf_counter()
    with torch.no_grad():
        preds = probe(X_te).argmax(dim=-1).cpu()
    latency_ms = (time.perf_counter() - t0) / max(len(X_te), 1) * 1000

    y_te_cpu = y_te.cpu()
    acc      = float((preds == y_te_cpu).float().mean())

    f1_scores = []
    for c in range(task["n_labels"]):
        tp = float(((preds == c) & (y_te_cpu == c)).sum())
        fp = float(((preds == c) & (y_te_cpu != c)).sum())
        fn = float(((preds != c) & (y_te_cpu == c)).sum())
        p  = tp / max(tp + fp, 1e-9)
        r  = tp / max(tp + fn, 1e-9)
        f1_scores.append(2 * p * r / max(p + r, 1e-9))
    f1 = float(np.mean(f1_scores))

    log.info(f"[{lang}/{regime}] {task['name']}: acc={acc:.4f} f1={f1:.4f}")
    return {
        "language": lang, "regime": regime, "task": task["name"],
        "accuracy": round(acc, 4), "f1": round(f1, 4),
        "inference_latency_ms": round(latency_ms, 3),
    }


# ---------------------------------------------------------------------------
# QA task
# ---------------------------------------------------------------------------

def run_qa(model: GPTModel, task: Dict, lang: str, regime: str,
           device: torch.device, tokenize) -> Dict:
    from datasets import load_dataset

    log.info(f"[{lang}/{regime}] Loading QA dataset {task['hf_args']}")
    try:
        ds = load_dataset(*task["hf_args"])
    except Exception as e:
        log.warning(f"[{lang}/{regime}] Dataset load failed: {e}")
        return {"language": lang, "regime": regime, "task": task["name"], "error": str(e)}

    split     = "validation" if "validation" in ds else "test"
    data      = ds[split]
    contexts  = [str(row[task["context_col"]])  for row in data]
    questions = [str(row[task["question_col"]]) for row in data]
    answers   = [row[task["answers_col"]]       for row in data]

    seq_len = TRAIN_CONFIG["sequence_length"]
    dataset = QADataset(contexts, questions, answers, tokenize, seq_len)

    def collate(batch):
        ids  = torch.stack([b[0] for b in batch])
        ans  = [b[1] for b in batch]
        return ids, ans

    loader = DataLoader(dataset, batch_size=16, shuffle=False, collate_fn=collate)

    hidden_size = MODEL_CONFIG["n_embd"]
    start_head  = nn.Linear(hidden_size, 1).to(device)
    end_head    = nn.Linear(hidden_size, 1).to(device)
    optimizer   = torch.optim.Adam(
        list(start_head.parameters()) + list(end_head.parameters()), lr=1e-3)

    # Collect hidden sequences
    all_hidden, all_answers = [], []
    for ids, ans in loader:
        ids      = ids.to(device)
        feat_ids = torch.zeros_like(ids)
        with torch.no_grad(), torch.autocast(device_type=device.type, dtype=torch.bfloat16):
            _, _, hidden = model(ids, feat_ids, None, return_hidden=True)
        all_hidden.append(hidden.float().cpu())
        all_answers.extend(ans)

    # Evaluate span predictions
    exact_matches, token_f1s, latencies = [], [], []

    for h, ans in zip(torch.cat(all_hidden), all_answers):
        h = h.unsqueeze(0).to(device)
        t0 = time.perf_counter()
        with torch.no_grad():
            s_idx = int(start_head(h).squeeze(-1).argmax(dim=-1).item())
            e_idx = int(end_head(h).squeeze(-1).argmax(dim=-1).item())
        latencies.append((time.perf_counter() - t0) * 1000)
        e_idx = max(e_idx, s_idx)

        gold_texts = ans.get("text", [])
        if not gold_texts:
            continue
        pred_len = e_idx - s_idx + 1
        gold_len = len(gold_texts[0].split())
        exact_matches.append(int(pred_len == gold_len))
        common = min(pred_len, gold_len)
        p = common / max(pred_len, 1)
        r = common / max(gold_len, 1)
        token_f1s.append(2 * p * r / max(p + r, 1e-9))

    em  = float(np.mean(exact_matches)) if exact_matches else None
    f1  = float(np.mean(token_f1s))     if token_f1s     else None
    lat = float(np.mean(latencies))     if latencies      else None

    log.info(f"[{lang}/{regime}] {task['name']}: EM={em} F1={f1}")
    return {
        "language": lang, "regime": regime, "task": task["name"],
        "exact_match": round(em, 4) if em is not None else None,
        "f1":          round(f1, 4) if f1 is not None else None,
        "inference_latency_ms": round(lat, 3) if lat is not None else None,
    }


# ---------------------------------------------------------------------------
# Compute metrics (plan.md §7)
# ---------------------------------------------------------------------------

@torch.no_grad()
def compute_and_save_compute_metrics(model: GPTModel, lang: str, regime: str,
                                     device: torch.device):
    seq_len  = TRAIN_CONFIG["sequence_length"]
    n_params = sum(p.numel() for p in model.parameters())
    flops_per_token = 6 * n_params  # standard 6N approximation

    dummy_ids  = torch.zeros(1, seq_len, dtype=torch.long, device=device)
    dummy_feat = torch.zeros_like(dummy_ids)

    for _ in range(3):  # warm-up
        with torch.autocast(device_type=device.type, dtype=torch.bfloat16):
            model(dummy_ids, dummy_feat, None)

    n_runs = 20
    t0 = time.perf_counter()
    for _ in range(n_runs):
        with torch.autocast(device_type=device.type, dtype=torch.bfloat16):
            model(dummy_ids, dummy_feat, None)
    latency_ms = (time.perf_counter() - t0) / n_runs * 1000

    # Attention weight stats — manually compute softmax attention (no flash attn)
    attn_weights_list: List[torch.Tensor] = []

    def _attn_hook(module, inp, out):
        # out is the projected output tensor; recompute attn weights from input
        x = inp[0]
        B, T, C = x.shape
        q, k, v = module.qkv(x).split(module.n_embd, dim=2)
        hd = module.head_dim
        q = q.view(B, T, module.n_head, hd).transpose(1, 2)
        k = k.view(B, T, module.n_head, hd).transpose(1, 2)
        att = (q @ k.transpose(-2, -1)) * (hd ** -0.5)
        att = att.masked_fill(module.mask[:, :, :T, :T] == 0, float("-inf"))
        att = torch.softmax(att.float(), dim=-1)
        attn_weights_list.append(att.detach().cpu())

    hooks = []
    for layer in model.blocks:
        hooks.append(layer.attn.register_forward_hook(_attn_hook))

    with torch.no_grad(), torch.autocast(device_type=device.type, dtype=torch.bfloat16):
        model(dummy_ids, dummy_feat, None)

    for h in hooks:
        h.remove()

    attn_gini = attn_entropy = None
    if attn_weights_list:
        w = torch.cat([a.reshape(-1) for a in attn_weights_list])
        w = w[w > 0]
        if len(w) > 0:
            w_sorted = w.sort().values
            n        = len(w_sorted)
            idx      = torch.arange(1, n + 1, dtype=torch.float)
            attn_gini    = float((2 * (idx * w_sorted).sum() / (n * w_sorted.sum()) - (n + 1) / n).item())
            attn_entropy = float(-(w * w.log()).sum().item())

    out_path = os.path.join("logs", "evaluation", f"{lang}_{regime}_compute.json")
    result   = {
        "language": lang, "regime": regime,
        "flops_per_token":      flops_per_token,
        "inference_latency_ms": round(latency_ms, 3),
        "attn_gini":            round(attn_gini, 4)    if attn_gini    is not None else None,
        "attn_entropy":         round(attn_entropy, 4) if attn_entropy is not None else None,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    log.info(f"[{lang}/{regime}] Compute metrics saved → {out_path}")


# ---------------------------------------------------------------------------
# Model loader
# ---------------------------------------------------------------------------

def load_model(lang: str, regime: str, device: torch.device) -> GPTModel:
    morph_mode = (regime == "morph")
    model_dir  = os.path.join("models", f"{lang}_{regime}")

    if not os.path.isdir(model_dir):
        raise FileNotFoundError(f"No model directory: {model_dir}")

    ckpts = sorted(
        [f for f in os.listdir(model_dir) if f.startswith("ckpt_step")],
        key=lambda x: int(x.split("step")[1].split(".")[0])
    )
    if not ckpts:
        raise FileNotFoundError(f"No checkpoints in {model_dir}")

    if morph_mode:
        with open(os.path.join("tokenizers", f"{lang}_morph", "vocab.json"), encoding="utf-8") as f:
            vocab_size = len(json.load(f))
        with open(os.path.join("tokenizers", f"{lang}_morph", "feature_bundles.json"), encoding="utf-8") as f:
            n_feat_bundles = len(json.load(f))
    else:
        import sentencepiece as spm
        sp = spm.SentencePieceProcessor()
        sp.load(os.path.join("tokenizers", f"{lang}_base", f"{lang}_base.model"))
        vocab_size, n_feat_bundles = sp.get_piece_size(), 1

    model = GPTModel(vocab_size, n_feat_bundles, MODEL_CONFIG, morph_mode).to(device)
    if device.type == "cuda":
        model = model.to(torch.bfloat16)
    ckpt = torch.load(os.path.join(model_dir, ckpts[-1]), map_location=device)
    model.load_state_dict(ckpt["model"])
    model.eval()
    return model


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def evaluate(lang: str, regime: str):
    device = (
        torch.device("cuda") if torch.cuda.is_available() else
        torch.device("mps")  if torch.backends.mps.is_available() else
        torch.device("cpu")
    )
    log.info(f"[{lang}/{regime}] Device: {device}")

    model    = load_model(lang, regime, device)
    tokenize = load_tokenizer(lang, regime)
    os.makedirs(os.path.join("logs", "evaluation"), exist_ok=True)

    compute_and_save_compute_metrics(model, lang, regime, device)

    for task in TASK_REGISTRY.get(lang, []):
        result = (run_classification if task["type"] == "classification" else run_qa)(
            model, task, lang, regime, device, tokenize)
        out_path = os.path.join("logs", "evaluation",
                                f"{lang}_{regime}_task_{task['name']}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        log.info(f"[{lang}/{regime}] Saved → {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Downstream task + compute evaluation.")
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
