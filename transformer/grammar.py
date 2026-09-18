from lark import Lark, ParseTree

grammar = r"""
book            :   page (PAGEBREAK page)* LINEBREAK*

PAGEBREAK       :   ANY_BREAK* "%NEW_SONG%" ANY_BREAK*

page            :   (title_section ANY_BREAK)? paragraph (PARAGRAPH_BREAK paragraph)+ LINEBREAK*

title_section       :   "---" ANY_BREAK meta_token (INDENT_LINEBREAK meta_token)* ANY_BREAK "---"
meta_token      :   (meta_category ":" SPACE* TEXT_LINE)
meta_category   :   META_CATEGORY_KEYWORD
META_CATEGORY_KEYWORD  :   "Title" | "Artist" | "Subtitle" | "Instruction"

paragraph       :   ((PARAGRAPH_TITLE LINEBREAK)? line? (LINEBREAK line)*) | PARAGRAPH_TITLE
line            :   word (SPACE+ word)*
word            :   TEXTTOKEN chord_run*
                |   chord_run+

chord_run       :   CHORDTOKEN TEXTTOKEN?

CHORDTOKEN      :   "{" TEXTTOKEN "}"
PARAGRAPH_TITLE :   "[" TEXT_LINE "]"
TEXT_LINE       :   TEXTTOKEN (SPACE+ TEXTTOKEN)*
TEXTTOKEN       :   /[^{}\[\]\s]+/
SPACE           :   " " | "\t"
PARAGRAPH_BREAK :   LINEBREAK LINEBREAK+
LINEBREAK       :   "\n"
INDENT_LINEBREAK:   LINEBREAK SPACE*
ANY_BREAK       :   (LINEBREAK | SPACE)+
"""

def cst(input: str, start:str = "book")->ParseTree:
    if f"%NEW_SONG%" in input and start != "book": raise ValueError("Cannot parse an input file with multiple songs in it on page level")
    parser = Lark(grammar, start=start)
    tree = parser.parse(input)
    return tree

