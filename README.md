# ZEX Tunnel Installer (WaterWall Custom)
## About 📖

This repository hosts \*\*a streamlined Bash installer for a personalised build of \*\*[**WaterWall**](https://github.com/radkesvat/WaterWall). On top of making installation almost one‑click for Ubuntu 20.04‑24.04, the menu also lets you optionally install the popular [3x‑ui](https://github.com/MHSanaei/3x-ui) X‑Ray (V2Ray) panel.

* **Upstream code‑base:** WaterWall by **radkesvat** – traffic tunnelling & obfuscation.
* **Add‑on:** One‑command installation of **3x‑ui** panel by **mhsanaei**.
* **Your twist:** Interactive installer, systemd units, bilingual TUI panel, web API.

---

## Features ✨

| Category                 | Highlights                                                                                                        |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| **Installer**            | – Works on Ubuntu 20.04 → 24.04– Interactive config (Iran / Outside Iran)– Auto‑generated `ztw` & `ztwl` services |
| **TUI Panel (**\`\`**)** | – Neat ANSI UI for start / stop / restart– Edit web API port & password– Optional **3x‑ui** installer             |
| **Web API**              | – Flask + Socket.IO– Runs as `ztwl` service                                                                       |
| **Clean uninstall**      | Removes everything in one click                                                                                   |

---

## Quick Install 🚀

```bash
curl -sL https://raw.githubusercontent.com/USER/REPO/main/zex-tunnel-install.sh | sudo bash
```

> Replace \`\` with this repository path. The script will fetch `zex_waterwall.zip` from the latest GitHub Release.

---

## Usage 🛠

After installation:

```bash
zt       # open the interactive panel
sudo systemctl status ztw    # WaterWall daemon
sudo systemctl status ztwl   # Web API
```

To uninstall completely, choose **10 Uninstall Everything** from the panel.

---

## Release Assets 📦

Binary builds are kept under the Release tab as versioned assets. The installer always downloads the ZIP that matches the tag (`v2.250706`, `v2.250901`, …).

---

## Credits 🙏

* **WaterWall** – © radkesvat – [https://github.com/radkesvat/WaterWall](https://github.com/radkesvat/WaterWall)
* **3x‑ui** – © mhsanaei – [https://github.com/MHSanaei/3x-ui](https://github.com/MHSanaei/3x-ui)
* Bash, Python 3, Flask, eventlet, Socket.IO.

---

## License 📜

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.

---

# فارسی 🇮🇷

## معرفی

این مخزن شامل **اسکریپت نصب خودکار «زِکس تونل»** است که بر پایهٔ پروژهٔ [WaterWall](https://github.com/radkesvat/WaterWall) نوشته شده و مراحل نصب را روی اوبونتو ۲۰٫۰۴ تا ۲۴٫۰۴ به چند کلیک کاهش می‌دهد. همچنین در منوی پنل می‌توانید **پنل X‑Ray (3x‑ui)** را نیز تنها با یک گزینه نصب کنید.

### تفاوت با نسخهٔ اصلی

* گفت‌وگوی تعاملی (انتخاب «داخل ایران / خارج ایران»)
* ایجاد خودکار سرویس‌های systemd (`ztw`, `ztwl`)
* پنل خط فرمان (TUI) دو زبانه با قابلیت مدیریت سرویس‌ها
* قابلیت نصب **3x‑ui** فقط با یک گزینه

## امکانات کلیدی

| دسته                   | توضیح                                                              |
| ---------------------- | ------------------------------------------------------------------ |
| **نصب سریع**           | پشتیبانی از Ubuntu 20.04 تا 24.04؛ دانلود ZIP از Release همین مخزن |
| **پنل TUI (**\`\`**)** | شروع / توقف / ریستارت؛ ویرایش پورت و رمز وب؛ نصب 3x‑ui             |
| **API وب**             | نوشته شده با Flask و Socket.IO؛ اجرا به صورت سرویس `ztwl`          |
| **حذف کامل**           | یک گزینه برای پاک‌کردن همه‌چیز                                     |

## نصب سریع

```bash
curl -sL https://raw.githubusercontent.com/USER/REPO/main/zex-tunnel-install.sh | sudo bash
```

## پس از نصب

```bash
zt                     # ورود به پنل
sudo systemctl status ztw   # وضعیت WaterWall
sudo systemctl status ztwl  # وضعیت API وب
```

برای حذف، در منوی پنل گزینهٔ **۱۰ Uninstall Everything** را بزنید.

## تشکر و قدردانی

* **WaterWall** توسط radkesvat
* **3x‑ui** توسط mhsanaei

## مجوز

این پروژه تحت **مجوز MIT** منتشر شده است.
