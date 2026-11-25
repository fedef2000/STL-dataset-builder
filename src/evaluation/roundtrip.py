"""
Step 8, the round-trip check, the filter of the dataset: a model reads only the description and writes the formula;
the comparator (compare.py) says how close it is to the dataset's formula. Two models, one answer each, one
description per call, so that one description never helps to read another. A candidate is in the dataset when at
least one of the two models wrote its formula back (a match), or when it was kept or fixed by hand
(src/dataset/sets.py, split; src/dataset/manual.py).

The descriptions checked (sets 2 and 3 wait for their new stl-nl run):

    set_1        set_1/candidates.jsonl: every description of the papers (step 7)
    paraphrase   set_1/augmented/candidates.jsonl: the paraphrases of step 9

A description dropped by hand is not asked about. A description whose formula stlgen can't read (real or expression
bounds, powers, ...) is not_checkable and no model is asked about it either.

Two stages compare an answer with the dataset's formula: compare.py (written the same way, up to renaming: the `level`)
and, for the answers it doesn't match exactly (near, same_pattern, different), stlsat (sat.py: the same meaning, the
`sat` outcome). An answer matches when its level is equivalent, renamed or near, or stlsat finds it equivalent.
"""
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from config import PROCESSED_DIR
from src.dataset import sets
from src.dataset.manual import read_decisions
from src.dataset.sets import DATASET_DIR, SET_1, read_jsonl
from src.evaluation import sat
from src.evaluation.compare import compare
from src.evaluation.stlgen import parse_many
from src.extraction.extractor import LOWEST_REASONING, ExtractionError, post_request
from src.extraction.records import DEFAULT_MODELS, item_key, parse_model

MODELS = DEFAULT_MODELS            # gemini-3.8-flash (no reasoning) and gpt-6-luna (medium), the two of step 5
ANSWERS_FILE = PROCESSED_DIR / "roundtrip" / "answers.jsonl"
TRIAL_FILE = PROCESSED_DIR / "roundtrip" / "trial.md"
OUT_DIR = DATASET_DIR / "roundtrip"
MAX_OUTPUT_TOKENS = 8000
GROUPS = ("set_1", "paraphrase")
SET_1_DIR = DATASET_DIR / SET_1
AUGMENTED_DIR = SET_1_DIR / "augmented"
# From the closest to the farthest: the order in which a description's two answers are ranked
ORDER = ("equivalent", "renamed", "near", "same_pattern", "different", "unparseable")
MATCH = ("equivalent", "renamed", "near")
SAT_LEVELS = ("near", "same_pattern", "different")   # the levels whose answers stlsat checks

SYSTEM_PROMPT = """\
You translate a natural-language requirement into a Signal Temporal Logic (STL) formula. You get one description, \
from a scientific paper or written by a person; write the formula it states, using only what it says: add no \
condition, time bound or operator it doesn't give, and leave none out.

Syntax (follow it exactly; anything else can't be read):
- G[a,b] p: p holds at every time from a to b after now. F[a,b] p: p holds at some time from a to b after now.
  p U[a,b] q: q holds at some time from a to b after now, and p holds at every time from now until then.
  p R[a,b] q: release, the dual of until: !((!p) U[a,b] (!q)).
- Every G, F, U and R has an interval, written right after the letter: G[0,5], not G [0,5] or G.
- An interval end is closed with [ ] or open with ( ): [0,5], [0,5), (0,5]. A bound is a whole number (0, 5, 120), \
a name (T, t_1, T_max), or inf as upper bound: G[0,inf] p means p holds forever.
- ! not, && and, || or, -> implies, <-> if and only if; true, false.
- A comparison is two arithmetic expressions joined by < <= > >= == !=. Expressions use signals, numbers (3, -2, \
0.5, 1/3), + - * /, |e| for the absolute value, and parentheses. No powers (write x * x); no minus sign before a \
signal (write 0 - x); no chained comparisons (write (20 <= x) && (x <= 25), not 20 <= x <= 25).
- A name starts with a letter and has only letters, digits and _ (x_2, phi_A, speed). G, F, U, R, X, true, false and \
inf are not names.
- Put parentheses around every operand that is not a single name or comparison.

How to write it:
- Names: use exactly the names the description gives (x_2, phi_1, T_c). For something it names only in words, make \
up a short name (engine speed -> speed, "the door is open" -> door_open).
- A condition on a quantity with a number is a comparison (speed > 80); a condition without a number is a Boolean \
name (in_region_A, alarm_on).
- Numbers exactly as the description writes them, in its own units: don't convert minutes to seconds.
- Time bounds: "within 5" is [0,5], "for 5" is G[0,5], "between 2 and 4" is [2,4], "after 5" or "from 5 on" is \
[5,inf]. A time the description names (a deadline d, T_c) is a bound with that name.
- A requirement stated as a rule that must hold whenever its condition occurs ("whenever ...", "every time ...", \
"if ..., then ...", "X happens within 3 s after Y"), with no time window of its own, holds at all times: write it \
inside G[0,inf]. A goal reached once from the start ("reach A within 10 s") is not a rule: no G[0,inf].

Answer in JSON only: {"formula": "<the formula>"}.

Examples:

Description: Whenever the pressure exceeds 80, the valve must open within 3 seconds.
{"formula": "G[0,inf] ((pressure > 80) -> (F[0,3] valve_open))"}

Description: During the first 20 time units, x_t stays between 18 and 24.
{"formula": "G[0,20] ((x_t >= 18) && (x_t <= 24))"}

Description: The drone keeps its altitude above 10 until it is over the landing pad, which must happen within \
T_land seconds.
{"formula": "(altitude > 10) U[0,T_land] over_pad"}

Description: Between 5 and 15 s the robot visits region A, and it never enters region B.
{"formula": "(F[5,15] in_A) && (G[0,inf] !in_B)"}
"""
EXAMPLE_FORMULAS = re.findall(r'\{"formula": "(.*?)"\}\n', SYSTEM_PROMPT)

