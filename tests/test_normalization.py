"""
Tests of the normalization (src/normalization): one or more cases per rule of docs/normalization_rules.md, each with
the formula, what it must become, and the rule that must fire. Run with: python -m pytest tests
"""
import re
import sys
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import STLGEN_BIN
from src.normalization.description import normalize_description
from src.normalization.emit import number
from src.normalization.latex import source_macros
from src.normalization.normalize import normalize
from src.normalization.rules import FAITHFUL_REJECTED, FAITHFUL_RULES, RULES, status
from src.normalization.select import select
from src.normalization.skeleton import skeleton
from src.normalization.stlgen_ast import formula as stlgen_ast
from src.normalization.validate import check

MACROS = source_macros(r"""
\newcommand{\glob}{\Box}
\def\Evt{\Diamond}
\newcommand{\BoxOp}[1]{\Box_{#1}}
\newcommand*{\globop}{\mathsf{G}}
\newcommand*{\stlunop}[3][]{\mathop{\mathsf{#2}^{#1}_{#3}}}
\newcommand*{\mglob}[2][]{\stlunop[{#1}]{\globop}{#2}}
\newcommand{\twice}{\Box} \renewcommand{\twice}{\Diamond}
\newcommand{\loop}{\loop}
\newcommand{\Always}{\operatorname{\text{\raisebox{-.01em}{\scalebox{1.1}{$\Square$}}}}}
\newcommand{\ev}{\mathbf{E}}
""")


def run(formula, **kwargs):
    kwargs.setdefault("macros", MACROS)
    kwargs.setdefault("record_id", "test")
    return normalize(formula, **kwargs)


