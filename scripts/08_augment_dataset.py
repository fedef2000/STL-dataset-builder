"""
Step 8: augment the dataset with paraphrases of its descriptions (src/augmentation/). Trials on N correct pairs of
set 1, each paraphrase judged against its formula by the judge of step 7, with two ways to paraphrase:

    textattack   TextAttack's augmenters (wordnet, embedding, eda, backtranslation), one paraphrase each
    llm          a model (llm.GENERATOR) writes K paraphrases of each description, given its formula

    python scripts/08_augment_dataset.py --method llm --trial 30 --dry-run   # the calls a run would make, and their cost
    python scripts/08_augment_dataset.py --method llm --trial 30             # the paraphrases, judged; llm_trial.md
    python scripts/08_augment_dataset.py --method textattack --trial 30      # the same with TextAttack; textattack_trial.md

and, with the model, every pair of set 1 (all correct: the ambiguous ones are in pairs_ambiguous.jsonl), not judged:

    python scripts/08_augment_dataset.py --method llm --all --no-judge --dry-run
    python scripts/08_augment_dataset.py --method llm --all --no-judge --budget 3   # data/dataset/set_1/augmented/

data/dataset/set_1/augmented/pairs.jsonl has one line per paraphrase: the pair it paraphrases with the paraphrase as
`nl`, id "<original id>:A<n>", `augmented_from` (the original id, to keep a paraphrase in the split of its original),
`augmentation` (how it was made, the numbers and symbols of the original it misses), `judge` and `original_nl` empty.
The paraphrases dropped after reading them (llm.DROPPED_BY_HAND) are in dropped.jsonl, with the reason.

The reports (src/augmentation/report.py) are written for readers who don't know the project.

TextAttack's paraphrases are made by src/augmentation/textattack_worker.py in .venv-augment (TextAttack doesn't
install in the project's .venv) and kept in data/processed/augmentation/trial_paraphrases.jsonl: a run makes them
again only when the sample changes, or with --regenerate. The model's paraphrases are kept in llm_answers.jsonl, the
judge's answers in answers.jsonl (not in step 7's file): a run makes only the calls not stored yet.
"""
import argparse
import collections
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import DATA_DIR
from src.augmentation import llm
from src.augmentation.paraphrase import (AUGMENT_DIR, METHODS, frozen_words, lost_frozen, missing_symbols, run_worker,
                                         trial_sample)
from src.augmentation.report import short, summary_table, write_llm_report, write_textattack_report
from src.dataset.judge import ANSWERS_FILE, build_messages, item_key, read_answers, run_calls, usable, vote
from src.dataset.sets import DATASET_DIR, SET_1, read_jsonl
from src.extraction.extractor import LOWEST_REASONING
from src.extraction.records import DEFAULT_MODELS, DEFAULT_TIE_BREAKER, parse_model

sys.stdout.reconfigure(encoding="utf-8")
PAIRED_RECORDS = DATA_DIR / "normalized" / "paired" / "records.jsonl"
PARAPHRASES = AUGMENT_DIR / "trial_paraphrases.jsonl"
JUDGE_ANSWERS = AUGMENT_DIR / "answers.jsonl"
MODELS = DEFAULT_MODELS + [DEFAULT_TIE_BREAKER]
LLM_METHODS = tuple(f"llm-{n}" for n in range(1, llm.K + 1))
# The `set` of the judge's items, one per way: their answers can't be taken for step 7's or for each other's
JUDGE_SET = {"textattack": "augment_set_1", "llm": "augment_llm_set_1"}
REPORT = {"textattack": AUGMENT_DIR / "textattack_trial.md", "llm": AUGMENT_DIR / "llm_trial.md"}
AUGMENTED_DIR = DATASET_DIR / SET_1 / "augmented"


# ---------------------------------------------------------------- the paraphrases, as lines {id, method, operation, text}

