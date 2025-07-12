#!/usr/bin/env bash
set -euo pipefail

VERSION="V2.250706"
BASE_DIR="/root/ZEX-Tunnel"
PANEL_PATH="/usr/local/bin/zt"

reconfigure_tunnel() {
  echo -e "\n🧹 Removing old config files..."
  rm -f "$BASE_DIR/core.json" "$BASE_DIR/config_ir.json" "$BASE_DIR/config_kharej.json"

  clear
  echo "========================"
  echo "   ZEX Tunnel Config"
  echo "========================"
  printf 'Select server location:\n  [1] Iran\n  [2] Outside Iran\n> '
  read -r LOCATION_CHOICE

  printf 'IRAN IP/Domain: '
  read -r IRAN_IP
  IRAN_IP="${IRAN_IP//\\}"

  printf 'Kharej IP/Domain: '
  read -r KHAREJ_IP
  KHAREJ_IP="${KHAREJ_IP//\\}"

  echo 'Protocol Numbers Info: https://en.wikipedia.org/wiki/List_of_IP_protocol_numbers'
  printf 'Protocol Number (Default 18): '
  read -r PROTOCOL; [[ -z "$PROTOCOL" ]] && PROTOCOL=18

  printf 'Port Number (Default 443): '
  read -r PORT; [[ -z "$PORT" ]] && PORT=443

  if [[ "$LOCATION_CHOICE" == "1" ]]; then
    cp "$BASE_DIR/Iran/config_ir.json" "$BASE_DIR/config_ir.json"
    cp "$BASE_DIR/Iran/core.json" "$BASE_DIR/core.json"
    CONF_FILE="$BASE_DIR/config_ir.json"
  elif [[ "$LOCATION_CHOICE" == "2" ]]; then
    cp "$BASE_DIR/Kharej/config_kharej.json" "$BASE_DIR/config_kharej.json"
    cp "$BASE_DIR/Kharej/core.json" "$BASE_DIR/core.json"
    CONF_FILE="$BASE_DIR/config_kharej.json"
  else
    echo "❌ Invalid selection."; exit 1
  fi

  sed -i -e "s#__IP_IRAN__#${IRAN_IP}#g" \
         -e "s#__IP_KHAREJ__#${KHAREJ_IP}#g" \
         -e "s#__PROTOCOL__#${PROTOCOL}#g" \
         -e "s#__PORT__#${PORT}#g" "$CONF_FILE"

  printf '%s\n%s\n%s\n%s\n' "$IRAN_IP" "$KHAREJ_IP" "$PROTOCOL" "$PORT" > "$BASE_DIR/config.zex"
  echo "✅ Tunnel reconfigured successfully."
}

# ─────── فقط ری‌کانفیگ ───────
if [[ "${1:-}" == "--reconfigure" ]]; then
  reconfigure_tunnel
  systemctl restart ztw ztwl
  exit 0
fi

[[ $EUID -eq 0 ]] || { echo "❌ Run as root."; exit 1; }

echo "🔧 Installing dependencies..."
apt update -y
apt install -y python3 python3-pip curl
pip3 install -U flask flask-socketio eventlet

echo "🛠 Setting up systemd services..."

cat >/etc/systemd/system/ztw.service <<EOF
[Unit]
Description=ZEX Waterwall
After=network.target

[Service]
Type=simple
WorkingDirectory=$BASE_DIR
ExecStart=$BASE_DIR/Waterwall
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/ztwl.service <<EOF
[Unit]
Description=ZEX Waterwall Web
After=network.target

[Service]
Type=simple
WorkingDirectory=$BASE_DIR
ExecStart=/usr/bin/python3 $BASE_DIR/web.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ztw ztwl

reconfigure_tunnel
systemctl restart ztw ztwl

echo -e "\n✅ Installation complete. Run \e[33mzt\e[0m to open the panel."
