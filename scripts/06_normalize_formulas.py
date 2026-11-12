"""
Step 6: normalizes the formulas extracted by step 5 into one STL syntax, that of stl-nl. Two inputs, each with
its mode (src/normalization/rules.py):

- unpaired (data/extracted/unpaired.jsonl, mode stl-nl): the formulas without a requirement become the input
  of stl-nl (one formula per .stl file, in its grammar), so that stl-nl can write natural-language descriptions of
  them. Each is checked with stlgen, the parser of stl-nl.
- paired (data/extracted/paired.jsonl, mode faithful): the formulas with a requirement go to fine-tuning with the
  paper's description, so they keep the meaning it describes: same syntax, but bounds and powers stay as the paper
  writes them (F[0,2.5], F(2,12], G[T,T + delta], x^2), beyond stl-nl's grammar, and the rules that would change the
  meaning reject the formula. Their descriptions are written to match the formula (src/normalization/description.py).

    python scripts/06_normalize_formulas.py                     # both inputs
    python scripts/06_normalize_formulas.py --only paired       # one of them (unpaired, paired)
    python scripts/06_normalize_formulas.py --seed 1            # other random values for the bounds that cannot stay symbolic
    python scripts/06_normalize_formulas.py --stlgen PATH       # the stlgen binary of stl-nl (default: STLGEN_BIN)
    python scripts/06_normalize_formulas.py --max-per-pattern 0 # every formula ok to stl-nl (default: 10 per pattern)
    python scripts/06_normalize_formulas.py --show-rejected               # the reasons of rejection, with counts
    python scripts/06_normalize_formulas.py --show-rejected function      # 10 random formulas rejected by `function`
    python scripts/06_normalize_formulas.py --show-rejected "unknown_command: \\overline" --limit 0   # all of them
    python scripts/06_normalize_formulas.py --show-rejected --only paired # the same, for the paired formulas

--show-rejected only reads the manifest of the last run (unpaired, unless --only paired): nothing is normalized again
and no file is written.

Of the unpaired formulas ok, those with the same normalized text as an earlier one are left out, and at most
--max-per-pattern of each pattern are kept (taken from the papers in turn): the manifest says which (`selection`).
The paired ones are all kept: the same formula with another description is another pair. Writes (the files of an
earlier run are replaced):

    data/normalized/unpaired/
        stl/f00001.stl ...            the formulas kept for stl-nl (status ok, selection kept)
        needs_review/r00001.stl ...   the formulas with a rule of status needs_review (none since 2026-10-19: not written)
        manifest.jsonl                one line per input record: status, file, reasons, rules, original and normalized text
        report.md                     counts by status, reason and pattern, with examples
    data/normalized/paired/
        records.jsonl                 the records of step 5 whose formula is ok, with `normalized`, `stl` (the same formula
                                      with the parentheses stl-nl prints), `pattern`, `skeleton`
                                      and, in each requirement, `normalized`: the text that matches the formula
        manifest.jsonl                as above, with the passages of the formulas ok and what couldn't be converted
        report.md                     as above, with what goes beyond stl-nl's grammar and how the descriptions were written
"""
import argparse
import collections
import json
import random
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import DATA_DIR, STLGEN_BIN
from src.normalization.report import reason_rule, report
from src.normalization.run import normalize_records
from src.normalization.select import select

sys.stdout.reconfigure(encoding="utf-8")
OUTPUT_DIR = DATA_DIR / "normalized"
# name: (input, mode of the normalization, output folder)
INPUTS = {
    "unpaired": (DATA_DIR / "extracted" / "unpaired.jsonl", "stl-nl", OUTPUT_DIR / "unpaired"),
    "paired": (DATA_DIR / "extracted" / "paired.jsonl", "faithful", OUTPUT_DIR / "paired"),
}
FOLDERS = {"ok": ("stl", "f"), "needs_review": ("needs_review", "r")}


def write_stl_files(lines: list[dict], output: Path):
    """The formulas for stl-nl, one per .stl file (unpaired)."""
    for status, (folder, prefix) in FOLDERS.items():
        directory = output / folder
        directory.mkdir(parents=True, exist_ok=True)
        for old in directory.glob("*.stl"):
            old.unlink()
        number = 0
        for line in lines:
            if line["status"] == status and line["selection"] in ("kept", None):
                number += 1
                line["file"] = f"{folder}/{prefix}{number:05d}.stl"
                (output / line["file"]).write_text(line["normalized"] + "\n", encoding="utf-8")
        if number == 0 and not any(directory.iterdir()):
            directory.rmdir()  # no formula with this status: no empty folder


def paired_record(record: dict, line: dict) -> dict:
    """
    The record of step 5 with its normalized formula (after `formula`, which stays the paper's LaTeX) and, in each
    requirement, the normalized text (after `text`, which stays as the paper writes it).
    """
    out = {}
    for key, value in record.items():
        if key == "requirements":
            value = [{**passage, "normalized": normalized["normalized"]}
                     for passage, normalized in zip(value, line["requirements"])]
        out[key] = value
        if key == "formula":
            out.update(normalized=line["normalized"], stl=line["stl"], pattern=line["pattern"], skeleton=line["skeleton"])
    return out


