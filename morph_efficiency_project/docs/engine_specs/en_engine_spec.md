# English Engine Design Specification

**Language:** English (en)
**Typology:** Semi-fusional analytic
**Engine file:** `scripts/engines/en_engine.py`
**Status:** Built, audited, tested (Phase 0 complete)

---

## Morphological Overview

English is a predominantly analytic language that encodes most grammatical relationships through fixed word order (SVO) and function words rather than through rich inflectional morphology. Compared to fusional languages like Arabic or agglutinative languages like Turkish, English has an exceptionally shallow morphological system: nouns distinguish only singular vs. plural (and possessive), verbs carry at most tense and aspect marking, and adjectives inflect only for degree (comparative/superlative). Case is vestigial, surviving only in the pronoun system (I/me, he/him, etc.).

English morphological processes fall into three broad categories. Inflection is the most constrained: regular verbs use just four suffixes (-s, -ed, -ing, -en), nouns add -s/-es for plural, and adjectives take -er/-est for degree. Irregular inflection covers roughly 200 high-frequency verbs (went, sang, been) and several dozen nouns (children, mice, oxen) and must be handled by explicit lookup. Derivation is far more productive, with dozens of Latinate and Germanic suffixes (-tion, -ness, -able, -ful, -ize, etc.) and prefixes (un-, re-, pre-, dis-, etc.) that change a word's part of speech or meaning. Compounding (e.g., software, bookshelf, sunflower) is orthographically fused into single tokens in English, unlike languages where compounds are transparently segmented.

Because English carries so little information per word-form, its morphological efficiency ratio is expected to be the lowest among the nine languages in this experiment. A typical English word produces a feature bundle containing at most 2-3 feature-value pairs (e.g., `pos=VERB|tense=PAST`), whereas an Arabic or Turkish word may produce 6-8. English therefore serves as the low-end baseline: the point of minimal morphological encoding density against which more morphologically rich languages are measured.

Conversion (zero-derivation) is another common English process where words shift part-of-speech without any overt morphological marking (e.g., "run" as both noun and verb, "clean" as both adjective and verb). The engine does not explicitly model conversion but handles it implicitly: words that do not match any inflectional or derivational pattern receive POS = UNKNOWN, which downstream components can resolve via context.

## Closed-Class Intercept

The engine maintains a static dictionary of 110 closed-class words (class attribute `CLOSED_CLASS`, lines 34-78) that are intercepted at the very beginning of Step A and bypass all inflectional stripping, derivational detection, and root extraction. Each entry maps a lowercased surface form to a `(POS, tags)` tuple.

The categories and their members are:

**Determiners (DET) -- 3 entries:**
`the`, `a`, `an`

**Prepositions (PREP) -- 35 entries:**
`to`, `of`, `in`, `at`, `by`, `for`, `with`, `on`, `from`, `about`, `into`, `through`, `during`, `before`, `after`, `above`, `below`, `between`, `under`, `over`, `against`, `along`, `among`, `around`, `behind`, `beneath`, `beside`, `beyond`, `despite`, `except`, `inside`, `outside`, `toward`, `towards`, `until`, `within`, `without`

**Pronouns (PRON) -- 40 entries:**
Personal: `i`, `me`, `you`, `he`, `him`, `she`, `her`, `it`, `we`, `us`, `they`, `them`
Possessive: `my`, `mine`, `your`, `yours`, `his`, `hers`, `its`, `our`, `ours`, `their`, `theirs`
Interrogative/relative: `who`, `whom`, `whose`, `which`, `that`, `what`
Demonstrative: `this`, `these`, `those`
Reflexive: `myself`, `yourself`, `himself`, `herself`, `itself`, `ourselves`, `yourselves`, `themselves`

**Conjunctions (CONJ) -- 18 entries (those not already assigned as PREP):**
`and`, `but`, `or`, `nor`, `so`, `yet`, `although`, `because`, `since`, `unless`, `while`, `if`, `when`, `where`, `as`, `though`, `whereas`, `whether`

