# German Engine Design Specification

**Language:** German (de)
**Typology:** Irregular fusional
**Engine file:** `scripts/engines/de_engine.py` (to be built)
**Status:** Design phase

---

## Morphological Overview

German (Deutsch) is an irregular fusional language that encodes grammatical relationships through a combination of inflectional suffixes, stem alternations, and function words. Unlike English, which has largely shed its inflectional system, German retains a four-case system (Kasus: Nominativ, Akkusativ, Dativ, Genitiv), three grammatical genders (Genus: Maskulinum, Femininum, Neutrum), and two number categories (Numerus: Singular, Plural). However, unlike more regular fusional languages such as Spanish, German's inflectional paradigms are riddled with irregularities, syncretism, and competing declension classes, making rule-based analysis considerably harder. On the morphological efficiency spectrum in this experiment, German is expected to sit in the mid-range -- more features per word-form than English, but less predictable than Spanish and far less dense than Arabic or Turkish.

The verb system (Konjugation) distinguishes six tense-mood combinations in synthetic (single-word) form: Prasens (present indicative), Prateritum (simple past / Imperfekt), Konjunktiv I (subjunctive of indirect speech), Konjunktiv II (subjunctive of hypothetical/counterfactual), Imperativ (imperative), and two participial forms -- Partizip I (present participle, formed with -end) and Partizip II (past participle, formed with ge-...-t for weak verbs or ge-...-en for strong verbs). Compound tenses (Perfekt, Plusquamperfekt, Futur I/II) are formed analytically with auxiliaries (haben/sein/werden) and are therefore multi-word constructions not analyzed at the single-token level. German verbs fall into three conjugation classes: schwache Verben (weak/regular verbs) that form the Prateritum with a dental suffix -te and the Partizip II with -t (machen - machte - gemacht); starke Verben (strong verbs, roughly 170 in common use) that show Ablaut (stem vowel change) in the Prateritum and Partizip II (singen - sang - gesungen); and gemischte Verben (mixed verbs, roughly 8) that combine stem vowel change with weak endings (kennen - kannte - gekannt).

The nominal system is characterized by the interaction of gender, number, case, and definiteness, but critically, most case-marking in German falls on the article and adjective rather than on the noun itself. Noun inflection is minimal: the genitive singular of masculine and neuter nouns takes -(e)s (des Mannes, des Kindes), the dative plural takes -n (den Kindern), and weak masculine nouns (schwache Maskulina / N-Deklination) take -(e)n in all cases except nominative singular (der Mensch, den/dem/des Menschen). Plural formation is notoriously irregular, with at least five major patterns (-e, -er, -en/-n, -s, zero-plural) often combined with Umlaut (vowel fronting: a>a, o>o, u>u), and the choice of plural marker is not fully predictable from gender or phonology alone (das Wort > die Worter, but das Wort > die Worte with different meaning).

Adjective declension (Adjektivdeklination) is one of the most complex subsystems. German adjectives take different endings depending on three factors: the grammatical case, the gender/number of the noun, and what type of determiner precedes the adjective. This yields three declension paradigms: starke Deklination (strong, when no article precedes: guter Wein, gutes Bier), schwache Deklination (weak, after definite articles: der gute Wein, das gute Bier), and gemischte Deklination (mixed, after indefinite articles: ein guter Wein, ein gutes Bier). The suffixes fuse case, gender, and number into a single morpheme, producing up to 48 cells in the full paradigm (4 cases x 3 genders x 2 numbers x 3 declension types), though extensive syncretism reduces the number of distinct surface forms to roughly a dozen (-er, -e, -es, -en, -em).

Separable verb prefixes (trennbare Vorsilben) are a distinctive feature of German morphology. Prefixes such as ab-, an-, auf-, aus-, bei-, ein-, mit-, nach-, vor-, zu-, and many others attach to verb stems to create new lexemes with modified meaning (machen "to make" > aufmachen "to open", zumachen "to close"). In infinitive and participial forms, the prefix is attached as part of the word (aufmachen, aufgemacht), but in finite main-clause forms, the prefix detaches and moves to the end of the clause ("Ich mache die Tur auf"). Since this engine operates at the word level, prefix detection is limited to non-finite forms where the prefix is orthographically attached. Non-separable prefixes (untrennbare Vorsilben: be-, emp-, ent-, er-, ge-, miss-, ver-, zer-) are always attached and do not separate in any syntactic context.

Compounding (Komposition) is the single most challenging aspect of German morphology for computational analysis. German forms compounds by concatenating nouns, adjectives, verbs, and other word classes into single orthographic units with no spaces or hyphens: Handschuh (Hand + Schuh, "glove"), Krankenhaus (krank + en + Haus, "hospital"), Bundesausbildungsforderungsgesetz (Bund + es + Ausbildung + s + Forderung + s + Gesetz, "Federal Education Assistance Act"). Compounds are right-headed (the last component determines gender, number, and syntactic category), can be recursive (compounds within compounds), and frequently employ linking elements (Fugenelemente: -s-, -n-, -en-, -er-, -e-, -es-) between components. Productive compounding means the set of valid compounds is effectively unbounded, making dictionary-based approaches inherently incomplete. The engine must therefore implement a dynamic compound splitting algorithm.

## Closed-Class Intercept

The engine maintains a static dictionary of closed-class words that are intercepted before Steps A/B/C and bypass all morphological analysis. Each entry maps a lowercased surface form to a `(POS, tags)` tuple.

### Articles (DET) -- 12 entries

**Definite articles (bestimmte Artikel):**
`der` (MASC.NOM), `die` (FEM.NOM/ACC or PL.NOM/ACC), `das` (NEUT.NOM/ACC), `dem` (MASC/NEUT.DAT), `den` (MASC.ACC or PL.DAT), `des` (MASC/NEUT.GEN)

**Indefinite articles (unbestimmte Artikel):**
`ein` (MASC.NOM / NEUT.NOM/ACC), `eine` (FEM.NOM/ACC), `einem` (MASC/NEUT.DAT), `einen` (MASC.ACC), `einer` (FEM.DAT/GEN), `eines` (MASC/NEUT.GEN)

Note: Articles are heavily syncretic. `der` is simultaneously masculine nominative singular, feminine dative singular, feminine genitive singular, and genitive plural. Context-free analysis cannot disambiguate; the engine stores the most common reading and tags `ambig=YES` on multiply-assignable forms.

