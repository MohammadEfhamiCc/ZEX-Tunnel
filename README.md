# ZEX Tunnel V3
WaterWall custom build + one-command installer with a clean TUI panel.

---

## ✨ Overview
`zex-tunnel` provides a streamlined way to deploy a customised build of [WaterWall](https://github.com/radkesvat/WaterWall) for traffic tunnelling & obfuscation. It ships all required templates in-repo, installs services, and includes a powerful terminal panel (`zt`) for daily operations.

### What’s new in V3
- **Ubuntu 20.04 / 22.04 only** (systemd required)
- **Unified `config/`** folder (replaces `Iran/` & `Kharej/`)
- **Setup wizard** (review & confirm, English UI; shows local IPv4/IPv6)
- **Multi‑port (Iran)**: enter up to **10** ports (e.g., `443 2083 2087`)
- **Kharej** mode: no port prompt (share protocol with Iran)
- **Services renamed**: `zextunnel` (main), `zexweb` (web), `zexapi` (api); all auto‑start on boot
- **Two‑step uninstall** (type `UNINSTALL`)
- **Python deps** include `psutil`; JSON edits powered by `jq`
- Panel: modern layout, actions grouped, reconfigure from menu

---

## ✅ Requirements
- Ubuntu **20.04** or **22.04**
- `sudo` privileges (run installer as root)
- Internet access for Python dependencies

> The installer relies on **systemd** (service management).

---

## 🚀 Quick Start (Install)
```bash
git clone https://github.com/izex/ZEX-Tunnel.git
cd ZEX-Tunnel
chmod +x zex-tunnel-install.sh
sudo bash zex-tunnel-install.sh
```
The wizard will prompt for:
- **IRAN IP/Domain**
- **Kharej IP/Domain**
- **Protocol Number** (default **18**, recommended **< 100**, range **0–255**)
- **Ports (Iran mode only)**: single `443` or multi `443 2083 2087` (max **10**, unique, 1–65535)

**Files written to `/root/ZEX-Tunnel`** (copied from `config/` and customised):
- `core.json` → sets `"configs": ["config_ir.json"]` or `"config_kharej.json"`
- `config_ir.json` / `config_kharej.json` → placeholders replaced
- `config.zex` → 4 lines: `IRAN_IP`, `KHAREJ_IP`, `PROTOCOL`, `PORTS`

> Templates in `config/` are **never modified**—only copied out and edited in the main directory.

---

## 🧭 Setup Wizard (Preview)
```
====================================================
                 ZEX Tunnel V3 Setup
====================================================

IP V4: 203.0.113.10
IP V6: 2001:db8::10
---------------------------------------
Mode: choose server location
  [1] Iran
  [2] Kharej
```

- **Iran mode** → asks for ports; generates `inputN/outputN` pairs for each additional port.
- **Kharej mode** → no port input; enter the same protocol number used on the Iran server.

---

## 🖥 Panel
Open the panel:
```bash
zt
```
Key options:
- **1/2/3/4/5**: start/stop/restart/logs/kill (zextunnel)
- **6/7/8/9**: start/stop/restart/logs (zexweb)
- **10**: **Reconfigure** (wizard; rebuilds configs; restarts services)
- **11**: Edit Web Config (port/password)
- **15**: Reload panel info
- **16**: **Uninstall Everything** (two‑step)
- **17**: Install Sanaei **3x-ui**
- **18**: Reboot server

> `zexapi` is always‑on and hidden from the panel. All services start automatically on boot.

---

## 🔧 Services (systemd)
```bash
sudo systemctl status zextunnel   # WaterWall main
sudo systemctl status zexweb      # Flask web API
sudo systemctl status zexapi      # Binary API (always on)
```
Common actions:
```bash
sudo systemctl restart zextunnel zexweb
sudo systemctl enable  zextunnel zexweb zexapi
sudo journalctl -u zextunnel -n 200 --no-pager
```

---

## ♻️ Reconfigure / Update
- From panel: **Option 10** → runs the wizard again.
- Or via script:
```bash
sudo bash /root/ZEX-Tunnel/zex-tunnel-install.sh --reconfigure
```
What happens:
- Temporarily **disable/stop** `zextunnel` & `zexweb`
- Remove old `core.json`, `config_ir.json`/`config_kharej.json`, **`config.zex`**
- Copy fresh templates from `config/` and rebuild with new values
- **Enable + restart** services

---

## 🧹 Uninstall
From panel: **Option 16** → two-step confirmation (type `UNINSTALL`).  
Removes:
- Services: `zextunnel`, `zexweb`, `zexapi` (+ legacy `ztw`, `ztwl` if present)
- Unit files and the panel launcher
- `/root/ZEX-Tunnel` directory

---

## 🔐 Notes & Tips
- Use non‑privileged ports only if your network rules require; defaults like **443** are fine.
- Ensure your firewall allows chosen ports (e.g., `ufw allow 443`), and that your IR/Kharej IPs are reachable.
- Keep your protocol number aligned between Iran/Kharej (recommended `< 100`).

---

## 📁 Repo layout (V3)
```
.
├── zex-tunnel-install.sh        # installer / reconfigure
├── Waterwall                    # main binary
├── api                          # zexapi binary
├── web.py                       # Flask web API
├── web.zex                      # default web API config
├── config/                      # templates (read-only)
│   ├── core.json
│   ├── config_ir.json
│   └── config_kharej.json
└── README.md
```

---

## 🙏 Credits
- WaterWall — https://github.com/radkesvat/WaterWall  
- 3x-ui — https://github.com/MHSanaei/3x-ui

MIT Licensed.
