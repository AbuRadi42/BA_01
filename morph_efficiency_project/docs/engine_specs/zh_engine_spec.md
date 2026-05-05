# Mandarin Chinese Engine Design Specification

**Language:** Mandarin Chinese (zh)
**Typology:** Isolating-analytic (morphological minimum)
**Engine file:** `scripts/engines/zh_engine.py` (to be built)
**Status:** Design phase
**Role in experiment:** Control -- expected ~0% efficiency gain from morph-aware tokenization

---

## Morphological Overview

Mandarin Chinese is the paradigm case of an isolating language: it sits at the extreme analytic end of the morphological typology spectrum, opposite agglutinative Turkish and fusional Arabic. In Mandarin, the fundamental unit of meaning -- the morpheme -- maps almost one-to-one onto a single syllable, which is in turn written as a single character (hanzi). There are no conjugation tables, no declension paradigms, no case systems, no grammatical gender, no number agreement, and no person/tense marking on verbs. The word "go" is qu in all contexts: I go, he went, they will go, we have gone -- the verb form never changes. This stands in stark contrast to Arabic, where a single verb form like "kataba" encodes person, number, gender, tense, voice, and mood simultaneously.

Mandarin expresses grammatical relationships through three primary mechanisms: rigid word order (SVO), grammatical particles, and pragmatic context. Word order determines who does what to whom. Aspect (not tense) is optionally marked by free-standing particles -- le for perfective/completed action, zhe for ongoing/durative state, guo for experiential ("have ever done"). Structural particles de (three homophones written differently: possessive/attributive, adverbial, and complement) serve roles that inflectional morphology handles in fusional languages. Sentence-final particles like ma (question), ba (suggestion), and ne (topic continuation) encode pragmatic and modal information that other languages fold into verbal morphology or dedicated syntactic constructions.

The morphological processes that do exist in Mandarin are limited and mostly lexicalized. Compounding is the dominant word-formation strategy: diannao (electric + brain = computer), huoche (fire + vehicle = train), shouji (hand + machine = cellphone). These compounds are semantically opaque and lexically frozen -- decomposing them does not aid grammatical analysis. Reduplication exists in limited patterns: adjective reduplication for emphasis (gaogao de = "very tall"), verb reduplication for tentativeness (kan kan = "take a look"). A small inventory of derivational affixes exists: the plural marker men (restricted to animate nouns and pronouns), the ordinal prefix di (di-yi = first), nominalizing suffixes like zi (zhuozi = table), er (erhua diminutive), tou (shitou = stone), and a handful of others. But even these are largely lexicalized -- zhuozi is simply "table" in modern Mandarin, not productively analyzed as "table-thing."

What "morphology-aware" means for Mandarin is therefore fundamentally different from what it means for other languages in this experiment. For Arabic, morphology-awareness means decomposing a single token into 6-8 grammatical features (root, pattern, person, number, gender, tense, voice, mood). For Turkish, it means peeling off a stack of agglutinated suffixes in slot order. For Mandarin, "morphology-awareness" is really "grammar-role-awareness" -- identifying what function each word serves (noun, verb, particle, classifier, etc.) rather than decomposing the word itself. The engine tags each word's grammatical role but finds almost nothing to strip, split, or decompose within the word form.

This is precisely why Mandarin serves as the experimental control. If the morph-aware tokenization method shows significant efficiency gains on Arabic (predicted ~15-20% improvement) and Turkish (predicted ~10-15%) but near-zero improvement on Mandarin, this confirms that the gains come from morphological compression specifically, not from some artifact of the method (e.g., vocabulary reduction from POS tagging alone, or statistical effects of the additional annotation layer). Mandarin's near-zero expected improvement is not a failure of the engine -- it is the most important data point in the experiment. An engine that faithfully represents Mandarin's minimal morphology and produces correspondingly minimal feature bundles is essential for the experimental design.

## Preprocessing: Word Segmentation

Mandarin text is written without spaces between words. Before the engine can analyze individual words, the continuous character stream must be segmented into word-level tokens. This is a non-trivial NLP task with its own error rate, and it is handled as a **preprocessing dependency external to the engine**.

### Dependency

Word segmentation is performed by one of the following libraries (configured in `preprocess_morph.py`):
- **jieba** (recommended, default): fast, well-maintained, MIT-licensed. Install via `pip install jieba`.
- **pkuseg** (alternative): higher accuracy on formal text, slower. Install via `pip install pkuseg`.

### Architecture

- Segmentation is called in `preprocess_morph.py`, **NOT** in `zh_engine.py`.
- The engine's `analyze(word)` method receives a **single pre-segmented word** (one or more characters).
- The engine's `analyze_sentence(text)` method receives a **space-separated string** of pre-segmented words.
- The engine does **NOT** import jieba or pkuseg and has **no segmentation capability**.
- If unsegmented text is passed to `analyze_sentence()`, the engine will treat each character as a separate word, producing incorrect but non-crashing results.

### Preprocessing pipeline

```
Raw text:  "我在北京学习中文"
           ↓ jieba.cut()
Segmented: "我 在 北京 学习 中文"
           ↓ zh_engine.analyze_sentence()
TokenInfo: [TokenInfo(surface="我", ...), TokenInfo(surface="在", ...), ...]
```

### Error propagation

Segmentation errors propagate silently into the engine. Common failure modes:
- Over-segmentation: "北京" (Beijing) split into "北" + "京" -- each character analyzed independently.
- Under-segmentation: "在北京" (in Beijing) merged into one token -- closed-class lookup fails for "在".
- The engine cannot detect or correct these errors. Segmentation quality is a confound documented in the experimental limitations.

## Closed-Class Intercept

