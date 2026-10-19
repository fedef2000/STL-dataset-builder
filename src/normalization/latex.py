"""
The LaTeX side of the normalization: a formula cut into TeX tokens, the macros a paper defines (\\newcommand, \\def,
...) read from its sources, and their expansion in a formula.

A token is a string: a command ("\\Box", "\\,", "\\{"), a single character, or " " for a run of spaces.
"""
import re
from dataclasses import dataclass
from pathlib import Path

from src.analysis.estimator import MACRO_SOURCE_EXTENSIONS, find_document_files, strip_latex_comments
from src.normalization.rules import Rejected, Trace

# Characters some formulas (mostly from PDFs) have instead of the LaTeX commands
UNICODE_COMMANDS = {
    "□": "\\Box", "◇": "\\Diamond", "¬": "\\neg", "∧": "\\wedge", "∨": "\\vee", "→": "\\rightarrow",
    "⇒": "\\Rightarrow", "↔": "\\leftrightarrow", "⇔": "\\Leftrightarrow", "≤": "\\leq", "≥": "\\geq", "≠": "\\neq",
    "−": "-",
}
MAX_EXPANSION_ROUNDS = 10
MAX_TOKENS = 20000


def tokenize(text: str) -> list[str]:
    tokens, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == "\\":
            j = i + 1
            while j < n and text[j].isascii() and text[j].isalpha():
                j += 1
            if j == i + 1:
                j = min(i + 2, n)  # a command of one symbol: \, \{ \| ...
            tokens.append(text[i:j])
            i = j
        elif c.isspace():
            if not tokens or tokens[-1] != " ":
                tokens.append(" ")
            i += 1
        else:
            tokens.append(UNICODE_COMMANDS.get(c, c))
            i += 1
    return tokens


def group_end(tokens: list[str], start: int, opening: str = "{", closing: str = "}") -> int:
    """The index of the token that closes the group opened at `start`, or -1."""
    depth = 0
    for i in range(start, len(tokens)):
        if tokens[i] == opening:
            depth += 1
        elif tokens[i] == closing:
            depth -= 1
            if depth == 0:
                return i
    return -1


def skip_spaces(tokens: list[str], i: int) -> int:
    while i < len(tokens) and tokens[i] == " ":
        i += 1
    return i


def argument(tokens: list[str], i: int) -> tuple[list[str], int]:
    """The argument of a command starting at `i` (a group without its braces, or one token) and the index after it."""
    i = skip_spaces(tokens, i)
    if i >= len(tokens):
        return [], i
    if tokens[i] == "{":
        end = group_end(tokens, i)
        if end < 0:
            return tokens[i + 1:], len(tokens)
        return tokens[i + 1:end], end + 1
    return [tokens[i]], i + 1


# ---------------------------------------------------------------- the macros of a paper

@dataclass
class Macro:
    arguments: int
    default: list[str] | None  # the default of an optional first argument (\newcommand{\x}[2][d]{...})
    body: list[str]
    fallback: bool = False  # from the table of operator names, not from the paper (see normalize.with_fallback)

    def key(self) -> str:
        return f"{self.arguments}|{''.join(self.default or [])}|{''.join(t for t in self.body if t != ' ')}"


DEFINITION_PATTERN = re.compile(
    r"\\(?:newcommand|renewcommand|providecommand|DeclareRobustCommand|DeclareMathOperator)\*?(?![a-zA-Z])"
    r"|\\[gex]?def(?![a-zA-Z])|\\let(?![a-zA-Z])")
DEFINITION_WINDOW = 3000


def _definition(tokens: list[str]) -> tuple[str, Macro] | None:
    """The macro defined by the tokens of a definition (starting with \\newcommand, \\def, ...), or None."""
    command, i = tokens[0], 1
    if i < len(tokens) and tokens[i] == "*":
        i += 1
    if command == "\\let":
        name_tokens, i = argument(tokens, i)
        i = skip_spaces(tokens, i)
        if i < len(tokens) and tokens[i] == "=":
            i += 1
        body, _ = argument(tokens, i)
        if len(name_tokens) == 1 and name_tokens[0].startswith("\\") and len(body) == 1:
            return name_tokens[0], Macro(0, None, body)
        return None
    if command in ("\\def", "\\gdef", "\\edef", "\\xdef"):
        i = skip_spaces(tokens, i)
        if i >= len(tokens) or not tokens[i].startswith("\\"):
            return None
        name, i = tokens[i], i + 1
        # Only plain parameters (#1#2...): a delimited parameter text can't be expanded this simply
        arguments = 0
        while i + 1 < len(tokens) and tokens[i] == "#" and tokens[i + 1] == str(arguments + 1):
            arguments, i = arguments + 1, i + 2
        i = skip_spaces(tokens, i)
        if i >= len(tokens) or tokens[i] != "{":
            return None
        body, _ = argument(tokens, i)
        return name, Macro(arguments, None, body)
    name_tokens, i = argument(tokens, i)
    name_tokens = [t for t in name_tokens if t != " "]
    if len(name_tokens) != 1 or not name_tokens[0].startswith("\\"):
        return None
    arguments, default = 0, None
    if command != "\\DeclareMathOperator":
        j = skip_spaces(tokens, i)
        if j < len(tokens) and tokens[j] == "[":
            end = group_end(tokens, j, "[", "]")
            count = "".join(tokens[j + 1:end]).strip()
            if end < 0 or not count.isdigit():
                return None
            arguments, i = int(count), end + 1
            j = skip_spaces(tokens, i)
            if j < len(tokens) and tokens[j] == "[":
                end = group_end(tokens, j, "[", "]")
                if end < 0:
                    return None
                default, i = tokens[j + 1:end], end + 1
    j = skip_spaces(tokens, i)
    if j >= len(tokens) or tokens[j] != "{" or group_end(tokens, j) < 0:
        return None
    body, _ = argument(tokens, j)
    return name_tokens[0], Macro(arguments, default, body)


