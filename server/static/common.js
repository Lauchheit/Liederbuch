// Gemeinsame Logik fuer alle drei Seiten (Home/Browse, Eigene Songs, Editor):
// Auth-Overlay + Top-Nav, API-Fetch-Wrapper mit 401-Handling, Liederbuch-Verwaltung.

const ACTIVE_BOOK_KEY = "corda-active-book";

// ---------- API-Helper ----------

async function apiFetch(url, opts) {
  const res = await fetch(url, opts);
  if (res.status === 401) {
    showAuthOverlay();
    throw new Error("unauthorized");
  }
  return res;
}

// ---------- Auth-Overlay + Top-Nav ----------

function injectChrome() {
  document.body.insertAdjacentHTML("afterbegin", `
    <div id="auth-overlay">
      <div id="auth-card">
        <h1>Corda Live-Editor</h1>
        <form id="login-form" class="auth-form">
          <input type="text" id="login-username" placeholder="Username" autocomplete="username" required>
          <input type="password" id="login-password" placeholder="Passwort" autocomplete="current-password" required>
          <button type="submit">Anmelden</button>
        </form>
        <form id="register-form" class="auth-form" style="display:none">
          <input type="text" id="register-username" placeholder="Username (3-32 Zeichen)" autocomplete="username" required>
          <input type="password" id="register-password" placeholder="Passwort (mind. 6 Zeichen)" autocomplete="new-password" required>
          <button type="submit">Konto erstellen</button>
        </form>
        <div id="auth-error"></div>
        <div id="auth-switch">
          <span id="switch-to-register">Noch kein Konto? <a>Registrieren</a></span>
          <span id="switch-to-login" style="display:none">Schon ein Konto? <a>Anmelden</a></span>
        </div>
      </div>
    </div>
    <div id="topnav">
      <div id="topnav-left">
        <a href="index.html">Songs durchstöbern</a>
        <a href="my-songs.html">Eigene Songs</a>
        <a href="editor.html" class="new-song-link">+ Neuer Song</a>
      </div>
      <div id="topnav-right">
        <a href="howto.html">Hilfe</a>
        <span id="current-username"></span>
        <button id="logout-btn">Abmelden</button>
      </div>
    </div>
  `);

  document.getElementById("login-form").addEventListener("submit", onLoginSubmit);
  document.getElementById("register-form").addEventListener("submit", onRegisterSubmit);
  document.getElementById("switch-to-register").addEventListener("click", (e) => {
    if (e.target.tagName !== "A") return;
    toggleAuthForm(true);
  });
  document.getElementById("switch-to-login").addEventListener("click", (e) => {
    if (e.target.tagName !== "A") return;
    toggleAuthForm(false);
  });
  document.getElementById("logout-btn").addEventListener("click", async () => {
    await fetch("/api/logout", { method: "POST" });
    localStorage.removeItem(ACTIVE_BOOK_KEY);
    location.reload();
  });
}

function toggleAuthForm(showRegister) {
  document.getElementById("login-form").style.display = showRegister ? "none" : "flex";
  document.getElementById("register-form").style.display = showRegister ? "flex" : "none";
  document.getElementById("switch-to-register").style.display = showRegister ? "none" : "inline";
  document.getElementById("switch-to-login").style.display = showRegister ? "inline" : "none";
  document.getElementById("auth-error").textContent = "";
}

async function onLoginSubmit(e) {
  e.preventDefault();
  const authError = document.getElementById("auth-error");
  authError.textContent = "";
  const res = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: document.getElementById("login-username").value,
      password: document.getElementById("login-password").value,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    authError.textContent = data.error || "Fehler";
    return;
  }
  onLoggedIn(data.username);
}

async function onRegisterSubmit(e) {
  e.preventDefault();
  const authError = document.getElementById("auth-error");
  authError.textContent = "";
  const res = await fetch("/api/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: document.getElementById("register-username").value,
      password: document.getElementById("register-password").value,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    authError.textContent = data.error || "Fehler";
    return;
  }
  onLoggedIn(data.username);
}

