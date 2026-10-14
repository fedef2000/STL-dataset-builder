"""
Runs several models over the evaluation set and compares them: how many answers are right, how long a call takes
and what it costs.

    python scripts/eval/benchmark.py                 # run what is missing, then print the comparison
    python scripts/eval/benchmark.py --report        # only score the answers already stored: no model is called
    python scripts/eval/benchmark.py --models google/gemini-3.8-flash --reasoning minimal --runs 1

Every answer is stored in data/processed/benchmark/<name>/answers.jsonl as soon as it arrives, so an interrupted run
continues where it stopped and the scores can be recomputed for free after a label is corrected. The comparison is
printed and written to report.md in the same folder, with the entries where the models disagree with the labels.

An entry of the evaluation set is scored on three things:
  requirement  right when the label is "none" and the model gives none, or when the model gives every labelled
               passage and nothing else. A paper may state a requirement more than once: all passages are wanted.
               Two passages match when they share at least half of the shorter one; "exact" means nearly the same
               text. "Partly" means some passages found but one left out, or an extra one given. Every passage
               also has a kind, specific or generic: "kind right" counts the found passages given the kind of
               their label.
  domain       the same domain as the label.
  variables    the share of the labelled symbols the model explained. The meanings are not graded: report.md
               puts them side by side.
"""
import argparse, collections, json, re, statistics, sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo)); sys.path.insert(0, str(Path(__file__).parent))
from check_contexts import find_ignoring_spaces
from config import PROCESSED_DIR, RAW_LATEX_DIR
from src.extraction import context as c
from src.extraction import extractor as x
from src.extraction.runs import latest_answers, matches_region, nearly_equal, run_calls, same_passage

sys.stdout.reconfigure(encoding="utf-8")
DEFAULT_MODELS = ["anthropic/claude-sonnet-5.5", "google/gemini-3.8-flash", "deepseek/deepseek-v4.1-flash", "z-ai/glm-5.3-flash", "openai/gpt-6-luna"]
# "off" is the lowest each model allows: a model that cannot answer without reasoning is asked with minimal reasoning
DEFAULT_REASONING = ["off", "medium"]
# Models that get other levels when --reasoning is not given. Claude Sonnet 5.5 answers the same at off and at medium
# and at high (same output size and cost, no reasoning tokens), so it runs at one level only.
MODEL_REASONING = {"anthropic/claude-sonnet-5.5": ["medium"]}
# Calls of the full job, used to project the cost: the number printed by "python scripts/eval/check_contexts.py --corpus"
CORPUS_REGIONS = 1227
nows = lambda s: re.sub(r"\s+", "", s or "")


def load_tasks(limit: int | None = None):
    """
    Places every entry of the evaluation set: returns the entries, each with the (paper, region number, formula ID)
    where its formula is marked, and the regions to send, keyed by (paper, region number).
    """
    corpus = json.load(open(repo / "data/corpus.json", encoding="utf-8"))
    entries = json.load(open(PROCESSED_DIR / "eval_set.json", encoding="utf-8"))[:limit]
    contexts, regions, placed = {}, {}, []
    for entry in entries:
        pid = entry["paper_id"]
        if pid not in contexts:
            contexts[pid] = c.build_paper_context(pid, corpus[pid].get("title"), RAW_LATEX_DIR / pid)
        # A paper may print the same formula several times (in the text, again in a caption). The entry is scored on the
        # occurrence its requirement stands next to; a "none" entry on the occurrence of the labelled line.
        hits = []
        for n, region in enumerate(contexts[pid].regions, 1):
            req = find_ignoring_spaces(region.text, entry["requirements"][0]["text"]) if entry["requirements"] else None
            for f in region.formulas:
                if nows(entry["formula"]) in nows(f.source):
                    gap = max(req[0] - f.end, f.start - req[1], 0) if req else 10 ** 9
                    hits.append((gap, not region.file.endswith(entry["source_file"]), abs(f.line - int(entry["line"])), n, f.id))
        where = None
        if hits:
            _, _, _, n, fid = min(hits)
            where = (pid, n, fid)
            regions[(pid, n)] = (contexts[pid], contexts[pid].regions[n - 1])
        placed.append((entry, where))
    return placed, regions


# ---------------------------------------------------------------- calling the models

def run_benchmark_calls(args, regions: dict, answers_file: Path) -> None:
    # The reasoning levels of each model: the ones asked for, otherwise the model's own defaults
    pairs = [(model, reasoning) for model in args.models
             for reasoning in (args.reasoning or MODEL_REASONING.get(model, DEFAULT_REASONING))]
    print(f"{len(pairs)} model and reasoning pairs x {args.runs} runs x {len(regions)} regions")
    tasks = [(model, reasoning, run, pid, n) for run in range(1, args.runs + 1) for model, reasoning in pairs for (pid, n) in sorted(regions)]
    run_calls(tasks, regions, answers_file, args.workers, args.budget, retry_incomplete=False)


