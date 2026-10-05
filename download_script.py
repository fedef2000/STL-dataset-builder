from datetime import datetime
import gzip
import json
import logging
import os
import shutil
import tarfile
import time
import requests

INPUT_JSON = "stl_expanded_corpus.json"
LATEX_DIR = "./dataset_raw/latex"
PDF_DIR = "./dataset_raw/pdfs"
LOG_FILE = "./dataset_raw/download_progress.log"
STATE_FILE = "./dataset_raw/download_state.json"

os.makedirs(LATEX_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "NL2STL-ResearchHarvester/2.1 (mailto:your-email@domain.com)"
}

# Configure logging to write to BOTH the log file and your terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)


def is_already_downloaded(work_id):
    """
    Checks if a paper was completely downloaded on disk.
    Cleans up empty folders or 0-byte files left behind by Ctrl+C.
    """
    tex_folder = os.path.join(LATEX_DIR, work_id)
    pdf_path = os.path.join(PDF_DIR, f"{work_id}.pdf")
    temp_archive = f"{tex_folder}_temp"

    # Remove leftover temporary archive from an interrupted download
    if os.path.exists(temp_archive):
        os.remove(temp_archive)

    # Check if tex_folder exists AND actually contains at least one .tex file
    if os.path.isdir(tex_folder):
        tex_files = [f for f in os.listdir(tex_folder) if f.lower().endswith(".tex")]
        if len(tex_files) > 0:
            return "latex"
        else:
            # Folder was created right before Ctrl+C — remove it so we retry
            shutil.rmtree(tex_folder, ignore_errors=True)

    # Check if PDF exists and is not an empty 0-byte file
    if os.path.isfile(pdf_path):
        if os.path.getsize(pdf_path) > 1024:  # At least 1 KB
            return "pdf"
        else:
            os.remove(pdf_path)

    return None


def load_or_sync_state(corpus):
    """Syncs disk state with download_state.json so counts are 100% accurate."""
    state = {"latex": [], "pdf": [], "failed": []}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            pass

    latex_set = set(state.get("latex", []))
    pdf_set = set(state.get("pdf", []))
    failed_set = set(state.get("failed", []))

    # Scan actual folders on disk to catch everything from your first interrupted run
    for paper in corpus:
        work_id = paper["openalex_id"].split("/")[-1]
        status = is_already_downloaded(work_id)
        if status == "latex":
            latex_set.add(work_id)
            failed_set.discard(work_id)
        elif status == "pdf":
            pdf_set.add(work_id)
            failed_set.discard(work_id)

    return {"latex": latex_set, "pdf": pdf_set, "failed": failed_set}


def save_state(state):
    """Saves sets as JSON lists to disk after each paper."""
    serializable = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "counts": {
            "total_downloaded": len(state["latex"]) + len(state["pdf"]),
            "latex_count": len(state["latex"]),
            "pdf_count": len(state["pdf"]),
            "failed_count": len(state["failed"]),
        },
        "latex": sorted(list(state["latex"])),
        "pdf": sorted(list(state["pdf"])),
        "failed": sorted(list(state["failed"])),
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2)


