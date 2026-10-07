import argparse
import sys
from pathlib import Path
import logging

# Ensure project root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.storage import CorpusStore
from src.licensing.resolver import resolve_paper_license
from src.licensing.stats import generate_license_report

logging.basicConfig(level=logging.INFO, format="%(message)s")

def main():
    parser = argparse.ArgumentParser(description="Step 3: Audit exact licenses for downloaded papers and print stats.")
    parser.add_argument("--skip-audit", action="store_true", help="Skip scanning files and just print stats from corpus.json.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of papers audited (for testing).")
    args = parser.parse_args()

    store = CorpusStore()
    
    if not args.skip_audit:
        # Gather downloaded papers that need an audit
        queue = [
            pid for pid, p in store.papers.items()
            if p.get("local_files", {}).get("status") in ("downloaded_latex", "downloaded_pdf")
        ]
        
        if args.limit:
            queue = queue[:args.limit]

        logging.info(f"Starting deep license audit on {len(queue)} downloaded papers...")
        
        updated = 0
        for i, pid in enumerate(queue):
            paper = store.papers[pid]
            resolve_paper_license(paper, BASE_DIR)
            updated += 1
            
            # Save every 50 papers and print progress
            if updated % 50 == 0:
                store.save()
                logging.info(f"  ...Audited {updated}/{len(queue)} papers.")
                
        # Final save
        store.save()
        logging.info(f"Audit complete. Updated {updated} paper records in data/corpus.json.\n")
    else:
        logging.info("Skipping deep audit; generating report from existing data/corpus.json...\n")

    # Generate the terminal report
    generate_license_report(store)

if __name__ == "__main__":
    main()