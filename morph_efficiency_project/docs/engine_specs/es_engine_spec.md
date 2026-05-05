# Spanish Engine Design Specification

**Language:** Spanish (es)  
**Typology:** Regular fusional  
**Engine file:** `scripts/engines/es_engine.py` (to be built)  
**Status:** Design phase

---

## Morphological Overview

Spanish (espanol) is a Romance language whose morphology sits squarely in the fusional typological category. Unlike agglutinative languages such as Turkish, where each morpheme encodes a single grammatical function in a transparent, concatenative chain, Spanish fuses multiple grammatical features into single suffixal morphemes. A verb ending like *-amos* simultaneously encodes person (1st), number (plural), tense (present), and mood (indicative) -- four grammatical features packed into a single indivisible suffix. This fusional character means that suffix stripping in Spanish cannot proceed slot-by-slot; instead, the engine must match entire suffix paradigms against known conjugation tables.

The verb system is the morphological centerpiece of Spanish. All verbs belong to one of three conjugation classes determined by their infinitive ending: *-ar* (first conjugation, e.g., *hablar* "to speak"), *-er* (second conjugation, e.g., *comer* "to eat"), and *-ir* (third conjugation, e.g., *vivir* "to live"). The first conjugation is overwhelmingly dominant, accounting for roughly 90% of all Spanish verbs and serving as the productive class for neologisms (e.g., *googlear*, *chatear*, *tuitear*). Each conjugation class inflects across 6 person-number cells (yo, tu, el/ella/usted, nosotros/as, vosotros/as, ellos/ellas/ustedes) and 14+ tense-mood combinations, yielding a theoretical paradigm of approximately 50 distinct synthetic forms per regular verb. When compound tenses (formed with the auxiliary *haber* + past participle) and periphrastic constructions are included, the total number of verb forms per lemma exceeds 100.

The nominal and adjectival systems are considerably simpler but still richer than English. Nouns carry grammatical gender (masculine or feminine, with rare ambigeneric exceptions like *el/la mar*) and number (singular or plural). Gender is partially predictable from the ending (*-o* typically masculine, *-a* typically feminine), but numerous exceptions exist (*el dia*, *la mano*, *el mapa*, *la foto*). Adjectives agree with their head nouns in both gender and number, producing up to four forms for most adjectives (*bueno/buena/buenos/buenas*) or two forms for those ending in *-e* or a consonant (*grande/grandes*, *feliz/felices*). This agreement system is a key feature that distinguishes Spanish from English and contributes to its higher morphological density.

Spanish employs a system of clitic pronouns (pronombres atonos) that attach phonologically and orthographically to certain verb forms. Object clitics (*me, te, lo, la, le, nos, os, los, las, les, se*) appear as proclitics before conjugated verb forms (*lo veo* "I see it") but as enclitics fused to infinitives (*verlo* "to see it"), gerunds (*viendolo* "seeing it"), and affirmative imperatives (*miralo* "look at it"). Up to three clitics can stack in enclitic position (*diselo* "tell it to him/her" = *di+se+lo*), and the resulting word may require an accent mark to preserve the original stress pattern. This clitic attachment makes word-level morphological analysis essential for recovering the base verb form.

Derivational morphology in Spanish is highly productive. Nominalization suffixes like *-cion/-sion* (nominalizacion, expresion), *-miento* (conocimiento), and *-idad/-dad* (realidad, bondad) systematically convert verbs and adjectives into nouns. The adverbialization suffix *-mente* (rapidamente, facilmente) is fully productive and transparently segmentable. Agent nouns are formed with *-dor/-dora* (trabajador), *-ero/-era* (panadero), and *-ista* (pianista). Prefixes like *des-* (deshacer), *re-* (reconstruir), *in-/im-* (imposible, increible) modify meaning predictably. This derivational richness contributes additional morphological density beyond the inflectional system.

The label "regular fusional" captures Spanish's position on the morphological typology spectrum. The paradigms are large (over 50 synthetic forms per verb), but the vast majority of verbs (the *-ar* class and most *-er/-ir* verbs) follow their paradigms with perfect regularity. Stem-changing verbs (*e->ie*, *o->ue*, *e->i*) number around 200-300 and follow predictable sub-patterns; truly suppletive irregulars like *ser*, *ir*, and *haber* number only about 20-30. This high regularity means the engine can handle most of the language through rule-based suffix matching, with a manageable irregular lookup table. Spanish is expected to produce a moderate number of feature bundles -- significantly more than English (15-25) but less than Arabic (100+) or Turkish (80+), reflecting its intermediate morphological density.

## Closed-Class Intercept

The engine maintains a static dictionary of approximately **165** closed-class words that are intercepted before any inflectional or derivational analysis. Each entry maps a lowercased surface form to a `(POS, tags)` tuple. These words bypass Steps A, B, and C entirely.

### Determiners (DET) -- 11 entries

Definite articles: `el`, `la`, `los`, `las`, `lo` (neuter)  
Indefinite articles: `un`, `una`, `unos`, `unas`  
Contracted forms: `al` (a + el), `del` (de + el)

Tags: `gender=MASC/FEM`, `num=SG/PL` where applicable. `lo` receives `gender=NEUT`. `al` and `del` receive `contraction=YES`.

### Prepositions (ADP) -- 20 entries

`a`, `ante`, `bajo`, `cabe` (archaic), `con`, `contra`, `de`, `desde`, `durante`, `en`, `entre`, `hacia`, `hasta`, `mediante`, `para`, `por`, `segun`, `sin`, `sobre`, `tras`

All receive `pos=ADP` with no additional feature tags. Note: *cabe* is archaic but retained for completeness; *segun* is stored without its accent mark (accent-stripped input is assumed for lookup, with the accented form `según` as an alias).

### Pronouns (PRON) -- 60 entries

**Personal subject pronouns (12):**  
`yo`, `tu`, `el`, `ella`, `usted`, `nosotros`, `nosotras`, `vosotros`, `vosotras`, `ellos`, `ellas`, `ustedes`  
Tags: `person=1/2/3`, `num=SG/PL`, `gender=MASC/FEM` where applicable, `formality=FORMAL` for `usted`/`ustedes`.

**Unstressed object pronouns / clitics when freestanding (11):**  
`me`, `te`, `le`, `lo`, `la`, `nos`, `os`, `les`, `los`, `las`, `se`  
Tags: `subcat=CLITIC`, `person=1/2/3`, `num=SG/PL`, `case=ACC/DAT` where determinable. Note: these same forms also appear as bound enclitics on verb forms, handled separately in the clitic stripping module.

**Prepositional pronouns (6):**  
`mi` (after preposition, "a mi"), `ti`, `si`, `conmigo`, `contigo`, `consigo`  
Tags: `subcat=PREP_PRON`, `person=1/2/3`.

**Relative/interrogative pronouns (5):**  
`que`, `quien`, `cual`, `cuyo`, `cuya`  
Tags: `subcat=REL` or `subcat=INTERR`.

