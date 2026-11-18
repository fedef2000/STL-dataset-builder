"""
Step 8, paraphrases written by a model: for each description, K paraphrases in one call (so that they differ from
each other), given the formula and the variable meanings so that the model knows what must not change. The answers
are kept in data/processed/augmentation/llm_answers.jsonl, as the judge keeps its own: an answer is used again while
what the model reads (prompt, formula, description) is the same, so a run makes only the calls not stored yet.
"""
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.augmentation.paraphrase import AUGMENT_DIR, missing_symbols
from src.dataset.judge import item_key
from src.extraction.extractor import LOWEST_REASONING, ExtractionError, post_request

GENERATOR = "anthropic/claude-sonnet-5.5:off"
K = 2   # paraphrases per description
LLM_ANSWERS = AUGMENT_DIR / "llm_answers.jsonl"
MAX_OUTPUT_TOKENS = 4000

# Paraphrases of set 1 dropped after reading them (the 16 the symbols check flagged were read; these 3 lose something)
DROPPED_BY_HAND = {
    "W4225679458:F5:D1:A1": "the name phi, the formula's only symbol, is left out",
    "W4225679458:F5:D1:A2": "the name phi, the formula's only symbol, is left out",
    "arxiv_2603.25531:F4:D1:A1": "V_EGM written out from the variable meanings, and 'below' made 'to or below' from the formula",
}

SYSTEM_PROMPT = """\
You paraphrase natural-language descriptions of Signal Temporal Logic (STL) formulas, for a dataset that teaches a \
model to write the formula from its description. You get one description, the formula it describes and, when known, \
the meanings of the formula's variables from the paper. Write {k} paraphrases of the description.

Each paraphrase must say exactly what the description says, so that someone who knows STL would write the same \
formula from it:
- Keep every number and every symbol exactly as written (T_c, phi_1, x_2, [a,b], 0.3). You may write a unit in full \
("s" as "seconds").
- Keep what the description talks about: the same signals, quantities, objects and regions. You may reword them \
("the speed of the engine" for "engine speed"), never replace them with something else.
- Keep the temporal and logical meaning, with its strength: "within 5 seconds" may become "no later than 5 seconds", \
but "less than" must not become "at most", nor "always" become "usually".
- Add nothing, remove nothing, make nothing more precise. The formula is given only so that you understand the \
description: take nothing from it that the description doesn't say. Where the description is vague, the paraphrase \
stays vague.
- Use no STL notation (G, F, U, temporal operators written as symbols) that the description doesn't use.

Variety: each paraphrase must differ from the description and from the other paraphrases in its sentence structure, \
not only in single words: change the order of the clauses, the voice (active or passive), the way the timing is \
said ("within", "no later than", "before ... has passed"), or the way a condition is said ("whenever", "every time", \
"if ..., then"). Write natural English, as the author of a scientific paper would.

Answer in JSON only: {{"paraphrases": [...]}} with exactly {k} strings.
"""

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"paraphrases": {"type": "array", "items": {"type": "string"}}},
    "required": ["paraphrases"],
    "additionalProperties": False,
}


def build_messages(description: str, formula: str, variables: dict[str, str] | None = None, k: int = K) -> list[dict]:
    """The messages of one call: the formula, the variable meanings when there are any, the description."""
    user = f"Formula:\n{formula}\n\n"
    if variables:
        user += "Variable meanings (from the paper):\n" + "".join(f"- {name}: {meaning}\n" for name, meaning in variables.items()) + "\n"
    user += f"Description:\n{description}\n"
    return [{"role": "system", "content": SYSTEM_PROMPT.format(k=k)}, {"role": "user", "content": user}]


def check_answer(text: str, k: int) -> tuple[list[str] | None, list[str]]:
    """The k paraphrases of an answer; None with the problems when it isn't {"paraphrases": [k non-empty strings]}."""
    text = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    try:
        items = json.loads(fenced.group(1) if fenced else text)["paraphrases"]
        assert isinstance(items, list)
    except (ValueError, KeyError, TypeError, AssertionError) as exc:
        return None, [f"the answer is not the expected JSON ({type(exc).__name__})"]
    texts = [" ".join(t.split()) for t in items if isinstance(t, str) and t.strip()]
    if len(texts) != k or len(texts) != len(items):
        return None, [f"the answer has {len(items)} paraphrases ({len(texts)} non-empty strings), not {k}"]
    return texts, []


def build_request(model: str, messages: list[dict], reasoning: str, use_schema: bool = True) -> dict:
    """As the judge's request (judge.build_request), with this answer schema."""
    body = {"model": model, "messages": messages, "max_tokens": MAX_OUTPUT_TOKENS,
            "reasoning": {"effort": "none" if reasoning == "off" else reasoning}}
    if use_schema:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "paraphrases", "strict": True, "schema": ANSWER_SCHEMA}}
        body["provider"] = {"require_parameters": True}
    else:
        body["response_format"] = {"type": "json_object"}
    return body


