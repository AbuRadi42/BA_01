# Basque Engine Design Specification

**Language:** Basque / Euskara (eu)
**Typology:** Polypersonal + ergative-absolutive -- morphological outlier, language isolate
**Engine file:** `scripts/engines/eu_engine.py` (to be built)
**Status:** Design phase
**Role in experiment:** Predicted strongest efficiency gain

---

## Morphological Overview

Basque (Euskara) is a language isolate -- it has no demonstrated genetic relationship to any other living or dead language. It predates the Indo-European expansion into the Iberian Peninsula by millennia and survived in the mountainous terrain of the western Pyrenees, straddling the modern border of Spain and France. Its morphological system evolved in complete isolation from every other language in this experiment: it shares no common ancestor with the Indo-European languages (English, German, Spanish), the Afro-Asiatic languages (Arabic), the Uralic languages (Hungarian), the Altaic/Turkic languages (Turkish), the Sino-Tibetan languages (Chinese), or the Bantu languages (Swahili). This independence is scientifically critical: if the morphological efficiency formula produces valid predictions for Basque, it cannot be an artifact of shared linguistic ancestry. The formula would then be genuinely universal.

The most typologically distinctive feature of Basque is its **ergative-absolutive alignment** (ergatibo-absolutibo sistema). In the nominative-accusative alignment used by most European languages, the subject of both transitive and intransitive verbs receives the same morphological marking (nominative case), while the object of a transitive verb is distinctly marked (accusative case). Basque inverts this pattern. The subject of an intransitive verb (NOR = "nor" = "who") and the object of a transitive verb both receive **absolutive case** (absolutiboa, zero-marking or -a/-ak for definite forms). The subject of a transitive verb (NORK = "nor-k" = "who-ERG") receives **ergative case** (ergatiboa, -k/-ek). Concretely: "Umea lo dago" (The child sleeps) uses child-ABS, but "Umeak liburua irakurtzen du" (The child reads the book) uses child-ERG book-ABS. The intransitive subject and the transitive object share the same case marking. This alignment pervades the entire grammar and fundamentally shapes the auxiliary verb system.

Basque possesses a **tri-personal verb agreement** system (aditz laguntzailea hirupertsonal), which is the single most information-dense morphological feature in this entire nine-language experiment. The vast majority of Basque verbs (~99%) use a periphrastic construction: a main verb in participial form (aditz nagusia) paired with an auxiliary verb (aditz laguntzailea). The auxiliary agrees simultaneously with up to three arguments: NOR (absolutive = intransitive subject or transitive direct object), NORK (ergative = transitive subject), and NORI (dative = indirect object). A single auxiliary form like "diet" encodes three agreement slots: d- (ABS.3SG) + -i- (root) + -e- (DAT.1SG) + -t (ERG.3SG), meaning "he/she [verb]s it to me." This means one auxiliary word can encode the equivalent of three separate pronouns plus tense information, packing an extraordinary density of grammatical information into a single morphological unit. The NOR-NORI-NORK paradigm (ditransitive, three-argument agreement) produces approximately 200-600 distinct forms depending on tense, making it by far the largest paradigm table of any language in the experiment.

The **case system** (kasu sistema) comprises 14 productive cases, applied agglutinatively via suffixes. Beyond the grammatical core of absolutive (-zero/-a/-ak), ergative (-k/-ek), dative (-ri/-ari/-ei), and genitive (-ren/-aren/-en), Basque employs a rich set of locative and relational cases: comitative (-rekin, "with"), instrumental (-z, "by means of"), inessive (-n/-an/-etan, "in"), allative (-ra/-ara/-etara, "to"), ablative (-tik/-atik/-etatik, "from"), locative-genitive (-ko/-ako/-etako, "of/at"), destinative (-rako/-arako/-etarako, "for/towards"), motivative (-gatik/-agatik/-egatik, "because of"), partitive (-rik, "some/any"), and prolative (-tzat/-atzat/-etzat, "as/for the purpose of"). These suffixes attach to the determiner-marked stem, creating a fused determiner+case complex that the engine must decompose.

A crucial asymmetry governs the verb system: only approximately 10 verbs possess **synthetic conjugation** (aditz trinkoak), where a single word carries both the lexical content and all agreement/tense information. These include: izan (to be), ukan/edun (to have), egon (to be/stay), joan (to go), etorri (to come), jakin (to know), ekarri (to bring), eraman (to carry), ibili (to walk), and esan (to say). All other verbs in the language -- hundreds of lexical verbs -- use the **periphrastic construction** (aditz perifrastikoak), where the main verb appears as a non-finite form (participle, imperfective, or prospective) and the auxiliary carries all inflectional information. The main verb's non-finite form encodes aspect: the participle (-tu/-du/-i) marks perfective aspect, the imperfective stem (-tzen/-ten) marks ongoing/habitual action, and the prospective form (-ko/-go) marks future/intentional action. The engine must handle both synthetic forms (via lookup) and periphrastic constructions (via compositional analysis of main verb + auxiliary).

The non-finite verb forms follow regular patterns with limited allomorphy. The **perfective participle** (partizipioa) takes -tu after consonant-final stems (ikasi -> ikasi, but egin -> egin is irregular, ikusi -> ikusi), -du after certain nasal/liquid-final stems, or -i for a class of older verbs. The **imperfective** (burutugabea) takes -tzen (after consonants) or -ten (after certain stems): ikusten (seeing), egiten (doing), etortzen (coming). The **prospective** (gerokoa) takes -ko (after consonants) or -go (after nasals/liquids): ikusiko (will see), egingo (will do). These suffixes are stripped in Step A to recover the verbal stem and assign aspect tags.

Basque also features **allocutive verb forms** (hitanoa), a globally rare phenomenon where the auxiliary verb marks the gender of the addressee (the person being spoken to), even when that person is not a participant in the event described. In the informal register (hika), auxiliaries take additional morphology: masculine allocutive forms use -k-based suffixes and feminine allocutive forms use -n-based suffixes. For example, "da" (it is, neutral) becomes "duk" (it is, speaking to a male friend) or "dun" (it is, speaking to a female friend). This effectively creates a fourth agreement slot. For this engine, the most frequent allocutive forms will be included in the auxiliary lookup table with an `allocutive_gender` tag, but exhaustive coverage of all allocutive combinations across all paradigms is deferred to a future phase due to the combinatorial explosion it introduces.

## Closed-Class Intercept

The engine intercepts closed-class function words before attempting morphological analysis. These words are atomic lexical items that should not be decomposed.

**Conjunctions (12):** eta (AND), edo (OR), baina (BUT), baizik (BUT_RATHER), ezta (NOR), hala ere (NEVERTHELESS), beraz (THEREFORE), orduan (THEN), gainera (MOREOVER), bestalde (ON_THE_OTHER_HAND), nahiz eta (ALTHOUGH), baldin eta (IF)

**Question words (10):** nor (WHO), zer (WHAT), non (WHERE), nora (WHERE_TO), nondik (WHERE_FROM), noiz (WHEN), nola (HOW), zergatik (WHY), zein (WHICH), zenbat (HOW_MANY)

**Pronouns (20):** ni (1SG), zu (2SG_FORMAL), hi (2SG_INFORMAL), hura (3SG), gu (1PL), zuek (2PL), haiek (3PL), hau (DEM_PROX), hori (DEM_MED), hura (DEM_DIST), nor (INTERR_WHO), zer (INTERR_WHAT), bera (REFLEXIVE), elkar (RECIPROCAL), zerbait (INDEF_THING), norbait (INDEF_PERSON), ezer (NEG_THING), inor (NEG_PERSON), dena (UNIVERSAL_THING), denak (UNIVERSAL_PERSON)

**Postpositions (14):** aurretik (BEFORE), ondoren (AFTER), gainean (ON_TOP), azpian (UNDER), artean (BETWEEN), inguruan (AROUND), barruan (INSIDE), kanpoan (OUTSIDE), alde (SIDE), kontra (AGAINST), buruz (ABOUT), gabe (WITHOUT), bidez (BY_MEANS_OF), zehar (THROUGH)

**Adverbs (16):** oso (VERY), ere (ALSO), bakarrik (ONLY), hemen (HERE_PROX), hor (HERE_MED), han (THERE_DIST), orain (NOW), gero (LATER), lehen (BEFORE), beti (ALWAYS), inoiz (NEVER), askotan (OFTEN), gutxitan (RARELY), ondo (WELL), gaizki (BADLY), azkar (FAST)