### Prepositions (ADP) -- 36 entries

**Accusative prepositions:** `bis` (until), `durch` (through), `fur` (for), `gegen` (against), `ohne` (without), `um` (around)

**Dative prepositions:** `aus` (out of), `bei` (at/near), `mit` (with), `nach` (after/to), `seit` (since), `von` (from/of), `zu` (to), `ausser` / `außer` (except), `gegenuber` / `gegenüber` (opposite)

**Two-way prepositions (Wechselprapositionen, ACC or DAT):** `an` (at/on), `auf` (on/upon), `hinter` (behind), `in` (in), `neben` (next to), `uber` / `über` (over/above), `unter` (under/among), `vor` (before/in front of), `zwischen` (between)

**Genitive prepositions:** `wahrend` / `während` (during), `wegen` (because of), `trotz` (despite), `statt` (instead of), `gemass` / `gemäß` (according to), `laut` (according to), `mangels` (for lack of), `mittels` (by means of), `samt` (together with), `entlang` (along)

### Pronouns (PRON) -- 72 entries

**Personal pronouns (Personalpronomen), all cases:**
NOM: `ich`, `du`, `er`, `sie`, `es`, `wir`, `ihr`, `Sie` (formal)
ACC: `mich`, `dich`, `ihn`, `sie`, `es`, `uns`, `euch`, `Sie`
DAT: `mir`, `dir`, `ihm`, `ihr`, `uns`, `euch`, `ihnen`, `Ihnen`
Reflexive: `sich` (3rd person / formal reflexive, ACC/DAT)

**Possessive pronouns (Possessivpronomen), base forms:**
`mein`, `dein`, `sein`, `ihr`, `unser`, `euer`
Each has inflected forms following the mixed declension pattern (mein-e, mein-em, mein-en, mein-er, mein-es). The base forms are intercepted; inflected forms are handled by adjective declension stripping with a special possessive tag.

**Interrogative pronouns:** `wer` (who, NOM), `wen` (who, ACC), `wem` (who, DAT), `wessen` (whose, GEN), `was` (what), `welch` (which, base form)

**Demonstrative pronouns:** `dieser`, `diese`, `dieses`, `jener`, `jene`, `jenes`

**Indefinite pronouns:** `man` (one/generic), `jeder`, `jede`, `jedes` (every), `alle` (all), `manche` (some), `einige` (some), `kein`, `keine` (none/no), `etwas` (something), `nichts` (nothing), `jemand` (somebody), `niemand` (nobody)

### Conjunctions (CONJ) -- 32 entries

**Coordinating (nebenordnende Konjunktionen):** `und` (and), `oder` (or), `aber` (but), `sondern` (but rather), `denn` (because/for), `doch` (yet/however), `jedoch` (however)

**Subordinating (unterordnende Konjunktionen):** `weil` (because), `dass` (that), `wenn` (if/when), `als` (when/as, past), `ob` (whether), `obwohl` (although), `damit` (so that), `bevor` (before), `nachdem` (after), `wahrend` / `während` (while), `seit` / `seitdem` (since), `bis` (until), `falls` (in case), `indem` (by/while), `sobald` (as soon as), `solange` (as long as)

**Correlative pairs (stored as individual tokens):** `weder` (neither), `noch` (nor), `entweder` (either), `sowohl` (both), `zwar` (indeed)

Note: `während`, `seit`, and `bis` are listed under both prepositions and conjunctions. The engine stores the preposition entry with priority; the conjunction reading is tagged as `ambig_conj=YES`.

### Modal Verbs (AUX) -- 36 entries (6 verbs x 6 conjugated Prasens forms)

Base forms: `konnen` / `können` (can), `mussen` / `müssen` (must), `durfen` / `dürfen` (may), `sollen` (shall), `wollen` (want to), `mogen` / `mögen` (to like)

Prasens conjugations stored explicitly because modals have irregular present-tense stems (Praeteritopraesentia):
- konnen: `kann`, `kannst`, `kann`, `konnen`, `konnt`, `konnen`
- mussen: `muss`, `musst`, `muss`, `mussen`, `musst`, `mussen`
- durfen: `darf`, `darfst`, `darf`, `durfen`, `durft`, `durfen`
- sollen: `soll`, `sollst`, `soll`, `sollen`, `sollt`, `sollen`
- wollen: `will`, `willst`, `will`, `wollen`, `wollt`, `wollen`
- mogen: `mag`, `magst`, `mag`, `mogen`, `mogt`, `mogen`

All tagged with `modal=YES`.

### Auxiliary Verbs (AUX) -- 30 entries (3 verbs, all Prasens + Prateritum forms)

**haben (to have):** `habe`, `hast`, `hat`, `haben`, `habt`, `hatte`, `hattest`, `hatten`, `hattet`
**sein (to be):** `bin`, `bist`, `ist`, `sind`, `seid`, `war`, `warst`, `waren`, `wart`, `gewesen`
**werden (to become / future/passive auxiliary):** `werde`, `wirst`, `wird`, `werden`, `werdet`, `wurde`, `wurdest`, `wurden`, `wurdet`

All tagged with `aux=YES` and their respective `tense` and `person` features.

### Particles and Adverbs (PART) -- 20 entries

**Particles:** `nicht` (not), `ja` (yes/indeed), `nein` (no), `schon` (already/indeed), `mal` (once/just), `denn` (then, modal particle), `halt` (just, modal particle), `eben` (just/exactly), `wohl` (probably), `doch` (indeed/after all)

**Fixed adverbs:** `hier` (here), `dort` (there), `heute` (today), `gestern` (yesterday), `morgen` (tomorrow), `immer` (always), `nie` / `niemals` (never), `sehr` (very), `auch` (also), `nur` (only)

### Total Closed-Class Count

**Estimated total: ~238 entries** across articles (12), prepositions (36), pronouns (72), conjunctions (32), modal verbs (36), auxiliary verbs (30), and particles/adverbs (20).

## Step A: Inflectional Stripping

Step A takes a single word, lowercases it, and attempts to identify its inflectional morphology, returning a tuple of `(stem, tags_dict, pos)`. Rules are checked in strict priority order; the first match wins.

### 1. Closed-Class Lookup

If the lowercased word is in `CLOSED_CLASS`, return immediately with the pre-assigned POS and tags. No further processing.

### 2. Irregular Form Lookup

