import transformer.transformer as transformer

PREAMBLE_PATH = "latex/preambel.tex"
END_PATH = "latex/end.tex"

class LaTeXRenderer:
    def __init__(self, style):
        self.style = style
        self.columns = style.columns

    def render_document(self, node) -> str:
        with open(PREAMBLE_PATH, "r") as f_pre:
            pre = f_pre.read()
        with open(END_PATH, "r") as f_end:
            end = f_end.read()

        body = self.render(node)
        return f"{pre}\n{self.style.to_latex_preamble()}\n\\begin{{document}}\n{body}\n{end}"

    def render(self, node):
        if isinstance(node, transformer.Paragraph):
            title = f"\\paragraphtitle{{{node.title}}}\n" if node.title else ""
            body = "".join(self.render(l) for l in node.lines)
            content = f"{title}{body}"
            # minipage ist für TeX ein unteilbares Element: passt sie nicht mehr
            # in die aktuelle Spalte/Seite, wird die ganze Strophe als Block auf die
            # nächste Spalte/Seite verschoben, statt mittendrin umzubrechen.
            return f"\\begin{{minipage}}{{\\linewidth}}\n{content}\\end{{minipage}}\n"

        elif isinstance(node, transformer.Line):
            if not node.has_chords:
                text = " ".join(text for word in node.tokens for _, text in word.boxes)
                return f"\\noindent \\lyricline{{{text}}}\\\\\n"
            boxes = " ".join(self.render(t) for t in node.tokens)
            return f"\\noindent {boxes}\\\\\n"

        elif isinstance(node, transformer.Word):
            return "".join(self.box(chord, text) for chord, text in node.boxes)
        
        elif isinstance(node, transformer.Page):
            title_section = f"{self.render(node.title_section)}\n" if node.title_section else ""
            body = "\n\n".join(self.render(paragraph) for paragraph in node.paragraphs)
            if self.columns > 1:
                body = f"\\begin{{multicols}}{{{self.columns}}}\n{body}\n\\end{{multicols}}"
            return f"{title_section}{body}"

        elif isinstance(node, transformer.TitleSection):
            return "".join(self.render(info) for info in node.infos)

        elif isinstance(node, transformer.MetaInfo):
            macro = transformer.meta_macro_name(node.category)
            return f"\\{macro}{{{node.text}}}\n"

        elif isinstance(node, transformer.Book):
            return "\n\\newpage\n".join(self.render(page) for page in node.pages)

        else:
            raise ValueError(f"Unbekannter Node-Typ: {type(node)}")

    def box(self, chord, text):
        return f"\\cw{{{chord}}}{{{text}}}"