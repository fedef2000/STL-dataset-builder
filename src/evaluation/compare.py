"""
How close a formula is to a reference one: the round-trip check of the dataset (step 8) and, later, the evaluation of
the model trained on it. Both formulas come as the tree `stlgen parse` gives (stlgen.py); the level is the first that
holds:

    equivalent     the same formula once both are written in one standard form (below)
    renamed        the same after renaming signals and parameters one to one (omega -> speed, T -> T_max)
    near           the same after renaming, apart from details a description seldom states:
                   strict          < vs <=, > vs >=
                   open_end        an open vs a closed end of an interval, [0,3) vs [0,3]
                   outer_always    G[0,inf] around the whole formula, or around some of its top-level conjuncts
    same_pattern   the same pattern (src/normalization/pattern.py, as in analysis.md), with two flags:
                   bounds_equal    the same time intervals (as a multiset, parameters renamed)
                   leaves_equal    the same conditions: relations, atoms, true/false (as a multiset, names renamed)
    different      anything else

The standard form only rewrites what holds in any STL semantics (continuous or discrete time, strict or inclusive
until), so it doesn't depend on which one a set uses:
    a -> b  =  !a || b;  negations pushed down to the atoms (!F p = G !p, !(a && b) = !a || !b, !(p U q) = !p R !q,
    !(x < 3) = x >= 3);  && and || flattened, sorted, without repeats or true/false operands;  G[I] (a && b) =
    G[I] a && G[I] b and F[I] (a || b) = F[I] a || F[I] b;  a comparison as one polynomial against 0, divided by its
    largest coefficient, with the sign whose text is smaller (x - y > 0 = x > y, 2 * x > 4 = x > 2, 3 < x = x > 3;
    |-x| = |x|, |2 * x| = 2 * |x|);  an absolute value alone against a number opened (|e| <= c = e <= c && -e <= c,
    |e| >= c = e >= c || -e >= c);  a comparison of two numbers is true or false;  G[I] true = true, F[I] false =
    false (no interval is empty);  true U[I] q = F[I] q, false R[I] q = G[I] q.
Not rewritten: nested operators merged (F[0,5] F[0,3] p = F[0,8] p), anything else that needs real reasoning.

Renaming (the technique of pattern.py): each signal is replaced by a placeholder, and the placeholders are given in
every order to the names that play the same role in the formula; the smallest text is a form that every renaming of
the formula shares. A name's role: the formula written with that name marked and the others as their kinds, then
refined with the roles of the names around it (_roles), so that few names share one. Two formulas are the same up to
renaming when those texts are equal. Past MAX_ORDERS orders one order is used ("exact": False), and a renamed formula
might then be missed (on the dataset's formulas, never: at most 5 names share a role). Atoms, real-valued signals and
parameters are kept apart: an atom never becomes a signal or a parameter. In arithmetic, signals are kept apart by
identity whatever their names, so that writing every other name as its kind doesn't merge x - y into 0.
"""
from fractions import Fraction
from itertools import combinations, permutations, product
from math import factorial
import re

from src.normalization.pattern import pattern

MAX_ORDERS = 40320                # 8! orders of the names of one formula
PLACEHOLDER = re.compile(r"§(\d+)§")  # a name's placeholder: § is never in a name, and survives repr()
NEAR_DETAILS = ("strict", "open_end", "outer_always")
LEVELS = ("equivalent", "renamed", "near", "same_pattern", "different", "unparseable", "not_checkable")

FLIP = {"<": ">", "<=": ">=", ">": "<", ">=": "<=", "==": "==", "!=": "!="}         # sides swapped
NEGATION = {"<": ">=", "<=": ">", ">": "<=", ">=": "<", "==": "!=", "!=": "=="}     # relation negated
RELAXED = {"<": "<=", ">": ">="}
UNARY = {"globally": "G", "eventually": "F"}
BINARY = {"until": "U", "release": "R"}
DUAL = {"G": "F", "F": "G", "U": "R", "R": "U", "and": "or", "or": "and", "true": "false", "false": "true"}


# ---------------------------------------------------------------- tree -> negation normal form (no names involved)

