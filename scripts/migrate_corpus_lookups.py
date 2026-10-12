"""
One-off migration: records in the corpus what is already known about the Semantic Scholar, arXiv title search
and HAL lookups made so far by step 2, so that the enrichment phase of step 1 does not repeat them.

The corpus only kept one flag per paper ("recovery_rate_limited"), so the detail is rebuilt from data/logs/pipeline.log.
Each paper gets a "lookups" field, one entry per service:

    "lookups": {"arxiv_title": {"status": "not_found", "checked_at": "2026-10-08"}, ...}

    found      the service answered and gave an arXiv ID or a PDF link
    not_found  the service answered and had nothing
    no_answer  the service was rate-limited or unreachable: worth asking again
    (absent)   never asked, or it is not known what the service answered

Without --apply nothing is written: the script only prints what it would do.
"""
import argparse
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import LOG_FILE
from src.harvesting.downloader import relabel_failure_reason
from src.storage import CorpusStore

# Before this moment a rate-limited lookup was silently recorded as "not found", so earlier runs prove nothing
RELIABLE_SINCE = datetime(2026, 10, 7, 12, 35)
# A service that kept rate-limiting was skipped for 15 minutes; the margin covers the delay between a lookup and its log line
COOLDOWN = timedelta(seconds=900 + 120)
SERVICES = {"Semantic Scholar": "semantic_scholar", "arXiv title search": "arxiv_title", "HAL": "hal"}
PAPER_ID = re.compile(r"\b(W\d+|arxiv_[\w.\-]+)")
RESULT = re.compile(r"\] (SUCCESS \[LaTeX\]|SUCCESS \[PDF\]|RECOVERED \[LaTeX\]|FAILED)")


def read_log(path: Path) -> dict:
    """
    Returns evidence[paper_id][service] = (answered, date), from the runs made since RELIABLE_SINCE with the lookups enabled.
    A service that answered in one run and was rate-limited in another counts as answered.
    """
    evidence = {}
    run_lines, runs = [], []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "===" in line and ("START" in line or "RESUMING" in line):
            run_lines = []
            runs.append(run_lines)
        run_lines.append(line)

    for lines in runs:
        started = datetime.strptime(lines[0][:19], "%Y-%m-%d %H:%M:%S")
        lookups_enabled = any("Semantic Scholar check" in l or "[!]" in l for l in lines)
        if started < RELIABLE_SINCE or not lookups_enabled:
            continue
        throttled_now, cooldown_until = set(), {}
        for line in lines[1:]:
            try:
                at = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            warning = re.search(r"\[!\] (.+?) (lookup rate-limited|is still rate-limiting)", line)
            if warning:
                throttled_now.add(warning.group(1))
                if warning.group(2).startswith("is still"):
                    cooldown_until[warning.group(1)] = at + COOLDOWN
                continue
            result = RESULT.search(line)
            if not result:
                continue
            ids = PAPER_ID.findall(line.split(" | ", 2)[1])
            # A LaTeX success comes from the link already in the corpus: no lookup was made for that paper
            if ids and result.group(1) != "SUCCESS [LaTeX]":
                for service, key in SERVICES.items():
                    answered = service not in throttled_now and at > cooldown_until.get(service, datetime.min)
                    previous = evidence.setdefault(ids[-1], {}).get(key)
                    if answered or previous is None or not previous[0]:
                        evidence[ids[-1]][key] = (answered, at.strftime("%Y-%m-%d"))
            throttled_now = set()
    return evidence


def lookup_status(paper: dict, key: str, answered: bool) -> str | None:
    """What can be said about one service for one paper, or None when nothing certain is known."""
    mirrors = (paper.get("urls") or {}).get("pdf_mirrors") or []
    has_arxiv = bool(paper.get("arxiv_id"))
    if key == "semantic_scholar":
        if not paper.get("doi"):
            return None  # asked by DOI only
        if not answered:
            return "no_answer"
        # With an arXiv ID or a PDF link on record, the log does not say whether they came from this service
        return None if has_arxiv or mirrors else "not_found"
    if key == "arxiv_title":
        if has_arxiv or len(paper.get("title") or "") < 15:
            return None  # asked only for a long enough title, and settled once the arXiv ID is known
        return "not_found" if answered else "no_answer"
    if not paper.get("title"):
        return None
    if not answered:
        return "no_answer"
    return "found" if any("hal." in m or "archives-ouvertes" in m for m in mirrors) else "not_found"


def main():
    parser = argparse.ArgumentParser(description="One-off migration: record the past recovery lookups in the corpus.")
    parser.add_argument("--apply", action="store_true", help="Write the changes to the corpus. Without it, only a report is printed.")
    args = parser.parse_args()

    store = CorpusStore()
    evidence = read_log(LOG_FILE)

    # Paper IDs in the log may since have been merged into another entry
    def current_id(pid: str) -> str | None:
        return pid if pid in store.papers else store.alias_index.get(pid)

    per_paper = {}
    for logged_id, services in evidence.items():
        pid = current_id(logged_id)
        if pid:
            for key, (answered, date) in services.items():
                previous = per_paper.setdefault(pid, {}).get(key)
                if answered or previous is None or not previous[0]:
                    per_paper[pid][key] = (answered, date)

    statuses, flagged, flagged_explained = Counter(), 0, 0
    for pid, paper in store.papers.items():
        # Answers already recorded (by an earlier run of this script or by the enrichment) are never overwritten
        lookups = dict(paper.get("lookups") or {})
        for key, (answered, date) in sorted(per_paper.get(pid, {}).items()):
            status = lookup_status(paper, key, answered)
            if status and key not in lookups:
                lookups[key] = {"status": status, "checked_at": date}
        for key, entry in lookups.items():
            statuses[(key, entry["status"])] += 1
        local_files = paper.get("local_files", {})
        if local_files.get("recovery_rate_limited"):
            flagged += 1
            flagged_explained += any(v["status"] == "no_answer" for v in lookups.values())
        if args.apply:
            paper["lookups"] = lookups
            # The old flag is replaced by the per-service entries, and the failure reason follows them
            local_files.pop("recovery_rate_limited", None)
            if local_files.get("status") == "unavailable":
                local_files["failure_reason"] = relabel_failure_reason(paper)

    if args.apply:
        store.save()

    print(f"Papers in the corpus:                         {len(store.papers)}")
    print(f"Papers with lookup evidence in the log:       {len(per_paper)}")
    print("-" * 60)
    for key in SERVICES.values():
        for status in ("found", "not_found", "no_answer"):
            print(f"{statuses[(key, status)]:>5} | {key:<17} {status}")
    print("-" * 60)
    print(f"Papers with the old recovery_rate_limited flag: {flagged} ({flagged_explained} of them have a no_answer entry)")
    print("Corpus updated." if args.apply else "Dry run: nothing was written. Use --apply to update the corpus.")


if __name__ == "__main__":
    main()
