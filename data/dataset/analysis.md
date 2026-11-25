# Analysis of the dataset

The dataset is: set 1's pairs whose formula a model wrote back from the description alone (the round trip of step 8), with those kept or fixed by hand; every pair of sets 2 and 3 (not checked by the round trip yet). Patterns, domains and operators count formulas, not descriptions (in sets 2 and 3 each formula has two descriptions); a formula is counted once per set, and the total adds the three sets. The paraphrases of step 9 are counted apart.

## Size

Paraphrases: those step 9 adds to the descriptions (see Paraphrases below); they have the formulas of their originals, so they add no formula.

| Set | Descriptions | Paraphrases | Formulas |
|---|---|---|---|
| set_1 | 568 | 1073 | 554 |
| set_2 | 2378 | 0 | 1189 |
| set_3 | 2000 | 0 | 1000 |
| total | 4946 | 1073 | 2743 |

## Set 1: round trip

Every description of set 1 is a candidate; the round trip of step 8 (a model writes the formula from the description alone) decides which are in the dataset: those at least one of its two models wrote back, and those kept or fixed by hand after reading them. Out: neither model wrote the formula back, stlgen can't read the formula (not checkable), or dropped by hand.

| Candidates | In the dataset | Match | Kept or fixed by hand | Out | both miss | not checkable | dropped by hand |
|---|---|---|---|---|---|---|---|
| 1712 | 33.2% | 531 | 37 | 1144 | 1035 | 106 | 3 |

## Paraphrases

Step 9: a model writes two paraphrases of each pair of set 1 in the dataset, keeping its numbers, symbols and meaning; the round trip of step 8 keeps those a model writes back into the formula, as for set 1. Missing a symbol: the paraphrases in the dataset that lack a number or symbol of their original. Word difference: how different the words of a paraphrase are from its original's, 0 (the same words in the same order) to 1 (no word in common); in the trial of TextAttack (archive/textattack_trial/), its word-level augmenters gave 0.08 and back-translation 0.22.

| Set | Descriptions paraphrased | Formulas | Paraphrases | Out (round trip or by hand) | Missing a symbol | Word difference |
|---|---|---|---|---|---|---|
| set_1 | 555 | 542 | 1073 | 63 | 10 | 0.55 |

## Patterns

The pattern of a formula: its temporal and Boolean structure, each condition a Greek letter, every bound `#` (or `inf`), computed as in step 6. The full list, with the formulas of each set, is in `patterns.csv`.

| Set | Formulas | Patterns | Top 10 cover |
|---|---|---|---|
| set_1 | 554 | 103 | 73.8% |
| set_2 | 1189 | 418 | 35.6% |
| set_3 | 1000 | 401 | 25.5% |
| total | 2743 | 810 | 35.7% |

### The 10 most common patterns of the dataset

Formulas of each set with the pattern, and their share of that set's formulas.

| Pattern | set_1 | set_2 | set_3 | total |
|---|---|---|---|---|
| `G[#,#] φ` | 120 (21.7%) | 107 (9.0%) | 32 (3.2%) | 259 (9.4%) |
| `F[#,#] φ` | 120 (21.7%) | 85 (7.1%) | 29 (2.9%) | 234 (8.5%) |
| `φ U[#,#] ψ` | 59 (10.6%) | 25 (2.1%) | 17 (1.7%) | 101 (3.7%) |
| `G[#,#] F[#,#] φ` | 18 (3.2%) | 45 (3.8%) | 20 (2.0%) | 83 (3.0%) |
| `F[#,#] G[#,#] φ` | 16 (2.9%) | 19 (1.6%) | 27 (2.7%) | 62 (2.3%) |
| `G[#,inf] (φ -> F[#,#] ψ)` | 30 (5.4%) | 14 (1.2%) | 10 (1.0%) | 54 (2.0%) |
| `(F[#,#] φ) && (G[#,#] ψ)` | 7 (1.3%) | 41 (3.4%) | 0 (0.0%) | 48 (1.7%) |
| `G[#,#] (φ && ψ)` | 9 (1.6%) | 37 (3.1%) | 1 (0.1%) | 47 (1.7%) |
| `G[#,#] (φ -> F[#,#] ψ)` | 4 (0.7%) | 18 (1.5%) | 25 (2.5%) | 47 (1.7%) |
| `G[#,inf] φ` | 17 (3.1%) | 22 (1.9%) | 6 (0.6%) | 45 (1.6%) |

### The 10 most common patterns of set_1

| Pattern | Formulas | Share |
|---|---|---|
| `F[#,#] φ` | 120 | 21.7% |
| `G[#,#] φ` | 120 | 21.7% |
| `φ U[#,#] ψ` | 59 | 10.6% |
| `G[#,inf] (φ -> F[#,#] ψ)` | 30 | 5.4% |
| `G[#,#] F[#,#] φ` | 18 | 3.2% |
| `G[#,inf] φ` | 17 | 3.1% |
| `F[#,#] G[#,#] φ` | 16 | 2.9% |
| `G[#,#] !φ` | 13 | 2.3% |
| `G[#,#] (φ && ψ)` | 9 | 1.6% |
| `(F[#,#] φ) && (G[#,#] ψ)` | 7 | 1.3% |

