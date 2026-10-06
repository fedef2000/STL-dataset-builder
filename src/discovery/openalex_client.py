import re
import time
import requests
from config import HEADERS, OPENALEX_API_KEY, USER_EMAIL
from src.storage import classify_tier

STL_RELEVANCE_TERMS = {
    "stl",
    "mtl",
    "mitl",
    "temporal logic",
    "signal",
    "falsification",
    "cyber-physical",
    "specification",
    "monitoring",
    "robustness",
    "verification",
    "control barrier",
    "autonomous",
    "shield",
}


def is_stl_relevant_locally(work: dict) -> bool:
    """Checks title and abstract locally in Python (0 API credits!) for STL relevance."""
    title = (work.get("display_name") or "").lower()
    if any(term in title for term in STL_RELEVANCE_TERMS):
        return True
    inv_abs = work.get("abstract_inverted_index") or {}
    abs_words = " ".join(w.lower() for w in inv_abs.keys())
    return any(term in abs_words for term in STL_RELEVANCE_TERMS)


def request_with_retry(url: str, params: dict = None, max_retries: int = 5):
    """Handles short burst 429s automatically, and exits cleanly if daily quota is exhausted."""
    if params is None:
        params = {}
    if OPENALEX_API_KEY:
        params["api_key"] = OPENALEX_API_KEY

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=40)
            if resp.status_code == 200:
                return resp

            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                wait_sec = (
                    int(retry_after)
                    if (retry_after and retry_after.isdigit())
                    else (4 * attempt)
                )
                if wait_sec > 300:
                    raise SystemExit(
                        f"\n[QUOTA EXHAUSTED] OpenAlex daily credit limit reached "
                        f"(resets in {wait_sec // 3600}h {(wait_sec % 3600) // 60}m).\n"
                        f"All progress so far is saved in data/corpus.json!\n"
                        f"-> Fix: Add a free OPENALEX_API_KEY in config.py (from https://openalex.org) for 10x daily credits."
                    )
                print(
                    f"    [!] Burst rate limit (429). Waiting {wait_sec}s ({attempt}/{max_retries})..."
                )
                time.sleep(wait_sec)
                continue

            if resp.status_code in (500, 502, 503, 504):
                time.sleep(4 * attempt)
                continue

            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            if attempt == max_retries:
                raise
            print(
                f"    [!] Network error ({e}). Retrying in {4 * attempt}s ({attempt}/{max_retries})..."
            )
            time.sleep(4 * attempt)

    raise RuntimeError(f"Failed to fetch {url} after {max_retries} retries.")


def parse_openalex_work(work: dict) -> dict:
    """Converts a raw OpenAlex API work JSON into our standardized corpus schema."""
    pid = work["id"].split("/")[-1]
    arxiv_id = None
    pdf_urls = []
    oa_licenses = set()

    arxiv_url = (work.get("ids") or {}).get("arxiv") or ""
    if arxiv_url:
        m = re.search(
            r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}|[a-z\-]+/[0-9]{7})",
            arxiv_url,
        )
        if m:
            arxiv_id = m.group(1)

    for loc in work.get("locations", []):
        lic = loc.get("license")
        if lic:
            oa_licenses.add(lic.lower())

        for key in ("landing_page_url", "pdf_url"):
            url = loc.get(key) or ""
            if "arxiv.org" in url and not arxiv_id:
                m = re.search(
                    r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}|[a-z\-]+/[0-9]{7})",
                    url,
                )
                if m:
                    arxiv_id = m.group(1)
            if key == "pdf_url" and url and url not in pdf_urls:
                pdf_urls.append(url)

    oa_url = (work.get("open_access") or {}).get("oa_url")
    if oa_url and oa_url not in pdf_urls:
        pdf_urls.append(oa_url)

    oa_lic_list = sorted(list(oa_licenses))
    eff_lic = oa_lic_list[0] if oa_lic_list else None

    return {
        "paper_id": pid,
        "openalex_id": work.get("id"),
        "arxiv_id": arxiv_id,
        "doi": work.get("doi"),
        "title": work.get("display_name"),
        "year": work.get("publication_year"),
        "cited_by_count": work.get("cited_by_count", 0),
        "is_oa": (work.get("open_access") or {}).get("is_oa", False),
        "urls": {
            "eprint_source": (
                f"https://export.arxiv.org/e-print/{arxiv_id}"
                if arxiv_id
                else None
            ),
            "pdf_mirrors": pdf_urls,
        },
        "local_files": {
            "status": "pending",
            "path": None,
        },
        "license_info": {
            "effective_license": eff_lic,
            "effective_licenses_all": oa_lic_list,
            "effective_source": "openalex_locations" if eff_lic else "none",
            "tier": classify_tier(oa_lic_list),
            "has_conflict": False,
            "sources": {
                "openalex_locations": oa_lic_list,
                "tex_source": [],
                "arxiv_oai": [],
                "pdf_metadata": [],
            },
        },
    }


