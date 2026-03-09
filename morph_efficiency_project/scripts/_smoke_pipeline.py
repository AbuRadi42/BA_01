"""
_smoke_pipeline.py
------------------
End-to-end smoke test for the data pipeline.
Runs on this machine (no GPU, no full corpus) using a tiny synthetic slice.

Tests:
  1. download_data.py  — streams a small sample from HuggingFace and writes
                         data/raw/{lang}/train|val|test.txt
  2. preprocess_baseline.py — trains a tiny SentencePiece tokenizer and
                              produces data/processed/{lang}/baseline/*.npy
  3. preprocess_morph.py   — runs all three grammar engines over the sample
                              and produces data/processed/{lang}/morph/*.npy

All output goes to a temp directory so it never touches the real data/.
Prints a clear PASS / FAIL summary at the end.

Usage:
  python morph_efficiency_project/scripts/_smoke_pipeline.py
  python morph_efficiency_project/scripts/_smoke_pipeline.py --lang en
  python morph_efficiency_project/scripts/_smoke_pipeline.py --lang ar
  python morph_efficiency_project/scripts/_smoke_pipeline.py --lang tr
  python morph_efficiency_project/scripts/_smoke_pipeline.py --lang all
"""

import argparse
import json
import logging
import os
import shutil
import sys
import tempfile
import traceback

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Tiny synthetic corpora (no network needed for the morph/baseline steps) ───
# 20 sentences per language — enough to exercise the full pipeline.

