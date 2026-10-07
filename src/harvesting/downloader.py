from collections import Counter
import difflib
import gzip
import logging
from pathlib import Path, PurePosixPath
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


# Kept from arXiv bundles: .tex plus the files where authors define their macros
SOURCE_EXTENSIONS = (".tex", ".sty", ".cls", ".def")


def safe_member_path(member_name: str) -> PurePosixPath | None:
    """Returns the archive member's relative path, or None if it would escape the target folder."""
    path = PurePosixPath(member_name.replace("\\", "/"))
    parts = [p for p in path.parts if p != "."]
    if not parts or any(p in ("/", "..") or ":" in p for p in parts):
        return None
    return PurePosixPath(*parts)


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
        if any(tex_dir.rglob("*.tex")):
            return "downloaded_latex", f"data/raw/latex/{paper_id}"
        else:
            shutil.rmtree(tex_dir, ignore_errors=True)

    if pdf_file.is_file():
        if pdf_file.stat().st_size > 1024:
            return "downloaded_pdf", f"data/raw/pdfs/{paper_id}.pdf"
        else:
            pdf_file.unlink()

    return "pending", None

def download_and_extract_arxiv_tex(eprint_url: str, target_folder: Path) -> tuple[bool, str]:
    """Downloads an arXiv e-print bundle. Returns (success, reason)."""
    temp_archive = Path(f"{target_folder}_temp")
    try:
        resp = requests.get(eprint_url, headers=HEADERS, timeout=45, stream=True)
        if resp.status_code == 404:
            return False, "arXiv Error: HTTP 404 (Not Found)"
        if resp.status_code == 403:
            return False, "arXiv Error: HTTP 403 (Forbidden/Blocked)"
        if resp.status_code != 200:
            return False, f"arXiv Error: HTTP {resp.status_code}"

        with open(temp_archive, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        target_folder.mkdir(parents=True, exist_ok=True)

        if tarfile.is_tarfile(temp_archive):
            with tarfile.open(temp_archive, "r:*") as tar:
                tex_count = 0
                for member in tar.getmembers():
                    if not member.isfile() or not member.name.lower().endswith(SOURCE_EXTENSIONS):
                        continue
                    rel_path = safe_member_path(member.name)
                    src = tar.extractfile(member)
                    if rel_path is None or src is None:
                        continue
                    dst_path = target_folder / rel_path
                    try:
                        dst_path.parent.mkdir(parents=True, exist_ok=True)
                        with src, open(dst_path, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                    except OSError:
                        continue
                    if dst_path.suffix.lower() == ".tex":
                        tex_count += 1
            temp_archive.unlink(missing_ok=True)
            if tex_count > 0:
                return True, "Success"
            shutil.rmtree(target_folder, ignore_errors=True)
            return False, "Archive contained no .tex files"

        try:
            with gzip.open(temp_archive, "rb") as gz:
                content = gz.read()
                if not content.startswith(b"%PDF"):
                    with open(target_folder / "main.tex", "wb") as dst:
                        dst.write(content)
                    temp_archive.unlink(missing_ok=True)
                    return True, "Success"
        except OSError:
            pass

        shutil.rmtree(target_folder, ignore_errors=True)
        temp_archive.unlink(missing_ok=True)
        return False, "Invalid archive format or PDF only"

    except requests.exceptions.Timeout:
        return False, "arXiv Error: Connection Timeout"
    except Exception as e:
        shutil.rmtree(target_folder, ignore_errors=True)
        temp_archive.unlink(missing_ok=True)
        return False, f"arXiv Error: Network/System Exception"


def download_pdf_from_mirrors(
    pdf_urls: list[str], dest_path: Path, use_browser_headers: bool = True
) -> tuple[bool, str]:
    """Tries each mirror URL. Returns (success, reason)."""
    if not pdf_urls:
        return False, "No PDF URLs in metadata"

    req_headers = BROWSER_HEADERS if use_browser_headers else HEADERS
    last_reason = "Unknown Error"

    for url in pdf_urls:
        if not url:
            continue
        try:
            resp = requests.get(url, headers=req_headers, timeout=30, allow_redirects=True)
            
            if resp.status_code == 403:
                last_reason = "HTTP 403 (Paywall or Bot Protection)"
                continue
            if resp.status_code == 404:
                last_reason = "HTTP 404 (Dead Link)"
                continue
            if resp.status_code != 200:
                last_reason = f"HTTP {resp.status_code}"
                continue

            # Check magic bytes to ensure it's actually a PDF and not an HTML login page
            if resp.content.startswith(b"%PDF"):
                with open(dest_path, "wb") as f:
                    f.write(resp.content)
                return True, "Success"
            else:
                last_reason = "HTML Landing Page (Not a %PDF file)"
                
        except requests.exceptions.Timeout:
            last_reason = "Connection Timeout"
        except Exception:
            last_reason = "Connection Error (Domain unreachable)"

    return False, last_reason

# -------------------------------------------------------------------------
# SECOND-CHANCE RECOVERY HELPERS (Semantic Scholar, arXiv Title, HAL)
# -------------------------------------------------------------------------
RETRY_WAITS = (2, 5, 10)
MAX_CONSECUTIVE_GIVE_UPS = 20

# Lookups abandoned while the service was still throttling us, per service (read by scripts/02 for reporting)
rate_limit_hits = Counter()
_consecutive_give_ups = Counter()


def get_with_backoff(service: str, url: str, timeout: int) -> requests.Response:
    """
    GET for the recovery lookups. Retries on 429/503 so a throttled lookup is not mistaken for "not found".
    If a service keeps throttling for many papers in a row, stops waiting on it until it answers again.
    """
    waits = RETRY_WAITS if _consecutive_give_ups[service] < MAX_CONSECUTIVE_GIVE_UPS else ()
    for wait in (*waits, None):
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code not in (429, 503):
            _consecutive_give_ups[service] = 0
            return resp
        if wait is not None:
            retry_after = resp.headers.get("Retry-After", "")
            time.sleep(min(int(retry_after), 30) if retry_after.isdigit() else wait)

    _consecutive_give_ups[service] += 1
    rate_limit_hits[service] += 1
    logging.warning(f"    [!] {service} lookup rate-limited (HTTP {resp.status_code}), giving up on this paper.")
    return resp


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
        resp = get_with_backoff("arXiv title search", url, timeout=20)
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
        resp = get_with_backoff("Semantic Scholar", url, timeout=15)
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
        resp = get_with_backoff("HAL", url, timeout=15)
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