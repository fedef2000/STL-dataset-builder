# Normalized formulas for stl-nl

From `data/dataset/stl_formulas_unpaired.jsonl` (6592 formulas), with the rules of `docs/normalization_rules.md` and the stlgen parser of stl-nl. Seed of the random bounds: `0`.

## By status

| Status | Formulas | Share |
|---|---|---|
| ok | 2304 | 35.0% |
| needs_review | 0 | 0.0% |
| rejected | 4288 | 65.0% |

## Why formulas are rejected

The first reason of each formula. *Example* is one of these formulas as the paper writes it; *What the rule found* is the part of that same formula that made the rule reject it, written after the paper's macros are expanded and with the names already normalized (\varphi_{1} is varphi_1). The example is a formula without the paper's macros when there is one, so that the part can be seen in it; *(macro)* marks one where it comes from a macro of the paper.

| Rule | Formulas | What it is | Example | What the rule found |
|---|---|---|---|---|
| semantics_definition | 610 | a definition of the semantics (\models, \vDash) | `(x, t) \models G_{[a,b]}\phi` | `\models` |
| unknown_command | 567 | a command neither defined by the paper nor known | `\LTLonce_{[0,T]}p` | `\LTLonce` |
| function | 462 | a name followed by (...) or [...] with an argument that isn't a name or an integer (rho(G_{[a,b]} phi,t), x(t+1)), or \max, \min, \log, ... | `\mathsf L[\Until[0,\infty]]` | `L[{\mathcal{U}}[0,\infty]]` |
| power | 445 | a power or a superscript that isn't a name | `\mu^1 U_{[a,b]}\mu^2` | `mu^1` |
| parse_error | 414 | a construct the parser doesn't recognise | `G_[0,H](F_[0,h](mu))` | `subscript [` |
| grammar_definition | 388 | a grammar of the logic (::=, \mid, | between alternatives) | `\phi ::= \Box_{[t_1, t_2]} \mu` | `::=` |
| operator_definition | 297 | a definition of an operator: the left side of = or := is not a single name | `F_{[a,b]} \phi=\top U_{[a,b]}\phi` | `an operator on the left of =` |
| other_logic | 275 | the formula holds a construct of another logic | `p\since_{[1,3]}q` | `past-time` |
| nonstandard_operator | 156 | an operator STL doesn't have, or a G/F/U/R with a script that isn't an interval | `\boxplus_{[r,r]}` | `\boxplus` |
| several_formulas | 149 | several formulas, or a formula with text (where, and, if, ...) | `\eventually{[0,1]}{}` | `a comma between formulas` |
| indexed_operator | 130 | \bigwedge, \bigvee, \land_{i}, \sum, \ldots, ... | `\bigwedge_l (\mathcal{F}_{[t',t']}\psi_l)` | `\bigwedge` |
| operator_alone | 94 | a temporal operator with no operand (F_{[a,b]}, U_{[a,b]} alone, or at the end) | `\diamond_{[x,y]}` | `F` |
| set_membership | 78 | \in a set that is not an interval | `\diamondsuit_{[3,4]}(x\in A)` | `\in a set` |
| multiplication | 68 | a product: 2x, \cdot, \times, *, two terms side by side | `F_{[0,10]}(\cdot)` | `\cdot` |
| connective_at_edge | 63 | starts or ends with a connective: part of it is on another row | `\land \G{0}{T} SDF (\cdot, M)` |  |
| quantifier | 63 | \forall, \exists | `\varphi_1=X(\Diamond_{[0,5]}(\exists^2 x\geq 2))` | `\exists` |
| division | 25 | a division other than of two integers | `\Box_{[11,40]}(\|\frac{\lambda(t) - \lambda_{ref}}{\lambda_{ref}}\| < tol)` | `\frac{\lambda(t)-\lambda_{ref}}{\lambda_{ref}}` |
| macro_loop | 4 | a macro still left after 10 rounds of expansion | `\urule {\Gamma, F^m(T)\le X, X\le F^n(T)\vdash X:\alpha,\Delta} {\Gamma\vdash T:\Box_{[m,n]}\alpha,\Delta } {  …` *(macro)* | `the expansion grows without end` |

