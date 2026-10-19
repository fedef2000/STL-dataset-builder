"""
The tree of a normalized formula written in the grammar of stl-nl, with explicit parentheses around every temporal
operand and every binary subformula, so that stl-nl's precedence can't change its reading.
"""
import re
from fractions import Fraction

from src.normalization.parser import Node
from src.normalization.rules import Rejected

IDENTIFIER_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,255}")
CONNECTIVES = {"and": " && ", "or": " || "}
ARITHMETIC = {"add": " + ", "sub": " - "}


def number(x: Fraction) -> str:
    """An integer, an exact decimal (0.25), or a fraction of integers (1/3)."""
    if x.denominator == 1:
        return str(x.numerator)
    d, twos, fives = x.denominator, 0, 0
    while d % 2 == 0:
        d, twos = d // 2, twos + 1
    while d % 5 == 0:
        d, fives = d // 5, fives + 1
    if d != 1:
        return f"{x.numerator}/{x.denominator}"
    places = max(twos, fives)
    digits = str(abs(x.numerator) * 10**places // x.denominator).rjust(places + 1, "0")
    return f"{'-' if x < 0 else ''}{digits[:-places]}.{digits[-places:]}"


def identifier(name: str) -> str:
    if not IDENTIFIER_PATTERN.fullmatch(name):
        raise Rejected("parse_error", f"not a valid name: {name!r}")
    return name


def expression(node: Node) -> str:
    if node.kind == "num":
        return number(node.value)
    if node.kind == "var":
        return identifier(node.value)
    if node.kind == "abs":
        return f"|{expression(node.args[0])}|"
    if node.kind == "neg":
        return f"(0 - {_wrapped_expression(node.args[0])})"
    left, right = node.args
    return f"{_wrapped_expression(left)}{ARITHMETIC[node.kind]}{_wrapped_expression(right)}"


def _wrapped_expression(node: Node) -> str:
    text = expression(node)
    return f"({text})" if node.kind in ARITHMETIC else text


def interval(node: Node) -> str:
    return f"[{node.interval.lower},{node.interval.upper}]"


def formula(node: Node) -> str:
    kind = node.kind
    if kind in ("true", "false"):
        return kind
    if kind == "atom":
        return identifier(node.value)
    if kind == "rel":
        return f"{expression(node.args[0])} {node.value} {expression(node.args[1])}"
    if kind == "not":
        return f"!{_wrapped(node.args[0])}"
    if kind in CONNECTIVES:
        return CONNECTIVES[kind].join(_wrapped(a) for a in node.args)
    if kind in ("imp", "iff"):
        return f"{_wrapped(node.args[0])} {'->' if kind == 'imp' else '<->'} {_wrapped(node.args[1])}"
    if kind in ("G", "F"):
        return f"{kind}{interval(node)} {_wrapped(node.args[0])}"
    if kind == "X":
        return f"X {_wrapped(node.args[0])}"
    if kind in ("U", "R"):
        return f"{_wrapped(node.args[0])} {kind}{interval(node)} {_wrapped(node.args[1])}"
    raise ValueError(kind)


def _wrapped(node: Node) -> str:
    text = formula(node)
    return text if node.kind in ("true", "false", "atom") else f"({text})"
