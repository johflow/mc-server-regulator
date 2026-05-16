#!/bin/bash
set -euo pipefail

if [[ ! -f "config.env" ]]; then
  echo "ERROR: config.env file not found! Please create it."
  exit 1
fi

source config.env

if [[ "$EUID" -ne 0 ]]; then
  echo "Please run this script as root (use sudo)."
  exit 1
fi

if ! command -v apt &>/dev/null; then
  echo "The system is not using apt."
  exit 1
fi

if [[ "$#" -lt 1 || "$1" != "proxy" && "$1" != "server" ]]; then
  echo "Try \" ./install.sh <proxy || server>\""
  exit 1
fi

if [[ "$1" = "proxy" ]]; then
  apt update
  apt install -y python3 python3-venv

  mkdir -p "$PROXY_SCRIPT_INSTALL_DIR"
  cp "$PROXY_SCRIPT_NAME" "$PROXY_SCRIPT_INSTALL_DIR/"
  chown root:root "$PROXY_SCRIPT_INSTALL_DIR/$PROXY_SCRIPT_NAME"
  chmod 644 "$PROXY_SCRIPT_INSTALL_DIR/$PROXY_SCRIPT_NAME"
  python3 -m venv "$PROXY_SCRIPT_INSTALL_DIR/venv"
  "$PROXY_SCRIPT_INSTALL_DIR/venv/bin/pip" install -r requirements.txt

  mkdir -p "$PROXY_SERVICE_INSTALL_DIR"
  sed -e "s|__INSTALL_DIR__|${PROXY_SCRIPT_INSTALL_DIR}|g" \
    -e "s|__SCRIPT_NAME__|${PROXY_SCRIPT_NAME}|g" \
    "$PROXY_SERVICE_NAME.template" >"$PROXY_SERVICE_INSTALL_DIR/$PROXY_SERVICE_NAME"
  chown root:root "$PROXY_SERVICE_INSTALL_DIR/$PROXY_SERVICE_NAME"
  chmod 644 "$PROXY_SERVICE_INSTALL_DIR/$PROXY_SERVICE_NAME"
  systemctl daemon-reload
  systemctl enable "$PROXY_SERVICE_NAME"
  systemctl start "$PROXY_SERVICE_NAME"

elif [[ "$1" = "server" ]]; then
  apt update
  apt install -y python3

  mkdir -p "$SERVER_SCRIPT_INSTALL_DIR"
  cp "$SERVER_SCRIPT_NAME" "$SERVER_SCRIPT_INSTALL_DIR/"
  if ! crontab -l 2>/dev/null | grep -q "$SERVER_SCRIPT_NAME"; then
    echo "Adding cron job..."
    (
      crontab -l 2>/dev/null
      echo "*/5 * * * * /usr/bin/python3 $SERVER_SCRIPT_INSTALL_DIR/$SERVER_SCRIPT_NAME >> /var/log/mc-server-regulator.log 2>&1"
    ) | crontab -
  else
    echo "Cron job already exists. Skipping."
  fi
fi

exit 0