The closed-class dictionary is the **largest and most important component** of the Mandarin engine. In isolating languages, grammatical information resides almost entirely in function words rather than in morphological marking on content words. The engine maintains a static dictionary (class attribute `CLOSED_CLASS`) mapping surface forms to `(POS, tags)` tuples. All entries are intercepted at the beginning of `_step_a` and bypass all further processing.

### Aspect Particles (PART, 3 entries)

| Surface | POS | Tags | Gloss |
|---------|-----|------|-------|
| 了 | PART | `{aspect: PERF}` | Perfective / change of state |
| 着 | PART | `{aspect: DUR}` | Durative / progressive |
| 过 | PART | `{aspect: EXP}` | Experiential ("have ever") |

Note: These are listed here as free-standing particles (post-verbal or sentence-final position). When attached to a verb as a suffix in the segmenter output (e.g., "做了" as one token), they are handled by Step A inflectional stripping instead.

### Structural Particles (PART, 3 entries)

| Surface | POS | Tags | Gloss |
|---------|-----|------|-------|
| 的 | PART | `{role: ATTR}` | Attributive / possessive marker |
| 地 | PART | `{role: ADVL}` | Adverbial marker |
| 得 | PART | `{role: COMP}` | Complement marker |

### Sentence-Final Particles (PART, 10 entries)

| Surface | POS | Tags | Gloss |
|---------|-----|------|-------|
| 吗 | PART | `{particle_type: QUESTION}` | Yes/no question |
| 呢 | PART | `{particle_type: TOPIC}` | Follow-up question / topic continuation |
| 吧 | PART | `{particle_type: SUGGESTION}` | Suggestion / mild uncertainty |
| 啊 | PART | `{particle_type: EMPHASIS}` | Exclamation / softening |
| 啦 | PART | `{particle_type: EMPHASIS}` | Fusion of 了+啊, exclamatory completion |
| 哦 | PART | `{particle_type: ACKNOWLEDGMENT}` | Acknowledgment / realization |
| 嘛 | PART | `{particle_type: OBVIOUSNESS}` | "obviously" / rhetorical softening |
| 呀 | PART | `{particle_type: EMPHASIS}` | Variant of 啊 after certain finals |
| 哇 | PART | `{particle_type: EMPHASIS}` | Exclamatory variant of 啊 |
| 哈 | PART | `{particle_type: EMPHASIS}` | Light-hearted emphasis |

### Prepositions / Coverbs (ADP, 14 entries)

| Surface | POS | Tags | Gloss |
|---------|-----|------|-------|
| 在 | ADP | `{}` | at / in / on (locative) |
| 从 | ADP | `{}` | from |
| 到 | ADP | `{}` | to / until |
| 向 | ADP | `{}` | toward |
| 给 | ADP | `{}` | to / for (dative) |
| 跟 | ADP | `{}` | with / and |
| 对 | ADP | `{}` | toward / regarding |
| 把 | ADP | `{construction: BA}` | Patient-fronting marker (ba-construction) |
| 被 | ADP | `{construction: BEI}` | Passive marker (bei-construction) |
| 比 | ADP | `{construction: BI}` | Comparative marker |
| 用 | ADP | `{}` | using / with (instrumental) |
| 替 | ADP | `{}` | for / on behalf of |
| 离 | ADP | `{}` | from / away from (distance) |
| 往 | ADP | `{}` | toward (directional) |

Note: Many of these words (e.g., 在, 给, 到, 用) also function as full verbs. The engine assigns the closed-class ADP reading. Context-dependent disambiguation is a known limitation.

### Conjunctions (CONJ, 20 entries)

| Surface | POS | Tags | Gloss |
|---------|-----|------|-------|
| 和 | CONJ | `{}` | and |
| 或 | CONJ | `{}` | or |
| 或者 | CONJ | `{}` | or (spoken/full form) |
| 但 | CONJ | `{}` | but |
| 但是 | CONJ | `{}` | but (full form) |
| 可是 | CONJ | `{}` | but / however |
| 不过 | CONJ | `{}` | but / however (colloquial) |
| 因为 | CONJ | `{}` | because |
| 所以 | CONJ | `{}` | therefore |
| 如果 | CONJ | `{}` | if |
| 虽然 | CONJ | `{}` | although |
| 而 | CONJ | `{}` | and / but / yet (literary) |
| 而且 | CONJ | `{}` | moreover / and also |
| 还是 | CONJ | `{}` | or (in questions) / still |
| 无论 | CONJ | `{}` | regardless / no matter |
| 不管 | CONJ | `{}` | regardless / no matter |
| 既然 | CONJ | `{}` | since / given that |
| 只要 | CONJ | `{}` | as long as |
| 除非 | CONJ | `{}` | unless |
| 否则 | CONJ | `{}` | otherwise |

### Pronouns (PRON, 20 entries)

| Surface | POS | Tags | Gloss |
|---------|-----|------|-------|
| 我 | PRON | `{person: 1, num: SG}` | I / me |
| 你 | PRON | `{person: 2, num: SG}` | you (singular) |
| 您 | PRON | `{person: 2, num: SG, register: POLITE}` | you (polite) |
| 他 | PRON | `{person: 3, num: SG, gender: MASC}` | he / him |
| 她 | PRON | `{person: 3, num: SG, gender: FEM}` | she / her |
| 它 | PRON | `{person: 3, num: SG, gender: NEUT}` | it |
| 我们 | PRON | `{person: 1, num: PL}` | we / us |
| 你们 | PRON | `{person: 2, num: PL}` | you (plural) |
| 他们 | PRON | `{person: 3, num: PL}` | they / them (masc/default) |
| 她们 | PRON | `{person: 3, num: PL, gender: FEM}` | they / them (feminine) |
| 它们 | PRON | `{person: 3, num: PL, gender: NEUT}` | they / them (inanimate) |
| 这 | PRON | `{deixis: PROX}` | this |
| 那 | PRON | `{deixis: DIST}` | that |
| 谁 | PRON | `{interrog: YES}` | who |
| 什么 | PRON | `{interrog: YES}` | what |
| 哪 | PRON | `{interrog: YES}` | which |
| 自己 | PRON | `{reflex: YES}` | self / oneself |
| 大家 | PRON | `{}` | everyone |
| 别人 | PRON | `{}` | others / other people |
| 哪里 | PRON | `{interrog: YES}` | where |