def textattack_lines(sample: list[dict], regenerate: bool = False, make: bool = True) -> list[dict] | None:
    """The worker's lines for the sample: the stored ones when they are of the same descriptions, else made again
    (None without `make`)."""
    if PARAPHRASES.exists() and not regenerate:
        stored = read_jsonl(PARAPHRASES)
        if sorted({p["id"] for p in stored}) == sorted(r["id"] for r in sample) and len(stored) == len(sample) * len(METHODS):
            if make:
                print(f"Paraphrases from {PARAPHRASES.relative_to(BASE_DIR)} (--regenerate to make them again)")
            return stored
    if not make:
        return None
    print(f"TextAttack on {len(sample)} descriptions ({len(METHODS)} methods each)", flush=True)
    return run_worker(sample, PARAPHRASES)


def llm_lines(sample: list[dict], records: dict, budget: float, workers: int, dry_run: bool) -> tuple[list[dict], float, str]:
    """
    The model's paraphrases of the sample (calls made only for those not stored), what they cost, and the reasoning
    they were asked with (the lowest the model accepts when it refuses "off").
    """
    model, reasoning = parse_model(llm.GENERATOR)
    items = llm.items_for(sample, records)
    if dry_run:
        print_generation_plan(items, model, reasoning)
        return [], 0.0, reasoning
    print(f"Paraphrases by {short(llm.GENERATOR)} (reasoning {reasoning}), {llm.K} per description:")
    stored = llm.generate(items, model, reasoning, workers=workers, budget=budget)
    lines, cost, used = [], 0.0, reasoning
    for item in items:
        row = stored.get((model, reasoning, item["id"]))
        if not llm.usable(row, item):
            continue
        cost += row.get("cost", 0)
        if any("asked with reasoning" in note for note in row.get("notes", [])):
            used = f"{LOWEST_REASONING} (it refuses off)"
        lines += [{"id": item["id"], "method": method, "operation": None, "text": text}
                  for method, text in zip(LLM_METHODS, row["paraphrases"])]
    return lines, cost, used


def print_generation_plan(items: list[dict], model: str, reasoning: str):
    """The model's calls a run would make, priced at the average of its stored calls."""
    stored = llm.read_answers()
    todo = sum(1 for i in items if not llm.usable(stored.get((model, reasoning, i["id"])), i))
    costs = [r["cost"] for k, r in stored.items() if k[:2] == (model, reasoning) and r.get("paraphrases")]
    price = f"about ${todo * sum(costs) / len(costs):.2f}" if costs else "no price stored yet: about a cent per call or less"
    print(f"{short(llm.GENERATOR)} (reasoning {reasoning}): {todo} of {len(items)} calls to make, "
          f"{llm.K} paraphrases each ({price})")


def augment_all(rows: list[dict], records: dict, budget: float, workers: int, dry_run: bool):
    """Every pair of set 1 paraphrased by the model, not judged, written to set_1/augmented/ (kept and dropped by hand)."""
    model, reasoning = parse_model(llm.GENERATOR)
    items = llm.items_for(rows, records)
    if dry_run:
        print_generation_plan(items, model, reasoning)
        return
    print(f"Paraphrases by {short(llm.GENERATOR)} (reasoning {reasoning}), {llm.K} per description:")
    stored = llm.generate(items, model, reasoning, workers=workers, budget=budget)
    answers = [stored[(model, reasoning, i["id"])] for i in items if llm.usable(stored.get((model, reasoning, i["id"])), i)]
    used = (f"{LOWEST_REASONING} (it refuses off)"
            if any("asked with reasoning" in n for a in answers for n in a.get("notes", [])) else reasoning)
    pairs = llm.augmented_pairs(rows, items, stored, model, reasoning, used)
    kept = [p for p in pairs if p["id"] not in llm.DROPPED_BY_HAND]
    dropped = [{**p, "dropped": llm.DROPPED_BY_HAND[p["id"]]} for p in pairs if p["id"] in llm.DROPPED_BY_HAND]
    AUGMENTED_DIR.mkdir(parents=True, exist_ok=True)
    for name, lines in (("pairs.jsonl", kept), ("dropped.jsonl", dropped)):
        with open(AUGMENTED_DIR / name, "w", encoding="utf-8") as out:
            out.writelines(json.dumps(p, ensure_ascii=False) + "\n" for p in lines)
    missing = sum(1 for p in kept if p["augmentation"]["missing_symbols"])
    print(f"\n{len(answers)} of {len(rows)} descriptions paraphrased (${sum(a.get('cost', 0) for a in answers):.2f}), "
          f"{len(pairs)} paraphrases: {len(kept)} kept ({missing} missing a number or symbol of the original), "
          f"{len(dropped)} dropped by hand\n -> {AUGMENTED_DIR.relative_to(BASE_DIR)}/")
    if len(answers) < len(rows):
        print(f"{len(rows) - len(answers)} descriptions without paraphrases yet: run again to make them.")