# (formula, the result, the rule that must fire); the result "ok" cases give the normalized text
OK_CASES = [
    # Stage 1
    (r"\glob_{[0,5]} p", "G[0,5] p", "expand_paper_macros"),
    (r"\BoxOp{[600,700]} (\mathit{glucose} < 200)", "G[600,700] (glucose < 200)", "expand_paper_macros"),
    (r"\mglob{[3,50]} a", "G[3,50] a", "expand_paper_macros"),
    (r"\Box_{[0,5]} \left( a \,\wedge\, b \right)", "G[0,5] (a && b)", "strip_layout"),
    (r"\F_{[1,4]}\,p", "F[1,4] p", "fallback_operator_table"),                 # \F defined nowhere
    (r"\Always_{[0,10]} p", "G[0,10] p", "fallback_operator_table"),           # defined, but only drawn
    (r"\LTLdiamond_{[0,6]} r", "F[0,6] r", "fallback_operator_table"),
    (r"\Box_{[0,5]} \mathit{glucose} < 200", "G[0,5] (glucose < 200)", "unwrap_font"),
    # Stage 2: operators and constants
    (r"\Box_{[0,5]} (\neg a \vee b \rightarrow c)", "G[0,5] (((!a) || b) -> c)", "latex_ops"),
    (r"(\Diamond_{[0,5]} a) \leftrightarrow (\lozenge_{[0,5]} b)", "(F[0,5] a) <-> (F[0,5] b)", "latex_ops"),
    (r"\bigcirc a", "X a", "latex_ops"),
    (r"\Box_{[0,5]} (x \leq 3 \wedge y \geq 2 \wedge z \neq 1)", "G[0,5] ((x <= 3) && (y >= 2) && (z != 1))", "latex_ops"),
    (r"\Box_{[0,5]} (x \leqslant 3 \wedge y \geqslant 2)", "G[0,5] ((x <= 3) && (y >= 2))", "latex_ops"),
    (r"\Diamond_{[0,5]} \top", "F[0,5] true", "bool_constants"),
    (r"\Diamond_{[0,5]} \texttt{True}", "F[0,5] true", "bool_constants"),
    (r"\Box_{[0,5]}[a \wedge b]", "G[0,5] (a && b)", "group_brackets"),
    # Stage 2: intervals
    (r"G_{[0,5]} p", "G[0,5] p", "subscript_interval"),
    (r"\mathbf{G}^{[0,5]} p", "G[0,5] p", "subscript_interval"),
    (r"p \mathcal{U}_{[1,2]} q", "p U[1,2] q", "subscript_interval"),
    (r"\textbf{F}_{\left[0,5\right]} p", "F[0,5] p", "subscript_interval"),
    (r"\mathbf{G}_{\le 100}(q \rightarrow \mathbf{F}_{< 5}p)", "G[0,100] (q -> (F[0,5] p))", "bound_shorthand"),
    (r"\Diamond_{(1,2)} p", "F[1,2] p", "close_open_interval"),
    (r"\Diamond_{[0,10)} p", "F[0,10] p", "close_open_interval"),
    (r"\Box_{[0.2,0.4]} p", "G[0,1] p", "round_bounds_outward"),
    (r"\Box_{[1.5,3.7]} p", "G[1,4] p", "round_bounds_outward"),
    (r"\Box_{[0.0,5.0]} p", "G[0,5] p", None),
    (r"\Box_{[0,T]} p", "G[0,T] p", "parameter_bounds"),
    (r"\Diamond_{(a,b]} (x > 1)", "F[a,b] (x > 1)", "parameter_bounds"),
    (r"\mathbf{G}_{\le T} p", "G[0,T] p", "parameter_bounds"),
    (r"\Box p", "G[0,inf] p", "unbounded_interval"),
    (r"G (p \rightarrow F q)", "G[0,inf] (p -> (F[0,inf] q))", "unbounded_interval"),
    (r"p \mathcal{U} q", "p U[0,inf] q", "unbounded_interval"),
    (r"\mathbf{F}_{[5,\infty)} p", "F[5,inf] p", "unbounded_interval"),
    (r"F_{\ge 3} p", "F[3,inf] p", "unbounded_interval"),
    (r"\Diamond_{[a,\infty)} p", "F[a,inf] p", "unbounded_interval"),
    # Stage 2: signals and numbers
    (r"\Box_{[0,5]} \theta > 1", "G[0,5] (theta > 1)", "greek_names"),
    (r"\Box_{[0,5]} (x_{1} > v_{max})", "G[0,5] (x_1 > v_max)", "index_names"),
    (r"\Diamond_{[0,10]} \text{Trust Increase}", "F[0,10] Trust_Increase", "multiword_names"),
    (r"\Box_{[0,5]} (\dot{x} < 1 \wedge x' > 0)", "G[0,5] ((x_dot < 1) && (x_prime > 0))", "accent_names"),
    (r"\Box_{[0,5]} (x(t) > 0 \wedge y[t] > 0 \wedge z_t > 0)", "G[0,5] ((x > 0) && (y > 0) && (z > 0))", "current_time_index"),
    (r"\Box_{[0,5]} (X(t) > 0)", "G[0,5] (X_sig > 0)", "reserved_names"),
    (r"\Box_{[0,5]} F > 3", "G[0,5] (F_sig > 3)", "reserved_names"),
    (r"\Box_{[0,5]} x > \frac{1}{3}", "G[0,5] (x > 1/3)", "frac_numbers"),
    (r"\Box_{[0,5]} (x > .5 \wedge y < 1e-3)", "G[0,5] ((x > 0.5) && (y < 0.001))", "number_forms"),
    (r"\Box_{[0,5]} -x > 0", "G[0,5] ((0 - x) > 0)", "negation_minus"),
    (r"\Box_{[0,5]} a \cdot x > 1", "G[0,5] (a * x > 1)", "products_and_divisions"),
    (r"\Box_{[0,5]} (2x \leq 1 \wedge 0.75r < y)", "G[0,5] ((2 * x <= 1) && (0.75 * r < y))", "products_and_divisions"),
    (r"\Box_{[0,5]} x / y > 1", "G[0,5] (x / y > 1)", "products_and_divisions"),
    (r"\Box_{[0,5]} |\frac{x - y}{y}| < 0.1", "G[0,5] (|(x - y) / y| < 0.1)", "products_and_divisions"),
    (r"\Box_{[0,5]} a + b \times c - d / 2 > 0", "G[0,5] ((a + (b * c)) - (d / 2) > 0)", "products_and_divisions"),
    (r"\Box_{[0,5]} x / 2 / 3 > 0", "G[0,5] ((x / 2) / 3 > 0)", "products_and_divisions"),
    (r"\Box_{[0,5]} x / \frac{1}{3} > 0", "G[0,5] (x / (1/3) > 0)", "products_and_divisions"),
    (r"\Box_{[0,5]} x > -3", "G[0,5] (x > -3)", None),
    # Stage 2: comparisons
    (r"\Box_{[0,30]} (gear = 4)", "G[0,30] (gear == 4)", "relational_eq"),
    (r"\Box_{[0,5]} 20 \le x \le 80", "G[0,5] ((20 <= x) && (x <= 80))", "chained_comparison"),
    (r"\Box_{[0,5]} x \in [0, 5)", "G[0,5] ((0 <= x) && (x < 5))", "interval_membership"),
    (r"\Box_{[0,5]} |x - y| \leq 0.25", "G[0,5] (|x - y| <= 0.25)", "latex_ops"),
    # Stage 3
    (r"\psi_2 = \square_{[0,20]} p", "G[0,20] p", "strip_label"),
    (r"\phi := G_{[0,5]} p", "G[0,5] p", "strip_label"),
    (r"\text{AT19}:\; \Diamond_{[0,30]} (gear \neq 1)", "F[0,30] (gear != 1)", "strip_label"),
    (r"\Diamond_{[0,5]} p.", "F[0,5] p", "strip_trailing_punct"),
    # Stage 4: the parentheses
    (r"\psi = \Box_{[0,30]} (gear = 4 \rightarrow \Diamond_{[0,5]} rpm < 3000)",
     "G[0,30] ((gear == 4) -> (F[0,5] (rpm < 3000)))", None),
    (r"\Box_{[0,5]} (a \wedge b \vee c)", "G[0,5] ((a && b) || c)", None),
    (r"a \rightarrow b \rightarrow c", "a -> (b -> c)", None),
    (r"(\Box_{[2,10]} p_1) \mathbf{U}_{[1,4]} p_2", "(G[2,10] p_1) U[1,4] p_2", None),
]


