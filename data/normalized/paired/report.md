# Normalized paired formulas

From `data/dataset/stl_dataset.jsonl` (3255 formulas, each with the requirement the paper gives it), with the rules of `docs/normalization_rules.md` in the faithful mode: the meaning the requirement describes is kept, so the bounds and powers stay as the paper writes them, beyond the grammar of stl-nl, and the rules that would change the meaning reject the formula. These formulas don't go to stl-nl: they are checked by the normalizer's own parser only, not by stlgen.

## By status

| Status | Formulas | Share |
|---|---|---|
| ok | 1614 | 49.6% |
| needs_review | 0 | 0.0% |
| rejected | 1641 | 50.4% |

## Why formulas are rejected

Each formula is counted under the first rule that rejects it: a single construct the rule can't accept rejects the whole formula, even when the rest is valid STL.

| Rule | Formulas | Why it is rejected |
|---|---|---|
| parse_error | 277 | a construct the parser can't read (a subscript where none can go, an unexpected symbol, unbalanced brackets): it is never guessed |
| unknown_command | 272 | a LaTeX command the paper doesn't define and the normalizer has no translation for (it is not an STL operator, connective, comparison, font or spacing command): its meaning is unknown, so the whole formula is rejected even if the rest is valid STL |
| indexed_operator | 168 | an operator over an index (\bigwedge, \bigvee, \land_{i}, \sum, \ldots, ...): the number of terms isn't known, so it can't be written out |
| other_logic | 161 | the paper writes it in another logic (past-time, spatial, probabilistic, strategic): its operators have no STL equivalent |
| power | 148 | a superscript that is neither an integer exponent nor part of a name (\rho^{\varphi}, [1,1]^T, x^{(j)}, 30^\circ), or an integer superscript on a Boolean atom (\pi^8 \vee \pi^9: a label, not a power) |
| semantics_definition | 105 | a definition of the semantics (\models, \vDash): it says when a signal satisfies a formula, it is not a formula itself |
| multiplication | 87 | two terms side by side: a product with a space (k x), a unit (200 N) or a missing operator |
| nonstandard_operator | 69 | an operator STL doesn't have (\boxplus, \sqcup, ...), or a G/F/U/R with a script that isn't an interval |
| function | 61 | a function applied to something (rho(G_{[a,b]} phi,t), x(t+1), \max, \min, \log, ...): stl-nl has no functions (a call on names and integers only, Reg(4,4), is kept as one name) |
| set_membership | 55 | \in a set that is not an interval: STL can only compare a signal with numbers |
| quantifier | 48 | a quantifier (\forall, \exists): STL has none |
| several_formulas | 45 | several formulas, or a formula with text (where, and, if, ...): stl-nl takes exactly one formula |
| connective_at_edge | 44 | starts or ends with a connective (\land, \lor, ...): the extraction found that the rest of the formula is on another row |
| operator_definition | 38 | a definition of an operator in terms of others (F_{[a,b]} phi := true U_{[a,b]} phi): the left side of = or := is not a single name |
| grammar_definition | 23 | a grammar of the logic (::=, \mid, \| between alternatives): it lists the forms a formula can take, it is not a formula itself |
| close_parentheses | 19 | brackets left open at the end: the formula may have been cut, and the description may be about the part that is missing |
| overline_operator | 11 | an operator with a line over it is a variant of the paper (averaged, marked, ...) with its own semantics, which the plain operator would lose |
| operator_alone | 4 | a temporal operator with no operand (F_{[a,b]}, U_{[a,b]} alone, or at the end): an operator, not a formula |
| macro_loop | 4 | a macro of the paper still left after 10 rounds of expansion: it never turns into a formula |
| unbounded_operator | 1 | an infinite lower bound, or \infty in a bound expression |
| negative_bound | 1 | a negative time bound |

### Examples of each rule

Up to 3 formulas per rule, from different papers and showing different cases of the rule. *Example* is the formula as the paper writes it. *Why* names the part that made the rule reject it, written after the paper's macros are expanded and with the names normalized (\varphi_{1} is varphi_1); *(macro)* marks an example where that part comes from a macro of the paper, so it can't be seen in the formula as written.

**parse_error** (277 formulas): a construct the parser can't read (a subscript where none can go, an unexpected symbol, unbalanced brackets): it is never guessed.

| Example | Why |
|---|---|
| `\Box_{[0,5]} s \le s_{*1}` | the subscript `*1` is on a name, but it is neither an interval nor part of the name |
| `\psi = \Box (p => \Diamond_{<5} q)` | the parser didn't expect `>` here: `( p = > F q` |
| `P=?~ [ F_{<=100} ~(Agent=g) ]` | the character `?` isn't part of the grammar |

