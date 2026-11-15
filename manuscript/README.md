# Manuscript

The paper has **one source** and **two builds**.

```
manuscript/
├── tex/                  ← THE source. Edit text here and nowhere else.
│   ├── main.tex          ← development build (article class); this is the public PDF
│   ├── references.bib    ← the only bibliography
│   └── sections/         ← sec_01_abstract.tex … sec_08_conclusion.tex
├── tex_cambridge/        ← journal build: cup-journal.cls preamble + end matter only;
│   └── main.tex             it \input{}s ../tex/sections/ and reads ../tex/references.bib
└── figures/              ← PDFs/PNGs both builds include
```

Because `tex_cambridge/` holds no copy of the text, the submission can never drift
from the development version. Anything journal-specific (front matter, the
Funding / Ethics / Author Contributions statements, biblatex settings) lives in
`tex_cambridge/main.tex`.

## Development build (public PDF)

XeLaTeX is required for the Arabic and Mandarin script.

```bash
cd manuscript/tex
xelatex main && bibtex main && xelatex main && xelatex main
```

Deploying it to https://alt.llm.samhoustonlabs.tech/paper.pdf is a manual copy on
the VPS: back up `/var/www/paper/main.pdf`, then replace it with `main.pdf`.

## Cambridge build (submission)

```bash
cd manuscript/tex_cambridge
xelatex main && biber main && xelatex main && xelatex main
```

Needs `biber` and the fonts the class loads (including `fbb`). The VPS lacks
`fbb`, so this build is run on the author's machine.

## Conventions

- Floats use `[tbp]`; never `[H]` or a per-float `\FloatBarrier`. `placeins`
  with `[section]` keeps every table and figure inside its own section.
- No run-in `\paragraph{}` headings in the body; topics are carried by the
  opening sentence.
- No em-dashes. British spelling. Languages always in the order ZH, EN, TR, AR.
- Arabic: full tashkil by default, but a word cited for its ambiguity stays
  bare, and roots are bare hyphenated skeletons (see `../CLAUDE.md`).

## Figures

`../morph_efficiency_project/scripts/make_figures_p2.py` regenerates the Phase 2
figures from `../results/`; `make_figures.py` regenerates the pilot-era ones
from `../results/analysis/`.

Pre-submission checklists are in `../docs/`.
