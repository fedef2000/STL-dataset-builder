"""
The report of step 6 (report.md), from the manifest lines of one run: counts by status, why formulas are rejected (with
examples), the most frequent unknown commands, the templates and patterns, and for the formulas without a requirement
the selection for stl-nl; for the paired ones the extensions of stl-nl's grammar they use and how their descriptions
were written (description.py).
"""
import collections
import re

from src.normalization.rules import FAITHFUL_RULES, description

def table(rows, header) -> list[str]:
    out = [f"| {' | '.join(header)} |", f"|{'---|' * len(header)}"]
    out += [f"| {' | '.join(str(c) for c in row)} |" for row in rows]
    return out + [""]


def reason_rule(reason: str) -> str:
    return reason.split(":", 1)[0]


EXAMPLE_CHARS = 110
# An example shorter than this is often a fragment (a lone number): taken only if no longer one exists
EXAMPLE_MIN_CHARS = 15


def code(text: str) -> str:
    """Text as inline code in a table cell (| escaped, long text cut)."""
    text = " ".join(text.split())
    if len(text) > EXAMPLE_CHARS:
        text = text[:EXAMPLE_CHARS] + " …"
    return f"`{text}`".replace("|", "\\|")


def cell(text: str) -> str:
    """Plain text in a table cell (| escaped)."""
    return text.replace("|", "\\|")


def shortest(candidates: list[dict], *preferred) -> dict:
    """
    The example among `candidates`: the shortest original of at least EXAMPLE_MIN_CHARS characters among those that
    meet all the `preferred` conditions, else all but the last condition, ..., else among all (the first on a tie, so
    a rerun picks the same).
    """
    for k in range(len(preferred), -1, -1):
        pool = [c for c in candidates if all(p(c) for p in preferred[:k])]
        long_enough = [c for c in pool if len(c["original"]) >= EXAMPLE_MIN_CHARS]
        if long_enough or pool:
            return min(long_enough or pool, key=lambda c: len(c["original"]))


def examples(lines: list[dict], status: str) -> dict[str, dict]:
    """An example per rule of the formulas with `status` (see shortest)."""
    by_rule = collections.defaultdict(list)
    for line in lines:
        if line["status"] == status:
            for rule in {reason_rule(r) for r in line["reasons"]}:
                by_rule[rule].append(line)
    return {rule: shortest(candidates, without_macros) for rule, candidates in by_rule.items()}


def without_macros(line: dict) -> bool:
    return "expand_paper_macros" not in line["rules"]


def macro_mark(line: dict) -> str:
    return " *(macro)*" if "expand_paper_macros" in line["rules"] else ""


def found(line: dict) -> str:
    """What the first rule that rejects the formula found in it (the text after "rule: " in the reason)."""
    reason = line["reasons"][0]
    return reason.split(": ", 1)[1] if ": " in reason else ""


def bare(text: str) -> str:
    return re.sub(r"[\\{}\s]", "", text)


def found_visible(line: dict) -> bool:
    """
    What the rule found can be seen in the formula as the paper writes it. Backslashes, braces and spaces aside: the
    found part is written after the macros are expanded and the names normalized (\\mu^1 is found as mu^1).
    """
    part = bare(found(line))
    return bool(part) and part in bare(line["original"])


EXAMPLES_PER_RULE = 3


