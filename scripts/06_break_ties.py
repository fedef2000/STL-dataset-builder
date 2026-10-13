"""
Step 6: asks a third model about the formulas on whose requirement the two models of step 5 disagree, and reports
which of the two it sides with.

    python scripts/06_break_ties.py                 # ask what is missing, then report
    python scripts/06_break_ties.py --dry-run       # how many calls that would be, and about what they cost
    python scripts/06_break_ties.py --report        # report on the stored answers: no model is called
    python scripts/06_break_ties.py --kinds         # also the formulas the two tag differently (specific / generic)
    python scripts/06_break_ties.py --paper W3080701220     # only this paper, and print its disputed formulas

The third model is not shown the two answers: it is asked the same question as they were, about every region that
holds a disputed formula, and its answer is compared with theirs. Its answers are stored with the others in
data/processed/extractions/answers.jsonl, and data/processed/extractions/formulas.jsonl is written again with, for
each disputed formula, the answer of the third model and its verdict.
"""
import argparse
import collections
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.storage import CorpusStore
from src.extraction.extractor import REASONING_LEVELS
from src.extraction.records import (ANSWERS_FILE, DEFAULT_MODELS, DEFAULT_TIE_BREAKER, DISPUTED, FORMULAS_FILE, SETTLED, VERDICTS,
                                    collect, kind_of, load_contexts, parse_model, write_formulas)
from src.extraction.runs import run_calls

sys.stdout.reconfigure(encoding="utf-8")
WIDTH = 100
# What a call of Claude Sonnet 5.5 cost on the regions of the benchmark: only for the estimate of --dry-run
DOLLARS_PER_CALL = 0.02


def short(label: str) -> str:
    return label.split("/")[-1]


def named(verdict: str, labels: list[str]) -> str:
    """'sides with the first' -> 'sides with gemini-3.8-flash:off'."""
    return verdict.replace("the first", short(labels[0])).replace("the second", short(labels[1]))


def settled_answer(record: dict) -> dict | None:
    """The requirement two of the three models agree on (as the tie-breaker gives it), or None when they do not."""
    tie = record.get("tie_breaker")
    return tie["answer"] if tie and tie["verdict"] in SETTLED else None


def print_report(records: list[dict], calls: dict, labels: list[str], tie_label: str, asked_regions: int) -> None:
    disputed = [r for r in records if r.get("dispute") == "requirement"]
    answered = [r for r in disputed if "tie_breaker" in r]
    print("\n" + "=" * WIDTH)
    print("                              TIE-BREAKER REPORT")
    print("=" * WIDTH)
    print(f"Disagreement between {labels[0]} and {labels[1]}, broken by {tie_label}")
    print(f"{len(disputed):>6,} | formulas whose requirement is disputed, in {len({(r['paper_id'], r['region']) for r in disputed}):,} regions")
    print(f"{len(answered):>6,} | of them answered by the tie-breaker"
          f"   ({len(calls[tie_label]):,} of {asked_regions:,} calls stored, ${sum(c['cost'] for c in calls[tie_label]):.2f})")
    if not answered:
        print("=" * WIDTH)
        return

    print("-" * WIDTH)
    print(f"{'Verdict of the tie-breaker':<38}" + "".join(f"{name:>20}" for name in DISPUTED) + f"{'Total':>10}")
    counts = collections.Counter((r["tie_breaker"]["verdict"], r["requirement_agreement"]) for r in answered)
    for verdict in VERDICTS:
        row = [counts[(verdict, name)] for name in DISPUTED]
        if sum(row):
            print(f"{named(verdict, labels):<38}" + "".join(f"{n:>20,}" for n in row) + f"{sum(row):>10,}")
    print("   Sides with / agrees with both: its requirement is the one that model gives (or both give none).")
    print("   Partly agrees: it shares a passage with one of them, but not all. Agrees with neither: a third answer.")

    settled = [settled_answer(r) for r in answered]
    kinds = collections.Counter(kind_of(a) for a in settled if a is not None)
    print("-" * WIDTH)
    print(f"{sum(kinds.values()):>6,} | disputed formulas settled (two of the three models give the same requirement)")
    print(f"{kinds['specific']:>6,} |    with a specific requirement")
    print(f"{kinds['generic']:>6,} |    with a generic requirement")
    print(f"{kinds['none']:>6,} |    with no requirement")
    print(f"{settled.count(None):>6,} | still open (partly agrees, agrees with neither)")

    for first, second in ((0, 1), (1, 0)):
        alone = [r for r in answered if r["requirement_agreement"] == "one gives none" and r["answers"][labels[first]]["requirements"]
                 and not r["answers"][labels[second]]["requirements"]]
        kept = sum(1 for r in alone if r["tie_breaker"]["answer"]["requirements"])
        if alone:
            print(f"   Of the {len(alone):,} requirements only {short(labels[first])} gave, the tie-breaker also finds one for {kept:,}"
                  f" ({100 * kept / len(alone):.0f}%)")

    by_kind = [r for r in records if r.get("dispute") == "kind"]
    if by_kind:
        seen = [r for r in by_kind if "tie_breaker" in r]
        verdicts = collections.Counter(r["tie_breaker"]["kind"] if r["tie_breaker"]["verdict"] in SETTLED else "other passages" for r in seen)
        print("-" * WIDTH)
        print(f"{len(by_kind):>6,} | formulas with the same passages for both models, tagged specific by one and generic by the other")
        print(f"{len(seen):>6,} | of them answered by the tie-breaker" + ("" if len(seen) == len(by_kind) else "   (--kinds asks about the others)"))
        if seen:
            print(f"          it tags {verdicts['specific']:,} specific and {verdicts['generic']:,} generic, gives none for {verdicts['none']:,},"
                  f" and gives other passages for {verdicts['other passages']:,}")
    print_vote(records)
    print("=" * WIDTH)


