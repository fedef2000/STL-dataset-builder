import re
from pathlib import Path

# Files that can hold author macro definitions (formulas are only counted in .tex files)
MACRO_SOURCE_EXTENSIONS = (".tex", ".sty", ".cls", ".def")

# Interval bounds: a number, or a symbolic parameter (e.g., \tau, t_1, T_{s})
NUM = r"\d+(?:\.\d+)?"
SYM = r"[a-zA-Z\\][a-zA-Z0-9_^\\]*(?:\{[a-zA-Z0-9]*\})?"
BOUND = rf"(?:{NUM}|{SYM})"
NUM_PATTERN = re.compile(NUM)

FONT_COMMANDS = r"(?:mathcal|mathbf|mathsf|mathrm|mathit|mathtt|boldsymbol|bm|textbf|textsf|textrm|text|operatorname)"

# Word-named operators: these may also take the interval as arguments (e.g., \always{0}{200})
WORD_OPERATORS = r"\\(?:[Aa]lways|[Ee]ventually|[Gg]lobally|[Ff]inally|[Uu]ntil)(?![a-zA-Z])"

# Operators that are only recognized when followed by a sub/superscript interval (e.g., \Box_{[0, 5]}, G_{[0, 5]})
# Deliberately case-sensitive: a lowercase f_{[0,1]} or u_{[0,1]} is not a temporal operator.
SYMBOL_OPERATORS = "|".join([
    r"\\(?:square|lozenge|Box|Diamond|diamond)(?![a-zA-Z])",
    rf"\\{FONT_COMMANDS}\s*\{{\s*[GFU]\s*\}}",
    r"\\[GFU](?![a-zA-Z])",
    # A bare letter only counts with a subscript: U^{[0,T]} is usually a signal space, not "until"
    r"(?<![a-zA-Z\\])[GFU](?=\s*_)",
])

# Macro definitions: \newcommand{\alw}[2]{...}, \def\G{...}, \DeclareMathOperator{\ev}{F}, \NewDocumentCommand{\alw}{m m}{...}
MACRO_DEF_PATTERN = re.compile(
    r"\\(?:(?:re)?newcommand|providecommand|DeclareRobustCommand|DeclareMathOperator)\*?\s*"
    r"\{?\s*\\([a-zA-Z]+)\s*\}?\s*(?:\[[^\]]*\]\s*){0,2}(?=\{)"
    r"|\\[gex]?def\s*\\([a-zA-Z]+)\s*(?:#\d\s*)*(?=\{)"
    r"|\\(?:New|Renew|Provide|Declare)DocumentCommand\s*\{?\s*\\([a-zA-Z]+)\s*\}?\s*\{[^{}]*\}\s*(?=\{)"
)

# A macro is a temporal operator if its body draws a box/diamond, or is just a styled G/F/U
MACRO_BODY_SYMBOL_PATTERN = re.compile(r"\\(?:square|lozenge|Box|Diamond|diamond)(?![a-zA-Z])")
MACRO_BODY_WRAPPER_PATTERN = re.compile(
    rf"\\(?:{FONT_COMMANDS}|mathop|mathbin|mathrel|mathord|ensuremath|limits|nolimits|xspace)(?![a-zA-Z])|\\[,!;: ]|[{{}}\s]"
)

# PDF Regex: PDFs lose LaTeX macros, so we look for raw text approximations (e.g., G[0, 5], Always_[0, 10], □[0, 5])
PDF_CONCRETE_PATTERN = re.compile(
    r"(?:(?<![A-Za-z])[GFU](?![A-Za-z])|\b(?i:always|eventually|globally|finally|until)\b|[□◇◊♢⋄])"
    rf"\s*[\[_\{{]\s*{NUM}\s*,\s*{NUM}\s*[\]\}}]"
)

# Blocks that authors disabled without using %: the comment environment and \iffalse ... \fi
DISABLED_BLOCK_PATTERN = re.compile(
    r"\\begin\{comment\}.*?\\end\{comment\}|\\iffalse(?![a-zA-Z]).*?\\fi(?![a-zA-Z])",
    re.DOTALL,
)

def strip_latex_comments(text: str) -> str:
    """Removes commented-out lines and disabled blocks to prevent counting formulas that authors deleted/disabled."""
    text = "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in text.splitlines())
    return DISABLED_BLOCK_PATTERN.sub("", text)

def read_braced_group(text: str, start: int, limit: int = 2000) -> str:
    """Returns the content of the balanced {...} group opening at text[start] ('' if unbalanced)."""
    depth = 0
    i = start
    end = min(len(text), start + limit)
    while i < end:
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
        i += 1
    return ""

def find_temporal_macros(text: str) -> set[str]:
    """Finds author-defined macros that expand to a temporal operator (e.g., \\alw -> \\square, \\G -> \\mathbf{G})."""
    bodies = {}
    for m in MACRO_DEF_PATTERN.finditer(text):
        name = next(g for g in m.groups() if g)
        bodies.setdefault(name, []).append(read_braced_group(text, m.end()))

    temporal = set()
    for name, defs in bodies.items():
        for body in defs:
            if MACRO_BODY_SYMBOL_PATTERN.search(body) or re.fullmatch(r"[GFU]", MACRO_BODY_WRAPPER_PATTERN.sub("", body)):
                temporal.add(name)
                break

    # Follow macros defined in terms of other temporal macros (e.g., \newcommand{\alw}{\G})
    changed = True
    while changed:
        changed = False
        known = re.compile(r"\\(?:" + "|".join(sorted(temporal, key=len, reverse=True)) + r")(?![a-zA-Z])") if temporal else None
        for name, defs in bodies.items():
            if name not in temporal and known and any(known.search(body) for body in defs):
                temporal.add(name)
                changed = True
    return temporal

