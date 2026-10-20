# Normalization of the unpaired formulas for `stl-nl`: rules

Input: `data/dataset/stl_formulas_unpaired.jsonl` (6,592 records).
Output: `data/normalized/` (tracked), with one `.stl` file per accepted formula.
Spec: `NORMALIZER_BRIEF.md`. Target grammar: `stl-nl`, `rust/stlgen/src/parser.rs`.
Code: `src/normalization/`, run by `scripts/07_normalize_formulas.py`. Tests: `tests/test_normalization.py`, with at least one case per rule.

Every record ends with one status:

* `ok`: normalized, accepted by `stlgen`, written to `data/normalized/stl/`.
* `needs_review`: normalized as far as the agreed rules allow, but with a choice we haven't approved. Since 2026-10-19 no rule has this status (every choice was approved), so the folder isn't written; the status stays for a future rule that may need it. Written to `data/normalized/needs_review/` (also checked with `stlgen`), so that approving a policy later only means moving files.
* `rejected`: can't be represented. The reason says why.

Each rule has a name (the list is `RULES` in `src/normalization/rules.py`). The manifest lists the rules that fired for each record, so every change can be traced. In the examples, `→` shows the result of that rule alone. A rejected formula gets the first rule that rejects it.

## Stage 0: filters on the whole record

| Rule | Status | Example |
|---|---|---|
| `other_logic` | rejected | `other_logic` is not null (past-time, spatial, ...): 275 records |
| `semantics_definition` | rejected | `(x,t) \models \varphi \mathcal{U}_{[a,b]} \psi \Leftrightarrow \exists t' ...` (contains `\models`, `\vDash`, `\vdash`, `\Vdash`) |
| `grammar_definition` | rejected | `\varphi ::= \top \mid \mu \mid \neg\varphi ...` (contains `::=` or `\mid`); also `\phi := \mu \| \neg\phi \| ...`, a `\|` the parser can't read as an absolute value (found by the parser, since 2026-10-20) |
| `operator_definition` | rejected | `F_{[a,b]} \varphi := \top \mathcal{U}_{[a,b]} \varphi`: a `:=`/`\equiv`/`\triangleq` at the top level whose left side is not a single name, or a `=` with an operator on its left and a formula on its right (compare `strip_label`) |
| `several_formulas` | rejected | `\Box_{[i,j]} p, \Diamond_{[i,j]} p`: a comma (or `;`) at the top level; `\phi = ... \text{ where } ...`: a `\text{...}` that starts with where, and, or, if, iff, for, with, s.t., such that, otherwise, when, then, i.e., e.g.; also a comma inside brackets where the parser stops, a set or a tuple of formulas (`\{p, \Diamond_{[a,b]}p\}`, since 2026-10-20) |
| `connective_at_edge` | rejected | the record's flag "starts or ends with a connective": part of the formula is on another row |

## Stage 1: TeX tokens and the paper's macros (`latex.py`, `lexer.py`)