def rejected_examples(lines: list[dict], rule: str) -> list[dict]:
    """
    Up to EXAMPLES_PER_RULE formulas rejected first by `rule`, to show its different cases. The formulas are grouped
    by the first word of what the rule found (\\models and \\vDash; subscript, unexpected and character for
    parse_error; rho, x and \\min for function), the largest groups first, and each example comes from another
    paper. In a group the example is the shortest formula without the paper's macros whose found part can be seen in
    it (see shortest). With fewer groups than examples, the other examples come from the rest of the formulas.
    """
    candidates = [l for l in lines if l["status"] == "rejected" and reason_rule(l["reasons"][0]) == rule]
    groups = collections.defaultdict(list)
    for line in candidates:
        first_word = re.match(r"\\?[A-Za-z]+|\S*", found(line)).group()
        groups[first_word].append(line)

    def rank(group):  # the largest group first; on a tie, the one with the clearer and then the shorter example
        best = shortest(group, without_macros, found_visible)
        return -len(group), not without_macros(best), not found_visible(best), len(best["original"])

    chosen, papers = [], set()
    for group in sorted(groups.values(), key=rank) + [candidates]:
        while len(chosen) < EXAMPLES_PER_RULE:
            pool = [l for l in group if l["id"].split(":")[0] not in papers]
            if not pool:
                break
            chosen.append(shortest(pool, without_macros, found_visible))
            papers.add(chosen[-1]["id"].split(":")[0])
            if group is not candidates:
                break  # one example per group, until the groups run out
    return chosen


def why(line: dict) -> str:
    """Why this formula is rejected, in a sentence built from its rule and what the rule found."""
    rule, part = reason_rule(line["reasons"][0]), found(line)
    if rule == "semantics_definition":
        return f"{code(part)} says when a signal satisfies a formula: this defines the meaning of an operator"
    if rule == "grammar_definition":
        if part.startswith("|"):
            return "a `\\|` separates the alternatives of a grammar (it can't be read as an absolute value)"
        return f"{code(part)} introduces the forms a formula can take: a grammar"
    if rule == "operator_definition":
        if part == "an operator on the left of =":
            return "a temporal operator is on the left of =: the formula defines that operator"
        return "the left side of := (or \\equiv) is an expression, not a name: the formula defines it"
    if rule == "several_formulas":
        if part.startswith("text "):
            return f"the word {part[5:]} joins the formula to text or to another formula"
        if part == "a comma at the top level":
            return "a comma at the top level separates two formulas"
        return "a comma inside brackets separates formulas (a set or a tuple)"
    if rule == "connective_at_edge":
        return "it starts or ends with a connective: the rest of the formula is on another row of the paper"
    if rule == "macro_loop":
        return "a macro of the paper keeps expanding without end"
    if rule == "unknown_command":
        return f"{code(part)} isn't defined by the paper and the normalizer doesn't know it"
    if rule == "multiplication":
        if part.endswith(" side by side"):
            return f"{code(part[:-len(' side by side')])}: two terms side by side are a product"
        return f"{code(part)} is a product"
    if rule == "division":
        return f"{code(part)} is a division"
    if rule == "power":
        if part.endswith(" on a Boolean atom"):
            return (f"{code(part[:-len(' on a Boolean atom')])} is a Boolean atom with a superscript: a label, not a "
                    "number raised to a power")
        return f"{code(part)} is a power or a superscript that isn't a name"
    if rule == "overline_operator":
        return "a line over an operator marks the paper's own variant of it (averaged, marked, ...)"
    if rule == "close_parentheses":
        return "a bracket is never closed: the formula was cut, the rest is on another row of the paper"
    if rule == "function":
        if part.startswith("\\"):
            return f"{code(part)} is a function"
        return f"{code(part)} applies a function to something that isn't a name or an integer"
    if rule == "indexed_operator":
        return f"{code(part)} stands for a number of terms that isn't known"
    if rule == "quantifier":
        return f"{code(part)} is a quantifier"
    if rule == "set_membership":
        return "\\in says that a signal belongs to a set: STL can only compare it with numbers"
    if rule == "nonstandard_operator":
        if part == "X with an interval":
            return "X (next) with an interval: stl-nl has no such operator"
        if part == "two intervals on one operator":
            return "an operator with two intervals"
        return f"{code(part)} isn't an STL operator"
    if rule == "operator_alone":
        if part.startswith("nothing after "):
            return f"the formula ends right after the operator {code(part[len('nothing after '):])}"
        return f"the operator {code(part)} has no operand"
    if rule == "parse_error":
        if part.startswith("subscript after "):
            return f"a subscript after {code(part[len('subscript after '):])}, where none can go"
        if part.startswith("subscript "):
            return (f"the subscript {code(part[len('subscript '):])} is on a name, but it is neither an interval "
                    "nor part of the name")
        if part.startswith("unexpected "):
            symbol, _, context = part[len("unexpected "):].partition(" in: ")
            return f"the parser didn't expect {code(symbol)} here: {code(context)}"
        if part.startswith("character "):
            return f"the character {code(part[len('character '):].strip(chr(39)))} isn't part of the grammar"
        return f"the parser can't read it: {code(part)}"
    return code(part) if part else ""


