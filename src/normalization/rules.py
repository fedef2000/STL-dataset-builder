"""
The named rules of the normalization, what a record collects as they fire (Trace), and the rules that work on the
parsed tree: the time bounds (random values for symbols, open intervals closed, real bounds rounded outward) and the
checks of the symbols against the meanings the extraction gives them (constants, placeholder subformulas).
"""
import math
import re
from fractions import Fraction

# name: (status, what it does). Status "ok" is a rewrite that keeps the formula; "needs_review" and "rejected" are what
# the record becomes when the rule fires. See docs/normalization_rules.md.
RULES = {
    # Stage 0: the whole record
    "other_logic": ("rejected", "the formula holds a construct of another logic"),
    "semantics_definition": ("rejected", "a definition of the semantics (\\models, \\vDash)"),
    "grammar_definition": ("rejected", "a grammar of the logic (::=, \\mid, | between alternatives)"),
    "operator_definition": ("rejected", "a definition of an operator: the left side of = or := is not a single name"),
    "several_formulas": ("rejected", "several formulas, or a formula with text (where, and, if, ...)"),
    "connective_at_edge": ("rejected", "starts or ends with a connective: part of it is on another row"),
    # Stage 1: tokens and macros
    "expand_paper_macros": ("ok", "a macro of the paper replaced by its definition"),
    "fallback_operator_table": ("ok", "an operator name (\\always, \\F, \\LTLdiamond, ...) the paper doesn't define, or defines with commands that only draw it, read from a fixed table"),
    "macro_conflict": ("ok", "a macro the paper defines twice differently: the last definition is used"),
    "macro_loop": ("rejected", "a macro still left after 10 rounds of expansion"),
    "unknown_command": ("rejected", "a command neither defined by the paper nor known"),
    "strip_layout": ("ok", "spacing, sizing and alignment commands removed"),
    "unwrap_font": ("ok", "a font command replaced by its content"),
    # Stage 2: operators and constants
    "latex_ops": ("ok", "a LaTeX operator replaced by its STL token"),
    "bool_constants": ("ok", "\\top, \\bot, True, ... replaced by true/false"),
    "group_brackets": ("ok", "[ ] or \\{ \\} used as parentheses"),
    # Stage 2: intervals
    "subscript_interval": ("ok", "G_{[a,b]} written as G[a,b]"),
    "bound_shorthand": ("ok", "G_{<= c} written as G[0,c]"),
    "close_open_interval": ("ok", "an open or half-open interval closed"),
    "round_bounds_outward": ("ok", "real bounds rounded: the lower one down, the upper one up"),
    "random_symbolic_bounds": ("ok", "symbols in bounds replaced by random integers, everywhere in the formula"),
    "random_horizon": ("ok", "a temporal operator without an interval, or with an infinite upper bound, given a random horizon: [0,h] or [a,a+h]"),
    "unbounded_operator": ("rejected", "an infinite lower bound, or \\infty in a bound expression"),
    "bounds_unsatisfiable": ("rejected", "no random values of the symbols give valid intervals"),
    "negative_bound": ("rejected", "a negative time bound"),
    "empty_interval": ("rejected", "an interval whose lower bound is above the upper one"),
    "bound_too_large": ("rejected", "a time bound above 2147483647"),
    # Stage 2: signals and numbers
    "greek_names": ("ok", "a Greek letter written as its name"),
    "index_names": ("ok", "a subscript (or a superscript of letters) made part of the name"),
    "multiword_names": ("ok", "the spaces of a name written with underscores"),
    "accent_names": ("ok", "an accent, a line over or under, or a prime made part of the name"),
    "current_time_index": ("ok", "x(t), x[t], x_t written as x"),
    "reserved_names": ("ok", "a signal named G, F, X, U or R renamed"),
    "frac_numbers": ("ok", "\\frac{n}{d} of integers written as n/d"),
    "number_forms": ("ok", ".5, 5., 1e-3 written as plain decimals"),
    "negation_minus": ("ok", "-x written as (0 - x)"),
    "norm_as_abs": ("ok", "a norm \\|x\\| read as the absolute value |x|; its subscript (\\|x\\|_2) and a square after it dropped"),
    "overline_operator": ("ok", "an operator with a line over it (\\overline{\\Diamond}: a variant of the paper, averaged, marked, ...) read as the operator"),
    "function_as_name": ("ok", "a call whose arguments are names and integers written as one name: Reg(4,4) -> Reg_4_4"),
    # Stage 2: comparisons
    "relational_eq": ("ok", "a lone = in a comparison written as =="),
    "chained_comparison": ("ok", "a < x < b written as (a < x) && (x < b)"),
    "interval_membership": ("ok", "x \\in [a,b] written as two comparisons"),
    # Stage 2: what can't be represented
    "multiplication": ("rejected", "a product: 2x, \\cdot, \\times, *, two terms side by side"),
    "division": ("rejected", "a division other than of two integers"),
    "power": ("rejected", "a power or a superscript that isn't a name"),
    "function": ("rejected", "a name followed by (...) or [...] with an argument that isn't a name or an integer (rho(G_{[a,b]} phi,t), x(t+1)), or \\max, \\min, \\log, ..."),
    "indexed_operator": ("rejected", "\\bigwedge, \\bigvee, \\land_{i}, \\sum, \\ldots, ..."),
    "quantifier": ("rejected", "\\forall, \\exists"),
    "set_membership": ("rejected", "\\in a set that is not an interval"),
    "infinity": ("rejected", "\\infty outside of a time bound"),
    "nonstandard_operator": ("rejected", "an operator STL doesn't have, or a G/F/U/R with a script that isn't an interval"),
    # Stage 2: only recorded (needs_review until 2026-10-19)
    "placeholder_subformula": ("ok", "a Boolean atom the paper calls a (sub)formula: kept as an atom, as the subformula can't be rebuilt"),
    "symbolic_constant": ("ok", "a symbol the paper calls a threshold, constant, parameter, ...: kept as a signal"),
    "indexed_signal": ("ok", "x[0], x[1] written x_0, x_1 (a component, though it may be the signal at time 0)"),
    # Stage 3: parser
    "strip_label": ("ok", "the name in front of the formula (\\psi = ..., \\phi := ..., u_4: ...) removed"),
    "strip_trailing_punct": ("ok", "a final , . ; removed"),
    "ambiguous_scope": ("ok", "an unparenthesized temporal operand followed by a connective: read as the operator on the operand alone (the standard reading)"),
    "close_parentheses": ("ok", "brackets still open at the end closed (a missing ), or a formula cut by the extraction: its first part)"),
    "operator_alone": ("rejected", "a temporal operator with no operand (F_{[a,b]}, U_{[a,b]} alone, or at the end)"),
    "parse_error": ("rejected", "a construct the parser doesn't recognise"),
    # Stage 5: validation
    "stlgen_error": ("rejected", "the stlgen parser of stl-nl rejects the result"),
}

