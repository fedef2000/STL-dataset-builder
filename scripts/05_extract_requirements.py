"""
Step 5: asks two models, through OpenRouter, for the requirement, domain and variables of every formula of the papers
held as LaTeX, and with --tie-break asks a third model about the formulas the two disagree on. Every answer is kept,
and the models' answers are put to a vote: a requirement passage is kept when two models give it.

    python scripts/05_extract_requirements.py                       # the two models on every formula, then the summary
    python scripts/05_extract_requirements.py --tie-break           # also the third model, on the disagreements
    python scripts/05_extract_requirements.py --report              # the summary only: no model is called
    python scripts/05_extract_requirements.py --report --concrete   # the report of the concrete formulas (--parametric: of those)
    python scripts/05_extract_requirements.py --report --details    # the report of each kind, with its technical tables
    python scripts/05_extract_requirements.py --dry-run             # how many calls a run would make, and their cost
    python scripts/05_extract_requirements.py --paper W3080701220   # only this paper, and print its answers

Answers are stored in data/processed/extractions/answers.jsonl as they arrive (parametric/answers.jsonl for the
parametric formulas), so an interrupted run continues where it stopped. A run or a report over the whole corpus also
writes formulas.jsonl next to it: one record per formula, with the answer of every model and the outcome of the vote.
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
from src.extraction.records import (AGREED, AGREEMENTS, DEFAULT_MODELS, DEFAULT_TIE_BREAKER, DISPUTED, VERDICTS, collect,
                                    kind_of, load_contexts, parse_model, store_files, write_formulas)
from src.extraction.runs import latest_answers, matches_region, run_calls, unanswered

sys.stdout.reconfigure(encoding="utf-8")
WIDTH = 78


def short(label: str) -> str:
    """'google/gemini-3.8-flash:off' -> 'gemini-3.8-flash (reasoning off)'."""
    model, reasoning = parse_model(label)
    return f"{model.split('/')[-1]} (reasoning {reasoning})"


def named(verdict: str, labels: list[str]) -> str:
    """'sides with the first' -> 'sides with gemini-3.8-flash'."""
    return verdict.replace("the first", parse_model(labels[0])[0].split("/")[-1]).replace("the second", parse_model(labels[1])[0].split("/")[-1])


def tie_regions(records: list[dict]) -> list[tuple[str, int]]:
    """The regions the third model is asked about: those that hold a formula whose requirement or kind is disputed."""
    return sorted({(r["paper_id"], r["region"]) for r in records if r.get("dispute")})


# ---------------------------------------------------------------- the report

def print_report(title: str, contexts: dict, records: list[dict], calls: dict, labels: list[str], tie_label: str,
                 tie_asked: bool) -> None:
    final = collections.Counter((r["final"]["outcome"], r["final"]["kind"]) for r in records)
    with_requirement = [r for r in records if r["final"]["outcome"] == "requirement"]
    print("\n" + "=" * WIDTH)
    print(f"  STEP 5 · {title}")
    print(f"  {len(contexts):,} papers · {len(records):,} formulas")
    print("=" * WIDTH)

    print("RESULT")
    print(f"  {len(with_requirement):>6,}  formulas with a requirement           from {len({r['paper_id'] for r in with_requirement}):,} papers")
    print(f"  {'':>6}  {final[('requirement', 'specific')]:>8,} specific")
    print(f"  {'':>6}  {final[('requirement', 'generic')]:>8,} generic")
    print(f"  {'':>6}  {final[('requirement', 'unclear')]:>8,} specific or generic: the models are split")
    print(f"  {final[('none', 'none')]:>6,}  formulas without a requirement")
    undecided = sum(1 for r in records if r["final"]["outcome"] == "open")
    print(f"  {undecided:>6,}  undecided: " + ("the models disagree" if tie_asked else "the two models disagree (see below)"))

    print("\nHOW EACH FORMULA WAS DECIDED")
    agreement = collections.Counter(r["requirement_agreement"] for r in records)
    agreed = sum(agreement[name] for name in AGREED)
    print(f"  {agreed:>6,}  the two models agree           ({agreement['same passages']:,} requirement · {agreement['both none']:,} none)")
    tie_name = parse_model(tie_label)[0].split("/")[-1]
    for dispute, text in (("requirement", "they disagree"), ("kind", "same passage, kind disputed")):
        disputed = [r for r in records if r.get("dispute") == dispute]
        if not disputed:
            continue
        asked = [r for r in disputed if "tie_breaker" in r]
        if dispute == "requirement":
            decided = sum(1 for r in asked if r["final"]["outcome"] != "open")
        else:
            decided = sum(1 for r in asked if r["final"]["kind"] in ("specific", "generic"))
        line = f"  {len(disputed):>6,}  {text:<30} "
        if asked:
            line += f"→ {tie_name} asked: {decided:,} decided · {len(asked) - decided:,} undecided"
            if len(asked) < len(disputed):
                line += f" · {len(disputed) - len(asked):,} not asked yet"
        else:
            line += "→ run with --tie-break to decide them"
        print(line)
    if agreement["not answered"]:
        print(f"  {agreement['not answered']:>6,}  {'a model has no answer yet':<30} → run without --report to ask for it")

    print("\nCOST")
    total = 0.0
    for label in labels + ([tie_label] if calls.get(tie_label) else []):
        cost = sum(c["cost"] for c in calls[label])
        total += cost
        role = " · tie-break" if label == tie_label else ""
        print(f"  {short(label) + role:<50} {len(calls[label]):>6,} calls  ${cost:>7.2f}")
    print(f"  {'total':<63}${total:>7.2f}")

    flagged = sum(1 for r in records for label in labels if r["answers"].get(label) and r["answers"][label]["problems"]) \
        + sum(1 for r in records if r.get("tie_breaker") and r["tie_breaker"]["answer"]["problems"])
    if flagged:
        print("\nWARNINGS")
        print(f"  {flagged:,} answers failed a check (e.g. a passage not copied from the paper): see --details.")
        print("  A passage the vote keeps is taken from a model that copied it exactly, where one did.")
    print("=" * WIDTH)


def print_details(records: list[dict], calls: dict, labels: list[str], tie_label: str) -> None:
    """The technical tables: answers per model, failed checks, how the two models agree, the verdicts of the third."""
    every = labels + ([tie_label] if calls.get(tie_label) else [])
    answer = lambda r, label: r["answers"].get(label) if label in labels else (r.get("tie_breaker") or {}).get("answer")
    print("\nDETAILS")
    print("-" * WIDTH)
    print("Answers per model (a formula counts once, by the best passage it was given):")
    print(f"  {'model':<44}{'answered':>9}{'specific':>9}{'generic':>8}{'none':>7}")
    for label in every:
        given = [answer(r, label) for r in records if answer(r, label)]
        kinds = collections.Counter(kind_of(a) for a in given)
        print(f"  {short(label):<44}{len(given):>9,}{kinds['specific']:>9,}{kinds['generic']:>8,}{kinds['none']:>7,}")

    print("-" * WIDTH)
    print("Answers that failed a check (run again on the stored answers at every report):")
    flags = {label: collections.Counter(re.sub(r" \(passage \d+\)|: .*", "", problem) for r in records if answer(r, label)
                                        for problem in set(answer(r, label)["problems"])) for label in every}
    checks = sorted({check for counts in flags.values() for check in counts}, key=lambda check: -sum(c[check] for c in flags.values()))
    print(f"  {'check':<52}" + "".join(f"{parse_model(label)[0].split('/')[-1][:10]:>11}" for label in every))
    for check in checks:
        print(f"  {check:<52}" + "".join(f"{flags[label][check]:>11,}" for label in every))

    print("-" * WIDTH)
    print(f"How the two models agree on the requirement:")
    counts = collections.Counter(r["requirement_agreement"] for r in records)
    meaning = {"same passages": "both give the same passages", "both none": "both give none",
               "partly the same": "some passages shared, not all", "different passages": "no passage in common",
               "one gives none": "one gives a requirement, the other none", "not answered": "a model has no answer"}
    for name in AGREEMENTS:
        if counts[name]:
            print(f"  {counts[name]:>6,}  {name:<20} {100 * counts[name] / len(records):5.1f}%   {meaning[name]}")
    both = [r for r in records if r["domain_agreement"] is not None]
    if both:
        print(f"  Same domain for {sum(1 for r in both if r['domain_agreement']):,} of {len(both):,} formulas.")

    answered = [r for r in records if r.get("dispute") == "requirement" and "tie_breaker" in r]
    if answered:
        print("-" * WIDTH)
        print(f"What the third model says about the disputed requirements ({len(answered):,} formulas):")
        print(f"  {'':<34}" + "".join(f"{name:>15}" for name in ("partly same", "different", "one gives none")) + f"{'total':>8}")
        verdicts = collections.Counter((r["tie_breaker"]["verdict"], r["requirement_agreement"]) for r in answered)
        for verdict in VERDICTS:
            row = [verdicts[(verdict, name)] for name in DISPUTED]
            if sum(row):
                print(f"  {named(verdict, labels):<34}" + "".join(f"{n:>15,}" for n in row) + f"{sum(row):>8,}")
        for first, second in ((0, 1), (1, 0)):
            alone = [r for r in answered if r["requirement_agreement"] == "one gives none"
                     and r["answers"][labels[first]]["requirements"] and not r["answers"][labels[second]]["requirements"]]
            kept = sum(1 for r in alone if r["tie_breaker"]["answer"]["requirements"])
            if alone:
                print(f"  Of the {len(alone):,} requirements only {parse_model(labels[first])[0].split('/')[-1]} gave, the third model"
                      f" also finds one for {kept:,} ({100 * kept / len(alone):.0f}%).")
    print("=" * WIDTH)


def print_paper(context, records: list[dict]) -> None:
    print("\n" + "=" * WIDTH)
    print(f"{context.paper_id} | {context.title}")
    for r in (r for r in records if r["paper_id"] == context.paper_id):
        print("-" * WIDTH)
        final = r["final"]
        print(f"{r['formula_id']} | {r['file']} line {r['line']} | result: {final['outcome']}"
              + (f" ({final['kind']})" if final["outcome"] == "requirement" else ""))
        answers = dict(r["answers"])
        if r.get("tie_breaker"):
            answers[r["tie_breaker"]["model"] + " (tie-break)"] = r["tie_breaker"]["answer"]
        for label, answer in answers.items():
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
        for passage in final["requirements"]:
            print(f"  => kept: <{passage['kind']}> {passage['text']}")


# ---------------------------------------------------------------- planning a run

def print_plan(regions: dict, answers_file: Path, pairs: list[tuple[str, str]], tie_breaker: tuple[str, str], records: list[dict],
               tie_break: bool) -> None:
    """--dry-run: the calls a run would make, priced at what the stored calls of each model cost on average."""
    stored = latest_answers(answers_file)
    done = lambda key: key in stored and not stored[key].get("error") and matches_region(stored[key], regions[key[3:]][1]) and not unanswered(stored[key])

    def price(model: str, reasoning: str) -> float | None:
        costs = [row["cost"] for key, row in stored.items() if key[:2] == (model, reasoning) and not row.get("error")]
        return sum(costs) / len(costs) if costs else None

    plan = [(model, reasoning, [key for key in regions if not done((model, reasoning, 1, *key))]) for model, reasoning in pairs]
    if tie_break:
        plan.append((*tie_breaker, [key for key in tie_regions(records) if not done((*tie_breaker, 1, *key))]))
    print("\nCalls a run would make:")
    total = 0.0
    for model, reasoning, todo in plan:
        each = price(model, reasoning)
        cost = f"about ${each * len(todo):.2f}" if each is not None else "cost unknown: no stored call to price it"
        total += each * len(todo) if each else 0
        print(f"  {short(f'{model}:{reasoning}'):<44} {len(todo):>6,} calls   {cost}")
    print(f"  {'total (at the average cost of the stored calls)':<51}   about ${total:.2f}")
    if not tie_break:
        print("  The tie-break is planned once the two models have answered: add --tie-break.")
    elif any(r["requirement_agreement"] == "not answered" for r in records):
        print("  The tie-break covers only the formulas both models have answered so far.")


def print_summary(results: list[dict], labels: list[str], tie_label: str) -> None:
    """The report of a plain --report: the concrete and the parametric formulas side by side, and together."""
    records = [r for result in results for r in result["records"]]
    papers = {pid for result in results for pid in result["contexts"]}
    names = [result["name"] for result in results]
    total_column = len(results) > 1

    def row(text: str, counts: list, total=None, money: bool = False) -> None:
        cell = (lambda v: f"{'$' + format(v, '.2f'):>11}") if money else (lambda v: f"{v:>11,}")
        total = sum(counts) if total is None else total
        print(f"  {text:<42}" + "".join(cell(v) for v in counts) + (cell(total) if total_column else ""))

    def count(match) -> list[int]:
        return [sum(1 for r in result["records"] if match(r)) for result in results]

    print("\n" + "=" * WIDTH)
    print(f"  STEP 5 · {' AND '.join(name.upper() for name in names)} FORMULAS · LaTeX papers")
    print(f"  {len(papers):,} papers · {len(records):,} formulas")
    print("=" * WIDTH)
    header = "".join(f"{name:>11}" for name in names) + (f"{'total':>11}" if total_column else "")
    outcome = lambda r: (r["final"]["outcome"], r["final"]["kind"])

    print(f"{'RESULT':<44}{header}")
    row("formulas with a requirement", count(lambda r: r["final"]["outcome"] == "requirement"))
    row("   specific", count(lambda r: outcome(r) == ("requirement", "specific")))
    row("   generic", count(lambda r: outcome(r) == ("requirement", "generic")))
    row("   specific or generic: the models split", count(lambda r: outcome(r) == ("requirement", "unclear")))
    row("formulas without a requirement", count(lambda r: r["final"]["outcome"] == "none"))
    row("undecided", count(lambda r: r["final"]["outcome"] == "open"))
    sources = [{r["paper_id"] for r in result["records"] if r["final"]["outcome"] == "requirement"} for result in results]
    row("papers with a requirement", [len(s) for s in sources], len(set().union(*sources)))
    if total_column:
        print("  (a paper can have both kinds of formula: the total counts it once)")

    print(f"\n{'HOW EACH FORMULA WAS DECIDED':<44}{header}")
    row("the two models agree", count(lambda r: r["requirement_agreement"] in AGREED))
    row("they disagree on the requirement", count(lambda r: r.get("dispute") == "requirement"))
    row("   decided by the third model", count(lambda r: r.get("dispute") == "requirement" and "tie_breaker" in r and r["final"]["outcome"] != "open"))
    row("   undecided after the third model", count(lambda r: r.get("dispute") == "requirement" and "tie_breaker" in r and r["final"]["outcome"] == "open"))
    row("   third model not asked yet", count(lambda r: r.get("dispute") == "requirement" and "tie_breaker" not in r))
    row("same passage, kind disputed", count(lambda r: r.get("dispute") == "kind"))
    row("   third model not asked yet", count(lambda r: r.get("dispute") == "kind" and "tie_breaker" not in r))
    row("a model has no answer yet", count(lambda r: r["requirement_agreement"] == "not answered"))

    print(f"\n{'COST':<44}{header}")
    for label in labels + [tie_label]:
        costs = [sum(c["cost"] for c in result["calls"].get(label, [])) for result in results]
        if any(costs):
            row(short(label), costs, money=True)
    row("total", [sum(c["cost"] for calls in result["calls"].values() for c in calls) for result in results], money=True)

    pending = []
    if any(r["requirement_agreement"] == "not answered" for r in records):
        pending.append("some formulas have no answer yet: run without --report")
    if any(r.get("dispute") and "tie_breaker" not in r for r in records):
        pending.append("some disputed formulas were not asked to the third model: run with --tie-break")
    flagged = sum(1 for r in records for label in labels if r["answers"].get(label) and r["answers"][label]["problems"]) \
        + sum(1 for r in records if r.get("tie_breaker") and r["tie_breaker"]["answer"]["problems"])
    if flagged:
        pending.append(f"{flagged:,} answers failed a check (e.g. a passage not copied from the paper): see --details")
    if pending:
        print("\nNOTES")
        for note in pending:
            print(f"  · {note}")
    print("=" * WIDTH)
    print("  --concrete or --parametric: the report of one kind of formula; --details adds its technical tables.")


def process(parametric: bool, args, store: CorpusStore, pairs: list, tie_breaker: tuple, budget: float) -> dict:
    """Reads the papers, makes the calls that are missing (unless --report) and collects the records of one kind of formula."""
    labels = [f"{model}:{reasoning}" for model, reasoning in pairs]
    tie_label = f"{tie_breaker[0]}:{tie_breaker[1]}"
    name = "parametric" if parametric else "concrete"
    print(f"\nReading the LaTeX sources ({name} formulas)...")
    answers_file, formulas_file = store_files(parametric)
    contexts = load_contexts(store, args.paper, args.limit, parametric)
    regions = {(pid, n): (context, region) for pid, context in contexts.items() for n, region in enumerate(context.regions, 1)}
    print(f"{len(contexts)} papers with {name} formulas | {len(regions)} regions | {sum(len(c.formulas) for c in contexts.values())} formulas")
    result = dict(name=name, title=f"{name.upper()} FORMULAS · LaTeX papers", contexts=contexts, formulas_file=formulas_file, spent=0.0)

    if args.dry_run:
        if args.paper:
            for (pid, n), (context, region) in regions.items():
                print("\n" + "=" * WIDTH + f"\n{pid} | REGION {n}/{len(context.regions)} | {region.file} L{region.line_start}-{region.line_end}\n" + "-" * WIDTH)
                for message in build_messages(context, region):
                    print(f"[{message['role']}]\n{message['content']}\n")
        records, _ = collect(store, contexts, pairs, tie_breaker, answers_file)
        print_plan(regions, answers_file, pairs, tie_breaker, records, args.tie_break)
        return result

    if not args.report:
        print(f"Extraction models: {', '.join(short(label) for label in labels)}")
        tasks = [(model, reasoning, 1, pid, n) for model, reasoning in pairs for (pid, n) in regions]
        result["spent"] = run_calls(tasks, regions, answers_file, args.workers, budget)
    records, calls = collect(store, contexts, pairs, tie_breaker, answers_file)
    if args.tie_break and not args.report:
        asked = tie_regions(records)
        print(f"Tie-break: {short(tie_label)} on {len(asked):,} regions with a disputed formula")
        if budget - result["spent"] <= 0:
            print("   The budget is spent: no call to the third model is made. Run again to continue.")
        else:
            result["spent"] += run_calls([(*tie_breaker, 1, pid, n) for pid, n in asked], regions, answers_file, args.workers,
                                         budget - result["spent"])
            records, calls = collect(store, contexts, pairs, tie_breaker, answers_file)
    if not args.paper and not args.limit:
        # A partial selection must not overwrite the file of the whole corpus
        write_formulas(records, formulas_file)
    result.update(records=records, calls=calls)
    return result


def main():
    parser = argparse.ArgumentParser(description="Step 5: extract the requirements of the formulas with two models (and a third on their disagreements).")
    parser.add_argument("--models", nargs=2, default=DEFAULT_MODELS, metavar="ID[:REASONING]",
                        help=f"The two extraction models, each with an optional reasoning level ({', '.join(REASONING_LEVELS)}). Default: {' '.join(DEFAULT_MODELS)}.")
    parser.add_argument("--tie-break", action="store_true",
                        help="Also ask the third model about the formulas the two disagree on: their requirement, or its kind (specific / generic).")
    parser.add_argument("--tie-breaker", default=DEFAULT_TIE_BREAKER, metavar="ID[:REASONING]", help=f"The third model. Default: {DEFAULT_TIE_BREAKER}.")
    parser.add_argument("--concrete", action="store_true",
                        help="Only the concrete formulas (numeric time bounds), and print their own report instead of the summary.")
    parser.add_argument("--parametric", action="store_true",
                        help="Only the parametric formulas (time bounds given as symbols), and print their own report instead of the summary. "
                             "Their answers are kept apart, in data/processed/extractions/parametric. With --concrete: both, each with its own report.")
    parser.add_argument("--paper", action="append", help="Only this paper (repeatable); its answers are printed. The paper must be held as LaTeX.")
    parser.add_argument("--limit", type=int, help="Only the first N papers.")
    parser.add_argument("--report", action="store_true", help="Report on the stored answers and write formulas.jsonl. No model is called.")
    parser.add_argument("--details", action="store_true",
                        help="Print the report of each kind of formula with its technical tables: answers per model, failed checks, agreement, verdicts.")
    parser.add_argument("--dry-run", action="store_true", help="Print how many calls a run would make and about what they cost, and exit. With --paper, also print the prompts.")
    parser.add_argument("--workers", type=int, default=8, help="Calls made at the same time (default 8).")
    parser.add_argument("--budget", type=float, default=20.0, help="Stop starting new calls once this many dollars are spent in this invocation (default 20).")
    args = parser.parse_args()
    pairs = [parse_model(spec) for spec in args.models]
    tie_breaker = parse_model(args.tie_breaker)
    if tie_breaker in pairs:
        sys.exit("The tie-breaker must be another model than the two extraction models.")
    labels = [f"{model}:{reasoning}" for model, reasoning in pairs]
    tie_label = f"{tie_breaker[0]}:{tie_breaker[1]}"

    store = CorpusStore()
    results, budget = [], args.budget
    kinds = [kind for kind, wanted in ((False, args.concrete), (True, args.parametric)) if wanted] or [False, True]
    for parametric in kinds:
        results.append(process(parametric, args, store, pairs, tie_breaker, budget))
        budget -= results[-1]["spent"]
    if args.dry_run:
        return

    for result in results:
        for pid in args.paper or []:
            if pid in result["contexts"]:
                print_paper(result["contexts"][pid], result["records"])
    if args.concrete or args.parametric or args.details:
        for result in results:
            print_report(result["title"], result["contexts"], result["records"], result["calls"], labels, tie_label, bool(result["calls"].get(tie_label)))
            if args.details:
                print_details(result["records"], result["calls"], labels, tie_label)
    else:
        print_summary(results, labels, tie_label)
    if args.paper or args.limit:
        print("formulas.jsonl is not written for a selection of papers: only by a run or a report over the whole corpus.")
    else:
        for result in results:
            print(f"One record per {result['name']} formula, with every answer and the outcome of the vote: {result['formulas_file']}")


if __name__ == "__main__":
    main()
