"""
The dataset, built at the end of step 5 from its records (one per formula, with every model's answer and the outcome
of the vote): one record per formula with a requirement, with the formula as the paper writes it, the requirement
passages, the domain, the meaning of the variables, the paper and its licence; one per formula the models agree has
no requirement; the formulas left out of both, with the reason; and stats.md, what the dataset holds.
"""
import collections
import json
import re
from pathlib import Path

from config import DATA_DIR
from src.extraction.extractor import FORMULA_LAYOUT_PATTERN, formula_key
from src.storage import classify_tier

DATASET_DIR = DATA_DIR / "dataset"
LICENSE_TIERS = ("permissive_cc", "restricted_cc", "custom_or_arxiv", "unspecified")

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


# ---------------------------------------------------------------- the whole dataset

FORMULA_ID_PATTERN = re.compile(r"(?:[\w.]+:)?\b[FP]\d+\b")


def formula_number(record_id: str) -> int:
    return int(record_id.rsplit(":", 1)[1][1:])


def left_out(item_id: str, reason: str, outcome: str, source_type: str, bounds: str, source: str, requirements: list) -> dict:
    """An entry of excluded.jsonl. `outcome` is the vote of step 5: "requirement", "none" or "open" (undecided)."""
    return {"id": item_id, "reason": reason, "outcome": outcome, "source_type": source_type, "bounds": bounds,
            "source": source, "requirements": requirements}


