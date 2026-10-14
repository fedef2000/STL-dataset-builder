"""
Runs many extraction calls and keeps every answer: used by the full extraction (step 5) and by the model benchmark.
Each answer is appended to a .jsonl file as soon as it arrives, so an interrupted run continues where it stopped.
"""
import difflib
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.extraction import extractor as x


def read_answers(answers_file: Path) -> list[dict]:
    """The stored answers. A last line cut short by an interruption is skipped: that call is simply made again."""
    rows = []
    if not answers_file.exists():
        return rows
    for line in open(answers_file, encoding="utf-8"):
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def answer_key(row: dict) -> tuple:
    return (row["model"], row["reasoning"], row["run"], row["paper_id"], row["region"])


def latest_answers(answers_file: Path) -> dict[tuple, dict]:
    """One row per call, keyed by answer_key: the last answer received, a failed call never replacing a good one."""
    rows = {}
    for row in read_answers(answers_file):
        key = answer_key(row)
        if key not in rows or not row.get("error"):
            rows[key] = row
    return rows


def matches_region(row: dict, region) -> bool:
    """
    False when the stored answer was given for another text than the region as it is built now: the formulas of a
    paper are renumbered when the way they are found changes, and an old answer would then be read against the wrong IDs.
    """
    if "formulas" in row:
        return [(f["id"], without_spaces(f["source"])) for f in row["formulas"]] == [(f.id, without_spaces(f.source)) for f in region.formulas]
    # Rows stored before the formulas were recorded with them
    return row.get("line_start") == region.line_start and {e["id"] for e in row.get("extractions") or []} <= {f.id for f in region.formulas}


def unanswered(row: dict) -> int:
    """How many formulas of the region a stored answer leaves without an answer (skipped, or an answer that is not JSON)."""
    answered = {e["id"] for e in row.get("extractions") or []}
    return sum(1 for f in row.get("formulas") or [] if f["id"] not in answered)


def run_calls(tasks: list[tuple], regions: dict, answers_file: Path, workers: int = 8, budget: float = 15.0,
              retry_incomplete: bool = True) -> float:
    """
    Makes the calls of `tasks` that are not stored yet. A task is (model, reasoning, run, paper_id, region number);
    `regions` maps (paper_id, region number) to (PaperContext, Region). Stops starting new calls once `budget`
    dollars are spent in this invocation. With `retry_incomplete`, a call whose answer left formulas unanswered is
    made again (the benchmark keeps such answers: they are part of what it measures). Returns the dollars spent.
    """
    stored = latest_answers(answers_file)
    current = {key for key, row in stored.items() if not row.get("error") and key[3:] in regions and matches_region(row, regions[key[3:]][1])}
    incomplete = {key for key in current if retry_incomplete and unanswered(stored[key])}
    done = current - incomplete
    todo = [task for task in tasks if task not in done]
    outdated = sum(1 for task in todo if task in stored and not stored[task].get("error") and task not in incomplete)
    again = sum(1 for task in todo if task in incomplete)
    print(f"{len(tasks)} calls | {len(tasks) - len(todo)} already stored | {len(todo)} to make"
          + (f" ({outdated} of them again, because their region has changed since the stored answer)" if outdated else "")
          + (f" ({again} of them again, because the stored answer left formulas unanswered)" if again else ""))
    if not todo:
        return 0.0

    spent, stop = [0.0], threading.Event()

    def call(task):
        model, reasoning, run, pid, n = task
        if stop.is_set():
            return None
        paper, region = regions[(pid, n)]
        row = dict(model=model, reasoning=reasoning, run=run, paper_id=pid, region=n, file=region.file, line_start=region.line_start,
                   formulas=[dict(id=f.id, line=f.line, kind=f.kind, source=f.source) for f in region.formulas])
        try:
            result = x.extract_region(paper, region, model, reasoning)
        except x.ExtractionError as exc:
            return {**row, "error": str(exc)}
        return {
            **row, "seconds": round(result.seconds, 2), "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
            "reasoning_tokens": result.reasoning_tokens, "cost": result.cost, "notes": result.notes, "problems": result.problems,
            "extractions": [dict(id=e.id, formula=e.formula, requirements=e.requirements, domain=e.domain, variables=e.variables, problems=e.problems)
                            for e in result.extractions],
        }

    started, finished, failed = time.monotonic(), 0, 0
    answers_file.parent.mkdir(parents=True, exist_ok=True)
    if answers_file.exists() and answers_file.stat().st_size and not answers_file.read_bytes().endswith(b"\n"):
        with open(answers_file, "a", encoding="utf-8") as out:
            out.write("\n")   # close a line cut short by an interruption, so the next answer starts on its own line
    with open(answers_file, "a", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=workers) as pool:
        try:
            for future in as_completed([pool.submit(call, task) for task in todo]):
                row = future.result()
                if row is None:
                    continue
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                out.flush()
                finished += 1
                failed += 1 if row.get("error") else 0
                spent[0] += row.get("cost", 0)
                if row.get("error"):
                    print(f"   FAILED | {row['model']} ({row['reasoning']}) | {row['paper_id']} region {row['region']} | {row['error'][:120]}")
                if finished % 25 == 0 or finished == len(todo):
                    print(f"   {finished}/{len(todo)} calls | {failed} failed | ${spent[0]:.2f} spent | {time.monotonic() - started:.0f} s")
                if spent[0] >= budget and not stop.is_set():
                    stop.set()
                    print(f"   Budget of ${budget:g} reached: no new call is started. Run again with a higher --budget to continue.")
        except KeyboardInterrupt:
            stop.set()
            print("   Interrupted: the answers received so far are stored. Run the same command again to continue.")
    if failed:
        print(f"{failed} calls failed: run the same command again to retry them.")
    return spent[0]


# ---------------------------------------------------------------- comparing passages

def without_spaces(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def common_length(a: str, b: str) -> int:
    """Length of the longest passage two texts share."""
    return difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b)).size


def same_passage(a: str, b: str) -> bool:
    """Two requirement passages are the same when they share at least half of the shorter one (spacing aside)."""
    a, b = without_spaces(a), without_spaces(b)
    return bool(a and b) and common_length(a, b) >= 0.5 * min(len(a), len(b))


def nearly_equal(a: str, b: str) -> bool:
    a, b = without_spaces(a), without_spaces(b)
    shared = common_length(a, b)
    return bool(a and b) and shared / (len(a) + len(b) - shared) >= 0.9
