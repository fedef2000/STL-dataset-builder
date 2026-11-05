r"""
The description of a paired formula (a requirement passage of the paper) written to match its normalized formula: plain
text, as stl-nl writes its descriptions, with every symbol written as the formula writes it.

    the warning must be activated within $T_{\max}$ s, while $\varphi_{1}$ holds  ->
    the warning must be activated within T_max s, while varphi_1 holds

- Math ($...$, $$...$$, \\(...\\), \\[...\\]) goes through the same stages as the formula: the paper's macros expanded,
  then the lexer (lexer.py), so names, Greek letters, operators and comparisons come out as in the formula (varphi_1,
  x_dot, <=, G[0,5]); x(t) is x, a signal G is G_sig if the formula renamed it. The tokens are written back one by one,
  as the author wrote them: no tree, no parentheses added; a lone = stays = (it is prose).
- A math command written outside $...$ (\\varphi, \\leq, a paper macro) is read as math too.
- Text-mode LaTeX becomes plain text: \\emph{x} -> x, ``x'' -> "x", ~ and \\, -> a space, \\% -> %.
- Unicode math (from PDFs) becomes the names of the formula: φ1 -> phi_1 (varphi_1 if the formula has varphi), ≤ -> <=.

A passage with an odd number of $ that starts with a piece of math ("\varphi_2$ requires ...": the extraction cut it
inside math) is read as starting with a $.

What can't be converted is left as written and recorded, to count it before deciding what to do with it: a math span
the lexer can't read (`unreadable`, with the reason), a reference (\\ref, \\cite: `references`), any other LaTeX command
(`latex_left`). `names_not_in_formula` lists the names of the description the formula doesn't have (t, i, or a symbol
the formula writes another way).
"""
import re
from dataclasses import dataclass, field

from src.normalization.latex import Macro, expand, tokenize
from src.normalization.lexer import (ACCENTS, CONNECTIVES, GREEK, KNOWN_COMMANDS, MATH_FONTS, MATH_WRAPPERS,
                                     OPERATORS, PROTECTED_COMMANDS, RELATIONS, Tok, lex)
from src.normalization.emit import number
from src.normalization.rules import Rejected, Trace

DOLLAR = re.compile(r"(?<!\\)\$")
MATH_SPAN = re.compile(r"(?<!\\)\$\$(.+?)(?<!\\)\$\$|(?<!\\)\$(.+?)(?<!\\)\$|\\\((.+?)\\\)|\\\[(.+?)\\\]", re.S)
TEXT_WRAPPERS = re.compile(r"\\(emph|textit|textbf|texttt|textrm|textsf|textsc|textup|textnormal|textsl|text|mbox|"
                           r"underline)\s*\{([^{}]*)\}")
REFERENCE = re.compile(r"\\(ref|eqref|autoref|cref|Cref|pageref|cite|citep|citet|citealp)\s*(\[[^\]]*\])?\{[^{}]*\}")
TEXT_SYMBOLS = [("``", '"'), ("''", '"'), ("\\%", "%"), ("\\&", "&"), ("\\_", "_"), ("\\#", "#"), ("\\$", "$"),
                ("\\,", " "), ("\\ ", " "), ("\\;", " "), ("\\:", " "), ("\\!", ""), ("\\@", ""), ("\\-", ""),
                ("~", " ")]
TEXT_COMMANDS = {"\\ldots": "...", "\\dots": "...", "\\textendash": "-", "\\textemdash": "-", "\\xspace": "",
                 "\\newline": " ", "\\linebreak": " ", "\\noindent": "", "\\item": ""}
# A math command outside $...$, with its arguments and scripts: read as math
BARE_MATH = re.compile(r"\\[A-Za-z]+(?:\s*\{[^{}]*\})*(?:\s*[_^](?:\{[^{}]*\}|\\[A-Za-z]+|[A-Za-z0-9]))*")
LATEX_COMMAND = re.compile(r"\\[A-Za-z]+")
# Math the lexer doesn't read, written as words the lexer reads as names and then as the symbol (PLACEHOLDERS)
SPAN_SYMBOLS = {"\\%": "ZZpercent", "\\ldots": "ZZdots", "\\dots": "ZZdots", "\\cdots": "ZZdots"}
PLACEHOLDERS = {"ZZpercent": "%", "ZZdots": "..."}

UNICODE_GREEK = dict(zip("αβγδεζηθικλμνξπρστυφχψωΓΔΘΛΞΠΣΥΦΨΩϕϵϑϱς∆",
                         "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi pi rho sigma tau "
                         "upsilon phi chi psi omega Gamma Delta Theta Lambda Xi Pi Sigma Upsilon Phi Psi Omega phi "
                         "epsilon theta rho sigma Delta".split()))
