"""
Writes the formulas of step 6 as CSV files, to check by eye that each was translated correctly. Reads the manifests of
the last run of step 6: nothing is normalized again.

    data/normalized/unpaired/translations.csv   the formulas kept for stl-nl: original LaTeX, normalized text, pattern
    data/normalized/paired/translations.csv     the paired formulas ok, one row per requirement passage: original
                                                LaTeX, normalized formula, the passage as the paper writes it and as
                                                normalized to match the formula

    python scripts/inspect_normalization.py                    # both files
    python scripts/inspect_normalization.py --only paired      # one of them (unpaired, paired)
"""
import argparse
import csv
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import DATA_DIR

NORMALIZED_DIR = DATA_DIR / "normalized"


def unpaired_rows(lines: list[dict]) -> list[list[str]]:
    """One row per formula kept for stl-nl."""
    return [[line["original"], line["normalized"], line["pattern"]] for line in lines if line["selection"] == "kept"]


def paired_rows(lines: list[dict]) -> list[list[str]]:
    """One row per requirement passage of a formula ok: the formula is repeated for each of its passages."""
    return [[line["original"], line["normalized"], passage["text"], passage["normalized"]]
            for line in lines if line["status"] == "ok" for passage in line["requirements"]]


# name: (header, rows of the manifest lines)
FILES = {
    "unpaired": (["original", "normalized", "pattern"], unpaired_rows),
    "paired": (["original", "normalized", "text original", "text normalized"], paired_rows),
}


def write(name: str):
    header, rows_of = FILES[name]
    manifest = NORMALIZED_DIR / name / "manifest.jsonl"
    if not manifest.is_file():
        sys.exit(f"{manifest.relative_to(BASE_DIR)} not found: run scripts/06_normalize_formulas.py first")
    rows = rows_of([json.loads(line) for line in open(manifest, encoding="utf-8")])
    output = NORMALIZED_DIR / name / "translations.csv"
    with open(output, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"{len(rows)} rows written to {output.relative_to(BASE_DIR)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", choices=sorted(FILES), help="write only this file (default: both)")
    args = parser.parse_args()
    for name in [args.only] if args.only else list(FILES):
        write(name)


if __name__ == "__main__":
    main()
