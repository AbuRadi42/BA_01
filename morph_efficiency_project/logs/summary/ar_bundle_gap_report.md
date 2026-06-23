# Arabic Bundle Gap Audit

Scope: 20,000 sentences from `mini_experiment/data/ar_{train,val,test}.txt`
(901,068 tokens). ArabicEngine emitted **697 unique (POS, tags) bundles**, of
which **124 pass** `check_morph_sequence_ar` and **573 are rejected**.

## Failure-category histogram

| Category | Unique bundles rejected |
|---|---|
| `VERB_missing_tense` | 304 |
| `NOM_missing_num` | 146 |
| `VERB_missing_person` | 123 |
| **Total** | **573** |

All 573 rejections fall into three buckets, and every one of them is a
missing-required-tag failure. Zero bundles trip the IMP/PASS/JUS
co-occurrence rules or the VERB-with-case/def guard, because the validator
short-circuits on missing tense/person before reaching those checks.

## Top surprising rejected bundles

1. `VERB[form=I, tense=PAST, voice=ACT]` (134,212 tokens). Examples:
   شفافةٌ، وهو، سطح. These are not verbs at all: شفافة is an ADJ, هو is a
   pronoun, سطح is a NOM. The engine's morphological-pattern classifier is
   defaulting many CaCaC/CaaCiC-shaped nominals to VERB form I past active
   because the surface matches فَعَلَ. Person is never assigned because the
   word has no verbal subject affix, so the validator correctly rejects.

2. `NOM[role=DERIVED]` (38,162 tokens). Examples: مركزية، مياه، معلّق. The
   engine recognizes these as derived nominals but never assigns num/gender,
   even though مركزية carries an unambiguous ـة feminine singular and مياه is
   a broken plural. The `role=DERIVED` branch in `ar_engine.py` is skipping
   the num/gender resolver that the plain-NOM branch runs.

3. `VERB[form=I]` with no tense at all (61,782 tokens). Examples: ذرّة،
   ترتبط، طرفيها. Mixed bag: ذرّة and طرفيها are NOMs (the latter is a dual
   in oblique with a 3FSG clitic), only ترتبط is genuinely verbal. The
   engine assigns `form=I` from the root-and-pattern stage but the conjugation
   stage bails out, so the bundle has neither tense nor person.

## Recommendation

The split is not symmetric. Two of the three categories are engine bugs; one
is a partial validator over-reach.

- **`VERB_missing_tense` (304 bundles, fix the engine).** A VERB bundle
  without tense is structurally incoherent in Arabic; فعل لا زمن له is not a
  category we want to admit. The fix is in `ar_engine.py`: stop emitting
  `pos=VERB` when the conjugation classifier fails. Reroute to NOM (or to a
  new `pos=UNRESOLVED`) when no tense can be derived. This will also clean
  up the noun-misclassified-as-verb bleed visible in items 1 and 3 above.

- **`VERB_missing_person` (123 bundles, fix the engine).** Same root cause
  as above plus a separate gap: when the engine does identify a finite verb
  it sometimes leaves person unset rather than defaulting to 3MSG (the
  default for verbal sentences in MSA). Default person to 3 with the gender
  taken from the suffix, or, if truly ambiguous, drop the token to
  UNRESOLVED rather than emitting an incomplete VERB bundle.

- **`NOM_missing_num` (146 bundles, relax the validator).** Requiring both
  num and gender on every NOM is too strict for diptotes, masdars, proper-
  noun-shaped tokens, foreign-script segments, and number-like surfaces
  (H2O, 71%). The engine is honest here: these are genuinely number/gender
  underspecified. Recommend weakening the rule to: require num **or**
  gender, and exempt NOMs carrying `role` in {MASDAR, PLURAL, PROPER} or
  carrying `diptote=YES`. This matches the linguistic reality that
  masdars and broken plurals do not always carry overt number marking.

Cross-cutting observation: many rejected VERB bundles also carry `def=DEF`
or `case`, which the validator forbids on VERBs. The classifier never sees
these because the tense/person guard fires first. After the engine fix, a
second sweep is worth running because those guards will then become live.