@pytest.mark.parametrize("formula,expected,rule", OK_CASES)
def test_ok(formula, expected, rule):
    result = run(formula)
    assert (result.status, result.normalized) == ("ok", expected), result.reasons
    if rule:
        assert rule in result.rules


def test_label_with_equals_only_for_formula_names():
    # "gear = 4 \wedge ..." is a comparison, not the label "gear"
    result = run(r"gear = 4 \wedge \Box_{[0,5]} speed < 20")
    assert result.normalized == "(gear == 4) && (G[0,5] (speed < 20))"
    assert "strip_label" not in result.rules
    # a name the paper's variables call a formula is a label
    result = run(r"spec = p \wedge q", variables={"spec": "the specification"})
    assert result.normalized == "p && q"


def test_random_symbolic_bounds():
    # A symbol also used as a signal can't be a parameter of stl-nl: it gets a random value, everywhere
    result = run(r"\Box_{[0,T]} (x < T)")
    value = result.substitutions["T"]
    assert result.normalized == f"G[0,{value}] (x < {value})"
    assert "random_symbolic_bounds" in result.rules and "parameter_bounds" not in result.rules
    # The same record and seed give the same values
    assert run(r"\Box_{[0,T]} (x < T)").substitutions == result.substitutions
    # A symbol in a bound expression gets a random value; a symbol alone stays a parameter
    for record_id in map(str, range(50)):
        r = run(r"(\Diamond_{[a,b]} p) \wedge (\Box_{[t, t+5]} q)", record_id=record_id)
        assert r.status == "ok" and set(r.substitutions) == {"t"}
        assert r.normalized == f"(F[a,b] p) && (G[{r.substitutions['t']},{r.substitutions['t'] + 5}] q)"
    # The same symbol alone in another bound gets the same value
    r = run(r"(\Diamond_{[0,t]} p) \wedge (\Box_{[t, t+5]} q)")
    t = r.substitutions["t"]
    assert r.normalized == f"(F[0,{t}] p) && (G[{t},{t + 5}] q)"


