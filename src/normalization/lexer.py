"""
The lexer of the normalization: the TeX tokens of a formula (macros expanded) turned into STL tokens: temporal
operators with their intervals, connectives, comparisons, numbers, names, parentheses. The token rules of stage 1 and
2 (docs/normalization_rules.md) fire here; what can't be represented is rejected here, with its rule.
"""
import re
from dataclasses import dataclass, field
from fractions import Fraction

from src.normalization.latex import argument, group_end, skip_spaces
from src.normalization.rules import Rejected, Trace


@dataclass
class Interval:
    """A time interval as written: its bounds as STL tokens (parsed into expressions by the parser)."""
    lo: list
    hi: list
    lo_open: bool = False
    hi_open: bool = False


@dataclass
class Tok:
    """
    An STL token. kind: OP (G, F, X), BOP (U, R), NOT, AND, OR, IMP, IFF, REL (<, <=, >, >=, =, ==, !=), DEF (:=, \\equiv,
    ...), COLON, COMMA (, ;), PUNCT (.), PLUS, MINUS, SLASH, LP, RP (value: the bracket), ABS, NUM (a Fraction), ID (a
    name), BOOL, IN, INF.
    """
    kind: str
    value: object = None
    interval: Interval | None = None
    candidate: bool = False  # an ID that is a bare G, F, X, U or R: an operator if an interval follows
    spaced: bool = False     # preceded by a space in the source

    def __repr__(self):
        return f"{self.kind}({self.value!r})" if self.value is not None else self.kind

    def text(self) -> str:
        """The token as a reader would write it (for the messages of the report)."""
        if self.kind in ("OP", "BOP"):
            return self.value
        if self.kind == "NUM":
            v = self.value
            return str(v.numerator) if v.denominator == 1 else str(float(v))
        if self.kind == "BOOL":
            return "true" if self.value else "false"
        fixed = {"NOT": "!", "AND": "&&", "OR": "||", "IMP": "->", "IFF": "<->", "COLON": ":", "PLUS": "+",
                 "MINUS": "-", "SLASH": "/", "ABS": "|", "IN": "\\in", "INF": "\\infty"}
        return fixed.get(self.kind, str(self.value))


GREEK = set("""alpha beta gamma delta epsilon varepsilon zeta eta theta vartheta iota kappa lambda mu nu xi pi varpi
rho varrho sigma varsigma tau upsilon phi varphi chi psi omega Gamma Delta Theta Lambda Xi Pi Sigma Upsilon Phi Psi
Omega""".split())

# The brief's table (plus \diamondsuit): the commands of the temporal operators
OPERATORS = {"\\Box": ("OP", "G"), "\\square": ("OP", "G"), "\\always": ("OP", "G"),
             "\\Diamond": ("OP", "F"), "\\lozenge": ("OP", "F"), "\\diamondsuit": ("OP", "F"),
             "\\eventually": ("OP", "F"), "\\until": ("BOP", "U"), "\\bigcirc": ("OP", "X")}
# Commands of the brief's table that are not LaTeX's own: a paper's definition of them wins
PAPER_OVERRIDABLE = {"\\always", "\\eventually", "\\until"}
OPERATOR_LETTERS = {"G", "F", "X", "U", "R"}
CONNECTIVES = {"\\neg": "NOT", "\\lnot": "NOT", "\\wedge": "AND", "\\land": "AND", "\\vee": "OR", "\\lor": "OR",
               "\\rightarrow": "IMP", "\\Rightarrow": "IMP", "\\implies": "IMP", "\\to": "IMP",
               "\\leftrightarrow": "IFF", "\\Leftrightarrow": "IFF", "\\iff": "IFF"}
RELATIONS = {"\\leq": "<=", "\\le": "<=", "\\geq": ">=", "\\ge": ">=", "\\neq": "!=", "\\ne": "!="}
DEFINITIONS = {"\\equiv", "\\triangleq", "\\coloneqq", "\\coloneq", "\\doteq"}