| Rule | Example |
|---|---|
| `expand_paper_macros` | the paper has `\newcommand{\glob}{\Box}`: `\glob_{[0,5]} p` → `\Box_{[0,5]} p`. With arguments: `\newcommand{\BoxOp}[1]{\Box_{#1}}`: `\BoxOp{[600,700]}` → `\Box_{[600,700]}`; with an optional argument (`\newcommand{\glob}[2][]{...}`) its default is used when the formula has no `[...]`. Read from `\newcommand`, `\renewcommand`, `\providecommand`, `\DeclareRobustCommand`, `\DeclareMathOperator`, `\def` (plain parameters `#1#2` only) and `\let`, in the same files as step 4: the `.tex` files of the document (not the old drafts an arXiv bundle may carry) and the `.sty`, `.cls`, `.def` files, without comments and `\iffalse` blocks. Repeated until no macro is left. LaTeX records only. The commands the lexer knows as standard LaTeX (`\Box`, `\wedge`, `\mathbf`, ...) are never expanded, even if a bundled package defines them; the brief's names that are not LaTeX's own (`\always`, `\eventually`, `\until`) are, as the paper's definition is more exact than the table. |
| `fallback_operator_table` | the usual names of the temporal operators, read from a fixed table when the paper doesn't define them (`\F_{[1,4]}\,p` → `F[1,4] p`) or defines them with commands that only draw the symbol (`\newcommand{\always}{\operatorname{\text{\raisebox{-.01em}{\scalebox{1.1}{$\Square$}}}}}`: `\always_{[0,3]} p` → `G[0,3] p`), i.e. a definition that, fully expanded, still has a command the lexer doesn't know. Names: `\always` `\Always` `\alw` `\glob` `\globally` `\lglobally` `\lalways` `\LTLg` `\LTLglobally` `\LTLsquare` `\G` → `G`; `\eventually` `\Eventually` `\ev` `\even` `\event` `\levent` `\leventually` `\LTLf` `\LTLeventually` `\LTLdiamond` `\diamond` `\F` → `F`; `\until` `\Until` `\U` `\luntil` `\LTLu` → `U` (the names `scripts/eval/render.py` uses to render the evaluation set, and the LTL symbols of the mathabx package). A definition that works is kept, whatever it means. Also for PDF records. Decided on 2026-10-19: the meaning may differ from the paper's, but the pair is built from the formula we produce. |
| `macro_conflict` | a macro used in the formula has two different definitions in the paper. The last one (in path order) is used; only recorded (needs_review until 2026-10-19). |
| `macro_loop` | rejected: a macro still left after 10 rounds, or an expansion that grows past 20,000 tokens |
| `unknown_command` | rejected: a command neither defined by the paper nor known, with its name (the report lists the most frequent ones). `\mathbb`, `\mathscr`, `\mathfrak` are among them: their letters are sets, not signals. |
| `strip_layout` | removes `\left`, `\right`, `\big…`/`\Big…`, `\,` `\;` `\:` `\!` `\ ` `\>` `~` `\quad` `\qquad` `\limits` `\displaystyle` `\nonumber` `\xspace` `$` `&` `\\`, the font switches `\rm` `\sf` `\bf` `\it` `\tt` `\cal`, commands with their argument `\phantom{…}` `\label{…}` `\hspace{…}` `\color{…}`, `\kern`/`\mkern` with their dimension, an empty script `^{}` (left by a macro whose optional argument isn't given); unwraps `\ensuremath`, `\mathop`, `\mathbin`, `\mathrel`, `\mathord`, `\operatorname`, `\textcolor{c}{…}` |
| `unwrap_font` | `\mathit{glucose}` → `glucose`; the same for `\mathrm` `\mathbf` `\mathsf` `\mathtt` `\mathcal` `\mathnormal` `\bm` `\boldsymbol` `\pmb` (read as math) and `\text` `\textit` `\textbf` `\texttt` `\textrm` `\textsf` `\textup` `\textnormal` `\textsl` `\emph` `\mbox` `\hbox` (read as one name, see `multiword_names`). `\mathbf{G}`, `\mathcal{U}`, ... become the bare letters `G`, `U`, which are operators when an interval follows. |

## Stage 2: token rules (`lexer.py`, and `parser.py` for the comparisons)

### Operators and constants

| Rule | Example |
|---|---|
| `latex_ops` | the brief's table: `\Box` `\square` `\always` `□` → `G`; `\Diamond` `\lozenge` `\diamondsuit` `\eventually` `◇` → `F`; `\until` → `U`; `\bigcirc` → `X`; the letters `G` `F` `U` `R` (bare or in a font command: `\mathbf{G}`, `\mathcal{U}`, `\mathsf{F}`) are the operators when an interval follows; a bare `X` before an operand is next; `\neg` `\lnot` `¬` → `!`; `\wedge` `\land` `∧` → `&&`; `\vee` `\lor` `∨` → `\|\|`; `\rightarrow` `\Rightarrow` `\implies` `\to` `→` `⇒` → `->`; `\leftrightarrow` `\Leftrightarrow` `\iff` `↔` `⇔` → `<->`; `\leq` `\le` `≤` → `<=`; `\geq` `\ge` `≥` → `>=`; `\neq` `\ne` `≠` → `!=`; `\lvert…\rvert`, `\vert`, `\left\|…\right\|` → `\|…\|`; `−` (Unicode minus) → `-`. The ASCII forms `&&`, `\|\|`, `!`, `->`, `<->`, `<=`, `>=`, `==`, `!=` are kept. |
| `bool_constants` | `\top` `\mathbf{true}` `True` `\texttt{TRUE}` → `true`; `\bot` `\mathbf{false}` → `false` (a word true or false in any case is always the constant, never a signal) |
| `group_brackets` | `[` `]` and `\{` `\}` used as parentheses → `(` `)`: `\Box_{[0,5]}[a \wedge b]` → `G[0,5] (a && b)`. A `[a,b]` right after an operator is its interval, not a group. |

### Intervals

| Rule | Example |
|---|---|
| `subscript_interval` | `G_{[0,5]}`, `G^{[0,5]}` → `G[0,5]`. A plain `G[0,5]` or `G [0,5]` (as some PDF transcriptions write it) is read the same way. |
| `bound_shorthand` | `G_{\le 100}` → `G[0,100]`; `F_{< 5}` → `F[0,5]` (closed by `close_open_interval`); `\mathbf{U}^{\leq T}` → `U[0,T]` |
| `close_open_interval` | `(1,2)` → `[1,2]`; `[0,10)` → `[0,10]` (agreed: never shrink an interval) |
| `round_bounds_outward` | `[0.2, 0.4]` → `[0,1]`; `[1.5, 3.7]` → `[1,4]`; `[0.0, 5.0]` → `[0,5]` without firing (agreed: lower bound down, upper bound up). The manifest lists each rounding (`rounded`). |
| `random_symbolic_bounds` | `G[0,T] (x < T)` → `G[0,37] (x < 37)`. Each symbol in a bound is drawn uniformly from 0–100. The same symbol gets the same value in the whole formula, comparisons included. Expressions (`[0, T-\tau]`, `[t, t+5]`) are computed after the draw. If a bound is negative or a lower bound is above its upper one, all the symbols are drawn again (up to 100 times). The seed is `<--seed>:<record id>`, so a rerun gives the same numbers and one record doesn't change another. The manifest lists the values (`substitutions`). |
| `random_horizon` | `\Box p`, `G (p \rightarrow F q)`, `p \mathcal{U} q` (no interval) → `G[0,h] p`, ...; `F_{[a,\infty)} p`, `F_{\geq 3} p` (an infinite upper bound) → `F[a,a+h] p`, `F[3,3+h] p`. Each operator gets its own horizon `h`, a symbol drawn as in `random_symbolic_bounds` (0–100; the manifest lists it in `substitutions` as `horizon#1`, `horizon#2`, ...: no name of a formula has a `#`). Adding it to the lower bound keeps the interval valid whatever the draw. The brief rejects these (a horizon changes the meaning); decided on 2026-10-20 to keep them, as for symbolic bounds: the description is written from our formula. `X` keeps no interval. |
| `unbounded_operator` | rejected: `\infty` in a lower bound (`F_{(-\infty, 0]} p`) or inside a bound expression (`[0, \infty - 1]`) |
| `bounds_unsatisfiable` | rejected: no draw in 100 gives valid intervals (`[a, a-200]`). The draft had needs_review, but with no valid intervals there is no formula to put in `needs_review/`. |
| `negative_bound`, `empty_interval`, `bound_too_large` | rejected: `[-1,0]` (a past bound); `[3,1]`; a bound above 2,147,483,647 (the largest stlgen accepts) |

### Signals and numbers

| Rule | Example |
|---|---|
| `greek_names` | `\theta` → `theta`, `\varphi` → `varphi` (`\phi` → `phi`: kept apart, as a paper may use both) |
| `index_names` | `x_{1}`, `x_1` → `x_1`; `v_{max}` → `v_max`; `x_{i,j}` → `x_i_j`; `\mu^{h}` → `mu_h` (a superscript of letters is part of the name; of digits it is a `power`). Font commands in the script are ignored: `\mu_\text{inv}` (no braces), `\phi_{\operatorname{Obs}_1}`, `\phi^{\rm{path}}`, `\mathbb`, ... (since 2026-10-20). Consecutive letters are one name (`gear`, `rpm`), as authors mean them. |
| `multiword_names` | `\text{Trust Increase}` → `Trust_Increase` |
| `accent_names` | `\dot{x}` → `x_dot`; `\bar{x}`, `\overline{x}` → `x_bar`; `\underline{x}` → `x_under`; `\hat{x}` → `x_hat`; `\tilde{x}` → `x_tilde`; `x'`, `x^\prime` → `x_prime` (`\overline` and `\underline` on a name since 2026-10-20: `v \le \overline{v}` keeps two names) |
| `overline_operator` | `\overline{\Diamond}_{[0,10]} p` → `F[0,10] p`; also on `\square`, `\mathcal{U}`, `\mathsf{G}`, ... (and `\underline`). Papers use the line for a variant of the operator: the averaged operators of AvSTL, the marked operators of a tableau. The variant is read as the plain operator: the meaning may change, the pattern stays (decided on 2026-10-20). `\overline` on anything other than a name or an operator stays `unknown_command`. |
| `current_time_index` | `x(t)`, `x[t]`, `x_t` → `x` (only the letter `t`, the evaluation time) |
| `reserved_names` | a signal named `G`, `F`, `X`, `U` or `R` → `G_sig`, ...: `F > 3` → `F_sig > 3`; `X(t)` → `X_sig` |
| `frac_numbers` | `\frac{1}{3}` → `1/3` (integer literals only; otherwise rejected `division`) |
| `number_forms` | `.5` → `0.5`; `5.` → `5`; `1e-3` → `0.001` (exact) |
| `negation_minus` | `-x > 0` → `(0 - x) > 0`; `-3` stays a literal |
| `norm_as_abs` | `\|x - y\|`, `\lVert x \rVert`, `\Vert x \Vert` → `\|x - y\|`. The norm's subscript (`\|x\|_2`, `\|x\|_\infty`, `\Vert x\Vert_{P_1}`) and a square after it (`\|x\|^2`) are dropped. The meaning changes, the pattern (a size compared with a number) stays: decided on 2026-10-20, as the description is written from our formula. Other powers of a norm stay `power`. |
| `function_as_name` | a name followed by `(...)` or `[...]` whose arguments are only names and non-negative integers becomes one name, the function and its arguments joined with `_`: `\mathrm{Reg}(4,4)` → `Reg_4_4`; `behind(p_s, p_{uas})` → `behind_p_s_p_uas`; `h_4(\beta_2(\mathbf{x}))` → `h_4_beta_2_x` (the inner call first); `\phi[\theta]` → `phi_theta`. It can be a proposition (`F[0,10] Reg_4_4`) or a signal (`tau_p_P_A <= 24.5`). The arguments stay in the name so that different calls stay different atoms (`Reg(4,4) && Reg(3,3)` is not `a && a`). Decided on 2026-10-20. Anything else in the brackets (an operator, a formula, an expression, a real number) is `function`. |
| `placeholder_subformula` | `\varphi_1 \mathcal{U}_{[a,b]} \varphi_2` where `variables` calls `\varphi_1` a "(sub)formula" or "specification": kept as the atom `varphi_1` with no flag (decided on 2026-10-19: the subformula can't be rebuilt). The rule is only recorded in the manifest, so these formulas can be found. |

### Comparisons

| Rule | Example |
|---|---|
| `relational_eq` | `gear = 4` → `gear == 4` (a `=` that is not a label, see `strip_label`) |
| `chained_comparison` | `20 \le x \le 80` → `(20 <= x) && (x <= 80)` |
| `interval_membership` | `x \in [a,b]` → `(a <= x) && (x <= b)`; `x \in (a,b]` → `(a < x) && (x <= b)` (here the brackets are about values, not time, so they are kept exactly) |

### Rejected (can't be represented)

| Rule | Example |
|---|---|
| `multiplication` | `2x`, `2\pi`, `a \cdot x`, `\times`, `\ast`, `x * y`, and two terms side by side (`k x`, `p q`: a product or a missing operator) |
| `division` | `x / y`, `1/x`, `\frac{a}{b}` (anything but an integer over an integer) |
| `power` | `(x-1)^2`, `x^2`, `E^*`, a superscript that isn't letters |
| `function` | `\sin x`, `\max`, `\exp`, `\sqrt`, `x(t+1)` (a signal at another time), `\rho(\Box_{[a,b]} \varphi, x, t)` (a call with an argument that isn't a name or an integer, see `function_as_name`) |
| `indexed_operator` | `\bigwedge_{i=1}^n`, `\bigvee`, `\sum`, `\prod`, `\ldots`, `\cdots`; `\land_{i}`, `\lor_{w=1}^{n}` (a connective with a subscript) |
| `quantifier` | `\forall`, `\exists` |
| `set_membership` | `x \in X`, `x \in \mathcal{X}` (not an interval) |
| `infinity` | `x < \infty` (in a time bound it is `unbounded_operator`) |
| `nonstandard_operator` | `\widetilde{\Box}`, `\boxplus`, `\sqcup`, `\oplus`, `\boxminus`, `\diamondminus`, an operator command with a script that isn't an interval (`\Box_{\phi}`), `X` with an interval. A bare letter with a script that isn't an interval is a name (`G_R`, `R_{30,30}`). |
| `parse_error` | anything else the parser doesn't recognise (an incomplete formula, a `\|` used as a separator, ...), with the position |

### Only recorded (needs_review until 2026-10-19, then approved)

| Rule | Example |
|---|---|
| `symbolic_constant` | `x > c` where `variables["c"]` says threshold/constant/parameter/bound/limit/maximum/minimum/max/min: `c` is kept as a signal. Symbols the paper doesn't describe are not recorded. |
| `indexed_signal` | `x[0]`, `x[1]` → `x_0`, `x_1` (read as vector components, though they may be the signal at time 0) |

## Stage 3: parser (`parser.py`)

A recursive-descent parser with the precedence levels of the brief (unary → U/R → `&&` → `||` → `->`/`<->`). It builds the tree. Anything it doesn't recognise → rejected, never guessed.

| Rule | Status | Example |
|---|---|---|
| `strip_label` | ok | `\psi_2 = \square_{[0,20]}(…)`, `\phi := …`, `u_4: …`, `\text{AT19}:\; …` → the formula after the name. Always with `:=` or `:`. With `=` only when the name is a formula name (`\phi`, `\varphi`, `\psi`, `\Phi`, `\Psi` with any subscript, or a name the paper's `variables` call a formula) or an operator follows the `=` (in `gear = 4 \wedge …` the `=` is a comparison). |
| `strip_trailing_punct` | ok | a final `,` `.` `;` is removed |
| `close_parentheses` | ok | brackets still open at the end are closed: `\Box_{[0,20]}\big((gear==4 \land throttle > 45` → `G[0,20] ((gear == 4) && (throttle > 45))`. Some are a `)` the paper misses; others are formulas cut by the extraction (the equation goes on in another row), and the result is their first part. Accepted, as the description is written from our formula (decided on 2026-10-20); only recorded in the manifest, so they can be found. Not applied when a bracket closes one never opened. |
| `operator_alone` | rejected | a temporal operator with no operand: `\Theta_1 = F_{[a,b]}`, `\textbf{U}_{[t_1,t_2]}` (only operators), or an operator at the end (`G_{[0,5]} p \wedge F_{[0,3]}`) |
| `ambiguous_scope` | ok | `\Box_{[0,10]} a \wedge b`: a temporal operator whose operand isn't parenthesized, followed by `&&`, `\|\|`, `->`, `<->`, `U` or `R`. Read with the standard reading `(G[0,10] a) && b` (decided on 2026-10-19, after seeing that most are like `\Box_{[0,40]}p_1\wedge\Box_{[0,30]}(p_4)`), and only recorded in the manifest. |

## Stage 4: emitter (`emit.py`)

The whole tree is written with explicit parentheses around every temporal operand and every binary subformula:

`\psi = \Box_{[0,30]} (gear = 4 \rightarrow \Diamond_{[0,5]} rpm < 3000)` → `G[0,30] ((gear == 4) -> (F[0,5] (rpm < 3000)))`

Numbers are written exactly: integers, exact decimals (`0.25`), or fractions of integers (`1/3`).

## Stage 5: validation (`validate.py`)

Each formula goes through `stlgen import` alone, in a temporary directory, because the import stops at the first bad file. Failure → rejected `stlgen_error`, with stlgen's message. The manifest keeps stlgen's canonical text of each formula (`stl`), to compare with ours. Formulas over the `stl-nl` selection limits (2,000 AST nodes, depth 32, 20,000 characters) keep their status and are listed in `over_limits`; the report counts them.

## Output

```
data/normalized/
├── stl/f00001.stl ...            # status ok, numbered in input order
├── needs_review/r00001.stl ...   # status needs_review (not written while no rule has it)
├── manifest.jsonl                # one line per input record
└── report.md                     # counts by status, the rejection reasons, the most frequent unknown commands and structures, each with an example
```

A manifest line: `id`, `status`, `file` (or null), `reasons`, `rules` (those that fired), `original`, `normalized`, `structure` (see below), `stl` (stlgen's canonical text), `substitutions` (e.g. `{"T": 37}`), `rounded` (e.g. `[[["0.2","0.4"],["0","1"]]]`), `over_limits`, `bounds`, `source_type`.

## Structures

The structure of a formula (`emit.structure`, decided on 2026-10-19) is its normalized text, written by the same writer, with every number (bounds and constants) written `#` and the names renamed `a`, `b`, ... (then `v27`, `v28`, ...) in the order they appear. A name used twice keeps its letter, and the operators and comparison directions are kept; the operands of `&&`/`||` are not sorted.

| Formula | Structure |
|---|---|
| `G[0,30] ((gear == 4) -> (F[0,5] (rpm < 3000)))` | `G[#,#] ((a == #) -> (F[#,#] (b < #)))` |
| `(G[0,5] (x < 3)) -> (G[0,2] (x < 4))` | `(G[#,#] (a < #)) -> (G[#,#] (a < #))` |
| `(G[0,5] (x < 3)) -> (G[0,2] (y < 4))` | `(G[#,#] (a < #)) -> (G[#,#] (b < #))` |
| `F[1,2] p`, `F[42,94] varphi` | `F[#,#] a` |

It is only measured (manifest field `structure`, report section *Structures*): no formula is left out for it. A cap per structure for the input of stl-nl is to be decided once the counts are seen.

