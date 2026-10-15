"""
Puts the stored answers of the models side by side: one record per formula, with how far the two extraction models
agree on its requirement and, where a third model was asked to break the tie, which of them it sides with. Used by
the extraction (step 5).
"""
import json
import sys
from pathlib import Path

from config import BASE_DIR, PROCESSED_DIR, RAW_LATEX_DIR
from src.storage import CorpusStore
from src.extraction.context import build_paper_context
from src.extraction.pdf_context import PdfRegion, build_pdf_context
from src.extraction.extractor import REASONING_LEVELS, check_passage, formula_key, passage_core, recheck_stored
from src.extraction.runs import latest_answers, matches_region, same_passage

# The two models chosen with the benchmark (scripts/eval/benchmark.py), each with the reasoning level it did best at
DEFAULT_MODELS = ["google/gemini-3.8-flash:off", "openai/gpt-6-luna:medium"]
# The model asked about the formulas the two disagree on: the most stable one of the benchmark
DEFAULT_TIE_BREAKER = "anthropic/claude-sonnet-5.5:medium"
EXTRACTIONS_DIR = PROCESSED_DIR / "extractions"
# The status step 2 gives a paper held in each source
SOURCE_STATUS = {"latex": "downloaded_latex", "pdf": "downloaded_pdf"}


def store_files(parametric: bool = False, pdf: bool = False) -> tuple[Path, Path]:
    """
    (answers file, formulas file), in extractions/<latex|pdf>/<concrete|parametric>. Each kind of formula of each
    source has files of its own: the regions of a paper are numbered per source and kind of formula, so in one file
    the answers of two kinds would be taken for one another.
    """
    folder = EXTRACTIONS_DIR / ("pdf" if pdf else "latex") / ("parametric" if parametric else "concrete")
    return folder / "answers.jsonl", folder / "formulas.jsonl"


ANSWERS_FILE, FORMULAS_FILE = store_files()


# How far two models agree on the requirement of a formula, from full agreement down
AGREEMENTS = ("same passages", "both none", "partly the same", "different passages", "one gives none", "not answered")
AGREED = ("same passages", "both none")
DISPUTED = ("partly the same", "different passages", "one gives none")


def parse_model(spec: str) -> tuple[str, str]:
    """'google/gemini-3.8-flash:off' -> (model ID, reasoning level); the level defaults to off."""
    model, _, reasoning = spec.rpartition(":") if spec.rsplit(":", 1)[-1] in REASONING_LEVELS else (spec, "", "off")
    return model, reasoning


def load_contexts(store: CorpusStore, paper_ids: list[str] | None = None, limit: int | None = None, parametric: bool = False,
                  pdf: bool = False) -> dict:
    """
    The context of every paper held as LaTeX that has concrete formulas (or of the papers asked for that are held as
    LaTeX). With `parametric`, the formulas marked are the parametric ones instead, numbered P1, P2, ... With `pdf`,
    the papers held only as a PDF instead: one region per page.
    """
    count = "symbolic" if parametric else "concrete"
    options = dict(kinds=("symbolic",), id_prefix="P") if parametric else {}
    status = SOURCE_STATUS["pdf" if pdf else "latex"]
    if paper_ids:
        for pid in paper_ids:
            if pid not in store.papers:
                sys.exit(f"{pid} is not in the corpus")
        paper_ids = [pid for pid in paper_ids if store.papers[pid].get("local_files", {}).get("status") == status]
    else:
        paper_ids = [
            pid for pid, p in store.papers.items()
            if p.get("local_files", {}).get("status") == status and (p.get("formula_estimates") or {}).get(count)
        ][:limit]
    contexts = {}
    for n, pid in enumerate(paper_ids, 1):
        paper = store.papers[pid]
        if pdf:
            context = build_pdf_context(pid, paper.get("title"), BASE_DIR / paper["local_files"]["path"], **options)
        else:
            context = build_paper_context(pid, paper.get("title"), RAW_LATEX_DIR / pid, **options)
        if context.regions:
            contexts[pid] = context
        if n % 100 == 0:
            print(f"   {n}/{len(paper_ids)} papers read")
    return contexts


def agreement(a: dict | None, b: dict | None) -> str:
    """How far two answers for the same formula agree on its requirement."""
    if a is None or b is None:
        return "not answered"
    ra, rb = [r["text"] for r in a["requirements"]], [r["text"] for r in b["requirements"]]
    if not ra and not rb:
        return "both none"
    if not ra or not rb:
        return "one gives none"
    a_found = sum(1 for p in ra if any(same_passage(p, q) for q in rb))
    b_found = sum(1 for q in rb if any(same_passage(p, q) for p in ra))
    if a_found == len(ra) and b_found == len(rb):
        return "same passages"
    return "partly the same" if a_found or b_found else "different passages"


