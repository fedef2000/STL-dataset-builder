"""
Normalization of the extracted formulas (LaTeX as the papers write it) into the STL syntax of `stl-nl`: the paper's
macros expanded (latex.py), the formula cut into tokens (lexer.py), parsed into a tree (parser.py), its bounds resolved
and its symbols checked (rules.py), written back fully parenthesized (emit.py) and checked with the `stlgen` parser of
`stl-nl` (validate.py). normalize.py ties the stages together, run.py runs them on a file of records.

Two modes (rules.py): "stl-nl", for the formulas without a requirement, writes them in the grammar of stl-nl; "faithful",
for the paired formulas, keeps the meaning their description has, so it keeps the paper's bounds and powers beyond that
grammar, and is not checked with stlgen. Then: the pattern of each formula (pattern.py, from stlgen's AST or, in the
faithful mode, from stlgen_ast.py), the requirement passages written to match the formula (description.py), the choice
of the formulas for stl-nl (select.py) and the report (report.py). The rules are listed in docs/normalization_rules.md.
"""