def nnf(node: dict, negated: bool = False) -> tuple:
    """The stlgen tree as tuples, without -> and with ! only on atoms."""
    kind = node["type"]
    if kind in ("true", "false"):
        return (DUAL[kind] if negated else kind,)
    if kind == "atom":
        return ("natom" if negated else "atom", node["name"])
    if kind == "relation":
        op = node["comparison"]
        return ("rel", NEGATION[op] if negated else op, node["left"], node["right"])
    if kind == "not":
        return nnf(node["child"], not negated)
    if kind in ("and", "or"):
        connective = DUAL[kind] if negated else kind
        return (connective, tuple(nnf(child, negated) for child in node["children"]))
    if kind == "implies":
        return nnf({"type": "or", "children": [{"type": "not", "child": node["left"]}, node["right"]]}, negated)
    if kind in UNARY:
        op = UNARY[kind]
        return (DUAL[op] if negated else op, node["interval"], nnf(node["child"], negated))
    if kind in BINARY:
        op = BINARY[kind]
        return (DUAL[op] if negated else op, node["interval"], nnf(node["left"], negated), nnf(node["right"], negated))
    raise ValueError(f"unknown formula node {kind!r}")


def identifiers(tree: tuple) -> set[tuple[str, str]]:
    """The names in the tree, as (kind, name): kind atom, var (a real-valued signal) or param (a bound)."""
    found = set()

    def expression(node):
        if node["type"] == "variable":
            found.add(("var", node["name"]))
        for key in ("child", "left", "right"):
            if key in node:
                expression(node[key])

    def walk(t):
        kind = t[0]
        if kind in ("atom", "natom"):
            found.add(("atom", t[1]))
        elif kind == "rel":
            expression(t[2]), expression(t[3])
        elif kind in ("and", "or"):
            for child in t[1]:
                walk(child)
        elif kind in ("G", "F", "U", "R"):
            for bound in (t[1]["lower"], t[1]["upper"]):
                if isinstance(bound, dict) and bound["type"] == "parameter":
                    found.add(("param", bound["name"]))
            for child in t[2:]:
                walk(child)
    walk(tree)
    return found


# ---------------------------------------------------------------- the standard form, with the names given by `name`

class Options:
    def __init__(self, strict=False, open_end=False, outer_always=False):
        self.strict, self.open_end, self.outer_always = strict, open_end, outer_always


def polynomial(node: dict) -> dict[tuple, Fraction]:
    """
    An arithmetic tree as {monomial: coefficient}, a monomial being the tuple of its factors: a signal ("var", name),
    an absolute value ("abs", inner polynomial) or a division by a signal ("div", numerator, denominator). Signals are
    kept apart by identity, whatever names are given to them when the text is written (_text).
    """
    kind = node["type"]
    if kind == "variable":
        return {(("var", node["name"]),): Fraction(1)}
    if kind == "rational":
        return _clean({(): Fraction(int(node["numerator"]), int(node["denominator"]))})
    if kind == "abs":
        inner = polynomial(node["child"])
        if not _variable_part(inner):
            return _clean({(): abs(inner.get((), Fraction(0)))})
        size = _size(inner)                       # |2 * x| = 2 * |x|; the sign inside is chosen by _text
        return {(("abs", _key(_scaled(inner, 1 / size))),): size}
    left, right = polynomial(node["left"]), polynomial(node["right"])
    if kind in ("add", "subtract"):
        return _sum(left, right, 1 if kind == "add" else -1)
    if kind == "multiply":
        total = {}
        for (m1, c1), (m2, c2) in product(left.items(), right.items()):
            monomial = tuple(sorted(m1 + m2, key=repr))
            total[monomial] = total.get(monomial, Fraction(0)) + c1 * c2
        return _clean(total)
    if kind == "divide":
        if not _variable_part(right) and right.get((), 0):
            return _scaled(left, 1 / right[()])
        return {(("div", _key(left), _key(right)),): Fraction(1)}   # by a signal: kept as one factor
    raise ValueError(f"unknown arithmetic node {kind!r}")


def _clean(p):
    return {m: c for m, c in p.items() if c != 0}


def _variable_part(p):
    return [m for m in p if m]


def _size(p):
    return max(abs(c) for m, c in p.items() if m)


def _scaled(p, factor):
    return _clean({m: c * factor for m, c in p.items()})