If the word appears as a key in `de_irregulars.json` (~200 entries), read the entry's `base`, `pos`, and `tag` fields. This handles:
- Strong verb Prateritum stems: `sang` -> base=`singen`, pos=`VERB`, tags=`{tense: PAST}`
- Strong verb Partizip II: `gesungen` -> base=`singen`, pos=`VERB`, tags=`{aspect: PERF}`
- Irregular Prasens forms: `isst` -> base=`essen`, pos=`VERB`, tags=`{tense: PRES, person: 3, num: SG}`
- Irregular noun plurals: `Manner` / `Männer` -> base=`Mann`, pos=`NOUN`, tags=`{num: PL}`
- Suppletive comparatives: `besser` -> base=`gut`, pos=`ADJ`, tags=`{degree: COMP}`

### 3. Partizip II Detection (ge-...-t / ge-...-en)

**Pattern A (weak):** word starts with `ge-` and ends with `-t`, length > 5.
Action: strip `ge-` prefix and `-t` suffix. Example: `gemacht` -> `mach`.
Tags: `{aspect: PERF}`, POS = `VERB`.

**Pattern B (strong):** word starts with `ge-` and ends with `-en`, length > 6.
Action: strip `ge-` prefix and `-en` suffix. Example: `geschrieben` -> `schrieb` (then check irregulars for root `schreiben`).
Tags: `{aspect: PERF}`, POS = `VERB`.

**Pattern C (separable prefix + ge-):** word starts with a known separable prefix followed by `ge-` and ends with `-t` or `-en`.
Action: strip the prefix, `ge-`, and the ending. Tag the prefix. Example: `aufgemacht` -> prefix=`auf`, stem=`mach`.
Tags: `{aspect: PERF, verb_prefix: AUF}`, POS = `VERB`.

**Pattern D (non-separable prefix, no ge-):** verbs with non-separable prefixes (be-, emp-, ent-, er-, ge-, miss-, ver-, zer-) do NOT take ge- in Partizip II. These are handled through `de_irregulars.json` or by recognizing the non-separable prefix + -t/-en pattern.
Example: `besucht` -> prefix=`be`, stem=`such`, tags=`{aspect: PERF}`.

### 4. Partizip I Detection (-end)

Pattern: word ends with `-end`, length > 5.
Action: strip `-end`, append `-en` to reconstruct infinitive. Example: `laufend` -> `laufen`.
Tags: `{aspect: PROG}`, POS = `VERB`.
Note: Some adjectives are frozen Partizip I forms (dringend, bedeutend); these are handled via `de_irregulars.json`.

### 5. Verb Conjugation Stripping

German verb conjugation suffixes in Prasens (present indicative):

| Person | Weak suffix | Example (machen) |
|--------|-------------|-------------------|
| ich (1SG) | -e | mache |
| du (2SG) | -st | machst |
| er/sie/es (3SG) | -t | macht |
| wir (1PL) | -en | machen |
| ihr (2PL) | -t | macht |
| sie/Sie (3PL) | -en | machen |

Stripping order (longest suffix first): `-est` (2SG Prateritum), `-est` (archaic 2SG), `-et` (3SG/2PL with stem-final -d/-t), `-st` (2SG), `-en` (1PL/3PL/infinitive), `-te` (1SG/3SG Prateritum weak), `-t` (3SG/2PL), `-e` (1SG).

**Prateritum (simple past) for weak verbs:**
Insert `-te-` before person endings: `machte`, `machtest`, `machten`, `machtet`.
Pattern: if after stripping person ending the stem ends in `-te`, strip it and tag `{tense: PAST}`.

**Prateritum for strong verbs:** handled via `de_irregulars.json` because the stem vowel changes are unpredictable (Ablaut: singen/sang, sprechen/sprach, nehmen/nahm).

**Konjunktiv I:**
Formed from Prasens stem + subjunctive endings (-e, -est, -e, -en, -et, -en).
Pattern: identical to Prasens for many forms; disambiguation requires context. Engine tags ambiguous forms with `mood_ambig=IND_SUBJ_I`.

**Konjunktiv II:**
For weak verbs: identical to Prateritum (machte = both past indicative and Konj. II). Tagged `mood_ambig=PAST_SUBJ_II`.
For strong verbs: Prateritum stem + Umlaut + subjunctive endings (sang -> sange, kam -> kame). Handled via `de_irregulars.json`.

**Imperative:**
2SG: stem (+ optional -e): `mach!` / `mache!`
2PL: stem + -t: `macht!`
Formal: infinitive + Sie: `machen Sie!` (multi-word, not handled at word level)
Tags: `{mood: IMP}`.

### Verb Conjugation: Suffix Priority Table

| Priority | Suffix | Person | Number | Tense | Conditions |
|----------|--------|--------|--------|-------|------------|
| 1 | -test | 2 | SG | PAST | After -te- (weak Prateritum) |
| 2 | -tet | 2 | PL | PAST | After -te- (weak Prateritum) |
| 3 | -ten | 1/3 | PL | PAST | After -te- (weak Prateritum) |
| 4 | -te | 1/3 | SG | PAST | Weak Prateritum |
| 5 | -est | 2 | SG | PRES | Stem ends in -d/-t/-chn/-ffn |
| 6 | -et | 3/2 | SG/PL | PRES | Stem ends in -d/-t/-chn/-ffn |
| 7 | -st | 2 | SG | PRES | General |
| 8 | -en | 1/3 | PL | PRES | Also infinitive form |
| 9 | -t | 3/2 | SG/PL | PRES | General |
| 10 | -e | 1 | SG | PRES | General |

### Separable Verb Prefixes

The engine maintains a list of known separable prefixes:

**Separable (trennbar):** `ab`, `an`, `auf`, `aus`, `bei`, `dar`, `ein`, `empor`, `fest`, `fort`, `her`, `hin`, `los`, `mit`, `nach`, `nieder`, `um` (when separable), `vor`, `weg`, `weiter`, `wider` (when separable), `zu`, `zuruck` / `zurück`, `zusammen`

**Non-separable (untrennbar):** `be`, `emp`, `ent`, `er`, `ge`, `miss`, `ver`, `zer`

**Ambiguous (separable or non-separable depending on meaning):** `durch`, `hinter`, `uber` / `über`, `um`, `unter`, `wider`, `wieder`

