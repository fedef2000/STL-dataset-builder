import re
from pathlib import Path

# LaTeX Regex: Matches operators followed by numeric intervals (e.g., \always_{[0, 5]}, \mathcal{G}_{0, 10}, G_{[0.5, 2.0]})
LATEX_CONCRETE_PATTERN = re.compile(
    r"(?:\\always|\\eventually|\\square|\\lozenge|\\Box|\\Diamond|\\mathcal\{G\}|\\mathcal\{F\}|\\mathbf\{G\}|\\mathbf\{F\}|\\Until|\b[GFU]\b)\s*"
    r"[_^]\s*\{?\s*\[\s*\d+(?:\.\d+)?\s*,\s*\d+(?:\.\d+)?\s*\]\s*\}?",
    re.IGNORECASE
)

# LaTeX Regex: Matches operators followed by symbolic/parameterized intervals (e.g., \always_{[0, \tau]}, \mathcal{F}_{[t_1, t_2]})
LATEX_SYMBOLIC_PATTERN = re.compile(
    r"(?:\\always|\\eventually|\\square|\\lozenge|\\Box|\\Diamond|\\mathcal\{G\}|\\mathcal\{F\}|\\mathbf\{G\}|\\mathbf\{F\}|\\Until|\b[GFU]\b)\s*"
    r"[_^]\s*\{?\s*\[\s*(?:[a-zA-Z\\][a-zA-Z0-9_^]*|\d+(?:\.\d+)?)\s*,\s*(?:[a-zA-Z\\][a-zA-Z0-9_^]*|\d+(?:\.\d+)?)\s*\]\s*\}?",
    re.IGNORECASE
)

# PDF Regex: PDFs lose LaTeX macros, so we look for raw text approximations (e.g., G[0, 5], Always_[0, 10])
PDF_CONCRETE_PATTERN = re.compile(
    r"\b(?:G|F|U|always|eventually|square|lozenge)\b\s*[\[_\{]\s*\d+(?:\.\d+)?\s*,\s*\d+(?:\.\d+)?\s*[\]\}]",
    re.IGNORECASE
)

def strip_latex_comments(text: str) -> str:
    """Removes commented-out lines to prevent counting formulas that authors deleted/disabled."""
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in text.splitlines())

def estimate_tex_folder(tex_folder: Path) -> dict:
    """Scans all .tex files in a folder and counts formula matches."""
    counts = {"concrete": 0, "symbolic": 0}
    if not tex_folder.is_dir():
        return counts

    for tex_file in tex_folder.glob("*.tex"):
        try:
            raw = tex_file.read_text(encoding="utf-8", errors="ignore")
            active_code = strip_latex_comments(raw)
            
            # Find all symbolic patterns first
            symbolic_matches = LATEX_SYMBOLIC_PATTERN.findall(active_code)
            # Find strictly concrete ones
            concrete_matches = LATEX_CONCRETE_PATTERN.findall(active_code)
            
            # The symbolic regex matches concrete ones too (since numbers are valid symbols), 
            # so we subtract concrete to get purely symbolic parameterized formulas.
            pure_symbolic_count = max(0, len(symbolic_matches) - len(concrete_matches))
            
            counts["concrete"] += len(concrete_matches)
            counts["symbolic"] += pure_symbolic_count
        except Exception:
            continue
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