**Particles (5):** ez (NEG), ba- (AFF_COND), al (Q_PARTICLE), ote (WONDER), bide (APPARENTLY)

**Determiners (5):** bat (INDEF_SG), batzuk (INDEF_PL), hainbat (SEVERAL), asko (MANY), gutxi (FEW)

**Total: 82 entries**

Note on the definite article: Basque marks definiteness with a **bound suffix** (-a singular, -ak plural) fused directly onto the noun stem, not as a separate word. For example, "etxe" (house) becomes "etxea" (the house) and "etxeak" (the houses). Because the article is a bound morpheme, it is handled in Step A (inflectional stripping) as part of the case suffix complex, NOT in the closed-class intercept. The determiner entries listed above (bat, batzuk, etc.) are the indefinite/quantifier determiners that do appear as free-standing words.

Note on multi-word entries: "hala ere", "nahiz eta", and "baldin eta" are multi-word conjunctions. The engine performs multi-token lookahead to catch these before individual words are analyzed.

## The Ergative-Absolutive System

This section documents the case alignment system that fundamentally distinguishes Basque from every other language in the experiment. The engine must correctly decompose case suffixes and assign alignment-aware tags.

### Alignment Rules

**Absolutive case (absolutiboa, NOR):** Used for (a) the sole argument of an intransitive verb (S), and (b) the patient/object of a transitive verb (O). These two syntactic roles receive the same morphological marking. The auxiliary verb agrees with the absolutive argument in its NOR slot.

**Ergative case (ergatiboa, NORK):** Used exclusively for the agent/subject of a transitive verb (A). The auxiliary verb agrees with the ergative argument in its NORK slot.

**Dative case (datiboa, NORI):** Used for the indirect object/recipient of a ditransitive verb. The auxiliary verb agrees with the dative argument in its NORI slot.

### Case Alignment Examples

| Sentence | Gloss | Alignment |
|----------|-------|-----------|
| Umea lo dago | child-ABS sleep is | S=ABS (intransitive) |
| Umeak liburua irakurtzen du | child-ERG book-ABS read-IMPERF AUX(3SG.ABS+3SG.ERG) | A=ERG, O=ABS (transitive) |
| Umeak amari liburua eman dio | child-ERG mother-DAT book-ABS give-PERF AUX(3SG.ABS+3SG.DAT+3SG.ERG) | A=ERG, IO=DAT, O=ABS (ditransitive) |

### Full Case Suffix Table

The 14 cases with their suffix forms across definiteness and number. The definite article (-a/-ak) is fused into the case suffix; the engine strips the combined case+definiteness complex as a single unit.

| Case | Basque name | Indefinite | Def. SG | Def. PL | Tag |
|------|-------------|-----------|---------|---------|-----|
| ABS | Absolutiboa | -zero | -a | -ak | case=ABS |
| ERG | Ergatiboa | -k (rare) | -ak | -ek | case=ERG |
| DAT | Datiboa | -(r)i | -ari | -ei | case=DAT |
| GEN | Genitiboa | -(r)en | -aren | -en | case=GEN |
| COM | Soziatiboa | -(r)ekin | -arekin | -ekin | case=COM |
| INS | Instrumentala | -(e)z | -az | -ez | case=INS |
| INES | Inesiboa | -(e)n | -an | -etan | case=INES |
| ALLAT | Adlatiboa | -(e)ra | -ara | -etara | case=ALLAT |
| ABLAT | Ablatiboa | -(e)tik | -atik | -etatik | case=ABLAT |
| LOC_GEN | Leku-genitiboa | -(e)ko | -ako | -etako | case=LOC_GEN |
| DEST | Destinatiboa | -(e)rako | -arako | -etarako | case=DEST |
| MOT | Motibatiboa | -(e)gatik | -agatik | -egatik | case=MOT |
| PART | Partitiboa | -(r)ik | -- | -- | case=PART |
| PROL | Prolatiboa | -(t)zat | -atzat | -etzat | case=PROL |

**Stripping strategy:** Longest suffix first. The engine builds a flattened list of all case+definiteness+number suffix combinations and sorts them by descending length. For each word, it attempts to match the longest suffix first, and upon a match, strips the suffix and assigns `case`, `num`, and `def` tags simultaneously.

**Definiteness extraction:** Because the definite article is fused into the case suffix (e.g., -ari = -a.DEF + -ri.DAT), the engine does not strip the article separately. Instead, each suffix entry in the lookup table carries pre-assigned `def` and `num` values:

| Suffix form | case | def | num |
|-------------|------|-----|-----|
| -a | ABS | DEF | SG |
| -ak | ABS or ERG | DEF | PL (ABS) or SG (ERG) |
| -ek | ERG | DEF | PL |
| -ari | DAT | DEF | SG |
| -ei | DAT | DEF | PL |
| -aren | GEN | DEF | SG |
| -en | GEN | DEF | PL |
| -arekin | COM | DEF | SG |
| -ekin | COM | DEF | PL |
| ... | ... | ... | ... |

**Critical ambiguity:** The suffix -ak is ambiguous between ABS.DEF.PL and ERG.DEF.SG. For example, "gizonak" could be "the men" (ABS.PL, intransitive subject or transitive object) or "the man" (ERG.SG, transitive subject). Disambiguation requires sentence-level context (presence of a transitive auxiliary). The engine records both possible readings when the suffix is -ak and defers disambiguation to the sentence-level validator.

**Handling the ERG.INDEF:** Indefinite ergative marking (-k directly on an indefinite stem) is rare in modern Standard Basque (Batua) and typically restricted to specific syntactic environments. The engine treats bare -k on an indefinite noun as a low-confidence ERG.INDEF tag.

## The Auxiliary System (Aditz Laguntzailea)

This is the most complex component of the engine and the primary source of Basque's predicted efficiency advantage. The auxiliary verb system encodes agreement with up to three arguments in a single word form, producing an extraordinarily high density of grammatical information per token.

### Architecture Decision: Lookup Table

Unlike Turkish, where suffixes are transparently segmentable (one morpheme per slot, agglutinative), Basque auxiliaries are **fusional**: a single auxiliary form encodes multiple agreement values simultaneously, and the morpheme boundaries are often impossible to segment cleanly. For example, in "diegu" (we [verb] them to him/her), the form cannot be cleanly cut into independent person morphemes -- the agreement values are distributed across the entire form through prefixes, infixes, and suffixes that interact.

Therefore, the engine uses a **full-form lookup table** rather than a suffix-stripping approach for auxiliaries. The table is stored in `eu_auxiliary.json` and maps each auxiliary surface form directly to its decomposed agreement values. This is more practical and more accurate than attempting morpheme segmentation on fusional forms.

When the engine encounters a word, it first checks the auxiliary lookup table. If the word is found, the engine returns the pre-decomposed tags directly, bypassing Steps A/B/C entirely.

### Paradigm 1: NOR (Intransitive -- izan "to be")

Agreement with the absolutive argument only. This is the simplest paradigm.

**Present tense (orainaldia):**

| ABS person | Form | Tags |
|-----------|------|------|
| 1SG | naiz | agr_obj=1SG, tense=PRES |
| 2SG_FORMAL | zara | agr_obj=2SG, tense=PRES, formality=FORMAL |
| 2SG_INFORMAL | haiz | agr_obj=2SG, tense=PRES, formality=INFORMAL |
| 3SG | da | agr_obj=3SG, tense=PRES |
| 1PL | gara | agr_obj=1PL, tense=PRES |
| 2PL | zarete | agr_obj=2PL, tense=PRES |
| 3PL | dira | agr_obj=3PL, tense=PRES |

**Past tense (iraganaldia):**

| ABS person | Form | Tags |
|-----------|------|------|
| 1SG | nintzen | agr_obj=1SG, tense=PAST |
| 2SG_FORMAL | zinen | agr_obj=2SG, tense=PAST, formality=FORMAL |
| 2SG_INFORMAL | hintzen | agr_obj=2SG, tense=PAST, formality=INFORMAL |
| 3SG | zen | agr_obj=3SG, tense=PAST |
| 1PL | ginen | agr_obj=1PL, tense=PAST |
| 2PL | zineten | agr_obj=2PL, tense=PAST |
| 3PL | ziren | agr_obj=3PL, tense=PAST |

**Hypothetical/subjunctive (ahalezkoa):**

