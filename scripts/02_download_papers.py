import argparse
import logging
from pathlib import Path
import sys
import time

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import LOG_FILE, RAW_LATEX_DIR, RAW_PDF_DIR
from src.harvesting.downloader import (
    download_and_extract_arxiv_tex,
    download_pdf_from_mirrors,
    find_arxiv_by_title,
    find_via_hal,
    find_via_semantic_scholar,
    verify_disk_status,
)
from src.storage import CorpusStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


def sync_corpus_with_disk(store: CorpusStore) -> dict:
    """
    Ensures every paper's local_files.status in corpus.json matches actual files on disk,
    and returns summary counts.
    """
    counts = {
        "downloaded_latex": 0,
        "downloaded_pdf": 0,
        "unavailable": 0,
        "pending": 0,
    }

    for pid, paper in store.papers.items():
        disk_status, disk_path = verify_disk_status(pid)
        cur_status = paper.get("local_files", {}).get("status", "pending")

        if disk_status in ("downloaded_latex", "downloaded_pdf"):
            paper["local_files"] = {"status": disk_status, "path": disk_path}
            counts[disk_status] += 1
        else:
            # Keep 'unavailable' if it was already marked unavailable; otherwise set to 'pending'
            effective_status = (
                "unavailable" if cur_status == "unavailable" else "pending"
            )
            paper["local_files"] = {"status": effective_status, "path": None}
            counts[effective_status] += 1

    store.save()
    return counts


def main():
    parser = argparse.ArgumentParser(
        description="Step 2: Download LaTeX sources and fallback PDFs for papers in data/corpus.json."
    )
    parser.add_argument(
        "--with-recovery",
        action="store_true",
        help="Query Semantic Scholar, arXiv title search, and HAL when primary links are missing/broken.",
    )
    parser.add_argument(
        "--retry-unavailable",
        action="store_true",
        help="Re-attempt papers previously marked as 'unavailable' in corpus.json.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of papers to attempt in this run.",
    )
    args = parser.parse_args()

    store = CorpusStore()
    counts = sync_corpus_with_disk(store)
    total_corpus = len(store.papers)

    target_statuses = {"pending"}
    if args.retry_unavailable:
        target_statuses.add("unavailable")

    queue = [
        pid
        for pid, p in store.papers.items()
        if p.get("local_files", {}).get("status") in target_statuses
    ]

    if args.limit:
        queue = queue[: args.limit]

    logging.info(
        f"=== STEP 2 HARVESTER START | Corpus: {total_corpus} | "
        f"On Disk -> LaTeX: {counts['downloaded_latex']}, PDF: {counts['downloaded_pdf']} | "
        f"Unavailable: {counts['unavailable']} | Queued to try: {len(queue)} ==="
    )

    attempted = 0
    for pid in queue:
        attempted += 1
        paper = store.papers[pid]
        urls = paper.get("urls") or {}
        eprint_url = urls.get("eprint_source")
        pdf_mirrors = list(urls.get("pdf_mirrors") or [])

        tex_folder = RAW_LATEX_DIR / pid
        pdf_path = RAW_PDF_DIR / f"{pid}.pdf"
        downloaded = False
        status_label = ""

        # ---------------------------------------------------------------------
        # TIER 1: Try known arXiv e-print source bundle (.tex)
        # ---------------------------------------------------------------------
        if eprint_url:
            if download_and_extract_arxiv_tex(eprint_url, tex_folder):
                paper["local_files"] = {
                    "status": "downloaded_latex",
                    "path": f"data/raw/latex/{pid}",
                }
                counts["downloaded_latex"] += 1
                counts[
                    "pending" if not args.retry_unavailable else "unavailable"
                ] = max(
                    0,
                    counts[
                        "pending"
                        if not args.retry_unavailable
                        else "unavailable"
                    ]
                    - 1,
                )
                downloaded = True
                status_label = f"SUCCESS [LaTeX] {pid} ({paper.get('arxiv_id')})"
            time.sleep(3.5)  # Mandatory polite delay for export.arxiv.org

        # ---------------------------------------------------------------------
        # TIER 2: Optional Deep Recovery (Semantic Scholar + arXiv Title + HAL)
        # ---------------------------------------------------------------------
        if not downloaded and args.with_recovery:
            s2_arxiv, s2_pdf = find_via_semantic_scholar(paper.get("doi"))
            recovered_arxiv = s2_arxiv or find_arxiv_by_title(
                paper.get("title") or ""
            )

            if recovered_arxiv and not eprint_url:
                rec_eprint = (
                    f"https://export.arxiv.org/e-print/{recovered_arxiv}"
                )
                paper["arxiv_id"] = recovered_arxiv
                paper["urls"]["eprint_source"] = rec_eprint
                if download_and_extract_arxiv_tex(rec_eprint, tex_folder):
                    paper["local_files"] = {
                        "status": "downloaded_latex",
                        "path": f"data/raw/latex/{pid}",
                    }
                    counts["downloaded_latex"] += 1
                    downloaded = True
                    status_label = (
                        f"RECOVERED [LaTeX] {pid} (arXiv:{recovered_arxiv})"
                    )
                time.sleep(3.5)

            if not downloaded:
                if s2_pdf and s2_pdf not in pdf_mirrors:
                    pdf_mirrors.append(s2_pdf)
                hal_pdf = find_via_hal(paper.get("title") or "")
                if hal_pdf and hal_pdf not in pdf_mirrors:
                    pdf_mirrors.append(hal_pdf)
                paper["urls"]["pdf_mirrors"] = pdf_mirrors
                time.sleep(1.0)

        # ---------------------------------------------------------------------
        # TIER 3: Try Open Access PDF Mirrors (with Browser Headers)
        # ---------------------------------------------------------------------
        if not downloaded and pdf_mirrors:
            if download_pdf_from_mirrors(
                pdf_mirrors, pdf_path, use_browser_headers=True
            ):
                paper["local_files"] = {
                    "status": "downloaded_pdf",
                    "path": f"data/raw/pdfs/{pid}.pdf",
                }
                counts["downloaded_pdf"] += 1
                downloaded = True
                status_label = f"SUCCESS [PDF]   {pid}"
            time.sleep(1.0)

        # ---------------------------------------------------------------------
        # Mark Unavailable if all tiers failed
        # ---------------------------------------------------------------------
        if not downloaded:
            paper["local_files"] = {"status": "unavailable", "path": None}
            counts["unavailable"] += 1
            status_label = f"FAILED  [None]  {pid}"

        # Persist directly into data/corpus.json after every paper
        store.save()

        total_dl = counts["downloaded_latex"] + counts["downloaded_pdf"]
        logging.info(
            f"[{attempted}/{len(queue)}] {status_label} | "
            f"Totals -> Downloaded: {total_dl} "
            f"(LaTeX: {counts['downloaded_latex']}, PDF: {counts['downloaded_pdf']}) | "
            f"Unavailable: {counts['unavailable']}"
        )

    total_dl = counts["downloaded_latex"] + counts["downloaded_pdf"]
    logging.info(
        f"=== STEP 2 FINISHED | Total Downloaded: {total_dl}/{total_corpus} "
        f"(LaTeX: {counts['downloaded_latex']}, PDFs: {counts['downloaded_pdf']}, "
        f"Unavailable: {counts['unavailable']}) ==="
    )


if __name__ == "__main__":
    main()