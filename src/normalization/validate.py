"""
The check of the normalized formulas with the parser of stl-nl itself: `stlgen import`, one formula at a time, as the
import stops at the first file it can't parse.
"""
import json
import subprocess
import tempfile
from pathlib import Path

# The selection limits of stl-nl (Python CLI defaults): formulas over them are skipped when stl-nl selects its input
SELECTION_LIMITS = {"node_count": 2000, "syntax_depth": 32, "text_chars": 20000}


def check(formula: str, stlgen: Path) -> tuple[dict | None, str | None]:
    """(the record stlgen makes of the formula, None) when it parses; (None, stlgen's message) otherwise."""
    with tempfile.TemporaryDirectory() as directory:
        (Path(directory) / "f.stl").write_text(formula + "\n", encoding="utf-8")
        run = subprocess.run([str(stlgen), "import", "--input-dir", directory, "--output", "-"],
                             capture_output=True, text=True, encoding="utf-8")
    if run.returncode != 0:
        message = run.stderr.strip().splitlines()[-1] if run.stderr.strip() else f"exit code {run.returncode}"
        return None, message.replace(f"{directory}/f.stl: ", "")
    return json.loads(run.stdout.splitlines()[0]), None


def over_limits(record: dict) -> list[str]:
    """The selection limits of stl-nl the formula is over (by its stlgen statistics)."""
    statistics = record["statistics"]
    return [f"{k} {statistics[k]} > {limit}" for k, limit in SELECTION_LIMITS.items() if statistics[k] > limit]