Note: Pronoun plurals (我们, 你们, etc.) are listed as full entries here because the segmenter typically outputs them as single tokens. If the segmenter splits them (我 + 们), the singular pronoun is caught here and 们 is handled by Step A.

### Negation (ADV, 3 entries)

| Surface | POS | Tags | Gloss |
|---------|-----|------|-------|
| 不 | ADV | `{negation: BU}` | General negation (present/future/habitual) |
| 没 | ADV | `{negation: MEI}` | Perfective negation ("did not") |
| 别 | ADV | `{negation: BIE}` | Prohibitive ("don't!") |

Note: 没有 (mei you) may appear as one token or two. If one token, it is listed separately below as a closed-class entry. If segmented as 没 + 有, each is handled independently.

### Common Adverbs (ADV, 20 entries)

| Surface | POS | Tags | Gloss |
|---------|-----|------|-------|
| 很 | ADV | `{}` | very |
| 也 | ADV | `{}` | also |
| 都 | ADV | `{}` | all / even |
| 就 | ADV | `{}` | then / just / only |
| 才 | ADV | `{}` | only then / not until |
| 再 | ADV | `{}` | again (future) |
| 又 | ADV | `{}` | again (past / and also) |
| 已经 | ADV | `{}` | already |
| 正在 | ADV | `{aspect: PROG}` | currently / in the process of |
| 一直 | ADV | `{}` | always / continuously |
| 马上 | ADV | `{}` | immediately |
| 常常 | ADV | `{}` | often |
| 刚 | ADV | `{}` | just (recently) |
| 还 | ADV | `{}` | still / also |
| 只 | ADV | `{}` | only |
| 非常 | ADV | `{}` | extremely |
| 太 | ADV | `{}` | too (excessively) |
| 最 | ADV | `{degree: SUPER}` | most (superlative marker) |
| 更 | ADV | `{degree: COMP}` | more (comparative marker) |
| 没有 | ADV | `{negation: MEI}` | did not / have not |

### Measure Words / Classifiers (CLF, 20 entries)

| Surface | POS | Tags | Gloss |
|---------|-----|------|-------|
| 个 | CLF | `{classifier: GEN}` | General classifier (default) |
| 本 | CLF | `{classifier: YES}` | Books, bound volumes |
| 条 | CLF | `{classifier: YES}` | Long/thin things (rivers, fish, roads, pants) |
| 只 | CLF | `{classifier: YES}` | Small animals, one of a pair |
| 张 | CLF | `{classifier: YES}` | Flat things (paper, tables, tickets, faces) |
| 把 | CLF | `{classifier: YES}` | Graspable things (chairs, knives, umbrellas) |
| 件 | CLF | `{classifier: YES}` | Clothing, matters, items |
| 位 | CLF | `{classifier: YES}` | People (polite) |
| 辆 | CLF | `{classifier: YES}` | Vehicles |
| 双 | CLF | `{classifier: YES}` | Pairs (shoes, chopsticks, hands) |
| 块 | CLF | `{classifier: YES}` | Money units, lumps, pieces |
| 杯 | CLF | `{classifier: YES}` | Cups/glasses of liquid |
| 瓶 | CLF | `{classifier: YES}` | Bottles of liquid |
| 支 | CLF | `{classifier: YES}` | Pens, sticks, songs |
| 台 | CLF | `{classifier: YES}` | Machines, performances |
| 座 | CLF | `{classifier: YES}` | Mountains, buildings, bridges |
| 所 | CLF | `{classifier: YES}` | Houses, schools, institutions |
| 篇 | CLF | `{classifier: YES}` | Articles, essays |
| 首 | CLF | `{classifier: YES}` | Songs, poems |
| 家 | CLF | `{classifier: YES}` | Families, businesses, restaurants |

Note: Classifier identification is context-dependent. Many classifier characters have other uses (e.g., 只 is also an adverb meaning "only"; 把 is also the ba-construction marker). The engine assigns the CLF reading when the word appears in the closed-class list. Context-level disambiguation is a known limitation. Additional classifiers can be added to `zh_classifiers.json`.

### Determiners / Demonstratives (DET, 6 entries)

| Surface | POS | Tags | Gloss |
|---------|-----|------|-------|
| 每 | DET | `{}` | every |
| 某 | DET | `{}` | certain / some |
| 各 | DET | `{}` | each / every |
| 一些 | DET | `{}` | some / a few |
| 几 | DET | `{interrog: YES}` | how many / several |
| 所有 | DET | `{}` | all |

Note: 这 and 那 (this/that) are listed under pronouns. When used as prenominal determiners (这本书 "this book"), they function as demonstrative determiners, but the engine assigns PRON for simplicity. This ambiguity parallels English "this" (pronoun vs. determiner).

### Numbers (NUM, 16 entries)

| Surface | POS | Tags | Gloss |
|---------|-----|------|-------|
| 一 | NUM | `{}` | one |
| 二 | NUM | `{}` | two |
| 两 | NUM | `{}` | two (used with classifiers) |
| 三 | NUM | `{}` | three |
| 四 | NUM | `{}` | four |
| 五 | NUM | `{}` | five |
| 六 | NUM | `{}` | six |
| 七 | NUM | `{}` | seven |
| 八 | NUM | `{}` | eight |
| 九 | NUM | `{}` | nine |
| 十 | NUM | `{}` | ten |
| 百 | NUM | `{}` | hundred |
| 千 | NUM | `{}` | thousand |
| 万 | NUM | `{}` | ten thousand |
| 亿 | NUM | `{}` | hundred million |
| 零 | NUM | `{}` | zero |