def print_vote(records: list[dict]) -> None:
    """The outcome of the vote on each passage, over all the formulas and over the disputed ones."""
    disputed = [r for r in records if r.get("dispute") == "requirement"]
    rows = (("requirement", "specific", "with a requirement: specific"), ("requirement", "generic", "with a requirement: generic"),
            ("requirement", "unclear", "with a requirement: specific or generic, the models are split"),
            ("none", "none", "with no requirement"), ("open", "none", "open: no passage and no 'none' has two votes"))
    print("-" * WIDTH)
    print("Vote on each passage: a passage is kept when at least two models give it, whatever else they give.")
    print(f"{'All formulas':>14}{'Disputed':>10}")
    for outcome, kind, text in rows:
        match = lambda r: r["final"]["outcome"] == outcome and r["final"]["kind"] == kind
        print(f"{sum(1 for r in records if match(r)):>14,}{sum(1 for r in disputed if match(r)):>10,} | {text}")
    kept = [r for r in records if r["final"]["outcome"] == "requirement"]
    print(f"   {len(kept):,} formulas with a requirement, from {len({r['paper_id'] for r in kept}):,} papers,"
          f" with {sum(len(r['final']['requirements']) for r in kept):,} passages")


def print_paper(context, records: list[dict], labels: list[str]) -> None:
    print("\n" + "=" * WIDTH)
    print(f"{context.paper_id} | {context.title}")
    for r in (r for r in records if r["paper_id"] == context.paper_id and "dispute" in r):
        print("-" * WIDTH)
        tie = r.get("tie_breaker")
        print(f"{r['formula_id']} | {r['file']} line {r['line']} | {r['requirement_agreement']}"
              + (f" | disputed kind" if r["dispute"] == "kind" else "") + (f" | {named(tie['verdict'], labels)}" if tie else " | tie-breaker not asked"))
        print(f"     Formula: {' '.join(r['source'].split())[:WIDTH - 14]}")
        answers = dict(r["answers"])
        if tie:
            answers[tie["model"]] = tie["answer"]
        for label, answer in answers.items():
            print(f"  [{label}]")
            if not answer:
                print("     not answered")
            elif not answer["requirements"]:
                print("     Requirement: (none stated)")
            for passage in (answer or {}).get("requirements") or []:
                print(f"     Requirement: <{passage['kind']}> {passage['text']}")


