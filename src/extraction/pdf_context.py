"""
What the extraction model reads for a paper held only as a PDF: the paper header, and one region per page that holds
formulas. A region is the text layer of the page, with the end of the previous page and the start of the next, and the
image of the page. The text layer garbles formulas (flattened subscripts, symbols turned into other characters), so
the model reads the formulas from the image and copies the requirement passages from the text.

A formula is the text line on which step 4 finds a bounded temporal operator (src/analysis/estimator.py): the line
is marked in the text, and the model transcribes the whole formula it belongs to from the image.
"""
import re
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from src.analysis import estimator as e
from src.extraction.context import Formula, PaperContext, Region

# Text of the neighbouring pages given with a page, in characters: a requirement often sits just before a formula
# that opens a new page, or just after one that closes a page
NEIGHBOUR_CHARS = 1500
# Resolution of the page image: enough for subscripts, without making the image needlessly large
IMAGE_DPI = 150
# Where the abstract of a PDF ends: the first heading after it
ABSTRACT_END = re.compile(r"\n\s*(?:index terms|keywords|key words|(?:1|I)\.?\s+introduction|introduction)\b", re.IGNORECASE)

# MuPDF is not safe to use from several threads at once, and the calls are made from several threads
_PDF_LOCK = threading.Lock()


@dataclass
class PdfRegion(Region):
    """A page of a PDF. `text` is the end of the previous page, the page, and the start of the next."""
    pdf_path: Path = None
    page: int = 0                 # 1-based
    page_start: int = 0           # offsets of the page itself in `text`
    page_end: int = 0

    def image_png(self) -> bytes:
        """The image of the page, rendered when it is needed (it is not kept with the region)."""
        with _PDF_LOCK:
            import pymupdf
            with pymupdf.open(self.pdf_path) as doc:
                return doc[self.page - 1].get_pixmap(dpi=IMAGE_DPI).tobytes("png")


def page_texts(pdf_path: Path) -> list[str]:
    """The text layer of every page, normalised as step 4 reads it (NFKC: ligatures and compatibility characters)."""
    with _PDF_LOCK:
        import pymupdf
        with pymupdf.open(pdf_path) as doc:
            return [unicodedata.normalize("NFKC", page.get_text()) for page in doc]


def find_abstract(first_page: str) -> str:
    """The abstract from the text of the first page: from "Abstract" to the first heading after it."""
    m = re.search(r"\babstract\b[\s.:—-]*", first_page, re.IGNORECASE)
    if not m:
        return ""
    rest = first_page[m.end():]
    end = ABSTRACT_END.search(rest)
    return " ".join(rest[:end.start() if end else 2000].split())[:2000]


def operator_text(text: str, pos: int) -> str:
    """The operator found at `pos` with its interval, as the text gives it, e.g. '□[0,2)' or 'U[2.3,4.5]'."""
    end = re.search(r"[\])]|\n", text[pos:pos + 40])
    return " ".join(text[pos:pos + (end.end() if end and end.group() != "\n" else 12)].split())


def formula_lines(text: str, kinds: tuple[str, ...]) -> list[tuple[int, int, str, str]]:
    """
    The lines of a page that hold a bounded temporal operator of the wanted kinds, as (start, end, kind, operators):
    a line with a concrete operator is concrete, as step 4 counts it. `operators` names the operators found on it.
    """
    lines = {}
    for pos, kind in sorted(e.find_pdf_operators(text)):
        start = text.rfind("\n", 0, pos) + 1
        end = text.find("\n", pos)
        end = len(text) if end < 0 else end
        lines.setdefault((start, end), []).append((kind, operator_text(text, pos)))
    found = [(start, end, "concrete" if any(k == "concrete" for k, _ in ops) else "symbolic", ", ".join(dict.fromkeys(o for _, o in ops)))
             for (start, end), ops in sorted(lines.items())]
    return [line for line in found if line[2] in kinds]


def build_pdf_context(paper_id: str, title: str, pdf_path: Path, kinds: tuple[str, ...] = ("concrete",),
                      id_prefix: str = "F") -> PaperContext:
    """The header and the regions (one per page with formulas of the wanted kinds) of a paper held as a PDF."""
    context = PaperContext(paper_id=paper_id, title=title or "", abstract="")
    if not pdf_path.is_file():
        return context
    pages = page_texts(pdf_path)
    context.abstract = find_abstract(pages[0]) if pages else ""
    n = 0
    for number, page in enumerate(pages, 1):
        lines = formula_lines(page, kinds)
        if not lines:
            continue
        before = pages[number - 2][-NEIGHBOUR_CHARS:] if number > 1 else ""
        after = pages[number][:NEIGHBOUR_CHARS] if number < len(pages) else ""
        head = before + ("\n\n" if before else "")
        text = head + page + ("\n\n" + after if after else "")
        region = PdfRegion(file=pdf_path.name, line_start=number, line_end=number, section=[], text=text,
                           pdf_path=pdf_path, page=number, page_start=len(head), page_end=len(head) + len(page))
        for start, end, kind, operators in lines:
            n += 1
            region.formulas.append(Formula(id=f"{id_prefix}{n}", kind=kind, line=number, start=len(head) + start,
                                           end=len(head) + end, source=page[start:end], hint=operators))
        context.regions.append(region)
    return context
