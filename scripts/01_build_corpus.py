import argparse
from pathlib import Path
import sys

# Ensure project root is on sys.path when running from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DEFAULT_KEYWORDS, SEED_DOIS
from src.discovery.keyword_search import search_arxiv_by_keywords
from src.discovery.openalex_client import (
    fetch_citing_works,
    resolve_dois_to_work_ids,
    search_openalex_by_keywords,
)
from src.storage import CorpusStore


def main():
    parser = argparse.ArgumentParser(
        description="Step 1: Build and expand the STL paper corpus (1-hop, 2-hop citations, and keywords)."
    )
    parser.add_argument(
        "--mode",
        choices=["citations", "keywords", "all"],
        default="citations",
        help="Discovery mode: 'citations' (1-hop or 2-hop), 'keywords' (OpenAlex + arXiv), or 'all'.",
    )
    parser.add_argument(
        "--hops",
        type=int,
        choices=[1, 2],
        default=1,
        help="Citation hop depth: 1 = papers citing the 4 seeds; 2 = papers citing Hop-1 papers.",
    )
    parser.add_argument(
        "--min-hop1-citations",
        type=int,
        default=5,
        help="When --hops 2 is used, only expand Hop-1 papers that have at least this many citations (default: 5).",
    )
    parser.add_argument(
        "--hop2-require-stl-text",
        action="store_true",
        default=True,
        help="When --hops 2 is used, require Hop-2 papers to mention 'Signal Temporal Logic' or 'STL' (prevents topic drift).",
    )
    parser.add_argument(
        "--keywords",
        nargs="+",
        default=DEFAULT_KEYWORDS,
        help="Custom list of keywords for --mode keywords.",
    )
    args = parser.parse_args()

    store = CorpusStore()
    initial_count = len(store.papers)
    print(f"Loaded existing corpus with {initial_count} unique papers.")

    # -------------------------------------------------------------------------
    # MODE A: CITATION GRAPH CRAWLING (HOP 1 & HOP 2)
    # -------------------------------------------------------------------------
    if args.mode in ("citations", "all"):
        print("\n=== STEP 1A: Resolving Hop-0 Foundational STL Seeds ===")
        seed_ids = resolve_dois_to_work_ids(SEED_DOIS)

        # Check if Hop 1 is already populated
        hop1_ids = [
            pid
            for pid, p in store.papers.items()
            if p.get("discovery", {}).get("hop_distance") == 1
            and pid.startswith("W")
        ]

        # Check if Hop 1 is missing OR if migrated Hop-1 papers are missing cited_by_count
        hop1_has_citations = any(
            store.papers[pid].get("cited_by_count", 0) > 0 for pid in hop1_ids
        )

        if not hop1_ids or args.hops == 1 or not hop1_has_citations:
            print("\n=== Fetching/Refreshing Hop-1 Papers (Citing Foundational Seeds) ===")
            added_h1 = fetch_citing_works(seed_ids, store, hop=1)
            print(f"Hop-1 sync complete: {added_h1} new papers added (citation counts updated).")
            hop1_ids = [
                pid
                for pid, p in store.papers.items()
                if p.get("discovery", {}).get("hop_distance") == 1
                and pid.startswith("W")
            ]

        if args.hops == 2:
            # Filter Hop-1 parents to those that actually have citations
            eligible_hop1 = [
                pid
                for pid in hop1_ids
                if store.papers[pid].get("cited_by_count", 0)
                >= args.min_hop1_citations
            ]
            print(
                f"\n=== Fetching Hop-2 Papers (Citing {len(eligible_hop1)} Hop-1 papers "
                f"with >= {args.min_hop1_citations} citations) ==="
            )
            # Prevent topic drift on Hop 2 by filtering for temporal logic relevance
            extra_filter = (
                'default.search:"Signal Temporal Logic" OR "Metric Temporal Logic"'
                if args.hop2_require_stl_text
                else None
            )
            added_h2 = fetch_citing_works(
                eligible_hop1,
                store,
                hop=2,
                require_stl_relevance=args.hop2_require_stl_text,
            )
            print(f"Hop-2 complete: {added_h2} new papers added.")

    # -------------------------------------------------------------------------
    # MODE B: KEYWORD SEARCH (DIRECT ARXIV + OPENALEX)
    # -------------------------------------------------------------------------
    if args.mode in ("keywords", "all"):
        print("\n=== STEP 1B: Keyword Discovery (Direct arXiv + OpenAlex) ===")
        added_arxiv = search_arxiv_by_keywords(args.keywords, store)
        added_oa = search_openalex_by_keywords(args.keywords, store)
        print(
            f"Keyword discovery complete: +{added_arxiv} from arXiv, +{added_oa} from OpenAlex."
        )

    store.save()
    final_count = len(store.papers)
    print("\n" + "=" * 68)
    print(
        f"CORPUS BUILD COMPLETE | Initial: {initial_count} -> Final: {final_count} (+{final_count - initial_count} new)"
    )
    print("=" * 68)


if __name__ == "__main__":
    main()