function showAuthOverlay() {
  document.getElementById("auth-overlay").style.display = "flex";
  document.getElementById("page-body").style.visibility = "hidden";
}

function hideAuthOverlay() {
  document.getElementById("auth-overlay").style.display = "none";
  document.getElementById("page-body").style.visibility = "visible";
}

let _onLoggedInCallback = null;

function onLoggedIn(username) {
  document.getElementById("current-username").textContent = username;
  hideAuthOverlay();
  if (_onLoggedInCallback) _onLoggedInCallback(username);
}

// Auf jeder Seite ganz unten aufrufen: initAuth(onReady), onReady(username) laeuft nach Login.
function initAuth(onReady) {
  injectChrome();
  _onLoggedInCallback = onReady;
  fetch("/api/me").then(async (res) => {
    if (res.ok) {
      const data = await res.json();
      onLoggedIn(data.username);
    } else {
      showAuthOverlay();
    }
  });
}

// ---------- Liederbuecher (persistiert, mehrere pro User, eigener Name) ----------
// activeBook haelt das aktuell gewaehlte Liederbuch inkl. aufgeloester Songs (Titel/Artist).
// books haelt nur die Zusammenfassungen (fuer den Auswahl-Dropdown).

let books = [];
let activeBook = null;

function getActiveBookId() {
  const v = localStorage.getItem(ACTIVE_BOOK_KEY);
  return v ? parseInt(v, 10) : null;
}

function setActiveBookId(id) {
  if (id == null) localStorage.removeItem(ACTIVE_BOOK_KEY);
  else localStorage.setItem(ACTIVE_BOOK_KEY, String(id));
}

function activeBookSongIds() {
  return activeBook ? activeBook.songs.map((s) => s.id) : [];
}

// Auf jeder Seite mit Warenkorb-Widget nach initAuth() aufrufen.
async function loadBooks() {
  try {
    const res = await apiFetch("/api/books");
    if (!res.ok) return;
    books = await res.json();
  } catch (e) {
    return; // 401 wird schon von apiFetch behandelt
  }

  let activeId = getActiveBookId();
  if (!books.some((b) => b.id === activeId)) {
    activeId = books.length ? books[0].id : null;
    setActiveBookId(activeId);
  }

  if (activeId) {
    await loadActiveBook(activeId);
  } else {
    activeBook = null;
  }
  renderCartWidget();
  document.dispatchEvent(new CustomEvent("corda-cart-changed"));
}

async function loadActiveBook(id) {
  try {
    const res = await apiFetch(`/api/books/${id}`);
    if (res.ok) {
      activeBook = await res.json();
      setActiveBookId(activeBook.id);
      return;
    }
  } catch (e) {
    // 401 wird schon von apiFetch behandelt
  }
  activeBook = null;
  setActiveBookId(null);
}

async function switchActiveBook(id) {
  await loadActiveBook(id);
  renderCartWidget();
  document.dispatchEvent(new CustomEvent("corda-cart-changed"));
}

async function createBookPrompt() {
  const name = prompt("Name des neuen Liederbuchs:", "Mein Liederbuch");
  if (!name) return;
  try {
    const res = await apiFetch("/api/books", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!res.ok) return;
    const book = await res.json();
    const listRes = await apiFetch("/api/books");
    books = await listRes.json();
    await switchActiveBook(book.id);
  } catch (e) {
    // 401 wird schon von apiFetch behandelt
  }
}

