# Normalized formulas for stl-nl

From `data/dataset/stl_formulas_unpaired.jsonl` (6592 formulas), with the rules of `docs/normalization_rules.md` and the stlgen parser of stl-nl. Seed of the random values: `0`.

## By status

| Status | Formulas | Share |
|---|---|---|
| ok | 2317 | 35.1% |
| needs_review | 0 | 0.0% |
| rejected | 4275 | 64.9% |

## Why formulas are rejected

Each formula is counted under the first rule that rejects it: a single construct the rule can't accept rejects the whole formula, even when the rest is valid STL.

| Rule | Formulas | Why it is rejected |
|---|---|---|
| semantics_definition | 610 | a definition of the semantics (\models, \vDash): it says when a signal satisfies a formula, it is not a formula itself |
| unknown_command | 578 | a LaTeX command the paper doesn't define and the normalizer has no translation for (it is not an STL operator, connective, comparison, font or spacing command): its meaning is unknown, so the whole formula is rejected even if the rest is valid STL |
| function | 464 | a function applied to something (rho(G_{[a,b]} phi,t), x(t+1), \max, \min, \log, ...): stl-nl has no functions (a call on names and integers only, Reg(4,4), is kept as one name) |
| power | 447 | a power or a superscript that isn't a name (x^2, \rho^{\varphi}): stl-nl has no powers |
| parse_error | 418 | a construct the parser can't read (a subscript where none can go, an unexpected symbol, unbalanced brackets): it is never guessed |
| grammar_definition | 388 | a grammar of the logic (::=, \mid, \| between alternatives): it lists the forms a formula can take, it is not a formula itself |
| operator_definition | 297 | a definition of an operator in terms of others (F_{[a,b]} phi := true U_{[a,b]} phi): the left side of = or := is not a single name |
| other_logic | 275 | the paper writes it in another logic (past-time, spatial, probabilistic, strategic): its operators have no STL equivalent |
| nonstandard_operator | 154 | an operator STL doesn't have (\boxplus, \sqcup, ...), or a G/F/U/R with a script that isn't an interval |
| several_formulas | 152 | several formulas, or a formula with text (where, and, if, ...): stl-nl takes exactly one formula |
| indexed_operator | 132 | an operator over an index (\bigwedge, \bigvee, \land_{i}, \sum, \ldots, ...): the number of terms isn't known, so it can't be written out |
| operator_alone | 96 | a temporal operator with no operand (F_{[a,b]}, U_{[a,b]} alone, or at the end): an operator, not a formula |
| set_membership | 78 | \in a set that is not an interval: STL can only compare a signal with numbers |
| quantifier | 64 | a quantifier (\forall, \exists): STL has none |
| connective_at_edge | 63 | starts or ends with a connective (\land, \lor, ...): the extraction found that the rest of the formula is on another row |
| multiplication | 55 | two terms side by side: a product with a space (k x), a unit (200 N) or a missing operator |
| macro_loop | 4 | a macro of the paper still left after 10 rounds of expansion: it never turns into a formula |

### Examples of each rule

Up to 3 formulas per rule, from different papers and showing different cases of the rule. *Example* is the formula as the paper writes it. *Why* names the part that made the rule reject it, written after the paper's macros are expanded and with the names normalized (\varphi_{1} is varphi_1); *(macro)* marks an example where that part comes from a macro of the paper, so it can't be seen in the formula as written.

**semantics_definition** (610 formulas): a definition of the semantics (\models, \vDash): it says when a signal satisfies a formula, it is not a formula itself.

| Example | Why |
|---|---|
| `(x, t) \models G_{[a,b]}\phi` | `\models` says when a signal satisfies a formula: this defines the meaning of an operator |
| `\tau\vDash \Box_{[u,v]} \varphi` | `\vDash` says when a signal satisfies a formula: this defines the meaning of an operator |
| `\vdash C: \Box_{[0,1]} c: \Box_{[0,1]}p` | `\vdash` says when a signal satisfies a formula: this defines the meaning of an operator |

**unknown_command** (578 formulas): a LaTeX command the paper doesn't define and the normalizer has no translation for (it is not an STL operator, connective, comparison, font or spacing command): its meaning is unknown, so the whole formula is rejected even if the rest is valid STL.