**Demonstrative pronouns (12):**  
`este`, `esta`, `estos`, `estas`, `ese`, `esa`, `esos`, `esas`, `aquel`, `aquella`, `aquellos`, `aquellas`  
Tags: `subcat=DEM`, `gender=MASC/FEM`, `num=SG/PL`, `distance=PROX/MED/DIST`.

**Indefinite pronouns (14):**  
`algo`, `alguien`, `nada`, `nadie`, `todo`, `toda`, `todos`, `todas`, `cada`, `otro`, `otra`, `otros`, `otras`, `mismo`  
Tags: `subcat=INDEF`, with `gender` and `num` where applicable.

### Conjunctions (CONJ) -- 18 entries

**Coordinating (7):**  
`y`, `e` (before *i-/hi-*), `o`, `u` (before *o-/ho-*), `ni`, `pero`, `sino`  
Tags: `subcat=COORD`.

**Subordinating (11):**  
`mas` (literary "but"), `aunque`, `porque`, `pues`, `que` (complementizer), `si` (conditional), `como`, `cuando`, `donde`, `mientras`, `segun`  
Tags: `subcat=SUBORD`.

Note: `que` and `segun` appear in multiple categories (pronoun and conjunction). The engine stores the first registration only; context-dependent disambiguation is deferred to downstream processing.

### Non-derivable Adverbs (ADV) -- 22 entries

**Degree:** `muy`, `mas`, `menos`, `tan`  
**Temporal:** `ya`, `hoy`, `ayer`, `manana`, `siempre`, `nunca`, `jamas`  
**Affirmation/Negation:** `no`, `si`, `tambien`, `tampoco`  
**Spatial:** `aqui`, `ahi`, `alli`  
**Epistemic:** `quizas`, `acaso`  
**Manner (non-derivable):** `bien`, `mal`, `asi`

Tags: `pos=ADV`, `subcat=DEGREE/TEMP/NEG/SPATIAL/EPIST/MANNER` as appropriate.

### Auxiliary Verbs (AUX) -- 2 entries

`haber` (perfective auxiliary), `estar` (progressive auxiliary when used with gerund)

These receive `pos=AUX`. Their conjugated forms are handled through `es_irregulars.json` rather than the closed-class dictionary, since they inflect fully. Only the infinitive forms are intercepted here to prevent derivational analysis from attempting to strip *-er* as a suffix.

### Particles and Interjections (PART) -- 12 entries

`he` (presentative, archaic: *he aqui*), `no` (negation), `si` (affirmation), `pues` (discourse), `oye`, `mira`, `vaya`, `ole`, `ay`, `eh`, `ah`, `oh`

Note: `no`, `si`, and `pues` are registered under ADV or CONJ in their primary function; PART variants are stored as aliases only if their primary entry does not already exist.

### Numerals (NUM) -- 20 entries

`uno`, `dos`, `tres`, `cuatro`, `cinco`, `seis`, `siete`, `ocho`, `nueve`, `diez`, `once`, `doce`, `trece`, `catorce`, `quince`, `cien`, `ciento`, `mil`, `millon`, `primer`

Tags: `pos=NUM`.

**Total unique entries in closed-class dictionary: ~165** (exact count depends on deduplication of multi-category entries like *que*, *si*, *mas*).

## Step A: Inflectional Stripping

Step A takes a single word, lowercases it, strips diacritics for lookup purposes (preserving them in the surface form), and attempts to identify its inflectional morphology. It returns a tuple of `(stem, tags_dict, pos)`. Rules are checked in strict priority order; the first match wins.

### 1. Closed-Class Lookup

If the lowercased/accent-stripped word is in `CLOSED_CLASS`, return immediately with the pre-assigned POS and tags. No further processing.

### 2. Irregular Form Lookup

If the word appears as a key in `es_irregulars.json` (estimated ~2,500 entries covering ~400 irregular verb lemmas with their full paradigms), the engine reads the entry's `base`, `pos`, and `tag` fields. The tag string is pipe-delimited key=value pairs.

Examples:
- `"fui"` -> base=`ir`, pos=`VERB`, tags=`{tense=PAST_SIMPLE, person=1, num=SG, mood=IND}`
- `"soy"` -> base=`ser`, pos=`VERB`, tags=`{tense=PRES, person=1, num=SG, mood=IND}`
- `"dicho"` -> base=`decir`, pos=`VERB`, tags=`{aspect=PERF, form=PTCP}`

### 3. Enclitic Pronoun Stripping

Before attempting regular conjugation matching, the engine checks for and strips enclitic pronouns (see Clitic Pronouns section below for full design). If enclitics are detected, they are stripped and the remaining stem is re-submitted to steps 4-6 for conjugation matching.

### 4. Verb Conjugation

This is the core of the Spanish engine. The engine maintains suffix tables for all three conjugation classes (*-ar*, *-er*, *-ir*) across all tense/mood combinations. Matching proceeds **longest suffix first** within each tense/mood to prevent false prefix matches.

#### Conjugation Class Detection

The engine attempts to match the word ending against known suffix paradigms. For each candidate match, it verifies that the resulting stem + class infinitive ending (*-ar*, *-er*, or *-ir*) forms a plausible verb. A frequency list of the ~10,000 most common Spanish verbs is consulted for validation; if the reconstructed infinitive is not in the list, the match is rejected and the next candidate is tried.

#### Suffix Paradigms

The suffix tables below show the endings that replace the infinitive ending. For example, *hablar* (to speak): the infinitive ending *-ar* is replaced by the conjugation suffix.

**Paradigm 1: Presente de indicativo**

| Person | -ar | -er | -ir |
|--------|-----|-----|-----|
| 1SG (yo) | -o | -o | -o |
| 2SG (tu) | -as | -es | -es |
| 3SG (el/ella/usted) | -a | -e | -e |
| 1PL (nosotros) | -amos | -emos | -imos |
| 2PL (vosotros) | -ais | -eis | -is |
| 3PL (ellos/ustedes) | -an | -en | -en |

Tags: `{tense=PRES, mood=IND, person=P, num=SG/PL}`

**Paradigm 2: Preterito indefinido (simple past)**

| Person | -ar | -er | -ir |
|--------|-----|-----|-----|
| 1SG | -e | -i | -i |
| 2SG | -aste | -iste | -iste |
| 3SG | -o | -io | -io |
| 1PL | -amos | -imos | -imos |
| 2PL | -asteis | -isteis | -isteis |
| 3PL | -aron | -ieron | -ieron |

Tags: `{tense=PAST_SIMPLE, mood=IND, person=P, num=SG/PL}`

