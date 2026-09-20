import transformer.transformer as transformer

PREAMBLE_PATH = "latex/preambel.tex"
END_PATH = "latex/end.tex"

_LATEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "#": r"\#",
    "_": r"\_",
    "%": r"\%",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

def escape_latex(text: str) -> str:
    return "".join(_LATEX_ESCAPES.get(ch, ch) for ch in text)

class LaTeXRenderer:
    def __init__(self, style):
        self.style = style
        self.columns = style.columns

    def render_document(self, node) -> str:
        with open(PREAMBLE_PATH, "r", encoding="utf-8") as f_pre:
            pre = f_pre.read()
        with open(END_PATH, "r", encoding="utf-8") as f_end:
            end = f_end.read()

        body = self.render(node)
        return f"{pre}\n{self.style.to_latex_preamble()}\n\\begin{{document}}\n{body}\n{end}"

    def render(self, node):
        if isinstance(node, transformer.Paragraph):
            title = f"\\paragraphtitle{{{escape_latex(node.title)}}}\n" if node.title else ""
            body = "".join(self.render(l) for l in node.lines)
            content = f"{title}{body}"
            # minipage ist für TeX ein unteilbares Element: passt sie nicht mehr
            # in die aktuelle Spalte/Seite, wird die ganze Strophe als Block auf die
            # nächste Spalte/Seite verschoben, statt mittendrin umzubrechen.
            return f"\\begin{{minipage}}{{\\linewidth}}\n\\raggedright\n{content}\\end{{minipage}}\n"

        elif isinstance(node, transformer.Line):
            if not node.has_chords:
                text = " ".join(text for word in node.tokens for _, text in word.boxes)
                return f"\\noindent \\lyricline{{{escape_latex(text)}}}\\\\\n"
            if not node.has_lyrics:
                # Reine Akkordzeile (z.B. Intro-/Interlude-Riff): kompakt wie \lyricline,
                # sonst würde die (dann leere) Textzeile trotzdem reserviert und einzelne
                # Akkorde ohne Lyrics dazwischen würden ohne Leerzeichen aneinanderkleben.
                chords = " ".join(chord for word in node.tokens for chord, _ in word.boxes)
                return f"\\noindent \\chordline{{{escape_latex(chords)}}}\\\\\n"
            boxes = " ".join(self.render(t) for t in node.tokens)
            return f"\\noindent {boxes}\\\\\n"

        elif isinstance(node, transformer.Word):
            return "".join(self.box(chord, text) for chord, text in node.boxes)
        
        elif isinstance(node, transformer.Page):
            # \strut\par statt nur einer Leerzeile: die Metadaten-Makros (\metaTitle,
            # \metaArtist, ...) enden alle mit \\ (Zeilenumbruch INNERHALB des Absatzes).
            # Ein Absatz, der mit \\ endet, gefolgt von \par (Leerzeile), erzeugt in LaTeX
            # eine leere letzte Zeile ohne Höhe - dadurch würde \parskip vor der ersten
            # Strophe verschluckt. \strut gibt dieser letzten Zeile echte Höhe zurück.
            title_section = f"{self.render(node.title_section)}\\strut\\par\n" if node.title_section else ""
            body = "\n\n".join(self.render(paragraph) for paragraph in node.paragraphs)
            if self.columns > 1:
                body = f"\\cordaSongLayout{{{body}}}"
            return f"{title_section}{body}"

        elif isinstance(node, transformer.TitleSection):
            return "".join(self.render(info) for info in node.infos)

        elif isinstance(node, transformer.MetaInfo):
            macro = transformer.meta_macro_name(node.category)
            return f"\\{macro}{{{escape_latex(node.text)}}}\n"

        elif isinstance(node, transformer.Book):
            # Inhaltsverzeichnis nur bei echten Mehr-Song-Buechern, nicht bei der
            # Einzelsong-Vorschau (ein Page-Buch braucht kein Verzeichnis seiner selbst).
            is_book = len(node.pages) > 1
            parts = []
            if is_book:
                parts.append("\\tableofcontents")
            for page in node.pages:
                page_body = self.render(page)
                if is_book:
                    page_body = f"\\addcontentsline{{toc}}{{section}}{{{escape_latex(self._page_title(page))}}}\n{page_body}"
                parts.append(page_body)
            return "\n\\newpage\n".join(parts)

        else:
            raise ValueError(f"Unbekannter Node-Typ: {type(node)}")

    def _page_title(self, page) -> str:
        if page.title_section:
            for info in page.title_section.infos:
                if info.category == transformer.MetaCategory.title:
                    return info.text
        return "Unbenannt"

    def box(self, chord, text):
        return f"\\cw{{{escape_latex(chord)}}}{{{escape_latex(text)}}}"