MAX_BOUND = 2**31 - 1
RANDOM_BOUND_RANGE = (0, 100)
RANDOM_BOUND_TRIES = 100


class Rejected(Exception):
    """The formula can't be represented: `rule` is the reason, `detail` the construct (e.g. the unknown command)."""

    def __init__(self, rule: str, detail: str = ""):
        assert RULES[rule][0] == "rejected", rule
        super().__init__(f"{rule}: {detail}" if detail else rule)
        self.rule, self.detail = rule, detail


class Trace:
    """What happens to one formula: the rules that fire (in order, once each), the review reasons, the substitutions."""

    def __init__(self):
        self.rules: list[str] = []
        self.reviews: list[str] = []
        self.substitutions: dict[str, int] = {}
        self.rounded: list[list[list[str]]] = []

    def fire(self, rule: str):
        assert rule in RULES, rule
        if rule not in self.rules:
            self.rules.append(rule)

    def review(self, rule: str, detail: str = ""):
        assert RULES[rule][0] == "needs_review", rule
        self.fire(rule)
        reason = f"{rule}: {detail}" if detail else rule
        if reason not in self.reviews:
            self.reviews.append(reason)


# ---------------------------------------------------------------- the time bounds

def _walk(node):
    yield node
    for child in node.args:
        yield from _walk(child)
    if node.interval is not None:
        yield from _walk(node.interval.lo)
        if node.interval.hi is not None:
            yield from _walk(node.interval.hi)