# ---------------------------------------------------------------- the judge

def judge_items(sample: list[dict], lines: list[dict], records: dict, judge_set: str) -> list[dict]:
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
        items.append({"set": judge_set, "id": row["id"], "count": len(texts), "messages": messages, "key": item_key(messages),
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
    words TextAttack was told to keep) and the numbers and symbols it misses (the check of the LLM trial).
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


def textattack_rows(sample: list[dict], records: dict) -> list[dict] | None:
    """The rows of the TextAttack trial on the same sample, from the stored data (no call); None if it wasn't run."""
    lines = textattack_lines(sample, make=False)
    if lines is None:
        return None
    items = judge_items(sample, lines, records, JUDGE_SET["textattack"])
    return results(sample, lines, items, read_answers(JUDGE_ANSWERS))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--method", required=True, choices=("textattack", "llm"), help="how to paraphrase")
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--trial", type=int, metavar="N", help="paraphrase N correct descriptions of set 1")
    which.add_argument("--all", action="store_true", help="llm: paraphrase every pair of set 1 into set_1/augmented/")
    parser.add_argument("--no-judge", action="store_true", help="only make the paraphrases (no judge, no report)")
    parser.add_argument("--regenerate", action="store_true", help="textattack: make the paraphrases again even if stored")
    parser.add_argument("--dry-run", action="store_true", help="only print the calls a run would make and their cost")
    parser.add_argument("--budget", type=float, default=2.0, help="dollars after which no new call is started (default 2)")
    parser.add_argument("--workers", type=int, default=8, help="calls made at the same time (default 8)")
    args = parser.parse_args()

    if args.all and (args.method != "llm" or not args.no_judge):
        parser.error("--all is only for --method llm, with --no-judge (judging the whole set is not designed yet)")
    pairs = read_jsonl(DATASET_DIR / SET_1 / "pairs.jsonl")
    records = {r["id"]: r for r in read_jsonl(PAIRED_RECORDS)}
    if args.all:
        augment_all(pairs, records, args.budget, args.workers, args.dry_run)
        return
    sample = trial_sample(pairs, args.trial)
    generation_cost, reasoning = 0.0, None
    if args.method == "textattack":
        lines = textattack_lines(sample, args.regenerate)
    else:
        lines, generation_cost, reasoning = llm_lines(sample, records, args.budget, args.workers, args.dry_run)
    if args.no_judge:
        if not args.dry_run:
            print(f"{len(lines)} paraphrases made, not judged (no report without the judge)")
        return
    items = judge_items(sample, lines, records, JUDGE_SET[args.method])
    if args.dry_run:
        dry_run(items, len(sample))
        return
    stored = judge(items, args.budget - generation_cost, args.workers)
    rows = results(sample, lines, items, stored)
    if args.method == "textattack":
        print("\n" + "\n".join(summary_table(rows, METHODS)))
        write_textattack_report(REPORT["textattack"], rows, sample, items, stored, MODELS)
    else:
        print("\n" + "\n".join(summary_table(rows, LLM_METHODS, lost=False)))
        write_llm_report(REPORT["llm"], rows, sample, items, stored, MODELS, LLM_METHODS, llm.GENERATOR, reasoning, llm.K,
                         generation_cost, textattack_rows(sample, records))
    print(f"\nThe report, with every paraphrase: {REPORT[args.method].relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
