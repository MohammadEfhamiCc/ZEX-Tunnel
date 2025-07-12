<!-- README.md for izex/zex-tunnel -->

<h1 align="center">
  ZEX Tunnel<br/>
  <sub><sup>WaterWall custom build &amp; easy installer</sup></sub>
</h1>

<p align="center">
  <a href="https://github.com/izex/zex-tunnel/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/github/license/izex/zex-tunnel?style=flat-square"></a>
  <a href="https://github.com/izex/zex-tunnel/releases/latest"><img alt="Latest Release" src="https://img.shields.io/github/v/release/izex/zex-tunnel?style=flat-square"></a>
  <a href="https://github.com/izex/zex-tunnel/stargazers"><img alt="Stars" src="https://img.shields.io/github/stars/izex/zex-tunnel?style=flat-square"></a>
</p>

---

## ✨ Overview

`zex-tunnel` is a **one-command installer** for a customised build of
[**WaterWall**](https://github.com/radkesvat/WaterWall) – an efficient traffic‐tunnelling &
obfuscation tool. The script ships *all binaries and configs in-repo* so no extra
ZIP download is needed. It also provides a colourful **TUI panel** (`zt`) and an
option to install the popular [**3x-ui**](https://github.com/MHSanaei/3x-ui) panel.

### Why bother?

* ⏱ **Quick setup** – Ubuntu 20.04 → 24.04 in under a minute.
* 🖥 **TUI control panel** with start/stop/restart & live status.
* ⚙️ **Interactive config** (Iran / Outside Iran, protocol, port, …).
* 🌐 Optional **web API** (Flask + Socket.IO).
* 🔄 **Reconfigure** any time – just rerun the installer from the panel.
* 🧹 **One-click uninstall** cleans every file & systemd unit.

---

## 🚀 Quick start

```bash
git clone https://github.com/izex/ZEX-Tunnel.git
cd ZEX-Tunnel
chmod +x *
sudo bash zex-tunnel-install.sh
```

### Requirements

* Ubuntu 20.04, 22.04, 23.10 or 24.04
* `sudo` privileges (root)
* \~150 MB free disk space & outbound HTTP access (for Python deps)

---

## 🖥 Using the panel

```bash
zt                 # open colourful menu
sudo systemctl status ztw   # WaterWall daemon
sudo systemctl status ztwl  # Web API (optional)
```

| Menu option                          | What it does                                                                            |
| ------------------------------------ | --------------------------------------------------------------------------------------- |
| **1 Reconfigure Tunnel**             | Runs installer again → services auto‑restart                                            |
| **2 Edit Web Config**                | Change API port & password                                                              |
| **3/4/5** Start / Stop / Restart     | Control the WaterWall systemd service (`ztw`)                                           |
| **7/8/9** Start / Stop / Restart API | Control the Flask web‑API service (`ztwl`)                                              |
| **11 Install 3x-ui Panel**           | Pulls & installs [https://github.com/MHSanaei/3x-ui](https://github.com/MHSanaei/3x-ui) |
| **10 Uninstall Everything**          | Removes binaries, configs, services & the panel launcher                                |

---

## 🛠 Project structure

```
.
├── zex-tunnel-install.sh   # main installer (run with sudo)
├── Waterwall               # upstream binary (executable)
├── web.py                  # Flask API entry‑point
├── web.zex                 # default web‑API config (port / password)
├── Iran/                   # configs for servers *inside* Iran
├── Kharej/                 # configs for servers *outside* Iran
├── LICENSE                 # MIT
└── README.md               # this file
```

> **Note:** WaterWall payload is committed directly – no Git LFS or extra download required.

---

## 🙏 Credits

| Project   | Author        | URL                                                                              |
| --------- | ------------- | -------------------------------------------------------------------------------- |
| WaterWall | **radkesvat** | [https://github.com/radkesvat/WaterWall](https://github.com/radkesvat/WaterWall) |
| 3x-ui     | **mhsanaei**  | [https://github.com/MHSanaei/3x-ui](https://github.com/MHSanaei/3x-ui)           |

---

## 📜 License

Released under the MIT License – see [`LICENSE`](LICENSE).
