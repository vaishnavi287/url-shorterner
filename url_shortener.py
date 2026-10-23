"""URL Shortener - single-file web app (Flask + SQLite) with dashboard and click analytics.
Setup: pip install flask
Run:   python url_shortener.py      then open http://127.0.0.1:5000
Data is saved in urls.db next to this file.
"""
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, abort, jsonify, redirect, request

PAGE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Link Shortener</title>
<style>
:root{--bg:#f5f6fa;--card:#fff;--text:#1b2233;--muted:#6b7385;--accent:#4f46e5;--on-accent:#fff;--accent-2:#e0e7ff;--border:#e3e6ee;--danger:#d92d20;--ok:#067647}
@media (prefers-color-scheme:dark){:root{--bg:#0e1120;--card:#171b2e;--text:#e9ebf5;--muted:#9aa2b8;--accent:#8b8cf8;--on-accent:#0e1120;--accent-2:#262b52;--border:#2a3049;--danger:#f97066;--ok:#47cd89}}
*{box-sizing:border-box}
body{margin:0;font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text)}
main{max-width:900px;margin:0 auto;padding:24px 16px 48px;display:grid;gap:16px}
h1{font-size:22px;margin:0}
h2{font-size:13px;margin:0;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.05em}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px}
.row{display:flex;gap:10px}
.head{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
input,button{font:inherit;padding:10px 12px;border-radius:8px;border:1px solid var(--border);background:var(--card);color:var(--text)}
input{flex:1;min-width:0}
button{cursor:pointer}
button.primary{background:var(--accent);color:var(--on-accent);border:0;font-weight:600}
button.del{background:transparent;color:var(--danger);border:0;padding:4px 8px}
.msg{min-height:1.2em;margin:10px 0 0;font-size:13px;color:var(--ok)}
.msg.err{color:var(--danger)}
.result{display:flex;gap:10px;align-items:center;margin-top:12px;padding:12px;border-radius:8px;background:var(--accent-2)}
.result a{flex:1;font-weight:600;color:var(--text);word-break:break-all}
.tablewrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;padding:8px;border-bottom:1px solid var(--border);vertical-align:middle}
th{color:var(--muted);font-weight:600;font-size:12px}
td.long{max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--muted)}
td.num{text-align:right;font-variant-numeric:tabular-nums}
a{color:var(--accent)}
.muted{color:var(--muted);font-size:13px}
</style>
</head>
<body>
<main>
  <h1>🔗 Link Shortener</h1>

  <section class="card">
    <form id="shorten-form" class="row">
      <input id="url" type="url" required placeholder="Paste a long URL, e.g. https://example.com/some/long/path" aria-label="Long URL">
      <button class="primary" type="submit">Shorten</button>
    </form>
    <p id="msg" class="msg" role="status"></p>
    <div id="result" class="result" hidden>
      <a id="result-link" target="_blank" rel="noopener"></a>
      <button id="copy" type="button">Copy</button>
    </div>
  </section>

  <section class="card">
    <div class="head"><h2>Recent links</h2><button id="refresh" type="button">Refresh</button></div>
    <div class="tablewrap">
      <table>
        <thead><tr><th>Short link</th><th>Original URL</th><th class="num">Clicks</th><th>Created</th><th></th></tr></thead>
        <tbody id="rows"></tbody>
      </table>
    </div>
    <p id="empty" class="muted" hidden>No links yet. Shorten your first URL above.</p>
  </section>
</main>

<script>
const $ = (s) => document.querySelector(s);
function el(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  }
  e.append(...kids.filter((k) => k != null && k !== false));
  return e;
}
let msgTimer;
function flash(text, isErr = false) {
  const m = $("#msg");
  m.textContent = text;
  m.className = "msg" + (isErr ? " err" : "");
  clearTimeout(msgTimer);
  if (text) msgTimer = setTimeout(() => (m.textContent = ""), 3500);
}
async function api(path, opts) {
  const res = await fetch(path, opts);
  const data = res.status === 204 ? {} : await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}
const when = (s) => new Date(s.replace(" ", "T") + "Z").toLocaleString();

