# Normalized formulas for stl-nl

From `data/dataset/stl_formulas_unpaired.jsonl` (6592 formulas), with the rules of `docs/normalization_rules.md` and the stlgen parser of stl-nl. Seed of the random bounds: `0`.

## By status

| Status | Formulas | Share |
|---|---|---|
| ok | 1764 | 26.8% |
| needs_review | 74 | 1.1% |
| rejected | 4754 | 72.1% |

## By source and bounds

| Source | Bounds | ok | needs_review | rejected |
|---|---|---|---|---|
| latex | numeric | 785 | 25 | 1434 |
| latex | symbolic | 644 | 29 | 2801 |
| pdf | numeric | 260 | 12 | 222 |
| pdf | symbolic | 75 | 8 | 297 |

## Why formulas are rejected

The first reason of each formula. *Example* is one of these formulas as the paper writes it; *What the rule found* is the part of that same formula that made the rule reject it, written after the paper's macros are expanded and with the names already normalized (\varphi_{1} is varphi_1). The example is a formula without the paper's macros when there is one, so that the part can be seen in it; *(macro)* marks one where it comes from a macro of the paper.

| Rule | Formulas | What it is | Example | What the rule found |
|---|---|---|---|---|
| function | 768 | a name followed by (...) or [...] (f(x), rho(phi,t), x(t+1)), or \max, \min, \|x\|, \log, ... | `\text{hrz}(\phi)` | `hrz(\phi)` |
| parse_error | 686 | a construct the parser doesn't recognise | `\diamond_{[x,y]}` | `the formula ends before it is complete` |
| unknown_command | 594 | a command neither defined by the paper nor known | `\LTLonce_{[0,T]}p` | `\LTLonce` |
| semantics_definition | 582 | a definition of the semantics (\models, \vDash) | `(x, t) \models G_{[a,b]}\phi` | `\models` |
| power | 429 | a power or a superscript that isn't a name | `\mu^1 U_{[a,b]}\mu^2` | `mu^1` |
| grammar_definition | 293 | a grammar of the logic (::=, \mid) | `\phi ::= \Box_{[t_1, t_2]} \mu` | `::=` |
| operator_definition | 280 | a definition of an operator: the left side of = or := is not a single name | `F_{[a,b]} \phi=\top U_{[a,b]}\phi` | `an operator on the left of =` |
| other_logic | 275 | the formula holds a construct of another logic | `p\since_{[1,3]}q` | `past-time` |
| unbounded_operator | 210 | a temporal operator without an interval, or with an infinite bound | `F_{[a,\infty)} p` | `\infty` |
| nonstandard_operator | 165 | an operator STL doesn't have, or a G/F/U/R with a script that isn't an interval | `\boxplus_{[r,r]}` | `\boxplus` |
| indexed_operator | 111 | \bigwedge, \bigvee, \sum, \ldots, ... | `\bigwedge_l (\mathcal{F}_{[t',t']}\psi_l)` | `\bigwedge` |
| several_formulas | 104 | several formulas, or a formula with text (where, and, if, ...) | `\varphi = B, \square_{[a,b]}B` | `a comma at the top level` |
| connective_at_edge | 63 | starts or ends with a connective: part of it is on another row | `\land \G{0}{T} SDF (\cdot, M)` |  |
| set_membership | 62 | \in a set that is not an interval | `\diamondsuit_{[3,4]}(x\in A)` | `\in a set` |
| quantifier | 58 | \forall, \exists | `\varphi_1=X(\Diamond_{[0,5]}(\exists^2 x\geq 2))` | `\exists` |
| multiplication | 49 | a product: 2x, \cdot, \times, *, two terms side by side | `F_{[0,10]}(\cdot)` | `\cdot` |
| division | 21 | a division other than of two integers | `\Box_{[11,40]}(\|\frac{\lambda(t) - \lambda_{ref}}{\lambda_{ref}}\| < tol)` | `\frac{\lambda(t)-\lambda_{ref}}{\lambda_{ref}}` |
| macro_loop | 4 | a macro still left after 10 rounds of expansion | `\urule {\Gamma, F^m(T)\le X, X\le F^n(T)\vdash X:\alpha,\Delta} {\Gamma\vdash T:\Box_{[m,n]}\alpha,\Delta } {  …` *(macro)* | `the expansion grows without end` |

## Why formulas need review

A formula may have several reasons: the counts add up to more than the formulas.

| Rule | Formulas | What it is | Example | Normalized as |
|---|---|---|---|---|
| symbolic_constant | 65 | a symbol the paper calls a threshold, constant, parameter, ...: it becomes a signal | `F_{\le i}(x\le v)` | `F[0,53] (x <= v)` |
| macro_conflict | 8 | a macro the paper defines twice differently (the last definition is used) | `a ~\U_{[2,2]} b` | `a U[2,2] b` |
| indexed_signal | 1 | x[0], x[1]: written x_0, x_1, but it may be the signal at time 0 | `\phi := G_{[0, 5]}(F_{[0, 3]}(x[0] \ge 0 \wedge x[1] \ge 0))` | `G[0,5] (F[0,3] ((x_0 >= 0) && (x_1 >= 0)))` |

## Most frequent unknown commands

Candidates for a new rule. Many come from the paper's macros: its definition of an operator uses a command to draw the symbol (\raisebox, \rotatebox, ...).

