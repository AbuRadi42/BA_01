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
- **Never commit without Sameh's explicit go-ahead.** Stage approved work (`git add`) and leave it staged; he decides when it is committed. (The old single-amended-commit rule is retired: `main` is now a normal multi-commit history.)
- When he does authorise commits, he names the timestamp; everything committed under one timestamp is **one commit** with a short single-line message of exactly 63 characters (no AI trailers). Author identity on every commit: `𝕾𝖆𝖒𝖊𝖍 𝕬𝖇𝖚𝕽𝖆𝖉𝖎 <team@samhoustonlabs.com>`.
- Never push without explicit permission, and never force-push or rewrite published history unless he explicitly authorises that specific rewrite.
- He often works from his phone: show every proposed change (text before/after, commit messages) inline in chat, not only in files.

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

The four-language experiment (Phase 2) is **done and written up**: compute-optimal, transformer-matched baseline vs grammar-aware pairs for ZH, EN, TR, AR, plus a four-seed Arabic replication and a parameter-matched shuffle control. The verdict is a split: no rebate for ZH/EN/TR, a robust structural rebate for AR (the Templatic Lexical Surplus). The manuscript reports it and is in pre-submission review: an external reviewer (Tawfiq Omar Abuaisha, PhD candidate in English Language Teaching, Arab American University, Jenin) is auditing its linguistic terminology before it goes to Cambridge NLP.

### What is done
- Four grammar engines (`morph_efficiency_project/scripts/engines/`) at 100% test pass across 4,343 tests
- Sentence-grammar layer (`morph_efficiency_project/scripts/engines/grammar/`) with context-aware POS resolution and structural validation
- Tokenisation pipeline (`morph_efficiency_project/scripts/tokenize_for_training.py`) with per-(lang, surface) memoisation; full-corpus runs complete for all four languages on disk in `mini_experiment/data/` (.npy files gitignored, vocab JSONs at `mini_experiment/tokenizers/` are tracked)
- Multi-stream MiniGPT architecture (`mini_experiment/run_mini.py`) supporting 1/2/4 input embedding streams with parameter-matched comparison
- Trainer (`morph_efficiency_project/scripts/train_model.py`) — cosine LR + AdamW + checkpointing + resume
- AWS SageMaker launcher (`morph_efficiency_project/scripts/aws/launch_run.py`) with dry-run and `--deploy` modes
- Phase 2 results at `results/phase2_fourlang/` and `results/phase2_seeds/`; engine and pilot metrics at `results/analysis/`
- Manuscript (`manuscript/tex/`, the single source) reporting Phase 2 in §6; the journal-template build in `manuscript/tex_cambridge/` reads the same sections (see `manuscript/README.md`)
- Audit reports + bundle distribution Zipf plots at `morph_efficiency_project/logs/summary/`
- Pipeline diagrams at `pipeline_diagrams.html` with Mermaid algorithm flowcharts plus data-flow SVGs
- 8-cell rehearsal smoke test passing (each cell trains a tiny model for 234 steps on CPU, all checkpoints save cleanly)

