"""
The extraction call: one request to a model (through OpenRouter) per region of a paper. The model answers once per
marked formula with the formula itself, every passage of the paper that states what it requires (possibly none), the
application domain and the meaning of the variables. Every answer is then checked against the region: the formula and
the requirement must be copied from it, not rewritten.
"""
import json
import re
import time
from dataclasses import dataclass, field

import requests

from config import OPENROUTER_API_KEY
from src.extraction.context import MARK_CLOSE, MARK_OPEN, PaperContext, Region

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
REQUEST_TIMEOUT = 300
# Rate limit or a provider that is down: seconds to wait before each new try
RETRY_WAITS = (5, 20, 60)
# Room for the answer and, when reasoning is on, for the reasoning that precedes it
MAX_OUTPUT_TOKENS = 16000

# "generic": an abstract example over an unnamed signal, with no application behind it
DOMAINS = ("aerial robotics", "automotive", "aviation", "epidemiology", "industrial machinery", "marine robotics", "mechatronics", "mobile robotics", "power systems", "railway", "robotic manipulation", "smart city", "smart home", "social dynamics", "generic")
# A specific passage carries the particulars of its formula (numbers, thresholds, named regions); a generic one only
# says what the formula is for. The kind lets the final dataset be sorted by quality.
REQUIREMENT_KINDS = ("specific", "generic")
REASONING_LEVELS = ("off", "minimal", "low", "medium", "high")
# Used in place of "off" for a model that cannot answer without reasoning
LOWEST_REASONING = "minimal"

SYSTEM_PROMPT = f"""You read excerpts of the LaTeX source of scientific papers that use Signal Temporal Logic (STL). \
In each excerpt some formulas are marked: {MARK_OPEN.format(id='F1')} opens the formula with ID F1 and \
{MARK_CLOSE.format(id='F1')} closes it. For every marked formula you report four things.

1. formula: the formula itself, copied character for character from between its markers. Leave out the math \
delimiters and environment commands around it ($, \\[, \\begin{{equation}}, \\label{{...}}, &, \\\\) and punctuation \
that belongs to the sentence. Keep a name the paper gives it (e.g. "\\varphi_1 = ..."). Do not expand macros, \
fix typos or change spacing inside the formula.

2. requirements: every passage of the excerpt that states in natural language what this formula requires, each \
copied character for character, LaTeX commands included. A paper often states the same requirement more than once \
in different words, e.g. once before the formula and again after it: report every such passage as its own item, in \
the order they appear. Do not pick one and do not merge them. Every passage is given a kind:
   - "specific": it carries the particulars of this formula, i.e. its numbers, thresholds, time bounds or named \
regions, even if not all of them. E.g. "the vehicle must reach the goal within 10 seconds".
   - "generic": it says what the formula is for without those particulars. E.g. "the vehicle reaches a goal \
location within a certain time limit" or "this bounds the number of spreaders from above". The test: if the \
numbers of the formula were replaced by others and the passage would still fit, it is generic.
   Report every specific passage. Report a generic passage only when the excerpt has no specific one for this \
formula; then report the generic ones. Never mix the two kinds for one formula.
Rules:
   - It must say what this particular formula demands of the system, e.g. "the vehicle must reach the goal within \
10 seconds". A general explanation of an operator, of the logic or of the notation is not a requirement.
   - It must state the behaviour itself: what has to happen or hold. A passage that only names, announces or \
motivates the formula is not a requirement, e.g. "we must add a mutual separation formula", "the safety \
specification is" or "consider the following property". Nor is a passage that only explains a symbol of the \
formula, e.g. "in which $s$ is a lower bound on the separation": that belongs under variables. If the excerpt says \
nothing more than this about the formula, give an empty list.
   - Each item is the shortest passage that states the whole requirement: usually one sentence or part of one. Leave out \
lead-ins such as "This is expressed by the formula" or "the specification", and the quotation marks when the paper \
puts the requirement in quotes.
   - When one sentence states the requirements of several formulas, give each formula the part that concerns it.
   - Never write or complete a requirement yourself. If the excerpt does not state one for this formula, give an \
empty list. \
Many marked formulas have none: definitions of the syntax or semantics, formulas in tables, formulas used only in \
a proof or a benchmark list.

3. domain: the application area of the system this formula is about, one of: {", ".join(DOMAINS)}. \
Use "generic" when the formula is an abstract example over unnamed signals with no application behind it. \
The title and abstract of the paper help here, but judge the formula: a paper on drones may still give a generic example.

4. variables: for each signal, predicate, region or parameter name that appears in the formula, its symbol copied \
from the formula and a short explanation of what it stands for, with the unit when the excerpt gives one. \
Do not list temporal or logical operators or numbers. Take the meaning from the excerpt; when the excerpt does not \
explain a symbol, say what can be inferred and add "(not explained in the excerpt)".

Answer with one JSON object and nothing else: {{"formulas": [{{"id": "F1", "formula": "...", "requirements": [{{"text": "...", "kind": "specific"}}], \
"domain": "...", "variables": [{{"symbol": "...", "meaning": "..."}}]}}]}}. Give exactly one entry for every \
marked ID, in the order they appear. Formulas that are not marked are not to be reported."""

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "formulas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "formula": {"type": "string"},
                    "requirements": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"text": {"type": "string"}, "kind": {"type": "string", "enum": list(REQUIREMENT_KINDS)}},
                            "required": ["text", "kind"],
                            "additionalProperties": False,
                        },
                    },
                    "domain": {"type": "string", "enum": list(DOMAINS)},
                    "variables": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"symbol": {"type": "string"}, "meaning": {"type": "string"}},
                            "required": ["symbol", "meaning"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["id", "formula", "requirements", "domain", "variables"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["formulas"],
    "additionalProperties": False,
}


@dataclass
class Extraction:
    """The answer for one marked formula, with the result of the checks."""
    id: str
    formula: str
    requirements: list[dict]    # every passage that states the requirement, as {"text", "kind"}; empty when the paper states none
    domain: str
    variables: dict[str, str]
    problems: list[str] = field(default_factory=list)


@dataclass
class RegionResult:
    model: str
    extractions: list[Extraction] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)   # about the answer as a whole, e.g. a formula left out
    notes: list[str] = field(default_factory=list)      # how the request had to be changed for this model
    seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0      # includes the reasoning tokens
    reasoning_tokens: int = 0
    cost: float = 0.0           # in dollars, as charged by OpenRouter
    raw_answer: str = ""