def _value(node, values: dict) -> Fraction:
    """The number an arithmetic expression of a bound gives, with `values` for its symbols."""
    if node.kind == "num":
        return node.value
    if node.kind == "var":
        return Fraction(values[node.value])
    if node.kind == "neg":
        return -_value(node.args[0], values)
    if node.kind == "abs":
        return abs(_value(node.args[0], values))
    left, right = (_value(a, values) for a in node.args)
    return left + right if node.kind == "add" else left - right


def _resolved(interval, values: dict) -> tuple[int, int, str | None]:
    """(lower, upper, the rule a failure breaks or None) of an interval: closed, rounded outward."""
    lo, hi = _value(interval.lo, values), _value(interval.hi, values)
    lo_int, hi_int = math.floor(lo), math.ceil(hi)
    if lo_int < 0:
        return lo_int, hi_int, "negative_bound"
    if lo_int > hi_int:
        return lo_int, hi_int, "empty_interval"
    if hi_int > MAX_BOUND:
        return lo_int, hi_int, "bound_too_large"
    return lo_int, hi_int, None


def _number_text(x: Fraction) -> str:
    return str(x.numerator) if x.denominator == 1 else str(float(x)) if 10**12 % x.denominator == 0 else str(x)


def resolve_bounds(root, trace: Trace, rng):
    """
    Makes every interval of the tree a closed integer interval: the symbols of the bounds get random integers (the same
    symbol the same value, also where it is compared), open intervals are closed, real bounds rounded outward. The
    nodes are changed in place; each interval gets `lower` and `upper`.
    """
    intervals = [n.interval for n in _walk(root) if n.interval is not None]
    symbols = sorted({n.value for i in intervals for n in _walk(i.lo) if n.kind == "var"}
                     | {n.value for i in intervals for n in _walk(i.hi) if n.kind == "var"})
    values = {}
    if symbols:
        trace.fire("random_symbolic_bounds")
        for _ in range(RANDOM_BOUND_TRIES):
            values = {s: rng.randint(*RANDOM_BOUND_RANGE) for s in symbols}
            # A horizon of 0 would give G[0,0]: drawn again, so a horizon is 1-100 (and other records draw as before)
            if all(_resolved(i, values)[2] is None for i in intervals) and \
                    all(v > 0 for s, v in values.items() if s.startswith("horizon#")):
                break
        else:
            raise Rejected("bounds_unsatisfiable", ", ".join(symbols))
        trace.substitutions = values
        # The symbols also become numbers where they are compared (G[0,T] (x < T) -> G[0,37] (x < 37))
        for node in _walk(root):
            if node.kind == "var" and node.value in values:
                node.kind, node.value = "num", Fraction(values[node.value])
    for interval in intervals:
        lo_int, hi_int, broken = _resolved(interval, values)
        if broken:
            raise Rejected(broken, f"[{lo_int},{hi_int}]")
        if interval.lo_open or interval.hi_open:
            trace.fire("close_open_interval")
        exact = (_value(interval.lo, values), _value(interval.hi, values))
        if exact != (lo_int, hi_int):
            trace.fire("round_bounds_outward")
            trace.rounded.append([[_number_text(x) for x in exact], [str(lo_int), str(hi_int)]])
        interval.lower, interval.upper = lo_int, hi_int


# ---------------------------------------------------------------- the symbols and their meanings

CONSTANT_PATTERN = re.compile(r"\b(threshold|constant|parameter|bound|limit|maximum|minimum|max|min)s?\b", re.I)
PLACEHOLDER_PATTERN = re.compile(r"\b(sub-?formula|formula|specification)s?\b", re.I)


def check_symbols(root, meanings: dict[str, str], trace: Trace):
    """
    Records the real-valued signals the paper calls a threshold, constant, ... (symbolic_constant: they are read as
    signals) and the Boolean atoms it calls a (sub)formula (placeholder_subformula: the subformula can't be rebuilt,
    so the atom stands for it). `meanings` maps the normalized names to the meanings.
    """
    constants = sorted({n.value for n in _walk(root) if n.kind == "var"
                        and CONSTANT_PATTERN.search(meanings.get(n.value, ""))})
    if constants:
        trace.fire("symbolic_constant")
    placeholders = sorted({n.value for n in _walk(root) if n.kind == "atom"
                           and PLACEHOLDER_PATTERN.search(meanings.get(n.value, ""))})
    if placeholders:
        trace.fire("placeholder_subformula")
