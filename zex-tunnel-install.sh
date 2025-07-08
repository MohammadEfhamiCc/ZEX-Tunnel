#!/usr/bin/env bash
#─────────────────────────────────────────────────────────────────
#  ZEX Tunnel – WaterWall custom installer
#  Author : izex        •  Version : 2.250706
#  License: MIT         •  Requires: sudo (root privileges)
#─────────────────────────────────────────────────────────────────
set -euo pipefail

VERSION="2.250706"
BASE_DIR="/root/ZEX-Tunnel"          # final installation path
PANEL_PATH="/usr/local/bin/zt"       # launcher for the TUI panel
INSTALL_COPY="/root/zex-tunnel-install.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "===== Installing ZEX Tunnel ${VERSION} ====="

#──────────────────── Pre-checks & cleanup ────────────────────
[[ $EUID -eq 0 ]] || { echo "❌  Please run as root (use sudo)."; exit 1; }

systemctl disable --now ztw ztwl >/dev/null 2>&1 || true
rm -f /etc/systemd/system/ztw.service /etc/systemd/system/ztwl.service
rm -rf "$BASE_DIR"
rm -f "$PANEL_PATH"
systemctl daemon-reload

UBUNTU_VERSION=$(grep '^VERSION_ID=' /etc/os-release | cut -d'=' -f2 | tr -d '"')
case "$UBUNTU_VERSION" in 20.*|21.*|22.*|23.*|24.*) ;; *)
  echo "❌  Unsupported Ubuntu version: ${UBUNTU_VERSION}"; exit 1 ;;
esac

#──────────────────── Dependencies ────────────────────────────
apt update -y
apt install -y python3 python3-pip curl
pip3 install -U flask flask-socketio eventlet

