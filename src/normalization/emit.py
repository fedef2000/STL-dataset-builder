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


# ---------------------------------------------------------------- the text as stl-nl prints it

# The same formula written with the parentheses stlgen prints (rust/stlgen/src/formula.rs, Display), so that the
# formulas of every set of the final dataset are written alike: parentheses only where stl-nl's precedence needs them
# (unary G/F/X/!, then U/R, &&, ||, ->), plus those stlgen keeps for readability (comparisons inside any operator,
# G/F inside a binary operator, operands of U/R other than atoms, nested connectives). What stlgen doesn't have is
# written in the same style: X like G/F, <-> like ->, a power ^ binding tightest, open intervals and real or expression
# bounds as the faithful mode keeps them.
#
#     (F[0,15] (G[0,5] Reg_1_1)) || (F[0,15] (G[0,5] Reg_3_2))  ->  (F[0,15] G[0,5] Reg_1_1) || (F[0,15] G[0,5] Reg_3_2)

UNARY = ("not", "G", "F", "X")
STLNL_ARITHMETIC = {"add": ("+", 1), "sub": ("-", 1), "mul": ("*", 2), "div": ("/", 2)}


def stlnl_number(x: Fraction, exact_decimals: bool) -> str:
    """
    stlgen's way: an integer, a decimal with at most two places (0.5, -4.25), or n/d. With `exact_decimals` (the
    paired formulas, whose descriptions write the paper's numbers) every exact decimal stays a decimal (0.125).
    """
    if x.denominator == 1 or exact_decimals:
        return number(x)
    if 100 % x.denominator:
        return f"{x.numerator}/{x.denominator}"
    hundredths = x.numerator * (100 // x.denominator)
    whole, fraction = divmod(abs(hundredths), 100)
    sign = "-" if hundredths < 0 else ""
    return f"{sign}{whole}.{fraction // 10}" if fraction % 10 == 0 else f"{sign}{whole}.{fraction:02d}"


def _is_fraction_literal(node: Node, exact_decimals: bool) -> bool:
    return node.kind == "num" and "/" in stlnl_number(node.value, exact_decimals)


def _precedence(node: Node) -> int:
    if node.kind in STLNL_ARITHMETIC or node.kind == "neg":
        return STLNL_ARITHMETIC["sub" if node.kind == "neg" else node.kind][1]
    if node.kind == "pow":
        return 4
    return 3   # var, num, abs


def stlnl_expression(node: Node, exact_decimals: bool = True) -> str:
    kind = node.kind
    if kind == "num":
        return stlnl_number(node.value, exact_decimals)
    if kind == "var":
        return identifier(node.value)
    if kind == "abs":
        return f"|{stlnl_expression(node.args[0], exact_decimals)}|"
    if kind == "pow":
        base, exponent = node.args
        text = stlnl_expression(base, exact_decimals)
        if base.kind not in ("var", "num", "abs") or (base.kind == "num" and (base.value < 0 or "/" in text)):
            text = f"({text})"
        exponent_text = stlnl_number(exponent.value, exact_decimals)
        return f"{text}^{exponent_text if exponent.value >= 0 else f'({exponent_text})'}"
    if kind == "neg":   # stlgen reads -x as 0 - x
        left, right, symbol = Node("num", value=Fraction(0)), node.args[0], "-"
    else:
        (left, right), symbol = node.args, STLNL_ARITHMETIC[kind][0]
    level = _precedence(node)
    left_text, right_text = stlnl_expression(left, exact_decimals), stlnl_expression(right, exact_decimals)
    if _precedence(left) < level:
        left_text = f"({left_text})"
    if _precedence(right) <= level or (symbol == "/" and _is_fraction_literal(right, exact_decimals)):
        right_text = f"({right_text})"
    return f"{left_text} {symbol} {right_text}"


def _stlnl_bound(x, exact_decimals: bool) -> str:
    if isinstance(x, Node):
        return stlnl_expression(x, exact_decimals)
    if x == math.inf:
        return "inf"
    if isinstance(x, str):
        return identifier(x)
    return stlnl_number(Fraction(x), exact_decimals) if not isinstance(x, int) else str(x)


def _stlnl_interval(node: Node, exact_decimals: bool) -> str:
    i = node.interval
    return (f"{'(' if i.lo_open else '['}{_stlnl_bound(i.lower, exact_decimals)},"
            f"{_stlnl_bound(i.upper, exact_decimals)}{')' if i.hi_open else ']'}")


def _atomic(node: Node) -> bool:
    return node.kind in ("atom", "true", "false")


def _closed_negation(node: Node) -> bool:
    return node.kind == "not" and node.args[0].kind not in UNARY


def _operand(node: Node, bare: bool, exact_decimals: bool) -> str:
    text = _stlnl_formula(node, exact_decimals)
    return text if bare else f"({text})"


def _stlnl_formula(node: Node, exact_decimals: bool) -> str:
    kind = node.kind
    connective = lambda child: _atomic(child) or _closed_negation(child)
    unary = lambda child: _atomic(child) or child.kind in UNARY
    if kind in ("true", "false"):
        return kind
    if kind == "atom":
        return identifier(node.value)
    if kind == "rel":
        left, right = (stlnl_expression(a, exact_decimals) for a in node.args)
        return f"{left} {node.value} {right}"
    if kind in CONNECTIVES:
        return CONNECTIVES[kind].join(_operand(a, connective(a), exact_decimals) for a in node.args)
    if kind == "not":
        return "!" + _operand(node.args[0], unary(node.args[0]), exact_decimals)
    if kind in ("imp", "iff"):
        left, right = node.args
        return (f"{_operand(left, connective(left), exact_decimals)} {'->' if kind == 'imp' else '<->'} "
                f"{_operand(right, connective(right), exact_decimals)}")
    if kind in ("G", "F", "X"):
        prefix = "X" if kind == "X" else kind + _stlnl_interval(node, exact_decimals)
        return f"{prefix} {_operand(node.args[0], unary(node.args[0]), exact_decimals)}"
    if kind in ("U", "R"):
        left, right = node.args
        return (f"{_operand(left, _atomic(left), exact_decimals)} {kind}{_stlnl_interval(node, exact_decimals)} "
                f"{_operand(right, _atomic(right), exact_decimals)}")
    raise ValueError(kind)


def stlnl_text(node: Node, exact_decimals: bool = True) -> str:
    """The formula with the parentheses stlgen prints. `exact_decimals`: see stlnl_number."""
    return _stlnl_formula(node, exact_decimals)