At word level, prefix detection applies to:
1. **Infinitives:** `aufmachen` -> prefix=`auf`, base=`machen`. Tag: `{verb_prefix: AUF}`.
2. **Partizip II:** `aufgemacht` -> handled in Partizip II detection above.
3. **Partizip I:** `aufmachend` -> prefix=`auf`, base=`machend`.
4. **zu-Infinitiv:** `aufzumachen` -> prefix=`auf`, infix=`zu`, base=`machen`. Tag: `{verb_prefix: AUF, infinitive_marker: ZU}`.

In conjugated main-clause forms, the prefix is syntactically separated ("Ich mache auf") and therefore not detectable at the word level. This is a known limitation.

### Noun Declension

German noun inflection is minimal compared to article/adjective inflection. The engine strips the following:

**Genitive -s/-es (masculine and neuter nouns):**
Pattern: word ends with `-es` or `-s` and context (or dictionary lookup) suggests genitive.
Example: `Mannes` -> `Mann`, tags=`{case: GEN, num: SG}`.
Guard: minimum length 4 to avoid stripping short words.

**Dative plural -n:**
Pattern: word ends with `-n` and the un-suffixed form is a known plural.
Example: `Kindern` -> `Kinder` (already plural), tags=`{case: DAT, num: PL}`.

**Weak masculine -n/-en (N-Deklination):**
Pattern: word ends with `-en` or `-n`, noun is in the weak masculine list.
Example: `Menschen` -> `Mensch`, tags=`{case: ACC/DAT/GEN, num: SG}` or `{num: PL}` (ambiguous).
A set of ~80 common weak masculine nouns is stored in `de_irregulars.json`.

**Plural formation (5+ patterns):**

| Pattern | Example | Umlaut? |
|---------|---------|---------|
| -e | Tag -> Tage | sometimes (Gast -> Gaste) |
| -er | Kind -> Kinder | sometimes (Mann -> Manner) |
| -en / -n | Frau -> Frauen, Blume -> Blumen | never |
| -s | Auto -> Autos, Kino -> Kinos | never |
| zero | Lehrer -> Lehrer, Fenster -> Fenster | sometimes (Mutter -> Mutter) |

Plural stripping attempts to reverse these patterns. The engine tries each in order:
1. If word ends in `-er` and un-umlauted stem + `-er` removal yields a known singular: strip.
2. If word ends in `-en`/`-n`: strip and check.
3. If word ends in `-e`: strip and check (also try un-umlauting).
4. If word ends in `-s`: strip and check.
5. If word contains Umlaut: try un-umlauting without suffix removal (zero-plural with Umlaut).

Tags: `{num: PL}`, POS = `NOUN`. If Umlaut was reversed, add `umlaut: YES`.

### Adjective Declension

Adjective endings fuse case, gender, and number. The engine strips adjective suffixes and tags the features:

**Strong declension (starke Deklination, no preceding article):**

| | Masc | Fem | Neut | Plural |
|------|------|-----|------|--------|
| NOM | -er | -e | -es | -e |
| ACC | -en | -e | -es | -e |
| DAT | -em | -er | -em | -en |
| GEN | -en | -er | -en | -er |

**Weak declension (schwache Deklination, after definite article):**

| | Masc | Fem | Neut | Plural |
|------|------|-----|------|--------|
| NOM | -e | -e | -e | -en |
| ACC | -en | -e | -e | -en |
| DAT | -en | -en | -en | -en |
| GEN | -en | -en | -en | -en |

**Mixed declension (gemischte Deklination, after indefinite article):**

| | Masc | Fem | Neut | Plural |
|------|------|-----|------|--------|
| NOM | -er | -e | -es | -en |
| ACC | -en | -e | -es | -en |
| DAT | -en | -en | -en | -en |
| GEN | -en | -en | -en | -en |

Since the engine operates at the word level without article context, it cannot determine which declension paradigm is active. Strategy:
1. Strip the suffix (-er, -e, -es, -en, -em).
2. Check if the resulting stem is a known adjective (from `de_stems.json`).
3. Tag all possible feature readings as an ambiguity set: e.g., `-er` -> `{case: NOM, gender: MASC, declension: STRONG}` OR `{case: DAT, gender: FEM, declension: STRONG}` OR `{case: GEN, gender: FEM/PL, declension: STRONG}`.
4. Store the primary (most frequent) reading and tag `adj_ambig=YES` when multiple readings exist.

**Comparative and superlative:**
Comparative: stem + `-er` + declension ending. Example: `schoner` / `schönerer` (more beautiful, strong MASC.NOM).
Superlative: stem + `-st-` / `-est-` + declension ending, or `am` + stem + `-sten`. Example: `schonsten` / `am schönsten`.

Strip order: superlative (-st-/-est-) before comparative (-er-), then declension ending.
Tags: `{degree: COMP}` or `{degree: SUPER}`.

Umlaut in comparative/superlative: many common adjectives take Umlaut (alt -> alter -> altest, gross -> grosser -> grosst, jung -> junger, kurz -> kurzer, lang -> langer). Handled via `de_irregulars.json` for irregular forms and a heuristic un-umlaut check for productive forms.

### Umlaut Handling

Umlaut (a -> a, o -> o, u -> u, au -> au) is a morphophonological process that accompanies several inflectional and derivational operations:

1. **Noun plurals:** Mutter -> Mutter, Vater -> Vater, Haus -> Hauser, Gast -> Gaste
2. **Konjunktiv II:** ware (< war), hatte (< hatte), konnte (< konnte), musste (< musste)
3. **Comparative/superlative:** alt -> alter -> altest, gross -> grosser
4. **Derivation:** lang -> Lange, stark -> Starke

**Implementation strategy:** When stripping a suffix, the engine also attempts to un-umlaut the stem vowel (a -> a, o -> o, u -> u, au -> au). If the un-umlauted form is found in the known stems dictionary or irregulars file, the un-umlauted form is used as the root and `umlaut=YES` is added to the tags. The un-umlaut check proceeds right-to-left through the stem, targeting the last umlautable vowel (since German Umlaut typically affects the stem vowel closest to the triggering suffix).

Note on encoding: The engine accepts both Unicode Umlaut characters (a, o, u) and ASCII-digraph representations (ae, oe, ue). Normalization to Unicode form is performed at input.

## Compound Splitting

This is the most computationally demanding component of the German engine.

### The Problem

