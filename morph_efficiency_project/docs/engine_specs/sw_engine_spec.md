# Swahili Engine Design Specification

**Language:** Swahili (sw)  
**Typology:** Classificatory (Bantu noun class system) -- morphological outlier  
**Engine file:** `scripts/engines/sw_engine.py` (to be built)  
**Status:** Design phase

---

## Morphological Overview

Swahili morphology (mfumo wa mofolojia ya Kiswahili) is built on the Bantu noun class system, a classificatory mechanism that organizes all nouns into 15+ classes, each identified by a characteristic prefix. These classes are conventionally numbered 1 through 18 and organized into singular/plural pairs: M-/WA- (Classes 1/2, humans), M-/MI- (Classes 3/4, plants and natural objects), JI-/MA- (Classes 5/6, fruits, augmentatives, paired body parts), KI-/VI- (Classes 7/8, tools, diminutives, languages), N-/N- (Classes 9/10, animals, loanwords, miscellaneous), U- (Class 11, abstract qualities and long thin objects), U- (Class 14, abstract concepts, often no plural), KU- (Class 15, infinitives and gerunds), and PA-/KU-/MU- (Classes 16/17/18, locative). This system is not merely a gender system like those of Romance or Semitic languages -- it is a comprehensive classificatory mechanism that pervades every syntactic relationship in the clause.

The defining feature of Swahili morphology is the agreement cascade (mfumo wa upatanisho). When a noun belongs to a particular class, every word that is syntactically related to it -- verbs, adjectives, possessives, demonstratives, relative markers, and numerals -- must carry a prefix that agrees with that noun's class. For example, the noun "kitabu" (book, Class 7) triggers ki- on verbs ("kitabu ki-na-anguka" = the book is falling), ki- on adjectives ("kitabu ki-kubwa" = big book), ch-a on possessives ("kitabu ch-angu" = my book), and ki-le on demonstratives ("kitabu ki-le" = that book). Change the noun to its plural "vitabu" (books, Class 8), and every agreement marker changes in lockstep: "vitabu vi-na-anguka", "vitabu vi-kubwa", "vitabu vy-angu", "vitabu vi-le". This cascade is a chain reaction: one morphological choice on the noun propagates through the entire clause, producing a system where a single noun class prefix can force 3 to 6 simultaneous prefix changes elsewhere.

The Swahili verb is a complex agglutinative structure organized around a strict positional template: NEG + SUBJ + TENSE + REL + OBJ + ROOT + EXT + FINAL_VOWEL. A single verb form can encode subject agreement, tense/aspect, an object pronoun, the lexical root, one or more derivational extensions (causative, applicative, passive, reciprocal, stative, reversive), and mood via the final vowel -- all within a single orthographic word. For example, "ha-wa-ta-ki-pik-ish-i-w-a" (they will not make it be cooked for someone) contains: negation ha-, subject agreement wa- (Class 2 / 3PL), future tense ta-, object prefix ki- (Class 7), verb root -pik- (cook), causative extension -ish-, applicative extension -i-, passive extension -w-, and final vowel -a. This is eight morphemes in one word, encoding what English expresses with an entire passive causative clause.

Verb extensions (viambishi vya kauli) are a productive derivational mechanism that modifies the valency and voice of the verb root. The five primary extensions are: applicative -i-/-e- (adds a benefactive or locative argument: pika > pikia "cook for"), causative -ish-/-esh- (adds a causer: pika > pikisha "make cook"), passive -w- (removes the agent: pika > pikwa "be cooked"), reciprocal -an- (makes the action mutual: penda > pendana "love each other"), and stative -ik-/-ek- (indicates potential or state: pika > pikika "be cookable"). A sixth extension, the reversive -u-/-o- (reverses the action: funga > fungua "open/untie"), is also productive. These extensions can stack in predictable orderings: causative + applicative + passive (pikishiwa, "be made to cook for"), producing combinatorial complexity within a single verb form.

What makes Swahili a morphological outlier is not agglutination per se -- Turkish is also agglutinative -- but the agreement cascade mechanism. In Turkish, suffixes on a noun do not force changes on the verb. In Arabic, the templatic system is word-internal. In Swahili, the noun class system creates a CROSS-WORD dependency: the morphological form of one word (the noun) determines the morphological form of every other word that syntactically relates to it. This is a cascade or concordial mechanism -- fundamentally different from both the concatenative agglutination of Turkish and the non-concatenative templatic morphology of Arabic. The engine must therefore not only analyze individual words but also track noun class information to validate agreement patterns across the clause.

Additionally, Swahili has a significant Arabic loanword stratum (estimated at 30-40% of the core vocabulary), reflecting centuries of trade and cultural contact along the East African coast. These loanwords (such as "kitabu" from Arabic "kitab", "wakati" from "waqt", "habari" from "khabar") have been fully integrated into the noun class system, receiving Bantu class prefixes and participating in agreement cascades. The engine must handle these loanwords as regular Swahili nouns -- they are NOT Arabic morphologically, even though their roots are Arabic etymologically.

## Closed-Class Intercept

The engine intercepts an estimated **95 closed-class entries** before the main stripping pipeline. These are function words that do not undergo productive morphological processes and would be incorrectly analyzed if sent through the prefix-stripping pipeline. Swahili's closed-class set is notably smaller than that of many other languages because numerous function words that are invariant in other languages (demonstratives, possessives, some quantifiers) inflect by noun class in Swahili and must therefore be processed through the agreement system.

### Categories

**Conjunctions (viunganishi) -- subcat=CONJ:**  
na (and), au (or), ama (or, colloquial), lakini (but), bali (but rather), wala (nor), kwa sababu (because), kwa kuwa (because/since), ingawa (although), ingawaje (even though), ijapokuwa (even though), kama (if), ili (so that/in order to), hata (even/until), ila (except), halafu (then/afterwards), tena (and also/again), kwani (because/for), yaani (that is/meaning), au sivyo (otherwise). **Count: 20**

