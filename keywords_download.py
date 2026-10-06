import os
import time
import urllib.parse
import xml.etree.ElementTree as ET
import requests
from download_stl_papers import LATEX_DIR, download_and_extract_arxiv_tex

HEADERS = {"User-Agent": "NL2STL-DirectArxivSearch/1.0 (mailto:your-email@domain.com)"}

# Search arXiv directly for STL and MTL papers across CS, EECS, and Math
QUERIES = [
    'all:"Signal Temporal Logic"',
    'all:"STL specification" OR all:"STL specifications"',
    'all:"STL formula" OR all:"STL formulas"',
    'all:"Metric Temporal Logic"',
]


def harvest_arxiv_directly():
    seen_arxiv_ids = set()

    for q in QUERIES:
        start = 0
        batch_size = 200
        encoded_q = urllib.parse.quote(q)

        while True:
            url = f"http://export.arxiv.org/api/query?search_query={encoded_q}&start={start}&max_results={batch_size}"
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code != 200:
                break

            root = ET.fromstring(resp.content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", ns)
            if not entries:
                break

            for entry in entries:
                id_url = entry.find("atom:id", ns).text
                arxiv_id = id_url.split("/abs/")[-1].split("v")[0]
                if arxiv_id in seen_arxiv_ids:
                    continue
                seen_arxiv_ids.add(arxiv_id)

                clean_id = f"arxiv_{arxiv_id.replace('/', '_')}"
                target_folder = os.path.join(LATEX_DIR, clean_id)
                if os.path.isdir(target_folder) and os.listdir(target_folder):
                    continue

                eprint_url = f"https://export.arxiv.org/e-print/{arxiv_id}"
                print(f"[Direct arXiv] Downloading .tex for {arxiv_id}...")
                download_and_extract_arxiv_tex(eprint_url, target_folder)
                time.sleep(3.5)

            if len(entries) < batch_size:
                break
            start += batch_size
            time.sleep(3.0)

    print(f"Total unique arXiv STL/MTL papers scanned: {len(seen_arxiv_ids)}")


if __name__ == "__main__":
    harvest_arxiv_directly()