### Auxiliary / Modal Expressions (AUX, 10 entries)

| Surface | POS | Tags | Gloss |
|---------|-----|------|-------|
| 会 | AUX | `{modal: ABILITY}` | can / will (learned ability, future) |
| 能 | AUX | `{modal: ABILITY}` | can (physical ability, permission) |
| 可以 | AUX | `{modal: PERMISSION}` | may / can (permission) |
| 应该 | AUX | `{modal: OBLIGATION}` | should |
| 必须 | AUX | `{modal: OBLIGATION}` | must |
| 要 | AUX | `{modal: VOLITION}` | want to / going to |
| 想 | AUX | `{modal: VOLITION}` | want to / think |
| 敢 | AUX | `{modal: ABILITY}` | dare |
| 肯 | AUX | `{modal: VOLITION}` | be willing to |
| 得 | AUX | `{modal: OBLIGATION}` | have to / must (colloquial; homograph with 得 COMP particle) |

### Copula and Existentials (VERB, 3 entries)

| Surface | POS | Tags | Gloss |
|---------|-----|------|-------|
| 是 | VERB | `{role: COPULA}` | to be (equative/identification) |
| 有 | VERB | `{role: EXISTENTIAL}` | to have / there is |
| 在 | VERB | `{role: LOCATIVE}` | to be at / to be (doing) |

Note: 是, 有, and 在 are listed here under VERB but also appear elsewhere (在 as ADP). In implementation, the first-registered entry wins. Design decision: register 在 as ADP (its more frequent grammatical function) and handle verbal 在 as an UNKNOWN that gains POS from context. 是 and 有 are registered as VERB.

### Total Closed-Class Entries

| Category | Count |
|----------|-------|
| Aspect particles | 3 |
| Structural particles | 3 |
| Sentence-final particles | 10 |
| Prepositions / coverbs | 14 |
| Conjunctions | 20 |
| Pronouns | 20 |
| Negation | 3 |
| Common adverbs | 20 |
| Classifiers | 20 |
| Determiners | 6 |
| Numbers | 16 |
| Auxiliaries / modals | 10 |
| Copula / existentials | 2 (是, 有; 在 counted under ADP) |
| **Total** | **~147** |

Additional classifiers and function words can be added via `zh_particles.json` and `zh_classifiers.json`, bringing the practical total to **~200+ entries**. This is where the vast majority of Mandarin's "grammar" lives -- in the closed-class intercept, not in morphological rules.

## Step A: Inflectional Stripping

Mandarin has almost no inflectional morphology. Step A (`_step_a`) handles only 5 stripping rules -- the fewest of any engine in the experiment, by a wide margin (compare: English has 10 rules, Turkish has 30+, Arabic has 50+).

### 1. Closed-Class Lookup

If the word is in `CLOSED_CLASS`, return immediately with pre-assigned POS and tags. No further processing.

### 2. Plural Marker 们 (men)

**Pattern:** Word ends with 们 AND the preceding character(s) form a recognized animate noun or pronoun base.
**Action:** Strip 们, assign `{num: PL}`, POS = `NOUN`.
**Constraint:** 们 attaches only to animate/human nouns and pronouns. It does not mark plural on inanimate nouns (books, cars, ideas -- these have no plural form). A whitelist of common animate bases is maintained:
- Pronoun bases: 我, 你, 他, 她, 它 (already handled by closed-class for full forms 我们 etc.)
- Animate nouns: 人 (person), 孩子 (child), 同学 (classmate), 朋友 (friend), 同事 (colleague), 老师 (teacher), 学生 (student), 客人 (guest), 女士 (lady), 先生 (gentleman)

If the base is not in the whitelist, 们 is not stripped (the word is returned as-is with POS = UNKNOWN). This prevents false stripping on words that happen to end in 们 but are not pluralized nouns.

**Examples:**
- 朋友们 -> root=朋友, tags=`{num: PL}`, POS=NOUN
- 老师们 -> root=老师, tags=`{num: PL}`, POS=NOUN

### 3. Aspect Suffix 了 (le) -- Perfective

**Pattern:** Word ends with 了 AND length >= 2 characters AND the base (word minus 了) is longer than 0 characters.
**Action:** Strip 了, assign `{aspect: PERF}`, POS = `VERB`.
**Note:** This rule fires only when the segmenter has attached 了 to the preceding verb as a single token (e.g., "做了" segmented as one unit). When 了 appears as a separate token, it is caught by the closed-class intercept.

**Ambiguity:** 了 is famously ambiguous between verbal aspect (perfective: 我吃了饭 "I ate") and sentence-final change-of-state (我知道了 "now I know"). At the word level, the engine cannot distinguish these -- both are tagged `aspect=PERF`. This is a documented limitation.

**Examples:**
- 做了 -> root=做, tags=`{aspect: PERF}`, POS=VERB
- 吃了 -> root=吃, tags=`{aspect: PERF}`, POS=VERB

### 4. Aspect Suffix 着 (zhe) -- Durative

**Pattern:** Word ends with 着 AND length >= 2 characters.
**Action:** Strip 着, assign `{aspect: DUR}`, POS = `VERB`.

**Examples:**
- 看着 -> root=看, tags=`{aspect: DUR}`, POS=VERB
- 等着 -> root=等, tags=`{aspect: DUR}`, POS=VERB

### 5. Aspect Suffix 过 (guo) -- Experiential

**Pattern:** Word ends with 过 AND length >= 2 characters.
**Action:** Strip 过, assign `{aspect: EXP}`, POS = `VERB`.
**Caution:** 过 as a standalone word means "to pass/cross" and is a common verb. This rule only fires when 过 is the final character of a multi-character token.

