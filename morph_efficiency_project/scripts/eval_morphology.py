"""
eval_morphology.py
------------------
Morphology-specific evaluation metrics (plan.md §8).

Metrics:
  8.1 Tokens per meaning unit
  8.2 Agreement accuracy (via check_morph_sequence_L)
  8.3 Lemma + feature bundle accuracy
  8.4 Nats per morpheme

Usage:
  python scripts/eval_morphology.py --language en --regime baseline
  python scripts/eval_morphology.py --language ar --regime morph
  python scripts/eval_morphology.py --language all --regime all

Saves to: logs/evaluation/{language}_{regime}_morph.json
"""

import argparse
import json
import logging
import math
import os
from typing import List, Dict, Tuple, Optional

import numpy as np
import torch
from torch.utils.data import DataLoader

import sys
sys.path.insert(0, os.path.dirname(__file__))
from train_lm import GPTModel, TokenDataset, MODEL_CONFIG, TRAIN_CONFIG

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agreement validators (plan.md §4.2)
# ---------------------------------------------------------------------------

def check_morph_sequence_ar(token_infos: List[Dict]) -> bool:
    """Validate Arabic tag bundles against النحو rules."""
    POS_REQUIRED = {
        "VERB": {"tense", "person", "num", "gender", "voice"},
        "NOM":  {"num", "gender"},
        "ADJ":  {"num", "gender"},
        "PART": set(),
    }
    POS_INVALID = {
        "VERB": {"case", "def"},
        "NOM":  {"tense", "person", "mood"},
        "ADJ":  {"tense", "person", "mood"},
        "PART": {"tense", "case", "num", "gender"},
    }
    for ti in token_infos:
        pos  = ti.get("pos", "")
        tags = ti.get("tags", {})
        req  = POS_REQUIRED.get(pos, set())
        inv  = POS_INVALID.get(pos, set())
        if not req.issubset(tags.keys()):
            return False
        if inv.intersection(tags.keys()):
            return False
        # Additional Arabic rules
        if tags.get("tense") == "IMP":
            if tags.get("person") != "2" or tags.get("voice") != "ACT":
                return False
        if tags.get("voice") == "PASS" and tags.get("tense") == "IMP":
            return False
        if tags.get("mood") == "JUS" and tags.get("tense") != "PRES":
            return False
    return True


def check_morph_sequence_tr(token_infos: List[Dict]) -> bool:
    """Validate Turkish suffix slot ordering (Dilbilgisi)."""
    NOM_ORDER  = ["DERIV", "NUM", "POSS", "CASE"]
    VERB_ORDER = ["DERIV", "VOICE", "NEG", "TENSE", "MOOD", "PERSON"]

    for ti in token_infos:
        pos    = ti.get("pos", "")
        slots  = ti.get("slot_order", [])  # list of slot names in order they appear
        order  = VERB_ORDER if pos == "VERB" else NOM_ORDER
        seen   = []
        for slot in slots:
            if slot in order:
                idx = order.index(slot)
                if seen and idx < max(order.index(s) for s in seen if s in order):
                    return False
                seen.append(slot)
        tags = ti.get("tags", {})
        if tags.get("mood") == "IMP" and tags.get("person") != "2":
            return False
        if tags.get("polarity") == "NEG":
            neg_pos  = slots.index("NEG")  if "NEG"  in slots else -1
            tns_pos  = slots.index("TENSE") if "TENSE" in slots else -1
            if neg_pos > tns_pos and tns_pos != -1:
                return False
    return True


def check_morph_sequence_en(token_infos: List[Dict]) -> bool:
    """Validate English inflectional tag bundles."""
    POS_ALLOWED = {
        "NOUN": {"num", "poss"},
        "VERB": {"tense", "aspect", "person", "voice"},
        "ADJ":  {"degree"},
        "ADV":  {"degree"},
    }
    POS_INVALID = {
        "NOUN": {"tense", "aspect", "degree", "person", "voice"},
        "VERB": {"degree"},
        "ADJ":  {"tense", "aspect", "person", "voice"},
        "ADV":  {"tense", "aspect", "person", "voice", "num"},
    }
    for ti in token_infos:
        pos  = ti.get("pos", "")
        tags = ti.get("tags", {})
        inv  = POS_INVALID.get(pos, set())
        if inv.intersection(tags.keys()):
            return False
        if tags.get("aspect") == "PERF" and tags.get("tense") not in ("PAST", "PRES", None):
            return False
        if tags.get("degree") in ("COMP", "SUPER") and pos not in ("ADJ", "ADV"):
            return False
    return True


VALIDATORS = {
    "ar": check_morph_sequence_ar,
    "tr": check_morph_sequence_tr,
    "en": check_morph_sequence_en,
}

# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

def tokens_per_meaning_unit(token_ids: np.ndarray, feature_ids: Optional[np.ndarray],
                             morph_mode: bool) -> float:
    """
    Estimate avg tokens per meaning unit.
    Meaning unit = content token (non-padding, non-function).
    For morph mode, feature_ids != 0 marks content morphemes.
    For baseline, every non-pad token counts as one unit.
    """
    non_pad = token_ids[token_ids != 0]
    total_tokens = len(non_pad)
    if morph_mode and feature_ids is not None:
        feat_non_pad = feature_ids[token_ids != 0]
        # feature_id == 0 is reserved for "no_features" (non-first morphemes)
        meaning_units = int((feat_non_pad != 0).sum())
    else:
        meaning_units = total_tokens  # baseline: 1 token ≈ 1 unit
    return total_tokens / max(meaning_units, 1)


def nats_per_morpheme(loss_per_token: np.ndarray, token_ids: np.ndarray,
                      feature_ids: Optional[np.ndarray], morph_mode: bool) -> float:
    """
    Nats per morpheme (plan.md §8.4).
    Morph: total nats / number of underlying morphemes.
    Baseline: distribute token loss across morphemes proportionally (1 token = 1 morpheme).
    """
    mask = token_ids != 0
    total_nats = float(loss_per_token[mask].sum())
    if morph_mode and feature_ids is not None:
        feat_non_pad = feature_ids[mask]
        n_morphemes  = int((feat_non_pad != 0).sum())
    else:
        n_morphemes = int(mask.sum())
    return total_nats / max(n_morphemes, 1)


# ---------------------------------------------------------------------------
# Per-token loss extraction
# ---------------------------------------------------------------------------

