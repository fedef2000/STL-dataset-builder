"""
Checks the context builder (src/extraction/context.py), which decides what the extraction model reads.

    python scripts/eval/check_contexts.py                  # coverage of the evaluation set
    python scripts/eval/check_contexts.py --entry EVAL_56  # print the region the model reads for one entry of the set
    python scripts/eval/check_contexts.py --paper W123     # print every region of one paper as the model sees them
    python scripts/eval/check_contexts.py --corpus         # size of the job over every LaTeX paper of the corpus

The coverage report answers, for every entry of the evaluation set: is its formula marked in a region, and is its
requirement inside that region? An entry that fails here cannot be extracted, whatever the model.
--before, --after, --max-formulas and --symbolic change the builder's settings in all three modes.
"""
import argparse, json, re, sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo))
from src.extraction import context as c

sys.stdout.reconfigure(encoding="utf-8")
CHARS_PER_TOKEN = 3.3  # rough figure for LaTeX source
nows = lambda s: re.sub(r"\s+", "", s)
tokens = lambda chars: chars / CHARS_PER_TOKEN


def find_ignoring_spaces(text: str, needle: str) -> tuple[int, int] | None:
    """Span of the first occurrence of `needle` in `text`, comparing both without whitespace."""
    positions = [i for i, ch in enumerate(text) if not ch.isspace()]
    at = nows(text).find(nows(needle))
    if at < 0 or not nows(needle):
        return None
    return positions[at], positions[at + len(nows(needle)) - 1] + 1


def quantile(values: list, q: float):
    return sorted(values)[int(q * (len(values) - 1))]


def coverage(corpus: dict, options: dict) -> None:
    entries = json.load(open(repo / "data/processed/eval_set.json", encoding="utf-8"))
    contexts, rows = {}, []
    for x in entries:
        pid = x["paper_id"]
        if pid not in contexts:
            contexts[pid] = c.build_paper_context(pid, corpus[pid].get("title"), repo / "data/raw/latex" / pid, **options)
        # The region where the labelled formula overlaps a marked formula; failing that, a region that just holds it
        marked = seen = None
        for region in contexts[pid].regions:
            span = find_ignoring_spaces(region.text, x["formula"])
            if not span:
                continue
            seen = seen or region
            hit = next((f for f in region.formulas if f.start < span[1] and span[0] < f.end), None)
            if hit:
                marked = (region, hit)
                break
        has_req = bool(x["requirements"])
        req_inside = bool(marked and has_req and all(find_ignoring_spaces(marked[0].text, r["text"]) for r in x["requirements"]))
        rows.append((x, marked, seen, has_req, req_inside))

    positives = [r for r in rows if r[3]]
    print("=" * 78)
    print("          CONTEXT BUILDER: COVERAGE OF THE EVALUATION SET")
    print("=" * 78)
    print(f"{len(rows):>4} | entries, from {len(contexts)} papers")
    print(f"{sum(1 for r in rows if r[1]):>4} | formula marked in a region")
    print(f"{sum(1 for r in rows if not r[1] and r[2]):>4} | formula inside a region but not marked (the estimator does not count it)")
    print(f"{sum(1 for r in rows if not r[2]):>4} | formula in no region")
    print("-" * 78)
    print(f"{len(positives):>4} | entries with a requirement")
    print(f"{sum(1 for r in positives if r[4]):>4} | requirement inside the region of its formula (every passage, when it is stated more than once)")
    print(f"{sum(1 for r in positives if r[1] and not r[4]):>4} | formula marked, requirement outside the region")
    print("-" * 78)
    regions = [region for ctx in contexts.values() for region in ctx.regions]
    sizes = [tokens(len(region.text)) for region in regions]
    if regions:
        print(f"Regions of these papers: {len(regions)} | tokens per region (rough): median {quantile(sizes, .5):,.0f}, largest {max(sizes):,.0f}")
    print("=" * 78)
    failed = [r for r in rows if not r[1] or (r[3] and not r[4])]
    for x, marked, seen, has_req, req_inside in failed:
        why = "requirement outside the region" if marked else "formula not marked" if seen else "formula in no region"
        print(f"{x['id']} | {x['paper_id']:<12} | {x['source_file']} L{x['line']} | {why}")
        print(f"         formula: {x['formula'][:100]}")


def show_paper(corpus: dict, pid: str, options: dict, full: bool) -> None:
    ctx = c.build_paper_context(pid, corpus[pid].get("title"), repo / "data/raw/latex" / pid, **options)
    print("=" * 100)
    print(f"{pid} | {ctx.title}")
    print(f"{len(ctx.regions)} regions | {len(ctx.formulas)} formulas | about {tokens(sum(len(r.text) for r in ctx.regions)):,.0f} tokens of region text")
    print(f"Abstract: {ctx.abstract or '(not found)'}")
    for n, region in enumerate(ctx.regions, 1):
        ids = f"{region.formulas[0].id}-{region.formulas[-1].id}" if len(region.formulas) > 1 else region.formulas[0].id
        print("\n" + "=" * 100)
        print(f"REGION {n}/{len(ctx.regions)} | {region.file} L{region.line_start}-{region.line_end} | {ids} | about {tokens(len(region.text)):,.0f} tokens")
        print(f"Section: {' > '.join(region.section) or '(none)'}")
        print("-" * 100)
        text = region.marked_text()
        if not full and len(text) > 2400:
            text = text[:1200] + f"\n\n   [... {len(text) - 2400:,} characters not shown, use --full ...]\n\n" + text[-1200:]
        print(text)


