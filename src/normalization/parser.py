"""
The parser of the normalization: the STL tokens of a formula (lexer.py) parsed into a tree, by recursive descent with
the precedence levels of stl-nl (tightest first): unary (G, F, X, !), U/R, &&, ||, -> and <->. Before parsing, the
label in front of the formula and a final punctuation mark are taken out; a formula that is a definition, or several
formulas, is rejected. An unparenthesized temporal operand followed by a connective is read as the operator on the
operand alone, as stl-nl reads it (the standard reading), and recorded as ambiguous_scope.
"""
from dataclasses import dataclass, field
from fractions import Fraction

from src.normalization.lexer import Interval, Tok
from src.normalization.rules import Rejected, Trace


@dataclass
class Bounds:
    """A parsed interval: its bounds as arithmetic trees; `lower` and `upper` are set once resolved (rules.py)."""
    lo: "Node"
    hi: "Node"
    lo_open: bool
    hi_open: bool
    lower: int | None = None
    upper: int | None = None


@dataclass
class Node:
    """
    A node of the tree. Formulas: true, false, atom (value: name), rel (value: operator; args: two expressions), not,
    and, or, imp, iff, G, F, X, U, R (interval: Bounds). Expressions: num (value: Fraction), var (value: name), add,
    sub, neg, abs.
    """
    kind: str
    args: list = field(default_factory=list)
    value: object = None
    interval: Bounds | None = None


class ParseFail(Exception):
    """This reading of the tokens fails (the parser may try another one)."""


# What can start the operand of a bare G, F or X (a minus can't: in "X - 3 > 0", X is a signal)
TERM_START = {"ID", "NUM", "LP", "NOT", "OP", "BOOL", "ABS"}
CONNECTIVE_KINDS = {"AND", "OR", "IMP", "IFF", "BOP"}
FORMULA_KINDS = {"OP", "BOP", "NOT", "AND", "OR", "IMP", "IFF", "REL", "BOOL"}


def _depths(tokens: list[Tok]) -> list[int]:
    """The parenthesis depth of each token."""
    depths, depth = [], 0
    for t in tokens:
        if t.kind == "RP":
            depth -= 1
        depths.append(depth)
        if t.kind == "LP":
            depth += 1
    return depths


def strip_trailing_punct(tokens: list[Tok], trace: Trace) -> list[Tok]:
    while tokens and tokens[-1].kind in ("COMMA", "PUNCT"):
        trace.fire("strip_trailing_punct")
        tokens = tokens[:-1]
    return tokens


# The usual names of formulas: "\\phi_1 = ..." names a formula, "x = ..." compares a signal
FORMULA_NAME_BASES = {"phi", "varphi", "psi", "Phi", "Psi", "varPhi", "varPsi"}


def is_label(tokens: list[Tok], formula_names: set[str]) -> bool:
    """
    Whether tokens[0] is the name of the formula that follows. With := or : always; with = only when the name is a
    formula name (\\phi, \\psi, ..., or one the paper's variables call a formula) or an operator follows the = (in
    "gear = 4 \\wedge ..." the = is a comparison).
    """
    if len(tokens) < 3 or tokens[0].kind != "ID":
        return False
    sep, first = tokens[1], tokens[2]
    if sep.kind in ("DEF", "COLON"):
        return True
    if sep.kind != "REL" or sep.value != "=":
        return False
    name = tokens[0].value
    return (name.split("_")[0] in FORMULA_NAME_BASES or name in formula_names
            or first.kind in ("OP", "NOT", "BOOL"))


def strip_label(tokens: list[Tok], trace: Trace, formula_names: set[str] = frozenset()) -> list[Tok]:
    """\\psi = ..., \\phi := ..., u_4: ... -> the formula after the name (see is_label)."""
    while True:
        if is_label(tokens, formula_names):
            trace.fire("strip_label")
            tokens = tokens[2:]
        else:
            return tokens


def check_shape(tokens: list[Tok]):
    """Rejects several formulas (a comma at the top level) and the definitions of an operator."""
    depths = _depths(tokens)
    for k, t in enumerate(tokens):
        if depths[k] != 0:
            continue
        if t.kind == "COMMA":
            raise Rejected("several_formulas", "a comma at the top level")
        if t.kind == "DEF" or t.kind == "COLON":
            raise Rejected("operator_definition", "the left side is not a single name")
        if t.kind == "REL" and t.value == "=":
            left, right = tokens[:k], tokens[k + 1:]
            if any(x.kind in ("OP", "BOP") for x in left) and any(x.kind in FORMULA_KINDS for x in right):
                raise Rejected("operator_definition", "an operator on the left of =")


