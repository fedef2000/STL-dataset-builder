"""
Step 5: asks two models, through OpenRouter, for the requirement, domain and variables of every concrete formula of
the papers held as LaTeX, keeps every answer, and reports where the two models agree.

    python scripts/05_extract_requirements.py                       # extract what is missing, then report
    python scripts/05_extract_requirements.py --report              # report on the stored answers: no model is called
    python scripts/05_extract_requirements.py --paper W3080701220   # only this paper, and print its answers
    python scripts/05_extract_requirements.py --limit 20            # only the first 20 papers (a trial)
    python scripts/05_extract_requirements.py --paper W3080701220 --dry-run     # print the prompts, call nothing

Answers are stored in data/processed/extractions/answers.jsonl as they arrive, so an interrupted run continues where
it stopped. The report also writes data/processed/extractions/formulas.jsonl: one record per formula, with the answer
of each model and how far the two agree on its requirement.
"""
import argparse
import collections
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.storage import CorpusStore
from src.extraction.extractor import REASONING_LEVELS, build_messages
from src.extraction.records import (AGREEMENTS, ANSWERS_FILE, DEFAULT_MODELS, DEFAULT_TIE_BREAKER, FORMULAS_FILE, SETTLED, collect,
                                    kind_of, load_contexts, parse_model, write_formulas)
from src.extraction.runs import run_calls

sys.stdout.reconfigure(encoding="utf-8")
WIDTH = 100


def print_report(contexts: dict, records: list[dict], calls: dict, pairs: list[tuple[str, str]]) -> None:
    labels = list(calls)[:len(pairs)]
    regions = sum(len(c.regions) for c in contexts.values())
    print("\n" + "=" * WIDTH)
    print("                         REQUIREMENT EXTRACTION REPORT")
    print("=" * WIDTH)
    print(f"{len(contexts):>6,} | papers   {regions:>6,} | regions (calls per model)   {len(records):>6,} | concrete formulas")
    print("-" * WIDTH)
    print(f"{'Model':<34}{'Regions done':>13}{'Answered':>10}{'Specific':>10}{'Generic':>9}{'None':>7}{'Flagged':>9}{'Cost $':>9}")
    for label in labels:
        answers = [r["answers"][label] for r in records if r["answers"][label]]
        kinds = collections.Counter(kind_of(a) for a in answers)
        print(f"{label:<34}{len(calls[label]):>13,}{len(answers):>10,}{kinds['specific']:>10,}{kinds['generic']:>9,}{kinds['none']:>7,}"
              f"{sum(1 for a in answers if a['problems']):>9,}{sum(c['cost'] for c in calls[label]):>9.2f}")
    print("   Specific / Generic / None: formulas whose requirement carries the particulars of the formula, only says what it")
    print("   is for, or is not stated. Flagged: answers that failed a check (e.g. a passage that is not a copy of the source).")
    flags = {label: collections.Counter(re.sub(r" \(passage \d+\)|: .*", "", problem) for r in records if r["answers"][label]
                                        for problem in set(r["answers"][label]["problems"])) for label in labels}
    kinds_of_flag = sorted({kind for counts in flags.values() for kind in counts}, key=lambda kind: -sum(c[kind] for c in flags.values()))
    if kinds_of_flag:
        print("-" * WIDTH)
        print("Formulas flagged, by check (the checks are run again on the stored answers each time):")
        for kind in kinds_of_flag:
            print(f"   {kind:<58}" + "".join(f"{flags[label][kind]:>7,}  {label.split('/')[-1]:<22}" for label in labels))
    if len(labels) > 1:
        both = [r for r in records if all(r["answers"][label] for label in labels[:2])]
        counts = collections.Counter(r["requirement_agreement"] for r in records)
        print("-" * WIDTH)
        print(f"Agreement on the requirement between {labels[0]} and {labels[1]}:")
        for name in AGREEMENTS:
            if counts[name]:
                print(f"{counts[name]:>6,} | {name:<20} {100 * counts[name] / len(records):5.1f}%")
        agreed = [r for r in records if r["requirement_agreement"] == "same passages"]
        if agreed:
            kinds = collections.Counter(kind_of(r["answers"][labels[0]]) if kind_of(r["answers"][labels[0]]) == kind_of(r["answers"][labels[1]])
                                        else "kinds differ" for r in agreed)
            print(f"   Of the {len(agreed):,} formulas with the same passages: {kinds['specific']:,} specific for both, {kinds['generic']:,} generic for both,"
                  f" {kinds['kinds differ']:,} tagged differently")
        if both:
            print(f"Same domain for {sum(1 for r in both if r['domain_agreement']):,} of the {len(both):,} formulas both models answered"
                  f" ({100 * sum(1 for r in both if r['domain_agreement']) / len(both):.1f}%)")
        disputed = sum(counts[name] for name in ("partly the same", "different passages", "one gives none"))
        print(f"{disputed:,} formulas would go to a tie-breaker (partly the same, different passages, one gives none).")
        broken = [r for r in records if r.get("dispute") == "requirement" and "tie_breaker" in r]
        if broken:
            print(f"   {len(broken):,} of them have the answer of the tie-breaker ({broken[0]['tie_breaker']['model']}), which settles"
                  f" {sum(1 for r in broken if r['tie_breaker']['verdict'] in SETTLED):,}: see scripts/06_break_ties.py --report")
    print("=" * WIDTH)