| ABS person | Form | Tags |
|-----------|------|------|
| 1SG | nintzateke | agr_obj=1SG, mood=POT |
| 3SG | litzateke / zateke | agr_obj=3SG, mood=POT |
| 1PL | ginateke | agr_obj=1PL, mood=POT |
| 3PL | lirateke | agr_obj=3PL, mood=POT |

**Imperative (agintera):**

| ABS person | Form | Tags |
|-----------|------|------|
| 2SG_FORMAL | zaitez | agr_obj=2SG, mood=IMP, formality=FORMAL |
| 2SG_INFORMAL | hadi | agr_obj=2SG, mood=IMP, formality=INFORMAL |
| 2PL | zaitezte | agr_obj=2PL, mood=IMP |
| 3SG | bedi | agr_obj=3SG, mood=IMP |
| 3PL | bitez | agr_obj=3PL, mood=IMP |

**NOR paradigm total:** ~30 forms (7 present + 7 past + ~8 hypothetical + ~8 imperative)

### Paradigm 2: NOR-NORK (Transitive -- ukan/edun "to have")

Agreement with both the absolutive argument (NOR = direct object or subject role of the transitive) and the ergative argument (NORK = agent). This creates a matrix of person combinations.

**Present tense (orainaldia), ABS.3SG column:**

| ERG | Form | Tags |
|-----|------|------|
| 1SG | dut | agr_obj=3SG, agr_subj=1SG, tense=PRES |
| 2SG_FORMAL | duzu | agr_obj=3SG, agr_subj=2SG, tense=PRES, formality=FORMAL |
| 2SG_INFORMAL | duk (masc) / dun (fem) | agr_obj=3SG, agr_subj=2SG, tense=PRES, formality=INFORMAL |
| 3SG | du | agr_obj=3SG, agr_subj=3SG, tense=PRES |
| 1PL | dugu | agr_obj=3SG, agr_subj=1PL, tense=PRES |
| 2PL | duzue | agr_obj=3SG, agr_subj=2PL, tense=PRES |
| 3PL | dute | agr_obj=3SG, agr_subj=3PL, tense=PRES |

**Present tense, ABS.3PL column:**

| ERG | Form | Tags |
|-----|------|------|
| 1SG | ditut | agr_obj=3PL, agr_subj=1SG, tense=PRES |
| 2SG_FORMAL | dituzu | agr_obj=3PL, agr_subj=2SG, tense=PRES, formality=FORMAL |
| 3SG | ditu | agr_obj=3PL, agr_subj=3SG, tense=PRES |
| 1PL | ditugu | agr_obj=3PL, agr_subj=1PL, tense=PRES |
| 2PL | dituzue | agr_obj=3PL, agr_subj=2PL, tense=PRES |
| 3PL | dituzte | agr_obj=3PL, agr_subj=3PL, tense=PRES |

**Present tense, ABS.1SG column:**

| ERG | Form | Tags |
|-----|------|------|
| 2SG_FORMAL | nauzu | agr_obj=1SG, agr_subj=2SG, tense=PRES |
| 3SG | nau | agr_obj=1SG, agr_subj=3SG, tense=PRES |
| 1PL | -- | (impossible: "we verb me") |
| 2PL | nauzue | agr_obj=1SG, agr_subj=2PL, tense=PRES |
| 3PL | naute | agr_obj=1SG, agr_subj=3PL, tense=PRES |

**Present tense, ABS.2SG column:**

| ERG | Form | Tags |
|-----|------|------|
| 1SG | zaitut | agr_obj=2SG, agr_subj=1SG, tense=PRES |
| 3SG | zaitu | agr_obj=2SG, agr_subj=3SG, tense=PRES |
| 1PL | zaitugu | agr_obj=2SG, agr_subj=1PL, tense=PRES |
| 3PL | zaituzte | agr_obj=2SG, agr_subj=3PL, tense=PRES |

**Present tense, ABS.1PL column:**

| ERG | Form | Tags |
|-----|------|------|
| 2SG_FORMAL | gaituzu | agr_obj=1PL, agr_subj=2SG, tense=PRES |
| 3SG | gaitu | agr_obj=1PL, agr_subj=3SG, tense=PRES |
| 2PL | gaituzue | agr_obj=1PL, agr_subj=2PL, tense=PRES |
| 3PL | gaituzte | agr_obj=1PL, agr_subj=3PL, tense=PRES |

**Present tense, ABS.2PL column:**

| ERG | Form | Tags |
|-----|------|------|
| 1SG | zaitutztet | agr_obj=2PL, agr_subj=1SG, tense=PRES |
| 3SG | zaituzte | agr_obj=2PL, agr_subj=3SG, tense=PRES |
| 1PL | zaituzteegu | agr_obj=2PL, agr_subj=1PL, tense=PRES |
| 3PL | zaituztete | agr_obj=2PL, agr_subj=3PL, tense=PRES |

**Past tense (iraganaldia), ABS.3SG column:**

| ERG | Form | Tags |
|-----|------|------|
| 1SG | nuen | agr_obj=3SG, agr_subj=1SG, tense=PAST |
| 2SG_FORMAL | zenuen | agr_obj=3SG, agr_subj=2SG, tense=PAST |
| 3SG | zuen | agr_obj=3SG, agr_subj=3SG, tense=PAST |
| 1PL | genuen | agr_obj=3SG, agr_subj=1PL, tense=PAST |
| 2PL | zenuten | agr_obj=3SG, agr_subj=2PL, tense=PAST |
| 3PL | zuten | agr_obj=3SG, agr_subj=3PL, tense=PAST |

**Past tense, ABS.3PL column:**

| ERG | Form | Tags |
|-----|------|------|
| 1SG | nituen | agr_obj=3PL, agr_subj=1SG, tense=PAST |
| 2SG_FORMAL | zenituen | agr_obj=3PL, agr_subj=2SG, tense=PAST |
| 3SG | zituen | agr_obj=3PL, agr_subj=3SG, tense=PAST |
| 1PL | genituen | agr_obj=3PL, agr_subj=1PL, tense=PAST |
| 2PL | zenituzten | agr_obj=3PL, agr_subj=2PL, tense=PAST |
| 3PL | zituzten | agr_obj=3PL, agr_subj=3PL, tense=PAST |

**Past tense, ABS.1SG column:**

| ERG | Form | Tags |
|-----|------|------|
| 2SG_FORMAL | ninduzun | agr_obj=1SG, agr_subj=2SG, tense=PAST |
| 3SG | ninduen | agr_obj=1SG, agr_subj=3SG, tense=PAST |
| 2PL | ninduzuen | agr_obj=1SG, agr_subj=2PL, tense=PAST |
| 3PL | ninduten | agr_obj=1SG, agr_subj=3PL, tense=PAST |

**Past tense, ABS.2SG column:**

| ERG | Form | Tags |
|-----|------|------|
| 1SG | zintudan | agr_obj=2SG, agr_subj=1SG, tense=PAST |
| 3SG | zintuen | agr_obj=2SG, agr_subj=3SG, tense=PAST |
| 1PL | zintugun | agr_obj=2SG, agr_subj=1PL, tense=PAST |
| 3PL | zintuzten | agr_obj=2SG, agr_subj=3PL, tense=PAST |

**Impossible cells:** Reflexive combinations (1SG ERG + 1SG ABS, etc.) use distinct constructions with "burua" (self) or synthetic reflexive forms, and are excluded from the standard transitive paradigm.

**NOR-NORK paradigm total:** ~72 forms (36 present + 36 past, minus ~8 impossible reflexive cells per tense = ~56 per tense x 2 = ~112, plus ~20 hypothetical/imperative forms = ~132 forms)

### Paradigm 3: NOR-NORI (Intransitive-dative -- izan "to be" with dative)

Agreement with absolutive AND dative, but no ergative. Used with intransitive verbs that take dative arguments (e.g., "gustatzen zait" = "it pleases to me" = "I like it").

**Present tense, ABS.3SG:**

| DAT | Form | Tags |
|-----|------|------|
| 1SG | zait | agr_obj=3SG, agr_iobj=1SG, tense=PRES |
| 2SG_FORMAL | zaizu | agr_obj=3SG, agr_iobj=2SG, tense=PRES |
| 3SG | zaio | agr_obj=3SG, agr_iobj=3SG, tense=PRES |
| 1PL | zaigu | agr_obj=3SG, agr_iobj=1PL, tense=PRES |
| 2PL | zaizue | agr_obj=3SG, agr_iobj=2PL, tense=PRES |
| 3PL | zaie | agr_obj=3SG, agr_iobj=3PL, tense=PRES |

