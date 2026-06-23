# Arabic Engine Comprehensive Audit

Test file: `morph_efficiency_project/tests/ar_morph/test_ar_engine_comprehensive.py`
Run: `python -X utf8 -m pytest morph_efficiency_project/tests/ar_morph/test_ar_engine_comprehensive.py -v --tb=no`

## Summary

| Metric | Value |
|---|---:|
| Total tests | 254 |
| Passed | 94 |
| Failed | 159 |
| Skipped | 1 (composite multi-token sentence) |
| Pass rate | 37% |

The suite exercises 12 linguistic categories. Tests assert the
linguistically correct expected analysis (POS, root, key tags), so each
failure is a real engine gap, not a test artifact.

## 1. Test-category coverage table

| # | Category | Cases | Pass | Fail | Pass-rate |
|---|---|---:|---:|---:|---:|
| 1 | Verbal Forms I-X (past, present, passive, imperative, jussive, subjunctive) | 38 | 19 | 18 (+1 skip) | 50% |
| 2 | Verbal Forms XI-XII (احمارّ، اخشوشن) | 2 | 0 | 2 | 0% |
| 3 | Weak-root paradigms (ناقص، أجوف، مثال، مهموز، مضعّف) | 25 | 13 | 12 | 52% |
| 4 | Masdar patterns (40+ awzān) | 32 | 4 | 28 | 13% |
| 5 | Broken plurals (diptote + triptote) | 13 | 0 | 13 | 0% |
| 6 | Active / passive participles per form | 17 | 0 | 17 | 0% |
| 7 | Derived nominal templates (instrument, place, sifa, mubalaghah, diminutive, elative, nisba) | 28 | 4 | 24 | 14% |
| 8 | Clitic stacking (proclitic clusters + enclitic paradigm + circumfix) | 24 | 22 | 2 | 92% |
| 9 | Closed-class particles | 40 | 29 | 11 | 73% |
| 10 | Hamza variants and normalization | 10 | 9 | 1 | 90% |
| 11 | Number-like and foreign surfaces | 7 | 7 | 0 | 100% |
| 12 | Wazn-semantic-class lookup (Step B') | 17 | 1 | 16 | 6% |

Notes: items 8, 10, 11 are the engine's strong areas. Items 4, 5, 6, 7, 12
are systemic gaps that block any downstream consumer of `role` / `semantic_role`.

## 2. Top 10 failure patterns

| Rank | Pattern | Affected surfaces (examples) | Count |
|---:|---|---|---:|
| 1 | NOM `role` tag missing on masdar (`role=None`, `form=None`) | تَعْلِيم passes, but تَعَلُّم، تَبَادُل، اِنْفِجَار، اِسْتِعْمَال، إِعْلَان all lose role/form. The role+form pair only emerges for Form II (تَفْعِيل) and Form IV (إِفْعَال). All others fall through to the augmented-stem branch and emit bare `{num,gender}`. | 24 |
| 2 | Derived NOM never tagged with template's true `role` | مَكْتَب، مَكْتُوب، مَدَارِس all returned as `role=PASSIVE_PARTICIPLE` regardless of true semantic_role. INSTRUMENT, PLACE, SIFA_MUSHABBAHA, MUBALAGHAH, DIMINUTIVE never surface. Step B' lookup is unwired. | 22 |
| 3 | Broken plural detected only on أَفْعَال (`BROKEN_PLURAL_AF3AL`); all other broken-plural schemas misclassified | كُتُب، رِجَال، بُيُوت، عُيُون → demoted to VERB form I. شُعَرَاء، عَجَائِب، فُعُول → spuriously tagged form XII. مَدَارِس → tagged PASSIVE_PARTICIPLE. مَفَاعِل → tagged PASSIVE_PARTICIPLE. | 13 |
| 4 | Active participles (فاعل، مفعِّل، مفاعِل، مفعِل، مفتعِل، مستفعِل) emitted with `role=DERIVED` instead of `role=AGENT`, or demoted to VERB | كَاتِب، فَاعِل، مُعَلِّم، مُدَرِّس، مُقَاتِل، مُسَافِر، مُنْجِز، مُحْسِن، مُجْتَمِع، مُعْتَقِد، مُسْتَقْبِل. | 12 |
| 5 | Imperative (الأمر) demoted to NOM | اُكْتُبْ، اِكْتُبْ، اُدْرُسْ all surface as NOM with `template=VERB_AUGMENTED_VIII`. اِجْلِسْ surfaces as VERB but with phantom `form=XII`. | 5 |
| 6 | Imperfect form-and-tense always reported as `PAST` for imperfect surfaces | يَكْتُبُ، يَدْرُسُ، يُكْتَبُ، يَكْتُبْ، يَكْتُبَ all return `tense=PAST` (verbatim Step B' tag, never overridden by the يَـ prefix). Mood (JUS/SUBJ) is never assigned. | 9 |
| 7 | Form II/III/V/VI past actives misclassified as Form I | عَلَّمَ، دَرَّسَ، تَعَلَّمَ، تَدَرَّبَ، تَبَادَلَ، قَاتَلَ، شَارَكَ → emitted as VERB with `form=I`. The shadda and medial alif never trigger augmented-form detection. | 7 |
| 8 | Augmented Forms VII-X past actives demoted to NOM (lose tense/voice/person) | اِجْتَمَعَ، اِسْتَخْرَجَ، اِنْفَجَرَ، اِعْتَقَدَ، اِحْمَرَّ، اِسْوَدَّ، اِسْتَعْمَلَ، اِسْتَغْفَرَ → NOM with bare `{num,gender}`. Recent VERB-demotion fix over-fires here. | 8 |
| 9 | Demonstratives misrouted | هَذَا، هَذِهِ، ذَلِكَ، تِلْكَ، هَؤُلَاءِ → emitted as VERB/NOM with phantom roots (هذي، هذذ، ذلك، تلك، هءلاء). Closed-class intercept misses all DEM. أُولَئِكَ same. | 6 |
| 10 | Subordinators tagged as wrong subcat | إِذَا → CONJ (should be SUB), حَتَّى → PREP (should be SUB), كَيْ → CONJ (should be SUB), أَيُّهَا → NOM (should be PART/VOC). | 4 |

## 3. Specific bugs in priority order

### P0 (blocking)

1. **`SEV=BLOCKER` Step B' (wazn → semantic_role) is unwired.** All
   17 `semantic_role` probes fail; the engine never propagates the
   `semantic_role` field from `ar_templates.json` to `TokenInfo.tags`.
   *Fix sketch:* after a template match in Step B, copy
   `template.semantic_role` into `tags['semantic_role']`, and copy
   `template.role`/`template.verb_form` if present.

2. **`SEV=BLOCKER` Derived-NOM role resolver is one-rule-fits-all.**
   Every مَفْعَل/مَفْعِل/مَفْعَلَة surface (مَكْتَب، مَلْعَب، مَدْرَسَة، مَطْبَخ) is
   stamped `role=PASSIVE_PARTICIPLE`, including in cases where the template
   is unambiguously PLACE.  *Fix sketch:* replace the constant-string
   assignment in the NOM_DERIVED branch with a lookup keyed on the matched
   wazn name.

3. **`SEV=BLOCKER` Masdars only resolve for Forms II and IV.** Masdar
   detection fires for تَعْلِيم and إِنْجَاز but not for تَعَلُّم،
   تَبَادُل، اِنْفِجَار، اِجْتِمَاع، اِسْتِعْمَال، اِسْتِخْرَاج، جِهَاد،
   ضَرْب، فَهْم، كِتَابَة، جُلُوس، ضَرْبَة، مَجْلِس.  *Fix sketch:* add
   MASDAR templates for Forms I, III, V, VI, VII, VIII, IX, X plus
   مرة/هيئة/ميمي patterns; the templates exist in `ar_templates.json` but
   the engine's MASDAR branch only matches the Form II/IV schemas.

### P1 (severe)

4. **`SEV=SEVERE` Broken-plural detection only covers أَفْعَال.** All
   other schemas (فُعُول، فِعَال، فُعَلَاء، فَعَائِل، مَفَاعِل، أَفْعِلَة)
   are misclassified.  *Fix sketch:* extend `BROKEN_PLURAL_*` regex
   family to include the seven canonical broken-plural awzān.

5. **`SEV=SEVERE` Imperfect tense classifier defaults to PAST.** The
   imperfect-prefix يَـ/تَـ/نَـ/أَـ stripper does not flip
   `tense=PAST → tense=PRES`.  *Fix sketch:* in the imperfect-prefix
   branch, set `tags['tense']='PRES'` and clear `voice=ACT/PASS` based on
   the prefix vowel (يَ→ACT, يُ→PASS).

6. **`SEV=SEVERE` Mood (JUS/SUBJ) never assigned.** Surfaces with
   sukun-final يَكْتُبْ or fatha-final يَكْتُبَ are tagged identically to
   indicative.  *Fix sketch:* after PRES detection, inspect the final
   short vowel (sukun → JUS, fatha → SUBJ, damma → IND).

7. **`SEV=SEVERE` Form II/III past actives misclassified as Form I.**
   The shadda on R2 (Form II) and the medial alif (Form III) are not
   diagnostic in the form classifier.  *Fix sketch:* add shadda detection
   in `_classify_verb_form` ahead of the trilateral fallback.

8. **`SEV=SEVERE` Augmented Forms VII-X past actives over-demoted to
   NOM.** The recent VERB-demotion guard (no tense/person → NOM) now
   wrongly fires for اِجْتَمَعَ، اِسْتَخْرَجَ، اِحْمَرَّ. The form is
   detectable from the augmentation prefix; tense=PAST and voice=ACT
   should be inferred.  *Fix sketch:* in the demotion guard, exempt
   surfaces whose stripped stem matches a VERB_AUGMENTED_* template and
   default tense=PAST, voice=ACT, person=3, gender=M.

9. **`SEV=SEVERE` Active participles tagged `role=DERIVED` instead of
   `role=AGENT`.** Fixable concurrent with bug #2.

### P2 (high)

10. **`SEV=HIGH` Imperative surfaces (اُكْتُبْ، اُدْرُسْ) demoted to
    NOM.** The initial wasla-alif strip + imperative-stem pattern is
    not recognized.  *Fix sketch:* add IMP detection: initial اُ/اِ
    + trilateral stem with sukun-medial vowel.

11. **`SEV=HIGH` Demonstratives missing from closed-class table.**
    Add هَذَا، هَذِهِ، ذَلِكَ، تِلْكَ، هَؤُلَاءِ، أُولَئِكَ to the
    closed-class intercept with `subcat=DEM`.

12. **`SEV=HIGH` Forms XI/XII not surfaced.** اِحْمَارَّ and
    اِخْشَوْشَنَ get template `VERB_AUGMENTED_XI/XII` (correct) but POS
    is demoted to NOM with no form tag.  *Fix sketch:* same fix as #8.

### P3 (medium)

13. **`SEV=MED` Subordinator subcat confusion.** إِذَا، كَيْ tagged
    CONJ; حَتَّى tagged PREP. أَيُّهَا entirely missing.

14. **`SEV=MED` Adjectives شَبَّهَة (صَغِير، كَبِير، عَطْشَان، جَوْعَان،
    كَسْلَان) misclassified as VERB form I past.** Their NOM/ADJ
    nature should beat the verb classifier; trigger `pos=ADJ,
    role=SIFA_MUSHABBAHA` for surfaces matching فَعِيل/فَعْلَان templates.

15. **`SEV=MED` Diminutive (فُعَيْل) misclassified as VERB form XII.**
    كُتَيْب، جُبَيْل. *Fix sketch:* add فُعَيْل branch ahead of the
    XII fallback.

16. **`SEV=MED` Feminine elative (فُعْلَى) misses `degree=COMP`.**
    كُبْرَى returns no degree tag.

17. **`SEV=MED` Feminine nisba (مِصْرِيَّة) misses `role=NISBA`.**
    Gets `role=DERIVED` instead.

18. **`SEV=LOW` Dual endings stripped too aggressively.**
    كِتَابَانِ and كِتَابَيْنِ lose the stem; root extraction returns
    a partial.

19. **`SEV=LOW` Hamza-on-alif-below (إِبْرَاهِيم) not normalized to
    bare ء in root.** Returns ءبرهيم with surface kasra preserved
    inconsistently.

## 4. Categories with high pass rates

- **Clitic stacking (92%)** — all proclitic clusters (وَبِال, فَلِل,
  كَال), the full enclitic pronoun paradigm (هـ/ها/هم/هن/هما/ك/كم/كنّ/كما/ي/نا),
  and the لَـ...ـنّ circumfix work cleanly. Only the dual-noun strip
  (كِتَابَانِ، كِتَابَيْنِ) is broken.
- **Hamza normalization (90%)** — أ، إ، آ، ؤ، ئ correctly normalized
  to ء for root matching. Only إِبْرَاهِيم edge case fails.
- **Foreign and number-like surfaces (100%)** — H2O, 71%, COVID, plus
  أَكْسِجِين، هَيْدْرُوجِين، بِيَانُو، كُومْبْيُوتَر all routed correctly
  (LOANWORD / NOUN_DIPTOTE).
- **Closed-class particles (73%)** — prepositions, conjunctions,
  negation, interrogatives, vocative يَا, and ism-fi3l (هَيْهَات،
  آمِين، صَه) all work. The gaps are demonstratives and a few
  subordinators.
- **Weak roots ناقص + أجوف active past (50%)** — Form I past active
  weak-root verbs are reliably resolved, and root weak-letter resolution
  (ناقص و/ي, أجوف و/ي, مثال) is generally correct.

## 5. Recommendations (ordered by leverage)

1. Wire Step B': copy `semantic_role` / `role` from the matched template
   into `tags`. This unlocks bugs #1, #2, #9, #14, #15, #16, #17 with
   one change.
2. Fix the imperfect tense override (#5) and mood detection (#6). This
   unlocks half of category 1 and trims the `VERB_missing_tense` rejected
   bundles from the corpus audit.
3. Expand broken-plural template family (#4) to cover all seven schemas.
4. Refine the VERB-demotion guard (#8) so augmented forms keep
   tense/voice/person.
5. Add demonstratives to closed-class table (#11).
