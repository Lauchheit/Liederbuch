
import transformer.grammar as grammar
from transformer.transformer import CordaTransformer
from pprint import pprint
from transformer.renderer import LaTeXRenderer

input = "Be{Fm}fore I for{C}get {A} {B}  {C}I{Cm} will {Fm}remember"
cst = grammar.cst(input)
ast = CordaTransformer().transform(cst)

renderer: LaTeXRenderer = LaTeXRenderer()
rendered = renderer.render(ast)

with open("latex/preambel.tex", 'r') as f_pre:
    pre = f_pre.read()
with open("latex/end.tex") as f_end:
    end = f_end.read()

output = f"{pre}\n{rendered}\n{end}" 

with open("output.tex", 'w') as f_out:
    f_out.write(output)
