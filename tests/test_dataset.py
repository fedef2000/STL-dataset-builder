"""Step 7: the checks on the judge's answers, the vote and the signals computed without a model."""
import json

from src.dataset.judge import build_messages, check_answer, item_key, vote


def answer(*items):
    return json.dumps({"descriptions": [dict(zip(("id", "describes", "faithful"), item), problems=[], reason="r") for item in items]})


def test_check_answer_labels():
    judgments, problems = check_answer(answer(("D1", "yes", "correct"), ("D2", "no", None), ("D3", "yes", "wrong")), 3)
    assert problems == [] and [j["label"] for j in judgments] == ["correct", "no", "wrong"]


def test_check_answer_fenced_json():
    judgments, _ = check_answer("```json\n" + answer(("D1", "yes", "ambiguous")) + "\n```", 1)
    assert judgments[0]["label"] == "ambiguous"


def test_check_answer_rejects_missing_or_extra_ids():
    assert check_answer(answer(("D1", "yes", "correct")), 2)[0] is None
    assert check_answer(answer(("D2", "yes", "correct")), 1)[0] is None


def test_check_answer_rejects_inconsistent_labels():
    assert check_answer(answer(("D1", "no", "correct")), 1)[0] is None
    assert check_answer(answer(("D1", "yes", None)), 1)[0] is None


def test_check_answer_rejects_other_keys_and_prose():
    assert check_answer(json.dumps({"items": []}), 1)[0] is None
    assert check_answer("The formula says ...", 1)[0] is None


def test_vote():
    assert vote(["correct", "correct"], None) == ("correct", "agreed")
    assert vote(["correct", "ambiguous"], None)[0] == "disputed"
    assert vote(["correct", "ambiguous"], "ambiguous") == ("ambiguous", "decided by the third model")
    assert vote(["correct", "ambiguous"], "wrong")[0] == "undecided"
    assert vote(["correct", None], None)[0] == "unjudged"


def test_item_key_follows_the_content():
    a = build_messages("G[0,2] p", ["p holds for 2 s"])
    assert item_key(a) == item_key(build_messages("G[0,2] p", ["p holds for 2 s"]))
    assert item_key(a) != item_key(build_messages("G[0,3] p", ["p holds for 2 s"]))


def test_variables_only_when_given():
    assert "Variable meanings" not in build_messages("p", ["d"])[1]["content"]
    assert "- \\mu_C: note C" in build_messages("mu_C", ["d"], {"\\mu_C": "note C"})[1]["content"]


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
    manifest = [{"id": "P:F1", "file": "stl/f00001.stl", "normalized": "G[0,5] p", "pattern": "G[#,#] a", "original": r"\Box_{[0,5]} p"}]
    records = {"P:F1": {"paper_id": "P", "domain": "generic", "license_tier": "permissive_cc", "license": "cc-by", "source_type": "latex"}}

    rows, counts = stlnl_rows("set_2", tmp_path, manifest, records)
    assert [r["id"] for r in rows] == ["P:F1:R0", "P:F1:R1"]
    assert rows[0]["paper_id"] == "P" and rows[0]["stlnl_formula_id"] == "h1" and rows[0]["skeleton"] == "G[#,#] φ"
    assert counts["descriptions"] == 2 and sum(n for what, n in counts.items() if what.startswith("formulas without")) == 1

    rows, _ = stlnl_rows("set_3", tmp_path)   # no paper: the formula is named after its source index
    assert rows[0]["id"] == "stlnl_0:R0" and rows[0]["paper_id"] is None
