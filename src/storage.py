import json
from pathlib import Path
import re
from config import CORPUS_FILE, RAW_LATEX_DIR, RAW_PDF_DIR


def normalize_title(title: str) -> str:
    return re.sub(r"\W+", "", (title or "").lower())


def classify_tier(licenses: list) -> str:
    if not licenses:
        return "unspecified"
    lic_set = {l.lower() for l in licenses}
    has_nc_nd = any("nc" in l or "nd" in l for l in lic_set)
    has_perm = any(
        l in ("cc0", "cc-by", "cc-by-sa", "cc-by-4.0") for l in lic_set
    )
    if has_perm and not has_nc_nd:
        return "permissive_cc"
    elif any(l.startswith("cc-") for l in lic_set):
        return "restricted_cc"
    return "custom_or_arxiv"


class CorpusStore:
    """Thread-safe, deduplicating manager for data/corpus.json."""

    def __init__(self, path: Path = CORPUS_FILE):
        self.path = path
        self.papers = {}
        self.arxiv_index = {}
        self.doi_index = {}
        self.title_index = {}
        self.load()

    def load(self):
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                self.papers = json.load(f)
        self._rebuild_indexes()

    def _rebuild_indexes(self):
        self.arxiv_index.clear()
        self.doi_index.clear()
        self.title_index.clear()
        for pid, p in self.papers.items():
            if p.get("arxiv_id"):
                self.arxiv_index[p["arxiv_id"]] = pid
            if p.get("doi"):
                self.doi_index[p["doi"].lower()] = pid
            norm_t = normalize_title(p.get("title"))
            if len(norm_t) > 15:
                self.title_index[norm_t] = pid

    def upsert_paper(
        self,
        paper_dict: dict,
        method: str,
        hop: int = None,
        parent_ids: list = None,
    ):
        """
        Inserts a newly discovered paper or merges discovery/license data
        if the paper already exists under the same ID, arXiv ID, DOI, or Title.
        """
        pid = paper_dict["paper_id"]
        arxiv_id = paper_dict.get("arxiv_id")
        doi = (paper_dict.get("doi") or "").lower()
        norm_t = normalize_title(paper_dict.get("title"))

        existing_id = None
        if pid in self.papers:
            existing_id = pid
        elif arxiv_id and arxiv_id in self.arxiv_index:
            existing_id = self.arxiv_index[arxiv_id]
        elif doi and doi in self.doi_index:
            existing_id = self.doi_index[doi]
        elif len(norm_t) > 15 and norm_t in self.title_index:
            existing_id = self.title_index[norm_t]

        if existing_id:
            rec = self.papers[existing_id]
            # Update cited_by_count if the new record has it
            if paper_dict.get("cited_by_count", 0) > rec.get("cited_by_count", 0):
                rec["cited_by_count"] = paper_dict["cited_by_count"]
            
            disc = rec.setdefault(
                "discovery",
                {"methods": [], "hop_distance": None, "parent_ids": []},
            )
            if method not in disc["methods"]:
                disc["methods"].append(method)
            if hop is not None:
                cur_hop = disc.get("hop_distance")
                disc["hop_distance"] = (
                    min(cur_hop, hop) if cur_hop is not None else hop
                )
            if parent_ids:
                disc["parent_ids"] = sorted(
                    list(set(disc.get("parent_ids", [])) | set(parent_ids))
                )

            # Merge any newly discovered arXiv ID or PDF mirrors
            if not rec.get("arxiv_id") and arxiv_id:
                rec["arxiv_id"] = arxiv_id
                rec["urls"]["eprint_source"] = (
                    f"https://export.arxiv.org/e-print/{arxiv_id}"
                )
                self.arxiv_index[arxiv_id] = existing_id

            existing_pdfs = set(rec.get("urls", {}).get("pdf_mirrors", []))
            new_pdfs = set(paper_dict.get("urls", {}).get("pdf_mirrors", []))
            rec["urls"]["pdf_mirrors"] = sorted(list(existing_pdfs | new_pdfs))

            # Merge OpenAlex licenses without overwriting verified .tex licenses
            oa_src = (
                rec.setdefault("license_info", {})
                .setdefault("sources", {})
                .setdefault("openalex_locations", [])
            )
            new_oa_lics = (
                paper_dict.get("license_info", {})
                .get("sources", {})
                .get("openalex_locations", [])
            )
            merged_oa = sorted(list(set(oa_src) | set(new_oa_lics)))
            rec["license_info"]["sources"]["openalex_locations"] = merged_oa
            if not rec["license_info"].get("effective_license") and merged_oa:
                rec["license_info"]["effective_license"] = merged_oa[0]
                rec["license_info"]["effective_licenses_all"] = merged_oa
                rec["license_info"]["effective_source"] = "openalex_locations"
                rec["license_info"]["tier"] = classify_tier(merged_oa)

            return existing_id, False

        # Check if local files already exist on disk for this new paper
        tex_dir = RAW_LATEX_DIR / pid
        pdf_file = RAW_PDF_DIR / f"{pid}.pdf"
        if tex_dir.is_dir() and any(tex_dir.glob("*.tex")):
            paper_dict["local_files"] = {
                "status": "downloaded_latex",
                "path": f"data/raw/latex/{pid}",
            }
        elif pdf_file.is_file() and pdf_file.stat().st_size > 1024:
            paper_dict["local_files"] = {
                "status": "downloaded_pdf",
                "path": f"data/raw/pdfs/{pid}.pdf",
            }

        paper_dict["discovery"] = {
            "methods": [method],
            "hop_distance": hop,
            "parent_ids": parent_ids or [],
        }
        self.papers[pid] = paper_dict
        if arxiv_id:
            self.arxiv_index[arxiv_id] = pid
        if doi:
            self.doi_index[doi] = pid
        if len(norm_t) > 15:
            self.title_index[norm_t] = pid

        return pid, True

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.papers, f, indent=2, ensure_ascii=False)