# Rules that only record what they find (they were needs_review until 2026-10-19)
RECORDED_CASES = [
    (r"\twice_{[0,5]} p", "F[0,5] p", "macro_conflict"),
    (r"\Box_{[0,5]} x > c", "G[0,5] (x > c)", "symbolic_constant"),
    (r"G_{[0,5]}(x[0] \ge 0)", "G[0,5] (x_0 >= 0)", "indexed_signal"),
    (r"\Box_{[0,5]} \|x - y\| < 1", "G[0,5] (|x - y| < 1)", "norm_as_abs"),
    (r"\Box_{[0,5]} \lVert x \rVert_\infty < 1", "G[0,5] (|x| < 1)", "norm_as_abs"),
    (r"\Box_{[0,5]} \Vert x \Vert_{2}^2 \le 1", "G[0,5] (|x| <= 1)", "norm_as_abs"),
    (r"\mathbf{F}_{[0,10]} \mathrm{Reg}\,(4,4) \wedge \mathbf{F}_{[0,10]} \mathrm{Reg}\,(3,3)",
     "(F[0,10] Reg_4_4) && (F[0,10] Reg_3_3)", "function_as_name"),
    (r"\Box_{[0,5]} h_4(\beta_2(\mathbf{x})) \ge 0", "G[0,5] (h_4_beta_2_x >= 0)", "function_as_name"),
    (r"\Box_{[0,5]} \phi[\theta]", "G[0,5] phi_theta", "function_as_name"),
    (r"\overline{\Diamond}_{[0,10]} p \wedge \overline{\mathsf{G}}_{[0,5]} q", "(F[0,10] p) && (G[0,5] q)",
     "overline_operator"),
    (r"\Box_{[0,5]} v \le \overline{v}", "G[0,5] (v <= v_bar)", "accent_names"),
    (r"\Box_{[0,3]}(\mu_\text{h} \mathbf{U}_{[0,3]} \mu_\text{g})", "G[0,3] (mu_h U[0,3] mu_g)", "index_names"),
    (r"\Box_{[0,3]} \phi_{\operatorname{Obs}_1} \wedge \phi^{\rm{path}}", "(G[0,3] phi_Obs_1) && phi_path", "index_names"),
    (r"\Box_{[0,20]}\big((gear==4 \land throttle > 45", "G[0,20] ((gear == 4) && (throttle > 45))", "close_parentheses"),
]
VARIABLES = {"c": "the speed threshold", "\\varphi_1": "a subformula", "\\varphi_2": "a subformula"}


@pytest.mark.parametrize("formula,expected,rule", RECORDED_CASES)
def test_recorded(formula, expected, rule):
    result = run(formula, variables=VARIABLES)
    assert (result.status, result.normalized) == ("ok", expected), result.reasons
    assert rule in result.rules


def test_bounds_under_and_over_a_line_are_two_symbols():
    r = run(r"F_{[\underline{t}, \overline{t}]} p")
    assert r.status == "ok" and r.normalized == "F[t_under,t_bar] p"


def test_x_keeps_no_interval():
    r = run(r"\bigcirc p")
    assert r.normalized == "X p" and "unbounded_interval" not in r.rules


def test_a_working_definition_wins_over_the_table():
    # The paper's \ev is \mathbf{E}, not eventually: kept, so E_{[0,5]} is a name and p beside it a product
    result = run(r"\ev_{[0,5]} p")
    assert "fallback_operator_table" not in result.rules and result.status == "rejected"
    # \glob is defined by the paper as \Box: the table is not needed
    assert run(r"\glob_{[0,5]} p").rules[0] == "expand_paper_macros"


def test_placeholder_subformula_is_kept_without_a_flag():
    result = run(r"\varphi_1 \mathcal{U}_{[1,2]} \varphi_2", variables=VARIABLES)
    assert (result.status, result.normalized) == ("ok", "varphi_1 U[1,2] varphi_2")
    assert "placeholder_subformula" in result.rules


def test_ambiguous_scope_takes_the_standard_reading():
    result = run(r"\Box_{[0,10]} a \wedge b")
    assert (result.status, result.normalized) == ("ok", "(G[0,10] a) && b")
    assert "ambiguous_scope" in result.rules
    # A parenthesized operand is not ambiguous
    assert "ambiguous_scope" not in run(r"\Box_{[0,10]} (a) \wedge b").rules
    assert "ambiguous_scope" not in run(r"(\Box_{[0,10]} a) \wedge b").rules


