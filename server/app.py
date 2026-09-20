import json
import os
import re
import secrets
import sqlite3
import subprocess
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

import bcrypt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

import transformer.grammar as grammar
from transformer.renderer import LaTeXRenderer
from transformer.style import Style
from transformer.transformer import Book, CordaTransformer, MetaCategory

app = FastAPI()

STYLE_PATH = "style.xml"

# Persistenter Ordner fuer DB + Session-Key.
# Im Container wird das auf ein Docker-Volume gemountet (siehe docker-compose.yml).
DATA_DIR = Path(os.environ.get("CORDA_DATA_DIR", "input"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "app.db"


def get_or_create_secret_key() -> str:
    """SECRET_KEY aus Env, sonst dauerhaft im Datenordner abgelegt (uebersteht Neustarts)."""
    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key
    key_path = DATA_DIR / ".secret_key"
    if key_path.is_file():
        return key_path.read_text(encoding="utf-8").strip()
    key = secrets.token_hex(32)
    key_path.write_text(key, encoding="utf-8")
    return key


# https_only=False, weil das Setup standardmaessig ueber HTTP laeuft (siehe docker-compose.yml).
# Bei Deployment hinter HTTPS-Reverse-Proxy sollte das auf True gesetzt werden.
app.add_middleware(SessionMiddleware, secret_key=get_or_create_secret_key(), same_site="lax", https_only=False)


def ensure_column(conn: sqlite3.Connection, table: str, column: str, coltype: str):
    """Fuegt eine Spalte nachtraeglich hinzu, falls sie in einer aelteren DB noch fehlt
    (SQLite kennt kein 'ADD COLUMN IF NOT EXISTS')."""
    existing = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL REFERENCES users(id),
                title TEXT NOT NULL,
                artist TEXT,
                content TEXT NOT NULL,
                published INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        ensure_column(conn, "songs", "subtitle", "TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL REFERENCES users(id),
                name TEXT NOT NULL,
                song_ids TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS votes (
                user_id INTEGER NOT NULL REFERENCES users(id),
                song_id INTEGER NOT NULL REFERENCES songs(id),
                value INTEGER NOT NULL,
                PRIMARY KEY (user_id, song_id)
            )
            """
        )


init_db()


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


USERNAME_RE = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")


def get_user_by_username(username: str) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def create_user(username: str, password: str) -> int:
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, password_hash, datetime.now(timezone.utc).isoformat()),
        )
        return cur.lastrowid


def current_user(request: Request) -> dict:
    user_id = request.session.get("user_id")
    user = get_user_by_id(user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(status_code=401, detail="nicht eingeloggt")
    return user


def extract_meta(page) -> tuple[str | None, str | None, str | None]:
    """(title, artist, subtitle) aus der title_section eines geparsten Page-AST."""
    title, artist, subtitle = None, None, None
    if page.title_section:
        for info in page.title_section.infos:
            if info.category == MetaCategory.title:
                title = info.text
            elif info.category == MetaCategory.artist:
                artist = info.text
            elif info.category == MetaCategory.subtitle:
                subtitle = info.text
    return title, artist, subtitle


def parse_song_content(content: str):
    """Wirft bei ungueltiger Grammatik; gibt sonst (page_ast, title, artist, subtitle) zurueck."""
    cst = grammar.cst(content, start="page")
    page = CordaTransformer().transform(cst)
    title, artist, subtitle = extract_meta(page)
    return page, (title or "Unbenannt"), artist, subtitle


def parse_error_response(e: Exception) -> JSONResponse:
    """Lark-Parse-Fehler (UnexpectedCharacters/UnexpectedToken) tragen line/column
    als echte Attribute - die geben wir mit, damit der Editor die Fehlerzeile
    markieren kann, statt sie aus dem Fehlertext zu parsen."""
    content = {"error": f"Parse-Fehler: {e}"}
    line = getattr(e, "line", None)
    column = getattr(e, "column", None)
    if isinstance(line, int) and isinstance(column, int):
        content["line"] = line
        content["column"] = column
    return JSONResponse(status_code=400, content=content)


def compile_pdf(ast: Book, timeout: int = 30, passes: int = 1) -> Response | JSONResponse:
    """Rendert ein Book-AST zu LaTeX und kompiliert es zu PDF.

    passes=2 ist noetig, damit ein Inhaltsverzeichnis (siehe LaTeXRenderer bei
    Mehr-Song-Buechern) korrekte Seitenzahlen zeigt: der erste Lauf schreibt die
    .toc-Datei, erst der zweite Lauf liest sie fuer die Anzeige wieder ein.
    """
    style = Style.from_xml(STYLE_PATH)
    output = LaTeXRenderer(style).render_document(ast)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        tex_path = tmp / "output.tex"
        tex_path.write_text(output, encoding="utf-8")

        try:
            for _ in range(passes):
                subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "output.tex"],
                    cwd=tmpdir,
                    check=True,
                    capture_output=True,
                    timeout=timeout,
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


# ---------- Auth ----------

class AuthRequest(BaseModel):
    username: str
    password: str


@app.post("/api/register")
def register(req: AuthRequest, request: Request):
    if not USERNAME_RE.match(req.username):
        return JSONResponse(
            status_code=400,
            content={"error": "Username: 3-32 Zeichen, nur Buchstaben/Zahlen/-/_"},
        )
    if len(req.password) < 6:
        return JSONResponse(status_code=400, content={"error": "Passwort muss mind. 6 Zeichen haben"})
    if get_user_by_username(req.username):
        return JSONResponse(status_code=409, content={"error": "Username bereits vergeben"})

    user_id = create_user(req.username, req.password)
    request.session["user_id"] = user_id
    return {"username": req.username}


@app.post("/api/login")
def login(req: AuthRequest, request: Request):
    user = get_user_by_username(req.username)
    if not user or not bcrypt.checkpw(req.password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        return JSONResponse(status_code=401, content={"error": "Username oder Passwort falsch"})
    request.session["user_id"] = user["id"]
    return {"username": user["username"]}


@app.post("/api/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@app.get("/api/me")
def me(user: dict = Depends(current_user)):
    return {"username": user["username"]}


# ---------- Ad-hoc Preview (Editor, nicht persistiert) ----------

class RenderRequest(BaseModel):
    content: str


@app.post("/api/render")
def render(req: RenderRequest, user: dict = Depends(current_user)):
    try:
        page, _, _, _ = parse_song_content(req.content)
    except Exception as e:
        return parse_error_response(e)

    return compile_pdf(Book(pages=[page]))


# ---------- Eigene Songs (privat, mit Publish-Status) ----------

def song_summary(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "artist": row["artist"],
        "subtitle": row["subtitle"],
        "published": bool(row["published"]),
        "updated_at": row["updated_at"],
    }


@app.get("/api/my-songs")
def list_my_songs(user: dict = Depends(current_user)):
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM songs WHERE owner_id = ? ORDER BY updated_at DESC",
            (user["id"],),
        ).fetchall()
    return [song_summary(r) for r in rows]


@app.get("/api/my-songs/{song_id}")
def get_my_song(song_id: int, user: dict = Depends(current_user)):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM songs WHERE id = ? AND owner_id = ?", (song_id, user["id"])
        ).fetchone()
    if not row:
        return JSONResponse(status_code=404, content={"error": "nicht gefunden"})
    return {**song_summary(row), "content": row["content"]}


class SongContentRequest(BaseModel):
    content: str


@app.post("/api/my-songs")
def create_song(req: SongContentRequest, user: dict = Depends(current_user)):
    try:
        _, title, artist, subtitle = parse_song_content(req.content)
    except Exception as e:
        return parse_error_response(e)

    now = datetime.now(timezone.utc).isoformat()
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO songs (owner_id, title, artist, subtitle, content, published, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 0, ?, ?)",
            (user["id"], title, artist, subtitle, req.content, now, now),
        )
        song_id = cur.lastrowid
    return {"id": song_id, "title": title, "artist": artist, "subtitle": subtitle, "published": False}


@app.put("/api/my-songs/{song_id}")
def update_song(song_id: int, req: SongContentRequest, user: dict = Depends(current_user)):
    try:
        _, title, artist, subtitle = parse_song_content(req.content)
    except Exception as e:
        return parse_error_response(e)

    with db() as conn:
        existing = conn.execute(
            "SELECT id FROM songs WHERE id = ? AND owner_id = ?", (song_id, user["id"])
        ).fetchone()
        if not existing:
            return JSONResponse(status_code=404, content={"error": "nicht gefunden"})
        conn.execute(
            "UPDATE songs SET title = ?, artist = ?, subtitle = ?, content = ?, updated_at = ? WHERE id = ?",
            (title, artist, subtitle, req.content, datetime.now(timezone.utc).isoformat(), song_id),
        )
    return {"id": song_id, "title": title, "artist": artist, "subtitle": subtitle}


def set_published(song_id: int, user: dict, published: bool):
    with db() as conn:
        cur = conn.execute(
            "UPDATE songs SET published = ? WHERE id = ? AND owner_id = ?",
            (1 if published else 0, song_id, user["id"]),
        )
        if cur.rowcount == 0:
            return JSONResponse(status_code=404, content={"error": "nicht gefunden"})
    return {"id": song_id, "published": published}


@app.post("/api/my-songs/{song_id}/publish")
def publish_song(song_id: int, user: dict = Depends(current_user)):
    return set_published(song_id, user, True)


@app.post("/api/my-songs/{song_id}/unpublish")
def unpublish_song(song_id: int, user: dict = Depends(current_user)):
    return set_published(song_id, user, False)


# ---------- Score: Upvotes/Downvotes + Liederbuch-Speicherungen ----------
# score = upvotes - downvotes + (Anzahl Liederbuecher ANDERER User, die den Song
# enthalten) * 3. Speicherungen durchs eigene Konto zaehlen bewusst nicht mit,
# sonst koennte man sich per eigenem Liederbuch selbst hochpushen.

def compute_scores(conn: sqlite3.Connection, songs: list[sqlite3.Row], user_id: int) -> dict[int, dict]:
    song_ids = [row["id"] for row in songs]
    if not song_ids:
        return {}
    owner_of = {row["id"]: row["owner_id"] for row in songs}
    placeholders = ",".join("?" * len(song_ids))

    vote_rows = conn.execute(
        f"""
        SELECT song_id,
               SUM(CASE WHEN value = 1 THEN 1 ELSE 0 END) AS up,
               SUM(CASE WHEN value = -1 THEN 1 ELSE 0 END) AS down
        FROM votes WHERE song_id IN ({placeholders}) GROUP BY song_id
        """,
        song_ids,
    ).fetchall()
    vote_map = {r["song_id"]: (r["up"], r["down"]) for r in vote_rows}

    my_vote_rows = conn.execute(
        f"SELECT song_id, value FROM votes WHERE user_id = ? AND song_id IN ({placeholders})",
        [user_id, *song_ids],
    ).fetchall()
    my_vote_map = {r["song_id"]: r["value"] for r in my_vote_rows}

    saves = {sid: 0 for sid in song_ids}
    for book in conn.execute("SELECT owner_id, song_ids FROM books").fetchall():
        for sid in json.loads(book["song_ids"]):
            if sid in saves and book["owner_id"] != owner_of[sid]:
                saves[sid] += 1

    result = {}
    for sid in song_ids:
        up, down = vote_map.get(sid, (0, 0))
        result[sid] = {
            "upvotes": up,
            "downvotes": down,
            "book_saves": saves[sid],
            "score": up - down + saves[sid] * 3,
            "my_vote": my_vote_map.get(sid, 0),
        }
    return result


class VoteRequest(BaseModel):
    value: int  # 1 (upvote) oder -1 (downvote)


@app.post("/api/songs/{song_id}/vote")
def vote_song(song_id: int, req: VoteRequest, user: dict = Depends(current_user)):
    if req.value not in (1, -1):
        return JSONResponse(status_code=400, content={"error": "value muss 1 oder -1 sein"})

    with db() as conn:
        song = conn.execute("SELECT * FROM songs WHERE id = ?", (song_id,)).fetchone()
        if not song:
            return JSONResponse(status_code=404, content={"error": "nicht gefunden"})

        existing = conn.execute(
            "SELECT value FROM votes WHERE user_id = ? AND song_id = ?", (user["id"], song_id)
        ).fetchone()
        if existing and existing["value"] == req.value:
            # nochmal derselbe Button -> Vote zurueckziehen
            conn.execute("DELETE FROM votes WHERE user_id = ? AND song_id = ?", (user["id"], song_id))
        else:
            conn.execute(
                "INSERT INTO votes (user_id, song_id, value) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id, song_id) DO UPDATE SET value = excluded.value",
                (user["id"], song_id, req.value),
            )

        scores = compute_scores(conn, [song], user["id"])
    return {"song_id": song_id, **scores[song_id]}


# ---------- Oeffentliche Songs (Browse-Homepage) ----------
# Gruppiert nach (title, artist), damit nicht jede Version einzeln in der Suche
# auftaucht - Versionen desselben Songs sieht man ueber /api/song-versions.
# Sortiert nach Relevanz = Score der hoechstplatzierten Version der Gruppe.
# Ohne Suchbegriff werden nur die Top 20 geladen; mit Suchbegriff wird der
# gesamte veroeffentlichte Katalog durchsucht (kein Limit), da sonst Treffer
# ausserhalb der ersten 20 unauffindbar waeren.

PUBLIC_SONGS_LIMIT = 20


@app.get("/api/public-songs")
def list_public_songs(q: str | None = None, user: dict = Depends(current_user)):
    q = (q or "").strip()
    with db() as conn:
        if q:
            like = f"%{q}%"
            rows = conn.execute(
                "SELECT * FROM songs WHERE published = 1 AND (title LIKE ? OR artist LIKE ?)",
                (like, like),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM songs WHERE published = 1").fetchall()

        scores = compute_scores(conn, rows, user["id"])

    groups: dict[tuple[str, str | None], dict] = {}
    for row in rows:
        key = (row["title"], row["artist"])
        score = scores[row["id"]]["score"]
        group = groups.get(key)
        if group is None:
            groups[key] = {"title": row["title"], "artist": row["artist"], "version_count": 1, "score": score}
        else:
            group["version_count"] += 1
            group["score"] = max(group["score"], score)

    result = sorted(groups.values(), key=lambda g: g["score"], reverse=True)
    if not q:
        result = result[:PUBLIC_SONGS_LIMIT]
    return result


@app.get("/api/song-versions")
def song_versions(title: str, artist: str | None = None, user: dict = Depends(current_user)):
    artist = artist or None  # leerer String wie "kein Artist" behandeln
    with db() as conn:
        rows = conn.execute(
            """
            SELECT songs.*, users.username AS owner_username
            FROM songs JOIN users ON users.id = songs.owner_id
            WHERE songs.published = 1 AND songs.title = ?
              AND ((songs.artist IS NULL AND ? IS NULL) OR songs.artist = ?)
            """,
            (title, artist, artist),
        ).fetchall()
        scores = compute_scores(conn, rows, user["id"])

    versions = [
        {**song_summary(r), "owner": r["owner_username"], "is_mine": r["owner_id"] == user["id"], **scores[r["id"]]}
        for r in rows
    ]
    versions.sort(key=lambda v: v["score"], reverse=True)
    return versions


@app.post("/api/songs/{song_id}/fork")
def fork_song(song_id: int, user: dict = Depends(current_user)):
    """Kopiert einen fuer den User sichtbaren Song (veroeffentlicht oder eigen) als
    neuen, unveroeffentlichten Song in seine eigenen Songs - zum Bearbeiten einer
    fremden Version, ohne das Original zu veraendern."""
    now = datetime.now(timezone.utc).isoformat()
    with db() as conn:
        row = conn.execute("SELECT * FROM songs WHERE id = ?", (song_id,)).fetchone()
        if not row or not (row["published"] or row["owner_id"] == user["id"]):
            return JSONResponse(status_code=404, content={"error": "nicht gefunden"})
        cur = conn.execute(
            "INSERT INTO songs (owner_id, title, artist, subtitle, content, published, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 0, ?, ?)",
            (user["id"], row["title"], row["artist"], row["subtitle"], row["content"], now, now),
        )
        new_id = cur.lastrowid
    return {"id": new_id}


# ---------- Liederbuch-Rendering: aus oeffentlichen + eigenen Songs zusammengestellt ----------

def render_song_ids(song_ids: list[int], user: dict) -> Response | JSONResponse:
    pages = []
    skipped = []
    with db() as conn:
        for song_id in song_ids:
            row = conn.execute("SELECT * FROM songs WHERE id = ?", (song_id,)).fetchone()
            # Zugriff erlaubt, wenn veroeffentlicht ODER eigener Song (auch unveroeffentlicht)
            if not row or not (row["published"] or row["owner_id"] == user["id"]):
                skipped.append(song_id)
                continue
            try:
                cst = grammar.cst(row["content"], start="page")
                pages.append(CordaTransformer().transform(cst))
            except Exception:
                traceback.print_exc()
                skipped.append(song_id)

    if not pages:
        return JSONResponse(status_code=400, content={"error": "Keine der ausgewaehlten Songs konnte gerendert werden."})

    # passes=2 fuer korrekte Seitenzahlen im Inhaltsverzeichnis (siehe compile_pdf)
    result = compile_pdf(Book(pages=pages), timeout=120, passes=2)
    if not isinstance(result, JSONResponse) and skipped:
        result.headers["X-Skipped-Songs"] = json.dumps(skipped)
    return result


class RenderBookRequest(BaseModel):
    song_ids: list[int]  # Reihenfolge = Reihenfolge im Buch, Ad-hoc (nicht persistiert)


@app.post("/api/render-book")
def render_book(req: RenderBookRequest, user: dict = Depends(current_user)):
    return render_song_ids(req.song_ids, user)


# ---------- Liederbuecher (persistiert, mehrere pro User, eigener Name) ----------

def resolve_book_songs(conn: sqlite3.Connection, song_ids: list[int], user: dict) -> list[dict]:
    resolved = []
    for song_id in song_ids:
        row = conn.execute("SELECT * FROM songs WHERE id = ?", (song_id,)).fetchone()
        accessible = row and (row["published"] or row["owner_id"] == user["id"])
        if accessible:
            resolved.append({"id": song_id, "title": row["title"], "artist": row["artist"], "available": True})
        else:
            # Song wurde geloescht oder vom Besitzer zurueckgezogen -> sichtbar bleiben lassen (entfernbar),
            # statt kommentarlos aus der Liste zu verschwinden.
            resolved.append({"id": song_id, "title": None, "artist": None, "available": False})
    return resolved


def book_summary(row: sqlite3.Row) -> dict:
    song_ids = json.loads(row["song_ids"])
    return {
        "id": row["id"],
        "name": row["name"],
        "song_ids": song_ids,
        "song_count": len(song_ids),
        "updated_at": row["updated_at"],
    }


@app.get("/api/books")
def list_books(user: dict = Depends(current_user)):
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM books WHERE owner_id = ? ORDER BY updated_at DESC", (user["id"],)
        ).fetchall()
    return [book_summary(r) for r in rows]


@app.get("/api/books/{book_id}")
def get_book(book_id: int, user: dict = Depends(current_user)):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM books WHERE id = ? AND owner_id = ?", (book_id, user["id"])
        ).fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "nicht gefunden"})
        songs = resolve_book_songs(conn, json.loads(row["song_ids"]), user)
    return {"id": row["id"], "name": row["name"], "songs": songs}


class CreateBookRequest(BaseModel):
    name: str


@app.post("/api/books")
def create_book(req: CreateBookRequest, user: dict = Depends(current_user)):
    name = req.name.strip() or "Neues Liederbuch"
    now = datetime.now(timezone.utc).isoformat()
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO books (owner_id, name, song_ids, created_at, updated_at) VALUES (?, ?, '[]', ?, ?)",
            (user["id"], name, now, now),
        )
        book_id = cur.lastrowid
    return {"id": book_id, "name": name, "songs": []}


class UpdateBookRequest(BaseModel):
    name: str | None = None
    song_ids: list[int] | None = None


@app.put("/api/books/{book_id}")
def update_book(book_id: int, req: UpdateBookRequest, user: dict = Depends(current_user)):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM books WHERE id = ? AND owner_id = ?", (book_id, user["id"])
        ).fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "nicht gefunden"})

        name = req.name.strip() if (req.name is not None and req.name.strip()) else row["name"]
        song_ids_json = json.dumps(req.song_ids) if req.song_ids is not None else row["song_ids"]

        conn.execute(
            "UPDATE books SET name = ?, song_ids = ?, updated_at = ? WHERE id = ?",
            (name, song_ids_json, datetime.now(timezone.utc).isoformat(), book_id),
        )
        songs = resolve_book_songs(conn, json.loads(song_ids_json), user)
    return {"id": book_id, "name": name, "songs": songs}


@app.delete("/api/books/{book_id}")
def delete_book(book_id: int, user: dict = Depends(current_user)):
    with db() as conn:
        cur = conn.execute("DELETE FROM books WHERE id = ? AND owner_id = ?", (book_id, user["id"]))
        if cur.rowcount == 0:
            return JSONResponse(status_code=404, content={"error": "nicht gefunden"})
    return {"ok": True}


@app.post("/api/books/{book_id}/render")
def render_book_by_id(book_id: int, user: dict = Depends(current_user)):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM books WHERE id = ? AND owner_id = ?", (book_id, user["id"])
        ).fetchone()
        if not row:
            return JSONResponse(status_code=404, content={"error": "nicht gefunden"})
        song_ids = json.loads(row["song_ids"])
    return render_song_ids(song_ids, user)


app.mount("/", StaticFiles(directory="server/static", html=True), name="static")
