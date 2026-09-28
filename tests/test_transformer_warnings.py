import transformer.grammar as grammar
from transformer.transformer import CordaTransformer

SONG_WITH_BAD_CHORD = """---
Title: Test Song
---

[Verse 1]
To {C}make it {7Cm}all right
"""

SONG_ALL_VALID = """---
Title: Test Song
---

[Verse 1]
To {C}make it {Am7}all {D/F#}right
"""

SONG_WITH_ESCAPED_MARKER = """---
Title: Test Song
---

[Instrumental]
{Em}{C}{G}{D/F}{\\x2}
"""


def test_unknown_chord_produces_warning_with_line_number():
    cst = grammar.cst(SONG_WITH_BAD_CHORD, start="page")
    t = CordaTransformer()
    t.transform(cst)
    assert len(t.warnings) == 1
    assert "Zeile 6" in t.warnings[0]
    assert "{7Cm}" in t.warnings[0]


def test_song_still_renders_despite_unknown_chord():
    cst = grammar.cst(SONG_WITH_BAD_CHORD, start="page")
    page = CordaTransformer().transform(cst)
    chords = [c for para in page.paragraphs for line in para.lines for word in line.tokens for c, _ in word.boxes]
    assert "7Cm" in chords


def test_no_warnings_for_valid_chords():
    cst = grammar.cst(SONG_ALL_VALID, start="page")
    t = CordaTransformer()
    t.transform(cst)
    assert t.warnings == []


def test_escaped_marker_produces_no_warning_and_strips_backslash():
    cst = grammar.cst(SONG_WITH_ESCAPED_MARKER, start="page")
    t = CordaTransformer()
    page = t.transform(cst)
    assert t.warnings == []
    chords = [c for para in page.paragraphs for line in para.lines for word in line.tokens for c, _ in word.boxes]
    assert "x2" in chords
    assert "\\x2" not in chords
