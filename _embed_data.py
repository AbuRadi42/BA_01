import json, os

base = "morph_efficiency_project/logs"
mini_base = "mini_experiment"

def load_json(path):
    if not os.path.exists(path): return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def load_jsonl(path):
    if not os.path.exists(path): return []
    with open(path, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    return [json.loads(l) for l in lines]

models = ["en_baseline", "en_morph", "ar_baseline", "ar_morph", "tr_baseline", "tr_morph"]

out = {"timeseries": {}, "lm": {}, "morph": {}, "compute": {}}

for m in models:
    out["timeseries"][m] = load_jsonl(f"{base}/training/{m}_timeseries.jsonl")
    out["lm"][m]         = load_json(f"{base}/evaluation/{m}_lm.json")
    out["morph"][m]      = load_json(f"{base}/evaluation/{m}_morph.json")
    out["compute"][m]    = load_json(f"{base}/evaluation/{m}_compute.json")

# ── Mini experiment results ───────────────────────────────────────────────────
mini_langs = ["en", "ar", "tr"]
mini_regimes = ["baseline", "morph"]

out["mini"] = {
    "timeseries": {},
    "eval": {},
    "summary": load_json(f"{mini_base}/results/mini_summary.json"),
}

for lang in mini_langs:
    for regime in mini_regimes:
        key = f"{lang}_{regime}"
        out["mini"]["timeseries"][key] = load_jsonl(
            f"{mini_base}/logs/{key}_timeseries.jsonl"
        )
        out["mini"]["eval"][key] = load_json(
            f"{mini_base}/results/{key}_eval.json"
        )

out["tok_examples"] = load_json(f"{mini_base}/results/tok_examples.json") or {}

js = "// Auto-generated — do not edit manually\nconst EMBEDDED_DATA = " + json.dumps(out, indent=None) + ";\n"

with open("morph_efficiency_project/presentation/data.js", "w") as f:
    f.write(js)

print("Done. data.js written.")