def build_formula_patterns(temporal_macros: set[str]) -> list[tuple[re.Pattern, bool]]:
    """
    Builds the (pattern, needs_numeric_bound) forms for one paper. Every pattern captures the two interval bounds.
    Forms without brackets around the interval need at least one numeric bound, otherwise
    \\until{\\phi}{\\psi} would be counted as a parametric formula.
    """
    macro_ops = (
        r"\\(?:" + "|".join(sorted(temporal_macros, key=len, reverse=True)) + r")(?![a-zA-Z])"
        if temporal_macros
        else None
    )
    arg_ops = "|".join(filter(None, [WORD_OPERATORS, macro_ops]))
    all_ops = "|".join([arg_ops, SYMBOL_OPERATORS])
    pair = rf"\s*({BOUND})\s*,\s*({BOUND})\s*"

    return [
        # \Box_{[0, 5]}, G^{[0, \tau]}, \alw_[0, 5]
        (re.compile(rf"(?:{all_ops})\s*[_^]\s*\{{?\s*\[{pair}\]\s*\}}?"), False),
        # \always{[0, 200]}
        (re.compile(rf"(?:{arg_ops})\s*\{{\s*\[{pair}\]\s*\}}"), False),
        # \always[0, 200]
        (re.compile(rf"(?:{arg_ops})\s*\[{pair}\]"), False),
        # \always{0, 200}
        (re.compile(rf"(?:{arg_ops})\s*\{{{pair}\}}"), True),
        # \always{0}{200}
        (re.compile(rf"(?:{arg_ops})\s*\{{\s*({BOUND})\s*\}}\s*\{{\s*({BOUND})\s*\}}"), True),
    ]

def count_formulas(text: str, patterns: list[tuple[re.Pattern, bool]]) -> dict:
    """Counts operator+interval matches, split into concrete (both bounds numeric) and symbolic."""
    counts = {"concrete": 0, "symbolic": 0}
    for pattern, needs_numeric in patterns:
        for m in pattern.finditer(text):
            numeric_bounds = sum(1 for bound in m.groups() if NUM_PATTERN.fullmatch(bound))
            if numeric_bounds == 2:
                counts["concrete"] += 1
            elif numeric_bounds == 1 or not needs_numeric:
                counts["symbolic"] += 1
    return counts

def estimate_tex_folder(tex_folder: Path) -> dict:
    """Scans all .tex files in a folder and counts formula matches, including the paper's own operator macros."""
    counts = {"concrete": 0, "symbolic": 0}
    if not tex_folder.is_dir():
        return counts

    # Macros are often defined in one file (macros.tex, a .sty) and used in another, so collect them per paper
    sources = {}
    for src_file in tex_folder.rglob("*"):
        if src_file.suffix.lower() in MACRO_SOURCE_EXTENSIONS and src_file.is_file():
            try:
                raw = src_file.read_text(encoding="utf-8", errors="ignore")
                sources[src_file] = strip_latex_comments(raw)
            except Exception:
                continue

    temporal_macros = set()
    for active_code in sources.values():
        temporal_macros |= find_temporal_macros(active_code)
    patterns = build_formula_patterns(temporal_macros)

    for src_file, active_code in sources.items():
        if src_file.suffix.lower() != ".tex":
            continue
        file_counts = count_formulas(active_code, patterns)
        counts["concrete"] += file_counts["concrete"]
        counts["symbolic"] += file_counts["symbolic"]
    return counts

def estimate_pdf_file(pdf_path: Path) -> dict:
    """Scans PDF text for raw formula representations."""
    counts = {"concrete": 0, "symbolic": 0}
    if not pdf_path.is_file():
        return counts

    try:
        import pymupdf
        pymupdf.TOOLS.mupdf_display_errors(False)
        pymupdf.TOOLS.mupdf_display_warnings(False)

        with pymupdf.open(pdf_path) as doc:
            for page in doc:
                text = page.get_text()
                concrete_matches = PDF_CONCRETE_PATTERN.findall(text)
                counts["concrete"] += len(concrete_matches)
    except Exception:
        pass

    return counts

def estimate_paper_formulas(paper: dict, base_dir: Path) -> dict:
    """Estimates the formulas for a single paper and returns the counts."""
    pid = paper["paper_id"]
    status = paper.get("local_files", {}).get("status", "pending")

    if status == "downloaded_latex":
        folder = base_dir / "data" / "raw" / "latex" / pid
        return estimate_tex_folder(folder)

    elif status == "downloaded_pdf":
        pdf_file = base_dir / "data" / "raw" / "pdfs" / f"{pid}.pdf"
        return estimate_pdf_file(pdf_file)

    return {"concrete": 0, "symbolic": 0}