def _sum(left, right, sign=1):
    total = dict(left)
    for monomial, c in right.items():
        total[monomial] = total.get(monomial, Fraction(0)) + sign * c
    return _clean(total)


def _key(p):
    return tuple(sorted(p.items(), key=repr))


def _factor_text(factor, name) -> str:
    if factor[0] == "var":
        return name(factor)
    if factor[0] == "abs":
        inner = dict(factor[1])
        return "|" + min(_text(inner, name), _text(_scaled(inner, -1), name)) + "|"   # |x - y| = |y - x|
    return f"({_text(dict(factor[1]), name)})/({_text(dict(factor[2]), name)})"


def _text(p, name) -> str:
    """The polynomial written with the names `name` gives, its terms sorted by their text."""
    terms = sorted(("*".join(sorted(_factor_text(f, name) for f in m)), str(c)) for m, c in p.items())
    return " + ".join(f"{c}*{m}" if m else c for m, c in terms) or "0"


def relation(op: str, left: dict, right: dict, name, options: Options) -> tuple:
    """
    left op right as p op 0, p divided by its largest coefficient (x - y > 0 = x > y, 2 * x > 4 = x > 2); of p op 0
    and -p flip(op) 0 (3 < x = x > 3) the one whose text is smaller. A comparison of numbers is true or false.
    """
    return _comparison(_sum(polynomial(left), polynomial(right), -1), op, name, options)


def _comparison(p: dict, op: str, name, options: Options) -> tuple:
    """p op 0 in the standard form (see relation); an absolute value alone against a number is opened (_opened)."""
    opened = _opened(p, op)
    if opened is not None:
        kind, parts = opened
        return _combine(kind, [_comparison(part, part_op, name, options) for part, part_op in parts])
    if not _variable_part(p):
        value = p.get((), Fraction(0))
        holds = {"<": value < 0, "<=": value <= 0, ">": value > 0, ">=": value >= 0, "==": value == 0, "!=": value != 0}
        return ("true",) if holds[op] else ("false",)
    p = _scaled(p, 1 / _size(p))
    candidates = []
    for poly, comparison in ((p, op), (_scaled(p, -1), FLIP[op])):
        if options.strict:
            comparison = RELAXED.get(comparison, comparison)
        candidates.append(("rel", comparison, _text(poly, name)))
    return min(candidates, key=repr)


def _opened(p: dict, op: str):
    """
    a * |e| + k op 0, with |e| the only signal term, as two comparisons of e: |e| <= c is e <= c && -e <= c, and
    |e| >= c is e >= c || -e >= c (the same with < and >). Returns (connective, [(polynomial, op), ...]) or None.
    """
    terms = _variable_part(p)
    if len(terms) != 1 or len(terms[0]) != 1 or terms[0][0][0] != "abs" or op in ("==", "!="):
        return None
    a = p[terms[0]]
    c = -p.get((), Fraction(0)) / a
    if a < 0:
        op = FLIP[op]
    e = dict(terms[0][0][1])
    parts = [(_sum(e, {(): c}, -1), op), (_sum(_scaled(e, -1), {(): c}, -1), op)]
    return ("and" if op in ("<", "<=") else "or"), parts


def interval(bounds: dict, name, options: Options) -> tuple:
    def bound(b):
        if isinstance(b, int):
            return b
        return "inf" if b["type"] == "infinity" else ("param", name(("param", b["name"])))
    lower_open, upper_open = bounds.get("lower_open", False), bounds.get("upper_open", False)
    if options.open_end:
        lower_open = upper_open = False
    return (bound(bounds["lower"]), bound(bounds["upper"]), lower_open, upper_open)


def _combine(kind: str, items) -> tuple:
    """&& or || of standard forms: flattened, without true/false operands or repeats, sorted."""
    absorbing, neutral = ("false",), ("true",)
    if kind == "or":
        absorbing, neutral = neutral, absorbing
    flat = []
    for item in items:
        flat.extend(item[1] if item[0] == kind else [item])
    if absorbing in flat:
        return absorbing
    flat = sorted({item for item in flat if item != neutral}, key=repr)
    if not flat:
        return neutral
    return flat[0] if len(flat) == 1 else (kind, tuple(flat))