def build(groups: list[tuple[str, list[dict]]], papers: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """
    The records of the dataset, the formulas without a requirement (records with no passages), and the formulas left
    out of either (with the reason). `groups` holds the records of step 5 of every source and kind of formula, each
    with its bounds ("numeric" for the concrete formulas, "symbolic" for the parametric ones), the LaTeX ones first:
    a formula repeated in a paper is kept where it is first met. `papers` is the corpus.
    """
    kept, unpaired, excluded, seen = [], [], [], {}
    for bounds, records in groups:
        for record in records:
            item, reason = dataset_record(record, bounds, papers.get(record["paper_id"], {}))
            if item is None:
                excluded.append(left_out(f"{record['paper_id']}:{record['formula_id']}", reason,
                                         record["final"]["outcome"], record.get("source_type", "latex"), bounds,
                                         record["source"], record["final"]["requirements"]))
                continue
            outcome = "requirement" if item["requirements"] else "none"
            key = duplicate_key(item)
            if key in seen:
                # The same formula (with the same passages), elsewhere in the paper: kept once
                seen[key].setdefault("also_at", []).append(item["location"])
                what = "formula and requirement" if item["requirements"] else "formula, without a requirement,"
                excluded.append(left_out(item["id"], f"the same {what} as {seen[key]['id']}", outcome,
                                         item["source_type"], bounds, item["formula"], item["requirements"]))
                continue
            seen[key] = item
            (kept if item["requirements"] else unpaired).append(item)
    # A formula the paper also has with a requirement is in the dataset already
    paired = {formula_of_paper(r): r["id"] for r in kept}
    for item in [r for r in unpaired if formula_of_paper(r) in paired]:
        excluded.append(left_out(item["id"], f"the same formula as {paired[formula_of_paper(item)]}, which has a requirement",
                                 "none", item["source_type"], item["bounds"], item["formula"], []))
    unpaired = [r for r in unpaired if formula_of_paper(r) not in paired]
    for records in (kept, unpaired):
        records.sort(key=lambda r: (r["paper_id"], r["bounds"], formula_number(r["id"])))
    return kept, unpaired, excluded


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_dataset(groups: list[tuple[str, list[dict]]], papers: dict, licenses: list[str] | None = None) -> None:
    """
    Builds the dataset and writes it to data/dataset/ (stl_dataset.jsonl, stl_formulas_unpaired.jsonl, excluded.jsonl,
    stats.md), with copies of the first two holding only the licence tiers in `licenses`, if given.
    """
    records, unpaired, excluded = build(groups, papers)
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(DATASET_DIR / "stl_dataset.jsonl", records)
    write_jsonl(DATASET_DIR / "stl_formulas_unpaired.jsonl", unpaired)
    write_jsonl(DATASET_DIR / "excluded.jsonl", excluded)
    (DATASET_DIR / "stats.md").write_text(stats(records, unpaired, excluded), encoding="utf-8", newline="\n")
    print(f"\nDATASET")
    print(f"{len(records):,} records from {len({r['paper_id'] for r in records}):,} papers -> {DATASET_DIR / 'stl_dataset.jsonl'}")
    for tier, n in collections.Counter(r["license_tier"] for r in records).most_common():
        print(f"   {n:>6,}  {tier}")
    print(f"{len(unpaired):,} formulas without a requirement -> {DATASET_DIR / 'stl_formulas_unpaired.jsonl'}")
    print(f"{len(excluded):,} formulas left out -> {DATASET_DIR / 'excluded.jsonl'} (reasons in stats.md)")
    if licenses:
        tiers = "_".join(sorted(licenses))
        for name, rows in (("stl_dataset", records), ("stl_formulas_unpaired", unpaired)):
            subset = [r for r in rows if r["license_tier"] in licenses]
            path = DATASET_DIR / f"{name}_{tiers}.jsonl"
            write_jsonl(path, subset)
            print(f"{len(subset):,} records with licence tier {', '.join(licenses)} -> {path}")


# ---------------------------------------------------------------- stats.md

def table(title: str, counts: collections.Counter, total: int, unit: str = "Records") -> list[str]:
    lines = [f"| {title} | {unit} | Share |", "|---|---|---|"]
    lines += [f"| {name} | {n:,} | {100 * n / total:.1f}% |" for name, n in counts.most_common()]
    return lines + [""]


def reason_table(excluded: list[dict]) -> list[str]:
    reasons = collections.Counter(FORMULA_ID_PATTERN.sub("another formula", e["reason"]) for e in excluded)
    return [f"| Reason | Formulas |", "|---|---|"] + [f"| {reason} | {n:,} |" for reason, n in reasons.most_common()] + [""]


def subsets(records: list[dict]) -> list[str]:
    """How many records are left with a specific passage, and the licence tiers of those."""
    def row(name, rows):
        return f"| {name} | {len(rows):,} | {len({r['paper_id'] for r in rows}):,} |"

    with_specific = [r for r in records if any(p["kind"] == "specific" for p in r["requirements"])]
    lines = ["## Best quality subset", "", "",
             "| Filter | Records | Papers |", "|---|---|---|",
             row("all records", records),
             row("... with a specific passage", with_specific), ""]
    return lines + table("Licence tier of the cleanest set",
                         collections.Counter(r["license_tier"] or "none" for r in with_specific), len(with_specific))


# What each kind of requirement passage means, and a record of the dataset that shows it
PASSAGE_KINDS = {
    "specific": ("it states what the formula says: its condition, with the thresholds and time bounds (or, for a "
                 "formula with symbolic bounds, the names of its parameters)", "W3008764564:F22"),
    "generic": ("it only says what the formula is for, without what is needed to write it", "W4311414009:P9"),
}


def passage_kinds(records: list[dict]) -> list[str]:
    """What specific and generic mean, each with a real example."""
    by_id = {r["id"]: r for r in records}
    lines = ["| Kind | Meaning | Example |", "|---|---|---|"]
    for kind, (meaning, example_id) in PASSAGE_KINDS.items():
        example = by_id.get(example_id)
        passage = next((p["text"] for p in example["requirements"] if p["kind"] == kind), None) if example else None
        shown = (f"\"{passage}\" for `{example['formula']}` ({example_id})" if passage else "").replace("|", "\\|")
        lines.append(f"| **{kind}** | {meaning} | {shown} |")
    return lines + ["", ""]


def stats(records: list[dict], unpaired: list[dict], excluded: list[dict]) -> str:
    """stats.md: what the dataset holds. No date in it, so that a rebuild with the same data changes nothing."""
    total = len(records)
    lines = ["# STL dataset: statistics", "",
             f"{total:,} records (one per formula with a requirement), "
             f"with {sum(len(r['requirements']) for r in records):,} requirement passages.", "", "", ""]
    kinds = collections.Counter(p["kind"] for r in records for p in r["requirements"])
    lines += table("Kind of requirement passage", kinds, sum(kinds.values()), unit="Passages")
    lines += passage_kinds(records)
    lines += table("Licence tier", collections.Counter(r["license_tier"] or "none" for r in records), total)
    lines += table("Licence", collections.Counter(r["license"] or "none" for r in records), total)
    lines += table("Domain", collections.Counter(r["domain"] for r in records), total)
    lines += [""] + subsets(records)
    n = len(unpaired)
    lines += ["## Formulas without a requirement", "",
              f"{n:,} formulas that the models agree have no requirement (`stl_formulas_unpaired.jsonl`): records with "
              "no passages.", ""]
    lines += table("Licence tier", collections.Counter(r["license_tier"] or "none" for r in unpaired), n)
    lines += table("Domain", collections.Counter(r["domain"] for r in unpaired), n)
    lines += ["## Left out", "", "Formulas with a requirement (or undecided) that are not in the dataset (`excluded.jsonl`):", ""]
    lines += reason_table([e for e in excluded if e["outcome"] != "none"])
    lines += ["Formulas without a requirement that are not in `stl_formulas_unpaired.jsonl` (`excluded.jsonl`):", ""]
    lines += reason_table([e for e in excluded if e["outcome"] == "none"])
    return "\n".join(lines)
