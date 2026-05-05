# Morphological Efficiency Project — Phase 2 Roadmap

**Goal:** Determine the mathematical relationship between a language's morphological
structure and the computational cost of training a capable language model on it.

**Ultimate vision:** Can morphology-aware training shrink models enough to run
reasoning-capable LMs on consumer edge devices?

**Author:** Sameh AbuRadi
**Started:** April 2026

---

## The 9 Languages

### Spectrum (isolating → agglutinative)

| # | Language | Code | Typology | Key morphological feature |
|---|----------|------|----------|--------------------------|
| 1 | Mandarin | zh | Isolating-analytic | Near-zero morphology; tonal; classifiers; aspect particles |
| 2 | English | en | Semi-fusional analytic | Minimal inflection; word-order grammar; irregular suppletives |
| 3 | German | de | Irregular fusional | Case system; compounds; separable verbs; irregular plurals |
| 4 | Spanish | es | Regular fusional | Rich but predictable verb conjugation; gender agreement |
| 5 | Hungarian | hu | Agglutinative-fusional hybrid | Vowel harmony; 18 cases; definite/indefinite conjugation |
| 6 | Turkish | tr | Pure agglutinative | Strict suffix slots; vowel harmony; evidentiality |

### Outliers (mechanisms not on the spectrum)

| # | Language | Code | Typology | Key morphological feature |
|---|----------|------|----------|--------------------------|
| 7 | Arabic | ar | Templatic (root-and-pattern) | Triconsonantal roots + vocalic patterns; clitics |
| 8 | Swahili | sw | Classificatory (Bantu noun class) | 15+ noun classes; agreement prefixes cascade across clause |
| 9 | Basque | eu | Polypersonal + ergative | Tri-personal verb agreement; ergative-absolutive alignment; language isolate |

### Existing engines (from Phase 1)

- `en_engine.py` — English (audit needed)
- `ar_engine.py` — Arabic (audit needed)
- `tr_engine.py` — Turkish (audit needed)

### New engines to build (6)

- `zh_engine.py` — Mandarin
- `de_engine.py` — German
- `es_engine.py` — Spanish
- `hu_engine.py` — Hungarian
- `sw_engine.py` — Swahili
- `eu_engine.py` — Basque

---

## Phases Overview

```
Phase 0:  Audit & Foundation                    ✅ COMPLETE (2026-04-04)
Phase 1:  Engine Design                         ✅ COMPLETE (2026-04-05)
Phase 1b: Engine Design Infographics (9 pages)  ✅ COMPLETE (2026-04-05)
Phase 2:  Engine Build & Test                   ✅ COMPLETE (2026-04-06)
Phase 3:  Mini Experiment (9 langs)             ⬜ NEXT
Phase 4:  Analysis & Formula Search             ⬜ Pending
Phase 5:  Small Scale (20M/100M)                ⬜ Pending
Phase 6:  Medium Scale (60M/1.2B)               ⬜ Pending (if patterns hold)
Phase 7:  Predictive Model & Write-up           ⬜ Pending
```

### Current status (2026-04-06)

**5,079 tests passing across 9 engines. 0 failures.**

| Engine | Lang | Lines | Tests | Config files |
|--------|------|-------|-------|-------------|
| en_engine.py | English | ~200 | 1,269 | en_irregulars, en_derivations, en_compounds, en_phrasal_verbs |
| ar_engine.py | Arabic | ~1,900 | 1,160 | ar_roots, ar_templates, ar_vocab_space |
| tr_engine.py | Turkish | ~350 | 449 | tr_suffixes, tr_derivations |
| es_engine.py | Spanish | ~855 | 484 | es_irregulars, es_derivations |
| zh_engine.py | Mandarin | ~185 | 360 | zh_particles, zh_classifiers |
| de_engine.py | German | ~600 | 458 | de_irregulars, de_stems, de_derivations |
| hu_engine.py | Hungarian | ~500 | 353 | hu_suffixes, hu_irregulars, hu_derivations |
| sw_engine.py | Swahili | ~600 | 232 | sw_classes, sw_extensions, sw_irregulars |
| eu_engine.py | Basque | ~500 | 314 | eu_auxiliary, eu_cases, eu_derivations |

**Next step:** Phase 3 — adapt mini_experiment/run_mini.py for 9 languages, train 18 models.

Total: ~22-33 weeks depending on engine complexity and VPS speed.

---

## Phase 0: Audit & Foundation

**Duration:** ~1 week
**Goal:** Ensure the existing 3 engines are solid, and establish the universal
interface contract that all 9 engines must follow.

### 0.1 Audit existing engines

For each of en_engine.py, ar_engine.py, tr_engine.py:

- [ ] **Correctness audit**: Run all 2,150 existing tests. Identify any failures or
      edge cases that were deferred.
- [ ] **Coverage audit**: For each engine, list which morphological phenomena
      are handled and which are explicitly out of scope. Document gaps.
- [ ] **Interface conformance**: Verify each engine's analyze() and
      analyze_sentence() match the contract in shared.py exactly.
- [ ] **Performance audit**: Measure tokens/second on a 10K-sentence sample.
      This sets the baseline for engine speed expectations.
- [ ] **Bug fixes**: Fix any issues found. Do not add new features.

### 0.2 Define universal engine contract

Formalize the interface that all 9 engines must implement:

```python
class MorphEngine:
    """Universal interface for all grammar engines."""

    lang: str                    # ISO 639-1 code
    closed_class: Dict[str, Dict[str, str]]  # Particles, prepositions, etc.

    def analyze(self, word: str) -> TokenInfo:
        """Decompose a single word into root + tags."""

    def analyze_sentence(self, sentence: str) -> Tuple[List[TokenInfo], bool, str]:
        """Analyze all words in a sentence. Returns (tokens, valid, message)."""
```

Every engine must follow the three-step decomposition:

- **Step A — Inflectional stripping**: Remove inflectional affixes, record tags.
- **Step B — Derivational detection**: Identify derivational morphology.
- **Step C — Root extraction**: Find the base root/stem.

Languages where this pattern doesn't naturally apply (e.g., Mandarin) should
implement the steps as pass-throughs with appropriate documentation.

### 0.3 Define morphological property extraction

For the formula search (Phase 4), each engine must be able to report its own
morphological properties. Define the standard property set:

| Property | Description | How to compute |
|----------|-------------|----------------|
| `bundle_count` | Total unique feature bundles | len(engine.vocab.bundle2id) after processing corpus |
| `avg_bundles_per_word` | Mean features per token | Sum of tag counts / total words in sample |
| `max_paradigm_depth` | Max features in one word | Max tag count across all words in sample |
| `concatenativity` | Fraction of morphology that is concatenative (prefix/suffix) vs. non-concatenative (infix/template/tone) | Manual classification per engine |
| `agreement_span` | How far agreement reaches in a sentence | Mean distance (in words) between agreeing elements |
| `vocab_compression` | Morph tokens / BPE tokens for same content | Computed during preprocessing |
| `closed_class_ratio` | Fraction of running text that is closed-class | Computed during preprocessing |

### 0.4 Standardize config structure

Create a config template that each language must have:

```
configs/
  {lang}_grammar.json      # Roots, templates, suffix tables, etc.
  training_config_{lang}.json  # Data sources, training hyperparams
```

### 0.5 Update shared.py if needed

- Ensure TokenInfo.clitics can represent all affix types across all 9 languages
  (prefixes, suffixes, infixes, circumfixes, noun class prefixes, etc.)
- Add infix support if not present (needed for Basque, possibly Swahili)
- Ensure validators are pluggable by language code

**Deliverables:**
- [ ] Audit report for en/ar/tr engines (issues + fixes)
- [ ] Universal engine contract document
- [ ] Morphological property extraction spec
- [ ] Updated shared.py (if changes needed)
- [ ] Config templates for new languages

---

## Phase 1: Engine Design

**Duration:** ~1 week
**Goal:** Write the linguistic design spec for all 6 new engines before writing
any code. Each spec defines Steps A/B/C, the tag inventory, config files
needed, and known edge cases.

### Design template (for each language)

```
## {Language} Engine Design Spec

### Morphological overview
- Type: [isolating / fusional / agglutinative / etc.]
- Key phenomena: [list]

### Closed-class intercept
- Which words bypass Steps A/B/C entirely
- Estimated count

### Step A: Inflectional stripping
- What affixes are stripped
- In what order
- What tags are recorded
- Special rules (harmony, sandhi, etc.)

### Step B: Derivational detection
- What derivational processes exist
- How they're identified

### Step C: Root extraction
- How the final root/stem is determined

### Tag inventory
- Complete list of tags and their possible values
- Expected bundle count

### Config files needed
- What lookup tables / grammar resources are required
- Sources for these resources

### Known edge cases and limitations
- What the engine will NOT handle
- Why

### Test plan
- Categories of test cases
- Estimated test count
```

### 1.1 Mandarin (zh) design

Key challenge: Mandarin is isolating. "Morphology-aware" means something
fundamentally different here. The engine should:

- Tag POS (noun, verb, adjective, adverb, classifier, particle, etc.)
- Identify aspect particles (了 le, 着 zhe, 过 guo) and their grammatical role
- Identify classifiers/measure words and link to noun
- Identify resultative/directional verb compounds (打开, 跑出来)
- Handle 把 (ba) and 被 (bei) constructions as structural markers
- Treat each character/word as one token with POS + function tags

Expected bundle count: ~15-25 (lowest of all 9 — this IS the point)
Expected improvement: ~0% (serves as control confirming the effect is real)

### 1.2 German (de) design

Key challenge: Compounds (Donaudampfschifffahrtsgesellschaft), case system,
separable verbs, irregular plurals.

- Step A: Strip case/number/gender suffixes from nouns/adjectives/articles;
  strip person/number/tense from verbs; handle strong/weak/mixed declension
- Step B: Compound splitting (longest-match against dictionary); derivational
  affixes (ver-, be-, ent-, -ung, -keit, -lich, etc.)
- Step C: Extract base stem

Config needed: Irregular verb table, irregular plural table, compound dictionary
Expected bundle count: ~60-80

### 1.3 Spanish (es) design

Key challenge: Regular but rich verb conjugation (6 persons × 14+ tenses),
gender/number agreement on nouns/adjectives, clitic pronouns.

- Step A: Strip verb conjugation suffixes (regular -ar/-er/-ir paradigms);
  strip noun/adj gender (-o/-a) and number (-s/-es) markers;
  strip clitic pronouns (me, te, le, lo, la, nos, os, les, los, las, se)
- Step B: Derivational affixes (des-, in-, -ción, -mente, -idad, -oso, etc.)
- Step C: Extract infinitive stem (verbs) or root (nouns)

Config needed: Irregular verb table (~400 verbs), irregular noun plurals
Expected bundle count: ~80-100