# The LaTeX names a Unicode letter may stand for: the one the formula uses is taken
VARIANTS = {"phi": "varphi", "epsilon": "varepsilon", "theta": "vartheta", "rho": "varrho", "sigma": "varsigma"}
SUBSCRIPT_DIGITS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
UNICODE_NAME = re.compile(f"([{''.join(UNICODE_GREEK)}])([0-9₀-₉]*)")
UNICODE_SYMBOLS = {"≤": "<=", "≥": ">=", "≠": "!=", "−": "-", "∞": "inf", "□": "G", "◇": "F", "♢": "F", "¬": "!",
                   "∧": "&&", "∨": "||"}

# After these a - is a sign and a | opens an absolute value
OPERATOR_KINDS = {"REL", "AND", "OR", "IMP", "IFF", "NOT", "LP", "COMMA", "COLON", "PLUS", "MINUS", "STAR", "SLASH",
                  "CARET", "IN", "DEF", "OP", "BOP", "PUNCT"}
SIMPLE_TEXT = {"NOT": "!", "AND": "&&", "OR": "||", "IMP": "->", "IFF": "<->", "COLON": ":", "PUNCT": ".", "PLUS": "+",
               "MINUS": "-", "SLASH": "/", "CARET": "^", "ABS": "|", "IN": "in", "INF": "inf"}


class Unreadable(Exception):
    """A math span that can't be written as text (the reason)."""


@dataclass
class Description:
    normalized: str
    unreadable: list[dict] = field(default_factory=list)     # {"span": as written, "reason": ...}
    references: list[str] = field(default_factory=list)
    latex_left: list[str] = field(default_factory=list)
    names_not_in_formula: list[str] = field(default_factory=list)


class Writer:
    """The tokens of a math span written back as text (see the module), and the names found in them."""

    def __init__(self, formula_names: set[str]):
        self.formula_names = formula_names
        self.names: list[str] = []

    def name(self, value: str) -> str:
        if value in PLACEHOLDERS:
            return PLACEHOLDERS[value]
        if value in ("G", "F", "X", "U", "R") and f"{value}_sig" in self.formula_names:
            value = f"{value}_sig"  # the formula renamed this signal (reserved_names)
        self.names.append(value)
        return value

    def interval(self, interval) -> str:
        """As the formula writes it: [a,b], (a,b], ...; an infinite upper bound is always closed: [a,inf]."""
        lo, hi = self.tokens(interval.lo), self.tokens(interval.hi)
        infinite = [t.kind for t in interval.hi if t.kind != "PLUS"] == ["INF"]
        return f"{'(' if interval.lo_open else '['}{lo},{'inf' if infinite else hi}" \
               f"{')' if interval.hi_open and not infinite else ']'}"

    def text(self, tok: Tok) -> str:
        kind = tok.kind
        if kind in ("OP", "BOP"):
            return tok.value + (self.interval(tok.interval) if tok.interval else "")
        if kind == "ID":
            return self.name(tok.value)
        if kind == "NUM":
            return number(tok.value)
        if kind == "BOOL":
            return "true" if tok.value else "false"
        if kind == "REL":
            return tok.value
        if kind == "DEF":
            if tok.value != ":=":
                raise Unreadable(f"definition symbol {tok.value}")
            return ":="
        if kind in ("LP", "RP", "COMMA"):
            return tok.value
        if kind == "STAR":
            return "*"
        return SIMPLE_TEXT[kind]

    def tokens(self, tokens: list[Tok]) -> str:
        """The tokens joined: spaces between them, except inside brackets, before , . : ) and around ^."""
        out, previous, open_abs = "", None, False
        tight_brackets = self._interval_like(tokens)
        for k, tok in enumerate(tokens):
            text = self.text(tok)
            kind = tok.kind
            space = previous is not None
            if previous is not None:
                pk = previous.kind
                if pk == "LP" or kind in ("RP", "COMMA", "PUNCT", "COLON", "CARET") or pk in ("CARET", "NOT"):
                    space = False
                if pk == "MINUS" and (k < 2 or tokens[k - 2].kind in OPERATOR_KINDS):
                    space = False  # a sign: -3, x < -3
                if pk == "ABS" and open_abs:
                    space = False
                if kind == "ABS" and open_abs:
                    space = False
                if pk == "COMMA" and k - 1 in tight_brackets:
                    space = False
                if kind == "ID" and tok.value == "ZZpercent":
                    space = False
            if kind == "ABS":
                open_abs = not open_abs
            out += (" " if space else "") + text
            previous = tok
        return out

    @staticmethod
    def _interval_like(tokens: list[Tok]) -> set[int]:
        """The commas of [a,b] and (a,b) with only numbers and names inside: written without a space, as in G[0,5]."""
        commas = set()
        for start, tok in enumerate(tokens):
            if tok.kind != "LP" or tok.value not in "[(":
                continue
            inside = []
            for end in range(start + 1, len(tokens)):
                if tokens[end].kind == "RP":
                    break
                inside.append(end)
            else:
                continue
            kinds = [tokens[i].kind for i in inside]
            if kinds.count("COMMA") == 1 and set(kinds) <= {"NUM", "ID", "MINUS", "PLUS", "COMMA", "INF"}:
                commas |= {i for i in inside if tokens[i].kind == "COMMA"}
        return commas


