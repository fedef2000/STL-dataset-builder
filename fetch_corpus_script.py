import json
import re
import time
import requests

USER_EMAIL = "federico.ferrari@ait.ac.at"
HEADERS = {"User-Agent": f"NL2STL-Collector/2.0 (mailto:{USER_EMAIL})"}

# Top 4 foundational STL papers (Maler 2004, Donze 2010, Fainekos 2009, Donze Breach 2010)
SEED_DOIS = [
    "https://doi.org/10.1007/978-3-540-30206-3_12",  # Maler & Nickovic 2004 (STL) Monitoring Temporal Properties of Continuous Signals
    "https://doi.org/10.1007/978-3-642-15297-9_9",   # Donze & Maler 2010 (Quantitative STL) Robust Satisfaction of Temporal Logic over Real-Valued Signals
    "https://doi.org/10.1016/j.tcs.2009.06.021",     # Fainekos & Pappas 2009 (Robustness / MTL-STL) Robustness of temporal logic specifications for continuous-time signals
    "https://doi.org/10.1007/978-3-642-14295-6_17",  # Donze 2010 (Breach Toolbox) Breach, A Toolbox for Verification and Parameter Synthesis of Hybrid Systems
]


def resolve_seed_ids(dois):
    work_ids = []
    for doi in dois:
        resp = requests.get(f"https://api.openalex.org/works/{doi}", headers=HEADERS, timeout=30)
        if resp.status_code == 200:
             data = resp.json()
             wid = data["id"].split("/")[-1]
             work_ids.append(wid)
             print(f"Resolved {wid}: {data['display_name']} ({data.get('cited_by_count')} citations)")
    return work_ids


def analyze_locations(work):
    """Scans ALL locations for arXiv IDs, HAL/repo PDFs, and any permissive/NC licenses."""
    arxiv_id = None
    all_pdf_urls = []
    licenses_found = set()

    # Check canonical IDs first
    arxiv_url = (work.get("ids") or {}).get("arxiv") or ""
    if arxiv_url:
        m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}|[a-z\-]+/[0-9]{7})", arxiv_url)
        if m:
            arxiv_id = m.group(1)

    for loc in work.get("locations", []):
        lic = loc.get("license")
        if lic:
            licenses_found.add(lic.lower())

        for url_key in ("landing_page_url", "pdf_url"):
            url = loc.get(url_key) or ""
            if "arxiv.org" in url and not arxiv_id:
                m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}|[a-z\-]+/[0-9]{7})", url)
                if m:
                    arxiv_id = m.group(1)
            if url_key == "pdf_url" and url:
                all_pdf_urls.append(url)

    # Also check open_access.oa_url fallback
    oa_url = (work.get("open_access") or {}).get("oa_url")
    if oa_url and oa_url not in all_pdf_urls:
        all_pdf_urls.append(oa_url)

    return {
        "arxiv_id": arxiv_id,
        "eprint_source_url": f"https://export.arxiv.org/e-print/{arxiv_id}" if arxiv_id else None,
        "pdf_urls": all_pdf_urls,
        "has_hal_or_repo_pdf": len(all_pdf_urls) > 0,
        "licenses": list(licenses_found),
        "has_cc_license": any(l.startswith("cc-") or l == "cc0" for l in licenses_found),
    }


def fetch_citing_corpus(seed_ids):
    base_url = "https://api.openalex.org/works"
    # Combine all seed IDs with OR ('|') — OpenAlex automatically deduplicates works!
    cites_filter = "|".join(seed_ids)
    cursor = "*"
    corpus = []

    while cursor:
        params = {
            "filter": f"cites:{cites_filter}",
            "per-page": 200,
            "cursor": cursor,
            "mailto": USER_EMAIL,
        }
        resp = requests.get(base_url, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            break

        for work in results:
            loc_info = analyze_locations(work)
            corpus.append({
                "openalex_id": work.get("id"),
                "title": work.get("display_name"),
                "year": work.get("publication_year"),
                "doi": work.get("doi"),
                "is_oa": (work.get("open_access") or {}).get("is_oa", False),
                **loc_info
            })

        cursor = data.get("meta", {}).get("next_cursor")
        print(f"Collected {len(corpus)} unique STL-related papers...")
        time.sleep(0.15)

    return corpus


if __name__ == "__main__":
    seed_ids = resolve_seed_ids(SEED_DOIS)
    corpus = fetch_citing_corpus(seed_ids)

    print("\n--- Expanded STL Corpus Summary ---")
    print(f"Total unique citing papers: {len(corpus)}")
    print(f"Papers with arXiv .tex source: {sum(1 for p in corpus if p['arxiv_id'])}")
    print(f"Papers with ANY Open Access PDF (arXiv, HAL, Inria, Univ Repos): {sum(1 for p in corpus if p['has_hal_or_repo_pdf'])}")
    print(f"Papers with any Creative Commons license (including CC-BY-NC): {sum(1 for p in corpus if p['has_cc_license'])}")

    with open("stl_expanded_corpus.json", "w", encoding="utf-8") as f:
        json.dump(corpus, f, indent=2)