def write_lines(path: Path, lines: list[dict]):
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")


def run(name: str, args):
    source, mode, output = INPUTS[name]
    output.mkdir(parents=True, exist_ok=True)
    records = [json.loads(line) for line in open(source, encoding="utf-8")]
    print(f"Normalizing {len(records)} {name} formulas from {source.relative_to(BASE_DIR)} (mode {mode})")
    lines = normalize_records(records, args.seed, args.stlgen, mode)
    select(lines, args.max_per_pattern if mode == "stl-nl" else 0, args.seed)
    if mode == "stl-nl":
        write_stl_files(lines, output)
    else:
        for line in lines:
            line["selection"] = None  # no selection: every pair is kept
        write_lines(output / "records.jsonl",
                    [paired_record(r, l) for r, l in zip(records, lines) if l["status"] == "ok"])
    write_lines(output / "manifest.jsonl", lines)
    text = report(lines, mode=mode, source=str(source.relative_to(BASE_DIR)), seed=args.seed,
                  max_per_pattern=args.max_per_pattern)
    (output / "report.md").write_text(text, encoding="utf-8")
    status = collections.Counter(l["status"] for l in lines)
    kept = f" (kept for stl-nl {sum(1 for l in lines if l['selection'] == 'kept')})" if mode == "stl-nl" else ""
    print(f"ok {status['ok']}{kept}, needs_review {status['needs_review']}, rejected {status['rejected']}: "
          f"see {(output / 'report.md').relative_to(BASE_DIR)}")


def show_rejected(name: str, prefix: str, limit: int, seed: str):
    """
    Prints the rejected formulas of the manifest of `name` whose reason starts with `prefix` (a rule, or a rule and
    what it found): a random sample of `limit` (0: all), drawn with `seed`, because the manifest is ordered by paper
    and the first ones would often all come from one paper. With an empty `prefix`, the reasons with their counts.
    """
    manifest = INPUTS[name][2] / "manifest.jsonl"
    if not manifest.is_file():
        sys.exit(f"{manifest.relative_to(BASE_DIR)} not found: run this script without --show-rejected first")
    rejected = [line for line in map(json.loads, open(manifest, encoding="utf-8")) if line["status"] == "rejected"]
    if not prefix:
        count = collections.Counter(reason_rule(l["reasons"][0]) for l in rejected)
        print(f"{len(rejected)} rejected {name} formulas, by reason:")
        for rule, n in count.most_common():
            print(f"  {rule:<22} {n:>5}")
        return
    chosen = [l for l in rejected if l["reasons"][0].startswith(prefix)]
    if not chosen:
        sys.exit(f"no rejected formula has a reason starting with {prefix!r}: --show-rejected alone lists them")
    sample = chosen if limit == 0 or limit >= len(chosen) else random.Random(seed).sample(chosen, limit)
    print(f"{prefix}: {len(chosen)} formulas, showing {len(sample)} (seed {seed})")
    for n, line in enumerate(sample, 1):
        print(f"\n[{n}/{len(sample)}] {line['id']}   ({line['source_type']}, bounds: {line['bounds']})")
        print(f"  original : {' '.join(line['original'].split())}")
        reason = line["reasons"][0]
        print(f"  found    : {' '.join(reason.split(': ', 1)[1].split()) if ': ' in reason else '-'}")
        print(f"  rules    : {', '.join(line['rules'][:-1]) or '-'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", choices=sorted(INPUTS), help="normalize only these formulas (default: both)")
    parser.add_argument("--seed", default="0", help="seed of the random values of the symbolic bounds")
    parser.add_argument("--stlgen", type=Path, default=STLGEN_BIN, help="the stlgen binary of stl-nl")
    parser.add_argument("--max-per-pattern", type=int, default=10,
                        help="at most this many formulas of each pattern go to stl-nl (0: no cap)")
    parser.add_argument("--show-rejected", nargs="?", const="", metavar="REASON",
                        help="print rejected formulas whose reason starts with REASON (alone: list the reasons), "
                             "from the manifest of the last run")
    parser.add_argument("--limit", type=int, default=10, help="with --show-rejected: how many formulas (0: all)")
    args = parser.parse_args()
    if args.show_rejected is not None:
        show_rejected(args.only or "unpaired", args.show_rejected, args.limit, args.seed)
        return
    names = [args.only] if args.only else list(INPUTS)
    if "unpaired" in names and not args.stlgen.is_file():
        sys.exit(f"stlgen not found at {args.stlgen}: build it in stl-nl (cargo build --release --locked "
                 f"--manifest-path rust/stlgen/Cargo.toml) or pass --stlgen")
    for name in names:
        run(name, args)


if __name__ == "__main__":
    main()