ANSWER_SCHEMA = {"type": "object", "properties": {"formula": {"type": "string"}}, "required": ["formula"],
                 "additionalProperties": False}


# ---------------------------------------------------------------- the descriptions

def candidates(group: str) -> list[dict]:
    """The candidates of a group, every one (an empty list while the file isn't written)."""
    path = (SET_1_DIR if group == "set_1" else AUGMENTED_DIR) / "candidates.jsonl"
    return read_jsonl(path) if path.exists() else []


def group_rows(group: str) -> list[dict]:
    """The candidates of a group the round trip checks: all but those dropped by hand."""
    dropped = {i for i, d in read_decisions().items() if d["action"] == "drop"}
    return [r for r in candidates(group) if r["id"] not in dropped]


def build_messages(description: str) -> list[dict]:
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"Description: {description}"}]


def items_of(groups=GROUPS) -> list[dict]:
    """One item per description: what the model reads, and the dataset's formula to compare with."""
    items = []
    for group in groups:
        for r in group_rows(group):
            messages = build_messages(r["nl"])
            items.append({"group": group, "id": r["id"], "nl": r["nl"], "stl": r["stl"], "formula_id": r["formula_id"],
                          "augmented_from": r.get("augmented_from"),
                          "messages": messages, "key": item_key(messages)})
    return items


def reference_trees(items: list[dict]) -> dict[str, dict | None]:
    """The dataset's formulas as trees, one stlgen call for all; None for those stlgen can't read (not checkable)."""
    parsed = parse_many({stl: stl for stl in sorted({i["stl"] for i in items})})
    return {stl: p["ast"] if p["ok"] else None for stl, p in parsed.items()}


# ---------------------------------------------------------------- the calls

def check_answer(text: str) -> tuple[str | None, list[str]]:
    """The formula of an answer, or None with the problems when it isn't {"formula": "<text>"}."""
    text = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    try:
        formula = json.loads(fenced.group(1) if fenced else text)["formula"]
        assert isinstance(formula, str) and formula.strip()
    except (ValueError, KeyError, TypeError, AssertionError) as exc:
        return None, [f"the answer is not the expected JSON ({type(exc).__name__})"]
    return formula.strip(), []


def build_request(model: str, messages: list[dict], reasoning: str, use_schema: bool = True) -> dict:
    """The request of one call through OpenRouter, with this answer's schema (strict JSON when the provider takes it)."""
    body = {"model": model, "messages": messages, "max_tokens": MAX_OUTPUT_TOKENS,
            "reasoning": {"effort": "none" if reasoning == "off" else reasoning}}
    if use_schema:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "formula", "strict": True, "schema": ANSWER_SCHEMA}}
        body["provider"] = {"require_parameters": True}
    else:
        body["response_format"] = {"type": "json_object"}
    return body


def ask(model: str, reasoning: str, messages: list[dict]) -> dict:
    """One call (with two fallbacks: lowest reasoning when a model can't answer without, plain JSON when the
    strict format is refused). The fields of the stored answer; `formula` is None when the answer failed its check."""
    notes, use_schema = [], True
    while True:
        try:
            data, seconds = post_request(build_request(model, messages, reasoning, use_schema))
            break
        except ExtractionError as exc:
            if reasoning == "off" and re.search(r"reasoning is mandatory|cannot be disabled", str(exc), re.IGNORECASE):
                reasoning = LOWEST_REASONING
                notes.append(f"this model cannot answer without reasoning: asked with reasoning {LOWEST_REASONING}")
            elif use_schema and re.search(r"HTTP (400|404|422)", str(exc)):
                use_schema = False
                notes.append(f"strict answer format refused ({exc}): plain JSON asked instead")
            else:
                raise
    usage = data.get("usage") or {}
    choice = data["choices"][0]
    answer = (choice.get("message") or {}).get("content") or ""
    formula, problems = check_answer(answer)
    if choice.get("finish_reason") == "length":
        problems.append("the answer was cut off at the output limit")
    return {"seconds": round(seconds, 2), "input_tokens": usage.get("prompt_tokens") or 0,
            "output_tokens": usage.get("completion_tokens") or 0,
            "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0,
            "cost": float(usage.get("cost") or 0), "notes": notes, "problems": problems, "formula": formula,
            "raw_answer": None if formula else answer}