def report(lines: list[dict], *, mode: str, source: str, seed: str, max_per_template: int | None = None) -> str:
    """The report of a run on the records of `source` (a path, for the text) in `mode` (rules.py)."""
    total = len(lines)
    status = collections.Counter(l["status"] for l in lines)
    if mode == "stl-nl":
        out = ["# Normalized formulas for stl-nl", "",
               f"From `{source}` ({total} formulas), with the rules of `docs/normalization_rules.md` and the stlgen "
               f"parser of stl-nl. Seed of the random values: `{seed}`.", ""]
    else:
        out = ["# Normalized paired formulas", "",
               f"From `{source}` ({total} formulas, each with the requirement the paper gives it), with the rules of "
               "`docs/normalization_rules.md` in the faithful mode: the meaning the requirement describes is kept, so "
               "the bounds and powers stay as the paper writes them, beyond the grammar of stl-nl, and the rules that "
               "would change the meaning reject the formula. These formulas don't go to stl-nl: they are checked by "
               "the normalizer's own parser only, not by stlgen.", ""]
    out += ["## By status", ""]
    out += table([(s, status[s], f"{100 * status[s] / total:.1f}%") for s in ("ok", "needs_review", "rejected")],
                 ("Status", "Formulas", "Share"))
    rejected = collections.Counter(reason_rule(l["reasons"][0]) for l in lines if l["status"] == "rejected")
    out += ["## Why formulas are rejected", "",
            "Each formula is counted under the first rule that rejects it: a single construct the rule can't accept "
            "rejects the whole formula, even when the rest is valid STL.", ""]
    out += table([(r, n, cell(description(r, mode))) for r, n in rejected.most_common()],
                 ("Rule", "Formulas", "Why it is rejected"))
    out += ["### Examples of each rule", "",
            f"Up to {EXAMPLES_PER_RULE} formulas per rule, from different papers and showing different cases of the "
            "rule. *Example* is the formula as the paper writes it. *Why* names the part that made the rule reject "
            "it, written after the paper's macros are expanded and with the names normalized (\\varphi_{1} is "
            "varphi_1); *(macro)* marks an example where that part comes from a macro of the paper, so it can't be "
            "seen in the formula as written.", ""]
    for r, n in rejected.most_common():
        out += [f"**{r}** ({n} formulas): {cell(description(r, mode))}.", ""]
        out += table([(code(l["original"]) + macro_mark(l), why(l)) for l in rejected_examples(lines, r)],
                     ("Example", "Why"))
    review = collections.Counter(r for l in lines if l["status"] == "needs_review"
                                 for r in {reason_rule(x) for x in l["reasons"]})
    if review:
        out += ["## Why formulas need review", "", "A formula may have several reasons: the counts add up to more "
                "than the formulas.", ""]
        example = examples(lines, "needs_review")
        out += table([(r, n, description(r, mode), code(example[r]["original"]), code(example[r]["normalized"]))
                      for r, n in review.most_common()], ("Rule", "Formulas", "What it is", "Example", "Normalized as"))
    unknown = collections.Counter(l["reasons"][0].split(": ", 1)[1] for l in lines
                                  if l["status"] == "rejected" and reason_rule(l["reasons"][0]) == "unknown_command")
    with_command = collections.defaultdict(list)
    for l in lines:
        if l["status"] == "rejected" and reason_rule(l["reasons"][0]) == "unknown_command":
            with_command[l["reasons"][0].split(": ", 1)[1]].append(l)
    rows = []
    for command, n in unknown.most_common(30):
        written = sum(1 for l in with_command[command] if command in l["original"])
        # Preferably a formula that has the command itself, not one of the paper's macros that expands to it
        example = shortest(with_command[command], lambda l: command in l["original"])
        where = "" if command in example["original"] else " (in a macro of the paper)"
        rows.append((code(command), n, written, n - written, code(example["original"]) + where))
    out += ["## Most frequent unknown commands", "",
            "Candidates for a new rule. Many come from the paper's macros: its definition of an operator uses a "
            "command to draw the symbol (\\raisebox, \\rotatebox, ...).", ""]
    out += table(rows, ("Command", "Formulas", "Written in the formula", "From a macro", "Example"))
    out += templates(lines)
    out += patterns(lines, with_selection=mode == "stl-nl")
    if mode == "stl-nl":
        out += selection(lines, max_per_template)
    else:
        out += extensions(lines)
        out += descriptions(lines)
    return "\n".join(out)


