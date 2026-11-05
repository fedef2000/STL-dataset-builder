"""
The tree of a normalized formula written in the grammar of stl-nl, with explicit parentheses around every temporal
operand and every binary subformula, so that stl-nl's precedence can't change its reading. The faithful mode adds what
stl-nl's grammar doesn't have: open intervals (F(2,12]), bounds that are real numbers or expressions (F[0,2.5],
G[T,T + delta]) and powers with an integer exponent (x^2, without parentheses around it: a power binds tightest). The same writer gives the
pattern of the formula: the same text with every number and parameter written # and the names renamed a, b, ... in the
order they appear, so that formulas that differ only in their numbers and names have the same pattern.
"""
import math
import re
from fractions import Fraction

from src.normalization.parser import Node
from src.normalization.rules import Rejected

IDENTIFIER_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,255}")
CONNECTIVES = {"and": " && ", "or": " || "}
ARITHMETIC = {"add": " + ", "sub": " - ", "mul": " * ", "div": " / "}


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
    """How the writer writes names and numbers: as they are (the formula), or hidden (its pattern)."""

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

    def bound(self, x) -> str:
        """
        A time bound: a number, a parameter or an expression (all # in the pattern), or inf (kept in the pattern).
        """
        if isinstance(x, Node):
            return "#" if self.hidden else expression(x, self)
        if x == math.inf:
            return "inf"
        if isinstance(x, str):
            return "#" if self.hidden else identifier(x)
        return self.number(x)


def expression(node: Node, names: Names) -> str:
    if node.kind == "num":
        return names.number(node.value)
    if node.kind == "var":
        return names.name(node.value)
    if node.kind == "abs":
        return f"|{expression(node.args[0], names)}|"
    if node.kind == "neg":
        return f"({names.number(0)} - {_wrapped_expression(node.args[0], names)})"
    if node.kind == "pow":
        base, exponent = node.args
        base_text = expression(base, names)
        if base.kind not in ("var", "num", "abs") or (base.kind == "num" and base.value < 0) or "/" in base_text:
            base_text = f"({base_text})"
        exponent_text = names.number(exponent.value)
        return f"{base_text}^{exponent_text if exponent.value >= 0 else f'({exponent_text})'}"
    left, right = node.args
    left_text, right_text = _wrapped_expression(left, names), _wrapped_expression(right, names)
    # stl-nl reads x / 1/3 as (x / 1) / 3: a fraction after / is grouped
    if node.kind == "div" and right.kind == "num" and "/" in right_text:
        right_text = f"({right_text})"
    return f"{left_text}{ARITHMETIC[node.kind]}{right_text}"


def _wrapped_expression(node: Node, names: Names) -> str:
    text = expression(node, names)
    return f"({text})" if node.kind in ARITHMETIC else text


def interval(node: Node, names: Names) -> str:
    """The interval, with ( or ) where it is open (only in the faithful mode: the stl-nl mode closes every interval)."""
    i = node.interval
    return f"{'(' if i.lo_open else '['}{names.bound(i.lower)},{names.bound(i.upper)}{')' if i.hi_open else ']'}"


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


def pattern(node: Node) -> str:
    """
    The pattern of the formula: its text with every number (bound or constant) and parameter written # (inf is kept)
    and the names renamed a, b, ... in the order they appear. A name used twice keeps one letter, so
    (G (x < 3)) -> (G (x < 4)) and (G (x < 3)) -> (G (y < 4)) have different patterns; the comparison operators are kept.
    """
    return _formula(node, Names(hidden=True))