REJECTED_CASES = [
    (r"(x,t) \models \varphi", "semantics_definition"),
    (r"\varphi ::= \top \mid \mu", "grammar_definition"),
    (r"\varphi ::= \top \;|\; \mu", "grammar_definition"),
    (r"\phi := \mu \ | \ \neg \phi \ | \ \phi_1 \land \phi_2", "grammar_definition"),
    (r"\{p, \Diamond_{[0,5]}p, \Box_{[0,5]}p\}", "several_formulas"),
    (r"\land_{i}(\neg \mathit{Obs}_i)", "indexed_operator"),
    (r"\Theta_1=F_{[0,5]}", "operator_alone"),
    (r"\textbf{U}_{[0,5]}", "operator_alone"),
    (r"\Box_{[0,5]} p \wedge \Diamond_{[0,3]}", "operator_alone"),
    (r"\Box_{[0,5]} p)) \wedge (q", "parse_error"),
    (r"F_{[a,b]} \varphi := \top \mathcal{U}_{[a,b]} \varphi", "operator_definition"),
    (r"\Diamond_{[a,b]} \varphi = \top \mathcal{U}_{[a,b]} \varphi", "operator_definition"),
    (r"\Box_{[0,5]} p, \Diamond_{[0,5]} q", "several_formulas"),
    (r"\phi = \Box_{[0,5]} p \text{ where } p = x > 0", "several_formulas"),
    (r"\loop_{[0,5]} p", "macro_loop"),
    (r"\Box_{[0,5]} \frobnicate p", "unknown_command"),
    (r"\mathbf{F}_{(-\infty,0]} p", "unbounded_operator"),
    (r"\Box_{[3,1]} p", "empty_interval"),
    (r"\Box_{[-1,0]} p", "negative_bound"),
    (r"\Box_{[0,3000000000]} p", "bound_too_large"),
    (r"\Box_{[0,5]} k x > 1", "multiplication"),
    (r"\Box_{[0,5]} s < 200\ \mathrm{N}", "multiplication"),
    (r"\Box_{[0,5]} x / 0 > 1", "division"),
    (r"\Diamond_{[0.1s,0.6s]} p", "multiplication"),
    (r"\Diamond_{[0,24h]} p", "multiplication"),
    (r"\Box_{[0,5]} (x-1)^2 < 1", "power"),
    (r"\Box_{[0,5]} \sin x < 1", "function"),
    (r"\Box_{[0,5]} \|x\|^3 < 1", "power"),
    (r"\Box_{[0,5]} f(x, 0.5) < 1", "function"),
    (r"\Box_{[0,5]} \rho(\Box_{[0,1]} p, x, t) > 0", "function"),
    (r"\Box_{[0,5]} x(t+1) < 1", "function"),
    (r"\bigwedge_{i=1}^n \Box_{[0,5]} p_i", "indexed_operator"),
    (r"\forall i \; \Box_{[0,5]} p_i", "quantifier"),
    (r"\Box_{[0,5]} x \in X", "set_membership"),
    (r"\Box_{[0,5]} x < \infty", "infinity"),
    (r"\boxplus_{[0,1]} p", "nonstandard_operator"),
    (r"\Box_{\phi} p", "nonstandard_operator"),
    (r"\Box_{[0,5]} (a \wedge", "parse_error"),
]


@pytest.mark.parametrize("formula,rule", REJECTED_CASES)
def test_rejected(formula, rule):
    result = run(formula)
    assert result.status == "rejected" and result.reasons[0].startswith(rule), result.reasons


def test_record_filters():
    flag = "the formula ends or starts with a connective: part of it may be on another row"
    assert run(r"\Box_{[0,5]} p \wedge", flags=[flag]).reasons == ["connective_at_edge"]


def test_every_rule_is_tested():
    tested = ({c[2] for c in OK_CASES} | {c[2] for c in RECORDED_CASES} | {c[1] for c in REJECTED_CASES}
              | {c[2] for c in FAITHFUL_CASES} | {c[1] for c in FAITHFUL_REJECTED_CASES}
              | {"random_symbolic_bounds", "connective_at_edge", "bounds_unsatisfiable",
                 "placeholder_subformula", "ambiguous_scope"})
    # stlgen_error is the check of step 6, after the normalization (test_stlgen_accepts_every_ok_case)
    assert set(RULES) - tested == {"stlgen_error"}


def test_bounds_that_no_draw_satisfies():
    assert run(r"\Box_{[a, a-200]} p").reasons[0].startswith("bounds_unsatisfiable")


def test_pattern():
    result = run(r"\psi = \Box_{[0,30]} (gear = 4 \rightarrow \Diamond_{[0,5]} rpm < 3000)")
    assert result.pattern == "G[#,#] ((a == #) -> (F[#,#] (b < #)))"
    # A name used twice keeps its letter; numbers inside expressions are hidden too
    assert run(r"(\Box_{[0,5]} x < 3) \rightarrow (\Box_{[0,2]} x < 4)").pattern == \
           "(G[#,#] (a < #)) -> (G[#,#] (a < #))"
    assert run(r"(\Box_{[0,5]} x < 3) \rightarrow (\Box_{[0,2]} y < 4)").pattern == \
           "(G[#,#] (a < #)) -> (G[#,#] (b < #))"
    assert run(r"\Box_{[0,5]} |x - y| > -x").pattern == "G[#,#] (|a - b| > (# - a))"
    # Formulas that differ only in numbers and names share their pattern
    assert run(r"\Diamond_{[1,2]} p").pattern == run(r"\Diamond_{[0,T]} \varphi").pattern == "F[#,#] a"
    # A parameter is written # as a number (G[0,T] and G[0,5] share a pattern); inf is kept
    assert run(r"\Box_{[a,b]} x > c").pattern == "G[#,#] (a > b)"
    assert run(r"\Box p").pattern == "G[#,inf] a"
    assert run(r"\Box_{[0,5]} 2x + y > 1").pattern == "G[#,#] ((# * a) + b > #)"
    assert run(r"\Box p \wedge \forall i").pattern is None


