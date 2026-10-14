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


# The prompt for the parametric formulas (time bounds given as symbols): the same task, with the two kinds of
# requirement told apart without numbers, and the parameters asked for among the variables.
_CONCRETE_KINDS = SYSTEM_PROMPT[SYSTEM_PROMPT.index('   - "specific": it carries'):SYSTEM_PROMPT.index("   Report every specific passage.")]
_PARAMETRIC_KINDS = """   - "specific": it expresses this formula: it says what has to hold, when and for how long, naming a parameter \
where the formula has one (or giving its value, if the excerpt does). E.g. for G_{[0,T]}(v < v_{max}): "the speed \
must stay below $v_{max}$ during the first $T$ seconds" or "the speed never exceeds its maximum over the whole \
horizon".
   - "generic": it says what the formula is for without expressing it. E.g. "a safety constraint on the speed" or \
"the vehicle reaches a goal location". The test: if the formula could be written down from the passage, up to the \
names of its symbols, the passage is specific; if the passage would fit many different formulas, it is generic.
"""
_CONCRETE_VARIABLES = "Do not list temporal or logical operators or numbers."
_PARAMETRIC_VARIABLES = ("Include the parameters of the formula (the symbols in its time bounds, its thresholds and constants) "
                         "with what the excerpt says they stand for. Do not list temporal or logical operators or numbers.")
_CONCRETE_NONE = "Many marked formulas have none:"
_PARAMETRIC_NONE = ("The marked formulas are those whose time bounds are symbols; formulas with numeric time bounds are not marked. "
                    "Most marked formulas have none:")
for _part in (_CONCRETE_VARIABLES, _CONCRETE_NONE):
    assert SYSTEM_PROMPT.count(_part) == 1, _part
PARAMETRIC_SYSTEM_PROMPT = (
    SYSTEM_PROMPT.replace(_CONCRETE_KINDS, _PARAMETRIC_KINDS).replace(_CONCRETE_VARIABLES, _PARAMETRIC_VARIABLES)
    .replace(_CONCRETE_NONE, _PARAMETRIC_NONE).replace("F1", "P1")
)

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
    parametric = all(f.kind == "symbolic" for f in region.formulas)
    return [{"role": "system", "content": PARAMETRIC_SYSTEM_PROMPT if parametric else SYSTEM_PROMPT}, {"role": "user", "content": user}]


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


# Spacing that models drop or add when they copy: \, \! \; \: "\ " ~ \quad \qquad
SPACING_PATTERN = r"\\[,;:! ]|~|\\q?quad(?![a-zA-Z])"

# A line break of the source that a model wrote as the two characters \n instead of a newline. Followed by a letter
# it would be a command (\neg, \nu) and is left alone.
WRITTEN_NEWLINE_PATTERN = r"\\n(?![a-zA-Z])"

# What lays a formula out on the page without being part of it: row breaks, alignment marks, labels, math delimiters,
# spacing. The model is told to leave these out, so they are not compared.
FORMULA_LAYOUT_PATTERN = re.compile(
    WRITTEN_NEWLINE_PATTERN + "|" + SPACING_PATTERN
    + r"|\\\\(?:\s*\[[^\]]*\])?|&|\$|\\label\{[^{}]*\}|\\(?:nonumber|notag)(?![a-zA-Z])"
    r"|\\(?:begin|end)\{[a-zA-Z*]+\}(?:\[[^\]]*\])?(?:\{[^{}]*\})?|\\[\[\]]|\s+"
)

# What may differ between a passage and its copy: math delimiters, row breaks (also of a word hyphenated across
# rows), spacing, quotation marks, the markers put around the formulas, and a backslash before a sign (\% against %).
PASSAGE_LAYOUT_PATTERN = re.compile(
    WRITTEN_NEWLINE_PATTERN + "|" + SPACING_PATTERN
    + r"|-?\\\\|-\s+(?=[a-z])|\$|``|''|[\"“”]|⟦/?[A-Z]\d+⟧|\\(?![a-zA-Z])|\s+"
)

# A passage given in pieces is "joined" rather than "not a copy" when it has at most this many pieces, each at least
# this long (after the layout is removed).
MAX_JOINED_PIECES = 3
MIN_JOINED_PIECE = 15


def _formula_core(text: str) -> str:
    return FORMULA_LAYOUT_PATTERN.sub("", text)


def passage_core(text: str) -> str:
    return PASSAGE_LAYOUT_PATTERN.sub("", text)


