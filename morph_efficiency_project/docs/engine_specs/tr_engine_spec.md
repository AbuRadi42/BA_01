# Turkish Engine Design Specification

**Language:** Turkish (tr)  
**Typology:** Pure agglutinative  
**Engine file:** `scripts/engines/tr_engine.py`  
**Status:** Built, audited, tested (Phase 0 complete -- major architectural rework)

---

## Morphological Overview

Turkish (Turkce) is a pure agglutinative language belonging to the Turkic family. Its morphology operates by concatenating suffixes onto a stem in a strict, predetermined slot order. Unlike fusional languages such as Arabic, where a single morpheme may encode multiple grammatical categories simultaneously, Turkish assigns one morpheme per grammatical function, making morphological analysis highly decomposable. Each suffix occupies a fixed positional slot, and the order of these slots is invariant across all well-formed words.

The most distinctive phonological feature of Turkish morphology is vowel harmony (unlu uyumu). Turkish enforces two dimensions of harmony: backness harmony (2-way), which requires suffix vowels to agree with the last vowel of the preceding morpheme in the front/back dimension (front vowels: e, i, o, u; back vowels: a, i, o, u), and rounding harmony (4-way), which additionally constrains high vowels in suffixes to match the rounding of the stem's last vowel. This system produces the characteristic four-variant suffix paradigm seen throughout the language (e.g., -lar/-ler for plural, -lIk with four surface forms -lik/-lik/-luk/-luk).

Consonant mutations (unsuz degisimi) add a further phonological layer. When certain case suffixes beginning with a vowel attach to stems ending in voiceless stops, the stem-final consonant softens: p to b (kitap to kitabi), t to d, k to g/g, c to c. The engine must reverse these mutations during analysis to recover the dictionary form of the stem. Additionally, buffer consonants (y, n, s) are inserted between vowel-final stems and vowel-initial suffixes to avoid hiatus, creating systematic surface variation that the engine must handle.

The nominal template follows a strict slot order: stem + DERIV + NUM + POSS + CASE. A noun like "evlerimizdeki" (the one at our houses) decomposes as ev (house) + ler (PL) + imiz (POSS.1PL) + de (LOC) + ki (REL.ADJ). Each suffix occupies exactly one slot, and no slot may appear out of order. The verbal template is considerably richer: stem + DERIV + VOICE + ABIL + NEG + TENSE + MOOD + PERSON_NUM + EPIST + Q. A verb like "gorulemeyebilecektiniz" layers voice, ability, negation, tense, and person agreement in this rigid sequence.

Turkish also employs compound tenses formed by cliticizing the auxiliary copula (imek) onto an already-inflected form. These produce forms like "gidiyordu" (was going = progressive + past copula) and "gidecekmiş" (was apparently going to go = future + narrative copula). These compound tenses are treated as single-slot matches in the engine to avoid incorrect decomposition.

Turkish sits at the extreme agglutinative end of the morphological typology spectrum. A single word can theoretically carry over a dozen suffixes, each transparently segmentable, making it an ideal candidate for slot-based suffix stripping. However, the system must handle suffix ambiguity (the same surface form -da can be locative case or the additive particle, -a can be dative case or optative mood), which motivated the two-pass architecture described below.

## Closed-Class Intercept

The engine intercepts 83 closed-class function words before attempting any morphological analysis. These are words that should not be decomposed, as they are atomic lexical items.

**Postpositions (18):** icin (PURPOSE), ile (COMITATIVE), gibi (SIMILATIVE), kadar (DEGREE), gore (ACCORDING_TO), dogru (DIRECTION), karsi (AGAINST), ragmen (DESPITE), dolayi (CAUSE), beri (SINCE), once (BEFORE), sonra (AFTER), disinda (OUTSIDE), hakkinda (ABOUT), itibaren (STARTING_FROM), boyunca (THROUGHOUT), arasinda (BETWEEN), uzere (ABOUT_TO)

**Conjunctions (11):** ve (AND), veya (OR), ama (BUT), fakat (BUT), ancak (HOWEVER), cunku (BECAUSE), oysa (WHEREAS), halbuki (WHEREAS), hem (BOTH), ise (AS_FOR), ki (THAT)

**Pronouns (19):** ben (1SG), sen (2SG), o (3SG), biz (1PL), siz (2PL), onlar (3PL), bu (DEM), su (DEM), bunlar (DEM.PL), sunlar (DEM.PL), kendi (REFLEXIVE), kim (INTERR), hangi (INTERR), her (UNIVERSAL), bazi (INDEFINITE), bircok (INDEFINITE), hic (NEGATIVE), hep (UNIVERSAL), herkes (UNIVERSAL)

