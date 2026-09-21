# Liederbuch

Ein Tool, das Songtexte mit Akkord-Annotationen (eigenes `.corda`-Format) in ein
zweispaltiges PDF-Liederbuch rendert. Pipeline: `.corda`-Dateien
→ Lark-Grammatik (CST) → Transformer (AST) → LaTeX-Renderer → `pdflatex`.

Es gibt zwei Wege, die Pipeline zu nutzen:

- **CLI** (`main.py`): liest `.corda`-Dateien aus `input/`, baut ein einzelnes
  PDF. Siehe [Verwendung](#verwendung) unten.
- **Web-App** (`server/`): Mehrbenutzer-FastAPI-App mit Editor, Live-Vorschau,
  Songverwaltung, Versionierung und Liederbüchern. Siehe
  [Web-App](#web-app-server).

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

## Web-App (`server/`)

Eine FastAPI-App über derselben Pipeline (`transformer/*`), die statt einer
einzelnen `input/`-basierten CLI-Ausführung ein Mehrbenutzer-Web-Frontend
bietet: Songs anlegen/bearbeiten mit Live-Vorschau, veröffentlichen,
Versionen/Forks, Up-/Downvotes, Liederbücher zusammenstellen und als PDF
rendern.

### Starten

```bash
docker compose up -d --build
```

Öffnet auf `http://localhost:8000`. Der Container installiert `pdflatex`
selbst (`texlive-latex-base`, `texlive-latex-extra`,
`texlive-fonts-recommended` im [`server/dockerfile`](server/dockerfile)) -
im Gegensatz zur CLI muss dafür lokal nichts eingerichtet werden.

Ohne Docker lokal starten (z.B. für schnellere Iteration, benötigt lokal
installiertes `pdflatex`):

```bash
pip install -r requirements.txt
uvicorn server.app:app --reload
```

### Seiten

Statisch ausgeliefert aus `server/static/`, gemeinsame Logik (Auth-Overlay,
Top-Nav, Liederbuch-Widget, "Zu Liederbuch hinzufügen"-Popover, PDF-Vollbild-
Vorschau) liegt in `common.js`/`common.css` und wird von jeder Seite geladen.

| Seite | Zweck |
|---|---|
| `index.html` | Songs durchstöbern: veröffentlichte Songs, gruppiert nach (Titel, Artist), sortiert nach Score der besten Version. Ohne Suche nur Top 20, Suche durchsucht serverseitig den ganzen Katalog. |
| `my-songs.html` | Eigene Songs (Entwürfe + eigene veröffentlichte), bearbeiten/veröffentlichen/importieren. |
| `editor.html` | Live-Editor: Textarea mit Zeilennummern-Gutter links, gerenderte PDF-Vorschau rechts (debounced, 600ms). Bei Parse-Fehlern wird die betroffene Zeile im Gutter rot markiert (`line`/`column` aus der Lark-Exception). |
| `versions.html` | Alle Versionen eines Songs (gleicher Titel+Artist), sortiert nach Score, mit Vote-Buttons. |
| `howto.html` | Einfache Nutzer-Anleitung (verlinkt als "Hilfe" in der Top-Nav). |

### API-Endpunkte (`server/app.py`)

Alle Endpunkte außer `/api/register` und `/api/login` verlangen eine gültige
Session (Cookie, siehe Persistenz unten) - ohne liefern sie `401`.

| Endpunkt | Zweck |
|---|---|
| `POST /api/register`, `/api/login`, `/api/logout`, `GET /api/me` | Auth. |
| `POST /api/render` | Ad-hoc-Vorschau eines rohen `.corda`-Texts (Editor-Live-Preview), nicht persistiert. |
| `GET/POST /api/my-songs`, `GET/PUT /api/my-songs/{id}` | Eigene Songs auflisten/anlegen/lesen/bearbeiten. |
| `POST /api/my-songs/{id}/publish` bzw. `/unpublish` | Sichtbarkeit umschalten. |
| `GET /api/public-songs?q=` | Veröffentlichte Songs gruppiert, nach Score sortiert (Top 20 ohne `q`). |
| `GET /api/song-versions?title=&artist=` | Alle Versionen einer Song-Familie inkl. Score, sortiert. |
| `POST /api/songs/{id}/fork` | Kopiert eine fremde (veröffentlichte) Version als eigenen Entwurf. |
| `POST /api/songs/{id}/vote` | Up-/Downvote, Toggle bei erneutem Klick auf denselben Wert. |
| `POST /api/render-book` | Rendert eine Ad-hoc-Liste von `song_ids` zu einem PDF (mit Inhaltsverzeichnis bei >1 Song). |
| `GET/POST /api/books`, `GET/PUT/DELETE /api/books/{id}`, `POST /api/books/{id}/render` | Persistierte, benannte Liederbücher. |

### Persistenzschicht

Kein externer DB-Server - alles liegt in einer einzigen **SQLite-Datei** plus
ein paar Nebendateien in einem Datenordner, der per Docker-Volume persistiert
wird (siehe [`docker-compose.yml`](docker-compose.yml), Volume `corda-songs`
→ `/app/input` im Container). Pfad konfigurierbar über die Env-Variable
`CORDA_DATA_DIR` (Default `input`).

```
<CORDA_DATA_DIR>/
  app.db          SQLite-DB (siehe Schema unten)
  .secret_key     Session-Signierschlüssel, s.u.
```

**`app.db`-Schema** (angelegt/migriert beim Start in `init_db()`):

| Tabelle | Felder | Zweck |
|---|---|---|
| `users` | `id, username (unique), password_hash (bcrypt), created_at` | Accounts. |
| `songs` | `id, owner_id, title, artist, subtitle, content (.corda-Text), published, created_at, updated_at` | Ein Datensatz pro Song-*Version*. `title`/`artist`/`subtitle` sind beim Speichern aus `content` geparste Kopien (fürs schnelle Auflisten/Gruppieren, ohne jedes Mal neu zu parsen). |
| `books` | `id, owner_id, name, song_ids (JSON-Array), created_at, updated_at` | Ein Liederbuch = benannte, geordnete Liste von `song.id`s. Kein Join-Table - bewusst einfach gehalten, siehe unten. |
| `votes` | `user_id, song_id, value (1/-1)`, PK `(user_id, song_id)` | Ein Vote pro User+Song, erzwungen durch den Primary Key. |

Schema-Änderungen an bestehenden Spalten laufen über `ensure_column()`
(`ALTER TABLE ... ADD COLUMN`, da SQLite kein `ADD COLUMN IF NOT EXISTS`
kennt) statt über ein Migrationstool - für den Umfang des Projekts bewusst
minimal gehalten.

**Wichtige Designentscheidungen:**

- **Songs sind nicht in Dateien** (anders als bei der CLI/`input/`) -
  jede Version liegt als Zeile in `songs`. "Versionen" eines Songs sind
  schlicht alle Zeilen mit gleichem `title`+`artist` (exakter String-Vergleich,
  kein Fuzzy-Matching).
- **Liederbuch-Mitgliedschaft** liegt als JSON-Array direkt in der `books`-Zeile
  statt in einer normalisierten Zwischentabelle - bei der erwarteten
  Datenmenge (private Liederbücher weniger Nutzer) unproblematisch und
  spart einen Join bei jedem Request. `resolve_book_songs()` löst die IDs bei
  Bedarf gegen `songs` auf und markiert nicht mehr verfügbare Songs
  (gelöscht/zurückgezogen) statt sie kommentarlos verschwinden zu lassen.
- **Score** (`compute_scores()` in `server/app.py`) = `upvotes - downvotes +
  3 × Anzahl Liederbücher anderer User, die die Version enthalten`. Bewusst
  nur *anderer* User, sonst könnte man sich durch eigene Liederbücher selbst
  hochstimmen.
- **Session-Handling**: `starlette.middleware.sessions.SessionMiddleware`
  (signiertes Cookie, keine Server-Session-Tabelle). Der Signierschlüssel wird
  beim ersten Start zufällig erzeugt und nach `<CORDA_DATA_DIR>/.secret_key`
  geschrieben (übersteht dadurch Container-Neustarts); alternativ per
  `SECRET_KEY`-Env-Variable fix vorgeben (z.B. für mehrere Replicas hinter
  einem Load-Balancer). `https_only=False` passend zum aktuellen
  HTTP-Setup - hinter einem HTTPS-Reverse-Proxy sollte das auf `True`.
- **PDF-Kompilierung** läuft nie gegen echte Dateien im Projektverzeichnis,
  sondern in einem `tempfile.TemporaryDirectory()` pro Request
  (`compile_pdf()`), das PDF wird als Bytes zurückgegeben statt als Datei
  referenziert - kein Cleanup-Risiko, keine Kollisionen zwischen parallelen
  Requests.

### Projektstruktur (Web-App-Teil)

```
server/app.py                FastAPI-App: Auth, Songs, Buecher, Votes, PDF-Rendering
server/dockerfile            Python + pdflatex (texlive)
server/static/*.html         Seiten (siehe Tabelle oben)
server/static/common.js      Auth-Overlay, Top-Nav, Liederbuch-Widget, PDF-Overlay
server/static/common.css     Gemeinsames Styling (CSS-Variablen in :root)
docker-compose.yml           Service + benanntes Volume fuer den Datenordner
requirements.txt             lark, fastapi, uvicorn, bcrypt, itsdangerous
```

## Projektstruktur (CLI-Teil)

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