def read_answers(answers_file: Path = ANSWERS_FILE) -> dict[tuple, dict]:
    """(model, reasoning, id) -> the last usable answer for the item as it is now; a failed one only if no other."""
    rows = {}
    if not answers_file.exists():
        return rows
    for line in open(answers_file, encoding="utf-8"):
        try:
            row = json.loads(line)
        except ValueError:
            continue   # a line cut short by an interruption: that call is made again
        key = (row["model"], row["reasoning"], row["id"])
        old = rows.get(key)
        if old is None or row.get("formula") or empty_answer(row) or not (old.get("formula") or empty_answer(old)) \
                or old["key"] != row["key"]:
            rows[key] = row
    return rows


NO_FORMULA = "the model wrote no formula: it found none to write in the description"


def empty_answer(row: dict | None) -> bool:
    """
    The model answered {"formula": ""}: it found no formula to write, as for a passage that only says what the formula
    is for. A final answer (asked again it gives the same), compared as unparseable: a miss for that model.
    """
    if not row or row.get("formula") or not row.get("raw_answer"):
        return False
    text = row["raw_answer"].strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    try:
        answer = json.loads(fenced.group(1) if fenced else text)
    except ValueError:
        return False
    return isinstance(answer, dict) and answer.get("formula") == ""


def usable(row: dict | None, item: dict) -> bool:
    """A stored answer counts only for the same description and prompt (the key hashes what the model reads)."""
    return bool(row and (row.get("formula") or empty_answer(row)) and row["key"] == item["key"])


def tasks_to_make(items: list[dict], stored: dict) -> list[tuple[str, str, dict]]:
    return [(*parse_model(label), item) for label in MODELS for item in items
            if not usable(stored.get((*parse_model(label), item["id"])), item)]


def run_calls(items: list[dict], workers: int = 8, budget: float = 5.0) -> float:
    """
    The calls of both models for `items` that have no usable stored answer, each appended to ANSWERS_FILE as it
    arrives (an interrupted run continues where it stopped). No new call starts once `budget` dollars are spent.
    Returns the dollars spent.
    """
    todo = tasks_to_make(items, read_answers())
    print(f"{len(items) * len(MODELS)} calls | {len(items) * len(MODELS) - len(todo)} already stored | {len(todo)} to make")
    if not todo:
        return 0.0
    spent, stop = [0.0], threading.Event()

    def call(task):
        model, reasoning, item = task
        if stop.is_set():
            return None
        row = {"model": model, "reasoning": reasoning, "id": item["id"], "group": item["group"], "key": item["key"]}
        try:
            return {**row, **ask(model, reasoning, item["messages"])}
        except ExtractionError as exc:
            return {**row, "error": str(exc), "formula": None}

    ANSWERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if ANSWERS_FILE.exists() and ANSWERS_FILE.stat().st_size and not ANSWERS_FILE.read_bytes().endswith(b"\n"):
        with open(ANSWERS_FILE, "a", encoding="utf-8") as out:
            out.write("\n")
    started, finished, failed = time.monotonic(), 0, 0
    with open(ANSWERS_FILE, "a", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=workers) as pool:
        try:
            for future in as_completed([pool.submit(call, task) for task in todo]):
                row = future.result()
                if row is None:
                    continue
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                out.flush()
                finished += 1
                spent[0] += row.get("cost", 0)
                if not row.get("formula"):
                    failed += 1
                    print(f"   FAILED | {row['model']} | {row['id']} | {row.get('error') or '; '.join(row['problems'])[:150]}")
                if finished % 50 == 0 or finished == len(todo):
                    print(f"   {finished}/{len(todo)} calls | {failed} failed | ${spent[0]:.2f} spent | {time.monotonic() - started:.0f} s")
                if spent[0] >= budget and not stop.is_set():
                    stop.set()
                    print(f"   Budget of ${budget:g} reached: no new call is started. Run again to continue.")
        except KeyboardInterrupt:
            stop.set()
            print("   Interrupted: no new call is started.")
            raise
    if failed:
        print(f"{failed} calls failed: run the same command again to retry them.")
    return spent[0]


def plan(items: list[dict], references: dict) -> None:
    """--dry-run: the calls still to make per model, priced at the average of that model's stored calls."""
    stored = read_answers()
    todo = tasks_to_make([i for i in items if references[i["stl"]] is not None], stored)
    total = 0.0
    for label in MODELS:
        model, reasoning = parse_model(label)
        n = sum(1 for t in todo if t[:2] == (model, reasoning))
        costs = [r["cost"] for k, r in stored.items() if k[:2] == (model, reasoning) and r.get("formula")]
        if costs:
            total += n * sum(costs) / len(costs)
            price = f"about ${n * sum(costs) / len(costs):.2f}"
        else:
            price = "cost unknown: no stored answer to price it (run --trial first)"
        print(f"  {short(label):<24} {n:>6} calls   {price}")
    print(f"  {'total':<24}               about ${total:.2f} (of the models with stored answers)")


