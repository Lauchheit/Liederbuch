# Liederbuch

Ein Tool, das Songtexte mit Akkord-Annotationen (eigenes `.corda`-Format) in ein
zweispaltiges PDF-Liederbuch rendert. Pipeline: `.corda`-Dateien in `input/`
→ Lark-Grammatik (CST) → Transformer (AST) → LaTeX-Renderer → `pdflatex`.

## Verwendung

```bash
python main.py
```

Liest alle `*.corda`-Dateien aus `input/` (jede Datei = ein Song), rendert sie
in `output.tex` und kompiliert das per `pdflatex` zu `output.pdf`. Eine Datei,
die nicht geparst werden kann, wird mit einer Warnung übersprungen - der Rest
des Liederbuchs wird trotzdem gebaut.

`pdflatex` muss im `PATH` liegen (z.B. via MiKTeX). Benötigte LaTeX-Pakete:
`xcolor`, `multicol`, `geometry`.

## Das `.corda`-Format

Ein Song besteht aus einem optionalen Metadaten-Block, gefolgt von einer oder
mehreren Strophen. Akkorde stehen in `{geschweiften Klammern}` direkt vor der
Silbe, auf die sie fallen.

```
---
Title: As The World Caves In
Artist: Matt Maltese
---

[Verse 1]
My {B}feet are aching
And your {Eb}back is pretty tired

[Chorus]
{Eb7}you that I {Ebm6}lie with
As the {B}atom bomb {D7}locks in
```

Mehrere Songs lassen sich auch in einer einzigen Datei trennen (statt auf
mehrere `.corda`-Dateien in `input/` aufzuteilen):

```
...letzte Zeile von Song 1

%NEW_SONG%

---
Title: Nächster Song
---
[Verse 1]
...
```

### Grammatik-Bausteine (`transformer/grammar.py`)

| Regel | Bedeutung |
|---|---|
| `book` | Eine ganze `.corda`-Datei: eine oder mehrere `page`s, getrennt durch `%NEW_SONG%`. |
| `page` | Ein Song: optionaler `title_section`-Block + eine oder mehrere `paragraph`s. |
| `title_section` | Metadaten-Block, eingerahmt von `---`-Zeilen (siehe unten). |
| `paragraph` | Eine Strophe: optionaler `[Kommentar]` als erste Zeile, danach beliebig viele `line`s. Ein Kommentar ganz ohne folgende Zeilen (z.B. reine Instrumental-Marker wie `[Solo]`) ist ebenfalls erlaubt. |
| `line` | Eine Zeile aus durch Leerzeichen getrennten `word`s. |
| `word` | Text, optional mit einem oder mehreren Akkorden davor/dazwischen/danach. |
| `chord_run` | Ein `{Akkord}` mit optional direkt folgendem Text (kein Leerzeichen dazwischen). |

**Wichtige Regeln/Grenzfälle:**

- Ein Zeilenumbruch am Dateiende ist erlaubt und wird ignoriert.
- Erlaubte Zeichen für Text/Akkordnamen: alles außer `{`, `}`, `[`, `]` und
  Whitespace (Blacklist statt Whitelist - jedes Unicode-Zeichen, jedes
  Sonderzeichen in Akkordnamen wie `D#`, `Gm/F`, `C7` funktioniert automatisch).
