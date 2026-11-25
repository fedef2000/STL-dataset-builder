"""Step 8, the round-trip check (src/evaluation/roundtrip.py), without calling a model."""
import pytest

from src.evaluation import roundtrip
from src.evaluation.stlgen import StlgenError, parse_many


def test_check_answer():
    assert roundtrip.check_answer('{"formula": "F[0,5] p"}') == ("F[0,5] p", [])
    assert roundtrip.check_answer('```json\n{"formula": " G[0,1] q "}\n```')[0] == "G[0,1] q"
    assert roundtrip.check_answer('{"formula": ""}')[0] is None
    assert roundtrip.check_answer("F[0,5] p")[0] is None


def test_empty_formula_is_a_final_answer():
    item = {"key": "k"}
    empty = {"key": "k", "formula": None, "raw_answer": '{"formula":""}'}
    broken = {"key": "k", "formula": None, "raw_answer": "I cannot"}
    assert roundtrip.empty_answer(empty) and roundtrip.usable(empty, item)
    assert not roundtrip.empty_answer(broken) and not roundtrip.usable(broken, item)


def test_best_level():
    assert roundtrip.best_level({"a": {"level": "near"}, "b": {"level": "different"}}) == "near"
    assert roundtrip.best_level({"a": {"level": "unparseable"}, "b": {"level": "same_pattern"}}) == "same_pattern"
    assert roundtrip.best_level({"a": {"level": None}, "b": {"level": "equivalent"}}) is None
    assert roundtrip.best_level({"a": {"level": "not_checkable"}, "b": {"level": "not_checkable"}}) == "not_checkable"


def test_prompt_examples_parse():
    assert len(roundtrip.EXAMPLE_FORMULAS) == 4
    try:
        parsed = parse_many({str(n): f for n, f in enumerate(roundtrip.EXAMPLE_FORMULAS)})
    except StlgenError:
        pytest.skip("stlgen of stl-nl with the parse command not built")
    assert all(p["ok"] for p in parsed.values())


def test_review_sheets_and_verdict():
    def row(i, group, levels, augmented_from=None):
        return {"id": i, "group": group, "augmented_from": augmented_from, "best": roundtrip.best_level(levels), "models": levels}
    labels = [roundtrip.short(m) for m in roundtrip.MODELS]
    match = {m: {"level": "renamed"} for m in labels}
    one = dict(zip(labels, ({"level": "renamed"}, {"level": "different"})))
    miss = {m: {"level": "different"} for m in labels}
    unread = {m: {"level": "not_checkable"} for m in labels}
    rows = [row("A:D1", "set_1", match), row("B:D1", "set_1", one), row("C:D1", "set_1", miss), row("D:D1", "set_1", unread),
            row("A:D1:A1", "paraphrase", miss, "A:D1"), row("C:D1:A1", "paraphrase", miss, "C:D1")]
    sheets = roundtrip.review_sheets(rows)
    assert [r["id"] for r in sheets["set 1, both miss"]] == ["C:D1"]
    assert [r["id"] for r in sheets["paraphrase loses it"]] == ["A:D1:A1"]   # its original matched
    assert [roundtrip.verdict(r)["verdict"] for r in rows[:4]] == ["match", "match", "miss", "not_checkable"]
    assert roundtrip.verdict(rows[0]) == {"verdict": "match", "best": "renamed"}


def test_matched_with_stlsat():
    assert roundtrip.matched({"level": "near"})
    assert roundtrip.matched({"level": "different", "sat": "equivalent"})
    assert not roundtrip.matched({"level": "same_pattern", "sat": "stronger"})
    assert not roundtrip.matched({"level": "different", "sat": None})
    assert roundtrip.sat_details({"level": "different", "sat": "equivalent", "sat_mapping": {"open": "door_open"}}) \
        == "equivalent (open -> door_open)"
    assert roundtrip.sat_details({"level": "near", "sat": "not_checkable", "sat_reason": "an infinite interval end"}) \
        == "not_checkable: an infinite interval end"