def short(label: str) -> str:
    return label.split("/")[-1]


# ---------------------------------------------------------------- the comparison

def results(items: list[dict], references: dict, use_sat: bool = True, workers: int = 8) -> list[dict]:
    """
    One row per description: the dataset's formula (with stl_flag: unsatisfiable or valid for stlsat, see sat.py),
    and per model its formula and the comparator's verdict, with stlsat's outcome (sat, sat_mapping, sat_reason; None
    without use_sat, or for no answer or one stlgen can't read).
    """
    stored = read_answers()
    answers = {}
    for item in items:
        for label in MODELS:
            row = stored.get((*parse_model(label), item["id"]))
            if references[item["stl"]] is not None and usable(row, item):
                answers[(item["id"], label)] = row["formula"] or ""
    parsed = parse_many({f"{i}\t{label}": formula for (i, label), formula in answers.items() if formula})
    out = []
    for item in items:
        reference = references[item["stl"]]
        per_model = {}
        for label in MODELS:
            if reference is None:
                per_model[short(label)] = {"formula": None, **compare(None, None)}
                continue
            formula = answers.get((item["id"], label))
            if formula is None:
                per_model[short(label)] = {"formula": None, "level": None}   # no answer yet
                continue
            if formula == "":   # the model wrote none (empty_answer)
                per_model[short(label)] = {"formula": "", **compare(reference, None), "error": NO_FORMULA, "tree": None}
                continue
            p = parsed[f"{item['id']}\t{label}"]
            verdict = compare(reference, p["ast"] if p["ok"] else None)
            per_model[short(label)] = {"formula": formula, **verdict, "error": None if p["ok"] else p["error"],
                                       "tree": p["ast"] if p["ok"] else None}
        out.append({"id": item["id"], "group": item["group"], "formula_id": item["formula_id"],
                    "augmented_from": item["augmented_from"], "nl": item["nl"],
                    "stl": item["stl"], "stl_flag": None, "models": per_model, "best": best_level(per_model)})
    if use_sat:
        add_sat(out, references, workers)
    for row in out:
        for v in row["models"].values():
            v.pop("tree", None)
            if not use_sat and v.get("level") is not None:
                v |= {"sat": None, "sat_mapping": {}, "sat_reason": None}
    return out


def add_sat(rows: list[dict], references: dict, workers: int = 8) -> None:
    """
    stlsat's outcome on every answer (sat.py), in place: equivalent and renamed answers are equivalent already (no
    call); near, same_pattern and different ones are checked; the others (no answer, unparseable) get None. Then the
    flag of every dataset formula stlsat can take.
    """
    tasks = []
    for row in rows:
        for v in row["models"].values():
            v |= {"sat": None, "sat_mapping": {}, "sat_reason": None}
            if v.get("level") in ("equivalent", "renamed"):
                v |= {"sat": "equivalent", "sat_mapping": dict(v["mapping"])}
            elif v.get("level") in SAT_LEVELS:
                tasks.append((references[row["stl"]], v))
    formulas = sorted({row["stl"] for row in rows if references.get(row["stl"]) is not None
                       and sat.checkable(references[row["stl"]]) is None})
    print(f"stlsat: {len(tasks)} answers to check, {len(formulas)} dataset formulas to flag "
          f"(at most {sat.TIMEOUT} s per call, {workers} in parallel)")
    started, done = time.time(), [0]

    def one(task):
        reference, v = task
        v |= sat.check(reference, v["tree"], v.get("mapping"))
        done[0] += 1
        if done[0] % 200 == 0:
            print(f"  {done[0]}/{len(tasks)} answers checked ({time.time() - started:.0f} s)")
    flags = {}

    def flag(stl):
        flags[stl] = sat.reference_flag(references[stl])
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for future in as_completed([pool.submit(one, t) for t in tasks] + [pool.submit(flag, f) for f in formulas]):
            future.result()
    for row in rows:
        row["stl_flag"] = flags.get(row["stl"])
    print(f"stlsat done in {time.time() - started:.0f} s")


def best_level(per_model: dict) -> str | None:
    """The closest level of the description's answers; None while one is missing."""
    levels = [v["level"] for v in per_model.values()]
    if None in levels:
        return None
    if "not_checkable" in levels:
        return "not_checkable"
    return min(levels, key=ORDER.index)


def matched(verdict: dict) -> bool:
    """An answer matches: written the same way (equivalent, renamed, near) or, for stlsat, the same meaning."""
    return verdict["level"] in MATCH or verdict.get("sat") == "equivalent"


def any_match(row: dict) -> bool:
    return any(matched(v) for v in row["models"].values())


