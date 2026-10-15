# STL dataset: statistics

3,255 records (one per formula with a requirement) from 730 papers, with 3,507 requirement passages.

| Source and kind of formula | Records | Share |
|---|---|---|
| latex · concrete | 1,705 | 52.4% |
| latex · parametric | 1,093 | 33.6% |
| pdf · concrete | 330 | 10.1% |
| pdf · parametric | 127 | 3.9% |

| Quality of the requirement | Records | Share |
|---|---|---|
| specific | 2,455 | 75.4% |
| generic | 655 | 20.1% |
| unclear | 145 | 4.5% |

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

## Left out

Formulas with a requirement that are not in the dataset (`excluded.jsonl`):

| Reason | Formulas |
|---|---|
| the same formula and requirement as another record | 95 |
| undecided: no two models agree on a requirement | 84 |
| no two models transcribe the formula from the PDF alike | 56 |
| the formula is an operator alone, not a whole formula | 47 |
| the same formula as another line of the PDF text | 47 |
| the requirement is not in English | 2 |
