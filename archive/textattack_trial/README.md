# TextAttack trial (step 8, November 2026) — archived

The first way tried to augment the dataset by paraphrasing its descriptions: [TextAttack](https://github.com/QData/TextAttack)'s
augmenters. It was rejected in favour of paraphrases written by an LLM (now step 9, `scripts/09_augment_dataset.py`).
This folder keeps the trial as it was run, so that the reasons can be read and shown.

**Read first: [`textattack_trial.md`](textattack_trial.md)**, the report written for readers who don't know the project
(the conclusion, the four methods, the results, the major problems with examples, every paraphrase).

## What was tried

- 30 correct descriptions of set 1, chosen at random with a fixed seed (`"augment-trial"`).
- Four TextAttack augmenters, one paraphrase each: `wordnet` (WordNet synonyms), `embedding` (nearby words in an
  embedding space), `eda` (Easy Data Augmentation), `backtranslation` (English → Spanish → English, MarianMT).
- The words that carry the formula were frozen, so the word-level augmenters couldn't change them: numbers, the
  formula's names, temporal, logical and comparison keywords, NLTK stopwords (`frozen_words` in `paraphrase.py`).
- Each paraphrase was judged against its formula by the LLM judge that step 7 had then (two models, a third on their
  disagreements; `judge.py`).

## Result

The judge labelled 74 of 109 changed paraphrases correct. Read by hand, though, most of the word-level ones are
broken English ("safety boundary" → "condom boundary", "the case" → "the pillowcase"), and signal names get swapped
(engine speed → acceleration). Hand estimate of usable paraphrases: wordnet ~4/18, embedding ~8/23, eda ~2/15,
backtranslation ~11/18. Back-translation is the best of the four, but it can't freeze words and its changes can't be
controlled.

## The files

| File | What it is |
|---|---|
| `textattack_trial.md` | The report (copied from `data/processed/augmentation/`, which git doesn't track) |
| `trial_paraphrases_input.jsonl` | What the worker read: id, description, frozen words |
| `trial_paraphrases.jsonl` | What TextAttack wrote: one line per description and method |
| `run_trial.py` | The TextAttack part of `scripts/08_augment_dataset.py` (`--method textattack --trial 30`) |
| `paraphrase.py` | Was `src/augmentation/paraphrase.py`: frozen words, the sample, the call to the worker, the checks |
| `textattack_worker.py` | Was `src/augmentation/textattack_worker.py`: runs the augmenters, in `.venv-augment` |
| `report.py` | Was `src/augmentation/report.py`, without the part of the LLM trial: writes `textattack_trial.md` |
| `judge.py` | Was `src/dataset/judge.py`: the judge of step 7, removed from the pipeline on 2026-11-25 |
| `requirements-augment.txt` | The environment of the worker (top of the file: how `.venv-augment` was made) |

## It doesn't run any more

The code is as it was in the pipeline, with the imports of that layout (`src.augmentation.paraphrase`,
`src.augmentation.report`, `src.dataset.judge`): those modules are no longer there, and the judge was removed from
the pipeline. Running it again would need them put back in place and `.venv-augment` made again: Python 3.10 (via
pyenv), CPU torch, `textattack==0.3.11` (TextAttack doesn't install in the project's Python 3.14).
