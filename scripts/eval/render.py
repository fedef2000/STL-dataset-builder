"""Turns a paper's formula into LaTeX that a plain KaTeX renderer (VS Code's Markdown preview) can display,
by expanding the paper's own macros. Display aid only: the verbatim source stays the reference."""
import re
from pathlib import Path

BS = chr(92)
DEF_PATTERN = re.compile(
    r"\\(?:(?:re)?newcommand|providecommand|DeclareRobustCommand)\*?\s*\{?\s*\\([a-zA-Z]+)\s*\}?\s*(?:\[(\d)\])?\s*(\[[^\]]*\])?\s*(?=\{)"
    r"|\\(DeclareMathOperator)\*?\s*\{?\s*\\([a-zA-Z]+)\s*\}?\s*(?=\{)"
    r"|\\[gex]?def\s*\\([a-zA-Z]+)\s*((?:#\d\s*)*)(?=\{)"
)
# Used when the paper's definition is not on disk (e.g. it lives in a .sty that was not downloaded)
FALLBACK = {
    **{n: r"\square" for n in ("always", "Always", "alw", "glob", "globally", "lglobally", "lalways", "LTLg", "LTLglobally", "Box")},
    **{n: r"\lozenge" for n in ("eventually", "Eventually", "ev", "even", "event", "levent", "leventually", "LTLf", "LTLeventually", "Diamond")},
    **{n: r"\mathbin{\mathcal{U}}" for n in ("until", "Until", "U", "luntil", "LTLu")},
    "G": r"\mathbf{G}", "F": r"\mathbf{F}",
}
CLEANUPS = [
    (r"\\(?:ensuremath|protect|xspace|nonumber|mathsmaller|small|normalsize|allowbreak)(?![a-zA-Z])", ""),
    (r"\\(?:label|vspace|hspace)\*?\{[^{}]*\}", ""),
    (r"\\(?:textsc|mbox|textup|textnormal|textrm)(?![a-zA-Z])", r"\\text"),
    (r"\\hl(?![a-zA-Z])", ""),
    (r"\\rotatebox\[[^\]]*\]\{45\}\{\$\\Box\$\}", r"\\Diamond"),
    (r"\\boxbox(?![a-zA-Z])", r"\\boxed{\\square}"),
    (r"\\defeq(?![a-zA-Z])", ":="),
    (r"\\Vec(?![a-zA-Z])", r"\\vec"),
    (r"\\mathbbm(?![a-zA-Z])", r"\\mathbb"),
    (r"\\coloneqq(?![a-zA-Z])", ":="),
]

def read_group(text, start):
    """Content and end index of the balanced {...} group opening at text[start]."""
    depth, i = 0, start
    while i < len(text) and i < start + 3000:
        ch = text[i]
        if ch == BS:
            i += 2; continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
        i += 1
    return None, start

def paper_macros(folder: Path, strip_comments):
    macros = {}
    for f in folder.rglob("*"):
        if f.suffix.lower() not in (".tex", ".sty", ".cls", ".def") or not f.is_file():
            continue
        t = strip_comments(f.read_text(encoding="utf-8", errors="ignore"))
        for m in DEF_PATTERN.finditer(t):
            body, _ = read_group(t, m.end())
            if body is None:
                continue
            if m.group(1):
                if m.group(3):
                    continue  # optional-argument macros are not expanded
                macros[m.group(1)] = (int(m.group(2) or 0), body)
            elif m.group(4):
                macros[m.group(5)] = (0, r"\operatorname{" + body + "}")
            else:
                macros[m.group(6)] = (len(re.findall(r"#\d", m.group(7) or "")), body)
    return macros

def expand(formula: str, macros: dict):
    """Replaces paper macros by their bodies until nothing changes. Returns (latex, names taken from FALLBACK)."""
    guessed = set()
    table = dict(macros)
    for name, body in FALLBACK.items():
        if name not in table and name not in ("Box", "Diamond"):
            table[name] = (0, body); guessed.add(name)
    used_guess = set()
    text = formula
    for _ in range(12):
        changed = False
        out, i = [], 0
        for m in re.finditer(r"\\([a-zA-Z]+)", text):
            if m.start() < i or m.group(1) not in table:
                continue
            name = m.group(1); nargs, body = table[name]
            j, args = m.end(), []
            ok = True
            for _k in range(nargs):
                while j < len(text) and text[j].isspace():
                    j += 1
                if j < len(text) and text[j] == "{":
                    arg, j2 = read_group(text, j)
                    if arg is None:
                        ok = False; break
                    args.append(arg); j = j2
                elif j < len(text):
                    tok = re.match(r"\\[a-zA-Z]+|\\.|.", text[j:], re.S)
                    args.append(tok.group(0)); j += tok.end()
                else:
                    ok = False; break
            if not ok:
                continue
            rep = body
            for k, a in enumerate(args, 1):
                rep = rep.replace(f"#{k}", a)
            if re.search(r"\\[a-zA-Z]+$", rep) and j < len(text) and text[j].isalpha():
                rep += " "
            out.append(text[i:m.start()]); out.append(rep); i = j
            changed = True
            if name in guessed:
                used_guess.add(name)
        out.append(text[i:])
        text = "".join(out)
        if not changed:
            break
    for pat, rep in CLEANUPS:
        text = re.sub(pat, rep, text)
    if used_guess:
        # a guessed operator written as \glob{[3,50]} takes its interval as an argument: show it as a subscript
        text = re.sub(r"(\\square|\\lozenge)\s*\{\s*\[", r"\1_{[", text)
    # anything still unknown to the renderer is shown by name instead of failing the whole formula
    by_name = set()
    def name_only(m):
        if m.group(1) in KNOWN:
            return m.group(0)
        by_name.add(m.group(1))
        return r"\mathrm{" + m.group(1) + "}"
    text = re.sub(r"\\([a-zA-Z]+)", name_only, text)
    text = re.sub(r"\s+", " ", text).strip()
    if "&" in text or BS * 2 in text:
        text = r"\begin{aligned} " + text + r" \end{aligned}"
    return text, used_guess, by_name

KNOWN = set("""
Big Bigg Box Delta Diamond Gamma Lambda Leftrightarrow Longrightarrow Omega Phi Pi Psi Rightarrow Sigma Theta Vert
aligned alpha approx bar begin beta bf big bigg bigvee bigwedge bm boldsymbol bot boxed cap cdot chi circ cup ddot delta
displaystyle dot dots ell end epsilon equiv eta exists forall frac gamma ge geq hat implies in infty kappa lVert lambda
land langle ldots le left leftrightarrow leq lfloor lnot lor lozenge mathbb mathbf mathbin mathcal mathit mathop mathrm
mathsf mathtt max mid min mu ne neg neq nolimits notin nu omega operatorname overline parallel perp phi pi prime psi
qquad quad rVert rangle rfloor rho right rightarrow sigma sim sqrt square subset sum tau text textbf textit texttt theta
tilde times to top underline varepsilon varphi vec vee vert vphantom wedge xi zeta
""".split())
