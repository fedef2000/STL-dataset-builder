"""
The report of the TextAttack trial of step 8 (textattack_trial.md), written to be shared with readers who don't know
the project: what was tried, the conclusion, how the trial was done, the results, the problems with examples, then
every paraphrase. (Archived: the LLM trial's report was removed from this file.)

The conclusions, the problems and the counts "read by hand" are written by hand after reading every paraphrase of the
trial of 30 descriptions (seed "augment-trial"); the examples are given as (description id, method) and their text and
labels are taken from the data.
"""
import collections
import difflib
import statistics
from pathlib import Path

from src.augmentation.paraphrase import word_difference
from src.extraction.records import DEFAULT_TIE_BREAKER, parse_model

LABEL_ORDER = ("correct", "ambiguous", "wrong", "no", "undecided", "unchanged", "unjudged", "disputed")
LABELS_TEXT = ("*correct* (someone who knows STL would write this formula from it), *ambiguous* (it also fits other "
               "formulas), *wrong* (it contradicts the formula), *no* (it no longer describes the formula), "
               "*undecided* (the three models all differ)")


def short(label: str) -> str:
    return parse_model(label)[0].split("/")[-1]


def summary_table(rows: list[dict], methods: tuple, lost: bool = True) -> list[str]:
    """Per method: how many paraphrases got each label, and (with `lost`) how many lost a frozen word."""
    labels = [l for l in LABEL_ORDER if any(r["label"] == l for r in rows)]
    out = ["| Method | " + " | ".join(labels) + (" | lost a frozen word |" if lost else " |"),
           "|---|" + "---:|" * (len(labels) + lost)]
    for method in methods + ("all",):
        mine = [r for r in rows if method in ("all", r["method"])]
        counts = collections.Counter(r["label"] for r in mine)
        name = f"**{method}**" if method == "all" else method
        out.append(f"| {name} | " + " | ".join(str(counts[l]) for l in labels) + " |"
                   + (f" {sum(1 for r in mine if r['lost'])} |" if lost else ""))
    return out


def md(text: str) -> str:
    """Text safe in a Markdown table cell: no pipes, asterisks or tildes read as formatting."""
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("*", "\\*").replace("~", "\\~").replace("$", "\\$")


def highlight(original: str, paraphrase: str) -> str:
    """The paraphrase with the words it adds in bold and the words of the original it drops struck through."""
    a, b = original.split(), paraphrase.split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op in ("delete", "replace"):
            out.append("~~" + md(" ".join(a[i1:i2])) + "~~")
        if op in ("insert", "replace"):
            out.append("**" + md(" ".join(b[j1:j2])) + "**")
        if op == "equal":
            out.append(md(" ".join(b[j1:j2])))
    return " ".join(out)


def judge_line(r: dict) -> str:
    how = {"decided by the third model": " (third model)", "all three models differ": " (all three models differ)",
           "correct, ambiguous and wrong: the middle one": " (the three models differ)"}.get(r["how"], "")
    return f"{r['label']}{how}"


def judge_facts(items: list[dict], stored: dict, models: list[str]) -> tuple[int, float]:
    """(descriptions for which the third model was asked, dollars of all the judge calls)."""
    from src.dataset.judge import usable
    third = sum(1 for i in items if usable(stored.get((*parse_model(DEFAULT_TIE_BREAKER), i["set"], i["id"])), i))
    cost = sum(row.get("cost", 0) for i in items for label in models
               if usable(row := stored.get((*parse_model(label), i["set"], i["id"])), i))
    return third, cost


def reasons_block(rows: list[dict]) -> list[str]:
    """The judges' reasons for the paraphrases not labelled correct, collapsed."""
    reasons = [r for r in rows if r["label"] not in ("correct", "unchanged")]
    if not reasons:
        return []
    out = ["", "<details><summary>Why the judges said so</summary>", ""]
    for r in reasons:
        out.append(f"- **{r['method']}: {r['label']}**")
        out += [f"  - {a['model']}, {a['label']}: {md(a['reason'])}" for a in r["answers"]]
    return out + ["", "</details>"]


def examples_table(by_key: dict, examples: list[tuple], diff: bool) -> list[str]:
    out = ["| Formula | Original | Paraphrase | Judge |", "|---|---|---|---|"]
    for key in examples:
        r = by_key.get(key)
        if r and r["text"]:
            text = highlight(r["original"], r["text"]) if diff else md(r["text"])
            out.append(f"| `{md(r['stl'])}` | {md(r['original'])} | {text} | {judge_line(r)} |")
    return out


# ---------------------------------------------------------------- TextAttack