### What is NOT done (and is yours when Sameh says go)
1. **Submission.** Fold in the reviewer's terminology corrections, add his acknowledgement to both `tex/main.tex` and `tex_cambridge/main.tex` (approved wording: "The author is also grateful to Tawfiq Omar Abuaisha, PhD candidate in English Language Teaching at the Department of Educational Sciences, Arab American University, Jenin, for reading the manuscript and reviewing its linguistic terminology."), commit the staged manuscript work (with permission), build the Cambridge version on Sameh's machine, submit.
2. **Phase 3.** Originally scoped as a Turkish reasoning SLM, but Phase 2 found no rebate for Turkish and a real one only for Arabic, so the direction itself is open (the paper's own programme points at cross-Semitic replication, e.g. the first-milestone Hebrew engine). Sameh has not specified it. Do not infer; wait for him.

---

## Quick verification of project health

If you just inherited this and want to confirm nothing rotted:

```bash
# 1. Test suite (expect 4,343 passing)
python -X utf8 -m pytest morph_efficiency_project/tests/ -q

# 2. Local CPU smoke training (expect monotonic loss decrease in ~30s)
python morph_efficiency_project/scripts/train_model.py \
    --lang en --regime baseline --model-dim 64 --layers 2 \
    --max-tokens 50000 --batch-size 4 --seq-len 32 \
    --eval-every 100 --save-every 500 \
    --output-dir /tmp/smoke_en_baseline

# 3. Manuscript build (expect a ~29-page PDF, zero Missing-character warnings)
cd manuscript/tex && xelatex main && bibtex main && xelatex main && xelatex main

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

- **Tashkil**: Arabic words in the manuscript are fully vocalised by default, and a new Arabic word should be vocalised too, with two exceptions. (1) A word cited *for its ambiguity* stays unvocalised, because the harakat would resolve the very ambiguity the example illustrates: write `مدرسة` (*madrasa* "school" or *mudarrisa* "female teacher"), never `مَدْرَسَة`. (2) A root is always a bare, hyphenated consonantal skeleton (`ك-ت-ب`, `م-ص-ر`), never a vocalised word such as `مِصْر`. Patterns are cited in full, final vowel included (`اسْتَفْعَلَ`). The external reviewer flagged a vocalised ambiguity example in November 2026; the audience will catch these.
- **polyglossia**: loaded in `manuscript/tex/main.tex`. Arabic uses the `\ar{...}` macro for proper RTL rendering. Mandarin uses `\zh{...}` for the SimSun CJK font. The Cambridge class cannot take polyglossia, so `tex_cambridge/main.tex` defines the same two macros with fontspec alone.
- **Manuscript layout conventions**: floats `[H]`, each placed directly after the paragraph that first refers to it, so no sentence is ever split around a figure or table (Sameh's choice, November 2026; `[tbp]` let floats interrupt sentences mid-page), no run-in `\paragraph{}` headings in the body, text edited only in `manuscript/tex/`.
- **TR engine speed**: the worst case is ~25 ms/word without caching. The tokeniser has a per-(lang, surface) memoisation cache that cuts TR full-corpus from ~30 hours to ~16 minutes. Do not remove the cache without measuring.
- **Bundle counts shift with corpus size**. The 20k-sample audit (from `compute_bundle_space.py`) and the full-corpus tokeniser produce slightly different `observed` numbers for the bundle stream. Both are correct for their respective sample. The diagrams and the manuscript already document the difference.
- **The five spare engines** (German, Spanish, Hungarian, Swahili, Basque) were removed earlier. They are in git history if you need to resurrect them, but the project's headline scope is the four languages.

---

## Open decisions waiting on Sameh

1. **When to commit** the staged manuscript and cleanup work (see the Git workflow rules).
2. **Phase 3 spec**: direction, scale, data, benchmarks, release path. Do not infer; wait for him.

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
| `manuscript/README.md` | How the paper is built: one source, two builds, deploy steps |
| `manuscript/tex/main.tex` | Manuscript root (public PDF); sections at `manuscript/tex/sections/sec_0*_*.tex` |
| `manuscript/tex/references.bib` | The only bibliography (shared with the Cambridge build) |
| `manuscript/tex_cambridge/main.tex` | Journal-template preamble + end matter; no copy of the text |
| `results/` | Phase 2 readings (`phase2_fourlang/`, `phase2_seeds/`) and analysis metrics (`analysis/`) |
| `docs/` | Pre-submission checklists (publication, citation verification) |
| `archive/` | Superseded drafts, planning notes, old demo site, pilot scripts; see `archive/README.md` |

---

## If something is broken or unclear

Ask Sameh. He prefers a brief precise question over a long preamble. If you need to dispatch agents to investigate something, dispatch them with explicit scope; he is comfortable with that workflow.

Do not silently revert his work. If you see something that looks wrong but might be intentional (a deliberate test-spec choice, a manuscript prose decision, a numeric value), surface it as a question rather than fixing it unilaterally.