Note: The 1SG *-e* for *-ar* verbs and the 1SG/3SG *-i*/*-io* for *-er/-ir* verbs carry accent marks in standard orthography (*-e*, *-i*, *-io*). The engine handles both accented and unaccented input.

**Paradigm 3: Preterito imperfecto (imperfect past)**

| Person | -ar | -er/-ir |
|--------|-----|---------|
| 1SG | -aba | -ia |
| 2SG | -abas | -ias |
| 3SG | -aba | -ia |
| 1PL | -abamos | -iamos |
| 2PL | -abais | -iais |
| 3PL | -aban | -ian |

Tags: `{tense=PAST_IMPERF, mood=IND, person=P, num=SG/PL}`

Note: *-er* and *-ir* verbs share identical imperfect endings. The engine cannot distinguish conjugation class from the imperfect alone; both classes are accepted.

**Paradigm 4: Futuro simple**

The future tense is formed by adding suffixes directly to the full infinitive (not the stem). This is unique among Spanish tenses.

| Person | All classes |
|--------|-------------|
| 1SG | -e (infinitive + e) |
| 2SG | -as (infinitive + as) |
| 3SG | -a (infinitive + a) |
| 1PL | -emos (infinitive + emos) |
| 2PL | -eis (infinitive + eis) |
| 3PL | -an (infinitive + an) |

Tags: `{tense=FUT, mood=IND, person=P, num=SG/PL}`

Design note: Because future suffixes attach to the full infinitive, the engine first checks whether the word contains a recognizable infinitive substring (*-ar-*, *-er-*, *-ir-*) followed by a future ending. Irregular future stems (e.g., *tendr-* for *tener*, *pondr-* for *poner*, *sabr-* for *saber*, *querr-* for *querer*, *habr-* for *haber*, *podr-* for *poder*, *saldr-* for *salir*, *vendr-* for *venir*, *dir-* for *decir*, *har-* for *hacer*, *valdr-* for *valer*, *cabr-* for *caber*) are stored in `es_irregulars.json`.

**Paradigm 5: Condicional simple**

Like the future, the conditional attaches to the full infinitive.

| Person | All classes |
|--------|-------------|
| 1SG | -ia |
| 2SG | -ias |
| 3SG | -ia |
| 1PL | -iamos |
| 2PL | -iais |
| 3PL | -ian |

Tags: `{tense=COND, mood=IND, person=P, num=SG/PL}`

Design note: The conditional shares the same irregular stems as the future tense. Forms like *tendria*, *pondria*, *sabria* are in `es_irregulars.json`.

**Paradigm 6: Presente de subjuntivo**

| Person | -ar | -er/-ir |
|--------|-----|---------|
| 1SG | -e | -a |
| 2SG | -es | -as |
| 3SG | -e | -a |
| 1PL | -emos | -amos |
| 2PL | -eis | -ais |
| 3PL | -en | -an |

Tags: `{tense=PRES, mood=SUBJ, person=P, num=SG/PL}`

Design note: The present subjunctive "swaps" the theme vowel -- *-ar* verbs take *-e-* based endings, *-er/-ir* verbs take *-a-* based endings. This creates potential ambiguity with the present indicative of the opposite class (e.g., *-ar* subjunctive *-e* looks like *-er* indicative *-e*). The engine resolves this by consulting the verb frequency list to determine the conjugation class.

**Paradigm 7: Preterito imperfecto de subjuntivo**

Two forms exist: *-ra* and *-se*. Both are equally valid; *-ra* is more common in modern usage.

| Person | -ar (-ra) | -ar (-se) | -er/-ir (-ra) | -er/-ir (-se) |
|--------|-----------|-----------|---------------|---------------|
| 1SG | -ara | -ase | -iera | -iese |
| 2SG | -aras | -ases | -ieras | -ieses |
| 3SG | -ara | -ase | -iera | -iese |
| 1PL | -aramos | -asemos | -ieramos | -iesemos |
| 2PL | -arais | -aseis | -ierais | -ieseis |
| 3PL | -aran | -asen | -ieran | -iesen |

Tags: `{tense=PAST_IMPERF, mood=SUBJ, person=P, num=SG/PL, subj_form=RA/SE}`

**Paradigm 8: Futuro de subjuntivo (archaic)**

Rarely used in modern Spanish except in legal/formulaic language (*"donde fuere"*, *"si tuviere"*).

| Person | -ar | -er/-ir |
|--------|-----|---------|
| 1SG | -are | -iere |
| 2SG | -ares | -ieres |
| 3SG | -are | -iere |
| 1PL | -aremos | -ieremos |
| 2PL | -areis | -iereis |
| 3PL | -aren | -ieren |

Tags: `{tense=FUT, mood=SUBJ, person=P, num=SG/PL}`

**Paradigm 9: Imperativo (affirmative)**

The imperative has only 5 forms (no 1SG). Negative imperatives use the present subjunctive.

| Person | -ar | -er | -ir |
|--------|-----|-----|-----|
| 2SG (tu) | -a | -e | -e |
| 3SG (usted) | -e | -a | -a |
| 1PL (nosotros) | -emos | -amos | -amos |
| 2PL (vosotros) | -ad | -ed | -id |
| 3PL (ustedes) | -en | -an | -an |

Tags: `{mood=IMP, person=P, num=SG/PL, formality=FORMAL}` (for usted/ustedes forms)

Design note: The 2SG imperative often coincides with the 3SG present indicative. The engine tags these as imperative only when enclitics are attached (e.g., *habla* = ambiguous, *hablame* = imperative + clitic). Without enclitics, the present indicative reading is preferred.

**Paradigm 10: Gerundio**

| Class | Suffix |
|-------|--------|
| -ar | -ando |
| -er | -iendo |
| -ir | -iendo |

Tags: `{aspect=PROG, form=GER}`

Irregular gerunds: *diciendo* (decir), *viniendo* (venir), *pudiendo* (poder), *durmiendo* (dormir), *sintiendo* (sentir), *pidiendo* (pedir), *muriendo* (morir), *yendo* (ir). These are stored in `es_irregulars.json`.

**Paradigm 11: Participio pasado**

| Class | Suffix |
|-------|--------|
| -ar | -ado |
| -er | -ido |
| -ir | -ido |

Tags: `{aspect=PERF, form=PTCP}`

When used adjectivally, participles also carry gender/number: *-ado/-ada/-ados/-adas*, *-ido/-ida/-idos/-idas*. Tags: `{aspect=PERF, form=PTCP, gender=MASC/FEM, num=SG/PL}`.

Irregular participles: *dicho* (decir), *hecho* (hacer), *escrito* (escribir), *visto* (ver), *puesto* (poner), *vuelto* (volver), *abierto* (abrir), *cubierto* (cubrir), *muerto* (morir), *roto* (romper), *resuelto* (resolver), *impreso* (imprimir), *satisfecho* (satisfacer), *frito* (freir). These are stored in `es_irregulars.json`.

**Paradigm 12: Infinitivo**

| Class | Suffix |
|-------|--------|
| 1st | -ar |
| 2nd | -er |
| 3rd | -ir |

Tags: `{form=INF}`

The infinitive is the citation/lemma form. If a word is recognized as an infinitive, the stem is the word itself (no stripping), and the root is set to the infinitive.

**Paradigm 13: Preterito perfecto compuesto (compound)**

Formed with *haber* (present indicative) + past participle.

This is a **multi-word** tense. The engine does not attempt to analyze compound tenses as single tokens. Each word (*he*, *has*, *ha*, *hemos*, *habeis*, *han* + participle) is analyzed independently. The auxiliary forms of *haber* are in `es_irregulars.json`.

**Paradigm 14: Pluscuamperfecto (compound)**

Formed with *haber* (imperfect indicative) + past participle.

Same multi-word design as Paradigm 13. The imperfect forms of *haber* (*habia, habias, habia, habiamos, habiais, habian*) are in `es_irregulars.json`.

Other compound tenses (future perfect, conditional perfect, subjunctive compound tenses) follow the same pattern: conjugated *haber* + past participle. All are handled by independent analysis of each word.

#### Stripping Order

The engine checks suffix paradigms in the following order, designed to match longest/most-specific suffixes first and avoid false matches:

1. **Imperfect subjunctive (-ra/-se forms):** Suffixes like *-ieramos*, *-iesemos* are the longest (7+ characters) and most distinctive.
2. **Future subjunctive:** *-ieremos*, *-aremos* -- long and rare, low false-positive risk.
3. **Preterite (simple past):** *-asteis*, *-isteis*, *-ieron*, *-aron* -- distinctive long endings.
4. **Imperfect indicative:** *-abamos*, *-abais*, *-iamos*, *-iais* -- distinctive *-aba-*/*-ia-* patterns.
5. **Future indicative:** Checked by looking for infinitive-internal pattern + future ending.
6. **Conditional:** Same strategy as future.
7. **Present subjunctive:** After longer tenses are eliminated.
8. **Present indicative:** Most ambiguous (short endings like *-a*, *-e*, *-o*), checked last among finite forms.
9. **Imperative:** Only matched when enclitics are present, otherwise deferred to present indicative.
10. **Gerund:** *-ando*, *-iendo* -- distinctive and unambiguous.
11. **Past participle:** *-ado*, *-ido* (and gender/number variants).
12. **Infinitive:** *-ar*, *-er*, *-ir* -- checked last as these are very short suffixes with high false-positive risk.