| Example | Why |
|---|---|
| `\mathbb{S}_{\mathsf{F}_{[a, b]}\mu_1}` | `\mathbb` isn't defined by the paper and the normalizer doesn't know it |
| `\phi_2:=F_{[5,15]}(\\|\boldsymbol{x}_2-\begin{bmatrix} 90 90 \end{bmatrix}\\|\le 5)` | `\begin` isn't defined by the paper and the normalizer doesn't know it |
| `\langle \Box_{[a,b]} \psi \rangle_i = 1` | `\langle` isn't defined by the paper and the normalizer doesn't know it |

**function** (464 formulas): a function applied to something (rho(G_{[a,b]} phi,t), x(t+1), \max, \min, \log, ...): stl-nl has no functions (a call on names and integers only, Reg(4,4), is kept as one name).

| Example | Why |
|---|---|
| `\rho(x_{k:K},G_{[k_s,k_e]}\phi)` | `rho(x_{k:K},G_{[k_s,k_e]}\phi)` applies a function to something that isn't a name or an integer |
| `r(s,F_{[a,b)} \varphi,t) = \underset{t' \in [t+a,t+b)}{\max} r(s,\varphi,t')` | `r(s,F_{[a,b)` applies a function to something that isn't a name or an integer |
| `\tau(s,\lozenge_{[a,b]}\phi)` | `tau(s,\lozenge_{[a,b]}\phi)` applies a function to something that isn't a name or an integer |

**power** (447 formulas): a power or a superscript that isn't a name (x^2, \rho^{\varphi}): stl-nl has no powers.

| Example | Why |
|---|---|
| `\rho^{\square_{[a, b]} \varphi}(\xi, k)` | `rho^\square_{[a, b]} \varphi` is a power or a superscript that isn't a name |
| `\phi^2=F_{\le 5}\clubsuit` | `phi^2` is a power or a superscript that isn't a name |
| `z_k^{\square_{[a, b]} \varphi}` | `z_k^\square_{[a, b]} \varphi` is a power or a superscript that isn't a name |

**parse_error** (418 formulas): a construct the parser can't read (a subscript where none can go, an unexpected symbol, unbalanced brackets): it is never guessed.

| Example | Why |
|---|---|
| `G_[0,H](F_[0,h](mu))` | the subscript `[` is on a name, but it is neither an interval nor part of the name |
| `F_{[0,10]}(\cdot)` | the parser didn't expect `*` here: `F ( * )` |
| `\square_{[t_1, t_2]}#1` | the character `#` isn't part of the grammar |

**grammar_definition** (388 formulas): a grammar of the logic (::=, \mid, \| between alternatives): it lists the forms a formula can take, it is not a formula itself.