async function load() {
  const list = await api("/api/links");
  $("#empty").hidden = list.length > 0;
  $("#rows").replaceChildren(...list.map((l) => el("tr", {},
    el("td", {}, el("a", {href: l.short_url, target: "_blank", rel: "noopener"}, l.short_url)),
    el("td", {class: "long", title: l.long_url}, l.long_url),
    el("td", {class: "num"}, String(l.clicks)),
    el("td", {}, when(l.created_at)),
    el("td", {}, el("button", {class: "del", type: "button", title: "Delete", "aria-label": "Delete link",
                               onclick: () => remove(l.code)}, "✕")))));
}
async function remove(code) {
  if (!confirm("Delete this link? The short URL will stop working.")) return;
  try { await api("/api/links/" + code, {method: "DELETE"}); load(); } catch (e) { flash(e.message, true); }
}

$("#shorten-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const d = await api("/api/shorten", {method: "POST", headers: {"Content-Type": "application/json"},
                                         body: JSON.stringify({url: $("#url").value.trim()})});
    const a = $("#result-link");
    a.textContent = d.short_url; a.href = d.short_url;
    $("#result").hidden = false;
    $("#url").value = "";
    flash("");
    load();
  } catch (err) { flash(err.message, true); }
});
$("#copy").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("#result-link").textContent); flash("Copied to clipboard."); }
  catch { flash("Could not copy automatically. Select the link and press Ctrl+C.", true); }
});
$("#refresh").addEventListener("click", () => load().catch((e) => flash(e.message, true)));
load().catch((e) => flash(e.message, true));
setInterval(() => load().catch(() => {}), 5000);
</script>
</body>
</html>
'''


app = Flask(__name__)
DB = Path(__file__).with_name("urls.db")
ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS urls(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        long_url TEXT NOT NULL,
        clicks INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    return con


def encode(n):
    s = ""
    while n:
        n, r = divmod(n, 62)
        s = ALPHABET[r] + s
    return s or "0"


def decode(code):
    n = 0
    for ch in code:
        n = n * 62 + ALPHABET.index(ch)
    return n


def valid(url):
    u = urlparse(url)
    return u.scheme in ("http", "https") and bool(u.netloc)


@app.get("/")
def index():
    return PAGE


@app.post("/api/shorten")
def shorten():
    url = str((request.get_json(silent=True) or {}).get("url", "")).strip()
    if not valid(url):
        return jsonify(error="Provide a valid http(s) URL"), 400
    with db() as con:
        new_id = con.execute("INSERT INTO urls(long_url) VALUES(?)", (url,)).lastrowid
    return jsonify(short_url=request.host_url + encode(new_id)), 201


@app.get("/api/links")
def links():
    rows = db().execute(
        "SELECT id, long_url, clicks, created_at FROM urls ORDER BY id DESC LIMIT 20").fetchall()
    return jsonify([{"code": encode(r[0]), "short_url": request.host_url + encode(r[0]),
                     "long_url": r[1], "clicks": r[2], "created_at": r[3]} for r in rows])


@app.delete("/api/links/<code>")
def delete_link(code):
    try:
        uid = decode(code)
    except ValueError:
        abort(404)
    with db() as con:
        deleted = con.execute("DELETE FROM urls WHERE id=?", (uid,)).rowcount
    if not deleted:
        abort(404)
    return "", 204


@app.get("/api/stats/<code>")
def stats(code):
    try:
        uid = decode(code)
    except ValueError:
        abort(404)
    row = db().execute("SELECT long_url, clicks, created_at FROM urls WHERE id=?", (uid,)).fetchone()
    if not row:
        abort(404)
    return jsonify(long_url=row[0], clicks=row[1], created_at=row[2])


@app.get("/<code>")
def go(code):
    try:
        uid = decode(code)
    except ValueError:
        abort(404)
    with db() as con:
        row = con.execute("SELECT long_url FROM urls WHERE id=?", (uid,)).fetchone()
        if not row:
            abort(404)
        con.execute("UPDATE urls SET clicks = clicks + 1 WHERE id=?", (uid,))
    return redirect(row[0])


if __name__ == "__main__":
    app.run(debug=True)
