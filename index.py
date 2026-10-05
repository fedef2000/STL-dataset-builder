import csv
import json
import re
import time
import requests

# Replace with your email to join OpenAlex's "Polite Pool" (10 requests/sec)
USER_EMAIL = "your-email@domain.com"
FOUNDATIONAL_DOI = "https://doi.org/10.1007/978-3-540-30206-3_12" 
FOUNDATIONAL_TITLE = "Monitoring Temporal Properties of Continuous Signals"
SEED_WORK_ID = "W1547304883"

HEADERS = {
    "User-Agent": f"NL2STL-CitationCollector/1.0 (mailto:{USER_EMAIL})"
}


"""
def get_seed_work_id():
    \"""Finds the OpenAlex Work ID for Maler & Nickovic (2004).\"""
    # 1. Try lookup by exact DOI first
    url = f"https://api.openalex.org/works/{FOUNDATIONAL_DOI}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        work_id = data["id"].split("/")[-1]
        print(f"Found seed paper via DOI: {data['display_name']} ({work_id})")
        print(f"Reported citation count: {data.get('cited_by_count', 0)}")
        return work_id

    # 2. Fallback to title search if DOI format varies
    search_url = "https://api.openalex.org/works"
    params = {"filter": f"title.search:{FOUNDATIONAL_TITLE}", "per-page": 5}
    resp = requests.get(search_url, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        raise ValueError("Could not locate the seed paper in OpenAlex.")

    work_id = results[0]["id"].split("/")[-1]
    print(f"Found seed paper via search: {results[0]['display_name']} ({work_id})")
    return work_id
"""

def extract_arxiv_id(work):
    """Extracts a clean arXiv ID (e.g., '2305.12345') if the paper has an arXiv preprint."""
    # 1. Check OpenAlex's canonical ids dictionary first
    arxiv_url = (work.get("ids") or {}).get("arxiv") or ""
    urls_to_check = [arxiv_url] if arxiv_url else []

    # 2. Also check all indexed repository locations
    for loc in work.get("locations", []):
        if loc.get("landing_page_url"):
            urls_to_check.append(loc["landing_page_url"])
        if loc.get("pdf_url"):
            urls_to_check.append(loc["pdf_url"])

    for url in urls_to_check:
        if "arxiv.org" in url:
            match = re.search(
                r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}|[a-z\-]+/[0-9]{7})",
                url,
            )
            if match:
                return match.group(1)
    return None


def reconstruct_abstract(inverted_index):
    """Reconstructs plain-text abstract from OpenAlex's inverted index format."""
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)


def fetch_all_citing_papers(seed_work_id):
    """Retrieves all works citing the seed paper using cursor pagination."""
    base_url = "https://api.openalex.org/works"
    cursor = "*"
    citing_papers = []
    page = 1

    while cursor:
        params = {
            "filter": f"cites:{seed_work_id}",
            "per-page": 200,  # Maximum allowed by OpenAlex per page
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
            best_oa = work.get("best_oa_location") or {}
            primary_loc = work.get("primary_location") or {}
            source = primary_loc.get("source") or {}

            arxiv_id = extract_arxiv_id(work)
            license_str = (
                best_oa.get("license")
                or primary_loc.get("license")
                or "unknown"
            )

            paper_record = {
                "openalex_id": work.get("id"),
                "title": work.get("display_name"),
                "publication_year": work.get("publication_year"),
                "doi": work.get("doi"),
                "arxiv_id": arxiv_id,
                "eprint_source_url": (
                    f"https://export.arxiv.org/e-print/{arxiv_id}"
                    if arxiv_id
                    else None
                ),
                "venue": source.get("display_name"),
                "is_oa": work.get("open_access", {}).get("is_oa", False),
                "license": license_str,
                "is_permissive_license": license_str in ("cc-by", "cc0", "cc-by-sa"),
                "pdf_url": best_oa.get("pdf_url")
                or work.get("open_access", {}).get("oa_url"),
                "cited_by_count": work.get("cited_by_count", 0),
                "abstract": reconstruct_abstract(
                    work.get("abstract_inverted_index")
                ),
            }
            citing_papers.append(paper_record)

        cursor = data.get("meta", {}).get("next_cursor")
        print(f"Page {page}: Collected {len(citing_papers)} citing papers so far...")
        page += 1
        time.sleep(0.15)  # Polite rate-limiting

    return citing_papers


if __name__ == "__main__":
    seed_id = SEED_WORK_ID #get_seed_work_id()
    papers = fetch_all_citing_papers(seed_id)

    # Summary statistics for your NL-to-STL dataset pipeline
    arxiv_count = sum(1 for p in papers if p["arxiv_id"])
    permissive_count = sum(1 for p in papers if p["is_permissive_license"])
    arxiv_and_permissive = sum(
        1 for p in papers if p["arxiv_id"] and p["is_permissive_license"]
    )

    print("\n--- Collection Complete ---")
    print(f"Total citing papers retrieved: {len(papers)}")
    print(f"Papers with arXiv LaTeX sources available: {arxiv_count}")
    print(f"Papers with CC-BY / CC0 licenses: {permissive_count}")
    print(f"Papers with BOTH arXiv source + permissive license: {arxiv_and_permissive}")

    # Save full records (including reconstructed abstracts) to JSON
    with open("stl_citing_papers.json", "w", encoding="utf-8") as jf:
        json.dump(papers, jf, indent=2, ensure_ascii=False)

    # Save tabular summary to CSV
    if papers:
        csv_fields = [k for k in papers[0].keys() if k != "abstract"]
        with open("stl_citing_papers.csv", "w", newline="", encoding="utf-8") as cf:
            writer = csv.DictWriter(cf, fieldnames=csv_fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(papers)

    print("Saved output to 'stl_citing_papers.json' and 'stl_citing_papers.csv'.")