def _temporal(op: str, iv: tuple, child: tuple) -> tuple:
    # every interval holds at least one time step (stlgen checks it), so G false = false and F true = true
    if child[0] in ("true", "false"):
        return child
    return (op, iv, child)


def standard(tree: tuple, name, options: Options) -> tuple:
    kind = tree[0]
    if kind in ("true", "false"):
        return tree
    if kind == "atom":
        return ("atom", name(("atom", tree[1])))
    if kind == "natom":
        return ("not", ("atom", name(("atom", tree[1]))))
    if kind == "rel":
        return relation(tree[1], tree[2], tree[3], name, options)
    if kind in ("and", "or"):
        return _combine(kind, [standard(child, name, options) for child in tree[1]])
    iv = interval(tree[1], name, options)
    if kind in ("G", "F"):
        child = standard(tree[2], name, options)
        split = "and" if kind == "G" else "or"
        if child[0] == split:
            return _combine(split, [_temporal(kind, iv, part) for part in child[1]])
        return _temporal(kind, iv, child)
    left, right = standard(tree[2], name, options), standard(tree[3], name, options)
    if kind == "U" and left == ("true",):     # true U[I] q = F[I] q
        return standard(("F", tree[1], tree[3]), name, options)
    if kind == "R" and left == ("false",):    # false R[I] q = G[I] q
        return standard(("G", tree[1], tree[3]), name, options)
    return (kind, iv, left, right)


def _without_outer_always(form: tuple) -> tuple:
    parts = form[1] if form[0] == "and" else (form,)
    unwrapped = [p[2] if p[0] == "G" and p[1][:3] == (0, "inf", False) else p for p in parts]
    return _combine("and", unwrapped)


def standard_form(tree: tuple, name, options: Options) -> tuple:
    form = standard(tree, name, options)
    return _without_outer_always(form) if options.outer_always else form


def _parts(form: tuple, leaves: bool) -> list[str]:
    """The intervals (leaves=False) or the conditions (leaves=True) of a standard form, sorted, repeats kept."""
    out = []

    def walk(f):
        kind = f[0]
        if kind in ("and", "or"):
            for child in f[1]:
                walk(child)
        elif kind in ("G", "F", "U", "R"):
            if not leaves:
                out.append(repr(f[1]))
            for child in f[2:]:
                walk(child)
        elif leaves:
            out.append(repr(f))
    walk(form)
    return sorted(out)


# ---------------------------------------------------------------- renaming

def _same_names(tree: tuple, render) -> str:
    return render(lambda identifier: identifier[1])


def _any_kind_name(identifier: tuple) -> str:
    return "?" + identifier[0]


def _roles(names: list, render) -> dict:
    """
    A label for each name that every renaming of the formula keeps, and that tells apart as many names as it can: at
    first the formula with that name marked and every other name written as its kind; then, until no more names are
    told apart, with every other name written as its current label (so a name is known by the names around it).
    """
    labels = {i: (i[0], render(lambda other, marked=i: "@" if other == marked else _any_kind_name(other)))
              for i in names}
    while True:
        rank = {label: n for n, label in enumerate(sorted(set(labels.values())))}
        short = {i: f"<{rank[labels[i]]}>" for i in names}
        refined = {i: (labels[i], render(lambda other, marked=i: "@" if other == marked else short[other]))
                   for i in names}
        refined_rank = {label: n for n, label in enumerate(sorted(set(refined.values())))}
        refined = {i: (i[0], refined_rank[refined[i]]) for i in names}
        if len(set(refined.values())) == len(rank):
            return {i: (i[0], rank[labels[i]]) for i in names}
        labels = refined


_CACHE: dict = {}


