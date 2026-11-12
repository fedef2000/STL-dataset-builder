"""
The judge of step 7: a model reads a formula and its descriptions and says, for each description, whether it describes
the formula and whether what it says is faithful to it. One call per formula, with all its descriptions: they share the
formula and the meanings of its variables. The same call judges the three sets (paper descriptions, stl-nl descriptions
of paper formulas, stl-nl descriptions of stl-nl formulas); only the paper descriptions come with variable meanings.
"""
import hashlib
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from config import PROCESSED_DIR
from src.extraction.extractor import LOWEST_REASONING, ExtractionError, post_request


SYSTEM_PROMPT = """\
You check pairs of a Signal Temporal Logic (STL) formula and a natural-language description, for a dataset that teaches \
a model to write the formula from the description. You get one formula and one or more descriptions of it, each with an \
ID (D1, D2, ...). Judge each description on its own, against this formula only.

The syntax of the formula:
- G[a,b] phi: phi holds at every time in [a,b] from now ("always", "for", "during").
- F[a,b] phi: phi holds at some time in [a,b] from now ("eventually", "within", "at some point").
- phi U[a,b] psi: psi holds at some time in [a,b] from now, and phi holds until then.
- phi R[a,b] psi: release, the dual of until.
- ! not, && and, || or, -> implies, <-> if and only if; comparisons < <= > >= == != on signals, numbers and + - * / ^.
- An interval may be closed [a,b] or open on one side, as (a,b] or [a,b); its bounds may be numbers, names of \
parameters (F[0,T] phi), expressions (G[T,T + d] phi) or inf ([0,inf]: with no end).
- A name such as phi_1 or varphi_2 may stand for a subformula defined elsewhere; other names are signals or Boolean \
propositions.
- The formula is fully parenthesized.

The descriptions come from scientific papers or were written by a model, in plain text: symbols are written as in the \
formula (phi_1, x_dot, <=). When variable meanings are given, they come from the paper, keyed by the symbol as the paper \
writes it in LaTeX (\\mu_C is mu_C in the formula); use them to read the description, never to fill in what it leaves out.

For each description, answer:

problems: every concrete difference between the description and the formula, one short sentence each (for example \
"the formula bounds the response by 5, the description says 10", "the formula has no counterpart for G[0,20] (x > 0)", \
"the description does not say when the obstacle must be avoided"). Empty when there is none. Write them first, then \
decide the labels from them.

reason: one sentence that sums up the judgment.

describes: "yes" when the description states what this formula requires and every part of it has a counterpart in the \
description: each condition and each temporal operator, even if a detail of it (a time bound, a threshold) is vague or \
missing. "no" when it only says what the formula is for (its purpose, "the safety requirement of the robot"), when it \
describes only a part of the formula (a whole condition or temporal operator has no counterpart), or when it is about \
something else.

An implicit "always": when the formula's outermost operator is G and the description states a rule ("when ..., \
then ...", "whenever ...", "if ... then ...", "every time ...", "X occurs within 10 s after Y"), the rule counts as \
holding at every time, so that G has a counterpart even if the description doesn't say "always". This applies to \
the outermost G only: any other temporal operator with no counterpart is still a missing part. The interval of that \
G is read as [0,inf]: when the formula gives it another interval (G[0,30], G[0,T]) that the description doesn't \
state, that is a time bound not given.

faithful (only when describes is "yes", otherwise null):
- "correct": someone who knows STL, writing a formula from the description, would write this formula, up to the names \
of the signals and equivalent rewritings. Usual phrasing is fine: "within 5 seconds" for F[0,5], "for 2 seconds" for \
G[0,2], "always" for G over the whole interval, "above 3" for > 3 or >= 3 (unless the description insists on strict \
or not), "within 3" for [0,3) as for [0,3].
- "ambiguous": the description fits this formula, but also formulas that mean something else: a time bound or threshold \
not given or vague ("soon", "eventually" for F[0,10], "close to the target" for a distance below 0.5), an unclear \
scope or nesting ("always eventually" for G F or F G), an unclear order of an implication.
- "wrong": the description contradicts the formula: a different number, a different operator (always for eventually), \
a comparison in the other direction, a negation added or missing, an implication reversed, a different signal.

Answer in JSON only, with one item per description, in the order given.
"""

