"""
The named rules of the normalization, what a record collects as they fire (Trace), and the rules that work on the
parsed tree: the time bounds (random values for symbols, open intervals closed, real bounds rounded outward) and the
checks of the symbols against the meanings the extraction gives them (constants, placeholder subformulas).

The normalization has two modes (Trace.mode). "stl-nl", for the formulas without a requirement, writes them in the
grammar of stl-nl, which then describes them: a change of meaning is acceptable, as the description is written from the
result. "faithful", for the formulas the paper describes, must keep the meaning the description has: the bounds stay
as written (real numbers, open intervals, expressions: FAITHFUL_RULES), powers with an integer exponent stay, and the
rules that change the meaning reject the formula instead (FAITHFUL_REJECTED).
"""
import math
import re
from fractions import Fraction

# name: (status, what it does). Status "ok" is a rewrite that keeps the formula; "needs_review" and "rejected" are what
# the record becomes when the rule fires. See docs/normalization_rules.md.
RULES = {
    # Stage 0: the whole record
    "other_logic": ("rejected", "the paper writes it in another logic (past-time, spatial, probabilistic, strategic): its operators have no STL equivalent"),
    "semantics_definition": ("rejected", "a definition of the semantics (\\models, \\vDash): it says when a signal satisfies a formula, it is not a formula itself"),
    "grammar_definition": ("rejected", "a grammar of the logic (::=, \\mid, | between alternatives): it lists the forms a formula can take, it is not a formula itself"),
    "operator_definition": ("rejected", "a definition of an operator in terms of others (F_{[a,b]} phi := true U_{[a,b]} phi): the left side of = or := is not a single name"),
    "several_formulas": ("rejected", "several formulas, or a formula with text (where, and, if, ...): stl-nl takes exactly one formula"),
    "connective_at_edge": ("rejected", "starts or ends with a connective (\\land, \\lor, ...): the extraction found that the rest of the formula is on another row"),
    # Stage 1: tokens and macros
    "expand_paper_macros": ("ok", "a macro of the paper replaced by its definition"),
    "fallback_operator_table": ("ok", "an operator name (\\always, \\F, \\LTLdiamond, ...) the paper doesn't define, or defines with commands that only draw it, read from a fixed table"),
    "macro_conflict": ("ok", "a macro the paper defines twice differently: the last definition is used"),
    "macro_loop": ("rejected", "a macro of the paper still left after 10 rounds of expansion: it never turns into a formula"),
    "unknown_command": ("rejected", "a LaTeX command the paper doesn't define and the normalizer has no translation for (it is not an STL operator, connective, comparison, font or spacing command): its meaning is unknown, so the whole formula is rejected even if the rest is valid STL"),
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
    "parameter_bounds": ("ok", "a symbol alone in a bound kept as a parameter of stl-nl: G[0,T]"),
    "random_symbolic_bounds": ("ok", "the symbols of a bound expression ([t,t+5]) or also used as a signal (x < T) replaced by random integers, everywhere in the formula"),
    "unbounded_interval": ("ok", "a temporal operator without an interval read as [0,inf]; an infinite upper bound written inf"),
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
    "products_and_divisions": ("ok", "a product or a division written with * and /: a \\cdot x, 2x, \\frac{a}{b}"),
    "multiplication": ("rejected", "two terms side by side: a product with a space (k x), a unit (200 N) or a missing operator"),
    "division": ("rejected", "a division by 0"),
    "power": ("rejected", "a power or a superscript that isn't a name (x^2, \\rho^{\\varphi}): stl-nl has no powers"),
    "function": ("rejected", "a function applied to something (rho(G_{[a,b]} phi,t), x(t+1), \\max, \\min, \\log, ...): stl-nl has no functions (a call on names and integers only, Reg(4,4), is kept as one name)"),
    "indexed_operator": ("rejected", "an operator over an index (\\bigwedge, \\bigvee, \\land_{i}, \\sum, \\ldots, ...): the number of terms isn't known, so it can't be written out"),
    "quantifier": ("rejected", "a quantifier (\\forall, \\exists): STL has none"),
    "set_membership": ("rejected", "\\in a set that is not an interval: STL can only compare a signal with numbers"),
    "infinity": ("rejected", "\\infty outside of a time bound: not a number stl-nl can write"),
    "nonstandard_operator": ("rejected", "an operator STL doesn't have (\\boxplus, \\sqcup, ...), or a G/F/U/R with a script that isn't an interval"),
    # Stage 2: only recorded (needs_review until 2026-10-19)
    "placeholder_subformula": ("ok", "a Boolean atom the paper calls a (sub)formula: kept as an atom, as the subformula can't be rebuilt"),
    "symbolic_constant": ("ok", "a symbol the paper calls a threshold, constant, parameter, ...: kept as a signal"),
    "indexed_signal": ("ok", "x[0], x[1] written x_0, x_1 (a component, though it may be the signal at time 0)"),
    # Stage 3: parser
    "strip_label": ("ok", "the name in front of the formula (\\psi = ..., \\phi := ..., u_4: ...) removed"),
    "strip_trailing_punct": ("ok", "a final , . ; removed"),
    "ambiguous_scope": ("ok", "an unparenthesized temporal operand followed by a connective: read as the operator on the operand alone (the standard reading)"),
    "close_parentheses": ("ok", "brackets still open at the end closed (a missing ), or a formula cut by the extraction: its first part)"),
    "operator_alone": ("rejected", "a temporal operator with no operand (F_{[a,b]}, U_{[a,b]} alone, or at the end): an operator, not a formula"),
    "parse_error": ("rejected", "a construct the parser can't read (a subscript where none can go, an unexpected symbol, unbalanced brackets): it is never guessed"),
    # Stage 5: validation
    "stlgen_error": ("rejected", "the stlgen parser of stl-nl rejects the result"),
    # Faithful mode only (FAITHFUL_RULES): what the stl-nl mode changes, kept as the paper writes it
    "real_bounds": ("ok", "a time bound that isn't an integer kept as written: F[0,2.5] (faithful mode)"),
    "open_intervals": ("ok", "an open or half-open interval kept open: F(2,12] (faithful mode)"),
    "bound_expressions": ("ok", "a time bound written as an expression of symbols kept: G[T,T + delta] (faithful mode)"),
    "powers": ("ok", "a power with an integer exponent kept: x^2, (x - 1)^2, |x|^2 (faithful mode)"),
}