### The 10 most common patterns of set_2

| Pattern | Formulas | Share |
|---|---|---|
| `G[#,#] φ` | 107 | 9.0% |
| `F[#,#] φ` | 85 | 7.1% |
| `G[#,#] F[#,#] φ` | 45 | 3.8% |
| `(F[#,#] φ) && (G[#,#] ψ)` | 41 | 3.4% |
| `G[#,#] (φ && ψ)` | 37 | 3.1% |
| `φ U[#,#] ψ` | 25 | 2.1% |
| `G[#,inf] φ` | 22 | 1.9% |
| `F[#,#] (φ && ψ)` | 22 | 1.9% |
| `(F[#,#] φ) && (F[#,#] ψ)` | 20 | 1.7% |
| `F[#,#] G[#,#] φ` | 19 | 1.6% |

### The 10 most common patterns of set_3

| Pattern | Formulas | Share |
|---|---|---|
| `φ R[#,#] ψ` | 42 | 4.2% |
| `G[#,#] φ` | 32 | 3.2% |
| `F[#,#] φ` | 29 | 2.9% |
| `F[#,#] G[#,#] φ` | 27 | 2.7% |
| `G[#,#] !(φ && ψ)` | 26 | 2.6% |
| `G[#,#] (φ -> F[#,#] ψ)` | 25 | 2.5% |
| `G[#,#] F[#,#] φ` | 20 | 2.0% |
| `(G[#,#] φ) -> G[#,#] ψ` | 18 | 1.8% |
| `(F[#,#] φ) -> F[#,#] ψ` | 18 | 1.8% |
| `G[#,#] F[#,#] G[#,#] φ` | 18 | 1.8% |

## Domains

In sets 1 and 2 the domain is the one step 5's models read in the paper (`generic`: an abstract example, with no application); in set 3 stl-nl's generator assigns it, spreading the formulas over its 17 domains (two of them, `medical devices` and `cloud computing`, are not among step 5's).

| Domain | set_1 | set_2 | set_3 | total |
|---|---|---|---|---|
| generic | 346 (62.5%) | 663 (55.8%) | 58 (5.8%) | 1067 (38.9%) |
| automotive | 78 (14.1%) | 225 (18.9%) | 63 (6.3%) | 366 (13.3%) |
| mobile robotics | 59 (10.6%) | 120 (10.1%) | 49 (4.9%) | 228 (8.3%) |
| marine robotics | 3 (0.5%) | 25 (2.1%) | 81 (8.1%) | 109 (4.0%) |
| aerial robotics | 12 (2.2%) | 20 (1.7%) | 51 (5.1%) | 83 (3.0%) |
| industrial machinery | 3 (0.5%) | 24 (2.0%) | 55 (5.5%) | 82 (3.0%) |
| robotic manipulation | 8 (1.4%) | 19 (1.6%) | 54 (5.4%) | 81 (3.0%) |
| medical devices | 0 (0.0%) | 0 (0.0%) | 81 (8.1%) | 81 (3.0%) |
| smart city | 14 (2.5%) | 5 (0.4%) | 60 (6.0%) | 79 (2.9%) |
| railway | 3 (0.5%) | 21 (1.8%) | 55 (5.5%) | 79 (2.9%) |
| power systems | 3 (0.5%) | 7 (0.6%) | 67 (6.7%) | 77 (2.8%) |
| social dynamics | 4 (0.7%) | 22 (1.9%) | 48 (4.8%) | 74 (2.7%) |
| mechatronics | 5 (0.9%) | 10 (0.8%) | 58 (5.8%) | 73 (2.7%) |
| epidemiology | 2 (0.4%) | 16 (1.3%) | 52 (5.2%) | 70 (2.6%) |
| smart home | 8 (1.4%) | 6 (0.5%) | 51 (5.1%) | 65 (2.4%) |
| cloud computing | 0 (0.0%) | 0 (0.0%) | 65 (6.5%) | 65 (2.4%) |
| aviation | 6 (1.1%) | 6 (0.5%) | 52 (5.2%) | 64 (2.3%) |

## Operators

Share of the formulas of each set that hold each operator.

| Operator | set_1 | set_2 | set_3 | total |
|---|---|---|---|---|
| `G` | 61.6% | 69.6% | 59.4% | 64.2% |
| `F` | 52.0% | 60.4% | 66.7% | 61.0% |
| `U` | 13.2% | 13.5% | 5.5% | 10.5% |
| `R` | 0.0% | 0.8% | 12.0% | 4.7% |
| `!` | 8.8% | 16.5% | 31.1% | 20.3% |
| `&&` | 16.2% | 41.9% | 38.7% | 35.5% |
| `\|\|` | 2.2% | 15.1% | 24.1% | 15.8% |
| `->` | 13.2% | 15.0% | 40.7% | 24.0% |
