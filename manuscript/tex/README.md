# LaTeX build — Cambridge NLP submission

Scaffolding for the manuscript. Produces a complete, compilable document from the current draft state; fully-converted prose for §1 (abstract) and §2 (introduction), plus equation-bearing subsections in §4 and table/figure skeletons in §6. Remaining sections are stubbed with section labels, TODOs, and pointers to their markdown sources.

## Directory layout

```
manuscript/
├── tex/
│   ├── main.tex                  ← top-level document
│   ├── references.bib            ← BibTeX for all §9 citations
│   ├── sections/
│   │   ├── sec_01_abstract.tex   ← fully converted
│   │   ├── sec_02_introduction.tex ← fully converted
│   │   ├── sec_03_related_work.tex ← stub + labels
│   │   ├── sec_04_framework.tex    ← equations + subsection labels
│   │   ├── sec_05_case_studies.tex ← stub
│   │   ├── sec_06_results.tex      ← tables + figures + stubs
│   │   ├── sec_07_discussion.tex   ← stub
│   │   ├── sec_08_conclusion.tex   ← stub
│   │   └── sec_appendices.tex      ← stub
│   └── README.md                 ← this file
├── figures/                      ← PDF + PNG from make_figures.py
│   ├── fig_01_ordinal_validation.{pdf,png}
│   ├── fig_02_alpha_dispersion.{pdf,png}
│   └── fig_03_curve_shift_schematic.{pdf,png}
└── section_*.md                  ← prose drafts to convert
```

## Compile

The draft compiles with XeLaTeX (needed for the Arabic script in §5). Command:

```bash
cd manuscript/tex
xelatex main
bibtex main
xelatex main
xelatex main
```

Or with latexmk:

```bash
cd manuscript/tex
latexmk -xelatex main.tex
```

If Arabic-font warnings appear, install the Amiri font or swap the `\newfontfamily\arabicfont[Script=Arabic]{Amiri}` line in `main.tex` for a font present on the system.

## Installing the Cambridge NLP template

The draft currently uses `\documentclass{article}` as a portable stand-in. Before submission:

1. Obtain the template — either from the journal's Overleaf link or by downloading "NLP LaTeX Files" from https://www.cambridge.org/core/journals/natural-language-processing/information/author-instructions/preparing-your-materials.
2. Copy the Cambridge `.cls` file (typically `cambridge7A.cls` or equivalent) into `manuscript/tex/`.
3. Replace the `\documentclass[11pt, a4paper]{article}` line in `main.tex` with the class name specified by the template's documentation.
4. Verify the bibliography style. The draft uses `plainnat`; the Cambridge template provides its own `.bst` file that should replace it.
5. Remove any package imports that conflict with the Cambridge template's preamble.
6. Compile; adjust as needed.

## Markdown-to-LaTeX conversion pattern

The abstract (`sec_01_abstract.tex`) and introduction (`sec_02_introduction.tex`) are the pattern. The common substitutions:

| Markdown | LaTeX |
|----------|-------|
| `# Section` | `\section{Section}\label{sec:…}` |
| `## Subsection` | `\subsection{Subsection}\label{sec:…-…}` |
| `*italic*` | `\emph{italic}` |
| `**bold**` | `\textbf{bold}` |
| `—` (em dash) | `---` |
| Tables | `tabular` environment inside `table` with `\caption` and `\label` |
| Code (`inline`) | `\texttt{inline}` |
| Math `ρ · H` | `$\rho \cdot H$` |
| Math `log₂` | `$\log_2$` |
| Citation "(Author Year)" | `\citep{authorYEAR}` |
| In-text "Author (Year)" | `\citet{authorYEAR}` |
| Section reference | `\S\ref{sec:…}` |
| Equation reference | `Eq.~\ref{eq:…}` |
| Figure reference | `Figure~\ref{fig:…}` |

Arabic script inside prose uses `{\arabicfont …}` (font family defined in `main.tex`). For longer RTL passages, switch to a `polyglossia`/`arabtex` block depending on the Cambridge template's LaTeX-engine preference.

## Figures

`../../morph_efficiency_project/scripts/make_figures.py` regenerates all three figures from `hl_metrics.json` and `alpha_fit.json`. Run after updating either data source.

```bash
cd ../../
python morph_efficiency_project/scripts/make_figures.py
```

## Citation verification

All BibTeX entries flagged `% VERIFY` need confirmation during Week 1 lit review. See `../../CITATION_VERIFICATION.md` for the full checklist, which items are high-stakes, and the verification workflow.

## Known open items before submission

- Full markdown-to-LaTeX conversion of §3, §5, §7, §8, and appendices.
- Cambridge template installed and preamble swapped.
- Bibliography style replaced with the Cambridge `.bst`.
- Citation verification complete (per `CITATION_VERIFICATION.md`).
- ORCID registered and placed in the `\author{}` block.
- AI-use disclosure and competing-interests statements reviewed.