**unknown_command** (272 formulas): a LaTeX command the paper doesn't define and the normalizer has no translation for (it is not an STL operator, connective, comparison, font or spacing command): its meaning is unknown, so the whole formula is rejected even if the rest is valid STL.

| Example | Why |
|---|---|
| `\Diamond_{[0,t_g]}\langle relayed, [0, d_g]\rangle` | `\langle` isn't defined by the paper and the normalizer doesn't know it |
| `\phi_5:=F_{[5,15]}(\\|\boldsymbol{x}_5-\begin{bmatrix} 10 10 \end{bmatrix}\\|\le 5)` | `\begin` isn't defined by the paper and the normalizer doesn't know it |
| `\mathbb{F}^{\le 100}(x \ge 1) \wedge (y = 0)` | `\mathbb` isn't defined by the paper and the normalizer doesn't know it |

**indexed_operator** (168 formulas): an operator over an index (\bigwedge, \bigvee, \land_{i}, \sum, \ldots, ...): the number of terms isn't known, so it can't be written out.

| Example | Why |
|---|---|
| `F_{[t_a,t_b]}(\bigwedge_{j=1}^N\mu_j)` | `\bigwedge` stands for a number of terms that isn't known |
| `\varphi=\Diamond_{[0,5]}\left(\bigvee_z\bigwedge_{i\in\{1,2\}}(z\leq x_i\leq z+0.1)\right)` | `\bigvee` stands for a number of terms that isn't known |
| `\Diamond_{[t_1,t_2]} (x \geq a_1) \wedge \cdots \wedge \Diamond_{[t_3,t_4]} (x \geq a_n)` | `\cdots` stands for a number of terms that isn't known |

**other_logic** (161 formulas): the paper writes it in another logic (past-time, spatial, probabilistic, strategic): its operators have no STL equivalent.

| Example | Why |
|---|---|
| `a \since_{[2,3]} b` | the extraction classed it as past-time logic: its operators (once, since, historically, ...) look back in time, STL's only forward |
| `\phi \sqcap \square_{[a,b]} \psi` | the extraction classed it as a spatial or description logic: its operators are about places or objects |
| `\mathbb{P}[\diamond^{\leq t}G]\sim\theta` | the extraction classed it as a probabilistic logic: its operators are about probabilities |

**power** (148 formulas): a superscript that is neither an integer exponent nor part of a name (\rho^{\varphi}, [1,1]^T, x^{(j)}, 30^\circ), or an integer superscript on a Boolean atom (\pi^8 \vee \pi^9: a label, not a power).

| Example | Why |
|---|---|
| `\square_{[t_1,t_2]}(\neg(x^{(j)}_t \geq c_1))` | `x^(j)` is a power or a superscript that isn't a name |
| `\phi_1 = F_{[5,15]}(\\|x-[10 \; 0]^T\\|\leq 5)` | `^T` is a power or a superscript that isn't a name |
| `\phi^\ast_{\textrm{f}}=\Diamond\Box_{\le30}((3\le x\le6)\wedge(5\le y\le8))` | `phi^\ast` is a power or a superscript that isn't a name |

**semantics_definition** (105 formulas): a definition of the semantics (\models, \vDash): it says when a signal satisfies a formula, it is not a formula itself.

| Example | Why |
|---|---|
| `\bf x\models \Box_{[a,b]}\varphi` | `\models` says when a signal satisfies a formula: this defines the meaning of an operator |
| `(\mathbf{x},t)\vDash F_{[t_1,t_2]}\phi` | `\vDash` says when a signal satisfies a formula: this defines the meaning of an operator |
| `\bf x\models \Box_{[a,b]}\varphi` | `\models` says when a signal satisfies a formula: this defines the meaning of an operator |

**multiplication** (87 formulas): two terms side by side: a product with a space (k x), a unit (200 N) or a missing operator.

| Example | Why |
|---|---|
| `\Box_{[0,5s]}(v\_vel > 0)` | `a time unit in a bound: 5s` is a product |
| `\phi_3 = \square_{[0,T]}(\Delta x>0)` | `Delta x`: two terms side by side are a product |
| `\psi_1 = \square_{[0,20]} (G_Sx \leq H_S)` | `G_S x`: two terms side by side are a product |

**nonstandard_operator** (69 formulas): an operator STL doesn't have (\boxplus, \sqcup, ...), or a G/F/U/R with a script that isn't an interval.

| Example | Why |
|---|---|
| `\tilde{\phi} = \square_{[0,15]}^{\bm{w}} \pi` | `G^{\bm{w}}` isn't an STL operator |
| `\boxplus_{[0,i]} A` | `\boxplus` isn't an STL operator |
| `\Diamond^{-}_{[1,2]} Vaccinated` | `F^{-}` isn't an STL operator |

