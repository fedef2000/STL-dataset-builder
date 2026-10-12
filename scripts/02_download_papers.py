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
    download_and_extract_arxiv_tex,
    download_pdf_from_mirrors,
    has_unanswered_lookup,
    is_transient_failure,
    no_link_reason,
    relabel_failure_reason,
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

def print_corpus_stats(store: CorpusStore, counts: dict) -> None:
    total = max(1, len(store.papers))
    unavailable_papers = [p for p in store.papers.values() if p.get("local_files", {}).get("status") == "unavailable"]
    unavailable = [p["local_files"] for p in unavailable_papers]
    reasons = Counter(lf.get("failure_reason") or "No reason recorded" for lf in unavailable)

    print("\n" + "=" * 60)
    print("                 CORPUS DOWNLOAD STATS")
    print("=" * 60)
    print(f"{len(store.papers):>5} | Total papers")
    downloaded = counts["downloaded_latex"] + counts["downloaded_pdf"]
    print(f"{downloaded:>5} | Downloaded, LaTeX + PDF ({downloaded / total * 100:.1f}%)")
    for status, label in (("downloaded_latex", "    LaTeX source"), ("downloaded_pdf", "    PDF only"), ("unavailable", "Unavailable"), ("pending", "Not tried yet")):
        print(f"{counts[status]:>5} | {label} ({counts[status] / total * 100:.1f}%)")
    print("-" * 60)
    print("Unavailable papers by failure reason:")
    for reason, count in reasons.most_common():
        print(f"{count:>5} | {reason}")
    print("-" * 60)
    print(f"{sum(1 for lf in unavailable if is_transient_failure(lf.get('failure_reason'))):>5} | would be retried by --retry-transient")
    print(f"{sum(1 for p in unavailable_papers if has_unanswered_lookup(p)):>5} | have a lookup that got no answer (01_build_corpus.py --mode enrich asks again)")
    print("=" * 60)

# Answers from arXiv that will not change: the paper has no LaTeX source there
NO_LATEX_SOURCE_REASONS = ("Archive contained no .tex files", "Invalid archive format or PDF only", "arXiv Error: HTTP 404 (Not Found)")

# When arXiv answers "slow down" (HTTP 429 or 503): seconds to wait before each new try of the same paper
RATE_LIMIT_WAITS = (30, 60, 120, 300)
# Each rate-limit answer doubles the pause between papers, up to this many seconds
MAX_UPGRADE_DELAY = 30.0
# A dropped connection or a timeout is tried once more after this many seconds
TRANSIENT_RETRY_WAIT = 10

def is_rate_limited(reason: str) -> bool:
    return "HTTP 429" in reason or "HTTP 503" in reason

class ArxivPacer:
    """
    Downloads arXiv LaTeX sources at a pace arXiv accepts. When arXiv rate-limits, the same paper is tried again
    after a growing wait and the pause between arXiv papers is raised; it comes back down once arXiv stops refusing.
    """
    def __init__(self, base_delay: float = 3.5):
        self.base_delay = base_delay
        self.delay = base_delay
        self.rate_limit_answers = 0
        self.answers_in_a_row = 0

    def fetch(self, pid: str, eprint_url: str, indent: str = "") -> tuple[bool, str, bool]:
        """Returns (success, reason, gave_up). gave_up: arXiv still refuses after the last wait, the caller should stop."""
        rate_limit_tries, transient_retried = 0, False
        while True:
            success, reason = download_and_extract_arxiv_tex(eprint_url, RAW_LATEX_DIR / pid)
            if success or reason in NO_LATEX_SOURCE_REASONS:
                return success, reason, False
            if is_rate_limited(reason):
                self.rate_limit_answers += 1
                self.answers_in_a_row = 0
                self.delay = min(max(self.delay * 2, self.base_delay), max(MAX_UPGRADE_DELAY, self.base_delay))
                if rate_limit_tries == len(RATE_LIMIT_WAITS):
                    return False, reason, True
                wait = RATE_LIMIT_WAITS[rate_limit_tries]
                rate_limit_tries += 1
                logging.info(f"{indent} waiting   | {pid:<12} | arXiv asked to slow down ({reason.removeprefix('arXiv Error: ')}): "
                             f"trying again in {wait} s (try {rate_limit_tries + 1} of {len(RATE_LIMIT_WAITS) + 1}), pause between papers now {self.delay:g} s")
                time.sleep(wait)
            elif is_transient_failure(reason) and not transient_retried:
                transient_retried = True
                logging.info(f"{indent} waiting   | {pid:<12} | {reason}: trying once more in {TRANSIENT_RETRY_WAIT} s")
                time.sleep(TRANSIENT_RETRY_WAIT)
            else:
                return False, reason, False

    def pause(self, indent: str = "") -> None:
        """The pause after an arXiv paper. After 10 answers in a row without a refusal, goes back towards the normal pace."""
        self.answers_in_a_row += 1
        if self.answers_in_a_row >= 10 and self.delay > self.base_delay:
            self.delay = max(self.base_delay, self.delay / 2)
            self.answers_in_a_row = 0
            logging.info(f"{indent} pace      | no refusal for 10 papers: pause between papers back to {self.delay:g} s")
        time.sleep(self.delay)