def kind_of(answer: dict | None) -> str:
    """'specific', 'generic' or 'none': the quality of what the model found for a formula."""
    kinds = {r["kind"] for r in (answer or {}).get("requirements") or []}
    return "specific" if "specific" in kinds else "generic" if kinds else "none"


def dispute_of(record: dict, labels: list[str]) -> str | None:
    """
    What the two models disagree on for a formula: 'requirement' (its passages), 'kind' (the same passages, tagged
    specific by one and generic by the other), 'formula' (for a PDF: the same passages, but the formula transcribed
    differently, so that the pair could not be used), or None.
    """
    first, second = record["answers"][labels[0]], record["answers"][labels[1]]
    if record["requirement_agreement"] in DISPUTED:
        return "requirement"
    if record["requirement_agreement"] == "same passages" and kind_of(first) != kind_of(second):
        return "kind"
    if record.get("source_type") == "pdf" and record["requirement_agreement"] == "same passages" \
            and formula_key(first["formula"]) != formula_key(second["formula"]):
        return "formula"
    return None


def verdict_of(tie_answer: dict, first: dict, second: dict) -> str:
    """Which of the two answers the tie-breaker's own answer agrees with on the requirement."""
    with_first, with_second = agreement(tie_answer, first), agreement(tie_answer, second)
    if with_first in AGREED and with_second in AGREED:
        return "agrees with both"
    if with_first in AGREED:
        return "sides with the first"
    if with_second in AGREED:
        return "sides with the second"
    if "partly the same" in (with_first, with_second):
        return "partly agrees"
    return "agrees with neither"


VERDICTS = ("sides with the first", "sides with the second", "agrees with both", "partly agrees", "agrees with neither")
# The verdicts after which two of the three models give the same requirement
SETTLED = ("sides with the first", "sides with the second", "agrees with both")


# What the vote of the models leaves for a formula
OUTCOMES = ("requirement", "none", "open")
VOTES_NEEDED = 2


def vote_formula(answers: dict, order: list[str]) -> dict:
    """
    For a formula transcribed from a PDF page: the transcription two models agree on (see formula_key), taken from the
    first model of `order` that gives it, or None when no two agree.
    """
    groups = {}
    for label in order:
        if answers[label]["formula"].strip():
            groups.setdefault(formula_key(answers[label]["formula"]), []).append(label)
    agreed = max(groups.values(), key=len, default=[])
    if len(agreed) < VOTES_NEEDED:
        return {"formula": None, "formula_given_by": []}
    return {"formula": answers[agreed[0]]["formula"], "formula_given_by": agreed}


def vote(given: dict, region_core: str, prefer: list[str] = (), transcribed: bool = False) -> dict:
    """
    The outcome of the vote of the models on one formula. `given` maps each model to its answer (None when it was
    not asked or did not answer); `region_core` is passage_core of the excerpt.

    A passage is kept when at least two models give it (see same_passage). The formula then has a 'requirement'.
    It has 'none' when no passage is kept and at least two models give none, and it stays 'open' otherwise. The kind
    of a kept passage is the one most of the models that give it chose ('unclear' when they are split), and a
    generic passage is dropped when a specific one is kept, as the models themselves are asked to do. The text is
    taken from a model whose passage is a copy of the excerpt, those of `prefer` first.
    """
    answers = {label: answer for label, answer in given.items() if answer}
    order = [label for label in prefer if label in answers] + [label for label in answers if label not in prefer]
    groups = []   # each: the passages of the models that are the same one, as (model, passage)
    for label in order:
        for passage in answers[label]["requirements"]:
            group = next((g for g in groups if any(same_passage(passage["text"], other["text"]) for _, other in g)), None)
            if group is None:
                groups.append(group := [])
            group.append((label, passage))

    kept = []
    for group in groups:
        voters = [label for label in order if any(label == member for member, _ in group)]
        if len(voters) < VOTES_NEEDED:
            continue
        # One vote per model: its first passage of the group
        votes = {label: next(passage for member, passage in group if member == label) for label in voters}
        kinds = [passage["kind"] for passage in votes.values()]
        top = max(set(kinds), key=kinds.count)
        copies = [label for label in voters if check_passage(votes[label]["text"], region_core) is None]
        source = (copies or voters)[0]
        kept.append({"text": votes[source]["text"], "kind": top if kinds.count(top) > len(kinds) / 2 else "unclear",
                     "from": source, "given_by": voters})
    if any(passage["kind"] == "specific" for passage in kept):
        kept = [passage for passage in kept if passage["kind"] != "generic"]

    none_votes = sum(1 for answer in answers.values() if not answer["requirements"])
    outcome = "requirement" if kept else "none" if none_votes >= VOTES_NEEDED else "open"
    kinds = {passage["kind"] for passage in kept}
    domains = [answer["domain"] for answer in answers.values()]
    variables = {}
    for label in answers:
        for symbol, meaning in answers[label]["variables"].items():
            variables.setdefault(symbol, meaning)
    return {
        "outcome": outcome,
        "kind": "none" if not kept else "specific" if "specific" in kinds else "unclear" if "unclear" in kinds else "generic",
        "requirements": kept,
        # The domain most models give; when they all differ, that of the first one asked
        "domain": max(domains, key=lambda d: (domains.count(d), -domains.index(d))) if domains else None,
        "variables": variables,
        "models": len(answers),
        # A formula read from a PDF page is a transcription: it counts when two models agree on it
        **(vote_formula(answers, order) if transcribed else {}),
    }