**function** (61 formulas): a function applied to something (rho(G_{[a,b]} phi,t), x(t+1), \max, \min, \log, ...): stl-nl has no functions (a call on names and integers only, Reg(4,4), is kept as one name).

| Example | Why |
|---|---|
| `\varphi_{green} = G_{[0,3]}\{\varphi_{wait}(17.09) \vee \varphi_{walk}(2100)\}` | `varphi_wait(17.09)` applies a function to something that isn't a name or an integer |
| `\varphi_{\text{classifier}} = \mathbf{G}_{[0.1,\infty)}\left(P(\alpha_t^\top [x_t\ y_t\ z_t] < 0) > 0.95\right …` | `P(\alpha_t^\top[x_t\y_t\z_t]<0)` applies a function to something that isn't a name or an integer |
| `\phi_{\texttt{car}} =G_{[0,20]} \big(d(\vec{s}_{ego},\vec{s}_{car}) > 5\big)` | `d(\vec{s}_{ego},\vec{s}_{car})` applies a function to something that isn't a name or an integer |

**set_membership** (55 formulas): \in a set that is not an interval: STL can only compare a signal with numbers.

| Example | Why |
|---|---|
| `\Box_{[8,8.5]}(x\in D)` | \in says that a signal belongs to a set: STL can only compare it with numbers |
| `\lozenge^{\le T_d}\{y\in \mathsf B\}` | \in says that a signal belongs to a set: STL can only compare it with numbers |
| `\mathbf{G}_{[0,T]} x \in \mathcal{H}` | \in says that a signal belongs to a set: STL can only compare it with numbers |

**quantifier** (48 formulas): a quantifier (\forall, \exists): STL has none.

| Example | Why |
|---|---|
| `\forall \mathbf{G}\mathcal{P} := x_1^2 + x_2 - 3 < 0` | `\forall` is a quantifier |
| `(x = 0)\mathcal{U}_{\leq 5}(\exists^{4} \bigcirc (0.1 \leq x \leq 0.4))` | `\exists` is a quantifier |
| `\Box\forall x.\, in(x)\rightarrow\Diamond_{[0,6)}\, out(x)` | `\forall` is a quantifier |

**several_formulas** (45 formulas): several formulas, or a formula with text (where, and, if, ...): stl-nl takes exactly one formula.

| Example | Why |
|---|---|
| `\varphi_1 := \ev_{[0, 9]}(x(t) = (0,4))` | a comma inside brackets separates formulas (a set or a tuple) |
| `a_l \text{if}\;\;\; G_{[a_l,b_l]} \mu_l` | the word "if" joins the formula to text or to another formula |
| `\Phi_2 = \mathbf{G}_{[0,60]} ((x,y) \!\in\! L)` | a comma inside brackets separates formulas (a set or a tuple) |

**connective_at_edge** (44 formulas): starts or ends with a connective (\land, \lor, ...): the extraction found that the rest of the formula is on another row.

| Example | Why |
|---|---|
| `\wedge\Box_{[0,200]} (C\le0.1)` | it starts or ends with a connective: the rest of the formula is on another row of the paper |
| `\wedge\Box_{[0,100]} (D\le0.05)` | it starts or ends with a connective: the rest of the formula is on another row of the paper |
| `\wedge \TBoxOp{[T,10]}{\neg \mathtt{gear}_4}` | it starts or ends with a connective: the rest of the formula is on another row of the paper |

**operator_definition** (38 formulas): a definition of an operator in terms of others (F_{[a,b]} phi := true U_{[a,b]} phi): the left side of = or := is not a single name.

| Example | Why |
|---|---|
| `\mathbf{F}_{[a,b]}\Phi := \top \mathbf{U}_{[a,b]}\Phi` | the left side of := (or \equiv) is an expression, not a name: the formula defines it |
| `\square_{[t_1,t_2]} G G=\{S = N\}` | a temporal operator is on the left of =: the formula defines that operator |
| `F_{[0,5]} status = \lnot sidewalk` | a temporal operator is on the left of =: the formula defines that operator |

**grammar_definition** (23 formulas): a grammar of the logic (::=, \mid, \| between alternatives): it lists the forms a formula can take, it is not a formula itself.

