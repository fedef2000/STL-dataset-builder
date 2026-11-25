"""The comparator of formulas (src/evaluation/compare.py), on trees parsed by stlgen: one case per rewrite and level."""
import pytest

from src.evaluation.compare import compare
from src.evaluation.stlgen import StlgenError, parse_many


def _stlgen_works() -> bool:
    try:
        return parse_many({"x": "p"})["x"]["ok"]
    except StlgenError:
        return False


pytestmark = pytest.mark.skipif(not _stlgen_works(), reason="stlgen of stl-nl with the parse command not built")


def check(reference: str, candidate: str) -> dict:
    parsed = parse_many({"reference": reference, "candidate": candidate})
    tree = lambda key: parsed[key]["ast"] if parsed[key]["ok"] else None
    return compare(tree("reference"), tree("candidate"))


def level(reference: str, candidate: str) -> str:
    return check(reference, candidate)["level"]


# ---------------------------------------------------------------- equivalent: the standard form

@pytest.mark.parametrize("reference, candidate", [
    ("G[0,10] (x < 5)", "G[0,10] (x < 5)"),
    ("a -> b", "!a || b"),                                          # implication
    ("!F[0,5] p", "G[0,5] !p"),                                     # negation through F
    ("!G[0,5] p", "F[0,5] !p"),
    ("!(a && b)", "!a || !b"),                                      # De Morgan
    ("!(p U[0,3] q)", "(!p) R[0,3] (!q)"),                          # until / release duality
    ("!(x < 3)", "x >= 3"),                                         # negated comparison
    ("!!a", "a"),
    ("b && a && a", "a && b"),                                      # sorted, repeats removed
    ("(a && b) && c", "a && (b && c)"),                             # flattened
    ("G[0,5] (a && b)", "G[0,5] a && G[0,5] b"),                    # G over &&
    ("F[0,5] (a || b)", "F[0,5] a || F[0,5] b"),                    # F over ||
    ("x - y > 0", "x > y"),                                         # comparisons as one polynomial
    ("2 * x > 4", "x > 2"),
    ("3 < x", "x > 3"),
    ("x <= 0.5", "x <= 1/2"),
    ("|0 - x| < 2", "|x| < 2"),
    ("|2 * x| < 4", "|x| < 2"),
    ("|c_e| <= 2.25", "(c_e >= -2.25) && (c_e <= 2.25)"),          # an absolute value against a number, opened
    ("|x - y| < 1", "(x - y < 1) && (y - x < 1)"),
    ("|x| > 3", "(x > 3) || (x < -3)"),
    ("3 >= |x|", "(-3 <= x) && (x <= 3)"),
    ("!(true U[0,2] (|s| > 2))", "G[0,2] (|s| <= 2)"),             # true U q = F q
    ("false R[1,4] p", "G[1,4] p"),                                 # false R q = G q
    ("a && true", "a"),                                             # constants
    ("a || (1 < 2)", "true"),
    ("G[0,inf] ((v > 5) -> (F[0,10] (w < 2)))", "G[0,inf] ((v <= 5) || (F[0,10] (w < 2)))"),
])
def test_equivalent(reference, candidate):
    result = check(reference, candidate)
    assert result["level"] == "equivalent" and result["renamed"] is False


@pytest.mark.parametrize("reference, candidate", [
    ("G[0,5] (a || b)", "G[0,5] a || G[0,5] b"),                    # G doesn't distribute over ||
    ("F[0,5] (a && b)", "F[0,5] a && F[0,5] b"),                    # nor F over &&
    ("(a U[0,3] b) && F[0,1] a", "(b U[0,3] a) && F[0,1] a"),      # a U b is not b U a ...
    ("|x| <= 2", "(x >= -2) || (x <= 2)"),                          # |x| <= 2 is an and, not an or
])
def test_not_equivalent(reference, candidate):
    assert level(reference, candidate) not in ("equivalent", "renamed")


