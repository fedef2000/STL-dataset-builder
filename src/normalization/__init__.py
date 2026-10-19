"""
Normalization of the formulas of the dataset (LaTeX as the papers write it) into the STL grammar of `stl-nl`: the
paper's macros expanded (latex.py), the formula cut into tokens (lexer.py), parsed into a tree (parser.py), its bounds
resolved and its symbols checked (rules.py), written back fully parenthesized (emit.py) and checked with the `stlgen`
parser of `stl-nl` (validate.py). normalize.py ties the stages together. The rules are listed in docs/normalization_rules.md.
"""