**Adverbs (17):** cok (DEGREE), az (DEGREE), daha (COMPARATIVE), en (SUPERLATIVE), simdi (TEMPORAL), hemen (TEMPORAL), hala (TEMPORAL), artik (TEMPORAL), henuz (TEMPORAL), bile (ADDITIVE), sadece (RESTRICTIVE), yalniz (RESTRICTIVE), zaten (ALREADY), belki (EPISTEMIC), evet (AFFIRMATIVE/PART), hayir (NEGATIVE/PART), tamam (AGREEMENT/PART)

**Question words (10):** ne (INTERR), nerede (INTERR), nereye (INTERR), nereden (INTERR), nasil (INTERR), nicin (INTERR), niye (INTERR), neden (INTERR), kac (INTERR), dahi (ADDITIVE)

**Particles (8):** da (ADDITIVE), de (ADDITIVE), ya (DISCOURSE), mi (QUESTION), mi (QUESTION), mu (QUESTION), mu (QUESTION), degil (NEGATION)

**Total: 83 entries**

Note: da/de appear both as standalone particles in the closed-class lexicon and as bound suffixes in the ADDITIVE slot (slot 13). The closed-class intercept catches the free-standing usage; the suffix slot catches the bound usage. This dual registration is intentional and resolves one of the key ambiguity sources in Turkish morphology.

## Two-Pass Analysis Architecture

The two-pass system is the key architectural innovation introduced in Phase 0. It resolves a fundamental ambiguity problem in Turkish suffix stripping.

### The Problem

Many Turkish suffixes are surface-identical across different grammatical functions:

- **-da/-de**: locative case (evde = at home) vs. additive particle (o da = he too)
- **-a/-e**: dative case (eve = to the house) vs. optative mood (gide = let him go)
- **-ar/-er**: aorist tense (gider = he goes) vs. plural (evler = houses, where -ler not -er, but CAUS voice -ar/-er overlaps)
- **-sa/-se**: conditional mood (giderse = if he goes) vs. copula conditional (ogrenciyse = if he is a student)

A single-pass greedy strip from the outermost slot inward can misidentify these suffixes, especially when verbal mood/tense slots (high slot numbers, stripped first) consume characters that actually belong to nominal case/number slots (lower slot numbers).

### Pass 1: Full Slot Stripping

Pass 1 executes the original approach: strip suffixes from outermost to innermost, traversing all 15 slots in descending slot order (14, 13, 12, 11, 10, 9.5, 9, 8, 7, 6, 5, 4.5, 4, 3, 2). Within each slot, the longest matching suffix that satisfies vowel harmony, buffer consonant constraints, and stem plausibility is accepted. The copula slot (11) is deferred and only attempted if no tense marker was found.

### Pass 2: Nominal-Only Stripping

Pass 2 restricts analysis to nominal slots only: CASE (4), POSS (3), NUM (2), processed in descending order (4, 3, 2). This conservative pass only looks for the three nominal inflection categories, ignoring all verbal and other slots entirely.

### Selection Logic

After both passes complete, the engine selects the best analysis:

1. **If Pass 1 found clear verbal markers** (PRES_PROG, PAST_DEF, PAST_NARR, PRES_AORIST, FUT, converb semantics, or real moods INF/NECESS/COND): prefer Pass 1. However, if Pass 2 also found nominal tags and consumed more suffix characters, prefer Pass 2 (the verbal match was likely spurious).

2. **If Pass 2 found nominal markers** (case, poss, or num tags) and produced a plausible stem: prefer Pass 2 when it yields a longer or equal stem, when Pass 1's stem is implausible, or when Pass 1 produced ambiguous tags (mood, add, aspect that are likely misidentified).

3. **Otherwise**: fall back to Pass 1.

### Example: "evlerde"

- **Pass 1** (full): tries slot 14 down. At slot 13 (ADDITIVE), -de matches. Then at slot 7 or 8, -ler could match AORIST or be left. Result may be stem="ev", tags={add: ALSO, ...} with possible spurious verbal tags.
- **Pass 2** (nominal-only): at slot 4 (CASE), -de matches as LOC. At slot 2 (NUM), -ler matches as PL. Result: stem="ev", tags={case: LOC, num: PL}.
- **Selection**: Pass 2 found nominal markers, produced a plausible stem. Pass 2 wins. Correct analysis: ev + ler (PL) + de (LOC) = "at the houses".

