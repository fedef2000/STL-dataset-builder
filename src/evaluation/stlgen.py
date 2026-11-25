"""
Formula text to tree with stl-nl's parser: `stlgen parse` reads one formula per JSONL line and answers, line by line,
either the tree (the AST that `stlgen import` writes) or the parser's error. One call parses any number of formulas,
and a formula that doesn't parse doesn't stop the others.
"""
import json
import subprocess
import tempfile
from pathlib import Path

from config import STLGEN_BIN


class StlgenError(Exception):
    """stlgen is missing, too old (no `parse` command), or failed on the whole file."""


def parse_many(texts: dict[str, str], binary: Path = STLGEN_BIN, timeout: int = 600) -> dict[str, dict]:
    """
    {id: formula text} -> {id: {"ok": True, "ast": ..., "stl": ...} or {"ok": False, "error": ...}}; ids are strings.
    "stl" is the formula as stlgen prints it (decimals as fractions, X as F[1,1]).
    """
    if not texts:
        return {}
    binary = Path(binary)
    if not binary.is_file():
        raise StlgenError(f"stlgen not found at {binary} (set STLGEN_BIN or build it: cargo build --release)")
    with tempfile.TemporaryDirectory(prefix="stlgen-parse-") as directory:
        source, target = Path(directory) / "texts.jsonl", Path(directory) / "parsed.jsonl"
        source.write_text("".join(json.dumps({"id": i, "stl": t}) + "\n" for i, t in texts.items()), encoding="utf-8")
        result = subprocess.run([str(binary), "parse", "--input", str(source), "--output", str(target)],
                                capture_output=True, text=True, timeout=timeout, check=False)
        if result.returncode != 0:
            hint = " (a build without the parse command? rebuild stlgen)" if "parse" in result.stderr else ""
            raise StlgenError(f"stlgen parse exited {result.returncode}{hint}: {result.stderr.strip()[:500]}")
        lines = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
    if [line["id"] for line in lines] != list(texts):
        raise StlgenError("stlgen parse returned other ids, or in another order, than it was given")
    return {line.pop("id"): line for line in lines}
