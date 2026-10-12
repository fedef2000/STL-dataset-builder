"""
Step 5 (in progress): asks a model, through OpenRouter, for the requirement, domain and variables of the formulas of
one paper, and prints the answers with what they cost. Nothing is stored yet: this is for trying a model on a paper.

    python scripts/05_extract_requirements.py --paper W3080701220 --model google/gemini-3.8-flash
    python scripts/05_extract_requirements.py --paper W3080701220 --model anthropic/claude-sonnet-5.5 --reasoning medium
    python scripts/05_extract_requirements.py --paper W3080701220 --dry-run      # print the prompts, call nothing
"""
import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import RAW_LATEX_DIR
from src.storage import CorpusStore
from src.extraction.context import build_paper_context
from src.extraction.extractor import REASONING_LEVELS, ExtractionError, build_messages, extract_region

sys.stdout.reconfigure(encoding="utf-8")
WIDTH = 100


def print_region_result(region, result) -> None:
    by_id = {x.id: x for x in result.extractions}
    for formula in region.formulas:
        x = by_id.get(formula.id)
        print(f"\n{formula.id} | line {formula.line}")
        if not x:
            print("   NOT ANSWERED")
            continue
        print(f"   Formula:     {x.formula}")
        if not x.requirements:
            print("   Requirement: (none stated)")
        elif len(x.requirements) == 1:
            print(f"   Requirement: [{x.requirements[0]['kind']}] {x.requirements[0]['text']}")
        else:
            print(f"   Requirement, stated {len(x.requirements)} times:")
            for n, passage in enumerate(x.requirements, 1):
                print(f"      {n}. [{passage['kind']}] {passage['text']}")
        print(f"   Domain:      {x.domain}")
        print("   Variables:" + ("" if x.variables else "   (none)"))
        for symbol, meaning in x.variables.items():
            print(f"      {symbol}: {meaning}")
        for problem in x.problems:
            print(f"   PROBLEM: {problem}")
    for problem in result.problems:
        print(f"\nPROBLEM: {problem}")
    for note in result.notes:
        print(f"\nNOTE: {note}")
    print(f"\n{result.seconds:.1f} s | {result.input_tokens:,} input tokens | {result.output_tokens:,} output tokens"
          f" (of which {result.reasoning_tokens:,} reasoning) | ${result.cost:.5f}")


def main():
    parser = argparse.ArgumentParser(description="Step 5 (in progress): try the extraction on one paper.")
    parser.add_argument("--paper", required=True, help="Paper ID, e.g. W3080701220. The paper must be held as LaTeX.")
    parser.add_argument("--model", help="OpenRouter model ID, e.g. google/gemini-3.8-flash.")
    parser.add_argument("--reasoning", choices=REASONING_LEVELS, default="off", help="How much the model reasons before answering (default off).")
    parser.add_argument("--region", type=int, help="Only this region of the paper (1 = the first).")
    parser.add_argument("--dry-run", action="store_true", help="Print the prompts that would be sent and exit. No model is called, no key is needed.")
    args = parser.parse_args()
    if not args.dry_run and not args.model:
        parser.error("--model is required (or use --dry-run)")

    paper = CorpusStore().papers.get(args.paper)
    if not paper:
        sys.exit(f"{args.paper} is not in the corpus")
    if paper.get("local_files", {}).get("status") != "downloaded_latex":
        sys.exit(f"{args.paper} is not held as LaTeX (status: {paper.get('local_files', {}).get('status')})")
    context = build_paper_context(args.paper, paper.get("title"), RAW_LATEX_DIR / args.paper)
    if not context.regions:
        sys.exit(f"{args.paper} has no concrete formula to extract")
    numbered = list(enumerate(context.regions, 1))
    if args.region:
        if not 1 <= args.region <= len(numbered):
            sys.exit(f"{args.paper} has regions 1 to {len(numbered)}")
        numbered = [numbered[args.region - 1]]

    print("=" * WIDTH)
    print(f"{args.paper} | {context.title}")
    print(f"{len(context.regions)} regions | {len(context.formulas)} formulas"
          + ("" if args.dry_run else f" | model {args.model} | reasoning {args.reasoning}"))

    totals = dict(seconds=0.0, input=0, output=0, cost=0.0, answered=0, with_requirement=0, problems=0, asked=0)
    for n, region in numbered:
        ids = f"{region.formulas[0].id}-{region.formulas[-1].id}" if len(region.formulas) > 1 else region.formulas[0].id
        print("\n" + "=" * WIDTH)
        print(f"REGION {n}/{len(context.regions)} | {region.file} L{region.line_start}-{region.line_end} | {ids}")
        print("-" * WIDTH)
        if args.dry_run:
            for message in build_messages(context, region):
                print(f"[{message['role']}]\n{message['content']}\n")
            continue
        totals["asked"] += len(region.formulas)
        try:
            result = extract_region(context, region, args.model, args.reasoning)
        except ExtractionError as exc:
            print(f"FAILED: {exc}")
            totals["problems"] += 1
            continue
        print_region_result(region, result)
        totals["seconds"] += result.seconds
        totals["input"] += result.input_tokens
        totals["output"] += result.output_tokens
        totals["cost"] += result.cost
        totals["answered"] += len(result.extractions)
        totals["with_requirement"] += sum(1 for x in result.extractions if x.requirements)
        totals["problems"] += len(result.problems) + sum(len(x.problems) for x in result.extractions)

    if not args.dry_run:
        print("\n" + "=" * WIDTH)
        print(f"TOTAL | {totals['answered']} of {totals['asked']} formulas answered | {totals['with_requirement']} with a requirement"
              f" | {totals['problems']} problems")
        print(f"      | {totals['seconds']:.1f} s | {totals['input']:,} input tokens | {totals['output']:,} output tokens | ${totals['cost']:.5f}")
        print("=" * WIDTH)


if __name__ == "__main__":
    main()