## Most frequent unknown commands

Candidates for a new rule. Many come from the paper's macros: its definition of an operator uses a command to draw the symbol (\raisebox, \rotatebox, ...).

| Command | Formulas | Written in the formula | From a macro | Example |
|---|---|---|---|---|
| `\mathbb` | 48 | 32 | 16 | `\mathbb{S}_{\mathsf{F}_{[a, b]}\mu_1}` |
| `\begin` | 33 | 29 | 4 | `\phi_2:=F_{[5,15]}(\\|\boldsymbol{x}_2-\begin{bmatrix} 90 90 \end{bmatrix}\\|\le 5)` |
| `\llbracket` | 31 | 7 | 24 | `\llbracket\Diamond_{[S,T]}\phi\rrbracket_\omega` |
| `\not` | 30 | 30 | 0 | `N'\not\models\Diamond_{[a,b]}\mu` |
| `\langle` | 30 | 20 | 10 | `\langle \Box_{[a,b]} \psi \rangle_i = 1` |
| `\circ` | 28 | 28 | 0 | `\circ \in \{\mOr,\mAnd, \mUntil_{[a,b]} \}` |
| `\leftarrow` | 27 | 27 | 0 | `Q \leftarrow \boxplus_{(0, \infty)} P` |
| `\boxdot` | 19 | 4 | 15 | `\boxdot_{[0,+\infty)}p` |
| `\ifthenelse` | 17 | 0 | 17 | `p_1\release_{[t_1,t_2]}p_2` (in a macro of the paper) |
| `\newcommand` | 16 | 16 | 0 | `\newcommand{\Glt}{\mathbf{G}^{\le t}}` |
| `\raisebox` | 13 | 0 | 13 | `\diamondplus_{[1,1]}` (in a macro of the paper) |
| `\Tilde` | 13 | 13 | 0 | `\lglobally_{[0,21]}(\AgtTrajNoT{1}\in{\Tilde{Q}_3})` |
| `\sim` | 11 | 11 | 0 | `G_{[t_0,t_1]} (s_j \sim \pi)` |
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
| `\stackrel` | 5 | 0 | 5 | `Atlast \df \neg\fut_{[0,\infty)} XXS` (in a macro of the paper) |
| `\LTLonce` | 5 | 3 | 2 | `\LTLonce_{[0,T]}p` |
| `\parallel` | 5 | 5 | 0 | `\Psi_2 = F_{[1,16]}(\parallel \textbf{x}_2 - [2,1]^T \parallel < 0.5)` |
| `\cap` | 5 | 5 | 0 | `\bar{\phi}_{12} =\textsf{G}_{[0, 1]}(\mathbf{p}\in\mathbf{Z}_{1}), \bar{\phi}_{13}=\textsf{F}_{[0, 1]}(\mathbf …` |
| `\gets` | 5 | 5 | 0 | `{P'(\sbf) \gets \Box_{[0,\infty) }P(\sbf)}` |
| `\nvDash` | 4 | 4 | 0 | `\sigma \nvDash \dia_{[a,b]}\psi` |
| `\ell` | 4 | 4 | 0 | `(\mathbf{x},H,\ell) \models \varphi_1\mathcal{U}_{[0,t_2]}\varphi_2` |

## Structures

The structure of a formula is its normalized text with every number written # and the names renamed a, b, ... in the order they appear (a name used twice keeps its letter; operators and comparisons are kept). Formulas that differ only in their numbers and names have the same structure. The manifest has the structure of each formula (`structure`); the example is the shortest formula of each structure.

2304 formulas kept have 635 structures; 427 of them have one formula only. The 30 most common cover 1329 formulas (58%).