def selection_line(record_id, normalized, pattern, status="ok"):
    return {"id": record_id, "status": status, "normalized": normalized, "pattern": pattern}


def test_selection_leaves_out_duplicates():
    lines = [selection_line("W1:P1", "G[0,5] p", "G[#,#] a"), selection_line("W2:P1", "G[0,5] p", "G[#,#] a"),
             selection_line("W2:P2", "G[0,6] p", "G[#,#] a"), selection_line("W3:P1", None, None, "rejected")]
    select(lines, 10, "0")
    assert [(l["selection"], l["duplicate_of"]) for l in lines] == \
           [("kept", None), ("duplicate", "W1:P1"), ("kept", None), (None, None)]


def test_selection_caps_each_pattern_over_papers():
    # Paper W1 has 5 formulas of the pattern, W2 and W3 one each: a cap of 3 takes one from each paper
    lines = [selection_line(f"W1:P{i}", f"F[0,{i}] p", "F[#,#] a") for i in range(5)]
    lines += [selection_line("W2:P1", "F[0,9] q", "F[#,#] a"), selection_line("W3:P1", "F[0,8] r", "F[#,#] a"),
              selection_line("W4:P1", "G[0,1] p", "G[#,#] a")]
    select(lines, 3, "0")
    kept = [l["id"] for l in lines if l["selection"] == "kept"]
    assert len(kept) == 4 and {"W2:P1", "W3:P1", "W4:P1"} <= set(kept)
    assert sum(1 for l in lines if l["selection"] == "pattern_cap") == 4
    # The same seed picks the same; no cap keeps all
    again = [dict(l) for l in lines]
    select(again, 3, "0")
    assert [l["selection"] for l in again] == [l["selection"] for l in lines]
    select(lines, 0, "0")
    assert all(l["selection"] == "kept" for l in lines)


@pytest.mark.skipif(not STLGEN_BIN.is_file(), reason="stlgen of stl-nl not built")
def test_skeleton():
    def of(formula):
        parsed, error = check(run(formula).normalized, STLGEN_BIN)
        assert error is None, error
        return skeleton(parsed["ast"])[0]
    assert of(r"\psi = \Box_{[0,30]} (gear = 4 \rightarrow \Diamond_{[0,5]} rpm < 3000)") == "G[#,#] (φ -> F[#,#] ψ)"
    # Conditions become letters whatever their relations: two patterns, one skeleton
    assert of(r"\Box_{[0,5]} x < 3") == of(r"\Diamond_{[0,T]} (x + y > z)".replace("Diamond", "Box")) == "G[#,#] φ"
    # A letter repeats only when the same condition repeats; && is unordered; inf is kept
    assert of(r"(\Box_{[0,5]} x < 3) \wedge (\Diamond_{[0,2]} x < 3)") == "(F[#,#] φ) && (G[#,#] φ)"
    assert of(r"(\Box_{[0,5]} x < 3) \wedge (\Diamond_{[0,2]} x < 4)") == "(F[#,#] φ) && (G[#,#] ψ)"
    assert of(r"\Box p") == "G[#,inf] φ"


def test_number_text():
    assert [number(Fraction(x)) for x in ("5", "1/4", "-1/2", "1/3", "4500", "0.786")] == \
           ["5", "0.25", "-0.5", "1/3", "4500", "0.786"]


@pytest.mark.skipif(not STLGEN_BIN.is_file(), reason="stlgen of stl-nl not built")
def test_stlgen_accepts_every_ok_case():
    for formula, expected, _ in OK_CASES:
        parsed, error = check(expected, STLGEN_BIN)
        assert error is None, (formula, expected, error)
    parsed, error = check("G [0,5] a", STLGEN_BIN)
    assert parsed is None and "parse error" in error



# ---------------------------------------------------------------- the faithful mode (paired formulas)

