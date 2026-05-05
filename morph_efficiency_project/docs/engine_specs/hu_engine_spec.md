# Hungarian Engine Design Specification

**Language:** Hungarian (hu)  
**Typology:** Agglutinative-fusional hybrid  
**Engine file:** `scripts/engines/hu_engine.py` (to be built)  
**Status:** Design phase

---

## Morphological Overview

Hungarian (magyar nyelv) is a Uralic language of the Finno-Ugric branch, typologically classified as an agglutinative-fusional hybrid. Like Turkish, Hungarian builds word forms by concatenating suffixes onto stems in a largely predictable slot order. However, unlike Turkish's near-perfect one-morpheme-per-function transparency, Hungarian exhibits significant fusional behavior in specific domains -- most notably in its verbal person-marking suffixes, where a single morpheme simultaneously encodes person, number, and definiteness of the object. This fusion places Hungarian in a middle position on the agglutinative-to-fusional spectrum, more complex than Turkish but more regular than Spanish or Arabic.

The phonological backbone of Hungarian morphology is vowel harmony (maganhangzo-illeszkedas). Hungarian enforces front/back harmony: stems containing back vowels (a, a, o, o, u, u) select back-harmonic suffix variants, while stems containing front vowels select front variants. Front vowels are further subdivided into unrounded (e, e, i, i) and rounded (o, o, u, u), yielding a three-way distinction for certain suffixes. For example, the allative case suffix appears as -hoz (back), -hez (front unrounded), or -hoz (front rounded). Unlike Turkish, where the last vowel almost always determines harmony, Hungarian has a class of "vacillating" stems (ingadozo tovu szavak) and transparent vowels (i, i, e, e) that do not block the harmony of preceding back vowels, creating systematic exceptions that the engine must accommodate.

Hungarian possesses one of the richest case systems among European languages, with 18 productive grammatical cases (some analyses count up to 31 by including less productive or semi-fossilized forms). The cases are organized into spatial triads: for each spatial relation, there is an interior set (-ban/-ben INESSIVE, -bol/-bol ELATIVE, -ba/-be ILLATIVE), a surface set (-n/-on/-en/-on SUPERESSIVE, -rol/-rol DELATIVE, -ra/-re SUBLATIVE), and a proximity set (-nal/-nel ADESSIVE, -tol/-tol ABLATIVE, -hoz/-hez/-hoz ALLATIVE). This triadic organization is typologically remarkable and highly productive. Beyond spatial cases, Hungarian has structural cases (nominative, accusative, dative, instrumental) and abstract cases (causal-final -ert, translative -va/-ve, terminative -ig, formal -kent, distributive -nkent).

The definite-indefinite verb conjugation system (hatarozott es hatarozatlan ragozas, also called alanyi and targyas ragozas) is Hungarian's most distinctive morphological feature and sets it apart from virtually all other European languages. Every Hungarian verb has two complete conjugation paradigms: the indefinite conjugation is used when the verb has no object, an indefinite object, or a first/second person object, while the definite conjugation is used when the verb has a definite third-person object (marked by the definite article, a demonstrative, a proper name, or a possessive suffix). This means that each person-number cell in the verbal paradigm has two distinct suffix forms, and the choice between them carries syntactic information about the object's definiteness. For example, "latom" (I see it, DEF) vs. "latok" (I see something, INDEF) differ only in the final suffix, but encode radically different argument structures. The engine must identify which paradigm a given form belongs to based on suffix shape alone.

Possessive marking (birtokos szemelyjel) in Hungarian is expressed through suffixes that encode the person and number of the possessor, attached directly to the possessed noun. These suffixes interact with both the plural marker and case suffixes, producing complex stacking patterns. A form like "hazaimban" decomposes as haz (house) + -a- (linking vowel) + -i- (plural possessed) + -m (POSS.1SG) + -ban (INESSIVE) = "in my houses." The possessive suffixes show partial fusion: third-person forms (-ja/-je vs. -a/-e) vary based on the stem's phonological shape, and the plural-possessed marker -i- interacts with subsequent possessive and case suffixes in ways that are not fully transparent.

Hungarian also makes extensive use of verbal prefixes (igekotok), which function as separable particles analogous to German separable prefixes or English phrasal verb particles. Prefixes like meg- (perfectivizing), el- (away), ki- (out), be- (in), fel/fol- (up), and le- (down) attach to verb stems to modify aspect or meaning. Crucially, these prefixes separate from the verb under negation, focus, and certain syntactic conditions, appearing after the verb rather than before it. The engine treats these as derivational prefixes in Step B but must be aware that their positional flexibility in sentences complicates identification. This is a known limitation: the engine analyzes word forms in isolation and cannot determine whether a free-standing "meg" is a separated prefix or a discourse particle.

## Closed-Class Intercept

The engine intercepts **142 closed-class function words** before attempting any morphological analysis. These are atomic lexical items that should not be decomposed.

**Pronouns (22):** en (1SG), te (2SG), o (3SG), mi (1PL), ti (2PL), ok (3PL), ez (DEM.PROX), az (DEM.DIST), ki (INTERR.WHO), mi (INTERR.WHAT), maga (FORMAL.3SG), on (FORMAL.2SG), minden (UNIVERSAL), senki (NEG.WHO), valaki (INDEF.WHO), nehany (INDEF.SOME), mas (OTHER), egyeb (OTHER), ilyen (DEM.QUAL.PROX), olyan (DEM.QUAL.DIST), ugyanaz (DEM.SAME), mindegyik (UNIVERSAL.EACH)

**Conjunctions (24):** es (AND), vagy (OR), de (BUT), hanem (BUT.RATHER), mert (BECAUSE), hogy (THAT/SO_THAT), ha (IF), mint (THAN/AS), sem (NEITHER), pedig (HOWEVER), ugyanis (NAMELY), tehat (THEREFORE), vagyis (THAT_IS), illetve (RESPECTIVELY), am (BUT), bar (ALTHOUGH), noha (ALTHOUGH), holott (WHEREAS), amikor (WHEN), amig (WHILE/UNTIL), miutan (AFTER), mielott (BEFORE), ahogy (AS), mivel (SINCE)

**Question words (12):** ki (WHO), mi (WHAT), hol (WHERE), hova (WHITHER), honnan (WHENCE), mikor (WHEN), hogyan (HOW), miert (WHY), melyik (WHICH), mennyi (HOW_MUCH), hany (HOW_MANY), milyen (WHAT_KIND)

**Postpositions (23):** alatt (UNDER), folott (ABOVE), felett (ABOVE), elott (BEFORE), mogott (BEHIND), mellett (BESIDE), kozott (BETWEEN), korul (AROUND), helyett (INSTEAD), nelkul (WITHOUT), ellen (AGAINST), fele (TOWARD), irant (TOWARD), szerint (ACCORDING_TO), szamara (FOR), utan (AFTER), ota (SINCE), kozben (DURING), vegett (FOR_PURPOSE), reven (BY_MEANS), folytan (DUE_TO), gyanant (AS), mulva (IN_TIME), altal (BY)

