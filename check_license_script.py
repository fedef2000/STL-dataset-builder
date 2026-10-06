import glob
import json
import os
import re
import time
import xml.etree.ElementTree as ET
import requests

CORPUS_JSON = "stl_expanded_corpus.json"
LATEX_DIR = "./dataset_raw/latex"

HEADERS = {
    "User-Agent": "NL2STL-LicenseAuditor/1.0 (mailto:your-email@domain.com)"
}

# Ordered from most specific (NC/ND variants) to general CC-BY / CC0
LATEX_LICENSE_PATTERNS = [
    # 1. Explicit URLs or standard Creative Commons abbreviations
    (
        "cc0",
        re.compile(
            r"creativecommons\.org/publicdomain/zero|cc0[\s\-]1\.0|\\cczero",
            re.I,
        ),
    ),
    (
        "cc-by-nc-nd",
        re.compile(
            r"creativecommons\.org/licenses/by-nc-nd|cc[\s\-]by[\s\-]nc[\s\-]nd|\\ccbyncnd",
            re.I,
        ),
    ),
    (
        "cc-by-nc-sa",
        re.compile(
            r"creativecommons\.org/licenses/by-nc-sa|cc[\s\-]by[\s\-]nc[\s\-]sa|\\ccbyncsa",
            re.I,
        ),
    ),
    (
        "cc-by-nc",
        re.compile(
            r"creativecommons\.org/licenses/by-nc(?!/)|cc[\s\-]by[\s\-]nc(?![\s\-](?:sa|nd))|\\ccbync(?![a-z])",
            re.I,
        ),
    ),
    (
        "cc-by-nd",
        re.compile(
            r"creativecommons\.org/licenses/by-nd|cc[\s\-]by[\s\-]nd|\\ccbynd",
            re.I,
        ),
    ),
    (
        "cc-by-sa",
        re.compile(
            r"creativecommons\.org/licenses/by-sa|cc[\s\-]by[\s\-]sa|\\ccbysa",
            re.I,
        ),
    ),
    (
        "cc-by",
        re.compile(
            r"creativecommons\.org/licenses/by(?!/)|"
            r"cc[\s\-]by(?![\s\-](?:nc|sa|nd))|"
            r"\\ccby(?![a-z])|"
            r"creative\s+commons\s+attribution\s+(?:4\.0|3\.0|international)|"
            r"type=\{cc\}[\s,]*modifier=\{by\}|"
            r"\\acmlicense\{cc-by\}",
            re.I,
        ),
    ),
    # 2. Non-CC arXiv default license if mentioned in header comments/text
    (
        "arxiv-nonexclusive",
        re.compile(r"arxiv\.org/licenses/nonexclusive-distrib", re.I),
    ),
]


def strip_latex_comments(text):
    """Removes commented-out LaTeX lines (%) so template comments don't trigger false positives."""
    cleaned_lines = []
    for line in text.splitlines():
        # Strip everything after an unescaped %
        line_no_comment = re.sub(r"(?<!\\)%.*$", "", line)
        cleaned_lines.append(line_no_comment)
    return "\n".join(cleaned_lines)


def detect_license_in_tex_folder(tex_folder):
    """Scans all .tex files in a paper's directory for license declarations."""
    if not os.path.isdir(tex_folder):
        return []

    found_licenses = set()
    tex_files = glob.glob(os.path.join(tex_folder, "*.tex"))

    for tex_file in tex_files:
        try:
            with open(tex_file, "r", encoding="utf-8", errors="ignore") as f:
                raw_content = f.read()

            active_code = strip_latex_comments(raw_content)

            for lic_name, pattern in LATEX_LICENSE_PATTERNS:
                if pattern.search(active_code):
                    found_licenses.add(lic_name)
                    # Stop if we matched a specific CC-BY variant so 'cc-by-nc' doesn't also trigger generic checks
                    break
        except Exception:
            continue

    return sorted(list(found_licenses))


