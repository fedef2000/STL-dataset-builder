import bisect
import re
from pathlib import Path

# Files that can hold author macro definitions (formulas are only counted in .tex files)
MACRO_SOURCE_EXTENSIONS = (".tex", ".sty", ".cls", ".def")

# Interval bounds: a number, infinity, or a symbolic parameter (e.g., \tau, t_1, T_{s})
NUM = r"(?:\d+(?:\.\d+)?|\.\d+)"
INF = r"[+-]?\s*\\infty(?![a-zA-Z])"
SYM = r"[a-zA-Z\\][a-zA-Z0-9_^\\]*(?:\{[a-zA-Z0-9]*\})?"
BOUND = rf"(?:{NUM}|{INF}|{SYM})"
NUMERIC_BOUND_PATTERN = re.compile(rf"{NUM}|{INF}")
# A time unit written next to a numeric bound (e.g., [0.2s, 0.8s])
UNIT = r"(?:\s*(?:ms|sec|min|s|h)(?![a-zA-Z]))?"
# Whitespace inside an interval, including LaTeX spacing commands (e.g., [\,0,\,4\,])
SP = r"(?:\s|\\[,;:!]|~)*"

FONT_COMMANDS = r"(?:mathcal|mathbf|mathsf|mathrm|mathit|mathtt|boldsymbol|bm|textbf|textsf|textrm|text|operatorname)"

# Word-named operators: these may also take the interval as arguments (e.g., \always{0}{200})
WORD_OPERATORS = (
    r"\\(?:[Aa]lways|[Ee]ventually|[Gg]lobally|[Ff]inally|[Uu]ntil|[Rr]elease"
    r"|[Oo]nce|[Ss]ince|[Hh]istorically)(?![a-zA-Z])"
)

# Box and diamond symbols, including the past-time variants (e.g., \boxminus, \diamondminus)
SYMBOL_COMMANDS = (
    r"\\(?:square|lozenge|Box|Diamond|diamond|diamondsuit|blacksquare|blacklozenge|Diamonddot|boxdot"
    r"|boxminus|boxplus|diamondminus|diamondplus"
    r"|LTL(?:square|diamond|globally|always|finally|eventually|until|release|once|since|historically))(?![a-zA-Z])"
)