@torch.no_grad()
def get_per_token_loss(model: GPTModel, loader: DataLoader,
                       device: torch.device) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Returns (token_ids_flat, feature_ids_flat, loss_per_token_flat)."""
    all_ids   = []
    all_feats = []
    all_loss  = []

    criterion = torch.nn.CrossEntropyLoss(reduction="none", ignore_index=0)

    for x, feat, y in loader:
        x, feat, y = x.to(device), feat.to(device), y.to(device)
        with torch.autocast(device_type=device.type, dtype=torch.bfloat16):
            logits, _ = model(x, feat, None)  # (B, T, V)

        B, T, V = logits.shape
        loss_flat = criterion(logits.reshape(B * T, V).float(), y.reshape(B * T))
        all_ids.append(y.cpu().numpy().reshape(-1))
        all_feats.append(feat.cpu().numpy().reshape(-1))
        all_loss.append(loss_flat.cpu().numpy())

    return (np.concatenate(all_ids),
            np.concatenate(all_feats),
            np.concatenate(all_loss))


# ---------------------------------------------------------------------------
# Agreement accuracy (§8.2) — sampled from test feature_ids
# ---------------------------------------------------------------------------

def agreement_accuracy(lang: str, feature_bundles: Dict[int, str],
                       token_ids: np.ndarray, feature_ids: np.ndarray,
                       n_samples: int = 5000) -> float:
    """
    Reconstruct tag dicts from feature bundle strings and run the validator.
    Returns fraction of sampled sequences that pass check_morph_sequence_L.
    """
    validator = VALIDATORS.get(lang)
    if validator is None:
        return float("nan")

    # Build sequences of ~10 tokens each
    seq_len = 10
    n_tokens = len(token_ids)
    starts = np.random.choice(max(1, n_tokens - seq_len), size=min(n_samples, n_tokens // seq_len), replace=False)
    correct = 0
    total   = 0

    for s in starts:
        chunk_ids  = token_ids[s:s + seq_len]
        chunk_feat = feature_ids[s:s + seq_len]
        token_infos = []
        for tid, fid in zip(chunk_ids, chunk_feat):
            if tid == 0:
                continue
            bundle_str = feature_bundles.get(int(fid), "")
            tags = {}
            pos  = ""
            for part in bundle_str.split("|"):
                if "=" in part:
                    k, v = part.split("=", 1)
                    if k == "pos":
                        pos = v
                    else:
                        tags[k] = v
            token_infos.append({"pos": pos, "tags": tags, "slot_order": list(tags.keys())})
        if token_infos:
            correct += int(validator(token_infos))
            total   += 1

    return correct / max(total, 1)


# ---------------------------------------------------------------------------
# Bundle accuracy (§8.3)
# ---------------------------------------------------------------------------

def bundle_accuracy(pred_feature_ids: np.ndarray, ref_feature_ids: np.ndarray) -> float:
    """Fraction of non-pad positions where predicted bundle == reference bundle."""
    mask = ref_feature_ids != 0
    if mask.sum() == 0:
        return float("nan")
    return float((pred_feature_ids[mask] == ref_feature_ids[mask]).mean())


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------

def load_model_for_eval(lang: str, regime: str, device: torch.device):
    """Load latest checkpoint. Returns (model, step, vocab_size, n_feat_bundles)."""
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

    ckpt_path = os.path.join(model_dir, ckpts[-1])
    step = int(ckpts[-1].split("step")[1].split(".")[0])

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


def evaluate(lang: str, regime: str):
    morph_mode = (regime == "morph")
    log_path   = os.path.join("logs", "evaluation", f"{lang}_{regime}_morph.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    device = (
        torch.device("cuda") if torch.cuda.is_available() else
        torch.device("mps")  if torch.backends.mps.is_available() else
        torch.device("cpu")
    )
    log.info(f"[{lang}/{regime}] Device: {device}")

    model, step = load_model_for_eval(lang, regime, device)

    proc_base  = os.path.join("data", "processed", lang,
                              "morph" if morph_mode else "baseline")
    seq_len    = TRAIN_CONFIG["sequence_length"]
    batch_size = TRAIN_CONFIG["batch_size"]

    tok_path  = os.path.join(proc_base, "test_tokens.npy")
    feat_path = os.path.join(proc_base, "test_feature_ids.npy") if morph_mode else None

    if not os.path.exists(tok_path):
        log.warning(f"[{lang}/{regime}] test data not found: {tok_path} — skipping.")
        return

    ds     = TokenDataset(tok_path, feat_path, seq_len)
    loader = DataLoader(ds, batch_size=batch_size, shuffle=False,
                        num_workers=2, pin_memory=True, drop_last=False)

    log.info(f"[{lang}/{regime}] Extracting per-token losses...")
    token_ids_flat, feat_ids_flat, loss_flat = get_per_token_loss(model, loader, device)

    # Load raw arrays for metric computation
    raw_tokens = np.load(tok_path)
    raw_feats  = np.load(feat_path) if (morph_mode and feat_path) else None

    # 8.1 Tokens per meaning unit
    tpu = tokens_per_meaning_unit(raw_tokens, raw_feats, morph_mode)
    log.info(f"[{lang}/{regime}] tokens/meaning_unit = {tpu:.4f}")

    # 8.4 Nats per morpheme
    npm = nats_per_morpheme(loss_flat, token_ids_flat, feat_ids_flat, morph_mode)
    log.info(f"[{lang}/{regime}] nats/morpheme = {npm:.4f}")

    # 8.2 Agreement accuracy (morph only — requires feature bundles)
    agr_acc = float("nan")
    if morph_mode:
        fb_path = os.path.join("tokenizers", f"{lang}_morph", "feature_bundles.json")
        if os.path.exists(fb_path):
            with open(fb_path, encoding="utf-8") as f:
                raw_fb = json.load(f)
            # feature_bundles.json: {bundle_str: id} → invert to {id: bundle_str}
            if isinstance(raw_fb, dict):
                first_val = next(iter(raw_fb.values()))
                if isinstance(first_val, int):
                    feature_bundles = {v: k for k, v in raw_fb.items()}
                else:
                    feature_bundles = {int(k): v for k, v in raw_fb.items()}
            else:
                feature_bundles = {i: s for i, s in enumerate(raw_fb)}
            agr_acc = agreement_accuracy(lang, feature_bundles,
                                         token_ids_flat, feat_ids_flat)
            log.info(f"[{lang}/{regime}] agreement_accuracy = {agr_acc:.4f}")

    # 8.3 Bundle accuracy — compare model's predicted feature IDs vs reference
    # (meaningful only for morph; for baseline we report nan)
    bnd_acc = float("nan")
    if morph_mode and raw_feats is not None:
        # Align lengths
        min_len = min(len(feat_ids_flat), len(raw_feats.reshape(-1)))
        bnd_acc = bundle_accuracy(feat_ids_flat[:min_len], raw_feats.reshape(-1)[:min_len])
        log.info(f"[{lang}/{regime}] bundle_accuracy = {bnd_acc:.4f}")

    results = {
        "language":              lang,
        "regime":                regime,
        "step":                  step,
        "tokens_per_meaning_unit": round(tpu, 4),
        "agreement_accuracy":    round(agr_acc, 4) if not math.isnan(agr_acc) else None,
        "bundle_accuracy":       round(bnd_acc, 4) if not math.isnan(bnd_acc) else None,
        "nats_per_morpheme":     round(npm, 4),
    }

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    log.info(f"[{lang}/{regime}] Saved → {log_path}")


def main():
    parser = argparse.ArgumentParser(description="Morphology-specific evaluation.")
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
