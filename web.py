#!/usr/bin/env python3
# ZEX Tunnel Web Panel V3 — Bootstrap Minimal + Realtime + Tunnel Status (LISTEN-only view)

# ─── USER SETTINGS (DEFAULTS) ────────────────────────────────────────────────
PORT          = 8989        # Web port (default)
POLL_INTERVAL = 0.8         # Seconds between polls
PASSWORD      = "mdo"       # Login password
DEBUG         = True        # Extra prints
TOP_N         = 10          # rows for processes / connections / open ports
# ─────────────────────────────────────────────────────────────────────────────

# eventlet must patch stdlib **before** any other networking import
import eventlet
eventlet.monkey_patch()

import re, time, threading, secrets, sys, logging, socket, platform
from pathlib import Path
from functools import wraps
from flask import Flask, render_template_string, request, redirect, session, url_for
from flask_socketio import SocketIO, emit
import psutil

# ─── Settings file (web.zex) ─────────────────────────────────────────────────
CONFIG_FILE = Path(__file__).with_name("web.zex")
def save_default_settings():
    try:
        CONFIG_FILE.write_text(f"{PORT}\n{POLL_INTERVAL}\n{PASSWORD}\n{int(DEBUG)}\n", encoding="utf-8")
    except Exception as e:
        print(f"[WARN] could not write {CONFIG_FILE}: {e}", file=sys.stderr)
def load_settings():
    global PORT, POLL_INTERVAL, PASSWORD, DEBUG
    if not CONFIG_FILE.exists():
        save_default_settings(); return
    try:
        lines = [ln.strip() for ln in CONFIG_FILE.read_text(encoding="utf-8").splitlines()]
        if len(lines) >= 1 and lines[0]: PORT = int(lines[0])
        if len(lines) >= 2 and lines[1]: POLL_INTERVAL = float(lines[1])
        if len(lines) >= 3 and lines[2]: PASSWORD = lines[2]
        if len(lines) >= 4 and lines[3]: DEBUG = lines[3].lower() in ("1","true","yes","on")
    except Exception as e:
        print(f"[WARN] could not parse {CONFIG_FILE}: {e}", file=sys.stderr)
load_settings()

# ─── Paths / Logs ────────────────────────────────────────────────────────────
LOG_DIR   = Path(__file__).resolve().parent / "log"
PREFIXES  = ("network.", "core.", "internal.")
TAIL_LAST = 110

# ─── App / Sockets ───────────────────────────────────────────────────────────
app            = Flask(__name__)
app.secret_key = secrets.token_hex(16)
socketio       = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet",
                          manage_session=False)

def dbg(msg: str):
    if DEBUG: print(msg, flush=True)

# ─── Access log ──────────────────────────────────────────────────────────────
logger = logging.getLogger("zex_requests")
logger.handlers.clear()
h = logging.StreamHandler(sys.stdout)
h.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(h)
logger.setLevel(logging.INFO)
@app.after_request
def _log(resp):
    ts = time.strftime("%d/%b/%Y %H:%M:%S")
    path = request.full_path.rstrip("?") or request.path
    logger.info(f'{request.remote_addr} - - [{ts}] "{request.method} {path} HTTP/1.1" {resp.status_code} -')
    return resp

# ─── Auth ────────────────────────────────────────────────────────────────────
def login_required(view):
    @wraps(view)
    def wrapped(*a, **k):
        if not session.get("auth"):
            return redirect(url_for("login"))
        return view(*a, **k)
    return wrapped

# ─── Helpers: logs ───────────────────────────────────────────────────────────
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