async function renameActiveBookPrompt() {
  if (!activeBook) return;
  const name = prompt("Neuer Name:", activeBook.name);
  if (!name || name.trim() === activeBook.name) return;
  try {
    const res = await apiFetch(`/api/books/${activeBook.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!res.ok) return;
    activeBook = await res.json();
    const listRes = await apiFetch("/api/books");
    books = await listRes.json();
    renderCartWidget();
  } catch (e) {
    // 401 wird schon von apiFetch behandelt
  }
}

async function deleteActiveBookPrompt() {
  if (!activeBook) return;
  if (!confirm(`Liederbuch "${activeBook.name}" wirklich löschen?`)) return;
  try {
    const res = await apiFetch(`/api/books/${activeBook.id}`, { method: "DELETE" });
    if (!res.ok) return;
    setActiveBookId(null);
    await loadBooks();
    document.dispatchEvent(new CustomEvent("corda-cart-changed"));
  } catch (e) {
    // 401 wird schon von apiFetch behandelt
  }
}

async function saveActiveBookSongs(songs) {
  if (!activeBook) return;
  try {
    const res = await apiFetch(`/api/books/${activeBook.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ song_ids: songs.map((s) => s.id) }),
    });
    if (res.ok) {
      activeBook = await res.json();
      const listRes = await apiFetch("/api/books");
      books = await listRes.json();
    }
  } catch (e) {
    // 401 wird schon von apiFetch behandelt
  }
  renderCartWidget();
  document.dispatchEvent(new CustomEvent("corda-cart-changed"));
}

async function removeFromActiveBook(songId) {
  if (!activeBook) return;
  await saveActiveBookSongs(activeBook.songs.filter((s) => s.id !== songId));
}

async function moveActiveBookItem(index, delta) {
  if (!activeBook) return;
  const songs = [...activeBook.songs];
  const target = index + delta;
  if (target < 0 || target >= songs.length) return;
  [songs[index], songs[target]] = [songs[target], songs[index]];
  await saveActiveBookSongs(songs);
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

// ---------- PDF-Vollbild-Vorschau ----------
// Ersetzt window.open(blobUrl, "_blank"): das wird auf Mobile (v.a. iOS Safari)
// von Popup-Blockern oft verhindert, weil der Klick durch den vorherigen await
// nicht mehr als direkte User-Geste zaehlt. Ein Overlay in der Seite selbst
// braucht kein window.open und liefert gleichzeitig genau die Vollbild-Ansicht,
// die man am Handy zum Ablesen der Noten will.

let _pdfOverlayUrl = null;

function ensurePdfOverlay() {
  let el = document.getElementById("pdf-overlay");
  if (el) return el;

  document.body.insertAdjacentHTML("beforeend", `
    <div id="pdf-overlay">
      <div id="pdf-overlay-bar">
        <span id="pdf-overlay-title"></span>
        <a id="pdf-overlay-download" download="liederbuch.pdf">Herunterladen</a>
        <button id="pdf-overlay-close">✕ Schließen</button>
      </div>
      <iframe id="pdf-overlay-frame"></iframe>
    </div>
  `);
  el = document.getElementById("pdf-overlay");
  document.getElementById("pdf-overlay-close").addEventListener("click", closePdfOverlay);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && el.classList.contains("open")) closePdfOverlay();
  });
  return el;
}

function showPdfOverlay(blob, title) {
  const el = ensurePdfOverlay();
  if (_pdfOverlayUrl) URL.revokeObjectURL(_pdfOverlayUrl);
  const url = URL.createObjectURL(blob);
  _pdfOverlayUrl = url;

  document.getElementById("pdf-overlay-title").textContent = title || "Vorschau";
  document.getElementById("pdf-overlay-download").href = url;
  document.getElementById("pdf-overlay-frame").src = url;
  el.classList.add("open");
  document.body.style.overflow = "hidden";
}

function closePdfOverlay() {
  const el = document.getElementById("pdf-overlay");
  if (el) {
    el.classList.remove("open");
    document.getElementById("pdf-overlay-frame").src = "about:blank";
  }
  document.body.style.overflow = "";
  if (_pdfOverlayUrl) {
    URL.revokeObjectURL(_pdfOverlayUrl);
    _pdfOverlayUrl = null;
  }
}

// ---------- "Zu Liederbuch hinzufügen"-Popover (ersetzt die alte Checkbox) ----------
// Zeigt alle Liederbücher des Users mit Checkbox (Mitgliedschaft dieses Songs) plus
// Inline-Feld fuer ein neues Liederbuch. Toggle wirkt direkt auf das jeweilige Buch,
// unabhaengig vom "aktiven" Liederbuch in der Sidebar.

