"""
The analysis of the final dataset (data/dataset/analysis.md and patterns.csv), written from the files of the three
sets, at the end of every run of step 8 (the round trip, which decides what is in the dataset). The pattern of a
formula (the field `pattern` of the rows, as in step 6) is its temporal and Boolean structure. The dataset is: set 1's
pairs.jsonl (the candidates a model wrote back into their formula, and those kept or fixed by hand,
src/dataset/manual.py); every row of sets 2 and 3 (not checked by the round trip yet). Patterns, domains and operators
count formulas, not descriptions: in sets 2 and 3 stl-nl wrote two descriptions of each formula, which would otherwise
count it twice. A formula is counted once per set.

The paraphrases of step 9 (set_1/augmented/pairs.jsonl) are counted apart, in the size and in a section of their own:
they have the formulas of their originals, so they change no count of formulas.
"""
import collections
import csv
import re
from pathlib import Path

from src.augmentation.llm import word_difference
from src.dataset.sets import SET_1, SET_2, SET_3, read_jsonl, short_reason

SETS = (SET_1, SET_2, SET_3)
TOTAL = "total"
TOP = 10
AUGMENTED = "augmented"   # the folder of step 9's paraphrases inside a set's folder


# ---------------------------------------------------------------- the rows of the dataset

def dataset_rows(folder: Path) -> dict[str, list[dict]]:
    """Set name -> the rows that are in the dataset (see the module's docstring); a set with no files is empty."""
    rows = {}
    for name in SETS:
        rows[name] = read_jsonl(folder / name / "pairs.jsonl") if (folder / name / "pairs.jsonl").exists() else []
    return rows


def augmented_rows(folder: Path) -> dict[str, dict[str, list[dict]]]:
    """Set name -> the paraphrases of step 9 in the dataset (`pairs`) and out of it (`dropped`); empty for a set without them."""
    out = {}
    for name in SETS:
        sub = folder / name / AUGMENTED
        out[name] = {f: read_jsonl(sub / f"{f}.jsonl") if (sub / f"{f}.jsonl").exists() else [] for f in ("pairs", "dropped")}
    return out


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
    augmented = augmented_rows(folder)
    present = [s for s in SETS if rows[s]]
    by_set = {s: formulas(rows[s]) for s in present}
    by_set[TOTAL] = [f for s in present for f in by_set[s]]
    columns = present + [TOTAL]
    out = ["# Analysis of the dataset", "",
           "The dataset is: set 1's pairs whose formula a model wrote back from the description alone (the round "
           "trip of step 8), with those kept or fixed by hand; every pair of sets 2 and 3 (not checked by the round "
           "trip yet). Patterns, domains and operators count formulas, not descriptions (in sets 2 and 3 each formula "
           "has two descriptions); a formula is counted once per set, and the total adds the three sets. The "
           "paraphrases of step 9 are counted apart.", ""]

    # Size
    out += ["## Size", "",
            "Paraphrases: those step 9 adds to the descriptions (see Paraphrases below); they have the formulas of their "
            "originals, so they add no formula.", ""]
    n_par = {s: len(augmented[s]["pairs"]) for s in present}
    out += table(["Set", "Descriptions", "Paraphrases", "Formulas"],
                 [[s, len(rows[s]) if s != TOTAL else sum(len(rows[x]) for x in present),
                   n_par[s] if s != TOTAL else sum(n_par.values()), len(by_set[s])] for s in columns])

    # Set 1: round trip
    dropped_1 = read_jsonl(folder / SET_1 / "dropped.jsonl") if (folder / SET_1 / "dropped.jsonl").exists() else []
    if rows[SET_1] or dropped_1:
        out += ["", "## Set 1: round trip", "",
                "Every description of set 1 is a candidate; the round trip of step 8 (a model writes the formula from "
                "the description alone) decides which are in the dataset: those at least one of its two models wrote "
                "back, and those kept or fixed by hand after reading them. Out: neither model wrote the formula back, "
                "stlgen can't read the formula (not checkable), or dropped by hand.", ""]
        reasons = collections.Counter(short_reason(r["dropped"]) for r in dropped_1)
        by_hand = sum(1 for r in rows[SET_1] if r.get("manual"))
        total = len(rows[SET_1]) + len(dropped_1)
        out += table(["Candidates", "In the dataset", "Match", "Kept or fixed by hand", "Out"] + list(reasons),
                     [[total, share(len(rows[SET_1]), total), len(rows[SET_1]) - by_hand, by_hand, len(dropped_1)]
                      + [reasons[k] for k in reasons]])

    # Paraphrases
    with_par = [s for s in present if augmented[s]["pairs"] or augmented[s]["dropped"]]
    if with_par:
        out += ["", "## Paraphrases", "",
                "Step 9: a model writes two paraphrases of each pair of set 1 in the dataset, keeping its numbers, "
                "symbols and meaning; the round trip of step 8 keeps those a model writes back into the formula, as for "
                "set 1. Missing a symbol: the paraphrases in the dataset that lack a number or symbol of their "
                "original. Word difference: how different the words of a paraphrase are from its original's, 0 (the "
                "same words in the same order) to 1 (no word in common); in the trial of TextAttack "
                "(archive/textattack_trial/), its word-level augmenters gave 0.08 and back-translation 0.22.", ""]
        par_rows = []
        for s in with_par:
            kept = augmented[s]["pairs"]
            originals = {r["id"]: r for r in rows[s]}
            diff = [word_difference(originals[p["augmented_from"]]["nl"], p["nl"]) for p in kept if p["augmented_from"] in originals]
            par_rows.append([s, len({p["augmented_from"] for p in kept}), len({p["formula_id"] for p in kept}), len(kept),
                             len(augmented[s]["dropped"]),
                             sum(1 for p in kept if p["augmentation"]["missing_symbols"]),
                             f"{sum(diff) / len(diff):.2f}" if diff else "-"])
        out += table(["Set", "Descriptions paraphrased", "Formulas", "Paraphrases", "Out (round trip or by hand)",
                      "Missing a symbol", "Word difference"], par_rows)

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