# ---------------------------------------------------------------- scoring

def score_entry(entry: dict, answer: dict | None) -> dict:
    """Scores one entry against the model's answer for its formula (None when the formula was not answered)."""
    labelled, variables = entry["requirements"], entry["variables"]
    score = dict(requirement="unanswered", passages_found=0, passages_extra=0, kinds_right=0, domain=False, variables=0,
                 labelled_variables=len(variables), problems=0, answer=answer)
    if answer is None:
        return score
    given = answer["requirements"]
    if not labelled:
        score["requirement"] = "none, right" if not given else "invented"
        score["passages_extra"] = len(given)
    elif not given:
        score["requirement"] = "missed"
    else:
        # Which labelled passages the model found, and which of its passages match no label
        same = same_passage
        labels, answers = [nows(r["text"]) for r in labelled], [nows(r["text"]) for r in given]
        score["passages_found"] = sum(1 for a in labels if any(same(a, b) for b in answers))
        score["passages_extra"] = sum(1 for b in answers if not any(same(a, b) for a in labels))
        # A found passage has the right kind when the model gives it the kind of its label
        score["kinds_right"] = sum(1 for a, label in zip(labels, labelled)
                                   if any(same(a, b) and answer_passage["kind"] == label["kind"] for b, answer_passage in zip(answers, given)))
        if score["passages_found"] == 0:
            score["requirement"] = "other passage"
        elif score["passages_found"] < len(labels) or score["passages_extra"]:
            score["requirement"] = "partly"
        elif all(any(nearly_equal(a, b) for b in answers) for a in labels):
            score["requirement"] = "exact"
        else:
            score["requirement"] = "overlap"
    score["domain"] = answer["domain"] == entry["domain"]
    explained = {nows(symbol) for symbol in answer["variables"]}
    score["variables"] = sum(1 for symbol in variables if nows(symbol) in explained)
    score["problems"] = len(answer["problems"])
    return score


RIGHT = ("none, right", "exact", "overlap")


def score_all(placed: list, answers_file: Path, regions: dict) -> dict:
    """Returns {(model, reasoning): {run: {"calls": [...], "scores": {entry id: score}}}} from the stored answers."""
    rows = latest_answers(answers_file)
    configs = collections.defaultdict(dict)
    for (model, reasoning, run, _, _), row in rows.items():
        configs[(model, reasoning)].setdefault(run, {"calls": [], "scores": {}})["calls"].append(row)
    for (model, reasoning), runs in configs.items():
        for run, data in runs.items():
            for entry, where in placed:
                answer = None
                if where:
                    row = rows.get((model, reasoning, run, where[0], where[1]))
                    if row is None or (not row.get("error") and not matches_region(row, regions[where[:2]][1])):
                        # This region was not asked in this run (e.g. a run that was interrupted), or the stored
                        # answer is about the region as it was before the formulas were found differently
                        continue
                    if not row.get("error"):
                        x.recheck_stored(row.get("extractions") or [], regions[where[:2]][1])
                    answer = next((e for e in row.get("extractions") or [] if e["id"] == where[2]), None)
                data["scores"][entry["id"]] = score_entry(entry, answer)
    return configs


