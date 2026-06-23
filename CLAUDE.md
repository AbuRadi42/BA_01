# Agent Briefing — Morphology-Aware Tokenization (BA_01)

If you are a Claude Code agent picking this repository up cold, read this whole file before doing anything. The high-level scientific framing is in `README.md`. This file documents the standing rules, the operational context, and the open decisions that a fresh agent cannot infer from the code alone.

---

## Who you are working with

- **Sameh AbuRadi** — author, CODE University of Applied Sciences, Berlin. Native Arabic, fluent English, fluent Turkish. Linguistically literate, computer-science literate. Direct communicator; brief answers preferred. Will say "fuck" when frustrated — that signals "I need this fixed now," not "I am angry at you, agent."
- **Fabian Geier** — academic supervisor. The project's Cambridge NLP Press submission is governed by him.
- **Deniz Sertkan** — Sameh's friend, donor of the $24,000 AWS credit budget. Spell the name *exactly* as "Deniz Sertkan". Earlier agents have fumbled this and Sameh hates it.

---

## Standing rules — non-negotiable

### Git workflow
- **Always amend, never commit.** This repository maintains a single canonical commit. Every change is `git add <files>; git commit --amend --no-edit` (or with an explicit `-m` if Sameh asks for a message change).
- Preserve the author and committer date with `GIT_COMMITTER_DATE="<date>" git commit --amend --date "<date>"` if a date is dictated.
- Never push without explicit permission. Amending changes the SHA; force-push is destructive.

### AWS deployment
- **Never run `launch_run.py --deploy` or any equivalent that starts a real AWS / SageMaker training job without Sameh's explicit per-instance permission.** Dry runs (without `--deploy`) that only emit config files are fine.
- The same rule applies to any `aws s3 sync` of multi-GB artefacts.
- Deniz's $24,000 credit pool funds Phase 2 (proof of concept) AND Phase 3 (Turkish reasoning SLM). Spending it without permission betrays the gift.

### Writing tone
- The target audience is linguistically trained, not CS-fluent. Lead with what something *is* before naming it. Use linguistic terminology where it exists (agglutinative, templatic, analytic, wazn, izafet). Replace CS-only jargon with linguist-readable equivalents (tokeniser pipeline beats ingestion stack; training run beats execution).
- **No em-dashes ("—") anywhere.** Use commas, colons, or new sentences.
- No LLM-tell phrases ("It's important to note...", "delve into...", "In this paper, we will...").

### Canonical ordering
- The four languages are always listed in this order across the project: **ZH → EN → TR → AR**. Tables, code loops, manuscript subsections, diagrams — all of them. This is typological order from isolating to templatic.

### Memory files
- Sameh's user memory at `C:\Users\Sameh AbuRadi\.claude\projects\C--Users-Sameh-AbuRadi-Desktop-BA-01\memory\` documents prior feedback that should still apply. Read `MEMORY.md` there if you have filesystem access; the rules in this `CLAUDE.md` mirror the most load-bearing ones.

---

## Current project state

A single commit on `main` contains everything. As of the last amend, the project is **architecture-complete and AWS-deployable**, with one rehearsal smoke test passing on all eight (lang × regime) cells. Sameh has not yet authorised the AWS spend.

### What is done
- Four grammar engines (`morph_efficiency_project/scripts/engines/`) at 100% test pass across 4,283 tests
- Sentence-grammar layer (`morph_efficiency_project/scripts/engines/grammar/`) with context-aware POS resolution and structural validation
- Tokenisation pipeline (`morph_efficiency_project/scripts/tokenize_for_training.py`) with per-(lang, surface) memoisation; full-corpus runs complete for all four languages on disk in `mini_experiment/data/` (.npy files gitignored, vocab JSONs at `mini_experiment/tokenizers/` are tracked)
- Multi-stream MiniGPT architecture (`mini_experiment/run_mini.py`) supporting 1/2/4 input embedding streams with parameter-matched comparison
- Trainer (`morph_efficiency_project/scripts/train_model.py`) — cosine LR + AdamW + checkpointing + resume
- AWS SageMaker launcher (`morph_efficiency_project/scripts/aws/launch_run.py`) with dry-run and `--deploy` modes
- Manuscript (`manuscript/tex/`) tone-polished across all 8 sections, every Arabic word vocalised with tashkil, polyglossia loaded for RTL
- Audit reports + bundle distribution Zipf plots at `morph_efficiency_project/logs/summary/`
- Pipeline diagrams at `pipeline_diagrams.html` with Mermaid algorithm flowcharts plus data-flow SVGs
- 8-cell rehearsal smoke test passing (each cell trains a tiny model for 234 steps on CPU, all checkpoints save cleanly)

### What is NOT done (and is yours when Sameh says go)
1. **Phase 2 AWS deployment**. The 8-cell proof-of-concept sweep at 30M-parameter Chinchilla-optimal scale. Cost ~$3-5k. This is the Cambridge submission.
2. **Phase 3 Turkish reasoning SLM**. The bulk of the credits (~$15-20k) goes to scaling Turkish specifically into a reasoning-capable small language model using the technique Phase 2 proves. Sameh has not yet specified the target parameter count, the additional data sources (Turkish CommonCrawl, OSCAR, news, books, reasoning-task data), or the release path. Wait for him to spec it.
3. Section 6 of the manuscript ("Empirical Results") still contains Phase 1 (3-language, 2M-parameter) numbers. These will be replaced when Phase 2 data lands.
4. A handful of Phase 1 magnitudes are quoted in sections 1, 2, and 7 of the manuscript; those also update after Phase 2.

