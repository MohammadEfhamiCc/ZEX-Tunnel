#!/usr/bin/env python3

# ─── USER SETTINGS (DEFAULTS) ────────────────────────────────────────────────
PORT          = 8989        # Web port (default)
POLL_INTERVAL = 0.3         # Seconds between file-scan polls (default)
PASSWORD      = "mdo"       # Login password (default)
DEBUG         = True        # Extra server prints (default)
# ─────────────────────────────────────────────────────────────────────────────

# eventlet must patch stdlib **before** any other networking import
import eventlet
eventlet.monkey_patch()

import re, time, threading, secrets, sys, logging
from pathlib import Path
from functools import wraps
from flask import Flask, render_template_string, request, redirect, session
from flask_socketio import SocketIO, emit

# ─── Settings file (web.zex) ─────────────────────────────────────────────────
CONFIG_FILE = Path(__file__).with_name("web.zex")

def save_default_settings() -> None:
    """Create web.zex with current defaults if it doesn’t exist."""
    try:
        with CONFIG_FILE.open("w", encoding="utf-8") as fh:
            fh.write(f"{PORT}\n{POLL_INTERVAL}\n{PASSWORD}\n{int(DEBUG)}\n")
    except Exception as e:
        print(f"[WARN] could not write {CONFIG_FILE}: {e}", file=sys.stderr)

def load_settings() -> None:
    """Override defaults from web.zex (PORT, POLL_INTERVAL, PASSWORD, DEBUG)."""
    global PORT, POLL_INTERVAL, PASSWORD, DEBUG

    if not CONFIG_FILE.exists():
        save_default_settings()
        return

    try:
        with CONFIG_FILE.open(encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh.readlines()]

        if len(lines) >= 1 and lines[0]:
            PORT = int(lines[0])
        if len(lines) >= 2 and lines[1]:
            POLL_INTERVAL = float(lines[1])
        if len(lines) >= 3 and lines[2]:
            PASSWORD = lines[2]
        if len(lines) >= 4 and lines[3]:
            DEBUG = lines[3].lower() in ("1", "true", "yes", "on")
    except Exception as e:
        print(f"[WARN] could not parse {CONFIG_FILE}: {e}", file=sys.stderr)

# Load (or create) settings immediately
load_settings()

# ─── Log-file config ────────────────────────────────────────────────────────
LOG_DIR   = Path(__file__).resolve().parent / "log"
PREFIXES  = ("network.", "core.", "internal.")
TAIL_LAST = 300                         # Lines sent to browser on first load

# ─── Flask + Socket.IO (eventlet) ────────────────────────────────────────────
app            = Flask(__name__)
app.secret_key = secrets.token_hex(16)
socketio       = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet",
                          manage_session=False)

def dbg(msg: str) -> None:
    if DEBUG:
        print(msg, flush=True)

# ─── stdout request logger (Werkzeug-style) ──────────────────────────────────
logger = logging.getLogger("zex_requests")
logger.handlers.clear()
h = logging.StreamHandler(sys.stdout)
h.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(h)
logger.setLevel(logging.INFO)

@app.after_request
def _log(resp):
    ts   = time.strftime("%d/%b/%Y %H:%M:%S")
    path = request.full_path.rstrip("?") or request.path
    logger.info(f'{request.remote_addr} - - [{ts}] "{request.method} {path} HTTP/1.1" {resp.status_code} -')
    return resp

# ─── auth decorator ──────────────────────────────────────────────────────────
def login_required(view):
    @wraps(view)
    def wrapped(*a, **k):
        if not session.get("auth"):
            return redirect("/")
        return view(*a, **k)
    return wrapped

# ─── Helpers for file selection & tail ───────────────────────────────────────
DATE_RE = re.compile(r"(\d{8})")

def latest_file(prefix: str):
    files = [p for p in LOG_DIR.iterdir() if p.is_file() and p.name.startswith(prefix)]
    return max(files, key=lambda p: (DATE_RE.search(p.name) or ["00000000"])[0]) if files else None

def ordered_files():
    return [f for f in (latest_file(pr) for pr in PREFIXES) if f]

def tail(path: Path, lines: int) -> str:
    try:
        return "".join(path.read_text(errors="ignore").splitlines(keepends=True)[-lines:])
    except Exception as e:
        return f"[error reading {path.name}: {e}]\n"

# ─── Polling thread ──────────────────────────────────────────────────────────
offsets: dict[Path, int] = {}

def poll_loop() -> None:
    while True:
        for p in ordered_files():
            try:
                if p not in offsets:
                    offsets[p] = p.stat().st_size
                size = p.stat().st_size
                if size > offsets[p]:
                    # New data appended
                    with p.open("rb") as fh:
                        fh.seek(offsets[p])
                        data = fh.read()
                    offsets[p] = size
                    socketio.emit("update", {
                        "filename": p.name,
                        "content" : data.decode(errors="ignore")
                    })
            except Exception as e:
                dbg(f"[ERR] {p}: {e}")
        eventlet.sleep(POLL_INTERVAL)