### 1.4 Hungarian (hu) design

Key challenge: 18 cases, vowel harmony, definite vs. indefinite conjugation,
possessive suffixes, fusional elements within agglutinative structure.

- Step A: Strip case suffixes (-ban/-ben, -nak/-nek, -ból/-ből, etc.);
  strip possessive suffixes (-m, -d, -ja/-je, etc.);
  strip verb person/number/definiteness suffixes;
  vowel harmony validation (back/front, like Turkish but with rounding)
- Step B: Derivational suffixes (-ság/-ség, -talan/-telen, -ás/-és, etc.)
- Step C: Extract stem with vowel-shortening/lengthening rules

Config needed: Suffix inventory with harmony variants, irregular verbs
Expected bundle count: ~90-120

### 1.5 Swahili (sw) design

Key challenge: Noun class system (15+ classes), agreement prefixes cascade
from noun through verb, adjective, demonstrative, possessive.

- Step A: Strip noun class prefix (m-/wa-, ki-/vi-, etc.);
  strip verb agreement prefixes (subject + tense + object);
  strip verb extensions (-ish-, -an-, -w-, -ik-);
  handle negation (ha-, -ku-, -to-)
- Step B: Derivational processes (verbal extensions change valence/voice)
- Step C: Extract verb root or noun stem

Config needed: Noun class table, verb conjugation prefix table, extension list
Expected bundle count: ~100-140 (high due to class × person × tense combinations)

### 1.6 Basque (eu) design

Key challenge: Tri-personal auxiliary agreement, ergative case marking,
14 cases, language isolate with no cognates to lean on.

- Step A: Strip case suffixes (-k ERG, -a ABS, -ri DAT, -n INES, etc.);
  decompose synthetic verb forms (if any — most Basque verbs use
  periphrastic construction: participle + auxiliary);
  decompose auxiliary into person-agreement slots
  (ERG slot + ABS slot + DAT slot);
  strip plural marker (-k/-ek)
- Step B: Derivational suffixes (-tasun, -garri, -tzaile, -keta, etc.)
- Step C: Extract root

Config needed: Auxiliary agreement paradigm (~600 forms), case suffix table,
  irregular synthetic verbs (izan, ukan, egon, joan, etorri, etc.)
Expected bundle count: ~150-200 (highest of all 9 — tri-personal agreement
  creates a combinatorial explosion of person×number×case slots)

**Deliverables:**
- [ ] Design spec for each of the 6 new engines
- [ ] Approved tag inventories (no changes after approval)
- [ ] Config file requirements and data sources identified
- [ ] Test plan outlines for each engine

---

## Phase 1b: Engine Design Infographics

**Duration:** ~3-5 days
**Goal:** Build 9 interactive HTML5 infographic pages — one per language engine —
that visually explain how each grammar engine works. These are public-facing
assets for demonstrating the depth of the project and supporting an IP patent
filing in Germany.

**Trigger:** Phase 1b starts immediately after Phase 1 is complete and all 9 engine
design specs are finalized. The infographics visualize the *designs*, not the code.

### 1b.1 Design principles

Each page should:

- **Explain the engine to a non-expert.** No linguistics degree required. Use
  animations, color-coded decompositions, and step-by-step walkthroughs.
- **Show a real word being decomposed** through Steps A → B → C, animated
  so the viewer sees clitics peeling off, suffixes detaching, roots emerging,
  and tags appearing — in the native script of the language.
- **Highlight what makes each language unique.** The page for Turkish should
  feel fundamentally different from the page for Arabic or Basque. Each
  language has its own visual metaphor.
- **Use consistent branding** across all 9 pages (shared color palette, nav,
  typography) but with per-language accent colors and motifs.

### 1b.2 Tech stack

| Technology | Purpose |
|------------|---------|
| HTML5 + CSS | Structure and layout |
| TailwindCSS (CDN) | Utility-first styling, responsive design |
| GSAP (CDN) | Timeline-based animations for decomposition sequences |
| Canvas / SVG | Diagrams, morphological tree visualizations, flow charts |

No build step. Each page is a self-contained .html file that opens in a browser.

### 1b.3 Per-page structure

Each of the 9 pages follows this layout:

```
┌─────────────────────────────────────────────┐
│  Header: Language name (native + English)    │
│  Typology badge: "Agglutinative" / etc.      │
│  Morphological complexity meter (visual)     │
├─────────────────────────────────────────────┤
│  Section 1: "How {Language} builds words"    │
│  → Animated diagram of the language's        │
│    word-building mechanism                   │
│  → e.g., Turkish: suffix slot chain          │
│    Arabic: root + template overlay           │
│    Basque: verb with 3 agreement slots       │
├─────────────────────────────────────────────┤
│  Section 2: "Live decomposition"             │
│  → Pick a word (or use default)              │
│  → GSAP animation: Step A → B → C            │
│  → Tags appear as the word is stripped       │
│  → Final result: root + feature bundle       │
├─────────────────────────────────────────────┤
│  Section 3: "The tag inventory"              │
│  → Visual grid of all possible tags          │
│  → Grouped by category (nominal, verbal)     │
│  → Count badge: "63 bundles" / "270 bundles" │
├─────────────────────────────────────────────┤
│  Section 4: "Why this matters for AI"        │
│  → BPE vs. morph-aware comparison            │
│  → Token count visual: same sentence,        │
│    two tokenizations, side by side            │
│  → Information density metaphor              │
├─────────────────────────────────────────────┤
│  Footer: Project branding + navigation       │
│  → Links to other 8 language pages           │
└─────────────────────────────────────────────┘
```

