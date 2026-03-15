"""
run_mini.py — Mini morphological efficiency experiment
======================================================
Trains 6 tiny GPT models (EN/AR/TR × baseline/morph) on ~5M tokens each.
Runs entirely on CPU in ~30–60 min. No raw data needed — downloads on the fly.

Usage:
    pip install torch sentencepiece datasets numpy
    python mini_experiment/run_mini.py

Outputs:
    mini_experiment/results/  — eval JSON per model
    mini_experiment/logs/     — training timeseries JSONL per model
    mini_experiment/models/   — final checkpoints
"""

import os, sys, json, math, time, logging, argparse
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

# Chinchilla-optimal: for a 2M-param model, ~40M tokens is optimal.
# We use 5M to keep wall time under 30 min on CPU — still a valid pilot.
CFG = {
    "n_layer":    4,
    "n_embd":   128,
    "n_head":     4,
    "ffn_dim":  512,
    "seq_len":  128,
    "dropout":  0.0,   # no dropout at this scale — too few params
}

TRAIN = {
    "total_tokens":    5_000_000,
    "batch_size":         16,
    "lr":              3e-4,
    "weight_decay":    0.01,
    "grad_clip":        1.0,
    "warmup_steps":     200,
    "log_every":        100,
    "checkpoint_every": 500,
}

LANGS = ["en", "ar", "tr"]
# Sentences to download per language (train/val/test)
N_TRAIN = 80_000
N_VAL   =  5_000
N_TEST  =  5_000

OUT = os.path.join(os.path.dirname(__file__))
RESULTS_DIR  = os.path.join(OUT, "results")
LOGS_DIR     = os.path.join(OUT, "logs")
MODELS_DIR   = os.path.join(OUT, "models")
DATA_DIR     = os.path.join(OUT, "data")
TOK_DIR      = os.path.join(OUT, "tokenizers")

for d in [RESULTS_DIR, LOGS_DIR, MODELS_DIR, DATA_DIR, TOK_DIR]:
    os.makedirs(d, exist_ok=True)

# ── Step 1: Download tiny corpora ─────────────────────────────────────────────

# wikimedia/wikipedia uses the new datasets API (no legacy scripts)
SOURCES = {
    "en": ("wikimedia/wikipedia", "20231101.en"),
    "ar": ("wikimedia/wikipedia", "20231101.ar"),
    "tr": ("wikimedia/wikipedia", "20231101.tr"),
}

def download_corpus(lang: str, n_train: int, n_val: int, n_test: int):
    train_path = os.path.join(DATA_DIR, f"{lang}_train.txt")
    val_path   = os.path.join(DATA_DIR, f"{lang}_val.txt")
    test_path  = os.path.join(DATA_DIR, f"{lang}_test.txt")

    if all(os.path.exists(p) for p in [train_path, val_path, test_path]):
        log.info(f"[{lang}] Corpus already downloaded — skipping.")
        return

    log.info(f"[{lang}] Downloading Wikipedia corpus (~{n_train+n_val+n_test} sentences)...")
    from datasets import load_dataset
    ds_name, config = SOURCES[lang]
    ds = load_dataset(ds_name, config, split="train", streaming=True, trust_remote_code=False)

    sentences = []
    for item in ds:
        text = item.get("text", "").strip()
        for line in text.split("\n"):
            line = line.strip()
            if len(line) > 20:
                sentences.append(line)
            if len(sentences) >= n_train + n_val + n_test:
                break
        if len(sentences) >= n_train + n_val + n_test:
            break

    log.info(f"[{lang}] Collected {len(sentences):,} sentences.")
    total = len(sentences)
    t_end = min(n_train, total)
    v_end = min(t_end + n_val, total)

    with open(train_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sentences[:t_end]))
    with open(val_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sentences[t_end:v_end]))
    with open(test_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sentences[v_end:]))
    log.info(f"[{lang}] Saved: train={t_end}, val={v_end-t_end}, test={total-v_end}")


# ── Step 2: Baseline tokenization ─────────────────────────────────────────────

