"""
Step 7: normalizes the formulas without a requirement into the input of stl-nl (one formula per .stl file, in its STL
grammar), so that stl-nl can write natural-language descriptions of them.

    python scripts/07_normalize_formulas.py                     # data/dataset/stl_formulas_unpaired.jsonl
    python scripts/07_normalize_formulas.py --seed 1            # other random values for the bounds that cannot stay symbolic
    python scripts/07_normalize_formulas.py --stlgen PATH       # the stlgen binary of stl-nl (default: STLGEN_BIN)
    python scripts/07_normalize_formulas.py --max-per-pattern 0 # every formula ok to stl-nl (default: 10 per pattern)
    python scripts/07_normalize_formulas.py --show-rejected               # the reasons of rejection, with counts
    python scripts/07_normalize_formulas.py --show-rejected function      # 10 random formulas rejected by `function`
    python scripts/07_normalize_formulas.py --show-rejected "unknown_command: \\overline" --limit 0   # all of them

--show-rejected only reads the manifest of the last run: nothing is normalized again and no file is written.

Each formula goes through the rules of docs/normalization_rules.md and then through stlgen, the parser of stl-nl.
Of the formulas ok, those with the same normalized text as an earlier one are left out, and at most --max-per-pattern
of each pattern are kept (taken from the papers in turn): the manifest says which (`selection`).
Writes, in data/normalized/ (the .stl files of an earlier run are replaced):

    stl/f00001.stl ...            the formulas kept for stl-nl (status ok, selection kept)
    needs_review/r00001.stl ...   the formulas with a rule of status needs_review (none since 2026-10-19: not written)
    manifest.jsonl                one line per input record: status, file, reasons, rules, original and normalized text
    report.md                     counts by status, reason and pattern, with examples
"""
import argparse
import collections
import json
import random
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import DATA_DIR, RAW_LATEX_DIR, STLGEN_BIN
from src.normalization.latex import paper_macros
from src.normalization.normalize import normalize
from src.normalization.rules import RULES
from src.normalization.select import select
from src.normalization.skeleton import skeleton
from src.normalization.validate import check, over_limits

sys.stdout.reconfigure(encoding="utf-8")
INPUT_FILE = DATA_DIR / "dataset" / "stl_formulas_unpaired.jsonl"
OUTPUT_DIR = DATA_DIR / "normalized"
FOLDERS = {"ok": ("stl", "f"), "needs_review": ("needs_review", "r")}


def normalize_records(records: list[dict], seed: str, stlgen: Path) -> list[dict]:
    """One manifest line per record: the normalization, then the check with stlgen of what it gives."""
    macros_of, lines = {}, []
    for n, record in enumerate(records, 1):
        paper = record["paper_id"]
        if record["source_type"] == "latex" and paper not in macros_of:
            macros_of[paper] = paper_macros(RAW_LATEX_DIR / paper)
        result = normalize(record["formula"], record_id=record["id"], seed=seed,
                           macros=macros_of.get(paper, {}) if record["source_type"] == "latex" else {},
                           variables=record.get("variables") or {}, other_logic=record.get("other_logic"),
                           flags=record["provenance"].get("flags", []))
        line = {"id": record["id"], "status": result.status, "file": None, "reasons": result.reasons,
                "rules": result.rules, "original": record["formula"], "normalized": result.normalized,
                "pattern": result.pattern, "skeleton": None,
                "stl": None, "substitutions": result.substitutions, "rounded": result.rounded, "over_limits": [],
                "bounds": record["bounds"], "source_type": record["source_type"]}
        if result.normalized is not None:
            parsed, error = check(result.normalized, stlgen)
            if parsed is None:
                line.update(status="rejected", reasons=[f"stlgen_error: {error}"], rules=result.rules + ["stlgen_error"],
                            normalized=None, pattern=None)
            else:
                text, exact = skeleton(parsed["ast"])
                if not exact:
                    print(f"   {record['id']}: too many interchangeable conditions to compare every renaming; its "
                          f"skeleton may differ from an equal one")
                line.update(stl=parsed["stl"], over_limits=over_limits(parsed), skeleton=text)
        lines.append(line)
        if n % 500 == 0:
            print(f"   {n}/{len(records)}")
    return lines