| Example | Why |
|---|---|
| `{\phi ::= F_{[0, 5]}\\|x - x^*\\| \leq \epsilon}` | `::=` introduces the forms a formula can take: a grammar |
| `\varphi_{i} := F_{[a,b]}\mu_i\|G_{[a,b]}\mu_i` | a `\|` separates the alternatives of a grammar (it can't be read as an absolute value) |
| `\Box_{[0,50]} \mid x_2 - x_3 \mid \le 10` | `\mid` introduces the forms a formula can take: a grammar |

**close_parentheses** (19 formulas): brackets left open at the end: the formula may have been cut, and the description may be about the part that is missing.

| Example | Why |
|---|---|
| `{G_{[t_0,t_e]}((F_{[0,t_{s}]}(u_2))}` | a bracket is never closed: the formula was cut, the rest is on another row of the paper |
| `G \big(\text{pedestrian} \implies F_{[0, 5]}` | a bracket is never closed: the formula was cut, the rest is on another row of the paper |
| `\phi_2 = G_{[0,T]}((x-x_1)^2+(y-y_1)^2\leq r_1^2` | a bracket is never closed: the formula was cut, the rest is on another row of the paper |

**overline_operator** (11 formulas): an operator with a line over it is a variant of the paper (averaged, marked, ...) with its own semantics, which the plain operator would lose.

| Example | Why |
|---|---|
| `\phi := F_{(0,5)} \mu_\text{R1}^\text{Ri}\wedge G_{[0,\infty)}\Big(\mu_\text{O1}^\text{Ri}\wedge \mu_\text{O2} …` | a line over an operator marks the paper's own variant of it (averaged, marked, ...) |
| `\DiaOp{[0,T]}\varphi\lor \TDiaOp{[T,T+\delta]}\varphi` *(macro)* | a line over an operator marks the paper's own variant of it (averaged, marked, ...) |
| `\G_{[10,150]}((z_1 < 0.2) \rightarrow \underline{\F}_{[1,3]}(z_2 < 0.3))` *(macro)* | a line over an operator marks the paper's own variant of it (averaged, marked, ...) |

**operator_alone** (4 formulas): a temporal operator with no operand (F_{[a,b]}, U_{[a,b]} alone, or at the end): an operator, not a formula.

| Example | Why |
|---|---|
| `G_{[t_{0},t_{e}]}` | the operator `G` has no operand |
| `\varphi_1:(1\!\le\! \textit{pos}_0\!-\!\textit{pos}_1 \!\le \! 3)\until[2,3]` | the formula ends right after the operator `U` |
| `\mu = \eventually[\phi, m]` *(macro)* | the operator `F` has no operand |

**macro_loop** (4 formulas): a macro of the paper still left after 10 rounds of expansion: it never turns into a formula.

| Example | Why |
|---|---|
| `\varphi_{stayIn} = \square_{[0,20]}\code{region}, \text{ where}` *(macro)* | a macro of the paper keeps expanding without end |
| `\phi^{MTL}_{bound.overload} \defeq \G (oload_i \rightarrow \F_{[0, \kappa]} \neg oload_i)` *(macro)* | a macro of the paper keeps expanding without end |
| `\mathbf{G}\bigl(\, \mathit{Says}(\atom{atc},\ \atom{cmd\_descend}(\atom{AZA545},\atom{FL120})) \rightarrow \ma …` *(macro)* | a macro of the paper keeps expanding without end |

**unbounded_operator** (1 formulas): an infinite lower bound, or \infty in a bound expression.

| Example | Why |
|---|---|
| `\phi_1 := G_{[10,\infty)]} \big(\|c_e\|\le 2.25\big)` | `\infty` |

**negative_bound** (1 formulas): a negative time bound.

| Example | Why |
|---|---|
| `\mathsf{sunny} \; \U_{[-3,-1]}\; (\mathsf{cloudy} \wedge \finally_{\geq 1}\; \mathsf{ rainy})` *(macro)* | `[-3,-1]` |

## Most frequent unknown commands

Candidates for a new rule. Many come from the paper's macros: its definition of an operator uses a command to draw the symbol (\raisebox, \rotatebox, ...).

| Command | Formulas | Written in the formula | From a macro | Example |
|---|---|---|---|---|
| `\langle` | 22 | 19 | 3 | `\Diamond_{[0,t_g]}\langle relayed, [0, d_g]\rangle` |
| `\begin` | 20 | 19 | 1 | `\phi_5:=F_{[5,15]}(\\|\boldsymbol{x}_5-\begin{bmatrix} 10 10 \end{bmatrix}\\|\le 5)` |
| `\mathbb` | 13 | 5 | 8 | `\mathbb{F}^{\le 100}(x \ge 1) \wedge (y = 0)` |
| `\notin` | 12 | 12 | 0 | `\square^{\leq T} s \notin S_{unsafe}` |
| `\defeq` | 9 | 9 | 0 | `\varphi_1\defeq\always_{[0,\, 15]}\, p_1` |
| `\ell` | 8 | 8 | 0 | `\mathbf{G}_{[0,5]} \ell` |
| `\parallel` | 8 | 8 | 0 | `\Psi_1 = F_{[0,10]}(\parallel \textbf{x}_1 - [3,1]^T \parallel < 0.5)` |
| `\deg` | 8 | 8 | 0 | `F_{[0,35]}G_{[30,35]}((\Vert \boldsymbol{p}_{1}-[0.7;0.6]\Vert \leq 0.05) \wedge(\vert \deg(x_{1,3}) - 0 \vert …` |
| `\underbrace` | 8 | 8 | 0 | `\texttt{TYPE}(\omega, \text{type}) \coloneqq \Diamond_{[0,T]} \underbrace{\big(\omega(t) \models \text{type}\b …` |
| `\gls` | 8 | 8 | 0 | `\gls{psistl}_{pick} = G(pick \Rightarrow (F_{[0,30]}(d_{obj} < 1)))` |
| `\formula` | 7 | 7 | 0 | `\formula_4 = (x_2 \notin Z_1) \until_{[0,5]} (x_3 \notin Z_1)` |
| `\not` | 7 | 7 | 0 | `X(\omega),t\not\models\Diamond_{(1,4)}p` |
| `\boxbox` | 7 | 4 | 3 | `\boxbox_{ ([0, +\infty), \mathsf{School})}\always_{[0,30]} (\agr_{([0,1], \top)}^{\avg} x_\mathsf{Noise} < 50)` |
| `\%` | 6 | 6 | 0 | `\Diamond_{[0,\delta]}(\Box(\|(s-s_{ref})/s_{ref}\|<5\%))` |
| `\blacklozenge` | 5 | 4 | 1 | `\blacklozenge_{[0,3600]}` |
| `\raisebox` | 4 | 0 | 4 | `\diamondplus_{[1.5,3]} \varphi` (in a macro of the paper) |
| `\downarrow` | 4 | 1 | 3 | `\Box \downarrow^{\mathrm{cid}} c. \downarrow^{\mathrm{tid}} t. \downarrow^{\mathrm{amt}} a. \mathrm{trans}(c,  …` |
| `\uparrow` | 4 | 4 | 0 | `\square(\uparrow (cmd \geq m) \rightarrow \lozenge_{[0,T]} \square_{[0,a]} (\|cmd - pos\| \leq n))` |
| `\Longrightarrow` | 4 | 4 | 0 | `\Box(B_1 \Longrightarrow \Diamond_{[0,b]} B_2)` |
| `\Tilde` | 4 | 4 | 0 | `\formula{}{1}:=(\leventually_{[5,10]}(\AgtTrajNoT{1}\in{R_1}))\land(\lglobally_{[0,15]}(\AgtTrajNoT{1}\in{\Til …` |
| `\tag` | 3 | 3 | 0 | `\tag{P1} \always \freeze{cid}{c} \freeze{tid}{t} \freeze{sum}{a} \mathit{trans}(c,t,a)\wedge a>2000 \rightarro …` |
| `\Perm` | 3 | 3 | 0 | `\Perm{\alpha}{\eventually_{\leq n} \matom{reachExit}}` |
| `\scalebox` | 3 | 2 | 1 | `\frac{ \left( \scalebox{0.94}{\begin{tabular}{c} $(b < a \land [x'=\theta \ \ \ \chi]\phi) \ \lor$ $((\chi \lo …` |
| `\mathlarger` | 3 | 0 | 3 | `(\mathcal{X}, t) \mymodels \Box_{[a,b]}\varphi \:\Leftrightarrow \forall t' \in t+[a, b]: (\mathcal{X}, t') \m …` (in a macro of the paper) |
| `\cup` | 3 | 3 | 0 | `\evt_{(0,k]} Q \rightarrow (\neg Q \cup _{[0,k)} P)` |
| `\eqqcolon` | 3 | 3 | 0 | `\Phi_H \eqqcolon \mathrm{G}_{[t_\mathrm{start}, t_\mathrm{end}]} (\mathtt{head\_on})` |
| `\underline` | 3 | 3 | 0 | `\underline{\G_{[0,2]}(T > 22) \land \F_{[2,4]}(T > 30)}` |
| `\Diamonddot` | 2 | 2 | 0 | `\phi_R := \Diamonddot_{[1000,2000]}\phi_{W_h}\Rightarrow \Diamonddot_{[0,800]}\neg \phi_{W_h}` |
| `\True` | 2 | 2 | 0 | `\Always_{[0,t]}\ \Eventually_{[0,5]}\ \mathtt{x}\!-\!2 \!>\! 0 ~~\equiv~~ \neg ( \True\ \Until_{[0,t]}\ \True\ …` |
| `\stackrel` | 2 | 0 | 2 | `\phi_{RPS} \eqdef \G_{[0, k]}(\phi_{i}^R \wedge \phi_{i}^P \wedge \phi_{i}^S)` (in a macro of the paper) |

## Patterns

The pattern of a formula is its normalized text with every number written # and the names renamed a, b, ... in the order they appear (a name used twice keeps its letter; operators and comparisons are kept). Formulas that differ only in their numbers and names have the same pattern. The manifest has the pattern of each formula (`pattern`); the example is the shortest formula of each pattern.

1614 formulas kept have 695 patterns; 497 of them have one formula only. The 30 most common cover 695 formulas (43%).

| Pattern | Formulas | Share | Example |
|---|---|---|---|
| `F[#,#] a` | 134 | 8.3% | `F[3,8] p` |
| `G[#,#] a` | 114 | 7.1% | `G[0,0] B` |
| `a U[#,#] b` | 68 | 4.2% | `p U[a,b] q` |
| `G[#,inf] (a -> (F[#,#] b))` | 33 | 2.0% | `G[0,inf] (p -> (F[2,3] q))` |
| `G[#,#] (!a)` | 33 | 2.0% | `G[0,T] (!p)` |
| `G[#,#] (a < #)` | 28 | 1.7% | `G[0,1] (a < 1)` |
| `G[#,#] (a > #)` | 26 | 1.6% | `G[2,5] (x > 3)` |
| `G[#,#] (a <= #)` | 23 | 1.4% | `G[0,T] (s <= 0)` |
| `F[#,#] (a > #)` | 22 | 1.4% | `F[0,1] (k > 3)` |
| `F[#,#] (G[#,#] a)` | 18 | 1.1% | `F[0,6] (G[0,4] A)` |
| `F[#,#] (a < #)` | 18 | 1.1% | `F[0,2] (x < 5)` |
| `G[#,#] (a >= #)` | 18 | 1.1% | `G[a,b] (h_x >= 0)` |
| `G[#,#] (F[#,#] a)` | 16 | 1.0% | `G[0,6] (F[0,3] g)` |
| `F[#,#] (a >= #)` | 14 | 0.9% | `F[0,10] (v >= 80)` |
| `G[#,#] (a >= b)` | 13 | 0.8% | `G[15,60] (x >= h_1)` |
| `G[#,#] ((# * a <= b) && (b <= # * a))` | 11 | 0.7% | `G[0,T] ((0.8 * lambda_ref <= lambda) && (lambda <= 1.2 * lambda_ref))` |
| `G[#,inf] a` | 11 | 0.7% | `G[0,inf] psi` |
| `G[#,#] (\|a - b\|^# <= #)` | 11 | 0.7% | `G[1,2] (\|x_4 - x_5\|^2 <= 26.75)` |
| `(F[#,#] a) && (F[#,#] b)` | 10 | 0.6% | `(F[0,T] A) && (F[0,T] B)` |
| `(G[#,#] (a < #)) -> (G[#,#] (b < #))` | 10 | 0.6% | `(G[0,30] (omega < 3000)) -> (G[0,4] (v < 35))` |
| `G[#,#] (a < b)` | 7 | 0.4% | `G[a,b] (x < c)` |
| `F[#,#] (a <= #)` | 7 | 0.4% | `F[0,5] (x_2 <= 10)` |
| `(F[#,#] a) && (G[#,#] (!b))` | 7 | 0.4% | `(F[0,6] T) && (G[0,6] (!O))` |
| `(!a) U[#,#] (G[#,#) a)` | 7 | 0.4% | `(!varphi) U[0,alpha] (G[0,beta) varphi)` |
| `(G[#,#] a) && (F[#,#] b)` | 6 | 0.4% | `(G[1,T] a) && (F[1,T] b)` |
| `G[#,inf] (\|a\| <= #)` | 6 | 0.4% | `G[0,inf] (\|v\| <= 2.42)` |
| `F[#,inf] a` | 6 | 0.4% | `F[20,inf] a` |
| `G[#,inf] (a -> (F[#,#] (!a)))` | 6 | 0.4% | `G[0,inf] (miss -> (F[0,w] (!miss)))` |
| `(F[#,#] (a && (F[#,#] b))) && (G[#,#] (!c))` | 6 | 0.4% | `(F[2,6] (G_1 && (F[3,7] G_2))) && (G[0,15] (!Obs))` |
| `F[#,#] (((# <= a) && (a <= #)) && ((# <= b) && (b <= #)))` | 6 | 0.4% | `F[0,10] (((3 <= x) && (x <= 5)) && ((4 <= y) && (y <= 6)))` |

## Skeletons

The skeleton of a formula is its temporal and Boolean structure, as stl-nl's `scripts/formula_patterns.py` computes it (`src/normalization/skeleton.py`, from stlgen's AST): each distinct relation or Boolean signal is a Greek letter, which repeats only when the exact same condition repeats; bounds are `[#,#]`, or `[#,inf]` when unbounded; the operands of `+ * && || == !=` are unordered. It is coarser than the pattern, which also keeps the relations. The manifest has the skeleton of each formula ok (`skeleton`); the example is the shortest formula of each skeleton.

