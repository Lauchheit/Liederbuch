from lark import Lark, ParseTree

grammar = r"""
line            :   word (" "+ word)*
word            :   (mid_chord | pre_chord | post_chord | plain_chord | plain_text)

mid_chord       :   TEXTTOKEN CHORDTOKEN TEXTTOKEN

pre_chord       :   CHORDTOKEN TEXTTOKEN
post_chord      :   TEXTTOKEN CHORDTOKEN

plain_chord     :   CHORDTOKEN
plain_text      :   TEXTTOKEN

CHORDTOKEN      :   "{" TEXTTOKEN "}"
TEXTTOKEN       :   /[a-zA-ZäöüÄÖÜß\!?'\-]+/
"""

grammar2 = r"""
line            :   word (" "+ word)*
word            :   

chord_box       :   

plain_chord     :   CHORDTOKEN
plain_text      :   TEXTTOKEN

CHORDTOKEN      :   "{" TEXTTOKEN "}"
TEXTTOKEN       :   /[a-zA-ZäöüÄÖÜß\!?'\-]+/
"""

def cst(input: str)->ParseTree:
    parser = Lark(grammar, start="line")
    tree = parser.parse(input)
    print(tree.pretty())
    return tree

# input = "Be{Fm}fore I for{C}get {A} I{Cm} will {Fm}remember"