PATTERNS_SHOWN = 30


def templates(lines: list[dict]) -> list[str]:
    """The templates of the formulas kept: how many there are, and the most common ones with an example each."""
    kept = [l for l in lines if l["status"] != "rejected"]
    count = collections.Counter(l["template"] for l in kept)
    once = sum(1 for n in count.values() if n == 1)
    shown = count.most_common(PATTERNS_SHOWN)
    covered = sum(n for _, n in shown)
    example = {}
    for l in kept:
        best = example.get(l["template"])
        if best is None or len(l["normalized"]) < len(best["normalized"]):
            example[l["template"]] = l
    out = ["## Templates", "",
           "The template of a formula is its normalized text with every number written # and the names renamed a, "
           "b, ... in the order they appear (a name used twice keeps its letter; operators and comparisons are kept). "
           "Formulas that differ only in their numbers and names have the same template. The manifest has the "
           f"template of each formula (`template`); the example is the shortest formula of each template.", "",
           f"{len(kept)} formulas kept have {len(count)} templates; {once} of them have one formula only. The "
           f"{len(shown)} most common cover {covered} formulas ({100 * covered / len(kept):.0f}%).", ""]
    out += table([(code(s), n, f"{100 * n / len(kept):.1f}%", code(example[s]["normalized"])) for s, n in shown],
                 ("Template", "Formulas", "Share", "Example"))
    return out


def coverage(group: list[dict], field: str) -> tuple:
    """Formulas, distinct values of `field`, values seen once, share of the formulas the 10 most common cover."""
    count = collections.Counter(l[field] for l in group)
    top = sum(n for _, n in count.most_common(10))
    return (len(group), len(count), sum(1 for n in count.values() if n == 1), f"{100 * top / len(group):.1f}%")


