# Round-trip check

Each description is given, alone, to a model, which writes the formula from it (prompt: `src/evaluation/roundtrip.py`, models: gemini-3.8-flash:off, gpt-6-luna:medium, one answer each). The comparator (`src/evaluation/compare.py`) then says how close that formula is to the dataset's: equivalent (the same formula), renamed (the same with other names), near (the same apart from < vs <=, an open vs a closed interval end, or an outer G[0,inf]), same_pattern (the same structure, other bounds or conditions), different, or unparseable. For the answers at near, same_pattern or different, stlsat (`src/evaluation/sat.py`) then checks whether they mean the same: equivalent, stronger (the answer asks more), weaker, incomparable, unknown (past its time) or sat_skipped (a formula stlsat can't take). A match is one of the first three levels, or equivalent for stlsat. Groups: set 1 (every description of the papers, step 7) and the paraphrases of step 9. Not checkable: formulas stlgen can't read (decimal or expression bounds, powers): the answers can't be compared, they are shown for deciding by hand. A description is in the dataset when at least one model matches it, or when it was kept or fixed by hand.

## Size

| Group | Descriptions | Checkable | Not checkable |
|---|---|---|---|
| set_1 | 1709 | 1603 | 106 |
| paraphrase | 1134 | 1134 | 0 |

## The dataset

How the round trip splits the candidates (src/dataset/sets.py, split): in the dataset when a model wrote the formula back or when kept or fixed by hand; out when dropped by hand, when neither model wrote it back, when it can't be checked, or (a paraphrase) when its original is out.

| Group | Candidates | In the dataset | match | kept or fixed by hand | Out | dropped by hand | both miss | not checkable |
|---|---|---|---|---|---|---|---|---|
| set_1 | 1712 | 568 | 531 | 37 | 1144 | 3 | 1035 | 106 |
| paraphrase | 1136 | 1073 | 1072 | 1 | 63 | 2 | 61 | 0 |

## Matches

Share of the checkable descriptions whose formula each model matched, both matched, or neither did.

| Group | gemini-3.8-flash:off | gpt-6-luna:medium | Both | Neither |
|---|---|---|---|---|
| set_1 | 545 (34.0%) | 514 (32.1%) | 491 (30.6%) | 1035 (64.6%) |
| paraphrase | 1041 (91.8%) | 996 (87.8%) | 965 (85.1%) | 62 (5.5%) |

## Levels: gemini-3.8-flash:off

| Group | equivalent | renamed | near | same_pattern | different | unparseable |
|---|---|---|---|---|---|---|
| set_1 | 323 (20.1%) | 149 (9.3%) | 70 (4.4%) | 109 (6.8%) | 919 (57.3%) | 33 (2.1%) |
| paraphrase | 605 (53.4%) | 299 (26.4%) | 126 (11.1%) | 24 (2.1%) | 66 (5.8%) | 14 (1.2%) |

## Levels: gpt-6-luna:medium

| Group | equivalent | renamed | near | same_pattern | different | unparseable |
|---|---|---|---|---|---|---|
| set_1 | 307 (19.2%) | 139 (8.7%) | 63 (3.9%) | 101 (6.3%) | 941 (58.7%) | 52 (3.2%) |
| paraphrase | 580 (51.1%) | 283 (25.0%) | 118 (10.4%) | 28 (2.5%) | 113 (10.0%) | 12 (1.1%) |

## Near: what differs

Answers at level near, by the details they differ in (one answer may differ in two).

| Detail | gemini-3.8-flash:off | gpt-6-luna:medium |
|---|---|---|
| strict | 115 | 95 |
| open_end | 61 | 67 |
| outer_always | 33 | 35 |

## Meaning (stlsat)

The answers at near, same_pattern or different, checked by stlsat (discrete time, inclusive until; formulas with inf, named bounds or products skipped: sat_skipped). stronger: the answer implies the dataset's formula, not the converse; weaker: the converse.


### gemini-3.8-flash:off

| Group | Checked | equivalent | stronger | weaker | incomparable | unknown | sat_skipped |
|---|---|---|---|---|---|---|---|
| set_1 | 1098 | 3 | 51 | 40 | 59 | 7 | 938 |
| paraphrase | 216 | 11 | 55 | 21 | 10 | 0 | 119 |

### gpt-6-luna:medium

| Group | Checked | equivalent | stronger | weaker | incomparable | unknown | sat_skipped |
|---|---|---|---|---|---|---|---|
| set_1 | 1105 | 5 | 49 | 36 | 45 | 3 | 967 |
| paraphrase | 259 | 15 | 51 | 21 | 14 | 0 | 158 |

Matches found only by stlsat (the answer's level is same_pattern or different), per group and model:

| Group | gemini-3.8-flash:off | gpt-6-luna:medium |
|---|---|---|
| set_1 | 3 | 5 |
| paraphrase | 11 | 15 |

Why stlsat skipped an answer (sat_skipped, both models together):

| Reason | Answers |
|---|---|
| an infinite interval end | 1060 |
| a named interval end | 809 |
| a different number of atoms | 246 |
| a different number of signals | 52 |
| arithmetic beyond affine | 8 |
| too many renamings to try | 7 |

Dataset formulas that nothing satisfies (unsatisfiable) or everything does (valid), for stlsat: against them, equivalent says little.

| Flag | Formula | Descriptions |
|---|---|---|
| unsatisfiable | `(F[0,20] ((0 <= z) && (z <= 20))) && (F[0,20] ((15 <= z) && (z <= 30))) && (((30 <= z) && (z <= 60)) U[40,50] ((55 <= z) && (z <= 60)))` | W4402300289:F1:D1 |
| unsatisfiable | `(G[0,18] ((x < 1.69) && (x > -0.35) && (y < 1.15) && (y > -1.1))) && (G[15,25] ((x < 3.16) && (x > 2.16) && (y < 1.27) && (y > -1.35)))` | arxiv_2604.24907:F9:D1 |
| unsatisfiable | `(G[11,29] F[0,15] (a >= 80)) && (F[8,23] (a >= 80)) && (F[9,24] (a >= 80)) && (F[10,25] (a >= 80)) && (G[10,25] (a < 80))` | W4413131612:F15:D1, W4413131612:F15:D1:A1, W4413131612:F15:D1:A2 |
| unsatisfiable | `(X_I > 0) U[100,120] (X_I == 0)` | W4387225991:F1:D1 |
| valid | `F[0,30] ((v > 100) -> (G[0,20] (v > 100)))` | W2549790574:F31:D1 |
| valid | `F[0,30] (p_1 -> (G[0,20] p_1))` | W2549790574:F5:D1 |

## Paraphrases against their originals

The closest level of a paraphrase's two answers against that of its original's.

| Paraphrase | Paraphrases |
|---|---|
| closer | 23 (2.0%) |
| as close | 1016 (89.6%) |
| farther | 95 (8.4%) |
| original matched, paraphrase not | 62 (5.5%) |

## To read

Sheets of `roundtrip.xlsx`:

| Sheet | Descriptions | Why |
|---|---|---|
| set 1, both miss | 1035 | neither model wrote the formula back, so the pair is out: keep it when the description is enough after all, fix the formula when the description is right and the formula opaque (phi for a condition the description spells out) |
| set 1, not checkable | 106 | stlgen can't read the formula, so the pair is out: the column why not checkable says what it has that stlgen doesn't take, the models' formulas are there to compare by eye; keep it when the description is right, fix the formula into one stlgen reads (then it is checked) |
| paraphrase loses it | 62 | the original's formula was matched, the paraphrase's not: it may lose something |
| all | 2843 | every description |
