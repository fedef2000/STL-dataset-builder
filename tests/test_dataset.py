"""Step 7: the checks on the judge's answers, the vote and the signals computed without a model."""
import json

from src.dataset.judge import build_messages, check_answer, item_key, vote
from src.dataset.sets import numbers_missing


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


def test_numbers_missing():
    assert numbers_missing("G[0,2] (x < 4300)", "x stays below 4300 for two seconds") == []
    assert numbers_missing("F[10,20] sat", "sat occurs after req") == ["10", "20"]
    assert numbers_missing("G[0,inf] (x > -1.5)", "x is always above -1.5") == []
    assert numbers_missing("F[0,200] (v < 30.85)", "v below 30.85m within 200ms") == []   # units attached
    assert numbers_missing("G[2,26] (y > 11.1)", "y above 11.10 between 2.0 and 26") == []   # values, not text
    assert numbers_missing("G[0,5] (x_1 > 3)", "x_1 above 3 for 5 s") == []   # the 1 of x_1 is a name, not a number
