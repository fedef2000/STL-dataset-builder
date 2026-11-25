"""The second stage of the comparator (src/evaluation/sat.py): stlsat on trees parsed by stlgen."""
import pytest

from src.evaluation import sat
from src.evaluation.compare import compare
from src.evaluation.stlgen import StlgenError, parse_many


def _tools_work() -> bool:
    try:
        return parse_many({"x": "p"})["x"]["ok"] and sat.satisfiable("p && !p") == "unsat"
    except (StlgenError, sat.StlsatError):
        return False


pytestmark = pytest.mark.skipif(not _tools_work(), reason="stlgen (parse) or stlsat not built")


def trees(*formulas: str) -> list[dict]:
    parsed = parse_many({str(n): f for n, f in enumerate(formulas)})
    return [parsed[str(n)]["ast"] for n in range(len(formulas))]


def check(reference: str, candidate: str) -> dict:
    r, c = trees(reference, candidate)
    return sat.check(r, c, compare(r, c)["mapping"])


@pytest.mark.parametrize("reference, candidate, outcome", [
    ("F[0,5] F[0,3] p", "F[0,8] p", "equivalent"),                       # nested operators merged: compare.py misses it
    ("G[0,3] p", "G[0,5] p", "stronger"),                                # the answer asks more
    ("G[0,5] p", "G[0,3] p", "weaker"),
    ("F[0,4] p", "G[0,4] !p", "incomparable"),
    ("F(0,3] p", "F[1,3] p", "equivalent"),                              # an open end is one step in
    ("G[0,10] (|x - 2*y| / 2 <= 1/2)", "G[0,10] ((x - 2*y <= 1) && (2*y - x <= 1))", "equivalent"),
    ("p U[0,0] q", "p && q", "equivalent"),                              # inclusive until
    ("x - 0.5 * y > 1", "2 * x > y + 2", "equivalent"),
])
def test_outcomes(reference, candidate, outcome):
    assert check(reference, candidate)["sat"] == outcome


def test_renaming_one_name():
    result = check("F[0,5] F[0,3] door_open", "F[0,8] open")
    assert result["sat"] == "equivalent" and result["sat_mapping"] == {"open": "door_open"}


def test_renaming_finds_the_right_order():
    result = check("F[0,5] F[0,3] ((x > 2) && (y < 1))", "F[0,8] ((s2 < 1) && (s1 > 2))")
    assert result["sat"] == "equivalent" and result["sat_mapping"] == {"s1": "x", "s2": "y"}


def test_renamings_likeliest_first():
    r, c = trees("(speed > 80) && (temp < 3) && F[0,2] (speed > temp)", "F[0,2] (t < 3) && (v > 80) && (v > t)")
    first = sat.renamings(r, c)[0]
    assert {k[1]: v[1] for k, v in first.items()} == {"v": "speed", "t": "temp"}


@pytest.mark.parametrize("reference, candidate, reason", [
    ("G[0,inf] p", "G[0,inf] p", "an infinite interval end"),
    ("G[0,T] p", "G[0,5] p", "a named interval end"),
    ("G[0,5] p", "G[0,T] p", "a named interval end"),
    ("x * y > 1", "x > 1", "arithmetic beyond affine"),
    ("p && q", "a", "a different number of atoms"),
    ("(x1 > 1) && (x2 > 2) && (x3 > 3) && (x4 > 4) && (x5 > 5)",
     "(y1 > 1) && (y2 > 2) && (y3 > 3) && (y4 > 4) && (y5 > 5)", "too many renamings"),
])
def test_not_checkable(reference, candidate, reason):
    result = check(reference, candidate)
    assert result["sat"] == "not_checkable" and result["sat_reason"].startswith(reason)


def test_reference_flag():
    unsat, valid, plain = trees("p U[7,9] !p", "G[0,3] (p || !p)", "F[0,2] p")
    assert sat.reference_flag(unsat) == "unsatisfiable"
    assert sat.reference_flag(valid) == "valid"
    assert sat.reference_flag(plain) is None


def test_text_for_stlsat():
    tree, = trees("G[0,10] (|x - 2*y| / 2 <= 1/2) -> (a U(0,4) (3 < x - 0.5*z))")
    assert sat.to_stlsat(tree, lambda i: i[1]) == \
        "((G[0,10] ((|1/2*x - y| - 1/2 <= 0))) -> (((a) U[1,3] ((0 - x + 1/2*z + 3 < 0)))))"