### 1b.4 Visual metaphors per language

| Language | Visual metaphor | Animation concept |
|----------|----------------|-------------------|
| Mandarin | Single blocks on a shelf — each word is one block, no assembly | Blocks sit still; particles float in as modifiers |
| English | Light assembly line — a few parts snap together | Short conveyor belt, 1-2 suffixes click on |
| German | Workshop with compound press — parts fuse and stack | Multiple pieces slam together; irregular forms glow differently |
| Spanish | Conjugation wheel — verb root in center, endings orbit | Wheel spins to select person/tense; endings snap to root |
| Hungarian | Suffix train — carriages attach in strict order | Train cars couple one by one; vowel harmony shown as color matching |
| Turkish | Suffix assembly line — longest chain, strict slot order | Conveyor belt with labeled slots; suffixes drop into position; harmony pulses |
| Arabic | Root constellation — 3 consonants in space, template wraps around them | Stars (root letters) appear; vowel pattern weaves between them; clitics orbit |
| Swahili | Agreement cascade — noun class prefix triggers chain reaction | Domino effect: noun prefix tips over, verb/adj/det prefixes follow |
| Basque | Three-lane highway — subject/object/indirect object converge into one verb | Three colored streams merge into single verb form |

### 1b.5 IP protection measures

Since these pages will be publicly deployed and the underlying engine designs
represent patentable IP, implement the following protection layers:

**Layer 1 — Code obfuscation:**
- Minify all JavaScript (remove whitespace, shorten variable names)
- Obfuscate GSAP timeline logic and animation parameters
- Encode string literals (tag names, linguistic terms) as hex/base64 arrays
  that are decoded at runtime
- Split logic across multiple obfuscated functions with misleading names

**Layer 2 — Anti-inspection:**
- Disable right-click context menu (return false on contextmenu event)
- Disable F12 / Ctrl+Shift+I / Ctrl+Shift+J / Ctrl+U (keyboard intercept)
- Detect DevTools open via window.outerHeight/debugger timing checks;
  if detected, replace page content with a notice
- Disable text selection on critical content sections (user-select: none)
- Disable drag on images and SVGs

**Layer 3 — Content protection:**
- Render critical diagrams and tag inventories as Canvas (not DOM text) —
  cannot be scraped by DOM inspection or copy-paste
- Use web fonts with custom glyph mappings for sensitive labels —
  what appears as "ROOT" on screen maps to a different codepoint,
  so copy-pasting yields garbled text
- Split SVG paths across multiple layers so inspecting one element
  doesn't reveal the full diagram
- Watermark canvas renders with invisible per-session fingerprint

**Layer 4 — Structural obfuscation:**
- Do not use semantic class names (no `.tag-inventory`, `.root-display`)
- Generate randomized class names at build time (e.g., `.x7f2a`, `.k9m1`)
- Inline critical CSS to prevent stylesheet inspection from revealing structure
- Fragment the HTML: load sections via JavaScript from encoded data blobs,
  not from readable HTML in the source

**Layer 5 — Legal notice:**
- Include visible copyright footer: "© 2026 Sameh AbuRadi. All rights reserved.
  Patent pending (DE)."
- Include invisible metadata watermark in the HTML source
- Include a `<meta name="robots" content="noindex, nofollow, noarchive">`
  to prevent search engine caching of source

**Important caveat:** No client-side protection is unbreakable. A determined
reverse-engineer can always get past JavaScript obfuscation. These measures
are designed to make casual copying and AI-assisted extraction impractical —
raising the effort bar high enough that it's easier to design your own system
than to steal this one. The real IP protection comes from the patent filing.

### 1b.6 Build process

Since the pages should be obfuscated for deployment but readable for
development, maintain two versions:

```
presentation/
  infographics/
    src/                    # Development versions (readable, version-controlled)
      zh.html               # NEVER deployed to public web — local/repo only
      en.html
      de.html
      es.html
      hu.html
      tr.html
      ar.html
      sw.html
      eu.html
    dist/                   # Obfuscated deployment versions (public-facing)
      zh.html
      en.html
      ...
    build.py                # Obfuscation script: src/ → dist/
```

**Deployment rule:** Only `dist/` is ever uploaded to any public server, CDN,
or hosting platform. `src/` lives in the git repo for version control and
collaboration but must never be served on the open internet. Deployment
scripts/CI pipelines must only reference `dist/`.

The `build.py` script handles:
1. Minifying inline JS (terser or custom minifier)
2. Encoding string literals
3. Randomizing class names
4. Injecting anti-inspection code
5. Converting text elements to canvas renders where specified
6. Adding watermarks and legal notices

### 1b.7 Navigation and index

Create an `index.html` landing page that shows all 9 languages as a visual
spectrum with the outliers positioned separately. Clicking a language opens
its infographic page. The spectrum visualization itself serves as a project
overview infographic.

**Deliverables:**
- [ ] 9 interactive HTML5 infographic pages (src/ versions)
- [ ] 9 obfuscated deployment versions (dist/)
- [ ] build.py obfuscation script
- [ ] index.html landing page with spectrum visualization
- [ ] All pages tested on Chrome, Firefox, Safari, mobile

---

## Phase 2: Engine Build & Test

**Duration:** ~5-7 weeks
**Goal:** Implement all 6 new engines with comprehensive test suites.

### Build order (easiest → hardest)