def both_match(row: dict) -> bool:
    return all(matched(v) for v in row["models"].values())


def both_miss(row: dict) -> bool:
    return not any_match(row)


def verdict(row: dict) -> dict:
    """What a description's round trip says, as stored in the dataset's rows (`roundtrip`): match, miss or
    not_checkable, and the closest level of its two answers."""
    if row["best"] == "not_checkable":
        return {"verdict": "not_checkable", "best": "not_checkable"}
    return {"verdict": "match" if any_match(row) else "miss", "best": row["best"]}


# ---------------------------------------------------------------- what is written

def details(verdict: dict) -> str:
    """The comparator's verdict in a few words, for the tables and the xlsx."""
    if verdict.get("level") in (None, "not_checkable"):
        return ""
    if verdict["level"] == "unparseable":
        return verdict.get("error") or ""
    parts = []
    if verdict.get("near"):
        parts.append("differs in: " + ", ".join(verdict["near"]))
    if verdict.get("mapping"):
        parts.append("renamed: " + ", ".join(f"{a} -> {b}" for a, b in verdict["mapping"].items()))
    if verdict["level"] in ("same_pattern", "different"):
        parts.append(f"bounds {'equal' if verdict['bounds_equal'] else 'differ'}, "
                     f"conditions {'equal' if verdict['leaves_equal'] else 'differ'}")
    return "; ".join(parts)


def sat_details(verdict: dict) -> str:
    """stlsat's outcome in a few words: the outcome, the renaming it used, or why it couldn't check."""
    outcome = verdict.get("sat")
    if outcome is None or verdict.get("level") in ("equivalent", "renamed"):
        return outcome or ""
    if outcome == "not_checkable":
        return f"not_checkable: {verdict['sat_reason']}"
    mapping = verdict.get("sat_mapping") or {}
    return outcome + (" (" + ", ".join(f"{a} -> {b}" for a, b in mapping.items()) + ")" if mapping else "")


def share(n: int, total: int) -> str:
    return f"{n} ({100 * n / total:.1f}%)" if total else "0"


def table(header: list[str], rows: list[list]) -> list[str]:
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(map(str, r)) + " |" for r in rows]


def review_sheets(rows: list[dict]) -> dict[str, list[dict]]:
    """The descriptions worth reading, and every row."""
    originals = {r["id"]: r for r in rows if r["group"] != "paraphrase"}

    def lost(r):   # a paraphrase whose original is matched and that itself is not
        original = originals.get(r["augmented_from"])
        return original is not None and any_match(original) and r["best"] != "not_checkable" and not any_match(r)
    return {
        "set 1, both miss": [r for r in rows if r["group"] == "set_1" and r["best"] != "not_checkable" and both_miss(r)],
        "paraphrase loses it": [r for r in rows if r["group"] == "paraphrase" and lost(r)],
        "all": rows,
    }