MODES = ("stl-nl", "faithful")
FAITHFUL_RULES = {"real_bounds", "open_intervals", "bound_expressions", "powers"}
# Rules that keep the formula in the stl-nl mode but change its meaning: in the faithful mode they reject it
FAITHFUL_REJECTED = {
    "overline_operator": "an operator with a line over it is a variant of the paper (averaged, marked, ...) with its own semantics, which the plain operator would lose",
    "close_parentheses": "brackets left open at the end: the formula may have been cut, and the description may be about the part that is missing",
}


# What a rule that still rejects does in the faithful mode, where it differs from RULES
FAITHFUL_DESCRIPTIONS = {
    "power": "a superscript that is neither an integer exponent nor part of a name (\\rho^{\\varphi}, [1,1]^T, x^{(j)}, 30^\\circ), or an integer superscript on a Boolean atom (\\pi^8 \\vee \\pi^9: a label, not a power)",
}


def status(rule: str, mode: str = "stl-nl") -> str:
    """What a formula becomes when `rule` fires in `mode`: ok, needs_review or rejected."""
    return "rejected" if mode == "faithful" and rule in FAITHFUL_REJECTED else RULES[rule][0]


def description(rule: str, mode: str = "stl-nl") -> str:
    """What `rule` does in `mode` (for a rule that rejects, why)."""
    if mode == "faithful":
        return FAITHFUL_REJECTED.get(rule) or FAITHFUL_DESCRIPTIONS.get(rule) or RULES[rule][1]
    return RULES[rule][1]

MAX_BOUND = 2**31 - 1
RANDOM_BOUND_RANGE = (0, 100)
RANDOM_BOUND_TRIES = 100


class Rejected(Exception):
    """The formula can't be represented: `rule` is the reason, `detail` the construct (e.g. the unknown command)."""

    def __init__(self, rule: str, detail: str = ""):
        assert RULES[rule][0] == "rejected" or rule in FAITHFUL_REJECTED, rule
        super().__init__(f"{rule}: {detail}" if detail else rule)
        self.rule, self.detail = rule, detail


