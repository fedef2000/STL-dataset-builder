# Normalized formulas for stl-nl

From `data/dataset/stl_formulas_unpaired.jsonl` (6592 formulas), with the rules of `docs/normalization_rules.md` and the stlgen parser of stl-nl. Seed of the random bounds: `0`.

## By status

| Status | Formulas | Share |
|---|---|---|
| ok | 1838 | 27.9% |
| needs_review | 0 | 0.0% |
| rejected | 4754 | 72.1% |

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

## Structures

The structure of a formula is its normalized text with every number written # and the names renamed a, b, ... in the order they appear (a name used twice keeps its letter; operators and comparisons are kept). Formulas that differ only in their numbers and names have the same structure. The manifest has the structure of each formula (`structure`); the example is the shortest formula of each structure.

1838 formulas kept have 471 structures; 310 of them have one formula only. The 30 most common cover 1141 formulas (62%).

| Structure | Formulas | Share | Example |
|---|---|---|---|
| `F[#,#] a` | 263 | 14.3% | `F[0,7] p` |
| `G[#,#] a` | 237 | 12.9% | `G[2,6] p` |
| `a U[#,#] b` | 167 | 9.1% | `a U[0,6] b` |
| `G[#,#] (a > #)` | 47 | 2.6% | `G[3,4] (x > 4)` |
| `G[#,#] (a < #)` | 46 | 2.5% | `G[0,1] (N < 4)` |
| `F[#,#] (a > #)` | 36 | 2.0% | `F[0,2] (s > 0)` |
| `G[#,#] (F[#,#] a)` | 33 | 1.8% | `G[0,2] (F[2,4] p)` |
| `(G[#,#] (a < #)) -> (G[#,#] (b < #))` | 33 | 1.8% | `(G[0,30] (w < 3000)) -> (G[0,4] (v < 35))` |
| `G[#,#] (a <= #)` | 32 | 1.7% | `G[0,1] (x <= 1)` |
| `F[#,#] (G[#,#] a)` | 31 | 1.7% | `F[2,5] (G[3,10] p)` |
| `G[#,#] (!a)` | 21 | 1.1% | `G[5,8] (!c)` |
| `F[#,#] (a >= #)` | 18 | 1.0% | `F[0,1] (c >= 4)` |
| `G[#,#] ((# <= a) && (a <= #))` | 17 | 0.9% | `G[0,10] ((2 <= y) && (y <= 4))` |
| `F[#,#] (a < #)` | 13 | 0.7% | `F[0,3] (x < 0)` |
| `G[#,#] (a >= #)` | 13 | 0.7% | `G[0,10] (x >= 5)` |
| `F[#,#] (a <= #)` | 12 | 0.7% | `F[0,1] (x <= 1)` |
| `(G[#,#] a) && (F[#,#] b)` | 12 | 0.7% | `(G[1,84] a) && (F[1,84] b)` |
| `G[#,#] (!((a >= #) && (a <= #) && (b >= #) && (b <= #)))` | 11 | 0.6% | `G[0,10] (!((v >= -1) && (v <= 1) && (x >= 1) && (x <= 2)))` |
| `G[#,#] (F[#,#] (a - b >= #))` | 10 | 0.5% | `G[0,70] (F[0,30] (y_5 - y_4 >= 15))` |
| `G[#,#] (F[#,#] (G[#,#] (a - b >= #)))` | 10 | 0.5% | `G[0,65] (F[0,30] (G[0,5] (y_5 - y_4 >= 8)))` |
| `G[#,#] (a < b)` | 9 | 0.5% | `G[0,63] (x < p)` |
| `(F[#,#] a) && (G[#,#] b)` | 9 | 0.5% | `(F[0,2] A) && (G[4,7] B)` |
| `G[#,#] (a - b <= #)` | 9 | 0.5% | `G[0,100] (y_5 - y_4 <= 40)` |
| `G[#,#] (F[#,#] ((G[#,#] (a - b >= #)) -> (G[#,#] (c - d >= #))))` | 9 | 0.5% | `G[0,72] (F[0,8] ((G[0,5] (y_2 - y_1 >= 9)) -> (G[5,20] (y_5 - y_4 >= 9))))` |
| `G[#,#] ((G[#,#] (a - b <= #)) \|\| (F[#,#] (c - d >= #)))` | 8 | 0.4% | `G[0,80] ((G[0,20] (y_2 - y_1 <= 20)) \|\| (F[0,20] (y_5 - y_4 >= 40)))` |
| `G[#,#] (a && b)` | 8 | 0.4% | `G[0,5] (mu_1 && mu_2)` |
| `G[#,#] (a -> (F[#,#] b))` | 7 | 0.4% | `G[0,10] (p -> (F[0,5] q))` |
| `(F[#,#] a) && (F[#,#] b)` | 7 | 0.4% | `(F[0,2] mu_1) && (F[2,4] mu_2)` |
| `G[#,#] (a >= b)` | 7 | 0.4% | `G[1,24] (x >= c)` |
| `true U[#,#] a` | 6 | 0.3% | `true U[1,2] b` |