def math_text(span: str, macros: dict[str, list[Macro]], writer: Writer, mode: str) -> str:
    """A math span (without its $) written as text, or Unreadable."""
    for symbol, word in SPAN_SYMBOLS.items():
        span = span.replace(symbol, f" {word} ")
    span = UNICODE_NAME.sub(lambda m: f"\\{UNICODE_GREEK[m[1]]}" + (f"_{{{m[2].translate(SUBSCRIPT_DIGITS)}}}"
                                                                     if m[2] else "") + " ", span)
    try:
        tokens = lex(expand(tokenize(span), macros, PROTECTED_COMMANDS, Trace(mode)), Trace(mode))
    except Rejected as rejected:
        raise Unreadable(f"{rejected.rule}: {rejected.detail}" if rejected.detail else rejected.rule)
    return writer.tokens(tokens)


def unicode_name(letter: str, digits: str, formula_names: set[str]) -> str:
    """φ1 -> phi_1, or varphi_1 when the formula has a name written with varphi and none with phi."""
    name = UNICODE_GREEK[letter]
    variant = VARIANTS.get(name)
    bases = {n.split("_")[0] for n in formula_names}
    if variant and variant in bases and name not in bases:
        name = variant
    digits = digits.translate(SUBSCRIPT_DIGITS)
    return f"{name}_{digits}" if digits else name


def normalize_description(text: str, *, macros: dict[str, list[Macro]], formula_names: list[str] | set[str],
                          mode: str = "faithful") -> Description:
    """The description written as plain text with the symbols of its formula (see the module)."""
    formula_names = set(formula_names)
    writer = Writer(formula_names)
    result = Description("")
    known = KNOWN_COMMANDS | set(macros)
    math_commands = ({f"\\{g}" for g in GREEK} | set(OPERATORS) | set(CONNECTIVES) | set(RELATIONS) | set(ACCENTS)
                     | MATH_FONTS | MATH_WRAPPERS | {"\\in", "\\infty", "\\top", "\\bot"} | set(macros))

    def convert(span: str, written: str) -> str:
        try:
            return math_text(span, macros, writer, mode)
        except Unreadable as unreadable:
            result.unreadable.append({"span": written, "reason": str(unreadable)})
            return written

    def plain(part: str) -> str:
        """Text outside $...$."""
        result.references += [m[0] for m in REFERENCE.finditer(part)]
        refs = []
        part = REFERENCE.sub(lambda m: refs.append(m[0]) or f"\x00{len(refs) - 1}\x00", part)
        previous = None
        while previous != part:
            previous, part = part, TEXT_WRAPPERS.sub(lambda m: m[2], part)
        for symbol, replacement in TEXT_SYMBOLS:
            part = part.replace(symbol, replacement)
        for command, replacement in TEXT_COMMANDS.items():
            part = re.sub(re.escape(command) + r"(?![A-Za-z])\s*", replacement, part)

        def bare(m):
            command = LATEX_COMMAND.match(m[0])[0]
            if command in math_commands:
                return convert(m[0], m[0])
            if command not in known:
                result.latex_left.append(command)
            return m[0]
        part = BARE_MATH.sub(bare, part)

        def greek(m):
            name = unicode_name(m[1], m[2], formula_names)
            writer.names.append(name)
            return name
        part = UNICODE_NAME.sub(greek, part)
        for symbol, replacement in UNICODE_SYMBOLS.items():
            part = part.replace(symbol, replacement)
        return re.sub("\x00(\\d+)\x00", lambda m: refs[int(m[1])], part)

    if len(DOLLAR.findall(text)) % 2:
        first = DOLLAR.search(text).start()
        if first > 0 and not re.search(r"\s", text[:first]):
            text = "$" + text  # cut inside math by the extraction: "\varphi_2$ requires ..."
        elif len(DOLLAR.findall(text)) > 1:
            result.unreadable.append({"span": "", "reason": "an odd number of $"})
    pieces, end = [], 0
    for m in MATH_SPAN.finditer(text):
        pieces.append(plain(text[end:m.start()]))
        span = next(g for g in m.groups() if g is not None)
        pieces.append(convert(span, m[0]))
        end = m.end()
    pieces.append(plain(text[end:]))
    result.normalized = re.sub(r"[ \t]{2,}", " ", "".join(pieces)).strip()
    result.names_not_in_formula = sorted(set(writer.names) - formula_names)
    return result