# Sets 2 and 3: the semantics of stl-nl (its docs/SEMANTICS.md), which its descriptions follow and the usual reading
# of STL doesn't: discrete steps, intervals that include both ends, an until whose left operand holds also at the step
# where the right one holds. Without it the judges call such descriptions wrong (tried on 200 formulas of each set).
STLNL_SEMANTICS = """\
The semantics of these formulas, which the descriptions follow (where it differs from the usual reading of STL, this \
one holds):
- Time is discrete: steps 0, 1, 2, ... The formula is evaluated at step 0; every interval is relative to the step at \
which its subformula is evaluated.
- Every interval [a,b] is closed and contains both ends: G[0,5] p covers the six steps 0 to 5, G[1,2] p means p at \
steps 1 and 2, F[2,3] p means p at step 2 or at step 3. Naming the steps of an interval, or counting them ("six \
consecutive steps"), is correct.
- p U[a,b] q: there is a step tau in [a,b] at which q holds, and p holds at every step from now up to and including \
tau. A description where p holds "up to and including" the step of q is correct.
- p R[a,b] q is the negation of (!p) U[a,b] (!q): at every step tau in [a,b], q holds at tau or p holds at some step \
from now up to and including tau.
- A name in a bound (F[0,T]) is a parameter: a fixed but unspecified number of steps. inf means no upper limit.

"""
STLNL_SYSTEM_PROMPT = SYSTEM_PROMPT.replace("For each description, answer:", STLNL_SEMANTICS + "For each description, answer:")

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "descriptions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "problems": {"type": "array", "items": {"type": "string"}},
                    "reason": {"type": "string"},
                    "describes": {"type": "string", "enum": ["yes", "no"]},
                    # anyOf, not a nullable type: Anthropic's models refuse ["string", "null"] with an enum (HTTP 400)
                    "faithful": {"anyOf": [{"type": "string", "enum": ["correct", "ambiguous", "wrong"]}, {"type": "null"}]},
                },
                "required": ["id", "problems", "reason", "describes", "faithful"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["descriptions"],
    "additionalProperties": False,
}


def build_messages(formula: str, descriptions: list[str], variables: dict[str, str] | None = None,
                   stlnl: bool = False) -> list[dict]:
    """
    The messages of one call: the formula, the variable meanings when there are any, the descriptions D1, D2, ...
    With `stlnl` (sets 2 and 3) the instructions also give stl-nl's semantics.
    """
    user = f"Formula:\n{formula}\n\n"
    if variables:
        user += "Variable meanings (from the paper):\n" + "".join(f"- {name}: {meaning}\n" for name, meaning in variables.items()) + "\n"
    user += "Descriptions:\n" + "".join(f"D{n}: {text}\n" for n, text in enumerate(descriptions, 1))
    return [{"role": "system", "content": STLNL_SYSTEM_PROMPT if stlnl else SYSTEM_PROMPT}, {"role": "user", "content": user}]


# ---------------------------------------------------------------- the call

ANSWERS_FILE = PROCESSED_DIR / "judgments" / "answers.jsonl"
MAX_OUTPUT_TOKENS = 16000
# The label of a description: "no" when it doesn't describe the formula, else how faithful it is
LABELS = ("correct", "ambiguous", "wrong", "no")