---

## Quick verification of project health

If you just inherited this and want to confirm nothing rotted:

```bash
# 1. Test suite (expect 4,283 passing)
python -X utf8 -m pytest morph_efficiency_project/tests/ -q

# 2. Local CPU smoke training (expect monotonic loss decrease in ~30s)
python morph_efficiency_project/scripts/train_model.py \
    --lang en --regime baseline --model-dim 64 --layers 2 \
    --max-tokens 50000 --batch-size 4 --seq-len 32 \
    --eval-every 100 --save-every 500 \
    --output-dir /tmp/smoke_en_baseline

# 3. Manuscript build (expect ~360KB PDF, zero Missing-character warnings)
cd manuscript/tex && tectonic main.tex --outdir _build

# 4. Bundle-space audit (slow — TR alone is ~16 min)
python morph_efficiency_project/scripts/compute_bundle_space.py
```

---

## Architecture cheat-sheet

| Language | Type | Morph streams | Vocab caps |
|---|---|---|---|
| ZH (Mandarin) | Isolating + radical-semantic | 2: char + radical_class | 32k + 214 Kangxi |
| EN (English) | Analytic | 2: surface + feat | 32k + 21 bundles observed |
| TR (Turkish) | Agglutinative | 2: surface + feat | 32k + 469 bundles observed |
| AR (Arabic) | Templatic | **4**: surface + feat + root + wazn | 32k + 1,450 bundles + 7,142 roots + 185 wazn classes |

Baseline regime for every language: 1 stream, 32k BPE-style cap.

---

## Recent things worth knowing

- **Tashkil**: every Arabic word in the manuscript is fully vocalised. If you add a new Arabic word, vocalise it. Root letters with hyphens (e.g. `ك-ت-ب`) stay bare — they are consonantal skeletons by definition.
- **polyglossia**: loaded in `manuscript/tex/main.tex`. Arabic uses the `\ar{...}` macro for proper RTL rendering. Mandarin uses `\zh{...}` for the SimSun CJK font.
- **TR engine speed**: the worst case is ~25 ms/word without caching. The tokeniser has a per-(lang, surface) memoisation cache that cuts TR full-corpus from ~30 hours to ~16 minutes. Do not remove the cache without measuring.
- **Bundle counts shift with corpus size**. The 20k-sample audit (from `compute_bundle_space.py`) and the full-corpus tokeniser produce slightly different `observed` numbers for the bundle stream. Both are correct for their respective sample. The diagrams and the manuscript already document the difference.
- **The five spare engines** (German, Spanish, Hungarian, Swahili, Basque) were removed earlier. They are in git history if you need to resurrect them, but the project's headline scope is the four languages.

---

## Open decisions waiting on Sameh

1. **When to authorise Phase 2 AWS deployment.** Requires `MORPH_S3_BUCKET` and `MORPH_SM_ROLE_ARN` env vars set, then 8 `launch_run.py --deploy` invocations.
2. **Phase 3 spec.** Sameh has not yet decided: target parameter count for the Turkish reasoning SLM, what additional data to bring in, what reasoning benchmarks to evaluate against, where to release the final model. Do not infer; wait for him.
3. **Cambridge template swap.** The manuscript currently uses `\documentclass[11pt, a4paper]{article}` for development convenience. At submission, that one line swaps for the Cambridge NLP Press class (`cambridge7A` or equivalent from the journal's Overleaf template). All other parts are written to survive the swap.

---

## Files you should know about

| Path | What it is |
|---|---|
| `README.md` | The project narrative — read it before this file |
| `experimental_contract.md` | The pre-registered scientific contract; frozen before implementation |
| `pipeline_diagrams.html` | Visual reference for each engine pipeline + bundle space |
| `morph_efficiency_project/scripts/engines/` | The four grammar engines + shared utilities + sentence-grammar layer |
| `morph_efficiency_project/scripts/aws/README.md` | Step-by-step AWS deployment guide |
| `morph_efficiency_project/logs/summary/` | Engine audit reports, bundle distribution analysis, training-readiness audit |
| `mini_experiment/run_mini.py` | The multi-stream MiniGPT model |
| `mini_experiment/tokenizers/` | Per-language vocab JSON tables (committed) |
| `mini_experiment/data/` | Raw .txt corpora and .npy integer streams (gitignored, rebuildable) |
| `manuscript/tex/main.tex` | Manuscript root; sections at `manuscript/tex/sections/sec_0*_*.tex` |
| `manuscript/tex/references.bib` | Bibliography |

---

## If something is broken or unclear

Ask Sameh. He prefers a brief precise question over a long preamble. If you need to dispatch agents to investigate something, dispatch them with explicit scope; he is comfortable with that workflow.

Do not silently revert his work. If you see something that looks wrong but might be intentional (a deliberate test-spec choice, a manuscript prose decision, a numeric value), surface it as a question rather than fixing it unilaterally.
