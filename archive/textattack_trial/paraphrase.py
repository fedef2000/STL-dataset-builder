"""
Step 8: new descriptions of the dataset's formulas, made by paraphrasing its descriptions. For now a trial with
TextAttack (src/augmentation/textattack_worker.py, run in .venv-augment): its augmenters change single words (or,
back-translation, the whole sentence) and know nothing of which words the formula depends on. So:

- the words that carry the formula are frozen, so that no word augmenter changes them (frozen_words);
- each paraphrase is judged by the judge of step 7 against the formula (scripts/08_augment_dataset.py).
"""
import difflib
import json
import random
import re
import subprocess
from pathlib import Path

from config import BASE_DIR, PROCESSED_DIR

AUGMENT_DIR = PROCESSED_DIR / "augmentation"
AUGMENT_PYTHON = BASE_DIR / ".venv-augment" / "bin" / "python"
WORKER = Path(__file__).resolve().parent / "textattack_worker.py"
METHODS = ("wordnet", "embedding", "eda", "backtranslation")

# The words of the descriptions that say what the formula requires: temporal operators, logic, comparisons, time
# units. Frozen in every description, in addition to NLTK's English stopwords (which TextAttack freezes by default,
# and which already hold not, no, before, after, until, between, during, above, below, once, all, any, only, ...).
FROZEN_KEYWORDS = {
    # temporal operators and their usual wordings
    "always", "eventually", "never", "until", "unless", "within", "whenever", "every", "least", "most", "once",
    "globally", "finally", "release", "releases", "released", "next", "future", "now", "currently", "current",
    "consecutive", "consecutively", "continuously", "permanently", "forever", "persistently", "sometime",
    "sometimes", "later", "previous", "subsequently", "afterwards", "thereafter", "starting", "beginning",
    "since", "till", "throughout", "immediately", "instant", "moment", "point", "interval", "period", "window",
    "deadline", "time", "times", "step", "steps", "second", "seconds", "minute", "minutes", "hour", "hours",
    "ms", "unit", "units", "s", "sec", "min", "h",
    # logic
    "if", "then", "iff", "implies", "imply", "implied", "either", "neither", "nor", "both", "true", "false",
    "holds", "hold", "held", "satisfied", "satisfies", "satisfy", "violated", "must", "should", "shall", "cannot",
    "except", "whether", "otherwise", "also",
    # comparisons and quantities
    "greater", "less", "larger", "smaller", "higher", "lower", "exceed", "exceeds", "exceeding", "equal",
    "equals", "maximum", "minimum", "max", "min", "positive", "negative", "zero", "upper", "bound", "bounded",
    "bounds", "inside", "outside", "beyond", "reach", "reaches", "reached", "remain", "remains", "stay", "stays",
    "keep", "keeps", "avoid", "avoids", "far", "close", "near", "absolute", "value",
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "twice", "half", "percent",
}

# The words as TextAttack splits a text (textattack.shared.utils.words_from_text): letters, digits, ' - _ * @
WORD_RE = re.compile(r"[\w'\-*@]+")
NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def frozen_words(nl: str, stl: str) -> list[str]:
    """
    The words of a description that no augmenter may change, in lowercase: FROZEN_KEYWORDS, the names of the formula
    (signals, propositions, parameters), and every word of the description with a digit or an underscore, or of a
    single letter (numbers and symbols: 10, T_c, x_2, d).
    """
    names = {n.lower() for n in NAME_RE.findall(stl)}
    out = set()
    for word in WORD_RE.findall(nl):
        w = word.lower()
        if w in FROZEN_KEYWORDS or w in names or len(w) == 1 or "_" in w or any(c.isdigit() for c in w):
            out.add(w)
    return sorted(out)


def lost_frozen(original: str, paraphrase: str, frozen: list[str]) -> list[str]:
    """The frozen words that are fewer in the paraphrase than in the original (deleted, moved into a word, translated)."""
    count = lambda text, w: [x.lower() for x in WORD_RE.findall(text)].count(w)
    return [w for w in frozen if count(paraphrase, w) < count(original, w)]


def trial_sample(rows: list[dict], n: int, seed: str = "augment-trial") -> list[dict]:
    """n correct pairs at random (fixed seed), as stored in data/dataset/set_1/pairs.jsonl."""
    correct = sorted((r for r in rows if r["judge"]["label"] == "correct"), key=lambda r: r["id"])
    random.Random(seed).shuffle(correct)
    return sorted(correct[:n], key=lambda r: r["id"])


def run_worker(rows: list[dict], output: Path) -> list[dict]:
    """Runs the TextAttack worker in .venv-augment on the rows; returns its output lines, also written to `output`."""
    if not AUGMENT_PYTHON.exists():
        raise SystemExit(f"{AUGMENT_PYTHON.relative_to(BASE_DIR)} missing: create it with Python 3.10 and install "
                         "requirements-augment.txt (the commands are at its top)")
    output.parent.mkdir(parents=True, exist_ok=True)
    inputs = output.with_name(output.stem + "_input.jsonl")
    with open(inputs, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({"id": r["id"], "nl": r["nl"], "frozen": frozen_words(r["nl"], r["stl"])}, ensure_ascii=False) + "\n")
    subprocess.run([str(AUGMENT_PYTHON), str(WORKER), str(inputs), str(output)], check=True, cwd=BASE_DIR)
    return [json.loads(line) for line in open(output, encoding="utf-8") if line.strip()]


# ---------------------------------------------------------------- checks made without a model (reported, not filters)

TOKEN_RE = re.compile(r"\d+(?:\.\d+)?|[A-Za-z_][A-Za-z0-9_']*")
STL_OPERATORS = {"G", "F", "U", "R", "X", "inf"}


def missing_symbols(original: str, paraphrase: str, stl: str) -> list[str]:
    """
    The numbers and symbols of the original that the paraphrase doesn't have: words with a digit or an underscore,
    and the formula's names (compared in lowercase). Presence only: a symbol written once where the original repeats it
    is not missing.
    """
    names = {n.lower() for n in NAME_RE.findall(stl) if n not in STL_OPERATORS}
    kept = {t.lower() for t in TOKEN_RE.findall(paraphrase)}
    out = []
    for t in TOKEN_RE.findall(original):
        w = t.lower()
        if (any(c.isdigit() for c in w) or "_" in w or w in names) and w not in kept and w not in out:
            out.append(w)
    return out


def word_difference(original: str, paraphrase: str) -> float:
    """How different the words are, 0 (the same words in the same order) to 1 (no word in common): 1 - difflib's ratio."""
    a = [t.lower() for t in TOKEN_RE.findall(original)]
    b = [t.lower() for t in TOKEN_RE.findall(paraphrase)]
    return 1 - difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()