German compounds are written as single orthographic words with no internal spacing or hyphenation. Compounds can be:
- **Binary:** Handschuh (Hand + Schuh, "glove"), Haustier (Haus + Tier, "pet")
- **Recursive:** Handschuhmacher (Hand + Schuh + Macher, "glove maker")
- **Very long:** Donaudampfschifffahrtsgesellschaftskapitan (Donau + Dampf + Schiff + Fahrt + s + Gesellschaft + s + Kapitan, 6 components)

### Linking Elements (Fugenelemente)

Between compound components, German inserts linking elements that are orthographically fused:

| Fugenelement | Example | Components |
|--------------|---------|------------|
| -s- | Arbeit**s**platz | Arbeit + Platz |
| -es- | Freund**es**kreis | Freund + Kreis |
| -n- | Blume**n**laden | Blume + Laden |
| -en- | Kirche**n**steuer | Kirche + Steuer |
| -er- | Kind**er**garten | Kind + Garten |
| -e- | Hund**e**hutte / Hundehütte | Hund + Hutte |
| zero | Haustier | Haus + Tier |

The linking element is NOT a morpheme (it carries no meaning) but must be accounted for during splitting.

### Splitting Algorithm

```
function split_compound(word, stems_dict, max_depth=3):
    if len(word) < 6: return [word]  # too short to be a compound
    if word in stems_dict: return [word]  # known simplex word

    candidates = []
    for split_pos in range(3, len(word) - 2):  # min 3 chars per component
        left = word[:split_pos]
        remainder = word[split_pos:]

        # Try each Fugenelement
        for fuge in ["", "s", "es", "n", "en", "er", "e"]:
            if remainder.startswith(fuge):
                right = remainder[len(fuge):]
                if len(right) < 3: continue

                if left in stems_dict:
                    # Recursively try to split the right component
                    right_parts = split_compound(right, stems_dict, max_depth - 1)
                    if all(part in stems_dict for part in right_parts):
                        score = sum(len(p) for p in [left] + right_parts)
                        candidates.append({
                            "parts": [left] + right_parts,
                            "fugen": fuge,
                            "score": score
                        })

    if not candidates: return [word]  # no valid split found
    # Prefer fewest components, then longest left component
    best = max(candidates, key=lambda c: (
        -len(c["parts"]),  # fewer parts preferred
        len(c["parts"][0])  # longer first component preferred
    ))
    return best["parts"]
```

### Configuration

**de_stems.json:** A dictionary of ~8,000 common German word stems organized by POS. Structure:

```json
{
  "nouns": {
    "Haus": {"gender": "NEUT", "freq_rank": 142},
    "Mann": {"gender": "MASC", "freq_rank": 87},
    "Frau": {"gender": "FEM", "freq_rank": 63}
  },
  "verbs": {
    "mach": {"infinitive": "machen", "freq_rank": 45},
    "geh": {"infinitive": "gehen", "freq_rank": 28}
  },
  "adjectives": {
    "gut": {"freq_rank": 31},
    "gross": {"freq_rank": 112}
  }
}
```

Frequency rank is used for disambiguation: when multiple valid splits exist, prefer the split whose components have lower (more common) frequency ranks.

### Compound Output

When a compound is successfully split, the engine records:
- `compound_parts`: list of component stems, e.g., `["Hand", "Schuh"]`
- `compound_head`: the rightmost component (determines gender and POS), e.g., `"Schuh"`
- `compound_fugen`: linking elements used, e.g., `[""]`
- The root is set to the head component's stem.
- POS is determined by the head component.
- Gender is determined by the head component (for nouns).

A chain entry `COMPOUND(Hand+Schuh)` is added to `derived_chain`.

### Guards and Heuristics

1. **Minimum component length:** 3 characters. Prevents splitting "Eis" (ice) as "E" + "is".
2. **Maximum recursion depth:** 3 levels. Prevents runaway splitting on long words.
3. **Known simplex guard:** If the whole word is in `de_stems.json` as a simplex entry, do not split. Prevents "Butter" from being split as "Butt" + "er".
4. **Frequency guard:** Only accept splits where all components have frequency rank <= 10,000 (i.e., are reasonably common words). Prevents splitting into obscure stems.

## Step B: Derivational Detection

Step B identifies one layer of derivational morphology on the stem produced by Step A. It returns the stripped stem and a derivation chain. Step B only runs when Step A assigned POS = `UNKNOWN`.

### Derivational Suffixes (~30 rules)

| Suffix | Input POS | Output POS | Semantic Type | Example |
|--------|-----------|------------|---------------|---------|
| -ung | VERB | NOUN (FEM) | ACTION_NOUN | Bildung < bilden |
| -heit | ADJ | NOUN (FEM) | QUALITY_NOUN | Freiheit < frei |
| -keit | ADJ | NOUN (FEM) | QUALITY_NOUN | Moglichkeit < moglich |
| -igkeit | ADJ | NOUN (FEM) | QUALITY_NOUN | Geschwindigkeit < geschwind |
| -nis | VERB/ADJ | NOUN (NEUT/FEM) | RESULT_NOUN | Ergebnis < ergeben |
| -schaft | NOUN | NOUN (FEM) | COLLECTIVE | Freundschaft < Freund |
| -tum | NOUN/ADJ | NOUN (NEUT) | STATE_DOMAIN | Eigentum < eigen |
| -lich | NOUN/ADJ | ADJ | RESEMBLANCE | freundlich < Freund |
| -isch | NOUN | ADJ | RELATING_TO | kindisch < Kind |
| -ig | NOUN | ADJ | HAVING_QUALITY | sonnig < Sonne |
| -bar | VERB | ADJ | ABILITY | machbar < machen |
| -sam | VERB/ADJ | ADJ | TENDENCY | langsam < lang |
| -haft | NOUN | ADJ | HAVING_QUALITY | fehlerhaft < Fehler |
| -los | NOUN | ADJ | WITHOUT | arbeitslos < Arbeit |
| -voll | NOUN | ADJ | FULL_OF | wertvoll < Wert |
| -reich | NOUN | ADJ | RICH_IN | erfolgreich < Erfolg |
| -arm | NOUN | ADJ | LOW_IN | fettarm < Fett |
| -er | VERB | NOUN (MASC) | AGENT | Lehrer < lehren |
| -in | NOUN (MASC) | NOUN (FEM) | FEMININE_AGENT | Lehrerin < Lehrer |
| -erin | VERB | NOUN (FEM) | FEMININE_AGENT | Lehrerin < lehren |
| -ler | NOUN | NOUN (MASC) | AGENT | Kunstler < Kunst |
| -ner | NOUN | NOUN (MASC) | AGENT | Redner < Rede |
| -chen | NOUN | NOUN (NEUT) | DIMINUTIVE | Madchen < Magd |
| -lein | NOUN | NOUN (NEUT) | DIMINUTIVE | Buchlein < Buch |
| -ling | ADJ/VERB | NOUN (MASC) | PERSON | Lehrling < lehren |
| -sel | VERB | NOUN (NEUT) | RESULT | Ratsel < raten |
| -e | ADJ | NOUN (FEM) | QUALITY_ABSTRACT | Starke < stark |
| -ieren | NOUN (foreign) | VERB | VERBALIZE | studieren < Studium |
| -isieren | NOUN/ADJ | VERB | VERBALIZE | modernisieren < modern |