def test_swapped_operands_are_a_renaming():
    # ... unless nothing else tells a from b: then swapping the names gives the other formula
    assert level("a U[0,3] b", "b U[0,3] a") == "renamed"
    assert level("x > y", "y > x") == "renamed"


# ---------------------------------------------------------------- renamed

def test_renamed_signal():
    result = check("G[0,10] (omega < 4750)", "G[0,10] (speed < 4750)")
    assert result["level"] == "renamed" and result["mapping"] == {"speed": "omega"}


def test_renamed_atoms_follow_their_role():
    result = check("G[0,inf] (a -> F[0,2] b)", "G[0,inf] (zone -> F[0,2] planner)")
    assert result["level"] == "renamed" and result["mapping"] == {"zone": "a", "planner": "b"}


def test_renamed_parameter():
    result = check("F[0,T] p", "F[0,T_max] p")
    assert result["level"] == "renamed" and result["mapping"] == {"T_max": "T"}


def test_renamed_accepts_swapped_names():
    # names the description gave, swapped: renamed, not equivalent (hence the two outcomes)
    result = check("(x_3 <= 10) && (x_4 >= 5)", "(x_4 <= 10) && (x_3 >= 5)")
    assert result["level"] == "renamed" and result["mapping"] == {"x_4": "x_3", "x_3": "x_4"}


def test_renaming_keeps_kinds_apart():
    # an atom never becomes a real-valued signal; constants are never renamed
    assert level("G[0,5] a", "G[0,5] (x > 0)") not in ("equivalent", "renamed", "near")
    assert level("x < 4750", "x < 4000") not in ("equivalent", "renamed", "near")


def test_renaming_needs_one_to_one():
    assert level("(x > 1) && (y > 1)", "(x > 1) && (x > 1)") not in ("equivalent", "renamed")


# ---------------------------------------------------------------- near

@pytest.mark.parametrize("reference, candidate, details", [
    ("F[0,5] ((x_2 <= 10) && (x_3 <= 10))", "F[0,5] ((x_2 < 10) && (x_3 < 10))", ["strict"]),
    ("F[0,3) phi", "F[0,3] phi", ["open_end"]),
    ("G[0,inf] ((G[0,2] m) -> (F(2,12] alarm))", "(G[0,2] m) -> (F(2,12] alarm)", ["outer_always"]),
    ("G[0,inf] a && F[0,5] b", "a && F[0,5] b", ["outer_always"]),
    ("G[0,inf] (x <= 3)", "x < 3", ["strict", "outer_always"]),
])
def test_near(reference, candidate, details):
    result = check(reference, candidate)
    assert result["level"] == "near" and result["near"] == details


def test_near_with_renaming():
    result = check("G[0,10] (omega < 4750)", "G[0,10] (rpm <= 4750)")
    assert result["level"] == "near" and result["renamed"] is True and result["mapping"] == {"rpm": "omega"}


def test_outer_always_only_at_the_top():
    assert level("F[0,5] G[0,inf] a", "F[0,5] a") != "near"


# ---------------------------------------------------------------- same pattern, different, unparseable

def test_same_pattern_other_bound():
    result = check("F[0,10] (x > 3)", "F[0,20] (x > 3)")
    assert result["level"] == "same_pattern" and result["bounds_equal"] is False and result["leaves_equal"] is True


def test_same_pattern_other_constant():
    result = check("F[0,10] (x > 3)", "F[0,10] (y > 4)")
    assert result["level"] == "same_pattern" and result["bounds_equal"] is True and result["leaves_equal"] is False


def test_different():
    result = check("F[0,10] (x > 3)", "G[0,10] (x > 3)")
    assert result["level"] == "different" and result["leaves_equal"] is True


def test_unparseable_and_not_checkable():
    assert level("F[0,10] p", "eventually p within 10") == "unparseable"
    assert level("F[0,0.3] p", "F[0,1] p") == "not_checkable"

