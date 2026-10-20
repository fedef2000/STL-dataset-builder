"""
Step 7: normalizes the formulas without a requirement into the input of stl-nl (one formula per .stl file, in its STL
grammar), so that stl-nl can write natural-language descriptions of them.

    python scripts/07_normalize_formulas.py                     # data/dataset/stl_formulas_unpaired.jsonl
    python scripts/07_normalize_formulas.py --seed 1            # other random values for the symbolic bounds
    python scripts/07_normalize_formulas.py --stlgen PATH       # the stlgen binary of stl-nl (default: STLGEN_BIN)
    python scripts/07_normalize_formulas.py --show-rejected               # the reasons of rejection, with counts
    python scripts/07_normalize_formulas.py --show-rejected function      # 10 random formulas rejected by `function`
    python scripts/07_normalize_formulas.py --show-rejected "unknown_command: \\overline" --limit 0   # all of them

--show-rejected only reads the manifest of the last run: nothing is normalized again and no file is written.

Each formula goes through the rules of docs/normalization_rules.md and then through stlgen, the parser of stl-nl.
Writes, in data/normalized/ (the .stl files of an earlier run are replaced):

    stl/f00001.stl ...            the formulas normalized and accepted by stlgen (status ok)
    needs_review/r00001.stl ...   the formulas with a rule of status needs_review (none since 2026-10-19: not written)
    manifest.jsonl                one line per input record: status, file, reasons, rules, original and normalized text
    report.md                     counts by status, reason and structure, with examples
"""
import argparse
import collections
import json
import random
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import DATA_DIR, RAW_LATEX_DIR, STLGEN_BIN
from src.normalization.latex import paper_macros
from src.normalization.normalize import normalize
from src.normalization.rules import RULES
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
                "structure": result.structure,
                "stl": None, "substitutions": result.substitutions, "rounded": result.rounded, "over_limits": [],
                "bounds": record["bounds"], "source_type": record["source_type"]}
        if result.normalized is not None:
            parsed, error = check(result.normalized, stlgen)
            if parsed is None:
                line.update(status="rejected", reasons=[f"stlgen_error: {error}"], rules=result.rules + ["stlgen_error"],
                            normalized=None, structure=None)
            else:
                line.update(stl=parsed["stl"], over_limits=over_limits(parsed))
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
            if line["status"] == status:
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


def shortest(candidates: list[dict], preferred=lambda line: True) -> dict:
    """
    The example among `candidates`: the shortest original of at least EXAMPLE_MIN_CHARS characters among the
    `preferred` ones, else among all (the first on a tie, so a rerun picks the same).
    """
    for pool in ([c for c in candidates if preferred(c)], candidates):
        long_enough = [c for c in pool if len(c["original"]) >= EXAMPLE_MIN_CHARS]
        if long_enough or pool:
            return min(long_enough or pool, key=lambda c: len(c["original"]))


def examples(lines: list[dict], status: str) -> dict[str, dict]:
    """An example per rule of the formulas with `status` (see shortest)."""
    by_rule = collections.defaultdict(list)
    for line in lines:
        if line["status"] == status:
            for rule in {reason_rule(r) for r in (line["reasons"][:1] if status == "rejected" else line["reasons"])}:
                by_rule[rule].append(line)
    return {rule: shortest(candidates, lambda line: "expand_paper_macros" not in line["rules"])
            for rule, candidates in by_rule.items()}


def macro_mark(line: dict) -> str:
    return " *(macro)*" if "expand_paper_macros" in line["rules"] else ""


def found(line: dict, rule: str) -> str:
    reason = next(r for r in line["reasons"] if reason_rule(r) == rule)
    return code(reason.split(": ", 1)[1]) if ": " in reason else ""


def report(lines: list[dict], seed: str) -> str:
    total = len(lines)
    status = collections.Counter(l["status"] for l in lines)
    out = ["# Normalized formulas for stl-nl", "",
           f"From `{INPUT_FILE.relative_to(BASE_DIR)}` ({total} formulas), with the rules of "
           f"`docs/normalization_rules.md` and the stlgen parser of stl-nl. Seed of the random bounds: `{seed}`.", ""]
    out += ["## By status", ""]
    out += table([(s, status[s], f"{100 * status[s] / total:.1f}%") for s in ("ok", "needs_review", "rejected")],
                 ("Status", "Formulas", "Share"))
    rejected = collections.Counter(reason_rule(l["reasons"][0]) for l in lines if l["status"] == "rejected")
    example = examples(lines, "rejected")
    out += ["## Why formulas are rejected", "",
            "The first reason of each formula. *Example* is one of these formulas as the paper writes it; *What the "
            "rule found* is the part of that same formula that made the rule reject it, written after the paper's "
            "macros are expanded and with the names already normalized (\\varphi_{1} is varphi_1). The example is "
            "a formula without the paper's macros when there is one, so that the part can be seen in it; *(macro)* "
            "marks one where it comes from a macro of the paper.", ""]
    out += table([(r, n, RULES[r][1], code(example[r]["original"]) + macro_mark(example[r]), found(example[r], r))
                  for r, n in rejected.most_common()],
                 ("Rule", "Formulas", "What it is", "Example", "What the rule found"))
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
    out += structures(lines)
    return "\n".join(out)


STRUCTURES_SHOWN = 30


def structures(lines: list[dict]) -> list[str]:
    """The structures of the formulas kept: how many there are, and the most common ones with an example each."""
    kept = [l for l in lines if l["status"] != "rejected"]
    count = collections.Counter(l["structure"] for l in kept)
    once = sum(1 for n in count.values() if n == 1)
    shown = count.most_common(STRUCTURES_SHOWN)
    covered = sum(n for _, n in shown)
    example = {}
    for l in kept:
        best = example.get(l["structure"])
        if best is None or len(l["normalized"]) < len(best["normalized"]):
            example[l["structure"]] = l
    out = ["## Structures", "",
           "The structure of a formula is its normalized text with every number written # and the names renamed a, "
           "b, ... in the order they appear (a name used twice keeps its letter; operators and comparisons are kept). "
           "Formulas that differ only in their numbers and names have the same structure. The manifest has the "
           f"structure of each formula (`structure`); the example is the shortest formula of each structure.", "",
           f"{len(kept)} formulas kept have {len(count)} structures; {once} of them have one formula only. The "
           f"{len(shown)} most common cover {covered} formulas ({100 * covered / len(kept):.0f}%).", ""]
    out += table([(code(s), n, f"{100 * n / len(kept):.1f}%", code(example[s]["normalized"])) for s, n in shown],
                 ("Structure", "Formulas", "Share", "Example"))
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
    write_files(lines)
    (OUTPUT_DIR / "report.md").write_text(report(lines, args.seed), encoding="utf-8")
    status = collections.Counter(l["status"] for l in lines)
    print(f"ok {status['ok']}, needs_review {status['needs_review']}, rejected {status['rejected']}: "
          f"see {(OUTPUT_DIR / 'report.md').relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