**Prepositions / Prepositional phrases (vihusishi) -- subcat=PREP:**  
kwa (with/for/by), katika (in/at/among), kuhusu (about/concerning), bila (without), baada ya (after), kabla ya (before), mbele ya (in front of), nyuma ya (behind), juu ya (on top of/above), chini ya (under/below), kati ya (between/among), karibu na (near/close to), mbali na (far from), pamoja na (together with), badala ya (instead of), kulingana na (according to), tangu (since), mpaka (until/up to), kutoka (from), hadi (until/up to), kuelekea (toward), nje ya (outside of), ndani ya (inside of). **Count: 23**

**Question words (maneno ya kuuliza) -- subcat=INTERROG:**  
nani (who), nini (what), wapi (where), lini (when), vipi (how), jinsi gani (how/in what manner), kwa nini (why), -ngapi (how many -- note: this inflects by class, so only the stem is listed). **Count: 8**

**Invariant adverbs (vielezi) -- subcat=ADV:**  
sana (very/much), pia (also/too), tu (only/just), sasa (now), hapa (here), pale (there), kule (over there), huko (there, Class 17), humu (in here, Class 18), bado (not yet/still), tena (again), haraka (quickly), pole pole (slowly), kabisa (completely/absolutely), labda (perhaps/maybe), pengine (perhaps), hasa (especially), halafu (then), mara (immediately/at once), pamoja (together), mbali (far), karibu (near/almost), ndio (yes/indeed), hapana (no), naam (yes, polite), siyo (no/not so), hivi (like this), hivyo (like that). **Count: 28**

**Interjections (viingizi) -- subcat=INTERJ:**  
lo (oh!), kumbe (so!/it turns out), ala (oh!, surprise), basi (well/so/enough), haya (okay/alright), sawa (okay/fine), pole (sorry), hodi (knock knock/may I come in?), karibu (welcome), starehe (relax), kwaheri (goodbye), jambo (hello/matter). **Count: 12**

**Existential/copular particles -- subcat=COP:**  
ni (is/am/are, affirmative copula), si (is not/am not, negative copula), ndio (it is/indeed), siyo (it is not). **Count: 4**

**Total: ~95 entries** across 6 subcategories.

### False-Positive Guards

Words like "katika" (in/at) superficially resemble a Class 7 noun prefix (ki-) preceded by further morphology. The closed-class intercept runs BEFORE any prefix stripping, so these frozen forms are tagged as atomic units and never enter the stripping pipeline. Similarly, "kabisa" (completely), "karibu" (near/welcome), and "kama" (if/like) begin with ka-/ki- but are not noun-class-prefixed forms. The particle "na" (and/with) must not be confused with the tense marker na- (present progressive) in verb analysis.

## The Noun Class System

This is the core mechanism of the Swahili engine. The noun class table defines the prefix inventory, agreement markers, and semantic associations for each class.

### Complete Noun Class Table

| Class | Noun Prefix | Typical Semantics | Subj Agr | Obj Agr | Adj Agr | Poss Stem | Demonst. Proximal | Example |
|-------|------------|-------------------|----------|---------|---------|-----------|-------------------|---------|
| 1 | m-, mw- (before vowel) | Humans (singular) | a- (yu- before vowel) | m-, mw- | m-, mw- | w-a | huyu | mtoto (child), mwalimu (teacher) |
| 2 | wa-, w- (before vowel) | Humans (plural) | wa- | wa- | wa-, w- | w-a | hawa | watoto (children), walimu (teachers) |
| 3 | m-, mw- (before vowel) | Plants, natural objects (singular) | u- | u- | m-, mw- | w-a | huu | mti (tree), mwezi (moon) |
| 4 | mi-, my- (before vowel) | Plants, natural objects (plural) | i- | i- | mi-, my- | y-a | hii | miti (trees), myezi (moons) |
| 5 | ji-, j- (before vowel), zero (common) | Fruits, augmentatives, paired body parts (sg) | li- | li- | ji-, j-, zero | l-a | hili | jicho (eye), jina (name), tunda (fruit) |
| 6 | ma- | Fruits, augmentatives, collective (plural) | ya- | ya- | ma- | y-a | haya | macho (eyes), majina (names), matunda (fruits) |
| 7 | ki-, ch- (before vowel) | Tools, diminutives, languages (singular) | ki- | ki- | ki-, ch- | ch-a | hiki | kitu (thing), kitabu (book), Kiswahili |
| 8 | vi-, vy- (before vowel) | Tools, diminutives (plural) | vi- | vi- | vi-, vy- | vy-a | hivi | vitu (things), vitabu (books) |
| 9 | n-, ny- (before vowel), zero (loanwords) | Animals, loanwords, misc (singular) | i- | i- | n-, ny-, zero | y-a | hii | nyumba (house), ndege (bird/plane), kalamu (pen) |
| 10 | n-, ny-, zero | Animals, loanwords, misc (plural) | zi- | zi- | n-, ny-, zero | z-a | hizi | nyumba (houses), ndege (birds), kalamu (pens) |
| 11 | u-, w- (before vowel) | Abstract, long/thin objects (singular) | u- | u- | m-, mw- | w-a | huu | ukuta (wall), uzi (thread), ukweli (truth) |
| 14 | u-, w- (before vowel) | Abstract concepts (no distinct plural) | u- | u- | m-, mw- | w-a | huu | uhuru (freedom), uzuri (beauty), utoto (childhood) |
| 15 | ku- | Infinitives, gerunds | ku- | ku- | ku- | kw-a | huku | kusoma (to read/reading), kula (to eat) |
| 16 | pa- | Definite/specific location | pa- | pa- | pa- | p-a | hapa | mahali (place, definite location) |
| 17 | ku- | Indefinite/general location | ku- | ku- | ku- | kw-a | huku | (used with locative -ni: nyumbani kule) |
| 18 | mu-, m- | Interior location | mu-, m- | mu-, m- | mu-, m- | mw-a | humu | (used with locative -ni: nyumbani mle) |