### Example: "gidiyordu"

- **Pass 1** (full): at slot 14 (COMPOUND_TENSE), -iyordu matches PROG_PAST. Result: stem="gid", tags={tense: PRES_PROG, aspect: PROG, cop: PAST}. Clearly verbal.
- **Pass 2** (nominal-only): no nominal suffix matches well on "gidiyordu".
- **Selection**: Pass 1 found clear verbal marker (PRES_PROG). Pass 1 wins.

## Stem Validation

The `_stem_plausible()` method prevents over-stripping by enforcing two constraints on any candidate stem remaining after suffix removal:

- **Minimum length**: the stem must be at least 2 characters long. This prevents the engine from stripping a word down to a single consonant or nothing.
- **Vowel requirement**: the stem must contain at least one vowel from the Turkish vowel inventory (a, e, i, i, o, o, u, u). This prevents accepting consonant-only remainders as valid stems.

Additionally, per-slot minimum stem lengths are enforced via `_SLOT_MIN_STEM`:

| Slot | Min stem length | Rationale |
|------|----------------|-----------|
| 5 (VOICE) | 3 | -l, -n, -t are very short and ambiguous |
| 9 (PERSON_NUM) | 3 | -m, -z, -n are single-character |
| 11 (COPULA) | 3 | Short suffixes risk false matches |
| All others | 2 | Default minimum |

These guards work together to ensure that only linguistically plausible stems survive the stripping process, preventing cascading errors where an over-stripped stem causes downstream derivational detection to produce nonsensical chains.

## Step A: Inflectional Stripping

### Slot System

The engine defines 15 suffix slots, each with a numeric `slot_order` that determines stripping priority (higher numbers are stripped first):

| Slot | Name | slot_order | Contents | Example suffixes |
|------|------|-----------|----------|-----------------|
| 1 | DERIV | 1 | Derivational suffixes | (from tr_derivations.json: -lik, -ci, -siz, -la, etc.) |
| 2 | NUM | 2 | Plural number | -lar/-ler |
| 3 | POSS | 3 | Possessive | -im/-im/-um/-um (1SG), -in/-in/-un/-un (2SG), -i/-i/-u/-u/-si/-si/-su/-su (3SG), -imiz/-imiz/-umuz/-umuz (1PL), -iniz/-iniz/-unuz/-unuz (2PL), -lari/-leri (3PL) |
| 4 | CASE | 4 | Grammatical case | NOM (zero), -i/-yi (ACC), -a/-e/-ya/-ye (DAT), -da/-de/-ta/-te (LOC), -dan/-den/-tan/-ten (ABL), -in/-nin (GEN), -la/-le/-yla/-yle (INS) |
| 4.5 | ABIL | 4.5 | Ability/possibility | -ebil-/-abil- (ABIL), -eme-/-ama- (ABIL_NEG) |
| 5 | VOICE | 5 | Voice | -il (PASS), -tir/-dir (CAUS), -is (RECIP), -in (REFL) |
| 6 | NEG | 6 | Verbal negation | -ma/-me |
| 7 | TENSE | 7 | Tense/aspect | -di (PAST_DEF), -mis (PAST_NARR), -iyor (PRES_PROG), -ar/-ir/-r (PRES_AORIST), -acak/-ecek (FUT), -diydi (PAST_COND), -misti (NARR_COND), -maz/-mez (PRES_AORIST_NEG) |
| 8 | MOOD | 8 | Mood | -sa/-se (COND), -a/-e (OPT), zero (IMP_2SG), -in (IMP_2PL), -sin (IMP_3SG), -sinlar (IMP_3PL), -mali/-meli (NECESS), -mak/-mek (INF), -iniz (IMP_2PL_FORMAL) |
| 9 | PERSON_NUM | 9 | Person+number agreement | -im (1SG), -sin (2SG), zero (3SG), -iz (1PL), -siniz (2PL), -lar/-ler (3PL) |
| 9.5 | EPIST | 9.5 | Epistemic/inferential | -dir/-dir/-dur/-dur/-tir/-tir/-tur/-tur |
| 10 | NONFINITE | 10 | Participles and converbs | -an/-en (ACT_PART), -dik (PAST_PART), -acak/-ecek (FUT_PART), -inca (WHEN), -arken (WHILE), -arak (BY), -madan (WITHOUT), -diktan sonra (AFTER), -ana kadar (UNTIL) |
| 11 | COPULA | 11 | Copular predication | -im (PRES.1SG), -sin (PRES.2SG), zero (PRES.3SG), -iz (PRES.1PL), -siniz (PRES.2PL), -lar (PRES.3PL), -di (PAST), -sa/-se (COND) |
| 12 | QUESTION | 12 | Yes/no question | -mi/-mi/-mu/-mu |
| 13 | ADDITIVE | 13 | Also/too particle | -da/-de/-ta/-te |
| 14 | COMPOUND_TENSE | 14 | Compound tenses | -iyordu (PROG_PAST), -acakti (FUT_PAST), -maliydi (NECESS_PAST), -irdi (AORIST_PAST), -iyormus (PROG_NARR), -acakmis (FUT_NARR), -maliymiş (NECESS_NARR), -irmis (AORIST_NARR), -saydi (COND_PAST), -mis (COP_NARR) |

