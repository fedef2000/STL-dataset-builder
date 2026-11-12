"""
The analysis of the final dataset (data/dataset/analysis.md and patterns.csv), written from the files of the three
sets. The pattern of a formula (the field `pattern` of the rows, as in step 6) is its temporal and Boolean structure. The dataset is: set 1's correct and ambiguous pairs (pairs.jsonl, pairs_ambiguous.jsonl); sets 2 and 3's rows
except those the judge's sample found wrong, not a description, or undecided (the rows outside the sample are kept).
Patterns, domains and operators count formulas, not descriptions: in sets 2 and 3 stl-nl wrote two descriptions of
each formula, which would otherwise count it twice. A formula is counted once per set.
"""
import collections
import csv
import re
from pathlib import Path

from src.dataset.sets import SET_1, SET_2, SET_3, read_jsonl

SETS = (SET_1, SET_2, SET_3)
TOTAL = "total"
KEPT = {"correct", "ambiguous"}
TOP = 10


# ---------------------------------------------------------------- the rows of the dataset

def dataset_rows(folder: Path) -> dict[str, list[dict]]:
    """Set name -> the rows that are in the dataset (see the module's docstring); a set with no files is empty."""
    rows = {}
    for name in SETS:
        files = ["pairs.jsonl", "pairs_ambiguous.jsonl"] if name == SET_1 else ["pairs.jsonl"]
        found = [r for f in files if (folder / name / f).exists() for r in read_jsonl(folder / name / f)]
        rows[name] = [r for r in found if r["judge"] is None or r["judge"]["label"] in KEPT]
    return rows


def formulas(rows: list[dict]) -> list[dict]:
    """One row per formula (the first of its descriptions)."""
    seen = {}
    for r in rows:
        seen.setdefault(r["formula_id"], r)
    return list(seen.values())


# ---------------------------------------------------------------- the pattern as a tree

TOKEN = re.compile(r"\s*(<->|->|&&|\|\||!|\(|\)|[GFUR][\[(][^\[\]()]*[\])]|[^\s()!&|<>-]+)")
TEMPORAL = re.compile(r"[GFUR][\[(]")


def tokens(text: str) -> list[str]:
    out, i = [], 0
    while i < len(text):
        m = TOKEN.match(text, i)
        if not m or not m.group(1):
            if text[i:].strip():
                raise ValueError(f"can't read {text[i:]!r} in {text!r}")
            break
        out.append(m.group(1))
        i = m.end()
    return out