### Derivational Prefixes (~20 rules)

| Prefix | Input POS | Output POS | Semantic Type | Example |
|--------|-----------|------------|---------------|---------|
| un- | ADJ | ADJ | NEGATION | unmoglich < moglich |
| un- | NOUN | NOUN | NEGATION | Ungluck < Gluck |
| ur- | NOUN/ADJ | NOUN/ADJ | ORIGINAL | uralt < alt |
| miss- | VERB/NOUN | VERB/NOUN | WRONG/BAD | Misserfolg < Erfolg |
| Ge- | VERB | NOUN (NEUT) | COLLECTIVE/ITERATIVE | Gerede < reden |
| Haupt- | NOUN | NOUN | MAIN | Hauptstadt < Stadt |
| Grund- | NOUN | NOUN | BASIC | Grundschule < Schule |
| Neben- | NOUN | NOUN | SECONDARY | Nebenstrasse < Strasse |
| Vor- | NOUN | NOUN | PRE/FORMER | Vorstadt < Stadt |
| Nach- | NOUN | NOUN | POST/SUCCESSOR | Nachfolger < Folger |
| Uber- | ADJ | ADJ | EXCESSIVE | ubergross < gross |
| Unter- | ADJ/NOUN | ADJ/NOUN | SUB | Untergruppe < Gruppe |
| Ruck- | NOUN/VERB | NOUN/VERB | BACK/RETURN | Ruckfahrt < Fahrt |
| Mit- | NOUN | NOUN | CO- | Mitarbeiter < Arbeiter |
| Anti- | NOUN/ADJ | NOUN/ADJ | AGAINST | Antiheld < Held |
| Nicht- | NOUN | NOUN | NON- | Nichtraucher < Raucher |

### Suffix/Prefix Interaction with Umlaut

Several derivational processes trigger Umlaut on the base stem:
- -chen/-lein (diminutive): Buch -> Buchlein, Haus -> Hauschen
- -lich: Tag -> taglich
- -in (sometimes): Arzt -> Arztin
- Ge- (collective): sprechen -> Gesprach

When stripping these suffixes/prefixes, the engine applies the un-umlaut heuristic to recover the base form.

**Total derivational rules: ~50** (30 suffixes + 20 prefixes), stored in `de_derivations.json`.

## Step C: Root Extraction

Step C performs iterative deepening by re-applying Step B and compound splitting up to 4 additional times. This handles multi-layered derivations and compounds-within-derivations.

**Order of operations per iteration:**
1. Attempt derivational stripping (Step B).
2. If no derivation was found, attempt compound splitting.
3. If a compound was split, apply Step B to each component individually.

**Maximum iterations:** 4.
**Stopping condition:** No further stripping or splitting is possible.

**Example of multi-layer analysis:**

`Unfreundlichkeit` (unkindness):
1. Suffix `-keit` -> `Unfreundlich`, chain: `["keit->QUALITY_NOUN"]`
2. Suffix `-lich` -> `Unfreund`, chain: `["keit->QUALITY_NOUN", "lich->RESEMBLANCE"]`
3. Prefix `Un-` -> `Freund`, chain: `["keit->QUALITY_NOUN", "lich->RESEMBLANCE", "un->NEGATION"]`
4. Root: `Freund` (friend). Total depth: 3.

`Krankenhausalltag` (hospital everyday life):
1. Compound split: `Krankenhaus` + `Alltag`
2. `Krankenhaus`: compound split `Kranken` + `Haus`. `Kranken` <- `krank` (sick) + -en (Fugenelement/weak adj form).
3. `Alltag`: compound split `All` + `Tag`.
4. Head: `Tag`, root: `Tag`.

## Tag Inventory

### Part of Speech Values

| POS Value | Description |
|-----------|-------------|
| `NOUN` | Common noun (includes all case/number/gender forms) |
| `VERB` | Verb (includes all conjugated, participial, and infinitive forms) |
| `ADJ` | Adjective (includes all declension forms, comparatives, superlatives) |
| `ADV` | Adverb |
| `PRON` | Pronoun (personal, possessive, interrogative, demonstrative, indefinite) |
| `DET` | Determiner / Article (der, die, das, ein, eine, etc.) |
| `ADP` | Adposition / Preposition |
| `CONJ` | Conjunction (coordinating and subordinating) |
| `PART` | Particle (negation, modal particles, focus particles) |
| `AUX` | Auxiliary and modal verb |
| `NUM` | Numeral |
| `UNKNOWN` | No inflectional pattern matched; word passed to Steps B/C |

### Feature Tags