| Command | Formulas | Written in the formula | From a macro | Example |
|---|---|---|---|---|
| `\overline` | 52 | 7 | 45 | `\overline{\psi}^s=G_{[a,b]}\bar{\mu}^s` |
| `\mathbb` | 47 | 31 | 16 | `\mathbb{S}_{\mathsf{F}_{[a, b]}\mu_1}` |
| `\llbracket` | 30 | 6 | 24 | `\llbracket\Diamond_{[S,T]}\phi\rrbracket_\omega` |
| `\langle` | 30 | 20 | 10 | `\langle \Box_{[a,b]} \psi \rangle_i = 1` |
| `\not` | 29 | 29 | 0 | `N'\not\models\Diamond_{[a,b]}\mu` |
| `\circ` | 28 | 28 | 0 | `\circ \in \{\mOr,\mAnd, \mUntil_{[a,b]} \}` |
| `\begin` | 24 | 20 | 4 | `r = \begin{cases} e^{\beta sat(\sigma^F,\phi)}, \text{if $\Phi = F_{[0,T]}\phi $}` |
| `\leftarrow` | 22 | 22 | 0 | `Q \leftarrow \boxplus_{(0, \infty)} P` |
| `\boxdot` | 19 | 4 | 15 | `\boxdot_{[0,+\infty)}p` |
| `\ifthenelse` | 17 | 0 | 17 | `p_1\release_{[t_1,t_2]}p_2` (in a macro of the paper) |
| `\newcommand` | 16 | 16 | 0 | `\newcommand{\Glt}{\mathbf{G}^{\le t}}` |
| `\raisebox` | 13 | 0 | 13 | `\diamondplus_{[1,1]}` (in a macro of the paper) |
| `\Tilde` | 13 | 13 | 0 | `\lglobally_{[0,21]}(\AgtTrajNoT{1}\in{\Tilde{Q}_3})` |
| `\sim` | 9 | 9 | 0 | `G_{[t_0,t_1]} (s_j \sim \pi)` |
| `\rightarrowtail` | 9 | 9 | 0 | `\Glb_{[0, 2)} p \rightarrowtail \Glb_{[0, 10)} p` |
| `\small` | 8 | 8 | 0 | `\varphi_{\text{vel}} = \G_{[0,\infty)}(\|v\| \leq 1) \text{\small{Velocity Bounds}}` |
| `\cup` | 8 | 8 | 0 | `\Sigma\cup\{\mu\vee\Diamond_{[t,b]}\mu\}` |
| `\Coloneqq` | 8 | 8 | 0 | `\varphi \Coloneqq \ \X \psi \ \vert \ \psi \U^{\leq k} \psi` |
| `\cong` | 7 | 7 | 0 | `(\bm{x}, t)\cong\mathcal{T}_{\mathsf{F}_{[a, b]}\hat\varphi_1}` |
| `\tag` | 7 | 7 | 0 | `\tag{P1$'$} \always \mathit{transaction} \wedge \mathit{suspicious} \to \eventually_{[0,3]} \mathit{report}` |
| `\mathfrak` | 7 | 2 | 5 | `\gamma\equiv \mathfrak{C}^{40}_{\bowtie 3}(a \land b) \mathsf{U}_{(30,100)} \neg c` |
| `\def` | 6 | 6 | 0 | `\def\buntilop{{\mathtt{U}^{\leq k}}}` |
| `\mathopen` | 6 | 0 | 6 | `\Diamond_{[0,20]} \square_{[0,1]} \neg \freqp{\tftr[x]<1}{0.5}{4}` (in a macro of the paper) |
| `\preceq` | 6 | 0 | 6 | `\orderSat(\varphi_1\UntilOp{I}\varphi_2) \;\Defeq\; \left\{ \left\langle \begin{array}{l} \exists i \in \kset{ …` (in a macro of the paper) |
| `\LTLonce` | 5 | 3 | 2 | `\LTLonce_{[0,T]}p` |
| `\parallel` | 5 | 5 | 0 | `\Psi_2 = F_{[1,16]}(\parallel \textbf{x}_2 - [2,1]^T \parallel < 0.5)` |
| `\cap` | 5 | 5 | 0 | `\bar{\phi}_{12} =\textsf{G}_{[0, 1]}(\mathbf{p}\in\mathbf{Z}_{1}), \bar{\phi}_{13}=\textsf{F}_{[0, 1]}(\mathbf …` |
| `\nvDash` | 4 | 4 | 0 | `\sigma \nvDash \dia_{[a,b]}\psi` |
| `\ell` | 4 | 4 | 0 | `(\mathbf{x},H,\ell) \models \varphi_1\mathcal{U}_{[0,t_2]}\varphi_2` |
| `\blacklozenge` | 4 | 4 | 0 | `\blacklozenge_{[0,1]} p` |

## Rules applied to the formulas kept

Formulas with status ok or needs_review.

| Rule | Formulas |
|---|---|
| subscript_interval | 1832 |
| latex_ops | 1243 |
| greek_names | 1204 |
| index_names | 954 |
| unwrap_font | 825 |
| random_symbolic_bounds | 766 |
| strip_label | 734 |
| placeholder_subformula | 539 |
| expand_paper_macros | 447 |
| strip_layout | 405 |
| ambiguous_scope | 148 |
| close_open_interval | 100 |
| fallback_operator_table | 70 |
| symbolic_constant | 65 |
| accent_names | 51 |
| current_time_index | 49 |
| bound_shorthand | 46 |
| chained_comparison | 41 |
| round_bounds_outward | 38 |
| relational_eq | 32 |
| group_brackets | 28 |
| reserved_names | 18 |
| bool_constants | 14 |
| macro_conflict | 8 |
| interval_membership | 5 |
| negation_minus | 3 |
| indexed_signal | 1 |
| multiword_names | 1 |

## Selection limits of stl-nl

0 of the formulas kept are over the limits (node_count 2000, syntax_depth 32, text_chars 20000) and would be skipped when stl-nl selects its input.