# ─── Helpers: tunnel info (like your bash) ───────────────────────────────────
BASE_DIR = Path("/root/ZEX-Tunnel")
def read_tunnel_info():
    location, conf_addr = "Unknown", "N/A"
    if (BASE_DIR / "config_ir.json").exists():
        location, conf_addr = "Iran", str(BASE_DIR / "config_ir.json")
    if (BASE_DIR / "config_kharej.json").exists():
        location, conf_addr = "Outside", str(BASE_DIR / "config_kharej.json")
    iran_ip = kharej_ip = protocol = port = "N/A"
    cfg = BASE_DIR / "config.zex"
    if cfg.exists():
        lines = [ln.strip() for ln in cfg.read_text().splitlines()]
        if len(lines) >= 1: iran_ip   = lines[0] or "N/A"
        if len(lines) >= 2: kharej_ip = lines[1] or "N/A"
        if len(lines) >= 3: protocol  = lines[2] or "N/A"
        if len(lines) >= 4: port      = lines[3] or "N/A"
    os_name = f"{platform.system()} {platform.release()}"
    try:
        data = Path("/etc/os-release").read_text()
        m = re.search(r'^PRETTY_NAME="?(.*?)"?$', data, re.M)
        if m: os_name = m.group(1)
    except Exception:
        pass
    uptime = int(time.time() - psutil.boot_time())
    return {
        "location": location,
        "iran_ip": iran_ip,
        "kharej_ip": kharej_ip,
        "protocol": protocol,
        "port": port,
        "config_addr": conf_addr,
        "os_name": os_name,
        "uptime": uptime
    }

# ─── Helpers: metrics & tables ───────────────────────────────────────────────
def bytes_h(n: float) -> str:
    units = ["B","KB","MB","GB","TB","PB"]; i=0
    while n>=1024 and i<len(units)-1: n/=1024.0; i+=1
    return f"{n:.1f} {units[i]}"

def get_stats(prev_net):
    cpu = psutil.cpu_percent(interval=None)
    vm  = psutil.virtual_memory()
    du  = psutil.disk_usage("/")
    ni  = psutil.net_io_counters()
    rx_rate = max(0, ni.bytes_recv - prev_net.bytes_recv) / max(POLL_INTERVAL, 1e-6)
    tx_rate = max(0, ni.bytes_sent - prev_net.bytes_sent) / max(POLL_INTERVAL, 1e-6)
    stats = {
        "cpu_pct": round(cpu,1),
        "ram_pct": round(vm.percent,1),
        "ram_used": bytes_h(vm.total - vm.available),
        "ram_total": bytes_h(vm.total),
        "disk_pct": round(du.percent,1),
        "disk_used": bytes_h(du.used),
        "disk_total": bytes_h(du.total),
        "net_rx_rate": bytes_h(rx_rate) + "/s",
        "net_tx_rate": bytes_h(tx_rate) + "/s",
        "net_rx_total": bytes_h(ni.bytes_recv),
        "net_tx_total": bytes_h(ni.bytes_sent),
        "uptime": int(time.time() - psutil.boot_time()),
    }
    return stats, ni