def write_report(rows: list[dict], path: Path, split_counts: dict[str, dict[str, int]]) -> None:
    labels = [short(label) for label in MODELS]
    lines = ["# Round-trip check", "",
             "Each description is given, alone, to a model, which writes the formula from it "
             f"(prompt: `src/evaluation/roundtrip.py`, models: {', '.join(labels)}, one answer each). The comparator "
             "(`src/evaluation/compare.py`) then says how close that formula is to the dataset's: equivalent (the same "
             "formula), renamed (the same with other names), near (the same apart from < vs <=, an open vs a closed "
             "interval end, or an outer G[0,inf]), same_pattern (the same structure, other bounds or conditions), "
             "different, or unparseable. For the answers at near, same_pattern or different, stlsat (`src/evaluation/sat.py`) "
             "then checks whether they mean the same: equivalent, stronger (the answer asks more), weaker, incomparable, "
             "unknown (past its time) or not_checkable. A match is one of the first three levels, or equivalent for "
             "stlsat. Groups: set 1 (every description of the papers, step 7) and the paraphrases of step 9. Not "
             "checkable: formulas stlgen can't read (real or expression bounds, powers); no model was asked about them. "
             "A description is in the dataset when at least one model matches it, or when it was kept or fixed by hand.",
             "", "## Size", ""]
    groups = [g for g in GROUPS if any(r["group"] == g for r in rows)]
    checkable = {g: [r for r in rows if r["group"] == g and r["best"] != "not_checkable"] for g in groups}
    lines += table(["Group", "Descriptions", "Checkable", "Not checkable"],
                   [[g, sum(1 for r in rows if r["group"] == g), len(checkable[g]),
                     sum(1 for r in rows if r["group"] == g) - len(checkable[g])] for g in groups])
    lines += ["", "## The dataset", "",
              "How the round trip splits the candidates (src/dataset/sets.py, split): in the dataset when a model wrote "
              "the formula back or when kept or fixed by hand; out when dropped by hand, when neither model wrote it "
              "back, when it can't be checked, or (a paraphrase) when its original is out.", ""]
    kept = ("match", "kept or fixed by hand")
    reasons = [k for k in sets.SHORT_REASONS.values() if any(k in c for c in split_counts.values())]
    lines += table(["Group", "Candidates", "In the dataset", *kept, "Out", *reasons],
                   [[g, sum(c.values()), sum(c[k] for k in kept), *(c[k] for k in kept),
                     sum(c.get(k, 0) for k in reasons), *(c.get(k, 0) for k in reasons)]
                    for g, c in split_counts.items()])
    lines += ["", "## Matches", "",
              "Share of the checkable descriptions whose formula each model matched, both matched, or neither did.", ""]
    lines += table(["Group"] + labels + ["Both", "Neither"],
                   [[g] + [share(sum(1 for r in checkable[g] if matched(r["models"][m])), len(checkable[g])) for m in labels]
                    + [share(sum(1 for r in checkable[g] if both_match(r)), len(checkable[g])),
                       share(sum(1 for r in checkable[g] if both_miss(r)), len(checkable[g]))] for g in groups])
    for m in labels:
        lines += ["", f"## Levels: {m}", ""]
        lines += table(["Group"] + list(ORDER),
                       [[g] + [share(sum(1 for r in checkable[g] if r["models"][m]["level"] == level), len(checkable[g]))
                               for level in ORDER] for g in groups])
    lines += ["", "## Near: what differs", "", "Answers at level near, by the details they differ in (one answer may differ in two).", ""]
    near = {m: {d: sum(1 for r in rows if d in (r["models"][m].get("near") or [])) for d in ("strict", "open_end", "outer_always")}
            for m in labels}
    lines += table(["Detail"] + labels, [[d] + [near[m][d] for m in labels] for d in ("strict", "open_end", "outer_always")])
    lines += sat_section(rows, checkable, groups, labels)
    if "paraphrase" in groups:
        originals = {r["id"]: r for r in rows if r["group"] != "paraphrase"}
        compared = [(r, originals[r["augmented_from"]]) for r in checkable["paraphrase"] if r["augmented_from"] in originals]
        rank = lambda r: ORDER.index(r["best"])
        lines += ["", "## Paraphrases against their originals", "",
                  "The closest level of a paraphrase's two answers against that of its original's.", ""]
        lines += table(["Paraphrase", "Paraphrases"],
                       [["closer", share(sum(1 for p, o in compared if rank(p) < rank(o)), len(compared))],
                        ["as close", share(sum(1 for p, o in compared if rank(p) == rank(o)), len(compared))],
                        ["farther", share(sum(1 for p, o in compared if rank(p) > rank(o)), len(compared))],
                        ["original matched, paraphrase not", share(sum(1 for p, o in compared if any_match(o) and not any_match(p)), len(compared))]])
    lines += ["", "## To read", "", "Sheets of `roundtrip.xlsx`:", ""]
    lines += table(["Sheet", "Descriptions", "Why"],
                   [["set 1, both miss", len(review_sheets(rows)["set 1, both miss"]), "neither model wrote the formula back, so the pair is out: keep it when the description is enough after all, fix the formula when the description is right and the formula opaque (phi for a condition the description spells out)"],
                    ["paraphrase loses it", len(review_sheets(rows)["paraphrase loses it"]), "the original's formula was matched, the paraphrase's not: it may lose something"],
                    ["all", len(rows), "every description"]])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def sat_section(rows: list[dict], checkable: dict, groups: list[str], labels: list[str]) -> list[str]:
    """The report's part on stlsat: outcomes of the answers it checked, the matches only it found, why it couldn't."""
    checked = lambda r, m: r["models"][m].get("level") in SAT_LEVELS and r["models"][m].get("sat") is not None
    if not any(checked(r, m) for r in rows for m in labels):
        return []
    lines = ["", "## Meaning (stlsat)", "",
             "The answers at near, same_pattern or different, checked by stlsat (discrete time, inclusive until; "
             "formulas with inf, named bounds or products not checkable). stronger: the answer implies the dataset's "
             "formula, not the converse; weaker: the converse.", ""]
    for m in labels:
        lines += ["", f"### {m}", ""]
        lines += table(["Group", "Checked"] + list(sat.OUTCOMES),
                       [[g, sum(1 for r in checkable[g] if checked(r, m))]
                        + [sum(1 for r in checkable[g] if checked(r, m) and r["models"][m]["sat"] == o) for o in sat.OUTCOMES]
                        for g in groups])
    lines += ["", "Matches found only by stlsat (the answer's level is same_pattern or different), per group and model:", ""]
    lines += table(["Group"] + labels,
                   [[g] + [sum(1 for r in checkable[g] if r["models"][m]["level"] in ("same_pattern", "different")
                                and r["models"][m].get("sat") == "equivalent") for m in labels] for g in groups])
    reasons = {}
    for r in rows:
        for m in labels:
            if checked(r, m) and r["models"][m]["sat"] == "not_checkable":
                reason = r["models"][m]["sat_reason"].split(" (")[0]
                reasons[reason] = reasons.get(reason, 0) + 1
    lines += ["", "Why stlsat couldn't check an answer (both models together):", ""]
    lines += table(["Reason", "Answers"], [[k, n] for k, n in sorted(reasons.items(), key=lambda x: -x[1])])
    flagged = {}
    for r in rows:
        if r["stl_flag"] in ("unsatisfiable", "valid"):
            flagged.setdefault((r["stl_flag"], r["stl"]), []).append(r["id"])
    lines += ["", "Dataset formulas that nothing satisfies (unsatisfiable) or everything does (valid), for stlsat: "
              "against them, equivalent says little.", ""]
    lines += table(["Flag", "Formula", "Descriptions"],
                   [[f, f"`{stl}`", ", ".join(ids)] for (f, stl), ids in sorted(flagged.items())]) if flagged else ["None."]
    return lines


