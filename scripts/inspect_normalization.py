"""
Writes the formulas step 7 kept for stl-nl as a CSV, to check by eye that each was translated correctly: the original
LaTeX, the formula written in its .stl file and its pattern. Reads the manifest of the last run of step 7: nothing is
normalized again.

    python scripts/inspect_normalization.py                    # data/normalized/translations.csv
    python scripts/inspect_normalization.py --output FILE      # another file
"""
import argparse
import csv
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import DATA_DIR

MANIFEST = DATA_DIR / "normalized" / "manifest.jsonl"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=DATA_DIR / "normalized" / "translations.csv")
    args = parser.parse_args()
    lines = [json.loads(line) for line in open(MANIFEST, encoding="utf-8")]
    kept = [line for line in lines if line["selection"] == "kept"]
    with open(args.output, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["original", "normalized", "pattern"])
        for line in kept:
            writer.writerow([line["original"], line["normalized"], line["pattern"]])
    print(f"{len(kept)} formulas written to {args.output}")


if __name__ == "__main__":
    main()