These formulas can't all be parsed by stlgen (their bounds and powers go beyond its grammar): their AST is built from the normalizer's own tree (`src/normalization/stlgen_ast.py`), which gives the same skeleton as stlgen's AST for every formula stlgen can parse. Every finite interval is `[#,#]`, open or not; a power is `^`.

| Level, formulas | Formulas | Distinct | Seen once | Top 10 cover |
|---|---|---|---|---|
| Skeleton, ok | 1614 | 392 | 264 | 55.4% |
| Pattern, ok | 1614 | 695 | 497 | 30.9% |

| Skeleton | Formulas ok | Share | Example |
|---|---|---|---|
| `G[#,#] φ` | 306 | 19.0% | `G[0,0] B` |
| `F[#,#] φ` | 231 | 14.3% | `F[3,8] p` |
| `φ U[#,#] ψ` | 88 | 5.5% | `p U[a,b] q` |
| `G[#,inf] (φ -> F[#,#] ψ)` | 52 | 3.2% | `G[0,inf] (p -> (F[2,3] q))` |
| `G[#,#] (φ && ψ)` | 47 | 2.9% | `G[0,3] ((T < 75) && (T > 60))` |
| `F[#,#] G[#,#] φ` | 39 | 2.4% | `F[0,6] (G[0,4] A)` |
| `G[#,#] !φ` | 38 | 2.4% | `G[0,T] (!p)` |
| `G[#,#] F[#,#] φ` | 38 | 2.4% | `G[0,6] (F[0,3] g)` |
| `G[#,inf] φ` | 29 | 1.8% | `G[0,inf] psi` |
| `G[#,#] (φ -> F[#,#] ψ)` | 26 | 1.6% | `G[0,a] ((y > 0) -> (F[b,c] (x > 0)))` |
| `(F[#,#] φ) && (G[#,#] ψ)` | 24 | 1.5% | `(G[1,T] a) && (F[1,T] b)` |
| `(F[#,#] φ) && (F[#,#] ψ)` | 17 | 1.1% | `(F[0,T] A) && (F[0,T] B)` |
| `G[#,#] (φ -> ψ)` | 16 | 1.0% | `G[0,tau_1) (phi_t1 -> phi_t2)` |
| `(G[#,#] φ) && (G[#,#] ψ)` | 15 | 0.9% | `(G[0,2] mu_C) && (G[2,3] mu_D)` |
| `(G[#,#] φ) -> G[#,#] ψ` | 13 | 0.8% | `(G[0,30] (omega < 3000)) -> (G[0,4] (v < 35))` |
| `(F[#,#] φ) && (G[#,#] !ψ)` | 11 | 0.7% | `(F[0,6] T) && (G[0,6] (!O))` |
| `F[#,#] (φ && ψ && χ && θ)` | 10 | 0.6% | `F[5,25] ((x >= 0) && (x <= 2) && (y >= 8) && (y <= 10))` |
| `F[#,#] (φ && ψ)` | 10 | 0.6% | `F[0,10] ((10 <= x) && (x <= 11))` |
| `G[#,inf] (φ && ψ)` | 9 | 0.6% | `G[0,inf] (psi_1 && psi_2)` |
| `G[#,#] (φ && ψ && χ && θ)` | 8 | 0.5% | `G[0,4) ((x > 10) && (x < 14) && (y > 6) && (y < 10))` |
| `G[#,inf] (φ -> F[#,#] G[#,#] ψ)` | 7 | 0.4% | `G[0,inf] ((x >= p) -> (F[0,s_2] (G[0,s_1] (x < p))))` |
| `G[#,#] (φ -> G[#,#] ψ)` | 7 | 0.4% | `G[0,20] ((u_1 < 0) -> (G[0,5] (u_2 >= 0)))` |
| `G[#,inf] F[#,#] φ` | 7 | 0.4% | `G[0,inf] (F[0,2] A)` |
| `(!φ) U[#,#] (G[#,#] φ)` | 7 | 0.4% | `(!varphi) U[0,alpha] (G[0,beta) varphi)` |
| `(F[#,#] φ) && (F[#,#] ψ) && (G[#,#] χ)` | 7 | 0.4% | `(F[0,3] A_1) && (F[4,6] A_2) && (G[8,10] A_3)` |
| `F[#,inf] φ` | 6 | 0.4% | `F[20,inf] a` |
| `G[#,inf] (φ -> F[#,#] !φ)` | 6 | 0.4% | `G[0,inf] (miss -> (F[0,w] (!miss)))` |
| `(F[#,#] ((F[#,#] φ) && ψ)) && (G[#,#] !χ)` | 6 | 0.4% | `(F[2,6] (G_1 && (F[3,7] G_2))) && (G[0,15] (!Obs))` |
| `φ -> F[#,#] ψ` | 6 | 0.4% | `A -> (F[0,10] B)` |
| `F[#,#] ((F[#,#] φ) && ψ)` | 5 | 0.3% | `F[0,20] (pi_1 && (F[10,20] pi_2))` |