def ask(model: str, reasoning: str, messages: list[dict], k: int) -> dict:
    """One call, with the judge's fallbacks (reasoning that can't be off, strict schema refused)."""
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
    paraphrases, problems = check_answer(answer, k)
    if choice.get("finish_reason") == "length":
        problems.append("the answer was cut off at the output limit")
    return {"seconds": round(seconds, 2), "input_tokens": usage.get("prompt_tokens") or 0,
            "output_tokens": usage.get("completion_tokens") or 0, "cost": float(usage.get("cost") or 0),
            "notes": notes, "problems": problems, "paraphrases": paraphrases, "raw_answer": None if paraphrases else answer}


def items_for(sample: list[dict], records: dict, k: int = K) -> list[dict]:
    """One call per description of the sample, with the formula and variables the judge reads (step 6's `normalized`)."""
    items = []
    for row in sample:
        record = records[row["formula_id"]]
        messages = build_messages(row["nl"], record["normalized"], record.get("variables"), k)
        items.append({"id": row["id"], "messages": messages, "key": item_key(messages), "k": k})
    return items


def read_answers() -> dict[tuple, dict]:
    """(model, reasoning, id) -> the last usable answer; a failed one only if there is no other."""
    rows = {}
    if not LLM_ANSWERS.exists():
        return rows
    for line in open(LLM_ANSWERS, encoding="utf-8"):
        try:
            row = json.loads(line)
        except ValueError:
            continue
        key = (row["model"], row["reasoning"], row["id"])
        old = rows.get(key)
        if old is None or row.get("paraphrases") or not old.get("paraphrases") or old["key"] != row["key"]:
            rows[key] = row
    return rows


def usable(row: dict | None, item: dict) -> bool:
    return bool(row and row.get("paraphrases") and row["key"] == item["key"])


def generate(items: list[dict], model: str, reasoning: str, workers: int = 8, budget: float = 2.0) -> dict:
    """The calls not stored yet, each answer appended as it arrives; no new call once `budget` is spent. Returns the answers."""
    stored = read_answers()
    todo = [i for i in items if not usable(stored.get((model, reasoning, i["id"])), i)]
    print(f"{len(items)} calls | {len(items) - len(todo)} already stored | {len(todo)} to make")
    if not todo:
        return stored
    spent, stop, failed = [0.0], threading.Event(), 0

    def call(item):
        if stop.is_set():
            return None
        row = {"model": model, "reasoning": reasoning, "id": item["id"], "key": item["key"]}
        try:
            return {**row, **ask(model, reasoning, item["messages"], item["k"])}
        except ExtractionError as exc:
            return {**row, "error": str(exc), "paraphrases": None}

    LLM_ANSWERS.parent.mkdir(parents=True, exist_ok=True)
    with open(LLM_ANSWERS, "a", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=workers) as pool:
        for n, future in enumerate(as_completed([pool.submit(call, i) for i in todo]), 1):
            row = future.result()
            if row is None:
                continue
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            spent[0] += row.get("cost", 0)
            if not row.get("paraphrases"):
                failed += 1
                print(f"   FAILED | {row['id']} | {row.get('error') or '; '.join(row['problems'])[:150]}")
            if n % 10 == 0 or n == len(todo):
                print(f"   {n}/{len(todo)} calls | {failed} failed | ${spent[0]:.2f} spent")
            if spent[0] >= budget and not stop.is_set():
                stop.set()
                print(f"   Budget of ${budget:g} reached: no new call is started. Run again to continue.")
    return read_answers()


def augmented_pairs(rows: list[dict], items: list[dict], stored: dict, model: str, reasoning: str, used: str) -> list[dict]:
    """
    The dataset's lines of the paraphrases: each the pair it paraphrases with the paraphrase as `nl`, id
    "<original id>:A<n>" and `augmented_from` the original id. What belongs only to the original is emptied: `judge`
    (the paraphrase isn't judged) and `original_nl` (the paper's text). `augmentation` tells how it was made and
    lists the numbers and symbols of the original it misses (missing_symbols; none in the trial). A paraphrase identical
    to the original or to an earlier one of the same description is left out.
    """
    by_id = {i["id"]: i for i in items}
    out = []
    for row in rows:
        answer = stored.get((model, reasoning, row["id"]))
        if not usable(answer, by_id[row["id"]]):
            continue
        seen = {row["nl"]}
        for n, text in enumerate(answer["paraphrases"], 1):
            if text in seen:
                continue
            seen.add(text)
            out.append({**row, "id": f"{row['id']}:A{n}", "nl": text, "judge": None, "original_nl": None,
                        "augmented_from": row["id"],
                        "augmentation": {"method": "llm", "model": f"{model}:{reasoning}", "reasoning_used": used,
                                         "missing_symbols": missing_symbols(row["nl"], text, row["stl"])}})
    return out
