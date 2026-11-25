"""
Decisions taken by hand on pairs of set 1 and on their paraphrases (step 9), kept in data/dataset/set_1/manual.jsonl
(tracked) and applied every time the files are written, so that a rebuild never loses them. One line per description:

    id               the pair (<record id>:D<n>) or the paraphrase (<record id>:D<n>:A<n>)
    action           keep     in the dataset whatever the round trip says (read by hand, the description is enough)
                     fix      the formula is replaced by `stl` (the description stays), and the pair is in the dataset
                              (pairs only)
                     drop     out of the dataset whatever the round trip says
    stl              the new formula (fix only), in the dataset's syntax; it must parse with stlgen
    note             why, in a few words
    formula_before   the dataset's formula when the decision was taken, to notice if it changes later

A fix is applied by step 7, which writes set 1's candidates: it changes the formula the round trip checks. Keep and
drop are applied by step 8, where the round trip splits the candidates into pairs.jsonl and dropped.jsonl
(src/dataset/sets.py, split). The decisions are written in the review sheets of data/dataset/roundtrip/roundtrip.xlsx
(step 8) and read from there into this file by `scripts/08_roundtrip.py --import-decisions`. They apply per
description, not per formula: several descriptions can share a formula, and a fix that suits one may not suit the
others.
"""
import json
from pathlib import Path

from config import DATA_DIR

MANUAL_FILE = DATA_DIR / "dataset" / "set_1" / "manual.jsonl"
ACTIONS = ("keep", "fix", "drop")
PARAPHRASE_ACTIONS = ("keep", "drop")


def is_paraphrase(identifier: str) -> bool:
    return ":A" in identifier


def read_decisions(path: Path = MANUAL_FILE) -> dict[str, dict]:
    if not path.exists():
        return {}
    return {d["id"]: d for d in (json.loads(line) for line in open(path, encoding="utf-8") if line.strip())}


def write_decisions(decisions: dict[str, dict], path: Path = MANUAL_FILE) -> None:
    with open(path, "w", encoding="utf-8") as out:
        for d in sorted(decisions.values(), key=lambda d: d["id"]):
            out.write(json.dumps(d, ensure_ascii=False) + "\n")


def check_decision(decision: str, stl: str, parsed: dict | None, paraphrase: bool = False) -> str | None:
    """
    What is wrong with a decision written in the xlsx, or None. `parsed`: stlgen's answer for `stl` (fix only);
    `paraphrase`: whether it is a paraphrase of step 9.
    """
    allowed = PARAPHRASE_ACTIONS if paraphrase else ACTIONS
    if decision not in allowed:
        return f"decision {decision!r} is not one of {', '.join(allowed)}" + (" (a paraphrase)" if paraphrase else "")
    if decision == "fix" and not stl:
        return "fix without a fixed formula"
    if decision != "fix" and stl:
        return f"a fixed formula with decision {decision} (only fix takes one)"
    if decision == "fix" and not parsed["ok"]:
        return f"the fixed formula doesn't parse: {parsed['error'][:120]}"
    return None


def apply_decisions(rows: list[dict], decisions: dict[str, dict], trees: dict[str, dict]) -> tuple[list[dict], dict, list[str]]:
    """
    Set 1's candidates with the decisions applied (step 7): a decided row gets `manual` (the decision without its id),
    so that it can be seen in the candidates; only a fix changes the row (keep and drop are applied by the split of
    step 8). A fixed
    row gets the new `stl`, `stl_before_fix`, its `pattern` from the new formula and `template` None (step 6's
    template comes from its own parser, which doesn't read this syntax). `trees`: {formula: stlgen's answer} for the
    fixed formulas. Returns (rows, counts per action, warnings).
    """
    from src.normalization.pattern import pattern
    counts, warnings, seen = {a: 0 for a in ACTIONS}, [], set()
    decisions = {i: d for i, d in decisions.items() if not is_paraphrase(i)}   # those are applied by step 8 only
    for row in rows:
        decision = decisions.get(row["id"])
        if decision is None:
            continue
        seen.add(row["id"])
        if decision["formula_before"] != row["stl"] and row.get("stl_before_fix") is None:
            warnings.append(f"{row['id']}: the formula is now {row['stl']!r}, the decision was taken on {decision['formula_before']!r}")
        row["manual"] = {k: v for k, v in decision.items() if k != "id"}
        counts[decision["action"]] += 1
        if decision["action"] == "fix":
            row["stl_before_fix"], row["stl"] = row["stl"], decision["stl"]
            row["pattern"], row["template"] = pattern(trees[decision["stl"]]["ast"])[0], None
    warnings += [f"{i}: decided by hand but not in set 1" for i in sorted(set(decisions) - seen)]
    return rows, counts, warnings
