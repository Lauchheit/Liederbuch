import transformer.transformer as transformer

class LaTeXRenderer:
    def render(self, node):
        if isinstance(node, transformer.Paragraph):
            title = f"\\paragraphtitle{{{node.title}}}\n" if node.title else ""
            body = "".join(self.render(l) for l in node.lines)
            return f"{title}{body}"

        elif isinstance(node, transformer.Line):
            boxes = " ".join(self.render(t) for t in node.tokens)
            return f"\\noindent {boxes}\\\\\n"

        elif isinstance(node, transformer.Word):
            return "".join(self.box(chord, text) for chord, text in node.boxes)
        
        elif isinstance(node, transformer.Page):
            title_section = f"{self.render(node.title_section)}\n" if node.title_section else ""
            body = "\n\n".join(self.render(paragraph) for paragraph in node.paragraphs)
            return f"{title_section}{body}"

        elif isinstance(node, transformer.TitleSection):
            return "".join(self.render(info) for info in node.infos)

        elif isinstance(node, transformer.MetaInfo):
            macro = transformer.meta_macro_name(node.category)
            return f"\\{macro}{{{node.text}}}\n"

        else:
            raise ValueError(f"Unbekannter Node-Typ: {type(node)}")

    def box(self, chord, text):
        return f"\\cw{{{chord}}}{{{text}}}"