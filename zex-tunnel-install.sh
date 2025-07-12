#!/usr/bin/env bash
set -euo pipefail
VERSION="V2.250706"
BASE_DIR="/root/ZEX-Tunnel"
CONFIG_FILE="$BASE_DIR/config.zex"
WEB_CONFIG="$BASE_DIR/web.zex"
CLR(){ printf "\e[%sm%b\e[0m" "$1" "$2"; }
banner(){ CLR "36;1" "╔══════════════════════════════════════════════════╗\n"; CLR "33;1" "          🚀  ZEX Tunnel Panel $VERSION 🚀\n"; CLR "36;1" "╚══════════════════════════════════════════════════╝\n"; }

while true; do
  clear; banner
  LOCATION="Unknown"
  [[ -f "$BASE_DIR/config_ir.json" ]] && LOCATION="Iran"
  [[ -f "$BASE_DIR/config_kharej.json" ]] && LOCATION="Outside"
  IRAN_IP="N/A"; KHAREJ_IP="N/A"; PROTOCOL="N/A"; PORT="N/A"
  [[ -f "$CONFIG_FILE" ]] && readarray -t cfg < "$CONFIG_FILE" && IRAN_IP="${cfg[0]}" && KHAREJ_IP="${cfg[1]}" && PROTOCOL="${cfg[2]}" && PORT="${cfg[3]}"
  CONFIG_ADDR="N/A"
  [[ -f "$BASE_DIR/config_ir.json" ]] && CONFIG_ADDR="$BASE_DIR/config_ir.json"
  [[ -f "$BASE_DIR/config_kharej.json" ]] && CONFIG_ADDR="$BASE_DIR/config_kharej.json"

  printf "\n"; CLR 35 "🛰  Server Location"; printf " : %s\n" "$LOCATION"
  CLR 35 "🌐  IRAN IP/Domain";        printf " : %s\n" "$IRAN_IP"
  CLR 35 "🌍  Kharej IP/Domain";      printf " : %s\n" "$KHAREJ_IP"
  CLR 35 "🔢  Protocol Number";       printf " : %s\n" "$PROTOCOL"
  CLR 35 "🔉  Tunnel Port";           printf " : %s\n" "$PORT"
  CLR 35 "📄  Config Address";        printf " : %s\n" "$CONFIG_ADDR"

  systemctl is-active --quiet ztw  && ZTW_STATUS=$(CLR 32 active) || ZTW_STATUS=$(CLR 31 inactive)
  systemctl is-active --quiet ztwl && ZTWL_ST=$(CLR 32 active)    || ZTWL_ST=$(CLR 31 inactive)

  printf "\n"; CLR 34 "┌────── ZEX Waterwall ──────┐\n"
  printf "🚀  Status              : %b\n" "$ZTW_STATUS"
  printf "🛠  Binary              : $BASE_DIR/Waterwall\n"
  printf "🪪  Service Name        : ztw\n"
  CLR 34 "└──────────────────────────────┘\n"

  WEB_PORT="N/A"; WEB_PASS="N/A"
  [[ -f "$WEB_CONFIG" ]] && readarray -t wcfg < "$WEB_CONFIG" && WEB_PORT="${wcfg[0]}" && WEB_PASS="${wcfg[2]}"
  CLR 36 "\n┌── ZEX Waterwall Web API ──┐\n"
  printf "🔌  Port                : %s\n" "$WEB_PORT"
  printf "🔑  Web Login Password  : %s\n" "$WEB_PASS"
  printf "📡  Status              : %b\n" "$ZTWL_ST"
  printf "🪪  Service Name        : ztwl\n"
  CLR 36 "└────────────────────────────┘\n"

  CLR 33 "\nOptions:\n"
  for x in \
    "1 Reconfigure Tunnel" \
    "2 Edit Web Config" \
    "3 Start ZEX Waterwall" \
    "4 Stop ZEX Waterwall" \
    "5 Restart ZEX Waterwall" \
    "6 Kill All Waterwall Processes" \
    "7 Start ZEX Waterwall Web" \
    "8 Stop ZEX Waterwall Web" \
    "9 Restart ZEX Waterwall Web" \
    "10 Uninstall Everything" \
    "11 Install Sanaei Xray Panel" \
    "12 Reload Panel Info" \
    "0 Exit"; do
      printf " [%s] %s\n" "${x%% *}" "${x#* }"
  done
  printf "\nSelect an option: "; read -r opt
  case "$opt" in
    1)
       sudo bash /root/zex-tunnel-install.sh
       sudo systemctl restart ztw ztwl
       exit ;;
    2)
       read -rp "New Web Port: " nport
       read -rp "New Web Password: " npass
       if [[ -f "$WEB_CONFIG" ]]; then
         readarray -t arr < "$WEB_CONFIG"
         arr[0]="$nport"; arr[2]="$npass"
         printf '%s\n%s\n%s\n%s\n' "${arr[0]}" "${arr[1]}" "${arr[2]}" "${arr[3]}" > "$WEB_CONFIG"
         CLR 32 "Web config updated.\n"
         sudo systemctl restart ztwl
       else
         CLR 31 "web.zex not found.\n"
       fi
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
       sudo rm -rf "$BASE_DIR/config.zex" "$BASE_DIR/core.json" "$BASE_DIR/config_ir.json" "$BASE_DIR/config_kharej.json"
       sudo rm -f /usr/local/bin/zt "$WEB_CONFIG"
       CLR 32 "Uninstalled.\n"; exit ;;
    11)
       CLR 36 "Installing Sanaei Xray Panel...\n"
       bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)
       exit ;;
    12) continue ;;
    0) exit ;;
    *) CLR 31 "Invalid option\n"; read -rp "Press Enter" ;;
  esac
done
