# Reflection: What We Tried, What Broke, and What We Got

*Sameh AbuRadi — March 2026*

---

The original idea was straightforward enough: train six small language models — two per language, one with raw BPE tokenization and one with morphological structure baked in — and see whether the grammar-aware models learn faster or more efficiently. Three languages, three pairs, one clean comparison. The whole thing was supposed to take a few weeks of compute and produce a tidy table of numbers.

It did not go that way.

---

## March 8 — The Start

The instance went up on the evening of March 8th. A dry run first: download 50,000 sentences per language, preprocess, check that all output files exist, wipe, and start the real thing. That part worked. By 21:07 the full download was running.

English hit its 2.5 billion whitespace token target at 77.6 million sentences. Arabic and Turkish did not. The original source list — Wikipedia, CC-100, OPUS-100 — ran dry at 9.6 million and 3.75 million sentences respectively, nowhere near the target. The token counts after baseline preprocessing came back at 350 million for Arabic and 162 million for Turkish. That is not a rounding error. It is a 7× and 15× shortfall.

The fix required finding new sources. The first candidate was OSCAR-2301 — large, well-known, should have been straightforward. It turned out to be gated: the dataset had been suspended pending a manual approval process on Hugging Face that could take weeks. The second candidate was MADLAD-400, freely streamable under CC-BY-4.0, no gating. That one worked. Arabic now had roughly 8.8 billion tokens of combined capacity across all sources; Turkish had around 25.8 billion. Both would easily hit 2.5 billion. The download script was updated to stop the moment the target was reached.

That fix took until March 11th to land. In the meantime, the English morph preprocessing was running.

---

## March 10 — First Reboot

At 10:15 UTC+1 on March 10th, the Vast.ai provider rebooted the instance. Every tmux session died. The English morph preprocessing had reached 36 million of 74 million sentences — roughly 1.2 billion tokens — before it was killed.

The reason all of that work was lost is that `preprocess_morph.py` had no checkpointing at the time. It processed everything in memory and only wrote output after the final merge. A crash meant zero output saved. Thirty-nine hours of instance time at $1.228/hr, gone. The balance at that point was around $76.

The response was to rewrite the pipeline with chunk-level checkpointing: each of the 32 parallel workers saves its output `.npz` to disk immediately on completion, and a restart skips any chunk whose file already exists. The script was also switched from single-threaded to 32 parallel workers, cutting the expected processing time from roughly 85 hours to 6–10. A local monitoring script was added to send a Windows notification if the instance went quiet unexpectedly.

---

## March 11 — The Deadlock

The restarted preprocessing ran well. By 03:55 UTC+1 on March 11th, 27 of 33 chunks were done. Then it stopped. The workers were alive — CPU at 99% idle — but `multiprocessing.Pool.map()` was hanging, waiting on results that were never going to come back. Memory pressure on the larger chunks had caused the pool to stall.

Killing and restarting with 6 workers deadlocked again at 28/33. Dropping to a single worker produced corrupt output: one chunk was written as if it were the entire dataset, falsely resuming from `chunk_00000`. That output was deleted.

The actual fix was `maxtasksperchild=1` in the Pool constructor, which recycles each worker process after completing one chunk. That prevents memory from accumulating across tasks. The resume size threshold was also raised to 500MB to reject any partial output from the single-worker incident. With those changes in place, the remaining chunks ran cleanly.

---

## March 12 — Second Reboot

At 00:50 UTC+1 on March 12th, the instance rebooted again. This time the preprocessing was at 28/33 chunks and had been deadlocked since the previous morning — so the reboot itself did not cost new compute, but it wiped `/workspace/BA_01/morph_efficiency_project/data/processed/` entirely.

Twenty-four of the 28 completed chunks had been backed up locally the day before. Those were re-uploaded. The pipeline resumed from chunk 24, finished all 33 chunks by 13:44 UTC+1, and the merge completed at 15:33. Final output: 9.4GB of token arrays and feature ID arrays for training, 239MB each for val and test. Roughly 2.5 billion tokens, 18 feature bundles. Everything backed up locally immediately.

English baseline training started at 18:14 that evening and finished at 23:20 — about five hours, 76,293 steps, 2,499,969,024 tokens. The full Chinchilla budget.

---

## March 13 — The Vocabulary Problem

English morph training failed to start. CUDA out-of-memory: tried to allocate 38.74 GiB. The morph tokenizer had produced 27,079,783 unique root-POS tokens. An embedding table for that vocabulary in bfloat16 would have been roughly 41GB — larger than the A100's memory.

The fix was to cap the vocabulary at the top 50,000 tokens by frequency and remap everything else to `<unk>`. A 50,000-token embedding table is about 77MB. The cap script ran on the instance, remapped all token ID arrays, and reported an unknown token rate of 10.68%. Training started at 23:54 and finished around 05:35 the following morning — 5.7 hours, same step count, same token budget.

Evaluation ran the same day. English baseline: test PPL 39.42. English morph: test PPL 55.47. The morph number is higher, which is the wrong direction if you are hoping to confirm the hypothesis. The most likely explanation is the 10.68% unknown rate: every `<unk>` token carries a loss penalty that the baseline model never sees, because its BPE vocabulary covers the corpus almost completely. The raw perplexity numbers are not directly comparable across regimes.