#──────────────────── Copy WaterWall payload ──────────────────
mkdir -p "$BASE_DIR"
echo "→ Copying WaterWall files into ${BASE_DIR}"
for item in "$SCRIPT_DIR"/*; do
  name="$(basename "$item")"
  [[ "$name" == "$(basename "$0")" || "$name" == "README.md" || "$name" == ".git" ]] && continue
  cp -r "$item" "$BASE_DIR/"
done

# Remove old placeholder configs that come with the payload
rm -f "$BASE_DIR"/config_*.json "$BASE_DIR/core.json"

#──────────────────── Interactive configuration ───────────────
clear
echo "========================="
echo "   ZEX Tunnel Config"
echo "========================="
printf 'Select server location:\n  [1] Iran\n  [2] Outside Iran\n> '
read -r LOCATION_CHOICE
printf 'IRAN IP / Domain  : ' ; read -r IRAN_IP
printf 'Foreign IP / Host : ' ; read -r FOREIGN_IP
echo 'Protocol numbers list: https://en.wikipedia.org/wiki/List_of_IP_protocol_numbers'
printf 'Protocol Number (default 18): ' ; read -r PROTOCOL ; [[ -z "$PROTOCOL" ]] && PROTOCOL=18
printf 'Port Number (default 443): '   ; read -r PORT     ; [[ -z "$PORT"     ]] && PORT=443

if [[ "$LOCATION_CHOICE" == "1" ]]; then
  cp "$BASE_DIR/Iran/config_ir.json"   "$BASE_DIR/"
  cp "$BASE_DIR/Iran/core.json"        "$BASE_DIR/"
  CONF_FILE="$BASE_DIR/config_ir.json"
elif [[ "$LOCATION_CHOICE" == "2" ]]; then
  cp "$BASE_DIR/Kharej/config_kharej.json" "$BASE_DIR/"
  cp "$BASE_DIR/Kharej/core.json"          "$BASE_DIR/"
  CONF_FILE="$BASE_DIR/config_kharej.json"
else
  echo "❌  Invalid selection"; exit 1
fi

# Apply user values to the chosen config
sed -i -e "s#__IP_IRAN__#${IRAN_IP}#g" \
       -e "s#__IP_KHAREJ__#${FOREIGN_IP}#g" \
       -e "s#__PROTOCOL__#${PROTOCOL}#g" \
       -e "s#__PORT__#${PORT}#g"           "$CONF_FILE"

# Flat file for the TUI panel to read
printf '%s\n%s\n%s\n%s\n' "$IRAN_IP" "$FOREIGN_IP" "$PROTOCOL" "$PORT" > "$BASE_DIR/config.zex"
chmod -R +x "$BASE_DIR"

#──────────────────── systemd units ───────────────────────────
cat > /etc/systemd/system/ztw.service <<EOF
[Unit]
Description=ZEX WaterWall
After=network.target

[Service]
Type=simple
WorkingDirectory=$BASE_DIR
ExecStart=$BASE_DIR/Waterwall
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/ztwl.service <<EOF
[Unit]
Description=ZEX WaterWall Web API
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

#──────────────────── TUI panel launcher (`zt`) ───────────────
cat > "$PANEL_PATH" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
VERSION="2.250706"
BASE_DIR="/root/ZEX-Tunnel"
CONFIG_FILE="$BASE_DIR/config.zex"
WEB_CONFIG="$BASE_DIR/web.zex"
CLR(){ printf "\e[%sm%b\e[0m" "$1" "$2"; }
banner(){ CLR "36;1" "╔══════════════════════════════════════════════════╗\n"; CLR "33;1" "          🚀  ZEX Tunnel Panel $VERSION 🚀\n"; CLR "36;1" "╚══════════════════════════════════════════════════╝\n"; }

while true; do
  clear; banner
  LOCATION="Unknown"
  [[ -f "$BASE_DIR/config_ir.json" ]]     && LOCATION="Iran"
  [[ -f "$BASE_DIR/config_kharej.json" ]] && LOCATION="Outside Iran"
  IRAN_IP="N/A"; FOREIGN_IP="N/A"; PROTOCOL="N/A"; PORT="N/A"
  [[ -f "$CONFIG_FILE" ]] && readarray -t cfg < "$CONFIG_FILE" && {
    IRAN_IP="${cfg[0]}"; FOREIGN_IP="${cfg[1]}"; PROTOCOL="${cfg[2]}"; PORT="${cfg[3]}";
  }
  CONFIG_ADDR="N/A"
  [[ -f "$BASE_DIR/config_ir.json" ]]     && CONFIG_ADDR="$BASE_DIR/config_ir.json"
  [[ -f "$BASE_DIR/config_kharej.json" ]] && CONFIG_ADDR="$BASE_DIR/config_kharej.json"

  printf "\n"; CLR 35 "🛰  Server Location"; printf " : %s\n" "$LOCATION"
  CLR 35 "🌐  IRAN IP / Domain";      printf " : %s\n" "$IRAN_IP"
  CLR 35 "🌍  Foreign IP / Host";     printf " : %s\n" "$FOREIGN_IP"
  CLR 35 "🔢  Protocol Number";       printf " : %s\n" "$PROTOCOL"
  CLR 35 "🔉  Tunnel Port";           printf " : %s\n" "$PORT"
  CLR 35 "📄  Config File";           printf " : %s\n" "$CONFIG_ADDR"

  systemctl is-active --quiet ztw  && ZTW_STATUS=$(CLR 32 active) || ZTW_STATUS=$(CLR 31 inactive)
  systemctl is-active --quiet ztwl && ZTWL_STATUS=$(CLR 32 active) || ZTWL_STATUS=$(CLR 31 inactive)

  printf "\n"; CLR 34 "┌────── ZEX WaterWall ──────┐\n"
  printf "🚀  Status              : %b\n" "$ZTW_STATUS"
  printf "🛠  Binary              : $BASE_DIR/Waterwall\n"
  printf "🪪  Service Name        : ztw\n"
  CLR 34 "└──────────────────────────────┘\n"

  WEB_PORT="N/A"; WEB_PASS="N/A"
  [[ -f "$WEB_CONFIG" ]] && readarray -t wcfg < "$WEB_CONFIG" && {
    WEB_PORT="${wcfg[0]}"; WEB_PASS="${wcfg[2]}";
  }
  CLR 36 "\n┌── ZEX WaterWall Web API ──┐\n"
  printf "🔌  Port                : %s\n" "$WEB_PORT"
  printf "🔑  Web Login Password  : %s\n" "$WEB_PASS"
  printf "📡  Status              : %b\n" "$ZTWL_STATUS"
  printf "🪪  Service Name        : ztwl\n"
  CLR 36 "└────────────────────────────┘\n"

  CLR 33 "\nOptions:\n"
  for x in \
    "1 Reconfigure Tunnel" \
    "2 Edit Web Config" \
    "3 Start ZEX WaterWall" \
    "4 Stop ZEX WaterWall" \
    "5 Restart ZEX WaterWall" \
    "6 Kill WaterWall Processes" \
    "7 Start Web API" \
    "8 Stop Web API" \
    "9 Restart Web API" \
    "10 Uninstall Everything" \
    "11 Install Sanaei 3x-ui Panel" \
    "12 Reload Panel" \
    "0 Exit"; do
      printf " [%s] %s\n" "${x%% *}" "${x#* }"
  done
  printf "\nSelect an option: "; read -r opt
  case "$opt" in
    1) sudo bash /root/zex-tunnel-install.sh; exit ;;
    2)
       read -rp "New Web Port: " nport
       read -rp "New Web Password: " npass
       if [[ -f "$WEB_CONFIG" ]]; then
         readarray -t arr < "$WEB_CONFIG"
         arr[0]="$nport"; arr[2]="$npass"
         printf '%s\n%s\n%s\n%s\n' "${arr[0]}" "${arr[1]}" "${arr[2]}" "${arr[3]}" > "$WEB_CONFIG"
         CLR 32 "Web config updated.\n"
       else CLR 31 "web.zex not found.\n"; fi
       read -rp "Press Enter to continue" ;;
    3) sudo systemctl start ztw;   read -rp "Press Enter" ;;
    4) sudo systemctl stop ztw;    read -rp "Press Enter" ;;
    5) sudo systemctl restart ztw; read -rp "Press Enter" ;;
    6) sudo pkill Waterwall || true; read -rp "Press Enter" ;;
    7) sudo systemctl start ztwl;  read -rp "Press Enter" ;;
    8) sudo systemctl stop ztwl;   read -rp "Press Enter" ;;
    9) sudo systemctl restart ztwl; read -rp "Press Enter" ;;
    10)
       sudo systemctl disable --now ztw ztwl || true
       sudo rm -f /etc/systemd/system/ztw.service /etc/systemd/system/ztwl.service
       sudo systemctl daemon-reload
       sudo rm -rf "$BASE_DIR" "$CONFIG_FILE" "$WEB_CONFIG"
       sudo rm -f /usr/local/bin/zt
       CLR 32 "Uninstalled.\n"; exit ;;
    11) CLR 36 "Installing Sanaei 3x-ui Panel...\n"; bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh); exit ;;
    12) continue ;;   # reload panel
    0) exit ;;
    *) CLR 31 "Invalid option\n"; read -rp "Press Enter" ;;
  esac
done
EOS

chmod +x "$PANEL_PATH"
cp "$(realpath "$0")" "$INSTALL_COPY"

echo -e "\n✅  Installation complete. Run \e[33mzt\e[0m to open the panel."
