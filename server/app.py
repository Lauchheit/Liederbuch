import os
import re
import subprocess
import tempfile
import traceback
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import transformer.grammar as grammar
from transformer.renderer import LaTeXRenderer
from transformer.style import Style
from transformer.transformer import Book, CordaTransformer, MetaCategory

app = FastAPI()

STYLE_PATH = "style.xml"

# Persistenter Ordner fuer hochgeladene/gespeicherte .corda-Dateien.
# Im Container wird das auf ein Docker-Volume gemountet (siehe docker-compose.yml).
DATA_DIR = Path(os.environ.get("CORDA_DATA_DIR", "input"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


def safe_filename(name: str) -> str:
    """Nur der Basename wird verwendet (kein Path-Traversal), muss auf .corda enden."""
    name = Path(name).name
    if not name.endswith(".corda") or name == ".corda":
        raise ValueError("ungueltiger Dateiname")
    return name


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "song"


def extract_meta(page) -> tuple[str, str | None]:
    """(title, artist) aus der title_section eines geparsten Page-AST, mit Fallback."""
    title, artist = None, None
    if page.title_section:
        for info in page.title_section.infos:
            if info.category == MetaCategory.title:
                title = info.text
            elif info.category == MetaCategory.artist:
                artist = info.text
    return title, artist


class RenderRequest(BaseModel):
    content: str


@app.post("/api/render")
def render(req: RenderRequest):
    try:
        cst = grammar.cst(req.content, start="page")
        page = CordaTransformer().transform(cst)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Parse-Fehler: {e}"})

    ast = Book(pages=[page])
    style = Style.from_xml(STYLE_PATH)
    output = LaTeXRenderer(style).render_document(ast)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        tex_path = tmp / "output.tex"
        tex_path.write_text(output, encoding="utf-8")

        try:
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "output.tex"],
                cwd=tmpdir,
                check=True,
                capture_output=True,
                timeout=30,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            log = getattr(e, "stdout", b"") or b""
            traceback.print_exc()
            return JSONResponse(
                status_code=400,
                content={"error": "pdflatex-Fehler", "log": log.decode("utf-8", "ignore")[-4000:]},
            )

        pdf_bytes = (tmp / "output.pdf").read_bytes()
        return Response(content=pdf_bytes, media_type="application/pdf")


@app.get("/api/songs")
def list_songs():
    songs = []
    for path in sorted(DATA_DIR.glob("*.corda")):
        title, artist = path.stem, None
        try:
            content = path.read_text(encoding="utf-8")
            cst = grammar.cst(content, start="page")
            page = CordaTransformer().transform(cst)
            parsed_title, artist = extract_meta(page)
            if parsed_title:
                title = parsed_title
        except Exception:
            pass  # Datei trotzdem auflisten, nur ohne Metadaten
        songs.append({"filename": path.name, "title": title, "artist": artist})
    return songs


@app.get("/api/songs/{filename}")
def get_song(filename: str):
    try:
        path = DATA_DIR / safe_filename(filename)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "ungueltiger Dateiname"})
    if not path.is_file():
        return JSONResponse(status_code=404, content={"error": "nicht gefunden"})
    return {"filename": path.name, "content": path.read_text(encoding="utf-8")}


class SaveRequest(BaseModel):
    content: str
    filename: str | None = None  # gesetzt = bestehende Datei ueberschreiben, sonst neu anlegen


@app.post("/api/songs")
def save_song(req: SaveRequest):
    try:
        cst = grammar.cst(req.content, start="page")
        page = CordaTransformer().transform(cst)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Parse-Fehler: {e}"})

    if req.filename:
        try:
            filename = safe_filename(req.filename)
        except ValueError:
            return JSONResponse(status_code=400, content={"error": "ungueltiger Dateiname"})
    else:
        title, _ = extract_meta(page)
        base = slugify(title or "song")
        filename = f"{base}.corda"
        i = 2
        while (DATA_DIR / filename).exists():
            filename = f"{base}-{i}.corda"
            i += 1

    (DATA_DIR / filename).write_text(req.content, encoding="utf-8")
    return {"filename": filename}


app.mount("/", StaticFiles(directory="server/static", html=True), name="static")