def patterns(lines: list[dict], with_selection: bool = True) -> list[str]:
    """
    The patterns of the formulas ok (and with `with_selection` of those kept for stl-nl), and the most common ones
    with an example each.
    """
    ok = [l for l in lines if l["status"] == "ok"]
    kept = [l for l in ok if l["selection"] == "kept"] if with_selection else []
    groups = (("ok", ok), ("kept for stl-nl", kept)) if with_selection else (("ok", ok),)
    count = collections.Counter(l["pattern"] for l in ok)
    count_kept = collections.Counter(l["pattern"] for l in kept)
    shown = count.most_common(PATTERNS_SHOWN)
    example = {}
    for l in ok:
        best = example.get(l["pattern"])
        if best is None or len(l["normalized"]) < len(best["normalized"]):
            example[l["pattern"]] = l
    out = ["## Patterns", "",
           "The pattern of a formula is its temporal and Boolean structure, as stl-nl's "
           "`scripts/formula_patterns.py` computes it, calling it the skeleton (`src/normalization/pattern.py`, "
           "from stlgen's AST): each "
           "distinct relation or Boolean signal is a Greek letter, which repeats only when the exact same condition "
           "repeats; bounds are `[#,#]`, or `[#,inf]` when unbounded; the operands of `+ * && || == !=` are "
           "unordered. It is coarser than the template, which also keeps the relations. The manifest has the pattern "
           "of each formula ok (`pattern`); the example is the shortest formula of each pattern.", ""]
    if not with_selection:
        out += ["These formulas can't all be parsed by stlgen (their bounds and powers go beyond its grammar): their "
                "AST is built from the normalizer's own tree (`src/normalization/stlgen_ast.py`), which gives the same "
                "pattern as stlgen's AST for every formula stlgen can parse. Every finite interval is `[#,#]`, open "
                "or not; a power is `^`.", ""]
    out += table([(f"{level}, {group_name}", *coverage(group, field))
                  for level, field in (("Pattern", "pattern"), ("Template", "template"))
                  for group_name, group in groups],
                 ("Level, formulas", "Formulas", "Distinct", "Seen once", "Top 10 cover"))
    if with_selection:
        out += table([(code(s), n, f"{100 * n / len(ok):.1f}%", count_kept[s], code(example[s]["normalized"]))
                      for s, n in shown], ("Pattern", "Formulas ok", "Share", "Kept for stl-nl", "Example"))
    else:
        out += table([(code(s), n, f"{100 * n / len(ok):.1f}%", code(example[s]["normalized"])) for s, n in shown],
                     ("Pattern", "Formulas ok", "Share", "Example"))
    return out


def selection(lines: list[dict], max_per_template: int) -> list[str]:
    """How many formulas ok go to stl-nl, and the templates the cap cuts."""
    ok = [l for l in lines if l["status"] == "ok"]
    count = collections.Counter(l["selection"] for l in ok)
    cap = f"at most {max_per_template} formulas of each template" if max_per_template else "no cap per template"
    out = ["## Selection for stl-nl", "",
           "Of the formulas ok, one with the same normalized text as an earlier one is left out (`duplicate`; the "
           f"manifest gives the id of the first in `duplicate_of`), and {cap} are kept, taken from the papers in "
           "turn, at random with the seed (`template_cap`). Only the formulas kept are written in `stl/`.", ""]
    out += table([(s, count[s], f"{100 * count[s] / len(ok):.1f}%") for s in ("kept", "duplicate", "template_cap")],
                 ("Selection", "Formulas", "Share of ok"))
    by_template = collections.defaultdict(collections.Counter)
    for l in ok:
        by_template[l["template"]][l["selection"]] += 1
    cut = sorted(((p, c) for p, c in by_template.items() if c["template_cap"]), key=lambda pc: -pc[1]["template_cap"])
    if cut:
        out += [f"{len(cut)} templates are cut:", ""]
        out += table([(code(p), sum(c.values()) - c["duplicate"], c["kept"]) for p, c in cut],
                     ("Template", "Formulas (no duplicates)", "Kept"))
    return out


def extensions(lines: list[dict]) -> list[str]:
    """How many formulas ok use each construct of the faithful mode that stl-nl's grammar doesn't have."""
    ok = [l for l in lines if l["status"] == "ok"]
    count = collections.Counter(r for l in ok for r in l["rules"] if r in FAITHFUL_RULES)
    using = sum(1 for l in ok if FAITHFUL_RULES & set(l["rules"]))
    example = {}
    for rule in FAITHFUL_RULES:
        with_rule = [l for l in ok if rule in l["rules"]]
        if with_rule:
            example[rule] = shortest(with_rule, without_macros)
    out = ["## Beyond the grammar of stl-nl", "",
           f"What the faithful mode keeps as the paper writes it, where the stl-nl mode would change it. {using} of the "
           f"{len(ok)} formulas ok use at least one; the others are in stl-nl's grammar.", ""]
    rows = [(r, count[r], cell(description(r, "faithful")), code(example[r]["original"]),
             code(example[r]["normalized"])) for r in sorted(FAITHFUL_RULES, key=lambda r: -count[r]) if count[r]]
    return out + table(rows, ("Rule", "Formulas", "What it keeps", "Example", "Normalized as"))