def write_files(lines: list[dict]):
    for status, (folder, prefix) in FOLDERS.items():
        directory = OUTPUT_DIR / folder
        directory.mkdir(parents=True, exist_ok=True)
        for old in directory.glob("*.stl"):
            old.unlink()
        number = 0
        for line in lines:
            if line["status"] == status and line["selection"] in ("kept", None):
                number += 1
                line["file"] = f"{folder}/{prefix}{number:05d}.stl"
                (OUTPUT_DIR / line["file"]).write_text(line["normalized"] + "\n", encoding="utf-8")
        if number == 0 and not any(directory.iterdir()):
            directory.rmdir()  # no formula with this status: no empty folder
    with open(OUTPUT_DIR / "manifest.jsonl", "w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")


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


LOGICS = {
    "past-time": "past-time logic: its operators (once, since, historically, ...) look back in time, STL's only forward",
    "spatial-or-description": "a spatial or description logic: its operators are about places or objects",
    "probabilistic": "a probabilistic logic: its operators are about probabilities",
    "strategic": "a strategic logic: its operators are about what agents can enforce",
}


def why(line: dict) -> str:
    """Why this formula is rejected, in a sentence built from its rule and what the rule found."""
    rule, part = reason_rule(line["reasons"][0]), found(line)
    if rule == "other_logic":
        return f"the extraction classed it as {LOGICS.get(part, part)}"
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
        return f"{code(part)} is a power or a superscript that isn't a name"
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