**Particles (16):** is (ALSO), sem (NEITHER), ne (PROHIBITIVE), nem (NEGATION), se (NEITHER), mar (ALREADY), meg (STILL/YET), meg (PREVERB/PERF), el (PREVERB/AWAY), ki (PREVERB/OUT), be (PREVERB/IN), fel (PREVERB/UP), fol (PREVERB/UP), le (PREVERB/DOWN), at (PREVERB/ACROSS), vissza (PREVERB/BACK)

**Articles (3):** a (DEF), az (DEF.PREVOCALIC), egy (INDEF)

**Numerals (10):** egy (ONE), ketto (TWO), harom (THREE), negy (FOUR), ot (FIVE), hat (SIX), het (SEVEN), nyolc (EIGHT), kilenc (NINE), tiz (TEN)

**Misc function words (32):** itt (HERE), ott (THERE), ide (HITHER), oda (THITHER), innen (HENCE), onnan (THENCE), igy (THUS), ugy (THAT_WAY), igen (YES), nagyon (VERY), tul (TOO_MUCH), eleg (ENOUGH), csak (ONLY), alig (BARELY), szinte (ALMOST), csaknem (ALMOST), majdnem (ALMOST), legfeljebb (AT_MOST), legalabb (AT_LEAST), inkabb (RATHER), sot (MOREOVER), megsem (NEVERTHELESS), megis (STILL/YET), rozsa (FORMER), kulonben (OTHERWISE), mindig (ALWAYS), soha (NEVER), most (NOW), azonnal (IMMEDIATELY), rogtOn (IMMEDIATELY), hamar (SOON), lassan (SLOWLY)

**Total: 142 entries**

Note: Several items appear in multiple categories. "ki" is both an interrogative pronoun and a verbal prefix; "mi" is both a pronoun (we) and a question word (what); "az" is both a demonstrative pronoun and a definite article. Context-free analysis cannot disambiguate these, so the closed-class intercept returns the most common function. The engine assigns a `sem=` tag reflecting the most frequent usage.

## Two-Pass Analysis Architecture

Hungarian requires a two-pass architecture similar to the Turkish engine, motivated by partially overlapping suffix forms across nominal and verbal paradigms.

### The Problem

Hungarian suffix ambiguity arises in several domains:

- **-t**: accusative case (hazat = house.ACC) vs. past tense marker (irt = he/she wrote)
- **-m**: possessive 1SG (hazam = my house) vs. verbal 1SG indefinite (irom = I write.DEF, but also lakom = I live.INDEF)
- **-tok/-tek/-tok**: possessive 2PL (hazatok = your.PL house) vs. verbal 2PL indefinite (irtok = you.PL write)
- **-ja/-je**: possessive 3SG (haza = his/her house) vs. verbal 3SG definite (irja = he/she writes it)
- **-k**: plural noun (hazak = houses) vs. verbal 1SG indefinite (irok = I write)

These overlaps mean a greedy single-pass strip risks misidentifying nominal suffixes as verbal ones or vice versa.

### Pass 1: Full Slot Stripping

Pass 1 executes comprehensive stripping across all slots in descending slot order. For nominal forms, it processes: CASE (slot 4), POSS (slot 3), NUM (slot 2), DERIV (slot 1). For verbal forms, it processes: PERSON_DEF (slot 7), MOOD (slot 6), TENSE (slot 5), DERIV (slot 1). Both nominal and verbal slot chains are attempted, and the best-fitting analysis is retained.

### Pass 2: Nominal-Only Stripping

Pass 2 restricts analysis to nominal slots only: CASE (4), POSS (3), NUM (2). This conservative pass avoids verbal misidentification.

### Selection Logic

1. **If Pass 1 found clear verbal markers** (PAST tense suffix -t/-tt/-ott/-ett/-ott, conditional -na/-ne, imperative -j-, or unambiguous person+definiteness markers): prefer Pass 1, unless Pass 2 consumed more suffix material with plausible nominal analysis.

2. **If Pass 2 found nominal markers** (case suffix, possessive, or plural) and produced a plausible stem: prefer Pass 2 when the stem is longer, when Pass 1's stem is implausible, or when Pass 1 produced ambiguous tags.

3. **Otherwise**: fall back to Pass 1.

## Stem Validation

The `_stem_plausible()` method enforces two constraints:

- **Minimum length**: the stem must be at least 2 characters long.
- **Vowel requirement**: the stem must contain at least one vowel from the Hungarian vowel inventory (a, a, e, e, i, i, o, o, o, o, u, u, u, u).

Per-slot minimum stem lengths:

| Slot | Min stem length | Rationale |
|------|----------------|-----------|
| 3 (POSS) | 3 | -m, -d, -a are single-character; high false-match risk |
| 7 (PERSON_DEF) | 3 | -m, -d, -k are single-character |
| All others | 2 | Default minimum |

## Step A: Inflectional Stripping

### Suffix Slot System

Hungarian uses two distinct templates depending on part of speech:

**NOUN template:** stem + [DERIV] + [NUM] + [POSS] + [CASE]

**VERB template:** stem + [DERIV] + [TENSE/MOOD] + [PERSON+NUM+DEF]

| Slot | Name | slot_order | Domain | Contents |
|------|------|-----------|--------|----------|
| 1 | DERIV | 1 | Both | Derivational suffixes (from hu_derivations.json) |
| 2 | NUM | 2 | Nominal | Plural -k (with linking vowels) |
| 3 | POSS | 3 | Nominal | Possessive person/number + plural possessed -i- |
| 4 | CASE | 4 | Nominal | 18 grammatical cases |
| 5 | TENSE | 5 | Verbal | Present (zero), Past (-t/-tt), Conditional (-na/-ne/-na/-ne) |
| 6 | MOOD | 6 | Verbal | Indicative (zero), Subjunctive/Imperative (-j-) |
| 7 | PERSON_DEF | 7 | Verbal | Person + Number + Definiteness (fusional) |

Stripping order: slots are processed from highest to lowest (7, 6, 5, 4, 3, 2, 1). Within each slot, the longest matching suffix satisfying vowel harmony and stem plausibility is accepted.

### Slot 2 -- NUM (Szam jel)

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| PL | -k, -ok, -ak, -ek, -ok | num=PL |

The linking vowel before -k depends on the stem's final sound and harmony class. Consonant-final stems require a linking vowel; vowel-final stems take -k directly (e.g., haz-ak but auto-k). The engine strips -k, -ok, -ak, -ek, -ok and validates harmony.

### Slot 3 -- POSS (Birtokos szemelyjel)