def main():
    parser = argparse.ArgumentParser(description="Step 6: ask a third model about the formulas on which the two models of step 5 disagree.")
    parser.add_argument("--tie-breaker", default=DEFAULT_TIE_BREAKER, metavar="ID[:REASONING]",
                        help=f"The third model, with an optional reasoning level ({', '.join(REASONING_LEVELS)}). Default: {DEFAULT_TIE_BREAKER}.")
    parser.add_argument("--models", nargs=2, default=DEFAULT_MODELS, metavar="ID[:REASONING]",
                        help=f"The two models of step 5 whose answers are compared. Default: {' '.join(DEFAULT_MODELS)}.")
    parser.add_argument("--kinds", action="store_true",
                        help="Also ask about the formulas for which the two give the same passages but tag them differently (specific / generic).")
    parser.add_argument("--paper", action="append", help="Only this paper (repeatable); its disputed formulas are printed.")
    parser.add_argument("--report", action="store_true", help="Report on the stored answers and write formulas.jsonl. No model is called.")
    parser.add_argument("--dry-run", action="store_true", help="Print how many calls would be made and about what they cost, and exit.")
    parser.add_argument("--workers", type=int, default=8, help="Calls made at the same time (default 8).")
    parser.add_argument("--budget", type=float, default=15.0, help="Stop starting new calls once this many dollars are spent in this invocation (default 15).")
    args = parser.parse_args()
    pairs = [parse_model(spec) for spec in args.models]
    tie_breaker = parse_model(args.tie_breaker)
    if tie_breaker in pairs:
        sys.exit("The tie-breaker must be another model than the two it decides between.")
    labels = [f"{model}:{reasoning}" for model, reasoning in pairs]
    tie_label = f"{tie_breaker[0]}:{tie_breaker[1]}"

    store = CorpusStore()
    print("Reading the LaTeX sources...")
    contexts = load_contexts(store, args.paper)
    regions = {(pid, n): (context, region) for pid, context in contexts.items() for n, region in enumerate(context.regions, 1)}

    records, calls = collect(store, contexts, pairs, tie_breaker)
    missing = sum(1 for r in records if r["requirement_agreement"] == "not answered")
    if missing:
        print(f"{missing} formulas lack the answer of one of the two models: run scripts/05_extract_requirements.py first to have them compared.")
    wanted = ("requirement", "kind") if args.kinds else ("requirement",)
    asked = sorted({(r["paper_id"], r["region"]) for r in records if r.get("dispute") in wanted})
    stored = {(row["paper_id"], row["region"]) for row in calls[tie_label]}
    print(f"{len(records):,} formulas | {sum(1 for r in records if r.get('dispute') == 'requirement'):,} with a disputed requirement"
          f" | {sum(1 for r in records if r.get('dispute') == 'kind'):,} with a disputed kind"
          f" | {len(asked):,} regions to ask the tie-breaker about{' (kinds included)' if args.kinds else ''}")

    if args.dry_run:
        todo = [key for key in asked if key not in stored]
        print(f"{len(todo):,} calls to {tie_label} would be made ({len(asked) - len(todo):,} are already stored):"
              f" about ${DOLLARS_PER_CALL * len(todo):.0f} at ${DOLLARS_PER_CALL:.2f} a call.")
        return

    if not args.report:
        print(f"Tie-breaker: {tie_breaker[0]} (reasoning {tie_breaker[1]})")
        run_calls([(*tie_breaker, 1, pid, n) for pid, n in asked], regions, ANSWERS_FILE, args.workers, args.budget)
        records, calls = collect(store, contexts, pairs, tie_breaker)

    if not args.paper:
        # A selection of papers must not overwrite the file of the whole corpus
        write_formulas(records)
    for pid in args.paper or []:
        if pid in contexts:
            print_paper(contexts[pid], records, labels)
    print_report(records, calls, labels, tie_label, len(asked))
    if args.paper:
        print("formulas.jsonl is not written for a selection of papers: only by a run or a report over the whole corpus.")
    else:
        print(f"One record per formula, with the verdict of the tie-breaker on the disputed ones: {FORMULAS_FILE}")


if __name__ == "__main__":
    main()
