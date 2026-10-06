import time
import urllib.parse
import xml.etree.ElementTree as ET
import requests
from config import HEADERS


def search_arxiv_by_keywords(
    keywords: list[str], store, max_per_keyword: int = 600
):
    """Queries export.arxiv.org directly by keyword and adds matching preprints to CorpusStore."""
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    newly_added = 0

    for kw in keywords:
        print(f"  [arXiv Direct Keyword] Searching for '{kw}'...")
        encoded_q = urllib.parse.quote(f'all:"{kw}"')
        start = 0
        batch_size = 200

        while start < max_per_keyword:
            url = (
                f"http://export.arxiv.org/api/query?"
                f"search_query={encoded_q}&start={start}&max_results={batch_size}"
            )
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                break

            root = ET.fromstring(resp.content)
            entries = root.findall("atom:entry", ns)
            if not entries:
                break

            for entry in entries:
                id_url = entry.find("atom:id", ns).text
                arxiv_id = id_url.split("/abs/")[-1].split("v")[0]
                title = (
                    entry.find("atom:title", ns).text.replace("\n", " ").strip()
                )
                published = entry.find("atom:published", ns).text
                year = int(published[:4]) if published else None

                doi_elem = entry.find("arxiv:doi", ns)
                doi = (
                    f"https://doi.org/{doi_elem.text.strip()}"
                    if (doi_elem is not None and doi_elem.text)
                    else None
                )

                pid = f"arxiv_{arxiv_id.replace('/', '_')}"
                paper_dict = {
                    "paper_id": pid,
                    "openalex_id": None,
                    "arxiv_id": arxiv_id,
                    "doi": doi,
                    "title": title,
                    "year": year,
                    "cited_by_count": 0,
                    "is_oa": True,
                    "urls": {
                        "eprint_source": (
                            f"https://export.arxiv.org/e-print/{arxiv_id}"
                        ),
                        "pdf_mirrors": [f"https://arxiv.org/pdf/{arxiv_id}"],
                    },
                    "local_files": {
                        "status": "pending",
                        "path": None,
                    },
                    "license_info": {
                        "effective_license": None,
                        "effective_licenses_all": [],
                        "effective_source": "none",
                        "tier": "unspecified",
                        "has_conflict": False,
                        "sources": {
                            "openalex_locations": [],
                            "tex_source": [],
                            "arxiv_oai": [],
                            "pdf_metadata": [],
                        },
                    },
                }

                _, is_new = store.upsert_paper(
                    paper_dict, method=f"arxiv_kw:{kw}", hop=None
                )
                if is_new:
                    newly_added += 1

            store.save()
            if len(entries) < batch_size:
                break
            start += batch_size
            time.sleep(3.0)  # Polite arXiv API delay

        print(
            f"    -> Finished arXiv search for '{kw}' ({newly_added} cumulative new preprints added)."
        )

    return newly_added