import gzip
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
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


# What the less common HTTP answers from PDF hosts mean in practice
PDF_STATUS_NOTES = {
    202: "Bot Protection Challenge",
    401: "Login Required",
    405: "Bot Protection",
    406: "Bot Protection",
    410: "Removed by Host",
    418: "Bot Protection",
    429: "Rate Limited",
}

# Failure reasons worth trying again later: network trouble, rate limits and server-side errors
TRANSIENT_FAILURE_MARKERS = (
    "Connection Error", "Connection Timeout", "Network/System Exception",
    "HTTP 429", "HTTP 500", "HTTP 502", "HTTP 503", "HTTP 504",
)


def is_transient_failure(failure_reason: str | None) -> bool:
    return any(marker in (failure_reason or "") for marker in TRANSIENT_FAILURE_MARKERS)


# Labels used before the reasons were made more descriptive
LEGACY_NO_LINK_REASONS = ("Closed Access / Paywalled", "Open Access but URLs missing/dead")


def has_unanswered_lookup(paper: dict) -> bool:
    """True when a lookup of the step 1 enrichment got no answer for this paper, so a link may still turn up."""
    return any(entry.get("status") == "no_answer" for entry in (paper.get("lookups") or {}).values())


def no_link_reason(paper: dict) -> str:
    """Reason for a paper that was never attempted because no source or PDF link is known for it."""
    if has_unanswered_lookup(paper):
        return "No Link Found (a lookup got no answer, run the enrichment again)"
    if paper.get("is_oa") is False:
        return "No Link Found (not open access)"
    return "No Link Found (open access, but no URL listed)"


def relabel_failure_reason(paper: dict) -> str | None:
    """Rewrites a stored failure reason in the current wording, using only what the corpus already records."""
    local_files = paper.get("local_files") or {}
    reason = local_files.get("failure_reason")
    if not reason:
        return reason
    if reason in LEGACY_NO_LINK_REASONS or reason.startswith("No Link Found"):
        return no_link_reason(paper)
    m = re.fullmatch(r"(.*HTTP (\d{3}))", reason)
    if m and int(m.group(2)) in PDF_STATUS_NOTES:
        return f"{m.group(1)} ({PDF_STATUS_NOTES[int(m.group(2))]})"
    return reason


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
                note = PDF_STATUS_NOTES.get(resp.status_code)
                last_reason = f"HTTP {resp.status_code} ({note})" if note else f"HTTP {resp.status_code}"
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
        except requests.exceptions.SSLError:
            last_reason = "SSL Certificate Error"
        except Exception:
            last_reason = "Connection Error (Domain unreachable)"

    return False, last_reason
