"""
The second stage of the comparator: whether two formulas are equivalent in meaning, checked with stlsat (a
satisfiability checker for STL: ~/repos/stlsat, config.STLSAT_BIN). compare.py only sees formulas that are written the
same way; F[0,5] F[0,3] p and F[0,8] p are different for it and the same for stlsat.

Two checks for the dataset's formula `ref` and a model's formula `cand`, with the names of `cand` renamed to those of
`ref`:
    ref && !cand  unsatisfiable: ref implies cand
    cand && !ref  unsatisfiable: cand implies ref
and the outcome:
    equivalent    both unsatisfiable
    stronger      only cand implies ref (cand asks more: G[0,5] p against G[0,3] p)
    weaker        only ref implies cand
    incomparable  neither
    unknown       stlsat ran past its time (TIMEOUT seconds) under every renaming tried
    sat_skipped   a formula stlsat can't take (below), or no renaming to try: not checked
The dataset's formula alone gets a flag: unsatisfiable (nothing satisfies it) or valid (everything does); then
"equivalent" says little.

stlsat's semantics, which the outcome depends on: discrete time (one step = 1, the bounds are integers), until
inclusive (p U[a,b] q: q at some i in [t+a,t+b], p on all of [t,i]), signals unconstrained real values and atoms free
Booleans. A named threshold (x > c) is a signal for stlsat, which may change over time: an "equivalent" holds
for every c, so also for a constant one; a "different" may (rarely) come from that.

Skipped (sat_skipped, decided on 2026-11-25): an interval with an infinite end (G[0,inf]) or a named end (G[0,T]),
stlsat has neither; arithmetic beyond affine (x * y, x / y). Open ends are moved by one step: (0,5] = [1,5]. Until
2026-11-25 this outcome was called not_checkable: renamed so that "not checkable" says only that stlgen can't read the
dataset's formula (roundtrip.py).

Renaming: the names of cand are given one to one to those of ref of the same kind (atom to atom, signal to signal); a
different number of names of one kind, or more than MAX_RENAMINGS ways, is skipped. The ways are tried from the
likeliest (the mapping compare.py found, then equal names, then names in the same conditions: speed > 80 and v > 80),
and the first equivalent one stops the search; otherwise the best certain outcome wins (stronger, weaker, then
incomparable). After MAX_TIMEOUTS renamings that ran past their time, the search stops.
"""
import subprocess
import tempfile
import threading
from fractions import Fraction
from itertools import permutations, product
from pathlib import Path

from config import STLSAT_BIN
from src.evaluation.compare import identifiers, nnf, polynomial

TIMEOUT = 10          # seconds per stlsat call
MAX_RENAMINGS = 24
MAX_TIMEOUTS = 3      # renamings that ran past their time, after which an answer is given up (unknown)
OUTCOMES = ("equivalent", "stronger", "weaker", "incomparable", "unknown", "sat_skipped")
PREFIX = {"atom": "a", "var": "v"}   # the names written for stlsat: a0, a1, ... and v0, v1, ...


class Skipped(Exception):
    """A formula stlsat can't take; the message says why."""


class StlsatError(Exception):
    """stlsat is missing or failed on a formula (not a timeout)."""


# ---------------------------------------------------------------- tree -> stlsat text

