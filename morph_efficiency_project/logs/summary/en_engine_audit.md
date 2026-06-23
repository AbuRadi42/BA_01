# English Engine Audit Report

Source suite: `morph_efficiency_project/tests/en_morph/test_en_engine_comprehensive.py`
Engine under test: `morph_efficiency_project/scripts/engines/en_engine.py`
Total cases: **248** (passed **125** / failed **123**, pass rate 50.4%).

Tests were written to assert the *linguistically correct* analysis (lemma,
POS, inflection tags, and full derivation chain). Failures therefore mark
real engine bugs rather than regressions against legacy output.

## 1. Test-category coverage

| # | Category | Cases | Pass | Fail | Pass % |
|---|---|---:|---:|---:|---:|
| 1a | Plural (regular) | 10 | 10 | 0 | 100 |
| 1b | Plural (irregular) | 10 | 10 | 0 | 100 |
| 1c | Possessive 's | 5 | 5 | 0 | 100 |
| 1d | Past (regular) | 7 | 6 | 1 | 86 |
| 1e | Past (irregular) | 10 | 10 | 0 | 100 |
| 1f | Aspect PROG (-ing) | 8 | 6 | 2 | 75 |
| 1g | Aspect PERF (participle) | 8 | 8 | 0 | 100 |
| 1h | 3SG present | 7 | 0 | 7 | 0 |
| 1i | Passive participle | 5 | 5 | 0 | 100 |
| 1j | Degree (regular) | 8 | 8 | 0 | 100 |
| 1k | Degree (irregular) | 8 | 0 | 8 | 0 |
| 2a | Agent -er (NOUN) | 8 | 0 | 8 | 0 |
| 2b | Gerund / deverbal noun | 5 | 1 | 4 | 20 |
| 2c | -ed deverbal ADJ | 4 | 4 | 0 | 100 |
| 2d | -ly ADV | 7 | 0 | 7 | 0 |
| 2e | -ness STATE | 6 | 0 | 6 | 0 |
| 2f | -ment | 5 | 0 | 5 | 0 |
| 2g | -ity | 5 | 0 | 5 | 0 |
| 2h | -ation / -tion | 5 | 0 | 5 | 0 |
| 2i | -ize / -ise | 5 | 0 | 5 | 0 |
| 2j | -ist | 5 | 0 | 5 | 0 |
| 2k | -ism | 4 | 0 | 4 | 0 |
| 2l | -able / -ible | 5 | 0 | 5 | 0 |
| 2m | Misc deriv suffix (POS) | 14 | 0 | 14 | 0 |
| 3  | Derivational prefixes | 36 | 19 | 17 | 53 |
| 4  | Multi-step derivation | 9 | 0 | 9 | 0 |
| 5  | Phrasal verb base | 8 | 8 | 0 | 100 |
| 6a | Solid compounds | 5 | 4 | 1 | 80 |
| 6b | Hyphenated compounds | 4 | 4 | 0 | 100 |
| 7a | Numerals | 3 | 3 | 0 | 100 |
| 7b | Abbreviations | 4 | 4 | 0 | 100 |
| 7c | Hyphenated prefix | 3 | 1 | 2 | 33 |
| 7d | Foreign loans | 4 | 4 | 0 | 100 |
| 8  | -er agent vs comparative | 8 | 3 | 5 | 63 |
| **Total** | | **248** | **125** | **123** | **50.4** |

## 2. Top 10 failure patterns

1. **Derivational suffix not detected; POS stays UNKNOWN.** The engine's
   `_step_b` only walks the suffix list when `_step_a` returned UNKNOWN, and
   even then it never re-assigns POS based on the suffix's `derives` slot.
   Examples: `darkness` (pos=UNKNOWN, expected NOUN), `quickly` (UNKNOWN, ADV),
   `modernize` (UNKNOWN, VERB), `artist` (UNKNOWN, NOUN), `readable`
   (UNKNOWN, ADJ).

2. **Agent -er mis-tagged as comparative ADJ.** `_step_a` strips any
   trailing -er with `degree=COMP, pos=ADJ` whenever the word is longer
   than 4 chars. There is no disambiguation against agent-noun -er.
   Examples: `writer`, `painter`, `lawyer`, `singer`, `dancer`, `runner`.

3. **Inflectional plural shadows derivation.** `researchers` falls through
   the `endswith("s")` branch and yields `root=researcher, num=PL`, never
   reaching derivational stripping. Same gap: any derived noun in plural
   form loses its derivation chain.

4. **Irregular comparative/superlative lemmas missing.** `better`, `worse`,
   `best`, `worst`, `more`, `most`, `less`, `least` all fall through to the
   regular -er/-est stripper, producing nonsense roots (`bett`, `mor`,
   `les`). They are absent from `en_irregulars.json` or not surfaced.

5. **3SG -s not tagged as VERB.** `walks`, `runs`, `eats` etc. land in the
   `endswith("s")` plural branch. The `COMMON_VERBS` check only adds
   `ambig_3sg=YES` while still returning `pos=NOUN, num=PL`. The 3SG
   reading is never selected.

6. **Multi-step derivation absent.** `_step_b` strips at most one suffix
   and one prefix, then returns. `_step_c` re-invokes `_step_b` four times
   but only on the *stem*, and never on UNKNOWN paths that succeeded once.
   Result: `ungodliness` -> `godli` (un- and -ly never removed),
   `denationalisation` -> `nationalis`, `antiestablishmentarianism` ->
   only top suffix.

