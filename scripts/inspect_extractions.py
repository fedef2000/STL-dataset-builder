"""
Prints answers of step 5 for a person to read, from the formulas.jsonl files the last run or report of step 5 wrote.

    python scripts/inspect_extractions.py undecided                 # the formulas the vote leaves undecided
    python scripts/inspect_extractions.py flags                     # the answers that failed a check, by check
    python scripts/inspect_extractions.py flags --check variable    # only this check (several can be given)
    python scripts/inspect_extractions.py undecided --limit 5       # only the first 5 (per check, for flags)
    python scripts/inspect_extractions.py flags --parametric        # only the parametric formulas (--concrete: those)
    python scripts/inspect_extractions.py undecided --pdf           # only the papers held as PDF (--latex: as LaTeX)

The checks are those of step 5 at its last run or report: after a change to them, run
`python scripts/05_extract_requirements.py --report` to refresh the files.
"""
import argparse
import collections
import json
import re
import sys
import textwrap
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import BASE_DIR, RAW_LATEX_DIR
from src.extraction.records import store_files

sys.stdout.reconfigure(encoding="utf-8")
WIDTH = 100


def one_line(text: str) -> str:
    return " ".join((text or "").split())


def wrapped(text: str, indent: str) -> str:
    """The text on lines of at most WIDTH characters, each starting with `indent`."""
    return textwrap.fill(one_line(text), WIDTH, initial_indent=indent, subsequent_indent=" " * len(indent) + "  ", break_long_words=False,
                         break_on_hyphens=False) or indent


# The checks of step 5 (src/extraction/extractor.py), by the name --check takes
CHECKS = {
    "variable": "variable not in the formula",
    "formula-copy": "the formula is not a copy of the marked text",
    "bounds": "the formula lacks the time bounds of its line",
    "no-formula": "no formula given",
    "requirement-copy": "the requirement is not a copy of the excerpt",
    "joined": "the requirement joins separate parts of the excerpt",
    "mixed-kinds": "specific and generic requirements given together",
    "unknown-kind": "unknown kind of requirement",
    "unknown-domain": "unknown domain",
}


def check_name(problem: str) -> str:
    """'the requirement is not a copy of the excerpt (passage 2)' -> 'the requirement is not a copy of the excerpt'."""
    return re.sub(r" \(passage \d+\)|: .*", "", problem)


def model_name(label: str) -> str:
    return label.split("/")[-1]


def answers_of(record: dict) -> dict:
    """Every answer of a formula, the third model's included, keyed by model."""
    answers = dict(record["answers"])
    if record.get("tie_breaker"):
        answers[record["tie_breaker"]["model"] + " (tie-break)"] = record["tie_breaker"]["answer"]
    return answers


def print_heading(n: int, total: int, kind: str, record: dict) -> None:
    print("=" * WIDTH)
    print(f"[{n}/{total}] {kind} · {record['paper_id']} · {record['formula_id']}")
    print(wrapped(record["title"], "Paper:   "))
    if record.get("source_type") == "pdf":
        print(f"Source:  {BASE_DIR / 'data' / 'raw' / 'pdfs' / record['file']}, page {record['line']}")
        print(wrapped(record["source"], "Line:    "))
        print(wrapped(record["final"].get("formula") or "(no two models transcribe it alike)", "Formula: "))
    else:
        print(f"Source:  {RAW_LATEX_DIR / record['paper_id'] / record['file']}, line {record['line']}")
        print(wrapped(record["source"], "Formula: "))


def print_answer(label: str, answer: dict | None) -> None:
    print(f"  [{model_name(label)}]")
    if not answer:
        print("     not answered")
        return
    if not answer["requirements"]:
        print("     requirement: none")
    for passage in answer["requirements"]:
        print(wrapped(passage["text"], f"     requirement <{passage['kind']}>: "))


# ---------------------------------------------------------------- the commands

def show_undecided(runs: list[tuple[str, list[dict]]], limit: int | None) -> None:
    """The formulas whose answers no two models agree on (outcome 'open'), with every answer."""
    found = [(kind, r) for kind, records in runs for r in records if r["final"]["outcome"] == "open"]
    counts = collections.Counter(kind for kind, _ in found)
    print(f"{len(found):,} undecided formulas (" + ", ".join(f"{n:,} {kind}" for kind, n in counts.items()) + ")"
          + (f": the first {min(limit, len(found)):,} are printed" if limit is not None and limit < len(found) else ""))
    print("Undecided: no passage is given by two models, and fewer than two models give none.\n")
    shown = found[:limit] if limit is not None else found
    for n, (kind, r) in enumerate(shown, 1):
        print_heading(n, len(shown), kind, r)
        tie = r.get("tie_breaker")
        if tie:
            print(f"Why:     the two models: {r['requirement_agreement']}; the third model {tie['verdict'].replace('the first', model_name(list(r['answers'])[0])).replace('the second', model_name(list(r['answers'])[1]))}")
        else:
            print(f"Why:     the two models: {r['requirement_agreement']}; the third model was not asked (run step 5 with --tie-break)")
        for label, answer in answers_of(r).items():
            print_answer(label, answer)
    print("=" * WIDTH)


