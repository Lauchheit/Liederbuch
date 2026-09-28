from transformer.chords import ParsedChord, parse_chord, preferred_accidental, transpose_chord_str, transpose_key


def test_parse_simple_chord():
    assert parse_chord("C") == ParsedChord(root="C", quality="")


def test_parse_minor_with_extension():
    assert parse_chord("C#m7") == ParsedChord(root="C#", quality="m7")


def test_parse_extensions():
    assert parse_chord("Gadd9") == ParsedChord(root="G", quality="add9")
    assert parse_chord("Bdim") == ParsedChord(root="B", quality="dim")
    assert parse_chord("EM7") == ParsedChord(root="E", quality="M7")


def test_parse_slash_chord():
    assert parse_chord("D/F#") == ParsedChord(root="D", quality="", bass="F#")
    assert parse_chord("G/B") == ParsedChord(root="G", quality="", bass="B")


def test_parse_non_chord_returns_none():
    assert parse_chord("") is None
    assert parse_chord("Hello") is None


def test_transpose_simple():
    assert transpose_chord_str("C", 2) == "D"
    assert transpose_chord_str("A", 3) == "C"


def test_transpose_wraps_around_octave():
    assert transpose_chord_str("B", 1) == "C"
    assert transpose_chord_str("C", -1) == "B"


def test_transpose_keeps_quality_and_bass():
    assert transpose_chord_str("C#m7/G#", 1) == "Dm7/A"


def test_transpose_negative_semitones():
    assert transpose_chord_str("D", -2) == "C"


def test_transpose_prefer_flat_and_sharp():
    assert transpose_chord_str("C", 1, prefer="sharp") == "C#"
    assert transpose_chord_str("C", 1, prefer="flat") == "Db"


def test_transpose_falls_back_to_original_spelling():
    # kein prefer angegeben: Original war scharf notiert -> Ergebnis bleibt scharf
    assert transpose_chord_str("C#", 1) == "D"
    assert transpose_chord_str("F#", 1) == "G"
    # Original war b-notiert -> Ergebnis bleibt b-notiert
    assert transpose_chord_str("Db", 2) == "Eb"
    assert transpose_chord_str("Bb", 3) == "Db"


def test_transpose_non_chord_passthrough():
    assert transpose_chord_str("", 3) == ""


def test_preferred_accidental_major_keys():
    assert preferred_accidental("G") == "sharp"
    assert preferred_accidental("F") == "flat"
    assert preferred_accidental("C") == "sharp"


def test_preferred_accidental_minor_keys():
    assert preferred_accidental("Em") == "sharp"
    assert preferred_accidental("Dm") == "flat"


def test_preferred_accidental_unknown_or_missing():
    assert preferred_accidental(None) is None
    assert preferred_accidental("") is None
    assert preferred_accidental("Xb") is None


def test_transpose_key_major():
    assert transpose_key("G", 2) == "A"
    assert transpose_key("C", -1) == "B"


def test_transpose_key_minor_keeps_suffix():
    assert transpose_key("Am", 2) == "Bm"
    assert transpose_key("Dm", -2) == "Cm"


def test_transpose_key_zero_is_identity():
    assert transpose_key("G", 0) == "G"


def test_transpose_key_unknown_returns_none():
    assert transpose_key("Xyz", 2) is None