Note: `for`, `after`, `before`, and `until` are listed in the conjunction source list but are already registered as PREP and are not overwritten (line 70: `if _w not in CLOSED_CLASS`).

**Auxiliary/Modal Verbs (AUX) -- 12 entries:**
`can`, `could`, `will`, `would`, `shall`, `should`, `may`, `might`, `must`, `ought`, `need`, `dare`
All receive the additional tag `modal=YES`.

Additional auxiliary forms (`do/does/did`, `have/has/had`, `am/is/are/was/were/be/been/being`) are handled through `en_irregulars.json` rather than the closed-class dictionary (see comment at line 80-81).

Total unique entries in `CLOSED_CLASS`: **110** (some words like `for` appear in multiple source lists but are stored only once, with PREP taking priority).

## Step A: Inflectional Stripping

Step A (`_step_a`, lines 138-198) takes a single word, lowercases it, and attempts to identify its inflectional morphology. It returns a tuple of `(stem, tags_dict, pos)`. The rules are checked in strict priority order; the first match wins.

### 1. Closed-Class Lookup (line 142)
If the lowercased word is in `CLOSED_CLASS`, return immediately with the pre-assigned POS and tags. No further processing.

### 2. Irregular Form Lookup (lines 146-153)
If the word appears as a key in `en_irregulars.json` (534 entries), the engine reads the entry's `base`, `pos`, and `tag` fields. The tag string (pipe-delimited key=value pairs like `"tense=PAST|person=3"`) is parsed into a dictionary. Examples:
- `"went"` -> base=`go`, pos=`VERB`, tags=`{tense: PAST}`
- `"children"` -> base=`child`, pos=`NOUN`, tags=`{num: PL}`
- `"better"` -> base=`good`, pos=`ADJ`, tags=`{degree: COMP}`

### 3. Possessive `'s` (lines 154-155)
Pattern: word ends with `'s`.
Action: strip the final 2 characters, assign `{poss: YES}`, POS = `NOUN`.
Example: `"dog's"` -> stem=`dog`, tags=`{poss: YES}`.

### 4. Progressive `-ing` (lines 156-162)
Pattern: word ends with `ing` AND length > 5.
Restoration logic:
- **Doubled consonant undoubling:** If the stem (after removing `-ing`) ends with two identical consonants that are not vowels, the final consonant is removed. E.g., `"running"` -> `runn` -> `run`.
- **Silent-e restoration:** Otherwise, if the stem ends in a non-vowel, `e` is appended. E.g., `"making"` -> `mak` -> `make`.
Tags: `{tense: PRES, aspect: PROG}`, POS = `VERB`.

### 5. Past Tense `-ed` (lines 163-183)
Pattern: word ends with `ed` AND length > 4.
Restoration logic (lines 165-181):
- **Doubled consonant undoubling (Bug 5 fix):** If the stem ends with two identical non-vowel consonants, attempt to remove the last one. A safety check (line 169) ensures the undoubled result is longer than 2 characters -- this prevents `"added"` -> `add` -> `ad` (incorrect). E.g., `"stopped"` -> `stopp` -> `stop`.
- **Silent-e restoration (Bug 2 fix):** Only applied when the stem ends in a vowel-consonant (VC) sequence (line 177-180), the final character is not `y`, and the final character is not a vowel. This prevents false restoration on stems ending in CC like `walk` or `talk`. E.g., `"loved"` -> `lov` -> `love`, but `"walked"` -> `walk` (no `e` added).
Tags: `{tense: PAST}`, POS = `VERB`. Note: `aspect=PERF` was explicitly removed per Bug 4 fix (line 182 comment).

### 6. Plural `-ies` (lines 184-185)
Pattern: word ends with `ies` AND length > 4.
Action: replace `-ies` with `-y`. E.g., `"cities"` -> `city`.
Tags: `{num: PL}`, POS = `NOUN`.

