"""
The normalization of a file of records (step 6): one manifest line per record. The formulas without a requirement are
normalized in the stl-nl mode and checked with stlgen, the parser of stl-nl, which also gives their skeleton. The
paired formulas are normalized in the faithful mode (rules.py), which stlgen can't parse, as it keeps the paper's bounds
and powers: their skeleton comes from their own tree (stlgen_ast.py), and their requirement passages are written to
match the formula (description.py).
"""
from pathlib import Path

from config import RAW_LATEX_DIR
from src.normalization.description import normalize_description
from src.normalization.emit import stlnl_text
from src.normalization.latex import paper_macros
from src.normalization.normalize import normalize, with_fallback
from src.normalization.skeleton import skeleton
from src.normalization.stlgen_ast import formula as stlgen_ast
from src.normalization.validate import check, over_limits


def skeleton_of(ast, record_id: str) -> str:
    text, exact = skeleton(ast)
    if not exact:
        print(f"   {record_id}: too many interchangeable conditions to compare every renaming; its skeleton may "
              f"differ from an equal one")
    return text


def descriptions(record: dict, macros: dict, names: list[str]) -> list[dict]:
    """The record's requirement passages, each with its text written to match the formula and what couldn't be."""
    out = []
    for passage in record["requirements"]:
        d = normalize_description(passage["text"], macros=with_fallback(macros), formula_names=names)
        out.append({"text": passage["text"], "normalized": d.normalized, "unreadable": d.unreadable,
                    "references": d.references, "latex_left": d.latex_left,
                    "names_not_in_formula": d.names_not_in_formula})
    return out


def normalize_records(records: list[dict], seed: str, stlgen: Path | None, mode: str) -> list[dict]:
    """One manifest line per record (`stlgen` is only used in the stl-nl mode)."""
    macros_of, lines = {}, []
    for n, record in enumerate(records, 1):
        paper = record["paper_id"]
        if record["source_type"] == "latex" and paper not in macros_of:
            macros_of[paper] = paper_macros(RAW_LATEX_DIR / paper)
        macros = macros_of.get(paper, {}) if record["source_type"] == "latex" else {}
        result = normalize(record["formula"], record_id=record["id"], seed=seed, macros=macros,
                           variables=record.get("variables") or {},
                           flags=record["provenance"].get("flags", []), mode=mode)
        line = {"id": record["id"], "status": result.status, "file": None, "reasons": result.reasons,
                "rules": result.rules, "original": record["formula"], "normalized": result.normalized,
                "pattern": result.pattern, "skeleton": None,
                "stl": None, "substitutions": result.substitutions, "rounded": result.rounded, "over_limits": [],
                "bounds": record["bounds"], "source_type": record["source_type"]}
        if result.normalized is not None and mode == "stl-nl":
            parsed, error = check(result.normalized, stlgen)
            if parsed is None:
                line.update(status="rejected", reasons=[f"stlgen_error: {error}"], rules=result.rules + ["stlgen_error"],
                            normalized=None, pattern=None)
            else:
                line.update(stl=parsed["stl"], over_limits=over_limits(parsed),
                            skeleton=skeleton_of(parsed["ast"], record["id"]))
        elif result.normalized is not None:
            line["skeleton"] = skeleton_of(stlgen_ast(result.tree), record["id"])
            # The text as stl-nl prints it (what stlgen gives the unpaired formulas), for the final dataset
            line["stl"] = stlnl_text(result.tree)
            if result.status == "ok":
                line["requirements"] = descriptions(record, macros, result.names)
        lines.append(line)
        if n % 500 == 0:
            print(f"   {n}/{len(records)}")
    return lines