- Text (Songtitel, Kommentare, Lyrics) wird beim Rendern automatisch für LaTeX
  escaped (`#`, `%`, `&`, `_`, `~`, `^`, `$`, `\`, `{`, `}`) - im `.corda` selbst
  muss nichts escaped werden.
- Eine Zeile ganz ohne Akkorde wird kompakter gerendert (ohne die für die
  Akkordzeile reservierte Höhe) - lohnt sich z.B. wenn man Akkorde bewusst
  weglässt, um Platz zu sparen.

### Metadaten-Block (`title_section`)

```
---
Title: <Songtitel>
Artist: <Interpret/Komponist>
Subtitle: <optional>
Instruction: <optional, z.B. Spielanweisung>
---
```

Alle vier Felder sind optional und beliebig oft/selten vorhanden. Jede
Kategorie hat ihr eigenes Aussehen (siehe `style.xml`) und wird beim Rendern
zu einem eigenen LaTeX-Befehl (`\metaTitle`, `\metaArtist`, ...).

**Neue Kategorie hinzufügen** (z.B. `Composer`):
1. Enum-Wert in `MetaCategory` (`transformer/transformer.py`) ergänzen.
2. Keyword in `META_CATEGORY_KEYWORD` (`transformer/grammar.py`) ergänzen.
3. Default-Aussehen in `default_meta_styles()` (`transformer/style.py`) ergänzen.
4. Optional: `<category name="composer" .../>` in `style.xml`.

Renderer und LaTeX-Erzeugung greifen danach automatisch darauf zu, ohne
weitere Codeänderungen.

## Style konfigurieren (`style.xml`)

Aussehen (Farben, Schriftgrößen, Abstände, Spaltenlayout, Seitenränder) wird
über `style.xml` im Projekt-Root gesteuert, siehe die Datei selbst für ein
vollständiges Beispiel. Die Python-Defaults in `transformer/style.py`
(`Style`-Dataclass) greifen für jedes Attribut, das in der XML fehlt oder
wenn die Datei gar nicht existiert - die XML muss also nie vollständig sein.

**Mapping:** Ein XML-Attribut `mein-attribut="..."` überschreibt das
gleichnamige `Style`-Feld `mein_attribut` (Bindestrich → Unterstrich). Welches
Element das Attribut umschließt, spielt für das Parsen keine Rolle - die
Gruppierung in `style.xml` (`<chord>`, `<lyric>`, `<spacing>`, ...) ist rein
zur besseren Lesbarkeit.

Wichtigste Felder:

| Feld | Bedeutung | Beispiel |
|---|---|---|
| `chord-color`, `chord-size`, `chord-bold` | Aussehen der Akkord-Beschriftung | `"2E86AB"`, `"small"`, `"true"` |
| `lyric-color`, `lyric-size`, `lyric-bold` | Aussehen des Liedtexts | |
| `title-color`, `title-size`, `title-bold`, `title-italic`, `title-smallcaps` | Aussehen des Strophenlabels (`[Verse 1]` etc.) | |
| `paragraph-skip`, `title-gap`, `chord-lyric-gap` | Abstände (LaTeX-Längen) | `"1.5em"`, `"2pt"` |
| `columns`, `column-sep`, `column-rule-width` | Spaltenlayout | `"2"`, `"1.8em"` |
| `margin-left/right/top/bottom` | Seitenränder | `"2.2cm"` |
| `<meta-styles><category name="..." .../></meta-styles>` | Aussehen pro Metadaten-Kategorie (siehe oben) | |

Größen-Werte müssen ein gültiger LaTeX-Größenbefehl ohne Backslash sein:
`tiny`, `scriptsize`, `footnotesize`, `small`, `normalsize`, `large`, `Large`,
`LARGE`, `huge`, `Huge` (siehe `FONT_SIZES` in `style.py`).

Farben sind Hex-Codes ohne `#`. Booleans akzeptieren `true`/`false` (auch
`1`/`0`, `yes`/`no`, `on`/`off`).

## Projektstruktur

```
main.py                    Einstiegspunkt: liest input/, parst, rendert, kompiliert
style.xml                  Style-Konfiguration (siehe oben)
input/*.corda               Ein Song pro Datei
latex/preambel.tex          Fixer LaTeX-Vorspann (\documentclass, Encoding)
latex/end.tex                \end{document}
transformer/grammar.py      Lark-Grammatik + cst()-Einstiegspunkt
transformer/transformer.py  AST-Dataclasses (Word, Line, Paragraph, Page, Book, ...) + CordaTransformer
transformer/style.py        Style-Dataclass, XML-Loading, LaTeX-Preamble-Erzeugung
transformer/renderer.py     AST → LaTeX (LaTeXRenderer)
```
