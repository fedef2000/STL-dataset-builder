import argparse
from collections import Counter
from pathlib import Path
import sys

# Ensure project root is on sys.path when running from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DEFAULT_KEYWORDS, SEED_DOIS
from src.discovery.enrichment import SERVICES, enrich_corpus, needs_lookup
from src.discovery.keyword_search import search_arxiv_by_keywords
from src.discovery.openalex_client import (
    fetch_citing_works,
    resolve_dois_to_work_ids,
    search_openalex_by_keywords,
)
from src.storage import CorpusStore


def print_corpus_stats(store: CorpusStore) -> None:
    papers = list(store.papers.values())
    total = max(1, len(papers))

    def row(count: int, label: str) -> None:
        print(f"{count:>5} | {label} ({count / total * 100:.1f}%)")

    hops = Counter(p.get("discovery", {}).get("hop_distance") for p in papers)
    methods = Counter(m for p in papers for m in p.get("discovery", {}).get("methods", []))
    by_citation = sum(1 for p in papers if any(m.startswith("citation_") for m in p.get("discovery", {}).get("methods", [])))
    by_keyword = sum(1 for p in papers if any("_kw:" in m for m in p.get("discovery", {}).get("methods", [])))
    hop1_expanded = sum(1 for p in papers if p.get("discovery", {}).get("expanded_hop_2"))

    print("\n" + "=" * 68)
    print("                     CORPUS DISCOVERY STATS")
    print("=" * 68)
    print(f"{len(papers):>5} | Total unique papers")
    print("-" * 68)
    print("By citation distance from the seed papers:")
    row(hops.get(1, 0), "Hop 1 (cite a seed paper)")
    row(hops.get(2, 0), "Hop 2 (cite a Hop-1 paper)")
    row(hops.get(None, 0), "Found by keyword only")
    print(f"{hop1_expanded:>5} | Hop-1 papers already expanded to Hop 2")
    print("-" * 68)
    print("By discovery method (a paper can be found by several):")
    row(by_citation, "Citation crawl")
    row(by_keyword, "Keyword search")
    row(sum(1 for p in papers if len(p.get("discovery", {}).get("methods", [])) > 1), "Found by more than one method")
    for method, count in methods.most_common():
        print(f"{count:>5} |     {method}")
    print("-" * 68)
    print("Metadata:")
    row(sum(1 for p in papers if p.get("is_oa")), "Open access according to OpenAlex")
    row(sum(1 for p in papers if p.get("arxiv_id")), "With an arXiv ID")
    row(sum(1 for p in papers if p.get("doi")), "With a DOI")
    print("-" * 68)
    print("Enrichment lookups (--mode enrich):")
    print(f"{'found':>9} {'not found':>10} {'no answer':>10} {'still to ask':>13} | Service")
    for service in SERVICES:
        answers = Counter((p.get("lookups") or {}).get(service, {}).get("status") for p in papers)
        to_ask = sum(1 for p in papers if needs_lookup(p, service))
        print(f"{answers['found']:>9} {answers['not_found']:>10} {answers['no_answer']:>10} {to_ask:>13} | {service}")
    print("'still to ask' counts the papers the next enrichment run will ask about, including those with no answer.")
    print("=" * 68)


def main():
    parser = argparse.ArgumentParser(
        description="Step 1: Build and expand the STL paper corpus (1-hop, 2-hop citations, keywords), and enrich it with the links other services know."
    )
    parser.add_argument(
        "--mode",
        choices=["citations", "keywords", "enrich", "all"],
        default="citations",
        help="'citations' (1-hop or 2-hop crawl), 'keywords' (OpenAlex + arXiv search), 'enrich' (ask Semantic Scholar, "
        "the arXiv title search and HAL for missing arXiv IDs and PDF links), or 'all' (the three in that order).",
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
        action=argparse.BooleanOptionalAction,
        default=True,
        help="When --hops 2 is used, keep only Hop-2 papers whose title/abstract matches the local STL relevance terms (prevents topic drift). Use --no-hop2-require-stl-text to disable.",
    )
    parser.add_argument(
        "--keywords",
        nargs="+",
        default=DEFAULT_KEYWORDS,
        help="Custom list of keywords for --mode keywords.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="With --mode enrich: ask each service about at most this many papers (for testing).",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print the discovery statistics of the existing corpus and exit, without querying any API.",
    )
    parser.add_argument(
        "--merge-duplicates",
        action="store_true",
        help="Merge entries of the existing corpus that share an arXiv ID or a DOI (deleting the duplicate downloads) and exit.",
    )
    args = parser.parse_args()

    store = CorpusStore()
    if args.merge_duplicates:
        merged = store.merge_duplicates()
        store.save()
        for kept, dropped in merged:
            print(f"  merged {dropped} into {kept}")
        print(f"Merged {len(merged)} duplicate entries. Corpus now has {len(store.papers)} unique papers.")
        return

    if args.stats:
        print_corpus_stats(store)
        return

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

    # -------------------------------------------------------------------------
    # MODE C: ENRICHMENT (SEMANTIC SCHOLAR + ARXIV TITLE SEARCH + HAL)
    # -------------------------------------------------------------------------
    if args.mode in ("enrich", "all"):
        print("\n=== STEP 1C: Enrichment (missing arXiv IDs and PDF links) ===")
        enrich_corpus(store, limit=args.limit)

    store.save()
    final_count = len(store.papers)
    print("\n" + "=" * 68)
    print(
        f"CORPUS BUILD COMPLETE | Initial: {initial_count} -> Final: {final_count} (+{final_count - initial_count} new)"
    )
    print("=" * 68)


if __name__ == "__main__":
    main()