| Example | Why |
|---|---|
| `\phi ::= \Box_{[t_1, t_2]} \mu` | `::=` introduces the forms a formula can take: a grammar |
| `(\bm{s}, t_k, t_{l}) \mid\asymp \varphi_1 \mathsf{U}_{[a, b]} \varphi_2` | `\mid` introduces the forms a formula can take: a grammar |
| `\phi := F_{[0, T]} \psi \| G_{[0, T]} \psi` | a `\|` separates the alternatives of a grammar (it can't be read as an absolute value) |

**operator_definition** (297 formulas): a definition of an operator in terms of others (F_{[a,b]} phi := true U_{[a,b]} phi): the left side of = or := is not a single name.

| Example | Why |
|---|---|
| `\always\phi:=\always_{[0,\infty)}\phi` | the left side of := (or \equiv) is an expression, not a name: the formula defines it |
| `F_{[a,b]} \phi=\top U_{[a,b]}\phi` | a temporal operator is on the left of =: the formula defines that operator |
| `F_{[a,b]}\Phi=\top\,U_{[a,b]}\,\Phi` | a temporal operator is on the left of =: the formula defines that operator |

**other_logic** (275 formulas): the paper writes it in another logic (past-time, spatial, probabilistic, strategic): its operators have no STL equivalent.

| Example | Why |
|---|---|
| `p\since_{[1,3]}q` | the extraction classed it as past-time logic: its operators (once, since, historically, ...) look back in time, STL's only forward |
| `\everywhere_{\ra}\always_{[a,b]}\varphi` | the extraction classed it as a spatial or description logic: its operators are about places or objects |
| `\mathbb{P}_s(\lozenge^{\leq n}\target)` | the extraction classed it as a probabilistic logic: its operators are about probabilities |

**nonstandard_operator** (154 formulas): an operator STL doesn't have (\boxplus, \sqcup, ...), or a G/F/U/R with a script that isn't an interval.

| Example | Why |
|---|---|
| `\boxplus_{[r,r]}` | `\boxplus` isn't an STL operator |
| `\Box_{I}(\Diamond_{[0,t]}\varphi_2)` | `G_{I}` isn't an STL operator |
| `\Diamond_{[a,b]}\varphi=True\sqcup_{[a,b]}\varphi` | `\sqcup` isn't an STL operator |

**several_formulas** (152 formulas): several formulas, or a formula with text (where, and, if, ...): stl-nl takes exactly one formula.

| Example | Why |
|---|---|
| `\text{ if } \phi=F_{[a,b]}\psi` | the word "if" joins the formula to text or to another formula |
| `\eventually{[0,1]}{}` | a comma inside brackets separates formulas (a set or a tuple) |
| `(p,p \wedge \Box_{[0,10]} p)` | a comma inside brackets separates formulas (a set or a tuple) |

**indexed_operator** (132 formulas): an operator over an index (\bigwedge, \bigvee, \land_{i}, \sum, \ldots, ...): the number of terms isn't known, so it can't be written out.

| Example | Why |
|---|---|
| `\bigwedge_l (\mathcal{F}_{[t',t']}\psi_l)` | `\bigwedge` stands for a number of terms that isn't known |
| `\diamondsuit_{[a,b]}\varphi \implies \bigvee_{t' \in [t+a,t+b]} z_{\varphi}^{t'}` | `\bigvee` stands for a number of terms that isn't known |
| `\{ \wedge, F_{[a,b]}, G_{[a,b]}\}, j\in \{k+1,\ldots, N_f\}` | `\ldots` stands for a number of terms that isn't known |

**operator_alone** (96 formulas): a temporal operator with no operand (F_{[a,b]}, U_{[a,b]} alone, or at the end): an operator, not a formula.

| Example | Why |
|---|---|
| `\mathbf{G}[0, 3]` | the operator `G` has no operand |
| `\phi_1=F_{\le i_1}` | the operator `F` has no operand |
| `\textbf{U}_{[a,b]}` | the operator `U` has no operand |

**set_membership** (78 formulas): \in a set that is not an interval: STL can only compare a signal with numbers.

| Example | Why |
|---|---|
| `\diamondsuit_{[3,4]}(x\in A)` | \in says that a signal belongs to a set: STL can only compare it with numbers |
| `\bm{u}\in \mathcal{U}_{\ge k}` | \in says that a signal belongs to a set: STL can only compare it with numbers |
| `\Box_{[a,b]}\varphi\in\Delta_1` | \in says that a signal belongs to a set: STL can only compare it with numbers |

**quantifier** (64 formulas): a quantifier (\forall, \exists): STL has none.

| Example | Why |
|---|---|
| `G_{[0,20)}F_{[0,5)}\forall_\mathcal{L}\bigcirc (\mu \geq1)` | `\forall` is a quantifier |
| `\varphi_1=X(\Diamond_{[0,5]}(\exists^2 x\geq 2))` | `\exists` is a quantifier |
| `\varphi^k_{rs} = G_{[a^k,b^k]} \mu_{rs}^k, \; \forall k\in \mathcal{I}_G` | `\forall` is a quantifier |

**connective_at_edge** (63 formulas): starts or ends with a connective (\land, \lor, ...): the extraction found that the rest of the formula is on another row.

| Example | Why |
|---|---|
| `\land \G{0}{T} SDF (\cdot, M)` | it starts or ends with a connective: the rest of the formula is on another row of the paper |
| `\land(\Box_{[12,15]}gear == 2)` | it starts or ends with a connective: the rest of the formula is on another row of the paper |
| `\wedge\Box_{[0,100]} (D\le0.02)` | it starts or ends with a connective: the rest of the formula is on another row of the paper |

**multiplication** (55 formulas): two terms side by side: a product with a space (k x), a unit (200 N) or a missing operator.

| Example | Why |
|---|---|
| `\textbf{G}_{[0.63s, 0.80s]} (x_2(t) >= 3)` | `a time unit in a bound: 0.63s` is a product |
| `\psi_2 = \square_{[0,20]} (G_Rx \leq H_R)` | `G_R x`: two terms side by side are a product |
| `\varphi = \varphi_o\land\varphi_u\land\textbf{F}_{[0,20]}\mbox{Tar}1` | `Tar 1`: two terms side by side are a product |

**macro_loop** (4 formulas): a macro of the paper still left after 10 rounds of expansion: it never turns into a formula.

| Example | Why |
|---|---|
| `\urule {\Gamma, F^m(T)\le X, X\le F^n(T)\vdash X:\alpha,\Delta} {\Gamma\vdash T:\Box_{[m,n]}\alpha,\Delta } {  …` *(macro)* | a macro of the paper keeps expanding without end |

## Most frequent unknown commands

Candidates for a new rule. Many come from the paper's macros: its definition of an operator uses a command to draw the symbol (\raisebox, \rotatebox, ...).

| Command | Formulas | Written in the formula | From a macro | Example |
|---|---|---|---|---|
| `\mathbb` | 48 | 32 | 16 | `\mathbb{S}_{\mathsf{F}_{[a, b]}\mu_1}` |
| `\begin` | 38 | 34 | 4 | `\phi_2:=F_{[5,15]}(\\|\boldsymbol{x}_2-\begin{bmatrix} 90 90 \end{bmatrix}\\|\le 5)` |
| `\langle` | 32 | 20 | 12 | `\langle \Box_{[a,b]} \psi \rangle_i = 1` |
| `\llbracket` | 31 | 7 | 24 | `\llbracket\Diamond_{[S,T]}\phi\rrbracket_\omega` |
| `\not` | 30 | 30 | 0 | `N'\not\models\Diamond_{[a,b]}\mu` |
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

## Patterns

The pattern of a formula is its normalized text with every number written # and the names renamed a, b, ... in the order they appear (a name used twice keeps its letter; operators and comparisons are kept). Formulas that differ only in their numbers and names have the same pattern. The manifest has the pattern of each formula (`pattern`); the example is the shortest formula of each pattern.

2317 formulas kept have 680 patterns; 462 of them have one formula only. The 30 most common cover 1264 formulas (55%).

| Pattern | Formulas | Share | Example |
|---|---|---|---|
| `F[#,#] a` | 292 | 12.6% | `F[0,7] p` |
| `G[#,#] a` | 250 | 10.8% | `G[2,6] p` |
| `a U[#,#] b` | 170 | 7.3% | `p U[a,b] q` |
| `G[#,#] (a > #)` | 49 | 2.1% | `G[3,4] (x > 4)` |
| `G[#,#] (a < #)` | 46 | 2.0% | `G[0,1] (N < 4)` |
| `F[#,#] (G[#,#] a)` | 42 | 1.8% | `F[a,b] (G[c,d] p)` |
| `F[#,#] (a > #)` | 36 | 1.6% | `F[a,b] (x > 5)` |
| `G[#,#] (F[#,#] a)` | 35 | 1.5% | `G[0,2] (F[2,4] p)` |
| `G[#,#] (a <= #)` | 33 | 1.4% | `G[0,1] (x <= 1)` |
| `(G[#,#] (a < #)) -> (G[#,#] (b < #))` | 33 | 1.4% | `(G[0,30] (w < 3000)) -> (G[0,4] (v < 35))` |
| `(F[#,#] a) && (F[#,#] b)` | 29 | 1.3% | `(F[a,b] z_i) && (F[a,b] z_j)` |
| `F[#,#] (a >= #)` | 23 | 1.0% | `F[0,1] (x >= 0)` |
| `G[#,#] (!a)` | 21 | 0.9% | `G[5,8] (!c)` |
| `G[#,#] ((# <= a) && (a <= #))` | 18 | 0.8% | `G[0,10] ((2 <= y) && (y <= 4))` |
| `G[#,inf] (a -> (F[#,#] b))` | 17 | 0.7% | `G[0,inf] (a -> (F[1,2] b))` |
| `G[#,#] (a >= #)` | 15 | 0.6% | `G[a,b] (x >= 0)` |
| `F[#,#] (a < #)` | 13 | 0.6% | `F[0,3] (x < 0)` |
| `(F[#,#] a) \|\| (F[#,#] b)` | 13 | 0.6% | `(F[0,t_1] mu_1) \|\| (F[0,t_1] mu_2)` |
| `F[#,#] (a <= #)` | 12 | 0.5% | `F[0,1] (x <= 1)` |
| `(G[#,#] a) && (F[#,#] b)` | 12 | 0.5% | `(G[1,T] a) && (F[1,T] b)` |
| `F[#,inf] a` | 11 | 0.5% | `F[a,inf] p` |
| `a U[#,inf] b` | 11 | 0.5% | `A U[0,inf] B` |
| `G[#,#] (F[#,#] (G[#,#] (a - b >= #)))` | 11 | 0.5% | `G[0,72] (F[0,8] (G[0,5] (y_2 - y_1 >= 9)))` |
| `(F[#,#] (G[#,#] a)) \|\| (F[#,#] (G[#,#] b))` | 11 | 0.5% | `(F[0,15] (G[0,5] Reg_4_4)) \|\| (F[0,15] (G[0,5] Reg_2_2))` |
| `G[#,#] (!((a >= #) && (a <= #) && (b >= #) && (b <= #)))` | 11 | 0.5% | `G[0,10] (!((v >= -1) && (v <= 1) && (x >= 1) && (x <= 2)))` |
| `G[#,inf] a` | 10 | 0.4% | `G[0,inf] psi` |
| `G[#,#] (a - b <= #)` | 10 | 0.4% | `G[0,100] (y_5 - y_4 <= 40)` |
| `G[#,#] (F[#,#] (a - b >= #))` | 10 | 0.4% | `G[0,70] (F[0,30] (y_5 - y_4 >= 15))` |
| `G[#,#] (\|a - b\| <= #)` | 10 | 0.4% | `G[5,10] (\|x_1 - x_2\| <= 2)` |
| `G[#,#] (a && b)` | 10 | 0.4% | `G[0,5] (mu_1 && mu_2)` |

## Skeletons

The skeleton of a formula is its temporal and Boolean structure, as stl-nl's `scripts/formula_patterns.py` computes it (`src/normalization/skeleton.py`, from stlgen's AST): each distinct relation or Boolean signal is a Greek letter, which repeats only when the exact same condition repeats; bounds are `[#,#]`, or `[#,inf]` when unbounded; the operands of `+ * && || == !=` are unordered. It is coarser than the pattern, which also keeps the relations. The manifest has the skeleton of each formula ok (`skeleton`); the example is the shortest formula of each skeleton.

