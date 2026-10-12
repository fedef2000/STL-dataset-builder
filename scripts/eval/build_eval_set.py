"""
Builds the evaluation set (data/processed/eval_set.json and eval_set.md) from the hand-written labels in labels.py.

Every formula and requirement in labels.py must be a verbatim substring of the paper's LaTeX source in
data/raw/latex/<paper_id>/: the script looks each one up, records the file and line, and cuts out the surrounding
context. If a label is not found it prints the problem and writes nothing. The domain and the meaning of the
variables are written by the labeller: the script only checks that the domain is one of DOMAINS and that every
variable is a verbatim piece of its formula.

    python scripts/eval/build_eval_set.py                    # check the labels and rewrite both files
    python scripts/eval/build_eval_set.py --show-negatives   # print the context of the "none" cases, write nothing

To change the set, edit labels.py and run the script again. Entries are numbered in the order of LABELS followed by
NEGATIVES, so add new labels at the end of a list, otherwise the EVAL_nn ids and the PARTIAL notes shift.
"""
import collections, json, re, sys
from pathlib import Path
repo = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo)); sys.path.insert(0, str(Path(__file__).parent))
from src.analysis import estimator as e
from labels import DOMAINS, LABELS, NEGATIVES, PARTIAL
from src.extraction.extractor import REQUIREMENT_KINDS

def norm_with_lines(text):
    """Collapses whitespace; returns the normalised text and, per character, its 1-based source line."""
    out, lines, line, prev_space = [], [], 1, True
    for ch in text:
        if ch.isspace():
            if not prev_space:
                out.append(" "); lines.append(line)
            prev_space = True
        else:
            out.append(ch); lines.append(line); prev_space = False
        if ch == "\n":
            line += 1
    return "".join(out), lines

ws = lambda s: re.sub(r"\s+", " ", s).strip()
nows = lambda s: re.sub(r"\s+", "", s)
corpus = json.load(open(repo / "data/corpus.json", encoding="utf-8"))
# A labelled paper may since have been merged into another entry as a duplicate: follow it to the entry that was kept
merged_into = {old: pid for pid, p in corpus.items() for old in p.get("alternate_ids") or []}
entries, problems = [], []
# A six-field entry of NEGATIVES is a "none" case that was relabelled with a requirement and kept at its place
rows = list(LABELS) + [t if len(t) == 6 else (t[0], t[1], None, t[2], t[3], t[4]) for t in NEGATIVES]
for n, (pid, formula, req, note, domain, variables) in enumerate(rows, 1):
    pid = merged_into.get(pid, pid)
    if domain not in DOMAINS:
        problems.append((n, pid, f"unknown domain: {domain}"))
    for symbol in variables:
        if ws(symbol) not in ws(formula):
            problems.append((n, pid, f"variable not in formula: {symbol}"))
    prefix = ""
    if note.startswith("REQ_PREFIX:"):
        prefix, note = note[len("REQ_PREFIX:"):], ""
    note = note or PARTIAL.get(n, "")
    f_n = ws(formula)
    # One passage, or the list of every passage that states the requirement
    passages = [req] if isinstance(req, (str, tuple)) else req or []
    # A passage is specific unless written as ("generic", text)
    kinds = [p[0] if isinstance(p, tuple) else "specific" for p in passages]
    reqs = [ws(p[1] if isinstance(p, tuple) else p) for p in passages]
    if any(kind not in REQUIREMENT_KINDS for kind in kinds) or len(set(kinds)) > 1:
        problems.append((n, pid, "requirement kinds must be all specific or all generic"))
    if prefix and len(reqs) != 1:
        problems.append((n, pid, "REQ_PREFIX needs exactly one requirement"))
    folder = repo / "data/raw/latex" / pid
    found, formula_seen = None, False
    for tex in sorted(folder.rglob("*.tex")):
        raw = tex.read_text(encoding="utf-8", errors="ignore")
        # blank out comments without removing lines, so line numbers stay true
        stripped = "\n".join(re.sub(r"(?<!\\)%.*$", "", l) for l in raw.splitlines())
        text, line_of = norm_with_lines(stripped)
        f_positions = [m.start() for m in re.finditer(re.escape(f_n), text)]
        if not f_positions:
            continue
        formula_seen = True
        if nows(e.strip_latex_comments(raw)).find(nows(formula)) < 0:
            continue  # only present inside a disabled block in this file
        fi = f_positions[0]
        if reqs:
            r_positions = [[m.start() for m in re.finditer(re.escape(r), text)] for r in reqs]
            if not all(r_positions):
                continue
            # A formula printed more than once (in the text, again in a caption): take the occurrence the requirement stands next to
            fi = min(f_positions, key=lambda f: min(abs(p - f) for p in r_positions[0]))
            starts = [min(positions, key=lambda p: abs(p - fi)) for positions in r_positions]
            if prefix:
                ri = starts[0]
                pi = text.rfind(ws(prefix), 0, ri)
                if pi < 0 or ri - pi > len(ws(prefix)) + 12:
                    problems.append((n, pid, "prefix not adjacent"))
                else:
                    reqs[0] = text[pi:ri + len(reqs[0])]; starts[0] = pi
        lo, hi = fi, fi + len(f_n)
        for start, r in zip(starts if reqs else [], reqs):
            lo, hi = min(lo, start), max(hi, start + len(r))
        a = max(0, lo - 350); b = min(len(text), hi + 250)
        a = text.rfind(" ", 0, a) + 1 if a else 0
        b = text.find(" ", b) if text.find(" ", b) > 0 else len(text)
        found = (tex, line_of[fi], text[a:b])
        break
    if not found:
        problems.append((n, pid, "requirement not found near formula" if formula_seen else "formula not found"))
        continue
    tex, line, context = found
    p = corpus[pid]
    entries.append({
        "id": f"EVAL_{n:02d}", "paper_id": pid, "title": p.get("title"), "year": p.get("year"),
        "arxiv_id": p.get("arxiv_id"), "license_tier": (p.get("license_info") or {}).get("tier"),
        "source_file": str(tex.relative_to(folder)).replace(chr(92), "/"), "line": line,
        "formula": f_n, "has_requirement": bool(reqs),
        "requirements": [{"text": r, "kind": kind} for r, kind in zip(reqs, kinds)],
        "domain": domain, "variables": {ws(s): meaning for s, meaning in variables.items()}, "context": context, "note": note,
    })

