# Arabic Engine Design Specification

**Language:** Arabic (ar)  
**Typology:** Templatic (root-and-pattern) -- morphological outlier  
**Engine file:** `scripts/engines/ar_engine.py`  
**Status:** Built, audited, tested (Phase 0 complete)

---

## Morphological Overview

Arabic morphology (علم الصرف / `ilm al-sarf`) is grounded in a root-and-pattern (الجذر والوزن / al-jadhr wa-l-wazn) system that is fundamentally non-concatenative. Unlike agglutinative languages such as Turkish, where morphemes stack linearly as prefixes and suffixes, Arabic interleaves discontinuous morphemes: a consonantal root (typically three consonants, called a triliteral or trilateral root) is interspersed with a vocalic template (وزن / wazn) that determines grammatical category, voice, aspect, and semantic nuance. For example, the root ك-ت-ب (k-t-b, "writing") combines with the pattern فَعَلَ (fa`ala) to yield كَتَبَ (kataba, "he wrote"), with فَاعِل (fa`il) to yield كَاتِب (kaatib, "writer"), and with مَفْعُول (maf`uul) to yield مَكْتُوب (maktuub, "written/letter").

The verb system is organized around numbered forms (الأوزان / al-awzaan), conventionally labeled I through XV, though Forms XI--XV are extremely rare in Modern Standard Arabic (MSA). Form I (فَعَلَ) is the base trilateral verb, with six sub-paradigms distinguished by the vowel on the imperfect stem (I-a/u, I-a/i, I-a/a, I-i/a, I-u/u, I-i/i). Augmented forms (Forms II--X) modify the base through consonant gemination (Form II فَعَّلَ), long-vowel insertion (Form III فَاعَلَ), prefix addition (Form IV أَفْعَلَ, Form VII اِنْفَعَلَ, Form X اِسْتَفْعَلَ), infix insertion (Form VIII اِفْتَعَلَ), combined modifications (Form V تَفَعَّلَ, Form VI تَفَاعَلَ), or gemination of the final radical (Form IX اِفْعَلَّ for color/defect verbs). Each form carries a characteristic semantic shift: causative (II, IV), reciprocal (III, VI), reflexive (V, VII), and requestative (X).

The nominal system is equally rich. Active participles (اسم الفاعل / ism al-fa`il) follow the pattern فَاعِل for Form I and مُفَعِّل/مُفَاعِل/etc. for augmented forms. Passive participles (اسم المفعول / ism al-maf`uul) follow مَفْعُول for Form I and مُفَعَّل/مُفَاعَل for augmented forms. Verbal nouns (المصدر / al-masdar) are highly irregular for Form I (with patterns like فَعْل, فِعَال, فُعُول, فَعَلَان) but predictable for augmented forms (تَفْعِيل for Form II, مُفَاعَلَة for Form III, إِفْعَال for Form IV, etc.). Broken plurals (جمع التكسير / jam` al-taksir) -- internal plurals formed by rearranging the vocalic template rather than adding a suffix -- are a hallmark feature: كِتَاب (kitaab, "book") becomes كُتُب (kutub, "books"), not *كِتَابَات.

Arabic also employs a productive clitic system. Proclitics include the conjunctions وَ (wa, "and") and فَ (fa, "and/so"), the prepositions بِ (bi, "with/by"), لِ (li, "for/to"), and كَ (ka, "like/as"), the definite article الـ (al), the future marker سَـ (sa), the emphatic lam لَـ (la), and the interrogative hamza أَ (a). These can stack: وَبِالـ (wa-bi-al, "and with the") is a single orthographic word containing three proclitics. Enclitics include a full paradigm of object/possessive pronoun suffixes for all persons, numbers, and genders (ـهُ, ـهَا, ـهُمْ, ـكَ, ـكِ, ـنَا, ـنِي, etc.), as well as dual noun markers, feminine plural markers, sound masculine plural markers, and the energetic nun (نون التوكيد: ـنَّ heavy, ـنْ light).

The combination of proclitics + verb prefix + stem + enclitics creates a circumstance where a single orthographic token can encode what other languages express in an entire clause. The circumfix لَـ...ـنَّ (lam al-tawkid + nun al-tawkid) brackets a verb to express sworn assertion: لَيَكْتُبَنَّ (la-yaktubanna, "he will most certainly write, I swear"). This discontinuous morpheme -- where the meaning arises only from the co-occurrence of both halves -- makes Arabic a morphological outlier among the world's languages.

Arabic's non-concatenative morphology means that standard finite-state approaches designed for concatenative or agglutinative languages (prefix + stem + suffix) fail to capture the interleaving of root consonants and pattern vowels. The engine described here addresses this by separating the analysis into three stages: clitic stripping (Step A, which IS concatenative), template matching (Step B, the non-concatenative core), and root extraction (Step C, which resolves weak-root alternations). This architecture mirrors the traditional Arabic grammatical distinction between النحو (al-nahw, syntax/inflection) and الصرف (al-sarf, morphology/derivation).

## Closed-Class Intercept

The engine intercepts 172 closed-class entries before Steps A/B/C. These are function words that are not derived from productive roots and would be incorrectly analyzed if sent through the template-matching pipeline. All entries are tagged with `pos=PART` (except كان وأخواتها which receive `pos=VERB`).

