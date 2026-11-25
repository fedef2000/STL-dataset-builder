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
    assert [r["id"] for r in sheets["set 1, not checkable"]] == ["D:D1"]
    assert sheets["stlsat checked"] == []
    assert [roundtrip.verdict(r)["verdict"] for r in rows[:4]] == ["match", "match", "miss", "not_checkable"]
    assert roundtrip.verdict(rows[0]) == {"verdict": "match", "best": "renamed"}


def test_sat_sheet():
    labels = [roundtrip.short(m) for m in roundtrip.MODELS]
    checked = dict(zip(labels, ({"level": "different", "sat": "stronger"}, {"level": "renamed", "sat": "equivalent"})))
    skipped = dict(zip(labels, ({"level": "near", "sat": "sat_skipped"}, {"level": "unparseable", "sat": None})))
    already = {m: {"level": "equivalent", "sat": "equivalent"} for m in labels}
    rows = [{"id": i, "group": "set_1", "augmented_from": None, "best": "different", "models": models}
            for i, models in (("A:D1", checked), ("B:D1", skipped), ("C:D1", already))]
    assert [r["id"] for r in roundtrip.review_sheets(rows)["stlsat checked"]] == ["A:D1"]


@pytest.mark.parametrize("stl, error, why", [
    ("F[0,0.3] (z <= -0.1)", "STL parse error at byte 1: unsupported", "decimal bound"),
    ("G[0,T - 5] (x < 1)", "STL parse error at byte 1: unsupported", "bound with an expression"),
    ("G(2 * i - 1,2 * i) a", "STL parse error at byte 1: unsupported", "bound with an expression; F or G with both ends open"),
    ("G[0,inf] (H -> (!F(0,1) H))", "STL parse error at byte 1: unsupported", "F or G with both ends open"),
    ("G[0,2] (x^2 > 1.5^2)", "STL parse error at byte 1: unsupported", "power (^)"),
    ("G[N,N] (cnt <= N)", 'STL parse error: name "N" is used both as a signal and as an interval parameter',
     "N both a signal and a bound"),
    ("G[0,5] p", "STL parse error: something else", "something else"),
])
def test_why_not_checkable(stl, error, why):
    assert roundtrip.why_not_checkable(stl, error) == why


def test_not_checkable_rows_keep_the_answers(monkeypatch):
    try:
        parse_many({"0": "p"})
    except StlgenError:
        pytest.skip("stlgen of stl-nl with the parse command not built")
    item = {"id": "X:F1:D1", "group": "set_1", "formula_id": "X:F1", "augmented_from": None, "nl": "within 0.3 s z drops",
            "stl": "F[0,0.3] (z <= -0.1)", "key": "k"}
    stored = {(*roundtrip.parse_model(label), item["id"]): {"key": "k", "formula": "F[0,0.3] (z <= -0.1)"}
              for label in roundtrip.MODELS}
    monkeypatch.setattr(roundtrip, "read_answers", lambda: stored)
    [row] = roundtrip.results([item], roundtrip.reference_trees([item]), use_sat=False)
    assert row["best"] == "not_checkable" and row["stl_error"] == "decimal bound"
    assert all(v["level"] == "not_checkable" and v["formula"] == "F[0,0.3] (z <= -0.1)" for v in row["models"].values())


def test_matched_with_stlsat():
    assert roundtrip.matched({"level": "near"})
    assert roundtrip.matched({"level": "different", "sat": "equivalent"})
    assert not roundtrip.matched({"level": "same_pattern", "sat": "stronger"})
    assert not roundtrip.matched({"level": "different", "sat": None})
    assert roundtrip.sat_details({"level": "different", "sat": "equivalent", "sat_mapping": {"open": "door_open"}}) \
        == "equivalent (open -> door_open)"
    assert roundtrip.sat_details({"level": "near", "sat": "sat_skipped", "sat_reason": "an infinite interval end"}) \
        == "sat_skipped: an infinite interval end"