7. **Past-participle / re-prefix interaction broken.** `rethought` is an
   irregular past-participle of `rethink`. The engine looks up `rethought`,
   misses, strips `re-`, then leaves `thought` as the root with
   `pos=UNKNOWN` and no tense tag. Should produce `root=think,
   chain=[re->REPETITION], tense=PAST, aspect=PERF`.

8. **Silent-e restoration loses base for -ly.** `simply` -> `simpl` (should
   be `simple`); `happily` -> `happi` (should be `happy`, with y-restoration);
   `walking` -> `walke` (over-restores silent-e on plain stems).

9. **Several common prefixes silently missed.** `dis-`, `in-`, `im-`,
   `il-`, `ir-`, `de-` (on `deactivate`), `mid-`, `fore-`, `em-`, `mega-`,
   `non-` (on `nonfiction`), `post-` (on `postwar`), `anti-` (on `antiwar`,
   `antisocial`) are not in the prefix surface-variant list, or are
   shadowed by suffix-stripping that fires first.

10. **No -ation / -tion / -ize lemma restoration.** Even when the suffix
    matches, the resulting stem is the raw truncated form (`educ`,
    `creat`, `decide` -> wrong) rather than the verb lemma. There is no
    map from derived form back to base verb.

## 3. Specific bugs in priority order

| # | Bug | Severity | Fix sketch |
|---|---|---|---|
| B1 | Agent -er never disambiguated; every -er word becomes COMP-ADJ | Critical | Add a list/heuristic: if the -er stem is in the verbs corpus or matches a derivation rule for AGENT, emit NOUN+derivation chain instead of COMP-ADJ. |
| B2 | Derivational stripping never updates POS or tags | Critical | After `_step_b` matches a suffix, use its `derives` field to overwrite POS (NOUN/ADJ/VERB/ADV) and clear inflection tags carried over from `_step_a`. |
| B3 | Multi-step recursive decomposition missing | Critical | `_step_c` must keep stripping prefixes AND suffixes (and accumulate chain) until no rule applies, ordered: inflection -> outer suffix -> outer prefix -> inner. |
| B4 | 3SG present misclassified as plural noun | High | When `endswith('s')` and base is in `COMMON_VERBS`, emit (VERB, tense=PRES, person=3SG) instead of (NOUN, num=PL, ambig_3sg=YES). |
| B5 | Irregular comparatives/superlatives missing from irregulars table | High | Add `better/best/worse/worst/more/most/less/least/further/farther` entries pointing to `good/bad/much/little/far`. |
| B6 | Past-participle of derived verbs (e.g. rethought) not analyzed | High | After matching a prefix in `_step_b`, look the remainder up in `irregulars` to recover the past-participle lemma and tags. |
| B7 | Silent-e and y-restoration too aggressive for non-verb -ing/-ly stripping | High | Gate silent-e restoration on whether the stripping rule is inflectional vs derivational; for -ly, restore -y from -i (`happi` -> `happy`) and never add silent-e. |
| B8 | Many common prefixes absent or shadowed | Medium | Audit `en_derivations.json` for `dis-, in-, im-, il-, ir-, de-, em-, mid-, fore-, mega-`. Where present, ensure `_step_b` tries them even when `_step_a` already produced a non-UNKNOWN POS. |
| B9 | Inflection blocks derivation (`researchers` -> `researcher`) | Critical | After inflectional stripping, ALWAYS attempt derivational decomposition on the resulting stem. Do not gate derivation on `pos == UNKNOWN`. |
| B10 | Hyphenated derivational prefixes (`re-evaluate`, `co-operate`) untokenized | Medium | Pre-process: split on internal hyphens, analyze each piece, then re-assemble surface; or add hyphen-aware prefix matching. |
| B11 | Solid compound `bookshop` not split | Low | Add `bookshop` and similar high-frequency compounds to `en_compounds.json` or implement a longest-suffix match against a constituent inventory. |
| B12 | Gerund / deverbal nouns always tagged as PROG-VERB | Medium | When -ing word appears in a subject/object slot or matches a known deverbal-noun list (`building, meaning, painting`), emit NOUN with a GERUND/NOMINALIZATION tag. Requires either a list or sentence-level context. |

## 4. What the engine handles correctly

These categories had >= 80% pass rate and represent the engine's solid core:

- Regular noun plural (10/10) and irregular noun plural (10/10): the
  irregulars table is comprehensive for nouns.
- Possessive 's (5/5).
- Irregular verb past (10/10) and past participles (8/8): irregular verb
  coverage is excellent.
- Regular past -ed stripping (6/7) and regular comparative/superlative
  (8/8): the inflectional stripper works well for these.
- Phrasal verb base detection (8/8): `phrasal_verb_base=YES` tag fires
  reliably for the common particle verbs.
- Compounds (8/9 across solid + hyphenated): the `en_compounds.json`
  lookup handles the cases it covers correctly.
- Numerals, abbreviations, foreign loans (11/11): the engine correctly
  declines to over-analyze.
- Two of the three regular comparatives in the -er disambiguation suite
  (`taller`, `faster`, `older`) succeed, which means once agent vs
  comparative is disambiguated upstream, the COMP path is sound.

The engine's strengths are dictionary-backed (irregulars, compounds,
phrasal verbs) and simple inflection stripping. Its weaknesses are
everything that requires (a) recursive/iterative decomposition, (b)
POS re-assignment from derivational evidence, or (c) disambiguation
between inflection and derivation that share a surface form.
