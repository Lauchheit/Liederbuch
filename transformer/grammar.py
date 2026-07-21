from lark import Lark, ParseTree

grammar = r"""
page            :   title_section? LINEBREAK + paragraph (PARAGRAPH_BREAK paragraph)+

title_section       :   "[" LINEBREAK? meta_token (LINEBREAK meta_token)* LINEBREAK? "]"
meta_token      :   (meta_category ":" " "* TEXT_LINE)
meta_category   :   META_CATEGORY_KEYWORD
META_CATEGORY_KEYWORD  :   "Title" | "Artist" | "Subtitle" | "Instruction"

paragraph       :   (PARAGRAPH_TITLE? LINEBREAK) line (LINEBREAK line)*
line            :   word (SPACE+ word)*
word            :   TEXTTOKEN chord_run*
                |   chord_run+

chord_run       :   CHORDTOKEN TEXTTOKEN?

CHORDTOKEN      :   "{" TEXTTOKEN "}"
PARAGRAPH_TITLE :   "[" TEXT_LINE "]"
TEXT_LINE       :   TEXTTOKEN (SPACE+ TEXTTOKEN)*
TEXTTOKEN       :   /[a-zA-Z0-9äöüÄÖÜß\!?'\-]+/
SPACE           :   " "
LINEBREAK       :   "\n"
PARAGRAPH_BREAK :   "\n\n"
"""

def cst(input: str)->ParseTree:
    parser = Lark(grammar, start="page")
    tree = parser.parse(input)
    print(tree.pretty())
    return tree

# input = "Be{Fm}fore I for{C}get {A} I{Cm} will {Fm}remember"
