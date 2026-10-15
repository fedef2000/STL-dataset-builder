# STL dataset: statistics

3,255 records (one per formula with a requirement), with 3,507 requirement passages.



| Construct of another logic | Records | Share |
|---|---|---|
| none found | 3,094 | 95.1% |
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

**specific**: it states what the formula says: e.g. "the predicted Air Quality Index should never exceed 50 in the next two hours" for `\always_{[0,2]} AQI < 50`

 **generic**:  it only says what the formula is for, without what is needed to write it, e.g. "reaching a goal while avoiding an obstacle" 

 **unclear**:  the models disagree on the kind
| Licence tier | Records | Share |
|---|---|---|
| custom_or_arxiv | 1,712 | 52.6% |
| permissive_cc | 982 | 30.2% |
| unspecified | 300 | 9.2% |
| restricted_cc | 261 | 8.0% |

| Licence | Records | Share |
|---|---|---|
| arxiv-nonexclusive | 1,649 | 50.7% |
| cc-by | 955 | 29.3% |
| none | 300 | 9.2% |
| cc-by-nc-nd | 141 | 4.3% |
| cc-by-nc-sa | 117 | 3.6% |
| other-oa | 63 | 1.9% |
| cc-by-sa | 20 | 0.6% |
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


## Best quality subset


| Filter | Records | Papers |
|---|---|---|
| all records | 3,255 | 730 |
| ... with a specific passage | 2,455 | 664 |
| ... and no `other_logic` | 2,315 | 642 |

| Licence tier of the cleanest set | Records | Share |
|---|---|---|
| custom_or_arxiv | 1,248 | 53.9% |
| permissive_cc | 668 | 28.9% |
| unspecified | 221 | 9.5% |
| restricted_cc | 178 | 7.7% |

## Formulas without a requirement

6,592 formulas that the models agree have no requirement (`stl_formulas_unpaired.jsonl`): records with no passages.

 |

| Construct of another logic | Records | Share |
|---|---|---|
| none found | 6,317 | 95.8% |
| past-time | 222 | 3.4% |
| spatial-or-description | 33 | 0.5% |
| probabilistic | 14 | 0.2% |
| strategic | 6 | 0.1% |

| Licence tier | Records | Share |
|---|---|---|
| custom_or_arxiv | 3,410 | 51.7% |
| permissive_cc | 2,005 | 30.4% |
| restricted_cc | 606 | 9.2% |
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