# ─── FULL HTML templates ─────────────────────────────────────────────────────
LOGIN_HTML = """
<!doctype html><html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ZEX Login</title>
<script src="https://cdn.tailwindcss.com"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
 body{background:linear-gradient(120deg,#0f172a,#1e293b)}
 .box{animation:drop .7s ease-out forwards;opacity:0}
 @keyframes drop{from{transform:translateY(-60px);opacity:0}
                 to{transform:translateY(0);opacity:1}}
 .glow{box-shadow:0 0 12px #0891b2,0 0 32px #0891b2}
</style></head>
<body class="h-screen flex items-center justify-center font-mono text-white">
<form method="post" class="box bg-slate-800/90 p-8 rounded-xl glow space-y-6 w-full max-w-sm">
  <div class="text-center">
    <i class="fas fa-shield-halved text-4xl text-cyan-400 animate-pulse"></i>
    <h1 class="text-2xl font-bold text-cyan-300 mt-2">ZEX Waterwall</h1>
    <p class="text-sm text-gray-400">Live Log Viewer</p>
  </div>
  {% if error %}
  <p class="bg-red-900 text-red-400 p-2 rounded text-center text-sm">
    <i class="fas fa-triangle-exclamation mr-1"></i>{{ error }}
  </p>{% endif %}
  <div>
    <label for="pw" class="block text-sm font-semibold mb-1">
      <i class="fas fa-lock mr-1"></i>Password
    </label>
    <input id="pw" name="pw" type="password" autofocus placeholder="••••••••"
           class="w-full px-4 py-2 bg-black/70 border border-slate-600 rounded focus:ring-2 focus:ring-cyan-500">
  </div>
  <button class="w-full py-2 bg-cyan-500 hover:bg-cyan-400 text-black font-bold rounded">
    <i class="fas fa-arrow-right-to-bracket mr-1"></i>Login
  </button>
  <div class="text-center text-xs text-gray-400">
    <i class="fas fa-code"></i> Code by
    <a href="https://zex.ae" class="underline text-cyan-300 hover:text-cyan-400">ZEX</a>
  </div>
</form></body></html>
"""

LOGS_HTML = r"""
<!doctype html><html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ZEX Logs</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.socket.io/4.7.4/socket.io.min.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
 body{background:#0f172a;color:#e2e8f0}
 header{background:#0369a1}
 .card{animation:fade .6s ease forwards;opacity:0}
 @keyframes fade{from{opacity:0;transform:translateY(40px)}to{opacity:1;transform:translateY(0)}}
 .scroll::-webkit-scrollbar{width:6px}
 .scroll::-webkit-scrollbar-thumb{background:#0891b2;border-radius:3px}
</style></head>
<body class="font-mono">

<header class="py-4 shadow-lg flex justify-between items-center px-6 text-black">
  <div class="text-lg font-extrabold tracking-wide flex items-center gap-2">
    <i class="fas fa-wave-square"></i> ZEX Waterwall — Live Logs
  </div>
</header>

<main class="p-6 space-y-8">
  {% if files|length == 0 %}
    <div class="text-center text-red-400 text-sm">
      <i class="fas fa-circle-exclamation"></i> No log files found in /log
    </div>
  {% endif %}
  {% for f in files %}
  <section class="card border border-cyan-600 rounded-lg overflow-hidden shadow-lg">
    <div class="bg-cyan-700 text-black px-4 py-2 text-sm uppercase tracking-wider flex items-center gap-2">
      <i class="fas fa-file-lines"></i> {{ f }}
    </div>
    <pre id="log_{{ loop.index0 }}" class="scroll bg-black text-green-400 text-sm p-3 h-80 overflow-y-scroll"></pre>
  </section>
  {% endfor %}
</main>

<footer class="py-4 text-center text-xs text-gray-400">
  <i class="fas fa-code"></i> Code By
  <a href="https://zex.ae" class="underline hover:text-cyan-400">ZEX</a>
</footer>

<script>
const files={{ files|tojson }};
const sock=io({transports:["websocket","polling"]});
sock.on("init",data=>data.forEach((o,i)=>{if(files[i]){b(i).textContent=o.content;auto(i);}}));
sock.on("update",({filename,content})=>{
  const i=files.indexOf(filename);
  if(i>=0){b(i).textContent+=content;auto(i);}
});
function b(i){return document.getElementById("log_"+i)}
function auto(i){const el=b(i);el.scrollTop=el.scrollHeight;}
</script></body></html>
"""

# ─── Flask routes ────────────────────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("pw") == PASSWORD:
            session["auth"] = True
            return redirect("/logs")
        return render_template_string(LOGIN_HTML, error="Wrong password")
    return render_template_string(LOGIN_HTML, error=None)

@app.route("/logs")
@login_required
def logs():
    return render_template_string(LOGS_HTML, files=[p.name for p in ordered_files()])

# ─── WebSocket gate ───────────────────────────────────────────────────────────
@socketio.on("connect")
def ws_gate():
    if not session.get("auth"):
        return False
    emit("init", [
        {"filename": p.name, "content": tail(p, TAIL_LAST)}
        for p in ordered_files()
    ])

# ─── Run server ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    LOG_DIR.mkdir(exist_ok=True)
    threading.Thread(target=poll_loop, daemon=True).start()

    print("\n========== ZEX WATERWALL Log System ==========")
    print(f"🚀  URL           : http://0.0.0.0:{PORT}")
    print(f"🔁  Poll interval : {POLL_INTERVAL} sec")
    print(f"🔑  Login password: {PASSWORD}")
    print(f"🐞  Debug mode    : {DEBUG}")
    print("===================================\n")

    socketio.run(app, host="0.0.0.0", port=PORT)