The morphological evaluation is more interesting. The morph model packs 4.91 tokens per meaning unit against 1.0 for the baseline — each morph token carries roughly five times as much morphological information. Agreement accuracy came back at 100%, which is expected given that the feature bundles are injected as structured inputs rather than inferred from text.

---

## March 14 — Where It Ended

Arabic and Turkish baseline models were trained on the same instance, both reaching 76,293 steps and the full 2.5 billion token budget. The AR checkpoint is at `models/ar_baseline/ckpt_step0076293.pt`, backed up locally. The TR checkpoint is at `models/tr_baseline/ckpt_step0076293.pt`.

The evaluation for both was queued and running when the credits ran out. The Turkish processed data also turned out to be the old 162-million-token set — the re-preprocessing had been scheduled but not yet confirmed complete. That is the last thing that needs to happen before the AR and TR numbers exist.

The morph models for Arabic and Turkish were never trained. That was always the more expensive half of the experiment, and it was explicitly deferred after the second reboot. The grammar engines are implemented. The preprocessing pipeline is written and resumable. The training script is the same one that ran for English. Everything is in place.

---

## What This Adds Up To

The balance ledger is roughly: started with $9, added $140 across two top-ups, lost ~$48 to the first reboot, spent the rest on English preprocessing, training, and the AR/TR baseline runs. The full three-language experiment — all six models, all five metrics — is estimated at around €1,800 in total GPU time. What was spent here got one language done and two languages most of the way there.

The infrastructure failures were not random bad luck. Vast.ai's spot-instance model means the provider can reclaim hardware at any time. That is the tradeoff for the low hourly rate, and it is stated in the terms. The lesson is that any experiment running on spot compute needs to be designed from the start to survive arbitrary interruption — not just at the data level, but at the model level too. Checkpointing every thousand steps is the right call. Assuming the instance will stay up for twelve hours is not.

The vocabulary cap problem is more fundamental. The morph tokenizer's explosion to 27 million unique tokens was not anticipated. A 50,000-token cap with a 10.68% unknown rate is a reasonable engineering fix, but it changes what the model is actually learning. A better approach would be to design the morphological vocabulary from the start with a hard size limit — perhaps by clustering feature bundles rather than enumerating all root-POS combinations — so the cap is a design choice rather than a patch applied the night before training.

The English results are a proof of concept, not a conclusion. The pipeline works. The training runs to completion. The evaluation produces numbers. Whether those numbers say anything meaningful about morphological efficiency in language models is a question that requires Arabic and Turkish data to answer.

That data is still out there, waiting.

---

## The Mini Experiment

While the full-scale Arabic and Turkish runs remained incomplete, a separate small-scale pilot was run locally across all three languages — the mini experiment. Two models per language, same architecture as the full run but at 2M parameters, trained on a small data slice. The goal was a directional signal without spending more compute.

The results were cleaner than expected. Turkish morph beat baseline by 57%. Arabic morph beat baseline by 14% — likely understated given that 19% of Arabic tokens were remapped to `<unk>` due to the same vocabulary pressure seen in the full English run. English was essentially flat at 1%, which is the expected result for a language with simple morphology.

The pattern holds exactly as the hypothesis predicted: the more morphologically complex the language, the more the model benefits from being told about its grammar upfront. Turkish, with its agglutinative suffix chains, gains the most. Arabic, with its root-and-pattern system and 270 distinct feature bundles, gains meaningfully. English, with 23 bundles and minimal inflection, gains almost nothing.

Bundle accuracy across all three morph models came back high — the models internalised the grammatical structure rather than memorising it. Token compression was also measurable: morph tokens carry more meaning per unit than BPE fragments, which is the core efficiency argument.

The mini experiment does not confirm the full-scale hypothesis. It is a pilot. But it is a consistent pilot, and consistency across three typologically different languages at small scale is a reasonable basis for expecting the effect to hold at larger scale.

---

## The Presentation

The experiment was documented as an interactive presentation built in plain HTML, CSS, and D3 — no build step, no framework, opens directly in a browser. The design follows the CODE Berlin visual identity: near-black background, accent red, monospace aesthetic.

The presentation covers the full arc: the hypothesis, the tokenisation comparison, the two training pipelines, the grammar engines for all three languages, the mini experiment results across five metrics, the full-scale English results, the deferred Arabic and Turkish runs, and the infrastructure timeline.

The grammar engines slide includes a working decomposition of Arabic root-and-pattern morphology with RTL rendering, tatweel applied correctly at joining boundaries, and form badges (وزن patterns) shown per token in the tokenisation slide — toggled via a collapsible drawer on the Arabic morph chain. The form data was verified against the Arabic grammar engine and manually corrected where the engine misfired on nominal and adjectival patterns (Form II masdar, nisba adjectives), which exposed a known gap in the engine's nominal recognition that is flagged for a future fix.

A presenter notes file (`cards.html`) was built alongside the presentation, styled for mobile use — short trigger phrases per slide rather than scripts, meant to be glanced at while the presentation is on screen.

The presentation is the deliverable. The data is real. The infrastructure story is honest. The gaps are documented.