# Operators that are only recognized when followed by a sub/superscript interval (e.g., \Box_{[0, 5]}, G_{[0, 5]})
# Deliberately case-sensitive: a lowercase f_{[0,1]} or u_{[0,1]} is not a temporal operator.
SYMBOL_OPERATORS = "|".join([
    SYMBOL_COMMANDS,
    # Common short macro names, for papers whose style file is not on disk
    r"\\(?:alw|ev)(?![a-zA-Z])",
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

# A macro is a temporal operator if its body draws a box/diamond, or is just a styled G/F/U or operator name
MACRO_BODY_SYMBOL_PATTERN = re.compile(SYMBOL_COMMANDS)
MACRO_BODY_WRAPPER_PATTERN = re.compile(
    rf"\\(?:{FONT_COMMANDS}|mathop|mathbin|mathrel|mathord|ensuremath|limits|nolimits|xspace)(?![a-zA-Z])|\\[,!;: ]|[{{}}\s]"
)
MACRO_BODY_NAME_PATTERN = re.compile(
    r"[GFU]|(?i:alw|always|ev|eventually|glob|globally|finally|until|release|once|since|hist|historically)"
)

# PDF Regex: PDFs lose LaTeX macros, so we look for raw text approximations (e.g., G[0, 5], Always_[0, 10], □[0, 5])
PDF_CONCRETE_PATTERN = re.compile(
    r"(?:(?<![A-Za-z])[GFU](?![A-Za-z])|\b(?i:always|eventually|globally|finally|until)\b|[□◇◊♢⋄])"
    r"\s*[\[_\{]\s*\d+(?:\.\d+)?\s*,\s*\d+(?:\.\d+)?\s*[\]\}]"
)

# Blocks that authors disabled without using %: the comment environment and \iffalse ... \fi
DISABLED_BLOCK_PATTERN = re.compile(
    r"\\begin\{comment\}.*?\\end\{comment\}|\\iffalse(?![a-zA-Z]).*?\\fi(?![a-zA-Z])",
    re.DOTALL,
)

# Math spans, used to group operators into formulas: display environments, \[ \], \( \), $$ $$ and $ $
MATH_SPAN_PATTERN = re.compile(
    r"\\begin\{((?:equation|align|alignat|flalign|gather|multline|eqnarray|IEEEeqnarray|displaymath|math|dmath)\*?)\}"
    r".*?\\end\{\1\}"
    r"|(?<!\\)\\\[.*?(?<!\\)\\\]"
    r"|(?<!\\)\\\(.*?(?<!\\)\\\)"
    r"|(?<!\\)\$\$.*?(?<!\\)\$\$"
    r"|(?<!\\)\$(?!\$).*?(?<!\\)\$",
    re.DOTALL,
)
ROW_BREAK_PATTERN = re.compile(r"\\\\(?:\s*\[[^\]]*\])?")
# A display row that starts or ends with a connective continues the formula of the neighbouring row
CONNECTIVE = (
    r"(?:\\(?:wedge|land|vee|lor|rightarrow|Rightarrow|Longrightarrow|implies|to|leftrightarrow|Leftrightarrow|iff"
    r"|bigwedge|bigvee)(?![a-zA-Z]))"
)
ROW_STARTS_WITH_CONNECTIVE = re.compile(rf"[\s&]*{CONNECTIVE}")
ROW_ENDS_WITH_CONNECTIVE = re.compile(rf"{CONNECTIVE}[\s&]*$")

# Files pulled into a document: \input{f}, \include{f}, \subfile{f}, \import{dir}{f}, \input f
INPUT_PATTERN = re.compile(
    r"\\(?:input|include|subfile|subfileinclude)\s*\{([^{}]+)\}"
    r"|\\(?:sub)?import\s*\{([^{}]*)\}\s*\{([^{}]+)\}"
    r"|\\input\s+([^\s{}\\]+)"
)

EMPTY_COUNTS = {"concrete": 0, "symbolic": 0, "formulas_concrete": 0, "formulas_symbolic": 0}

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
            if MACRO_BODY_SYMBOL_PATTERN.search(body) or MACRO_BODY_NAME_PATTERN.fullmatch(MACRO_BODY_WRAPPER_PATTERN.sub("", body)):
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
    Builds the (pattern, needs_numeric_bound) forms for one paper. Every pattern captures its bounds as 'lo' and 'hi'
    (only 'lo' for a single bound such as \\Diamond_{\\le 3}), and the brackets as 'open' and 'close' when it has them.
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
    pair = rf"{SP}(?P<lo>{BOUND}){UNIT}{SP},{SP}(?P<hi>{BOUND}){UNIT}{SP}"
    close = r"(?P<close>(?:\\right\s*)?[\]\)])"
    # Closed, open and half-open intervals: [0, 5], (0, 5), [0, 5), [5, \infty), \left[0, 7\right]
    interval = rf"(?P<open>(?:\\left\s*)?[\[\(]){pair}{close}"
    square_interval = rf"(?P<open>(?:\\left\s*)?\[){pair}{close}"
    relation = r"(?:\\(?:leq?|geq?|leqslant|geqslant)(?![a-zA-Z])|<=?|>=?)"

    return [
        # \Box_{[0, 5]}, G^{[0, \tau]}, \alw_[0, 5]
        (re.compile(rf"(?:{all_ops})\s*[_^]\s*\{{?\s*{interval}\s*\}}?"), False),
        # \always{[0, 200]}
        (re.compile(rf"(?:{arg_ops})\s*\{{\s*{interval}\s*\}}"), False),
        # \always[0, 200]
        (re.compile(rf"(?:{arg_ops})\s*{square_interval}"), False),
        # \always{0, 200}
        (re.compile(rf"(?:{arg_ops})\s*\{{{pair}\}}"), True),
        # \always{0}{200}
        (re.compile(rf"(?:{arg_ops})\s*\{{\s*(?P<lo>{BOUND}){UNIT}\s*\}}\s*\{{\s*(?P<hi>{BOUND}){UNIT}\s*\}}"), True),
        # \Diamond_{\le 3}, \Always^{\leq T}
        (re.compile(rf"(?:{all_ops})\s*[_^]\s*\{{\s*{relation}\s*(?P<lo>{BOUND}){UNIT}\s*\}}"), False),
    ]

def classify_match(m: re.Match, needs_numeric: bool) -> str | None:
    """Returns 'concrete' (every bound is a number or infinity), 'symbolic', or None when the match is not counted."""
    groups = m.groupdict()
    bounds = [b for b in (groups.get("lo"), groups.get("hi")) if b is not None]
    numeric_bounds = sum(1 for bound in bounds if NUMERIC_BOUND_PATTERN.fullmatch(bound))
    if numeric_bounds == len(bounds):
        return "concrete"
    if numeric_bounds == 0:
        if needs_numeric:
            return None
        # G_{(i,j)} is far more often a pair of indices than an open interval
        if (groups.get("open") or "").endswith("(") and (groups.get("close") or "").endswith(")"):
            return None
    return "symbolic"

def find_formula_units(text: str) -> list[tuple[int, int]]:
    """
    Splits the math of a file into formula units, as sorted (start, end) spans. An inline span is one unit.
    A display environment is split at its row breaks, except where a row continues the previous one with a connective.
    """
    units = []
    for span in MATH_SPAN_PATTERN.finditer(text):
        is_display = span.group(0).startswith(("\\begin", "\\[", "$$"))
        if not is_display:
            units.append((span.start(), span.end()))
            continue
        rows = []
        row_start = span.start()
        for br in ROW_BREAK_PATTERN.finditer(text, span.start(), span.end()):
            rows.append((row_start, br.start()))
            row_start = br.end()
        rows.append((row_start, span.end()))

        unit_start, unit_end = rows[0]
        for start, end in rows[1:]:
            continues = ROW_STARTS_WITH_CONNECTIVE.match(text, start, end) or ROW_ENDS_WITH_CONNECTIVE.search(text[unit_start:unit_end])
            if continues:
                unit_end = end
            else:
                units.append((unit_start, unit_end))
                unit_start, unit_end = start, end
        units.append((unit_start, unit_end))
    return units

def count_formulas(text: str, patterns: list[tuple[re.Pattern, bool]]) -> dict:
    """
    Counts temporal operators that carry a time bound, split into concrete (numeric bounds) and symbolic,
    and the formulas they belong to. A formula is concrete if at least one of its operators is.
    """
    matches = []
    for pattern, needs_numeric in patterns:
        for m in pattern.finditer(text):
            kind = classify_match(m, needs_numeric)
            if kind:
                matches.append((m.start(), kind))

    counts = dict(EMPTY_COUNTS)
    if not matches:
        return counts

    units = find_formula_units(text)
    unit_starts = [start for start, _ in units]
    kinds_per_formula = {}
    for pos, kind in matches:
        counts[kind] += 1
        i = bisect.bisect_right(unit_starts, pos) - 1
        if i >= 0 and pos < units[i][1]:
            key = ("unit", i)
        else:
            # Outside any math span (e.g., in a macro definition): group by line
            key = ("line", text.count("\n", 0, pos))
        kinds_per_formula.setdefault(key, set()).add(kind)

    for kinds in kinds_per_formula.values():
        counts["formulas_concrete" if "concrete" in kinds else "formulas_symbolic"] += 1
    return counts

def find_document_files(tex_sources: dict[Path, str], folder: Path) -> set[Path]:
    """
    Returns the .tex files that are part of the paper: the ones reachable from a main file (\\documentclass)
    through \\input and similar commands. arXiv bundles often carry old drafts and unused files as well.
    With several main files, the document holding the most text is taken, so two versions are not counted twice.
    """
    by_stem = {}
    for f in tex_sources:
        by_stem.setdefault(f.stem.lower(), []).append(f)

    def resolve(name: str, from_file: Path) -> list[Path]:
        name = name.strip().replace("\\", "/")
        for base in (folder, from_file.parent):
            for candidate in (base / name, base / (name + ".tex")):
                if candidate in tex_sources:
                    return [candidate]
        # Folders downloaded without their sub-directories: fall back to the file name
        stem = name.split("/")[-1]
        stem = stem[:-4] if stem.lower().endswith(".tex") else stem
        return by_stem.get(stem.lower(), [])

    def reachable_from(main: Path) -> set[Path]:
        seen, todo = set(), [main]
        while todo:
            f = todo.pop()
            if f in seen:
                continue
            seen.add(f)
            for m in INPUT_PATTERN.finditer(tex_sources[f]):
                name = m.group(1) or m.group(4) or f"{m.group(2)}/{m.group(3)}"
                todo.extend(resolve(name, f))
        return seen

    mains = [f for f, code in tex_sources.items() if "\\documentclass" in code]
    if not mains:
        return set(tex_sources)
    return max((reachable_from(main) for main in mains), key=lambda files: sum(len(tex_sources[f]) for f in files))

def estimate_tex_folder(tex_folder: Path) -> dict:
    """Scans the .tex files of a paper and counts formula matches, including the paper's own operator macros."""
    counts = dict(EMPTY_COUNTS)
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

    tex_sources = {f: code for f, code in sources.items() if f.suffix.lower() == ".tex"}
    # Nothing after \end{document} is typeset
    file_counts = {f: count_formulas(code.split("\\end{document}")[0], patterns) for f, code in tex_sources.items()}

    document_files = find_document_files(tex_sources, tex_folder)
    if not any(file_counts[f]["concrete"] + file_counts[f]["symbolic"] for f in document_files):
        # The \input chain could not be followed (e.g., file names built by macros): count every file instead
        document_files = set(tex_sources)

    for f in document_files:
        for key in counts:
            counts[key] += file_counts[f][key]
    return counts

def estimate_pdf_file(pdf_path: Path) -> dict:
    """Scans PDF text for raw formula representations."""
    counts = dict(EMPTY_COUNTS)
    if not pdf_path.is_file():
        return counts

    try:
        import pymupdf
        pymupdf.TOOLS.mupdf_display_errors(False)
        pymupdf.TOOLS.mupdf_display_warnings(False)

        with pymupdf.open(pdf_path) as doc:
            for page in doc:
                text = page.get_text()
                match_lines = [text.count("\n", 0, m.start()) for m in PDF_CONCRETE_PATTERN.finditer(text)]
                counts["concrete"] += len(match_lines)
                # PDF text has no math markup, so operators on the same text line count as one formula
                counts["formulas_concrete"] += len(set(match_lines))
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

    return dict(EMPTY_COUNTS)
