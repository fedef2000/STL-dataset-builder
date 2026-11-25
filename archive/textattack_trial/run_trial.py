"""
The TextAttack trial of step 8, as it was run on 2026-11-17 from scripts/08_augment_dataset.py
(`--method textattack --trial 30`). Archived: see README.md. Only the TextAttack part of that script is kept here; the
imports are those of the original layout (src/augmentation/paraphrase.py, src/augmentation/report.py,
src/dataset/judge.py), so this file does not run from the current pipeline.

30 correct descriptions of set 1 (fixed seed), four TextAttack augmenters (wordnet, embedding, eda, backtranslation),
one paraphrase each, the words that carry the formula frozen; each paraphrase judged against its formula by the judge
of step 7 (two models, a third on their disagreements).

    python scripts/08_augment_dataset.py --method textattack --trial 30 --dry-run
    python scripts/08_augment_dataset.py --method textattack --trial 30      # -> textattack_trial.md
"""
import argparse
import collections
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import DATA_DIR
from src.augmentation.paraphrase import AUGMENT_DIR, METHODS, frozen_words, lost_frozen, missing_symbols, run_worker, trial_sample
from src.augmentation.report import short, summary_table, write_textattack_report
from src.dataset.judge import ANSWERS_FILE, build_messages, item_key, read_answers, run_calls, usable, vote
from src.dataset.sets import DATASET_DIR, SET_1, read_jsonl
from src.extraction.records import DEFAULT_MODELS, DEFAULT_TIE_BREAKER, parse_model

sys.stdout.reconfigure(encoding="utf-8")
PAIRED_RECORDS = DATA_DIR / "normalized" / "paired" / "records.jsonl"
PARAPHRASES = AUGMENT_DIR / "trial_paraphrases.jsonl"
JUDGE_ANSWERS = AUGMENT_DIR / "answers.jsonl"
MODELS = DEFAULT_MODELS + [DEFAULT_TIE_BREAKER]
JUDGE_SET = "augment_set_1"   # the `set` of the judge's items: their answers can't be taken for step 7's
REPORT = AUGMENT_DIR / "textattack_trial.md"


def textattack_lines(sample: list[dict], regenerate: bool = False) -> list[dict]:
    """The worker's lines for the sample: the stored ones when they are of the same descriptions, else made again."""
    if PARAPHRASES.exists() and not regenerate:
        stored = read_jsonl(PARAPHRASES)
        if sorted({p["id"] for p in stored}) == sorted(r["id"] for r in sample) and len(stored) == len(sample) * len(METHODS):
            print(f"Paraphrases from {PARAPHRASES.relative_to(BASE_DIR)} (--regenerate to make them again)")
            return stored
    print(f"TextAttack on {len(sample)} descriptions ({len(METHODS)} methods each)", flush=True)
    return run_worker(sample, PARAPHRASES)


def judge_items(sample: list[dict], lines: list[dict], records: dict) -> list[dict]:
    """
    One item per description of the sample: its distinct paraphrases (none identical to the original), judged in one
    call. The judge reads what it read in step 7: the formula as step 6 normalizes it and the variable meanings.
    """
    by_id = collections.defaultdict(list)
    for line in lines:
        by_id[line["id"]].append(line)
    items = []
    for row in sample:
        record = records[row["formula_id"]]
        texts = []
        for line in by_id[row["id"]]:
            if line["text"] and line["text"] != row["nl"] and line["text"] not in texts:
                texts.append(line["text"])
        if not texts:
            continue
        messages = build_messages(record["normalized"], texts, record.get("variables"))
        items.append({"set": JUDGE_SET, "id": row["id"], "count": len(texts), "messages": messages, "key": item_key(messages),
                      "formula": record["normalized"], "descriptions": texts, "kinds": [None] * len(texts)})
    return items


def labels_of(stored: dict, label: str, item: dict) -> list[str | None]:
    row = stored.get((*parse_model(label), item["set"], item["id"]))
    return [j["label"] for j in row["judgments"]] if usable(row, item) else [None] * item["count"]


