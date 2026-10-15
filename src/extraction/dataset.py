"""
Turns the records of step 5 (one per formula, with every model's answer and the outcome of the vote) into the records
of the dataset: one per formula with a requirement, with the formula as the paper writes it, the requirement passages,
the domain, the meaning of the variables, the paper and its licence. Used by step 6.
"""
import re

from src.extraction.extractor import FORMULA_LAYOUT_PATTERN, formula_key
from src.storage import classify_tier

# ---------------------------------------------------------------- the formula of a LaTeX paper

# What lays a formula out on the page inside the stretch kept: labels, row breaks, alignment marks, spacing and
# style commands
INNER_LAYOUT_PATTERN = re.compile(
    r"\\label\{[^{}]*\}|\\(?:nonumber|notag|displaystyle|textstyle|scriptstyle|allowbreak)(?![a-zA-Z])"
    r"|\\[hv]space\*?\{[^{}]*\}|\\q?quad(?![a-zA-Z])|\\\\(?:\s*\[[^\]]*\])?|&"
)


def _core_with_positions(text: str) -> tuple[str, list[int]]:
    """The text without its layout (as the copy check compares it), and the position in `text` of each character kept."""
    kept, position = [], 0
    for m in FORMULA_LAYOUT_PATTERN.finditer(text):
        kept += range(position, m.start())
        position = m.end()
    kept += range(position, len(text))
    return "".join(text[i] for i in kept), kept


def trim_formula(source: str, copies: list[str]) -> tuple[str, bool]:
    """
    The formula as the paper writes it: the stretch of the marked source that the first of the models' `copies` found
    in it matches (layout aside), with labels, row breaks and alignment marks taken out. (text, True) when a copy was
    found; (the whole marked source, so cleaned, False) otherwise.
    """
    core, positions = _core_with_positions(source)
    for copy in copies:
        copy_core = FORMULA_LAYOUT_PATTERN.sub("", copy or "")
        start = core.find(copy_core) if copy_core else -1
        if start >= 0:
            stretch = source[positions[start]:positions[start + len(copy_core) - 1] + 1]
            return _clean(stretch), True
    return _clean(source.strip().strip("$")), False


def _clean(formula: str) -> str:
    formula = INNER_LAYOUT_PATTERN.sub(" ", formula)
    return " ".join(formula.split()).rstrip(".,;")


# Temporal operators as papers write them, and what is left of a formula once they and their bounds are taken out
OPERATOR_PATTERN = re.compile(
    r"\\(?:square|Box|Diamond|lozenge|diamondsuit|boxminus|diamondminus|always|eventually|until|glob|even|alw|ev|fut"
    r"|since|Since|once|historically|release|LTLg|LTLf|LTLu|G|F|U)(?![A-Za-z])|\\math(?:bf|sf|cal|rm)\{[GFU]\}|(?<![A-Za-z\\])[GFU](?![A-Za-z])")
BOUND_PATTERN = re.compile(r"[_^]\s*\{[^{}]*\}|[_^]\s*\\?\w+")
EMPTY_REST_PATTERN = re.compile(r"\\(?:left|right|big|Big|bigg|Bigg)(?![A-Za-z])|[{}()\[\]$.,;:\s]")
# A connective at the end (or the start) of a formula: the rest of it is on another row of the source
CONNECTIVE_EDGE_PATTERN = re.compile(
    r"(?:\\(?:wedge|land|vee|lor|rightarrow|Rightarrow|implies|to|bigwedge|bigvee)(?![A-Za-z])|=)\s*$"
    r"|^\s*(?:\\(?:wedge|land|vee|lor)(?![A-Za-z])|=)")


def is_fragment(formula: str) -> bool:
    """True for an operator alone, without what it applies to, e.g. "\\square_{[0,1]}": not a whole formula."""
    rest = OPERATOR_PATTERN.sub(" ", BOUND_PATTERN.sub(" ", formula))
    return EMPTY_REST_PATTERN.sub("", rest) == ""


def looks_cut(formula: str) -> bool:
    """True when a formula ends (or starts) with a connective: its other part is probably on another row."""
    return bool(CONNECTIVE_EDGE_PATTERN.search(formula))


def license_name(license: str | None) -> str | None:
    """The short name of a licence: "http://creativecommons.org/licenses/by/4.0/" -> "cc-by"."""
    m = re.search(r"creativecommons\.org/(?:licenses/([a-z-]+)|publicdomain/(zero))", license or "")
    if m:
        return "cc0" if m.group(2) else "cc-" + m.group(1)
    return license


