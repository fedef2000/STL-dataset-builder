"""
The tree of a normalized formula written in the grammar of stl-nl, with explicit parentheses around every temporal
operand and every binary subformula, so that stl-nl's precedence can't change its reading. The same writer gives the
structure of the formula: the same text with every number written # and the names renamed a, b, ... in the order they
appear, so that formulas that differ only in their numbers and names have the same structure.
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


class Names:
    """How the writer writes names and numbers: as they are (the formula), or hidden (its structure)."""

    def __init__(self, hidden: bool = False):
        self.hidden = hidden
        self.renamed: dict[str, str] = {}

    def name(self, name: str) -> str:
        if not self.hidden:
            return identifier(name)
        if name not in self.renamed:
            k = len(self.renamed)
            self.renamed[name] = chr(ord("a") + k) if k < 26 else f"v{k + 1}"
        return self.renamed[name]

    def number(self, x) -> str:
        return "#" if self.hidden else (number(x) if isinstance(x, Fraction) else str(x))


def expression(node: Node, names: Names) -> str:
    if node.kind == "num":
        return names.number(node.value)
    if node.kind == "var":
        return names.name(node.value)
    if node.kind == "abs":
        return f"|{expression(node.args[0], names)}|"
    if node.kind == "neg":
        return f"({names.number(0)} - {_wrapped_expression(node.args[0], names)})"
    left, right = node.args
    return f"{_wrapped_expression(left, names)}{ARITHMETIC[node.kind]}{_wrapped_expression(right, names)}"


def _wrapped_expression(node: Node, names: Names) -> str:
    text = expression(node, names)
    return f"({text})" if node.kind in ARITHMETIC else text


def interval(node: Node, names: Names) -> str:
    return f"[{names.number(node.interval.lower)},{names.number(node.interval.upper)}]"


def _formula(node: Node, names: Names) -> str:
    kind = node.kind
    if kind in ("true", "false"):
        return kind
    if kind == "atom":
        return names.name(node.value)
    if kind == "rel":
        return f"{expression(node.args[0], names)} {node.value} {expression(node.args[1], names)}"
    if kind == "not":
        return f"!{_wrapped(node.args[0], names)}"
    if kind in CONNECTIVES:
        return CONNECTIVES[kind].join(_wrapped(a, names) for a in node.args)
    if kind in ("imp", "iff"):
        return f"{_wrapped(node.args[0], names)} {'->' if kind == 'imp' else '<->'} {_wrapped(node.args[1], names)}"
    if kind in ("G", "F"):
        return f"{kind}{interval(node, names)} {_wrapped(node.args[0], names)}"
    if kind == "X":
        return f"X {_wrapped(node.args[0], names)}"
    if kind in ("U", "R"):
        return f"{_wrapped(node.args[0], names)} {kind}{interval(node, names)} {_wrapped(node.args[1], names)}"
    raise ValueError(kind)


def _wrapped(node: Node, names: Names) -> str:
    text = _formula(node, names)
    return text if node.kind in ("true", "false", "atom") else f"({text})"


def formula(node: Node) -> str:
    """The formula in the grammar of stl-nl."""
    return _formula(node, Names())


def structure(node: Node) -> str:
    """
    The structure of the formula: its text with every number (bound or constant) written # and the names renamed a,
    b, ... in the order they appear. A name used twice keeps one letter, so (G (x < 3)) -> (G (x < 4)) and
    (G (x < 3)) -> (G (y < 4)) have different structures; the comparison operators are kept.
    """
    return _formula(node, Names(hidden=True))