def what_failed(problem: str, answer: dict, record: dict) -> list[str]:
    """The lines that show what a failed check is about: the passage, the formula as given, the symbol."""
    name = check_name(problem)
    passage = re.search(r"\(passage (\d+)\)", problem)
    requirements = answer["requirements"]
    if name == "specific and generic requirements given together":
        return [wrapped(p["text"], f"     <{p['kind']}>: ") for p in requirements]
    if "requirement" in name and "kind" not in name:
        chosen = [requirements[int(passage.group(1)) - 1]] if passage else requirements[:1]
        return [wrapped(p["text"], "     passage given:    ") for p in chosen]
    if name in ("the formula is not a copy of the marked text", "no formula given"):
        return [wrapped(answer["formula"] or "(empty)", "     formula given:    "), wrapped(record["source"], "     formula in paper: ")]
    if name == "the formula lacks the time bounds of its line":
        return [wrapped(answer["formula"], "     formula given:    "), wrapped(record["source"], "     marked line:      ")]
    if name == "variable not in the formula":
        symbol = problem.split(": ", 1)[1]
        return [f"     symbol:           {symbol}", wrapped(answer["variables"].get(symbol, ""), "     explained as:     "),
                wrapped(answer["formula"], "     formula given:    ")]
    if name.startswith("unknown domain"):
        return [f"     domain given:     {answer['domain']}"]
    if name.startswith("unknown kind"):
        return [wrapped(p["text"], f"     <{p['kind'] or '(none)'}>: ") for p in requirements]
    return []


def show_flags(runs: list[tuple[str, list[dict]]], limit: int | None, checks: list[str] | None) -> None:
    """The answers that failed a check, grouped by check."""
    by_check = collections.defaultdict(list)
    for kind, records in runs:
        for r in records:
            for label, answer in answers_of(r).items():
                for problem in (answer or {}).get("problems") or []:
                    by_check[check_name(problem)].append((kind, r, label, answer, problem))
    names = sorted(by_check, key=lambda name: -len(by_check[name]))
    if checks:
        wanted = [CHECKS[check] for check in checks]
        names = [name for name in names if name in wanted]
        for check in checks:
            if CHECKS[check] not in by_check:
                print(f"No answer failed the check {check} ({CHECKS[check]}).")
        if not names:
            return
    unknown = [name for name in names if name not in CHECKS.values()]
    if unknown:
        print("Checks not known to --check (update CHECKS in this script): " + "; ".join(unknown))
    print("Answers that failed a check" + (f" (the first {limit:,} of each check are printed)" if limit is not None else "") + ":")
    for name in names:
        models = collections.Counter(model_name(label) for _, _, label, _, _ in by_check[name])
        key = next((k for k, v in CHECKS.items() if v == name), "?")
        print(f"  {len(by_check[name]):>5,}  {key:<17} {name:<52}" + " · ".join(f"{m} {n:,}" for m, n in models.most_common()))
    print()
    for name in names:
        entries = by_check[name][:limit] if limit is not None else by_check[name]
        print("#" * WIDTH)
        print(f"# {name.upper()}: {len(by_check[name]):,} answers" + (f", the first {len(entries):,} printed" if len(entries) < len(by_check[name]) else ""))
        print("#" * WIDTH)
        for n, (kind, r, label, answer, problem) in enumerate(entries, 1):
            print_heading(n, len(entries), kind, r)
            print(f"  [{model_name(label)}] {problem}")
            for line in what_failed(problem, answer, r):
                print(line)
            kept = r["final"]["requirements"]
            print(f"  Vote:    {r['final']['outcome']}" + (f" · kept passage from {model_name(kept[0]['from'])}" if kept else ""))
    print("=" * WIDTH)


def main():
    parser = argparse.ArgumentParser(description="Print answers of step 5 for a person to read.")
    parser.add_argument("what", choices=("undecided", "flags"),
                        help="undecided: the formulas the vote leaves undecided. flags: the answers that failed a check, by check.")
    parser.add_argument("--limit", type=int, help="Print only the first N (for flags: the first N of each check).")
    parser.add_argument("--check", nargs="+", choices=list(CHECKS), metavar="CHECK",
                        help="With flags: only these checks. " + "; ".join(f"{key}: {name}" for key, name in CHECKS.items()) + ".")
    parser.add_argument("--concrete", action="store_true", help="Only the concrete formulas.")
    parser.add_argument("--parametric", action="store_true", help="Only the parametric formulas.")
    parser.add_argument("--latex", action="store_true", help="Only the papers held as LaTeX.")
    parser.add_argument("--pdf", action="store_true", help="Only the papers held as PDF only.")
    args = parser.parse_args()

    runs = []
    kinds = [k for k, wanted in ((False, args.concrete), (True, args.parametric)) if wanted] or [False, True]
    sources = [s for s, wanted in ((False, args.latex), (True, args.pdf)) if wanted] or [False, True]
    for pdf in sources:
        for parametric in kinds:
            kind = f"{'parametric' if parametric else 'concrete'} {'PDF' if pdf else 'LaTeX'}"
            formulas_file = store_files(parametric, pdf)[1]
            if not formulas_file.exists():
                print(f"No {kind} formulas yet: {formulas_file} is written by a run or report of step 5.")
                continue
            runs.append((kind, [json.loads(line) for line in open(formulas_file, encoding="utf-8")]))
    if not runs:
        return
    if args.what == "undecided":
        show_undecided(runs, args.limit)
    else:
        show_flags(runs, args.limit, args.check)


if __name__ == "__main__":
    main()