def _number(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _affine(p: dict, name) -> str:
    """A polynomial (compare.polynomial) as an stlsat sum: coefficient*signal, |sum|, numbers; signs written apart."""
    terms = []
    for monomial, c in sorted(p.items(), key=repr):
        if not monomial:
            text, size = _number(abs(c)), None
        elif len(monomial) > 1 or monomial[0][0] == "div":
            raise Skipped("arithmetic beyond affine (a product or a division by a signal)")
        elif monomial[0][0] == "var":
            text = name(("var", monomial[0][1]))
            if abs(c) != 1:
                text = f"{_number(abs(c))}*{text}"
        else:   # |e| with coefficient c: |c| * |e| = | |c| * e |
            inner = {m: abs(c) * k for m, k in dict(monomial[0][1]).items()}
            text = f"|{_affine(inner, name)}|"
        terms.append(("-" if c < 0 else "+", text))
    if not terms:
        return "0"
    first_sign, first = terms[0]
    out = first if first_sign == "+" else f"0 - {first}"
    return out + "".join(f" {sign} {text}" for sign, text in terms[1:])


def _interval(bounds: dict) -> str:
    lower, upper = bounds["lower"], bounds["upper"]
    for b in (lower, upper):
        if isinstance(b, dict):
            raise Skipped("an infinite interval end" if b["type"] == "infinity" else "a named interval end")
    lower += 1 if bounds.get("lower_open") else 0
    upper -= 1 if bounds.get("upper_open") else 0
    if lower > upper:
        raise Skipped("an empty interval")
    return f"[{lower},{upper}]"


def to_stlsat(tree: dict, name) -> str:
    """An stlgen tree as stlsat text, every operand in parentheses; `name((kind, name))` gives the name to write."""
    kind = tree["type"]
    if kind in ("true", "false"):
        return kind
    if kind == "atom":
        return name(("atom", tree["name"]))
    if kind == "relation":
        p = {m: c for m, c in polynomial(tree["left"]).items()}
        for m, c in polynomial(tree["right"]).items():
            p[m] = p.get(m, Fraction(0)) - c
        p = {m: c for m, c in p.items() if c != 0}
        return f"({_affine(p, name)} {tree['comparison']} 0)"
    if kind == "not":
        return f"!({to_stlsat(tree['child'], name)})"
    if kind in ("and", "or"):
        joint = " && " if kind == "and" else " || "
        return "(" + joint.join(f"({to_stlsat(c, name)})" for c in tree["children"]) + ")"
    if kind == "implies":
        return f"(({to_stlsat(tree['left'], name)}) -> ({to_stlsat(tree['right'], name)}))"
    if kind in ("globally", "eventually"):
        op = "G" if kind == "globally" else "F"
        return f"{op}{_interval(tree['interval'])} ({to_stlsat(tree['child'], name)})"
    if kind in ("until", "release"):
        op = "U" if kind == "until" else "R"
        return f"(({to_stlsat(tree['left'], name)}) {op}{_interval(tree['interval'])} ({to_stlsat(tree['right'], name)}))"
    raise ValueError(f"unknown node {kind!r}")


def names_of(tree: dict) -> set[tuple[str, str]]:
    """(kind, name) of the atoms and signals; Skipped when a bound is a name (stlsat has no parameters)."""
    found = identifiers(nnf(tree))
    if any(kind == "param" for kind, _ in found):
        raise Skipped("a named interval end")
    return found


def why_skipped(tree: dict) -> str | None:
    """None if stlsat can take the formula, else why not."""
    try:
        names_of(tree)
        to_stlsat(tree, lambda i: i[1])
    except Skipped as exc:
        return str(exc)
    return None


# ---------------------------------------------------------------- stlsat

_cache: dict[str, str] = {}
_lock = threading.Lock()


def satisfiable(text: str, binary: Path = STLSAT_BIN, timeout: int = TIMEOUT) -> str:
    """'sat', 'unsat' or 'unknown' (past `timeout` seconds, or stlsat's own unknown) for one formula."""
    with _lock:
        if text in _cache:
            return _cache[text]
    binary = Path(binary)
    if not binary.is_file():
        raise StlsatError(f"stlsat not found at {binary} (set STLSAT_BIN, or build it: cargo build --release)")
    with tempfile.TemporaryDirectory(prefix="stlsat-") as directory:
        source = Path(directory) / "formula.stl"
        source.write_text(text + "\n", encoding="utf-8")
        try:
            result = subprocess.run([str(binary), "--smtlib-result", str(source)],
                                    capture_output=True, text=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            answer = "unknown"
        else:
            answer = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
            if result.returncode != 0 or answer not in ("sat", "unsat", "unknown"):
                raise StlsatError(f"stlsat exited {result.returncode} on {text!r}: {result.stderr.strip()[:300]}")
    with _lock:
        _cache[text] = answer
    return answer


# ---------------------------------------------------------------- renaming

def _conditions(tree: dict, own) -> dict:
    """For each name, the conditions it appears in, written with that name as @ and the others as their kind."""
    found = {}

    def walk(node):
        if node["type"] == "relation":    # its left and right are arithmetic, not formulas
            for i in names_of(node):
                text = to_stlsat(node, lambda other, i=i: "@" if other == i else PREFIX[other[0]])
                found.setdefault(i, []).append(text)
            return
        for child in [node[k] for k in ("child", "left", "right") if k in node] + node.get("children", []):
            walk(child)
    walk(tree)
    return {i: sorted(found.get(i, [])) for i in own}


def renamings(reference: dict, candidate: dict, hint: dict | None = None) -> list[dict]:
    """
    The one-to-one ways of giving the candidate's names those of the reference, kind by kind, likeliest first:
    {(kind, candidate name): (kind, reference name)}. Skipped when a kind has a different number of names, or
    there are more than MAX_RENAMINGS ways.
    """
    ref_names, cand_names = names_of(reference), names_of(candidate)
    by_kind = {}
    for kind in PREFIX:
        r = sorted(n for n in ref_names if n[0] == kind)
        c = sorted(n for n in cand_names if n[0] == kind)
        if len(r) != len(c):
            raise Skipped(f"a different number of {'atoms' if kind == 'atom' else 'signals'} ({len(r)} vs {len(c)})")
        by_kind[kind] = (r, c)
    count = 1
    for r, _ in by_kind.values():
        for n in range(2, len(r) + 1):
            count *= n
    if count > MAX_RENAMINGS:
        raise Skipped(f"too many renamings to try ({count})")
    ref_cond, cand_cond = _conditions(reference, ref_names), _conditions(candidate, cand_names)
    hint = hint or {}

    def score(mapping):
        s = 0
        for c, r in mapping.items():
            if hint.get(c[1]) == r[1]:
                s += 100
            elif c[1] == r[1] and c[1] not in hint:
                s += 10
            s += len(set(cand_cond[c]) & set(ref_cond[r]))
        return -s
    ways = []
    for choice in product(*[[dict(zip(c, order)) for order in permutations(r)] for r, c in by_kind.values()]):
        mapping = {}
        for part in choice:
            mapping |= part
        ways.append(mapping)
    return sorted(ways, key=lambda m: (score(m), sorted(m.items())))


# ---------------------------------------------------------------- the check

def _writer(reference_names):
    """name() for the reference's names: a0, a1, ... / v0, v1, ... in sorted order."""
    numbered = {}
    for kind in PREFIX:
        for n, i in enumerate(sorted(x for x in reference_names if x[0] == kind)):
            numbered[i] = f"{PREFIX[kind]}{n}"
    return numbered.__getitem__


def reference_flag(reference: dict) -> str | None:
    """'unsatisfiable', 'valid', 'unknown' or None (neither) for the dataset's formula; Skipped if stlsat can't take it."""
    text = to_stlsat(reference, _writer(names_of(reference)))
    if satisfiable(text) == "unsat":
        return "unsatisfiable"
    answer = satisfiable(f"!({text})")
    return "valid" if answer == "unsat" else ("unknown" if answer == "unknown" else None)


def _outcome(a: str, b: str) -> str:
    """The outcome from ref && !cand (a) and cand && !ref (b)."""
    if "unknown" in (a, b):
        return "unknown"
    return {("unsat", "unsat"): "equivalent", ("sat", "unsat"): "stronger",
            ("unsat", "sat"): "weaker", ("sat", "sat"): "incomparable"}[(a, b)]


def check(reference: dict, candidate: dict, hint: dict | None = None) -> dict:
    """
    -> {"sat": outcome, "sat_mapping": {candidate's name: reference's name} for the names that differ,
    "sat_reason": why sat_skipped, else None}. `hint`: compare.py's mapping, tried first.
    """
    try:
        for tree in (reference, candidate):
            to_stlsat(tree, lambda i: i[1])
        ways = renamings(reference, candidate, hint)
    except Skipped as exc:
        return {"sat": "sat_skipped", "sat_mapping": {}, "sat_reason": str(exc)}
    write = _writer(names_of(reference))
    ref_text = to_stlsat(reference, write)
    rank = {"equivalent": 0, "stronger": 1, "weaker": 2, "incomparable": 3}
    best, best_mapping, timeouts = "unknown", {}, 0
    for mapping in ways:
        cand_text = to_stlsat(candidate, lambda i, mapping=mapping: write(mapping[i]))
        a = satisfiable(f"({ref_text}) && !({cand_text})")
        b = "unknown" if a == "unknown" else satisfiable(f"({cand_text}) && !({ref_text})")
        outcome = _outcome(a, b)
        if outcome == "unknown":
            timeouts += 1
            if timeouts >= MAX_TIMEOUTS:
                break
            continue
        if best == "unknown" or rank[outcome] < rank[best]:
            best, best_mapping = outcome, mapping
        if best == "equivalent":
            break
    shown = {c[1]: r[1] for c, r in best_mapping.items() if c[1] != r[1]}
    return {"sat": best, "sat_mapping": shown, "sat_reason": None}