class ExtractionError(Exception):
    """The request could not be completed (no key, refused, no usable answer after the retries)."""


def build_messages(paper: PaperContext, region: Region) -> list[dict]:
    """The paper header comes first and is the same for every region of a paper, so providers can cache it."""
    ids = ", ".join(f.id for f in region.formulas)
    user = (
        f"Paper title: {paper.title or '(unknown)'}\n"
        f"Abstract: {paper.abstract or '(not available)'}\n\n"
        f"Excerpt from the file {region.file}"
        + (f", section: {' > '.join(region.section)}" if region.section else "")
        + f"\n-----\n{region.marked_text()}\n-----\n\n"
        f"Marked formulas to report: {ids}"
    )
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def build_request(model: str, messages: list[dict], reasoning: str = "off", use_schema: bool = True) -> dict:
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "reasoning": {"effort": "none" if reasoning == "off" else reasoning},
    }
    # No temperature: some models (e.g. Claude Sonnet 5.5) accept no fixed temperature, and every model gets the same request
    if use_schema:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "formula_extractions", "strict": True, "schema": ANSWER_SCHEMA}}
        # Only providers that enforce the schema, otherwise the format would silently depend on the routing
        body["provider"] = {"require_parameters": True}
    else:
        body["response_format"] = {"type": "json_object"}
    return body