| Order | Language | Estimated effort | Rationale |
|-------|----------|-----------------|-----------|
| 1 | Spanish (es) | 3-4 days | Regular fusional; most predictable paradigms; closest to EN engine pattern |
| 2 | German (de) | 4-5 days | Fusional but irregular; compound splitting adds complexity |
| 3 | Mandarin (zh) | 3-4 days | Simple morphology but novel design (POS/particle tagging) |
| 4 | Hungarian (hu) | 5-6 days | Agglutinative-fusional hybrid; can borrow patterns from TR engine |
| 5 | Swahili (sw) | 6-7 days | Noun class agreement is a new mechanism; cascading prefixes |
| 6 | Basque (eu) | 7-10 days | Tri-personal auxiliaries + ergative alignment; no related engine to borrow from |

### Per-engine workflow

For each language:

1. **Config files first**: Build grammar resource JSONs (root lists, suffix tables,
   paradigm tables, etc.)
2. **Closed-class intercept**: Implement particle/preposition/conjunction lookup
3. **Step A**: Inflectional stripping with tests
4. **Step B**: Derivational detection with tests
5. **Step C**: Root extraction with tests
6. **analyze_sentence()**: Sentence-level analysis
7. **Validators**: check_morph_sequence_{lang} + validate_sentence_structure_{lang}
8. **Smoke test**: Run on 100 real sentences from Wikipedia
9. **Stress test**: Comprehensive coverage of all tag combinations
10. **Regression test**: Lock down known-good outputs

### Test targets per engine

| Engine | Minimum test count | Coverage target |
|--------|-------------------|-----------------|
| es | 300 | All 14 tense paradigms, gender/number, clitics |
| de | 350 | Case system, compound splitting, separable verbs |
| zh | 150 | POS tagging accuracy, aspect particles, classifiers |
| hu | 400 | All 18 cases, vowel harmony, def/indef conjugation |
| sw | 400 | All noun classes, full agreement chains, verb extensions |
| eu | 500 | Auxiliary paradigm coverage, all 14 cases, ergativity |

### Integration checkpoints

After each engine is built:

- [ ] All tests pass
- [ ] Engine can process 1K Wikipedia sentences without crash
- [ ] Bundle count is within expected range from design spec
- [ ] TokenInfo output is compatible with MorphVocab.encode()
- [ ] Run mini experiment for that single language immediately (don't wait for all 9)

**Deliverables:**
- [ ] 6 new engine .py files in engines/
- [ ] 6 new config .json files in configs/
- [ ] ~2,100+ new tests across 6 engines
- [ ] Per-engine smoke test results on real Wikipedia data
- [ ] Incremental mini experiment results as each engine completes

---

## Phase 3: Mini Experiment (9 Languages)

**Duration:** ~1 week (mostly automated, some analysis)
**Goal:** Train 18 models (9 baseline + 9 morph) at 2M params / 5M tokens.

### 3.1 Infrastructure changes

Modify mini_experiment/run_mini.py:

- [ ] Extend LANGS list to all 9 language codes
- [ ] Add Wikipedia source configs for 6 new languages
- [ ] Wire each language to its grammar engine in tokenize_morph()
- [ ] Ensure all output paths use lang code consistently

### 3.2 Data acquisition

For each of the 6 new languages:

| Language | Wikipedia code | Estimated article count | Notes |
|----------|---------------|------------------------|-------|
| Mandarin | zh | ~1.3M | Simplified Chinese; needs word segmentation (jieba or similar) |
| German | de | ~2.8M | Large corpus available |
| Spanish | es | ~1.9M | Large corpus available |
| Hungarian | hu | ~500K | Sufficient |
| Swahili | sw | ~75K | Smallest corpus; may need OPUS/CC-100 supplement |
| Basque | eu | ~400K | Sufficient for mini; tight for larger scales |

Special handling:
- **Mandarin**: Requires word segmentation before analysis (Chinese text has
  no spaces). Use jieba or pkuseg as preprocessor.
- **Swahili**: If Wikipedia alone is insufficient, supplement with OPUS parallel
  corpus or CC-100.
- **Basque**: Monitor corpus quality; Basque Wikipedia has some auto-generated
  articles that may be lower quality.

### 3.3 Training configuration

Identical for all 9 languages (controlled variable):

```
Model:    4 layers, 128 hidden, 4 heads, seq_len=128
Params:   ~2M
Tokens:   5M per language
Batch:    16
LR:       3e-4 (cosine schedule)
Device:   CPU
```

### 3.4 Evaluation

For each of the 18 models:

- Test perplexity
- Tokens per meaning unit
- Unknown token rate
- Bundle accuracy (morph only)
- Training timeseries (loss curves)

### 3.5 Expected results (predictions to test)

| Language | Predicted PPL ratio (morph/base) | Rationale |
|----------|----------------------------------|-----------|
| Mandarin | ~1.00 (no improvement) | Near-zero morphology; nothing to compress |
| English | ~0.99 (negligible) | Known from Phase 1 |
| German | ~0.92-0.96 | Moderate fusional; compounds may help |
| Spanish | ~0.90-0.95 | Regular verb paradigms should compress well |
| Hungarian | ~0.75-0.85 | Rich agglutinative; similar to Turkish but with fusion |
| Turkish | ~0.43 (strong) | Known from Phase 1 |
| Arabic | ~0.86 (moderate) | Known from Phase 1; templatic compression |
| Swahili | ~0.80-0.90 | Noun class agreement should compress significantly |
| Basque | ~0.70-0.80 | Tri-personal = extreme info density per token |

These predictions are testable. If the data contradicts them, that's valuable.

**Deliverables:**
- [ ] Updated run_mini.py supporting 9 languages
- [ ] 18 trained models (9 baseline + 9 morph)
- [ ] mini_summary.json with all 18 results
- [ ] Prediction vs. actual comparison table
- [ ] Learning curve plots for all 9 languages

---

## Phase 4: Analysis & Formula Search

**Duration:** ~1 week
**Goal:** Find the mathematical relationship between morphological properties
and training efficiency.

### 4.1 Extract morphological properties

For each language, compute the property vector from Phase 0.3:

```
lang → [bundle_count, avg_bundles_per_word, max_paradigm_depth,
         concatenativity, agreement_span, vocab_compression,
         closed_class_ratio]
```

### 4.2 Compute efficiency metrics

For each language pair (baseline vs. morph):

- PPL ratio (morph / baseline) — lower is better
- Token compression ratio (morph tokens / baseline tokens for same text)
- Learning curve area ratio (area under morph curve / area under baseline curve)
- Steps-to-threshold ratio (steps to reach baseline's final PPL / total steps)

### 4.3 Regression analysis

With 9 data points, we can test simple models:

1. **Single predictor**: PPL_ratio = f(bundle_count)
2. **Single predictor**: PPL_ratio = f(avg_bundles_per_word)
3. **Two predictors**: PPL_ratio = f(bundle_count, concatenativity)
4. **Composite index**: Define a "morphological density score" as a weighted
   combination of properties, then PPL_ratio = f(density_score)

Use leave-one-out cross-validation to test predictive power.

### 4.4 Hypothesis testing

Key questions the data should answer:

1. **Is the relationship monotonic?** Does more morphological complexity always
   mean more efficiency gain?
2. **Is it linear or nonlinear?** Does the gain plateau, or does it keep growing?
3. **Which property is the dominant predictor?** Bundle count? Paradigm depth?
   Agreement span?
4. **Do outliers (Arabic, Swahili, Basque) follow the same curve as the spectrum
   languages?** If yes, the formula is universal. If no, typology matters
   independently of complexity.
5. **Does Mandarin actually show ~0% improvement?** This is the critical control.

### 4.5 Draft the formula

The target formula shape:

```
efficiency_gain(L) = f(morphological_properties(L))
```

Where efficiency_gain could predict:
- How much smaller a morph-aware model can be vs. BPE for equivalent performance
- How many fewer tokens are needed to reach a performance threshold
- What the compute multiplier is for a given language

This is the core scientific contribution.

**Deliverables:**
- [ ] Morphological property table for all 9 languages
- [ ] Correlation matrix (properties × efficiency metrics)
- [ ] Best-fit model with coefficients
- [ ] Prediction error analysis
- [ ] Draft formula with confidence intervals

---

## Phase 5: Small Scale (20M / 100M)

**Duration:** ~2-3 weeks on VPS
**Goal:** Test whether Phase 4's formula holds at 10× scale.

### 5.1 Configuration

```
Model:    8 layers, 256 hidden, 8 heads, seq_len=256
Params:   ~20M
Tokens:   100M per language
Batch:    32
LR:       3e-4 (cosine schedule, 1000-step warmup)
Device:   CPU (VPS)
```

Estimated time per model: ~8-12 hours on CPU
Total for 18 models: ~6-9 days (sequential)

### 5.2 Data requirements

100M tokens per language. Sources:

| Language | Primary source | Backup source | Feasibility |
|----------|---------------|---------------|-------------|
| Mandarin | Wikipedia | CC-100 | Easy |
| English | Wikipedia | CC-100 | Easy |
| German | Wikipedia | CC-100 | Easy |
| Spanish | Wikipedia | CC-100 | Easy |
| Hungarian | Wikipedia + OPUS | CC-100 | OK |
| Turkish | Wikipedia + OPUS | CC-100 | OK |
| Arabic | Wikipedia + OPUS | CC-100 | OK |
| Swahili | Wikipedia + OPUS + MADLAD-400 | CC-100 | Tight but feasible |
| Basque | Wikipedia + OPUS | CC-100 | Tight but feasible |

### 5.3 Vocabulary management

Lesson from Phase 1: cap morph vocabulary BEFORE training, not after.

- Design a principled vocab cap per language based on:
  - Root frequency (keep top N roots by corpus frequency)
  - Bundle coverage (keep bundles that cover ≥ 99% of running text)
- Target: ≤ 50K morph tokens, ≤ 5% unknown rate per language

### 5.4 Analysis

- Recompute all Phase 4 metrics at this scale
- Test Phase 4's formula predictions against actual results
- Measure prediction error
- Refine formula coefficients if needed

### 5.5 Checkpointing

All training must checkpoint every 500 steps (VPS may reboot).
Save optimizer state for exact resumption.

**Deliverables:**
- [ ] 18 trained models at 20M scale
- [ ] Phase 4 formula validation report
- [ ] Refined formula (if coefficients changed with scale)
- [ ] Learning curves at 20M scale
- [ ] Prediction error: formula(mini) → actual(small)

---

## Phase 6: Medium Scale (60M / 1.2B)

**Duration:** ~8-12 weeks on VPS
**Goal:** Push to the largest feasible scale on available hardware.

### 6.1 Go / No-Go decision

**Only proceed if:**
- Phase 4 formula has R² > 0.7 (explains >70% of variance)
- Phase 5 confirms the pattern holds at 10× scale
- VPS has sufficient disk space (~50GB for all data + models)
- Estimated wall-clock time is acceptable

**Skip or reduce if:**
- Pattern breaks at small scale → investigate why before scaling
- Only run the 3-4 most informative languages instead of all 9

### 6.2 Configuration

```
Model:    12 layers, 512 hidden, 8 heads, seq_len=512
Params:   ~60M
Tokens:   1.2B per language
Batch:    32
LR:       3e-4 (cosine schedule, 2000-step warmup)
Device:   CPU (VPS)
```

Estimated time per model: ~3-5 days on CPU
Total for 18 models: ~8-12 weeks (sequential)

### 6.3 Selective scaling

If full 18-model run is infeasible, prioritize:

1. **Mandarin** (control — must confirm ~0%)
2. **Turkish** (known strong signal — anchor point)
3. **Basque** (predicted strongest — test extreme)
4. **Spanish** (mid-spectrum — test interpolation)
5. **Swahili** (outlier — test universality)

That's 10 models (5 languages × 2 regimes) — cuts time roughly in half.

### 6.4 Corpus feasibility

1.2B tokens per language. Swahili and Basque will need multi-source aggregation:

- Swahili: Wikipedia (~30M tokens) + OPUS (~200M) + CC-100 (~500M) + MADLAD-400
- Basque: Wikipedia (~50M tokens) + OPUS (~150M) + CC-100 (~300M)

May need to reduce target to 500M tokens for these two languages.
Document any asymmetry and account for it in analysis.

**Deliverables:**
- [ ] Go/no-go decision documented with rationale
- [ ] 10-18 trained models at 60M scale (depending on decision)
- [ ] Final formula validation
- [ ] Scale-dependent analysis: does the efficiency gap widen or narrow with scale?

---

## Phase 7: Predictive Model & Write-up

**Duration:** ~1-2 weeks
**Goal:** Formalize findings into a predictive model and presentation.

### 7.1 The formula

Formalize the relationship discovered in Phases 4-6:

```
Given a language L with morphological property vector M(L):

  compute_multiplier(L) = f(M(L))

Where compute_multiplier represents:
  "How many times more tokens does a BPE model need vs. a morph-aware
   model to reach equivalent perplexity?"
```

Test the formula by:
- Holding out one language, predicting its efficiency gain from the other 8
- Checking if the formula generalizes (not overfit to 9 data points)

### 7.2 Edge device projections

Using the formula, project:
- What parameter count a morph-aware model needs to match a 1B BPE model's
  performance, per language
- Whether that parameter count fits on consumer devices (phone: ~1-4GB RAM,
  smart watch: ~256MB-1GB, IoT: ~64-256MB)
- Inference latency estimates at those sizes

### 7.3 Presentation

Update the interactive HTML presentation with:
- 9-language results dashboard
- The formula and its derivation
- Interactive "what-if" tool: pick a language's morphological properties,
  predict efficiency gain
- Edge device feasibility chart

### 7.4 Limitations and future work

Document honestly:
- What the formula can and cannot predict
- Where corpus size limitations affected results
- What a larger experiment (more languages, larger scale, GPU) would add
- The gap between "lower perplexity" and "reasoning capability"

**Deliverables:**
- [ ] Formal predictive model with coefficients and confidence intervals
- [ ] Edge device projection table
- [ ] Updated interactive presentation
- [ ] Limitations document
- [ ] Complete experimental data archive

---

## Engine Design Specifications

### Universal tag vocabulary

All engines must use tags from this controlled vocabulary to ensure
cross-language comparability:

#### Part of Speech (pos)
```
NOUN, VERB, ADJ, ADV, PRON, DET, ADP, CONJ, PART, INTJ, NUM, PUNCT, UNKNOWN
```

#### Nominal features
```
num:     SG, PL, DU (dual — Arabic, Basque)
case:    NOM, ACC, DAT, GEN, LOC, ABL, INS, VOC, ERG, ABS,
         INES, ELAT, ILLAT, ADESS, ABLAT, ALLAT, TRANSL, TERMIN,
         COMIT, CAUSAL, DISTRIB, PARTITIVE
         (not all languages use all cases)
gender:  MASC, FEM, NEUT, COM (common — for languages without gender)
person:  1, 2, 3
poss:    1SG, 2SG, 3SG, 1PL, 2PL, 3PL (possessive agreement)
def:     DEF, INDEF
```

#### Verbal features
```
tense:     PRES, PAST, FUT, PAST_DEF, PAST_NARR, IMPERF, PLUPERF,
           PRET, COND, AOR
aspect:    PERF, IMPERF, PROG, HAB, PROSP
mood:      IND, SUBJ, IMP, OPT, COND, JUSS, POT
voice:     ACT, PASS, CAUS, REFL, RECIP, MIDDLE, ANTIPASS
polarity:  AFF, NEG
evid:      DIRECT, INDIRECT (evidentiality — Turkish, Basque)
```

#### Agreement slots (for polypersonal languages)
```
agr_subj:   1SG, 2SG, 3SG, 1PL, 2PL, 3PL (+ ERG/ABS distinction for Basque)
agr_obj:    1SG, 2SG, 3SG, 1PL, 2PL, 3PL
agr_iobj:   1SG, 2SG, 3SG, 1PL, 2PL, 3PL (Basque only)
```

#### Noun class (Swahili)
```
nc:  1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17, 18
```

#### Derivation
```
derived_chain: List[str]  # e.g. ["PRE_un", "SUF_tion", "SUF_al"]
```

### Per-language engine specs (summary)

| Engine | Steps A/B/C focus | Expected bundles | Config files | Key challenge |
|--------|-------------------|-----------------|--------------|--------------|
| zh | POS + particle + classifier tagging | 15-25 | zh_particles.json, zh_classifiers.json | Word segmentation; near-zero morphology |
| en | Inflection + derivation stripping | 23 | en_irregulars.json, en_derivations.json | Existing engine — audit only |
| de | Case/gender stripping + compound split | 60-80 | de_irregulars.json, de_compounds.json | Compound splitting accuracy |
| es | Verb conjugation + gender/number + clitics | 80-100 | es_irregulars.json, es_verbs.json | 14+ tense paradigms |
| hu | Case + possessive + def/indef conjugation | 90-120 | hu_suffixes.json, hu_verbs.json | Vowel harmony + fusional exceptions |
| tr | Suffix slot stripping + vowel harmony | 63 | tr_suffixes.json | Existing engine — audit only |
| ar | Clitic stripping + template matching + root extraction | 270 | ar_roots.json, ar_templates.json | Existing engine — audit only |
| sw | Class prefix + verb agreement + extensions | 100-140 | sw_classes.json, sw_extensions.json | Cascading agreement chains |
| eu | Case stripping + auxiliary decomposition | 150-200 | eu_auxiliary.json, eu_cases.json | Tri-personal agreement; ergativity |

---

## Infrastructure Requirements

### VPS specifications needed

| Resource | Mini (Phase 3) | Small (Phase 5) | Medium (Phase 6) |
|----------|---------------|-----------------|-------------------|
| CPU | Any modern CPU | 4+ cores | 8+ cores recommended |
| RAM | 4 GB | 8 GB | 16 GB recommended |
| Disk | 5 GB | 50 GB | 200 GB |
| Time | ~3 hours | ~1-2 weeks | ~8-12 weeks |

### Software dependencies

```
Python 3.10+
PyTorch (CPU)
SentencePiece
numpy
```

New dependencies for specific engines:
- **Mandarin**: jieba or pkuseg (word segmentation)
- No other new dependencies — all engines are rule-based

### Checkpointing strategy

All training runs must:
- Save checkpoint every 500 steps (not just every 1000)
- Save optimizer state for exact resumption
- Write timeseries log after every 100 steps (append mode)
- Check for existing outputs before starting (full resumability)

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Swahili/Basque corpus too small for medium scale | Can't train at full 1.2B tokens | Reduce target to 500M; document asymmetry |
| Mandarin word segmentation errors propagate | Noisy morph tokens | Use jieba with custom dictionary; test accuracy on sample |
| Basque auxiliary paradigm too complex to encode | Engine takes >2 weeks | Start with the ~30 most common auxiliary forms; expand iteratively |
| VPS reboots during multi-day training | Lost progress | Checkpoint every 500 steps; auto-resume on restart |
| Formula overfits to 9 data points | Not predictive for other languages | Leave-one-out validation; test on held-out language |
| Morph vocab explosion (repeat of Phase 1) | OOM during training | Design vocab cap from the start; target ≤ 50K, ≤ 5% unk |
| German compound splitting quality | Poor root extraction → noisy morph tokens | Use frequency-based splitting; validate on gold standard |
| Hungarian vowel harmony edge cases | Wrong suffix stripping | Comprehensive test suite; manual review of mismatches |

---

## Success Criteria

### Minimum viable outcome
- All 9 engines built, tested, and producing valid TokenInfo
- Mini experiment completed for all 9 languages
- Clear trend visible in PPL ratio vs. morphological complexity
- Mandarin control confirms ~0% improvement

### Target outcome
- Formula with R² > 0.7 validated at two scales (mini + small)
- Dominant predictor identified (bundle count, paradigm depth, or composite)
- Edge device projections computed for at least 3 languages

### Stretch outcome
- Formula validated at three scales (mini + small + medium)
- Predictive accuracy < 5% error on held-out language
- Interactive presentation updated with 9-language dashboard
- Draft research paper ready for review

---

## File Organization (Phase 2 additions)

```
morph_efficiency_project/
  scripts/engines/
    shared.py          (updated: infix support, universal tag vocab)
    en_engine.py       (audited)
    ar_engine.py       (audited)
    tr_engine.py       (audited)
    zh_engine.py       (NEW)
    de_engine.py       (NEW)
    es_engine.py       (NEW)
    hu_engine.py       (NEW)
    sw_engine.py       (NEW)
    eu_engine.py       (NEW)
  configs/
    zh_particles.json  (NEW)
    zh_classifiers.json (NEW)
    de_irregulars.json (NEW)
    de_compounds.json  (NEW)
    es_irregulars.json (NEW)
    es_verbs.json      (NEW)
    hu_suffixes.json   (NEW)
    hu_verbs.json      (NEW)
    sw_classes.json    (NEW)
    sw_extensions.json (NEW)
    eu_auxiliary.json  (NEW)
    eu_cases.json      (NEW)
  tests/
    zh_morph/          (NEW: ~150 tests)
    de_morph/          (NEW: ~350 tests)
    es_morph/          (NEW: ~300 tests)
    hu_morph/          (NEW: ~400 tests)
    sw_morph/          (NEW: ~400 tests)
    eu_morph/          (NEW: ~500 tests)
```