An additional synthetic slot 14.5 is created at runtime for PRES_AORIST_NEG (-maz/-mez), ensuring it is attempted before person/mood slots can consume its characters.

### Slot Details

**Slot 2 -- NUM (Cogul eki)**

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| PL | -lar, -ler | num=PL |

**Slot 3 -- POSS (Iyelik eki)**

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| POSS_1SG | -im, -im, -um, -um, -m | poss=1SG |
| POSS_2SG | -in, -in, -un, -un, -n | poss=2SG |
| POSS_3SG | -i, -i, -u, -u, -si, -si, -su, -su | poss=3SG |
| POSS_1PL | -imiz, -imiz, -umuz, -umuz, -miz, -miz, -muz, -muz | poss=1PL |
| POSS_2PL | -iniz, -iniz, -unuz, -unuz, -niz, -niz, -nuz, -nuz | poss=2PL |
| POSS_3PL | -lari, -leri | poss=3PL |

**Slot 4 -- CASE (Hal eki)**

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| NOM | (zero suffix) | case=NOM |
| ACC | -i, -i, -u, -u, -yi, -yi, -yu, -yu | case=ACC |
| DAT | -a, -e, -ya, -ye | case=DAT |
| LOC | -da, -de, -ta, -te | case=LOC |
| ABL | -dan, -den, -tan, -ten | case=ABL |
| GEN | -in, -in, -un, -un, -nin, -nin, -nun, -nun | case=GEN |
| INS | -la, -le, -yla, -yle | case=INS |

**Slot 4.5 -- ABIL (Yeterlilik kipi)**

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| ABIL | -ebil-, -abil-, -ubil-, -ubil-, -yebil-, -yabil- | modality=ABIL |
| ABIL_NEG | -eme-, -ama-, -ume-, -ume-, -yeme-, -yama- | modality=ABIL, polarity=NEG |

**Slot 5 -- VOICE (Cati)**

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| PASS | -il, -il, -ul, -ul, -l | voice=PASS |
| CAUS | -tir, -tir, -tur, -tur, -dir, -dir, -dur, -dur, -t, -ir, -ir, -ur, -ur, -ar, -er | voice=CAUS |
| RECIP | -is, -is, -us, -us, -s | voice=RECIP |
| REFL | -in, -in, -un, -un, -n | voice=REFL |

**Slot 6 -- NEG (Olumsuzluk eki)**

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| NEG | -ma, -me | polarity=NEG |

**Slot 7 -- TENSE (Zaman eki)**

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| PAST_DEF | -di, -di, -du, -du, -ti, -ti, -tu, -tu | tense=PAST_DEF |
| PAST_NARR | -mis, -mis, -mus, -mus | tense=PAST_NARR |
| PRES_PROG | -iyor, -iyor, -uyor, -uyor | tense=PRES_PROG, aspect=PROG |
| PRES_AORIST | -ar, -er, -ir, -ir, -ur, -ur, -r | tense=PRES_AORIST, aspect=HAB |
| FUT | -acak, -ecek | tense=FUT |
| PAST_COND | -diydi, -diydi, -duydu, -duydu, -tiydi, -tiydi | tense=PAST_DEF, aspect=PERF |
| NARR_COND | -misti, -misti, -mustu, -mustu | tense=PAST_NARR, aspect=PERF |
| PRES_AORIST_NEG | -maz, -mez | tense=PRES_AORIST, polarity=NEG |

