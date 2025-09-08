# ZEX Tunnel V3(build 20250908)
WaterWall custom build + one-command installer.

<p align="center">
  <img alt="ZEX Tunnel" src="https://img.shields.io/badge/ZEX-Tunnel%20V3-blue?style=for-the-badge">
  <img alt="Ubuntu" src="https://img.shields.io/badge/Ubuntu-20.04%2F22.04-orange?style=for-the-badge">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge">
</p>

---

## ✨ Overview
`zex-tunnel` provides a streamlined way to deploy a customised build of [WaterWall](https://github.com/radkesvat/WaterWall) for traffic tunnelling & obfuscation. It ships all required templates in-repo, installs services, and includes a powerful terminal panel (`zt`) for daily operations.

### Highlights in V3
- **Ubuntu 20.04 / 22.04** only (systemd required)
- **Unified `config/`** folder (single source of truth for templates)
- **Setup wizard** (English UI, shows local IPv4/IPv6, review & confirm)
- **Multi‑port support**: enter up to **10** ports (e.g., `443 2083 2087`)
- **Services** renamed & streamlined: main tunnel + web API (auto‑start on boot)
- **Two‑step uninstall** (type `UNINSTALL`)
- Python deps include **psutil**; JSON edits via **jq**
- Modern **TUI panel** with grouped actions

> The installer copies templates from `config/` to the main directory and edits only the copies. Files inside `config/` are never modified.

---

## ✅ Requirements
- Ubuntu **20.04** or **22.04** (with systemd)
- `sudo` privileges
---

## 🚀 Install
```bash
git clone https://github.com/izex/ZEX-Tunnel.git
cd ZEX-Tunnel
chmod +x *
sudo bash zex-tunnel-install.sh
```

The wizard prompts for:
- Two server endpoints (**IP/Domain** for each side)
- **Protocol Number** (default **18**, recommended **< 100**, range **0–255**)
- **Ports** (optional multi‑port): single `443` or multi `443 2083 2087` (max **10**, unique, 1–65535)

It writes to `/root/ZEX-Tunnel`:
- `core.json` → selects the active runtime config
- a runtime config file (copied from `config/` and customised)
- `config.zex` → 4 lines: `ENDPOINT_A`, `ENDPOINT_B`, `PROTOCOL`, `PORTS`

---

## 🧭 Setup Wizard (preview)
```
====================================================
                 ZEX Tunnel V3 Setup
====================================================

IP V4: 203.0.113.10
IP V6: 2001:db8::10
---------------------------------------
Mode: choose server location
  [1] Server A role
  [2] Server B role
```
- Ports are optional and support **multi‑port** in one go.
- A review screen summarizes your choices before applying.

---

## 🖥 Panel
Open the panel:
```bash
zt
```
Key options:
- Start / Stop / Restart / Logs for the tunnel service
- Start / Stop / Restart / Logs for the web API
- **Reconfigure** (re‑runs the wizard and restarts services)
- Edit Web Config (port/password)
- Reload panel info, Uninstall Everything (two‑step), Install 3x‑ui, Reboot

**Services (systemd)**
```bash
sudo systemctl status zextunnel   # main tunnel
sudo systemctl status zexweb      # web API
sudo systemctl restart zextunnel zexweb
sudo systemctl enable  zextunnel zexweb
sudo journalctl -u zextunnel -n 200 --no-pager
```

---

## ♻️ Reconfigure
From panel (**Reconfigure**) or via script:
```bash
sudo bash /root/ZEX-Tunnel/zex-tunnel-install.sh --reconfigure
```
Flow:
1) Temporarily disable/stop services  
2) Remove old `core.json`, runtime config, **`config.zex`**  
3) Copy fresh templates from `config/` and rebuild with new values  
4) Enable + restart services

---

## 🧹 Uninstall
From panel (**Uninstall Everything**) → type `UNINSTALL` to confirm.  
Removes services, unit files, panel launcher, and `/root/ZEX-Tunnel` directory.

---

## 🗺 Roadmap (Next Release)
**ZEX Tunnel Config** (Windows) — a simple GUI that configures the tunnel for you.  
Just enter the **IP**, **SSH port**, **username**, and **password** for both servers; the app SSHs in and performs the setup automatically.

---

## 📁 Repo Layout (V3)
```
.
├── zex-tunnel-install.sh        # installer / reconfigure
├── Waterwall                    # main binary
├── web.py                       # Flask web API
├── web.zex                      # default web API config
├── config/                      # templates (read‑only)
│   ├── core.json
│   ├── config_ir.json
│   └── config_kharej.json
└── README.md
```

---

## 🙏 Credits & License
- WaterWall — https://github.com/radkesvat/WaterWall  
- 3x-ui — https://github.com/MHSanaei/3x-ui  
MIT Licensed.
