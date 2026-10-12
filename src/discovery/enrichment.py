from collections import Counter
from datetime import date
import difflib
import logging
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
import requests
from config import HEADERS, SEMANTIC_SCHOLAR_API_KEY

# -------------------------------------------------------------------------
# ENRICHMENT: asks Semantic Scholar, the arXiv title search and HAL for the
# arXiv ID or the open PDF link that OpenAlex did not give for a paper.
# Each answer is recorded per paper under "lookups", so nothing is asked twice.
# -------------------------------------------------------------------------
FOUND, NOT_FOUND, NO_ANSWER = "found", "not_found", "no_answer"
SERVICES = ("semantic_scholar", "arxiv_title", "hal")

RETRY_WAITS = (2, 5, 10)
MAX_CONSECUTIVE_GIVE_UPS = 5
SERVICE_COOLDOWN_SEC = 900
# Semantic Scholar allows about 1 request/second per API key, arXiv asks for one request every 3 seconds
MIN_INTERVAL_SEC = {"semantic_scholar": 1.1, "arxiv_title": 3.1, "hal": 1.0}
S2_BATCH_SIZE = 500  # the most the batch endpoint accepts
ARXIV_TITLES_PER_REQUEST = 15  # keeps the request URL under 2,000 characters
ARXIV_RESULTS_PER_TITLE = 5
SAVE_EVERY = 20