class Trace:
    """
    What happens to one formula: the rules that fire (in order, once each), the review reasons, the substitutions. In
    the faithful mode a rule of FAITHFUL_REJECTED rejects the formula as it fires.
    """

    def __init__(self, mode: str = "stl-nl"):
        assert mode in MODES, mode
        self.mode = mode
        self.rules: list[str] = []
        self.reviews: list[str] = []
        self.substitutions: dict[str, int] = {}
        self.rounded: list[list[list[str]]] = []

    def fire(self, rule: str):
        assert rule in RULES, rule
        assert self.mode == "faithful" or rule not in FAITHFUL_RULES, rule
        if self.mode == "faithful" and rule in FAITHFUL_REJECTED:
            raise Rejected(rule)
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


def _walk_formula(node):
    """The nodes of the formula outside its intervals."""
    yield node
    for child in node.args:
        yield from _walk_formula(child)


def _symbols(node) -> set[str]:
    return {n.value for n in _walk(node) if n.kind == "var"}


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
    if node.kind == "pow":
        return left ** int(right)
    if node.kind == "mul":
        return left * right
    if node.kind == "div":
        return left / right
    return left + right if node.kind == "add" else left - right


def _bound(node, values: dict, rounding) -> tuple[int | str | float, Fraction | None]:
    """A bound resolved (an integer rounded with `rounding`, a parameter, math.inf) and its exact value if a number."""
    if node.kind == "inf":
        return math.inf, None
    if node.kind == "var" and node.value not in values:
        return node.value, None
    exact = _value(node, values)
    return rounding(exact), exact


def _resolved(interval, values: dict) -> tuple[int | str | float, int | str | float, str | None]:
    """(lower, upper, the rule a failure breaks or None) of an interval: closed, rounded outward."""
    try:
        lo, hi = _bound(interval.lo, values, math.floor)[0], _bound(interval.hi, values, math.ceil)[0]
    except ZeroDivisionError:
        return 0, 0, "division"
    numbers = [b for b in (lo, hi) if isinstance(b, int)]
    if any(b < 0 for b in numbers):
        return lo, hi, "negative_bound"
    if len(numbers) == 2 and lo > hi:
        return lo, hi, "empty_interval"
    if any(b > MAX_BOUND for b in numbers):
        return lo, hi, "bound_too_large"
    return lo, hi, None


def _number_text(x: Fraction) -> str:
    return str(x.numerator) if x.denominator == 1 else str(float(x)) if 10**12 % x.denominator == 0 else str(x)


def resolve_bounds(root, trace: Trace, rng):
    """
    Makes every interval of the tree a closed interval of stl-nl, whose bounds are integers, parameters or an upper
    inf. A symbol alone in a bound stays a parameter (G[0,T]). The symbols that can't (in a bound expression such as
    [t, t+5], which stl-nl doesn't have, or also used as a signal, as in G[0,T] (x < T), which it forbids) get random
    integers: the same symbol the same value, also where it is compared. Open intervals are closed, real bounds rounded
    outward. The nodes are changed in place; each interval gets `lower` and `upper`. In the faithful mode the bounds
    are kept as written instead (keep_bounds).
    """
    if trace.mode == "faithful":
        keep_bounds(root, trace)
        return
    intervals = [n.interval for n in _walk(root) if n.interval is not None]
    bounds = [b for i in intervals for b in (i.lo, i.hi)]
    in_bounds = set().union(*map(_symbols, bounds))
    in_expressions = set().union(*(_symbols(b) for b in bounds if b.kind != "var"))
    signals = {n.value for n in _walk_formula(root) if n.kind in ("var", "atom")}
    # inf is stl-nl's word for an infinite bound: a symbol of that name can't be a parameter
    symbols = sorted(in_expressions | (in_bounds & signals) | ({"inf"} & in_bounds))
    if in_bounds - set(symbols):
        trace.fire("parameter_bounds")
    values = {}
    if symbols:
        trace.fire("random_symbolic_bounds")
        for _ in range(RANDOM_BOUND_TRIES):
            values = {s: rng.randint(*RANDOM_BOUND_RANGE) for s in symbols}
            if all(_resolved(i, values)[2] is None for i in intervals):
                break
        else:
            raise Rejected("bounds_unsatisfiable", ", ".join(symbols))
        trace.substitutions = values
        # The symbols also become numbers where they are compared (G[0,T] (x < T) -> G[0,37] (x < 37))
        for node in _walk(root):
            if node.kind == "var" and node.value in values:
                node.kind, node.value = "num", Fraction(values[node.value])
    for interval in intervals:
        lower, upper, broken = _resolved(interval, values)
        if broken:
            raise Rejected(broken, f"[{lower},{upper}]")
        if interval.lo_open or interval.hi_open:
            trace.fire("close_open_interval")
        exact = [_bound(interval.lo, values, math.floor)[1], _bound(interval.hi, values, math.ceil)[1]]
        resolved = [lower, upper]
        if any(x is not None and x != b for x, b in zip(exact, resolved)):
            trace.fire("round_bounds_outward")
            trace.rounded.append([[str(b) if x is None else _number_text(x) for x, b in zip(exact, resolved)],
                                  [str(b) for b in resolved]])
        interval.lower, interval.upper = lower, upper
        interval.lo_open = interval.hi_open = False