def print_paper(context, records: list[dict]) -> None:
    print("\n" + "=" * WIDTH)
    print(f"{context.paper_id} | {context.title}")
    for r in (r for r in records if r["paper_id"] == context.paper_id):
        print("-" * WIDTH)
        print(f"{r['formula_id']} | {r['file']} line {r['line']}" + (f" | requirement: {r['requirement_agreement']}" if r["requirement_agreement"] else ""))
        for label, answer in r["answers"].items():
            print(f"  [{label}]")
            if not answer:
                print("     not answered")
                continue
            print(f"     Formula:     {answer['formula']}")
            if not answer["requirements"]:
                print("     Requirement: (none stated)")
            for passage in answer["requirements"]:
                print(f"     Requirement: <{passage['kind']}> {passage['text']}")
            print(f"     Domain:      {answer['domain']}")
            for symbol, meaning in answer["variables"].items():
                print(f"        {symbol}: {meaning}")
            for problem in answer["problems"]:
                print(f"     PROBLEM: {problem}")


def main():
    parser = argparse.ArgumentParser(description="Step 5: extract the requirements of the formulas with two models and compare them.")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS, metavar="ID[:REASONING]",
                        help=f"OpenRouter model IDs, each with an optional reasoning level ({', '.join(REASONING_LEVELS)}). Default: {' '.join(DEFAULT_MODELS)}. The report compares the first two.")
    parser.add_argument("--paper", action="append", help="Only this paper (repeatable); its answers are printed. The paper must be held as LaTeX.")
    parser.add_argument("--limit", type=int, help="Only the first N papers.")
    parser.add_argument("--report", action="store_true", help="Report on the stored answers and write formulas.jsonl. No model is called.")
    parser.add_argument("--dry-run", action="store_true", help="With --paper: print the prompts that would be sent and exit.")
    parser.add_argument("--workers", type=int, default=8, help="Calls made at the same time (default 8).")
    parser.add_argument("--budget", type=float, default=20.0, help="Stop starting new calls once this many dollars are spent in this invocation (default 20).")
    args = parser.parse_args()
    pairs = [parse_model(spec) for spec in args.models]

    store = CorpusStore()
    print("Reading the LaTeX sources...")
    contexts = load_contexts(store, args.paper, args.limit)
    regions = {(pid, n): (context, region) for pid, context in contexts.items() for n, region in enumerate(context.regions, 1)}
    print(f"{len(contexts)} papers with concrete formulas | {len(regions)} regions | {sum(len(c.formulas) for c in contexts.values())} formulas")

    if args.dry_run:
        for (pid, n), (context, region) in regions.items():
            print("\n" + "=" * WIDTH + f"\n{pid} | REGION {n}/{len(context.regions)} | {region.file} L{region.line_start}-{region.line_end}\n" + "-" * WIDTH)
            for message in build_messages(context, region):
                print(f"[{message['role']}]\n{message['content']}\n")
        return

    if not args.report:
        print(f"Models: {', '.join(f'{model} (reasoning {reasoning})' for model, reasoning in pairs)}")
        tasks = [(model, reasoning, 1, pid, n) for model, reasoning in pairs for (pid, n) in regions]
        run_calls(tasks, regions, ANSWERS_FILE, args.workers, args.budget)

    # The answers of the tie-breaker (step 6), where there are any, stay in the records
    records, calls = collect(store, contexts, pairs, parse_model(DEFAULT_TIE_BREAKER))
    if not args.paper and not args.limit:
        # A partial selection must not overwrite the file of the whole corpus
        write_formulas(records)
    for pid in args.paper or []:
        if pid in contexts:
            print_paper(contexts[pid], records)
    print_report(contexts, records, calls, pairs)
    if args.paper or args.limit:
        print("formulas.jsonl is not written for a selection of papers: only by a run or a report over the whole corpus.")
    else:
        print(f"One record per formula, with the answer of each model: {FORMULAS_FILE}")


if __name__ == "__main__":
    main()