TEXTATTACK_METHODS = ("wordnet", "embedding", "eda", "backtranslation")
TEXTATTACK_METHOD_TEXT = {
    "wordnet": "replaces about 10% of the words with a synonym from WordNet, a general-purpose English thesaurus.",
    "embedding": "replaces about 10% of the words with a nearby word in a word-embedding space (vectors trained to keep "
                 "synonyms close and antonyms apart), only if it is very similar (cosine similarity at least 0.8).",
    "eda": "Easy Data Augmentation: one random operation on about 10% of the words: replace with a WordNet synonym, "
           "delete, swap two words, or insert a synonym of some word at a random place.",
    "backtranslation": "translates the sentence into Spanish and back into English with a machine-translation model "
                       "(MarianMT), so the whole sentence is rewritten.",
}
# Of the paraphrases the judge labelled correct, those that read as natural English (read by hand)
TEXTATTACK_NATURAL = {"wordnet": 4, "embedding": 8, "eda": 2, "backtranslation": 11}
TEXTATTACK_CONCLUSION = (
    "TextAttack is not a good way to paraphrase our descriptions. Its word-level methods (wordnet, embedding, eda) "
    "mostly produce broken or odd English, and the judge doesn't filter that out: it checks whether a paraphrase still "
    "matches the formula, not whether it is good English. Read by hand, only about a third of the paraphrases the "
    "judge calls correct read as natural English (about 25 of 74), and back-translation gives the largest share of them (about 11). "
    "Back-translation writes fluent sentences, but it rewrites the whole sentence, so it can't be told which words to keep, "
    "and it sometimes alters numbers and names. Even the good paraphrases change only one or two words, so they add little variety."
)
TEXTATTACK_PROBLEMS = [
    ("Synonyms from the wrong meaning",
     "WordNet and EDA take a synonym from any meaning of a word, not the one in the sentence. The formula is still "
     "matched, so the judge says correct: the judge doesn't catch this problem.",
     [("W3210726654:F1:D1", "wordnet"), ("W4403799341:F1:D1", "wordnet")]),
    ("Broken grammar and word order",
     "Word swaps, insertions and inflected forms give sentences no one would write.",
     [("arxiv_2207.00627:F16:D1", "eda"), ("W2470448410:F5:D1", "embedding")]),
    ("The quantity being constrained changes",
     "Words that carry the formula (numbers, the formula's names, temporal and logical words) were frozen, but "
     "descriptions often name a signal in plain English, a name that isn't in the formula, so it can be replaced.",
     [("W2221585980:F9:D1", "embedding"), ("W2221585980:F9:D1", "wordnet")]),
    ("Back-translation is fluent but can't be controlled",
     "It rewrites the whole sentence, so no word can be frozen: intervals, names and objects can change.",
     [("W3198638775:F1:D1", "backtranslation"), ("W2470448410:F5:D1", "backtranslation"),
      ("W4403799341:F1:D1", "backtranslation")]),
    ("Little variety",
     "The word methods change about 10% of the words (one to three in our descriptions), so a paraphrase is a near "
     "copy of the original; some descriptions had nothing that could be changed.",
     [("W2221585980:F9:D1", "backtranslation")]),
]


def write_textattack_report(path: Path, rows: list[dict], sample: list[dict], items: list[dict], stored: dict, models: list[str]):
    by_key = {(r["id"], r["method"]): r for r in rows}
    judged = [r for r in rows if r["label"] != "unchanged"]
    third, cost = judge_facts(items, stored, models)
    out = ["# Paraphrasing STL descriptions with TextAttack: a trial", "",
           "We want more training pairs (natural-language description, STL formula) by paraphrasing the descriptions "
           "we have. We tried [TextAttack](https://github.com/QData/TextAttack), a Python library for adversarial "
           "attacks and data augmentation in NLP, whose augmenters make new versions of a sentence by changing some of "
           "its words or rewriting it.", "",
           "## In short", "", TEXTATTACK_CONCLUSION, "",
           "## The four methods", "",
           "| Method | What it does |", "|---|---|"]
    out += [f"| {m} | {TEXTATTACK_METHOD_TEXT[m]} |" for m in TEXTATTACK_METHODS]
    out += ["", "## How the trial was done", "",
            f"- **Sample:** {len(sample)} descriptions of set 1 (formula and description from papers) that the "
            "dataset's judge had labelled correct, picked at random with a fixed seed.",
            f"- **Paraphrases:** one per method and description, {len(rows)} in all; {len(rows) - len(judged)} were "
            "identical to the original (the method found nothing to change) and are not judged.",
            "- **Frozen words:** the word methods were not allowed to change numbers, the names in the formula "
            "(signals, parameters), symbols such as `x_2` or `d`, temporal and logical words (always, eventually, "
            "until, within, not, at least, ...), comparisons (above, below, exceeds, ...), time units, and common English "
            "stopwords. Back-translation rewrites the whole sentence, so it can't freeze words.",
            f"- **Judge:** each paraphrase was checked against its formula by the same LLM judge used to build the "
            "dataset: two models label it, and a third decides when they disagree (here the third was needed for some paraphrase of "
            f"{third} of the {len(items)} descriptions). Labels: {LABELS_TEXT}.",
            f"- **Cost:** ${cost:.2f} of judge calls.", "",
            "## Results", "",
            "Paraphrases per label, by method:", ""]
    out += summary_table(rows, TEXTATTACK_METHODS, lost=False)
    out += ["", "The judge's labels look good, but the judge checks the meaning against the formula, not the "
            "language: many paraphrases labelled correct are broken English (see below).", "",
            "## Major problems", "",
            "In the examples, **bold** marks the words the method put in and ~~struck~~ the words it removed.", ""]
    for n, (title, text, examples) in enumerate(TEXTATTACK_PROBLEMS, 1):
        out += [f"### {n}. {title}", "", text, ""] + examples_table(by_key, examples, diff=True) + [""]
    out += ["## Every paraphrase", "",
            "For each description: its formula, the original, and the paraphrase of each method. Under the table, the "
            "judges' reasons for the paraphrases not labelled correct.", ""]
    for row in sample:
        mine = [by_key[(row["id"], m)] for m in TEXTATTACK_METHODS if (row["id"], m) in by_key]
        out += [f"### {row['id']}", "", f"Formula: `{md(row['stl'])}`", "", f"Original: {md(row['nl'])}", "",
                "| Method | Judge | Paraphrase |", "|---|---|---|"]
        for r in mine:
            method = r["method"] + (f" ({r['operation'][4:]})" if r["operation"] and r["operation"].startswith("eda_") else "")
            text = highlight(row["nl"], r["text"]) if r["label"] != "unchanged" else "*(nothing changed)*"
            out.append(f"| {method} | {judge_line(r) if r['label'] != 'unchanged' else '—'} | {text} |")
        out += reasons_block(mine) + [""]
    path.write_text("\n".join(out), encoding="utf-8")
