"""Akkord-Parsing und Transposition.

Ein Akkordstring wie "C#m7/G#" wird in Grundton ("C#"), Akkordart ("m7") und
optionale Bassnote bei Slash-Akkorden ("G#") zerlegt. Transponieren verschiebt
Grundton und Bassnote um n Halbtöne über eine Halbton-Tabelle; die Akkordart
bleibt als reiner Text unverändert stehen.
"""
import re
from dataclasses import dataclass
from typing import Literal

Accidental = Literal["sharp", "flat"]

NOTE_TO_SEMITONE: dict[str, int] = {
    "C": 0, "B#": 0,
    "C#": 1, "Db": 1,
    "D": 2,
    "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4,
    "F": 5, "E#": 5,
    "F#": 6, "Gb": 6,
    "G": 7,
    "G#": 8, "Ab": 8,
    "A": 9,
    "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11,
}

SEMITONE_TO_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
SEMITONE_TO_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

# Quintenzirkel: welche Durtonarten werden mit # bzw. b notiert.
SHARP_MAJOR_KEYS = {"C", "G", "D", "A", "E", "B", "F#", "C#"}
FLAT_MAJOR_KEYS = {"F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb"}

# Molltonart (z.B. "Am") -> parallele Durtonart (z.B. "C"), um dieselbe
# Vorzeichen-Präferenz wie die Durtonart zu übernehmen.
MINOR_TO_RELATIVE_MAJOR = {
    "Am": "C", "Em": "G", "Bm": "D", "F#m": "A", "C#m": "E", "G#m": "B",
    "D#m": "F#", "A#m": "C#",
    "Dm": "F", "Gm": "Bb", "Cm": "Eb", "Fm": "Ab", "Bbm": "Db", "Ebm": "Gb", "Abm": "Cb",
}

_CHORD_RE = re.compile(r"^([A-G][#b]?)([^/]*)(?:/([A-G][#b]?))?$")


@dataclass
class ParsedChord:
    root: str
    quality: str
    bass: str | None = None

    def __str__(self) -> str:
        suffix = f"/{self.bass}" if self.bass else ""
        return f"{self.root}{self.quality}{suffix}"


def parse_chord(raw: str) -> ParsedChord | None:
    """Zerlegt einen Akkordstring in Grundton/Akkordart/Bassnote.

    Gibt None zurück, wenn raw nicht wie ein Akkord aussieht (z.B. leerer
    String) - der Aufrufer soll solche Strings dann unverändert übernehmen.
    """
    match = _CHORD_RE.match(raw)
    if not match:
        return None
    root, quality, bass = match.groups()
    return ParsedChord(root=root, quality=quality, bass=bass)


def preferred_accidental(key: str | None) -> Accidental | None:
    """Vorzeichen-Präferenz (# oder b) für eine Tonart nach Quintenzirkel.

    Gibt None zurück, wenn keine Tonart angegeben oder unbekannt ist - der
    Aufrufer soll dann auf die ursprüngliche Schreibweise des Akkords
    zurückfallen.
    """
    if not key:
        return None
    key = key.strip()
    key = MINOR_TO_RELATIVE_MAJOR.get(key, key)
    if key in SHARP_MAJOR_KEYS:
        return "sharp"
    if key in FLAT_MAJOR_KEYS:
        return "flat"
    return None


def _transpose_note(note: str, semitones: int, prefer: Accidental | None) -> str:
    semitone = (NOTE_TO_SEMITONE[note] + semitones) % 12
    if prefer is None:
        prefer = "flat" if "b" in note else "sharp"
    table = SEMITONE_TO_FLAT if prefer == "flat" else SEMITONE_TO_SHARP
    return table[semitone]


def transpose_key(key: str, semitones: int) -> str | None:
    """Transponiert eine Tonart-Angabe (z.B. "G" oder "Am") um n Halbtöne.

    Gibt None zurück, wenn `key` keine erkennbare Notenbezeichnung ist - der
    Aufrufer soll dann keinen Tonart-Indikator anzeigen.
    """
    key = key.strip()
    root, suffix = (key[:-1], "m") if key.endswith("m") else (key, "")
    if root not in NOTE_TO_SEMITONE:
        return None
    prefer = preferred_accidental(key)
    return f"{_transpose_note(root, semitones, prefer)}{suffix}"


def transpose_chord_str(raw: str, semitones: int, prefer: Accidental | None = None) -> str:
    """Transponiert einen einzelnen Akkordstring um n Halbtöne.

    Strings, die nicht wie ein Akkord aussehen (z.B. "" bei reinen Text-Boxen),
    werden unverändert zurückgegeben.
    """
    chord = parse_chord(raw)
    if chord is None:
        return raw
    chord.root = _transpose_note(chord.root, semitones, prefer)
    if chord.bass is not None:
        chord.bass = _transpose_note(chord.bass, semitones, prefer)
    return str(chord)