| Level, formulas | Formulas | Distinct | Seen once | Top 10 cover |
|---|---|---|---|---|
| Skeleton, ok | 2317 | 429 | 281 | 60.3% |
| Skeleton, kept for stl-nl | 1200 | 429 | 303 | 35.2% |
| Pattern, ok | 2317 | 680 | 462 | 42.6% |
| Pattern, kept for stl-nl | 1200 | 680 | 508 | 8.3% |

| Skeleton | Formulas ok | Share | Kept for stl-nl | Example |
|---|---|---|---|---|
| `G[#,#] φ` | 468 | 20.2% | 107 | `G[2,6] p` |
| `F[#,#] φ` | 413 | 17.8% | 85 | `F[0,7] p` |
| `φ U[#,#] ψ` | 185 | 8.0% | 25 | `p U[a,b] q` |
| `G[#,#] F[#,#] φ` | 82 | 3.5% | 45 | `G[0,2] (F[2,4] p)` |
| `F[#,#] G[#,#] φ` | 53 | 2.3% | 19 | `F[a,b] (G[c,d] p)` |
| `G[#,#] (φ && ψ)` | 49 | 2.1% | 37 | `G[0,5] (mu_1 && mu_2)` |
| `(F[#,#] φ) && (G[#,#] ψ)` | 46 | 2.0% | 41 | `(G[1,T] a) && (F[1,T] b)` |
| `(F[#,#] φ) && (F[#,#] ψ)` | 39 | 1.7% | 20 | `(F[a,b] z_i) && (F[a,b] z_j)` |
| `(G[#,#] φ) -> G[#,#] ψ` | 36 | 1.6% | 13 | `(G[0,30] (w < 3000)) -> (G[0,4] (v < 35))` |
| `G[#,inf] φ` | 26 | 1.1% | 22 | `G[0,inf] psi` |
| `G[#,#] !φ` | 24 | 1.0% | 12 | `G[5,8] (!c)` |
| `G[#,inf] (φ -> F[#,#] ψ)` | 22 | 0.9% | 14 | `G[0,inf] (a -> (F[1,2] b))` |
| `F[#,#] (φ && ψ)` | 22 | 0.9% | 22 | `F[0,10] (p && q)` |
| `G[#,#] (φ -> F[#,#] ψ)` | 19 | 0.8% | 18 | `G[0,10] (p -> (F[0,5] q))` |
| `G[#,#] (φ -> ψ)` | 15 | 0.6% | 14 | `G[a,b] ((x == k) -> varphi_k)` |
| `G[#,#] F[#,#] G[#,#] φ` | 14 | 0.6% | 6 | `G[2,4] (F[3,5] (G[1,3] p))` |
| `(F[#,#] φ) \|\| (F[#,#] ψ)` | 14 | 0.6% | 8 | `(F[0,t_1] mu_1) \|\| (F[0,t_1] mu_2)` |
| `(G[#,#] φ) && (G[#,#] ψ)` | 13 | 0.6% | 12 | `(G[0,H] Z) && (G[0,H] P)` |
| `F[#,inf] φ` | 12 | 0.5% | 8 | `F[a,inf] p` |
| `φ U[#,inf] ψ` | 12 | 0.5% | 11 | `A U[0,inf] B` |
| `(F[#,#] φ) && ψ` | 12 | 0.5% | 8 | `p_1 && (F[0,2] p_2)` |
| `F[#,#] (φ \|\| ψ)` | 11 | 0.5% | 10 | `F[0,40] (p_1 \|\| p_3)` |
| `(F[#,#] φ) \|\| (G[#,#] ψ)` | 11 | 0.5% | 10 | `(G[4,8] (x_10 > 0.1)) \|\| (F[8,14] (x_10 < 0.1))` |
| `(F[#,#] G[#,#] φ) \|\| (F[#,#] G[#,#] ψ)` | 11 | 0.5% | 5 | `(F[0,15] (G[0,5] Reg_4_4)) \|\| (F[0,15] (G[0,5] Reg_2_2))` |
| `G[#,#] !(φ && ψ && χ && θ)` | 11 | 0.5% | 10 | `G[0,10] (!((v >= -1) && (v <= 1) && (x >= 1) && (x <= 2)))` |
| `G[#,#] F[#,#] ((G[#,#] φ) -> G[#,#] ψ)` | 10 | 0.4% | 2 | `G[0,72] (F[0,8] ((G[0,5] (y_2 - y_1 > 9)) -> (G[5,20] (y_5 - y_4 > 7))))` |
| `(G[#,#] φ) \|\| (G[#,#] ψ)` | 10 | 0.4% | 9 | `(G[a,b] varphi_1) \|\| (G[a,b] varphi_2)` |
| `G[#,#] ((F[#,#] φ) \|\| (G[#,#] ψ))` | 9 | 0.4% | 2 | `G[0,19] ((G[0,5] (b_1 <= 20)) \|\| (F[0,5] (b_2 >= 40)))` |
| `(F[#,#] φ) && (G[#,#] !ψ)` | 9 | 0.4% | 6 | `(F[0,10] a) && (G[0,20] (!b))` |
| `(F[#,#] φ) && (G[#,#] (ψ && χ))` | 9 | 0.4% | 5 | `(F[0,5] (vx > 0.5)) && (G[0,5] ((z > 1) && (z < 2)))` |