def download_and_extract_arxiv_tex(eprint_url, target_folder):
    """Downloads an arXiv e-print bundle and extracts only the .tex files."""
    temp_archive = f"{target_folder}_temp"
    try:
        resp = requests.get(eprint_url, headers=HEADERS, timeout=45, stream=True)
        if resp.status_code != 200:
            return False

        with open(temp_archive, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        os.makedirs(target_folder, exist_ok=True)

        # Case 1: Multi-file .tar.gz archive
        if tarfile.is_tarfile(temp_archive):
            with tarfile.open(temp_archive, "r:*") as tar:
                tex_members = [
                    m for m in tar.getmembers()
                    if m.isfile() and m.name.lower().endswith(".tex")
                ]
                for member in tex_members:
                    safe_name = os.path.basename(member.name)
                    with tar.extractfile(member) as src, open(
                        os.path.join(target_folder, safe_name), "wb"
                    ) as dst:
                        shutil.copyfileobj(src, dst)
            os.remove(temp_archive)
            if len(tex_members) > 0:
                return True
            shutil.rmtree(target_folder, ignore_errors=True)
            return False

        # Case 2: Single .tex file compressed with gzip
        try:
            with gzip.open(temp_archive, "rb") as gz:
                content = gz.read()
                if not content.startswith(b"%PDF"):
                    with open(os.path.join(target_folder, "main.tex"), "wb") as dst:
                        dst.write(content)
                    os.remove(temp_archive)
                    return True
        except OSError:
            pass

        shutil.rmtree(target_folder, ignore_errors=True)
        os.remove(temp_archive)
        return False

    except Exception as e:
        shutil.rmtree(target_folder, ignore_errors=True)
        if os.path.exists(temp_archive):
            os.remove(temp_archive)
        return False


def download_fallback_pdf(pdf_urls, pdf_dest_path):
    """Tries each mirror URL in pdf_urls until a valid PDF is downloaded."""
    for url in pdf_urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
            if resp.status_code == 200 and resp.content.startswith(b"%PDF"):
                with open(pdf_dest_path, "wb") as f:
                    f.write(resp.content)
                return True
        except Exception:
            continue
    return False


if __name__ == "__main__":
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    # Sync existing files on disk from your previous run
    state = load_or_sync_state(corpus)
    save_state(state)

    logging.info(
        f"=== RESUMING RUN | Already on disk -> "
        f"LaTeX: {len(state['latex'])} | PDFs: {len(state['pdf'])} | "
        f"Total Downloaded: {len(state['latex']) + len(state['pdf'])}/{len(corpus)} ==="
    )

    for idx, paper in enumerate(corpus, 1):
        work_id = paper["openalex_id"].split("/")[-1]

        # Skip if already downloaded or already known to have no working links
        if (
            work_id in state["latex"]
            or work_id in state["pdf"]
            or work_id in state["failed"]
        ):
            continue

        eprint_url = paper.get("eprint_source_url")
        pdf_urls = paper.get("pdf_urls") or []

        # Skip immediately if paper has neither arXiv nor OA PDF links
        if not eprint_url and not pdf_urls:
            state["failed"].add(work_id)
            save_state(state)
            continue

        tex_folder = os.path.join(LATEX_DIR, work_id)
        pdf_path = os.path.join(PDF_DIR, f"{work_id}.pdf")
        downloaded = False

        # TIER 1: Try arXiv LaTeX
        if eprint_url:
            if download_and_extract_arxiv_tex(eprint_url, tex_folder):
                state["latex"].add(work_id)
                downloaded = True
                status_msg = f"SUCCESS [LaTeX] {work_id} ({paper.get('arxiv_id')})"
            time.sleep(3.5)

        # TIER 2: Fallback to Open Access PDF
        if not downloaded and pdf_urls:
            if download_fallback_pdf(pdf_urls, pdf_path):
                state["pdf"].add(work_id)
                downloaded = True
                status_msg = f"SUCCESS [PDF]   {work_id}"
            time.sleep(1.0)

        if not downloaded:
            state["failed"].add(work_id)
            status_msg = f"FAILED  [None]  {work_id}"

        save_state(state)
        total_dl = len(state["latex"]) + len(state["pdf"])
        logging.info(
            f"[{idx}/{len(corpus)}] {status_msg} | "
            f"Running Totals -> Downloaded: {total_dl} "
            f"(LaTeX: {len(state['latex'])}, PDF: {len(state['pdf'])}) | "
            f"Unavailable: {len(state['failed'])}"
        )

    logging.info(
        f"=== FINISHED | Total Downloaded: {len(state['latex']) + len(state['pdf'])} "
        f"(LaTeX: {len(state['latex'])}, PDFs: {len(state['pdf'])}) ==="
    )