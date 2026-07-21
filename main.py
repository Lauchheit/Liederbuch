
import subprocess
import transformer.grammar as grammar
from transformer.transformer import CordaTransformer
from pprint import pprint
from transformer.renderer import LaTeXRenderer
from transformer.style import Style

with open("input.corda", "r") as f:
    input = f.read()
cst = grammar.cst(input)
ast = CordaTransformer().transform(cst)

renderer: LaTeXRenderer = LaTeXRenderer()
rendered = renderer.render(ast)

style = Style()

with open("latex/preambel.tex", 'r') as f_pre:
    pre = f_pre.read()
with open("latex/end.tex") as f_end:
    end = f_end.read()

output = f"{pre}\n{style.to_latex_preamble()}\n\\begin{{document}}\n{rendered}\n{end}"

with open("output.tex", 'w') as f_out:
    f_out.write(output)

subprocess.run(
    ["pdflatex", "-interaction=nonstopmode", "output.tex"],
    check=True,
)

