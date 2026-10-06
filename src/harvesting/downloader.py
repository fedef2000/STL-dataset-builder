import difflib
import gzip
import os
from pathlib import Path
import shutil
import tarfile
import time
import urllib.parse
import xml.etree.ElementTree as ET
import requests
from config import HEADERS, RAW_LATEX_DIR, RAW_PDF_DIR

# Standard browser headers to avoid 403 blocks on university/institutional PDF repositories
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def verify_disk_status(paper_id: str) -> tuple[str, str | None]:
    """
    Verifies if a paper's files actually exist on disk and are non-empty.
    Cleans up any partial artifacts left behind by an interrupted run (Ctrl+C).
    """
    tex_dir = RAW_LATEX_DIR / paper_id
    pdf_file = RAW_PDF_DIR / f"{paper_id}.pdf"
    temp_archive = RAW_LATEX_DIR / f"{paper_id}_temp"

    if temp_archive.exists():
        temp_archive.unlink()

    if tex_dir.is_dir():
        tex_files = list(tex_dir.glob("*.tex"))
        if len(tex_files) > 0:
            return "downloaded_latex", f"data/raw/latex/{paper_id}"
        else:
            shutil.rmtree(tex_dir, ignore_errors=True)

    if pdf_file.is_file():
        if pdf_file.stat().st_size > 1024:
            return "downloaded_pdf", f"data/raw/pdfs/{paper_id}.pdf"
        else:
            pdf_file.unlink()

    return "pending", None


def download_and_extract_arxiv_tex(eprint_url: str, target_folder: Path) -> bool:
    """Downloads an arXiv e-print bundle and extracts only the .tex files."""
    temp_archive = Path(f"{target_folder}_temp")
    try:
        resp = requests.get(eprint_url, headers=HEADERS, timeout=45, stream=True)
        if resp.status_code != 200:
            return False

        with open(temp_archive, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        target_folder.mkdir(parents=True, exist_ok=True)

        # Case 1: Multi-file .tar.gz archive (most common on arXiv)
        if tarfile.is_tarfile(temp_archive):
            with tarfile.open(temp_archive, "r:*") as tar:
                tex_members = [
                    m
                    for m in tar.getmembers()
                    if m.isfile() and m.name.lower().endswith(".tex")
                ]
                for member in tex_members:
                    safe_name = os.path.basename(member.name)
                    src = tar.extractfile(member)
                    if src:
                        with src, open(target_folder / safe_name, "wb") as dst:
                            shutil.copyfileobj(src, dst)
            temp_archive.unlink(missing_ok=True)
            if len(tex_members) > 0:
                return True
            shutil.rmtree(target_folder, ignore_errors=True)
            return False

        # Case 2: Single .tex file compressed with gzip (not tarred)
        try:
            with gzip.open(temp_archive, "rb") as gz:
                content = gz.read()
                if not content.startswith(b"%PDF"):
                    with open(target_folder / "main.tex", "wb") as dst:
                        dst.write(content)
                    temp_archive.unlink(missing_ok=True)
                    return True
        except OSError:
            pass

        shutil.rmtree(target_folder, ignore_errors=True)
        temp_archive.unlink(missing_ok=True)
        return False

    except Exception:
        shutil.rmtree(target_folder, ignore_errors=True)
        temp_archive.unlink(missing_ok=True)
        return False


def download_pdf_from_mirrors(
    pdf_urls: list[str], dest_path: Path, use_browser_headers: bool = True
) -> bool:
    """Tries each mirror URL until a valid PDF (verified via %PDF magic bytes) is saved."""
    req_headers = BROWSER_HEADERS if use_browser_headers else HEADERS
    for url in pdf_urls:
        if not url:
            continue
        try:
            resp = requests.get(
                url, headers=req_headers, timeout=30, allow_redirects=True
            )
            if resp.status_code == 200 and resp.content.startswith(b"%PDF"):
                with open(dest_path, "wb") as f:
                    f.write(resp.content)
                return True
        except Exception:
            continue
    return False


# -------------------------------------------------------------------------
# SECOND-CHANCE RECOVERY HELPERS (Semantic Scholar, arXiv Title, HAL)
# -------------------------------------------------------------------------
def _similar_title(t1: str, t2: str, threshold: float = 0.88) -> bool:
    clean1 = "".join(c.lower() for c in (t1 or "") if c.isalnum() or c == " ")
    clean2 = "".join(c.lower() for c in (t2 or "") if c.isalnum() or c == " ")
    return difflib.SequenceMatcher(None, clean1, clean2).ratio() >= threshold


def find_arxiv_by_title(title: str) -> str | None:
    """Searches arXiv API by exact title to catch preprints unlinked in OpenAlex."""
    if not title or len(title) < 15:
        return None
    clean_q = "".join(c if c.isalnum() or c == " " else " " for c in title)
    query = urllib.parse.quote(f'ti:"{clean_q}"')
    url = f"http://export.arxiv.org/api/query?search_query={query}&max_results=3"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return None
        root = ET.fromstring(resp.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns):
            cand_title = entry.find("atom:title", ns).text.replace("\n", " ")
            if _similar_title(title, cand_title):
                id_url = entry.find("atom:id", ns).text
                return id_url.split("/abs/")[-1].split("v")[0]
    except Exception:
        pass
    return None


def find_via_semantic_scholar(doi: str | None) -> tuple[str | None, str | None]:
    """Queries Semantic Scholar by DOI for unlinked ArXiv IDs or openAccessPdf URLs."""
    if not doi:
        return None, None
    try:
        clean_doi = doi.replace("https://doi.org/", "")
        url = (
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{clean_doi}"
            f"?fields=externalIds,openAccessPdf"
        )
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            arxiv_id = (data.get("externalIds") or {}).get("ArXiv")
            oa_pdf = (data.get("openAccessPdf") or {}).get("url")
            return arxiv_id, oa_pdf
    except Exception:
        pass
    return None, None


def find_via_hal(title: str) -> str | None:
    """Queries France's HAL archive by title for open PDFs."""
    if not title:
        return None
    q = urllib.parse.quote(f'title_t:("{title}")')
    url = f"https://api.archives-ouvertes.fr/search/?q={q}&fl=title_s,fileMain_s&wt=json&rows=3"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            docs = resp.json().get("response", {}).get("docs", [])
            for d in docs:
                hal_titles = d.get("title_s") or []
                if any(_similar_title(title, ht) for ht in hal_titles):
                    if d.get("fileMain_s"):
                        return d["fileMain_s"]
    except Exception:
        pass
    return None