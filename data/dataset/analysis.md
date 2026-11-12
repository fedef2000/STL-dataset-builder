# Analysis of the dataset

The dataset is: set 1's correct and ambiguous pairs; sets 2 and 3's pairs except the few the judge's sample found wrong, not a description, or undecided (the pairs outside the sample are not judged and are kept). Patterns, domains and operators count formulas, not descriptions (in sets 2 and 3 each formula has two descriptions); a formula is counted once per set, and the total adds the three sets.

## Size

| Set | Descriptions | Formulas |
|---|---|---|
| set_1 | 998 | 963 |
| set_2 | 2373 | 1188 |
| set_3 | 1994 | 1000 |
| total | 5365 | 3151 |

## Judge

Labels of the descriptions judged: every description of set 1, a sample of 500 formulas (1,000 descriptions) of sets 2 and 3. `No`: the description is not a description of the formula (it only says what the formula is for, describes a part of it, or something else). The rest of the judged descriptions are undecided (the three models gave three different labels).

| Set | Judged | Correct | Ambiguous | Wrong | No (not a description) |
|---|---|---|---|---|---|
| set_1 | 1719 | 573 (33.3%) | 425 (24.7%) | 126 (7.3%) | 537 (31.2%) |
| set_2 | 1000 | 987 (98.7%) | 8 (0.8%) | 2 (0.2%) | 0 (0.0%) |
| set_3 | 1000 | 988 (98.8%) | 6 (0.6%) | 2 (0.2%) | 0 (0.0%) |

## Patterns

The pattern of a formula: its temporal and Boolean structure, each condition a Greek letter, every bound `#` (or `inf`), computed as in step 6. The full list, with the formulas of each set, is in `patterns.csv`.

| Set | Formulas | Patterns | Top 10 cover |
|---|---|---|---|
| set_1 | 963 | 212 | 62.4% |
| set_2 | 1188 | 418 | 35.6% |
| set_3 | 1000 | 401 | 25.5% |
| total | 3151 | 886 | 37.3% |

### The 10 most common patterns of the dataset

Formulas of each set with the pattern, and their share of that set's formulas.

| Pattern | set_1 | set_2 | set_3 | total |
|---|---|---|---|---|
| `G[#,#] φ` | 199 (20.7%) | 107 (9.0%) | 32 (3.2%) | 338 (10.7%) |
| `F[#,#] φ` | 158 (16.4%) | 85 (7.2%) | 29 (2.9%) | 272 (8.6%) |
| `φ U[#,#] ψ` | 72 (7.5%) | 25 (2.1%) | 17 (1.7%) | 114 (3.6%) |
| `G[#,#] F[#,#] φ` | 22 (2.3%) | 45 (3.8%) | 20 (2.0%) | 87 (2.8%) |
| `G[#,#] (φ && ψ)` | 32 (3.3%) | 37 (3.1%) | 1 (0.1%) | 70 (2.2%) |
| `F[#,#] G[#,#] φ` | 24 (2.5%) | 19 (1.6%) | 27 (2.7%) | 70 (2.2%) |
| `G[#,inf] (φ -> F[#,#] ψ)` | 39 (4.0%) | 14 (1.2%) | 10 (1.0%) | 63 (2.0%) |
| `G[#,#] (φ -> F[#,#] ψ)` | 18 (1.9%) | 18 (1.5%) | 25 (2.5%) | 61 (1.9%) |
| `(F[#,#] φ) && (G[#,#] ψ)` | 14 (1.5%) | 41 (3.5%) | 0 (0.0%) | 55 (1.7%) |
| `G[#,inf] φ` | 17 (1.8%) | 22 (1.9%) | 6 (0.6%) | 45 (1.4%) |

### The 10 most common patterns of set_1

| Pattern | Formulas | Share |
|---|---|---|
| `G[#,#] φ` | 199 | 20.7% |
| `F[#,#] φ` | 158 | 16.4% |
| `φ U[#,#] ψ` | 72 | 7.5% |
| `G[#,inf] (φ -> F[#,#] ψ)` | 39 | 4.0% |
| `G[#,#] (φ && ψ)` | 32 | 3.3% |
| `F[#,#] G[#,#] φ` | 24 | 2.5% |
| `G[#,#] F[#,#] φ` | 22 | 2.3% |
| `G[#,#] !φ` | 20 | 2.1% |
| `G[#,#] (φ -> F[#,#] ψ)` | 18 | 1.9% |
| `G[#,inf] φ` | 17 | 1.8% |

### The 10 most common patterns of set_2

| Pattern | Formulas | Share |
|---|---|---|
| `G[#,#] φ` | 107 | 9.0% |
| `F[#,#] φ` | 85 | 7.2% |
| `G[#,#] F[#,#] φ` | 45 | 3.8% |
| `(F[#,#] φ) && (G[#,#] ψ)` | 41 | 3.5% |
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
| generic | 453 (47.0%) | 663 (55.8%) | 58 (5.8%) | 1174 (37.3%) |
| automotive | 190 (19.7%) | 224 (18.9%) | 63 (6.3%) | 477 (15.1%) |
| mobile robotics | 157 (16.3%) | 120 (10.1%) | 49 (4.9%) | 326 (10.3%) |
| marine robotics | 7 (0.7%) | 25 (2.1%) | 81 (8.1%) | 113 (3.6%) |
| aerial robotics | 31 (3.2%) | 20 (1.7%) | 51 (5.1%) | 102 (3.2%) |
| industrial machinery | 18 (1.9%) | 24 (2.0%) | 55 (5.5%) | 97 (3.1%) |
| robotic manipulation | 21 (2.2%) | 19 (1.6%) | 54 (5.4%) | 94 (3.0%) |
| smart city | 21 (2.2%) | 5 (0.4%) | 60 (6.0%) | 86 (2.7%) |
| power systems | 7 (0.7%) | 7 (0.6%) | 67 (6.7%) | 81 (2.6%) |
| medical devices | 0 (0.0%) | 0 (0.0%) | 81 (8.1%) | 81 (2.6%) |
| mechatronics | 11 (1.1%) | 10 (0.8%) | 58 (5.8%) | 79 (2.5%) |
| railway | 3 (0.3%) | 21 (1.8%) | 55 (5.5%) | 79 (2.5%) |
| aviation | 19 (2.0%) | 6 (0.5%) | 52 (5.2%) | 77 (2.4%) |
| social dynamics | 5 (0.5%) | 22 (1.9%) | 48 (4.8%) | 75 (2.4%) |
| smart home | 18 (1.9%) | 6 (0.5%) | 51 (5.1%) | 75 (2.4%) |
| epidemiology | 2 (0.2%) | 16 (1.3%) | 52 (5.2%) | 70 (2.2%) |
| cloud computing | 0 (0.0%) | 0 (0.0%) | 65 (6.5%) | 65 (2.1%) |

## Operators

Share of the formulas of each set that hold each operator.

| Operator | set_1 | set_2 | set_3 | total |
|---|---|---|---|---|
| `G` | 69.4% | 69.5% | 59.4% | 66.3% |
| `F` | 53.7% | 60.4% | 66.7% | 60.3% |
| `U` | 11.2% | 13.6% | 5.5% | 10.3% |
| `R` | 0.0% | 0.8% | 12.0% | 4.1% |
| `!` | 17.3% | 16.4% | 31.1% | 21.4% |
| `&&` | 27.7% | 41.8% | 38.7% | 36.5% |
| `\|\|` | 5.3% | 15.2% | 24.1% | 15.0% |
| `->` | 16.5% | 14.9% | 40.7% | 23.6% |