# Removed: spacing, sizing, alignment
LAYOUT = {"\\left", "\\right", "\\big", "\\Big", "\\bigg", "\\Bigg", "\\bigl", "\\bigr", "\\Bigl", "\\Bigr",
          "\\biggl", "\\biggr", "\\Biggl", "\\Biggr", "\\middle", "\\,", "\\;", "\\:", "\\!", "\\ ", "\\>", "\\quad",
          "\\qquad", "\\limits", "\\nolimits", "\\displaystyle", "\\textstyle", "\\scriptstyle", "\\nonumber",
          "\\notag", "\\allowbreak", "\\xspace", "\\relax", "\\nobreak", "\\strut", "\\mathstrut", "\\\\", "\\cr",
          "\\rm", "\\sf", "\\bf", "\\it", "\\tt", "\\cal", "\\normalfont"}
LAYOUT_WITH_ARGUMENT = {"\\phantom", "\\hphantom", "\\vphantom", "\\label", "\\hspace", "\\vspace", "\\color"}
LAYOUT_WITH_DIMENSION = {"\\kern", "\\mkern", "\\hskip", "\\mskip"}
DIMENSION_PATTERN = re.compile(r"[-+]?(\d+\.?\d*|\.\d+)(em|ex|pt|mu|mm|cm|in|bp|sp)")
# Replaced by their content, read as math
MATH_FONTS = {"\\mathit", "\\mathrm", "\\mathbf", "\\mathsf", "\\mathtt", "\\mathcal", "\\mathnormal", "\\bm",
              "\\boldsymbol", "\\pmb"}
MATH_WRAPPERS = {"\\ensuremath", "\\mathop", "\\mathbin", "\\mathrel", "\\mathord", "\\operatorname"}
# Replaced by their content, read as text
TEXT_FONTS = {"\\text", "\\textit", "\\textbf", "\\texttt", "\\textrm", "\\textsf", "\\textup", "\\textnormal",
              "\\textsl", "\\emph", "\\mbox", "\\hbox"}
ACCENTS = {"\\dot": "dot", "\\bar": "bar", "\\hat": "hat", "\\tilde": "tilde"}

REJECTED = {
    **dict.fromkeys(["\\cdot", "\\times", "\\ast"], "multiplication"),
    **dict.fromkeys(["\\sin", "\\cos", "\\tan", "\\exp", "\\log", "\\ln", "\\max", "\\min", "\\sup", "\\inf",
                     "\\sqrt", "\\lVert", "\\rVert", "\\|", "\\det", "\\arg", "\\lim", "\\Vert"], "function"),
    **dict.fromkeys(["\\bigwedge", "\\bigvee", "\\sum", "\\prod", "\\ldots", "\\dots", "\\cdots", "\\vdots",
                     "\\bigcup", "\\bigcap"], "indexed_operator"),
    **dict.fromkeys(["\\forall", "\\exists", "\\nexists"], "quantifier"),
    **dict.fromkeys(["\\models", "\\vDash", "\\vdash", "\\Vdash"], "semantics_definition"),
    "\\mid": "grammar_definition",
    **dict.fromkeys(["\\widetilde", "\\boxplus", "\\sqcup", "\\oplus", "\\boxminus", "\\diamondminus"],
                    "nonstandard_operator"),
}
TEXT_CONNECTIVE_PATTERN = re.compile(
    r"\s*[,;:]?\s*(where|and|or|if|iff|for|with|s\.t\.|such that|otherwise|when|then|i\.e\.|e\.g\.)\b", re.I)
WORD_TOKEN = re.compile(r"[A-Za-z0-9]")

# Every command the lexer knows: never expanded from a paper's definitions (except PAPER_OVERRIDABLE)
KNOWN_COMMANDS = ({f"\\{g}" for g in GREEK} | set(OPERATORS) | set(CONNECTIVES) | set(RELATIONS) | DEFINITIONS
                  | LAYOUT | LAYOUT_WITH_ARGUMENT | LAYOUT_WITH_DIMENSION | MATH_FONTS | MATH_WRAPPERS | TEXT_FONTS
                  | set(ACCENTS) | set(REJECTED)
                  | {"\\top", "\\bot", "\\in", "\\infty", "\\frac", "\\prime", "\\lvert", "\\rvert", "\\vert", "\\{",
                     "\\}", "\\_", "\\textcolor", "\\mathbb", "\\mathscr", "\\mathfrak"})
