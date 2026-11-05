"""
The skeleton of a formula, as stl-nl's scripts/formula_patterns.py computes it (copied from stl-nl at efe09be, only
the skeleton): its temporal and Boolean structure, with each distinct relation or Boolean signal written as a Greek
letter, a letter repeating only when the exact same condition repeats. Time bounds are [#,#], or [#,inf] when
unbounded. Operands of + * && || == != are unordered. It is computed from the AST that `stlgen import` gives
(validate.check), so a formula gets the same skeleton here and in stl-nl; the formulas stlgen can't parse (faithful
mode) give that AST with stlgen_ast.py. One addition to stl-nl's code: the power of the faithful mode (^, tightest).

    G[0,30] ((gear == 4) -> (F[0,5] (rpm < 3000)))  ->  G[#,#] (φ -> F[#,#] ψ)
"""
from itertools import permutations, product
from math import factorial
import re

GREEK = "φψχθωαβγδηκλμνρξζ"
UNARY_TEMPORAL = {"globally": "G", "eventually": "F"}
BINARY_TEMPORAL = {"until": "U", "release": "R"}
CONNECTIVES = {"and": " && ", "or": " || "}
ARITHMETIC = {"add": ("+", 1), "subtract": ("-", 1), "multiply": ("*", 2), "divide": ("/", 2), "power": ("^", 3)}
# Positions in the output reached by an operand, deciding which parentheses it needs.
ROOT, UNDER_UNARY_TEMPORAL, UNDER_OPERATOR, UNDER_BINARY_TEMPORAL = range(4)
# Identical-looking variables are tried in every order; past this limit one order is used.
MAX_RENAMINGS = 5040
PLACEHOLDER_BASE = 0xF0000
PLACEHOLDER = re.compile("[\U000F0000-\U000FFFFD]")


def unwrap(node):
    while node["type"] in CONNECTIVES and len(node["children"]) == 1:
        node = node["children"][0]
    return node


def flatten(node, kind):
    node = unwrap(node)
    if node["type"] != kind:
        return [node]
    children = node["children"] if kind in CONNECTIVES else (node["left"], node["right"])
    return [leaf for child in children for leaf in flatten(child, kind)]


def arithmetic(node, name, constant, parent_precedence=0, right_operand=False):
    kind = node["type"]
    if kind == "variable":
        return name(node["name"])
    if kind == "rational":
        return constant(node)
    if kind == "abs":
        return f"abs({arithmetic(node['child'], name, constant)})"
    if kind not in ARITHMETIC:
        raise ValueError(f"unknown arithmetic node {kind!r}")
    symbol, precedence = ARITHMETIC[kind]
    if kind in ("add", "multiply"):
        parts = sorted(arithmetic(part, name, constant, precedence) for part in flatten(node, kind))
    else:
        parts = [arithmetic(node["left"], name, constant, precedence),
                 arithmetic(node["right"], name, constant, precedence, right_operand=True)]
    text = f" {symbol} ".join(parts)
    if precedence < parent_precedence or (precedence == parent_precedence and right_operand):
        return f"({text})"
    return text


def relation(node, name, constant):
    sides = [arithmetic(node["left"], name, constant), arithmetic(node["right"], name, constant)]
    if node["comparison"] in ("==", "!="):
        sides.sort()
    return f"{sides[0]} {node['comparison']} {sides[1]}"


def interval(node):
    upper = node["upper"]
    return "[#,inf]" if isinstance(upper, dict) and upper["type"] == "infinity" else "[#,#]"


def logic(node, leaf, position=ROOT):
    node = unwrap(node)
    kind = node["type"]
    if kind in ("true", "false"):
        return kind
    if kind in ("relation", "atom"):
        text = leaf(node)
        return f"({text})" if position != ROOT and " " in text else text
    if kind == "not":
        text = f"!{logic(node['child'], leaf, UNDER_OPERATOR)}"
        return f"({text})" if position == UNDER_BINARY_TEMPORAL else text
    if kind in UNARY_TEMPORAL:
        text = f"{UNARY_TEMPORAL[kind]}{interval(node['interval'])} {logic(node['child'], leaf, UNDER_UNARY_TEMPORAL)}"
        return f"({text})" if position >= UNDER_OPERATOR else text
    if kind in CONNECTIVES:
        text = CONNECTIVES[kind].join(sorted(logic(part, leaf, UNDER_OPERATOR) for part in flatten(node, kind)))
    elif kind == "implies":
        # G/F on the right of -> reads unambiguously, as in `φ -> F[#,#] ψ`.
        text = f"{logic(node['left'], leaf, UNDER_OPERATOR)} -> {logic(node['right'], leaf, UNDER_UNARY_TEMPORAL)}"
    elif kind in BINARY_TEMPORAL:
        left = logic(node["left"], leaf, UNDER_BINARY_TEMPORAL)
        right = logic(node["right"], leaf, UNDER_BINARY_TEMPORAL)
        text = f"{left} {BINARY_TEMPORAL[kind]}{interval(node['interval'])} {right}"
    else:
        raise ValueError(f"unknown formula node {kind!r}")
    return text if position == ROOT else f"({text})"


def label(index, alphabet):
    suffix = index // len(alphabet)
    return alphabet[index % len(alphabet)] + (str(suffix) if suffix else "")


def canonical(render, alphabet):
    """Return (text, exact): the same text for every renaming of the identifiers render asks about.

    exact is False if a formula had too many interchangeable identifiers to try every order.
    """
    identifiers = set()
    render(lambda identifier: identifiers.add(identifier) or "x")
    signatures = {i: render(lambda other, marked=i: "@" if other == marked else "x") for i in identifiers}
    groups = {}
    for identifier in sorted(identifiers):
        groups.setdefault(signatures[identifier], []).append(identifier)
    groups = [groups[signature] for signature in sorted(groups)]
    renamings = 1
    for group in groups:
        renamings *= factorial(len(group))
    exact = renamings <= MAX_RENAMINGS
    orders = product(*map(permutations, groups)) if exact else [groups]
    best = None
    for order in orders:
        flat = [identifier for group in order for identifier in group]
        placeholders = {identifier: chr(PLACEHOLDER_BASE + i) for i, identifier in enumerate(flat)}
        candidate = render(placeholders.__getitem__)
        if best is None or candidate < best:
            best = candidate
    # Letters follow reading order; this depends only on the winning text, so it stays canonical.
    assigned = {}
    return PLACEHOLDER.sub(lambda m: assigned.setdefault(m[0], label(len(assigned), alphabet)), best), exact


def skeleton(ast):
    """(the skeleton of the formula whose stlgen AST is `ast`, whether every renaming could be compared)."""
    def identity(node):
        if node["type"] == "atom":
            return node["name"]
        return relation(node, str, lambda n: f"{n['numerator']}/{n['denominator']}")

    def render(name):
        return logic(ast, lambda node: name(identity(node)))
    return canonical(render, GREEK)