DECISION_COLUMNS = ("decision", "fixed formula", "note")   # filled by hand in the review sheets (src/dataset/manual.py)


def write_xlsx(rows: list[dict], path: Path) -> None:
    """
    The review sheets and every row. The review sheets have three columns to fill by hand (DECISION_COLUMNS: keep, fix
    or drop, a paraphrase only keep or drop; the new formula for fix; why), shown with the decisions already in
    manual.jsonl.
    """
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from src.dataset.sets import ILLEGAL_XML
    decided = read_decisions()
    labels = [short(label) for label in MODELS]
    decision_values = {"decision": lambda d: d["action"], "fixed formula": lambda d: d["stl"] or "", "note": lambda d: d["note"]}
    base = [("id", 26, lambda r: r["id"]), ("group", 11, lambda r: r["group"]), ("nl", 60, lambda r: r["nl"]), ("stl", 45, lambda r: r["stl"])]
    decision_columns = [(name, 14 if name == "decision" else 40,
                         lambda r, name=name: decision_values[name](decided[r["id"]]) if r["id"] in decided else "")
                        for name in DECISION_COLUMNS]
    rest = [("best", 13, lambda r: r["best"] or ""), ("stl flag", 13, lambda r: r.get("stl_flag") or "")]
    for m in labels:
        rest += [(f"{m} formula", 45, lambda r, m=m: r["models"][m]["formula"] or ""),
                 (f"{m} level", 13, lambda r, m=m: r["models"][m]["level"] or ""),
                 (f"{m} details", 35, lambda r, m=m: details(r["models"][m])),
                 (f"{m} sat", 25, lambda r, m=m: sat_details(r["models"][m]))]
    book = openpyxl.Workbook()
    book.remove(book.active)
    to_fill = PatternFill("solid", fgColor="FFF2CC")
    for name, sheet_rows in review_sheets(rows).items():
        columns = base + (decision_columns if name != "all" else []) + rest
        sheet = book.create_sheet(name[:31])
        sheet.append([c[0] for c in columns])
        for cell in sheet[1]:
            cell.font = Font(bold=True)
            if cell.value in DECISION_COLUMNS:
                cell.fill = to_fill
        for r in sheet_rows:
            sheet.append([ILLEGAL_XML.sub("", str(c[2](r))) for c in columns])
        for n, (_, width, _) in enumerate(columns, 1):
            sheet.column_dimensions[openpyxl.utils.get_column_letter(n)].width = width
        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
        sheet.freeze_panes = "B2"
        sheet.auto_filter.ref = sheet.dimensions
    book.save(path)


def xlsx_decisions(path: Path = OUT_DIR / "roundtrip.xlsx") -> tuple[dict[str, dict], list[str]]:
    """
    The decisions written by hand in the review sheets: {id: {"action", "stl", "note"}} for every row with something in
    DECISION_COLUMNS, and the problems (the same id decided differently in two sheets).
    """
    import openpyxl
    if not path.exists():
        return {}, []
    found, problems = {}, []
    for sheet in openpyxl.load_workbook(path, read_only=True).worksheets:
        rows = sheet.iter_rows(values_only=True)
        header = list(next(rows, []))
        if not all(c in header for c in DECISION_COLUMNS):
            continue
        at = {c: header.index(c) for c in ("id",) + DECISION_COLUMNS}
        for values in rows:
            cell = lambda c: str(values[at[c]] or "").strip()
            if not any(cell(c) for c in DECISION_COLUMNS):
                continue
            decision = {"action": cell("decision").lower(), "stl": cell("fixed formula") or None, "note": cell("note")}
            old = found.setdefault(cell("id"), decision)
            if old != decision:
                problems.append(f"{cell('id')}: decided differently in two sheets")
    return found, problems


def not_imported(path: Path = OUT_DIR / "roundtrip.xlsx") -> list[str]:
    """The ids whose decision in the xlsx isn't in manual.jsonl as written there."""
    decided = read_decisions()
    found, problems = xlsx_decisions(path)
    return sorted({i for i, d in found.items()
                   if i not in decided or {k: decided[i][k] for k in ("action", "stl", "note")} != d}
                  | {p.split(":")[0] for p in problems})