def source_macros(text: str) -> dict[str, list[Macro]]:
    """Every definition of each macro in a LaTeX source (comments taken out), in order: it may be defined twice."""
    macros: dict[str, list[Macro]] = {}
    for m in DEFINITION_PATTERN.finditer(text):
        found = _definition(tokenize(text[m.start():m.start() + DEFINITION_WINDOW]))
        if found:
            macros.setdefault(found[0], []).append(found[1])
    return macros


def paper_macros(source_dir: Path) -> dict[str, list[Macro]]:
    """
    The macros of the paper whose LaTeX sources are in `source_dir`, from the same files as step 4 reads: the .tex
    files of the document (not the old drafts an arXiv bundle may carry) and the .sty, .cls and .def files, in path
    order, without their comments and disabled blocks.
    """
    macros: dict[str, list[Macro]] = {}
    if not source_dir.is_dir():
        return macros
    sources = {path: strip_latex_comments(path.read_text(encoding="utf-8", errors="ignore"))
               for path in source_dir.rglob("*") if path.suffix.lower() in MACRO_SOURCE_EXTENSIONS and path.is_file()}
    document = find_document_files({f: code for f, code in sources.items() if f.suffix.lower() == ".tex"}, source_dir)
    for path in sorted(f for f in sources if f in document or f.suffix.lower() != ".tex"):
        for name, definitions in source_macros(sources[path]).items():
            macros.setdefault(name, []).extend(definitions)
    return macros


def expand(tokens: list[str], macros: dict[str, list[Macro]], protected: set[str], trace: Trace) -> list[str]:
    """
    The tokens with the paper's macros replaced by their definitions, repeated until none is left. The commands in
    `protected` (those the lexer knows as standard LaTeX) are never expanded, even if a source (often a bundled
    package) defines them.
    """
    for _ in range(MAX_EXPANSION_ROUNDS):
        out, i, changed = [], 0, False
        while i < len(tokens):
            name = tokens[i]
            definitions = macros.get(name) if name not in protected else None
            if not definitions:
                out.append(name)
                i += 1
                continue
            if len({d.key() for d in definitions}) > 1:
                trace.review("macro_conflict", name)
            macro, i = definitions[-1], i + 1
            args = []
            if macro.default is not None:
                j = skip_spaces(tokens, i)
                if j < len(tokens) and tokens[j] == "[":
                    end = group_end(tokens, j, "[", "]")
                    end = end if end >= 0 else len(tokens)
                    args.append(tokens[j + 1:end])
                    i = end + 1
                else:
                    args.append(macro.default)
            while len(args) < macro.arguments:
                arg, i = argument(tokens, i)
                args.append(arg)
            body, k = [], 0
            while k < len(macro.body):
                t = macro.body[k]
                if t == "#" and k + 1 < len(macro.body) and macro.body[k + 1].isdigit():
                    n = int(macro.body[k + 1])
                    body.extend(args[n - 1] if 0 < n <= len(args) else [])
                    k += 2
                else:
                    body.append(t)
                    k += 1
            # A group, so that the definition stays one unit (as TeX reads it, \x_1 with \x = ab is not a_b1)
            out += ["{"] + body + ["}"]
            trace.fire("fallback_operator_table" if macro.fallback else "expand_paper_macros")
            changed = True
        tokens = out
        if len(tokens) > MAX_TOKENS:
            raise Rejected("macro_loop", "the expansion grows without end")
        if not changed:
            return tokens
    if any(t in macros and t not in protected for t in tokens):
        raise Rejected("macro_loop", next(t for t in tokens if t in macros and t not in protected))
    return tokens