#### Stem-Changing Verb Handling

Approximately 200-300 Spanish verbs exhibit predictable stem changes in stressed syllables. These fall into defined sub-patterns:

- **e -> ie** (cerrar -> cierro, pensar -> pienso, entender -> entiendo): Affects 1SG, 2SG, 3SG, 3PL of present indicative and subjunctive.
- **o -> ue** (contar -> cuento, dormir -> duermo, poder -> puedo): Same distribution as e->ie.
- **e -> i** (pedir -> pido, servir -> sirvo, seguir -> sigo): Affects present indicative (same cells), plus all subjunctive forms and gerund.
- **u -> ue** (jugar -> juego): Only *jugar* in modern Spanish.
- **i -> ie** (adquirir -> adquiero): Very rare.

Design: Stem-changing verbs are handled through a hybrid approach. The ~50 most frequent stem-changing verbs have all their forms enumerated in `es_irregulars.json`. The remaining stem-changing verbs are handled by a reverse-stem-change module: when regular suffix stripping produces a stem containing *ie*, *ue*, or *i* (in specific positions), the engine attempts to reverse the change (*ie->e*, *ue->o*, *i->e*) and checks the resulting infinitive against the verb frequency list.

#### Truly Irregular Verbs

Approximately 20-30 Spanish verbs have suppletive or highly unpredictable forms. All forms of these verbs are enumerated in `es_irregulars.json`:

- **ser** (to be, essential): soy, eres, es, somos, sois, son; fui, fuiste, fue...; era, eras...; sea, seas...; etc.
- **ir** (to go): voy, vas, va, vamos, vais, van; fui, fuiste, fue... (identical preterite to *ser*); iba, ibas...; vaya, vayas...; yendo; ido.
- **haber** (to have, auxiliary): he, has, ha, hemos, habeis, han; hube...; habia...; haya...; habra...; habria...
- **estar** (to be, state): estoy, estas, esta...; estuve...; estaba...; este...; etc.
- **tener** (to have, possession): tengo, tienes...; tuve...; tenia...; tenga...; tendre...; tendria...
- **hacer** (to do/make): hago, haces...; hice, hiciste, hizo...; hare...; haria...; hecho (participle).
- **poder** (to be able): puedo, puedes...; pude...; podre...; podria...; pudiendo.
- **poner** (to put): pongo, pones...; puse...; pondre...; pondria...; puesto.
- **saber** (to know): se, sabes...; supe...; sabre...; sabria...; sepa...
- **querer** (to want): quiero, quieres...; quise...; querre...; querria...
- **venir** (to come): vengo, vienes...; vine...; vendre...; vendria...; viniendo.
- **decir** (to say): digo, dices...; dije...; dire...; diria...; diciendo; dicho.
- **dar** (to give): doy, das, da...; di, diste, dio...; de, des...
- **ver** (to see): veo, ves, ve...; vi, viste, vio...; veia...; visto.
- **oir** (to hear): oigo, oyes, oye...; oi...; oyendo; oido.
- **salir** (to leave): salgo, sales...; saldre...; saldria...
- **valer** (to be worth): valgo, vales...; valdre...; valdria...
- **caber** (to fit): quepo, cabes...; cupe...; cabre...; cabria...
- **traer** (to bring): traigo, traes...; traje...
- **caer** (to fall): caigo, caes...; cai...

Estimated total entries in `es_irregulars.json`: ~2,500 surface forms mapping to ~400 lemmas (including both truly irregular verbs and the most frequent stem-changing verbs with all their conjugated forms).

### 5. Noun Gender and Number

If the word was not matched as a verb, closed-class item, or irregular form, the engine attempts noun analysis.

#### Plural Stripping

Checked in order (longest suffix first):

1. **-ces -> -z** (e.g., *felices* -> *feliz*, *luces* -> *luz*, *voces* -> *voz*): Words ending in *-ces* have their ending replaced with *-z*. Tags: `{num=PL}`.
2. **-es** (e.g., *flores* -> *flor*, *ciudades* -> *ciudad*, *panes* -> *pan*): Stripped from words ending in a consonant + *es*. Length guard: stem must be >= 3 characters. Tags: `{num=PL}`.
3. **-s** (e.g., *gatos* -> *gato*, *casas* -> *casa*, *libros* -> *libro*): Stripped from words ending in a vowel + *s*. Length guard: stem must be >= 3 characters. Tags: `{num=PL}`.

Invariant nouns (words that are identical in singular and plural) are stored in a small exception list: *crisis*, *analisis*, *sintesis*, *tesis*, *dosis*, *genesis*, *lunes*, *martes*, *miercoles*, *jueves*, *viernes*, *virus*, *atlas*, *cosmos*, *paraguas*, *cumpleanos*, *rascacielos*, *parabrisas* (~20 entries). These are tagged `{num=SG, invariant=YES}` and bypass plural stripping.

#### Gender Assignment

After number stripping, the engine assigns grammatical gender based on the singular form:

1. **Explicit -o/-a pattern:** Words ending in *-o* receive `gender=MASC`; words ending in *-a* receive `gender=FEM`. This covers the majority of nouns.
2. **Exception list:** A set of ~50 gender exceptions overrides the *-o/-a* heuristic: *dia* (MASC), *mano* (FEM), *mapa* (MASC), *foto* (FEM, from *fotografia*), *moto* (FEM, from *motocicleta*), *radio* (FEM when "radio broadcast"), *planeta* (MASC), *tema* (MASC), *problema* (MASC), *sistema* (MASC), *programa* (MASC), *idioma* (MASC), *clima* (MASC), *poema* (MASC), *drama* (MASC), *fantasma* (MASC), *telegrama* (MASC), etc. (Greek-origin *-ma* nouns are systematically masculine.)
3. **Other endings:** Words ending in *-e*, *-cion/-sion*, *-dad/-tad*, *-tud*, *-umbre*, *-ez* receive `gender=FEM`. Words ending in *-or*, *-aje*, *-men* receive `gender=MASC`. Words ending in other consonants receive `gender=UNKNOWN_GENDER` (ambiguous without context).