**Examples:**
- 去过 -> root=去, tags=`{aspect: EXP}`, POS=VERB
- 吃过 -> root=吃, tags=`{aspect: EXP}`, POS=VERB

### 6. Ordinal Prefix 第 (di)

**Pattern:** Word starts with 第 AND length >= 2 characters AND the remainder is a numeral or numeral compound.
**Action:** Strip 第, assign `{role: ORDINAL}`, POS = `NUM`.

**Examples:**
- 第一 -> root=一, tags=`{role: ORDINAL}`, POS=NUM
- 第三 -> root=三, tags=`{role: ORDINAL}`, POS=NUM

### 7. Default

If no rule matches, the word is returned unchanged with empty tags and POS = `UNKNOWN`.

**Total inflectional rules: 5.** This is the point. In Arabic, Step A has 50+ pattern-template rules. In Turkish, 30+ suffix-slot rules. In English, 10 rules. Mandarin has 5, and even these are borderline -- aspect particles are arguably free morphemes, not inflectional affixes. The near-absence of inflection is what makes Mandarin the control.

## Step B: Derivational Detection

Step B (`_step_b`) identifies one layer of derivational morphology on the stem from Step A. Like English, it only runs when Step A assigned POS = UNKNOWN. The derivational morphology of Mandarin is limited and heavily lexicalized.

### Prefix Matching (3 prefix patterns)

| Prefix | Label | POS Assignment | Examples | Notes |
|--------|-------|---------------|----------|-------|
| 老 | FAMILIAR_PREFIX | NOUN | 老师 (teacher), 老虎 (tiger), 老鼠 (mouse), 老板 (boss) | Highly lexicalized; 老 = "old" but the compound meanings are opaque |
| 小 | DIMINUTIVE_PREFIX | NOUN | 小姐 (miss), 小心 (careful), 小时 (hour) | Lexicalized; 小 = "small" |
| 阿 | FAMILIAR_PREFIX | NOUN | 阿姨 (auntie), 阿爸 (dad, dialectal) | Informal/familiar prefix |

### Suffix Matching (10 suffix patterns)

| Suffix | Label | POS Assignment | Examples | Notes |
|--------|-------|---------------|----------|-------|
| 子 | NOMINALIZER | NOUN | 桌子 (table), 杯子 (cup), 孩子 (child), 椅子 (chair) | Most productive nominalizer, but thoroughly lexicalized |
| 儿 | ERHUA_DIM | NOUN | 花儿 (flower), 鸟儿 (bird), 歌儿 (song) | Erhua diminutive; phonological in Beijing dialect |
| 头 | NOMINALIZER | NOUN | 石头 (stone), 木头 (wood), 骨头 (bone) | Lexicalized nominalizer |
| 家 | AGENT_EXPERT | NOUN | 科学家 (scientist), 作家 (writer), 画家 (painter) | "-ist/-er" equivalent; productive |
| 员 | AGENT_MEMBER | NOUN | 演员 (actor), 教员 (instructor), 队员 (team member) | "-er/-member" equivalent |
| 者 | AGENT_PERSON | NOUN | 读者 (reader), 作者 (author), 记者 (journalist) | "-er/-person" equivalent; literary register |
| 化 | VERBALIZER | VERB | 现代化 (modernize), 工业化 (industrialize), 绿化 (make green) | "-ize/-ify" equivalent; productive |
| 性 | QUALITY_NOUN | NOUN | 可能性 (possibility), 重要性 (importance), 创造性 (creativity) | "-ity/-ness" equivalent |
| 式 | STYLE_ADJ | ADJ | 中式 (Chinese-style), 美式 (American-style), 正式 (formal) | "-style/-type" |
| 地 | ADVERBIALIZER | ADV | Already handled as structural particle in closed-class; only fire if multi-char token ends in 地 | Rare as suffix on multi-char words |

### Lexicalization Warning

A critical design note: most Mandarin "derivational" morphology is synchronically opaque. Modern speakers do not productively analyze 桌子 as 桌 + nominalizer; it is simply the word for "table." The engine tags these suffixes for consistency with other engines' treatment of derivation, but the derivational transparency is low. This contrasts with English, where un-happi-ness is transparently compositional, and Turkish, where ev-ler-imiz-de (house-PL-1PL.POSS-LOC) is fully decomposable.

The engine records a derivation chain entry (e.g., `子->NOMINALIZER`) but the practical impact on feature bundle diversity is minimal.

**Total derivational rules: ~13.** Compare: English has 80 rules, Turkish has 100+, Arabic uses pattern-template derivation with dozens of patterns.

## Step C: Root Extraction

Step C (`_step_c`) performs iterative re-application of Step B. For Mandarin, this is almost never needed.

- **Maximum iterations:** 2 (reduced from the English default of 4, since Mandarin derivation essentially never stacks).
- **Stopping condition:** Step B returns the same stem (no further stripping possible).
- **Expected behavior:** One pass at most. Mandarin words are 1-3 characters long; after one suffix/prefix strip, the remainder is typically a single character (the root). There are no attested cases of double-derivation in productive Mandarin morphology.

Example: 科学家 -> strip 家 (AGENT_EXPERT) -> root = 科学. One iteration, done. 科学 itself is a compound (science = branch + study) but compounds are not split (see below).

## Compound Identification

Many Mandarin words are compounds of two or more morphemes/characters:
- 电脑 (electric + brain = computer)
- 火车 (fire + vehicle = train)
- 手机 (hand + machine = cellphone)
- 飞机 (fly + machine = airplane)
- 大学 (big + study = university)
- 图书馆 (map + book + building = library)

**Design decision: The engine does NOT split compounds.** Rationale:

1. **Lexicalization:** These compounds are fully lexicalized. Knowing that 电脑 consists of 电 + 脑 does not help predict its meaning or grammatical behavior. The compound is semantically atomic.
2. **Segmentation boundary:** The word segmenter already decided that 电脑 is a single word. Re-splitting it into characters would undermine the segmentation step and produce misleading single-character "roots" (脑 alone means "brain," not "computer").
3. **Experimental validity:** Splitting compounds would artificially inflate the morphological analysis depth for Mandarin, undermining its role as the control. The point is that Mandarin words carry minimal decomposable structure.
4. **No head-constituency:** Unlike English (where compounds are right-headed: "bookshelf" is a kind of shelf), Mandarin compound headedness is inconsistent and often debated. There is no reliable rule for extracting a grammatical head.

The engine treats multi-character words as atomic units. No `zh_compounds.json` config file is needed.

## Tag Inventory

### Part of Speech Values

| POS Value | Description |
|-----------|-------------|
| `NOUN` | Common noun (content word, open class) |
| `VERB` | Verb (content word, open class; uninflected) |
| `ADJ` | Adjective (content word, open class; can function as stative verb) |
| `ADV` | Adverb (includes closed-class adverbs like 很, 也, 都) |
| `PRON` | Pronoun (personal, demonstrative, interrogative, reflexive) |
| `DET` | Determiner (每, 某, 各, etc.) |
| `ADP` | Adposition / preposition / coverb (在, 从, 把, 被, etc.) |
| `CONJ` | Conjunction (和, 或, 但是, 因为, etc.) |
| `PART` | Particle (aspect, structural, sentence-final) |
| `NUM` | Numeral (一 through 亿, 零, 两) |
| `CLF` | Classifier / measure word (个, 本, 条, etc.) |
| `AUX` | Auxiliary / modal (会, 能, 可以, 应该, etc.) |
| `UNKNOWN` | No pattern matched; content word without morphological features |

### Feature Tags

| Tag Key | Possible Values | Producing Step | Description |
|---------|----------------|----------------|-------------|
| `num` | `SG`, `PL` | Closed-class (pronouns), Step A (们 stripping) | Number (only on pronouns and animate nouns with 们) |
| `aspect` | `PERF`, `DUR`, `EXP`, `PROG` | Closed-class (free particles), Step A (attached particles) | Aspect marking via particles 了/着/过 or adverb 正在 |
| `role` | `ATTR`, `ADVL`, `COMP`, `ORDINAL`, `COPULA`, `EXISTENTIAL`, `LOCATIVE` | Closed-class (structural particles, copula/existentials), Step A (第) | Grammatical role marker |
| `particle_type` | `QUESTION`, `TOPIC`, `SUGGESTION`, `EMPHASIS`, `ACKNOWLEDGMENT`, `OBVIOUSNESS` | Closed-class (sentence-final particles) | Pragmatic function of sentence-final particle |
| `construction` | `BA`, `BEI`, `BI` | Closed-class (把, 被, 比) | Special grammatical construction marker |
| `classifier` | `GEN`, `YES` | Closed-class (classifiers) | Word is a measure word/classifier (GEN for default 个) |
| `negation` | `BU`, `MEI`, `BIE` | Closed-class (不, 没, 别) | Type of negation |
| `modal` | `ABILITY`, `PERMISSION`, `OBLIGATION`, `VOLITION` | Closed-class (auxiliaries) | Modal type |
| `degree` | `COMP`, `SUPER` | Closed-class (更, 最) | Degree (expressed by free adverbs, not inflection) |
| `person` | `1`, `2`, `3` | Closed-class (pronouns) | Person (on pronouns only, not on verbs) |
| `gender` | `MASC`, `FEM`, `NEUT` | Closed-class (他/她/它) | Gender (written distinction only; not grammatical gender) |
| `deixis` | `PROX`, `DIST` | Closed-class (这, 那) | Proximal vs. distal demonstrative |
| `interrog` | `YES` | Closed-class (谁, 什么, 哪, etc.) | Interrogative word |
| `reflex` | `YES` | Closed-class (自己) | Reflexive pronoun |
| `register` | `POLITE` | Closed-class (您) | Register marking |

### Tags That Do NOT Exist

The following grammatical categories, present in other engines, have **no corresponding tags** in the Mandarin engine because these concepts do not exist in Mandarin morphology:

| Absent Tag | Present In | Why Absent in Mandarin |
|-----------|-----------|----------------------|
| `tense` | English, Arabic, Turkish, Spanish, German | Mandarin has no tense morphology. Time is expressed lexically (昨天 "yesterday", 明天 "tomorrow") or inferred from context. |
| `mood` | Arabic, Turkish, Spanish, German | No morphological mood. Modal meaning is expressed by auxiliary verbs (会, 能, 应该). |
| `voice` | Arabic, Turkish | No passive morphology. Passive is expressed by the 被 construction (a syntactic pattern, tagged as `construction: BEI`). |
| `case` | Arabic, Turkish, German | No case system whatsoever. Grammatical role is determined entirely by word order. |
| `definiteness` / `def` | Arabic, German | No articles. Definiteness is contextual or marked by demonstratives (这/那). |
| `agreement` | Arabic, Spanish, German | No agreement of any kind. Adjectives, verbs, and determiners do not agree with nouns. |

This absence table is the single most important diagnostic of Mandarin's isolating typology. The tag inventory is sparse because Mandarin words genuinely carry almost no grammatical information beyond their lexical identity and POS.

### Bundle Count

**Estimated unique feature bundles: 15-25.** This is the **LOWEST** of all 9 languages in the experiment, by design.

The bundle space is small because:

1. **Content word bundles:** Most nouns, verbs, and adjectives receive `no_features` (POS = UNKNOWN, no tags). This single bundle accounts for the majority of content word tokens. Estimate: 1 bundle.
2. **Inflected verb bundles:** `aspect=PERF`, `aspect=DUR`, `aspect=EXP` -- 3 bundles. This is the entirety of Mandarin verbal "inflection."
3. **Plural bundle:** `num=PL` -- 1 bundle (only for animate nouns with 们).
4. **Ordinal bundle:** `role=ORDINAL` -- 1 bundle.
5. **Closed-class bundles:** Each unique tag combination in the closed-class dictionary produces one bundle. Many closed-class words share the same bundle (e.g., all conjunctions with empty tags share one bundle). Estimate: ~10-15 unique bundles from closed-class entries.
6. **Derivational bundles:** Words that match a derivational suffix/prefix but have no inflection receive `no_features` after stripping. No additional bundles.

**Projected total: ~18-22 unique bundles.**

For comparison:
- Arabic: 80-120 bundles (rich fusional morphology)
- Turkish: 50-80 bundles (deep agglutinative stacking)
- German: 40-60 bundles (case + gender + number agreement)
- Spanish: 35-50 bundles (verb conjugation + gender/number)
- English: 15-25 bundles (minimal inflection)
- **Mandarin: 15-25 bundles (near-zero morphology)**

Mandarin and English are expected to produce similar bundle counts, both at the low end. The key difference is that English's bundles come from productive inflectional rules (plural, tense, aspect, degree), while Mandarin's bundles come almost entirely from the closed-class dictionary (particles and function words). This distinction matters for the experimental hypothesis: morphology-aware tokenization should help English slightly (compressing regular inflections) but help Mandarin not at all (there is nothing to compress).

## Config Files

| File | Entries | Structure | Purpose |
|------|---------|-----------|---------|
| `zh_particles.json` | ~200 | `Dict[surface_form, {pos, tags, gloss}]` | All closed-class function words: particles, prepositions, conjunctions, pronouns, adverbs, negation, auxiliaries, determiners, numbers |
| `zh_classifiers.json` | ~50 | `List[{surface, gloss, semantic_class, examples}]` | Classifier/measure word inventory with semantic classification (animate, flat, long, vehicle, etc.) and example noun pairings |

No irregulars file is needed -- there are no irregular inflectional forms in Mandarin.
No compounds file is needed -- compounds are not split.
No derivations file is needed -- the ~13 derivational rules are hardcoded (the list is short and stable).

## Validators

### Word-level: `check_morph_sequence_zh`

Validates that each token's tag bundle is internally consistent for its POS. The allowed tag keys per POS are:

| POS | Allowed Tag Keys |
|-----|-----------------|
| `NOUN` | `num` |
| `VERB` | `aspect`, `role` |
| `ADJ` | (none expected) |
| `ADV` | `negation`, `degree`, `aspect` |
| `PRON` | `person`, `num`, `gender`, `deixis`, `interrog`, `reflex`, `register` |
| `PART` | `aspect`, `role`, `particle_type` |
| `ADP` | `construction` |
| `CLF` | `classifier` |
| `AUX` | `modal` |
| `NUM` | `role` |

Additional constraint:
- If `aspect` is present on a VERB, it must be one of `PERF`, `DUR`, `EXP`. No other aspect values are valid.
- If `negation` is present, it must be one of `BU`, `MEI`, `BIE`.

The function returns `True` if all tokens pass, `False` on first violation.

### Sentence-level: `validate_sentence_structure_zh`

Validates cross-token structural constraints:

1. **Classifier-noun ordering:** If a CLF token appears, the next content word (skipping adverbs/particles) should be a NOUN or PRON. Violation message: `"classifier not followed by noun: {surface}"`.
2. **Ba-construction structure:** If a token has `construction=BA`, there must be a VERB somewhere after it in the sentence. Violation message: `"把 without following verb"`.
3. **Bei-construction structure:** If a token has `construction=BEI`, there must be a VERB somewhere after it. Violation message: `"被 without following verb"`.
4. **Aspect particle attachment:** If a PART token has an `aspect` tag, the preceding content word should be a VERB. Violation message: `"aspect particle not preceded by verb: {surface}"`.
5. **Double negation check:** If two consecutive tokens both have `negation` tags, flag as suspicious (though 不...不 "not...not" double negation does exist in valid Mandarin). Warning only, not a hard failure.

Returns a `(bool, str)` tuple: `(True, "ok")` on success, or `(False, error_message)` on failure.

Both validators are called in `analyze_sentence()`, with their results ANDed together to produce the final validity flag.

## Known Limitations

1. **Word segmentation errors propagate silently.** The engine trusts the segmenter output completely. Over-segmentation (splitting a word into characters) and under-segmentation (merging adjacent words) both produce incorrect analyses. The engine cannot detect or correct these errors.

2. **Compounds are not split (by design).** Multi-character content words like 电脑, 火车, 手机 are treated as atomic. This is intentional but means the engine discovers no internal structure in the majority of Mandarin vocabulary.

3. **了 (le) ambiguity is not resolved.** At the word level, the engine cannot distinguish verbal-aspect 了 (perfective: 吃了 "ate") from sentence-final 了 (change of state: 下雨了 "it's started raining"). Both receive `aspect=PERF`. Resolving this requires sentence-level or discourse-level analysis beyond the engine's scope.

4. **Tone is not represented.** Mandarin is a tonal language (4 tones + neutral), but tonal information is not present in the character-based orthography and is not modeled by the engine.

5. **Classical Chinese / literary forms are not handled.** The engine targets modern standard Mandarin (普通话). Literary Chinese (文言文) uses different grammar, vocabulary, and function words that the engine does not recognize.

6. **Chengyu (成语, 4-character idioms) are not identified.** Four-character fixed expressions like 画蛇添足 (draw snake add feet = "gild the lily") are not recognized as morphological or phraseological units. They are analyzed character-by-character or as a single UNKNOWN token depending on segmenter behavior.