### 7. Plural `-es` (lines 186-187)
Pattern: word ends with `es` AND length > 4.
Action: strip the final 2 characters. E.g., `"boxes"` -> `box`.
Tags: `{num: PL}`, POS = `NOUN`.

### 8. Plural/3SG `-s` (lines 188-193)
Pattern: word ends with `s` AND length > 3 AND does not end with `ss`.
The `ss` guard prevents words like `"glass"`, `"moss"` from being incorrectly stripped.
Action: strip the final `s` to get the base form.
**3SG disambiguation (Bug 3 fix):** If the base form is found in `COMMON_VERBS` (a set of ~100 high-frequency verbs, lines 84-100), the engine records `{num: PL, ambig_3sg: YES}` to flag that this form is ambiguous between a plural noun and a 3rd person singular present verb. Otherwise, tags are simply `{num: PL}`.
POS = `NOUN` in both cases (the ambiguity tag allows downstream consumers to resolve).
Example: `"runs"` -> base=`run`, and since `run` is in `COMMON_VERBS`, tags=`{num: PL, ambig_3sg: YES}`.

### 9. Superlative `-est` (lines 194-195)
Pattern: word ends with `est` AND length > 5.
Action: strip 3 characters. E.g., `"tallest"` -> `tall`.
Tags: `{degree: SUPER}`, POS = `ADJ`.

### 10. Comparative `-er` (lines 196-197)
Pattern: word ends with `er` AND length > 4.
Action: strip 2 characters. E.g., `"taller"` -> `tall`.
Tags: `{degree: COMP}`, POS = `ADJ`.

### 11. Default (line 198)
If no rule matches, the word is returned unchanged with empty tags and POS = `UNKNOWN`.

## Step B: Derivational Detection

Step B (`_step_b`, lines 200-218) attempts to identify one layer of derivational morphology on the stem produced by Step A. It returns the stripped stem and a derivation chain (list of strings). Critically, Step B only runs when Step A assigned POS = `UNKNOWN` (line 235-236 in `analyze`), meaning it only processes words that could not be analyzed inflectionally.

### Compound Check (lines 203-208)
Before suffix/prefix matching, Step B checks whether the stem is a known compound in `en_compounds.json` (170 entries). If found, the head constituent (last element of the `constituents` array) is extracted, and a chain entry like `COMPOUND(soft+ware)` is recorded. The head's stem is returned. Example: `"software"` -> head stem = `ware`, chain = `["COMPOUND(soft+ware)"]`.

### Suffix Matching (lines 210-213)
The engine holds 81 suffix surface variants derived from 49 suffix rules in `en_derivations.json`. These are sorted longest-first (line 109-113) to ensure greedy matching (e.g., `-ation` is tried before `-tion`). Hyphens are stripped from surface variants during loading (Bug 1 fix, line 110).

For each suffix variant, the engine checks:
1. The stem ends with the suffix string.
2. The remaining stem after stripping is at least 3 characters long (line 211: `len(stem) - len(surface) >= 3`).

If matched, a chain entry like `tion->ACTION_NOUN` is recorded, and the stripped stem is returned. Only the first (longest) match is used.

### Prefix Matching (lines 214-217)
Similarly, 32 prefix surface variants from 31 prefix rules are checked, also sorted longest-first. The same minimum-remainder guard of 3 characters applies. Chain entries follow the same format (e.g., `un->NEG_REVERSAL`).

### Examples
- `"unhappiness"`: Step A produces POS=UNKNOWN (no inflectional match). Step B suffix-matches `-ness` -> chain `["ness->STATE_QUALITY_NOUN"]`, stem = `unhappi`. (Further derivation via Step C.)
- `"rebuilding"`: Step A strips `-ing` to get `rebuild` with POS=VERB. Since POS is not UNKNOWN, Step B is skipped entirely. The root stays `rebuild`.

## Step C: Root Extraction

Step C (`_step_c`, lines 220-227) performs iterative deepening by re-applying Step B up to 4 additional times. This handles multi-layered derivations where a word has been built up through successive affixation.