def train_or_load_tokenizer(lang: str) -> "spm.SentencePieceProcessor":
    import sentencepiece as spm
    model_path = os.path.join(TOK_DIR, f"{lang}_base.model")
    if os.path.exists(model_path):
        log.info(f"[{lang}] Tokenizer exists — loading.")
        sp = spm.SentencePieceProcessor()
        sp.load(model_path)
        return sp

    log.info(f"[{lang}] Training SentencePiece tokenizer (8k vocab)...")
    import tempfile
    train_path = os.path.join(DATA_DIR, f"{lang}_train.txt")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
        tmp_path = tmp.name
        with open(train_path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                tmp.write(line)
                if i >= 50_000:
                    break

    spm.SentencePieceTrainer.train(
        input=tmp_path,
        model_prefix=os.path.join(TOK_DIR, f"{lang}_base"),
        vocab_size=8000,
        character_coverage=0.9995,
        model_type="bpe",
        pad_id=0, unk_id=1, bos_id=2, eos_id=3,
        pad_piece="<pad>", unk_piece="<unk>", bos_piece="<s>", eos_piece="</s>",
    )
    os.unlink(tmp_path)
    sp = spm.SentencePieceProcessor()
    sp.load(model_path)
    return sp


def tokenize_baseline(lang: str, sp) -> dict:
    paths = {}
    for split in ["train", "val", "test"]:
        out_path = os.path.join(DATA_DIR, f"{lang}_baseline_{split}.npy")
        if os.path.exists(out_path):
            log.info(f"[{lang}/baseline/{split}] Already tokenized.")
            paths[split] = out_path
            continue
        in_path = os.path.join(DATA_DIR, f"{lang}_{split}.txt")
        log.info(f"[{lang}/baseline/{split}] Tokenizing...")
        ids = []
        with open(in_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    ids.extend([sp.bos_id()] + sp.encode(line) + [sp.eos_id()])
        arr = np.array(ids, dtype=np.int32)
        np.save(out_path, arr)
        log.info(f"[{lang}/baseline/{split}] {len(arr):,} tokens → {out_path}")
        paths[split] = out_path
    return paths

# ── Step 3: Morph tokenization (lightweight, no grammar engine) ───────────────
# For the mini experiment we use a simplified morph tokenizer:
# - EN: split on derivational suffixes (rule-based, no external deps)
# - AR: split on common prefixes/suffixes (approximation of templatic structure)
# - TR: split on agglutinative suffix chains (rule-based)
# This is NOT the full grammar engine — it's a principled approximation that
# captures the core information-density difference without requiring casmorphi/
# farasa/zemberek. The full engine is used in the main experiment.

import re

# Feature bundle = (root_approx, morphological_tag)
# We encode these as two parallel integer arrays: token_ids + feature_ids

EN_SUFFIXES = [
    "ational","tional","enci","anci","izer","ising","izing","alism","ness",
    "ation","ator","alism","aliti","ousli","ousness","iveness","fulness",
    "ible","able","ment","ness","ful","ous","ive","ing","tion","ed","er","ly","s",
]
AR_PREFIXES = ["ال","وال","بال","كال","فال","لل","وب","وك","وف","وم","ف","ب","ك","ل","و"]
AR_SUFFIXES = ["ون","ين","ات","ان","ها","هم","هن","كم","كن","نا","تم","تن","ني","ه","ة","ي","ا"]
TR_SUFFIXES = [
    "ların","lerin","ların","lerin","ları","leri","lar","ler",
    "nın","nin","nun","nün","ın","in","un","ün",
    "dan","den","tan","ten","da","de","ta","te",
    "ya","ye","a","e","ı","i","u","ü",
    "dır","dir","dur","dür","tır","tir","tur","tür",
    "mak","mek","yor","iyor","acak","ecek","dı","di","du","dü",
    "mış","miş","muş","müş","ım","im","um","üm",
    "lık","lik","luk","lük","cı","ci","cu","cü","çı","çi","çu","çü",
    "sız","siz","suz","süz","sal","sel","ça","çe",
]

def _morph_segment(word: str, lang: str):
    """Returns (root_approx, suffix_tag) for a word."""
    word = word.lower().strip(".,!?;:\"'()[]{}—–-")
    if not word:
        return word, "O"
    if lang == "en":
        for suf in EN_SUFFIXES:
            if word.endswith(suf) and len(word) - len(suf) >= 2:
                return word[:-len(suf)], f"SUF_{suf}"
        return word, "ROOT"
    elif lang == "ar":
        for pre in AR_PREFIXES:
            if word.startswith(pre) and len(word) - len(pre) >= 2:
                stem = word[len(pre):]
                for suf in AR_SUFFIXES:
                    if stem.endswith(suf) and len(stem) - len(suf) >= 1:
                        return stem[:-len(suf)], f"PRE_{pre}_SUF_{suf}"
                return stem, f"PRE_{pre}"
        for suf in AR_SUFFIXES:
            if word.endswith(suf) and len(word) - len(suf) >= 1:
                return word[:-len(suf)], f"SUF_{suf}"
        return word, "ROOT"
    elif lang == "tr":
        for suf in TR_SUFFIXES:
            if word.endswith(suf) and len(word) - len(suf) >= 2:
                return word[:-len(suf)], f"SUF_{suf}"
        return word, "ROOT"
    return word, "ROOT"


def tokenize_morph(lang: str) -> dict:
    """
    Builds a morph vocabulary from train, then encodes all splits.
    Returns paths dict and (vocab, bundle_vocab) sizes.
    """
    vocab_path   = os.path.join(TOK_DIR, f"{lang}_morph_vocab.json")
    bundles_path = os.path.join(TOK_DIR, f"{lang}_morph_bundles.json")

    # Check if all outputs exist
    all_exist = all(
        os.path.exists(os.path.join(DATA_DIR, f"{lang}_morph_{split}.npy"))
        and os.path.exists(os.path.join(DATA_DIR, f"{lang}_morph_feat_{split}.npy"))
        for split in ["train", "val", "test"]
    )
    if all_exist and os.path.exists(vocab_path):
        log.info(f"[{lang}/morph] Already tokenized — loading vocab sizes.")
        with open(vocab_path) as f: vocab = json.load(f)
        with open(bundles_path) as f: bundles = json.load(f)
        return {
            s: (os.path.join(DATA_DIR, f"{lang}_morph_{s}.npy"),
                os.path.join(DATA_DIR, f"{lang}_morph_feat_{s}.npy"))
            for s in ["train","val","test"]
        }, len(vocab), len(bundles)

    log.info(f"[{lang}/morph] Building vocabulary from train...")
    token2id  = {"<pad>": 0, "<unk>": 1, "<s>": 2, "</s>": 3}
    bundle2id = {"O": 0}

    def _encode_file(path, build_vocab=False):
        tok_ids, feat_ids = [], []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                tok_ids.append(2); feat_ids.append(0)   # BOS
                for word in line.split():
                    root, tag = _morph_segment(word, lang)
                    surface = f"{root}+{tag}"
                    if build_vocab:
                        if surface not in token2id:
                            token2id[surface] = len(token2id)
                        if tag not in bundle2id:
                            bundle2id[tag] = len(bundle2id)
                    tid = token2id.get(surface, 1)   # <unk>
                    bid = bundle2id.get(tag, 0)
                    tok_ids.append(tid); feat_ids.append(bid)
                tok_ids.append(3); feat_ids.append(0)   # EOS
        return np.array(tok_ids, dtype=np.int32), np.array(feat_ids, dtype=np.int32)

    # Build vocab on train
    _encode_file(os.path.join(DATA_DIR, f"{lang}_train.txt"), build_vocab=True)

    # Cap vocab at 50k (same as full experiment)
    if len(token2id) > 50_000:
        # Keep most frequent — approximate by keeping first 50k (train order ≈ freq)
        token2id = dict(list(token2id.items())[:50_000])

    with open(vocab_path,   "w", encoding="utf-8") as f: json.dump(token2id,  f)
    with open(bundles_path, "w", encoding="utf-8") as f: json.dump(bundle2id, f)
    log.info(f"[{lang}/morph] vocab={len(token2id):,}, bundles={len(bundle2id):,}")

    paths = {}
    for split in ["train", "val", "test"]:
        tok_out  = os.path.join(DATA_DIR, f"{lang}_morph_{split}.npy")
        feat_out = os.path.join(DATA_DIR, f"{lang}_morph_feat_{split}.npy")
        toks, feats = _encode_file(os.path.join(DATA_DIR, f"{lang}_{split}.txt"))
        np.save(tok_out,  toks)
        np.save(feat_out, feats)
        log.info(f"[{lang}/morph/{split}] {len(toks):,} tokens")
        paths[split] = (tok_out, feat_out)

    return paths, len(token2id), len(bundle2id)

# ── Step 4: Model (same architecture as full experiment, just smaller) ─────────

def build_model(vocab_size: int, n_feat_bundles: int, morph_mode: bool):
    import torch
    import torch.nn as nn

    C   = CFG["n_embd"]
    T   = CFG["seq_len"]

    class CausalSA(nn.Module):
        def __init__(self):
            super().__init__()
            self.n_head = CFG["n_head"]
            self.hd = C // self.n_head
            self.qkv  = nn.Linear(C, 3*C, bias=False)
            self.proj = nn.Linear(C, C, bias=False)
            self.drop = nn.Dropout(CFG["dropout"])
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
                                     nn.Linear(CFG["ffn_dim"],C),nn.Dropout(CFG["dropout"]))
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
            self.drop   = nn.Dropout(CFG["dropout"])
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
        def forward(self, idx, feat, targets=None):
            B,t = idx.shape
            pos = torch.arange(t, device=idx.device).unsqueeze(0)
            x   = self.tok_emb(idx) + self.pos_emb(pos)
            if self.morph_mode:
                x = x + self.feat_emb(feat)
            x = self.drop(x)
            for blk in self.blocks: x = blk(x)
            x = self.ln_f(x)
            logits = self.head(x)
            loss = None
            if targets is not None:
                loss = nn.functional.cross_entropy(
                    logits.view(-1, logits.size(-1)), targets.view(-1), ignore_index=0)
            return logits, loss

    model = MiniGPT()
    n_params = sum(p.numel() for p in model.parameters())
    log.info(f"Model: {n_params:,} parameters")
    return model

# ── Step 5: Dataset + training loop ──────────────────────────────────────────

def make_dataset(tok_path, feat_path=None):
    import torch
    from torch.utils.data import Dataset
    class DS(Dataset):
        def __init__(self):
            self.tok  = np.load(tok_path,  mmap_mode="r")
            self.feat = np.load(feat_path, mmap_mode="r") if feat_path else None
            self.n    = (len(self.tok) - 1) // CFG["seq_len"]
        def __len__(self): return self.n
        def __getitem__(self, i):
            s = i * CFG["seq_len"]
            e = s + CFG["seq_len"]
            x = torch.from_numpy(self.tok[s:e].astype(np.int64))
            y = torch.from_numpy(self.tok[s+1:e+1].astype(np.int64))
            f = torch.from_numpy(self.feat[s:e].astype(np.int64)) if self.feat is not None \
                else torch.zeros_like(x)
            return x, f, y
    return DS()


def get_lr(step, total_steps):
    w = TRAIN["warmup_steps"]
    if step < w:
        return TRAIN["lr"] * step / w
    p = (step - w) / max(total_steps - w, 1)
    return TRAIN["lr"] * 0.5 * (1.0 + math.cos(math.pi * p))


def train_model(lang, regime, tok_path, feat_path, vocab_size, n_feat_bundles):
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader

    morph_mode = (regime == "morph")
    model_path = os.path.join(MODELS_DIR, f"{lang}_{regime}.pt")
    ts_path    = os.path.join(LOGS_DIR,   f"{lang}_{regime}_timeseries.jsonl")

    if os.path.exists(model_path):
        log.info(f"[{lang}/{regime}] Checkpoint exists — skipping training.")
        return

    device = torch.device("cpu")
    model  = build_model(vocab_size, n_feat_bundles, morph_mode).to(device)

    decay   = [p for n,p in model.named_parameters() if p.requires_grad and p.dim()>=2]
    nodecay = [p for n,p in model.named_parameters() if p.requires_grad and p.dim()<2]
    opt = torch.optim.AdamW(
        [{"params": decay, "weight_decay": TRAIN["weight_decay"]},
         {"params": nodecay, "weight_decay": 0.0}],
        lr=TRAIN["lr"], betas=(0.9, 0.95))

    ds     = make_dataset(tok_path, feat_path)
    loader = DataLoader(ds, batch_size=TRAIN["batch_size"], shuffle=True,
                        num_workers=0, drop_last=True)

    tokens_per_step = TRAIN["batch_size"] * CFG["seq_len"]
    total_steps     = TRAIN["total_tokens"] // tokens_per_step
    log.info(f"[{lang}/{regime}] Training: {total_steps:,} steps × {tokens_per_step:,} tokens/step")

    model.train()
    step = 0; tokens_seen = 0; t0 = time.time()
    data_iter = iter(loader)

    while step < total_steps:
        try:
            x, f, y = next(data_iter)
        except StopIteration:
            data_iter = iter(loader)
            x, f, y  = next(data_iter)

        lr = get_lr(step, total_steps)
        for pg in opt.param_groups: pg["lr"] = lr

        opt.zero_grad(set_to_none=True)
        _, loss = model(x, f, y)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), TRAIN["grad_clip"])
        opt.step()

        step += 1; tokens_seen += tokens_per_step

        if step % TRAIN["log_every"] == 0:
            ppl = math.exp(min(loss.item(), 20))
            elapsed = time.time() - t0
            log.info(f"[{lang}/{regime}] step={step:5d} loss={loss.item():.4f} "
                     f"ppl={ppl:.1f} lr={lr:.2e} tokens={tokens_seen:,} t={elapsed:.0f}s")
            with open(ts_path, "a") as f_ts:
                f_ts.write(json.dumps({
                    "step": step, "tokens": tokens_seen,
                    "loss": round(loss.item(), 4), "ppl": round(ppl, 2),
                    "lr": round(lr, 8), "wall_time_sec": round(elapsed, 1),
                }) + "\n")

    torch.save({"model": model.state_dict(), "step": step,
                "vocab_size": vocab_size, "n_feat_bundles": n_feat_bundles,
                "morph_mode": morph_mode, "cfg": CFG}, model_path)
    log.info(f"[{lang}/{regime}] Done. Saved → {model_path}")