Hungarian possessive suffixes encode the person and number of the possessor. The plural-possessed marker -i- indicates the possessed item is plural (e.g., hazaim = my houses, where -i- marks plurality of houses and -m marks first person singular possessor).

**Singular possessed forms:**

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| POSS_1SG | -m, -om, -am, -em, -om | poss=1SG |
| POSS_2SG | -d, -od, -ad, -ed, -od | poss=2SG |
| POSS_3SG | -ja, -je, -a, -e | poss=3SG |
| POSS_1PL | -nk, -unk, -unk | poss=1PL |
| POSS_2PL | -tok, -tek, -tok, -atok, -etek, -otok | poss=2PL |
| POSS_3PL | -juk, -juk, -uk, -uk | poss=3PL |

**Plural possessed forms (preceded by -i-):**

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| POSS_PL_1SG | -im, -aim, -eim, -jaim, -jeim | poss=1SG, poss_num=PL |
| POSS_PL_2SG | -id, -aid, -eid, -jaid, -jeid | poss=2SG, poss_num=PL |
| POSS_PL_3SG | -i, -ai, -ei, -jai, -jei | poss=3SG, poss_num=PL |
| POSS_PL_1PL | -ink, -aink, -eink, -jaink, -jeink | poss=1PL, poss_num=PL |
| POSS_PL_2PL | -itok, -itek, -aitok, -eitek, -jaitok, -jeitek | poss=2PL, poss_num=PL |
| POSS_PL_3PL | -ik, -aik, -eik, -jaik, -jeik | poss=3PL, poss_num=PL |

The -j- linking element appears after vowel-final stems and certain consonant-final stems with back vowels. Its presence vs. absence is partly lexically determined, which is a known source of ambiguity.

**Stripping order within POSS:** Plural-possessed forms (longer, more specific) are attempted before singular-possessed forms. Within each group, longest suffix first.

### Slot 4 -- CASE (Eset rag)

Hungarian has 18 productive grammatical cases. They are organized below by functional grouping.

**Structural cases:**

| Case | Suffix | Harmony variants | Example | Meaning | Tags |
|------|--------|-----------------|---------|---------|------|
| NOM | -zero | -- | haz | house | case=NOM |
| ACC | -t | -at, -ot, -et, -ot | hazat | house (OBJ) | case=ACC |
| DAT | -nak/-nek | front/back | haznak | to/for house | case=DAT |
| INS | -val/-vel | + assimilation | hazzal | with house | case=INS |

**Abstract/semantic cases:**

| Case | Suffix | Harmony variants | Example | Meaning | Tags |
|------|--------|-----------------|---------|---------|------|
| CAUSAL | -ert | -- | hazert | for/because of house | case=CAUSAL |
| TRANSL | -va/-ve | + assimilation | hazza | (turning) into house | case=TRANSL |
| FORMAL | -kent | -- | hazkent | as (a) house | case=FORMAL |
| DISTRIB | -nkent | -- | hazonkent | per house | case=DISTRIB |
| TERMIN | -ig | -- | hazig | as far as house | case=TERMIN |

**Interior spatial cases:**

| Case | Suffix | Harmony variants | Example | Meaning | Tags |
|------|--------|-----------------|---------|---------|------|
| INESS | -ban/-ben | front/back | hazban | in house | case=INESS |
| ELAT | -bol/-bol | front/back | hazbol | out of house | case=ELAT |
| ILLAT | -ba/-be | front/back | hazba | into house | case=ILLAT |

**Surface spatial cases:**

| Case | Suffix | Harmony variants | Example | Meaning | Tags |
|------|--------|-----------------|---------|---------|------|
| SUPER | -n, -on, -en, -on | linking vowel | hazon | on house | case=SUPER |
| DELAT | -rol/-rol | front/back | hazrol | off/about house | case=DELAT |
| SUBLAT | -ra/-re | front/back | hazra | onto house | case=SUBLAT |

**Proximity spatial cases:**

| Case | Suffix | Harmony variants | Example | Meaning | Tags |
|------|--------|-----------------|---------|---------|------|
| ADESS | -nal/-nel | front/back | haznal | at/near house | case=ADESS |
| ABLAT | -tol/-tol | front/back | haztol | from (near) house | case=ABLAT |
| ALLAT | -hoz/-hez/-hoz | 3-way | hazhoz | toward house | case=ALLAT |

**Design decision on additional cases:** Hungarian has several semi-productive case-like suffixes that some grammarians count as additional cases:

| Suffix | Name | Example | Decision |
|--------|------|---------|----------|
| -stul/-stul | SOCIATIVE | hazastul (together with house) | EXCLUDED -- low frequency, semi-fossilized |
| -kor | TEMPORAL | haromkor (at three) | EXCLUDED -- attaches primarily to numerals/time words |
| -kepp/-keppen | MODAL | valamilyenkeppen (in some way) | EXCLUDED -- attaches only to manner words |

These are excluded from the core 18-case system. The engine may optionally recognize them in a future expansion. If encountered, they will be left on the stem and flagged as UNKNOWN derivational material.

**Consonant assimilation at morpheme boundaries:**

The instrumental (-val/-vel) and translative (-va/-ve) cases trigger regressive consonant assimilation: the initial v- of the suffix assimilates to the stem-final consonant. For example: haz + -val = hazzal (not *hazval), ut + -val = uttal (not *utval), kez + -vel = kezzel (not *kezvel).

The engine must reverse this assimilation during stripping. After removing what appears to be a case suffix, if the suffix was -INS or -TRANSL, the engine checks whether the stem ends in a doubled consonant and, if so, restores the single consonant as the stem-final sound:

| Surface | Analysis | Restoration |
|---------|----------|-------------|
| hazzal | hazz + -al? No. haz + -zal -> haz + INS (v->z assimilation) | stem = haz |
| kezzel | kez + -zel -> kez + INS (v->z assimilation) | stem = kez |
| uttal | ut + -tal -> ut + INS (v->t assimilation) | stem = ut |

Implementation: after stripping -al/-el (the post-assimilation remnant), check if the stem's final two characters are identical consonants. If so, deduplicate and tag as INS or TRANSL.

### Slot 5 -- TENSE (Igeidojel)

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| PRES | (zero) | tense=PRES |
| PAST | -t, -tt, -ott, -ett, -ott, -att | tense=PAST |
| COND | -na, -ne, -na, -ne | tense=COND |

**Past tense allomorphy:** The past tense marker -t has complex allomorphic behavior:
- After vowels: -tt (e.g., kere + tt = kertt -> kert, "he asked")
- After certain consonant clusters: -ott/-ett/-ott with linking vowel (e.g., mond + ott = mondott, "he said")
- After other consonants: -t (e.g., ir + t = irt, "he wrote")

The engine attempts to strip these in longest-first order (-ott, -ett, -ott, -att, -tt, -t) and validates the remaining stem.

