import transformer.grammar as grammar
from transformer.transformer import Book, CordaTransformer
from transformer.transpose import transpose_book


def _parse_page(content: str):
    cst = grammar.cst(content, start="page")
    return CordaTransformer().transform(cst)


def _chords(page) -> list[str]:
    return [
        chord
        for paragraph in page.paragraphs
        for line in paragraph.lines
        for word in line.tokens
        for chord, _ in word.boxes
        if chord
    ]


SONG_WITH_KEY = """---
Title: Test Song
Key: G
---

[Verse 1]
To {C}make it all {CM7}right
"""

SONG_WITHOUT_KEY = """---
Title: Test Song
---

[Verse 1]
{C#}Hey {Am}Jude {D/F#}don't
"""


def test_transpose_book_uses_key_for_spelling():
    page = _parse_page(SONG_WITH_KEY)
    book = transpose_book(Book(pages=[page]), 1)
    # Key "G" -> sharp preference, auch wenn Original-Akkorde keine Vorzeichen hatten
    assert _chords(book.pages[0]) == ["C#", "C#M7"]


def test_transpose_book_falls_back_without_key():
    page = _parse_page(SONG_WITHOUT_KEY)
    book = transpose_book(Book(pages=[page]), 2)
    # C# (scharf) -> D#, Am -> Bm, D/F# (scharf) -> E/G#
    assert _chords(book.pages[0]) == ["D#", "Bm", "E/G#"]


def test_transpose_book_zero_semitones_is_identity():
    page = _parse_page(SONG_WITHOUT_KEY)
    original = Book(pages=[page])
    transposed = transpose_book(original, 0)
    assert _chords(transposed.pages[0]) == _chords(original.pages[0])


def test_transpose_book_does_not_mutate_original():
    page = _parse_page(SONG_WITH_KEY)
    original = Book(pages=[page])
    transpose_book(original, 5)
    assert _chords(original.pages[0]) == ["C", "CM7"]