def faithful(formula, **kwargs):
    return run(formula, mode="faithful", **kwargs)


# (formula, the result in the faithful mode, the rule that must fire): what the stl-nl mode would change stays
FAITHFUL_CASES = [
    (r"\Box_{[0.2,0.4]} p", "G[0.2,0.4] p", "real_bounds"),
    (r"\Box_{[1/3, 2]} p", "G[1/3,2] p", "real_bounds"),
    (r"\Diamond_{(1,2)} p", "F(1,2) p", "open_intervals"),
    (r"\Diamond_{[0,10)} p", "F[0,10) p", "open_intervals"),
    (r"\mathbf{F}_{(5,\infty)} p", "F(5,inf] p", "open_intervals"),
    (r"\mathbf{F}_{< 5}p", "F[0,5) p", "open_intervals"),
    (r"\Box_{[T, T+\delta]} p", "G[T,T + delta] p", "bound_expressions"),
    (r"\Box_{[0,T]} (x < T)", "G[0,T] (x < T)", "parameter_bounds"),
    (r"\Box_{[0,8-4]} p", "G[0,4] p", None),
    (r"\Box_{[0,5]} (x-1)^2 < 1", "G[0,5] ((x - 1)^2 < 1)", "powers"),
    (r"G_{[0,2]}(x_4^2 + x_5^2 > 1.5^2)", "G[0,2] (x_4^2 + x_5^2 > 1.5^2)", "powers"),
    (r"\Box_{[0,5]} \Vert x \Vert_{2}^2 \le 1", "G[0,5] (|x|^2 <= 1)", "powers"),
    (r"\Box_{[0,5]} -x^2 > -3", "G[0,5] ((0 - x^2) > -3)", "powers"),
    (r"\Box_{[0,5]} x^{-1} > 3", "G[0,5] (x^(-1) > 3)", "powers"),
    (r"\Box_{[0,5]} \phi^{\rm{path}}", "G[0,5] phi_path", "index_names"),
]


@pytest.mark.parametrize("formula,expected,rule", FAITHFUL_CASES)
def test_faithful(formula, expected, rule):
    result = faithful(formula)
    assert (result.status, result.normalized) == ("ok", expected), result.reasons
    if rule:
        assert rule in result.rules


FAITHFUL_REJECTED_CASES = [
    (r"\overline{\Diamond}_{[0,10]} p", "overline_operator"),
    (r"\Box_{[0,20]}\big((gear==4 \land throttle > 45", "close_parentheses"),
    (r"\Diamond_{[0, 15]} (\pi^8 \vee \pi^9)", "power"),          # an atom with a superscript: a label
    (r"G_{[10,15]}(\|e - [1,1]^T\| \leq 3)", "power"),           # a transpose
    (r"\Box_{[0,5]} x^{(j)} > 0", "power"),
    (r"\Box_{[0.5,0.25]} p", "empty_interval"),
    (r"\Box_{[-1,0]} p", "negative_bound"),
]


@pytest.mark.parametrize("formula,rule", FAITHFUL_REJECTED_CASES)
def test_faithful_rejected(formula, rule):
    result = faithful(formula)
    assert result.status == "rejected" and result.reasons[0].startswith(rule), result.reasons


def test_rules_of_the_faithful_mode():
    # The rules that change the meaning reject in the faithful mode only
    assert {status(r, "faithful") for r in FAITHFUL_REJECTED} == {"rejected"}
    assert {status(r) for r in FAITHFUL_REJECTED} == {"ok"}
    # The rules of the faithful mode never fire in the stl-nl mode: the same formulas are changed instead
    for formula, _, _ in FAITHFUL_CASES:
        assert not FAITHFUL_RULES & set(run(formula).rules), formula


def test_faithful_pattern():
    # Bounds are # whatever they are, the brackets are kept, a power's exponent is a number
    assert faithful(r"\Diamond_{(0,T+1]} (x^2 < 2.5)").pattern == "F(#,#] (a^# < #)"
    assert faithful(r"\Box_{[0,T]} (x < T)").pattern == "G[#,#] (a < b)"


def test_faithful_names():
    # The names of the formula, for its description: signals, atoms, parameters
    assert faithful(r"\Box_{[0,T]} (x < c) \wedge p").names == ["T", "c", "p", "x"]


