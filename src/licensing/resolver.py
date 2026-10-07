import glob
import os
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
import requests

from config import HEADERS
from src.storage import classify_tier

# Ordered from most specific (NC/ND variants) to general CC-BY / CC0
LICENSE_PATTERNS = [
    ("cc0", re.compile(r"creativecommons\.org/publicdomain/zero|cc0[\s\-]1\.0|\\cczero", re.I)),
    ("cc-by-nc-nd", re.compile(r"creativecommons\.org/licenses/by-nc-nd|cc[\s\-]by[\s\-]nc[\s\-]nd|\\ccbyncnd", re.I)),
    ("cc-by-nc-sa", re.compile(r"creativecommons\.org/licenses/by-nc-sa|cc[\s\-]by[\s\-]nc[\s\-]sa|\\ccbyncsa", re.I)),
    ("cc-by-nc", re.compile(r"creativecommons\.org/licenses/by-nc(?!/)|cc[\s\-]by[\s\-]nc(?![\s\-](?:sa|nd))|\\ccbync(?![a-z])", re.I)),
    ("cc-by-nd", re.compile(r"creativecommons\.org/licenses/by-nd|cc[\s\-]by[\s\-]nd|\\ccbynd", re.I)),
    ("cc-by-sa", re.compile(r"creativecommons\.org/licenses/by-sa|cc[\s\-]by[\s\-]sa|\\ccbysa", re.I)),
    ("cc-by", re.compile(
        r"creativecommons\.org/licenses/by(?!/)|"
        r"cc[\s\-]by(?![\s\-](?:nc|sa|nd))|"
        r"\\ccby(?![a-z])|"
        r"creative\s+commons\s+attribution\s+(?:4\.0|3\.0|international)|"
        r"type=\{cc\}[\s,]*modifier=\{by\}|"
        r"\\acmlicense\{cc-by\}", re.I
    )),
    ("arxiv-nonexclusive", re.compile(r"arxiv\.org/licenses/nonexclusive-distrib", re.I)),
]

def strip_latex_comments(text: str) -> str:
    """Removes commented-out LaTeX lines (%) to avoid false matches in template instructions."""
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in text.splitlines())

def detect_licenses_in_text(text: str) -> list[str]:
    """Applies regex patterns to extract recognized licenses."""
    found = set()
    for lic_name, pattern in LICENSE_PATTERNS:
        if pattern.search(text):
            found.add(lic_name)
            break  # Stop if a specific CC variant matches to prevent generic overlap
    return sorted(list(found))

def scan_tex_folder(tex_folder: Path) -> list[str]:
    """Scans all .tex files in a folder for license declarations."""
    if not tex_folder.is_dir():
        return []
    found = set()
    for tex_file in tex_folder.rglob("*.tex"):
        try:
            raw = tex_file.read_text(encoding="utf-8", errors="ignore")
            active_code = strip_latex_comments(raw)
            found.update(detect_licenses_in_text(active_code))
        except Exception:
            continue
    return sorted(list(found))

def scan_pdf_file(pdf_path: Path) -> list[str]:
    """Scans PDF metadata and the first page for license declarations."""
    if not pdf_path.is_file():
        return []
    try:
        import pymupdf
        pymupdf.TOOLS.mupdf_display_errors(False)
        pymupdf.TOOLS.mupdf_display_warnings(False)
        
        found = set()
        with pymupdf.open(pdf_path) as doc:
            # Check metadata fields
            meta = doc.metadata or {}
            meta_text = f"{meta.get('subject', '')} {meta.get('keywords', '')} {meta.get('creator', '')}"
            found.update(detect_licenses_in_text(meta_text))
            
            # Check first page text (where copyright blocks usually live)
            if doc.page_count > 0:
                page_text = doc[0].get_text()
                found.update(detect_licenses_in_text(page_text))
                
        return sorted(list(found))
    except Exception:
        return []

def fetch_arxiv_oai_license(arxiv_id: str) -> list[str]:
    """Queries export.arxiv.org/oai2 to retrieve the exact upload license."""
    if not arxiv_id:
        return []
    clean_id = arxiv_id.split("v")[0]
    url = f"https://export.arxiv.org/oai2?verb=GetRecord&identifier=oai:arXiv.org:{clean_id}&metadataPrefix=arXiv"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for elem in root.iter():
                if elem.tag.endswith("license") and elem.text:
                    lic_url = elem.text.strip().lower()
                    matched = detect_licenses_in_text(lic_url)
                    return matched if matched else [lic_url]
    except Exception:
        pass
    return []

def resolve_paper_license(paper: dict, base_dir: Path) -> dict:
    """
    Main resolver logic: Inspects local files and APIs, resolves conflicts, 
    and updates the paper['license_info'] block in place.
    """
    pid = paper["paper_id"]
    status = paper.get("local_files", {}).get("status", "pending")
    arxiv_id = paper.get("arxiv_id")
    
    lic_info = paper.setdefault("license_info", {})
    sources = lic_info.setdefault("sources", {})
    
    # Preserve original OpenAlex licenses if this runs multiple times
    oa_licenses = set(sources.get("openalex_locations") or [])
    
    tex_lics, pdf_lics, oai_lics = [], [], []
    
    if status == "downloaded_latex":
        tex_folder = base_dir / "data" / "raw" / "latex" / pid
        tex_lics = scan_tex_folder(tex_folder)
        sources["tex_source"] = tex_lics
        
    elif status == "downloaded_pdf":
        pdf_file = base_dir / "data" / "raw" / "pdfs" / f"{pid}.pdf"
        pdf_lics = scan_pdf_file(pdf_file)
        sources["pdf_metadata"] = pdf_lics

    # Fallback to arXiv OAI if local files didn't specify a license
    if not tex_lics and not pdf_lics and arxiv_id:
        oai_lics = fetch_arxiv_oai_license(arxiv_id)
        sources["arxiv_oai"] = oai_lics
        time.sleep(0.5)  # Be polite to arXiv OAI

    # Determine the "Effective License" (Priority: Local Files -> arXiv OAI -> OpenAlex)
    if tex_lics:
        eff_lics = tex_lics
        eff_src = "tex_source"
    elif pdf_lics:
        eff_lics = pdf_lics
        eff_src = "pdf_metadata"
    elif oai_lics:
        eff_lics = oai_lics
        eff_src = "arxiv_oai"
    elif oa_licenses:
        eff_lics = list(oa_licenses)
        eff_src = "openalex_locations"
    else:
        eff_lics = []
        eff_src = "none"

    # Check for conflicts between the authoritative source and OpenAlex
    has_conflict = False
    if eff_src in ("tex_source", "pdf_metadata", "arxiv_oai") and oa_licenses:
        # It's a conflict if the sources disagree on restrictions (e.g., cc-by vs cc-by-nc)
        if set(eff_lics) != oa_licenses:
            has_conflict = True

    lic_info["effective_licenses_all"] = sorted(eff_lics)
    lic_info["effective_license"] = eff_lics[0] if eff_lics else None
    lic_info["effective_source"] = eff_src
    lic_info["tier"] = classify_tier(eff_lics)
    lic_info["has_conflict"] = has_conflict

    return lic_info