7. **Resultative and directional verb compounds are not decomposed.** Compounds like 打开 (hit+open = "to open"), 跑出来 (run+exit+come = "to run out"), 看见 (look+perceive = "to see") are treated as atomic verbs. These are productive in Mandarin and arguably represent verb-complement morphology, but decomposing them would require a verb-complement dictionary and introduce ambiguity with homographic sequences.

8. **Coverb/preposition vs. verb ambiguity.** Words like 在, 给, 到, 用 function as both full verbs and grammatical prepositions. The engine assigns one POS (typically ADP for frequent prepositions) regardless of context. This is a significant source of POS error.

9. **Classifier ambiguity.** Characters like 只 (CLF "animal classifier" vs. ADV "only") and 把 (CLF "graspable things" vs. ADP "patient marker") have multiple grammatical functions. The engine assigns one reading; context-dependent disambiguation is not performed.

10. **No handling of reduplication.** Adjective reduplication (高高的 "very tall"), verb reduplication (看看 "take a look"), and AABB patterns (高高兴兴 "very happy") are productive morphological processes in Mandarin but are not recognized or tagged by the engine.

11. **Spoken vs. written register differences.** Spoken Mandarin uses particles and constructions that differ from written Mandarin. The engine does not distinguish registers (e.g., spoken 啥 vs. written 什么 for "what").

## Test Plan

Testing for the Mandarin engine is lighter than other engines, reflecting the minimal morphological complexity.

| Test File | Test Count | Categories Covered |
|-----------|-----------|-------------------|
| `test_zh_engine_aspect.py` | 30 | Aspect particles 了/着/过 as free particles and as suffixes; interaction with different verb types; ambiguous 了 cases |
| `test_zh_engine_closed_class.py` | 80 | All closed-class categories: particles, prepositions, conjunctions, pronouns, negation, adverbs, classifiers, determiners, numbers, auxiliaries; correct POS and tag assignment |
| `test_zh_engine_derivation.py` | 30 | All prefix patterns (老/小/阿), all suffix patterns (子/儿/头/家/员/者/化/性/式); derivation chain recording; lexicalized forms |
| `test_zh_engine_plural.py` | 15 | 们 stripping on pronouns and animate nouns; rejection on inanimate nouns; interaction with closed-class pronoun entries |
| `test_zh_engine_edge_cases.py` | 30 | Segmentation artifacts (single characters, over-long tokens); punctuation handling; mixed script (Chinese + Latin); numbers and dates; empty input |
| `test_zh_engine_adversarial.py` | 30 | Homograph ambiguity (只/把/在/了); non-standard segmentation; classical Chinese characters; rare classifiers; boundary conditions for stripping rules |

**Total: ~215 tests across 6 files.**

This is the lowest test count of all 9 engines, reflecting the minimal number of rules to test. For comparison: Arabic has ~350 tests, Turkish has ~300, English has 177. The Mandarin engine has fewer rules, fewer edge cases, and fewer possible interactions between rules -- precisely because the language has almost no morphology to model.

## Experimental Role: The Control

This section summarizes why the Mandarin engine exists and what it is expected to demonstrate.

### Hypothesis

The morph-aware tokenization method improves LLM efficiency in proportion to a language's morphological complexity. Languages with rich morphology (Arabic, Turkish) should show the largest gains because morph-aware tokenization compresses redundant grammatical information. Languages with minimal morphology (Mandarin, English) should show near-zero gains because there is almost nothing to compress.

### Mandarin as Control

Mandarin is the ideal control for this experiment because:

1. **Near-zero morphological information per token.** Most Mandarin words produce the `no_features` bundle. The morph-aware tokenizer has almost no additional information to exploit.
2. **No inflectional paradigms to compress.** In Arabic, a single verb root can generate hundreds of surface forms (conjugation x voice x mood x person x number x gender). A morph-aware tokenizer can map all these forms back to a shared root+bundle, dramatically reducing effective vocabulary. In Mandarin, a verb has exactly one form. There is nothing to map back.
3. **No agreement to exploit.** In German or Spanish, adjective-noun agreement creates predictable co-occurrence patterns that morph-aware tokenization can compress. Mandarin has no agreement of any kind.
4. **Grammar lives in word order, not word form.** A morph-aware tokenizer adds information about word-internal structure. But Mandarin's grammatical information is in word-external structure (syntax). The tokenizer cannot capture this.

### Expected Result

- **Efficiency gain: ~0% (within noise).**
- If the experiment shows 0% gain for Mandarin but 15%+ gain for Arabic, this confirms that the gains are specifically due to morphological compression, not an artifact of the method.
- If the experiment shows significant gains for Mandarin (>5%), this would be surprising and would suggest that the method captures something beyond morphology (e.g., semantic clustering from POS tags, or vocabulary reduction effects). This would weaken the morphological interpretation of gains in other languages.

### Bundle Count as Diagnostic

The bundle count directly measures how much grammatical information the engine extracts per token. The predicted ranking:

| Language | Predicted Bundles | Typology |
|----------|------------------|----------|
| Arabic | 80-120 | Fusional (root-and-pattern) |
| Turkish | 50-80 | Agglutinative |
| German | 40-60 | Fusional (case + gender) |
| Spanish | 35-50 | Fusional (conjugation) |
| Russian | 35-50 | Fusional (case + aspect) |
| Japanese | 25-40 | Agglutinative (verb) + isolating (noun) |
| English | 15-25 | Analytic (minimal inflection) |
| **Mandarin** | **15-25** | **Isolating (near-zero morphology)** |

Mandarin's low bundle count is not a deficiency of the engine design. It is an accurate reflection of the language's typological position. The engine is designed to produce minimal bundles because the language genuinely carries minimal morphological information per word. This is the entire point.
