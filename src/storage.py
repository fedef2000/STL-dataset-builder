import json
import os
from pathlib import Path
import re
import shutil
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
        self.alias_index = {}
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
        self.alias_index.clear()
        for pid, p in self.papers.items():
            if p.get("arxiv_id"):
                self.arxiv_index[p["arxiv_id"]] = pid
            if p.get("doi"):
                self.doi_index[p["doi"].lower()] = pid
            # IDs and DOIs of entries merged into this one, so they are not added again by a later crawl
            for alias in p.get("alternate_ids") or []:
                self.alias_index[alias] = pid
            for alt_doi in p.get("alternate_dois") or []:
                self.doi_index.setdefault(alt_doi.lower(), pid)
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
        elif pid in self.alias_index:
            existing_id = self.alias_index[pid]
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
            arxiv_owner = None
            if not rec.get("arxiv_id") and arxiv_id:
                arxiv_owner = self.arxiv_index.get(arxiv_id)
                rec["arxiv_id"] = arxiv_id
                rec["urls"]["eprint_source"] = (
                    f"https://export.arxiv.org/e-print/{arxiv_id}"
                )
                self.arxiv_index.setdefault(arxiv_id, existing_id)

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

            # The new arXiv ID already belongs to another entry: the two are the same work
            if arxiv_owner and arxiv_owner != existing_id and arxiv_owner in self.papers:
                existing_id = self.merge_papers(existing_id, arxiv_owner)

            return existing_id, False

        # Check if local files already exist on disk for this new paper
        tex_dir = RAW_LATEX_DIR / pid
        pdf_file = RAW_PDF_DIR / f"{pid}.pdf"
        if tex_dir.is_dir() and any(tex_dir.rglob("*.tex")):
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

    def find_arxiv_owner(self, arxiv_id: str, other_than: str) -> str | None:
        """Returns the ID of another entry that already has this arXiv ID, if any."""
        owner = self.arxiv_index.get(arxiv_id)
        return owner if owner and owner != other_than and owner in self.papers else None

    def merge_papers(self, id_a: str, id_b: str) -> str:
        """
        Merges two entries that are the same work (e.g. the preprint and the published version) and returns the ID kept.
        The published OpenAlex record is preferred. The downloaded files of the better copy are kept, the others deleted.
        """
        def preference(pid: str) -> tuple:
            p = self.papers[pid]
            doi = (p.get("doi") or "").lower()
            return (pid.startswith("W"), bool(doi) and "10.48550/arxiv" not in doi, p.get("cited_by_count") or 0, pid)

        keep_id, drop_id = sorted((id_a, id_b), key=preference, reverse=True)
        keep = self.papers[keep_id]
        drop = self.papers.pop(drop_id)

        # Identifiers
        keep["alternate_ids"] = sorted(set(keep.get("alternate_ids") or []) | set(drop.get("alternate_ids") or []) | {drop_id})
        keep_doi, drop_doi = keep.get("doi"), drop.get("doi")
        if not keep_doi:
            keep["doi"] = drop_doi
        elif drop_doi and drop_doi.lower() != keep_doi.lower():
            keep["alternate_dois"] = sorted(set(keep.get("alternate_dois") or []) | {drop_doi})
        if drop.get("alternate_dois"):
            keep["alternate_dois"] = sorted(set(keep.get("alternate_dois") or []) | set(drop["alternate_dois"]))
        urls, drop_urls = keep.setdefault("urls", {}), drop.get("urls") or {}
        if not keep.get("arxiv_id"):
            keep["arxiv_id"] = drop.get("arxiv_id")
        if not urls.get("eprint_source"):
            urls["eprint_source"] = drop_urls.get("eprint_source")
        urls["pdf_mirrors"] = sorted(set(urls.get("pdf_mirrors") or []) | set(drop_urls.get("pdf_mirrors") or []))

        # Metadata and discovery
        keep["cited_by_count"] = max(keep.get("cited_by_count") or 0, drop.get("cited_by_count") or 0)
        keep["is_oa"] = bool(keep.get("is_oa") or drop.get("is_oa"))
        disc = keep.setdefault("discovery", {"methods": [], "hop_distance": None, "parent_ids": []})
        drop_disc = drop.get("discovery") or {}
        disc["methods"] = disc.get("methods", []) + [m for m in drop_disc.get("methods", []) if m not in disc.get("methods", [])]
        hops = [h for h in (disc.get("hop_distance"), drop_disc.get("hop_distance")) if h is not None]
        disc["hop_distance"] = min(hops) if hops else None
        disc["parent_ids"] = sorted((set(disc.get("parent_ids") or []) | set(drop_disc.get("parent_ids") or [])) - {keep_id, drop_id})
        if drop_disc.get("expanded_hop_2"):
            disc["expanded_hop_2"] = True
        openalex_licenses = sorted(
            set(((keep.get("license_info") or {}).get("sources") or {}).get("openalex_locations") or [])
            | set(((drop.get("license_info") or {}).get("sources") or {}).get("openalex_locations") or [])
        )

        # Downloaded files: keep the better copy (LaTeX over PDF over nothing) under the kept ID
        rank = {"downloaded_latex": 3, "downloaded_pdf": 2, "pending": 1, "unavailable": 0}
        keep_status = keep.get("local_files", {}).get("status", "pending")
        drop_status = drop.get("local_files", {}).get("status", "pending")
        keep_tex, drop_tex = RAW_LATEX_DIR / keep_id, RAW_LATEX_DIR / drop_id
        keep_pdf, drop_pdf = RAW_PDF_DIR / f"{keep_id}.pdf", RAW_PDF_DIR / f"{drop_id}.pdf"
        if rank.get(drop_status, 0) > rank.get(keep_status, 0):
            shutil.rmtree(keep_tex, ignore_errors=True)
            keep_pdf.unlink(missing_ok=True)
            if drop_tex.is_dir():
                shutil.move(str(drop_tex), str(keep_tex))
            if drop_pdf.is_file():
                shutil.move(str(drop_pdf), str(keep_pdf))
            path = {"downloaded_latex": f"data/raw/latex/{keep_id}", "downloaded_pdf": f"data/raw/pdfs/{keep_id}.pdf"}.get(drop_status)
            keep["local_files"] = {"status": drop_status, "path": path}
            # The licence audit and the formula estimate describe the files, so they follow them
            for field in ("formula_estimates", "license_info"):
                if field in drop:
                    keep[field] = drop[field]
                else:
                    keep.pop(field, None)
        else:
            shutil.rmtree(drop_tex, ignore_errors=True)
            drop_pdf.unlink(missing_ok=True)
        keep.setdefault("license_info", {}).setdefault("sources", {})["openalex_locations"] = openalex_licenses

        # Other papers that listed the dropped entry as a parent now point to the kept one
        for p in self.papers.values():
            parents = (p.get("discovery") or {}).get("parent_ids") or []
            if drop_id in parents:
                p["discovery"]["parent_ids"] = sorted((set(parents) - {drop_id}) | {keep_id})

        self._rebuild_indexes()
        return keep_id

    def merge_duplicates(self) -> list[tuple[str, str]]:
        """Merges every group of entries sharing an arXiv ID or a DOI. Returns the (kept, dropped) pairs."""
        merged = []
        while True:
            seen, pair = {}, None
            for pid, p in self.papers.items():
                for key in (("arxiv", p.get("arxiv_id")), ("doi", (p.get("doi") or "").lower())):
                    if not key[1]:
                        continue
                    if key in seen:
                        pair = (seen[key], pid)
                        break
                    seen[key] = pid
                if pair:
                    break
            if not pair:
                return merged
            kept = self.merge_papers(*pair)
            merged.append((kept, pair[0] if kept == pair[1] else pair[1]))

    def save(self):
        # Write to a temp file and swap it in, so an interrupted save never leaves a truncated corpus.json
        tmp_path = self.path.with_name(self.path.name + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.papers, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self.path)