## Beyond the grammar of stl-nl

What the faithful mode keeps as the paper writes it, where the stl-nl mode would change it. 169 of the 1614 formulas ok use at least one; the others are in stl-nl's grammar.

| Rule | Formulas | What it keeps | Example | Normalized as |
|---|---|---|---|---|
| open_intervals | 96 | an open or half-open interval kept open: F(2,12] (faithful mode) | `\Box_{[0,4)}\psi` | `G[0,4) psi` |
| real_bounds | 43 | a time bound that isn't an integer kept as written: F[0,2.5] (faithful mode) | `\Diamond_{(0, 1.5]} A` | `F(0,1.5] A` |
| powers | 27 | a power with an integer exponent kept: x^2, (x - 1)^2, \|x\|^2 (faithful mode) | `G_{[0,2]}(x_4^2 + x_5^2 > 1.5^2)` | `G[0,2] (x_4^2 + x_5^2 > 1.5^2)` |
| bound_expressions | 27 | a time bound written as an expression of symbols kept: G[T,T + delta] (faithful mode) | `\mathsf{F}_{[0,\|s\|)}(s' > 0.1 \wedge \mathsf{F}_{[0,20]} s' < -0.1)` | `F[0,\|s\|) ((s_prime > 0.1) && (F[0,20] (s_prime < -0.1)))` |