# ── Step 6: Evaluation ────────────────────────────────────────────────────────

def evaluate_model(lang, regime, tok_path, feat_path, vocab_size, n_feat_bundles):
    import torch
    from torch.utils.data import DataLoader

    morph_mode = (regime == "morph")
    model_path  = os.path.join(MODELS_DIR, f"{lang}_{regime}.pt")
    result_path = os.path.join(RESULTS_DIR, f"{lang}_{regime}_eval.json")

    if os.path.exists(result_path):
        log.info(f"[{lang}/{regime}] Eval results exist — skipping.")
        with open(result_path) as f: return json.load(f)

    ckpt  = torch.load(model_path, map_location="cpu")
    model = build_model(vocab_size, n_feat_bundles, morph_mode)
    model.load_state_dict(ckpt["model"])
    model.eval()

    ds     = make_dataset(tok_path, feat_path)
    loader = DataLoader(ds, batch_size=32, shuffle=False, num_workers=0)

    total_loss = 0.0; total_tokens = 0
    with torch.no_grad():
        for x, f, y in loader:
            _, loss = model(x, f, y)
            n = (y != 0).sum().item()
            total_loss   += loss.item() * n
            total_tokens += n

    avg_loss = total_loss / max(total_tokens, 1)
    ppl      = math.exp(min(avg_loss, 20))

    # Morphological metrics
    tokens_per_meaning_unit = None
    unk_rate = None
    if morph_mode:
        # tokens/meaning unit: ratio of morph tokens to unique root forms
        toks = np.load(tok_path, mmap_mode="r")
        unique_roots = len(set(toks.tolist()))
        tokens_per_meaning_unit = round(len(toks) / max(unique_roots, 1), 4)
        # unk rate
        unk_count = int((toks == 1).sum())
        unk_rate  = round(unk_count / max(len(toks), 1), 4)

    result = {
        "language": lang, "regime": regime,
        "test_loss": round(avg_loss, 4),
        "test_ppl":  round(ppl, 4),
        "num_tokens": total_tokens,
        "tokens_per_meaning_unit": tokens_per_meaning_unit,
        "unk_rate": unk_rate,
    }
    with open(result_path, "w") as f: json.dump(result, f, indent=2)
    log.info(f"[{lang}/{regime}] test_ppl={ppl:.2f} | "
             + (f"tpu={tokens_per_meaning_unit} unk={unk_rate:.2%}" if morph_mode else ""))
    return result


