"""
The tree of a normalized formula (parser.Node) written as the AST that `stlgen import` gives for its text, so that the
skeleton (skeleton.py, copied from stl-nl) can be computed without stlgen: for the formulas of the faithful mode, which
stlgen can't parse (open intervals, real or expression bounds, powers). It follows what stlgen does to the text:

    X a        -> F[1,1] a                     (stlgen has no next operator: it writes X as one step of F)
    a <-> b    -> (a && b) || (!a && !b)
    -x         -> 0 - x                        (emit.py writes it so)

For the formulas stlgen can parse, the result gives the same skeleton as stlgen's own AST (tested on every formula ok of
the unpaired run). What stlgen doesn't have is written as stlgen would if it had it: a power is {"type": "power"}, a
bound that is a real number or an expression is {"type": "expression"} (the skeleton writes every finite bound #), and
an open interval is not marked (the skeleton doesn't show the brackets).
"""
import math

from src.normalization.parser import Node

CONNECTIVES = {"and": "and", "or": "or"}
TEMPORAL = {"G": "globally", "F": "eventually", "U": "until", "R": "release"}
ARITHMETIC = {"add": "add", "sub": "subtract", "mul": "multiply", "div": "divide", "pow": "power"}
ZERO = {"type": "rational", "numerator": "0", "denominator": "1"}


def bound(x) -> object:
    """A resolved bound (Bounds.lower or upper) as stlgen writes it."""
    if x == math.inf:
        return {"type": "infinity"}
    if isinstance(x, str):
        return {"type": "parameter", "name": x}
    if isinstance(x, int):
        return x
    return {"type": "expression"}


def interval(node: Node) -> dict:
    return {"lower": bound(node.interval.lower), "upper": bound(node.interval.upper)}


def expression(node: Node) -> dict:
    kind = node.kind
    if kind == "num":
        return {"type": "rational", "numerator": str(node.value.numerator), "denominator": str(node.value.denominator)}
    if kind == "var":
        return {"type": "variable", "name": node.value}
    if kind == "abs":
        return {"type": "abs", "child": expression(node.args[0])}
    if kind == "neg":
        return {"type": "subtract", "left": ZERO, "right": expression(node.args[0])}
    if kind in ARITHMETIC:
        return {"type": ARITHMETIC[kind], "left": expression(node.args[0]), "right": expression(node.args[1])}
    raise ValueError(f"unknown expression node {kind!r}")


def formula(node: Node) -> dict:
    """The stlgen AST of the formula whose tree is `node`."""
    kind = node.kind
    if kind in ("true", "false"):
        return {"type": kind}
    if kind == "atom":
        return {"type": "atom", "name": node.value}
    if kind == "rel":
        return {"type": "relation", "comparison": node.value, "left": expression(node.args[0]),
                "right": expression(node.args[1])}
    if kind == "not":
        return {"type": "not", "child": formula(node.args[0])}
    if kind in CONNECTIVES:
        return {"type": kind, "children": [formula(a) for a in node.args]}
    if kind == "imp":
        return {"type": "implies", "left": formula(node.args[0]), "right": formula(node.args[1])}
    if kind == "iff":
        left, right = (formula(a) for a in node.args)
        return {"type": "or", "children": [{"type": "and", "children": [left, right]},
                                           {"type": "and", "children": [{"type": "not", "child": left},
                                                                        {"type": "not", "child": right}]}]}
    if kind == "X":
        return {"type": "eventually", "interval": {"lower": 1, "upper": 1}, "child": formula(node.args[0])}
    if kind in ("G", "F"):
        return {"type": TEMPORAL[kind], "interval": interval(node), "child": formula(node.args[0])}
    if kind in ("U", "R"):
        return {"type": TEMPORAL[kind], "interval": interval(node), "left": formula(node.args[0]),
                "right": formula(node.args[1])}
    raise ValueError(f"unknown formula node {kind!r}")