def parse(text: str) -> tuple:
    """
    A pattern (G[#,#] (φ -> F[#,#] ψ)) as a tree: (operator, children), with stl-nl's precedence: the unary
    operators (!, G, F) bind tightest, then U and R, then &&, ||, -> and <->. Leaves are ("cond", []).
    """
    toks, pos = tokens(text), [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def take():
        pos[0] += 1
        return toks[pos[0] - 1]

    def implication():
        left = disjunction()
        if peek() in ("->", "<->"):
            op = take()
            return (op, [left, implication()])
        return left

    def nary(op, below):
        children = [below()]
        while peek() == op:
            take()
            children.append(below())
        return children[0] if len(children) == 1 else (op, children)

    def disjunction():
        return nary("||", conjunction)

    def conjunction():
        return nary("&&", binary_temporal)

    def binary_temporal():
        left = unary()
        while peek() and peek()[0] in "UR" and TEMPORAL.match(peek()):
            op = take()[0]
            left = (op, [left, unary()])
        return left

    def unary():
        t = take()
        if t == "!":
            return ("!", [unary()])
        if TEMPORAL.match(t) and t[0] in "GF":
            return (t[0], [unary()])
        if t == "(":
            inner = implication()
            if take() != ")":
                raise ValueError(f"unbalanced parentheses in {text!r}")
            return inner
        return ("cond", [])

    tree = implication()
    if pos[0] != len(toks):
        raise ValueError(f"can't read the end of {text!r}")
    return tree


def operators(tree: tuple) -> set[str]:
    op, children = tree
    found = {op} if op != "cond" else set()
    for c in children:
        found |= operators(c)
    return found


# ---------------------------------------------------------------- the report

def share(n: int, total: int) -> str:
    return f"{100 * n / total:.1f}%" if total else "-"


def table(header: list[str], rows: list[list]) -> list[str]:
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def code(text: str) -> str:
    return "`" + text.replace("|", "\\|") + "`"


def write_analysis(folder: Path) -> Path:
    """data/dataset/analysis.md and patterns.csv. Returns the path of analysis.md."""
    rows = dataset_rows(folder)
    present = [s for s in SETS if rows[s]]
    by_set = {s: formulas(rows[s]) for s in present}
    by_set[TOTAL] = [f for s in present for f in by_set[s]]
    columns = present + [TOTAL]
    out = ["# Analysis of the dataset", "",
           "The dataset is: set 1's correct and ambiguous pairs; sets 2 and 3's pairs except the few the judge's sample "
           "found wrong, not a description, or undecided (the pairs outside the sample are not judged and are kept). "
           "Patterns, domains and operators count formulas, not descriptions (in sets 2 and 3 each formula has two "
           "descriptions); a formula is counted once per set, and the total adds the three sets.", ""]

    # Size
    out += ["## Size", ""]
    out += table(["Set", "Descriptions", "Formulas"],
                 [[s, len(rows[s]) if s != TOTAL else sum(len(rows[x]) for x in present), len(by_set[s])] for s in columns])

    # Judge
    out += ["", "## Judge", "",
            "Labels of the descriptions judged: every description of set 1, a sample of 500 formulas (1,000 "
            "descriptions) of sets 2 and 3. `No`: the description is not a description of the formula (it only says "
            "what the formula is for, describes a part of it, or something else). The rest of the judged descriptions "
            "are undecided (the three models gave three different labels, one of them `no`; correct, ambiguous and wrong "
            "together give ambiguous).", ""]
    labels = ("correct", "ambiguous", "wrong", "no")
    judge_rows = []
    for s in present:
        files = ["pairs.jsonl", "pairs_ambiguous.jsonl", "dropped.jsonl"] if s == SET_1 else ["pairs.jsonl"]
        judged = [r["judge"]["label"] for f in files if (folder / s / f).exists() for r in read_jsonl(folder / s / f) if r["judge"]]
        count = collections.Counter(judged)
        judge_rows.append([s, len(judged)] + [f"{count[l]} ({share(count[l], len(judged))})" for l in labels])
    out += table(["Set", "Judged", "Correct", "Ambiguous", "Wrong", "No (not a description)"], judge_rows)

    # Patterns
    counts = {s: collections.Counter(f["pattern"] for f in by_set[s]) for s in columns}
    out += ["", "## Patterns", "",
            "The pattern of a formula: its temporal and Boolean structure, each condition a Greek letter, every bound "
            "`#` (or `inf`), computed as in step 6. The full list, with the formulas of each set, is in `patterns.csv`.", ""]
    out += table(["Set", "Formulas", "Patterns", "Top 10 cover"],
                 [[s, len(by_set[s]), len(counts[s]), share(sum(v for _, v in counts[s].most_common(TOP)), len(by_set[s]))]
                  for s in columns])
    out += ["", f"### The {TOP} most common patterns of the dataset", "",
            "Formulas of each set with the pattern, and their share of that set's formulas."]
    out += [""] + table(["Pattern"] + columns,
                        [[code(k)] + [f"{counts[s][k]} ({share(counts[s][k], len(by_set[s]))})" for s in columns]
                         for k, _ in counts[TOTAL].most_common(TOP)])
    for s in present:
        out += ["", f"### The {TOP} most common patterns of {s}", ""]
        out += table(["Pattern", "Formulas", "Share"],
                     [[code(k), v, share(v, len(by_set[s]))] for k, v in counts[s].most_common(TOP)])
    with open(folder / "patterns.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["pattern"] + columns)
        for k, _ in counts[TOTAL].most_common():
            writer.writerow([k] + [counts[s][k] for s in columns])

    # Domains
    domains = {s: collections.Counter(f["domain"] or "unknown" for f in by_set[s]) for s in columns}
    out += ["", "## Domains", "",
            "In sets 1 and 2 the domain is the one step 5's models read in the paper (`generic`: an abstract example, "
            "with no application); in set 3 stl-nl's generator assigns it, spreading the formulas over its 17 domains "
            "(two of them, `medical devices` and `cloud computing`, are not among step 5's).", ""]
    out += table(["Domain"] + columns,
                 [[d] + [f"{domains[s][d]} ({share(domains[s][d], len(by_set[s]))})" for s in columns]
                  for d, _ in domains[TOTAL].most_common()])

    # Operators
    ops = {s: [operators(parse(f["pattern"])) for f in by_set[s]] for s in present}
    ops[TOTAL] = [x for s in present for x in ops[s]]
    out += ["", "## Operators", "",
            "Share of the formulas of each set that hold each operator.", ""]
    out += table(["Operator"] + columns,
                 [[code(op)] + [share(sum(1 for x in ops[s] if op in x), len(ops[s])) for s in columns]
                  for op in ("G", "F", "U", "R", "!", "&&", "||", "->")])

    path = folder / "analysis.md"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path