def fetch_arxiv_oai_license(arxiv_id):
    """Queries arXiv's OAI-PMH endpoint for the official upload license if still unknown."""
    if not arxiv_id:
        return None
    clean_id = arxiv_id.split("v")[0]
    oai_url = (
        f"https://export.arxiv.org/oai2?verb=GetRecord"
        f"&identifier=oai:arXiv.org:{clean_id}&metadataPrefix=arXiv"
    )
    try:
        resp = requests.get(oai_url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        root = ET.fromstring(resp.content)
        # Find the <license> element in the arXiv OAI namespace
        for elem in root.iter():
            if elem.tag.endswith("license") and elem.text:
                lic_url = elem.text.strip().lower()
                for lic_name, pattern in LATEX_LICENSE_PATTERNS:
                    if pattern.search(lic_url):
                        return lic_name
                return lic_url
    except Exception:
        pass
    return None

if __name__ == "__main__":
    with open(CORPUS_JSON, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    newly_found_count = 0
    mismatch_count = 0
    matched_count = 0
    oai_recovered_count = 0

    for paper in corpus:
        work_id = paper["openalex_id"].split("/")[-1]
        tex_folder = os.path.join(LATEX_DIR, work_id)

        # Preserve original OpenAlex licenses (even if you run this script multiple times)
        if "license_sources" in paper and "openalex" in paper["license_sources"]:
            oa_licenses = set(paper["license_sources"]["openalex"])
        else:
            oa_licenses = set(paper.get("licenses") or [])

        tex_licenses = set()
        if os.path.isdir(tex_folder):
            tex_licenses = set(detect_license_in_tex_folder(tex_folder))

        # Compare OpenAlex (JSON) vs. .tex file
        if tex_licenses and not oa_licenses:
            status = "newly_found_in_tex"
            newly_found_count += 1
            effective_licenses = tex_licenses
            print(f"[NEW IN .TEX] {work_id}: OpenAlex had None -> .tex has {sorted(tex_licenses)}")

        elif tex_licenses and oa_licenses:
            if tex_licenses == oa_licenses:
                status = "match"
                matched_count += 1
                effective_licenses = tex_licenses
            else:
                status = "mismatch"
                mismatch_count += 1
                # Since we extract text from the .tex file, the .tex file's own license governs it
                effective_licenses = tex_licenses
                print(
                    f"[MISMATCH!]   {work_id}: OpenAlex says {sorted(oa_licenses)} "
                    f"!= .tex says {sorted(tex_licenses)} -> Using .tex license"
                )

        elif not tex_licenses and oa_licenses:
            status = "openalex_only"
            effective_licenses = oa_licenses

        else:
            status = "none"
            effective_licenses = set()

        # Fallback: If neither OpenAlex nor .tex had a license, check arXiv OAI-PMH
        oai_license = None
        if not effective_licenses and paper.get("arxiv_id"):
            oai_license = fetch_arxiv_oai_license(paper["arxiv_id"])
            if oai_license:
                effective_licenses.add(oai_license)
                status = "recovered_from_arxiv_oai"
                oai_recovered_count += 1
                print(f"[ARXIV OAI]   {work_id}: Found '{oai_license}'")
            time.sleep(0.5)

        # Update the JSON record with full transparency
        paper["licenses"] = sorted(list(effective_licenses))
        paper["license_status"] = status
        paper["license_conflict"] = (status == "mismatch")
        paper["license_sources"] = {
            "openalex": sorted(list(oa_licenses)),
            "tex_file": sorted(list(tex_licenses)),
            "arxiv_oai": [oai_license] if oai_license else [],
        }
        paper["has_cc_license"] = any(
            l.startswith("cc-") or l == "cc0" for l in effective_licenses
        )
        # Strict check: ALL effective licenses must be permissive (or at least no NC/ND conflict)
        paper["is_permissive_cc"] = (
            any(l in ("cc0", "cc-by", "cc-by-sa") for l in effective_licenses)
            and not any("nc" in l or "nd" in l for l in effective_licenses)
        )

    with open(CORPUS_JSON, "w", encoding="utf-8") as f:
        json.dump(corpus, f, indent=2, ensure_ascii=False)

    print("\n=== License Comparison Summary ===")
    print(f"1. New licenses found in .tex (OpenAlex was empty): {newly_found_count}")
    print(f"2. Exact matches (OpenAlex == .tex):                {matched_count}")
    print(f"3. Conflicts/Mismatches (OpenAlex != .tex):         {mismatch_count}")
    print(f"4. Recovered via arXiv OAI-PMH metadata:            {oai_recovered_count}")