**Conditional mood:** The conditional marker -na/-ne (or lengthened -na/-ne in definite forms) attaches after the stem and before person suffixes. Harmony determines front/back variant selection.

### Slot 6 -- MOOD (Mod)

| Logical | Surface variants | Tags |
|---------|-----------------|------|
| IND | (zero) | mood=IND |
| SUBJ_IMP | -j-, surface realization varies | mood=SUBJ |

**Subjunctive/Imperative morpheme -j-:**

The subjunctive/imperative mood is marked by an underlying -j- morpheme that surfaces in various forms depending on the stem-final consonant:

| Stem-final | Surface of -j- | Example |
|------------|----------------|---------|
| Vowel | -j- | kere + j + e = kerje (let him ask) |
| t | -s- | lat + j + a = lassa (let him see) -- assimilation t+j -> ss |
| s | -s- | mos + j + a = mossa (let him wash) -- assimilation s+j -> ss |
| sz | -ssz- | vesz + j + e = vegye (let him buy) -- irregular |
| z | -zz- | hoz + j + a = hozza (let him bring) -- assimilation z+j -> zz |
| d | -dj-/-ggy- | mond + j + a = mondja (let him say) or irregular |
| l | -lj- | hal + j + on = haljon (let him die) |

This morphophonological complexity means the engine cannot simply strip a literal -j-. Instead, the MOOD slot recognizes the subjunctive by examining the person+definiteness suffix in conjunction with stem-final modifications. This is handled by matching full TENSE+MOOD+PERSON compound suffixes for subjunctive forms rather than isolating the -j- alone.

### Slot 7 -- PERSON_DEF (Szemely + Hatarozottsag)

**This is the fusional core of Hungarian verbal morphology.** Each suffix in this slot simultaneously encodes three features: person (1, 2, 3), number (SG, PL), and definiteness of the object (DEF, INDEF). This makes it the only genuinely fusional slot in the otherwise agglutinative system.

#### Indefinite Conjugation (Alanyi ragozas)

Used when the verb has no object, an indefinite object, or a 1st/2nd person object.

**Present indicative indefinite:**

| Person | Surface variants | Tags | Example |
|--------|-----------------|------|---------|
| 1SG | -ok, -ek, -ok | person=1, num=SG, def=INDEF | ir-ok (I write) |
| 2SG | -sz, -asz, -esz | person=2, num=SG, def=INDEF | ir-sz (you write) |
| 3SG | (zero) | person=3, num=SG, def=INDEF | ir (he/she writes) |
| 1PL | -unk, -unk | person=1, num=PL, def=INDEF | ir-unk (we write) |
| 2PL | -tok, -tek, -tok | person=2, num=PL, def=INDEF | ir-tok (you.PL write) |
| 3PL | -nak, -nek | person=3, num=PL, def=INDEF | ir-nak (they write) |

**Past indicative indefinite:**

| Person | Surface variants | Tags | Example |
|--------|-----------------|------|---------|
| 1SG | -tam, -tem | person=1, num=SG, def=INDEF, tense=PAST | ir-tam (I wrote) |
| 2SG | -tal, -tel | person=2, num=SG, def=INDEF, tense=PAST | ir-tal (you wrote) |
| 3SG | -t, -ott, -ett, -ott | person=3, num=SG, def=INDEF, tense=PAST | ir-t (he/she wrote) |
| 1PL | -tunk, -tunk | person=1, num=PL, def=INDEF, tense=PAST | ir-tunk (we wrote) |
| 2PL | -tatok, -tetek | person=2, num=PL, def=INDEF, tense=PAST | ir-tatok (you.PL wrote) |
| 3PL | -tak, -tek | person=3, num=PL, def=INDEF, tense=PAST | ir-tak (they wrote) |

**Conditional indefinite:**

| Person | Surface variants | Tags | Example |
|--------|-----------------|------|---------|
| 1SG | -nek, -nak | person=1, num=SG, def=INDEF, tense=COND | ir-nek (I would write) |
| 2SG | -nal, -nel | person=2, num=SG, def=INDEF, tense=COND | ir-nal (you would write) |
| 3SG | -na, -ne | person=3, num=SG, def=INDEF, tense=COND | ir-na (he would write) |
| 1PL | -nank, -nenk | person=1, num=PL, def=INDEF, tense=COND | ir-nank (we would write) |
| 2PL | -natok, -netek | person=2, num=PL, def=INDEF, tense=COND | ir-natok (you.PL would write) |
| 3PL | -nanak, -nenek | person=3, num=PL, def=INDEF, tense=COND | ir-nanak (they would write) |

**Subjunctive/Imperative indefinite:**

| Person | Surface variants | Tags | Example |
|--------|-----------------|------|---------|
| 1SG | -jak, -jek | person=1, num=SG, def=INDEF, mood=SUBJ | ir-jak (let me write) |
| 2SG | -j, -jal, -jel | person=2, num=SG, def=INDEF, mood=SUBJ | ir-j (write!) |
| 3SG | -jon, -jen, -jon | person=3, num=SG, def=INDEF, mood=SUBJ | ir-jon (let him write) |
| 1PL | -junk, -junk | person=1, num=PL, def=INDEF, mood=SUBJ | ir-junk (let us write) |
| 2PL | -jatok, -jetek | person=2, num=PL, def=INDEF, mood=SUBJ | ir-jatok (write.PL!) |
| 3PL | -janak, -jenek | person=3, num=PL, def=INDEF, mood=SUBJ | ir-janak (let them write) |

#### Definite Conjugation (Targyas ragozas)

Used when the verb has a definite third-person object.

**Present indicative definite:**

| Person | Surface variants | Tags | Example |
|--------|-----------------|------|---------|
| 1SG | -om, -em, -om | person=1, num=SG, def=DEF | ir-om (I write it) |
| 2SG | -od, -ed, -od | person=2, num=SG, def=DEF | ir-od (you write it) |
| 3SG | -ja, -i | person=3, num=SG, def=DEF | ir-ja (he writes it) |
| 1PL | -juk, -juk | person=1, num=PL, def=DEF | ir-juk (we write it) |
| 2PL | -jatok, -itek | person=2, num=PL, def=DEF | ir-jatok (you.PL write it) |
| 3PL | -jak, -ik | person=3, num=PL, def=DEF | ir-jak (they write it) |

**Past indicative definite:**

| Person | Surface variants | Tags | Example |
|--------|-----------------|------|---------|
| 1SG | -tam, -tem | person=1, num=SG, def=DEF, tense=PAST | ir-tam (I wrote it) |
| 2SG | -tad, -ted | person=2, num=SG, def=DEF, tense=PAST | ir-tad (you wrote it) |
| 3SG | -ta, -te | person=3, num=SG, def=DEF, tense=PAST | ir-ta (he wrote it) |
| 1PL | -tuk, -tuk | person=1, num=PL, def=DEF, tense=PAST | ir-tuk (we wrote it) |
| 2PL | -tatok, -tetek | person=2, num=PL, def=DEF, tense=PAST | ir-tatok (you.PL wrote it) |
| 3PL | -tak, -tek | person=3, num=PL, def=DEF, tense=PAST | ir-tak (they wrote it) |