def license_of(license_info: dict) -> str | None:
    """The licence that sets a paper's tier: when the paper has several, the most restrictive one."""
    names = [license_name(l) for l in license_info.get("effective_licenses_all") or []]
    tier = license_info.get("tier")
    return next((n for n in names if classify_tier([n]) == tier), license_name(license_info.get("effective_license")))


# ---------------------------------------------------------------- constructs of other logics

# The constructs of logics other than STL, found by keyword searches such as "Metric Temporal Logic" and by step 4,
# which takes any time-bounded operator: the logic each one marks, the first found deciding
LOGIC_PATTERNS = {
    "strategic": re.compile(r"\\langle\s*\\langle|⟨⟨|\\llangle"),    # a strategy quantifier, as in timed ATL
    # A path quantifier, as in TCTL. Not AF in letters: in the powertrain benchmarks it is the air-fuel ratio
    "branching-time": re.compile(
        r"(?<![A-Za-z\\])(?:[AE]\s*(?:\\Box|\\Diamond|\\square|\\lozenge|\\diamondsuit)|A[GXU]|E[GFXU])(?![A-Za-z])"
        r"|\\(?:forall|exists)\s*\\(?:Box|Diamond|square|lozenge|diamondsuit)(?![A-Za-z])"),
    "probabilistic": re.compile(                                          # a probability operator, as in PCTL or PrSTL
        r"(?<![A-Za-z\\])P\s*_\s*\{?\s*(?:\\[gl]eq?|[<>]|\\sim)|\\mathbb\{E?P\}|\\Pr(?![a-z])"),
    # Spatial operators (SSTL) and the concept inclusion and intersection of description logics
    "spatial-or-description": re.compile(r"\\(?:sqsubseteq|sqcap|somewhere|everywhere)(?![A-Za-z])"),
    "past-time": re.compile(r"\\(?:boxminus|diamondminus|since|Since|once|historically)(?![A-Za-z])|\\mathcal\{S\}"),
}


def other_logic_of(formula: str) -> str | None:
    """
    The logic other than STL whose construct the formula holds: one of LOGIC_PATTERNS ("strategic", "branching-time",
    "probabilistic", "spatial-or-description", "past-time"), or None when none is found. None does not make a formula
    STL: no parser has checked it.
    """
    return next((logic for logic, pattern in LOGIC_PATTERNS.items() if pattern.search(formula)), None)


# ---------------------------------------------------------------- the language of a passage

# Common words of other languages, that English text hardly ever uses
OTHER_LANGUAGE_WORDS = {
    "de": {"der", "die", "das", "und", "ist", "nicht", "mit", "ein", "eine", "wird", "werden", "zu", "auf"},
    "fr": {"le", "la", "les", "et", "est", "une", "des", "du", "dans", "pour", "que", "doit", "pas"},
    "es": {"el", "los", "las", "y", "es", "una", "del", "para", "que", "debe", "con"},
    "it": {"il", "lo", "gli", "che", "di", "una", "per", "non", "deve", "della", "nel"},
    "pt": {"os", "que", "uma", "não", "para", "com", "deve", "das", "dos"},
    "tr": {"ve", "bir", "bu", "için", "ile", "olan", "olarak", "gibi", "kadar"},
}
ENGLISH_WORDS = {"the", "a", "an", "is", "are", "to", "of", "and", "or", "that", "be", "must", "should", "within", "in",
                 "for", "at", "if", "then", "when", "not", "never", "always", "from", "with", "by", "before", "after",
                 "until", "each", "every", "any", "can", "will", "this", "it", "on", "away", "again", "do", "don"}
# Letters of other scripts, and Turkish letters English never uses. A PDF can turn a symbol into a letter of another
# script (φ read as 휑), so a few of them do not make a passage foreign: a share of its letters does.
OTHER_SCRIPT = re.compile(r"[\u0400-\u04FF\u0600-\u06FF\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]")
TURKISH_LETTERS = re.compile(r"[ğışĞİŞ]")