def dry_run(items: list[dict], n_descriptions: int):
    """The calls the judge would make, priced at the average of step 7's stored calls of each model."""
    stored, step7 = read_answers(JUDGE_ANSWERS), read_answers(ANSWERS_FILE)
    print(f"\nThe judge: {len(items) or n_descriptions} descriptions" + (f", {sum(i['count'] for i in items)} paraphrases" if items else ""))
    total = 0.0
    for label in DEFAULT_MODELS:
        model, reasoning = parse_model(label)
        todo = sum(1 for i in items if not usable(stored.get((model, reasoning, i["set"], i["id"])), i)) if items else n_descriptions
        costs = [r["cost"] for k, r in step7.items() if k[:2] == (model, reasoning) and r.get("judgments")]
        each = sum(costs) / len(costs) if costs else 0
        total += each * todo
        print(f"  {short(label):<24} {todo:>4} calls   about ${each * todo:.2f}")
    print(f"  {short(DEFAULT_TIE_BREAKER):<24} only where the two differ")
    print(f"  {'total':<24}             about ${total:.2f} (plus the third model)")


def judge(items: list[dict], budget: float, workers: int) -> dict:
    """As step 7: both models on every item, the third on the items where they differ."""
    first = [(*parse_model(label), item) for label in DEFAULT_MODELS for item in items]
    spent = run_calls(first, answers_file=JUDGE_ANSWERS, workers=workers, budget=budget)
    stored = read_answers(JUDGE_ANSWERS)
    disputed = [i for i in items if any(None not in pair and pair[0] != pair[1]
                                        for pair in zip(*(labels_of(stored, l, i) for l in DEFAULT_MODELS)))]
    print(f"\nThe third model ({short(DEFAULT_TIE_BREAKER)}) on the {len(disputed)} descriptions where the two differ:")
    run_calls([(*parse_model(DEFAULT_TIE_BREAKER), i) for i in disputed], answers_file=JUDGE_ANSWERS, workers=workers,
              budget=budget - spent)
    return read_answers(JUDGE_ANSWERS)


def results(sample: list[dict], lines: list[dict], items: list[dict], stored: dict) -> list[dict]:
    """
    One row per line: the paraphrase, its final label (with each model's answer), the frozen words it lost (the
    words TextAttack was told to keep) and the numbers and symbols it misses.
    """
    rows_by_id = {r["id"]: r for r in sample}
    items_by_id = {i["id"]: i for i in items}
    out = []
    for line in lines:
        row = rows_by_id[line["id"]]
        result = {**line, "original": row["nl"], "stl": row["stl"], "formula": None, "label": None, "how": None,
                  "answers": [], "lost": [], "missing": []}
        if not line["text"] or line["text"] == row["nl"]:
            result["label"] = "unchanged"
        else:
            item = items_by_id[line["id"]]
            n = item["descriptions"].index(line["text"])
            first = [labels_of(stored, l, item)[n] for l in DEFAULT_MODELS]
            result["label"], result["how"] = vote(first, labels_of(stored, DEFAULT_TIE_BREAKER, item)[n])
            result["formula"] = item["formula"]
            result["lost"] = lost_frozen(row["nl"], line["text"], frozen_words(row["nl"], row["stl"]))
            result["missing"] = missing_symbols(row["nl"], line["text"], row["stl"])
            for label in MODELS:
                answer = stored.get((*parse_model(label), item["set"], item["id"]))
                if usable(answer, item):
                    j = answer["judgments"][n]
                    result["answers"].append({"model": short(label), "label": j["label"], "reason": j["reason"], "problems": j["problems"]})
        out.append(result)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trial", type=int, required=True, metavar="N", help="paraphrase N correct descriptions of set 1")
    parser.add_argument("--regenerate", action="store_true", help="make the paraphrases again even if stored")
    parser.add_argument("--dry-run", action="store_true", help="only print the calls a run would make and their cost")
    parser.add_argument("--budget", type=float, default=2.0, help="dollars after which no new call is started (default 2)")
    parser.add_argument("--workers", type=int, default=8, help="calls made at the same time (default 8)")
    args = parser.parse_args()

    pairs = read_jsonl(DATASET_DIR / SET_1 / "pairs.jsonl")
    records = {r["id"]: r for r in read_jsonl(PAIRED_RECORDS)}
    sample = trial_sample(pairs, args.trial)
    lines = textattack_lines(sample, args.regenerate)
    items = judge_items(sample, lines, records)
    if args.dry_run:
        dry_run(items, len(sample))
        return
    stored = judge(items, args.budget, args.workers)
    rows = results(sample, lines, items, stored)
    print("\n" + "\n".join(summary_table(rows, METHODS)))
    write_textattack_report(REPORT, rows, sample, items, stored, MODELS)
    print(f"\nThe report, with every paraphrase: {REPORT.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