**Conditional definite:**

| Person | Surface variants | Tags | Example |
|--------|-----------------|------|---------|
| 1SG | -nam, -nem | person=1, num=SG, def=DEF, tense=COND | ir-nam (I would write it) |
| 2SG | -nad, -ned | person=2, num=SG, def=DEF, tense=COND | ir-nad (you would write it) |
| 3SG | -na, -ne | person=3, num=SG, def=DEF, tense=COND | ir-na (he would write it) |
| 1PL | -nank, -nenk | person=1, num=PL, def=DEF, tense=COND | ir-nank (we would write it) |
| 2PL | -natok, -netek | person=2, num=PL, def=DEF, tense=COND | ir-natok (you.PL would write it) |
| 3PL | -nak, -nek | person=3, num=PL, def=DEF, tense=COND | ir-nak (they would write it) |

**Subjunctive/Imperative definite:**

| Person | Surface variants | Tags | Example |
|--------|-----------------|------|---------|
| 1SG | -jam, -jem | person=1, num=SG, def=DEF, mood=SUBJ | ir-jam (let me write it) |
| 2SG | -jad/-d, -jed/-d | person=2, num=SG, def=DEF, mood=SUBJ | ir-d (write it!) |
| 3SG | -ja, -je | person=3, num=SG, def=DEF, mood=SUBJ | ir-ja (let him write it) |
| 1PL | -juk, -juk | person=1, num=PL, def=DEF, mood=SUBJ | ir-juk (let us write it) |
| 2PL | -jatok, -jetek | person=2, num=PL, def=DEF, mood=SUBJ | ir-jatok (write.PL it!) |
| 3PL | -jak, -jek | person=3, num=PL, def=DEF, mood=SUBJ | ir-jak (let them write it) |

#### The -lak/-lek Form (1SG subject, 2nd person object)

Hungarian has a unique conjugation form for the combination of first person singular subject acting on a second person object (singular or plural). This form does not fit neatly into either the definite or indefinite paradigm:

| Tense | Surface variants | Tags | Example |
|-------|-----------------|------|---------|
| PRES | -lak, -lek | person=1, num=SG, def=2OBJ | lat-lak (I see you) |
| PAST | -talak, -telek | person=1, num=SG, def=2OBJ, tense=PAST | lat-talak (I saw you) |
| COND | -nalak, -nelek | person=1, num=SG, def=2OBJ, tense=COND | lat-nalak (I would see you) |
| SUBJ | -jalak, -jelek | person=1, num=SG, def=2OBJ, mood=SUBJ | lat-jalak (let me see you) |

This is tagged as def=2OBJ to distinguish it from both DEF and INDEF paradigms. It is a uniquely Hungarian construction with no parallel in Turkish or other comparator languages.

#### Paradigm Identification Strategy

The engine determines which paradigm (DEF vs. INDEF) a verb form belongs to by matching the person+number+definiteness suffix as a composite unit. The key discriminating suffixes are:

| Discrimination | INDEF suffix | DEF suffix | Distinguishable? |
|---------------|-------------|-----------|------------------|
| 1SG PRES | -ok/-ek/-ok | -om/-em/-om | YES (k vs. m) |
| 2SG PRES | -sz/-asz/-esz | -od/-ed/-od | YES (sz vs. d) |
| 3SG PRES | zero | -ja/-i | YES (zero vs. overt) |
| 1PL PRES | -unk/-unk | -juk/-juk | YES (unk vs. juk) |
| 2PL PRES | -tok/-tek/-tok | -jatok/-itek | YES (length differs) |
| 3PL PRES | -nak/-nek | -jak/-ik | YES (nak vs. jak) |
| 1SG PAST | -tam/-tem | -tam/-tem | NO -- identical forms |
| 2SG PAST | -tal/-tel | -tad/-ted | YES (l vs. d) |
| 3SG PAST | -t/-ott/-ett | -ta/-te | YES (zero-ending vs. vowel) |
| 1PL PAST | -tunk/-tunk | -tuk/-tuk | YES (nk vs. k) |
| 3SG COND | -na/-ne | -na/-ne | NO -- identical forms |

Where forms are identical across paradigms (1SG PAST, 3SG COND), the engine cannot disambiguate without sentential context. In these cases, it defaults to INDEF and flags `def=AMBIG` in the tags.

### Vowel Harmony

Hungarian vowel harmony is a phonological constraint that governs suffix selection. The engine validates every candidate suffix match against harmony rules.

**Vowel classification:**

| Category | Vowels |
|----------|--------|
| Back | a, a, o, o, u, u |
| Front unrounded | e, e, i, i |
| Front rounded | o, o, u, u |

**Harmony rules:**

1. **2-way suffixes** (front/back): the suffix variant must match the harmonic class of the stem's last relevant vowel. Back stems select back suffixes; front stems select front suffixes. Example: -ban (back) / -ben (front).

2. **3-way suffixes** (front-unrounded / front-rounded / back): the suffix variant must match both the backness and rounding of the stem's last vowel. Example: -hoz (back) / -hez (front-unrounded) / -hoz (front-rounded).

3. **Transparent vowels:** The vowels i, i, and sometimes e, e are "transparent" -- they do not determine harmony in stems that also contain back vowels. For example, "radir" (eraser) has a back vowel (a) followed by a transparent vowel (i), and selects back-harmonic suffixes: radirnak (not *radirnek). The engine determines harmony by scanning from the last vowel backward, skipping transparent vowels, until a non-transparent vowel is found.

4. **Anti-harmonic stems:** A small set of stems with only front vowels nevertheless take back-harmonic suffixes. Examples: hid (bridge) -> hidak (not *hidek), cet (whale) -> cetek BUT cel (target) -> celok (not *celek). These are lexically marked exceptions. The engine maintains an anti-harmonic stem list in `hu_irregulars.json`.

5. **Mixed stems:** Stems containing both front and back vowels (common in loanwords) generally follow the last syllable's vowel. Example: sofor (driver) -> sofornek (front, because last vowel is o which is front-rounded). Compound words follow the harmony of the last component.

**Implementation:**

```
def _check_harmony(stem: str, suffix: str) -> bool:
    stem_vowel = _get_last_harmonic_vowel(stem)
    if stem_vowel is None:
        return True  # no vowel in stem -> harmony trivially satisfied
    suffix_vowel = _get_first_vowel(suffix)
    if suffix_vowel is None:
        return True  # no vowel in suffix -> trivially satisfied
    stem_class = _classify_vowel(stem_vowel)  # BACK, FRONT_UNROUND, FRONT_ROUND
    suffix_class = _classify_vowel(suffix_vowel)
    # For 2-way suffixes, FRONT_UNROUND and FRONT_ROUND both count as FRONT
    if suffix_class == stem_class:
        return True
    if stem_class in (FRONT_UNROUND, FRONT_ROUND) and suffix_class in (FRONT_UNROUND, FRONT_ROUND):
        return True  # both front, acceptable for 2-way
    return False
```