def resolve_dois_to_work_ids(dois: list[str]) -> list[str]:
    """Resolves seed DOIs into OpenAlex W... identifiers."""
    work_ids = []
    for doi in dois:
        url = f"https://api.openalex.org/works/{doi}"
        resp = request_with_retry(url, params={"mailto": USER_EMAIL})
        data = resp.json()
        wid = data["id"].split("/")[-1]
        work_ids.append(wid)
        print(
            f"  [Seed] {wid}: {data.get('display_name')} ({data.get('cited_by_count')} citations)"
        )
        time.sleep(0.2)
    return work_ids


def fetch_citing_works(
    parent_work_ids: list[str],
    store,
    hop: int,
    require_stl_relevance: bool = False,
    batch_size: int = 50,
):
    """
    Uses cheap 1-credit 'filter=cites:...' queries (no expensive 10-credit default.search!)
    and filters Hop-2 papers locally in Python.
    """
    base_url = "https://api.openalex.org/works"
    method_label = f"citation_hop_{hop}"
    newly_added = 0
    total_seen = 0

    if hop >= 2:
        remaining_parents = [
            pid
            for pid in parent_work_ids
            if not store.papers.get(pid, {})
            .get("discovery", {})
            .get(f"expanded_hop_{hop}", False)
        ]
        skipped = len(parent_work_ids) - len(remaining_parents)
        if skipped > 0:
            print(
                f"  [Resume] Skipping {skipped} Hop-{hop-1} parents already crawled in previous run."
            )
        parent_work_ids = remaining_parents

    if not parent_work_ids:
        return 0

    total_batches = (len(parent_work_ids) - 1) // batch_size + 1

    for b_idx in range(0, len(parent_work_ids), batch_size):
        batch = parent_work_ids[b_idx : b_idx + batch_size]
        cites_clause = f"cites:{'|'.join(batch)}"

        cursor = "*"
        while cursor:
            params = {
                "filter": cites_clause,
                "per-page": 200,
                "cursor": cursor,
                "mailto": USER_EMAIL,
            }
            resp = request_with_retry(base_url, params=params)
            data = resp.json()
            results = data.get("results", [])
            if not results:
                break

            for work in results:
                total_seen += 1
                if require_stl_relevance and not is_stl_relevant_locally(work):
                    continue

                parsed = parse_openalex_work(work)
                _, is_new = store.upsert_paper(
                    parsed, method=method_label, hop=hop, parent_ids=batch
                )
                if is_new:
                    newly_added += 1

            cursor = data.get("meta", {}).get("next_cursor")
            time.sleep(0.25)

        if hop >= 2:
            for pid in batch:
                if pid in store.papers:
                    store.papers[pid].setdefault("discovery", {})[
                        f"expanded_hop_{hop}"
                    ] = True

        store.save()
        print(
            f"  [Hop {hop} | Batch {b_idx // batch_size + 1}/{total_batches}] "
            f"Scanned {total_seen} citing works (+{newly_added} relevant new added to corpus)..."
        )

    return newly_added


def search_openalex_by_keywords(
    keywords: list[str], store, max_per_keyword: int = 1000
):
    """Searches OpenAlex titles/abstracts for STL keywords and upserts into CorpusStore."""
    base_url = "https://api.openalex.org/works"
    newly_added = 0

    for kw in keywords:
        print(f"  [OpenAlex Keyword] Searching for '{kw}'...")
        cursor = "*"
        fetched_for_kw = 0

        while cursor and fetched_for_kw < max_per_keyword:
            params = {
                "filter": f'default.search:"{kw}"',
                "per-page": 200,
                "cursor": cursor,
                "mailto": USER_EMAIL,
            }
            resp = request_with_retry(base_url, params=params)
            data = resp.json()
            results = data.get("results", [])
            if not results:
                break

            for work in results:
                parsed = parse_openalex_work(work)
                _, is_new = store.upsert_paper(
                    parsed, method=f"openalex_kw:{kw}", hop=None
                )
                fetched_for_kw += 1
                if is_new:
                    newly_added += 1

            cursor = data.get("meta", {}).get("next_cursor")
            time.sleep(0.3)

        store.save()
        print(
            f"    -> Finished '{kw}': scanned {fetched_for_kw} works (+{newly_added} cumulative new)."
        )

    return newly_added