def collect(store: CorpusStore, contexts: dict, pairs: list[tuple[str, str]], tie_breaker: tuple[str, str] | None = None,
            answers_file: Path = ANSWERS_FILE) -> tuple[list[dict], dict]:
    """
    One record per formula with the answer of each model of `pairs`, and the calls of each model that are stored and
    current. Every record carries the outcome of the vote of the models (see vote). Where the first two models disagree and `tie_breaker` has a stored answer for the formula, the record
    also carries that answer and which of the two it sides with.
    """
    rows = latest_answers(answers_file)
    asked = pairs + ([tie_breaker] if tie_breaker and tie_breaker not in pairs else [])
    labels = [f"{model}:{reasoning}" for model, reasoning in asked]
    tie_label = labels[len(pairs)] if len(asked) > len(pairs) else None
    calls = {label: [] for label in labels}
    records = []
    fields = ("formula", "requirements", "domain", "variables", "problems")
    for pid, context in contexts.items():
        paper = store.papers[pid]
        for n, region in enumerate(context.regions, 1):
            answers, region_core = {}, passage_core(region.text)
            transcribed = isinstance(region, PdfRegion)
            for label, (model, reasoning) in zip(labels, asked):
                row = rows.get((model, reasoning, 1, pid, n))
                if row and not row.get("error") and matches_region(row, region):
                    recheck_stored(row["extractions"], region)   # the flags follow the checks as they are now
                    calls[label].append(row)
                    answers[label] = {e["id"]: e for e in row["extractions"]}
            for f in region.formulas:
                given = {label: answers[label].get(f.id) if label in answers else None for label in labels}
                record = {
                    "paper_id": pid, "formula_id": f.id, "title": context.title, "year": paper.get("year"),
                    "license_tier": (paper.get("license_info") or {}).get("tier"), "file": region.file, "line": f.line, "region": n,
                    "source": f.source, "source_type": "pdf" if transcribed else "latex",
                    "requirement_agreement": agreement(*[given[label] for label in labels[:2]]) if len(pairs) > 1 else None,
                    "domain_agreement": (given[labels[0]] or {}).get("domain") == (given[labels[1]] or {}).get("domain")
                                        if len(pairs) > 1 and all(given[label] for label in labels[:2]) else None,
                    "answers": {label: given[label] and {k: given[label][k] for k in fields} for label in labels[:len(pairs)]},
                }
                dispute = dispute_of(record, labels) if len(pairs) > 1 else None
                if dispute:
                    record["dispute"] = dispute
                    if tie_label and given[tie_label]:
                        tie_answer = given[tie_label]
                        record["tie_breaker"] = {
                            "model": tie_label, "verdict": verdict_of(tie_answer, given[labels[0]], given[labels[1]]),
                            "kind": kind_of(tie_answer), "answer": {k: tie_answer[k] for k in fields},
                        }
                record["final"] = vote({label: given[label] for label in labels}, region_core, prefer=[tie_label] if tie_label else [],
                                       transcribed=transcribed)
                if transcribed and record["final"].get("formula"):
                    # A displayed formula broken over two lines of the text is marked twice, and transcribed twice
                    key = formula_key(record["final"]["formula"])
                    first = next((r for r in records if r["paper_id"] == pid and r["region"] == n
                                  and r["final"].get("formula") and formula_key(r["final"]["formula"]) == key), None)
                    if first:
                        record["final"]["same_formula_as"] = first["formula_id"]
                records.append(record)
    return records, calls


def write_formulas(records: list[dict], formulas_file: Path = FORMULAS_FILE) -> None:
    formulas_file.parent.mkdir(parents=True, exist_ok=True)
    with open(formulas_file, "w", encoding="utf-8") as out:
        for record in records:
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
