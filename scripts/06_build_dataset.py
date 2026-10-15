"""
Step 6: builds the dataset from the answers of step 5: one record per formula with a requirement, in one file.

    python scripts/06_build_dataset.py                                  # data/dataset/stl_dataset.jsonl
    python scripts/06_build_dataset.py --licenses permissive_cc         # also a copy with only these licence tiers

Reads the formulas.jsonl files of step 5 (LaTeX and PDF, concrete and parametric formulas): run step 5, or
`python scripts/05_extract_requirements.py --report`, first, so that they hold the latest answers and checks. No model
is called. Writes, in data/dataset/:

    stl_dataset.jsonl   one record per formula with a requirement
    excluded.jsonl      the formulas with a requirement that were left out, and why
    stats.md            what the dataset holds
"""
import argparse
import collections
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import DATA_DIR
from src.storage import CorpusStore
from src.extraction.dataset import dataset_record, duplicate_key
from src.extraction.records import store_files

sys.stdout.reconfigure(encoding="utf-8")
DATASET_DIR = DATA_DIR / "dataset"
LICENSE_TIERS = ("permissive_cc", "restricted_cc", "custom_or_arxiv", "unspecified")


def formula_number(record_id: str) -> int:
    return int(record_id.rsplit(":", 1)[1][1:])


def build(store: CorpusStore) -> tuple[list[dict], list[dict]]:
    """The records of the dataset, and the formulas with a requirement that were left out (with the reason)."""
    kept, excluded, seen = [], [], {}
    for pdf in (False, True):
        for parametric in (False, True):
            formulas_file = store_files(parametric, pdf)[1]
            if not formulas_file.exists():
                print(f"   missing: {formulas_file} (run step 5 for these formulas)")
                continue
            kind = "parametric" if parametric else "concrete"
            for line in open(formulas_file, encoding="utf-8"):
                record = json.loads(line)
                item, reason = dataset_record(record, kind, store.papers.get(record["paper_id"], {}))
                if item is None:
                    if reason:
                        excluded.append({"id": f"{record['paper_id']}:{record['formula_id']}", "reason": reason,
                                         "source_type": record.get("source_type", "latex"), "formula_kind": kind,
                                         "source": record["source"], "requirements": record["final"]["requirements"]})
                    continue
                key = duplicate_key(item)
                if key in seen:
                    # The same formula with the same passages, elsewhere in the paper: kept once
                    seen[key].setdefault("also_at", []).append(item["location"])
                    excluded.append({"id": item["id"], "reason": f"the same formula and requirement as {seen[key]['id']}",
                                     "source_type": item["source_type"], "formula_kind": kind, "source": item["formula"],
                                     "requirements": item["requirements"]})
                    continue
                seen[key] = item
                kept.append(item)
    kept.sort(key=lambda r: (r["paper_id"], r["formula_kind"], formula_number(r["id"])))
    return kept, excluded


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")


def table(title: str, counts: collections.Counter, total: int) -> list[str]:
    lines = [f"| {title} | Records | Share |", "|---|---|---|"]
    lines += [f"| {name} | {n:,} | {100 * n / total:.1f}% |" for name, n in counts.most_common()]
    return lines + [""]


def stats(records: list[dict], excluded: list[dict]) -> str:
    """stats.md: what the dataset holds. No date in it, so that a rebuild with the same data changes nothing."""
    total = len(records)
    lines = ["# STL dataset: statistics", "",
             f"{total:,} records (one per formula with a requirement) from {len({r['paper_id'] for r in records}):,} papers, "
             f"with {sum(len(r['requirements']) for r in records):,} requirement passages.", ""]
    lines += table("Source and kind of formula", collections.Counter(f"{r['source_type']} · {r['formula_kind']}" for r in records), total)
    lines += table("Quality of the requirement", collections.Counter(r["quality"] for r in records), total)
    lines += table("Licence tier", collections.Counter(r["license_tier"] or "none" for r in records), total)
    lines += table("Licence", collections.Counter(r["license"] or "none" for r in records), total)
    lines += table("Domain", collections.Counter(r["domain"] for r in records), total)
    lines += table("How the formula was obtained", collections.Counter(r["provenance"]["formula"] for r in records), total)
    flagged = sum(1 for r in records if r["provenance"]["flags"])
    lines += [f"{flagged:,} records come from an answer that failed a check (`provenance.flags`).", "",
              "## Left out", "", "Formulas with a requirement that are not in the dataset (`excluded.jsonl`):", ""]
    reasons = collections.Counter("the same formula and requirement as another record" if e["reason"].startswith("the same formula and")
                                  else "the same formula as another line of the PDF text" if e["reason"].startswith("the same formula as")
                                  else e["reason"] for e in excluded)
    lines += [f"| Reason | Formulas |", "|---|---|"] + [f"| {reason} | {n:,} |" for reason, n in reasons.most_common()] + [""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Step 6: build the dataset from the answers of step 5.")
    parser.add_argument("--licenses", nargs="+", choices=LICENSE_TIERS, metavar="TIER",
                        help=f"Also write a copy with only the records of these licence tiers ({', '.join(LICENSE_TIERS)}).")
    args = parser.parse_args()

    store = CorpusStore()
    print("Reading the answers of step 5...")
    records, excluded = build(store)
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(DATASET_DIR / "stl_dataset.jsonl", records)
    write_jsonl(DATASET_DIR / "excluded.jsonl", excluded)
    (DATASET_DIR / "stats.md").write_text(stats(records, excluded), encoding="utf-8", newline="\n")
    print(f"{len(records):,} records from {len({r['paper_id'] for r in records}):,} papers -> {DATASET_DIR / 'stl_dataset.jsonl'}")
    print(f"{len(excluded):,} formulas with a requirement left out -> {DATASET_DIR / 'excluded.jsonl'} (reasons in stats.md)")
    for tier, n in collections.Counter(r["license_tier"] for r in records).most_common():
        print(f"   {n:>6,}  {tier}")
    if args.licenses:
        subset = [r for r in records if r["license_tier"] in args.licenses]
        path = DATASET_DIR / f"stl_dataset_{'_'.join(sorted(args.licenses))}.jsonl"
        write_jsonl(path, subset)
        print(f"{len(subset):,} records with licence tier {', '.join(args.licenses)} -> {path}")


if __name__ == "__main__":
    main()