@pytest.mark.skipif(not STLGEN_BIN.is_file(), reason="stlgen of stl-nl not built")
def test_converter_gives_stlgen_skeletons():
    # Our tree as stlgen's AST gives the skeleton stlgen's own AST gives (step 6 checked it on every unpaired formula ok)
    for formula, expected, _ in OK_CASES + [(r"\bigcirc a \leftrightarrow b", None, None),
                                            (r"\Box_{[0,5]} -x > 0 \wedge |y| < 1", None, None)]:
        result = run(formula)
        parsed, error = check(result.normalized, STLGEN_BIN)
        assert error is None, error
        assert skeleton(stlgen_ast(result.tree)) == skeleton(parsed["ast"]), formula


def test_faithful_skeleton():
    def of(formula):
        return skeleton(stlgen_ast(faithful(formula).tree))[0]
    # Open, real and expression bounds are [#,#] as any finite bound: these have the skeleton of their stl-nl form
    assert of(r"\Diamond_{(0,2.5]} p") == of(r"\Diamond_{[0,T+1)} p") == "F[#,#] φ"
    assert of(r"\Box_{[0,5]} (x^2 > 1 \wedge x^2 > 1)") == "G[#,#] (φ && φ)"
    assert of(r"\Box p") == "G[#,inf] φ"


# ---------------------------------------------------------------- the descriptions of the paired formulas

DESCRIPTION_MACROS = source_macros(r"\newcommand{\Trec}{\alpha}\newcommand{\speed}{v_{\mathrm{car}}}")


def describe(text, names=(), macros=DESCRIPTION_MACROS):
    return normalize_description(text, macros=macros, formula_names=set(names))


DESCRIPTION_CASES = [
    # math as in the formula: names, Greek letters, indices, macros, comparisons; a lone = stays
    (r"while $\varphi_{1}$ holds, $x_1 \le 10$", "while varphi_1 holds, x_1 <= 10"),
    (r"recover within time $\Trec$ and keep $\speed > 3$", "recover within time alpha and keep v_car > 3"),
    (r"at $t=22.5$ the value $\dot{\psi} \leq 0.2$", "at t = 22.5 the value psi_dot <= 0.2"),
    (r"$\Diamond_{[0,5]} p$ and $\mathbf{G}_{\le 3}(a \wedge \neg b)$", "F[0,5] p and G[0,3] (a && !b)"),
    (r"$\phi_1:=F_{[0,\infty)}\psi_1$", "phi_1 := F[0,inf] psi_1"),
    (r"in $[0, 15]$ or $x \in (12, 17)$, for $A_i, B_i$", "in [0,15] or x in (12,17), for A_i, B_i"),
    (r"$|x - y| \le 0.2$ and $-4\le x_1\le -2$ and $x_1(t) > 0$", "|x - y| <= 0.2 and -4 <= x_1 <= -2 and x_1 > 0"),
    (r"in $99\%$ of the cases, \(x > 2\)", "in 99% of the cases, x > 2"),
    # text-mode LaTeX made plain; math outside $...$ read as math
    (r"\emph{always} ``safe''~speed\,\speed{} below \varphi", 'always "safe" speed v_car below varphi'),
    # Unicode of PDFs
    (r"if for all time 0≤t <2, q(t) > −1 and φ1 holds", "if for all time 0<=t <2, q(t) > -1 and phi_1 holds"),
    # cut inside math by the extraction
    (r"\varphi_2$ requires $O$ until $A$", "varphi_2 requires O until A"),
]


@pytest.mark.parametrize("text,expected", DESCRIPTION_CASES)
def test_description(text, expected):
    assert describe(text).normalized == expected


def test_description_uses_the_formula_names():
    # φ is varphi when the formula writes varphi; a signal G is G_sig when the formula renamed it
    assert describe("φ1 holds", names=["varphi_1"]).normalized == "varphi_1 holds"
    assert describe(r"$G > 2$", names=["G_sig"]).normalized == "G_sig > 2"
    d = describe(r"$x > 2$ at time $t$", names=["x"])
    assert d.names_not_in_formula == ["t"]


def test_description_keeps_what_it_cannot_convert():
    d = describe(r"$(p, t) \models \varphi$ (see Eq.~\eqref{eq:x}), \frobnicate")
    assert d.normalized == r"$(p, t) \models \varphi$ (see Eq. \eqref{eq:x}), \frobnicate"
    assert d.unreadable == [{"span": r"$(p, t) \models \varphi$", "reason": r"semantics_definition: \models"}]
    assert d.references == [r"\eqref{eq:x}"] and d.latex_left == [r"\frobnicate"]