let _openPicker = null;

function closeBookPicker() {
  if (_openPicker) {
    _openPicker.el.remove();
    document.removeEventListener("mousedown", _openPicker.outsideHandler);
    _openPicker = null;
  }
}

async function toggleSongInBook(bookId, song, add) {
  const book = books.find((b) => b.id === bookId);
  if (!book) return;
  const songIds = add
    ? [...book.song_ids, song.id]
    : book.song_ids.filter((id) => id !== song.id);

  try {
    const res = await apiFetch(`/api/books/${bookId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ song_ids: songIds }),
    });
    if (!res.ok) return;
    const updated = await res.json();
    book.song_ids = updated.songs.map((s) => s.id);
    book.song_count = updated.songs.length;
    if (activeBook && activeBook.id === bookId) {
      activeBook = updated;
      renderCartWidget();
    }
    document.dispatchEvent(new CustomEvent("corda-cart-changed"));
  } catch (e) {
    // 401 wird schon von apiFetch behandelt
  }
}

function openBookPicker(song, anchorEl) {
  const reopening = _openPicker && _openPicker.songId === song.id;
  closeBookPicker();
  if (reopening) return; // zweiter Klick auf denselben Button schliesst nur

  const rect = anchorEl.getBoundingClientRect();
  const el = document.createElement("div");
  el.id = "book-picker";
  el.style.top = `${rect.bottom + window.scrollY + 4}px`;
  el.style.left = `${Math.max(8, Math.min(rect.left + window.scrollX, window.innerWidth - 260))}px`;

  const rows = books
    .map(
      (b) => `
      <label class="book-picker-row">
        <input type="checkbox" data-book-id="${b.id}" ${b.song_ids.includes(song.id) ? "checked" : ""}>
        <span>${escapeHtml(b.name)}</span>
      </label>`
    )
    .join("");

  el.innerHTML = `
    <div class="book-picker-title">Zu Liederbuch hinzufügen</div>
    ${books.length ? `<div class="book-picker-list">${rows}</div>` : '<div class="book-picker-empty">Noch kein Liederbuch angelegt</div>'}
    <div class="book-picker-new">
      <input type="text" id="book-picker-new-name" placeholder="Neues Liederbuch...">
      <button id="book-picker-new-btn">+</button>
    </div>
  `;
  document.body.appendChild(el);

  el.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
    cb.addEventListener("change", () => {
      toggleSongInBook(parseInt(cb.dataset.bookId, 10), song, cb.checked);
    });
  });

  const newNameInput = el.querySelector("#book-picker-new-name");
  const createAndAdd = async () => {
    const name = newNameInput.value.trim();
    if (!name) return;
    try {
      const res = await apiFetch("/api/books", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!res.ok) return;
      const book = await res.json();
      const listRes = await apiFetch("/api/books");
      books = await listRes.json();
      await toggleSongInBook(book.id, song, true);
      closeBookPicker();
      openBookPicker(song, anchorEl);
    } catch (e) {
      // 401 wird schon von apiFetch behandelt
    }
  };
  el.querySelector("#book-picker-new-btn").addEventListener("click", createAndAdd);
  newNameInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      createAndAdd();
    }
  });

  const outsideHandler = (e) => {
    if (!el.contains(e.target) && e.target !== anchorEl) closeBookPicker();
  };
  setTimeout(() => document.addEventListener("mousedown", outsideHandler), 0);

  _openPicker = { el, outsideHandler, songId: song.id };
}

// Rendert die Liederbuch-Verwaltung in ein Element mit id="cart-widget", falls auf der Seite vorhanden.
function renderCartWidget() {
  const el = document.getElementById("cart-widget");
  if (!el) return;

  const options = books
    .map((b) => `<option value="${b.id}"${activeBook && activeBook.id === b.id ? " selected" : ""}>${escapeHtml(b.name)} (${b.song_count})</option>`)
    .join("");

  el.innerHTML = `
    <h2><span>Liederbücher</span></h2>
    <div id="book-controls">
      <select id="book-select" ${books.length === 0 ? "disabled" : ""}>${options || '<option>– keine –</option>'}</select>
      <button id="new-book-btn" title="Neues Liederbuch">+ Neu</button>
    </div>
    <div id="book-controls">
      <button id="rename-book-btn" title="Umbenennen" ${activeBook ? "" : "disabled"}>Umbenennen</button>
      <button id="delete-book-btn" title="Löschen" ${activeBook ? "" : "disabled"}>Löschen</button>
    </div>
    <ul id="cart-list"></ul>
    ${!activeBook ? '<div class="cart-empty">Noch kein Liederbuch angelegt</div>' : activeBook.songs.length === 0 ? '<div class="cart-empty">Noch keine Songs in diesem Liederbuch</div>' : ""}
    <button id="render-book-btn" ${!activeBook || activeBook.songs.length === 0 ? "disabled" : ""}>Buch rendern (PDF)</button>
    <div id="book-status"></div>
  `;

  if (activeBook) {
    const list = el.querySelector("#cart-list");
    activeBook.songs.forEach((song, i) => {
      const li = document.createElement("li");
      li.innerHTML = `
        <span class="cart-title"></span>
        <button class="cart-up" title="nach oben">↑</button>
        <button class="cart-down" title="nach unten">↓</button>
        <button class="cart-remove" title="entfernen">✕</button>`;
      const titleEl = li.querySelector(".cart-title");
      if (song.available) {
        titleEl.textContent = song.title;
        titleEl.title = song.title;
      } else {
        titleEl.textContent = "(nicht mehr verfügbar)";
        titleEl.classList.add("unavailable");
      }
      li.querySelector(".cart-up").disabled = i === 0;
      li.querySelector(".cart-down").disabled = i === activeBook.songs.length - 1;
      li.querySelector(".cart-up").addEventListener("click", () => moveActiveBookItem(i, -1));
      li.querySelector(".cart-down").addEventListener("click", () => moveActiveBookItem(i, 1));
      li.querySelector(".cart-remove").addEventListener("click", () => removeFromActiveBook(song.id));
      list.appendChild(li);
    });
  }

  const select = document.getElementById("book-select");
  if (select) {
    select.addEventListener("change", (e) => {
      const id = parseInt(e.target.value, 10);
      if (id) switchActiveBook(id);
    });
  }
  document.getElementById("new-book-btn").addEventListener("click", createBookPrompt);
  document.getElementById("rename-book-btn").addEventListener("click", renameActiveBookPrompt);
  document.getElementById("delete-book-btn").addEventListener("click", deleteActiveBookPrompt);
  const renderBtn = document.getElementById("render-book-btn");
  if (renderBtn) renderBtn.addEventListener("click", renderActiveBook);
}

async function renderActiveBook() {
  if (!activeBook) return;
  const btn = document.getElementById("render-book-btn");
  const statusEl = document.getElementById("book-status");
  btn.disabled = true;
  statusEl.textContent = `rendere Buch (${activeBook.songs.length} Songs)...`;
  statusEl.className = "";

  try {
    const res = await apiFetch(`/api/books/${activeBook.id}/render`, { method: "POST" });

    if (!res.ok) {
      const err = await res.json();
      statusEl.textContent = err.error || "Fehler beim Rendern";
      statusEl.className = "error";
      return;
    }

    const skippedHeader = res.headers.get("X-Skipped-Songs");
    const blob = await res.blob();
    showPdfOverlay(blob, activeBook.name);

    if (skippedHeader) {
      statusEl.textContent = `Übersprungen: ${JSON.parse(skippedHeader).join(", ")}`;
      statusEl.className = "error";
    } else {
      statusEl.textContent = "";
    }
  } catch (e) {
    if (e.message !== "unauthorized") {
      statusEl.textContent = "Netzwerkfehler";
      statusEl.className = "error";
    }
  } finally {
    btn.disabled = !activeBook || activeBook.songs.length === 0;
  }
}
