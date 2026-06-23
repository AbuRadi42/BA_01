# Mandarin Engine Audit

Test file: `morph_efficiency_project/tests/zh_morph/test_zh_engine_comprehensive.py`

Run: `python -X utf8 -m pytest morph_efficiency_project/tests/zh_morph/test_zh_engine_comprehensive.py -v`

## Totals

| Outcome | Count |
|---|---|
| Passed   | 92  |
| Failed   | 43  |
| XFailed  | 30  |
| **Total** | **165** |

The 30 xfails are the planned radical-class layer (intentionally not yet implemented). The 43 failures document real gaps and bugs in the current engine.

## 1. Test-category coverage

| Category | Tests | Pass | Fail | Xfail | Notes |
|---|---|---|---|---|---|
| Single-char nouns / verbs       | 9   | 0  | 9  | 0  | No monosyllabic open-class lexicon |
| Single-char pronouns            | 5   | 5  | 0  | 0  | All pronouns lexicalized |
| Single-char particles           | 6   | 6  | 0  | 0  | Aspect + sentence-final OK |
| Single-char ADP / CONJ          | 9   | 9  | 0  | 0  | All registered |
| Multi-char conjunctions         | 1   | 1  | 0  | 0  | |
| Bisyllabic nouns                | 4   | 0  | 4  | 0  | No open-class lookup |
| Bisyllabic verbs                | 4   | 0  | 4  | 0  | No open-class lookup |
| Verb reduplication              | 2   | 0  | 2  | 0  | No AA / AABB rule |
| Aspect suffix stripping         | 8   | 8  | 0  | 0  | PERF / DUR / EXP all work |
| Verb+complement+了              | 1   | 1  | 0  | 0  | `看完了` strips cleanly |
| Progressive (在 / 正在)         | 2   | 2  | 0  | 0  | 正在 OK; 在-PROG context not modeled |
| Negation                        | 7   | 7  | 0  | 0  | BU / MEI / BIE all OK |
| Ba-construction                 | 3   | 3  | 0  | 0  | Tag + sentence validator OK |
| Bei-construction                | 3   | 3  | 0  | 0  | Tag + sentence validator OK |
| Classifiers                     | 10  | 9  | 1  | 0  | 只 collides with adverb 只 |
| Modal auxiliaries               | 8   | 7  | 1  | 0  | 愿意 missing |
| Personal pronouns               | 10  | 10 | 0  | 0  | Full set lexicalized |
| Reflexive / inclusive           | 2   | 1  | 1  | 0  | 咱们 missing |
| Demonstratives (bare)           | 4   | 4  | 0  | 0  | |
| Demonstratives + CLF / locative | 4   | 0  | 4  | 0  | 这个/那个/这里/那里 missing |
| NUM + CLF + NOUN                | 3   | 1  | 2  | 0  | NUM/CLF OK; noun head UNKNOWN |
| Sentence-final particles        | 3   | 3  | 0  | 0  | |
| Interrogative pronouns          | 3   | 3  | 0  | 0  | |
| 多少                            | 1   | 0  | 1  | 0  | Missing |
| Coverbs                         | 5   | 5  | 0  | 0  | Full set |
| Compounds (VO/VV/NN/AN)         | 4   | 0  | 4  | 0  | No open-class lookup |
| Radical-class layer             | 30  | 0  | 0  | 30 | Not implemented (planned) |
| Punctuation                     | 4   | 0  | 4  | 0  | No PUNCT POS in shared.py |
| Ordinals (Arabic-mixed)         | 2   | 1  | 1  | 0  | Only Chinese-numeral suffix allowed |
| Loanwords / abbreviations       | 3   | 0  | 3  | 0  | No FOREIGN/PROPN fallback |
| Proper nouns                    | 2   | 0  | 2  | 0  | 北京 / 中国 UNKNOWN |
| 们 plural rules                 | 2   | 2  | 0  | 0  | Animate-base whitelist works |

## 2. Top 10 failure patterns

