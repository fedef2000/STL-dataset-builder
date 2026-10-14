"""
Builds what the extraction model reads about a paper held as LaTeX: a short header (title, abstract) and a list of
regions. A region is a piece of one .tex file around one or more formulas found by the estimator. Formulas that lie
close together share a region, so the same text is not sent once per formula; every formula gets an ID (F1, F2, ...)
and is wrapped in markers in the text given to the model, which then answers once per ID.
"""
import bisect
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from src.analysis import estimator as e

# Characters of context wanted before and after a formula. In the evaluation set the requirement follows the
# formula twice as often as it precedes it.
CONTEXT_BEFORE = 2000
CONTEXT_AFTER = 3000
# A window edge moves outwards by at most this many characters to reach the end of a paragraph
SNAP_SLACK = 600
# Two windows closer than this are joined
JOIN_GAP = 200
# A longer run of formulas is split into several regions, so the model's answer stays short
MAX_FORMULAS_PER_REGION = 15
MAX_ABSTRACT_CHARS = 2500

# Never occur in LaTeX source, so they cannot be confused with the paper's own text
MARK_OPEN = "⟦{id}⟧"
MARK_CLOSE = "⟦/{id}⟧"

HEADING_PATTERN = re.compile(r"\\(chapter|section|subsection|subsubsection)\*?\s*(?:\[[^\]]*\]\s*)?(?=\{)")
HEADING_LEVELS = {"chapter": 0, "section": 0, "subsection": 1, "subsubsection": 2}
# A region does not cross these: another section is another topic, and the bibliography is never context
HARD_BREAK_PATTERN = re.compile(
    r"\\(?:chapter|section)\*?\s*(?:\[[^\]]*\]\s*)?\{|\\begin\{document\}|\\begin\{thebibliography\}|\\bibliography\s*\{|\\printbibliography"
)
PARAGRAPH_BREAK_PATTERN = re.compile(r"\n[ \t]*\n\s*")
ABSTRACT_PATTERN = re.compile(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", re.DOTALL)
ABSTRACT_COMMAND_PATTERN = re.compile(r"\\abstract\s*(?=\{)")


@dataclass
class Formula:
    id: str
    kind: str          # 'concrete' or 'symbolic'
    line: int          # 1-based line of the formula in the source file
    start: int         # offsets of the formula in the text of its region
    end: int
    source: str


@dataclass
class Region:
    file: str          # path of the .tex file, relative to the paper's folder
    line_start: int
    line_end: int
    section: list[str]  # headings above the first formula, outermost first
    text: str
    formulas: list[Formula] = field(default_factory=list)

    def marked_text(self) -> str:
        """The text with every formula of the region wrapped in its markers."""
        out, pos = [], 0
        for f in self.formulas:
            out += [self.text[pos:f.start], MARK_OPEN.format(id=f.id), f.source, MARK_CLOSE.format(id=f.id)]
            pos = f.end
        out.append(self.text[pos:])
        return "".join(out)


@dataclass
class PaperContext:
    paper_id: str
    title: str
    abstract: str
    regions: list[Region] = field(default_factory=list)

    @property
    def formulas(self) -> list[Formula]:
        return [f for region in self.regions for f in region.formulas]


def strip_keeping_lines(raw: str) -> str:
    """Like the estimator's comment removal, but a disabled block leaves its line breaks, so line numbers stay true."""
    text = "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in raw.splitlines())
    return e.DISABLED_BLOCK_PATTERN.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def find_abstract(texts: list[str]) -> str:
    for text in texts:
        m = ABSTRACT_PATTERN.search(text)
        body = m.group(1) if m else ""
        if not body:
            m = ABSTRACT_COMMAND_PATTERN.search(text)
            body = e.read_braced_group(text, m.end(), limit=8000) if m else ""
        body = re.sub(r"\s+", " ", body).strip()
        if body:
            return body if len(body) <= MAX_ABSTRACT_CHARS else body[:MAX_ABSTRACT_CHARS].rsplit(" ", 1)[0] + " ..."
    return ""


class _FileLayout:
    """The positions in one .tex file that decide where a region may start and end."""

    def __init__(self, text: str):
        self.text = text
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", text)]
        self.hard_breaks = [m.start() for m in HARD_BREAK_PATTERN.finditer(text)]
        self.paragraph_breaks = [m.end() for m in PARAGRAPH_BREAK_PATTERN.finditer(text)]
        self.math_spans = [m.span() for m in e.MATH_SPAN_PATTERN.finditer(text)]
        self.math_starts = [start for start, _ in self.math_spans]
        self.headings = []
        for m in HEADING_PATTERN.finditer(text):
            title = re.sub(r"\s+", " ", e.read_braced_group(text, m.end(), limit=300)).strip()
            self.headings.append((m.start(), HEADING_LEVELS[m.group(1)], title))
        begin = text.find("\\begin{document}")
        self.body_start = begin if begin >= 0 else 0

    def line_of(self, pos: int) -> int:
        return bisect.bisect_right(self.line_starts, pos)

    def section_at(self, pos: int) -> list[str]:
        path = {}
        for start, level, title in self.headings:
            if start > pos:
                break
            path = {k: v for k, v in path.items() if k < level}
            path[level] = title
        return [path[level] for level in sorted(path) if path[level]]

    def _outside_math(self, pos: int, outwards: int) -> int:
        """Moves a cut that falls inside a math span to the start (outwards=-1) or the end (outwards=1) of the span."""
        i = bisect.bisect_right(self.math_starts, pos) - 1
        if i >= 0 and self.math_spans[i][0] < pos < self.math_spans[i][1]:
            return self.math_spans[i][0] if outwards < 0 else self.math_spans[i][1]
        return pos

    def window(self, start: int, end: int, before: int, after: int) -> tuple[int, int]:
        """The context span of the formula at text[start:end]: paragraph-aligned and inside the formula's section."""
        text = self.text
        i = bisect.bisect_right(self.hard_breaks, start)
        floor = self.hard_breaks[i - 1] if i else 0
        ceiling = self.hard_breaks[i] if i < len(self.hard_breaks) else len(text)

        lo = max(floor, start - before)
        if lo > floor:
            j = bisect.bisect_right(self.paragraph_breaks, lo)
            if j and self.paragraph_breaks[j - 1] >= max(floor, lo - SNAP_SLACK):
                lo = self.paragraph_breaks[j - 1]
            else:
                lo = max(floor, text.rfind("\n", 0, lo) + 1)
        hi = min(ceiling, end + after)
        if hi < ceiling:
            j = bisect.bisect_left(self.paragraph_breaks, hi)
            if j < len(self.paragraph_breaks) and self.paragraph_breaks[j] <= min(ceiling, hi + SNAP_SLACK):
                hi = self.paragraph_breaks[j]
            else:
                newline = text.find("\n", hi)
                hi = ceiling if newline < 0 else min(ceiling, newline)
        return min(self._outside_math(lo, -1), start), max(self._outside_math(hi, 1), end)


def _is_macro_definition(text: str, pos: int) -> bool:
    """True when the formula stands in a \\newcommand or \\def line: that is a definition, not a use."""
    line_start = text.rfind("\n", 0, pos) + 1
    return bool(e.MACRO_DEF_PATTERN.match(text[line_start:pos + 1].lstrip()))


def build_file_regions(text: str, patterns: list, kinds: tuple[str, ...] = ("concrete",), before: int = CONTEXT_BEFORE,
                       after: int = CONTEXT_AFTER, max_formulas: int = MAX_FORMULAS_PER_REGION) -> list[Region]:
    """Regions of one .tex file, in file order. Formula IDs and the file name are filled in by the caller."""
    layout = _FileLayout(text)
    found = [
        (start, end, kind) for start, end, kind in e.locate_formulas(text, patterns)
        if kind in kinds and start >= layout.body_start and not _is_macro_definition(text, start)
    ]
    if not found:
        return []

    # One window per formula; windows that touch are joined into a run
    windows = [layout.window(start, end, before, after) for start, end, _ in found]
    runs = [[0]]
    run_end = windows[0][1]
    for i in range(1, len(found)):
        if windows[i][0] <= run_end + JOIN_GAP:
            runs[-1].append(i)
            run_end = max(run_end, windows[i][1])
        else:
            runs.append([i])
            run_end = windows[i][1]

    regions = []
    for run in runs:
        pieces = math.ceil(len(run) / max_formulas)
        size = math.ceil(len(run) / pieces)
        for chunk in (run[i:i + size] for i in range(0, len(run), size)):
            lo = min(windows[i][0] for i in chunk)
            hi = max(windows[i][1] for i in chunk)
            # Trim the blank edges
            lo += len(text[lo:hi]) - len(text[lo:hi].lstrip())
            hi -= len(text[lo:hi]) - len(text[lo:hi].rstrip())
            regions.append(Region(
                file="", line_start=layout.line_of(lo), line_end=layout.line_of(max(lo, hi - 1)),
                section=layout.section_at(found[chunk[0]][0]), text=text[lo:hi],
                formulas=[
                    Formula(id="", kind=found[i][2], line=layout.line_of(found[i][0]), start=found[i][0] - lo,
                            end=found[i][1] - lo, source=text[found[i][0]:found[i][1]])
                    for i in chunk
                ],
            ))
    return regions


def build_paper_context(paper_id: str, title: str, tex_folder: Path, id_prefix: str = "F", **options) -> PaperContext:
    """
    Reads the LaTeX source of a paper and returns its header and regions. `options` are passed to build_file_regions
    (kinds, before, after, max_formulas). A paper without formulas of the wanted kinds has no regions. The formulas
    are numbered through the paper, `id_prefix` first: the concrete ones are F1, F2, ... and the parametric ones,
    which are found in a run of their own, P1, P2, ..., so that an ID is of one formula only.
    """
    context = PaperContext(paper_id=paper_id, title=title or "", abstract="")
    if not tex_folder.is_dir():
        return context

    tex_sources, patterns = e.read_tex_folder(tex_folder, strip=strip_keeping_lines)
    # The files that are part of the paper, the main file first; the rest in a fixed order, so IDs are stable
    by_name = lambda f: (0 if "\\documentclass" in tex_sources[f] else 1, f.relative_to(tex_folder).as_posix())
    document_files = sorted(e.find_document_files(tex_sources, tex_folder), key=by_name)
    regions_per_file = {f: build_file_regions(tex_sources[f], patterns, **options) for f in document_files}
    if not any(regions_per_file.values()):
        # The \input chain could not be followed (e.g., file names built by macros): take every file instead
        document_files = sorted(tex_sources, key=by_name)
        regions_per_file = {f: build_file_regions(tex_sources[f], patterns, **options) for f in document_files}

    context.abstract = find_abstract([tex_sources[f] for f in document_files])
    n = 0
    for f in document_files:
        for region in regions_per_file[f]:
            region.file = f.relative_to(tex_folder).as_posix()
            for formula in region.formulas:
                n += 1
                formula.id = f"{id_prefix}{n}"
            context.regions.append(region)
    return context
