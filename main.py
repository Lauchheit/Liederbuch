
import subprocess
import transformer.grammar as grammar
from transformer.transformer import CordaTransformer
from pprint import pprint
from transformer.renderer import LaTeXRenderer
from transformer.style import Style

with open("input/input.corda", "r") as f:
    input = f.read()

cst = grammar.cst(input)
ast = CordaTransformer().transform(cst)

style = Style()

renderer: LaTeXRenderer = LaTeXRenderer(style)
output = renderer.render_document(ast)

with open("output.tex", 'w') as f_out:
    f_out.write(output)

subprocess.run(
    ["pdflatex", "-interaction=nonstopmode", "output.tex"],
    check=True,
)