# How a symbol is written rather than which symbol it is: its font, its braces (p_2 against p_{2}), a backslash
# before a sign (in_room against in\_room).
SYMBOL_WRITING_PATTERN = re.compile(
    r"\\(?:math(?:bf|rm|it|sf|tt|cal|bb|frak|scr)|text(?:bf|rm|it|sf|tt|normal)?|rm|bf|it|sf|tt|cal|boldsymbol|bm|operatorname\*?)(?![a-zA-Z])"
    r"|[{}]|\\(?![a-zA-Z])"
)


def _symbol_core(text: str) -> str:
    return SYMBOL_WRITING_PATTERN.sub("", _formula_core(text))


def _symbol_in_formula(symbol: str, formula_symbols: str) -> bool:
    """
    True when the symbol is written in the formula (given as its _symbol_core), or when it is one of an indexed
    family the formula writes with another index: x_3 in a formula over x_i, or over x_1, ..., x_6.
    """
    core = _symbol_core(symbol)
    if core in formula_symbols:
        return True
    base = re.split(r"[_^]", core, maxsplit=1)[0]
    return base != core and bool(base) and re.search(r"(?<![A-Za-z\\])" + re.escape(base) + r"(?![A-Za-z])", formula_symbols) is not None


def _pieces_in_order(passage: str, source: str) -> int | None:
    """In how many pieces `passage` is found in `source`, one after the other; None when it is not, or in too many."""
    position, start, pieces = 0, 0, 0
    while start < len(passage):
        if pieces == MAX_JOINED_PIECES:
            return None
        # The longest stretch from `start` found at or after `position` (every shorter stretch is found there too)
        low, high = 0, len(passage) - start
        while low < high:
            middle = (low + high + 1) // 2
            if source.find(passage[start:start + middle], position) >= 0:
                low = middle
            else:
                high = middle - 1
        if low < min(MIN_JOINED_PIECE, len(passage) - start):
            return None
        position = source.find(passage[start:start + low], position) + low
        start += low
        pieces += 1
    return pieces


def check_passage(text: str, region_core: str) -> str | None:
    """
    None when the passage is a copy of the excerpt, otherwise what is wrong with it. A sentence end or a bracket
    left over at the edges of the copy is not compared.
    """
    core = passage_core(text).strip(".,;:()[]{}")
    if not core or core in region_core:
        return None
    if _pieces_in_order(core, region_core):
        return "the requirement joins separate parts of the excerpt"
    return "the requirement is not a copy of the excerpt"


def check_extraction(x: Extraction, formula_source: str, region_core: str) -> list[str]:
    """The problems of one answer, against the marked formula and the excerpt (given as passage_core of its text)."""
    problems = []
    if not x.formula.strip():
        problems.append("no formula given")
    elif _formula_core(x.formula) not in _formula_core(formula_source):
        problems.append("the formula is not a copy of the marked text")
    for n, passage in enumerate(x.requirements, 1):
        which = f" (passage {n})" if len(x.requirements) > 1 else ""
        problem = check_passage(passage["text"], region_core)
        if problem:
            problems.append(problem + which)
        if passage["kind"] not in REQUIREMENT_KINDS:
            problems.append(f"unknown kind of requirement: {passage['kind'] or '(none)'}" + which)
    if len({passage["kind"] for passage in x.requirements}) > 1:
        problems.append("specific and generic requirements given together")
    if x.domain not in DOMAINS:
        problems.append(f"unknown domain: {x.domain or '(none)'}")
    formula_symbols = _symbol_core(x.formula)
    for symbol in x.variables:
        if not _symbol_in_formula(symbol, formula_symbols):
            problems.append(f"variable not in the formula: {symbol}")
    return problems


def check_answer(region: Region, items: list[dict]) -> tuple[list[Extraction], list[str]]:
    """
    Turns the model's entries into Extractions and checks them against the region. Line breaks, spacing and other
    layout are not compared: a requirement copied across a line break of the source is still a copy.
    """
    marked = {f.id: f for f in region.formulas}
    region_core = passage_core(region.text)
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
        x.problems = check_extraction(x, marked[fid].source, region_core)
        extractions.append(x)
    for fid in marked:
        if fid not in seen:
            problems.append(f"{fid} was not answered")
    extractions.sort(key=lambda x: list(marked).index(x.id))
    return extractions, problems


def recheck_stored(extractions: list[dict], region: Region) -> None:
    """
    Checks answers that were stored earlier again, against the region as it is built now, and replaces their
    "problems". A change to the checks then shows in the stored answers without asking the models again.
    """
    marked = {f.id: f for f in region.formulas}
    region_core = passage_core(region.text)
    for e in extractions:
        if e.get("id") in marked:
            x = Extraction(id=e["id"], formula=e["formula"], requirements=e["requirements"], domain=e["domain"], variables=e["variables"])
            e["problems"] = check_extraction(x, marked[e["id"]].source, region_core)


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
