"""Step 7 (the sets), the split of step 8, the analysis."""
import json

from src.dataset import sets
from src.extraction.records import item_key


def test_item_key_follows_the_content():
    a = [{"role": "user", "content": "G[0,2] p: p holds for 2 s"}]
    assert item_key(a) == item_key([{"role": "user", "content": "G[0,2] p: p holds for 2 s"}])
    assert item_key(a) != item_key([{"role": "user", "content": "G[0,3] p: p holds for 2 s"}])


def test_stlnl_rows(tmp_path):
    """An stl-nl run: a formula with two descriptions, one with none; set 2 links the first to its paper."""
    from src.dataset.sets import stlnl_rows
    atom = {"type": "atom", "name": "p"}
    ast = {"type": "globally", "interval": {"lower": 0, "upper": 5}, "child": atom}
    formulas = [{"formula_id": "h1", "stl": "G[0,5] p", "ast": ast,
                 "source": {"source_index": 0, "path": "/x/f00001.stl", "source_text": "G[0,5] p\n"}},
                {"formula_id": "h2", "stl": "F[0,5] p", "ast": {**ast, "type": "eventually"},
                 "source": {"source_index": 1, "path": "/x/f00002.stl", "source_text": "F[0,5] p\n"}}]
    pairs = [{"formula_id": "h1", "realization_index": 1, "nl": "p holds for six steps"},
             {"formula_id": "h1", "realization_index": 0, "nl": "p holds from step 0 to step 5"}]
    for name, rows in (("formulas.jsonl", formulas), ("pairs.jsonl", pairs)):
        (tmp_path / name).write_text("".join(json.dumps(r) + "\n" for r in rows))
    manifest = [{"id": "P:F1", "file": "stl/f00001.stl", "normalized": "G[0,5] p", "template": "G[#,#] a", "original": r"\Box_{[0,5]} p"}]
    records = {"P:F1": {"paper_id": "P", "domain": "generic", "license_tier": "permissive_cc", "license": "cc-by", "source_type": "latex"}}

    rows, counts = stlnl_rows("set_2", tmp_path, manifest, records)
    assert [r["id"] for r in rows] == ["P:F1:R0", "P:F1:R1"]
    assert rows[0]["paper_id"] == "P" and rows[0]["stlnl_formula_id"] == "h1" and rows[0]["pattern"] == "G[#,#] φ"
    assert counts["descriptions"] == 2 and sum(n for what, n in counts.items() if what.startswith("formulas without")) == 1

    rows, _ = stlnl_rows("set_3", tmp_path)   # no paper: the formula is named after its source index
    assert rows[0]["id"] == "stlnl_0:R0" and rows[0]["paper_id"] is None


def test_pattern_tree():
    from src.dataset.analysis import operators, parse
    assert operators(parse("G[#,#] (φ -> F[#,#] ψ)")) == {"G", "->", "F"}
    tree = parse("(φ && ψ) R[#,#] (χ && θ)")   # U and R bind looser than the unary operators, tighter than &&
    assert tree[0] == "R" and operators(tree) == {"R", "&&"}
    tree = parse("(F[#,#] G[#,#] φ) || (F[#,#] G[#,#] ψ)")
    assert tree[0] == "||" and operators(tree) == {"||", "F", "G"}
    assert parse("!(φ U[#,#] ψ)")[0] == "!"


def test_without_next_leaves_out_only_the_operator():
    from src.dataset.sets import without_next
    rows = [{"stl": s} for s in ("G[0,inf] (red -> (X G[0,5] !red))", "G[0,1] ((l == p) && (X (l == n)))", "X !a",
                                 "G[0,l - 2] (XXS -> (F[0,1] XXS))", "G[1,4] (XMEAS_21 > 94.6)", "F[0,2] (X != 3)",
                                 "G[0,5] (X > 1)", "F[1,1] p")]
    kept, left_out = without_next(rows)
    assert left_out == 3 and [r["stl"] for r in kept] == [r["stl"] for r in rows[3:]]


def verdict(v):
    return {"verdict": v, "best": {"match": "renamed", "miss": "different", "not_checkable": "not_checkable"}[v]}


def test_split_follows_the_round_trip_and_the_hand():
    rows = [{"id": i, "stl": "p", "manual": {"action": "stale"}} for i in ("A", "B", "C", "D", "E", "F", "G")]
    verdicts = {"A": verdict("match"), "B": verdict("miss"), "C": verdict("not_checkable"), "D": verdict("match"),
                "E": verdict("miss"), "F": verdict("miss")}
    decisions = {"D": {"id": "D", "action": "drop", "note": "covers another formula"},
                 "E": {"id": "E", "action": "keep", "note": "enough"}, "F": {"id": "F", "action": "fix", "note": "phi"}}
    pairs, dropped = sets.split(rows, verdicts, decisions)
    assert [r["id"] for r in pairs] == ["A", "E", "F"]
    why = {r["id"]: r["dropped"] for r in dropped}
    assert why == {"B": sets.BOTH_MISS, "C": sets.NOT_CHECKABLE, "D": "by hand: covers another formula", "G": sets.NO_ANSWER}
    assert pairs[0]["roundtrip"] == verdict("match") and "manual" not in pairs[0]   # a stale `manual` goes
    assert pairs[1]["manual"] == {"action": "keep", "note": "enough"}
    assert {sets.short_reason(r["dropped"]) for r in dropped} == {"both miss", "not checkable", "dropped by hand", "no answer yet"}


def test_split_of_paraphrases_needs_the_original():
    rows = [{"id": "A:A1", "augmented_from": "A"}, {"id": "B:A1", "augmented_from": "B"}, {"id": "B:A2", "augmented_from": "B"}]
    verdicts = {i: verdict("match") for i in ("A:A1", "B:A1", "B:A2")}
    keep = {"B:A2": {"id": "B:A2", "action": "keep", "note": ""}}
    pairs, dropped = sets.split(rows, verdicts, keep, originals={"A"})
    assert [r["id"] for r in pairs] == ["A:A1"] and all(r["dropped"] == sets.ORIGINAL_OUT for r in dropped)
