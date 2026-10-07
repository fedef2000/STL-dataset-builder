import argparse
import sys
from pathlib import Path
import logging

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.storage import CorpusStore
from src.analysis.estimator import estimate_paper_formulas

logging.basicConfig(level=logging.INFO, format="%(message)s")

def main():
    parser = argparse.ArgumentParser(description="Step 4: Estimate STL formula yield in downloaded papers.")
    parser.add_argument("--limit", type=int, default=None, help="Process only N papers (for testing).")
    args = parser.parse_args()

    store = CorpusStore()
    
    queue = [
        pid for pid, p in store.papers.items()
        if p.get("local_files", {}).get("status") in ("downloaded_latex", "downloaded_pdf")
    ]
    
    if args.limit:
        queue = queue[:args.limit]

    logging.info(f"=== STEP 4: FORMULA ESTIMATION | Scanning {len(queue)} downloaded papers ===")
    
    total_concrete = 0
    total_symbolic = 0
    papers_with_concrete = 0
    
    # Track top papers for reporting
    top_papers = []

    processed = 0
    for pid in queue:
        paper = store.papers[pid]
        
        # Estimate formulas
        estimates = estimate_paper_formulas(paper, BASE_DIR)
        paper["formula_estimates"] = estimates
        
        c = estimates["concrete"]
        s = estimates["symbolic"]
        
        total_concrete += c
        total_symbolic += s
        if c > 0:
            papers_with_concrete += 1
            
        top_papers.append((c, s, pid, paper.get("title", "Unknown Title"), paper.get("local_files", {}).get("status")))
        
        processed += 1
        if processed % 100 == 0:
            store.save()
            logging.info(f"  ...Scanned {processed}/{len(queue)} papers.")
            
    store.save()
    
    # ---------------------------------------------------------
    # PRINT ESTIMATION REPORT
    # ---------------------------------------------------------
    print("\n" + "=" * 80)
    print("                 STL FORMULA YIELD ESTIMATION REPORT")
    print("=" * 80)
    print(f"Total Papers Scanned:         {len(queue)}")
    print(f"Papers with >= 1 Formula:     {papers_with_concrete} ({(papers_with_concrete/max(1, len(queue)))*100:.1f}%)")
    print("-" * 80)
    print(f"Total Concrete Formulas:      {total_concrete}")
    print(f"Total Symbolic/Parametric:    {total_symbolic}")
    print("=" * 80)
    
    print("\nTOP 20 MOST PROMISING PAPERS:")
    print(f"{'Concrete':<9} | {'Symbolic':<9} | {'Source':<12} | {'Paper ID':<15} | {'Title'}")
    print("-" * 120)
    
    # Sort by highest concrete formulas, then symbolic
    top_papers.sort(key=lambda x: (-x[0], -x[1]))
    
    for c, s, pid, title, status in top_papers[:20]:
        src_label = "LaTeX" if "latex" in status else "PDF"
        short_title = title[:60] + "..." if len(title) > 60 else title
        print(f"{c:<9} | {s:<9} | {src_label:<12} | {pid:<15} | {short_title}")
    print("=" * 120)
    print("\nNote: These are regex-based estimates intended to help rank papers for rigorous extraction.")
    print("Formula counts have been saved to 'formula_estimates' in data/corpus.json.")

if __name__ == "__main__":
    main()