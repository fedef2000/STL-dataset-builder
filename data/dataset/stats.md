# STL dataset: statistics

3,255 records (one per formula with a requirement) from 730 papers, with 3,507 requirement passages.

| Source and bounds of the formula | Records | Share |
|---|---|---|
| latex · numeric | 1,705 | 52.4% |
| latex · symbolic | 1,093 | 33.6% |
| pdf · numeric | 330 | 10.1% |
| pdf · symbolic | 127 | 3.9% |

| Logic of the formula | Records | Share |
|---|---|---|
| propositional | 1,550 | 47.6% |
| stl | 1,544 | 47.4% |
| past-time | 92 | 2.8% |
| spatial-or-description | 35 | 1.1% |
| probabilistic | 29 | 0.9% |
| branching-time | 4 | 0.1% |
| strategic | 1 | 0.0% |

| Kind of requirement passage | Passages | Share |
|---|---|---|
| specific | 2,651 | 75.6% |
| generic | 687 | 19.6% |
| unclear | 169 | 4.8% |

| Licence tier | Records | Share |
|---|---|---|
| custom_or_arxiv | 2,398 | 73.7% |
| unspecified | 300 | 9.2% |
| permissive_cc | 296 | 9.1% |
| restricted_cc | 261 | 8.0% |

| Licence | Records | Share |
|---|---|---|
| arxiv-nonexclusive | 1,649 | 50.7% |
| cc-by | 954 | 29.3% |
| none | 300 | 9.2% |
| cc-by-nc-nd | 138 | 4.2% |
| cc-by-nc-sa | 117 | 3.6% |
| other-oa | 63 | 1.9% |
| cc-by-sa | 24 | 0.7% |
| cc0 | 7 | 0.2% |
| cc-by-nc | 3 | 0.1% |

| Domain | Records | Share |
|---|---|---|
| generic | 1,302 | 40.0% |
| mobile robotics | 644 | 19.8% |
| automotive | 505 | 15.5% |
| aerial robotics | 214 | 6.6% |
| smart city | 127 | 3.9% |
| robotic manipulation | 96 | 2.9% |
| epidemiology | 68 | 2.1% |
| industrial machinery | 54 | 1.7% |
| aviation | 53 | 1.6% |
| smart home | 51 | 1.6% |
| marine robotics | 44 | 1.4% |
| mechatronics | 39 | 1.2% |
| power systems | 33 | 1.0% |
| railway | 13 | 0.4% |
| social dynamics | 12 | 0.4% |

| How the formula was obtained | Records | Share |
|---|---|---|
| as in the LaTeX source | 2,795 | 85.9% |
| transcribed from the PDF page; two models agree | 457 | 14.0% |
| the whole marked LaTeX text: no model's copy was found in it | 3 | 0.1% |

164 records come from an answer that failed a check (`provenance.flags`).

## Subsets for fine-tuning

The records left as filters are added one after another. The last but one is the cleanest set: a formula over real-valued signals, with a passage that states it.

| Filter | Records | Papers |
|---|---|---|
| all records | 3,255 | 730 |
| ... with a specific passage | 2,455 | 664 |
| ... and logic `stl` | 1,085 | 387 |
| ... and no `provenance.flags` | 1,033 | 377 |

| Variant | Records | Papers |
|---|---|---|
| a specific passage, logic `stl` or `propositional` | 2,455 | 664 |

| Licence tier of the cleanest set | Records | Share |
|---|---|---|
| custom_or_arxiv | 794 | 73.2% |
| unspecified | 128 | 11.8% |
| restricted_cc | 85 | 7.8% |
| permissive_cc | 78 | 7.2% |

## Formulas without a requirement

6,592 formulas from 738 papers that the models agree have no requirement (`stl_formulas_unpaired.jsonl`): records with no passages.

| Source and bounds of the formula | Records | Share |
|---|---|---|
| latex · symbolic | 3,474 | 52.7% |
| latex · numeric | 2,244 | 34.0% |
| pdf · numeric | 494 | 7.5% |
| pdf · symbolic | 380 | 5.8% |

| Logic of the formula | Records | Share |
|---|---|---|
| propositional | 3,988 | 60.5% |
| stl | 2,329 | 35.3% |
| past-time | 222 | 3.4% |
| spatial-or-description | 33 | 0.5% |
| probabilistic | 14 | 0.2% |
| strategic | 6 | 0.1% |

| Licence tier | Records | Share |
|---|---|---|
| custom_or_arxiv | 4,824 | 73.2% |
| restricted_cc | 606 | 9.2% |
| permissive_cc | 591 | 9.0% |
| unspecified | 571 | 8.7% |

| Domain | Records | Share |
|---|---|---|
| generic | 5,158 | 78.2% |
| automotive | 548 | 8.3% |
| mobile robotics | 411 | 6.2% |
| industrial machinery | 69 | 1.0% |
| aerial robotics | 66 | 1.0% |
| robotic manipulation | 62 | 0.9% |
| marine robotics | 50 | 0.8% |
| epidemiology | 48 | 0.7% |
| smart city | 32 | 0.5% |
| power systems | 30 | 0.5% |
| mechatronics | 30 | 0.5% |
| social dynamics | 24 | 0.4% |
| railway | 24 | 0.4% |
| aviation | 23 | 0.3% |
| smart home | 17 | 0.3% |

## Left out

Formulas with a requirement (or undecided) that are not in the dataset (`excluded.jsonl`):

| Reason | Formulas |
|---|---|
| the same formula and requirement as another formula | 95 |
| undecided: no two models agree on a requirement | 84 |
| no two models transcribe the formula from the PDF alike | 56 |
| the formula is an operator alone, not a whole formula | 47 |
| the same formula as another formula, on another line of the PDF text | 47 |
| the requirement is not in English | 2 |

Formulas without a requirement that are not in `stl_formulas_unpaired.jsonl` (`excluded.jsonl`):

| Reason | Formulas |
|---|---|
| the same formula, without a requirement, as another formula | 692 |
| the formula is an operator alone, not a whole formula | 590 |
| no two models transcribe the formula from the PDF alike | 361 |
| the same formula as another formula, which has a requirement | 133 |
| the same formula as another formula, on another line of the PDF text | 65 |