**Present tense, ABS.3PL:**

| DAT | Form | Tags |
|-----|------|------|
| 1SG | zaizkit | agr_obj=3PL, agr_iobj=1SG, tense=PRES |
| 2SG_FORMAL | zaizkizu | agr_obj=3PL, agr_iobj=2SG, tense=PRES |
| 3SG | zaizkio | agr_obj=3PL, agr_iobj=3SG, tense=PRES |
| 1PL | zaizkigu | agr_obj=3PL, agr_iobj=1PL, tense=PRES |
| 2PL | zaizkizue | agr_obj=3PL, agr_iobj=2PL, tense=PRES |
| 3PL | zaizkie | agr_obj=3PL, agr_iobj=3PL, tense=PRES |

**Past tense, ABS.3SG:**

| DAT | Form | Tags |
|-----|------|------|
| 1SG | zitzaidan | agr_obj=3SG, agr_iobj=1SG, tense=PAST |
| 2SG_FORMAL | zitzaizun | agr_obj=3SG, agr_iobj=2SG, tense=PAST |
| 3SG | zitzaion | agr_obj=3SG, agr_iobj=3SG, tense=PAST |
| 1PL | zitzaigun | agr_obj=3SG, agr_iobj=1PL, tense=PAST |
| 2PL | zitzaizuen | agr_obj=3SG, agr_iobj=2PL, tense=PAST |
| 3PL | zitzaien | agr_obj=3SG, agr_iobj=3PL, tense=PAST |

**NOR-NORI paradigm total:** ~50 forms (12 present + 12 past per ABS value, expanded across ABS.1SG/2SG/1PL/2PL columns + hypothetical)

### Paradigm 4: NOR-NORI-NORK (Ditransitive -- the crown jewel)

Agreement with ALL THREE arguments: absolutive (NOR = direct object), dative (NORI = indirect object), and ergative (NORK = subject). This is the most information-dense morphological paradigm in any language in the experiment.

**Present tense, ABS.3SG:**

| ERG \ DAT | 1SG | 2SG | 3SG | 1PL | 2PL | 3PL |
|-----------|-----|-----|-----|-----|-----|-----|
| 1SG | -- | dizut | diot | -- | dizuet | diet |
| 2SG | didazu | -- | diozu | -- | -- | diezu |
| 3SG | dit | dizu | dio | digu | dizue | die |
| 1PL | -- | dizugu | diogu | -- | dizuegu | diegu |
| 2PL | didazue | -- | diozue | -- | -- | diezue |
| 3PL | didate | dizute | diote | digute | dizuete | diete |

**Present tense, ABS.3PL:**

| ERG \ DAT | 1SG | 2SG | 3SG | 1PL | 2PL | 3PL |
|-----------|-----|-----|-----|-----|-----|-----|
| 1SG | -- | dizkizut | dizkiot | -- | dizkizuet | dizkiet |
| 2SG | dizkidazu | -- | dizkiozu | -- | -- | dizkiezu |
| 3SG | dizkit | dizkizu | dizkio | dizkigu | dizkizue | dizkie |
| 1PL | -- | dizkizugu | dizkiogu | -- | dizkizuegu | dizkiegu |
| 2PL | dizkidazue | -- | dizkiozue | -- | -- | dizkiezue |
| 3PL | dizkidate | dizkizute | dizkiote | dizkigute | dizkizuete | dizkiete |

**Past tense, ABS.3SG:**

| ERG \ DAT | 1SG | 2SG | 3SG | 1PL | 2PL | 3PL |
|-----------|-----|-----|-----|-----|-----|-----|
| 1SG | -- | nizun | nion | -- | nizuen | nien |
| 2SG | zenidan | -- | zenion | -- | -- | zenien |
| 3SG | zidan | zizun | zion | zigun | zizuen | zien |
| 1PL | -- | genizun | genion | -- | genizuen | genien |
| 2PL | zenidaten | -- | zenioten | -- | -- | zenieten |
| 3PL | zidaten | zizuten | zioten | ziguten | zizueten | zieten |

**Past tense, ABS.3PL:**

| ERG \ DAT | 1SG | 2SG | 3SG | 1PL | 2PL | 3PL |
|-----------|-----|-----|-----|-----|-----|-----|
| 1SG | -- | nizkizun | nizkion | -- | nizkizuen | nizkien |
| 2SG | zenizkidan | -- | zenizkion | -- | -- | zenizkien |
| 3SG | zizkidan | zizkizun | zizkion | zizkigun | zizkizuen | zizkien |
| 1PL | -- | genizkizun | genizkion | -- | genizkizuen | genizkien |
| 2PL | zenizkidaten | -- | zenizkioten | -- | -- | zenizkieten |
| 3PL | zizkidaten | zizkizuten | zizkioten | zizkiguten | zizkizueten | zizkieten |

**Morphological decomposition example:**

The form "dizkiogu" (present, ABS.3PL, DAT.3SG, ERG.1PL) can be analyzed as:
- d- : present tense prefix (3rd person ABS marker)
- -izki- : plural absolutive infix (marks ABS as 3PL rather than 3SG)
- -o- : dative 3SG marker
- -gu : ergative 1PL suffix

But this segmentation is not fully regular across the paradigm -- for example, the 1SG ergative suffix is -t (diot), the 3SG ergative has zero marking (dio), and the 3PL ergative suffix is -te (diote). The prefixes also change by ABS person: d- for 3rd person ABS, n- for 1SG ABS, z-/g- for 2nd/1PL ABS. This partial regularity is why the engine uses a lookup table rather than attempting compositional segmentation.

**NOR-NORI-NORK paradigm total:** ~200 forms for present+past with ABS.3SG and ABS.3PL columns. Including ABS.1SG, ABS.2SG, ABS.1PL, ABS.2PL columns plus hypothetical/imperative moods brings the total to ~350-400 forms.

### Lookup Table Structure

Each entry in `eu_auxiliary.json` has the following schema:

```json
{
  "diot": {
    "paradigm": "NOR-NORI-NORK",
    "tense": "PRES",
    "mood": "IND",
    "abs": "3SG",
    "dat": "3SG",
    "erg": "1SG",
    "polarity": "AFF"
  },
  "ez_diot": {
    "paradigm": "NOR-NORI-NORK",
    "tense": "PRES",
    "mood": "IND",
    "abs": "3SG",
    "dat": "3SG",
    "erg": "1SG",
    "polarity": "NEG"
  },
  "naiz": {
    "paradigm": "NOR",
    "tense": "PRES",
    "mood": "IND",
    "abs": "1SG",
    "polarity": "AFF"
  }
}
```

The engine maps the JSON fields to `TokenInfo` tags as follows:

| JSON field | TokenInfo tag | Description |
|-----------|---------------|-------------|
| paradigm | (internal, not emitted) | NOR, NOR-NORK, NOR-NORI, NOR-NORI-NORK |
| tense | tense | PRES, PAST |
| mood | mood | IND, SUBJ, IMP, POT, COND |
| abs | agr_obj | 1SG, 2SG, 3SG, 1PL, 2PL, 3PL |
| erg | agr_subj | 1SG, 2SG, 3SG, 1PL, 2PL, 3PL |
| dat | agr_iobj | 1SG, 2SG, 3SG, 1PL, 2PL, 3PL |
| polarity | polarity | AFF, NEG |
| allocutive | allocutive_gender | MASC, FEM (only for hitano forms) |

### Negation Interaction

