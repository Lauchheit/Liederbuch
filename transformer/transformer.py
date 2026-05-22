from lark import Transformer
from dataclasses import dataclass

# AST-Klassen
@dataclass
class MidChord:
    prefix: str
    chord: str
    suffix: str

@dataclass
class PreChord:
    chord: str
    text: str

@dataclass
class PlainChord:
    text: str

@dataclass 
class PlainText:
    text: str

@dataclass
class Line:
    tokens: list


@dataclass
class PostChord:
    text: str
    chord: str

# Transformer: CST → AST
class CordaTransformer(Transformer):
    def word(self, items):
        return items[0] 
    
    def chordtoken(self, items):
        return str(items[0]) 
    
    def mid_chord(self, items):
        return MidChord(str(items[0]), str(items[1]), str(items[2]))
    
    def pre_chord(self, items):
        return PreChord(str(items[0]), str(items[1]))
    
    def post_chord(self, items):
        return PostChord(str(items[0]), str(items[1]))
    
    def plain_chord(self, items):
        return PlainChord(str(items[0]))
    
    def plain_text(self, items):
        return PlainText(str(items[0]))
    
    def texttoken(self, items):
        return str(items[0])
    
    def line(self, items):
        return Line(tokens=items)