| Structure | Formulas | Share | Example |
|---|---|---|---|
| `F[#,#] a` | 303 | 13.2% | `F[0,7] p` |
| `G[#,#] a` | 260 | 11.3% | `G[2,6] p` |
| `a U[#,#] b` | 181 | 7.9% | `a U[0,6] b` |
| `G[#,#] (a > #)` | 50 | 2.2% | `G[3,4] (x > 4)` |
| `G[#,#] (a < #)` | 47 | 2.0% | `G[0,1] (N < 4)` |
| `F[#,#] (G[#,#] a)` | 43 | 1.9% | `F[2,5] (G[3,10] p)` |
| `G[#,#] (F[#,#] a)` | 40 | 1.7% | `G[0,2] (F[2,4] p)` |
| `F[#,#] (a > #)` | 36 | 1.6% | `F[0,2] (s > 0)` |
| `G[#,#] (a <= #)` | 34 | 1.5% | `G[0,1] (x <= 1)` |
| `(G[#,#] (a < #)) -> (G[#,#] (b < #))` | 33 | 1.4% | `(G[0,30] (w < 3000)) -> (G[0,4] (v < 35))` |
| `(F[#,#] a) && (F[#,#] b)` | 29 | 1.3% | `(F[0,2] mu_1) && (F[2,4] mu_2)` |
| `G[#,#] (a -> (F[#,#] b))` | 26 | 1.1% | `G[0,10] (p -> (F[0,5] q))` |
| `F[#,#] (a >= #)` | 23 | 1.0% | `F[0,1] (x >= 0)` |
| `G[#,#] (a >= #)` | 23 | 1.0% | `G[0,50] (x >= 0)` |
| `G[#,#] ((# <= a) && (a <= #))` | 21 | 0.9% | `G[0,10] ((2 <= y) && (y <= 4))` |
| `G[#,#] (!a)` | 21 | 0.9% | `G[5,8] (!c)` |
| `F[#,#] (a < #)` | 13 | 0.6% | `F[0,3] (x < 0)` |
| `F[#,#] (a && (F[#,#] b))` | 13 | 0.6% | `F[0,1] (a && (F[3,3] c))` |
| `(G[#,#] a) && (F[#,#] b)` | 13 | 0.6% | `(G[0,4] a) && (F[8,51] b)` |
| `F[#,#] (a <= #)` | 13 | 0.6% | `F[0,1] (x <= 1)` |
| `(F[#,#] a) \|\| (F[#,#] b)` | 13 | 0.6% | `(F[0,38] mu_1) \|\| (F[0,38] mu_2)` |
| `G[#,#] (a && b)` | 12 | 0.5% | `G[0,5] (mu_1 && mu_2)` |
| `G[#,#] (F[#,#] (G[#,#] (a - b >= #)))` | 11 | 0.5% | `G[0,72] (F[0,8] (G[0,5] (y_2 - y_1 >= 9)))` |
| `(F[#,#] (G[#,#] a)) \|\| (F[#,#] (G[#,#] b))` | 11 | 0.5% | `(F[0,15] (G[0,5] Reg_4_4)) \|\| (F[0,15] (G[0,5] Reg_2_2))` |
| `G[#,#] (!((a >= #) && (a <= #) && (b >= #) && (b <= #)))` | 11 | 0.5% | `G[0,10] (!((v >= -1) && (v <= 1) && (x >= 1) && (x <= 2)))` |
| `G[#,#] (a - b <= #)` | 10 | 0.4% | `G[0,100] (y_5 - y_4 <= 40)` |
| `G[#,#] (F[#,#] (a - b >= #))` | 10 | 0.4% | `G[0,70] (F[0,30] (y_5 - y_4 >= 15))` |
| `G[#,#] (a >= b)` | 10 | 0.4% | `G[0,24] (x >= p)` |
| `G[#,#] (\|a - b\| <= #)` | 10 | 0.4% | `G[5,10] (\|x_1 - x_2\| <= 2)` |
| `G[#,#] (a < b)` | 9 | 0.4% | `G[0,63] (x < p)` |