S2_HEADERS = dict(HEADERS)
if SEMANTIC_SCHOLAR_API_KEY:
    S2_HEADERS["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY

_consecutive_give_ups = Counter()
_cooldown_until = {}
_last_request_at = {}


def request_with_backoff(service: str, url: str, timeout: int, headers: dict = HEADERS, json_body: dict = None) -> requests.Response | None:
    """
    GET (or POST when json_body is given) that retries on 429/503. Returns None when the service gave no answer,
    so that a throttled lookup is not mistaken for "not found".
    If a service throttles several requests in a row (e.g. an IP block), it is left alone for
    SERVICE_COOLDOWN_SEC and then probed again, instead of being hit once per paper.
    """
    if time.monotonic() < _cooldown_until.get(service, 0):
        return None

    for wait in (*RETRY_WAITS, None):
        gap = MIN_INTERVAL_SEC.get(service, 0) - (time.monotonic() - _last_request_at.get(service, float("-inf")))
        if gap > 0:
            time.sleep(gap)
        _last_request_at[service] = time.monotonic()
        try:
            if json_body is None:
                resp = requests.get(url, headers=headers, timeout=timeout)
            else:
                resp = requests.post(url, headers=headers, json=json_body, timeout=timeout)
        except requests.exceptions.RequestException:
            return None
        if resp.status_code not in (429, 503):
            _consecutive_give_ups[service] = 0
            return resp
        if wait is not None:
            retry_after = resp.headers.get("Retry-After", "")
            time.sleep(min(int(retry_after), 30) if retry_after.isdigit() else wait)

    _consecutive_give_ups[service] += 1
    if _consecutive_give_ups[service] >= MAX_CONSECUTIVE_GIVE_UPS:
        _cooldown_until[service] = time.monotonic() + SERVICE_COOLDOWN_SEC
        logging.warning(
            f"    [!] {service} is still rate-limiting (HTTP {resp.status_code}): "
            f"skipping its lookups for {SERVICE_COOLDOWN_SEC // 60} min, then trying again."
        )
    return None


def _similar_title(t1: str, t2: str, threshold: float = 0.88) -> bool:
    clean1 = "".join(c.lower() for c in (t1 or "") if c.isalnum() or c == " ")
    clean2 = "".join(c.lower() for c in (t2 or "") if c.isalnum() or c == " ")
    return difflib.SequenceMatcher(None, clean1, clean2).ratio() >= threshold


def lookup_semantic_scholar(dois: list[str]) -> list[tuple[str, str | None, str | None]]:
    """Asks Semantic Scholar about up to S2_BATCH_SIZE DOIs in one request. Returns (status, arXiv ID, PDF URL) per DOI."""
    ids = ["DOI:" + doi.replace("https://doi.org/", "") for doi in dois]
    url = "https://api.semanticscholar.org/graph/v1/paper/batch?fields=externalIds,openAccessPdf"
    resp = request_with_backoff("semantic_scholar", url, timeout=60, headers=S2_HEADERS, json_body={"ids": ids})
    try:
        records = resp.json() if resp is not None and resp.status_code == 200 else None
    except ValueError:
        records = None
    if not isinstance(records, list) or len(records) != len(ids):
        return [(NO_ANSWER, None, None)] * len(ids)

    results = []
    for record in records:
        arxiv_id = ((record or {}).get("externalIds") or {}).get("ArXiv")
        pdf_url = ((record or {}).get("openAccessPdf") or {}).get("url") or None
        # For papers that are free on the publisher's site it gives the DOI link, which is a web page and not a PDF
        if pdf_url and "doi.org/" in pdf_url:
            pdf_url = None
        results.append((FOUND if arxiv_id or pdf_url else NOT_FOUND, arxiv_id, pdf_url))
    return results


def check_semantic_scholar() -> str:
    """A test lookup, so a blocked IP or a rejected API key is visible before a long run."""
    mode = "with API key" if SEMANTIC_SCHOLAR_API_KEY else "anonymous, SEMANTIC_SCHOLAR_API_KEY not set"
    url = "https://api.semanticscholar.org/graph/v1/paper/DOI:10.1007/978-3-540-30206-3_12?fields=externalIds"
    # Semantic Scholar answers the odd request with 429 even when all is well, so only report it if it persists
    for wait in (*RETRY_WAITS, None):
        try:
            resp = requests.get(url, headers=S2_HEADERS, timeout=15)
        except requests.exceptions.RequestException:
            return f"unreachable ({mode})"
        _last_request_at["semantic_scholar"] = time.monotonic()
        if resp.status_code != 429 or wait is None:
            break
        time.sleep(wait)

    if resp.status_code == 200:
        return f"OK ({mode})"
    if resp.status_code in (401, 403) and SEMANTIC_SCHOLAR_API_KEY:
        return f"API key rejected (HTTP {resp.status_code})"
    if resp.status_code == 429:
        return f"still rate-limited after {len(RETRY_WAITS)} retries (HTTP 429, {mode})"
    return f"HTTP {resp.status_code} ({mode})"


def lookup_arxiv_by_titles(titles: list[str]) -> list[tuple[str, str | None]]:
    """
    Searches the arXiv API by exact title to catch preprints unlinked in OpenAlex, several titles in one request.
    Returns (status, arXiv ID) per title.
    """
    phrases = [" ".join("".join(c if c.isalnum() or c == " " else " " for c in title).split()) for title in titles]
    query = urllib.parse.quote(" OR ".join(f'ti:"{phrase}"' for phrase in phrases))
    max_results = ARXIV_RESULTS_PER_TITLE * len(titles)
    url = f"https://export.arxiv.org/api/query?search_query={query}&max_results={max_results}"
    resp = request_with_backoff("arxiv_title", url, timeout=60)
    if resp is None or resp.status_code != 200:
        return [(NO_ANSWER, None)] * len(titles)
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        return [(NO_ANSWER, None)] * len(titles)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    candidates = [
        (entry.findtext("atom:title", "", ns).replace("\n", " "), entry.findtext("atom:id", "", ns))
        for entry in root.findall("atom:entry", ns)
    ]

    results = []
    for title in titles:
        match = next((id_url for cand_title, id_url in candidates if "/abs/" in id_url and _similar_title(title, cand_title)), None)
        if match:
            results.append((FOUND, re.sub(r"v\d+$", "", match.split("/abs/")[-1])))
        elif len(candidates) >= max_results and len(titles) > 1:
            # The answer was cut off, so this title's match may be missing from it: ask about it alone
            results.append(lookup_arxiv_by_titles([title])[0])
        else:
            results.append((NOT_FOUND, None))
    return results


def lookup_hal(title: str) -> tuple[str, str | None]:
    """Queries France's HAL archive by title for an open PDF. Returns (status, PDF URL)."""
    q = urllib.parse.quote(f'title_t:("{title}")')
    url = f"https://api.archives-ouvertes.fr/search/?q={q}&fl=title_s,fileMain_s&wt=json&rows=3"
    resp = request_with_backoff("hal", url, timeout=15)
    if resp is None or resp.status_code != 200:
        return NO_ANSWER, None
    try:
        docs = resp.json().get("response", {}).get("docs", [])
    except ValueError:
        return NO_ANSWER, None
    for d in docs:
        if d.get("fileMain_s") and any(_similar_title(title, ht) for ht in d.get("title_s") or []):
            return FOUND, d["fileMain_s"]
    return NOT_FOUND, None


def needs_lookup(paper: dict, service: str) -> bool:
    """True when the service could still tell something new about the paper: it was never asked, or it gave no answer."""
    entry = (paper.get("lookups") or {}).get(service)
    if entry and entry.get("status") != NO_ANSWER:
        return False
    if service == "semantic_scholar":
        return bool(paper.get("doi"))  # asked by DOI
    if paper.get("arxiv_id"):
        return False  # the title lookups only serve papers with no arXiv version on record
    if service == "arxiv_title":
        return len(paper.get("title") or "") >= 15
    # HAL only gives a PDF link, which a paper that is already downloaded does not need
    downloaded = paper.get("local_files", {}).get("status") in ("downloaded_latex", "downloaded_pdf")
    return bool(paper.get("title")) and not downloaded


def record_lookup(store, pid: str, service: str, status: str, arxiv_id: str = None, pdf_url: str = None) -> str:
    """
    Stores the answer of one service for one paper, with any arXiv ID or PDF link it gave.
    Returns the paper's ID, which changes when the arXiv ID shows that it duplicates another entry.
    """
    paper = store.papers[pid]
    paper.setdefault("lookups", {})[service] = {"status": status, "checked_at": date.today().isoformat()}
    gained_link = False
    mirrors = paper["urls"].setdefault("pdf_mirrors", [])
    if pdf_url and pdf_url not in mirrors:
        mirrors.append(pdf_url)
        gained_link = True
    if arxiv_id and not paper.get("arxiv_id"):
        pid = store.set_arxiv_id(pid, arxiv_id)
        paper = store.papers[pid]
        gained_link = True
    # A new link gives step 2 something to try, so a paper it had given up on goes back to its queue
    if gained_link and paper.get("local_files", {}).get("status") == "unavailable":
        paper["local_files"] = {"status": "pending", "path": None}
    return pid


def enrich_corpus(store, limit: int = None) -> None:
    """Runs the lookups that are still needed, Semantic Scholar first because it answers hundreds of papers per request."""
    before = len(store.papers)
    gained = Counter()
    try:
        queue = [pid for pid, p in store.papers.items() if needs_lookup(p, "semantic_scholar")][:limit]
        print(f"  [Semantic Scholar] {len(queue)} papers to ask, {S2_BATCH_SIZE} per request. Service check: {check_semantic_scholar()}")
        for start in range(0, len(queue), S2_BATCH_SIZE):
            # A paper of this batch may have been merged into another entry by an earlier answer
            batch = [pid for pid in queue[start : start + S2_BATCH_SIZE] if pid in store.papers]
            results = lookup_semantic_scholar([store.papers[pid]["doi"] for pid in batch])
            for pid, (status, arxiv_id, pdf_url) in zip(batch, results):
                if pid not in store.papers:
                    continue
                gained["arXiv IDs from Semantic Scholar"] += bool(arxiv_id and not store.papers[pid].get("arxiv_id"))
                record_lookup(store, pid, "semantic_scholar", status, arxiv_id, pdf_url)
            store.save()
            print(f"    [{min(start + S2_BATCH_SIZE, len(queue))}/{len(queue)}] {Counter(r[0] for r in results).most_common()}")

        queue = [pid for pid, p in store.papers.items() if needs_lookup(p, "arxiv_title")][:limit]
        print(f"  [arXiv title search] {len(queue)} papers to ask, {ARXIV_TITLES_PER_REQUEST} per request.")
        for start in range(0, len(queue), ARXIV_TITLES_PER_REQUEST):
            batch = [pid for pid in queue[start : start + ARXIV_TITLES_PER_REQUEST] if pid in store.papers]
            results = lookup_arxiv_by_titles([store.papers[pid]["title"] for pid in batch])
            for pid, (status, arxiv_id) in zip(batch, results):
                if pid not in store.papers:
                    continue
                gained["arXiv IDs from the arXiv title search"] += bool(arxiv_id)
                record_lookup(store, pid, "arxiv_title", status, arxiv_id=arxiv_id)
            store.save()
            print(f"    [{min(start + ARXIV_TITLES_PER_REQUEST, len(queue))}/{len(queue)}] {Counter(r[0] for r in results).most_common()}")

        queue = [pid for pid, p in store.papers.items() if needs_lookup(p, "hal")][:limit]
        print(f"  [HAL] {len(queue)} papers to ask, one request each.")
        for done, pid in enumerate(queue, 1):
            status, pdf_url = lookup_hal(store.papers[pid]["title"])
            gained["PDF links from HAL"] += bool(pdf_url)
            record_lookup(store, pid, "hal", status, pdf_url=pdf_url)
            print(f"    [{done}/{len(queue)}] {pid} | {status}")
            if done % SAVE_EVERY == 0:
                store.save()
    finally:
        # Also on Ctrl+C: every answer received so far is kept
        store.save()

    for what, count in gained.items():
        print(f"  {count:>5} | {what}")
    print(f"  {before - len(store.papers):>5} | entries merged because they turned out to be the same arXiv paper")
    print(f"  {sum(1 for p in store.papers.values() if p.get('local_files', {}).get('status') == 'pending'):>5} | papers now waiting for step 2")