PROTECTED_COMMANDS = KNOWN_COMMANDS - PAPER_OVERRIDABLE


def name_part(tokens: list[str]) -> str | None:
    """The text a subscript or superscript adds to a name (x_{max} -> "max", x_{i,j} -> "i_j"), or None if it isn't one."""
    parts, i = [], 0
    while i < len(tokens):
        t = tokens[i]
        if t in (" ", "{", "}") or t in MATH_FONTS or t in TEXT_FONTS:
            pass
        elif len(t) == 1 and t.isascii() and t.isalnum():
            parts.append(t)
        elif t in ("\\_", "_", ",", "'"):
            parts.append("_" if t != "'" else "_prime_")
        elif t == "\\prime":
            parts.append("_prime_")
        elif t.startswith("\\") and t[1:] in GREEK:
            parts.append(f"_{t[1:]}_")
        else:
            return None
        i += 1
    text = re.sub(r"_+", "_", "".join(parts)).strip("_")
    return text or None


class Lexer:
    def __init__(self, trace: Trace):
        self.trace = trace

    def read(self, tokens: list[str]) -> list[Tok]:
        out: list[Tok] = []
        i = 0
        while i < len(tokens):
            i = self._step(tokens, i, out)
        return out

    # ------------------------------------------------------------ one construct

    def _step(self, tokens: list[str], i: int, out: list[Tok]) -> int:
        t = tokens[i]
        spaced = i > 0 and tokens[i - 1] == " "
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if t in (" ", "$", "~"):
            return i + 1
        if t == "{":
            end = group_end(tokens, i)
            if end < 0:
                raise Rejected("parse_error", "unbalanced {")
            inner = self.read(tokens[i + 1:end])
            if inner:
                inner[0].spaced = inner[0].spaced or spaced
            out += inner
            return end + 1
        if t == "}":
            raise Rejected("parse_error", "unbalanced }")
        if (t.isascii() and t.isalpha()) and len(t) == 1:
            return self._word(tokens, i, out, spaced)
        if t.isdigit() or (t == "." and nxt is not None and nxt.isdigit()):
            return self._number(tokens, i, out, spaced)
        if t.startswith("\\") and len(t) > 1:
            return self._command(tokens, i, out, spaced)
        return self._symbol(tokens, i, out, spaced)

    def _emit(self, out: list[Tok], tok: Tok, spaced: bool):
        tok.spaced = spaced
        out.append(tok)

    def _word(self, tokens, i, out, spaced) -> int:
        """A name: letters, then letters, digits, \\_ (consecutive letters are one name, as authors mean them)."""
        j, word = i, ""
        while j < len(tokens) and (WORD_TOKEN.fullmatch(tokens[j]) or
                                   (tokens[j] == "\\_" and j + 1 < len(tokens) and WORD_TOKEN.fullmatch(tokens[j + 1]))):
            word += "_" if tokens[j] == "\\_" else tokens[j]
            j += 1
        self._name(word, out, spaced)
        return j

    def _name(self, word: str, out, spaced):
        if word.lower() in ("true", "false"):
            if word not in ("true", "false"):
                self.trace.fire("bool_constants")
            self._emit(out, Tok("BOOL", word.lower() == "true"), spaced)
        else:
            self._emit(out, Tok("ID", word, candidate=word in OPERATOR_LETTERS), spaced)

    def _number(self, tokens, i, out, spaced) -> int:
        j, text = i, ""
        while j < len(tokens) and tokens[j].isdigit():
            text, j = text + tokens[j], j + 1
        if j < len(tokens) and tokens[j] == ".":
            if j + 1 < len(tokens) and tokens[j + 1].isdigit():
                text, j = text + ".", j + 1
                while j < len(tokens) and tokens[j].isdigit():
                    text, j = text + tokens[j], j + 1
            elif text and (j + 1 >= len(tokens) or tokens[j + 1] in (" ", ")", "]", "}", ",")):
                j += 1  # 5. -> 5
                self.trace.fire("number_forms")
        if text.startswith("."):
            self.trace.fire("number_forms")
        # Scientific notation: 1e-3, 2.5E4
        if j < len(tokens) and tokens[j] in ("e", "E"):
            k = j + 1
            sign = ""
            if k < len(tokens) and tokens[k] in ("+", "-"):
                sign, k = tokens[k], k + 1
            if k < len(tokens) and tokens[k].isdigit():
                exponent = ""
                while k < len(tokens) and tokens[k].isdigit():
                    exponent, k = exponent + tokens[k], k + 1
                text, j = f"{text}e{sign}{exponent}", k
                self.trace.fire("number_forms")
        self._emit(out, Tok("NUM", Fraction(text)), spaced)
        # A number with a letter, a command or a parenthesis right after it: a product (2x, 2\pi, 2(x+y))
        if j < len(tokens) and (WORD_TOKEN.fullmatch(tokens[j]) or tokens[j] == "(" or
                                (tokens[j].startswith("\\") and tokens[j][1:] in GREEK)):
            raise Rejected("multiplication", f"{text}{tokens[j]}")
        return j

    def _command(self, tokens, i, out, spaced) -> int:
        t = tokens[i]
        name = t[1:]
        if t in LAYOUT:
            self.trace.fire("strip_layout")
            j = i + 1
            if t in ("\\left", "\\right", "\\middle") and j < len(tokens) and tokens[j] == ".":
                j += 1
            return j
        if t in LAYOUT_WITH_ARGUMENT:
            self.trace.fire("strip_layout")
            return argument(tokens, i + 1)[1]
        if t in LAYOUT_WITH_DIMENSION:
            self.trace.fire("strip_layout")
            j = skip_spaces(tokens, i + 1)
            rest = "".join(tokens[j:j + 12])
            m = DIMENSION_PATTERN.match(rest)
            if m:
                consumed = 0
                while consumed < m.end():
                    consumed += len(tokens[j])
                    j += 1
            return j
        if t == "\\textcolor":
            self.trace.fire("strip_layout")
            _, j = argument(tokens, i + 1)
            content, j = argument(tokens, j)
            self._splice(self.read(content), out, spaced)
            return j
        if t in MATH_FONTS or t in MATH_WRAPPERS:
            self.trace.fire("unwrap_font" if t in MATH_FONTS else "strip_layout")
            content, j = argument(tokens, i + 1)
            self._splice(self.read(content), out, spaced)
            return j
        if t in TEXT_FONTS:
            content, j = argument(tokens, i + 1)
            self._text(content, out, spaced)
            return j
        if name in GREEK:
            self.trace.fire("greek_names")
            self._emit(out, Tok("ID", name), spaced)
            return i + 1
        if t in OPERATORS:
            self.trace.fire("latex_ops")
            kind, value = OPERATORS[t]
            self._emit(out, Tok(kind, value), spaced)
            return i + 1
        if t in CONNECTIVES:
            self.trace.fire("latex_ops")
            self._emit(out, Tok(CONNECTIVES[t]), spaced)
            return i + 1
        if t in RELATIONS:
            self.trace.fire("latex_ops")
            self._emit(out, Tok("REL", RELATIONS[t]), spaced)
            return i + 1
        if t in DEFINITIONS:
            self._emit(out, Tok("DEF", t), spaced)
            return i + 1
        if t in ("\\top", "\\bot"):
            self.trace.fire("bool_constants")
            self._emit(out, Tok("BOOL", t == "\\top"), spaced)
            return i + 1
        if t in ("\\lvert", "\\rvert", "\\vert"):
            self.trace.fire("latex_ops")
            self._emit(out, Tok("ABS"), spaced)
            return i + 1
        if t in ("\\{", "\\}"):
            self._emit(out, Tok("LP" if t == "\\{" else "RP", t[1]), spaced)
            return i + 1
        if t == "\\in":
            self._emit(out, Tok("IN"), spaced)
            return i + 1
        if t == "\\infty":
            self._emit(out, Tok("INF"), spaced)
            return i + 1
        if t == "\\frac":
            numerator, j = argument(tokens, i + 1)
            denominator, j = argument(tokens, j)
            n, d = ("".join(x).replace(" ", "") for x in (numerator, denominator))
            if not (re.fullmatch(r"-?\d+", n) and re.fullmatch(r"-?\d+", d)) or int(d) == 0:
                raise Rejected("division", f"\\frac{{{n}}}{{{d}}}")
            self.trace.fire("frac_numbers")
            self._emit(out, Tok("NUM", Fraction(int(n), int(d))), spaced)
            return j
        if t in ACCENTS:
            content, j = argument(tokens, i + 1)
            inner = self.read(content)
            if len(inner) != 1 or inner[0].kind != "ID":
                raise Rejected("nonstandard_operator", f"{t}{{{''.join(content)}}}")
            self.trace.fire("accent_names")
            self._emit(out, Tok("ID", f"{inner[0].value}_{ACCENTS[t]}"), spaced)
            return j
        if t == "\\_":
            raise Rejected("parse_error", "\\_ outside a name")
        if t in REJECTED:
            raise Rejected(REJECTED[t], t)
        raise Rejected("unknown_command", t)

    def _splice(self, inner: list[Tok], out: list[Tok], spaced: bool):
        if inner:
            inner[0].spaced = inner[0].spaced or spaced
        out += inner

    def _text(self, content: list[str], out, spaced):
        """The content of \\text{...} and the like: one name (spaces become _), or else read as math."""
        raw = "".join(content)
        if TEXT_CONNECTIVE_PATTERN.match(raw):
            raise Rejected("several_formulas", f"text \"{raw.strip()}\"")
        words = raw.replace("\\_", "_").split()
        if not words:
            return
        if all(re.fullmatch(r"[A-Za-z0-9_]+", w) for w in words) and words[0][0].isalpha():
            self.trace.fire("unwrap_font")
            if len(words) > 1:
                self.trace.fire("multiword_names")
            self._name("_".join(words), out, spaced)
            return
        self.trace.fire("unwrap_font")
        self._splice(self.read([t for t in content if t != "$"]), out, spaced)

    def _symbol(self, tokens, i, out, spaced) -> int:
        t = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        prev = out[-1] if out else None
        two = t + (nxt or "")
        if t in ("_", "^"):
            return self._script(tokens, i, out)
        if t == "'":
            if prev is None or prev.kind != "ID":
                raise Rejected("parse_error", "' after no name")
            self.trace.fire("accent_names")
            prev.value, prev.candidate = f"{prev.value}_prime", False
            return i + 1
        if t == "(" or t == "[":
            if prev is not None and prev.kind == "ID" and not spaced:
                if not prev.candidate:
                    return self._after_name(tokens, i, prev)
                end = group_end(tokens, i, t, ")" if t == "(" else "]")
                if end > 0 and "".join(tokens[i + 1:end]).replace(" ", "") == "t":
                    self.trace.fire("current_time_index")  # X(t): the signal X, not the next operator
                    prev.candidate = False
                    return end + 1
            if t == "[" and prev is not None and (prev.kind in ("OP", "BOP") or prev.candidate) and prev.interval is None:
                end = self._interval_end(tokens, i)
                if end > 0:
                    self._attach_interval(prev, self._interval(tokens[i + 1:end], "[", tokens[end]), plain=True)
                    return end + 1
            self._emit(out, Tok("LP", t), spaced)
            return i + 1
        if t in (")", "]"):
            self._emit(out, Tok("RP", t), spaced)
            return i + 1
        if t == "|":
            if nxt == "|":
                self._emit(out, Tok("OR"), spaced)
                return i + 2
            self._emit(out, Tok("ABS"), spaced)
            return i + 1
        if t == "&":
            if nxt == "&":
                self._emit(out, Tok("AND"), spaced)
                return i + 2
            self.trace.fire("strip_layout")
            return i + 1
        if t == "!":
            if nxt == "=":
                self._emit(out, Tok("REL", "!="), spaced)
                return i + 2
            self._emit(out, Tok("NOT"), spaced)
            return i + 1
        if t == "<":
            if two == "<-" and i + 2 < len(tokens) and tokens[i + 2] == ">":
                self._emit(out, Tok("IFF"), spaced)
                return i + 3
            if nxt == "=":
                self._emit(out, Tok("REL", "<="), spaced)
                return i + 2
            self._emit(out, Tok("REL", "<"), spaced)
            return i + 1
        if t == ">":
            if nxt == "=":
                self._emit(out, Tok("REL", ">="), spaced)
                return i + 2
            self._emit(out, Tok("REL", ">"), spaced)
            return i + 1
        if t == "=":
            if nxt == "=":
                self._emit(out, Tok("REL", "=="), spaced)
                return i + 2
            self._emit(out, Tok("REL", "="), spaced)
            return i + 1
        if t == "-":
            if nxt == ">":
                self._emit(out, Tok("IMP"), spaced)
                return i + 2
            self._emit(out, Tok("MINUS"), spaced)
            return i + 1
        if t == ":":
            if nxt == ":" and i + 2 < len(tokens) and tokens[i + 2] == "=":
                raise Rejected("grammar_definition", "::=")
            if nxt == "=":
                self._emit(out, Tok("DEF", ":="), spaced)
                return i + 2
            self._emit(out, Tok("COLON"), spaced)
            return i + 1
        simple = {"+": "PLUS", "/": "SLASH", ",": "COMMA", ";": "COMMA", ".": "PUNCT"}
        if t in simple:
            self._emit(out, Tok(simple[t], t), spaced)
            return i + 1
        if t == "*":
            raise Rejected("multiplication", "*")
        raise Rejected("parse_error", f"character {t!r}")

    # ------------------------------------------------------------ names followed by ( or [

    def _after_name(self, tokens, i, prev: Tok) -> int:
        """x(t), x[t] -> x; x[0] -> x_0 (needs review); anything else in ( ) or [ ] after a name is a function."""
        closing = ")" if tokens[i] == "(" else "]"
        end = group_end(tokens, i, tokens[i], closing)
        if end < 0:
            raise Rejected("parse_error", f"unbalanced {tokens[i]}")
        inside = "".join(tokens[i + 1:end]).replace(" ", "")
        if inside == "t":
            self.trace.fire("current_time_index")
            return end + 1
        if tokens[i] == "[" and inside.isdigit():
            self.trace.fire("indexed_signal")
            prev.value = f"{prev.value}_{inside}"
            return end + 1
        raise Rejected("function", f"{prev.value}{tokens[i]}{inside}{closing}")

    # ------------------------------------------------------------ subscripts, superscripts, intervals

    def _script(self, tokens, i, out) -> int:
        mark = tokens[i]
        content, j = argument(tokens, i + 1)
        if not [t for t in content if t not in (" ", "{", "}")]:
            self.trace.fire("strip_layout")  # x^{}: an empty script, as a macro with an optional argument leaves it
            return j
        prev = out[-1] if out else None
        if prev is None:
            raise Rejected("parse_error", f"{mark} after nothing")
        if prev.kind in ("OP", "BOP") or prev.candidate:
            interval = self._script_interval(content)
            if interval is not None:
                if prev.interval is not None:
                    raise Rejected("nonstandard_operator", "two intervals on one operator")
                self._attach_interval(prev, interval)
                return j
            if prev.kind in ("OP", "BOP"):
                raise Rejected("nonstandard_operator", f"{prev.value}{mark}{{{''.join(content)}}}")
        if prev.kind == "ID":
            part = name_part(content)
            if mark == "_":
                if part is None:
                    raise Rejected("parse_error", f"subscript {''.join(content)}")
                if part == "t":
                    self.trace.fire("current_time_index")
                    return j
                self.trace.fire("index_names")
                prev.value, prev.candidate = f"{prev.value}_{part}", False
                return j
            if part == "prime":
                self.trace.fire("accent_names")
                prev.value, prev.candidate = f"{prev.value}_prime", False
                return j
            if part is None or part.isdigit():
                raise Rejected("power", f"{prev.value}^{''.join(content)}")
            self.trace.fire("index_names")
            prev.value, prev.candidate = f"{prev.value}_{part}", False
            return j
        if mark == "^":
            raise Rejected("power", f"^{''.join(content)}")
        raise Rejected("parse_error", f"subscript after {prev.text()}")

    def _attach_interval(self, op: Tok, interval: Interval, plain: bool = False):
        if op.candidate:
            if op.value == "X":
                raise Rejected("nonstandard_operator", "X with an interval")
            op.kind = "BOP" if op.value in ("U", "R") else "OP"
            op.candidate = False
        op.interval = interval
        if not plain:
            self.trace.fire("subscript_interval")

    def _interval_end(self, tokens, i) -> int:
        """The index of the ] or ) closing a plain interval [a,b] after an operator, or -1 if it isn't one."""
        depth = 0
        for k in range(i + 1, len(tokens)):
            if tokens[k] == "{":
                depth += 1
            elif tokens[k] == "}":
                depth -= 1
            elif depth == 0 and tokens[k] in ("]", ")"):
                try:
                    inner = Lexer(Trace()).read(tokens[i + 1:k])
                except Rejected:
                    return -1
                commas = sum(1 for x in inner if x.kind == "COMMA")
                if commas == 1 and all(x.kind in ("NUM", "ID", "PLUS", "MINUS", "COMMA", "INF") for x in inner):
                    return k
                return -1
            elif depth == 0 and tokens[k] in ("(", "["):
                return -1
        return -1

    def _interval(self, content: list[str], opening: str, closing: str) -> Interval:
        inner = self.read(content)
        comma = next(k for k, x in enumerate(inner) if x.kind == "COMMA")
        return Interval(inner[:comma], inner[comma + 1:], opening == "(", closing == ")")

    def _script_interval(self, content: list[str]) -> Interval | None:
        """The interval a sub- or superscript of an operator gives ([a,b], (a,b], <= c, < c), or None if it isn't one."""
        try:
            return self._script_interval_of(content)
        except Rejected:
            return None  # not an interval (X_{1i}: a name)

    def _script_interval_of(self, content: list[str]) -> Interval | None:
        stripped = [t for t in content if t != " "]
        if not stripped:
            return None
        if stripped[0] in ("[", "(") and stripped[-1] in ("]", ")"):
            inner = self.read(content)
            # The brackets themselves are the first and last tokens
            if len(inner) >= 2 and inner[0].kind == "LP" and inner[-1].kind == "RP":
                body = inner[1:-1]
                depth, commas = 0, []
                for k, x in enumerate(body):
                    depth += x.kind == "LP"
                    depth -= x.kind == "RP"
                    if x.kind == "COMMA" and depth == 0:
                        commas.append(k)
                if len(commas) == 1:
                    c = commas[0]
                    return Interval(body[:c], body[c + 1:], inner[0].value == "(", inner[-1].value == ")")
            return None
        inner = self.read(content)
        if inner and inner[0].kind == "REL" and inner[0].value in ("<", "<=") and len(inner) > 1:
            self.trace.fire("bound_shorthand")
            return Interval([Tok("NUM", Fraction(0))], inner[1:], False, inner[0].value == "<")
        if inner and inner[0].kind == "REL" and inner[0].value in (">", ">="):
            raise Rejected("unbounded_operator", f"_{{{''.join(content)}}}")
        return None


def lex(tokens: list[str], trace: Trace) -> list[Tok]:
    return Lexer(trace).read(tokens)