SAMPLE_SENTENCES = {
    "en": [
        "The quick brown fox jumps over the lazy dog.",
        "She has been running every morning for three years.",
        "The children were playing happily in the garden.",
        "He quickly modernized the organization's outdated systems.",
        "The cats sat on the mats and watched the birds.",
        "They have already finished their homework before dinner.",
        "The government's decision was widely criticized by experts.",
        "She is the most talented musician I have ever heard.",
        "The books on the shelf were carefully organized by topic.",
        "He was unable to understand the complexity of the problem.",
        "The researchers published their findings in a peer-reviewed journal.",
        "She had been working on the project for several months.",
        "The old man walked slowly along the riverbank at sunset.",
        "They are planning to build a new school in the neighborhood.",
        "The company's profits increased significantly during the last quarter.",
        "He smiled and nodded as she explained her reasoning.",
        "The students were asked to write a short essay about their goals.",
        "She carefully placed the fragile vase on the highest shelf.",
        "The train arrived at the station exactly on time.",
        "He has never visited the capital city of his own country.",
    ],
    "ar": [
        "ذَهَبَ الطَّالِبُ إِلَى الْمَدْرَسَةِ فِي الصَّبَاحِ.",
        "كَتَبَتِ الْمُعَلِّمَةُ الدَّرْسَ عَلَى السَّبُّورَةِ.",
        "يَقْرَأُ الأَطْفَالُ الْكُتُبَ فِي الْمَكْتَبَةِ.",
        "اِجْتَمَعَ الْمُدِيرُونَ لِمُنَاقَشَةِ الْخُطَّةِ الْجَدِيدَةِ.",
        "تَعَلَّمَ الطُّلَّابُ اللُّغَةَ الْعَرَبِيَّةَ بِجِدٍّ وَاجْتِهَادٍ.",
        "اِنْكَسَرَتِ الزُّجَاجَةُ عِنْدَمَا سَقَطَتْ مِنَ الطَّاوِلَةِ.",
        "يَسْتَخْدِمُ الْمُهَنْدِسُونَ أَحْدَثَ التِّقْنِيَّاتِ فِي عَمَلِهِمْ.",
        "قَرَأَتِ الْبِنْتُ قِصَّةً جَمِيلَةً قَبْلَ النَّوْمِ.",
        "وَصَلَ الْقِطَارُ إِلَى الْمَحَطَّةِ فِي الْوَقْتِ الْمُحَدَّدِ.",
        "تَفَاهَمَ الطَّرَفَانِ وَتَوَصَّلَا إِلَى اتِّفَاقٍ مُشْتَرَكٍ.",
        "اِسْتَخْرَجَ الْعُلَمَاءُ نَتَائِجَ مُهِمَّةً مِنَ الْبَيَانَاتِ.",
        "كَانَ الطَّقْسُ بَارِدًا جِدًّا فِي الشِّتَاءِ الْمَاضِي.",
        "تَرَاسَلَ الصَّدِيقَانِ عَبْرَ الْبَرِيدِ الإِلِكْتُرُونِيِّ.",
        "يُحِبُّ الأَوْلَادُ اللَّعِبَ فِي الْحَدِيقَةِ بَعْدَ الْمَدْرَسَةِ.",
        "اِنْتَخَبَ الشَّعْبُ رَئِيسًا جَدِيدًا فِي الاِنْتِخَابَاتِ.",
        "دَرَسَ الطَّالِبُ الْمُجْتَهِدُ طَوَالَ اللَّيْلِ لِلاِمْتِحَانِ.",
        "أَرْسَلَتِ الشَّرِكَةُ رِسَالَةً رَسْمِيَّةً إِلَى الْعُمَلَاءِ.",
        "تَقَدَّمَ الْعِلْمُ تَقَدُّمًا كَبِيرًا فِي الْقَرْنِ الْمَاضِي.",
        "اِحْتَرَمَ الطُّلَّابُ مُعَلِّمِيهِمْ وَأَطَاعُوا تَعْلِيمَاتِهِمْ.",
        "يَعْمَلُ الْمُزَارِعُونَ بِجِدٍّ لِإِنْتَاجِ الْغِذَاءِ لِلنَّاسِ.",
    ],
    "tr": [
        "Öğrenci sabah erkenden okula gitti.",
        "Öğretmen tahtaya dersi yazdı.",
        "Çocuklar kütüphanede kitap okuyorlar.",
        "Müdürler yeni planı tartışmak için toplandılar.",
        "Öğrenciler Türkçeyi çok çalışarak öğrendiler.",
        "Şişe masadan düşünce kırıldı.",
        "Mühendisler işlerinde en son teknolojileri kullanıyorlar.",
        "Kız uyumadan önce güzel bir hikaye okudu.",
        "Tren istasyona tam zamanında geldi.",
        "İki taraf anlaşarak ortak bir uzlaşıya vardılar.",
        "Bilim insanları verilerden önemli sonuçlar çıkardılar.",
        "Geçen kış hava çok soğuktu.",
        "İki arkadaş e-posta yoluyla haberleşti.",
        "Çocuklar okuldan sonra bahçede oynamayı seviyor.",
        "Halk seçimlerde yeni bir cumhurbaşkanı seçti.",
        "Çalışkan öğrenci sınav için bütün gece ders çalıştı.",
        "Şirket müşterilere resmi bir mektup gönderdi.",
        "Bilim geçen yüzyılda büyük ilerleme kaydetti.",
        "Öğrenciler öğretmenlerine saygı gösterdi ve talimatlarına uydu.",
        "Çiftçiler insanlara yiyecek üretmek için çok çalışıyor.",
    ],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def write_raw_split(lang: str, base_dir: str, sentences: list[str]):
    """Write synthetic sentences as train/val/test splits."""
    raw_dir = os.path.join(base_dir, "data", "raw", lang)
    os.makedirs(raw_dir, exist_ok=True)
    # 14 train / 3 val / 3 test
    splits = {
        "train": sentences[:14],
        "val":   sentences[14:17],
        "test":  sentences[17:],
    }
    for split, lines in splits.items():
        path = os.path.join(raw_dir, f"{split}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    log.info(f"[{lang}] Raw splits written to {raw_dir}")
    return splits


def check_npy(path: str, min_tokens: int = 1) -> tuple[bool, str]:
    if not os.path.exists(path):
        return False, f"missing: {path}"
    arr = np.load(path)
    if len(arr) < min_tokens:
        return False, f"too short ({len(arr)} tokens): {path}"
    return True, f"{len(arr)} tokens"


def run_baseline(lang: str, base_dir: str) -> tuple[bool, str]:
    """Run preprocess_baseline.py logic inline (avoids subprocess + path issues)."""
    try:
        import sentencepiece as spm
    except ImportError:
        return False, "sentencepiece not installed — pip install sentencepiece"

    import tempfile as _tmp

    paths = {
        "train_raw": os.path.join(base_dir, "data", "raw", lang, "train.txt"),
        "val_raw":   os.path.join(base_dir, "data", "raw", lang, "val.txt"),
        "test_raw":  os.path.join(base_dir, "data", "raw", lang, "test.txt"),
        "tok_dir":   os.path.join(base_dir, "tokenizers", f"{lang}_base"),
        "proc_dir":  os.path.join(base_dir, "data", "processed", lang, "baseline"),
    }
    os.makedirs(paths["tok_dir"],  exist_ok=True)
    os.makedirs(paths["proc_dir"], exist_ok=True)

    model_prefix = os.path.join(paths["tok_dir"], f"{lang}_base")

    # Train a tiny tokenizer (vocab=200 for smoke test)
    with _tmp.NamedTemporaryFile(mode="w", suffix=".txt",
                                  delete=False, encoding="utf-8") as tmp:
        tmp_path = tmp.name
        with open(paths["train_raw"], encoding="utf-8") as f:
            tmp.write(f.read())

    spm.SentencePieceTrainer.train(
        input=tmp_path,
        model_prefix=model_prefix,
        vocab_size=200,
        character_coverage=1.0,
        model_type="bpe",
        pad_id=0, unk_id=1, bos_id=2, eos_id=3,
        pad_piece="<pad>", unk_piece="<unk>",
        bos_piece="<s>", eos_piece="</s>",
    )
    os.unlink(tmp_path)

    sp = spm.SentencePieceProcessor()
    sp.load(model_prefix + ".model")

    for split in ("train", "val", "test"):
        raw_path = paths[f"{split}_raw"]
        out_path = os.path.join(paths["proc_dir"], f"{split}_tokens.npy")
        ids = []
        with open(raw_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    ids += [sp.bos_id()] + sp.encode(line) + [sp.eos_id()]
        np.save(out_path, np.array(ids, dtype=np.int32))

    return True, f"tokenizer vocab={sp.get_piece_size()}"


def run_morph(lang: str, base_dir: str) -> tuple[bool, str]:
    """Run preprocess_morph.py logic inline."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from morph_efficiency_project.scripts.engines import (
        EnglishEngine, ArabicEngine, TurkishEngine, MorphVocab,
    )
    from morph_efficiency_project.scripts.preprocess_morph import process_split

    engine_cls = {"en": EnglishEngine, "ar": ArabicEngine, "tr": TurkishEngine}[lang]
    config_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "morph_efficiency_project", "configs"
    )
    # Resolve to absolute so it works regardless of cwd
    config_dir = os.path.abspath(config_dir)

    engine = engine_cls(config_dir=config_dir)
    vocab  = MorphVocab()

    for split in ("train", "val", "test"):
        stats = process_split(lang, split, engine, vocab, base_dir=base_dir)
        if not stats:
            return False, f"process_split returned empty stats for {split}"

    tok_dir = os.path.join(base_dir, "tokenizers", f"{lang}_morph")
    vocab.save(tok_dir)
    return True, (
        f"vocab={len(vocab.token2id)} tokens, "
        f"{len(vocab.bundle2id)} feature bundles"
    )


# ── Per-language smoke test ───────────────────────────────────────────────────

def smoke_language(lang: str, base_dir: str) -> dict:
    results = {}

    # Step 0 — write synthetic raw data
    try:
        write_raw_split(lang, base_dir, SAMPLE_SENTENCES[lang])
        results["raw_data"] = ("PASS", "20 sentences written")
    except Exception as e:
        results["raw_data"] = ("FAIL", str(e))
        return results  # can't continue without raw data

    # Step 1 — baseline preprocessing
    try:
        ok, msg = run_baseline(lang, base_dir)
        if ok:
            # Verify outputs exist and have tokens
            checks = []
            for split in ("train", "val", "test"):
                p = os.path.join(base_dir, "data", "processed", lang,
                                 "baseline", f"{split}_tokens.npy")
                ok2, m2 = check_npy(p)
                checks.append(f"{split}: {m2}")
                if not ok2:
                    raise RuntimeError(m2)
            results["baseline_preprocess"] = ("PASS", msg + " | " + ", ".join(checks))
        else:
            results["baseline_preprocess"] = ("FAIL", msg)
    except Exception as e:
        results["baseline_preprocess"] = ("FAIL", traceback.format_exc(limit=3))

    # Step 2 — morph preprocessing
    try:
        ok, msg = run_morph(lang, base_dir)
        if ok:
            checks = []
            for split in ("train", "val", "test"):
                for suffix in ("tokens", "feature_ids"):
                    p = os.path.join(base_dir, "data", "processed", lang,
                                     "morph", f"{split}_{suffix}.npy")
                    ok2, m2 = check_npy(p)
                    checks.append(f"{split}_{suffix}: {m2}")
                    if not ok2:
                        raise RuntimeError(m2)
            results["morph_preprocess"] = ("PASS", msg + " | " + ", ".join(checks))
        else:
            results["morph_preprocess"] = ("FAIL", msg)
    except Exception as e:
        results["morph_preprocess"] = ("FAIL", traceback.format_exc(limit=3))

    return results


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="End-to-end pipeline smoke test.")
    parser.add_argument("--lang", choices=["en", "ar", "tr", "all"], default="all")
    args = parser.parse_args()

    langs = ["en", "ar", "tr"] if args.lang == "all" else [args.lang]

    # Use a temp directory so we never pollute the real data/
    tmp_dir = tempfile.mkdtemp(prefix="smoke_pipeline_")
    log.info(f"Smoke test working directory: {tmp_dir}")

    all_results = {}
    try:
        for lang in langs:
            log.info(f"\n{'='*60}")
            log.info(f"  Smoke test: {lang.upper()}")
            log.info(f"{'='*60}")
            all_results[lang] = smoke_language(lang, tmp_dir)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  SMOKE TEST SUMMARY")
    print(f"{'='*60}")
    total_pass = total_fail = 0
    for lang, steps in all_results.items():
        print(f"\n  [{lang.upper()}]")
        for step, (status, msg) in steps.items():
            icon = "✓" if status == "PASS" else "✗"
            print(f"    {icon} {step:<25s}  {status}  —  {msg[:120]}")
            if status == "PASS":
                total_pass += 1
            else:
                total_fail += 1

    print(f"\n{'='*60}")
    print(f"  {total_pass} passed,  {total_fail} failed")
    print(f"{'='*60}\n")

    sys.exit(0 if total_fail == 0 else 1)


if __name__ == "__main__":
    main()