Tags: `{pos=NOUN, num=SG/PL, gender=MASC/FEM}`

### 6. Adjective Agreement

Adjective analysis mirrors noun gender/number stripping but is triggered when the word matches known adjective patterns or appears in an adjective frequency list.

#### Four-form adjectives (-o/-a/-os/-as)

The engine strips gender/number suffixes:
- *-os* -> stem, tags: `{gender=MASC, num=PL}`
- *-as* -> stem, tags: `{gender=FEM, num=PL}`
- *-o* -> stem, tags: `{gender=MASC, num=SG}`
- *-a* -> stem, tags: `{gender=FEM, num=SG}`

POS = `ADJ` (assigned when the stem matches an adjective in the frequency list).

#### Two-form adjectives (-e/-es, consonant/-es)

- *-es* -> stem (strip *-es* or *-s*), tags: `{num=PL}`
- No ending -> tags: `{num=SG}`

Gender is not marked (these adjectives are gender-invariant).

#### Irregular comparatives

The following synthetic comparatives are stored in `es_irregulars.json`:
- *mejor* (base: *bueno*, tags: `{degree=COMP}`)
- *peor* (base: *malo*, tags: `{degree=COMP}`)
- *mayor* (base: *grande*, tags: `{degree=COMP}`)
- *menor* (base: *pequeno*, tags: `{degree=COMP}`)

Their superlative counterparts (*el mejor*, *el peor*) are analytic and handled at the sentence level.

### 7. Default

If no rule matches, the word is returned unchanged with empty tags and POS = `UNKNOWN`.

## Clitic Pronouns

Spanish clitic pronouns attach to verb forms in specific syntactic contexts. The engine handles enclitics (post-verbal attachment) at the word level and leaves proclitics (pre-verbal, written as separate words) to sentence-level processing.

### Enclitic Inventory

The following clitics can attach to infinitives, gerunds, and affirmative imperatives:

| Clitic | Person | Number | Case | Example |
|--------|--------|--------|------|---------|
| me | 1 | SG | ACC/DAT | *verme* (to see me) |
| te | 2 | SG | ACC/DAT | *decirte* (to tell you) |
| lo | 3 | SG | ACC | *hacerlo* (to do it, masc.) |
| la | 3 | SG | ACC | *verla* (to see her/it) |
| le | 3 | SG | DAT | *darle* (to give him/her) |
| se | 3 | SG/PL | REFL/DAT | *lavarse* (to wash oneself) |
| nos | 1 | PL | ACC/DAT | *decirnos* (to tell us) |
| os | 2 | PL | ACC/DAT | *miraros* (to look at you, vosotros) |
| los | 3 | PL | ACC | *verlos* (to see them, masc.) |
| las | 3 | PL | ACC | *verlas* (to see them, fem.) |
| les | 3 | PL | DAT | *darles* (to give them) |

### Clitic Stacking

Up to three clitics can attach in sequence. The order is constrained:

1. **se** always comes first (if present): *se* + indirect object + direct object
2. **Indirect object** (DAT) before **direct object** (ACC): *me lo*, *te la*, *nos los*
3. **se** replaces *le/les* before *lo/la/los/las*: *\*le lo* -> *se lo*

Examples of stacked enclitics:
- *diselo* = *di* + *se* + *lo* (say it to him/her) -- 3 clitics
- *damelo* = *da* + *me* + *lo* (give it to me) -- 2 clitics
- *diciendoselo* = *diciendo* + *se* + *lo* (saying it to him/her) -- 2 clitics

### Stripping Algorithm

The engine strips enclitics from the right edge of the word using a greedy approach:

1. Attempt to match the longest known clitic sequence at the end of the word. The engine checks for 3-clitic, then 2-clitic, then 1-clitic sequences.
2. For each candidate sequence, verify that the remaining stem is a valid verb form (infinitive, gerund, or imperative) by checking against the conjugation paradigms and irregular tables.
3. If the stem is valid, strip the clitics and record them in the `clitics` field of the `TokenInfo` as `{enclitic: [list_of_clitics]}`.
4. Re-submit the stripped stem to verb conjugation matching (steps 2 and 4 above).

Accent restoration: When clitics are stripped, the engine must handle accent marks. Spanish orthographic rules require accent marks to maintain original stress when clitics shift the syllable count (e.g., *da* -> *dame* -> *damelo*; the original stress on *da* is preserved with an accent on the *a* in *damelo*). The engine strips the accent mark from the stem after clitic removal, restoring the unmarked form for dictionary lookup.

Tags added: `{clitic_obj=SE+LO}` (pipe-separated list of attached clitics, in attachment order).

## Step B: Derivational Detection

Step B attempts to identify one layer of derivational morphology on the stem produced by Step A. It only runs when Step A assigned POS = `UNKNOWN`. It returns the stripped stem and a derivation chain entry.

### Suffix Rules (~35 rules)

Suffixes are sorted longest-first and checked greedily. Minimum stem remainder: 3 characters.

| Suffix | Direction | Derives | Example |
|--------|-----------|---------|---------|
| -cion / -sion | V -> N | ACTION_NOUN | *comunicacion* -> *comunicar* |
| -miento | V -> N | PROCESS_NOUN | *conocimiento* -> *conocer* |
| -mente | ADJ -> ADV | ADVERBIALIZATION | *rapidamente* -> *rapido* |
| -idad / -dad | ADJ -> N | QUALITY_NOUN | *realidad* -> *real*, *bondad* -> *bueno* |
| -oso / -osa | N -> ADJ | HAVING_QUALITY | *hermoso* -> *hermosura* |
| -ble | V -> ADJ | ABILITY | *comestible* -> *comer* |
| -ero / -era | N -> N | AGENT_OCCUPATION | *panadero* -> *pan* |
| -ista | N -> N/ADJ | AGENT_IDEOLOGY | *pianista* -> *piano* |
| -ismo | N/ADJ -> N | IDEOLOGY_SYSTEM | *socialismo* -> *social* |
| -anza | V -> N | STATE_RESULT | *esperanza* -> *esperar* |
| -encia / -ancia | V/ADJ -> N | STATE_QUALITY | *paciencia* -> *paciente* |
| -ura | ADJ -> N | QUALITY_ABSTRACT | *hermosura* -> *hermoso* |
| -dor / -dora | V -> N/ADJ | AGENT_INSTRUMENT | *trabajador* -> *trabajar* |
| -aje | V/N -> N | COLLECTIVE_ACTION | *aterrizaje* -> *aterrizar* |
| -eza | ADJ -> N | QUALITY_ABSTRACT | *belleza* -> *bello* |
| -ario / -aria | N -> ADJ/N | RELATIONAL | *universitario* -> *universidad* |
| -ivo / -iva | V -> ADJ | TENDENCY | *productivo* -> *producir* |
| -ante / -ente / -iente | V -> ADJ/N | AGENT_QUALITY | *estudiante* -> *estudiar* |
| -cion | V -> N | (variant of -cion) | |
| -ado / -ada | V -> N/ADJ | RESULT_STATE | *helado* -> *helar* (when not participle) |
| -al | N -> ADJ | PERTAINING_TO | *nacional* -> *nacion* |
| -ano / -ana | N -> ADJ | ORIGIN_RELATION | *mexicano* -> *Mexico* |
| -eno / -ena | N -> ADJ | ORIGIN | *chileno* -> *Chile* |
| -oso / -osa | N -> ADJ | FULL_OF | *peligroso* -> *peligro* |
| -able / -ible | V -> ADJ | POSSIBILITY | *lavable* -> *lavar* |
| -torio / -toria | V -> ADJ/N | PLACE_PURPOSE | *laboratorio* -> *laborar* |
| -cion / -sion | (grouped variant) | | |
| -tud | ADJ -> N | QUALITY | *juventud* -> *joven* |
| -ez | ADJ -> N | QUALITY | *vejez* -> *viejo* |
| -ia / -eria | N -> N | PLACE_COLLECTIVE | *panaderia* -> *panadero* |
| -amiento / -imiento | V -> N | PROCESS | *estacionamiento* -> *estacionar* |