**Slot 8 -- MOOD (Kip)**

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| COND | -sa, -se | mood=COND |
| OPT | -a, -e, -ya, -ye | mood=OPT |
| IMP_2SG | (zero) | mood=IMP, person=2, num=SG |
| IMP_2PL | -in, -in, -un, -un | mood=IMP, person=2, num=PL |
| IMP_3SG | -sin, -sin, -sun, -sun | mood=IMP, person=3, num=SG |
| IMP_3PL | -sinlar, -sinler, -sunlar, -sunler | mood=IMP, person=3, num=PL |
| NECESS | -mali, -meli | mood=NECESS |
| INF | -mak, -mek | mood=INF |
| IMP_2PL_FORMAL | -iniz, -iniz, -unuz, -unuz | mood=IMP, person=2, num=PL, register=FORMAL |

**Slot 9 -- PERSON_NUM (Sahis eki)**

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| P1SG | -im, -im, -um, -um, -m | person=1, num=SG |
| P2SG | -sin, -sin, -sun, -sun | person=2, num=SG |
| P3SG | (zero) | person=3, num=SG |
| P1PL | -iz, -iz, -uz, -uz, -z | person=1, num=PL |
| P2PL | -siniz, -siniz, -sunuz, -sunuz | person=2, num=PL |
| P3PL | -lar, -ler | person=3, num=PL |

**Slot 9.5 -- EPIST (Tahmin eki)**

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| EPIST | -dir, -dir, -dur, -dur, -tir, -tir, -tur, -tur | epist=INFER |

**Slot 10 -- NONFINITE (Sifat-fiil / Zarf-fiil)**

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| VN_ACT | -an, -en | pos=PART, aspect=ACT |
| VN_PAST | -dik, -dik, -duk, -duk, -tik, -tik, -tuk, -tuk | pos=PART, tense=PAST |
| VN_FUT | -acak, -ecek | pos=PART, tense=FUT |
| CONV_WHEN | -inca, -ince, -unca, -unce | pos=CONV, sem=WHEN |
| CONV_WHILE | -arken, -erken | pos=CONV, sem=WHILE |
| CONV_BY | -arak, -erek | pos=CONV, sem=MANNER |
| CONV_UNTIL | -ana kadar, -ene kadar | pos=CONV, sem=UNTIL |
| CONV_WITHOUT | -madan, -meden | pos=CONV, sem=WITHOUT |
| CONV_AFTER | -diktan sonra, -dikten sonra, -duktan sonra, -dukten sonra | pos=CONV, sem=AFTER |

**Slot 11 -- COPULA (Ek-fiil)**

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| COP_PRES_1SG | -im, -im, -um, -um | cop=PRES, person=1, num=SG |
| COP_PRES_2SG | -sin, -sin, -sun, -sun | cop=PRES, person=2, num=SG |
| COP_PRES_3SG | (zero) | cop=PRES, person=3, num=SG |
| COP_PRES_1PL | -iz, -iz, -uz, -uz | cop=PRES, person=1, num=PL |
| COP_PRES_2PL | -siniz, -siniz, -sunuz, -sunuz | cop=PRES, person=2, num=PL |
| COP_PRES_3PL | -lar, -ler | cop=PRES, person=3, num=PL |
| COP_PAST | -di, -di, -du, -du, -ti, -ti, -tu, -tu | cop=PAST |
| COP_COND | -sa, -se | cop=COND |

Special behavior: the copula slot is **deferred** during stripping. The engine processes all other slots first. Only if no tense marker was found does it attempt copula stripping. This prevents misidentifying verbal past tense -di as copula past -di on forms like "gitti" (he went).

**Slot 12 -- QUESTION (Soru eki)**

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| Q | -mi, -mi, -mu, -mu | q=YES_NO |

**Slot 13 -- ADDITIVE (Pekistirme eki)**

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| ADD | -da, -de, -ta, -te | add=ALSO |

