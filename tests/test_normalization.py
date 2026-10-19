"""
Tests of the normalization (src/normalization): one or more cases per rule of docs/normalization_rules.md, each with
the formula, what it must become, and the rule that must fire. Run with: python -m pytest tests
"""
import sys
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import STLGEN_BIN
from src.normalization.emit import number
from src.normalization.latex import source_macros
from src.normalization.normalize import normalize
from src.normalization.rules import RULES
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
    (r"\Diamond_{[0,5]} \top", "F[0,5] true", "bool_constants"),
    (r"\Diamond_{[0,5]} \texttt{True}", "F[0,5] true", "bool_constants"),
    (r"\Box_{[0,5]}[a \wedge b]", "G[0,5] (a && b)", "group_brackets"),
    # Stage 2: intervals
    (r"G_{[0,5]} p", "G[0,5] p", "subscript_interval"),
    (r"\mathbf{G}^{[0,5]} p", "G[0,5] p", "subscript_interval"),
    (r"p \mathcal{U}_{[1,2]} q", "p U[1,2] q", "subscript_interval"),
    (r"\mathbf{G}_{\le 100}(q \rightarrow \mathbf{F}_{< 5}p)", "G[0,100] (q -> (F[0,5] p))", "bound_shorthand"),
    (r"\Diamond_{(1,2)} p", "F[1,2] p", "close_open_interval"),
    (r"\Diamond_{[0,10)} p", "F[0,10] p", "close_open_interval"),
    (r"\Box_{[0.2,0.4]} p", "G[0,1] p", "round_bounds_outward"),
    (r"\Box_{[1.5,3.7]} p", "G[1,4] p", "round_bounds_outward"),
    (r"\Box_{[0.0,5.0]} p", "G[0,5] p", None),
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
    result = run(r"\Box_{[0,T]} (x < T)")
    value = result.substitutions["T"]
    assert result.normalized == f"G[0,{value}] (x < {value})"
    assert "random_symbolic_bounds" in result.rules
    # The same record and seed give the same values; the values respect lower <= upper
    assert run(r"\Box_{[0,T]} (x < T)").substitutions == result.substitutions
    for record_id in map(str, range(50)):
        r = run(r"(\Diamond_{[a,b]} p) \wedge (\Box_{[t, t+5]} q)", record_id=record_id)
        assert r.status == "ok" and r.substitutions["a"] <= r.substitutions["b"]
        assert r.normalized.endswith(f"(G[{r.substitutions['t']},{r.substitutions['t'] + 5}] q)")


# Rules that only record what they find (they were needs_review until 2026-10-19)
RECORDED_CASES = [
    (r"\twice_{[0,5]} p", "F[0,5] p", "macro_conflict"),
    (r"\Box_{[0,5]} x > c", "G[0,5] (x > c)", "symbolic_constant"),
    (r"G_{[0,5]}(x[0] \ge 0)", "G[0,5] (x_0 >= 0)", "indexed_signal"),
]
VARIABLES = {"c": "the speed threshold", "\\varphi_1": "a subformula", "\\varphi_2": "a subformula"}


@pytest.mark.parametrize("formula,expected,rule", RECORDED_CASES)
def test_recorded(formula, expected, rule):
    result = run(formula, variables=VARIABLES)
    assert (result.status, result.normalized) == ("ok", expected), result.reasons
    assert rule in result.rules


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
    (r"F_{[a,b]} \varphi := \top \mathcal{U}_{[a,b]} \varphi", "operator_definition"),
    (r"\Diamond_{[a,b]} \varphi = \top \mathcal{U}_{[a,b]} \varphi", "operator_definition"),
    (r"\Box_{[0,5]} p, \Diamond_{[0,5]} q", "several_formulas"),
    (r"\phi = \Box_{[0,5]} p \text{ where } p = x > 0", "several_formulas"),
    (r"\loop_{[0,5]} p", "macro_loop"),
    (r"\Box_{[0,5]} \frobnicate p", "unknown_command"),
    (r"G (p \rightarrow F q)", "unbounded_operator"),
    (r"\Box p", "unbounded_operator"),
    (r"\mathbf{F}_{[0,\infty)} p", "unbounded_operator"),
    (r"p \mathcal{U} q", "unbounded_operator"),
    (r"\Box_{[3,1]} p", "empty_interval"),
    (r"\Box_{[-1,0]} p", "negative_bound"),
    (r"\Box_{[0,3000000000]} p", "bound_too_large"),
    (r"\Box_{[0,5]} 2x > 1", "multiplication"),
    (r"\Box_{[0,5]} a \cdot x > 1", "multiplication"),
    (r"\Box_{[0,5]} k x > 1", "multiplication"),
    (r"\Box_{[0,5]} x / y > 1", "division"),
    (r"\Box_{[0,5]} (x-1)^2 < 1", "power"),
    (r"\Box_{[0,5]} \sin x < 1", "function"),
    (r"\Box_{[0,5]} f(x) < 1", "function"),
    (r"\Box_{[0,5]} \|x\| < 1", "function"),
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
    assert run(r"\Box_{[0,5]} p", other_logic="past-time").reasons == ["other_logic: past-time"]
    flag = "the formula ends or starts with a connective: part of it may be on another row"
    assert run(r"\Box_{[0,5]} p \wedge", flags=[flag]).reasons == ["connective_at_edge"]


def test_every_rule_is_tested():
    tested = ({c[2] for c in OK_CASES} | {c[2] for c in RECORDED_CASES} | {c[1] for c in REJECTED_CASES}
              | {"random_symbolic_bounds", "other_logic", "connective_at_edge", "bounds_unsatisfiable",
                 "placeholder_subformula", "ambiguous_scope"})
    # stlgen_error is the check of step 7, after the normalization (test_stlgen_accepts_every_ok_case)
    assert set(RULES) - tested == {"stlgen_error"}


def test_bounds_that_no_draw_satisfies():
    assert run(r"\Box_{[a, a-200]} p").reasons[0].startswith("bounds_unsatisfiable")


def test_structure():
    result = run(r"\psi = \Box_{[0,30]} (gear = 4 \rightarrow \Diamond_{[0,5]} rpm < 3000)")
    assert result.structure == "G[#,#] ((a == #) -> (F[#,#] (b < #)))"
    # A name used twice keeps its letter; numbers inside expressions are hidden too
    assert run(r"(\Box_{[0,5]} x < 3) \rightarrow (\Box_{[0,2]} x < 4)").structure == \
           "(G[#,#] (a < #)) -> (G[#,#] (a < #))"
    assert run(r"(\Box_{[0,5]} x < 3) \rightarrow (\Box_{[0,2]} y < 4)").structure == \
           "(G[#,#] (a < #)) -> (G[#,#] (b < #))"
    assert run(r"\Box_{[0,5]} |x - y| > -x").structure == "G[#,#] (|a - b| > (# - a))"
    # Formulas that differ only in numbers and names share their structure
    assert run(r"\Diamond_{[1,2]} p").structure == run(r"\Diamond_{[0,T]} \varphi").structure == "F[#,#] a"
    assert run(r"\Box p").structure is None


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