### Prefix Rules (~20 rules)

| Prefix | Direction | Derives | Example |
|--------|-----------|---------|---------|
| des- | V/ADJ -> V/ADJ | REVERSAL_NEGATION | *deshacer* -> *hacer* |
| in- / im- / i- | ADJ -> ADJ | NEGATION | *imposible* -> *posible* |
| re- | V -> V | REPETITION | *reconstruir* -> *construir* |
| pre- | V/N -> V/N | TEMPORAL_BEFORE | *predecir* -> *decir* |
| sobre- | V/N -> V/N | EXCESS_ABOVE | *sobrepasar* -> *pasar* |
| sub- | N/ADJ -> N/ADJ | UNDER_BELOW | *subterraneo* -> *terraneo* |
| anti- | N/ADJ -> N/ADJ | OPPOSITION | *antirrobo* -> *robo* |
| auto- | N/V -> N/V | SELF | *automovil* -> *movil* |
| contra- | N/V -> N/V | COUNTER | *contradecir* -> *decir* |
| inter- | ADJ/N -> ADJ/N | BETWEEN | *internacional* -> *nacional* |
| multi- | ADJ/N -> ADJ/N | MANY | *multicultural* -> *cultural* |
| super- | ADJ/N -> ADJ/N | EXCESS | *supermercado* -> *mercado* |
| co- | N/V -> N/V | TOGETHER | *coexistir* -> *existir* |
| trans- / tras- | V -> V | ACROSS | *trasladar* -> *ladar* |
| extra- | ADJ -> ADJ | BEYOND | *extraordinario* -> *ordinario* |
| semi- | ADJ/N -> ADJ/N | HALF | *semicirculo* -> *circulo* |
| pos- / post- | N/ADJ -> N/ADJ | AFTER | *posguerra* -> *guerra* |
| micro- | N -> N | SMALL | *microorganismo* -> *organismo* |
| macro- | N/ADJ -> N/ADJ | LARGE | *macroeconomia* -> *economia* |
| mono- | ADJ/N -> ADJ/N | SINGLE | *monolingue* -> *lingue* |

**Estimated total derivational rules: ~55** (35 suffix + 20 prefix).

## Step C: Root Extraction

Step C performs iterative deepening by re-applying Step B up to **4** additional times. This handles multi-layered derivations common in Spanish.

- **Maximum iterations:** 4
- **Stopping condition:** Step B returns the same stem it received (no further stripping possible).
- **Output:** The final irreducible root.

Like Step B, Step C only runs when Step A assigned POS = `UNKNOWN`.

Example of multi-layer stripping:
- *internacionalizacion* -> strip *-cion* -> *internacionaliza* -> strip *-iza* -> *internacional* -> strip *inter-* -> *nacional* -> strip *-al* -> *nacion* (4 iterations, root = *nacion*)
- *desafortunadamente* -> strip *-mente* -> *desafortunada* -> strip *-ada* -> *desafortun* -> strip *des-* -> *afortun* -> strip *a-* -> *fortun* (4 iterations, root = *fortun*)

## Tag Inventory

### Part of Speech Values

| POS Value | Description |
|-----------|-------------|
| `NOUN` | Common noun (includes gender/number inflected forms) |
| `VERB` | Verb (includes all conjugated forms, infinitives, gerunds, participles) |
| `ADJ` | Adjective (includes gender/number inflected forms, comparatives) |
| `ADV` | Adverb (non-derivable adverbs and *-mente* derivatives) |
| `PRON` | Pronoun (personal, demonstrative, relative, indefinite, prepositional) |
| `DET` | Determiner (definite/indefinite articles, contracted forms) |
| `ADP` | Adposition/preposition |
| `CONJ` | Conjunction (coordinating and subordinating) |
| `AUX` | Auxiliary verb (*haber*, *estar* in auxiliary function) |
| `NUM` | Numeral |
| `PART` | Particle/interjection |
| `UNKNOWN` | No inflectional pattern matched; word passed to Steps B/C |

### Feature Tags

| Tag Key | Possible Values | Producing Step | Description |
|---------|----------------|----------------|-------------|
| `num` | `SG`, `PL` | Step A (noun/adj/verb) | Grammatical number |
| `gender` | `MASC`, `FEM`, `NEUT` | Step A (noun/adj/det) | Grammatical gender (`NEUT` only for *lo*) |
| `person` | `1`, `2`, `3` | Step A (verb conjugation) | Person agreement |
| `tense` | `PRES`, `PAST_SIMPLE`, `PAST_IMPERF`, `FUT`, `COND` | Step A (verb conjugation) | Tense of verb |
| `mood` | `IND`, `SUBJ`, `IMP` | Step A (verb conjugation) | Mood of verb |
| `aspect` | `PERF`, `IMPERF`, `PROG` | Step A (participle/gerund) | Aspect marking |
| `form` | `INF`, `GER`, `PTCP` | Step A (non-finite forms) | Non-finite verb form type |
| `voice` | `ACT`, `PASS` | Sentence-level (with *se*) | Voice (passive with *se pasiva*) |
| `degree` | `COMP`, `SUPER` | Step A (irregular lookup) | Degree of adjective (synthetic comparatives only) |
| `formality` | `FORMAL`, `INFORMAL` | Step A (verb conjugation) | Register: *usted/ustedes* = FORMAL, *tu/vosotros* = INFORMAL |
| `subj_form` | `RA`, `SE` | Step A (imperfect subjunctive) | Distinguishes *-ra* vs. *-se* subjunctive forms |
| `clitic_obj` | e.g., `ME`, `SE+LO`, `TE+LA` | Step A (clitic stripping) | Attached enclitic pronoun(s), joined with `+` |
| `subcat` | `COORD`, `SUBORD`, `CLITIC`, `DEM`, `INDEF`, `REL`, `INTERR`, etc. | Closed-class | Subcategory within POS |
| `distance` | `PROX`, `MED`, `DIST` | Closed-class (demonstratives) | Deictic distance for demonstratives |
| `contraction` | `YES` | Closed-class (al, del) | Contracted preposition + article |
| `invariant` | `YES` | Step A (invariant nouns) | Noun form is identical in SG/PL |
| `derived_chain` | list of strings | Steps B/C | Derivational affixes stripped, e.g., `["cion->ACTION_NOUN", "inter->BETWEEN"]` |

