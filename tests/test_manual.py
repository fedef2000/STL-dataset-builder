"""Decisions taken by hand on pairs of set 1 (src/dataset/manual.py), and their way through roundtrip.xlsx (step 8)."""
import pytest

from src.dataset import manual
from src.evaluation.stlgen import StlgenError, parse_many


def parsed(stl):
    try:
        return parse_many({"x": stl})["x"]
    except StlgenError:
        pytest.skip("stlgen of stl-nl with the parse command not built")


def test_check_decision():
    assert manual.check_decision("keep", None, None) is None
    assert manual.check_decision("drop", None, None) is None
    assert "not one of" in manual.check_decision("maybe", None, None)
    assert "without a fixed formula" in manual.check_decision("fix", None, None)
    assert "only fix takes one" in manual.check_decision("drop", "G[0,1] p", None)
    assert manual.check_decision("fix", "G[0,tau] (h_x >= 0)", parsed("G[0,tau] (h_x >= 0)")) is None
    assert "doesn't parse" in manual.check_decision("fix", "G[0,tau] h_x >= 0)", parsed("G[0,tau] h_x >= 0)"))


def test_check_decision_paraphrases():
    assert manual.check_decision("drop", None, None, paraphrase=True) is None
    assert manual.check_decision("keep", None, None, paraphrase=True) is None
    assert "(a paraphrase)" in manual.check_decision("fix", "F[0,1] p", None, paraphrase=True)
    assert "not one of" in manual.check_decision("promote", None, None)   # gone with the judge
    assert manual.is_paraphrase("W1:F2:D1:A2") and not manual.is_paraphrase("W1:F2:D1")


def row(i, stl):
    return {"id": i, "stl": stl, "pattern": "?", "template": "?", "roundtrip": None}


def test_apply_decisions():
    fixed = "G[0,tau] (h_x >= 0)"
    decisions = {
        "A:D1": {"id": "A:D1", "action": "fix", "stl": fixed, "note": "the description gives the condition", "formula_before": "G[0,tau] phi"},
        "B:D1": {"id": "B:D1", "action": "drop", "stl": None, "note": "covers only the trajectory", "formula_before": "F[0,1] q"},
        "C:D1": {"id": "C:D1", "action": "keep", "stl": None, "note": "", "formula_before": "G[0,1] p"},
        "Z:D1": {"id": "Z:D1", "action": "keep", "stl": None, "note": "", "formula_before": "p"},
        "A:D1:A1": {"id": "A:D1:A1", "action": "drop", "stl": None, "note": "loses tau", "formula_before": "G[0,tau] phi"},
    }
    rows = [row("A:D1", "G[0,tau] phi"), row("B:D1", "F[0,1] q"), row("C:D1", "G[0,2] p"), row("D:D1", "F[0,1] r")]
    rows, counts, warnings = manual.apply_decisions(rows, decisions, {fixed: parsed(fixed)})
    a, b, c, d = rows
    assert a["stl"] == fixed and a["stl_before_fix"] == "G[0,tau] phi" and a["pattern"] == "G[#,#] φ" and a["template"] is None
    assert b["manual"]["action"] == "drop" and b["stl"] == "F[0,1] q"
    assert "manual" not in d
    assert counts == {"keep": 1, "fix": 1, "drop": 1}
    # C's formula changed since the decision; Z isn't in the set
    assert any(w.startswith("C:D1: the formula is now") for w in warnings) and any(w.startswith("Z:D1") for w in warnings)
    assert not any(w.startswith("A:D1:A1") for w in warnings)   # a paraphrase's decision is step 8's


def test_migrated_file_has_only_current_actions():
    """manual.jsonl as tracked: promote became keep when the judge went (2026-11-25)."""
    assert all(d["action"] in manual.ACTIONS for d in manual.read_decisions().values())


def test_decisions_through_the_xlsx(tmp_path, monkeypatch):
    """Written by step 8, filled in by hand, read back: the decisions come out as they were written."""
    import openpyxl
    from src.evaluation import roundtrip
    monkeypatch.setattr(manual, "MANUAL_FILE", tmp_path / "manual.jsonl")
    monkeypatch.setattr("src.dataset.manual.read_decisions", lambda path=None: {})
    level = {"level": "different", "formula": "F[0,1] x", "near": [], "mapping": {}, "bounds_equal": True, "leaves_equal": False}
    rows = [{"id": "A:D1", "group": "set_1", "nl": "h_x >= 0 always", "stl": "G[0,tau] phi",
             "augmented_from": None, "best": "different", "models": {roundtrip.short(m): level for m in roundtrip.MODELS}}]
    path = tmp_path / "roundtrip.xlsx"
    roundtrip.write_xlsx(rows, path)
    book = openpyxl.load_workbook(path)
    sheet = book["set 1, both miss"]
    header = [c.value for c in sheet[1]]
    sheet.cell(2, header.index("decision") + 1, "Fix")
    sheet.cell(2, header.index("fixed formula") + 1, "G[0,tau] (h_x >= 0)")
    sheet.cell(2, header.index("note") + 1, "the condition, not phi")
    book.save(path)
    found, problems = roundtrip.xlsx_decisions(path)
    assert problems == [] and found == {"A:D1": {"action": "fix", "stl": "G[0,tau] (h_x >= 0)", "note": "the condition, not phi"}}
    assert "decision" not in [c.value for c in openpyxl.load_workbook(path)["all"][1]]