def get_top_processes(n=TOP_N):
    procs = []
    for p in psutil.process_iter(attrs=["pid","name","username","cpu_percent","memory_info"]):
        try:
            cpu = p.info.get("cpu_percent") or 0.0
            mem = (p.info.get("memory_info").rss if p.info.get("memory_info") else 0)
            procs.append({
                "pid": p.info.get("pid"),
                "name": (p.info.get("name") or "")[:40],
                "user": (p.info.get("username") or "")[:20],
                "cpu": round(cpu,1),
                "mem": bytes_h(mem)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda x: (x["cpu"],), reverse=True)
    return procs[:n]

def _proto_from_type(t):
    try:
        import socket as _s
        return "TCP" if t == _s.SOCK_STREAM else "UDP" if t == _s.SOCK_DGRAM else str(t)
    except Exception:
        return str(t)

def get_live_connections(n=TOP_N):
    rows = []
    pid2name = {}
    for c in psutil.net_connections(kind='inet'):
        try:
            if c.status != psutil.CONN_ESTABLISHED:
                continue
            laddr = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "-"
            raddr = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "-"
            pid   = c.pid or 0
            if pid not in pid2name:
                try:
                    pid2name[pid] = psutil.Process(pid).name()[:40] if pid else "-"
                except Exception:
                    pid2name[pid] = "-"
            rows.append({
                "proto": _proto_from_type(c.type),
                "laddr": laddr,
                "raddr": raddr,
                "pid": pid,
                "pname": pid2name.get(pid, "-"),
                "status": c.status
            })
        except Exception:
            continue
    return rows[:n]

def get_open_ports(n=TOP_N):
    rows, seen = [], set()
    for c in psutil.net_connections(kind='inet'):
        try:
            if c.status != psutil.CONN_LISTEN:
                continue
            laddr = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "-"
            key = (c.type, laddr, c.pid)
            if key in seen: continue
            seen.add(key)
            pid = c.pid or 0
            try:
                pname = psutil.Process(pid).name()[:40] if pid else "-"
            except Exception:
                pname = "-"
            rows.append({
                "proto": _proto_from_type(c.type),
                "laddr": laddr,
                "pid": pid,
                "pname": pname
            })
        except Exception:
            continue
    return rows[:n]

# Tunnel Status (LISTEN-only Waterwall view)
def get_tunnel_status(tunnel_port_str: str, n=TOP_N):
    """
    Show only LISTEN sockets of Waterwall. Columns: Proto, Port, PID.
    Active = Waterwall LISTENs on configured tunnel port.
    """
    entries = []
    active = False
    pname_cache = {}
    # parse configured port if possible
    try:
        tp = int(str(tunnel_port_str).strip())
    except Exception:
        tp = None

    for c in psutil.net_connections(kind="inet"):
        try:
            if c.status != psutil.CONN_LISTEN:
                continue
            pid = c.pid or 0
            # Cache process name
            if pid not in pname_cache:
                try:
                    name = psutil.Process(pid).name() or ""
                except Exception:
                    name = ""
                pname_cache[pid] = name
            name = pname_cache.get(pid, "")
            if "waterwall" not in name.lower():
                continue  # only Waterwall
            # Mark active if listening on tunnel port
            if tp is not None and c.laddr and c.laddr.port == tp:
                active = True
            elif tp is None:
                active = True  # no port configured -> any Waterwall LISTEN counts

            # Port-only (hide 0.0.0.0), keep proto & pid
            port = c.laddr.port if c.laddr else "-"
            entries.append({
                "proto": _proto_from_type(c.type),
                "port": str(port),
                "pid": pid
            })
        except Exception:
            continue

    # sort by port asc
    entries.sort(key=lambda e: int(e["port"]) if e["port"].isdigit() else 0)
    return {"active": active, "entries": entries[:n]}

# ─── Polling loop ────────────────────────────────────────────────────────────
offsets: dict[Path, int] = {}
_prev_net = psutil.net_io_counters()
def poll_loop():
    global _prev_net
    while True:
        # logs
        for p in ordered_files():
            try:
                if p not in offsets: offsets[p] = p.stat().st_size
                size = p.stat().st_size
                if size > offsets[p]:
                    with p.open("rb") as fh:
                        fh.seek(offsets[p]); data = fh.read()
                    offsets[p] = size
                    socketio.emit("log_update", {"filename": p.name, "content": data.decode(errors="ignore")})
            except Exception as e:
                dbg(f"[ERR] {p}: {e}")
        # metrics
        try:
            stats, _prev_net = get_stats(_prev_net)
            socketio.emit("stats", stats)
        except Exception as e:
            dbg(f"[ERR stats] {e}")
        # tables (+ tunnel)
        try:
            tinfo = read_tunnel_info()
            tables = {
                "procs": get_top_processes(),
                "conns": get_live_connections(),
                "ports": get_open_ports(),
                "tunnel": get_tunnel_status(tinfo.get("port", ""))
            }
            socketio.emit("tables", tables)
        except Exception as e:
            dbg(f"[ERR tables] {e}")
        eventlet.sleep(POLL_INTERVAL)

# ─── Networking: local IPv4 for nicer URL ────────────────────────────────────
def get_local_ip():
    ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            pass
    return ip

# ─── HTML: Login (Bootstrap) ─────────────────────────────────────────────────
LOGIN_HTML = """
<!doctype html>
<html lang="en" data-bs-theme="dark">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ZEX Tunnel Web Panel V3 • Login</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body{background:#0b1220}
    .card{background:rgba(255,255,255,.04);border-color:rgba(255,255,255,.08)}
  </style>
</head>
<body>
  <main class="container d-flex align-items-center justify-content-center" style="min-height:100svh;padding:1rem;">
    <div class="card shadow-sm" style="max-width:420px;width:100%;">
      <div class="card-body">
        <div class="d-flex align-items-center gap-2 mb-2">
          <span class="badge text-bg-secondary">ZEX • Panel</span>
        </div>
        <h5 class="card-title mb-3">Sign in</h5>
        {% if error %}<div class="alert alert-danger py-2">Wrong password</div>{% endif %}
        <form method="post" class="vstack gap-2">
          <div>
            <label for="pw" class="form-label">Password</label>
            <input id="pw" name="pw" type="password" class="form-control" placeholder="••••••••" autofocus>
          </div>
          <button class="btn btn-info fw-bold">Login</button>
        </form>
        <div class="small text-secondary mt-3">
          ZEX Tunnel V3 Code By <a class="link-light" target="_blank" href="https://zex.ae">ZEX</a>
          &nbsp;•&nbsp;<a class="link-light" target="_blank" href="https://github.com/izex/ZEX-Tunnel">GitHub</a>
        </div>
      </div>
    </div>
  </main>
</body>
</html>
"""

# ─── HTML: Dashboard (Bootstrap + Tunnel Status) ────────────────────────────
DASH_HTML = r"""
<!doctype html>
<html lang="en" data-bs-theme="dark">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ZEX Tunnel Web Panel V3 • Dashboard</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <script src="https://cdn.socket.io/4.7.4/socket.io.min.js"></script>
  <style>
    body{background:#0b1220}
    .card{background:rgba(255,255,255,.04);border-color:rgba(255,255,255,.08)}
    .progress{height:.6rem}
    pre{max-height:180px;background:#0a101c;border:1px solid rgba(255,255,255,.08);border-radius:.5rem;padding:.5rem;color:#a7ffb1}
    .fw-mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
    .table-sm td,.table-sm th{padding:.35rem}
    .dot{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:.4rem;animation:blink 1.2s infinite}
    @keyframes blink{0%,100%{opacity:.25}50%{opacity:1}}
  </style>
</head>
<body>
  <!-- Header -->
  <header class="container py-3">
    <div class="d-flex justify-content-between align-items-center">
      <div class="d-flex align-items-center gap-2">
        <span class="badge text-bg-secondary">ZEX • Panel</span>
        <h5 class="m-0">ZEX Tunnel Web Panel V3</h5>
      </div>
      <div class="d-flex align-items-center gap-2">
        <a class="btn btn-sm btn-outline-light" href="https://github.com/izex/ZEX-Tunnel" target="_blank">GitHub</a>
        <a class="btn btn-sm btn-info" href="{{ url_for('logout') }}">Logout</a>
      </div>
    </div>
  </header>

  <main class="container">
    <div class="row g-3">
      <!-- Left column -->
      <div class="col-12 col-lg-8 d-flex flex-column gap-3">

        <!-- Resources -->
        <div class="card">
          <div class="card-body">
            <h6 class="card-title mb-3">Resources</h6>
            <div class="vstack gap-3">
              <div>
                <div class="d-flex justify-content-between"><span class="text-secondary small">CPU</span><span class="small fw-mono" id="cpu_v">—</span></div>
                <div class="progress"><div id="cpu_bar" class="progress-bar bg-info" role="progressbar" style="width:0%"></div></div>
              </div>
              <div>
                <div class="d-flex justify-content-between"><span class="text-secondary small">RAM</span><span class="small fw-mono" id="ram_v">—</span></div>
                <div class="progress"><div id="ram_bar" class="progress-bar bg-primary" role="progressbar" style="width:0%"></div></div>
              </div>
              <div>
                <div class="d-flex justify-content-between"><span class="text-secondary small">Disk</span><span class="small fw-mono" id="disk_v">—</span></div>
                <div class="progress"><div id="disk_bar" class="progress-bar bg-success" role="progressbar" style="width:0%"></div></div>
              </div>
              <div class="d-flex justify-content-between small text-secondary">
                <span>🖥 OS Version: <span class="text-light">{{ tinfo.os_name }}</span></span>
                <span>⏱ Uptime: <span class="text-light fw-mono" id="uptime_v">—</span></span>
              </div>
            </div>
          </div>
        </div>

        <!-- Live Logs -->
        <div class="card">
          <div class="card-body">
            <h6 class="card-title mb-3">Live Logs</h6>
            {% if files|length == 0 %}
              <p class="text-secondary small">No log files found in /log</p>
            {% endif %}
            <div class="accordion" id="logAcc">
              {% for f in files %}
              <div class="accordion-item">
                <h2 class="accordion-header" id="h{{ loop.index0 }}">
                  <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#c{{ loop.index0 }}">
                    {{ f }} <span class="ms-2 text-secondary small">(tail {{ tail_last }} lines)</span>
                  </button>
                </h2>
                <div id="c{{ loop.index0 }}" class="accordion-collapse collapse" data-bs-parent="#logAcc">
                  <div class="accordion-body p-2">
                    <pre id="log_{{ loop.index0 }}"></pre>
                  </div>
                </div>
              </div>
              {% endfor %}
            </div>
          </div>
        </div>

        <!-- Active Processes -->
        <div class="card">
          <div class="card-body">
            <h6 class="card-title mb-3">Active Processes (Top {{ top_n }})</h6>
            <div class="table-responsive">
              <table class="table table-sm table-hover align-middle">
                <thead><tr><th>PID</th><th>Name</th><th>User</th><th class="text-end">CPU %</th><th class="text-end">Memory</th></tr></thead>
                <tbody id="tbl_procs"><tr><td colspan="5" class="text-secondary">Loading…</td></tr></tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Live Connections -->
        <div class="card">
          <div class="card-body">
            <h6 class="card-title mb-3">Live Connections (ESTABLISHED, Top {{ top_n }})</h6>
            <div class="table-responsive">
              <table class="table table-sm table-hover align-middle">
                <thead><tr><th>Proto</th><th>Local</th><th>Remote</th><th>Status</th><th>PID</th><th>Name</th></tr></thead>
                <tbody id="tbl_conns"><tr><td colspan="6" class="text-secondary">Loading…</td></tr></tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Open Ports -->
        <div class="card">
          <div class="card-body">
            <h6 class="card-title mb-3">Open Ports (LISTEN, Top {{ top_n }})</h6>
            <div class="table-responsive">
              <table class="table table-sm table-hover align-middle">
                <thead><tr><th>Proto</th><th>Local</th><th>PID</th><th>Name</th></tr></thead>
                <tbody id="tbl_ports"><tr><td colspan="4" class="text-secondary">Loading…</td></tr></tbody>
              </table>
            </div>
          </div>
        </div>

      </div>

      <!-- Right column: Tunnel Status + Info + Network -->
      <div class="col-12 col-lg-4 d-flex flex-column gap-3">

        <!-- TUNNEL STATUS (LISTEN-only) -->
        <div class="card">
          <div class="card-body">
            <h6 class="card-title mb-3">Tunnel Status</h6>
            <div class="d-flex align-items-center gap-2 mb-2">
              <span id="tunnel_dot" class="dot bg-danger"></span>
              <span id="tunnel_text" class="fw-bold">Inactive</span>
            </div>
            <div class="table-responsive">
              <table class="table table-sm table-hover align-middle">
                <thead><tr><th>Proto</th><th>Port</th><th>PID</th></tr></thead>
                <tbody id="tbl_tunnel"><tr><td colspan="3" class="text-secondary">No Waterwall listeners</td></tr></tbody>
              </table>
            </div>
            <div class="small text-secondary mt-1">Shows only Waterwall LISTEN sockets on the system.</div>
          </div>
        </div>

        <!-- Tunnel & Server Info -->
        <div class="card">
          <div class="card-body">
            <h6 class="card-title mb-3">Tunnel &amp; Server Info</h6>
            <div class="vstack gap-2">
              <div class="d-flex justify-content-between"><span class="text-secondary small">🛡 Server Location</span><span class="fw-mono">{{ tinfo.location }}</span></div>
              <div class="d-flex justify-content-between"><span class="text-secondary small">🌐 IRAN IP/Domain</span><span class="fw-mono">{{ tinfo.iran_ip }}</span></div>
              <div class="d-flex justify-content-between"><span class="text-secondary small">🌍 Kharej IP/Domain</span><span class="fw-mono">{{ tinfo.kharej_ip }}</span></div>
              <div class="d-flex justify-content-between"><span class="text-secondary small">🔢 Protocol Number</span><span class="fw-mono">{{ tinfo.protocol }}</span></div>
              <div class="d-flex justify-content-between"><span class="text-secondary small">🔉 Tunnel Port</span><span class="fw-mono">{{ tinfo.port }}</span></div>
              <div class="d-flex justify-content-between"><span class="text-secondary small">📄 Config Address</span><span class="fw-mono text-break">{{ tinfo.config_addr }}</span></div>
              <div class="d-flex justify-content-between"><span class="text-secondary small">GitHub</span><span><a class="link-light" target="_blank" href="https://github.com/izex/ZEX-Tunnel">izex/ZEX-Tunnel</a></span></div>
            </div>
          </div>
        </div>

        <!-- Network (under Info) -->
        <div class="card">
          <div class="card-body">
            <h6 class="card-title mb-3">Network</h6>
            <div class="row g-3">
              <div class="col-6">
                <div class="text-secondary small">Download (live)</div>
                <div class="fw-mono" id="rx_now">—</div>
              </div>
              <div class="col-6">
                <div class="text-secondary small">Upload (live)</div>
                <div class="fw-mono" id="tx_now">—</div>
              </div>
              <div class="col-6">
                <div class="text-secondary small">Total Download</div>
                <div class="fw-mono" id="rx_tot">—</div>
              </div>
              <div class="col-6">
                <div class="text-secondary small">Total Upload</div>
                <div class="fw-mono" id="tx_tot">—</div>
              </div>
            </div>
          </div>
        </div>

      </div>

    </div>

    <footer class="text-center text-secondary small py-3">
      ZEX Tunnel V3 Code By <a class="link-light" href="https://zex.ae" target="_blank" rel="noreferrer">ZEX</a>
    </footer>
  </main>

<script>
const files={{ files|tojson }};
const sock=io({transports:["websocket","polling"]});
function el(id){return document.getElementById(id)}
function ms(s){const d=Math.floor(s/86400);s%=86400;const h=Math.floor(s/3600);s%=3600;const m=Math.floor(s/60);s%=60;let out=[];if(d)out.push(d+"d");if(h)out.push(h+"h");if(m)out.push(m+"m");out.push(s+"s");return out.join(" ")}

sock.on("init",payload=>{
  payload.logs.forEach((o,i)=>{ if(files[i]){ el("log_"+i).textContent=o.content; } });
  if(payload.stats){applyStats(payload.stats)}
  if(payload.tables){renderTables(payload.tables)}
});
sock.on("log_update",({filename,content})=>{
  const i=files.indexOf(filename);
  if(i>=0){ el("log_"+i).textContent+=content; }
});
sock.on("stats",applyStats);
sock.on("tables",renderTables);

function applyStats(s){
  el("cpu_v").textContent = s.cpu_pct + "%";
  el("cpu_bar").style.width = s.cpu_pct + "%";
  el("ram_v").textContent = s.ram_used + " / " + s.ram_total + " ("+s.ram_pct+"%)";
  el("ram_bar").style.width = s.ram_pct + "%";
  el("disk_v").textContent = s.disk_used + " / " + s.disk_total + " ("+s.disk_pct+"%)";
  el("disk_bar").style.width = s.disk_pct + "%";
  el("rx_now").textContent = s.net_rx_rate;
  el("tx_now").textContent = s.net_tx_rate;
  el("rx_tot").textContent = s.net_rx_total;
  el("tx_tot").textContent = s.net_tx_total;
  document.querySelectorAll("#uptime_v").forEach(n=>n.textContent = ms(s.uptime));
}

function esc(s){return (s??"").toString().replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;","&gt;":">","\"":"&quot;","'":"&#39;"}[m]))}
function renderTables(t){
  // processes
  let html = "";
  if(t.procs && t.procs.length){
    for(const r of t.procs){
      html += `<tr><td class="fw-mono">${esc(r.pid)}</td><td>${esc(r.name)}</td><td class="text-secondary small">${esc(r.user)}</td><td class="text-end fw-mono">${esc(r.cpu)}</td><td class="text-end fw-mono">${esc(r.mem)}</td></tr>`;
    }
  } else { html = `<tr><td colspan="5" class="text-secondary">No data</td></tr>`; }
  el("tbl_procs").innerHTML = html;

  // connections
  html = "";
  if(t.conns && t.conns.length){
    for(const r of t.conns){
      html += `<tr><td>${esc(r.proto)}</td><td class="fw-mono text-break">${esc(r.laddr)}</td><td class="fw-mono text-break">${esc(r.raddr)}</td><td class="text-secondary small">${esc(r.status)}</td><td class="fw-mono">${esc(r.pid)}</td><td>${esc(r.pname)}</td></tr>`;
    }
  } else { html = `<tr><td colspan="6" class="text-secondary">No established connections</td></tr>`; }
  el("tbl_conns").innerHTML = html;

  // open ports
  html = "";
  if(t.ports && t.ports.length){
    for(const r of t.ports){
      html += `<tr><td>${esc(r.proto)}</td><td class="fw-mono text-break">${esc(r.laddr)}</td><td class="fw-mono">${esc(r.pid)}</td><td>${esc(r.pname)}</td></tr>`;
    }
  } else { html = `<tr><td colspan="4" class="text-secondary">No listening sockets</td></tr>`; }
  el("tbl_ports").innerHTML = html;

  // Tunnel status (LISTEN-only)
  const st = t.tunnel || {active:false, entries:[]};
  const dot = el("tunnel_dot"), txt = el("tunnel_text");
  if(st.active){ dot.classList.remove("bg-danger"); dot.classList.add("bg-success"); txt.textContent="Active"; }
  else{ dot.classList.remove("bg-success"); dot.classList.add("bg-danger"); txt.textContent="Inactive"; }
  html = "";
  if(st.entries && st.entries.length){
    for(const r of st.entries){
      html += `<tr><td>${esc(r.proto)}</td><td class="fw-mono">${esc(r.port)}</td><td class="fw-mono">${esc(r.pid)}</td></tr>`;
    }
  } else { html = `<tr><td colspan="3" class="text-secondary">No Waterwall listeners</td></tr>`; }
  el("tbl_tunnel").innerHTML = html;
}
</script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# ─── Routes ─────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("pw") == PASSWORD:
            session["auth"] = True
            return redirect(url_for("dashboard"))
        return render_template_string(LOGIN_HTML, error=True)
    return render_template_string(LOGIN_HTML, error=None)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    tinfo = read_tunnel_info()
    return render_template_string(
        DASH_HTML,
        files=[p.name for p in ordered_files()],
        tail_last=TAIL_LAST,
        poll_interval=POLL_INTERVAL,
        tinfo=tinfo,
        top_n=TOP_N
    )

# ─── Socket gate ────────────────────────────────────────────────────────────
@socketio.on("connect")
def ws_gate():
    if not session.get("auth"):
        return False
    stats, _ = get_stats(psutil.net_io_counters())
    tinfo = read_tunnel_info()
    emit("init", {
        "logs": [{"filename": p.name, "content": tail(p, TAIL_LAST)} for p in ordered_files()],
        "stats": stats,
        "tables": {
            "procs": get_top_processes(),
            "conns": get_live_connections(),
            "ports": get_open_ports(),
            "tunnel": get_tunnel_status(tinfo.get("port",""))
        }
    })

# ─── Runner ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    LOG_DIR.mkdir(exist_ok=True)
    threading.Thread(target=poll_loop, daemon=True).start()

    def get_local_ip():
        ip = "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
        except Exception:
            try:
                ip = socket.gethostbyname(socket.gethostname())
            except Exception:
                pass
        return ip

    ip = get_local_ip()
    print("\n========== ZEX Tunnel Web Panel V3 ==========")
    print(f"🚀  URL           : http://{ip}:{PORT}")
    print(f"🔁  Poll interval : {POLL_INTERVAL} sec")
    print(f"🔑  Login password: {PASSWORD}")
    print(f"🐞  Debug mode    : {DEBUG}")
    print("=============================================\n")

    socketio.run(app, host="0.0.0.0", port=PORT)