### Bundle Count

**Estimated: ~90-110 unique feature bundles.**

Justification:

1. **Verb bundles (finite):** 6 persons x (5 tenses x 2 moods [IND + SUBJ] + 1 imperative) = 6 x 11 = 66 bundles. Adding the *-ra/-se* distinction for imperfect subjunctive adds 6 more = 72 finite verb bundles.
2. **Verb bundles (non-finite):** Infinitive (1) + gerund (1) + participle with 4 gender/number variants (4) = 6 non-finite verb bundles.
3. **Noun bundles:** 2 genders x 2 numbers = 4, plus invariant = 5 noun bundles.
4. **Adjective bundles:** 4-form (4) + 2-form with number only (2) + comparatives (2) = 8 adjective bundles.
5. **Closed-class bundles:** Determiners with gender/number (~6) + various pronoun subcategories (~8) + others = ~15 closed-class bundles.
6. **UNKNOWN:** 1 bundle.

Total: ~72 + 6 + 5 + 8 + 15 + 1 = **~107 bundles**. Clitic combinations would add further bundles but are encoded as tag values rather than separate bundles, keeping the count manageable.

This places Spanish firmly between English (~15-25 bundles) and Arabic (~100+ bundles) / Turkish (~80+ bundles), consistent with its "regular fusional" typological classification.

## Config Files

| File | Est. Entries | Structure | Purpose |
|------|-------------|-----------|---------|
| `es_irregulars.json` | ~2,500 | `Dict[surface_form, {base, pos, tag}]` -- tag is pipe-delimited `key=value` pairs | Irregular verb forms (all conjugations of ~400 irregular/stem-changing verbs), irregular participles, irregular comparatives, irregular noun plurals |
| `es_derivations.json` | ~55 rules | `List[{affix, surface_variants[], type, direction, derives, notes, examples}]` | Derivational affixes (~35 suffix rules + ~20 prefix rules) with surface variants, directionality, semantic type, and examples |
| `es_gender_exceptions.json` | ~50 | `Dict[noun, gender]` | Nouns whose gender cannot be predicted from their ending (*dia*=MASC, *mano*=FEM, etc.) |
| `es_invariant_nouns.json` | ~20 | `List[str]` | Nouns identical in singular and plural (*crisis*, *lunes*, etc.) |
| `es_verb_frequency.json` | ~10,000 | `Dict[infinitive, frequency_rank]` | Verb frequency list for conjugation class validation |

### es_irregulars.json Structure

```json
{
  "soy": {"base": "ser", "pos": "VERB", "tag": "tense=PRES|mood=IND|person=1|num=SG"},
  "eres": {"base": "ser", "pos": "VERB", "tag": "tense=PRES|mood=IND|person=2|num=SG"},
  "fui": {"base": "ir", "pos": "VERB", "tag": "tense=PAST_SIMPLE|mood=IND|person=1|num=SG"},
  "dicho": {"base": "decir", "pos": "VERB", "tag": "aspect=PERF|form=PTCP"},
  "mejor": {"base": "bueno", "pos": "ADJ", "tag": "degree=COMP"},
  "hice": {"base": "hacer", "pos": "VERB", "tag": "tense=PAST_SIMPLE|mood=IND|person=1|num=SG"}
}
```

Note: *fui* is ambiguous between *ser* (preterite 1SG) and *ir* (preterite 1SG). The engine stores the first registration (conventionally *ir*) and adds an `ambig_ser_ir=YES` tag. Disambiguation is deferred to sentence-level context.

### es_derivations.json Structure

```json
[
  {
    "affix": "-cion",
    "surface_variants": ["-cion", "-sion"],
    "type": "SUFFIX",
    "direction": "V->N",
    "derives": "ACTION_NOUN",
    "notes": "Nominalizes verbs. -sion after stems ending in -t, -d, -s.",
    "examples": ["comunicacion <- comunicar", "expresion <- expresar"]
  },
  {
    "affix": "des-",
    "surface_variants": ["des-"],
    "type": "PREFIX",
    "direction": "V->V",
    "derives": "REVERSAL_NEGATION",
    "notes": "Reverses or negates the base verb meaning.",
    "examples": ["deshacer <- hacer", "desaparecer <- aparecer"]
  }
]
```

## Validators

### Word-level: `check_morph_sequence_es`

Validates that each token's tag bundle is internally consistent for its POS.

**Allowed tag keys per POS:**

| POS | Allowed Tag Keys |
|-----|-----------------|
| `NOUN` | `num`, `gender`, `invariant` |
| `VERB` | `tense`, `mood`, `person`, `num`, `aspect`, `form`, `formality`, `subj_form`, `clitic_obj` |
| `ADJ` | `num`, `gender`, `degree` |
| `ADV` | `degree`, `subcat` |

**Additional constraints for VERB:**

- If `mood=IMP`, then `person` must not be `1` (no 1SG imperative exists).
- If `mood=SUBJ` and `tense=PAST_IMPERF`, then `subj_form` must be `RA` or `SE`.
- If `form=INF`, then `tense`, `person`, `num`, and `mood` must all be absent (infinitives are uninflected).
- If `form=GER`, then `tense`, `person`, `num`, and `mood` must all be absent (gerunds are uninflected, though they carry `aspect=PROG`).
- If `form=PTCP` and `gender` is present, then `num` must also be present (participles used adjectivally agree in both gender and number).

**Additional constraints for NOUN:**

- `gender` must be `MASC`, `FEM`, or absent (not `NEUT` -- only `lo` is neuter, and it is a DET).
- If `invariant=YES`, then `num` must be `SG` (the singular form is stored as canonical).

Returns `True` if all tokens pass, `False` on the first violation.

### Sentence-level: `validate_sentence_structure_es`

Validates cross-token structural constraints in a Spanish SVO sentence.

1. **Gender/number agreement (noun-adjective):** For each adjacent NOUN-ADJ or ADJ-NOUN pair, if both have `gender` tags, the values must match. If both have `num` tags, the values must match. Violation message: `"gender/number disagreement between noun and adjective: {noun_surface} / {adj_surface}"`.

2. **Verb person/number consistency:** If `mood=IND` or `mood=SUBJ`, then `person` and `num` must both be present. Violation message: `"finite verb missing person or number: {surface}"`.

3. **Clitic on non-verb:** `clitic_obj` must only appear on tokens with POS = `VERB`. Violation message: `"clitic_obj on non-VERB: {surface}"`.