def post_request(body: dict) -> tuple[dict, float]:
    """Sends the request and returns (response, seconds of the try that succeeded). Waits and retries on overload."""
    if not OPENROUTER_API_KEY:
        raise ExtractionError("OPENROUTER_API_KEY is not set: add it to the .env file")
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    last = ""
    for wait in (0,) + RETRY_WAITS:
        time.sleep(wait)
        started = time.monotonic()
        try:
            resp = requests.post(OPENROUTER_URL, headers=headers, json=body, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            last = f"{type(exc).__name__}: {exc}"
            continue
        seconds = time.monotonic() - started
        try:
            data = resp.json()
        except ValueError:
            data = {}
        # OpenRouter also reports provider failures inside a 200 answer
        error = data.get("error") or ({} if resp.ok else {"message": resp.text[:300]})
        if not error and data.get("choices"):
            return data, seconds
        code = error.get("code") or resp.status_code
        last = f"HTTP {code}: {error.get('message') or 'empty answer'}"
        if code not in (408, 429, 500, 502, 503, 504, 529):
            break
    raise ExtractionError(last)


def parse_answer(text: str) -> list[dict]:
    """The list under "formulas" of the model's answer. Raises ValueError when the answer is not that JSON object."""
    text = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    data = json.loads(text)
    if not isinstance(data, dict) or not isinstance(data.get("formulas"), list):
        raise ValueError('the answer has no "formulas" list')
    return data["formulas"]


def _without_spaces(text: str) -> str:
    return re.sub(r"\s+", "", text)


def check_answer(region: Region, items: list[dict]) -> tuple[list[Extraction], list[str]]:
    """
    Turns the model's entries into Extractions and checks them against the region. Line breaks and spacing are not
    compared: a requirement copied across a line break of the source is still a copy.
    """
    marked = {f.id: f for f in region.formulas}
    region_text = _without_spaces(region.text)
    extractions, problems, seen = [], [], set()
    for item in items:
        if not isinstance(item, dict):
            problems.append("an entry is not an object")
            continue
        fid = str(item.get("id", ""))
        if fid not in marked:
            problems.append(f"answer for {fid or 'an entry without ID'}, which is not marked in this region")
            continue
        if fid in seen:
            problems.append(f"{fid} answered twice: the second answer is dropped")
            continue
        seen.add(fid)
        given = item.get("requirements")
        requirements = []
        for passage in given if isinstance(given, list) else []:
            text = passage.get("text") if isinstance(passage, dict) else passage
            kind = passage.get("kind") if isinstance(passage, dict) else None
            # Some models write the word instead of leaving the list empty; the same passage twice counts once
            if isinstance(text, str) and text.strip().lower() not in ("", "null", "none") \
                    and _without_spaces(text) not in [_without_spaces(r["text"]) for r in requirements]:
                requirements.append({"text": text, "kind": str(kind or "")})
        variables = {}
        for v in item.get("variables") or []:
            if isinstance(v, dict) and v.get("symbol"):
                variables[str(v["symbol"])] = str(v.get("meaning") or "")
        x = Extraction(id=fid, formula=str(item.get("formula") or ""), requirements=requirements,
                       domain=str(item.get("domain") or ""), variables=variables)

        if not x.formula.strip():
            x.problems.append("no formula given")
        elif _without_spaces(x.formula) not in _without_spaces(marked[fid].source):
            x.problems.append("the formula is not a copy of the marked text")
        for n, passage in enumerate(x.requirements, 1):
            which = f" (passage {n})" if len(x.requirements) > 1 else ""
            if _without_spaces(passage["text"]) not in region_text:
                x.problems.append("the requirement is not a copy of the excerpt" + which)
            if passage["kind"] not in REQUIREMENT_KINDS:
                x.problems.append(f"unknown kind of requirement: {passage['kind'] or '(none)'}" + which)
        if len({passage["kind"] for passage in x.requirements}) > 1:
            x.problems.append("specific and generic requirements given together")
        if x.domain not in DOMAINS:
            x.problems.append(f"unknown domain: {x.domain or '(none)'}")
        for symbol in x.variables:
            if _without_spaces(symbol) not in _without_spaces(x.formula):
                x.problems.append(f"variable not in the formula: {symbol}")
        extractions.append(x)
    for fid in marked:
        if fid not in seen:
            problems.append(f"{fid} was not answered")
    extractions.sort(key=lambda x: list(marked).index(x.id))
    return extractions, problems


def extract_region(paper: PaperContext, region: Region, model: str, reasoning: str = "off") -> RegionResult:
    """
    Asks `model` about the marked formulas of one region. A model or provider that refuses the strict answer format
    is asked again for plain JSON. Raises ExtractionError when no answer could be obtained.
    """
    messages = build_messages(paper, region)
    notes = []
    use_schema = True
    while True:
        try:
            data, seconds = post_request(build_request(model, messages, reasoning, use_schema))
            break
        except ExtractionError as exc:
            if reasoning == "off" and re.search(r"reasoning is mandatory|cannot be disabled", str(exc), re.IGNORECASE):
                reasoning = LOWEST_REASONING
                notes.append(f"this model cannot answer without reasoning: asked with reasoning {LOWEST_REASONING} instead of off")
            elif use_schema and re.search(r"HTTP (400|404|422)", str(exc)):
                use_schema = False
                notes.append(f"strict answer format refused ({exc}): plain JSON asked instead")
            else:
                raise

    usage = data.get("usage") or {}
    answer = (data["choices"][0].get("message") or {}).get("content") or ""
    result = RegionResult(
        model=data.get("model") or model, seconds=seconds, raw_answer=answer,
        input_tokens=usage.get("prompt_tokens") or 0, output_tokens=usage.get("completion_tokens") or 0,
        reasoning_tokens=(usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0,
        cost=float(usage.get("cost") or 0),
    )
    result.notes = notes
    if data["choices"][0].get("finish_reason") == "length":
        result.problems.append("the answer was cut off at the output limit")
    try:
        items = parse_answer(answer)
    except ValueError as exc:
        result.problems.append(f"the answer is not the expected JSON ({exc})")
        result.problems += [f"{f.id} was not answered" for f in region.formulas]
        return result
    result.extractions, problems = check_answer(region, items)
    result.problems += problems
    return result