- **Maximum iterations:** 4 (line 222).
- **Stopping condition:** Step B returns the same stem it received (no further stripping possible, line 224).
- **Output:** The final irreducible root.

Like Step B, Step C only runs when Step A assigned POS = `UNKNOWN` (line 237). For inflectionally analyzed words, the Step A stem is used directly as the root.

Example of multi-layer stripping: `"internationalization"` could be stripped as `-tion` -> `internationaliza` -> `-ize` -> `international` -> `inter-` -> `national` -> `-al` -> `nation` (4 iterations).

## Compound Handling

Compounds are checked within Step B (lines 203-208) using the dictionary loaded from `en_compounds.json` at initialization (lines 121-125). The config file contains 170 compound entries, each with the following structure:

```json
{
  "compound": "software",
  "constituents": [
    {"stem": "soft", "pos": "ADJ"},
    {"stem": "ware", "pos": "NOUN"}
  ],
  "compound_type": "N+N",
  "semantic_relation": "INSTRUMENT",
  "gloss": "programs for computers"
}
```

When a stem matches a compound entry, the engine extracts the **head constituent** (the last element of the `constituents` array, following English right-headedness) and records a `COMPOUND(stem1+stem2+...)` chain entry. The head's stem becomes the new working stem for further derivational analysis.

## Phrasal Verb Handling

Phrasal verbs are loaded from `en_phrasal_verbs.json` (463 entries) at initialization (lines 128-136). Each entry has the structure:

```json
{
  "verb": "give",
  "particle": "up",
  "token": "give_up",
  "pos": "VERB",
  "meaning": "stop doing / surrender",
  "transitivity": "BOTH",
  "separable": true,
  "register": "NEUTRAL",
  "example": "She gave up smoking. / He gave up."
}
```

The engine builds two indexes:
1. `self.phrasal_verbs`: keyed by `token` (e.g., `"give_up"`).
2. `self.phrasal_verb_components`: keyed by `verb` (e.g., `"give"` -> list of all phrasal verbs using `give`).

During `analyze()` (lines 243-245), if the lowercased surface form matches a verb in `phrasal_verb_components`, the tag `phrasal_verb_base=YES` is added. This flags words like `"give"`, `"take"`, `"put"` that serve as bases for phrasal verb constructions, enabling downstream sentence-level processing to identify multi-word phrasal verbs.

## Tag Inventory

### Part of Speech Values

| POS Value | Description |
|-----------|-------------|
| `NOUN`    | Common noun (includes plural, possessive forms) |
| `VERB`    | Verb (includes past, progressive forms) |
| `ADJ`     | Adjective (includes comparative, superlative forms) |
| `ADV`     | Adverb (handled via derivational detection or irregulars) |
| `DET`     | Determiner (the, a, an) |
| `PREP`    | Preposition (35 entries) |
| `PRON`    | Pronoun (personal, possessive, interrogative, demonstrative, reflexive) |
| `CONJ`    | Conjunction (coordinating and subordinating) |
| `AUX`     | Auxiliary/modal verb (can, could, will, would, shall, should, may, might, must, ought, need, dare) |
| `UNKNOWN` | No inflectional pattern matched; word passed to Steps B/C for derivational analysis |

### Feature Tags

| Tag Key | Possible Values | Producing Step | Description |
|---------|----------------|----------------|-------------|
| `num` | `PL` | Step A (inflection or irregular lookup) | Plural number |
| `poss` | `YES` | Step A (possessive `'s`) | Possessive marking |
| `tense` | `PAST`, `PRES` | Step A (inflection or irregular lookup) | Tense of verb |
| `aspect` | `PROG`, `PERF`, `SIMPLE` | Step A (irregular lookup only; `-ing` sets `PROG`) | Aspect of verb |
| `person` | `1`, `2`, `3` | Step A (irregular lookup only) | Person agreement |
| `voice` | `ACT`, `PASS` | Step A (irregular lookup only) | Voice of verb |
| `degree` | `COMP`, `SUPER` | Step A (inflection or irregular lookup) | Degree of adjective/adverb |
| `modal` | `YES` | Closed-class intercept | Word is a modal auxiliary |
| `ambig_3sg` | `YES` | Step A (`-s` stripping, Bug 3) | Plural noun form is ambiguous with 3SG present verb |
| `phrasal_verb_base` | `YES` | `analyze()` (phrasal verb tagging) | Word serves as a base verb for phrasal verb constructions |
| `gender` | `MASC`, `FEM`, `NEUT` | Step A (irregular lookup, for pronouns) | Grammatical gender (limited to pronouns in English) |