| Tag Key | Possible Values | Producing Step | Description |
|---------|----------------|----------------|-------------|
| `num` | `SG`, `PL` | Step A | Grammatical number |
| `gender` | `MASC`, `FEM`, `NEUT` | Step A, Closed-class | Grammatical gender |
| `case` | `NOM`, `ACC`, `DAT`, `GEN` | Step A, Closed-class | Grammatical case |
| `person` | `1`, `2`, `3` | Step A | Person agreement (verbs) |
| `tense` | `PRES`, `PAST` | Step A | Tense (synthetic forms only) |
| `mood` | `IND`, `SUBJ_I`, `SUBJ_II`, `IMP` | Step A | Mood of verb |
| `aspect` | `PERF`, `PROG` | Step A | Aspect (Partizip II = PERF, Partizip I = PROG) |
| `voice` | `ACT`, `PASS` | Step A | Voice (passive only with werden auxiliary, multi-word) |
| `degree` | `POS`, `COMP`, `SUPER` | Step A | Degree of adjective/adverb |
| `verb_prefix` | `AB`, `AN`, `AUF`, `AUS`, `BEI`, `EIN`, `MIT`, `NACH`, `VOR`, `ZU`, `ZURUCK`, `ZUSAMMEN`, etc. | Step A | Separable verb prefix |
| `declension` | `STRONG`, `WEAK`, `MIXED` | Step A | Adjective declension type (when determinable) |
| `modal` | `YES` | Closed-class | Word is a modal verb |
| `aux` | `YES` | Closed-class | Word is an auxiliary verb |
| `umlaut` | `YES` | Step A | Umlaut was reversed during stem recovery |
| `compound_parts` | list of strings | Compound splitting | Components of a compound word |
| `compound_head` | string | Compound splitting | Head (rightmost) component of compound |
| `ambig` | `YES` | Various | Form is ambiguous between multiple readings |
| `adj_ambig` | `YES` | Step A | Adjective ending is ambiguous across paradigms |
| `mood_ambig` | `IND_SUBJ_I`, `PAST_SUBJ_II` | Step A | Mood is ambiguous |
| `ambig_conj` | `YES` | Closed-class | Word is ambiguous between preposition and conjunction |
| `infinitive_marker` | `ZU` | Step A | zu-Infinitiv detected |

### Bundle Count

**Estimated: 60-80 unique feature bundles.** Justification:

1. **Noun bundles:** `num` x `gender` x `case` = 2 x 3 x 4 = 24 theoretical cells, but heavy syncretism reduces this. With `umlaut` and `compound_parts` variants, estimate ~20 observed bundles.
2. **Verb bundles:** `tense` (2) x `person` (3) x `num` (2) = 12 for indicative, plus `mood` variants (SUBJ_I, SUBJ_II, IMP) adding ~8, plus `aspect` (PERF, PROG) adding ~4, plus `verb_prefix` combinations adding ~6. Estimate ~25-30 bundles.
3. **Adjective bundles:** `degree` (3) x `case` (4) x `gender` (3) x `declension` (3) = 108 theoretical, but massive syncretism and ambiguity tags collapse this. Estimate ~10-15 observed bundles.
4. **Closed-class bundles:** `no_features`, `modal=YES`, `aux=YES`, `ambig=YES`, etc. Estimate ~5 bundles.
5. **UNKNOWN:** `no_features` -- 1 bundle.

Total estimated range: **60-80 bundles**, placing German between English (~15-25) and Arabic (~80+) / Turkish (~50+). German has fewer verb tense-aspect combinations than Spanish but compensates with case x gender x number interactions in the nominal domain.

## Config Files

| File | Entries | Structure | Purpose |
|------|---------|-----------|---------|
| `de_irregulars.json` | ~200 | `Dict[surface_form, {base, pos, tag}]` -- tag is pipe-delimited `key=value` pairs | Strong verb stems (~170: Prateritum, Partizip II, irregular Prasens 2SG/3SG), mixed verbs (~8), fully irregular verbs (sein, haben, werden, tun, gehen, stehen, wissen), irregular noun plurals (~20), suppletive adjective comparatives (gut/besser/best, viel/mehr/meist, gern/lieber/liebst) |
| `de_stems.json` | ~8,000 | `Dict[pos_category, Dict[stem, {metadata}]]` | Known German word stems for compound splitting and adjective/noun recognition. Organized by POS (nouns with gender, verbs with infinitive, adjectives). Frequency rank included for disambiguation. |
| `de_derivations.json` | ~50 rules | `List[{affix, surface_variants[], type, direction, derives, notes, examples}]` | Derivational affixes (~30 suffixes, ~20 prefixes) with surface variants, directionality, semantic type, and examples. Same schema as `en_derivations.json`. |

### de_irregulars.json Structure

```json
{
  "sang": {"base": "singen", "pos": "VERB", "tag": "tense=PAST|person=1|num=SG"},
  "gesungen": {"base": "singen", "pos": "VERB", "tag": "aspect=PERF"},
  "isst": {"base": "essen", "pos": "VERB", "tag": "tense=PRES|person=3|num=SG"},
  "ging": {"base": "gehen", "pos": "VERB", "tag": "tense=PAST|person=1|num=SG"},
  "gegangen": {"base": "gehen", "pos": "VERB", "tag": "aspect=PERF"},
  "Manner": {"base": "Mann", "pos": "NOUN", "tag": "num=PL|umlaut=YES"},
  "Hauser": {"base": "Haus", "pos": "NOUN", "tag": "num=PL|umlaut=YES"},
  "besser": {"base": "gut", "pos": "ADJ", "tag": "degree=COMP"},
  "beste": {"base": "gut", "pos": "ADJ", "tag": "degree=SUPER"},
  "war": {"base": "sein", "pos": "VERB", "tag": "tense=PAST|person=1|num=SG"},
  "ware": {"base": "sein", "pos": "VERB", "tag": "mood=SUBJ_II|person=1|num=SG"},
  "gewesen": {"base": "sein", "pos": "VERB", "tag": "aspect=PERF"}
}
```

Each strong verb requires approximately 4-6 entries (Prateritum 1SG/3SG stem, Prateritum 2SG, Partizip II, and irregular Prasens 2SG/3SG if applicable). The ~170 strong verbs thus produce approximately 170-200 entries in the irregulars file.

## Validators

### Word-level: `check_morph_sequence_de`

Validates that each token's tag bundle is internally consistent for its POS.

| POS | Required Tags | Allowed Tags |
|-----|---------------|--------------|
| `NOUN` | `num` | `num`, `gender`, `case`, `umlaut`, `compound_parts`, `compound_head` |
| `VERB` | `tense` or `aspect` or `mood` | `tense`, `aspect`, `person`, `num`, `mood`, `voice`, `verb_prefix`, `infinitive_marker`, `mood_ambig` |
| `ADJ` | (none required) | `degree`, `case`, `gender`, `num`, `declension`, `adj_ambig`, `umlaut` |
| `ADV` | (none required) | `degree` |

Additional constraints:
- If `mood=IMP`, then `person` must be `2` or absent, and `tense` must be `PRES` or absent.
- If `aspect=PERF`, then `tense` must be absent (Partizip II is non-finite).
- If `aspect=PROG`, then `tense` must be absent (Partizip I is non-finite).
- `case` on a NOUN without `num` is invalid.
- `verb_prefix` must be from the known separable prefix set.

