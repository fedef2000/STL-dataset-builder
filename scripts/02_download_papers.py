import argparse
import logging
from pathlib import Path
import sys
import time
from collections import Counter

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import LOG_FILE, RAW_LATEX_DIR, RAW_PDF_DIR
from src.harvesting.downloader import (
    check_semantic_scholar,
    download_and_extract_arxiv_tex,
    download_pdf_from_mirrors,
    find_arxiv_by_title,
    find_via_hal,
    find_via_semantic_scholar,
    rate_limit_hits,
    verify_disk_status,
)
from src.storage import CorpusStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)

def sync_corpus_with_disk(store: CorpusStore) -> dict:
    counts = {"downloaded_latex": 0, "downloaded_pdf": 0, "unavailable": 0, "pending": 0}
    for pid, paper in store.papers.items():
        disk_status, disk_path = verify_disk_status(pid)
        cur_status = paper.get("local_files", {}).get("status", "pending")

        if disk_status in ("downloaded_latex", "downloaded_pdf"):
            paper["local_files"]["status"] = disk_status
            paper["local_files"]["path"] = disk_path
            counts[disk_status] += 1
        else:
            effective_status = "unavailable" if cur_status == "unavailable" else "pending"
            paper["local_files"]["status"] = effective_status
            paper["local_files"]["path"] = None
            counts[effective_status] += 1
    store.save()
    return counts

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-recovery", action="store_true")
    parser.add_argument("--retry-unavailable", action="store_true")
    parser.add_argument("--retry-rate-limited", action="store_true", help="Retry only unavailable papers whose recovery lookups were rate-limited.")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    store = CorpusStore()
    counts = sync_corpus_with_disk(store)
    total_corpus = len(store.papers)
    failure_stats = Counter()

    target_statuses = {"pending"}
    if args.retry_unavailable:
        target_statuses.add("unavailable")

    queue = [pid for pid, p in store.papers.items() if p.get("local_files", {}).get("status") in target_statuses]
    if args.retry_rate_limited and not args.retry_unavailable:
        queue += [
            pid for pid, p in store.papers.items()
            if p.get("local_files", {}).get("status") == "unavailable" and p["local_files"].get("recovery_rate_limited")
        ]
    if args.limit:
        queue = queue[: args.limit]

    logging.info(f"=== STEP 2 START | Queued: {len(queue)} ===")
    if args.with_recovery:
        logging.info(f"Semantic Scholar check: {check_semantic_scholar()}")

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
        rate_limit_hits_before = sum(rate_limit_hits.values())
        if paper.get("is_oa") is False:
            current_failure_reason = "Closed Access / Paywalled"
        else:
            current_failure_reason = "Open Access but URLs missing/dead"

        # TIER 1: arXiv .tex
        if eprint_url:
            success, reason = download_and_extract_arxiv_tex(eprint_url, tex_folder)
            if success:
                paper["local_files"] = {"status": "downloaded_latex", "path": f"data/raw/latex/{pid}"}
                counts["downloaded_latex"] += 1
                downloaded = True
                status_label = f"SUCCESS [LaTeX] {pid}"
            else:
                current_failure_reason = reason
            time.sleep(3.5)

        # TIER 2: Recovery
        if not downloaded and args.with_recovery:
            s2_arxiv, s2_pdf = find_via_semantic_scholar(paper.get("doi"))
            rec_arxiv = s2_arxiv or find_arxiv_by_title(paper.get("title") or "")
            if rec_arxiv and not eprint_url:
                rec_eprint = f"https://export.arxiv.org/e-print/{rec_arxiv}"
                paper["arxiv_id"] = rec_arxiv
                paper["urls"]["eprint_source"] = rec_eprint
                success, reason = download_and_extract_arxiv_tex(rec_eprint, tex_folder)
                if success:
                    paper["local_files"] = {"status": "downloaded_latex", "path": f"data/raw/latex/{pid}"}
                    counts["downloaded_latex"] += 1
                    downloaded = True
                    status_label = f"RECOVERED [LaTeX] {pid}"
                else:
                    current_failure_reason = reason
                time.sleep(3.5)

            if not downloaded:
                if s2_pdf and s2_pdf not in pdf_mirrors: pdf_mirrors.append(s2_pdf)
                hal_pdf = find_via_hal(paper.get("title") or "")
                if hal_pdf and hal_pdf not in pdf_mirrors: pdf_mirrors.append(hal_pdf)
                paper["urls"]["pdf_mirrors"] = pdf_mirrors
                time.sleep(1.0)

        # TIER 3: PDF Mirrors
        if not downloaded and pdf_mirrors:
            success, reason = download_pdf_from_mirrors(pdf_mirrors, pdf_path, use_browser_headers=True)
            if success:
                paper["local_files"] = {"status": "downloaded_pdf", "path": f"data/raw/pdfs/{pid}.pdf"}
                counts["downloaded_pdf"] += 1
                downloaded = True
                status_label = f"SUCCESS [PDF]   {pid}"
            else:
                current_failure_reason = f"PDF Mirrors: {reason}"
            time.sleep(1.0)

        # Handle Failure
        if not downloaded:
            paper["local_files"] = {
                "status": "unavailable",
                "path": None,
                "failure_reason": current_failure_reason
            }
            # A throttled recovery lookup is not a real "not found": mark it so the paper can be retried
            if sum(rate_limit_hits.values()) > rate_limit_hits_before:
                paper["local_files"]["recovery_rate_limited"] = True
            counts["unavailable"] += 1
            failure_stats[current_failure_reason] += 1
            status_label = f"FAILED  [{current_failure_reason[:30]}] {pid}"

        store.save()
        logging.info(f"[{attempted}/{len(queue)}] {status_label}")

    logging.info("=== STEP 2 FINISHED ===")
    for service, hits in rate_limit_hits.most_common():
        logging.info(f"Recovery lookups abandoned due to rate limiting | {service}: {hits}")
    
    # Print Statistical Report
    if failure_stats:
        print("\n" + "=" * 60)
        print("                 UNAVAILABLE PAPER STATS")
        print("=" * 60)
        for reason, count in failure_stats.most_common():
            print(f"{count:>5} | {reason}")
        print("=" * 60)

if __name__ == "__main__":
    main()