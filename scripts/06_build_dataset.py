"""
Step 6: builds the dataset from the answers of step 5: one record per formula with a requirement, in one file.

    python scripts/06_build_dataset.py                                  # data/dataset/stl_dataset.jsonl
    python scripts/06_build_dataset.py --licenses permissive_cc         # also copies with only these licence tiers

Reads the formulas.jsonl files of step 5 (LaTeX and PDF, concrete and parametric formulas): run step 5, or
`python scripts/05_extract_requirements.py --report`, first, so that they hold the latest answers and checks. No model
is called. Writes, in data/dataset/:

    stl_dataset.jsonl             one record per formula with a requirement
    stl_formulas_unpaired.jsonl   one record per formula the models agree has no requirement (no passages)
    excluded.jsonl                the formulas left out of both, and why
    stats.md                      what the dataset holds
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import DATA_DIR
from src.storage import CorpusStore
from src.extraction.dataset import dataset_record, duplicate_key, formula_of_paper
from src.extraction.records import store_files

sys.stdout.reconfigure(encoding="utf-8")
DATASET_DIR = DATA_DIR / "dataset"
LICENSE_TIERS = ("permissive_cc", "restricted_cc", "custom_or_arxiv", "unspecified")
FORMULA_ID_PATTERN = re.compile(r"(?:[\w.]+:)?\b[FP]\d+\b")


def formula_number(record_id: str) -> int:
    return int(record_id.rsplit(":", 1)[1][1:])


def left_out(item_id: str, reason: str, outcome: str, source_type: str, bounds: str, source: str, requirements: list) -> dict:
    """An entry of excluded.jsonl. `outcome` is the vote of step 5: "requirement", "none" or "open" (undecided)."""
    return {"id": item_id, "reason": reason, "outcome": outcome, "source_type": source_type, "bounds": bounds,
            "source": source, "requirements": requirements}


def build(store: CorpusStore) -> tuple[list[dict], list[dict], list[dict]]:
    """
    The records of the dataset, the formulas without a requirement (records with no passages), and the formulas left
    out of either (with the reason).
    """
    kept, unpaired, excluded, seen = [], [], [], {}
    for pdf in (False, True):
        for parametric in (False, True):
            formulas_file = store_files(parametric, pdf)[1]
            if not formulas_file.exists():
                print(f"   missing: {formulas_file} (run step 5 for these formulas)")
                continue
            bounds = "symbolic" if parametric else "numeric"
            for line in open(formulas_file, encoding="utf-8"):
                record = json.loads(line)
                item, reason = dataset_record(record, bounds, store.papers.get(record["paper_id"], {}))
                if item is None:
                    excluded.append(left_out(f"{record['paper_id']}:{record['formula_id']}", reason,
                                             record["final"]["outcome"], record.get("source_type", "latex"), bounds,
                                             record["source"], record["final"]["requirements"]))
                    continue
                outcome = "requirement" if item["requirements"] else "none"
                key = duplicate_key(item)
                if key in seen:
                    # The same formula (with the same passages), elsewhere in the paper: kept once
                    seen[key].setdefault("also_at", []).append(item["location"])
                    what = "formula and requirement" if item["requirements"] else "formula, without a requirement,"
                    excluded.append(left_out(item["id"], f"the same {what} as {seen[key]['id']}", outcome,
                                             item["source_type"], bounds, item["formula"], item["requirements"]))
                    continue
                seen[key] = item
                (kept if item["requirements"] else unpaired).append(item)
    # A formula the paper also has with a requirement is in the dataset already
    paired = {formula_of_paper(r): r["id"] for r in kept}
    for item in [r for r in unpaired if formula_of_paper(r) in paired]:
        excluded.append(left_out(item["id"], f"the same formula as {paired[formula_of_paper(item)]}, which has a requirement",
                                 "none", item["source_type"], item["bounds"], item["formula"], []))
    unpaired = [r for r in unpaired if formula_of_paper(r) not in paired]
    for records in (kept, unpaired):
        records.sort(key=lambda r: (r["paper_id"], r["bounds"], formula_number(r["id"])))
    return kept, unpaired, excluded


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")


def table(title: str, counts: collections.Counter, total: int, unit: str = "Records") -> list[str]:
    lines = [f"| {title} | {unit} | Share |", "|---|---|---|"]
    lines += [f"| {name} | {n:,} | {100 * n / total:.1f}% |" for name, n in counts.most_common()]
    return lines + [""]


def reason_table(excluded: list[dict]) -> list[str]:
    reasons = collections.Counter(FORMULA_ID_PATTERN.sub("another formula", e["reason"]) for e in excluded)
    return [f"| Reason | Formulas |", "|---|---|"] + [f"| {reason} | {n:,} |" for reason, n in reasons.most_common()] + [""]


def subsets(records: list[dict]) -> list[str]:
    """How many records are left as filters for fine-tuning are added one after another, and two looser variants."""
    def specific(r):
        return any(p["kind"] == "specific" for p in r["requirements"])

    def row(name, rows):
        return f"| {name} | {len(rows):,} | {len({r['paper_id'] for r in rows}):,} |"

    with_specific = [r for r in records if specific(r)]
    clean = [r for r in with_specific if r["logic"] == "stl"]
    lines = ["## Subsets for fine-tuning", "",
             "The records left as filters are added one after another. The last but one is the cleanest set: a formula "
             "over real-valued signals, with a passage that states it.", "",
             "| Filter | Records | Papers |", "|---|---|---|",
             row("all records", records),
             row("... with a specific passage", with_specific),
             row("... and logic `stl`", clean),
             row("... and no `provenance.flags`", [r for r in clean if not r["provenance"]["flags"]]), "",
             "| Variant | Records | Papers |", "|---|---|---|",
             row("a specific passage, logic `stl` or `propositional`", [r for r in with_specific if r["logic"] != "other"]), ""]
    return lines + table("Licence tier of the cleanest set", collections.Counter(r["license_tier"] or "none" for r in clean), len(clean))


def stats(records: list[dict], unpaired: list[dict], excluded: list[dict]) -> str:
    """stats.md: what the dataset holds. No date in it, so that a rebuild with the same data changes nothing."""
    total = len(records)
    lines = ["# STL dataset: statistics", "",
             f"{total:,} records (one per formula with a requirement) from {len({r['paper_id'] for r in records}):,} papers, "
             f"with {sum(len(r['requirements']) for r in records):,} requirement passages.", ""]
    lines += table("Source and bounds of the formula", collections.Counter(f"{r['source_type']} · {r['bounds']}" for r in records), total)
    lines += table("Logic of the formula", collections.Counter(r["logic"] for r in records), total)
    kinds = collections.Counter(p["kind"] for r in records for p in r["requirements"])
    lines += table("Kind of requirement passage", kinds, sum(kinds.values()), unit="Passages")
    lines += table("Licence tier", collections.Counter(r["license_tier"] or "none" for r in records), total)
    lines += table("Licence", collections.Counter(r["license"] or "none" for r in records), total)
    lines += table("Domain", collections.Counter(r["domain"] for r in records), total)
    lines += table("How the formula was obtained", collections.Counter(r["provenance"]["formula"] for r in records), total)
    flagged = sum(1 for r in records if r["provenance"]["flags"])
    lines += [f"{flagged:,} records come from an answer that failed a check (`provenance.flags`).", ""]
    lines += subsets(records)
    n = len(unpaired)
    lines += ["## Formulas without a requirement", "",
              f"{n:,} formulas from {len({r['paper_id'] for r in unpaired}):,} papers that the models agree have no "
              "requirement (`stl_formulas_unpaired.jsonl`): records with no passages.", ""]
    lines += table("Source and bounds of the formula", collections.Counter(f"{r['source_type']} · {r['bounds']}" for r in unpaired), n)
    lines += table("Logic of the formula", collections.Counter(r["logic"] for r in unpaired), n)
    lines += table("Licence tier", collections.Counter(r["license_tier"] or "none" for r in unpaired), n)
    lines += table("Domain", collections.Counter(r["domain"] for r in unpaired), n)
    lines += ["## Left out", "", "Formulas with a requirement (or undecided) that are not in the dataset (`excluded.jsonl`):", ""]
    lines += reason_table([e for e in excluded if e["outcome"] != "none"])
    lines += ["Formulas without a requirement that are not in `stl_formulas_unpaired.jsonl` (`excluded.jsonl`):", ""]
    lines += reason_table([e for e in excluded if e["outcome"] == "none"])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Step 6: build the dataset from the answers of step 5.")
    parser.add_argument("--licenses", nargs="+", choices=LICENSE_TIERS, metavar="TIER",
                        help=f"Also write copies with only the records of these licence tiers ({', '.join(LICENSE_TIERS)}).")
    args = parser.parse_args()

    store = CorpusStore()
    print("Reading the answers of step 5...")
    records, unpaired, excluded = build(store)
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(DATASET_DIR / "stl_dataset.jsonl", records)
    write_jsonl(DATASET_DIR / "stl_formulas_unpaired.jsonl", unpaired)
    write_jsonl(DATASET_DIR / "excluded.jsonl", excluded)
    (DATASET_DIR / "stats.md").write_text(stats(records, unpaired, excluded), encoding="utf-8", newline="\n")
    print(f"{len(records):,} records from {len({r['paper_id'] for r in records}):,} papers -> {DATASET_DIR / 'stl_dataset.jsonl'}")
    for tier, n in collections.Counter(r["license_tier"] for r in records).most_common():
        print(f"   {n:>6,}  {tier}")
    print(f"{len(unpaired):,} formulas without a requirement -> {DATASET_DIR / 'stl_formulas_unpaired.jsonl'}")
    print(f"{len(excluded):,} formulas left out -> {DATASET_DIR / 'excluded.jsonl'} (reasons in stats.md)")
    if args.licenses:
        tiers = "_".join(sorted(args.licenses))
        for name, rows in (("stl_dataset", records), ("stl_formulas_unpaired", unpaired)):
            subset = [r for r in rows if r["license_tier"] in args.licenses]
            path = DATASET_DIR / f"{name}_{tiers}.jsonl"
            write_jsonl(path, subset)
            print(f"{len(subset):,} records with licence tier {', '.join(args.licenses)} -> {path}")


if __name__ == "__main__":
    main()
