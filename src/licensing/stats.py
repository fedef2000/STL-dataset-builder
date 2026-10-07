from collections import Counter
from src.storage import CorpusStore

def print_table(title: str, counter: Counter, total: int):
    print(f"\n{title} (Total Evaluated: {total})")
    print("-" * 75)
    print(f"{'Category / License / Source':<52} | {'Count':>7} | {'Share':>6}")
    print("-" * 75)
    for key, count in sorted(counter.items(), key=lambda x: (-x[1], x[0])):
        pct = (count / total * 100) if total > 0 else 0.0
        print(f"{key:<52} | {count:>7} | {pct:>5.1f}%")
    print("-" * 75)

def generate_license_report(store: CorpusStore):
    all_tiers = Counter()
    dl_tiers = Counter()
    tex_tiers = Counter()
    pdf_tiers = Counter()
    
    exact_licenses = Counter()
    provenance_sources = Counter()
    conflict_count = 0

    downloaded_papers = 0

    for pid, p in store.papers.items():
        lic_info = p.get("license_info", {})
        tier = lic_info.get("tier", "unspecified")
        status = p.get("local_files", {}).get("status")
        
        all_tiers[tier] += 1
        
        if status in ("downloaded_latex", "downloaded_pdf"):
            downloaded_papers += 1
            dl_tiers[tier] += 1
            
            eff_lic = lic_info.get("effective_license") or "none / unspecified"
            exact_licenses[eff_lic] += 1
            
            src = lic_info.get("effective_source", "none")
            provenance_sources[src] += 1
            
            if lic_info.get("has_conflict"):
                conflict_count += 1
            
            if status == "downloaded_latex":
                tex_tiers[tier] += 1
            elif status == "downloaded_pdf":
                pdf_tiers[tier] += 1

    print("=" * 75)
    print("               STL CORPUS LICENSE AUDIT REPORT")
    print("=" * 75)

    print_table("1. LEGAL TIERS — ALL PAPERS IN CORPUS", all_tiers, len(store.papers))
    print_table("2. LEGAL TIERS — DOWNLOADED PAPERS ONLY", dl_tiers, downloaded_papers)
    print_table("3A. DOWNLOADED AS LATEX (.tex) — BY TIER", tex_tiers, sum(tex_tiers.values()))
    print_table("3B. DOWNLOADED AS PDF — BY TIER", pdf_tiers, sum(pdf_tiers.values()))
    print_table("4. EXACT EFFECTIVE LICENSES (DOWNLOADED)", exact_licenses, downloaded_papers)
    print_table("5. PROVENANCE SOURCE (Where did the license come from?)", provenance_sources, downloaded_papers)

    print(f"\n[!] Detected {conflict_count} License Conflicts where OpenAlex metadata mismatched local files.")
    print("    (Local files / arXiv OAI were prioritized as the Single Source of Truth).")
    print("=" * 75)