def _any_names(tree: tuple, render, key=None) -> tuple[str, list, bool]:
    """
    (text shared by every renaming of the formula, its names in the order their placeholders first appear, exact).
    `render(name)` writes the formula with the names that `name((kind, name))` gives. `key`: when given, the answer is
    kept and given again for the same key (the dataset's formula is compared with many candidates).
    """
    if key is not None and key in _CACHE:
        return _CACHE[key]
    names = sorted(identifiers(tree))
    roles = _roles(names, render)
    groups = {}
    for i in names:
        groups.setdefault(roles[i], []).append(i)
    groups = [groups[role] for role in sorted(groups)]
    orders_count = 1
    for group in groups:
        orders_count *= factorial(len(group))
    exact = orders_count <= MAX_ORDERS
    orders = product(*map(permutations, groups)) if exact else [groups]
    best, best_names = None, None
    for order in orders:
        flat = [i for group in order for i in group]
        placeholders = {i: f"§{n}§" for n, i in enumerate(flat)}
        text = render(placeholders.__getitem__)
        if best is None or text < best:
            best, best_names = text, flat
    # placeholders renumbered by first appearance, so that the text doesn't depend on unused or vanished names
    appearance = []

    def renumber(match):
        name = best_names[int(match[1])]
        if name not in appearance:
            appearance.append(name)
        return f"§{appearance.index(name)}§"
    answer = PLACEHOLDER.sub(renumber, best), appearance, exact
    if key is not None:
        if len(_CACHE) > 100_000:
            _CACHE.clear()
        _CACHE[key] = answer
    return answer


# ---------------------------------------------------------------- compare

def compare(reference: dict | None, candidate: dict | None) -> dict:
    """
    The level of `candidate` (a formula written from the description) against `reference` (the dataset's formula),
    both stlgen trees; None for a formula stlgen couldn't parse.
    -> {"level", "renamed", "mapping", "near", "bounds_equal", "leaves_equal", "exact"}:
    renamed: whether names had to be renamed (equivalent: False; renamed: True; near: either);
    mapping: {candidate's name: reference's name} for every name that differs;
    near: the details that differ (level near); bounds_equal, leaves_equal: for the levels below near;
    exact: False if a renaming couldn't be tried in every order.
    """
    result = {"level": None, "renamed": None, "mapping": {}, "near": [], "bounds_equal": None,
              "leaves_equal": None, "exact": True}
    if reference is None:
        return result | {"level": "not_checkable"}
    if candidate is None:
        return result | {"level": "unparseable"}
    ours, theirs = nnf(reference), nnf(candidate)

    def form_text(tree, options):
        return lambda name: repr(standard_form(tree, name, options))

    def matched(options):
        """(same with the same names, same up to renaming, mapping, exact) under these options."""
        render_o, render_t = form_text(ours, options), form_text(theirs, options)
        if _same_names(ours, render_o) == _same_names(theirs, render_t):
            return True, True, {}, True
        if render_o(_any_kind_name) != render_t(_any_kind_name):   # no renaming can make them equal
            return False, False, {}, True
        key = (repr(ours), "form", options.strict, options.open_end, options.outer_always)
        text_o, names_o, exact_o = _any_names(ours, render_o, key)
        text_t, names_t, exact_t = _any_names(theirs, render_t)
        if text_o != text_t:
            return False, False, {}, exact_o and exact_t
        mapping = {t[1]: o[1] for o, t in zip(names_o, names_t) if o[1] != t[1]}
        return False, True, mapping, exact_o and exact_t

    same, renamed, mapping, exact = matched(Options())
    result["exact"] = exact
    if same:
        return result | {"level": "equivalent", "renamed": False}
    if renamed:
        return result | {"level": "renamed", "renamed": True, "mapping": mapping}
    subsets = [s for size in (1, 2, 3) for s in combinations(NEAR_DETAILS, size)]
    for details in subsets:
        same, renamed, mapping, exact = matched(Options(**{d: True for d in details}))
        result["exact"] = result["exact"] and exact
        if same or renamed:
            return result | {"level": "near", "renamed": not same, "mapping": mapping, "near": list(details)}

    def parts_text(tree, leaves):
        return lambda name: repr(_parts(standard_form(tree, name, Options()), leaves))
    flags = {}
    for flag, leaves in (("bounds_equal", False), ("leaves_equal", True)):
        render_o, render_t = parts_text(ours, leaves), parts_text(theirs, leaves)
        if render_o(_any_kind_name) != render_t(_any_kind_name):
            flags[flag] = False
            continue
        text_o, _, exact_o = _any_names(ours, render_o, (repr(ours), flag))
        text_t, _, exact_t = _any_names(theirs, render_t)
        flags[flag] = text_o == text_t
        result["exact"] = result["exact"] and exact_o and exact_t
    level = "same_pattern" if pattern(reference)[0] == pattern(candidate)[0] else "different"
    return result | flags | {"level": level}

