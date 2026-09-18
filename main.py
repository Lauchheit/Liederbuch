
import subprocess
import transformer.grammar as grammar
from transformer.transformer import CordaTransformer, Book
from pprint import pprint
from transformer.renderer import LaTeXRenderer
from transformer.style import Style
import os
input_dir = "./input"

pages = []
for filename in sorted(os.listdir(input_dir)):
    if filename.split(".")[-1] != "corda": continue
    with open(os.path.join(input_dir, filename), 'r', encoding="utf-8") as f:
        content = f.read()
    try:
        cst = grammar.cst(content, start="book")
        book = CordaTransformer().transform(cst)
        pages.extend(book.pages)
    except Exception as e:
        print(f"WARNUNG: {filename} konnte nicht geparst werden, wird übersprungen.\n  {e}")

ast = Book(pages=pages)

style = Style()

renderer: LaTeXRenderer = LaTeXRenderer(style)
output = renderer.render_document(ast)

with open("output.tex", 'w', encoding="utf-8") as f_out:
    f_out.write(output)

subprocess.run(
    ["pdflatex", "-interaction=nonstopmode", "output.tex"],
    check=True,
)