1. **Open-class content words default to `UNKNOWN`.** Any noun / verb / adj not in a config file (`人`, `山`, `朋友`, `学校`, `学习`, `吃饭`, ...) returns `pos=UNKNOWN` with empty tags. This is the single largest cluster (28 / 43 failures).
2. **No `PUNCT` POS.** CJK punctuation (`，`, `。`, `！`, `？`) drops to `UNKNOWN`. The sentence validator already skips `PUNCT`, so the POS is "wired up" but never assigned.
3. **No `PROPN` / `FOREIGN` fallback.** Proper nouns (`北京`, `中国`), loanwords (`咖啡`, `沙发`), and Latin abbreviations (`CCTV`) are all `UNKNOWN`.
4. **Lexical collisions.** Surfaces that belong to two closed classes pick whichever JSON section loads first:
   - `只` ADV (`subcat=RESTRICTIVE`) wins over `只` CLF (`ANIMALS`).
   - `把` ADP (`construction=BA`) wins over `把` CLF (`GRASPABLE`).
   - `得` PART (`role=COMP`) wins over `得` AUX (`modal=OBLIGATION`).
   These need context-dependent disambiguation.
5. **Demonstrative + classifier compounds missing.** `这个`, `那个`, `这里`, `那里` are not in `zh_particles.json`; only the bare `这`, `那`, `这些`, `那些` are.
6. **Verb reduplication not detected.** `看看`, `试试` are AABB / AA tentative-aspect verbs but receive no special handling; they fall through to `UNKNOWN`.
7. **Progressive 在 is ADP, not aspect marker.** In `我 在 吃`, `在` is the progressive auxiliary, but the lexicon tags it as ADP (LOC). 正在 works correctly because it has a dedicated entry.
8. **Ordinal prefix 第 too restrictive.** `_step_a` only strips `第` if the remainder consists of Chinese numeral chars. `第3次` (mixed Arabic numeral + classifier) is left as `UNKNOWN`.
9. **Missing modals.** `愿意` is not registered; should be AUX/VOLITION.
10. **Missing pronouns / interrogatives.** `咱们` (inclusive 1PL) and `多少` (quantity interrogative) are absent.

## 3. Specific bugs in priority order

| # | Severity | Bug | One-line fix sketch |
|---|---|---|---|
| 1 | HIGH | Open-class content words have no POS guess. | Add an "open-class probe" step: if all chars are Han and no closed-class hit, return `pos=NOUN` with a low-confidence flag (or wire a HSK frequency lexicon). |
| 2 | HIGH | Lexical ambiguity (`只`, `把`, `得`) silently resolved by config load order. | Allow multiple `(pos, tags)` per surface in `closed_class`, then disambiguate in `analyze_sentence` using neighbors (NUM-X-NOUN -> CLF; X-V -> ADP/AUX). |
| 3 | HIGH | Demonstrative+CLF (`这个/那个/这里/那里`) not lexicalized. | Add entries to `zh_particles.json` under `pronouns` or a new `determiners_dem` group. |
| 4 | MED  | CJK punctuation -> `UNKNOWN`. | In `_step_a`, intercept chars in `，。！？；：、""''（）` and return `pos=PUNCT`. |
| 5 | MED  | Proper nouns / loanwords / Latin abbreviations -> `UNKNOWN`. | If a token is non-Han (Latin/digit) or contains only common loanword phonetic chars, return `pos=FOREIGN` or `PROPN` instead of `UNKNOWN`. |
| 6 | MED  | `第` ordinal rule too strict (Chinese numerals only). | In step A rule 6, accept either `all(ch in _NUMBERS)` or `remainder[0].isdigit()`. |
| 7 | MED  | Missing modals / pronouns / interrogatives (`愿意`, `咱们`, `多少`). | Add the entries to `zh_particles.json`. Mechanical fix. |
| 8 | MED  | Progressive `在 + V` not detected. | In `analyze_sentence`, when ADP `在` precedes a VERB (or UNKNOWN that ends in a verb suffix), re-tag as ADV with `aspect=PROG`. |
| 9 | LOW  | Verb reduplication (`看看`, `试试`) not detected. | Step A rule: if `len(word) == 2` and `word[0] == word[1]`, return `(word[0], {"aspect": "TENTATIVE"}, "VERB")`. |
| 10 | LOW | NUM-CLF-NOUN validator can't confirm noun head. | Once bug 1 is fixed this disappears automatically. |

