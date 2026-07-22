from dataclasses import dataclass, field

from transformer.transformer import MetaCategory, meta_macro_name

# LaTeX-Schriftgrößenbefehle, von klein nach groß
FONT_SIZES = [
    "tiny", "scriptsize", "footnotesize", "small",
    "normalsize", "large", "Large", "LARGE", "huge", "Huge",
]


@dataclass
class MetaStyle:
    """Aussehen einer einzelnen Metadaten-Kategorie (Title, Artist, ...)."""

    color: str = "1A1A1A"
    size: str = "normalsize"
    bold: bool = False
    italic: bool = False
    smallcaps: bool = False
    center: bool = False

    def __post_init__(self):
        if self.size not in FONT_SIZES:
            raise ValueError(
                f"size={self.size!r} ist keine gültige LaTeX-Größe. "
                f"Erlaubt: {', '.join(FONT_SIZES)}"
            )


def default_meta_styles() -> dict[MetaCategory, MetaStyle]:
    """Standard-Aussehen je Kategorie.

    Um eine neue Kategorie hinzuzufügen: Eintrag in MetaCategory (transformer.py),
    im Grammatik-Terminal 'meta_category' (grammar.py) und hier ergänzen -
    Renderer und LaTeX-Erzeugung greifen automatisch darauf zu.
    """
    return {
        MetaCategory.title: MetaStyle(
            color="1A1A1A", size="large", bold=True, center=False
        ),
        MetaCategory.artist: MetaStyle(
            color="6B6B6B", size="small", italic=True, center=False
        ),
        MetaCategory.subtitle: MetaStyle(
            color="8A8A8A", size="footnotesize", italic=True, center=False
        ),
        MetaCategory.instruction: MetaStyle(
            color="8A8A8A", size="footnotesize", smallcaps=True
        ),
    }


@dataclass
class Style:
    """Steuert Farben, Schriftgrößen und Abstände des gerenderten Liederbuchs.

    Farben als Hex-Code ohne '#' (z.B. "2E86AB"), Größen als LaTeX-Größenbefehl
    ohne Backslash (z.B. "small", siehe FONT_SIZES).
    """

    # Akkorde
    chord_color: str = "2E86AB"
    chord_size: str = "small"
    chord_bold: bool = True

    # Liedtext
    lyric_color: str = "1A1A1A"
    lyric_size: str = "normalsize"
    lyric_bold: bool = False

    # Strophenlabel (z.B. "Refrain", "Strophe 1")
    title_color: str = "8A8A8A"
    title_size: str = "footnotesize"
    title_bold: bool = False
    # nur eine der beiden Formen wirkt gleichzeitig (title_smallcaps hat Vorrang)
    title_italic: bool = False
    title_smallcaps: bool = True

    # Abstände
    paragraph_skip: str = "1.5em"
    title_gap: str = "0.3em"
    chord_lyric_gap: str = "2pt"

    # Kopfzeile (Title/Artist/Subtitle/Instruction, siehe MetaStyle)
    meta_styles: dict[MetaCategory, MetaStyle] = field(default_factory=default_meta_styles)

    # Layout
    columns: int = 2
    column_sep: str = "1.8em"
    column_rule_width: str = "0pt"

    # Seitenränder
    margin_left: str = "2.2cm"
    margin_right: str = "1.2cm"
    margin_top: str = "1.2cm"
    margin_bottom: str = "2.5cm"

    def __post_init__(self):
        for field_name in ("chord_size", "lyric_size", "title_size"):
            value = getattr(self, field_name)
            if value not in FONT_SIZES:
                raise ValueError(
                    f"{field_name}={value!r} ist keine gültige LaTeX-Größe. "
                    f"Erlaubt: {', '.join(FONT_SIZES)}"
                )
        if self.columns < 1:
            raise ValueError(f"columns={self.columns!r} muss mindestens 1 sein.")

    def to_latex_preamble(self) -> str:
        chord_weight = r"\bfseries" if self.chord_bold else r"\mdseries"
        lyric_weight = r"\bfseries" if self.lyric_bold else r"\mdseries"
        title_weight = r"\bfseries" if self.title_bold else r"\mdseries"
        if self.title_smallcaps:
            title_shape = r"\scshape"
        elif self.title_italic:
            title_shape = r"\itshape"
        else:
            title_shape = r"\upshape"

        lyric_style = rf"\color{{lyriccolor}}\{self.lyric_size}{lyric_weight}"

        return rf"""\usepackage{{xcolor}}
\usepackage{{multicol}}
\usepackage[left={self.margin_left},right={self.margin_right},top={self.margin_top},bottom={self.margin_bottom}]{{geometry}}

\definecolor{{chordcolor}}{{HTML}}{{{self.chord_color}}}
\definecolor{{lyriccolor}}{{HTML}}{{{self.lyric_color}}}
\definecolor{{titlecolor}}{{HTML}}{{{self.title_color}}}

\setlength{{\parskip}}{{{self.paragraph_skip}}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\columnsep}}{{{self.column_sep}}}
\setlength{{\columnseprule}}{{{self.column_rule_width}}}

% Akkord-Text-Box: Akkord über der Silbe/dem Wort
\newcommand{{\cw}}[2]{{%
  \begin{{tabular}}[t]{{@{{}}l@{{}}}}%
    \color{{chordcolor}}\{self.chord_size}{chord_weight} #1\\[{self.chord_lyric_gap}]%
    {lyric_style} #2%
  \end{{tabular}}%
}}

% Akkordlose Zeile: reiner Fließtext ohne Akkordzeile, spart die dafür reservierte Höhe
\newcommand{{\lyricline}}[1]{{%
  {lyric_style} #1%
}}

% Dezentes Strophenlabel (z.B. "Refrain", "Strophe 1")
\newcommand{{\paragraphtitle}}[1]{{%
  \noindent{{\color{{titlecolor}}\{self.title_size}{title_weight}{title_shape} #1}}\\[{self.title_gap}]%
}}

% Kopfzeile: ein Befehl pro Metadaten-Kategorie (\metaTitle, \metaArtist, ...)
{self._meta_macros_latex()}
"""

    def _meta_macros_latex(self) -> str:
        return "\n\n".join(
            self._meta_macro_latex(category, mstyle)
            for category, mstyle in self.meta_styles.items()
        )

    def _meta_macro_latex(self, category: MetaCategory, mstyle: MetaStyle) -> str:
        weight = r"\bfseries" if mstyle.bold else r"\mdseries"
        if mstyle.smallcaps:
            shape = r"\scshape"
        elif mstyle.italic:
            shape = r"\itshape"
        else:
            shape = r"\upshape"

        macro_name = meta_macro_name(category)
        color_name = f"{macro_name}color"
        content = rf"\color{{{color_name}}}\{mstyle.size}{weight}{shape} #1"
        body = (
            rf"\begin{{center}}{content}\end{{center}}"
            if mstyle.center
            else rf"\noindent{{{content}}}\\"
        )

        return rf"""\definecolor{{{color_name}}}{{HTML}}{{{mstyle.color}}}
\newcommand{{\{macro_name}}}[1]{{{body}}}"""