## Selection for stl-nl

Of the formulas ok, one with the same normalized text as an earlier one is left out (`duplicate`; the manifest gives the id of the first in `duplicate_of`), and at most 10 formulas of each pattern are kept, taken from the papers in turn, at random with the seed (`pattern_cap`). Only the formulas kept are written in `stl/`.

| Selection | Formulas | Share of ok |
|---|---|---|
| kept | 1200 | 51.8% |
| duplicate | 567 | 24.5% |
| pattern_cap | 550 | 23.7% |

19 patterns are cut:

| Pattern | Formulas (no duplicates) | Kept |
|---|---|---|
| `F[#,#] a` | 183 | 10 |
| `G[#,#] a` | 140 | 10 |
| `a U[#,#] b` | 80 | 10 |
| `G[#,#] (a > #)` | 41 | 10 |
| `F[#,#] (G[#,#] a)` | 37 | 10 |
| `G[#,#] (a < #)` | 31 | 10 |
| `F[#,#] (a > #)` | 31 | 10 |
| `G[#,#] (F[#,#] a)` | 27 | 10 |
| `G[#,#] (a <= #)` | 25 | 10 |
| `F[#,#] (a >= #)` | 20 | 10 |
| `G[#,#] (!a)` | 19 | 10 |
| `(F[#,#] a) && (F[#,#] b)` | 17 | 10 |
| `G[#,inf] (a -> (F[#,#] b))` | 16 | 10 |
| `G[#,#] (a >= #)` | 14 | 10 |
| `F[#,#] (a < #)` | 13 | 10 |
| `(G[#,#] (a < #)) -> (G[#,#] (b < #))` | 12 | 10 |
| `(G[#,#] a) && (F[#,#] b)` | 12 | 10 |
| `F[#,#] (a <= #)` | 11 | 10 |
| `G[#,#] (!((a >= #) && (a <= #) && (b >= #) && (b <= #)))` | 11 | 10 |