## 4. Categories with high pass rates (>= 90%)

- Pronouns (single-char + full set): 15 / 15
- Aspect particles and aspect suffix stripping: 14 / 14
- Negation: 7 / 7
- Coverbs / prepositions: 14 / 14 (single-char ADP + coverb tests)
- Conjunctions: 4 / 4
- Ba / Bei constructions (including sentence validation): 6 / 6
- Modal auxiliaries: 7 / 8
- Bare demonstratives + sentence-final particles + interrogative pronouns: 10 / 10
- 们 plural handling (animate whitelist + inanimate rejection): 2 / 2

The engine's **closed-class core is solid**. All gaps are in (a) open-class lookup, (b) compound / locative demonstratives, and (c) edge POS classes (PUNCT / PROPN / FOREIGN).

## 5. Radical-class layer (planned)

### Status

30 xfail tests are in place under section 15 of the test file
(`test_radical_class_layer`). They run as `XFAIL` today; they will flip
to `PASS` once the radical-class layer ships.

Coverage:

| Radical (Kangxi) | Class label              | Example chars covered                  |
|------------------|--------------------------|----------------------------------------|
| 人 / 亻          | CLASS:HUMAN_RELATION     | 人, 们, 你, 他                          |
| 木               | CLASS:TREE_WOOD          | 木, 林, 森, 树                          |
| 水 / 氵          | CLASS:WATER_LIQUID       | 水, 河, 海, 江                          |
| 心 / 忄          | CLASS:HEART_EMOTION      | 心, 想, 情, 快                          |
| 言 / 讠          | CLASS:SPEECH_LANGUAGE    | 言, 说, 话, 语                          |
| 火               | CLASS:FIRE_HEAT          | 火, 烧                                  |
| 山, 石, 土       | CLASS:EARTH_TERRAIN      | 山, 石, 土                              |
| 金 / 钅          | CLASS:METAL              | 金, 钱                                  |
| 手 / 扌          | CLASS:HAND_ACTION        | 手, 打, 拿                              |

### Required data structure

A single JSON table at `morph_efficiency_project/configs/zh_radicals.json`:

```json
{
  "version": "kangxi-214 v1",
  "radicals": {
    "9":  {"radical": "人",   "variants": ["亻"], "class": "CLASS:HUMAN_RELATION"},
    "75": {"radical": "木",   "variants": [],     "class": "CLASS:TREE_WOOD"},
    "85": {"radical": "水",   "variants": ["氵"], "class": "CLASS:WATER_LIQUID"},
    "61": {"radical": "心",   "variants": ["忄"], "class": "CLASS:HEART_EMOTION"},
    "149":{"radical": "言",   "variants": ["讠"], "class": "CLASS:SPEECH_LANGUAGE"}
  },
  "char_to_radical": {
    "U+4EBA": 9,
    "U+4F60": 9,
    "U+6728": 75,
    "U+6CB3": 85
  }
}
```

Two-stage lookup:

1. `codepoint -> radical_index` (the `char_to_radical` map; populate from
   Unicode `Unihan_RadicalStrokeCounts.txt`, kRSKangXi field).
2. `radical_index -> {radical, variants, class}` (the `radicals` table; the
   semantic-class assignment is the manual / theory-driven step).

### Engine wiring

Add a `_step_d_radical(stem)` step that runs after `_step_c`. For each Han
character in `stem` (or just the head character for single-syllable words),
look up the radical and write `tags['radical']` and `tags['radical_class']`.
For multi-character compounds, the convention is the head-character radical
class for nouns and the verb-head radical class for verbs.

### Acceptance

The 30 xfails in `test_radical_class_layer` are the acceptance suite. When
the layer ships, remove the `@pytest.mark.xfail` decorator and they should
pass without further edits.