## Descriptions

Each requirement passage of a formula ok is written to match the normalized formula (`src/normalization/description.py`): plain text, its math read with the paper's macros and the same lexer as the formula, so that each symbol is written as in the formula (`$\varphi_{1}$` is `varphi_1`), text-mode LaTeX made plain, Unicode letters of PDFs written as names. What can't be converted is left as written: it is counted here, and nothing is dropped for it yet. The manifest has, for each passage, `normalized` and what was left (`unreadable`, `references`, `latex_left`, `names_not_in_formula`).

| Passages | Count | Share |
|---|---|---|
| passages | 1719 |  |
| changed by the normalization | 1081 | 62.9% |
| with nothing left as written | 1615 | 93.9% |
| with a math span left as written (unreadable) | 79 | 4.6% |
| with a reference (\ref, \cite, ...) | 23 | 1.3% |
| with another LaTeX command left | 7 | 0.4% |
| with a name the formula doesn't have | 404 | 23.5% |

### Math left as written

Spans the lexer can't read, by the rule that stops it (the same rules that reject a formula).

| Reason | Spans | Example |
|---|---|---|
| unknown_command | 57 | `$\sec$` |
| quantifier | 20 | `$\forall t \in [a,b]$` |
| parse_error | 11 | `$L_{1:3}$` |
| semantics_definition | 11 | `$\s_k\vDash\varphi$` |
| power | 6 | `$100^{th}$` |
| definition symbol \coloneqq | 4 | `$\phi_2\coloneqq G_{[10,\infty)} (\|c_e\|\le 2.25)$` |
| function | 2 | `$r(x_M,x_P) = \max(0, \|x_M-x_P\|-0.1)$` |
| grammar_definition | 2 | `$x \in \{x \in \mathcal{X}\mid b_p(x, t)\geq 0\} \Leftrightarrow p_{\mu}=\top$` |
| nonstandard_operator | 1 | `$\alpha\oplus [a',b']$` |

### Other LaTeX commands left

| Command | Times |
|---|---|
| `\nolinebreak` | 2 |
| `\begin` | 2 |
| `\end` | 2 |
| `\SI` | 2 |
| `\be` | 1 |
| `\A` | 1 |
| `\small` | 1 |
| `\em` | 1 |

### Names the formula doesn't have

Names in a description that are not in its formula. Many are normal (the time t, an index i, a signal the passage mentions for context); others are a symbol the description writes differently from the formula.

| Name | Passages |
|---|---|
| `t` | 86 |
| `s` | 24 |
| `A` | 21 |
| `B` | 21 |
| `t_prime` | 19 |
| `phi` | 16 |
| `phi_1` | 14 |
| `C` | 14 |
| `i` | 13 |
| `phi_2` | 12 |
| `phi_3` | 10 |
| `k` | 9 |
| `varphi` | 8 |
| `S` | 8 |
| `r` | 7 |
| `x` | 7 |
| `G` | 7 |
| `m` | 7 |
| `gamma_1` | 6 |
| `rho_1_max` | 6 |
