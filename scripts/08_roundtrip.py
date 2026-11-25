"""
Step 8: the round-trip check, the filter of the dataset (src/evaluation/roundtrip.py). A model reads only a
description and writes the formula; the comparator says how close it is to the dataset's formula: compare.py (written
the same way) and, for the answers it doesn't match exactly, stlsat (src/evaluation/sat.py: the same meaning). Two
models (gemini-3.8-flash, gpt-6-luna), one answer each, one description per call. Checked: set 1's candidates (step 7)
and the paraphrases of step 9; sets 2 and 3 wait for their new stl-nl run.

    python scripts/08_roundtrip.py --trial 30 --dry-run   # the calls of the trial, and their cost when it is known
    python scripts/08_roundtrip.py --trial 30             # 30 descriptions of set 1: data/processed/roundtrip/trial.md
    python scripts/08_roundtrip.py --dry-run              # the calls a full run would make, and their cost
    python scripts/08_roundtrip.py                        # every description (at most --budget dollars)
    python scripts/08_roundtrip.py --group paraphrase     # the calls of one group only
    python scripts/08_roundtrip.py --import-decisions     # the decisions written by hand in roundtrip.xlsx -> set_1/manual.jsonl
    python scripts/08_roundtrip.py --no-sat               # without stlsat: compare.py only

Every run without --trial ends, when every checkable description has both answers, by writing:
- the split (src/dataset/sets.py, split): a candidate is in the dataset when at least one of the two models wrote its
  formula back, or when it was kept or fixed by hand (data/dataset/set_1/manual.jsonl); the others are out, with
  the reason. Set 1 to set_1/pairs.jsonl, dropped.jsonl and pairs1.xlsx; the paraphrases (only those of a pair in
  the dataset) to set_1/augmented/pairs.jsonl and dropped.jsonl;
- data/dataset/roundtrip/: results.jsonl (one row per description: the formulas of both models and the comparator's
  verdicts), report.md (the split, matches per group and model, levels, near details, stlsat, paraphrases against
  their originals) and roundtrip.xlsx (the descriptions to read, with three columns to fill by hand: decision (keep,
  fix, drop), fixed formula, note; and every row);
- data/dataset/analysis.md and patterns.csv (src/dataset/analysis.py).
--import-decisions checks the decisions and writes them to data/dataset/set_1/manual.jsonl; then run step 7 (only
needed for a fix), this step, step 9 (paraphrases for the pairs now in the dataset) and this step again.
roundtrip.xlsx is not rewritten while it holds decisions not imported yet.

stlgen (config.STLGEN_BIN) must have the parse command; stlsat (config.STLSAT_BIN) must be built (cargo build --release,
with libz3), unless --no-sat. The answers are kept in data/processed/roundtrip/answers.jsonl:
a run makes only the calls not stored yet, and a stored answer is asked again only when what the model reads (the
description, the prompt) has changed.
"""
import argparse
import random
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.dataset.analysis import write_analysis
from src.dataset.sets import DATASET_DIR
from src.evaluation import roundtrip
from src.evaluation.roundtrip import GROUPS, MODELS, ORDER, short

TRIAL_SEED = 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trial", type=int, metavar="N", help="N descriptions of set 1 only (fixed seed), and trial.md")
    parser.add_argument("--group", choices=GROUPS, action="append", help="make the calls of this group only (repeatable)")
    parser.add_argument("--dry-run", action="store_true", help="print the calls a run would make and their cost; call nothing")
    parser.add_argument("--budget", type=float, default=5.0, help="stop starting calls past this many dollars (default 5)")
    parser.add_argument("--workers", type=int, default=8, help="calls (and stlsat checks) in parallel (default 8)")
    parser.add_argument("--no-sat", action="store_true", help="compare with compare.py only, without stlsat")
    parser.add_argument("--import-decisions", action="store_true",
                        help="read the decisions written by hand in roundtrip.xlsx into data/dataset/set_1/manual.jsonl; call nothing")
    args = parser.parse_args()

    if args.import_decisions:
        if roundtrip.import_decisions():
            print("Next: python scripts/07_build_dataset.py (only needed for a fix), python scripts/08_roundtrip.py, "
                  "python scripts/09_augment_dataset.py, python scripts/08_roundtrip.py")
        return

    if args.trial:
        pool = roundtrip.items_of(["set_1"])
        items = sorted(random.Random(TRIAL_SEED).sample(pool, min(args.trial, len(pool))), key=lambda i: i["id"])
    else:
        items = roundtrip.items_of(args.group or GROUPS)
    references = roundtrip.reference_trees(items)
    checkable = [i for i in items if references[i["stl"]] is not None]
    print(f"{len(items)} descriptions, {len(checkable)} checkable ({len(items) - len(checkable)} formulas stlgen can't read)")
    if args.dry_run:
        roundtrip.plan(items, references)
        return
    spent = roundtrip.run_calls(checkable, args.workers, args.budget)
    print(f"${spent:.2f} spent in this run")

    if args.trial:
        rows = roundtrip.results(items, references, not args.no_sat, args.workers)
        path = roundtrip.write_trial(rows)
        for label in MODELS:
            m = short(label)
            print(f"  {m:<20} " + ", ".join(f"{level} {sum(1 for r in rows if r['models'][m]['level'] == level)}" for level in ORDER))
        print(f"\nEvery description with both answers: {path.relative_to(BASE_DIR)}")
        return
    everything = roundtrip.items_of(GROUPS)
    references = roundtrip.reference_trees(everything)
    rows = roundtrip.results(everything, references, not args.no_sat, args.workers)
    pending = sum(1 for r in rows if r["best"] is None)
    if pending:
        print(f"\nNot written: {pending} descriptions still miss an answer (run again, or without --group)")
        return
    out = roundtrip.write_outputs(rows)
    print(f"\nWritten {out.relative_to(BASE_DIR)}/: results.jsonl, report.md, roundtrip.xlsx; and the split of each "
          "group above (set_1/pairs.jsonl, dropped.jsonl, pairs1.xlsx; set_1/augmented/pairs.jsonl, dropped.jsonl)")
    print(f"Written {write_analysis(DATASET_DIR).relative_to(BASE_DIR)} and patterns.csv")


if __name__ == "__main__":
    main()