def build_request(model: str, messages: list[dict], reasoning: str, use_schema: bool = True) -> dict:
    """As step 5's request (extractor.build_request), with the judge's answer schema."""
    body = {"model": model, "messages": messages, "max_tokens": MAX_OUTPUT_TOKENS,
            "reasoning": {"effort": "none" if reasoning == "off" else reasoning}}
    if use_schema:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "judgments", "strict": True, "schema": ANSWER_SCHEMA}}
        body["provider"] = {"require_parameters": True}
    else:
        body["response_format"] = {"type": "json_object"}
    return body


def check_answer(text: str, count: int) -> tuple[list[dict] | None, list[str]]:
    """
    The judgments of an answer, one per description in order, each with its `label` (LABELS); None with the problems
    when the answer can't be used: not the JSON asked, an ID missing or repeated, `faithful` given with describes "no"
    or missing with "yes".
    """
    text = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    try:
        items = json.loads(fenced.group(1) if fenced else text)["descriptions"]
        assert isinstance(items, list)
    except (ValueError, KeyError, TypeError, AssertionError) as exc:
        return None, [f"the answer is not the expected JSON ({type(exc).__name__})"]
    expected = [f"D{n}" for n in range(1, count + 1)]
    ids = [item.get("id") if isinstance(item, dict) else None for item in items]
    if ids != expected:
        return None, [f"the answer has the descriptions {ids}, not {expected}"]
    out, problems = [], []
    for item in items:
        describes, faithful = item.get("describes"), item.get("faithful")
        if describes == "no" and faithful is None:
            label = "no"
        elif describes == "yes" and faithful in LABELS[:3]:
            label = faithful
        else:
            problems.append(f"{item['id']}: describes {describes!r} with faithful {faithful!r}")
            continue
        out.append({"id": item["id"], "label": label, "problems": [str(p) for p in item.get("problems") or []],
                    "reason": str(item.get("reason") or "")})
    return (None if problems else out), problems


def ask(model: str, reasoning: str, messages: list[dict], count: int) -> dict:
    """One call. The fields of the stored answer row; `judgments` is None when the answer failed its check."""
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
    judgments, problems = check_answer(answer, count)
    if choice.get("finish_reason") == "length":
        problems.append("the answer was cut off at the output limit")
    return {"seconds": round(seconds, 2), "input_tokens": usage.get("prompt_tokens") or 0,
            "output_tokens": usage.get("completion_tokens") or 0,
            "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0,
            "cost": float(usage.get("cost") or 0), "notes": notes, "problems": problems, "judgments": judgments,
            "raw_answer": None if judgments else answer}


# ---------------------------------------------------------------- the items and the stored answers