class Parser:
    def __init__(self, tokens: list[Tok], trace: Trace):
        self.tokens, self.trace = tokens, trace
        self.pos = 0
        self.furthest = 0
        self.paren_end = -1  # where the last parenthesized formula ended

    # ------------------------------------------------------------ helpers

    def peek(self, offset: int = 0) -> Tok | None:
        k = self.pos + offset
        return self.tokens[k] if k < len(self.tokens) else None

    def peek_kind(self, offset: int = 0) -> str | None:
        t = self.peek(offset)
        return t.kind if t else None

    def take(self) -> Tok:
        t = self.peek()
        if t is None:
            self.fail()
        self.pos += 1
        return t

    def expect(self, kind: str) -> Tok:
        if self.peek_kind() != kind:
            self.fail()
        return self.take()

    def fail(self):
        self.furthest = max(self.furthest, self.pos)
        raise ParseFail()

    # ------------------------------------------------------------ formulas

    def formula(self) -> Node:
        left = self.disjunction()
        if self.peek_kind() in ("IMP", "IFF"):
            kind = "imp" if self.take().kind == "IMP" else "iff"
            return Node(kind, [left, self.formula()])
        return left

    def disjunction(self) -> Node:
        items = [self.conjunction()]
        while self.peek_kind() == "OR":
            self.take()
            items.append(self.conjunction())
        return items[0] if len(items) == 1 else Node("or", items)

    def conjunction(self) -> Node:
        items = [self.until()]
        while self.peek_kind() == "AND":
            self.take()
            items.append(self.until())
        return items[0] if len(items) == 1 else Node("and", items)

    def until(self) -> Node:
        left = self.unary()
        while True:
            t = self.peek()
            if t is not None and t.kind == "ID" and t.candidate and t.value in ("U", "R"):
                raise Rejected("unbounded_operator", t.value)
            if t is None or t.kind != "BOP":
                return left
            self.take()
            if t.interval is None:
                raise Rejected("unbounded_operator", t.value)
            right = self.unary()
            left = Node(t.value, [left, right], interval=self.bounds(t.interval))

    def unary(self) -> Node:
        t = self.peek()
        if t is None:
            self.fail()
        if t.kind == "OP" or (t.kind == "ID" and t.candidate and t.value in ("G", "F", "X")
                              and self.peek_kind(1) in TERM_START):
            self.take()
            if t.kind == "ID":
                if t.value != "X":
                    raise Rejected("unbounded_operator", t.value)
                self.trace.fire("latex_ops")
            elif t.interval is None and t.value != "X":
                raise Rejected("unbounded_operator", t.value)
            start = self.pos
            operand = self.unary()
            wrapped = self.tokens[start].kind == "LP" and self.paren_end == self.pos
            if not wrapped and self.peek_kind() in CONNECTIVE_KINDS:
                self.trace.fire("ambiguous_scope")
            interval = self.bounds(t.interval) if t.interval is not None else None
            return Node(t.value, [operand], interval=interval)
        if t.kind == "NOT":
            self.take()
            return Node("not", [self.unary()])
        return self.primary()

    def primary(self) -> Node:
        t = self.peek()
        if t is None:
            self.fail()
        start = self.pos
        try:
            return self.relation()
        except ParseFail:
            self.pos = start
        if t.kind == "LP":
            self.take()
            node = self.formula()
            self.expect("RP")
            if t.value in ("[", "{"):
                self.trace.fire("group_brackets")
            self.paren_end = self.pos
            return node
        if t.kind == "BOOL":
            self.take()
            return Node("true" if t.value else "false")
        if t.kind == "ID":
            self.take()
            return Node("atom", value=self.name(t))
        self.fail()

    def name(self, t: Tok) -> str:
        if t.value in ("G", "F", "X", "U", "R"):
            self.trace.fire("reserved_names")
            return f"{t.value}_sig"
        return t.value

    # ------------------------------------------------------------ comparisons and arithmetic

    def relation(self) -> Node:
        first = self.arith()
        if self.peek_kind() == "IN":
            self.take()
            return self.membership(first)
        expressions, operators = [first], []
        while self.peek_kind() == "REL":
            op = self.take().value
            if op == "=":
                self.trace.fire("relational_eq")
                op = "=="
            operators.append(op)
            expressions.append(self.arith())
        if not operators:
            self.fail()
        relations = [Node("rel", [expressions[k], expressions[k + 1]], value=op) for k, op in enumerate(operators)]
        if len(relations) > 1:
            self.trace.fire("chained_comparison")
            return Node("and", relations)
        return relations[0]

    def membership(self, x: Node) -> Node:
        opening = self.peek()
        if opening is None or opening.kind != "LP" or opening.value not in ("[", "("):
            raise Rejected("set_membership", "\\in a set")
        self.take()
        lo = self.arith()
        self.expect("COMMA")
        hi = self.arith()
        closing = self.expect("RP")
        self.trace.fire("interval_membership")
        return Node("and", [Node("rel", [lo, x], value="<" if opening.value == "(" else "<="),
                            Node("rel", [x, hi], value="<" if closing.value == ")" else "<=")])

    def arith(self) -> Node:
        node = self.arith_term()
        while self.peek_kind() in ("PLUS", "MINUS"):
            kind = "add" if self.take().kind == "PLUS" else "sub"
            node = Node(kind, [node, self.arith_term()])
        return node

    def arith_term(self) -> Node:
        t = self.peek()
        if t is None:
            self.fail()
        if t.kind == "MINUS":
            self.take()
            operand = self.arith_term()
            if operand.kind == "num":
                return Node("num", value=-operand.value)
            self.trace.fire("negation_minus")
            return Node("neg", [operand])
        if t.kind == "PLUS":
            self.take()
            return self.arith_term()
        if t.kind == "NUM":
            self.take()
            value = t.value
            if self.peek_kind() == "SLASH":
                self.take()
                d = self.peek()
                if d is None or d.kind != "NUM" or d.value.denominator != 1 or value.denominator != 1 or d.value == 0:
                    raise Rejected("division", "/")
                self.take()
                value = value / d.value
            node = Node("num", value=value)
        elif t.kind == "ID":
            self.take()
            node = Node("var", value=self.name(t))
        elif t.kind == "LP":
            self.take()
            node = self.arith()
            self.expect("RP")
        elif t.kind == "ABS":
            self.take()
            node = Node("abs", [self.arith()])
            self.expect("ABS")
        elif t.kind == "INF":
            raise Rejected("infinity", "\\infty")
        else:
            self.fail()
        if self.peek_kind() == "SLASH":
            raise Rejected("division", "/")
        return node

    # ------------------------------------------------------------ intervals

    def bounds(self, interval: Interval) -> Bounds:
        if any(t.kind == "INF" for t in interval.lo + interval.hi):
            raise Rejected("unbounded_operator", "\\infty")
        return Bounds(self.bound(interval.lo), self.bound(interval.hi), interval.lo_open, interval.hi_open)

    def bound(self, tokens: list[Tok]) -> Node:
        sub = Parser(tokens, self.trace)
        try:
            node = sub.arith()
            if sub.pos != len(tokens):
                sub.fail()
        except ParseFail:
            raise Rejected("parse_error", f"time bound {' '.join(t.text() for t in tokens)}")
        return node


def parse(tokens: list[Tok], trace: Trace, formula_names: set[str] = frozenset()) -> Node:
    tokens = strip_trailing_punct(tokens, trace)
    tokens = strip_label(tokens, trace, formula_names)
    if not tokens:
        raise Rejected("parse_error", "empty formula")
    check_shape(tokens)
    parser = Parser(tokens, trace)
    try:
        root = parser.formula()
        if parser.pos != len(tokens):
            parser.fail()
        return root
    except ParseFail:
        k = parser.furthest
        before = tokens[k - 1] if 0 < k <= len(tokens) else None
        at = tokens[k] if k < len(tokens) else None
        # Two terms side by side (k x, p q): a product, or a missing operator
        if before is not None and at is not None and before.kind in ("ID", "NUM", "RP", "ABS") \
                and at.kind in ("ID", "NUM", "LP", "BOOL"):
            raise Rejected("multiplication", f"{before.text()} {at.text()} side by side")
        if at is None:
            raise Rejected("parse_error", "the formula ends before it is complete")
        context = " ".join(t.text() for t in tokens[max(0, k - 3):k + 3])
        raise Rejected("parse_error", f"unexpected {at.text()} in: {context}")
