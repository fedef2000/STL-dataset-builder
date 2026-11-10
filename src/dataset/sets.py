"""
The sets of the final dataset (data/dataset/), one folder each, named after where the formula and the description come
from: paper-paper (both from the papers), paper-stlnl (paper formula, stl-nl description), stlnl-stlnl (both from
stl-nl). Every set is written as rows of one schema, one row per (description, formula) pair:

    id            the pair: <record id>:D<n> for the paper descriptions
    set           the folder name
    nl, stl       the description and the formula, in the syntax of stl-nl (nl is the training input, stl the target)
    formula_id    the formula: the record id of step 5 for paper formulas
    pattern, skeleton   as in step 6
    judge         the final label (correct, ambiguous, wrong, no, undecided), how it was reached, and each model's answer
    signals       checks made without a model, recorded only: numbers of the formula the description doesn't state,
                  names of the description the formula doesn't have
    original_stl, original_nl   as the paper writes them (LaTeX), for checking
    kind, domain, paper_id, license_tier, license, source_type   from step 5 (null for stl-nl formulas)
"""
import json
import re
from pathlib import Path

from config import DATA_DIR
from src.dataset.judge import usable, vote
from src.extraction.records import parse_model

DATASET_DIR = DATA_DIR / "dataset"
NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])")
# In a description a unit may follow the number with no space: 30.85m, 200ms
NL_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?!\d|\.\d)")
NUMBER_WORDS = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7",
                "eight": "8", "nine": "9", "ten": "10", "eleven": "11", "twelve": "12", "fifteen": "15", "twenty": "20",
                "thirty": "30", "sixty": "60", "hundred": "100"}


def numbers_missing(stl: str, nl: str) -> list[str]:
    """
    The numbers of the formula (bounds, thresholds) the description doesn't state, as digits or as a word up to
    twenty and a few round ones ("two seconds" states 2), compared as values. 0 is left out: a lower bound 0 is "from now" in words.
    """
    stated = set(NL_NUMBER.findall(nl)) | {digit for word, digit in NUMBER_WORDS.items() if re.search(rf"\b{word}\b", nl, re.I)}
    values = {abs(float(n)) for n in stated}   # compared as values: 3.0 states 3, 11.10 states 11.1
    out = []
    for n in NUMBER.findall(stl):
        n = n.lstrip("-")
        if float(n) != 0 and float(n) not in values and n not in out:
            out.append(n)
    return out


def final_judgment(stored: dict, item: dict, n: int, models: list[str], tie_breaker: str) -> dict:
    """The final label of description n of an item, how it was reached, and each model's answer to it."""
    answers, labels = [], {}
    for label in models + [tie_breaker]:
        row = stored.get((*parse_model(label), item["set"], item["id"]))
        if usable(row, item):
            j = row["judgments"][n]
            labels[label] = j["label"]
            answers.append({"model": label, "label": j["label"], "reason": j["reason"], "problems": j["problems"]})
    final, how = vote([labels.get(m) for m in models], labels.get(tie_breaker))
    return {"label": final, "how": how, "answers": answers}


def paper_rows(records: list[dict], items: list[dict], stored: dict, models: list[str], tie_breaker: str) -> list[dict]:
    """Set 1: one row per requirement passage of the paired records, with the judge's final label."""
    rows = []
    by_id = {item["id"]: item for item in items}
    for r in records:
        for n, passage in enumerate(r["requirements"]):
            rows.append({
                "id": f"{r['id']}:D{n + 1}", "set": "paper-paper", "nl": passage["normalized"], "stl": r["normalized"],
                "formula_id": r["id"], "pattern": r["pattern"], "skeleton": r["skeleton"],
                "judge": final_judgment(stored, by_id[r["id"]], n, models, tie_breaker),
                "signals": {"numbers_missing": numbers_missing(r["normalized"], passage["normalized"]),
                            "names_not_in_formula": passage.get("names_not_in_formula") or []},
                "original_stl": r["formula"], "original_nl": passage["text"], "kind": passage["kind"],
                "domain": r.get("domain"), "paper_id": r["paper_id"], "license_tier": r.get("license_tier"),
                "license": r.get("license"), "source_type": r.get("source_type"),
            })
    return rows


# The files of a set: the label of the pairs that go in each
SPLIT = {"pairs": ("correct",), "pairs_ambiguous": ("ambiguous",), "dropped": ("wrong", "no", "undecided")}


def write_set(rows: list[dict], folder: Path) -> dict[str, int]:
    """pairs.jsonl, pairs_ambiguous.jsonl, dropped.jsonl, and pairs.xlsx with one sheet each. Returns the counts."""
    folder.mkdir(parents=True, exist_ok=True)
    parts = {name: [r for r in rows if r["judge"]["label"] in labels] for name, labels in SPLIT.items()}
    for name, part in parts.items():
        with open(folder / f"{name}.jsonl", "w", encoding="utf-8") as out:
            for r in part:
                out.write(json.dumps(r, ensure_ascii=False) + "\n")
    write_xlsx(folder / "pairs.xlsx", {"pairs": parts["pairs"], "ambiguous": parts["pairs_ambiguous"], "dropped": parts["dropped"]})
    return {name: len(part) for name, part in parts.items()}


# ---------------------------------------------------------------- the xlsx file, to check the pairs by eye

COLUMNS = [  # (header, width, value of a row)
    ("id", 24, lambda r: r["id"]),
    ("stl", 50, lambda r: r["stl"]),
    ("nl", 60, lambda r: r["nl"]),
    ("label", 11, lambda r: r["judge"]["label"]),
    ("how", 18, lambda r: r["judge"]["how"]),
    ("reason", 50, lambda r: next((a["reason"] for a in r["judge"]["answers"] if a["label"] == r["judge"]["label"]),
                                  r["judge"]["answers"][0]["reason"] if r["judge"]["answers"] else "")),
    ("problems", 50, lambda r: "\n".join(next((a["problems"] for a in r["judge"]["answers"] if a["label"] == r["judge"]["label"]), []))),
    ("models", 30, lambda r: "\n".join(f"{parse_model(a['model'])[0].split('/')[-1]}: {a['label']}" for a in r["judge"]["answers"])),
    ("numbers missing", 14, lambda r: ", ".join(r["signals"]["numbers_missing"])),
    ("kind", 10, lambda r: r.get("kind") or ""),
    ("original stl", 45, lambda r: r.get("original_stl") or ""),
    ("original nl", 60, lambda r: r.get("original_nl") or ""),
    ("domain", 16, lambda r: r.get("domain") or ""),
    ("license tier", 16, lambda r: r.get("license_tier") or ""),
]
ILLEGAL_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def write_xlsx(path: Path, sheets: dict[str, list[dict]]):
    """
    One sheet per part, with a frozen header, filters on every column and wrapped text. The reason and problems are
    those of a model that gave the final label (the first one), so they explain it.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter

    book = Workbook()
    book.remove(book.active)
    wrap = Alignment(wrap_text=True, vertical="top")
    for title, rows in sheets.items():
        sheet = book.create_sheet(title)
        sheet.append([header for header, _, _ in COLUMNS])
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for r in rows:
            sheet.append([ILLEGAL_XML.sub("", str(value(r))) for _, _, value in COLUMNS])
        for i, (_, width, _) in enumerate(COLUMNS, 1):
            sheet.column_dimensions[get_column_letter(i)].width = width
        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = wrap
        sheet.freeze_panes = "B2"
        sheet.auto_filter.ref = sheet.dimensions
    book.save(path)