def item_key(messages: list[dict]) -> str:
    """A hash of what the model reads: a stored answer counts only for the same formula, descriptions and prompt."""
    return hashlib.sha256(json.dumps(messages, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def paper_items(records: list[dict]) -> list[dict]:
    """
    Set 1: one item per record of data/normalized/paired/records.jsonl, with its normalized passages. The judge reads
    the formula as step 6 normalizes it (`normalized`, fully parenthesized), as it did when set 1 was judged.
    """
    items = []
    for r in records:
        descriptions = [p["normalized"] for p in r["requirements"]]
        messages = build_messages(r["normalized"], descriptions, r.get("variables"))
        items.append({"set": "set_1", "id": r["id"], "count": len(descriptions), "messages": messages,
                      "key": item_key(messages), "formula": r["normalized"], "descriptions": descriptions,
                      "kinds": [p["kind"] for p in r["requirements"]]})
    return items


def stlnl_items(rows: list[dict]) -> list[dict]:
    """
    Sets 2 and 3: one item per formula, with all the descriptions stl-nl wrote of it (the rows of sets.stlnl_rows, in
    their order), and no variable meanings. The judge reads the formula as stl-nl wrote it, as its describer did, and
    the semantics of stl-nl (STLNL_SEMANTICS).
    """
    by_formula: dict[str, list[dict]] = {}
    for row in rows:
        by_formula.setdefault(row["formula_id"], []).append(row)
    items = []
    for formula_id, described in by_formula.items():
        descriptions = [r["nl"] for r in described]
        messages = build_messages(described[0]["stl"], descriptions, stlnl=True)
        items.append({"set": described[0]["set"], "id": formula_id, "count": len(descriptions), "messages": messages,
                      "key": item_key(messages), "formula": described[0]["stl"], "descriptions": descriptions,
                      "kinds": [None] * len(descriptions)})
    return items


def read_answers(answers_file: Path = ANSWERS_FILE) -> dict[tuple, dict]:
    """(model, reasoning, set, id) -> the last usable answer for the item as it is now; a failed one only if no other."""
    rows = {}
    if not answers_file.exists():
        return rows
    for line in open(answers_file, encoding="utf-8"):
        try:
            row = json.loads(line)
        except ValueError:
            continue   # a line cut short by an interruption: that call is made again
        key = (row["model"], row["reasoning"], row["set"], row["id"])
        old = rows.get(key)
        if old is None or row.get("judgments") or not old.get("judgments") or old["key"] != row["key"]:
            rows[key] = row
    return rows


def usable(row: dict | None, item: dict) -> bool:
    return bool(row and row.get("judgments") and row["key"] == item["key"])


def run_calls(tasks: list[tuple[str, str, dict]], answers_file: Path = ANSWERS_FILE, workers: int = 8,
              budget: float = 10.0) -> float:
    """
    Makes the calls of `tasks` (model, reasoning, item) that have no usable stored answer. Each answer is appended to
    `answers_file` as it arrives, so an interrupted run continues where it stopped. Stops starting new calls once
    `budget` dollars are spent. Returns the dollars spent.
    """
    stored = read_answers(answers_file)
    todo = [t for t in tasks if not usable(stored.get((t[0], t[1], t[2]["set"], t[2]["id"])), t[2])]
    print(f"{len(tasks)} calls | {len(tasks) - len(todo)} already stored | {len(todo)} to make")
    if not todo:
        return 0.0
    spent, stop = [0.0], threading.Event()

    def call(task):
        model, reasoning, item = task
        if stop.is_set():
            return None
        row = {"model": model, "reasoning": reasoning, "set": item["set"], "id": item["id"], "key": item["key"]}
        try:
            return {**row, **ask(model, reasoning, item["messages"], item["count"])}
        except ExtractionError as exc:
            return {**row, "error": str(exc), "judgments": None}

    answers_file.parent.mkdir(parents=True, exist_ok=True)
    if answers_file.exists() and answers_file.stat().st_size and not answers_file.read_bytes().endswith(b"\n"):
        with open(answers_file, "a", encoding="utf-8") as out:
            out.write("\n")
    started, finished, failed = time.monotonic(), 0, 0
    with open(answers_file, "a", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=workers) as pool:
        try:
            for future in as_completed([pool.submit(call, task) for task in todo]):
                row = future.result()
                if row is None:
                    continue
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                out.flush()
                finished += 1
                spent[0] += row.get("cost", 0)
                if not row.get("judgments"):
                    failed += 1
                    print(f"   FAILED | {row['model']} | {row['id']} | {row.get('error') or '; '.join(row['problems'])[:150]}")
                if finished % 25 == 0 or finished == len(todo):
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


# ---------------------------------------------------------------- the vote

def vote(labels: list[str | None], third: str | None) -> tuple[str, str]:
    """
    The final label of one description from the labels of the first two models and, when they differ, of the third:
    (label, how). The two agree -> their label. They differ -> the label at least two of the three give, or
    "undecided" when all three differ; "disputed" while the third hasn't answered. "unjudged" while one of the first
    two hasn't answered.
    """
    if None in labels:
        return "unjudged", "a model has no answer yet"
    if labels[0] == labels[1]:
        return labels[0], "agreed"
    if third is None:
        return "disputed", "the two models differ, the third not asked yet"
    if third in labels:
        return third, "decided by the third model"
    return "undecided", "all three models differ"