Basque negation uses the particle "ez" placed immediately before the auxiliary, with the auxiliary often cliticizing onto it: "ez dut" (I don't have it) can surface as "ez dut" or as the fused form "eztut" in casual writing. Additionally, the negated auxiliary undergoes phonological changes in some dialects. The engine handles this by:

1. Checking for "ez" as a separate preceding token and tagging it as PART with polarity=NEG
2. Checking for "ez+auxiliary" fused forms in the auxiliary lookup table (prefixed entries)
3. Setting polarity=NEG on the auxiliary's tag bundle when negation is detected

### Synthetic Verb Forms

The ~10 synthetic verbs have their own conjugation paradigms where the lexical root and agreement morphology are fused into a single word. For example, "dator" (he/she comes) = synthetic present of etorri, with d- (3SG ABS prefix) + -ator- (root of etorri in synthetic form). These are stored in a separate lookup table `eu_synthetic_verbs.json`, organized by verb lemma:

```json
{
  "etorri": {
    "dator": {"abs": "3SG", "tense": "PRES"},
    "datoz": {"abs": "3PL", "tense": "PRES"},
    "nator": {"abs": "1SG", "tense": "PRES"},
    "zatoz": {"abs": "2SG", "tense": "PRES"},
    "gatoz": {"abs": "1PL", "tense": "PRES"},
    "zetorren": {"abs": "3SG", "tense": "PAST"},
    "zetozen": {"abs": "3PL", "tense": "PAST"}
  },
  "joan": {
    "doa": {"abs": "3SG", "tense": "PRES"},
    "doaz": {"abs": "3PL", "tense": "PRES"},
    "noa": {"abs": "1SG", "tense": "PRES"},
    "zoaz": {"abs": "2SG", "tense": "PRES"},
    "goaz": {"abs": "1PL", "tense": "PRES"},
    "zihoan": {"abs": "3SG", "tense": "PAST"},
    "zihoazen": {"abs": "3PL", "tense": "PAST"}
  },
  "jakin": {
    "daki": {"abs": "3SG", "tense": "PRES"},
    "dakite": {"abs": "3PL", "tense": "PRES"},
    "dakit": {"abs": "3SG", "erg": "1SG", "tense": "PRES"},
    "dakizu": {"abs": "3SG", "erg": "2SG", "tense": "PRES"}
  },
  "egon": {
    "dago": {"abs": "3SG", "tense": "PRES"},
    "daude": {"abs": "3PL", "tense": "PRES"},
    "nago": {"abs": "1SG", "tense": "PRES"},
    "zaude": {"abs": "2SG", "tense": "PRES"},
    "gaude": {"abs": "1PL", "tense": "PRES"},
    "zegoen": {"abs": "3SG", "tense": "PAST"},
    "zeuden": {"abs": "3PL", "tense": "PAST"}
  }
}
```

The POS for synthetic verb forms is set to VERB (not AUX), since they carry both lexical and grammatical content.

### Total Auxiliary/Synthetic Form Count

| Paradigm | Estimated forms | Source |
|----------|----------------|--------|
| NOR (izan) | ~30 | Present + past + hypothetical + imperative |
| NOR-NORK (ukan) | ~130 | ~56 present + ~56 past + ~20 other moods |
| NOR-NORI (izan + dat) | ~50 | Present + past across ABS x DAT combinations |
| NOR-NORI-NORK (ukan + dat) | ~400 | Present + past across ABS x DAT x ERG, minus impossible cells |
| Synthetic verbs (~10 verbs) | ~80 | ~8 forms per verb on average |
| **Total** | **~690** | Stored across eu_auxiliary.json + eu_synthetic_verbs.json |

## Step A: Inflectional Stripping

Step A handles noun declension, verb non-finite forms, and adjective inflection. Auxiliary forms bypass this step entirely (handled by lookup).

### Noun Declension (Izen deklinabidea)

The engine maintains a flattened suffix table combining case, definiteness, and number into single entries. Suffixes are sorted by descending length to ensure the longest (most specific) match is attempted first.

**Stripping procedure:**

1. Build the candidate list from `eu_cases.json`: all suffix entries sorted longest-first
2. For each candidate suffix, check if the word ends with it
3. If a match is found, verify that the remaining stem is at least 2 characters and contains at least one vowel
4. Strip the suffix and assign the case, def, and num tags from the matched entry
5. If no case suffix matches, check for bare definite article: -ak (DEF.PL or ERG.DEF.SG) or -a (DEF.SG ABS)

**Suffix priority table** (sorted by length, longest first):

| Suffix | case | def | num | Length |
|--------|------|-----|-----|--------|
| -etarako | DEST | DEF | PL | 7 |
| -etatik | ABLAT | DEF | PL | 6 |
| -etako | LOC_GEN | DEF | PL | 5 |
| -etara | ALLAT | DEF | PL | 5 |
| -arako | DEST | DEF | SG | 5 |
| -arekin | COM | DEF | SG | 6 |
| -agatik | MOT | DEF | SG | 6 |
| -egatik | MOT | DEF | PL | 6 |
| -atzat | PROL | DEF | SG | 5 |
| -etzat | PROL | DEF | PL | 5 |
| -aren | GEN | DEF | SG | 4 |
| -atik | ABLAT | DEF | SG | 4 |
| -ekin | COM | DEF | PL | 4 |
| -etan | INES | DEF | PL | 4 |
| -ari | DAT | DEF | SG | 3 |
| -ara | ALLAT | DEF | SG | 3 |
| -ako | LOC_GEN | DEF | SG | 3 |
| -an | INES | DEF | SG | 2 |
| -az | INS | DEF | SG | 2 |
| -ei | DAT | DEF | PL | 2 |
| -ek | ERG | DEF | PL | 2 |
| -en | GEN | DEF | PL | 2 |
| -ez | INS | DEF | PL | 2 |
| -ak | ABS/ERG | DEF | PL/SG | 2 |
| -a | ABS | DEF | SG | 1 |

**Indefinite case suffixes** (attached to bare stem without article):

| Suffix | case | def | num |
|--------|------|-----|-----|
| -rako | DEST | INDEF | -- |
| -rekin | COM | INDEF | -- |
| -gatik | MOT | INDEF | -- |
| -ren | GEN | INDEF | -- |
| -tik | ABLAT | INDEF | -- |
| -tzat | PROL | INDEF | -- |
| -rik | PART | INDEF | -- |
| -ra | ALLAT | INDEF | -- |
| -ko | LOC_GEN | INDEF | -- |
| -ri | DAT | INDEF | -- |
| -z | INS | INDEF | -- |
| -n | INES | INDEF | -- |
| -k | ERG | INDEF | -- |

**Stem-final phonological adjustments:** When the stem ends in a vowel and the case suffix begins with a vowel, Basque may insert an epenthetic -r- (e.g., "alaba" + "-en" = "alabaren" with linking -r-). The engine must recognize and strip these epenthetic consonants when they appear between stem and suffix. Rules:

- Epenthetic -r- before -en (GEN), -i (DAT), -ekin (COM): e.g., "alabaren" -> alaba + r(epenth) + en(GEN)
- Epenthetic -t- before -zat (PROL): e.g., "gizontzat" -> gizon + t(epenth) + zat(PROL)
- Epenthetic -e- in plural definite forms: e.g., "gizon" + -ek -> "gizonek" with linking -e-

### Verb Non-Finite Forms (Aditz ez-jokatuak)

Main verbs in periphrastic constructions appear in one of three non-finite forms. The engine strips these suffixes and assigns aspect tags.

**Perfective participle (partizipioa):**

| Suffix | Condition | Example | Tags |
|--------|-----------|---------|------|
| -tu | Default (most verbs) | ikusi -> ikustu? No: ikusi itself | aspect=PERF |
| -du | After nasals/liquids in some verbs | saldu (sold) | aspect=PERF |
| -i | Older verb class | etorri (come), ikasi (learn), ikusi (see) | aspect=PERF |
| -n | Small set | egin (done), joan (gone), edan (drunk) | aspect=PERF |

Note: Many participles are irregular or semi-regular. The engine maintains a lookup list of common participle forms in `eu_verb_forms.json` rather than relying purely on suffix stripping. For unknown verbs, the engine attempts -tu/-du stripping as default.

**Imperfective (burutugabea):**

| Suffix | Condition | Example | Tags |
|--------|-----------|---------|------|
| -tzen | After consonant-final stems | ikusten (seeing) | aspect=IMPERF |
| -ten | After certain stems | jaten (eating) | aspect=IMPERF |
| -tzen | Default | egiten (doing) = egin -> egi + -ten | aspect=IMPERF |

Stripping: remove -tzen or -ten, recover the verbal stem, tag aspect=IMPERF.

**Prospective (gerokoa):**

| Suffix | Condition | Example | Tags |
|--------|-----------|---------|------|
| -ko | After consonant-final stems | ikusiko (will see) | aspect=PROSP |
| -go | After nasal/liquid-final stems | egingo (will do) | aspect=PROSP |

Stripping: remove -ko or -go, recover the verbal stem, tag aspect=PROSP.

**Stem recovery:** After stripping the aspect suffix, the engine stores the recovered stem as the root. For example: "ikusten" -> strip -ten -> "ikus" (root=ikus, aspect=IMPERF). The engine then checks `eu_verb_forms.json` to validate that the recovered stem is a known verbal root.

### Adjective Inflection

Basque adjectives follow the noun and agree in case and number with the noun they modify (when used predicatively or with the article). Adjective inflection is identical to noun declension -- the same case suffix table applies. The engine does not distinguish noun vs. adjective inflection at the morphological level; POS assignment is handled separately based on syntactic position or dictionary lookup.

**Comparative and superlative:**

| Form | Construction | Example | Tags |
|------|-------------|---------|------|
| Comparative | stem + -ago | handiago (bigger, from handi "big") | degree=COMP |
| Superlative | stem + -en | handien (biggest) | degree=SUPER |
| Excessive | stem + -egi | handiegi (too big) | degree=EXCESS |

These degree suffixes are stripped before case suffixes in the stripping order.

## Step B: Derivational Detection

Basque has a productive derivational morphology system with both suffixes and prefixes. Step B identifies one derivational affix per iteration.

### Derivational Suffixes

| Suffix | Category | Meaning | Example | Source -> Target POS |
|--------|----------|---------|---------|---------------------|
| -tasun | Quality (N) | -ness | edertasun (beauty) < eder (beautiful) | ADJ -> NOUN |
| -keria | Pejorative quality | -ness (negative) | alferrkeria (laziness) < alfer (lazy) | ADJ -> NOUN |
| -garri | Worthy/capable | -able/-ible | harrigarri (amazing) < harritu (to amaze) | VERB -> ADJ |
| -ezin | Impossible | un-able | ikusezin (invisible) < ikusi (to see) | VERB -> ADJ |
| -kor | Prone to | -ful/-prone | beldurkor (fearful) < beldur (fear) | NOUN -> ADJ |
| -tsu | Abounding in | -ful/-ous | indartsu (strong) < indar (strength) | NOUN -> ADJ |
| -tzaile | Agent | -er/-ist | irakasle (teacher) < irakatsi (to teach) | VERB -> NOUN |
| -le | Agent (short) | -er | idazle (writer) < idatzi (to write) | VERB -> NOUN |
| -keta | Action/process | -ation | bilaketa (search) < bilatu (to search) | VERB -> NOUN |
| -pen | Result | -ment | sorpen (creation) < sortu (to create) | VERB -> NOUN |
| -kuntza | Process | -ation | hezkuntza (education) < hezi (to educate) | VERB -> NOUN |
| -dura | Result | -ure/-tion | itsaldura (transformation) | VERB -> NOUN |
| -era | Manner | way of | jolasera (way of playing) < jolastu (to play) | VERB -> NOUN |
| -gintza | Activity | -ing (profession) | kazetaritza (journalism) | NOUN -> NOUN |
| -tegi | Place | -ery/-ory | ikastegi (school) < ikasi (to learn) | VERB -> NOUN |
| -denda | Shop | store | okindegi (bakery) < okin (baker) | NOUN -> NOUN |
| -zain | Guardian | keeper | atezain (doorkeeper) < ate (door) | NOUN -> NOUN |
| -gile | Maker | -maker | esnegile (milkman) < esne (milk) | NOUN -> NOUN |
| -ki | Material/manner | -ly | euskalki (dialect) < euskal (Basque) | ADJ -> NOUN/ADV |
| -to | Diminutive | little | txikito (small one) | ADJ -> NOUN |
| -ska/-xka | Diminutive | little | neskatxo? neska + -txo | NOUN -> NOUN |
| -txo | Diminutive | little | neskatxo (little girl) < neska (girl) | NOUN -> NOUN |
| -alde | Side/area | area of | itsasalde (coastal area) < itsaso (sea) | NOUN -> NOUN |
| -eria | Collection | -ery | liburu + tegi? | NOUN -> NOUN |
| -kide | Fellow/co- | co- | lankide (colleague) < lan (work) | NOUN -> NOUN |
| -dun | Possessing | -ful/-ed | dirudun (wealthy) < diru (money) | NOUN -> ADJ |
| -gabe | Lacking | -less | lanik gabe (jobless) < lan (work) | NOUN -> ADJ |
| -zko | Made of | -en/-ish | egurrezko (wooden) < egur (wood) | NOUN -> ADJ |
| -tar | Inhabitant | -an/-ese | bilbotar (Bilbaoan) < Bilbo (Bilbao) | NOUN -> ADJ/NOUN |
| -tu/-du | Verbalization | to make/become | garbitu (to clean) < garbi (clean) | ADJ/NOUN -> VERB |
| -ta | Result state | -ed (stative) | hautsita (broken) < hautsi (to break) | VERB -> ADJ |

### Derivational Prefixes

| Prefix | Meaning | Example | Source -> Target POS |
|--------|---------|---------|---------------------|
| des- | Reversal (borrowed) | desagertu (to disappear) < agertu (to appear) | VERB -> VERB |
| bir- | Repetition | birsortu (to recreate) < sortu (to create) | VERB -> VERB |
| ez- | Negation | ezezagun (unknown) < ezagun (known) | ADJ -> ADJ |
| gain- | Over/super | gainbegiratu (to oversee) < begiratu (to look) | VERB -> VERB |
| berr- | Re-/new | berritu (to renew) < berri (new) | ADJ -> VERB |
| atz- | Back/behind | atzera (back, backward) | ADV -> ADV |
| aurr- | Front/before | aurrera (forward) | ADV -> ADV |

### Conservative Constraints

- Suffix must be at least 2 characters
- Remaining stem must be at least 2 characters
- Remaining stem must contain at least one vowel (Basque stems always contain vowels)
- Prefixes are checked only after suffix stripping has been attempted

**Total derivational rules: ~37** (30 suffixes + 7 prefixes)

Entries are sorted longest-first to prefer the most specific match. The first valid match is accepted, and Step B returns the shortened stem plus a derivation chain entry of the form `"suffix->CATEGORY"`.

## Step C: Root Extraction

Step C performs **iterative deepening** by calling Step B up to 3 times to peel successive derivational layers:

```
root = stem
derived_chain = []
for _ in range(3):
    new_root, deriv_tag = step_b(root)
    if new_root == root:
        break  # no more derivations found
    derived_chain.append(deriv_tag)
    root = new_root
```

This handles multiply-derived forms. For example: "edertasunaren" (of beauty) decomposes as:
1. Step A: strip -aren (GEN.DEF.SG) -> "edertasun"
2. Step C/iteration 1: Step B strips -tasun (quality suffix) -> "eder" (beautiful), chain = ["tasun->QUALITY"]
3. Step C/iteration 2: Step B finds no further derivation on "eder" -> stop

Final result: root="eder", pos=NOUN, tags={case=GEN, def=DEF, num=SG}, derived_chain=["tasun->QUALITY"]

The 3-layer limit prevents runaway stripping on short stems.

## Tag Inventory

### Part of Speech Values

| POS | Description |
|-----|-------------|
| NOUN | Nominal (default when case tag present without verbal tags) |
| VERB | Lexical verb in non-finite form (participle, imperfective, prospective) |
| AUX | Auxiliary verb (izan/ukan paradigms -- carries agreement, not lexical meaning) |
| ADJ | Adjective (from derivation or dictionary) |
| ADV | Adverb (closed-class or derived) |
| PRON | Pronoun (closed-class only) |
| DET | Determiner (closed-class only -- indefinite/quantifier determiners) |
| ADP | Postposition (closed-class only) |
| CONJ | Conjunction (closed-class only) |
| PART | Particle: ez, al, ote, bide, ba- |
| NUM | Numeral |
| UNKNOWN | Unclassified (neither case nor agreement tags found) |

Note: AUX is separated from VERB because auxiliaries carry agreement information but no independent lexical meaning. In the periphrastic construction "ikusi dut" (I have seen it), "ikusi" is VERB and "dut" is AUX.

### Feature Tags

This is the richest tag set of all 9 languages in the experiment, reflecting Basque's extraordinary morphological complexity.

| Tag key | Possible values | Source |
|---------|----------------|--------|
| case | ABS, ERG, DAT, GEN, COM, INS, INES, ALLAT, ABLAT, LOC_GEN, DEST, MOT, PART, PROL | Noun case stripping (Step A) |
| num | SG, PL | Case suffix (fused with definiteness) |
| def | DEF, INDEF | Case suffix (fused with case) |
| person | 1, 2, 3 | Synthetic verb forms |
| formality | FORMAL, INFORMAL | 2SG distinction: zu (formal) vs. hi (informal) |
| agr_subj | 1SG, 2SG, 3SG, 1PL, 2PL, 3PL | Ergative agreement on auxiliary (NORK slot) |
| agr_obj | 1SG, 2SG, 3SG, 1PL, 2PL, 3PL | Absolutive agreement on auxiliary (NOR slot) |
| agr_iobj | 1SG, 2SG, 3SG, 1PL, 2PL, 3PL | Dative agreement on auxiliary (NORI slot) |
| tense | PRES, PAST | Auxiliary tense |
| aspect | PERF, IMPERF, PROSP | Main verb non-finite form |
| mood | IND, SUBJ, IMP, POT, COND | Auxiliary mood |
| polarity | AFF, NEG | Negation particle "ez" interaction |
| degree | COMP, SUPER, EXCESS | Adjective comparison |
| allocutive_gender | MASC, FEM | Hitano addressee gender marking |
| derived_chain | list of strings | Derivational history from Step C |

### Bundle Count

**Estimated: 180-200 unique feature bundles.** This is the HIGHEST count of all 9 languages in the experiment.

Justification by component:

**Nominal bundles:**
- 14 cases x 2 numbers (SG/PL) x 2 definiteness (DEF/INDEF) = 56 maximum
- In practice, some combinations are rare or non-existent (PART has no plural, some indefinite forms are restricted), yielding ~45 observed nominal bundles
- Adjective degree adds 3 more bundles (COMP, SUPER, EXCESS)
- Estimated nominal total: ~48

**Auxiliary bundles (NOR paradigm):**
- 6 ABS persons x 2 tenses x 1 mood = 12 base bundles
- Add hypothetical/imperative: ~8 more
- Estimated NOR total: ~20

**Auxiliary bundles (NOR-NORK paradigm):**
- ~28 valid person combinations x 2 tenses = ~56 base bundles
- Add hypothetical/imperative: ~12 more
- Estimated NOR-NORK total: ~68

**Auxiliary bundles (NOR-NORI paradigm):**
- ~12 valid ABS x DAT combinations x 2 tenses = ~24
- Estimated NOR-NORI total: ~24

**Auxiliary bundles (NOR-NORI-NORK paradigm):**
- Each cell in the paradigm has a unique (ABS, DAT, ERG) triple
- ~25 valid triples per ABS value x 2 ABS values commonly attested x 2 tenses = ~100
- But many of these triples are empirically rare in running text
- Estimated commonly observed NOR-NORI-NORK total: ~40-50 (with long tail of rare forms)

**Verb non-finite bundles:**
- 3 aspects (PERF, IMPERF, PROSP) = 3 bundles

**Total estimated: 48 + 20 + 68 + 24 + 45 + 3 = ~208 theoretical maximum, ~180 commonly observed**

This extreme bundle count is the core reason we predict Basque will show the strongest efficiency gain from morph-aware tokenization. Each morph token carries more grammatical information (more bits per token) than any other language in the experiment. A single Basque auxiliary form encodes what would require 3-4 separate words in English (subject pronoun + auxiliary + object pronoun + indirect object pronoun). The morphological tokenizer captures this density in a single (root, bundle) pair, while a subword tokenizer must split the form into meaningless character sequences.

## Config Files

| File | Entry count | Description |
|------|-------------|-------------|
| `eu_auxiliary.json` | ~600 | All auxiliary forms (izan, ukan) across NOR, NOR-NORK, NOR-NORI, NOR-NORI-NORK paradigms with full agreement decomposition. This is the most critical config file. |
| `eu_synthetic_verbs.json` | ~80 | Synthetic conjugation tables for ~10 verbs (etorri, joan, egon, jakin, ekarri, eraman, ibili, esan, etc.) |
| `eu_cases.json` | ~70 | Case suffix table with all case x definiteness x number combinations, sorted by length |
| `eu_derivations.json` | ~37 | Derivational suffix and prefix rules with source/target POS annotations |
| `eu_verb_forms.json` | ~200 | Known participle/imperfective/prospective forms mapped to verbal roots, handling irregular stems |
| `eu_closed_class.json` | 82 | Closed-class function words with semantic tags |

### eu_auxiliary.json Structure

```json
{
  "dut": {"paradigm": "NOR-NORK", "tense": "PRES", "mood": "IND", "abs": "3SG", "erg": "1SG", "polarity": "AFF"},
  "ditut": {"paradigm": "NOR-NORK", "tense": "PRES", "mood": "IND", "abs": "3PL", "erg": "1SG", "polarity": "AFF"},
  "diet": {"paradigm": "NOR-NORI-NORK", "tense": "PRES", "mood": "IND", "abs": "3PL", "dat": "3PL", "erg": "1SG", "polarity": "AFF"},
  "diot": {"paradigm": "NOR-NORI-NORK", "tense": "PRES", "mood": "IND", "abs": "3SG", "dat": "3SG", "erg": "1SG", "polarity": "AFF"},
  "dio": {"paradigm": "NOR-NORI-NORK", "tense": "PRES", "mood": "IND", "abs": "3SG", "dat": "3SG", "erg": "3SG", "polarity": "AFF"},
  "dizkio": {"paradigm": "NOR-NORI-NORK", "tense": "PRES", "mood": "IND", "abs": "3PL", "dat": "3SG", "erg": "3SG", "polarity": "AFF"},
  "naiz": {"paradigm": "NOR", "tense": "PRES", "mood": "IND", "abs": "1SG", "polarity": "AFF"},
  "da": {"paradigm": "NOR", "tense": "PRES", "mood": "IND", "abs": "3SG", "polarity": "AFF"},
  "dira": {"paradigm": "NOR", "tense": "PRES", "mood": "IND", "abs": "3PL", "polarity": "AFF"},
  "zait": {"paradigm": "NOR-NORI", "tense": "PRES", "mood": "IND", "abs": "3SG", "dat": "1SG", "polarity": "AFF"},
  "zidan": {"paradigm": "NOR-NORI-NORK", "tense": "PAST", "mood": "IND", "abs": "3SG", "dat": "1SG", "erg": "3SG", "polarity": "AFF"},
  "nuen": {"paradigm": "NOR-NORK", "tense": "PAST", "mood": "IND", "abs": "3SG", "erg": "1SG", "polarity": "AFF"},
  "zuen": {"paradigm": "NOR-NORK", "tense": "PAST", "mood": "IND", "abs": "3SG", "erg": "3SG", "polarity": "AFF"},
  "duk": {"paradigm": "NOR-NORK", "tense": "PRES", "mood": "IND", "abs": "3SG", "erg": "2SG", "polarity": "AFF", "formality": "INFORMAL", "allocutive_gender": "MASC"},
  "dun": {"paradigm": "NOR-NORK", "tense": "PRES", "mood": "IND", "abs": "3SG", "erg": "2SG", "polarity": "AFF", "formality": "INFORMAL", "allocutive_gender": "FEM"}
}
```

### eu_cases.json Structure

```json
[
  {"suffix": "etarako", "case": "DEST", "def": "DEF", "num": "PL"},
  {"suffix": "etatik", "case": "ABLAT", "def": "DEF", "num": "PL"},
  {"suffix": "arekin", "case": "COM", "def": "DEF", "num": "SG"},
  {"suffix": "agatik", "case": "MOT", "def": "DEF", "num": "SG"},
  {"suffix": "egatik", "case": "MOT", "def": "DEF", "num": "PL"},
  {"suffix": "etako", "case": "LOC_GEN", "def": "DEF", "num": "PL"},
  {"suffix": "etara", "case": "ALLAT", "def": "DEF", "num": "PL"},
  {"suffix": "arako", "case": "DEST", "def": "DEF", "num": "SG"},
  {"suffix": "aren", "case": "GEN", "def": "DEF", "num": "SG"},
  {"suffix": "atik", "case": "ABLAT", "def": "DEF", "num": "SG"},
  {"suffix": "ekin", "case": "COM", "def": "DEF", "num": "PL"},
  {"suffix": "etan", "case": "INES", "def": "DEF", "num": "PL"},
  {"suffix": "atzat", "case": "PROL", "def": "DEF", "num": "SG"},
  {"suffix": "etzat", "case": "PROL", "def": "DEF", "num": "PL"},
  {"suffix": "ari", "case": "DAT", "def": "DEF", "num": "SG"},
  {"suffix": "ara", "case": "ALLAT", "def": "DEF", "num": "SG"},
  {"suffix": "ako", "case": "LOC_GEN", "def": "DEF", "num": "SG"},
  {"suffix": "an", "case": "INES", "def": "DEF", "num": "SG"},
  {"suffix": "az", "case": "INS", "def": "DEF", "num": "SG"},
  {"suffix": "ei", "case": "DAT", "def": "DEF", "num": "PL"},
  {"suffix": "ek", "case": "ERG", "def": "DEF", "num": "PL"},
  {"suffix": "en", "case": "GEN", "def": "DEF", "num": "PL"},
  {"suffix": "ez", "case": "INS", "def": "DEF", "num": "PL"},
  {"suffix": "ak", "case": "ABS", "def": "DEF", "num": "PL", "ambig": "ERG.DEF.SG"},
  {"suffix": "a", "case": "ABS", "def": "DEF", "num": "SG"}
]
```

## Validators

### Word-level: `check_morph_sequence_eu`

Defined in `shared.py`, this validator enforces Basque-specific morphological well-formedness on each token:

1. **Auxiliary minimum tags:** Any token with pos=AUX must have at least an `agr_obj` tag (NOR slot is always present). If `agr_subj` is present, `agr_obj` must also be present (ERG agreement requires ABS agreement). If `agr_iobj` is present, `agr_obj` must also be present.

2. **Case validity:** For NOUN tokens, the `case` tag must be one of the 14 valid cases: ABS, ERG, DAT, GEN, COM, INS, INES, ALLAT, ABLAT, LOC_GEN, DEST, MOT, PART, PROL.

3. **Auxiliary paradigm consistency:** If an auxiliary has `agr_subj` (ERG agreement), it must be from the NOR-NORK or NOR-NORI-NORK paradigm. If it also has `agr_iobj`, it must be NOR-NORI-NORK. An auxiliary with `agr_iobj` but without `agr_subj` must be NOR-NORI.

4. **Person exclusion:** The `agr_subj` and `agr_obj` tags must not have identical values when that identity is logically impossible (e.g., agr_subj=1SG + agr_obj=1SG is impossible in a standard transitive construction).

5. **Verb aspect requirement:** VERB tokens should have an `aspect` tag (PERF, IMPERF, or PROSP) since lexical verbs in Basque always appear in a non-finite form in periphrastic constructions.

### Sentence-level: `validate_sentence_structure_eu`

Also in `shared.py`, this validator checks sentence-level grammatical constraints reflecting Basque's SOV word order and ergative alignment:

1. **SOV order check:** In a canonical Basque sentence, the finite verb (AUX or synthetic VERB) should appear at or near the end. If content tokens are present and the last content token is a NOUN with no verbal tokens following, the sentence is flagged (warning, not error, since Basque allows some word order flexibility for focus).

2. **Ergative-absolutive agreement:** If an AUX token with `agr_subj` is present, there should be a NOUN in the sentence with `case=ERG`. If an AUX token has `agr_obj` with a non-3rd-person value, there should be a corresponding pronoun or NOUN with `case=ABS`.

3. **Dative agreement:** If an AUX token has `agr_iobj`, there should be a NOUN or PRON with `case=DAT` in the sentence.

4. **Auxiliary-verb pairing:** In periphrastic constructions, an AUX token should be accompanied by a VERB token with an `aspect` tag. An AUX without a corresponding VERB (or synthetic verb without AUX) is flagged as potentially incomplete.

5. **Negation placement:** The negation particle "ez" (pos=PART, polarity=NEG) must immediately precede the auxiliary. If "ez" is found with non-AUX tokens intervening before the next AUX, the structure is flagged.

Content tokens exclude those with POS of UNKNOWN, FOREIGN, or PUNCT.

## Known Limitations

1. **Allocutive (hitano) forms:** Only the most common allocutive forms of the NOR and NOR-NORK paradigms are included in the auxiliary lookup table. The full hitano paradigm across NOR-NORI-NORK creates a 2x combinatorial explosion (~800 additional forms) that is deferred. Allocutive forms are increasingly rare in written Basque and modern speech.

2. **Relative clause verb forms:** Basque relative clauses use a special verb form where the auxiliary takes the suffix -(e)n (e.g., "ikusi duen gizona" = "the man who has seen it", where "duen" = du + -en). These relativized auxiliaries are partially handled by including common -(e)n suffixed forms in the lookup table, but exhaustive coverage is deferred.

3. **Dialectal variation:** Standard Basque (Euskara Batua) is the only variety covered. The historical dialects -- Bizkaiera (Western), Gipuzkera (Central), Lapurtera (Labourdin), Zuberera (Souletin), and Nafarrera (Navarrese) -- have substantially different auxiliary paradigms, particularly in the NOR-NORI-NORK forms. Bizkaiera, for example, uses "deutsut" where Batua uses "dizut." The engine only handles Batua forms.

4. **Ambiguous -ak suffix:** As noted, -ak is ambiguous between ABS.DEF.PL and ERG.DEF.SG. The engine records the primary reading (ABS.DEF.PL) and flags the ambiguity; full disambiguation requires syntactic context.

5. **Noun-verb compounds:** Basque uses many light verb constructions where a noun + egin/eman/hartu forms a compound verb: "lan egin" (work do = to work), "min eman" (pain give = to hurt), "parte hartu" (part take = to participate). These are treated as separate tokens, and the semantic unity of the compound is not captured.

6. **Borrowed vocabulary:** Words borrowed from Spanish (gaztelania) and French (frantsesa) may not follow Basque phonological patterns. For example, Spanish-origin words like "ordenagailua" (computer) contain non-Basque phonotactics. The engine applies standard Basque stripping rules uniformly, which may produce incorrect decompositions for heavily borrowed terms.

7. **Comitative plural ambiguity:** The comitative suffix -ekin (DEF.PL) and the indefinite comitative -rekin can be confused when stem-final -r is present, as -rekin could be analyzed as stem ending in -r + -ekin.

8. **Zero-marked absolutive:** When a noun appears with no case suffix (bare stem or with just the definite article -a), the absolutive case is inferred by absence of marking. This zero morpheme cannot be positively identified -- it is the default reading when no other case suffix matches.

9. **Subordinate clause morphology:** Basque subordinate clauses use special suffixes on the auxiliary (-la for complement clauses, -(e)n for relative clauses, -(e)nean for temporal clauses, -(e)lako for causal clauses). These are partially handled but not exhaustively catalogued.

## Test Plan

| Test category | Test count | Description |
|---------------|-----------|-------------|
| Case stripping (14 cases x DEF/INDEF x SG/PL) | 100 | All case suffix forms: definite singular, definite plural, and indefinite for each of 14 cases. Includes ambiguous -ak tests. |
| NOR auxiliary paradigm (izan) | 30 | Present and past tenses across all 6 persons, plus hypothetical and imperative moods. |
| NOR-NORK auxiliary paradigm (ukan) | 80 | ABS.3SG and ABS.3PL columns fully tested for present and past; ABS.1SG, ABS.2SG columns sampled. |
| NOR-NORI auxiliary paradigm | 30 | ABS.3SG and ABS.3PL across all DAT persons for present and past. |
| NOR-NORI-NORK auxiliary paradigm | 100 | **Critical test set.** All cells of the ABS.3SG present matrix. All cells of the ABS.3PL present matrix. Past tense sampled for high-frequency forms. Verifies the tri-personal agreement decomposition. |
| Synthetic verbs | 20 | Present and past forms of etorri, joan, egon, jakin. |
| Verb non-finite forms | 30 | Participle (-tu/-du/-i), imperfective (-tzen/-ten), prospective (-ko/-go) stripping with stem recovery. |
| Derivation | 25 | Each derivational suffix/prefix tested with a known example. Multi-layer derivation (Step C) tested with 3-deep examples. |
| Closed-class | 25 | All conjunctions, key question words, pronouns, postpositions, particles. Multi-word entries (hala ere, nahiz eta). |
| Adversarial / edge cases | 60 | Ambiguous -ak forms, fused negation (ez+aux), epenthetic consonants, stem-minimum violations, borrowed words, short stems, unknown words. |

**Total: ~500 tests across 10 categories**

This is the largest test suite of all 9 languages, reflecting the complexity of Basque morphology. The NOR-NORI-NORK tests alone (100 tests) exceed the total test count of simpler languages like English or Chinese, because the tri-personal paradigm is the core feature that makes Basque the predicted outlier in the efficiency experiment.