NAMES_SHOWN = 20


def descriptions(lines: list[dict]) -> list[str]:
    """
    How the requirement passages of the formulas ok were written to match them (description.py): what was converted,
    and what was left as written, to decide later what to do with it.
    """
    passages = [p for l in lines if l["status"] == "ok" for p in l["requirements"]]
    clean = sum(1 for p in passages if not (p["unreadable"] or p["references"] or p["latex_left"]))
    changed = sum(1 for p in passages if p["normalized"] != p["text"])
    unreadable = collections.Counter(reason_rule(u["reason"]) for p in passages for u in p["unreadable"])
    unreadable_example = {}
    for p in passages:
        for u in p["unreadable"]:
            rule = reason_rule(u["reason"])
            if rule not in unreadable_example or 0 < len(u["span"]) < len(unreadable_example[rule]["span"]):
                unreadable_example[rule] = u
    with_unreadable = sum(1 for p in passages if p["unreadable"])
    references = sum(1 for p in passages if p["references"])
    left = collections.Counter(c for p in passages for c in p["latex_left"])
    missing = collections.Counter(n for p in passages for n in p["names_not_in_formula"])
    with_missing = sum(1 for p in passages if p["names_not_in_formula"])
    out = ["## Descriptions", "",
           "Each requirement passage of a formula ok is written to match the normalized formula "
           "(`src/normalization/description.py`): plain text, its math read with the paper's macros and the same "
           "lexer as the formula, so that each symbol is written as in the formula (`$\\varphi_{1}$` is `varphi_1`), "
           "text-mode LaTeX made plain, Unicode letters of PDFs written as names. What can't be converted is left as "
           "written: it is counted here, and nothing is dropped for it yet. The manifest has, for each passage, "
           "`normalized` and what was left (`unreadable`, `references`, `latex_left`, `names_not_in_formula`).", ""]
    out += table([("passages", len(passages), ""),
                  ("changed by the normalization", changed, f"{100 * changed / len(passages):.1f}%"),
                  ("with nothing left as written", clean, f"{100 * clean / len(passages):.1f}%"),
                  ("with a math span left as written (unreadable)", with_unreadable,
                   f"{100 * with_unreadable / len(passages):.1f}%"),
                  ("with a reference (\\ref, \\cite, ...)", references, f"{100 * references / len(passages):.1f}%"),
                  ("with another LaTeX command left", sum(1 for p in passages if p["latex_left"]),
                   f"{100 * sum(1 for p in passages if p['latex_left']) / len(passages):.1f}%"),
                  ("with a name the formula doesn't have", with_missing, f"{100 * with_missing / len(passages):.1f}%")],
                 ("Passages", "Count", "Share"))
    if unreadable:
        out += ["### Math left as written", "",
                "Spans the lexer can't read, by the rule that stops it (the same rules that reject a formula).", ""]
        out += table([(r, n, code(unreadable_example[r]["span"]) if unreadable_example[r]["span"] else "")
                      for r, n in unreadable.most_common()], ("Reason", "Spans", "Example"))
    if left:
        out += ["### Other LaTeX commands left", ""]
        out += table([(code(c), n) for c, n in left.most_common(NAMES_SHOWN)], ("Command", "Times"))
    out += ["### Names the formula doesn't have", "",
            "Names in a description that are not in its formula. Many are normal (the time t, an index i, a signal "
            "the passage mentions for context); others are a symbol the description writes differently from the "
            "formula.", ""]
    out += table([(code(n), c) for n, c in missing.most_common(NAMES_SHOWN)], ("Name", "Passages"))
    return out