def summarise(configs: dict, placed: list) -> list[dict]:
    lines = []
    n_none = sum(1 for entry, _ in placed if not entry["requirements"])
    n_passages = sum(len(entry["requirements"]) for entry, _ in placed)
    for (model, reasoning), runs in sorted(configs.items()):
        per_run = []
        for run, data in sorted(runs.items()):
            scores = list(data["scores"].values())
            ok_calls = [r for r in data["calls"] if not r.get("error")]
            labelled = sum(s["labelled_variables"] for s in scores)
            per_run.append(dict(
                scored=len(scores),
                right=sum(1 for s in scores if s["requirement"] in RIGHT),
                exact=sum(1 for s in scores if s["requirement"] == "exact"),
                none_right=sum(1 for s in scores if s["requirement"] == "none, right"),
                invented=sum(1 for s in scores if s["requirement"] == "invented"),
                missed=sum(1 for s in scores if s["requirement"] == "missed"),
                partly=sum(1 for s in scores if s["requirement"] == "partly"),
                found=sum(s["passages_found"] for s in scores), extra=sum(s["passages_extra"] for s in scores),
                kinds=sum(s["kinds_right"] for s in scores),
                domain=sum(1 for s in scores if s["domain"]),
                variables=100 * sum(s["variables"] for s in scores) / labelled if labelled else 0,
                problems=sum(s["problems"] for s in scores) + sum(len(r.get("problems") or []) for r in ok_calls),
                failed=len(data["calls"]) - len(ok_calls),
                seconds=statistics.median(r["seconds"] for r in ok_calls) if ok_calls else 0,
                cost=sum(r["cost"] for r in ok_calls), calls=len(ok_calls),
                reasoning_tokens=sum(r["reasoning_tokens"] for r in ok_calls),
                output_tokens=sum(r["output_tokens"] for r in ok_calls),
            ))
        # An entry is unstable when its requirement verdict (right or wrong) differs between the runs
        verdicts = collections.defaultdict(set)
        for data in runs.values():
            for eid, s in data["scores"].items():
                verdicts[eid].add(s["requirement"] in RIGHT)
        mean = lambda key: statistics.mean(r[key] for r in per_run)
        spread = lambda key: f"{mean(key):.1f}" + (f" ({min(r[key] for r in per_run)}-{max(r[key] for r in per_run)})" if len(per_run) > 1 else "")
        raised = any("cannot answer without reasoning" in note for data in runs.values() for r in data["calls"] for note in r.get("notes") or [])
        lines.append(dict(
            model=model, reasoning=f"off (ran as {x.LOWEST_REASONING})" if raised else reasoning, runs=len(per_run), scored=per_run[0]["scored"], n_none=n_none,
            right=spread("right"), right_mean=mean("right"), exact=f"{mean('exact'):.1f}", none_right=f"{mean('none_right'):.1f}",
            invented=f"{mean('invented'):.1f}", missed=f"{mean('missed'):.1f}", partly=f"{mean('partly'):.1f}",
            found=f"{mean('found'):.1f}", extra=f"{mean('extra'):.1f}", kinds=f"{mean('kinds'):.1f}", n_passages=n_passages, domain=f"{mean('domain'):.1f}", variables=f"{mean('variables'):.0f}%",
            problems=f"{mean('problems'):.1f}", failed=sum(r["failed"] for r in per_run), seconds=f"{mean('seconds'):.1f}",
            cost=mean("cost"), per_call=mean("cost") / max(1, mean("calls")),
            reasoning_share=100 * mean("reasoning_tokens") / max(1, mean("output_tokens")),
            unstable=sum(1 for v in verdicts.values() if len(v) > 1) if len(per_run) > 1 else None,
        ))
    return sorted(lines, key=lambda l: -l["right_mean"])


def comparison_table(lines: list[dict], corpus_regions: int) -> list[str]:
    n = lines[0]["scored"] if lines else 0
    header = ["Model", "Reasoning", "Runs", f"Requirement right (of {n})", "exact", f"none right (of {lines[0]['n_none'] if lines else 0})", "partly", "invented", "missed",
              f"Passages found (of {lines[0]['n_passages'] if lines else 0})", "Kind right (of found)", "Extra passages",
              f"Domain (of {n})", "Variables", "Problems", "Unstable", "s/call", "Reasoning tokens", "$/run", f"$ whole corpus"]
    table = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for l in lines:
        table.append("| " + " | ".join([
            l["model"], l["reasoning"], str(l["runs"]), l["right"], l["exact"], l["none_right"], l["partly"], l["invented"], l["missed"], l["found"], l["kinds"], l["extra"], l["domain"], l["variables"],
            l["problems"] + (f" (+{l['failed']} failed calls)" if l["failed"] else ""), "-" if l["unstable"] is None else str(l["unstable"]),
            l["seconds"], f"{l['reasoning_share']:.0f}% of output", f"{l['cost']:.3f}", f"{l['per_call'] * corpus_regions:.0f}",
        ]) + " |")
    return table


