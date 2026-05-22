import transformer.transformer as transformer

class LaTeXRenderer:
    def render(self, node):
        if isinstance(node, transformer.Line):
            boxes = " ".join(self.render(t) for t in node.tokens)
            return f"\\noindent {boxes}\\\\\n"
        
        elif isinstance(node, transformer.MidChord):
            # "be{Fm}fore" → \cw{be-}{Fm}\cw{}{fore}
            return self.box("", node.prefix + "-") + self.box(node.chord, node.suffix)
        
        elif isinstance(node, transformer.PreChord):
            # "{G}house" → \cw{G}{house}
            return self.box(node.chord, node.text)
        
        elif isinstance(node, transformer.PlainChord):
            # "{A}" → \cw{A}{}
            return self.box(node.text, "")
        
        elif isinstance(node, transformer.PlainText):
            # "will" → \cw{}{will}
            return self.box("", node.text)
        
        elif isinstance(node, transformer.PostChord):
            # "I{Cm}" → \cw{}{I} \cw{Cm}{}
            return self.render(transformer.PlainText(node.text)) + \
                   self.render(transformer.PlainChord(node.chord))
        
        else:
            raise ValueError(f"Unbekannter Node-Typ: {type(node)}")

    def box(self, chord, text):
        return f"\\cw{{{chord}}}{{{text}}}"