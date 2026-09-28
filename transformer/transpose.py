"""Transponiert ein geparstes Songbuch (AST) um n Halbtöne.

Sitzt als eigener Schritt zwischen CordaTransformer und Renderer: nimmt ein
Book entgegen und gibt eine transponierte Kopie zurück, ohne dass Grammatik,
AST-Klassen oder Renderer etwas von Akkorden "wissen" müssen.
"""
from dataclasses import replace

from transformer.chords import preferred_accidental, transpose_chord_str
from transformer.transformer import Book, Line, MetaCategory, Page, Paragraph, Word


def page_key(page: Page) -> str | None:
    """Die "Key:"-Metaangabe einer Page, falls vorhanden."""
    if not page.title_section:
        return None
    for info in page.title_section.infos:
        if info.category == MetaCategory.key:
            return info.text
    return None


def transpose_word(word: Word, semitones: int, prefer) -> Word:
    boxes = [(transpose_chord_str(chord, semitones, prefer), text) for chord, text in word.boxes]
    return replace(word, boxes=boxes)


def transpose_line(line: Line, semitones: int, prefer) -> Line:
    tokens = [transpose_word(word, semitones, prefer) for word in line.tokens]
    return replace(line, tokens=tokens)


def transpose_paragraph(paragraph: Paragraph, semitones: int, prefer) -> Paragraph:
    lines = [transpose_line(line, semitones, prefer) for line in paragraph.lines]
    return replace(paragraph, lines=lines)


def transpose_page(page: Page, semitones: int) -> Page:
    prefer = preferred_accidental(page_key(page))
    paragraphs = [transpose_paragraph(p, semitones, prefer) for p in page.paragraphs]
    return replace(page, paragraphs=paragraphs)


def transpose_book(book: Book, semitones: int) -> Book:
    """Gibt eine neue Book-Instanz mit allen Akkorden um `semitones` verschoben zurück.

    `semitones=0` gibt praktisch eine Kopie zurück. Die Zielschreibweise (#/b)
    richtet sich pro Page nach deren "Key:"-Metaangabe (falls vorhanden und
    über den Quintenzirkel bekannt), sonst bleibt je Akkord dessen
    ursprüngliche Schreibweise erhalten.
    """
    pages = [transpose_page(page, semitones) for page in book.pages]
    return replace(book, pages=pages)