def print_table(table: list[str]) -> None:
    cells = [[cell.strip() for cell in row.strip("|").split("|")] for row in table if not row.startswith("|---")]
    widths = [max(len(row[i]) for row in cells) for i in range(len(cells[0]))]
    for n, row in enumerate(cells):
        print(" | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))
        if n == 0:
            print("-+-".join("-" * w for w in widths))


def write_report(folder: Path, placed: list, configs: dict, table: list[str], corpus_regions: int) -> Path:
    md = ["# Benchmark of the extraction models", "",
          "Scores are means over the runs, with the lowest and highest run in brackets. `Unstable` counts the entries whose requirement "
          "was right in one run and wrong in another. `Problems` counts answers that failed a check (not a copy of the source, "
          "unknown domain, formula not answered). `$ whole corpus` is the cost per call of this benchmark times the "
          f"{corpus_regions:,} regions of the corpus, at normal (not batch) prices: a rough figure.", ""] + table + [""]

    # Entries where at least half of the configurations get the requirement wrong, counting each by its most frequent verdict
    md += ["## Entries to look at", "",
           "Entries where at least half of the model configurations disagree with the label. When several models agree with each "
           "other against a label, check the label first.", ""]
    listed = 0
    for entry, where in placed:
        wrong, given, domains = 0, collections.Counter(), collections.Counter()
        for (model, reasoning), runs in configs.items():
            scores = [data["scores"][entry["id"]] for data in runs.values() if entry["id"] in data["scores"]]
            if not scores:
                continue
            wrong += 1 if sum(1 for s in scores if s["requirement"] not in RIGHT) * 2 > len(scores) else 0
            for s in scores:
                if s["answer"]:
                    given[(s["requirement"], "  ||  ".join(f"<{r['kind']}> {r['text']}" for r in s["answer"]["requirements"]) or "(none)")] += 1
                    domains[s["answer"]["domain"]] += 1
        domain_votes = sum(domains.values())
        domain_off = domain_votes and domains.most_common(1)[0][0] != entry["domain"] and domains.most_common(1)[0][1] * 2 > domain_votes
        if wrong * 2 < max(1, len(configs)) and not domain_off:
            continue
        listed += 1
        md += [f"### {entry['id']}  {entry['paper_id']}  ({entry['source_file']}, line {entry['line']})", "",
               f"Formula: `{entry['formula']}`", "", "Label: " + ("  ||  ".join(f"<{r['kind']}> {r['text']}" for r in entry["requirements"]) or "(none)"), ""]
        if wrong * 2 >= max(1, len(configs)):
            md += [f"Requirement wrong for {wrong} of {len(configs)} configurations. Answers given (over all runs):", ""]
            md += [f"- {count}x [{verdict}] {text}" for (verdict, text), count in given.most_common(4)] + [""]
        if domain_off:
            md += [f"Domain: label `{entry['domain']}`, answers: " + ", ".join(f"{d} ({k}x)" for d, k in domains.most_common(3)), ""]
    if not listed:
        md += ["None.", ""]

    md += ["## Variables side by side", "", "The label and, for every configuration, the meanings given in its first run.", ""]
    for entry, where in placed:
        md += [f"### {entry['id']}  `{entry['formula'][:120]}`", "", "| Symbol | Label | " + " | ".join(f"{m.split('/')[-1]} ({r})" for m, r in sorted(configs)) + " |",
               "|" + "---|" * (2 + len(configs))]
        for symbol, meaning in entry["variables"].items():
            cells = []
            for key in sorted(configs):
                first = configs[key][min(configs[key])]["scores"].get(entry["id"])
                answer = (first or {}).get("answer") or {}
                cells.append(next((m for s, m in (answer.get("variables") or {}).items() if nows(s) == nows(symbol)), "-"))
            md.append(f"| `{symbol}` | {meaning} | " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |")
        md.append("")
    path = folder / "report.md"
    path.write_text("\n".join(md), encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser(description="Compare extraction models on the evaluation set.")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS, help="OpenRouter model IDs (default: the five candidates).")
    parser.add_argument("--reasoning", nargs="+", choices=x.REASONING_LEVELS, help="Reasoning levels to try for every model (default: off medium, and only medium for Claude Sonnet 5.5). A model that cannot switch reasoning off runs \"off\" as minimal.")
    parser.add_argument("--runs", type=int, default=3, help="How many times every model answers the whole set (default 3). Answers vary between runs.")
    parser.add_argument("--name", default="main", help="Folder under data/processed/benchmark that holds the answers and the report (default: main).")
    parser.add_argument("--workers", type=int, default=8, help="Calls made at the same time (default 8).")
    parser.add_argument("--budget", type=float, default=15.0, help="Stop starting new calls once this many dollars are spent in this invocation (default 15).")
    parser.add_argument("--entries", type=int, help="Only the first N entries of the evaluation set (for a quick trial).")
    parser.add_argument("--report", action="store_true", help="Score the stored answers and print the comparison. No model is called.")
    args = parser.parse_args()

    folder = PROCESSED_DIR / "benchmark" / args.name
    folder.mkdir(parents=True, exist_ok=True)
    answers_file = folder / "answers.jsonl"
    placed, regions = load_tasks(args.entries)
    unplaced = [entry["id"] for entry, where in placed if not where]
    print(f"Evaluation set: {len(placed)} entries in {len(regions)} regions" + (f" | not marked in any region: {', '.join(unplaced)}" if unplaced else ""))
    if not args.report:
        run_benchmark_calls(args, regions, answers_file)
    if not answers_file.exists():
        sys.exit("No stored answers yet.")

    configs = score_all(placed, answers_file, regions)
    table = comparison_table(summarise(configs, placed), CORPUS_REGIONS)
    print()
    print_table(table)
    print(f"\nReport with the entries to look at and the variables side by side: {write_report(folder, placed, configs, table, CORPUS_REGIONS)}")


if __name__ == "__main__":
    main()
