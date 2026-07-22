from lark import Transformer, Token
from dataclasses import dataclass
from enum import Enum
# AST-Klassen
@dataclass
class Word:
    # Liste von (chord, text) Paaren in Render-Reihenfolge
    boxes: list

@dataclass
class Line:
    tokens: list

    @property
    def has_chords(self) -> bool:
        return any(chord for word in self.tokens for chord, _ in word.boxes)

@dataclass
class Paragraph:
    title: str
    lines: list[Line]

class MetaCategory(Enum):
    title=1
    artist=2
    subtitle=3
    instruction=4

@dataclass
class MetaInfo:
    category: MetaCategory
    text: str

@dataclass
class TitleSection:
    infos: list[MetaInfo]

def meta_macro_name(category: MetaCategory) -> str:
    """LaTeX-Befehlsname für eine Metadaten-Kategorie, z.B. title -> 'metaTitle'."""
    return f"meta{category.name.capitalize()}"

@dataclass
class Page:
    title_section: TitleSection | None
    paragraphs: list[Paragraph]



# Transformer: CST → AST
class CordaTransformer(Transformer):
    def chord_run(self, items):
        chord = str(items[0])[1:-1]  # Klammern "{" "}" entfernen
        text = str(items[1]) if len(items) > 1 else ""
        return (chord, text)

    def word(self, items):
        boxes = []
        if items and isinstance(items[0], Token):
            leading_text = str(items[0])
            chord_runs = items[1:]
            if chord_runs:
                _, first_text = chord_runs[0]
                # Bindestrich nur, wenn das Wort nach dem Akkord weitergeht
                hyphen = len(chord_runs) > 1 or first_text != ""
                boxes.append(("", leading_text + ("-" if hyphen else "")))
                boxes.extend(chord_runs)
            else:
                boxes.append(("", leading_text))
        else:
            boxes.extend(items)
        return Word(boxes=boxes)

    def line(self, items):
        return Line(tokens=[item for item in items if isinstance(item, Word)])

    def paragraph(self, items):
        title = (items[0])[1:-1] if isinstance(items[0], str) else ""
        lines = [item for item in items if isinstance(item, Line)]
        return Paragraph(title=title, lines=lines)
    
    def meta_category(self, items):
        return MetaCategory[str(items[0]).lower()]

    def meta_token(self, items):
        category, text = items[0], items[-1]
        return MetaInfo(category=category, text=str(text).strip())

    def title_section(self, items):
        infos = [item for item in items if isinstance(item, MetaInfo)]
        return TitleSection(infos=infos)

    def page(self, items):
        title_section: TitleSection | None = items[0] if items and isinstance(items[0], TitleSection) else None
        paragraphs = [item for item in items if isinstance(item, Paragraph)]
        return Page(title_section=title_section, paragraphs=paragraphs)
    