print("labels:", len(rows), "| verified entries:", len(entries), "| problems:", len(problems))
for pr in problems:
    print("  PROBLEM", pr)
if problems:
    sys.exit(1)

if "--show-negatives" in sys.argv:
    for x in entries:
        if not x["has_requirement"]:
            print(f"--- {x['id']} {x['paper_id']} {x['source_file']} L{x['line']}\n{x['context']}")
    sys.exit(0)

out_dir = repo / "data/processed"
json.dump(entries, open(out_dir / "eval_set.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
pos = sum(x["has_requirement"] for x in entries)
md = ["# Evaluation set: requirement-formula pairs", "",
      f"{len(entries)} entries picked by hand from the LaTeX sources: {pos} with a requirement and {len(entries) - pos} \"none\" cases.", "",
      "`Formula` and `Requirement` are verbatim substrings of the source file (whitespace collapsed). "
      "When the paper states the requirement of a formula more than once, in different words, every passage is listed. "
      "A passage is specific when it carries the particulars of the formula (numbers, thresholds, named regions) and "
      "generic when it only says what the formula is for; a generic passage is labelled only when the paper has no specific one. "
      "A \"none\" case means the context given to the model holds no statement of what the formula requires; "
      "the paper may still describe it somewhere outside that context.", "",
      "`Domain` and `Variables` are written by the labeller, not copied: the domain is the application area of the system "
      "the formula is about (`generic` for an abstract example over an unnamed signal), and each variable of the formula "
      "gets a short explanation taken from the paper, which may lie outside the context.", ""]
import render
md += ["The rendered formula is a reading aid: each paper's own macros are expanded so the Markdown preview can draw it. "
       "The source line under it is the verbatim text and is what counts.", ""]
approx = 0
for x in entries:
    tex, guessed, by_name = render.expand(x["formula"], render.paper_macros(repo / "data/raw/latex" / x["paper_id"], e.strip_latex_comments))
    md += [f"## {x['id']}  {x['paper_id']}  ({x['source_file']}, line {x['line']})", "",
           f"*{x['title']}* ({x['year']}), licence tier: {x['license_tier']}", "",
           "**Formula**", "", "$$", tex, "$$", ""]
    if guessed or by_name:
        approx += 1
        parts = []
        if guessed:
            parts.append("symbol guessed for " + ", ".join(f"`\\{g}`" for g in sorted(guessed)))
        if by_name:
            parts.append("shown by name: " + ", ".join(f"`\\{g}`" for g in sorted(by_name)))
        md += ["*Rendering is approximate (the paper's definition of these macros is not on disk): " + "; ".join(parts) + ".*", ""]
    md += ["Source:", "", "```latex", x["formula"], "```", "", f"**Domain:** {x['domain']}", "", "**Variables**", ""]
    md += [f"- `{s}`: {meaning}" for s, meaning in x["variables"].items()] + [""]
    if x["has_requirement"]:
        many = len(x["requirements"]) > 1
        md += ["**Requirement**" + (f" (stated {len(x['requirements'])} times in the paper: the model has to report every passage)" if many else ""), ""]
        for r in x["requirements"]:
            md += (["*Generic: it does not carry the particulars of the formula.*", ""] if r["kind"] == "generic" else []) + ["```", r["text"], "```", ""]
        if x["note"]:
            md += [f"**Note:** {x['note']}", ""]
    else:
        md += ["**Requirement:** none", "", f"**Why none:** {x['note']}", ""]
    md += ["<details><summary>Context given to the model</summary>", "", "```", x["context"], "```", "", "</details>", ""]
(out_dir / "eval_set.md").write_text("\n".join(md), encoding="utf-8")
print("written:", len(entries), "entries |", pos, "with requirement,", len(entries) - pos, "none | papers:", len({x["paper_id"] for x in entries}))
print("domains:", dict(collections.Counter(x["domain"] for x in entries).most_common()))
print("none cases per licence tier:", dict(collections.Counter(x["license_tier"] for x in entries if not x["has_requirement"])))