Returns `True` if all tokens pass validation, `False` on the first violation.

### Sentence-level: `validate_sentence_structure_de`

Validates cross-token structural constraints for German sentence structure.

1. **V2 rule (main clause):** In declarative main clauses, the finite verb should be the second constituent. The engine checks: if the sentence does not begin with a subordinating conjunction, and contains a VERB with `tense` set, that verb should appear in position 1 or 2 among content tokens (excluding particles). Violation message: `"V2 violation: finite verb not in second position: {surface}"`.

2. **Verb-final rule (subordinate clause):** If the sentence begins with a subordinating conjunction (dass, weil, wenn, als, ob, obwohl, damit, bevor, nachdem, etc.), the finite verb should be the last content token. Violation message: `"verb-final violation in subordinate clause: {surface}"`.

3. **Case governance:** Prepositions tagged with required case (accusative, dative, genitive) should be followed by nominals in the matching case. Since case is often ambiguous at the word level, this check is advisory (logged as warning, not hard failure).

4. **Degree tag restriction:** `degree=COMP` or `degree=SUPER` must only appear on tokens with POS = `ADJ` or `ADV`. Violation message: `"degree tag on non-ADJ/ADV: {surface}"`.

5. **Imperative person restriction:** If `mood=IMP`, `person` must be `2` or absent. Violation message: `"imperative with non-2nd person: {surface}"`.

Returns a `(bool, str)` tuple: `(True, "ok")` on success, or `(False, error_message)` on failure.

## Known Limitations

1. **Compound splitting accuracy depends on dictionary coverage.** The `de_stems.json` dictionary covers approximately 8,000 stems, which handles the most common compounds but will miss rare or neologistic formations. Productive compounding means the set of valid compounds is unbounded; no fixed dictionary can achieve complete coverage.

2. **Case marking is largely on articles, not nouns.** Since the engine operates at the word level without cross-token context, it cannot determine case from article agreement. Noun case is only detectable in genitive -s/-es forms and N-Deklination nouns. For all other cases, the engine assigns case only when unambiguous.

3. **Adjective declension requires preceding article context.** Without knowing whether a definite article, indefinite article, or no article precedes the adjective, the engine cannot determine which declension paradigm is active. It tags the most common reading and marks ambiguity.

4. **Separable verb prefix detection only works on non-finite forms.** In conjugated main-clause forms, the prefix separates from the verb and moves to clause-final position ("Ich mache die Tur auf"). The engine cannot detect this separation at the word level; it only recognizes prefixes on infinitives (aufmachen), Partizip II forms (aufgemacht), and Partizip I forms (aufmachend).

5. **Konjunktiv I/II ambiguity.** Many Konjunktiv I forms are identical to Prasens indicative (except for 3SG: er mache vs. er macht). Many weak verb Konjunktiv II forms are identical to Prateritum indicative (er machte = both). The engine tags these ambiguities but cannot resolve them without syntactic context.

6. **No handling of Swiss German (Schweizerdeutsch) or Austrian German (Osterreichisches Deutsch).** The engine targets Standard German (Hochdeutsch) only. Swiss German does not use Prateritum forms, Austrian German has different auxiliary selection patterns (bin gestanden vs. habe gestanden), and both have vocabulary differences.

7. **Genitive -s may conflict with plural -s.** Foreign-origin nouns (Auto, Kino, Taxi) form plurals with -s (Autos), which looks identical to the genitive -s suffix. The engine requires dictionary lookup to disambiguate.

8. **Compound splitting can produce false positives.** Some words that look like compounds are in fact simplex: "Butter" should not be split as "Butt" + "er", "Muster" should not be split as "Mus" + "ter". The known-simplex guard mitigates this but requires comprehensive dictionary entries.

9. **No handling of nominalized adjectives/verbs.** German freely nominalizes adjectives (das Gute, "the good thing") and infinitives (das Laufen, "the running"). These appear as capitalized words with adjectival/verbal morphology, creating POS ambiguity the engine cannot fully resolve.

10. **Reflexive verb constructions are multi-word.** Verbs like sich freuen, sich erinnern require the reflexive pronoun sich, which is a separate token. The engine cannot identify these as reflexive constructions at the word level.

11. **Derivational analysis only runs on UNKNOWN words.** If Step A incorrectly assigns a POS via inflectional stripping (e.g., stripping -er from "Lehrer" as comparative instead of agent suffix), derivational morphology is never examined. The priority ordering of rules mitigates but does not eliminate this risk.

## Test Plan

| Category | Test Count | Description |
|----------|-----------|-------------|
| Strong verb conjugation | 100 | Ablaut patterns across all ~170 strong verbs; Prasens, Prateritum, Partizip II forms; stem vowel changes (e/i, e/a/o, ie/o/o, ei/ie/ie, etc.) |
| Weak verb conjugation | 50 | Regular -te Prateritum, -t Partizip II, all person/number forms; stems ending in -d/-t/-chn/-ffn requiring -e- insertion |
| Separable verbs | 40 | Prefix detection on infinitives, Partizip II (prefix+ge+stem+t/en), zu-Infinitiv (prefix+zu+stem+en); all major separable prefixes |
| Noun plurals + Umlaut | 60 | All 5 plural patterns with and without Umlaut; zero-plurals; N-Deklination weak masculines; genitive -s/-es; dative plural -n |
| Adjective declension | 40 | All 3 paradigms (strong/weak/mixed) across case/gender/number; comparative/superlative with declension endings; Umlaut in comparatives |
| Compound splitting | 80 | Binary compounds, recursive compounds (3+ parts), all Fugenelemente (-s-/-es-/-n-/-en-/-er-/-e-/zero), false positive prevention (Butter, Muster), known simplex guard |
| Derivation | 40 | All 30 suffix rules and 20 prefix rules; multi-layer stripping (Unfreundlichkeit); Umlaut interaction with derivation |
| Closed-class | 30 | All articles, pronouns, prepositions, conjunctions, modals, auxiliaries; ambiguous forms (wahrend as PREP vs. CONJ) |
| Adversarial | 50 | Short words that should not be stripped; words resembling compounds but simplex; Umlaut false positives; mixed-case input; empty/whitespace input; non-German input |

**Total: ~490 tests across 9 categories.**

Test files will follow the naming convention `test_de_engine_{category}.py` in `morph_efficiency_project/tests/de_morph/`.
