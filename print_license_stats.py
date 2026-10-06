from collections import Counter
import json
import os

CORPUS_JSON = "stl_expanded_corpus.json"
STATE_FILE = "./dataset_raw/download_state.json"
LATEX_DIR = "./dataset_raw/latex"
PDF_DIR = "./dataset_raw/pdfs"


def classify_license_tier(licenses):
    """Categorizes a paper's license list into a practical legal tier."""
    if not licenses:
        return "4. Unspecified / Unknown"

    lic_set = {l.lower() for l in licenses}

    # Check if any restrictive NC or ND clause is present
    has_nc_or_nd = any("nc" in l or "nd" in l for l in lic_set)
    has_permissive = any(l in ("cc0", "cc-by", "cc-by-sa") for l in lic_set)

    if has_permissive and not has_nc_or_nd:
        return "1. Permissive CC (cc0, cc-by, cc-by-sa)"
    elif any(l.startswith("cc-") for l in lic_set):
        return "2. Restricted CC (cc-by-nc, cc-by-nd, etc.)"
    else:
        return "3. Custom / Non-Exclusive (arXiv default, publisher, etc.)"


def get_download_sets():
    """Loads which papers are downloaded as LaTeX vs. PDF."""
    latex_ids, pdf_ids = set(), set()

    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
            latex_ids = set(state.get("latex", []))
            pdf_ids = set(state.get("pdf", []))
    else:
        # Fallback: check directories directly if state file isn't found
        if os.path.isdir(LATEX_DIR):
            latex_ids = set(os.listdir(LATEX_DIR))
        if os.path.isdir(PDF_DIR):
            pdf_ids = {
                f[:-4] for f in os.listdir(PDF_DIR) if f.endswith(".pdf")
            }

    return latex_ids, pdf_ids


def print_table(title, counter, total):
    """Helper to print nicely aligned count and percentage tables."""
    print(f"\n{title} (Total: {total})")
    print("-" * 68)
    print(f"{'Category / License':<48} | {'Count':>6} | {'Share':>7}")
    print("-" * 68)
    for key, count in sorted(counter.items(), key=lambda x: (-x[1], x[0])):
        pct = (count / total * 100) if total > 0 else 0.0
        print(f"{key:<48} | {count:>6} | {pct:>6.1f}%")
    print("-" * 68)


if __name__ == "__main__":
    if not os.path.exists(CORPUS_JSON):
        raise FileNotFoundError(f"Could not find {CORPUS_JSON}")

    with open(CORPUS_JSON, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    latex_ids, pdf_ids = get_download_sets()
    downloaded_ids = latex_ids | pdf_ids

    # Counters
    all_tiers = Counter()
    downloaded_tiers = Counter()
    latex_tiers = Counter()
    pdf_tiers = Counter()

    exact_licenses_all = Counter()
    exact_licenses_downloaded = Counter()
    audit_status_counter = Counter()
    conflicts = []

    for paper in corpus:
        work_id = paper["openalex_id"].split("/")[-1]
        licenses = paper.get("licenses") or []
        tier = classify_license_tier(licenses)

        # 1. All papers stats
        all_tiers[tier] += 1
        if licenses:
            for lic in licenses:
                exact_licenses_all[lic.lower()] += 1
        else:
            exact_licenses_all["none / unspecified"] += 1

        # Track audit status if update_licenses_from_tex.py was run
        status = paper.get("license_status", "not_audited_yet")
        audit_status_counter[status] += 1
        if paper.get("license_conflict"):
            conflicts.append((
                work_id,
                paper.get("license_sources", {}).get("openalex"),
                paper.get("license_sources", {}).get("tex_file"),
            ))

        # 2. Downloaded papers stats
        if work_id in downloaded_ids:
            downloaded_tiers[tier] += 1
            if licenses:
                for lic in licenses:
                    exact_licenses_downloaded[lic.lower()] += 1
            else:
                exact_licenses_downloaded["none / unspecified"] += 1

            if work_id in latex_ids:
                latex_tiers[tier] += 1
            if work_id in pdf_ids:
                pdf_tiers[tier] += 1

    # ==================== PRINT REPORT ====================
    print("=" * 68)
    print("                STL CORPUS LICENSE STATISTICS REPORT")
    print("=" * 68)

    # Table 1: Legal Tiers across ALL papers in JSON
    print_table("1. LEGAL TIERS — ALL PAPERS IN CORPUS", all_tiers, len(corpus))

    # Table 2: Legal Tiers across DOWNLOADED papers only
    print_table(
        "2. LEGAL TIERS — DOWNLOADED PAPERS ONLY",
        downloaded_tiers,
        len(downloaded_ids),
    )

    # Table 3: Breakdown of LaTeX (.tex) vs PDF downloads by Tier
    print_table(
        "3A. DOWNLOADED AS LATEX (.tex) — BY TIER", latex_tiers, len(latex_ids)
    )
    print_table("3B. DOWNLOADED AS PDF — BY TIER", pdf_tiers, len(pdf_ids))

    # Table 4: Exact license strings on downloaded papers
    print_table(
        "4. EXACT LICENSE STRINGS (DOWNLOADED PAPERS)",
        exact_licenses_downloaded,
        len(downloaded_ids),
    )

    # Table 5: Source comparison (OpenAlex vs .tex vs arXiv OAI)
    if "not_audited_yet" not in audit_status_counter:
        print_table(
            "5. LICENSE DISCOVERY SOURCE (OPENALEX VS .TEX)",
            audit_status_counter,
            len(corpus),
        )

    if conflicts:
        print(f"\n[!] Detected {len(conflicts)} License Conflicts (OpenAlex != .tex):")
        for wid, oa_lic, tex_lic in conflicts[:10]:
            print(f"  - {wid}: OpenAlex={oa_lic} vs. .tex={tex_lic}")