def upgrade_pdfs_to_latex(store: CorpusStore, counts: dict, limit: int | None, base_delay: float = 3.5) -> None:
    """
    Fetches the arXiv LaTeX source of the papers held as PDF that have an arXiv ID (usually found by the enrichment
    after the PDF was downloaded). Once the source is on disk the PDF is deleted. A paper for which arXiv has no LaTeX source is not asked again.
    When arXiv rate-limits, the same paper is tried again after a growing wait and the pause between papers is raised;
    if arXiv still refuses after the last wait, the run stops, so the rest of the queue is not wasted on refusals.
    """
    candidates = [
        pid for pid, p in store.papers.items()
        if p.get("local_files", {}).get("status") == "downloaded_pdf" and (p.get("urls") or {}).get("eprint_source")
    ]
    already_answered = [pid for pid in candidates if store.papers[pid]["local_files"].get("latex_upgrade")]
    queue = [pid for pid in candidates if pid not in set(already_answered)]
    if limit:
        queue = queue[:limit]

    logging.info(f"=== STEP 2: PDF -> LaTeX UPGRADE | Queued: {len(queue)} ===")
    upgraded, no_source, failed = 0, Counter(), Counter()
    interrupted = False
    stopped_by_rate_limit = False
    pacer = ArxivPacer(base_delay)
    try:
        for n, pid in enumerate(queue, 1):
            paper = store.papers[pid]
            position = f"[{n:>{len(str(len(queue)))}}/{len(queue)}]"
            indent = " " * len(position)
            success, reason, stopped_by_rate_limit = pacer.fetch(pid, paper["urls"]["eprint_source"], indent)
            if stopped_by_rate_limit:
                logging.info(f"{position} stopped   | {pid:<12} | arXiv still refuses after {sum(RATE_LIMIT_WAITS) // 60} minutes of waiting: stopping here, nothing is lost")
                break
            if success:
                paper["local_files"] = {"status": "downloaded_latex", "path": f"data/raw/latex/{pid}"}
                (RAW_PDF_DIR / f"{pid}.pdf").unlink(missing_ok=True)
                # The stored estimate was made on the PDF text: step 4 has to scan the LaTeX source
                paper.pop("formula_estimates", None)
                counts["downloaded_latex"] += 1
                counts["downloaded_pdf"] -= 1
                upgraded += 1
                label, detail = "LaTeX    ", "source downloaded, PDF deleted"
            elif reason in NO_LATEX_SOURCE_REASONS:
                paper["local_files"]["latex_upgrade"] = {"status": "no_latex_source", "reason": reason, "checked_at": time.strftime("%Y-%m-%d")}
                no_source[reason] += 1
                label, detail = "no source", reason
            else:
                failed[reason] += 1
                label, detail = "failed   ", reason
            store.save()
            logging.info(f"{position} {label} | {pid:<12} | arXiv {paper.get('arxiv_id') or '?':<12} | {detail}")
            pacer.pause(indent)
    except KeyboardInterrupt:
        interrupted = True
        store.save()

    tried = upgraded + sum(no_source.values()) + sum(failed.values())
    print("\n" + "=" * 72)
    print("                    PDF -> LaTeX UPGRADE REPORT" + ("  (interrupted)" if interrupted else "  (stopped: arXiv rate limit)" if stopped_by_rate_limit else ""))
    print("=" * 72)
    print(f"{len(candidates):>5} | PDF papers with an arXiv ID")
    print(f"{len(already_answered):>5} | skipped: an earlier run found that arXiv has no LaTeX source for them")
    print(f"{tried:>5} | tried in this run" + (f" (of {len(queue)} queued)" if tried != len(queue) else ""))
    print("-" * 72)
    print(f"{upgraded:>5} | upgraded to LaTeX (their PDF is deleted)")
    print(f"{sum(no_source.values()):>5} | arXiv has no LaTeX source: stays a PDF, not asked again")
    for reason, count in no_source.most_common():
        print(f"      {count:>5} | {reason}")
    print(f"{sum(failed.values()):>5} | failed for now: stays a PDF, tried again on the next run")
    for reason, count in failed.most_common():
        print(f"      {count:>5} | {reason}")
    print("-" * 72)
    print(f"{pacer.rate_limit_answers:>5} | times arXiv asked to slow down (HTTP 429/503); pause between papers at the end: {pacer.delay:g} s")
    if stopped_by_rate_limit:
        print(f"{len(queue) - tried:>5} | not tried: arXiv kept refusing, so the run stopped. Run the same command again later,")
        print("        possibly with a longer pause, e.g. --delay 15")
    print("-" * 72)
    print(f"Corpus now: {counts['downloaded_latex']} LaTeX | {counts['downloaded_pdf']} PDF only")
    if upgraded:
        print("Next: run steps 3 and 4 again, so the licences and formula counts of the upgraded papers")
        print("      are taken from the LaTeX source:")
        print("          python scripts/03_audit_and_print_licenses.py")
        print("          python scripts/04_estimate_formulas.py")
    print("=" * 72)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--retry-unavailable", action="store_true")
    parser.add_argument("--retry-transient", action="store_true", help="Retry only unavailable papers that failed on a connection error, timeout, rate limit or server error.")
    parser.add_argument("--upgrade-pdfs", action="store_true", help="Fetch the arXiv LaTeX source of the papers held as PDF that have an arXiv ID and delete their PDF, print a report and exit. Nothing else is downloaded.")
    parser.add_argument("--delay", type=float, default=3.5, help="Seconds to pause after each arXiv download (default 3.5). The pause grows by itself when arXiv rate-limits.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--stats", action="store_true", help="Print the download status of the whole corpus and exit, without downloading anything.")
    parser.add_argument("--relabel", action="store_true", help="Rewrite stored failure reasons in the current wording, print the stats and exit, without downloading anything.")
    args = parser.parse_args()

    store = CorpusStore()
    counts = sync_corpus_with_disk(store)
    total_corpus = len(store.papers)
    failure_stats = Counter()

    if args.relabel:
        changed = 0
        for paper in store.papers.values():
            if paper.get("local_files", {}).get("status") == "unavailable":
                new_reason = relabel_failure_reason(paper)
                if new_reason != paper["local_files"].get("failure_reason"):
                    paper["local_files"]["failure_reason"] = new_reason
                    changed += 1
        store.save()
        print(f"Relabelled {changed} failure reasons.")

    if args.stats or args.relabel:
        print_corpus_stats(store, counts)
        return

    if args.upgrade_pdfs:
        upgrade_pdfs_to_latex(store, counts, args.limit, args.delay)
        return

    target_statuses = {"pending"}
    if args.retry_unavailable:
        target_statuses.add("unavailable")

    queue = [pid for pid, p in store.papers.items() if p.get("local_files", {}).get("status") in target_statuses]
    if args.retry_transient and not args.retry_unavailable:
        queue += [
            pid for pid, p in store.papers.items()
            if p.get("local_files", {}).get("status") == "unavailable"
            and is_transient_failure(p["local_files"].get("failure_reason"))
        ]
    if args.limit:
        queue = queue[: args.limit]

    logging.info(f"=== STEP 2 START | Queued: {len(queue)} ===")

    attempted = 0
    stopped_by_rate_limit = False
    pacer = ArxivPacer(args.delay)
    for pid in queue:
        attempted += 1
        indent = " " * len(f"[{attempted}/{len(queue)}]")
        paper = store.papers[pid]
        urls = paper.get("urls") or {}
        eprint_url = urls.get("eprint_source")
        pdf_mirrors = list(urls.get("pdf_mirrors") or [])

        tex_folder = RAW_LATEX_DIR / pid
        pdf_path = RAW_PDF_DIR / f"{pid}.pdf"
        downloaded = False
        status_label = ""
        current_failure_reason = None  # stays None when there was no link to try at all

        # TIER 1: arXiv .tex
        if eprint_url:
            success, reason, stopped_by_rate_limit = pacer.fetch(pid, eprint_url, indent)
            if stopped_by_rate_limit:
                # Falling back to the PDF here would hide that the LaTeX source was never really asked for
                attempted -= 1
                logging.info(f"[{attempted + 1}/{len(queue)}] STOPPED [arXiv still refuses after {sum(RATE_LIMIT_WAITS) // 60} minutes of waiting] {pid}: "
                             f"this paper and the rest of the queue are left as they were")
                break
            if success:
                paper["local_files"] = {"status": "downloaded_latex", "path": f"data/raw/latex/{pid}"}
                counts["downloaded_latex"] += 1
                downloaded = True
                status_label = f"SUCCESS [LaTeX] {pid}"
            else:
                current_failure_reason = reason
            pacer.pause(indent)

        # TIER 2: PDF Mirrors
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
            if current_failure_reason is None:
                current_failure_reason = no_link_reason(paper)
            paper["local_files"] = {
                "status": "unavailable",
                "path": None,
                "failure_reason": current_failure_reason
            }
            counts["unavailable"] += 1
            failure_stats[current_failure_reason] += 1
            status_label = f"FAILED  [{current_failure_reason}] {pid}"

        store.save()
        logging.info(f"[{attempted}/{len(queue)}] {status_label}")

    if stopped_by_rate_limit:
        logging.info(f"=== STEP 2 STOPPED: arXiv rate limit | {attempted} of {len(queue)} papers done ===")
        print(f"\narXiv kept refusing, so the run stopped with {len(queue) - attempted} papers not tried. Run the same command again later,")
        print("possibly with a longer pause, e.g. --delay 15")
    else:
        logging.info("=== STEP 2 FINISHED ===")
    if pacer.rate_limit_answers:
        print(f"arXiv asked to slow down {pacer.rate_limit_answers} times (HTTP 429/503); pause between arXiv papers at the end: {pacer.delay:g} s")

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