def show_entry(entry_id: str) -> None:
    """Prints the one region the model reads for an entry of the evaluation set, with the labelled formula pointed out."""
    from benchmark import load_tasks  # imported here: benchmark.py imports this module
    placed, regions = load_tasks()
    match = next(((entry, where) for entry, where in placed if entry["id"] == entry_id.upper()), None)
    if not match:
        sys.exit(f"{entry_id} is not in the evaluation set")
    entry, where = match
    if not where:
        sys.exit(f"The formula of {entry_id} is not marked in any region")
    paper, region = regions[(where[0], where[1])]
    others = [e["id"] for e, w in placed if w and w[:2] == where[:2] and e["id"] != entry["id"]]
    print("=" * 100)
    print(f"{entry['id']} | {entry['paper_id']} | {paper.title}")
    print(f"Region {where[1]} of {len(paper.regions)} | {region.file} L{region.line_start}-{region.line_end} | about {tokens(len(region.text)):,.0f} tokens")
    print(f"The labelled formula is {where[2]}, pointed out below with >>> and <<<.")
    print(f"This region marks {len(region.formulas)} formulas ({region.formulas[0].id}-{region.formulas[-1].id}): every concrete formula step 4 found here,"
          " not only the labelled one." + (f" Also labelled in this region: {', '.join(others)}." if others else ""))
    print("-" * 100)
    if entry["requirements"]:
        for n, passage in enumerate(entry["requirements"], 1):
            print(f"Label, requirement{f' {n}' if len(entry['requirements']) > 1 else ''} [{passage['kind']}]: {passage['text']}")
    else:
        print(f"Label: no requirement. Why: {entry['note']}")
    print("=" * 100)
    text = region.marked_text()
    opening, closing = c.MARK_OPEN.format(id=where[2]), c.MARK_CLOSE.format(id=where[2])
    print(text.replace(opening, "\n>>> " + opening).replace(closing, closing + " <<<\n"))


def corpus_totals(corpus: dict, options: dict) -> None:
    kinds = options.get("kinds", ("concrete",))
    papers = [
        (pid, p) for pid, p in corpus.items()
        if (p.get("local_files") or {}).get("status") == "downloaded_latex"
        and any((p.get("formula_estimates") or {}).get(f"formulas_{kind}") for kind in kinds)
    ]
    contexts = []
    for n, (pid, p) in enumerate(papers, 1):
        contexts.append(c.build_paper_context(pid, p.get("title"), repo / "data/raw/latex" / pid, **options))
        if n % 100 == 0:
            print(f"   {n}/{len(papers)} papers read", file=sys.stderr)
    contexts = [ctx for ctx in contexts if ctx.regions]
    regions = [region for ctx in contexts for region in ctx.regions]
    sizes = [tokens(len(region.text)) for region in regions]
    per_region = [len(region.formulas) for region in regions]
    header = sum(tokens(len(ctx.title) + len(ctx.abstract)) * len(ctx.regions) for ctx in contexts)
    print("=" * 78)
    print("          CONTEXT BUILDER: THE WHOLE CORPUS (LaTeX papers)")
    print("=" * 78)
    print(f"{len(contexts):>7,} | papers with at least one region")
    print(f"{sum(per_region):>7,} | formulas marked ({', '.join(kinds)})")
    print(f"{len(regions):>7,} | regions = calls to the model")
    print(f"{sum(1 for ctx in contexts if not ctx.abstract):>7,} | papers whose abstract was not found")
    print("-" * 78)
    print(f"Formulas per region: median {quantile(per_region, .5)} | 90% {quantile(per_region, .9)} | largest {max(per_region)}")
    print(f"Tokens per region:   median {quantile(sizes, .5):,.0f} | 90% {quantile(sizes, .9):,.0f} | largest {max(sizes):,.0f}")
    print(f"Input tokens in all: {sum(sizes):,.0f} of region text + {header:,.0f} of title and abstract (rough: {CHARS_PER_TOKEN} characters per token)")
    print("=" * 78)


def main():
    parser = argparse.ArgumentParser(description="Check the context builder of the extraction step.")
    parser.add_argument("--paper", help="Print the regions of this paper as the model sees them.")
    parser.add_argument("--full", action="store_true", help="With --paper: print long regions whole.")
    parser.add_argument("--entry", help="Print the region the model reads for this entry of the evaluation set (e.g. EVAL_56), with the labelled formula pointed out.")
    parser.add_argument("--corpus", action="store_true", help="Report the size of the job over every LaTeX paper.")
    parser.add_argument("--before", type=int, default=c.CONTEXT_BEFORE, help=f"Characters of context before a formula (default {c.CONTEXT_BEFORE}).")
    parser.add_argument("--after", type=int, default=c.CONTEXT_AFTER, help=f"Characters of context after a formula (default {c.CONTEXT_AFTER}).")
    parser.add_argument("--max-formulas", type=int, default=c.MAX_FORMULAS_PER_REGION, help=f"Most formulas marked in one region (default {c.MAX_FORMULAS_PER_REGION}).")
    parser.add_argument("--symbolic", action="store_true", help="Also mark the formulas whose time bounds are all symbolic.")
    args = parser.parse_args()

    options = dict(before=args.before, after=args.after, max_formulas=args.max_formulas,
                   kinds=("concrete", "symbolic") if args.symbolic else ("concrete",))
    if args.entry:
        sys.path.insert(0, str(Path(__file__).parent))
        show_entry(args.entry)
        return
    corpus = json.load(open(repo / "data/corpus.json", encoding="utf-8"))
    if args.paper:
        if args.paper not in corpus:
            sys.exit(f"{args.paper} is not in the corpus")
        show_paper(corpus, args.paper, options, args.full)
    elif args.corpus:
        corpus_totals(corpus, options)
    else:
        coverage(corpus, options)


if __name__ == "__main__":
    main()