def import_decisions(path: Path = OUT_DIR / "roundtrip.xlsx") -> bool:
    """
    The decisions of the xlsx into manual.jsonl, after checking every one (nothing is written if one is wrong). A
    decision already in manual.jsonl is replaced by the xlsx's; one emptied in the xlsx stays (edit manual.jsonl to
    remove it). Returns whether it was written.
    """
    from src.dataset.manual import ACTIONS, MANUAL_FILE, check_decision, is_paraphrase, write_decisions
    found, problems = xlsx_decisions(path)
    set_1 = {r["id"]: r for group in GROUPS for r in candidates(group)}
    parsed = parse_many({d["stl"]: d["stl"] for d in found.values() if d["stl"]})
    for i, d in sorted(found.items()):
        if i not in set_1:
            problems.append(f"{i}: not a pair of set 1 nor one of its paraphrases")
            continue
        problem = check_decision(d["action"], d["stl"], parsed.get(d["stl"]), is_paraphrase(i))
        if problem:
            problems.append(f"{i}: {problem}")
    if problems:
        print("Nothing imported; fix these in the xlsx first:\n" + "\n".join(f"   {p}" for p in problems))
        return False
    decisions = read_decisions()
    for i, d in found.items():
        row = set_1[i]
        decisions[i] = {"id": i, **d, "formula_before": row.get("stl_before_fix") or row["stl"]}
    write_decisions(decisions)
    counts = {a: sum(1 for d in decisions.values() if d["action"] == a) for a in ACTIONS}
    print(f"{len(found)} decisions read from {path.name}; {MANUAL_FILE.name} now has "
          + ", ".join(f"{a} {n}" for a, n in counts.items()))
    return True


def split_dataset(rows: list[dict]) -> dict[str, dict[str, int]]:
    """
    The candidates split by the round trip's verdicts and the decisions taken by hand (sets.split): set 1 into
    set_1/pairs.jsonl, dropped.jsonl and pairs1.xlsx, then its paraphrases (against set 1's new pairs) into
    set_1/augmented/pairs.jsonl and dropped.jsonl. A group without candidates is left as it is. Returns, per group,
    the candidates per outcome: match, by hand (kept or fixed), or why they are out.
    """
    verdicts = {r["id"]: verdict(r) for r in rows}
    decisions = read_decisions()
    counts, originals = {}, None
    for group, folder in (("set_1", SET_1_DIR), ("paraphrase", AUGMENTED_DIR)):
        found = candidates(group)
        if not found:
            continue
        pairs, dropped = sets.split(found, verdicts, decisions, originals if group == "paraphrase" else None)
        sets.write_split(pairs, dropped, folder, xlsx=group == "set_1")
        if group == "set_1":
            originals = {r["id"] for r in pairs}
        c = {"match": sum(1 for r in pairs if r["id"] not in decisions),
             "kept or fixed by hand": sum(1 for r in pairs if r["id"] in decisions)}
        for r in dropped:
            reason = sets.short_reason(r["dropped"])
            c[reason] = c.get(reason, 0) + 1
        counts[group] = c
    return counts


def write_outputs(rows: list[dict]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "results.jsonl", "w", encoding="utf-8") as out:
        out.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    counts = split_dataset(rows)
    for group, c in counts.items():
        print(f"{group}: {c['match'] + c['kept or fixed by hand']} in the dataset; "
              + ", ".join(f"{k} {n}" for k, n in c.items()))
    write_report(rows, OUT_DIR / "report.md", counts)
    pending = not_imported()
    if pending:   # the xlsx holds decisions written by hand that would be lost
        print(f"roundtrip.xlsx NOT rewritten: it has {len(pending)} decisions not in manual.jsonl yet "
              f"(run with --import-decisions first), e.g. {', '.join(pending[:3])}")
    else:
        write_xlsx(rows, OUT_DIR / "roundtrip.xlsx")
    return OUT_DIR


def write_trial(rows: list[dict], path: Path = TRIAL_FILE) -> Path:
    """The trial's descriptions one by one, with both answers and their verdicts, to read them."""
    labels = [short(label) for label in MODELS]
    lines = ["# Round-trip trial", "", f"{len(rows)} descriptions of set 1, models {', '.join(labels)}.", ""]
    for m in labels:
        counts = {level: sum(1 for r in rows if r["models"][m]["level"] == level) for level in ORDER + ("not_checkable",)}
        lines.append(f"- {m}: " + ", ".join(f"{level} {n}" for level, n in counts.items() if n))
    for r in rows:
        lines += ["", f"## {r['id']}", "", f"Description: {r['nl']}", "", f"    dataset   {r['stl']}"]
        for m in labels:
            v = r["models"][m]
            lines.append(f"    {m:<16}  {v['formula'] or '-'}")
            lines.append(f"    {'':<16}  -> {v['level']}" + (f" ({details(v)})" if details(v) else "")
                         + (f"; stlsat: {sat_details(v)}" if v.get("level") in SAT_LEVELS and v.get("sat") else ""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