The `_get_last_harmonic_vowel()` function scans the stem right-to-left, skipping transparent vowels (i, i), to find the vowel that governs harmony.

### Possessive + Case Stacking

Possessive and case suffixes stack in the fixed order POSS + CASE. The engine strips CASE first (outermost), then POSS. Examples:

| Surface form | Decomposition | Tags |
|-------------|---------------|------|
| hazamban | haz + -am (POSS.1SG) + -ban (INESS) | poss=1SG, case=INESS |
| hazainkban | haz + -a- + -i- (PL.POSS) + -nk (POSS.1PL) + -ban (INESS) | poss=1PL, poss_num=PL, case=INESS |
| kezemmel | kez + -em (POSS.1SG) + -vel -> -mel (INS, assimilated) | poss=1SG, case=INS |
| hazatokat | haz + -atok (POSS.2PL) + -at (ACC) | poss=2PL, case=ACC |

After possessive stripping, the accusative case takes the special form -t (without linking vowel) when the possessed noun already ends in a vowel from the possessive suffix. This interaction is handled by checking whether a possessive suffix was already stripped before validating the accusative suffix form.

## Step B: Derivational Detection

Step B identifies and strips derivational suffixes and prefixes. It draws from `hu_derivations.json`.

### Derivational Suffixes (~35 rules)

**Noun-forming suffixes:**

| Suffix | Harmony variants | Source POS | Target POS | Meaning | Example |
|--------|-----------------|-----------|-----------|---------|---------|
| -sag/-seg | front/back | N/ADJ | N | quality, -ness | szep -> szepseg (beauty) |
| -as/-es | front/back | V | N | verbal noun, -tion | ir -> iras (writing) |
| -at/-et | front/back | V | N | result noun | gondol -> gondolat (thought) |
| -o/-o | front/back | V | N/ADJ | agent/present participle | tanit -> tanito (teacher) |
| -many/-meny | front/back | V | N | product | kormany -> kormany (product -- less productive) |

**Adjective-forming suffixes:**

| Suffix | Harmony variants | Source POS | Target POS | Meaning | Example |
|--------|-----------------|-----------|-----------|---------|---------|
| -i | -- | N | ADJ | relating to | Budapest -> budapesti (Budapest-ian) |
| -s | -- | N | ADJ | having, possessing | ero -> eros (strong) |
| -u/-u | front/back | N | ADJ | characterized by | nagy szemu (big-eyed) |
| -tlan/-telen | front/back | N/V | ADJ | without, -less | hatar -> hatartalan (boundless) |
| -tlan/-telen | front/back | V | ADJ | un-...-ed | ir -> iratlan (unwritten) |
| -os/-es/-os | 3-way | N | ADJ | related to, -ous | viz -> vizes (watery) |
| -beli | -- | N | ADJ | pertaining to | varos -> varosbeli (of the city) |

**Verb-forming suffixes:**

| Suffix | Harmony variants | Source POS | Target POS | Meaning | Example |
|--------|-----------------|-----------|-----------|---------|---------|
| -it | -- | ADJ/N | V | causative, to make X | szep -> szeppit (to beautify) |
| -ul/-ul | front/back | ADJ/N | V | intransitive, to become X | szep -> szepul (to become beautiful) |
| -hat/-het | front/back | V | V | possibility, can/may | ir -> irhat (can write) |
| -gat/-get | front/back | V | V | frequentative/iterative | ir -> irogat (to write repeatedly) |
| -kodik/-kedik/-kodik | 3-way | N/ADJ | V | reflexive/reciprocal | tanul -> tanulkodik (to study intently) |
| -tat/-tet | front/back | V | V | causative | ir -> irat (to have written) |
| -odik/-edik/-odik | 3-way | ADJ/N | V | inchoative | orog -> oregedik (to grow old) |
| -z/-oz/-ez/-oz | 3-way | N | V | to do/use X | foci -> focizik (to play soccer) |

**Adverb-forming suffixes:**

| Suffix | Harmony variants | Source POS | Target POS | Meaning | Example |
|--------|-----------------|-----------|-----------|---------|---------|
| -ul/-ul | front/back | ADJ | ADV | in X manner | szep -> szepen (beautifully) -- but -ul form |
| -an/-en | front/back | ADJ | ADV | in X manner | gyors -> gyorsan (quickly) |
| -lag/-leg | front/back | ADJ | ADV | -ly | altalanos -> altalanossaglag? -- marginal |

### Verbal Prefixes (~15 rules)

| Prefix | Meaning | Example |
|--------|---------|---------|
| meg- | perfective/completive | ir -> megir (to write completely) |
| el- | away, beginning | megy -> elmegy (to go away) |
| ki- | out | megy -> kimegy (to go out) |
| be- | in | megy -> bemegy (to go in) |
| fel- / fol- | up | megy -> felmegy (to go up) |
| le- | down | megy -> lemegy (to go down) |
| at- | across | megy -> atmegy (to cross) |
| vissza- | back | megy -> visszamegy (to go back) |
| ossze- | together | gyujt -> osszegyujt (to gather together) |
| szet- | apart | szed -> szetszed (to take apart) |
| hozzaa- | to/added | szokik -> hozzaszokik (to get used to) |
| bele- | into | esik -> beleesik (to fall into) |
| ra- | onto | nez -> ranez (to look at) |
| ide- | hither | jon -> idejon (to come here) |
| oda- | thither | megy -> odamegy (to go there) |

**Prefix stripping constraint:** Prefixes are only stripped if the remaining stem is at least 3 characters and contains a vowel. Prefix stripping is attempted in Step B after suffix-based derivational detection has been exhausted.

**Total derivational rules: ~50** (35 suffixes + 15 prefixes)

### Conservative Constraints

- Suffix must be at least 2 characters (single-char suffixes like -i, -s are attempted only if remaining stem is at least 4 characters)
- Remaining stem must be at least 3 characters
- Remaining stem must contain at least one vowel
- Vowel harmony must be satisfied between remaining stem and suffix
- Entries are sorted longest-first to prefer the most specific match

## Step C: Root Extraction

Step C performs iterative deepening by calling Step B up to 3 times to peel successive derivational layers:

```
root = stem
chain = []
for _ in range(3):
    new_root, derivation = step_b(root)
    if new_root == root:
        break  # no more derivations found
    chain.append(derivation)
    root = new_root
```

This allows the engine to handle multiply-derived forms. For example, "megirhatatlansag" (the state of not being able to be written) can be decomposed:

1. Strip -sag -> QUALITY -> stem: megirhatatlana
2. Strip -tlan -> PRIVATIVE -> stem: megirhat
3. Strip meg- -> PERF -> stem: irhat (or further: strip -hat -> POSSIBILITY -> stem: ir)

The 3-layer limit is a practical guard. The theoretical maximum nesting depth in Hungarian is higher (up to 5-6 derivational layers in rare cases), but 3 layers cover >98% of naturally occurring forms.

## Tag Inventory

### Part of Speech Values

| POS | Description |
|-----|-------------|
| NOUN | Nominal (default when case tag present) |
| VERB | Verbal (default when tense or def tag present) |
| ADJ | Adjective |
| ADV | Adverb (from closed-class or derivation) |
| PRON | Pronoun (closed-class only) |
| DET | Determiner/article (closed-class only) |
| ADP | Postposition (closed-class only) |
| CONJ | Conjunction (closed-class only) |
| PART | Particle (closed-class only) |
| NUM | Numeral |
| UNKNOWN | Unclassified (neither case nor verbal tags found) |

### Feature Tags

| Tag key | Possible values | Source slot(s) |
|---------|----------------|----------------|
| num | SG, PL | NUM (2), PERSON_DEF (7) |
| case | NOM, ACC, DAT, INS, CAUSAL, TRANSL, INESS, ELAT, ILLAT, SUPER, DELAT, SUBLAT, ADESS, ABLAT, ALLAT, TERMIN, FORMAL, DISTRIB | CASE (4) |
| poss | 1SG, 2SG, 3SG, 1PL, 2PL, 3PL | POSS (3) |
| poss_num | PL | POSS (3, plural-possessed forms) |
| person | 1, 2, 3 | PERSON_DEF (7) |
| tense | PRES, PAST, COND | TENSE (5), PERSON_DEF (7, compound forms) |
| mood | IND, SUBJ | MOOD (6), PERSON_DEF (7, subjunctive compound forms) |
| def | DEF, INDEF, 2OBJ, AMBIG | PERSON_DEF (7) |
| degree | POS, COMP, SUPER | Derivational (comparative -bb, superlative leg-...-bb) |
| derived_chain | list of strings | DERIV (1), Step B/C |

### Bundle Count

**Nominal bundles:**
- 18 cases x 2 numbers (SG/PL) = 36 base bundles
- 18 cases x 6 possessive persons = 108 possessive bundles
- 18 cases x 6 possessive persons x plural possessed = 108 plural-possessed bundles
- Theoretical maximum: 252

However, many combinations are rare or unattested. Empirically expected: ~80-100 distinct nominal bundles in natural text.

**Verbal bundles:**
- 6 person/number cells x 2 definiteness (DEF/INDEF) = 12 base cells
- 12 cells x 3 tenses (PRES/PAST/COND) = 36 tense-inflected cells
- 12 cells x 1 subjunctive mood = 12 subjunctive cells
- 4 -lak/-lek forms (1 per tense/mood) = 4 special cells
- Total verbal: 52

**Combined estimate: 90-120 observed unique bundles** in natural text. This is justified by:
- Many nominal case+possessive combinations are unattested in practice
- Verbal paradigms are relatively complete (most cells are attested)
- Derivational tags expand the space but are represented as chains, not atomic bundles

## Config Files

| File | Entry count | Surface variants | Content |
|------|-------------|-----------------|---------|
| `hu_suffixes.json` | ~95 | ~350 | Case (18 entries, ~50 variants), Possessive (12 base + 12 plural-possessed, ~80 variants), Verbal paradigms (52+ entries, ~180 variants), Plural (1 entry, 5 variants), Degree (2 entries, ~8 variants) |
| `hu_irregulars.json` | ~120 | -- | Irregular verbs: v-stems (lo -> lov-, no -> nov-, szo -> sov-), sz-stems (tesz -> tev-, vesz -> vev-, lesz -> lev-, visz -> viv-, eszik -> ev-, iszik -> iv-), consonant-dropping verbs (alszik -> alud-, fekszik -> fekud-), suppletive stems (van -> vagy-/vol-/len-, megy -> men-, jon -> jov-), anti-harmonic noun stems (~30 entries) |
| `hu_derivations.json` | ~50 | ~120 | Derivational suffixes (35 entries) and prefixes (15 entries) with POS-change mappings |

### hu_irregulars.json Detail

Hungarian irregular verbs fall into several well-defined classes:

**v-stem verbs (v-tos igek):** Stems that end in a long vowel in citation form but show a -v- before vowel-initial suffixes:
- lo (to shoot): lov- before vowels -> lovok (I shoot), lott (he shot)
- no (to grow): nov- -> novok, nott
- szo (to weave): sov- -> sovok, sott
- ro (to carve): rov- -> rovok, rott
- fo (to cook): fov- -> fovok, fott

**sz-stem verbs (sz-es igek):** Stems ending in -sz that show -v- or -d- alternants:
- tesz (to do/put): tev-/tet- -> tevok? No: teszek (I do), tettem (I did), tegyen (let him do)
- vesz (to buy/take): vev-/vet- -> veszek, vettem, vegyen
- lesz (to become): lev-/let- -> leszek, lettem, legyen
- visz (to carry): viv-/vit- -> viszek, vittem, vigyen
- eszik (to eat): ev-/et-/ed- -> eszem/eszek, ettem, egyen
- iszik (to drink): iv-/it-/id- -> iszom/iszok, ittam, igyon

**Suppletive verbs:**
- van (to be): present vagy-/van-, past vol-/volt-, subjunctive le-/len-/legy-
- megy (to go): present men-/megy-, past men-/ment-, subjunctive men-/menj-
- jon (to come): present jov-/jon-, past jot-/jott-, subjunctive joj-/jojj-

**Anti-harmonic stems (~30):** Nouns and adjectives with front vowels that take back-harmonic suffixes:
- hid (bridge): hidak, hidat, hidnak (all back)
- nyil (arrow): nyilak, nyilat
- sir (grave): sirok, sirot
- cet (whale): cetek (front -- actually regular; illustrates diagnostic difficulty)
- hej (shell): hejak (back)
- der (frost): derek (front -- regular)

The irregulars file maps each irregular stem to its alternant forms with conditions (before-vowel, past-tense, subjunctive).

## Validators

### Word-level: `check_morph_sequence_hu`

To be defined in `shared.py`. This validator enforces Hungarian-specific morphological well-formedness:

1. **Nominal slot ordering:** For NOUN tokens, the tag keys NUM, POSS, CASE must appear in the canonical order stem + NUM + POSS + CASE. If CASE precedes POSS, or NUM follows POSS, the token is invalid.

2. **Verbal feature completeness:** For VERB tokens, the tags must include at minimum `person` and `def`. A verb without person agreement is invalid (except infinitives, which receive mood=INF and no person tag).

