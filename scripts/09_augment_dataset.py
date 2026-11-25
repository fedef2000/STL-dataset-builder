"""
Step 9: augment the dataset with paraphrases of its descriptions (src/augmentation/llm.py). A model (llm.GENERATOR)
writes K paraphrases of each pair of set 1 in the dataset (set_1/pairs.jsonl, written by the round trip of step 8),
given its formula and variable meanings so that it knows what must not change.

    python scripts/09_augment_dataset.py --dry-run      # the calls a run would make, and their cost
    python scripts/09_augment_dataset.py --budget 3     # data/dataset/set_1/augmented/candidates.jsonl

candidates.jsonl has one line per paraphrase: the pair it paraphrases with the paraphrase as `nl`, id
"<original id>:A<n>", `augmented_from` (the original id, to keep a paraphrase in the split of its original),
`augmentation` (how it was made, the numbers and symbols of the original it misses), `roundtrip` and `original_nl`
empty. They are candidates: run python scripts/08_roundtrip.py next, which checks them as it checks set 1 and splits
them into set_1/augmented/pairs.jsonl (a model wrote the formula back, or kept by hand) and dropped.jsonl.

The model's answers are kept in data/processed/augmentation/llm_answers.jsonl: a run makes only the calls not stored
yet. How the way to paraphrase was chosen (a trial of TextAttack's augmenters, rejected): archive/textattack_trial/.
"""
import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import DATA_DIR
from src.augmentation import llm
from src.dataset.sets import DATASET_DIR, SET_1, read_jsonl, write_candidates
from src.extraction.extractor import LOWEST_REASONING
from src.extraction.records import parse_model

sys.stdout.reconfigure(encoding="utf-8")
PAIRED_RECORDS = DATA_DIR / "normalized" / "paired" / "records.jsonl"
AUGMENTED_DIR = DATASET_DIR / SET_1 / "augmented"


def short(label: str) -> str:
    return parse_model(label)[0].split("/")[-1]


def print_plan(items: list[dict], model: str, reasoning: str):
    """The model's calls a run would make, priced at the average of its stored calls."""
    stored = llm.read_answers()
    todo = sum(1 for i in items if not llm.usable(stored.get((model, reasoning, i["id"])), i))
    costs = [r["cost"] for k, r in stored.items() if k[:2] == (model, reasoning) and r.get("paraphrases")]
    price = f"about ${todo * sum(costs) / len(costs):.2f}" if costs else "no price stored yet: about a cent per call or less"
    print(f"{short(llm.GENERATOR)} (reasoning {reasoning}): {todo} of {len(items)} calls to make, "
          f"{llm.K} paraphrases each ({price})")


def augment(rows: list[dict], records: dict, budget: float, workers: int, dry_run: bool):
    """Every pair of set 1 paraphrased by the model, written to set_1/augmented/candidates.jsonl."""
    model, reasoning = parse_model(llm.GENERATOR)
    items = llm.items_for(rows, records)
    if dry_run:
        print_plan(items, model, reasoning)
        return
    print(f"Paraphrases by {short(llm.GENERATOR)} (reasoning {reasoning}), {llm.K} per description:")
    stored = llm.generate(items, model, reasoning, workers=workers, budget=budget)
    answers = [stored[(model, reasoning, i["id"])] for i in items if llm.usable(stored.get((model, reasoning, i["id"])), i)]
    used = (f"{LOWEST_REASONING} (it refuses off)"
            if any("asked with reasoning" in n for a in answers for n in a.get("notes", [])) else reasoning)
    pairs = llm.augmented_pairs(rows, items, stored, model, reasoning, used)
    write_candidates(pairs, AUGMENTED_DIR)
    missing = sum(1 for p in pairs if p["augmentation"]["missing_symbols"])
    print(f"\n{len(answers)} of {len(rows)} descriptions paraphrased (${sum(a.get('cost', 0) for a in answers):.2f}), "
          f"{len(pairs)} paraphrases ({missing} missing a number or symbol of the original)\n"
          f" -> {AUGMENTED_DIR.relative_to(BASE_DIR)}/candidates.jsonl")
    if len(answers) < len(rows):
        print(f"{len(rows) - len(answers)} descriptions without paraphrases yet: run again to make them.")
    print("Next: python scripts/08_roundtrip.py (checks the paraphrases and splits them)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="only print the calls a run would make and their cost")
    parser.add_argument("--budget", type=float, default=2.0, help="dollars after which no new call is started (default 2)")
    parser.add_argument("--workers", type=int, default=8, help="calls made at the same time (default 8)")
    args = parser.parse_args()
    pairs_file = DATASET_DIR / SET_1 / "pairs.jsonl"
    if not pairs_file.exists():
        raise SystemExit(f"{pairs_file.relative_to(BASE_DIR)} missing: run steps 7 and 8 first")
    records = {r["id"]: r for r in read_jsonl(PAIRED_RECORDS)}
    augment(read_jsonl(pairs_file), records, args.budget, args.workers, args.dry_run)


if __name__ == "__main__":
    main()