**Slot 14 -- COMPOUND_TENSE (Birlesik zaman)**

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| PROG_PAST | -iyordu, -iyordu, -uyordu, -uyordu | tense=PRES_PROG, aspect=PROG, cop=PAST |
| FUT_PAST | -acakti, -ecekti | tense=FUT, cop=PAST |
| NECESS_PAST | -maliydi, -meliydi | mood=NECESS, cop=PAST |
| AORIST_PAST | -ardi, -erdi, -irdi, -irdi, -urdu, -urdu | tense=PRES_AORIST, cop=PAST |
| PROG_NARR | -iyormus, -iyormus, -uyormus, -uyormus | tense=PRES_PROG, aspect=PROG, cop=NARR |
| FUT_NARR | -acakmis, -ecekmis | tense=FUT, cop=NARR |
| NECESS_NARR | -maliymiş, -meliymiş | mood=NECESS, cop=NARR |
| AORIST_NARR | -armis, -ermis, -irmis, -irmis, -urmus, -urmus | tense=PRES_AORIST, cop=NARR |
| COND_PAST | -saydi, -seydi | mood=COND, cop=PAST |
| COP_NARR | -mis, -mis, -mus, -mus | cop=NARR |

### Greedy Matching

Within each slot, the engine collects all candidate suffix matches and selects the best one using a priority scheme:

1. **All surface variants** of all entries in the slot are tested against the word's current tail.
2. For each candidate, the engine verifies: (a) the suffix is shorter than the current stem, (b) the remaining stem meets the per-slot minimum length, (c) the stem passes `_stem_plausible()`, (d) vowel harmony is satisfied, and (e) buffer consonant constraints are met.
3. Valid candidates are sorted by **effective length** = `suffix_length - 2 * is_buffer`. Buffer-consonant variants (those starting with y/n/s in the appropriate slot) are penalized by 2 characters, so a non-buffer match of equal or slightly shorter length is preferred. This prevents the engine from consuming stem-final y/n/s as spurious buffer consonants.
4. Among ties in effective length, raw suffix length breaks the tie (longer still preferred).
5. The top-ranked candidate is accepted, its tags are merged, and stripping proceeds to the next slot.

### Vowel Harmony Validation

Every candidate suffix match is validated against Turkish vowel harmony rules:

**2-way backness check:** The first vowel of the suffix must agree in backness with the last vowel of the stem. Back vowels are {a, i, o, u}; front vowels are {e, i, o, u}. If the stem's last vowel is back, the suffix's first vowel must also be back, and vice versa.

**4-way rounding check (added in Phase 0):** For high vowels (i, i, u, u) in the suffix, rounding must also agree. If the stem's last vowel is rounded (o, o, u, u), the suffix's high vowel must be rounded; if unrounded (a, e, i, i), the suffix's high vowel must be unrounded.

**Exception handling:** If the stem contains no vowels, harmony is not enforced (returns true). If the suffix contains no vowels, harmony is trivially satisfied. Loanwords that violate harmony are not explicitly handled -- the engine may produce suboptimal analyses for such words, which is a known limitation.

## Consonant Mutation

The `_try_consonant_unmutation()` method reverses consonant softening that occurs when vowel-initial suffixes attach to stems ending in voiceless stops.

**When applied:** After case suffix stripping, but only when a case suffix (ACC, DAT, GEN, LOC, or ABL) was identified. This is because consonant mutation is triggered by these specific suffixes.

**Mutation mappings** (surface form in inflected word to dictionary form):

| Surface (mutated) | Original (dictionary) | Example |
|-------------------|----------------------|---------|
| g | k | kitabi to kitap (book) |
| g | k | (same mapping via voiced velar) |
| d | t | agacida to agacit (rare) |
| b | p | kitabi to kitap |
| c | c | agaci to agac (tree) |

The method returns a list of candidates: the original stem plus (if applicable) the unmutated form. If the unmutated form passes `_stem_plausible()`, it replaces the original.

**Examples:**
- kitabi (ACC) -> strip -i -> kitab -> unmutate b to p -> kitap
- agaci (ACC) -> strip -i -> agac -> unmutate c to c -> agac

## Step B: Derivational Detection

Step B identifies and strips one derivational suffix from the stem. It draws from two sources:

1. **DERIV slot (slot_order=1):** 52 entries loaded from `tr_derivations.json`, covering noun-to-noun (-lik, -ci, -das), noun-to-adjective (-li, -siz, -sal, -ik, -msi), noun-to-verb (-la, -las, -lan, -landir), verb-to-noun (-ma, -is, -mak, -ici, -maca, -gi, -inti, -nak, -ti, -man, -c), verb-to-adjective (-an, -dik, -acak, -mis, -ar, -asi), verb-to-verb (-ala, -imsa, -istir, -a, -iver, -dur, -egel, -ekoy, -eyaz), adjective-to-adjective (-msi, -imtirak), adjective-to-verb (-ikla, -sa), noun/adj-to-adverb (-ce, -arca, -leyin, -sizin), and special forms (-ki relational, -gil family).