def report(lines: list[dict], seed: str, max_per_pattern: int) -> str:
    total = len(lines)
    status = collections.Counter(l["status"] for l in lines)
    out = ["# Normalized formulas for stl-nl", "",
           f"From `{INPUT_FILE.relative_to(BASE_DIR)}` ({total} formulas), with the rules of "
           f"`docs/normalization_rules.md` and the stlgen parser of stl-nl. Seed of the random values: `{seed}`.", ""]
    out += ["## By status", ""]
    out += table([(s, status[s], f"{100 * status[s] / total:.1f}%") for s in ("ok", "needs_review", "rejected")],
                 ("Status", "Formulas", "Share"))
    rejected = collections.Counter(reason_rule(l["reasons"][0]) for l in lines if l["status"] == "rejected")
    out += ["## Why formulas are rejected", "",
            "Each formula is counted under the first rule that rejects it: a single construct the rule can't accept "
            "rejects the whole formula, even when the rest is valid STL.", ""]
    out += table([(r, n, cell(RULES[r][1])) for r, n in rejected.most_common()],
                 ("Rule", "Formulas", "Why it is rejected"))
    out += ["### Examples of each rule", "",
            f"Up to {EXAMPLES_PER_RULE} formulas per rule, from different papers and showing different cases of the "
            "rule. *Example* is the formula as the paper writes it. *Why* names the part that made the rule reject "
            "it, written after the paper's macros are expanded and with the names normalized (\\varphi_{1} is "
            "varphi_1); *(macro)* marks an example where that part comes from a macro of the paper, so it can't be "
            "seen in the formula as written.", ""]
    for r, n in rejected.most_common():
        out += [f"**{r}** ({n} formulas): {cell(RULES[r][1])}.", ""]
        out += table([(code(l["original"]) + macro_mark(l), why(l)) for l in rejected_examples(lines, r)],
                     ("Example", "Why"))
    review = collections.Counter(r for l in lines if l["status"] == "needs_review"
                                 for r in {reason_rule(x) for x in l["reasons"]})
    if review:
        out += ["## Why formulas need review", "", "A formula may have several reasons: the counts add up to more "
                "than the formulas.", ""]
        example = examples(lines, "needs_review")
        out += table([(r, n, RULES[r][1], code(example[r]["original"]), code(example[r]["normalized"]))
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
    out += patterns(lines)
    out += skeletons(lines)
    out += selection(lines, max_per_pattern)
    return "\n".join(out)


PATTERNS_SHOWN = 30


def patterns(lines: list[dict]) -> list[str]:
    """The patterns of the formulas kept: how many there are, and the most common ones with an example each."""
    kept = [l for l in lines if l["status"] != "rejected"]
    count = collections.Counter(l["pattern"] for l in kept)
    once = sum(1 for n in count.values() if n == 1)
    shown = count.most_common(PATTERNS_SHOWN)
    covered = sum(n for _, n in shown)
    example = {}
    for l in kept:
        best = example.get(l["pattern"])
        if best is None or len(l["normalized"]) < len(best["normalized"]):
            example[l["pattern"]] = l
    out = ["## Patterns", "",
           "The pattern of a formula is its normalized text with every number written # and the names renamed a, "
           "b, ... in the order they appear (a name used twice keeps its letter; operators and comparisons are kept). "
           "Formulas that differ only in their numbers and names have the same pattern. The manifest has the "
           f"pattern of each formula (`pattern`); the example is the shortest formula of each pattern.", "",
           f"{len(kept)} formulas kept have {len(count)} patterns; {once} of them have one formula only. The "
           f"{len(shown)} most common cover {covered} formulas ({100 * covered / len(kept):.0f}%).", ""]
    out += table([(code(s), n, f"{100 * n / len(kept):.1f}%", code(example[s]["normalized"])) for s, n in shown],
                 ("Pattern", "Formulas", "Share", "Example"))
    return out


def coverage(group: list[dict], field: str) -> tuple:
    """Formulas, distinct values of `field`, values seen once, share of the formulas the 10 most common cover."""
    count = collections.Counter(l[field] for l in group)
    top = sum(n for _, n in count.most_common(10))
    return (len(group), len(count), sum(1 for n in count.values() if n == 1), f"{100 * top / len(group):.1f}%")


def skeletons(lines: list[dict]) -> list[str]:
    """The skeletons of the formulas ok and of those kept for stl-nl, and the most common ones with an example each."""
    ok = [l for l in lines if l["status"] == "ok"]
    kept = [l for l in ok if l["selection"] == "kept"]
    count = collections.Counter(l["skeleton"] for l in ok)
    count_kept = collections.Counter(l["skeleton"] for l in kept)
    shown = count.most_common(PATTERNS_SHOWN)
    example = {}
    for l in ok:
        best = example.get(l["skeleton"])
        if best is None or len(l["normalized"]) < len(best["normalized"]):
            example[l["skeleton"]] = l
    out = ["## Skeletons", "",
           "The skeleton of a formula is its temporal and Boolean structure, as stl-nl's "
           "`scripts/formula_patterns.py` computes it (`src/normalization/skeleton.py`, from stlgen's AST): each "
           "distinct relation or Boolean signal is a Greek letter, which repeats only when the exact same condition "
           "repeats; bounds are `[#,#]`, or `[#,inf]` when unbounded; the operands of `+ * && || == !=` are "
           "unordered. It is coarser than the pattern, which also keeps the relations. The manifest has the skeleton "
           "of each formula ok (`skeleton`); the example is the shortest formula of each skeleton.", ""]
    out += table([(f"{level}, {group_name}", *coverage(group, field))
                   for level, field in (("Skeleton", "skeleton"), ("Pattern", "pattern"))
                   for group_name, group in (("ok", ok), ("kept for stl-nl", kept))],
                 ("Level, formulas", "Formulas", "Distinct", "Seen once", "Top 10 cover"))
    out += table([(code(s), n, f"{100 * n / len(ok):.1f}%", count_kept[s], code(example[s]["normalized"]))
                  for s, n in shown], ("Skeleton", "Formulas ok", "Share", "Kept for stl-nl", "Example"))
    return out


def selection(lines: list[dict], max_per_pattern: int) -> list[str]:
    """How many formulas ok go to stl-nl, and the patterns the cap cuts."""
    ok = [l for l in lines if l["status"] == "ok"]
    count = collections.Counter(l["selection"] for l in ok)
    cap = f"at most {max_per_pattern} formulas of each pattern" if max_per_pattern else "no cap per pattern"
    out = ["## Selection for stl-nl", "",
           "Of the formulas ok, one with the same normalized text as an earlier one is left out (`duplicate`; the "
           f"manifest gives the id of the first in `duplicate_of`), and {cap} are kept, taken from the papers in "
           "turn, at random with the seed (`pattern_cap`). Only the formulas kept are written in `stl/`.", ""]
    out += table([(s, count[s], f"{100 * count[s] / len(ok):.1f}%") for s in ("kept", "duplicate", "pattern_cap")],
                 ("Selection", "Formulas", "Share of ok"))
    by_pattern = collections.defaultdict(collections.Counter)
    for l in ok:
        by_pattern[l["pattern"]][l["selection"]] += 1
    cut = sorted(((p, c) for p, c in by_pattern.items() if c["pattern_cap"]), key=lambda pc: -pc[1]["pattern_cap"])
    if cut:
        out += [f"{len(cut)} patterns are cut:", ""]
        out += table([(code(p), sum(c.values()) - c["duplicate"], c["kept"]) for p, c in cut],
                     ("Pattern", "Formulas (no duplicates)", "Kept"))
    return out


def show_rejected(prefix: str, limit: int, seed: str):
    """
    Prints the rejected formulas of the manifest whose reason starts with `prefix` (a rule, or a rule and what it
    found): a random sample of `limit` (0: all), drawn with `seed`, because the manifest is ordered by paper and the
    first ones would often all come from one paper. With an empty `prefix`, the reasons with their counts.
    """
    manifest = OUTPUT_DIR / "manifest.jsonl"
    if not manifest.is_file():
        sys.exit(f"{manifest.relative_to(BASE_DIR)} not found: run this script without --show-rejected first")
    rejected = [line for line in map(json.loads, open(manifest, encoding="utf-8")) if line["status"] == "rejected"]
    if not prefix:
        count = collections.Counter(reason_rule(l["reasons"][0]) for l in rejected)
        print(f"{len(rejected)} rejected formulas, by reason:")
        for rule, n in count.most_common():
            print(f"  {rule:<22} {n:>5}")
        return
    chosen = [l for l in rejected if l["reasons"][0].startswith(prefix)]
    if not chosen:
        sys.exit(f"no rejected formula has a reason starting with {prefix!r}: --show-rejected alone lists them")
    sample = chosen if limit == 0 or limit >= len(chosen) else random.Random(seed).sample(chosen, limit)
    print(f"{prefix}: {len(chosen)} formulas, showing {len(sample)} (seed {seed})")
    for n, line in enumerate(sample, 1):
        print(f"\n[{n}/{len(sample)}] {line['id']}   ({line['source_type']}, bounds: {line['bounds']})")
        print(f"  original : {' '.join(line['original'].split())}")
        reason = line["reasons"][0]
        print(f"  found    : {' '.join(reason.split(': ', 1)[1].split()) if ': ' in reason else '-'}")
        print(f"  rules    : {', '.join(line['rules'][:-1]) or '-'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=INPUT_FILE)
    parser.add_argument("--seed", default="0", help="seed of the random values of the symbolic bounds")
    parser.add_argument("--stlgen", type=Path, default=STLGEN_BIN, help="the stlgen binary of stl-nl")
    parser.add_argument("--max-per-pattern", type=int, default=10,
                        help="at most this many formulas of each pattern go to stl-nl (0: no cap)")
    parser.add_argument("--show-rejected", nargs="?", const="", metavar="REASON",
                        help="print rejected formulas whose reason starts with REASON (alone: list the reasons), "
                             "from the manifest of the last run")
    parser.add_argument("--limit", type=int, default=10, help="with --show-rejected: how many formulas (0: all)")
    args = parser.parse_args()
    if args.show_rejected is not None:
        show_rejected(args.show_rejected, args.limit, args.seed)
        return
    if not args.stlgen.is_file():
        sys.exit(f"stlgen not found at {args.stlgen}: build it in stl-nl (cargo build --release --locked "
                 f"--manifest-path rust/stlgen/Cargo.toml) or pass --stlgen")
    records = [json.loads(line) for line in open(args.input, encoding="utf-8")]
    print(f"Normalizing {len(records)} formulas from {args.input}")
    lines = normalize_records(records, args.seed, args.stlgen)
    select(lines, args.max_per_pattern, args.seed)
    write_files(lines)
    (OUTPUT_DIR / "report.md").write_text(report(lines, args.seed, args.max_per_pattern), encoding="utf-8")
    status = collections.Counter(l["status"] for l in lines)
    kept = sum(1 for l in lines if l["selection"] == "kept")
    print(f"ok {status['ok']} (kept for stl-nl {kept}), needs_review {status['needs_review']}, rejected {status['rejected']}: "
          f"see {(OUTPUT_DIR / 'report.md').relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