### Bundle Count

English is expected to produce the lowest feature bundle count among all nine languages in this experiment. The theoretical bundle space is small because:

1. **Noun bundles:** `no_features`, `num=PL`, `poss=YES`, `num=PL|ambig_3sg=YES` -- approximately 4 core bundles.
2. **Verb bundles:** `tense=PAST`, `tense=PRES|aspect=PROG`, plus irregular combinations involving `person`, `aspect`, `voice` -- approximately 10-15 bundles.
3. **Adjective bundles:** `degree=COMP`, `degree=SUPER` -- 2 bundles.
4. **Closed-class bundles:** `no_features` (for DET, PREP, PRON, CONJ), `modal=YES` (for AUX) -- 2 bundles.
5. **UNKNOWN:** `no_features` -- 1 bundle.

The total observed bundle count is expected to fall in the range of 15-25 unique bundles, compared to 50+ for Turkish and 80+ for Arabic, reflecting English's minimal morphological encoding.

## Config Files

| File | Entries | Structure | Purpose |
|------|---------|-----------|---------|
| `en_irregulars.json` | 534 | `Dict[surface_form, {base, pos, tag}]` -- tag is pipe-delimited `key=value` pairs | Irregular inflectional forms: nouns (children, mice), verbs (went, sang, been), adjectives (better, worst), and auxiliary verb forms (am, is, are, was, were, do, does, did, have, has, had) |
| `en_derivations.json` | 80 rules (49 suffix, 31 prefix) yielding 81 suffix variants + 32 prefix variants | `List[{affix, surface_variants[], type, direction, derives, notes, examples}]` | Derivational affixes with their surface spelling variants, directionality (e.g., V->N), semantic derivation type (e.g., ACTION_NOUN), and usage notes |
| `en_compounds.json` | 170 | `List[{compound, constituents[{stem, pos}], compound_type, semantic_relation, gloss}]` | Known compound words with constituent breakdown, compound type classification, and semantic relation between parts |
| `en_phrasal_verbs.json` | 463 | `List[{verb, particle, token, pos, meaning, transitivity, separable, register, example}]` | Phrasal verb entries with verb-particle combinations, transitivity information, separability, register level, and example sentences |

## Validators

### Word-level: `check_morph_sequence_en`

Defined in `shared.py` (lines 77-98). Validates that each token's tag bundle is internally consistent for its POS. The allowed tag keys per POS are:

| POS | Allowed Tag Keys |
|-----|-----------------|
| `NOUN` | `num`, `poss`, `ambig_3sg` |
| `VERB` | `tense`, `aspect`, `person`, `voice`, `phrasal_verb_base` |
| `ADJ` | `degree` |
| `ADV` | `degree` |

Additional constraints for VERB:
- If `aspect=PERF`, then `tense` must be `PAST`, `PRES`, or absent (line 90-91).
- If `voice=PASS`, then `aspect` must be `PERF`, `SIMPLE`, or absent (line 92-93).

The function returns `True` if all tokens pass validation, `False` on the first violation. Tags on POS values not listed above (DET, PREP, PRON, CONJ, AUX, UNKNOWN) are not checked.

### Sentence-level: `validate_sentence_structure_en`

Defined in `shared.py` (lines 153-164). Validates cross-token structural constraints:

1. **Degree tag restriction (lines 155-157):** `degree=COMP` or `degree=SUPER` must only appear on tokens with POS = `ADJ` or `ADV`. Violation message: `"degree tag on non-ADJ/ADV: {surface}"`.
2. **Perfect aspect tense (lines 158-160):** If `aspect=PERF`, `tense` must be `PAST`, `PRES`, or absent. Violation message: `"PERF aspect without valid tense: {surface}"`.
3. **Possessive on non-noun (lines 161-163):** `poss=YES` must only appear on tokens with POS = `NOUN`. Violation message: `"possessive on non-NOUN: {surface}"`.

Returns a `(bool, str)` tuple: `(True, "ok")` on success, or `(False, error_message)` on failure.

Both validators are called in `analyze_sentence()` (lines 252-256), with their results ANDed together to produce the final validity flag.

## Known Limitations

1. **No conversion/zero-derivation modeling:** English frequently converts words between POS without morphological marking (e.g., "run" as noun vs. verb). The engine assigns UNKNOWN to bare forms that match no pattern, leaving disambiguation to context.

2. **No 3SG verb form production:** The `-s` suffix is always analyzed as plural NOUN. The `ambig_3sg` tag flags common verbs but does not produce a VERB analysis. A downstream consumer must resolve this.

3. **No irregular comparative/superlative via rules:** Forms like `"better"`, `"best"`, `"worse"`, `"worst"` are handled solely through `en_irregulars.json`. If a form is missing from that file, it will be incorrectly analyzed.

4. **Superlative/comparative length guards may over-strip:** The `-er` rule (length > 4) will match words like `"water"` and strip them to `"wat"`. The `-est` rule (length > 5) will match `"forest"` and strip to `"for"`. These false positives are only partially guarded by length thresholds.

5. **No multi-word expression handling beyond phrasal verbs:** Idioms, collocations, and other multi-word units are not recognized.

6. **Progressive `-ing` restoration heuristics are imperfect:** The doubled-consonant and silent-e rules are heuristic and may produce incorrect stems for unusual words (e.g., words where `-ing` is part of the root like `"bring"`, `"ring"`, `"sing"` -- though these are typically caught by the irregulars lookup).

7. **Derivational analysis only runs on UNKNOWN words:** If Step A incorrectly assigns a POS via inflectional stripping, derivational morphology is never examined. For example, `"darkness"` ending in `-s` would be stripped to `"darknes"` with POS=NOUN (plural) rather than being recognized as a derivation of `"dark"`.

8. **Single derivational match per Step B call:** Step B finds only the first matching suffix or prefix. It does not attempt to find the optimal or longest-overall decomposition.

9. **Phrasal verb tagging is verb-base only:** The engine tags individual verb tokens that participate in phrasal verbs but does not identify the verb-particle combination as a unit across adjacent tokens in a sentence.

10. **Closed-class POS assignment is context-free:** Words like `"that"` (demonstrative pronoun vs. complementizer vs. relative pronoun) always receive PRON regardless of syntactic context.

## Test Coverage

| Test File | Test Count | Categories Covered |
|-----------|-----------|-------------------|
| `test_en_engine_inflection.py` | 14 | Regular/irregular plural, possessive, past tense, progressive, comparative, superlative, silent-e restoration, double-consonant undoubling |
| `test_en_engine_derivation.py` | 10 | Suffix stripping, prefix stripping, derivation chain recording, compound detection |
| `test_en_engine_sentence.py` | 10 | Sentence-level validation, SVO structure checks, multi-token analysis |
| `test_en_engine_regression.py` | 19 | Bug fixes (Bugs 1-9), edge cases for silent-e, doubled consonants, 3SG disambiguation, closed-class words |
| `test_en_engine_smoke.py` | 1 | Basic engine instantiation and single-word analysis |
| `test_en_engine_stress.py` | 50 | High-volume parametrized tests across diverse word forms |
| `test_en_engine_adversarial.py` | 73 | Edge cases, unusual inputs, boundary conditions, false-positive prevention |

**Total: 177 tests across 7 files.**