4. **Degree on non-adjective:** `degree=COMP` or `degree=SUPER` must only appear on tokens with POS = `ADJ`. Violation message: `"degree tag on non-ADJ: {surface}"`.

5. **Imperative with clitic validation:** If `mood=IMP` and `clitic_obj` is present, the clitic must be enclitic (post-verbal). This is always true at the word level (enclitics are the only kind that attach) so this check serves as a sanity assertion. Violation message: `"proclitic on imperative: {surface}"`.

Returns a `(bool, str)` tuple: `(True, "ok")` on success, or `(False, error_message)` on failure.

Both validators are called in `analyze_sentence()`, with their results ANDed to produce the final validity flag.

## Known Limitations

1. **No voseo handling:** Argentine, Uruguayan, and Central American Spanish use *vos* instead of *tu*, with distinct conjugation patterns (*vos hablas* vs. *vos hablais*). The engine does not model voseo forms. Adding voseo support would require a separate 2SG paradigm for each tense.

2. **No dialectal variation:** The engine models Peninsular Spanish (Castilian) as the reference variety. Latin American varieties that differ in pronoun usage (no *vosotros* forms), phonological features (seseo, yeismo), or vocabulary are not specifically handled. The *vosotros* forms are included but may not appear in Latin American corpora.

3. **No leismo/loismo/laismo:** The engine does not model the dialectal variation in clitic pronoun usage where *le* replaces *lo* as a masculine accusative (leismo) or *la* replaces *le* as a feminine dative (laismo). All clitics are tagged with their standard Peninsular functions.

4. **No diminutives or augmentatives:** Productive diminutive suffixes (*-ito/-ita/-illo/-illa/-ico/-ica*) and augmentatives (*-on/-ona/-azo/-aza/-ote/-ota*) are not handled. These are highly productive and semantically nuanced (they can express endearment, contempt, approximation, or literal size change). Including them would add approximately 30-40 additional derivational rules and significant false-positive risk (e.g., *bolsillo* "pocket" is not a diminutive of *bolso*).

5. **No context-dependent POS disambiguation:** Words like *que* (relative pronoun vs. conjunction vs. complementizer), *como* (adverb vs. conjunction vs. verb form of *comer*), and *para* (preposition vs. verb form of *parar*) always receive their closed-class POS regardless of syntactic context.

6. **No superlative absoluto:** The *-isimo/-isima* suffix (e.g., *rapidisimo* "very fast") is a productive inflectional/derivational hybrid not handled by the current design. It could be added as either an inflectional rule (Step A) or a derivational suffix (Step B).

7. **Preterite/imperative ambiguity for -ar verbs:** The 3SG preterite (*hablo* "he spoke") and the 1SG present indicative (*hablo* "I speak") of *-ar* verbs are disambiguated only by accent marks (*hablo* vs. *hablo*). If the input lacks accent marks, the engine defaults to the present indicative reading.

8. **Compound tenses are not unified:** Compound tenses like *he hablado* (present perfect) are analyzed as two separate tokens (*he* = auxiliary, *hablado* = participle) rather than as a unified tense. Cross-token tense identification is deferred to downstream processing.

9. **Reflexive/passive *se* ambiguity:** The clitic *se* can indicate reflexive action (*se lava* "he washes himself"), impersonal construction (*se dice* "one says / it is said"), or passive voice (*se vendieron las casas* "the houses were sold"). The engine tags *se* uniformly as `subcat=CLITIC` without distinguishing these functions.

10. **No periphrastic future:** The common spoken future construction *ir + a + infinitive* (*voy a hablar* "I'm going to speak") is not recognized as a tense marker. Each word is analyzed independently.

## Test Plan

### Test Categories and Estimated Counts

| Test Category | Est. Tests | Description |
|--------------|-----------|-------------|
| **Irregular verb conjugation** | ~200 | All forms of the 20-30 truly irregular verbs (*ser*, *ir*, *haber*, *estar*, *tener*, *hacer*, *poder*, *poner*, *saber*, *querer*, *venir*, *decir*, *dar*, *ver*, *oir*, *salir*, *valer*, *caber*, *traer*, *caer*). Verify correct base, tense, mood, person, number for each form. |
| **Regular verb paradigms** | ~100 | 3 conjugation classes x 14 tense/mood combinations x ~2 representative persons each. Verify correct suffix stripping and tag assignment for regular *-ar*, *-er*, *-ir* verbs. |
| **Stem-changing verbs** | ~50 | Cover all stem-change patterns (*e->ie*, *o->ue*, *e->i*, *u->ue*) across affected tenses. Verify reverse stem-change recovery. |
| **Noun gender/number** | ~50 | Regular masculine/feminine, regular plural (*-s*, *-es*, *-ces*), gender exceptions (*dia*, *mano*, *mapa*), invariant nouns (*crisis*, *lunes*), Greek-origin *-ma* nouns. |
| **Adjective agreement** | ~30 | 4-form adjectives (*bueno* paradigm), 2-form adjectives (*grande*, *feliz*), irregular comparatives (*mejor*, *peor*, *mayor*, *menor*). |
| **Clitic handling** | ~40 | Single enclitics (*verlo*, *hacerla*), double enclitics (*diselo*, *damelo*), triple enclitics (*diciendoselo*), accent restoration after clitic stripping, rejection of false clitic matches. |
| **Derivation** | ~50 | Suffix stripping (*-cion*, *-miento*, *-mente*, *-idad*, *-ble*, *-oso*), prefix stripping (*des-*, *in-/im-*, *re-*, *pre-*), multi-layer derivation (*internacionalizacion*), derivation chain recording. |
| **Closed-class** | ~30 | All categories (determiners, prepositions, pronouns, conjunctions, adverbs, numerals). Verify POS and subcategory tags. Verify that closed-class words bypass inflectional analysis. |
| **Sentence-level validation** | ~30 | Gender/number agreement checks, verb person/number consistency, clitic-on-non-verb rejection, degree-on-non-adjective rejection. |
| **Adversarial/edge cases** | ~50 | Empty strings, single characters, words that look like conjugations but are not (*como* as "I eat" vs. "like"), accent-mark ambiguity (*hablo* vs. *hablo*), words ending in *-mente* that are not adverbs (*clemente*), short words that could be false-matched, unknown words. |

**Total: ~630 tests across 10 categories.**

### Test File Organization

| Test File | Categories |
|-----------|-----------|
| `test_es_engine_irregular_verbs.py` | Irregular verb conjugation (~200 tests) |
| `test_es_engine_regular_verbs.py` | Regular verb paradigms, stem-changing verbs (~150 tests) |
| `test_es_engine_nominal.py` | Noun gender/number, adjective agreement (~80 tests) |
| `test_es_engine_clitics.py` | Enclitic stripping and tagging (~40 tests) |
| `test_es_engine_derivation.py` | Derivational suffix/prefix detection, multi-layer (~50 tests) |
| `test_es_engine_closed_class.py` | Closed-class intercept (~30 tests) |
| `test_es_engine_sentence.py` | Sentence-level validation (~30 tests) |
| `test_es_engine_adversarial.py` | Edge cases, false positives, boundary conditions (~50 tests) |
