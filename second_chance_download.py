import difflib
import json
import os
import time
import urllib.parse
import xml.etree.ElementTree as ET
import requests

# Reuse your existing extraction function from download_stl_papers.py
from download_script import (
    INPUT_JSON, LATEX_DIR, PDF_DIR, STATE_FILE,
    download_and_extract_arxiv_tex, save_state
)

# Standard browser headers to bypass 403 blocks on university repositories
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

API_HEADERS = {
    "User-Agent": "NL2STL-Recovery/1.0 (mailto:your-email@domain.com)"
}


def similar_title(t1, t2, threshold=0.88):
    """Checks if two paper titles match closely (ignoring case/punctuation)."""
    clean1 = "".join(c.lower() for c in (t1 or "") if c.isalnum() or c == " ")
    clean2 = "".join(c.lower() for c in (t2 or "") if c.isalnum() or c == " ")
    return difflib.SequenceMatcher(None, clean1, clean2).ratio() >= threshold


def find_arxiv_by_title(title):
    """Searches arXiv API directly by paper title to catch unlinked preprints."""
    if not title or len(title) < 15:
        return None
    clean_q = "".join(c if c.isalnum() or c == " " else " " for c in title)
    query = urllib.parse.quote(f'ti:"{clean_q}"')
    url = f"http://export.arxiv.org/api/query?search_query={query}&max_results=3"
    try:
        resp = requests.get(url, headers=API_HEADERS, timeout=20)
        if resp.status_code != 200:
            return None
        root = ET.fromstring(resp.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns):
            cand_title = entry.find("atom:title", ns).text.replace("\n", " ")
            if similar_title(title, cand_title):
                id_url = entry.find("atom:id", ns).text
                # Strip version suffix like v1/v2
                arxiv_id = id_url.split("/abs/")[-1].split("v")[0]
                return arxiv_id
    except Exception:
        pass
    return None


def find_via_semantic_scholar(doi, title):
    """Queries Semantic Scholar by DOI (or title) for hidden ArXiv IDs or author-homepage PDFs."""
    try:
        if doi:
            clean_doi = doi.replace("https://doi.org/", "")
            url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{clean_doi}?fields=externalIds,openAccessPdf"
            resp = requests.get(url, headers=API_HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                arxiv_id = (data.get("externalIds") or {}).get("ArXiv")
                oa_pdf = (data.get("openAccessPdf") or {}).get("url")
                return arxiv_id, oa_pdf
    except Exception:
        pass
    return None, None


def find_via_hal(title):
    """Queries France's HAL archive by title for open PDFs."""
    if not title:
        return None
    q = urllib.parse.quote(f'title_t:("{title}")')
    url = f"https://api.archives-ouvertes.fr/search/?q={q}&fl=title_s,fileMain_s&wt=json&rows=3"
    try:
        resp = requests.get(url, headers=API_HEADERS, timeout=15)
        if resp.status_code == 200:
            docs = resp.json().get("response", {}).get("docs", [])
            for d in docs:
                hal_titles = d.get("title_s") or []
                if any(similar_title(title, ht) for ht in hal_titles):
                    if d.get("fileMain_s"):
                        return d["fileMain_s"]
    except Exception:
        pass
    return None


def download_pdf_with_browser_headers(urls, dest_path):
    """Downloads PDF using standard Chrome headers to avoid 403 blocks on university repos."""
    for url in urls:
        if not url:
            continue
        try:
            resp = requests.get(url, headers=BROWSER_HEADERS, timeout=30, allow_redirects=True)
            if resp.status_code == 200 and resp.content.startswith(b"%PDF"):
                with open(dest_path, "wb") as f:
                    f.write(resp.content)
                return True
        except Exception:
            continue
    return False


if __name__ == "__main__":
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        corpus = json.load(f)
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        raw_state = json.load(f)

    state = {
        "latex": set(raw_state["latex"]),
        "pdf": set(raw_state["pdf"]),
        "failed": set(raw_state["failed"]),
    }

    failed_papers = [p for p in corpus if p["openalex_id"].split("/")[-1] in state["failed"]]
    print(f"Attempting deep recovery on {len(failed_papers)} previously unavailable papers...")

    recovered_tex = 0
    recovered_pdf = 0

    for idx, paper in enumerate(failed_papers, 1):
        work_id = paper["openalex_id"].split("/")[-1]
        title = paper.get("title") or ""
        doi = paper.get("doi")
        tex_folder = os.path.join(LATEX_DIR, work_id)
        pdf_path = os.path.join(PDF_DIR, f"{work_id}.pdf")

        # 1. Query Semantic Scholar for unlinked arXiv ID or author-homepage PDF
        s2_arxiv, s2_pdf = find_via_semantic_scholar(doi, title)

        # 2. If still no arXiv ID, search arXiv directly by title
        arxiv_id = s2_arxiv or find_arxiv_by_title(title)

        if arxiv_id:
            eprint_url = f"https://export.arxiv.org/e-print/{arxiv_id}"
            print(f"[{idx}/{len(failed_papers)}] Found unlinked arXiv ID {arxiv_id} for {work_id}!")
            if download_and_extract_arxiv_tex(eprint_url, tex_folder):
                state["failed"].discard(work_id)
                state["latex"].add(work_id)
                recovered_tex += 1
                save_state(state)
                time.sleep(3.5)
                continue
            time.sleep(3.5)

        # 3. Collect candidate PDFs: existing failed URLs + Semantic Scholar PDF + HAL PDF
        candidate_pdfs = list(paper.get("pdf_urls") or [])
        if s2_pdf:
            candidate_pdfs.append(s2_pdf)
        hal_pdf = find_via_hal(title)
        if hal_pdf:
            candidate_pdfs.append(hal_pdf)

        if candidate_pdfs:
            if download_pdf_with_browser_headers(candidate_pdfs, pdf_path):
                print(f"[{idx}/{len(failed_papers)}] Recovered PDF for {work_id}!")
                state["failed"].discard(work_id)
                state["pdf"].add(work_id)
                recovered_pdf += 1
                save_state(state)

        time.sleep(1.2)  # Respect S2 and arXiv rate limits

    print(f"\nRecovery complete! Recovered {recovered_tex} additional LaTeX bundles and {recovered_pdf} PDFs.")