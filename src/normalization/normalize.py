"""
The normalization of one formula, stage by stage: the record's filters, the paper's macros expanded, the tokens, the
tree, the bounds and symbols, the text in the grammar of stl-nl. The check with stlgen is done by the caller
(scripts/07_normalize_formulas.py), as it runs a program per formula.
"""
import random
from dataclasses import dataclass, field

from src.normalization import emit
from src.normalization.latex import Macro, expand, tokenize
from src.normalization.lexer import KNOWN_COMMANDS, PROTECTED_COMMANDS, lex
from src.normalization.parser import parse
from src.normalization.rules import PLACEHOLDER_PATTERN, Rejected, Trace, check_symbols, resolve_bounds

CONNECTIVE_FLAG = "the formula ends or starts with a connective"

# The usual names of the temporal operators (those of scripts/eval/render.py, which uses them to render the formulas
# of the evaluation set, and the LTL symbols of the mathabx package), for the papers that don't define them or define
# them with commands that only draw the symbol (\raisebox{...}{$\Square$}, \rotatebox{45}{$\Box$})
FALLBACK_OPERATORS = {
    **{n: r"\square" for n in ("always", "Always", "alw", "glob", "globally", "lglobally", "lalways", "LTLg",
                              "LTLglobally", "LTLsquare")},
    **{n: r"\lozenge" for n in ("eventually", "Eventually", "ev", "even", "event", "levent", "leventually", "LTLf",
                               "LTLeventually", "LTLdiamond", "diamond")},
    **{n: r"\mathcal{U}" for n in ("until", "Until", "U", "luntil", "LTLu")},
    "G": r"\mathbf{G}", "F": r"\mathbf{F}",
}


def _drawn_only(command: str, macros: dict[str, list[Macro]]) -> bool:
    """Whether the paper's definition of `command`, expanded in full, has a command the lexer doesn't know."""
    tokens = [command] + ["{", "}"] * max(d.arguments for d in macros[command])
    try:
        expanded = expand(tokens, macros, PROTECTED_COMMANDS, Trace())
    except Rejected:
        return True
    return any(t.startswith("\\") and len(t) > 2 and t not in KNOWN_COMMANDS for t in expanded)


def with_fallback(macros: dict[str, list[Macro]]) -> dict[str, list[Macro]]:
    """The paper's macros, with the table of operator names for the names it doesn't define or only draws."""
    merged = dict(macros)
    for name, body in FALLBACK_OPERATORS.items():
        command = "\\" + name
        if command not in macros or _drawn_only(command, macros):
            merged[command] = [Macro(0, None, tokenize(body), fallback=True)]
    return merged


@dataclass
class Result:
    status: str                      # ok, needs_review, rejected
    normalized: str | None
    rules: list[str]
    reasons: list[str]               # why it is rejected or needs review
    substitutions: dict = field(default_factory=dict)
    rounded: list = field(default_factory=list)
    structure: str | None = None     # the formula with numbers and names hidden (emit.structure)


def symbol_names(variables: dict[str, str], macros: dict[str, list[Macro]]) -> dict[str, str]:
    """The meanings of the variables by their normalized names (the LaTeX keys read as the formula is)."""
    names = {}
    for key, meaning in variables.items():
        try:
            tokens = lex(expand(tokenize(key), macros, PROTECTED_COMMANDS, Trace()), Trace())
        except Rejected:
            continue
        if len(tokens) == 1 and tokens[0].kind == "ID":
            names[tokens[0].value] = meaning
    return names


def normalize(formula: str, *, record_id: str = "", seed: str = "0", macros: dict[str, list[Macro]] | None = None,
              variables: dict[str, str] | None = None, other_logic: str | None = None,
              flags: list[str] = ()) -> Result:
    """
    The formula in the grammar of stl-nl, and what happened to it. `seed` and `record_id` set the random values of
    the symbolic bounds (the same record gets the same values on every run, whatever the other records).
    """
    trace = Trace()
    macros = with_fallback(macros or {})
    try:
        if other_logic:
            raise Rejected("other_logic", other_logic)
        if any(f.startswith(CONNECTIVE_FLAG) for f in flags):
            raise Rejected("connective_at_edge")
        tokens = lex(expand(tokenize(formula), macros, PROTECTED_COMMANDS, trace), trace)
        meanings = symbol_names(variables or {}, macros)
        formula_names = {n for n, m in meanings.items() if PLACEHOLDER_PATTERN.search(m)}
        root = parse(tokens, trace, formula_names)
        resolve_bounds(root, trace, random.Random(f"{seed}:{record_id}"))
        check_symbols(root, meanings, trace)
        text, structure = emit.formula(root), emit.structure(root)
    except Rejected as rejected:
        reason = f"{rejected.rule}: {rejected.detail}" if rejected.detail else rejected.rule
        trace.rules.append(rejected.rule)
        return Result("rejected", None, trace.rules, [reason], trace.substitutions, trace.rounded)
    status = "needs_review" if trace.reviews else "ok"
    return Result(status, text, trace.rules, trace.reviews, trace.substitutions, trace.rounded, structure)