3. **Definiteness coherence:** If `def=DEF`, the verb must not also carry mood=IMP with person=3 in the indefinite paradigm suffix shape. Subjunctive/imperative 3SG definite (-ja/-je) vs. indefinite (-jon/-jen/-jon) are distinct and must not be cross-assigned.

4. **Conditional+subjunctive exclusion:** A verb cannot simultaneously carry tense=COND and mood=SUBJ. These are mutually exclusive in Hungarian (unlike some analyses of Turkish where conditional is treated as a mood).

5. **Possessive on non-nominals:** If `poss` tag is present, POS must be NOUN (or UNKNOWN). Possessive suffixes on verbs indicate misanalysis.

### Sentence-level: `validate_sentence_structure_hu`

To be defined in `shared.py`. This validator checks sentence-level constraints:

1. **Topic-focus structure:** Hungarian has relatively free word order governed by information structure (topic-focus-verb). The validator does not enforce rigid word order but checks that:
   - If a verb carries mood=SUBJ/IMP with person=3, it should not be sentence-initial (imperative 3rd person typically follows a topic)
   - Verbal prefixes, if detected as separated particles, should appear adjacent to their verb (simplified check)

2. **Definiteness agreement (where detectable):** If a verb carries def=DEF, at least one other token in the sentence should be a definite noun (carrying a definite article "a"/"az" or a demonstrative). This is a soft check -- violations produce warnings, not failures.

3. **Nominative subject requirement:** If the sentence contains a verb with person agreement but no pronoun or nominative-marked noun is present, this is acceptable (Hungarian is pro-drop). No error is raised.

4. **Case government basic check:** Certain postpositions govern specific cases. If a postposition from the closed-class list is followed or preceded by a noun with an incompatible case, a warning is issued.

## Known Limitations

1. **Vowel harmony exceptions:** Anti-harmonic stems (front-vowel stems taking back suffixes) and vacillating stems (accepting either front or back suffixes, e.g., "fotel" -> fotelt/fotelet) require lexical lookup. Without exhaustive coverage in `hu_irregulars.json`, some forms will be misanalyzed due to incorrect harmony validation.

2. **Consonant assimilation complexity:** The instrumental and translative cases trigger v-assimilation, but other assimilations occur at morpheme boundaries (e.g., subjunctive -j- assimilating with stem-final consonants: latja vs. lassa). The engine handles v-assimilation systematically but treats -j- assimilation via compound suffix lookup rather than productive rules, which may miss rare forms.

3. **Verbal prefix separation:** Hungarian verbal prefixes (igekotok) separate from the verb under negation, focus, and interrogation. The engine analyzes words in isolation and cannot determine whether a free-standing particle (meg, el, ki, etc.) is a separated prefix or an independent word. This is a fundamental architectural limitation of word-level analysis.

4. **1SG PAST and 3SG COND ambiguity:** In the past tense 1SG and conditional 3SG, definite and indefinite forms are identical (-tam/-tem for past 1SG; -na/-ne for conditional 3SG). The engine defaults to INDEF and flags def=AMBIG. Disambiguation requires sentential context.

5. **No handling of dialectal variation:** Hungarian dialects (e.g., e-zo, o-zo) show vowel alternations that the engine does not model. Standard Hungarian (kozmagyar) is assumed throughout.

6. **Possessive 3SG ambiguity:** The 3SG possessive suffix appears as -ja/-je (after certain stems) or -a/-e (after others), with the choice partly lexically determined. The engine attempts both forms but may misidentify the boundary between stem and suffix for unfamiliar stems.

7. **Compound word segmentation:** Hungarian compounds (e.g., vasutallomas = railway station = vas + ut + allomas) are not segmented. The engine treats the entire compound as a single stem.

8. **Fusional suffix ambiguity:** Some verbal suffixes are identical across paradigms (e.g., -tok/-tek serves as both POSS.2PL and VERB.2PL.INDEF). Without syntactic context, POS assignment relies on heuristic: if case tags are found, prefer nominal; if tense tags are found, prefer verbal.

9. **Degree marking:** Comparative (-bb) and superlative (leg-...-bb) operate partly as derivational, partly as inflectional processes. The superlative prefix leg- is treated as derivational in Step B, but its interaction with the comparative suffix -bb across an adjective stem requires coordinated stripping that may fail on short stems.

10. **Low-vowel lengthening:** Certain stems undergo vowel alternation when suffixed: e.g., "haz" (house) -> "haza-" (his house), "viz" (water) -> "vize-" (his water), with the final vowel appearing or changing. This stem-internal alternation is not handled productively; known alternating stems are listed in `hu_irregulars.json`.

## Test Plan

| Test file | Test count | Categories |
|-----------|-----------|------------|
| `test_hu_engine_cases.py` | 100 | All 18 cases: 18 base cases x 2 numbers x ~3 harmony variants, plus assimilation tests for INS and TRANSL |
| `test_hu_engine_conjugation.py` | 110 | Definite/indefinite paradigms: 12 cells x 3 tenses x 2 paradigms = 72 base, +12 subjunctive, +4 -lak/-lek, +22 irregular verb forms |
| `test_hu_engine_possessive.py` | 60 | Possessive suffixes: 6 persons x 2 (singular/plural possessed) x 3 case combinations + stacking with plural and case |
| `test_hu_engine_harmony.py` | 50 | Vowel harmony: back stems, front-unrounded stems, front-rounded stems, transparent vowels, anti-harmonic stems, mixed stems, vacillating stems |
| `test_hu_engine_tense_mood.py` | 50 | Verbal tense/mood: past allomorphy (-t/-tt/-ott/-ett), conditional, subjunctive -j- assimilation patterns, compound tense+person forms |
| `test_hu_engine_derivation.py` | 40 | Derivational suffixes and prefixes: noun-forming, adj-forming, verb-forming, prefix stripping, iterative deepening through multiple layers |
| `test_hu_engine_closedclass.py` | 30 | Closed-class intercept: pronouns, conjunctions, postpositions, question words, articles, particles -- verify no spurious decomposition |
| `test_hu_engine_adversarial.py` | 50 | Edge cases: over-stripping prevention, short stems, cross-paradigm suffix ambiguity (nominal POSS vs. verbal PERSON), harmony violation rejection, consonant assimilation reversal, irregular verb stem recovery |
| `test_hu_engine_sentence.py` | 20 | Sentence-level validation: definiteness agreement, topic-focus compatibility, slot ordering, possessive-on-verb rejection |

**Total: 510 tests across 9 files**

All tests should assert correct grammatical analysis (correct root, correct tags, correct POS) rather than merely checking that the engine runs without errors. The adversarial suite specifically targets the known ambiguity zones documented in the limitations section: nominal-verbal suffix overlap, harmony edge cases, and fusional paradigm identification.
