"""
The paraphrases of TextAttack (step 8). This file runs in its own environment, .venv-augment (Python 3.10, with
requirements-augment.txt): TextAttack pins versions of torch and transformers that don't install in the project's
.venv. So it imports nothing of the project; scripts/08_augment_dataset.py runs it as a separate process:

    .venv-augment/bin/python src/augmentation/textattack_worker.py INPUT.jsonl OUTPUT.jsonl

INPUT has one line per description: {"id", "nl", "frozen"}, where `frozen` lists the words (lowercase) that no
augmenter may change (src/augmentation/paraphrase.py decides them). OUTPUT has one line per description and method:
{"id", "method", "operation", "text"}, `text` null when the method found nothing to change.

The methods, one paraphrase each, with TextAttack's settings of its recipes (textattack/augmentation/recipes.py):
    wordnet       WordNet synonyms in place of 10% of the words (WordNetAugmenter)
    embedding     the nearest words in counter-fitted embeddings, cosine similarity >= 0.8, for 10% of the words
                  (EmbeddingAugmenter)
    eda           one of the four operations of Easy Data Augmentation on 10% of the words, picked at random:
                  synonym (WordNet), deletion, swap of two words, insertion of a synonym (EasyDataAugmenter)
    backtranslation   English -> Spanish -> English with MarianMT, one round (BackTranslation; the recipe chains five
                  random languages, which drifts further from the original)

The recipes are rebuilt here rather than called, so that every word method gets our constraint: the recipes fix
their constraints (RepeatModification, StopwordModification with NLTK's English stopwords), and the stopwords are
kept frozen too. Back-translation rewrites the whole sentence: no word can be frozen in it.
"""
import json
import random
import sys
import warnings
import zlib

warnings.filterwarnings("ignore")

import nltk
from textattack.augmentation import Augmenter
from textattack.constraints import PreTransformationConstraint
from textattack.constraints.pre_transformation import RepeatModification
from textattack.constraints.semantics import WordEmbeddingDistance
from textattack.transformations import (WordDeletion, WordInnerSwapRandom, WordInsertionRandomSynonym,
                                        WordSwapEmbedding, WordSwapWordNet)
from textattack.transformations.sentence_transformations import BackTranslation

PCT_WORDS_TO_SWAP = 0.1   # TextAttack's default, as in every recipe
STOPWORDS = set(nltk.corpus.stopwords.words("english"))


class FrozenWords(PreTransformationConstraint):
    """No change at a word that is a stopword or in `frozen` (compared in lowercase)."""

    def __init__(self, frozen):
        self.frozen = {w.lower() for w in frozen} | STOPWORDS

    def _get_modifiable_indices(self, current_text):
        return {i for i, word in enumerate(current_text.words) if word.lower() not in self.frozen}

    def check_compatibility(self, transformation):
        return True


def augmenters(transformations: dict, frozen: list[str]) -> dict:
    """The augmenters of one description: the shared transformations with the constraints of its frozen words."""
    constraints = [RepeatModification(), FrozenWords(frozen)]
    made = {}
    for name, (transformation, extra) in transformations.items():
        made[name] = Augmenter(transformation, constraints=constraints + extra, pct_words_to_swap=PCT_WORDS_TO_SWAP,
                               transformations_per_example=1)
    return made


def paraphrase(made: dict, method: str, text: str, rng: random.Random) -> tuple[str | None, str | None]:
    """(operation, text) of one method; text None when nothing could change."""
    if method == "eda":
        operations = ["eda_synonym", "eda_deletion", "eda_swap", "eda_insertion"]
        rng.shuffle(operations)
        for operation in operations:   # as EasyDataAugmenter: one of the four, at random (the next if it gives nothing)
            out = [t for t in made[operation].augment(text) if t != text]
            if out:
                return operation, out[0]
        return None, None
    out = [t for t in made[method].augment(text) if t != text]
    return method, (out[0] if out else None)


def main(input_path: str, output_path: str):
    rows = [json.loads(line) for line in open(input_path, encoding="utf-8") if line.strip()]
    print(f"Loading the transformations (the first run downloads WordNet, the embeddings and MarianMT)...", flush=True)
    transformations = {
        "wordnet": (WordSwapWordNet(), []),
        "embedding": (WordSwapEmbedding(max_candidates=50), [WordEmbeddingDistance(min_cos_sim=0.8)]),
        "eda_synonym": (WordSwapWordNet(), []),
        "eda_deletion": (WordDeletion(), []),
        "eda_swap": (WordInnerSwapRandom(), []),
        "eda_insertion": (WordInsertionRandomSynonym(), []),
    }
    back = Augmenter(BackTranslation(), transformations_per_example=1)
    with open(output_path, "w", encoding="utf-8") as out:
        for n, row in enumerate(rows, 1):
            made = augmenters(transformations, row["frozen"])
            for method in ("wordnet", "embedding", "eda", "backtranslation"):
                # The same description and method give the same paraphrase on every run
                seed = zlib.crc32(f"{row['id']}|{method}".encode())
                random.seed(seed)
                rng = random.Random(seed)
                if method == "backtranslation":
                    texts = [t for t in back.augment(row["nl"]) if t != row["nl"]]
                    operation, text = method, (texts[0] if texts else None)
                else:
                    operation, text = paraphrase(made, method, row["nl"], rng)
                out.write(json.dumps({"id": row["id"], "method": method, "operation": operation, "text": text},
                                     ensure_ascii=False) + "\n")
            out.flush()
            print(f"   {n}/{len(rows)} descriptions", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