# ── Step 7: Summary ───────────────────────────────────────────────────────────

def print_summary(results: list):
    print("\n" + "="*72)
    print(f"{'Model':<20} {'Test PPL':>10} {'Tokens/Unit':>13} {'UNK rate':>10}")
    print("-"*72)
    for r in results:
        name = f"{r['language']}_{r['regime']}"
        ppl  = f"{r['test_ppl']:.2f}"
        tpu  = f"{r['tokens_per_meaning_unit']:.4f}" if r['tokens_per_meaning_unit'] else "—"
        unk  = f"{r['unk_rate']:.2%}" if r['unk_rate'] is not None else "—"
        print(f"{name:<20} {ppl:>10} {tpu:>13} {unk:>10}")
    print("="*72)

    # Efficiency ratios
    print("\nBaseline vs Morph — PPL ratio (lower morph PPL = morph wins):")
    by_lang = {}
    for r in results:
        by_lang.setdefault(r["language"], {})[r["regime"]] = r
    for lang, pair in by_lang.items():
        if "baseline" in pair and "morph" in pair:
            ratio = pair["morph"]["test_ppl"] / pair["baseline"]["test_ppl"]
            direction = "morph HIGHER" if ratio > 1 else "morph LOWER"
            print(f"  {lang}: morph/baseline PPL ratio = {ratio:.3f}  ({direction})")

    summary_path = os.path.join(RESULTS_DIR, "mini_summary.json")
    with open(summary_path, "w") as f:
        json.dump({"results": results, "by_lang": {
            lang: {
                "ppl_ratio": by_lang[lang].get("morph",{}).get("test_ppl",None) /
                             by_lang[lang].get("baseline",{}).get("test_ppl",1)
                if "morph" in by_lang[lang] and "baseline" in by_lang[lang] else None
            } for lang in by_lang
        }}, f, indent=2)
    log.info(f"Summary saved → {summary_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--langs", nargs="+", default=["en","ar","tr"],
                        choices=["en","ar","tr"])
    parser.add_argument("--skip-download", action="store_true")
    args = parser.parse_args()

    try:
        import torch
    except ImportError:
        print("ERROR: PyTorch not installed. Run: pip install torch")
        sys.exit(1)

    results = []

    for lang in args.langs:
        log.info(f"\n{'='*60}\nLanguage: {lang}\n{'='*60}")

        # 1. Download
        if not args.skip_download:
            download_corpus(lang, N_TRAIN, N_VAL, N_TEST)

        # 2. Baseline tokenization
        sp = train_or_load_tokenizer(lang)
        base_paths = tokenize_baseline(lang, sp)
        vocab_size_base = sp.get_piece_size()

        # 3. Morph tokenization
        morph_paths, vocab_size_morph, n_bundles = tokenize_morph(lang)

        # 4. Train baseline
        train_model(lang, "baseline",
                    base_paths["train"], None,
                    vocab_size_base, 1)

        # 5. Train morph
        train_model(lang, "morph",
                    morph_paths["train"][0], morph_paths["train"][1],
                    vocab_size_morph, n_bundles)

        # 6. Evaluate both on test
        r_base = evaluate_model(lang, "baseline",
                                base_paths["test"], None,
                                vocab_size_base, 1)
        r_morph = evaluate_model(lang, "morph",
                                 morph_paths["test"][0], morph_paths["test"][1],
                                 vocab_size_morph, n_bundles)
        results.extend([r_base, r_morph])

    print_summary(results)


if __name__ == "__main__":
    main()