def _kept_bound(node, trace: Trace):
    """
    A bound of the faithful mode: math.inf; a number (an int, or a Fraction when it isn't an integer: real_bounds),
    computed when it is an expression of numbers only (8-4 is 4); the name of a parameter; or else the expression
    itself, a tree (bound_expressions).
    """
    if node.kind == "inf":
        return math.inf
    if not _symbols(node):
        try:
            value = _value(node, {})
        except ZeroDivisionError:
            raise Rejected("division", "by 0 in a time bound")
        if value.denominator == 1:
            return int(value)
        trace.fire("real_bounds")
        return value
    if node.kind == "var":
        trace.fire("parameter_bounds")
        return node.value
    trace.fire("bound_expressions")
    return node


def keep_bounds(root, trace: Trace):
    """
    The intervals of the faithful mode: the bounds as the paper writes them (_kept_bound), open or closed as written.
    Only what has no meaning is rejected: a negative bound, a lower bound above the upper one.
    """
    for interval in (n.interval for n in _walk(root) if n.interval is not None):
        lower, upper = _kept_bound(interval.lo, trace), _kept_bound(interval.hi, trace)
        numbers = [b for b in (lower, upper) if isinstance(b, (int, Fraction)) and b != math.inf]
        if any(b < 0 for b in numbers):
            raise Rejected("negative_bound", f"[{interval_text(lower)},{interval_text(upper)}]")
        if len(numbers) == 2 and lower > upper:
            raise Rejected("empty_interval", f"[{interval_text(lower)},{interval_text(upper)}]")
        if interval.lo_open or interval.hi_open:
            trace.fire("open_intervals")
        interval.lower, interval.upper = lower, upper


def interval_text(bound) -> str:
    """A bound in a message."""
    return _number_text(bound) if isinstance(bound, Fraction) else str(bound)


# ---------------------------------------------------------------- the symbols and their meanings

CONSTANT_PATTERN = re.compile(r"\b(threshold|constant|parameter|bound|limit|maximum|minimum|max|min)s?\b", re.I)
PLACEHOLDER_PATTERN = re.compile(r"\b(sub-?formula|formula|specification)s?\b", re.I)


def check_symbols(root, meanings: dict[str, str], trace: Trace):
    """
    Records the real-valued signals the paper calls a threshold, constant, ... (symbolic_constant: they are read as
    signals) and the Boolean atoms it calls a (sub)formula (placeholder_subformula: the subformula can't be rebuilt,
    so the atom stands for it). `meanings` maps the normalized names to the meanings.
    """
    constants = sorted({n.value for n in _walk_formula(root) if n.kind == "var"
                        and CONSTANT_PATTERN.search(meanings.get(n.value, ""))})
    if constants:
        trace.fire("symbolic_constant")
    placeholders = sorted({n.value for n in _walk_formula(root) if n.kind == "atom"
                           and PLACEHOLDER_PATTERN.search(meanings.get(n.value, ""))})
    if placeholders:
        trace.fire("placeholder_subformula")