2. **NONFINITE slot (slot_order=10):** Participles and converbs are also treated as pseudo-derivational in Step B, since they convert verbs to adjective/adverb-like forms.

**Conservative constraints:**
- Suffix must be at least 2 characters (single-char derivational suffixes like -a/-e are too ambiguous)
- Remaining stem must be at least 3 characters
- Remaining stem must contain at least one vowel
- Vowel harmony must be satisfied between remaining stem and suffix

Entries are sorted longest-first to prefer the most specific match. The first valid match is accepted, and Step B returns the shortened stem plus a derivation chain entry of the form `"suffix->LOGICAL_TAG"`.

## Step C: Root Extraction

Step C performs **iterative deepening** by calling Step B up to 3 times to peel successive derivational layers:

```
root = stem
for _ in range(3):
    new_root, chain = step_b(root)
    if new_root == root:
        break  # no more derivations found
    root = new_root
```

This allows the engine to handle multiply-derived forms. For example, a word like "guclendirmek" (to strengthen) can be decomposed through multiple derivational layers: guc (strength) + len (reflexive denominative) + dir (causative) + mek (infinitive).

The 3-layer limit is a practical guard against runaway stripping on short stems.

## Tag Inventory

### Part of Speech Values

| POS | Description |
|-----|-------------|
| NOUN | Nominal (default when case tag present) |
| VERB | Verbal (default when tense tag present) |
| ADJ | Adjective |
| CONV | Converb (adverbial participle) |
| PART | Participle |
| ADV | Adverb (from closed-class or derivation) |
| PRON | Pronoun (closed-class only) |
| POSTP | Postposition (closed-class only) |
| CONJ | Conjunction (closed-class only) |
| UNKNOWN | Unclassified (neither case nor tense found) |

### Feature Tags

| Tag key | Possible values | Source slot(s) |
|---------|----------------|----------------|
| num | SG, PL | NUM (2), PERSON_NUM (9), MOOD (8), COPULA (11) |
| poss | 1SG, 2SG, 3SG, 1PL, 2PL, 3PL | POSS (3) |
| case | NOM, ACC, DAT, LOC, ABL, GEN, INS | CASE (4) |
| modality | ABIL | ABIL (4.5) |
| voice | PASS, CAUS, RECIP, REFL | VOICE (5) |
| polarity | NEG | NEG (6), ABIL (4.5), TENSE (7, for AORIST_NEG) |
| tense | PAST_DEF, PAST_NARR, PRES_PROG, PRES_AORIST, FUT | TENSE (7), COMPOUND_TENSE (14), NONFINITE (10) |
| aspect | PROG, HAB, PERF, ACT | TENSE (7), COMPOUND_TENSE (14), NONFINITE (10) |
| mood | COND, OPT, IMP, NECESS, INF | MOOD (8), COMPOUND_TENSE (14) |
| person | 1, 2, 3 | PERSON_NUM (9), MOOD (8, for imperatives), COPULA (11) |
| epist | INFER | EPIST (9.5) |
| cop | PRES, PAST, COND, NARR | COPULA (11), COMPOUND_TENSE (14) |
| q | YES_NO | QUESTION (12) |
| add | ALSO | ADDITIVE (13) |
| pos | PART, CONV | NONFINITE (10, overrides main POS) |
| sem | WHEN, WHILE, MANNER, UNTIL, WITHOUT, AFTER (+ closed-class semantics) | NONFINITE (10), closed-class |
| register | FORMAL | MOOD (8, for IMP_2PL_FORMAL) |
| deriv | (derivation type string) | DERIV (1, from derivations.json) |

### Bundle Count

The configuration defines **74 suffix entries** in `tr_suffixes.json`, each with its own tag bundle. However, many entries share identical tag bundles (e.g., COP_PRES_3SG and P3SG both have zero morphs), and empirical analysis across real text produces approximately **63 observed unique bundles**. The difference arises because some config-defined bundles are never observed in isolation (zero-suffix entries) or because tag merging across slots produces composite bundles not present in any single entry.

## Config Files

| File | Entry count | Surface variants | Slots covered |
|------|-------------|-----------------|---------------|
| `tr_suffixes.json` | 74 | 306 | 15 (slots 2-14 inclusive, plus 4.5 and 9.5) |
| `tr_derivations.json` | 52 | 182 | 1 (DERIV, mapped to slot_order=1) |

## Validators

### Word-level: `check_morph_sequence_tr`

