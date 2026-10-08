import argparse
import sys
from pathlib import Path
import logging

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.storage import CorpusStore
from src.analysis.estimator import estimate_paper_formulas

logging.basicConfig(level=logging.INFO, format="%(message)s")

def print_report(rows: list, scanned: int) -> None:
    """Prints the yield report from (estimates, paper_id, title, status) rows."""
    def total(key: str, subset: list = rows) -> int:
        return sum(r[0].get(key, 0) for r in subset)

    papers_with_concrete = sum(1 for r in rows if r[0]["concrete"] > 0)

    print("\n" + "=" * 80)
    print("                 STL FORMULA YIELD ESTIMATION REPORT")
    print("=" * 80)
    print(f"Total Papers Scanned:              {scanned}")
    print(f"Papers with >= 1 Concrete Formula: {papers_with_concrete} ({(papers_with_concrete/max(1, scanned))*100:.1f}%)")
    print("-" * 80)
    print("A formula is concrete when at least one of its temporal operators has numeric time bounds.")
    print(f"Concrete Formulas:                 {total('formulas_concrete')}")
    print(f"Symbolic/Parametric Formulas:      {total('formulas_symbolic')}")
    print(f"Operators with Numeric Bounds:     {total('concrete')}")
    print(f"Operators with Symbolic Bounds:    {total('symbolic')}")
    print("-" * 80)
    for label, key in (("LaTeX", "downloaded_latex"), ("PDF", "downloaded_pdf")):
        subset = [r for r in rows if r[3] == key]
        print(f"{label + ' papers:':<14}{len(subset):>5} scanned | {sum(1 for r in subset if r[0]['concrete'] > 0):>5} with >= 1 concrete | "
              f"{total('formulas_concrete', subset):>6} concrete formulas | {total('formulas_symbolic', subset):>6} symbolic formulas")
    print("=" * 80)

    print("\nTOP 20 MOST PROMISING PAPERS:")
    print(f"{'Formulas':<9} | {'Operators':<9} | {'Symbolic':<9} | {'Source':<7} | {'Paper ID':<16} | {'Title'}")
    print("-" * 120)

    # Sort by highest number of concrete formulas, then concrete operators
    rows.sort(key=lambda r: (-r[0].get("formulas_concrete", 0), -r[0]["concrete"]))

    for estimates, pid, title, status in rows[:20]:
        src_label = "LaTeX" if "latex" in (status or "") else "PDF"
        short_title = title[:60] + "..." if len(title) > 60 else title
        print(f"{estimates.get('formulas_concrete', 0):<9} | {estimates['concrete']:<9} | {estimates.get('formulas_symbolic', 0):<9} | {src_label:<7} | {pid:<16} | {short_title}")
    print("=" * 120)
    print("\nNote: These are regex-based estimates intended to help rank papers for rigorous extraction.")
    print("They are stored under 'formula_estimates' in data/corpus.json.")


def main():
    parser = argparse.ArgumentParser(description="Step 4: Estimate STL formula yield in downloaded papers.")
    parser.add_argument("--limit", type=int, default=None, help="Process only N papers (for testing).")
    parser.add_argument("--stats", action="store_true", help="Print the report from the estimates already stored in data/corpus.json and exit, without scanning any file.")
    args = parser.parse_args()

    store = CorpusStore()

    if args.stats:
        rows = [
            (p["formula_estimates"], pid, p.get("title") or "Unknown Title", p.get("local_files", {}).get("status"))
            for pid, p in store.papers.items()
            if p.get("formula_estimates") and p.get("local_files", {}).get("status") in ("downloaded_latex", "downloaded_pdf")
        ]
        not_scanned = sum(
            1 for p in store.papers.values()
            if p.get("local_files", {}).get("status") in ("downloaded_latex", "downloaded_pdf") and not p.get("formula_estimates")
        )
        print_report(rows, len(rows))
        if any("formulas_concrete" not in r[0] for r in rows):
            print("\nSome stored estimates predate the formula counts: run this script without --stats to refresh them.")
        if not_scanned:
            print(f"\n{not_scanned} downloaded papers have no stored estimate yet: run this script without --stats to scan them.")
        return
    
    queue = [
        pid for pid, p in store.papers.items()
        if p.get("local_files", {}).get("status") in ("downloaded_latex", "downloaded_pdf")
    ]
    
    if args.limit:
        queue = queue[:args.limit]

    logging.info(f"=== STEP 4: FORMULA ESTIMATION | Scanning {len(queue)} downloaded papers ===")
    
    # One row per paper for the report
    rows = []

    processed = 0
    for pid in queue:
        paper = store.papers[pid]
        
        # Estimate formulas
        estimates = estimate_paper_formulas(paper, BASE_DIR)
        paper["formula_estimates"] = estimates
        
        rows.append((estimates, pid, paper.get("title") or "Unknown Title", paper.get("local_files", {}).get("status")))
        
        processed += 1
        if processed % 100 == 0:
            store.save()
            logging.info(f"  ...Scanned {processed}/{len(queue)} papers.")
            
    store.save()
    
    print_report(rows, len(queue))

if __name__ == "__main__":
    main()