### Noun Class Prefix Stripping Algorithm

The engine processes noun class identification as follows:

1. **Longest-prefix-first matching:** Attempt to match the word against known noun class prefixes, ordered by length (mw- before m-, ny- before n-, etc.) to prevent partial matches.

2. **Prefix ambiguity resolution:** Classes 1 and 3 share the prefix m-/mw-. The engine disambiguates using:
   - Semantic heuristics: if the stem is a known human referent, assign Class 1; otherwise, default to Class 3
   - Plural lookup: if the plural form uses wa-, the singular is Class 1; if mi-, the singular is Class 3
   - A lookup table of ~200 common Class 1 vs. Class 3 nouns stored in `sw_classes.json`

3. **Class 11 vs. Class 14 disambiguation:** Both use u-/w-. Class 11 nouns typically have plurals in Class 10 (u-kuta > kuta, using n-/zero), while Class 14 nouns either lack plurals or use Class 6 (u-zuri > ma-zuri). A lookup table in `sw_classes.json` handles the ~100 most common cases.

4. **Class 9/10 nasal prefix complexity:** The N- prefix undergoes nasal assimilation:
   - n + p > mp (n + paka > mpaka, but this is a separate word "border")
   - n + b > mb (n + buzi > mbuzi "goat")
   - n + d > nd (n + dege > ndege "bird")
   - n + g > ng (n + gombe > ng'ombe "cow")
   - n + j > nj (n + jia > njia "path")
   - n + z > nz (n + zige > nzige "locust")
   - ny + vowel (ny + umba > nyumba "house")
   - Zero prefix for many loanwords (kalamu "pen", meza "table")
   The engine maintains a nasal assimilation table and attempts reverse-assimilation to recover the stem.

5. **Class 5 zero-prefix nouns:** Many Class 5 nouns have no overt prefix (tunda "fruit", gari "car", yai "egg"). These are identified via a lookup table in `sw_classes.json` rather than prefix stripping, since there is no prefix to strip.

6. **Output:** For each noun, the engine records:
   - `nc=CLASS_NUMBER` (1-18)
   - `num=SG` or `num=PL` (based on whether the class is a singular or plural class)
   - The extracted stem (noun minus class prefix)

### Agreement Cascade Validation

The engine uses noun class information to predict agreement markers on related words. Given a noun's class, the engine can validate:

1. **Subject agreement on verbs:** The subject prefix on the verb must match the noun's class agreement prefix (e.g., Class 7 noun requires ki- subject prefix)
2. **Object agreement on verbs:** If an object prefix is present, it must match the class of the object noun
3. **Adjective agreement:** The adjective prefix must match the noun's adjective agreement prefix
4. **Possessive agreement:** The possessive connector must match (e.g., ch-a for Class 7, vy-a for Class 8)
5. **Demonstrative agreement:** The demonstrative must carry the correct class marker

This validation is performed in `validate_sentence_structure_sw()` at the sentence level.

## Step A: Inflectional Stripping

### Verb Morphology

The Swahili verb template is the most important structural element after the noun class system. The full positional template is:

```
NEG + SUBJ + TENSE + REL + OBJ + ROOT + EXT + FINAL_VOWEL
```

Stripping proceeds in **reverse positional order** -- from the outermost (rightmost) morpheme inward. This is the opposite of the surface order: strip final vowel first, then extensions, then object prefix, then relative marker, then tense, then subject, then negation.

#### Final Vowel (stripped first)

The final vowel encodes mood and is the outermost morpheme:

| Final Vowel | Function | Tags |
|-------------|----------|------|
| -a | Default indicative | mood=IND |
| -e | Subjunctive, negative present/future, polite imperative | mood=SUBJ |
| -i | Negative past (with ha-...-ku-) | mood=NEG_PAST |

Stripping rule: remove the final vowel (-a, -e, or -i) and record the mood tag. Guard: the remaining stem must have at least 2 characters after stripping.

#### Verb Extensions (stripped second)

Extensions are suffixes inserted between the root and the final vowel. They are stripped in reverse order (rightmost extension first). Extensions can stack, so stripping is performed in a while-loop until no more extensions are found.

| Extension | Suffix | Semantic Function | Tags | Example |
|-----------|--------|-------------------|------|---------|
| Causative | -ish-, -esh- | Make/cause someone to do | voice=CAUS | pika > pik-ish-a (cook > make cook) |
| Applicative | -i-, -e-, -li-, -le- | Do for/to someone, directional | valence=APPL | soma > som-e-a (read > read for) |
| Passive | -w- | Be done (removes agent) | voice=PASS | pika > pik-w-a (cook > be cooked) |
| Reciprocal | -an- | Do to each other | voice=RECIP | penda > pend-an-a (love > love each other) |
| Stative | -ik-, -ek- | Be in a state, potential | valence=STAT | pika > pik-ik-a (cook > be cookable) |
| Reversive (intr.) | -uk-, -ok- | Undo (intransitive) | valence=REV | funga > fung-uk-a (close > come open) |
| Reversive (tr.) | -u-, -o- | Undo (transitive) | valence=REV | funga > fung-u-a (close > open) |

**Extension stacking order** (inner to outer, i.e., closest to root first):
1. Reversive
2. Causative
3. Applicative / Stative / Reciprocal
4. Passive (always outermost, immediately before final vowel)

Example of stacking: pik-ish-i-w-a = root pik + CAUS -ish- + APPL -i- + PASS -w- + FV -a

**Stripping guards:**
- After stripping an extension, the remaining stem must have at least 2 characters (to preserve a minimal CVC root)
- The passive -w- is only stripped if it immediately precedes the final vowel position
- The causative -ish-/-esh- is stripped before the shorter applicative -i-/-e- (longest-first matching)
- Record all stripped extensions in the `derived_chain` field in order of stripping

#### Object Prefix (stripped third)

The object prefix occupies the slot immediately before the verb root. It agrees with the noun class of the object:

| Object | Prefix | Tags |
|--------|--------|------|
| 1SG | -ni- | obj=1SG |
| 2SG | -ku- | obj=2SG |
| 3SG (Class 1) | -m-, -mw- | obj=3SG, obj_nc=1 |
| 1PL | -tu- | obj=1PL |
| 2PL | -wa- | obj=2PL |
| 3PL (Class 2) | -wa- | obj=3PL, obj_nc=2 |
| Class 3 | -u- | obj_nc=3 |
| Class 4 | -i- | obj_nc=4 |
| Class 5 | -li- | obj_nc=5 |
| Class 6 | -ya- | obj_nc=6 |
| Class 7 | -ki- | obj_nc=7 |
| Class 8 | -vi- | obj_nc=8 |
| Class 9 | -i- | obj_nc=9 |
| Class 10 | -zi- | obj_nc=10 |
| Class 11 | -u- | obj_nc=11 |
| Class 15 | -ku- | obj_nc=15 |
| Class 16 | -pa- | obj_nc=16 |
| Class 17 | -ku- | obj_nc=17 |
| Class 18 | -mu-, -m- | obj_nc=18 |
| Reflexive | -ji- | obj=REFL |

**Stripping guards:**
- Object prefix stripping is attempted only after extension and final-vowel stripping
- The prefix is optional -- most verbs do not carry an object prefix
- Ambiguity: -ki- can be object prefix (Class 7) or tense marker (sequential/conditional). Context from the tense slot resolution disambiguates
- The remaining stem after object prefix removal must have at least 2 characters

#### Relative Marker (stripped fourth)

The relative marker -o- (and its class-specific variants) is infixed between the tense marker and the object prefix. It marks relative clauses:

| Class | Relative Marker | Example |
|-------|----------------|---------|
| 1 | -ye- | a-li-ye-soma (he who read) |
| 2 | -o- | wa-li-o-soma (those who read) |
| 3 | -o- | u-li-o-anguka (which fell, Class 3) |
| 4 | -yo- | i-li-yo-anguka (which fell, Class 4) |
| 5 | -lo- | li-li-lo-anguka (which fell, Class 5) |
| 6 | -yo- | ya-li-yo-anguka (which fell, Class 6) |
| 7 | -cho- | ki-li-cho-anguka (which fell, Class 7) |
| 8 | -vyo- | vi-li-vyo-anguka (which fell, Class 8) |
| 9 | -yo- | i-li-yo-anguka (which fell, Class 9) |
| 10 | -zo- | zi-li-zo-anguka (which fell, Class 10) |
| 11 | -o- | u-li-o-anguka (which fell, Class 11) |
| 15 | -ko- | ku-li-ko-fanyika (where it happened, Class 15) |
| 16 | -po- | pa-li-po-fanyika (where it happened, Class 16) |
| 17 | -ko- | ku-li-ko-fanyika (where it happened, Class 17) |
| 18 | -mo- | mu-li-mo-fanyika (where it happened, Class 18) |

Tags: `rel=YES`, `rel_nc=CLASS_NUMBER`

**Stripping logic:** After tense marker identification, check if the segment between tense and the next morpheme matches a known relative marker. The -o- base form and its class-specific extensions (-ye-, -lo-, -cho-, -vyo-, -zo-, -po-, -ko-, -mo-) are checked longest-first.

#### Tense/Aspect Markers (stripped fifth)

The tense/aspect marker occupies the slot between the subject prefix and the relative marker (or object prefix, if no relative marker):

| Marker | Function | Tags |
|--------|----------|------|
| -na- | Present progressive / ongoing action | tense=PRES, aspect=PROG |
| -li- | Past (definite) | tense=PAST |
| -ta- | Future | tense=FUT |
| -me- | Present perfect / resultative | tense=PERF, aspect=RESULT |
| -ki- | Sequential (then), participial, conditional | aspect=SEQ, mood=COND |
| -ka- | Narrative past / consecutive | tense=PAST, aspect=NARR |
| -nge- | Conditional (hypothetical, present) | mood=COND |
| -ngali- | Conditional (hypothetical, past / counterfactual) | mood=COND, tense=PAST |
| -ku- | Negative past (in ha-...-ku-...) | tense=PAST, polarity=NEG |
| hu- | Habitual (no subject prefix) | tense=HAB |
| zero | Present simple / subjunctive (no overt marker) | tense=PRES |

**Stripping guards:**
- -nge- and -ngali- are checked before -na- to prevent partial matching
- -ku- as negative past tense marker is only stripped when the negation prefix ha- has already been identified
- The habitual hu- stands alone without a subject prefix and is detected as a special case: if the word begins with hu- and no subject prefix precedes it, tag as habitual
- Zero tense (no marker) is the default when no tense morpheme is found between the subject prefix and the next slot

#### Subject Agreement Prefix (stripped sixth)

The subject prefix agrees with the noun class of the subject. It is the second-outermost prefix (after negation):

| Subject | Prefix | Tags |
|---------|--------|------|
| 1SG | ni- | person=1, num=SG |
| 2SG | u- | person=2, num=SG |
| 3SG (Class 1) | a- (yu- before vowels in some dialects) | person=3, num=SG, nc=1 |
| 1PL | tu- | person=1, num=PL |
| 2PL | m- (mw- before vowel) | person=2, num=PL |
| 3PL (Class 2) | wa- | person=3, num=PL, nc=2 |
| Class 3 | u- | nc=3 |
| Class 4 | i- | nc=4 |
| Class 5 | li- | nc=5 |
| Class 6 | ya- | nc=6 |
| Class 7 | ki- | nc=7 |
| Class 8 | vi- | nc=8 |
| Class 9 | i- | nc=9 |
| Class 10 | zi- | nc=10 |
| Class 11 | u- | nc=11 |
| Class 14 | u- | nc=14 |
| Class 15 | ku- | nc=15 |
| Class 16 | pa- | nc=16 |
| Class 17 | ku- | nc=17 |
| Class 18 | mu-, m- | nc=18 |

**Ambiguity notes:**
- u- is shared by 2SG, Class 3, Class 11, and Class 14. Disambiguation relies on: (a) the tense marker following it, (b) sentence-level noun class tracking
- i- is shared by Class 4 and Class 9. Same disambiguation strategy
- ku- is shared by Class 15 and Class 17. Rarely ambiguous in practice since Class 17 locative verbs are uncommon
- The 2SG u- and Class 3/11/14 u- are formally identical at the word level; only sentence-level agreement resolution can disambiguate

#### Negation Prefix (stripped last -- outermost prefix)

Negation is the outermost prefix on the verb:

| Pattern | Form | Tags | Example |
|---------|------|------|---------|
| ha- + SUBJ + tense + ... | General negation | polarity=NEG | ha-tu-soma (we don't read) |
| si- (replaces ni- for 1SG) | 1SG negation | polarity=NEG, person=1, num=SG | si-somi (I don't read) |
| ha- + u- (> hu-) for 2SG | 2SG negation | polarity=NEG, person=2, num=SG | hu-somi (you don't read) |
| ha- + a- (> ha-) for 3SG | 3SG negation | polarity=NEG, person=3, num=SG | ha-somi (s/he doesn't read) |
| ha- + wa- for 3PL | 3PL negation | polarity=NEG | hawa-somi (they don't read) |
| ha- + CLASS prefix | Class-based negation | polarity=NEG, nc=CLASS | ha-ki-somi (it[cl.7] doesn't read) |

**Special negation patterns:**
- Negative past: ha- + SUBJ + -ku- + ROOT + -a (ha-tu-ku-soma = we did not read)
- Negative present: ha- + SUBJ + ROOT + -i (final vowel changes to -i: ha-tu-som-i = we do not read)
- Negative future: ha- + SUBJ + -ta- + ROOT + -a (ha-tu-ta-soma = we will not read)
- Negative subjunctive: SUBJ + -si- + ROOT + -e (tu-si-som-e = let us not read) -- here -si- replaces the tense slot
- Imperative negation: u-si- + ROOT + -e (usi-some = don't read!)

**Stripping guards:**
- ha- is only stripped if followed by a recognizable subject prefix or merged subject form
- si- for 1SG negation is a fused form (si- = ha- + ni-) and is treated as atomic, recording both polarity=NEG and person=1, num=SG
- The negative -si- infix (subjunctive negation) is detected when it occupies the tense slot position

### Noun Morphology

Noun inflectional stripping handles:

1. **Class prefix stripping:** As described in the Noun Class System section above. The prefix is stripped and the class number recorded.

2. **Number detection:** If the detected class is a singular class (1, 3, 5, 7, 9, 11, 14), tag `num=SG`. If a plural class (2, 4, 6, 8, 10), tag `num=PL`. Classes 15-18 do not have number.

3. **Locative suffix -ni:** The suffix -ni can be added to nouns to indicate location:
   - nyumba > nyumbani (at home/house)
   - shule > shuleni (at school)
   - mji > mjini (at/in the city)
   Strip -ni from the end of the word and tag `loc=YES`. Guard: the remaining stem after -ni removal must be at least 3 characters and must match a known noun stem or class-prefixed form.

4. **Diminutive/Augmentative class shift:** A noun can shift class to express diminutive (to Class 7/8: mtu > kijitu "small person") or augmentative (to Class 5/6: mtu > jitu "giant"). This is handled as derivation in Step B.

### Adjective Agreement

Adjective prefixes mirror the noun class agreement system. Swahili adjectives are a small closed class (~50 native adjective stems: -zuri "good/beautiful", -kubwa "big", -dogo "small", -refu "tall/long", -fupi "short", -pya "new", -zima "whole", -baya "bad", -ingine "other", -ote "all", -ake "his/her", etc.). Each takes the adjective agreement prefix matching the noun's class:

| Class | Adj Prefix | Example with -zuri |
|-------|-----------|-------------------|
| 1 | m-, mw- | mtu mzuri (good person) |
| 2 | wa-, w- | watu wazuri (good people) |
| 3 | m-, mw- | mti mzuri (good tree) |
| 4 | mi-, my- | miti mizuri (good trees) |
| 5 | ji-, j-, zero | tunda zuri (good fruit) |
| 6 | ma- | matunda mazuri (good fruits) |
| 7 | ki-, ch- | kitu kizuri (good thing) |
| 8 | vi-, vy- | vitu vizuri (good things) |
| 9 | n-, ny-, zero | nyumba nzuri (good house) |
| 10 | n-, ny-, zero | nyumba nzuri (good houses) |
| 11 | m-, mw- | ukuta mzuri (good wall) |

Stripping: remove the agreement prefix (matched against the noun class agreement table), record `nc=CLASS_NUMBER`, and extract the adjective stem.

### Monosyllabic Verb Handling

Swahili has approximately 15 monosyllabic verb roots that require special treatment. These verbs retain the infinitive ku- in certain tense forms where other verbs would drop it:

- kula (eat, root: -la)
- kunywa (drink, root: -nywa)
- kuja (come, root: -ja)
- kwenda (go, root: -enda)
- kufa (die, root: -fa)
- kuwa (be/become, root: -wa)
- kupa (give, root: -pa -- colloquial)

Example: "ninakula" (I am eating) = ni-na-ku-la, where ku- is retained before the monosyllabic root -la. Compare with a regular verb: "ninasoma" (I am reading) = ni-na-soma, where no ku- appears.

The engine maintains a `MONOSYLLABIC_VERBS` set in `sw_irregulars.json`. When a ku- appears in the object prefix slot but matches a known monosyllabic root, it is treated as part of the root rather than as an object prefix.

## Step B: Derivational Detection

Swahili derivation operates through two primary mechanisms: verb extensions (already handled in Step A as they are morphologically fused with inflection) and nominal derivation from verb roots.

### Nominal Derivation Patterns (~20 rules)

**Agent nouns (Class 1/2, m-/wa- prefix + verb root):**
- m- + pika > mpishi (cook/chef) -- with consonant modification
- m- + fundisha > mwalimu (teacher) -- with root suppletion (irregular)
- m- + soma > msomaji (reader) -- with agentive suffix -ji
- m- + cheza > mchezaji (player)
Tags: `derived=AGENT`, `derived_from=ROOT`

**Agentive suffix -ji (productive):**
- soma > msomaji (reader)
- cheza > mchezaji (player)
- imba > mwimbaji (singer)
Tags: `derived=AGENT`, `suffix=ji`

**Abstract nouns (Class 14, u- prefix):**
- -zuri (good) > uzuri (beauty/goodness)
- -toto (child) > utoto (childhood)
- -baya (bad) > ubaya (badness)
- -huru (free) > uhuru (freedom)
Tags: `derived=ABSTRACT`, `derived_from=ROOT`

**Instrument/tool nouns (Class 7/8, ki-/vi-):**
- fungua (open) > kifunguo/vifunguo (key/keys)
- piga (hit) > kipigo/vipigo (blow/blows)
Tags: `derived=INSTRUMENT`, `derived_from=ROOT`

**Place nouns (Class 5/6, ji-/ma- or other):**
- lala (sleep) > malazi (sleeping place)
- kaa (sit) > makao (residence)
Tags: `derived=PLACE`, `derived_from=ROOT`

**Result/state nouns (various classes):**
- funga (close) > mfungo (closure/knot, Class 3)
- badilisha (change) > mabadiliko (changes, Class 6)
Tags: `derived=RESULT`, `derived_from=ROOT`

**Verbal noun / gerund (Class 15, ku-):**
- soma > kusoma (reading, the act of reading)
This is handled as a Class 15 noun (infinitive class) in prefix stripping.

### Derivation Detection Algorithm

1. After noun class prefix stripping, check if the stem matches a known verb root from the verb root inventory
2. If matched, tag the noun as derived and record the source root and derivation type
3. Check for agentive suffix -ji, -i, or -shi and strip if present
4. Maximum 2 iterations of derivational stripping (e.g., u-fundish-aji could involve both causative extension recognition and agentive derivation)

## Step C: Root Extraction

Root extraction in Swahili is more straightforward than in Arabic because Swahili morphology is concatenative -- morphemes attach linearly rather than interleaving.

### Verb Root Extraction

After stripping all prefixes (negation, subject, tense, relative, object), extensions, and final vowel in Step A, the remaining segment is the verb root. The root is looked up against the verb root inventory in `sw_roots.json` (~1,500 common verb roots).

**Procedure:**
1. Take the stripped stem from Step A
2. If the stem contains a monosyllabic root marker (ku- before a CVC root), strip it and check against `MONOSYLLABIC_VERBS`
3. Look up the stem in `sw_roots.json`
4. If not found, attempt to undo extension stripping one level (in case of over-stripping) and retry
5. Maximum 2 iterations of derivational un-stripping

### Noun Root Extraction

After class prefix stripping, the remaining stem is the noun root. For derived nouns (detected in Step B), the root is traced back to the source verb root.

**Procedure:**
1. Take the stem from class prefix stripping
2. If locative -ni was stripped, restore for root matching, then re-strip
3. Look up the stem in the noun stem inventory
4. If not found, check if the stem matches a verb root (indicating nominal derivation)
5. Fallback: return the raw stem as root

### Adjective Root Extraction

Adjective stems are a small set (~50). After agreement prefix stripping, the stem is looked up in the adjective stem inventory. Unknown stems are returned as-is.

## Tag Inventory

### Part of Speech Values

| POS | Description | Source |
|-----|-------------|--------|
| `NOUN` | Nouns (all classes) | Noun class prefix detection |
| `VERB` | Verbs (all tenses, moods, extensions) | Verb template stripping |
| `ADJ` | Adjectives (with class agreement) | Adjective agreement prefix detection |
| `ADV` | Adverbs | Closed-class intercept, some productive forms |
| `PRON` | Pronouns (personal, demonstrative) | Closed-class / class-based paradigm |
| `DET` | Determiners (demonstratives, quantifiers) | Class-based paradigm |
| `ADP` | Adpositions (prepositions) | Closed-class intercept |
| `CONJ` | Conjunctions | Closed-class intercept |
| `PART` | Particles (copular ni/si, other) | Closed-class intercept |
| `NUM` | Numerals | Numeral paradigm |
| `UNKNOWN` | Unclassified | Fallback |

### Feature Tags

| Tag Key | Possible Values | Source |
|---------|----------------|--------|
| `nc` | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17, 18 | Noun class prefix detection, verb subject/object agreement |
| `num` | SG, PL | Noun class (odd = SG, even = PL), verb agreement |
| `person` | 1, 2, 3 | Verb subject agreement prefix |
| `tense` | PRES, PAST, FUT, PERF, HAB | Verb tense marker |
| `aspect` | PROG, RESULT, SEQ, NARR, COMPL | Verb tense/aspect marker |
| `mood` | IND, SUBJ, COND, IMP, NEG_PAST | Final vowel, tense markers |
| `polarity` | AFF, NEG | Negation prefix detection |
| `voice` | ACT, PASS, CAUS, RECIP | Verb extensions |
| `valence` | APPL, STAT, REV | Verb extensions (applicative, stative, reversive) |
| `obj` | 1SG, 2SG, 3SG, 1PL, 2PL, 3PL, REFL | Object prefix |
| `obj_nc` | 1-18 | Object prefix noun class (for class-based object prefixes) |
| `rel` | YES | Relative marker detected |
| `rel_nc` | 1-18 | Relative marker noun class |
| `loc` | YES | Locative suffix -ni detected |
| `derived` | AGENT, ABSTRACT, INSTRUMENT, PLACE, RESULT | Derivational detection (Step B) |
| `derived_from` | verb root string | Derivational source root |
| `suffix` | ji, i, shi | Agentive/derivational suffix |
| `subcat` | CONJ, PREP, INTERROG, ADV, INTERJ, COP | Closed-class subcategory |
| `gloss` | English gloss string | Closed-class intercept |
| `derived_chain` | list of derivation steps | Extension stacking history |

### Bundle Count

**Estimated: 120-140 feature bundles.** Justification:

- **Noun bundles:** 18 classes x 2 numbers (SG/PL, where applicable) = ~30 basic noun bundles, plus locative variants (+loc=YES) = ~45
- **Verb bundles:** person/class (18+) x tense (6 primary) x polarity (2) = ~216 theoretical, but many combinations are linguistically impossible or extremely rare. Observed in practice: ~60 common verb bundles
- **Adjective bundles:** 18 class agreement prefixes = ~18
- **Closed-class bundles:** ~10 (one per subcategory)
- **Extension combinations:** voice/valence variations add ~15 more
- **Total observed:** ~120-140, constrained by the fact that many class x tense x polarity combinations rarely occur in natural text

The noun class system is the primary multiplier. Unlike Arabic (where the form system x clitic combinations drive bundle count) or Turkish (where case x possessive x number drive it), Swahili's bundle count is driven primarily by the 18-class agreement system propagating across POS categories.

## Config Files

| File | Content | Estimated Count |
|------|---------|----------------|
| `sw_classes.json` | Noun class table: for each class, the noun prefix, subject agreement prefix, object agreement prefix, adjective agreement prefix, possessive connector, demonstrative forms, and typical semantic domain. Also includes the Class 1/3 and Class 11/14 disambiguation lookup tables and the Class 9/10 nasal assimilation table. | 18 classes + ~300 disambiguation entries |
| `sw_extensions.json` | Verb extension inventory: each extension's surface forms, semantic function, tags, and stacking rules (which extensions can combine and in what order). Includes vowel harmony rules (-ish-/-esh-, -ik-/-ek-, -i-/-e-). | 7 extensions + stacking matrix |
| `sw_irregulars.json` | Irregular and monosyllabic verbs: monosyllabic roots that retain ku- (-la, -nywa, -ja, -enda, -fa, -wa, -pa); irregular copular forms (ni/si, kuwa paradigm); suppletive forms (kwenda/kwisha). Also includes ~30 irregular noun plurals that do not follow class pairing rules. | ~50 entries |
| `sw_roots.json` | Verb root inventory for root lookup validation. Sourced from standard Swahili dictionaries (TUKI / Kamusi ya Kiswahili Sanifu). | ~1,500 verb roots |
| `sw_adjectives.json` | The closed set of native Swahili adjective stems with their agreement paradigms. | ~50 stems |

No separate derivations file is needed -- nominal derivation patterns are rule-based (Step B) and verb extensions are in `sw_extensions.json`.

## Validators

### Word-level: `check_morph_sequence_sw`

To be defined in `shared.py`. Validates per-token tag bundles according to Swahili morphosyntactic rules:

- **VERB bundles** must contain a subject agreement tag (either `person` or `nc`). Additional rules:
  - If `tense` is present, a subject prefix must also be present (except habitual hu-, which has no subject prefix)
  - If `polarity=NEG` and `tense=PAST`, the negative past marker -ku- should be present (tagged via tense=PAST, polarity=NEG)
  - If `mood=SUBJ`, the final vowel must be -e (not -a)
  - If `mood=IMP`, person must be 2 (imperatives are only 2nd person)
  - `voice=PASS` and `voice=CAUS` can co-occur (causative-passive is valid: pikishwa)
  - `voice=PASS` and `voice=RECIP` cannot co-occur (semantically incompatible)
  - Object prefix (`obj`) must not be present with intransitive verbs (guard: check against a known intransitive set, or allow it with a warning)

- **NOUN bundles** must contain `nc` (noun class). Must NOT have `tense`, `person`, or `mood` tags. If `num` is present, it must be consistent with the class (odd classes = SG, even classes = PL).

- **ADJ bundles** must contain `nc` (agreement class). Must NOT have `tense`, `person`, or `mood` tags.

### Sentence-level: `validate_sentence_structure_sw`

To be defined in `shared.py`. Validates Swahili SVO sentence structure and noun class agreement:

1. **Basic word order:** Swahili is SVO. The validator checks that if a VERB follows a NOUN, the verb's subject prefix agrees with the noun's class.

2. **Noun-adjective agreement:** If an ADJ follows a NOUN, the adjective's `nc` tag must match the noun's `nc` tag.

3. **Noun-verb agreement (subject):** The verb's subject agreement prefix class must match the subject noun's class. For personal pronouns (1st/2nd person), the person tag is validated instead of nc.

4. **Noun-verb agreement (object):** If the verb has an object prefix (`obj_nc`), it should match the class of a nearby noun in object position.

5. **Verb validity:** Same rules as word-level validator (no passive imperative in non-2nd person, etc.).

6. **Negation consistency:** If `polarity=NEG`, the final vowel and tense marker must be consistent with the negation pattern (e.g., negative present requires final vowel -i, negative subjunctive requires -si- infix and final vowel -e).

## Known Limitations

1. **Noun class assignment for loanwords is often unpredictable.** Most Arabic and English loanwords default to Class 9/10 (the "miscellaneous" class), but some are assigned to Class 5/6 (e.g., "gazeti" = newspaper, from "gazette") or Class 7/8 (e.g., "kitabu" from Arabic "kitab"). The engine relies on lookup tables rather than predictive rules for loanword class assignment.

2. **Class 9/10 nasal prefix undergoes complex assimilation.** The N- prefix triggers nasal assimilation (n+p > mp, n+b > mb, n+v > mv, n+t > nt, n+d > nd, n+k > nk, n+g > ng, ny+vowel) that is difficult to reverse-engineer reliably. Some Class 9/10 nouns have zero prefix (especially loanwords), making class detection impossible from form alone.

3. **Relative clause markers are complex and class-dependent.** The 18 different relative markers (one per class, some shared) create a large combinatorial space. The amba- relative construction (a periphrastic alternative: "kitabu ambacho nilikisoma" = the book which I read it) adds further complexity.

4. **Bantu tone is not represented.** While Standard Swahili is largely non-tonal (unlike most other Bantu languages), some minimal pairs exist based on pitch/stress patterns. The engine does not model tone or stress.

5. **Dialectal variation.** Standard Swahili (Kiswahili sanifu) is based on the Kiunguja dialect (Zanzibar), but mainland Tanzanian Swahili, Kenyan Swahili, and Congolese Swahili differ in vocabulary, phonology, and some morphological patterns. The engine targets Kiswahili sanifu only.

6. **Arabic loanword stratum.** 30-40% of Swahili vocabulary is of Arabic origin. These words have been nativized into the Bantu class system but may retain Arabic plural patterns (e.g., "vitabu" uses Bantu Class 8 vi- rather than Arabic "kutub"). The engine treats all nativized loanwords as regular Swahili nouns.

7. **Verb extension vowel harmony is context-dependent.** Extensions use either the -i-/-ish-/-ik- set or the -e-/-esh-/-ek- set depending on the vowel of the verb root (a form of vowel harmony). The engine currently strips both variants without validating harmony.

8. **Class 5 zero-prefix nouns are undetectable from form alone.** Nouns like "tunda" (fruit), "gari" (car), and "yai" (egg) belong to Class 5 but have no overt prefix. The engine relies entirely on lookup tables for these nouns.

9. **Amba- relative construction not modeled.** The periphrastic relative with "amba-" + relative suffix is a multi-word construction that the single-token analyzer cannot fully capture.

10. **Compound tenses not modeled.** Constructions like "alikuwa akisoma" (he was reading -- past progressive via auxiliary kuwa + participial ki-) involve multi-word tense marking that is beyond single-token analysis.

## Test Plan

| Category | Test Count | Description |
|----------|-----------|-------------|
| Noun class prefix stripping | 80 | All 18 classes, including ambiguous classes (1/3, 11/14), zero-prefix Class 5, nasal-assimilation Class 9/10. Multiple examples per class covering typical and edge-case stems. |
| Verb template (full slot analysis) | 120 | Subject + tense + object + root + extension + final vowel combinations. Covers all persons (1SG through 3PL), all tense markers (na-, li-, ta-, me-, ki-, ka-, nge-, ngali-, hu-), representative object prefixes, and representative roots. |
| Verb extension stripping | 50 | Each extension individually (causative, applicative, passive, reciprocal, stative, reversive), plus stacking combinations (causative+applicative, causative+passive, applicative+passive, causative+applicative+passive, reciprocal+stative). |
| Adjective agreement | 40 | All 18 class agreement prefixes on representative adjective stems (-zuri, -kubwa, -dogo, -refu, -fupi, -pya). Validates correct prefix-to-class mapping. |
| Negation patterns | 30 | All negation patterns: ha- general, si- 1SG, negative present (-i final vowel), negative past (ha-...-ku-), negative future (ha-...-ta-), negative subjunctive (-si-...-e), imperative negation (usi-...-e). |
| Relative clauses | 20 | Class-specific relative markers (-ye-, -o-, -lo-, -cho-, -vyo-, -zo-, -po-, -ko-, -mo-) in verb forms across representative tenses. |
| Monosyllabic verbs | 15 | Retention of ku- with monosyllabic roots across tenses and persons (-la, -nywa, -ja, -enda, -fa, -wa). |
| Closed-class intercept | 25 | All ~95 closed-class entries grouped by subcategory. Validates correct POS, subcat, and gloss assignment. |
| Derivational detection | 15 | Agent nouns (m- + root), abstract nouns (u- + root), instrument nouns (ki- + root), agentive -ji suffix. |
| Locative -ni | 10 | Locative suffix stripping with guard (minimum stem length, known noun validation). |
| Adversarial / edge cases | 50 | False-positive guards: closed-class words that resemble prefixed forms (katika, karibu, kama); monosyllabic root ku- vs. object prefix ku-; Class 9/10 nasal assimilation reversal errors; over-stripping of short words; ambiguous subject prefix u- (2SG vs. Class 3); overlapping tense marker ki- vs. object prefix ki-. |
| **Total** | **~455** | Covers: noun class system, verb template, extensions, agreement, negation, relative clauses, closed-class intercept, derivation, locative, monosyllabic verbs, adversarial edge cases |

The adversarial test suite is particularly important for Swahili because the prefix-heavy morphology creates many opportunities for false-positive stripping. The overlapping forms of subject prefixes (u- for 2SG / Class 3 / Class 11 / Class 14), tense markers (ki- for sequential vs. ki- object prefix for Class 7), and the zero-prefix problem in Classes 5 and 9/10 all require careful guard logic.