Defined in `shared.py`, this validator enforces Turkish-specific morphological well-formedness on each token:

1. **Nominal slot ordering:** For NOUN and ADJ tokens, the tag keys DERIV, NUM, POSS, CASE must appear in that order. If any are present out of sequence, the token is invalid. This enforces the Turkish nominal template.

2. **Verbal slot ordering:** For VERB tokens, the tag keys DERIV, VOICE, NEG, TENSE, MOOD, PERSON_NUM must follow the verbal slot order. Specifically:
   - NEG must precede TENSE (negation is always closer to the stem than tense marking)
   - Imperative mood (IMP) restricts person to 2nd person only
   - Causative voice (CAUS) cannot co-occur with passive base (`voice_base=PASS`)

### Sentence-level: `validate_sentence_structure_tr`

Also in `shared.py`, this validator checks sentence-level grammatical constraints for Turkish's SOV word order:

1. **Imperative person restriction:** Any verb with mood=IMP must have person=2 or no person tag. First and third person imperatives use distinct jussive/optative forms.

2. **Evidentiality consistency:** A verb cannot simultaneously carry PAST_DEF tense (direct witness) and PAST_NARR in its derivation chain (hearsay). These represent incompatible evidential stances.

3. **Nominal slot ordering at sentence level:** Re-validates that all NOUN/ADJ tokens have their NUM, POSS, CASE slots in correct sequential order, as a redundant safety check.

Content tokens exclude those with POS of UNKNOWN, FOREIGN, or PUNCT.

## Known Limitations

1. **Loanword harmony exceptions:** Turkish loanwords from Arabic, Persian, and French often violate vowel harmony (e.g., "saat" has back-front vowel sequence). The engine's harmony check may reject valid suffixed forms of these words, leading to under-analysis.

2. **Short-stem over-stripping:** Despite the minimum stem length guards, words with 3-4 character stems can still be over-stripped when multiple short suffixes each pass the plausibility check individually.

3. **No morphophonological alternation beyond consonant mutation:** The engine does not handle vowel dropping (e.g., "burun" to "burnu" when possessive is added), vowel shortening, or other stem-internal alternations. These forms may be under-analyzed.

4. **Suffix ambiguity residual cases:** While the two-pass system resolves the most common ambiguities (case vs. mood, locative vs. additive), some edge cases remain. Words like "yedi" (seven / he ate) require semantic context that the engine cannot access.

5. **No compound word segmentation:** Turkish compounds (e.g., "denizalti" = submarine) are not decomposed at the compound boundary.

6. **Buffer consonant false positives:** Despite penalization in sorting, some stem-final y/n/s characters may still be incorrectly consumed as buffer consonants in rare cases.

7. **Aorist stem allomorphy:** The aorist suffix (-ar/-er for monosyllabic stems, -ir/-ir/-ur/-ur for polysyllabic stems) depends on syllable count, which the engine does not explicitly check. It relies on harmony filtering to achieve approximately correct behavior.

8. **Zero morphemes:** Several slots have zero-suffix entries (NOM case, IMP_2SG, P3SG, COP_PRES_3SG) that cannot be positively identified -- they are inferred by absence of overt marking.

## Test Coverage

| Test file | Test count | Categories |
|-----------|-----------|------------|
| `test_tr_engine_nominal.py` | 38 | Nominal inflection: plurals, possessives, cases, combined nominal paradigms |
| `test_tr_engine_verbal.py` | 54 | Verbal inflection: tenses, moods, voice, negation, person agreement, compound tenses |
| `test_tr_engine_particles.py` | 34 | Closed-class words: postpositions, conjunctions, pronouns, adverbs, question particles |
| `test_tr_engine_sentence.py` | 15 | Sentence-level validation: SOV order, imperative constraints, evidentiality consistency |
| `test_tr_engine_smoke.py` | 1 | Basic instantiation and round-trip smoke test |
| `test_tr_engine_stress.py` | 68 | Edge cases: short stems, harmony violations, buffer consonants, compound forms, ambiguous suffixes |
| `test_tr_engine_adversarial.py` | 73 | Adversarial tests: over-stripping prevention, false suffix matches, cross-slot ambiguity, mutation edge cases |

**Total: 283 tests across 7 files**

All tests were rewritten in Phase 0 to assert correct grammatical analysis rather than merely checking that the engine runs without errors. The adversarial test suite was added specifically to validate the two-pass architecture and stem validation guards against known failure modes of the original single-pass design.
