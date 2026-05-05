"""Static verification of the LaTeX scaffold at manuscript/tex/.

Checks:
  [1] Every \\input referenced by main.tex points to an existing .tex file.
  [2] Every \\includegraphics references a figure file that exists in figures/.
  [3] Every \\cite{key} has a matching BibTeX entry in references.bib.
  [4] Every \\ref has a matching \\label somewhere in the project.
  [5] Per-file balance of braces and \\begin/\\end environments.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "manuscript" / "tex"
MAIN = ROOT / "main.tex"
BIB = ROOT / "references.bib"
SECTIONS = ROOT / "sections"
FIGS = ROOT.parent / "figures"

errors: list[str] = []
warnings: list[str] = []


def main_text() -> str:
    return MAIN.read_text(encoding="utf-8")


def load_all_tex() -> tuple[list[Path], str]:
    files = [MAIN] + sorted(SECTIONS.glob("*.tex"))
    return files, "\n".join(p.read_text(encoding="utf-8") for p in files)


RX_INPUT   = re.compile(r"\\input\{([^}]+)\}")
RX_FIG     = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")
RX_BIBKEY  = re.compile(r"@\w+\{([^,\s]+),")
RX_CITE    = re.compile(r"\\cite[pt]?\{([^}]+)\}")
RX_CITEALT = re.compile(r"\\citealt\{([^}]+)\}")
RX_LABEL   = re.compile(r"\\label\{([^}]+)\}")
RX_REF     = re.compile(r"\\(?:ref|pageref|eqref|Cref|cref)\{([^}]+)\}")
RX_BEGIN   = re.compile(r"\\begin\{([^}]+)\}")
RX_END     = re.compile(r"\\end\{([^}]+)\}")


def main() -> int:
    # [1] Inputs
    mt = main_text()
    inputs = RX_INPUT.findall(mt)
    print(f"[1] main.tex \\input directives: {len(inputs)}")
    for inp in inputs:
        p = ROOT / (inp + ".tex")
        exists = p.exists()
        size = p.stat().st_size if exists else 0
        status = "OK" if exists else "MISSING"
        print(f"    {inp:40s} {status:8s} ({size} bytes)")
        if not exists:
            errors.append(f"missing input: {inp}.tex")

    files, all_text = load_all_tex()

    # [2] Figures
    print()
    figs = RX_FIG.findall(all_text)
    print(f"[2] Figure references: {len(figs)}")
    for fig in figs:
        p = FIGS / fig
        exists = p.exists()
        status = "OK" if exists else "MISSING"
        print(f"    {fig:40s} {status}")
        if not exists:
            errors.append(f"missing figure: {fig}")

    # [3] BibTeX
    bib_text = BIB.read_text(encoding="utf-8")
    defined_keys = set(RX_BIBKEY.findall(bib_text))
    cited: set[str] = set()
    for m in RX_CITE.finditer(all_text):
        for k in m.group(1).split(","):
            cited.add(k.strip())
    for m in RX_CITEALT.finditer(all_text):
        for k in m.group(1).split(","):
            cited.add(k.strip())

    print()
    print(f"[3] Bibliography:")
    print(f"    BibTeX entries defined: {len(defined_keys)}")
    print(f"    citation keys used:     {len(cited)}")
    for k in sorted(cited - defined_keys):
        print(f"    CITED-NOT-DEFINED: {k}")
        errors.append(f"citation {k} has no BibTeX entry")
    for k in sorted(defined_keys - cited):
        warnings.append(f"BibTeX {k} defined but not cited (ok: stubs unfilled)")

    # [4] Cross-references
    defined_labels = set(RX_LABEL.findall(all_text))
    referenced = set(RX_REF.findall(all_text))
    print()
    print(f"[4] Cross-references:")
    print(f"    \\label targets defined: {len(defined_labels)}")
    print(f"    \\ref targets used:     {len(referenced)}")
    for r in sorted(referenced - defined_labels):
        print(f"    DANGLING: \\ref{{{r}}}")
        errors.append(f"dangling \\ref{{{r}}}")

    # [5] Per-file sanity
    print()
    print(f"[5] Structural sanity:")
    for p in files:
        txt = p.read_text(encoding="utf-8")
        opens, closes = txt.count("{"), txt.count("}")
        begins, ends = RX_BEGIN.findall(txt), RX_END.findall(txt)
        brace_ok = opens == closes
        env_ok = sorted(begins) == sorted(ends)
        status = "OK" if (brace_ok and env_ok) else "CHECK"
        print(f"    {p.name:40s} {status}  braces {opens}/{closes}  env {len(begins)}/{len(ends)}")
        if not brace_ok:
            warnings.append(f"{p.name}: brace imbalance {opens}/{closes}")
        if not env_ok:
            warnings.append(f"{p.name}: env mismatch {sorted(set(begins) ^ set(ends))}")

    print()
    print("=" * 60)
    print(f"errors:   {len(errors)}")
    print(f"warnings: {len(warnings)}")
    for e in errors:
        print(f"  ERR   {e}")
    for w in warnings:
        print(f"  WARN  {w}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