### Categories

**Prepositions (حروف الجر) -- subcat=PREP:**  
في / فِي (fi, "in/at"), من / مِن / مِنْ (min, "from"), إلى / إِلَى (ila, "to"), على / عَلَى (`ala, "on"), عن / عَن / عَنْ (`an, "about"), مع / مَعَ (ma`a, "with"), حتى / حَتَّى (hatta, "until"), منذ / مُنْذُ (mundhu, "since"), خلال (khilal, "during"), بين / بَيْنَ (bayna, "between"), فوق (fawqa, "above"), تحت (tahta, "under"), أمام (amama, "in front of"), وراء (wara'a, "behind"), بعد / بَعْدَ (ba`da, "after"), قبل / قَبْلَ (qabla, "before"), عند / عِنْدَ (`inda, "at/with"), لدى / لَدَى (lada, "with/at"), حول (hawla, "around"), ضد (didda, "against"), رغم (raghma, "despite"), نحو (nahwa, "toward").

**Conjunctions (حروف العطف والربط) -- subcat=CONJ:**  
أو / أَوْ (aw, "or"), أم / أَمْ (am, "or in questions"), لكن / لَكِن / لكنّ (lakin/lakinna, "but"), بل / بَلْ (bal, "rather"), ثم / ثُمَّ (thumma, "then"), إذ (idh, "since"), إذا / إِذَا (idha, "if/when"), لو / لَوْ (law, "if, counterfactual"), كي / كَيْ (kay, "so that"), حين / حِينَ (hina, "when"), عندما (`indama, "when"), بينما (baynama, "while"), لأن / لأنّ / لأنه / لأنها (li'anna, "because"), كلما (kullama, "whenever"), مما (mimma, "from what").

**Complementizers/Subordinators (إنّ وأخواتها) -- subcat=COMP:**  
أن / أَنْ (an, "that, before verb"), أنّ (anna, "that, before noun"), إن / إِنْ (in, "if, conditional"), إنّ (inna, "indeed/verily"), كأن / كأنّ (ka'anna, "as if"), ليت (layta, "would that"), لعل / لَعَلَّ (la`alla, "perhaps").

**Interrogatives (أدوات الاستفهام) -- subcat=INTERROG:**  
هل / هَلْ (hal, "yes/no question marker"), ما / مَا (ma, "what"), ماذا (madha, "what, object"), من (man, "who"), كيف / كَيْفَ (kayfa, "how"), لماذا (limadha, "why"), متى (mata, "when"), أين / أَيْنَ (ayna, "where"), كم / كَمْ (kam, "how many"), أيّ (ayy, "which"). Note: من is ambiguous between the preposition "from" and the interrogative "who"; the engine stores both entries, with context-dependent disambiguation left to downstream processing.

**Negation particles (أدوات النفي) -- subcat=NEG:**  
لا / لَا (la, "no/not"), لم / لَمْ (lam, "did not, jussive"), لن / لَنْ (lan, "will not, future"), ليس / لَيْسَ (laysa, "is not, copular"), غير (ghayr, "non-/un-, nominal negation").

**Discourse/focus particles (أدوات الخطاب) -- subcat=DISC:**  
قد / قَدْ (qad, "already/perhaps"), إلا / إِلَّا (illa, "except"), فقط (faqat, "only"), أيضا / أَيْضًا (aydan, "also"), جدا / جِدًّا (jiddan, "very"), ربما (rubbama, "perhaps"), حقا (haqqan, "truly"), إذن / إِذَنْ (idhan, "therefore"), هنا (huna, "here"), هناك / هُنَاكَ (hunaka, "there"), الآن (al-ana, "now"), دائما (da'iman, "always"), أحيانا (ahyanan, "sometimes"), أبدا (abadan, "never").

**Vocatives (أدوات النداء) -- subcat=VOC:**  
يا / يَا (ya, "O!"), أيا (aya, poetic/distant), هيا (hayya, "come on!"), آ (a, archaic), أي (ay, archaic/poetic), اللهم / اللّهم (allahumma, "O God!", frozen form: يا + الله + compensatory mim).

**Interjections (أسماء الأفعال) -- subcat=INTERJ:**  
هيهات / هَيْهَاتَ (hayhata, "far be it!"), آمين / أمين (amin, "amen"), آه (ah, "ah!"), أوه (awh, "oh!"), أف / أُفٍّ (uff, "ugh!"), صه / صهٍ (sah, "silence!"), مه (mah, "stop!"), إيه (ih, "go on!"), بخ / بخٍ (bakh, "bravo!"), وا (wa, "alas!"), واه (wah, "oh!"), شتان / شَتَّانَ (shattana, "how different!"), سرعان (sur`ana, "how quickly!"), وشكان (washkana, "how soon!").

**Oaths (أحرف القسم) -- subcat=OATH:**  
والله (wallahi, "by God!"), تالله (tallahi, "by God!, archaic"), بالله (billahi, "by God!").

**Response particles -- subcat=RESP:**  
نعم / نَعَمْ (na`am, "yes"), بلى / بَلَى (bala, "yes, contradicting a negative"), أجل (ajal, "yes/indeed"), كلا / كَلَّا (kalla, "no!/certainly not").

**Counterfactual conditionals -- subcat=COND:**  
لولا / لَوْلَا (lawla, "if it were not for"), لوما / لَوْمَا (lawma, rare variant of لولا).

**كان وأخواتها (ما-negated forms) -- subcat=KANA, pos=VERB:**  
مازال / مَازَالَ (mazala, "still is"), مادام / مَادَامَ (madama, "as long as"), مابرح / مَابَرِحَ (ma bariha, "has not ceased"), مافتئ / مَافَتِئَ (ma fati'a, "has not ceased"), ماانفك / مَاانْفَكَّ / ماانفكّ (ma infakka, "has not ceased").

**Total: 172 entries** across 12 subcategories.

### False-Positive Guards

Words like لولا, لوما, مازال, and مادام superficially resemble proclitic-plus-root combinations (e.g., لولا could be misanalyzed as لِ + ولا or لَ + ولا). The closed-class intercept runs BEFORE clitic stripping, so these frozen forms are tagged as atomic units and never enter the stripping pipeline. Similarly, oaths (والله, تالله, بالله) are intercepted whole rather than being decomposed into conjunctive/prepositional proclitic + الله.

## Loanword Intercept

The engine maintains a `LOANWORDS` set of 77 foreign-origin words adopted into Arabic that should not be analyzed through the root-and-pattern pipeline. When a word matches (checked against both the raw surface and diacritic-stripped form), the engine returns `pos=NOM`, `template=LOANWORD`, `tags={"origin": "FOREIGN"}`, with the diacritic-stripped surface as the root.

The loanwords span several semantic domains:
- **Technology:** تلفزيون (tilifziyun, "television"), كمبيوتر (kumbyutar, "computer"), إنترنت (internet), راديو (radio), كاميرا (camera)
- **Politics/Society:** ديمقراطية (dimuqratiyya, "democracy"), برلمان (barlamaan, "parliament"), دبلوماسية (diblumaasiyya, "diplomacy")
- **Finance:** بنك (bank), شيك (check), بورصة (bursa, "stock exchange")
- **Culture/Daily life:** فيلم (film), بيتزا (pizza), جينز (jeans)
- **Transportation:** تاكسي (taxi), ميترو (metro), باص (bus)
- **Science:** أوكسجين (uksijin, "oxygen"), فيزياء (fizya', "physics")

Variant spellings are included (e.g., both كمبيوتر and كومبيوتر, both ديموقراطية and ديمقراطية).

## Step A: Clitic Stripping

### Proclitics

Proclitics are stripped in a **while-loop architecture**: after each successful strip, the loop restarts from the beginning of the proclitic list, allowing stacked proclitics to be peeled off one at a time. The list is ordered **longest-first** to prevent partial matches (e.g., وَبِالـ is checked before وَ alone).

**Compound clusters (3+ morphemes):**
- وَبِالـ / فَبِالـ (conj + prep + def): "and with the" / "so with the"
- وَلِلـ / فَلِلـ (conj + prep + def): "and for the" / "so for the"
- وَالـ / فَالـ (conj + def): "and the" / "so the"
- وال / فال (undiacritical variants)

**Two-morpheme clusters (prep + def):**
- بِالـ / بِال / بال (prep B + def): "with the"
- لِلـ / لِل / لل (prep L + def): "for the"
- كَالـ / كَال / كال (prep K + def): "like the"

**Definite article alone:**
- الـ / ال (def): "the"

**Single proclitics (diacritical):**
- وَ (conj W, "and"), فَ (conj F, "and/so")
- بِ (prep B, "with/by"), لِ (prep L, "for/to"), كَ (prep K, "like/as")
- سَ (tense_prefix FUT, "will")
- لَ (emph LAM, emphasis/oath lam)

**Single proclitics (undiacritical):**
- و, ف, ب, ل, ك, س (same semantics as diacritical, for unvoweled corpus text)

**Interrogative hamza prefix:**
- أَ (interrog Q): e.g., أَكَتَبْتَ؟ ("did you write?")

#### Consonant-Count Guards

Single-character proclitics are protected by consonant-count guards that prevent the engine from consuming a root-initial consonant:

- **Conjunction proclitics** (وَ, فَ, و, ف): require **3 consonants** remaining after stripping. These are unambiguous conjunctions -- they never function as root-initial consonants with a following cluster in MSA.
- **Preposition/tense proclitics** (بِ, لِ, كَ, سَ, أَ, ب, ل, ك, س): require **4 consonants** remaining. These can be root-initial (سَفِينَة root سفن, كَتَبَ root كتب), so the stricter guard prevents false positives.
- **Undiacritical diacritic check**: for undiacritical single-char proclitics (و, ف, ب, ل, ك, س), if the character is immediately followed by a diacritic (haraka), it is treated as a root consonant with a vowel, not a bare proclitic. Example: كِتَابِي (kasra after ك) -- ك is NOT stripped.

#### The `al_stripped` Flag

Once the definite article ال has been stripped (alone or as part of a compound cluster like بال), no further single-char proclitic stripping is permitted in that pass. This prevents the engine from eating the first root consonant of the now-exposed stem. Example: الكتاب -- strip ال to get كتاب, then the ك must NOT be stripped as a ك-proclitic.

#### Form VIII Guard

Before stripping ال as a definite article, the engine checks whether the word matches the Form VIII pattern (اِفْتَعَلَ). In unvoweled text, اِلْتَقَى and الْتَقَى are byte-identical. The guard detects the Form VIII signature: starts with ا, consonant at position 1 (not ا/و/ي), ت at position 2, followed by 2+ consonants. When this pattern matches, the ا is treated as the Form VIII prosthetic hamza, not the definite article.

#### Imperfect Verb Prefix Stripping

After clitic stripping, the engine attempts to strip the imperfect (مضارع) prefix يَ/ي (3rd person masculine singular marker). This is an inflectional prefix, not a proclitic, but is stripped at this stage for template matching. The diacritical form يَ requires 3 consonants remaining; the bare form ي also requires 3 consonants. Prefixes تَ/أَ/نَ are NOT stripped due to high ambiguity with root-initial consonants.

### Enclitics

Enclitics are stripped in a **single-match-only design**: only one enclitic is stripped per word, because MSA does not stack enclitics (unlike proclitics).

**3rd person pronouns:**  
هُمَا (3DU), هِمَا (3DU, gen), هُنَّ (3FPL), هِنَّ (3FPL, gen), هُمْ / هُم (3MPL), هِمْ (3MPL, gen), هَا (3FSG), هُ (3MSG), هِ (3MSG, gen)

**1st person pronouns:**  
نَا (1PL), نِي (1SG), يَ / ي (1SG, after long vowel)

**2nd person pronouns:**  
كُمَا (2DU), كُمْ / كُم (2MPL), كُنَّ (2FPL), كَ (2MSG), كِ (2FSG)

**Dual noun endings:**  
انِ / ان (DU, NOM), يْنِ / ين (DU, OBL/acc-gen)

**Feminine plural endings:**  
اتِ (PL, F, OBL), اتٌ (PL, F, NOM), ات (undiacritical)

**2nd person verb agreement suffixes:**  
تُمَا (2, DU, M), تُمْ / تُم (2, PL, M), تُنَّ (2, PL, F)

**Energetic nun (نون التوكيد):**  
نَّ (NUN_THAQILA, heavy), نْ (NUN_KHAFIFA, light)

**Sound masculine plural markers:**  
ُون (PL, M, NOM), ِين (PL, M, OBL), ون / ين (undiacritical)

#### Enclitic Consonant-Count Guards

- **ي / يَ (1SG possessive):** requires 5+ consonants in the full stem before stripping, preventing root-final ي from being consumed (e.g., يَرْمِي root رمي has 4 consonants -- REJECT strip).
- **كَ / كِ (2MSG/2FSG):** requires 4 consonants remaining after stripping, since كَ can be a root consonant (e.g., شَارَكَ root شرك).
- **ون / ين (masculine plural):** requires 3 consonants remaining to avoid eating root consonants from short words (e.g., عُيُون -- strip ون would leave عي with 2 consonants -- REJECT).
- **نِي / نِ (1SG):** requires 3 consonants remaining (e.g., يَبْنِي -- strip نِي would leave يب with 1 consonant -- REJECT).
- **ه (3MSG, undiacritical):** requires 3 chars remaining.

### Circumfix Detection

After all clitic stripping is complete, the engine checks for the circumfix لَـ...ـنَّ/ـنْ (لام التوكيد + نون التوكيد). This is a discontinuous morpheme (الإحاطة / الاكتناف) that brackets the verb to express sworn assertion. Detection logic:

1. Check if any proclitic tag has `emph=LAM`
2. Check if any enclitic tag has `emph=NUN_THAQILA` or `emph=NUN_KHAFIFA`
3. If both are present, set `circumfix=LAM_NUN` and `assertion=SWORN`, and remove the independent `emph` tags (they are subsumed by the circumfix).

Example: لَيَكْتُبَنَّ (la-yaktubanna) -- after stripping, the verb receives `circumfix=LAM_NUN, assertion=SWORN`.

## Step B: Template Matching

### Consonant Extraction

The engine extracts consonants from the stripped stem via `_extract_consonants()`, which:
1. Strips Arabic diacritics (harakat, U+064B--U+065F and U+0670 superscript alif)
2. Strips ta marbuta (ة U+0629) -- a grammatical feminine suffix, never a root consonant
3. Normalizes all hamza variants (أ, إ, آ, ؤ, ئ) to bare ء
4. Filters to retain only characters in the `AR_CONSONANTS` set (30 base consonants + 6 hamza/alif variants)

A separate `_extract_root_consonants()` additionally strips internal alif (ا) -- which is almost always a long-vowel marker in unvoweled text -- while preserving initial and final alif. This gives the "true root-consonant count" needed for template index lookup.

### Template Index Organization

The template index is built once at initialization from `ar_templates.json` (348 templates). Templates are grouped by the number of **root-slot consonants** (ف/ع/ل positions in the وزن), not the total consonant count. This correctly groups مَفْعُول (3 root slots, not 5 total consonants) with trilateral stems. The index is a dict mapping root-slot count to a list of template entries.

### Nisba Adjective Detection

Before template lookup, the engine checks for the nisba suffix ـيّ (ya + shadda). If found, it is stripped and the word is immediately classified as `NISBA` with `pos=ADJ, role=NISBA`. Examples: عَرَبِيّ (arabiyy, "Arab/Arabic"), مِصْرِيّ (misriyy, "Egyptian").

### Pre-Index Prefix Checks

The engine runs rule-based checks for augmented forms with clear prefix markers BEFORE consulting the template index, to avoid the index returning a generic match that would suppress the prefix skip:

**Derived nominals (مُ-prefix):**
- مُسْت- prefix: Form X active participle (مُسْتَفْعِل) -- returns `NOM_DERIVED_X`
- مُ- prefix: generic derived nominal (Form II/III/IV active participle, or مَفْعُول passive participle) -- returns `NOM_DERIVED`
- مَ- prefix + 4+ consonants: مَفْعُول passive participle or place noun -- returns `NOM_DERIVED`
- Unvoweled م-initial + 4+ consonants: treated as `NOM_DERIVED` (cannot distinguish vowel pattern without diacritics)

### Verb Forms Handled

| Form | Pattern | Category | Detection Method |
|------|---------|----------|------------------|
| I | فَعَلَ (6 paradigms) | `VERB_TRILATERAL_BARE` | Template index (n=3) |
| II | فَعَّلَ | `VERB_FORM_II` | Shadda on 2nd consonant |
| III | فَاعَلَ | `VERB_FORM_III` | Known lookup set (21 verbs) + diacritic check (fatha on C2) |
| IV | أَفْعَلَ | `VERB_AUGMENTED_IV` | أ prefix + 4 consonants |
| V | تَفَعَّلَ | `VERB_AUGMENTED_V_VI` | ت prefix + 4 consonants (no internal ا) |
| VI | تَفَاعَلَ | `VERB_AUGMENTED_V_VI` | ت prefix + 5 consonants (root_consonants=4, internal ا) |
| VII | اِنْفَعَلَ | `VERB_AUGMENTED_VII` | ان prefix + 5 consonants, C2 is not ت |
| VIII | اِفْتَعَلَ | `VERB_AUGMENTED_VIII` | ت at position 2, OR ت at position 1 (assimilation), OR emphatic at position 1 |
| IX | اِفْعَلَّ | `VERB_AUGMENTED_IX` | ا prefix + final shadda or explicit geminate, non-emphatic C1 |
| X | اِسْتَفْعَلَ | `VERB_AUGMENTED_X` | است prefix + 5+ chars |
| XI | اِفْعَالَّ | `VERB_AUGMENTED_XI` | ا prefix + 5 consonants + ا at position 3 |
| XII | اِفْعَوْعَلَ | `VERB_AUGMENTED_XII` | ا prefix + 6 consonants + و at position 3 + repeated R2 |
| Q-II | تَفَعْلَلَ | `VERB_RESEMBLING_QUAD_II` | ت prefix + 5 consonants + 4-char root in root_set |
| Doubled | geminate (مضعّف) | `VERB_DOUBLED` | 2-consonant skeleton + doubled form in root_set |

### Form II/III Disambiguation (Phase 0 Addition)

In undiacritized text, Form III (فَاعَلَ) is indistinguishable from the active participle (فَاعِل) -- both have the shape C1+ا+C2+C3. The engine resolves this via:
1. **Known Form III lookup set** (21 common verbs): قاتل, شارك, سافر, حاول, ناقش, بادل, جاهد, عاون, عارض, راقب, واصل, دافع, سابق, نادى, هاجر, طالع, عالج, واجه, صاحب, جاور, ساعد
2. **Diacritic check**: if C2 is followed by fatha (َ), it is Form III; if by kasra (ِ), it is the active participle

### Elative Adjective Detection (Phase 0 Addition)

Elative adjectives (أَفْعَل, e.g., أَكْبَر "bigger", أَفْضَل "better") share the same pattern as Form IV verbs (أَفْعَلَ). The engine maintains a set of 52 known elative roots (كبر, صغر, فضل, حسن, سوء, عظم, etc.) and checks the 3-consonant root after أ against this set BEFORE falling through to the Form IV classification. Matched elatives receive `pos=ADJ, degree=COMP`.

### Additional Nominal Patterns

- **Broken plural أَفْعَال:** أ prefix + 5 consonants + ا at position 3 (e.g., أَقْلَام "pens", أَعْمَال "works")
- **Masdar Form II (تَفْعِيل):** ت prefix + 5 consonants + ي at position 3 (e.g., تَعْلِيم "education")
- **Masdar Form IV (إِفْعَال):** إ prefix + 5 consonants + ا at position 3 (e.g., إِرْسَال "sending")
- **Masdar Form IV ajwaf (إِفَالَة):** إ prefix + 4 consonants + ا at position 2 (e.g., إِقَامَة "establishment")
- **Masdar Form IX (اِفْعِلَال):** ا prefix + 6 consonants + ا at position 4 + R3 repeated
- **Masdar Form XI (اِفْعِيلَال):** ا prefix + 7 consonants + ي at position 3 + ا at position 5
- **Masdar Form XII (اِفْعِيعَال):** ا prefix + 7 consonants + ي at position 3 + R2 repeated

### Template Index Fallback

For stems with n=3 or n=4 root consonants, the template index is consulted. Priority order: `VERB_TRILATERAL_BARE` first, then weak/doubled/hamza categories if the stem contains weak-root markers (ا, و, ي). For n >= 5, the index is not trusted (augment consonants inflate the count), and rule-based heuristics are used instead. Ultimate fallback: `VERB_TRILATERAL_UNKNOWN` with `pos=VERB, form=I`.

## Step C: Root Extraction

### Direct Lookup

The primary strategy is direct lookup against the **7,142-root set** from `ar_roots.json` (sourced from the Doha Historical Dictionary of Arabic / معجم الدوحة التاريخي للغة العربية). The engine:

1. Applies augment prefix skip based on the template category from Step B (e.g., skip 3 consonants for Form X است, skip 2 for Form VII ان, skip 1 for Form IV أ or NOM_DERIVED م)
2. For Form VIII, removes the infixed ت (or its emphatic assimilation variant ط/د) at position 1 or 2
3. For NOM_DERIVED with مُ prefix, applies secondary augment removal: Form V/VI ت at position 0, Form VII ن at position 0, Form VIII ت at position 1
4. Tries root_consonants (with internal ا stripped) first, then full consonants, against root_set

### Augment Prefix Skip Table

| Template Category | Skip | Example |
|-------------------|------|---------|
| `VERB_AUGMENTED_X` | 3 | اِسْتَخْرَجَ: skip است -- root خرج |
| `NOM_DERIVED_X` | 3 | مُسْتَخْرِج: skip مست -- root خرج |
| `VERB_AUGMENTED_VII` | 2 | اِنْكَسَرَ: skip ان -- root كسر |
| `VERB_AUGMENTED_VIII` | 1 | اِحْتَرَمَ: skip ا -- root حرم (+ ت removal) |
| `VERB_AUGMENTED_IX` | 1 | اِحْمَرَّ: skip ا -- root حمر |
| `VERB_AUGMENTED_IV` | 1 | أَخْرَجَ: skip أ -- root خرج |
| `VERB_AUGMENTED_V_VI` | 1 | تَعَلَّمَ: skip ت -- root علم |
| `NOM_DERIVED` | 1 | مُعَلِّم: skip م -- root علم |
| `ADJ_ELATIVE` | 1 | أَكْبَر: skip أ -- root كبر |
| `BROKEN_PLURAL_AF3AL` | 1 | أَقْلَام: skip أ -- root قلم |
| `MASDAR_FORM_II` | 1 | تَعْلِيم: skip ت (+ ي removal) -- root علم |
| `MASDAR_FORM_IV` | 1 | إِرْسَال: skip إ -- root رسل |
| Trilateral bare, Form II/III, doubled, weak | 0 | Direct consonant lookup |

### Weak Root Resolution

**Ajwaf (أجوف) -- hollow roots (middle weak radical):**  
When the middle consonant is ا (ambiguous between و and ي roots), the engine consults the `_AJWAF_FRAME` disambiguation lexicon keyed by (R1, R3). This lexicon contains 40 entries covering the most common MSA ajwaf verbs. Examples:
- (ق, ل) -- و: قَالَ -- قول (said)
- (ب, ع) -- ي: بَاعَ -- بيع (sold)
- (ك, ن) -- و: كَانَ -- كون (was)
- (ج, ء) -- ي: جَاءَ -- جيء (came)

Passive ajwaf forms (surface ي but root و) are handled: قِيلَ -- قول (was said), دِيرَ -- دور (was managed).

**Naqis (ناقص) -- defective roots (final weak radical):**  
When the final consonant is ى, ا, ي, or ء, the engine consults the `_NAQIS_FRAME` disambiguation lexicon keyed by (R1, R2). This lexicon contains 25 entries. Examples:
- (ر, م) -- ي: رَمَى -- رمي (threw)
- (د, ع) -- و: دَعَا -- دعو (called)
- (ق, ض) -- ي: قَضَى -- قضي (judged)
- (ب, ن) -- و: بَنَى -- بنو (built)

Default ordering when the frame is unknown: و-first for ى/ا finals, ي-first for hamza finals.

**Mithal (مثال) -- assimilated roots (initial weak radical):**  
For 2-consonant skeletons, the engine tries prepending و (e.g., عد -- وعد "promised"). This handles verbs where the initial و drops in certain conjugations.

**Geminate (مضعّف) -- doubled roots:**  
For 2-consonant skeletons, the engine tries doubling the final consonant (e.g., شد -- شدد "pulled tight", مد -- مدد "extended"). For 2-consonant skeletons after augment skip, geminate is attempted before mithal.

**Hamzated (مهموز) -- hamza roots:**  
All hamza orthographic variants (أ, إ, آ, ؤ, ئ) are normalized to bare ء via `_HAMZA_NORM` translation table before root lookup. This ensures that أَكَلَ, إِكْلَة, etc., all map to the root ءكل.

**Form VIII assimilation recovery:**  
When a Form VIII skeleton starts with ت (assimilated from root-initial و/ي/ء), the engine tries prepending و, ي, ء to recover the root. Example: تصل (from اتصل -- وصل) -- tries وصل, finds it in root_set.

### Quadriliteral Root Handling

4-consonant roots (e.g., دحرج "to roll", زلزل "to shake") are looked up directly when the consonant skeleton has 4+ characters. The 4-consonant lookup runs BEFORE the 3-consonant truncation to prevent incorrect matches. Diminutive pattern فُعَيْلِل (5 consonants with ي at position 2) is handled by stripping the diminutive infix: دُرَيْهِم -- درهم.

### Fallback Behavior

When no root matches after all weak-root resolution attempts, the engine returns the raw consonant skeleton. Downstream processing can flag these as UNKNOWN.

## Passive Voice Detection

The engine detects passive voice from diacritics (Phase 0 addition). The `_check_passive()` method scans the original (pre-stripped) word for the Form I passive vowel pattern فُعِلَ: damma (ُ U+064F) on the first consonant and kasra (ِ U+0650) on the second consonant. When detected, `voice=PASS` is added to the tag bundle. This is only reliable when diacritics are present in the input text; unvoweled text cannot trigger passive detection.

## Tag Inventory

### Part of Speech Values

| POS | Description | Source |
|-----|-------------|--------|
| `VERB` | Verbs (all forms, tenses) | Step B template match, closed-class KANA |
| `NOM` | Nominals (nouns, masdars, participles, broken plurals) | Step B template match, loanword intercept |
| `ADJ` | Adjectives (elative, nisba) | Step B template match |
| `PART` | Particles (all closed-class function words) | Closed-class intercept |
| `UNKNOWN` | Unclassified | Fallback |

### Feature Tags

| Tag Key | Possible Values | Source |
|---------|----------------|--------|
| `form` | `I`, `II`, `III`, `IV`, `V`, `VI`, `VII`, `VIII`, `IX`, `X`, `XI`, `XII`, `Q-II` | Step B template match |
| `role` | `DERIVED`, `PASSIVE_PARTICIPLE`, `MASDAR`, `PLURAL`, `NISBA` | Step B template match |
| `tense` | `PAST`, `PRES`, `IMP` (imperative) | Template tags_implied, validator |
| `voice` | `ACT`, `PASS` | Template tags_implied, `_check_passive()` |
| `num` | `DU` (dual), `PL` (plural) | Enclitic tags |
| `gender` | `M`, `F` | Enclitic tags |
| `degree` | `COMP` (comparative/elative) | Step B elative detection |
| `weak` | (from template) | Template tags_implied for weak roots |
| `weak_type` | (from template) | Template tags_implied for weak root type |
| `diptote` | (from template) | Template tags_implied for diptote nouns |
| `subcat` | `PREP`, `CONJ`, `COMP`, `INTERROG`, `NEG`, `DISC`, `VOC`, `INTERJ`, `OATH`, `RESP`, `COND`, `KANA` | Closed-class intercept |
| `gloss` | English gloss string | Closed-class intercept |
| `conj` | `W` (و), `F` (ف) | Proclitic stripping |
| `prep` | `B` (ب), `L` (ل), `K` (ك) | Proclitic stripping |
| `def` | `DEF` | Proclitic stripping (definite article) |
| `tense_prefix` | `FUT` | Proclitic stripping (سـ future marker) |
| `emph` | `LAM`, `NUN_THAQILA`, `NUN_KHAFIFA` | Proclitic/enclitic stripping |
| `interrog` | `Q` | Proclitic stripping (أَ prefix) |
| `obj` | `3MSG`, `3FSG`, `3DU`, `3MPL`, `3FPL`, `1SG`, `1PL`, `2MSG`, `2FSG`, `2DU`, `2MPL`, `2FPL` | Enclitic stripping |
| `case` | `NOM`, `OBL`, `GEN` | Enclitic tags (dual/plural markers) |
| `person` | `2`, `3` (from verb agreement suffixes, imperfect prefix) | Enclitic/proclitic stripping |
| `imperf` | `3MSG` | Imperfect prefix stripping (يَ/ي) |
| `circumfix` | `LAM_NUN` | Circumfix detection |
| `assertion` | `SWORN` | Circumfix detection |
| `origin` | `FOREIGN` | Loanword intercept |
| `mood` | `JUS` (jussive) | Validator (sentence-level) |

### Bundle Count

The engine produces **270 observed feature bundles** in corpus processing. The combinatorial origin of this number derives from the cross-product of: POS (5 values) x form (14 values for verbs) x clitic combinations (conj x prep x def x tense_prefix x emph x interrog x obj x case x num x gender x person) x voice (2 values) x weak-root features. However, many combinations are linguistically impossible (e.g., passive imperative, jussive outside present tense), so the actual observed count is far below the theoretical maximum.

## Config Files

| File | Content | Count |
|------|---------|-------|
| `ar_roots.json` | Trilateral and quadriliteral roots from the Doha Historical Dictionary of Arabic (معجم الدوحة التاريخي للغة العربية) | 7,142 roots |
| `ar_templates.json` | Morphological templates (verb paradigms, nominal patterns, broken plurals, participles, masdars) across 42 categories | 348 templates |
| `ar_vocab_space.json` | Placeholder file; populated at runtime by crossing roots against templates. Contains only a comment in the repository. | Dynamic |

## Validators

### Word-level: `check_morph_sequence_ar`

Defined in `shared.py`. Validates per-token tag bundles according to Arabic morphosyntactic rules (النحو والصرف):

- **VERB bundles** must contain both `tense` and `person` tags. Additional rules:
  - Imperative (`tense=IMP`) requires `person=2` and `voice=ACT` (only 2nd person active imperatives exist)
  - Passive imperative (`voice=PASS` + `tense=IMP`) is invalid
  - Jussive mood (`mood=JUS`) requires `tense=PRES` (jussive only applies to present tense)
  - Verbs must NOT have `case` or `def` tags (these are nominal features)
- **NOM bundles** must contain both `num` and `gender` tags. Must NOT have `tense`, `person`, or `mood` tags.
- **ADJ bundles** must NOT have `tense`, `person`, or `mood` tags.

### Sentence-level: `validate_sentence_structure_ar`

Defined in `shared.py`. Validates Arabic sentence-level structure (VSO verbal sentences and nominal sentences):

1. Filters out non-content tokens (`PART`, `FOREIGN`, `PROPER`, `UNKNOWN`)
2. **Verbal sentence opener (الجملة الفعلية):** if the first content token is a VERB, it must have both `tense` and `person` tags
3. **Nominal sentence opener (الجملة الاسمية):** if the first content token is a NOM, its case must be `NOM` (nominative) or unspecified
4. **Global verb rules:** passive imperative is invalid; jussive mood outside present tense is invalid
5. **Dual noun rule:** dual nouns (`num=DU`) must have a `case` tag (dual nouns have overt case marking in Arabic: ـانِ nominative, ـيْنِ oblique)

## Known Limitations

1. **Form II/III surface ambiguity without diacritics:** In fully unvoweled text, فَعَّلَ (Form II) and فَاعَلَ (Form III) and فَاعِل (active participle) can be indistinguishable. The engine handles this via a 21-entry lookup set for Form III and shadda detection for Form II, but coverage is incomplete for rare verbs.

2. **Imperfect تَ/أَ/نَ prefixes not stripped:** Only the يَ/ي imperfect prefix is stripped. The تَ (2nd person / 3rd feminine), أَ (1st singular), and نَ (1st plural) prefixes are not stripped because they are highly ambiguous with root-initial consonants. This means imperfect verbs with these prefixes may be misanalyzed.

3. **No context-dependent disambiguation:** The engine is a single-token analyzer. It cannot disambiguate homographs that require sentential context (e.g., من as preposition "from" vs. interrogative "who", قد + past verb "already" vs. قد + present verb "perhaps").

4. **Passive detection requires diacritics:** The `_check_passive()` method only works when the input has short vowel diacritics. Unvoweled text (the vast majority of real-world Arabic) cannot trigger passive voice detection.

5. **Limited Form III lookup set:** Only 21 known Form III verbs are in the undiacritized lookup set. Other Form III verbs in unvoweled text will fall through to the template index and may be misclassified as active participles.

6. **No morphophonemic interaction modeling:** The engine does not model assimilation rules beyond Form VIII emphatic assimilation (ت -- ط/د). Other assimilations (e.g., Form V/VI تَ assimilation before sibilants: تَصَبَّرَ -- اصطبر) are not handled.

7. **Oath prefix (تَ/تِ) excluded from stripping:** The oath prefix (تَاللهِ) was removed from the proclitic list to avoid false positives on common words starting with تَ/تِ. Oath forms are handled only as frozen closed-class entries.

8. **Broken plural coverage:** Only the أَفْعَال pattern is explicitly detected. Other broken plural patterns (فُعُول, فِعَال, أَفْعِلَة, فَوَاعِل, مَفَاعِل, etc.) are handled by the template index but without explicit pattern classification.

## Test Coverage

| Test File | Test Count | Categories |
|-----------|-----------|------------|
| `test_ar_engine_adversarial.py` | 44 | False-positive proclitic guards, root-initial consonant protection, Form VIII disambiguation, weak-root edge cases, loanword bypass, geminate verbs, hamza normalization |
| `test_ar_engine_sentence.py` | 29 | VSO validation, nominal sentences, passive imperative rejection, jussive constraints, dual case requirements, mixed content filtering |
| `test_ar_engine_fixes.py` | 3 | Phase 0 regression fixes (Form II/III disambiguation, elative detection, passive voice) |
| `test_ar_engine_particles.py` | 1 | Closed-class intercept coverage (parametrized across all 172 entries) |
| `test_ar_engine_regression.py` | 1 | Regression suite (parametrized across known-good root extractions) |
| `test_ar_engine_templates.py` | 1 | Template loading and index construction validation |
| **Total** | **79** | Covers: clitic stripping guards, template matching, root extraction, weak-root resolution, closed-class intercept, loanword intercept, sentence validation, adversarial edge cases |

The adversarial test suite (`test_ar_engine_adversarial.py`) is the largest at 44 tests, specifically targeting false-positive scenarios where the engine could incorrectly strip proclitics or enclitics from short words, misclassify Form VIII as definite-article + root, or fail on weak-root disambiguation.