def is_english(text: str) -> bool:
    """False when a passage is plainly in another language: other letters, or more common words of another language."""
    letters = max(1, sum(1 for c in text if c.isalpha()))
    if len(OTHER_SCRIPT.findall(text)) / letters > 0.3 or len(TURKISH_LETTERS.findall(text)) >= 3:
        return False
    words = re.findall(r"[^\W\d_]+", re.sub(r"\\[A-Za-z]+|\$[^$]*\$", " ", text).lower())
    english = sum(1 for w in words if w in ENGLISH_WORDS)
    other = max(sum(1 for w in words if w in vocabulary) for vocabulary in OTHER_LANGUAGE_WORDS.values())
    return not (other >= 2 and other > english)


# ---------------------------------------------------------------- one record of the dataset

def answers_of(record: dict) -> dict:
    """Every model's answer for a formula, the third model's included, the third model first."""
    answers = {}
    if record.get("tie_breaker"):
        answers[record["tie_breaker"]["model"]] = record["tie_breaker"]["answer"]
    answers.update({label: answer for label, answer in record["answers"].items() if answer})
    return answers


def dataset_record(record: dict, bounds: str, paper: dict) -> tuple[dict | None, str | None]:
    """
    (the record of the dataset, None), or (None, why the formula is left out). `bounds` is "numeric" (a concrete
    formula of step 4: a bound at least is a number) or "symbolic" (a parametric one: every bound is a symbol);
    `paper` is the paper's entry of the corpus. A formula the models agree has no requirement gets a record too, with
    no passages (`requirements` empty): it goes to the file of the formulas without a requirement.
    """
    final = record["final"]
    if final["outcome"] == "open":
        return None, "undecided: no two models agree on a requirement"
    if final.get("same_formula_as"):
        return None, f"the same formula as {final['same_formula_as']}, on another line of the PDF text"
    passages = []
    if final["outcome"] == "requirement":
        passages = [p for p in final["requirements"] if is_english(p["text"])]
        if not passages:
            return None, "the requirement is not in English"
    answers = answers_of(record)
    if record.get("source_type") == "pdf":
        if not final.get("formula"):
            return None, "no two models transcribe the formula from the PDF alike"
        formula, how = final["formula"], "transcribed from the PDF page; two models agree"
    else:
        formula, found = trim_formula(record["source"], [a["formula"] for a in answers.values()])
        how = "as in the LaTeX source" if found else "the whole marked LaTeX text: no model's copy was found in it"
    if is_fragment(formula):
        return None, "the formula is an operator alone, not a whole formula"
    from_models = {p["from"] for p in passages}
    license_info = paper.get("license_info") or {}
    return {
        "id": f"{record['paper_id']}:{record['formula_id']}",
        "formula": formula,
        "other_logic": other_logic_of(formula),
        "requirements": [{"text": " ".join(p["text"].split()), "kind": p["kind"]} for p in passages],
        "domain": final["domain"],
        "variables": final["variables"],
        "bounds": bounds,
        "paper_id": record["paper_id"],
        "title": record["title"],
        "year": record["year"],
        "doi": paper.get("doi"),
        "arxiv_id": paper.get("arxiv_id"),
        "license_tier": license_info.get("tier") or record["license_tier"],   # the corpus: step 3 may have changed it
        "license": license_of(license_info),
        "source_type": record.get("source_type", "latex"),
        "location": {"file": record["file"], ("page" if record.get("source_type") == "pdf" else "line"): record["line"]},
        "provenance": {
            "formula": how,
            "requirement_given_by": sorted({model for p in passages for model in p["given_by"]}),
            "formula_given_by": final.get("formula_given_by"),
            # The first two models disagree on it. The third model may give the requirement without that: it answers
            # every formula of a region it is asked about, and the vote counts those answers too
            "disputed": "dispute" in record,
            # The checks failed by the answers the kept passages are taken from
            "flags": sorted({problem for model in from_models for problem in answers.get(model, {}).get("problems", [])}
                            | ({"the formula ends or starts with a connective: part of it may be on another row"} if looks_cut(formula) else set())),
        },
    }, None


def duplicate_key(item: dict) -> tuple:
    """
    Two records of one paper are the same when their formula and their passages are (layout aside). Without a
    requirement, the formula alone.
    """
    passages = tuple(sorted(re.sub(r"\s+", "", p["text"]) for p in item["requirements"]))
    return item["paper_id"], formula_key(item["formula"]), passages


def formula_of_paper(item: dict) -> tuple:
    return item["paper_id"], formula_key(item["formula"])
