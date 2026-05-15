#!/bin/bash
PROXY_SCRIPT_NAME="server-proxy.py"
PROXY_SERVICE_NAME="mc-server-proxy.service"
PROXY_SCRIPT_INSTALL_DIR="/opt/mc-server-proxy/"
PROXY_SERVICE_INSTALL_DIR="/etc/systemd/system/"

SERVER_SCRIPT_NAME="server-regulator.py"
SERVER_SCRIPT_INSTALL_DIR="/opt/mc-server-regulator"

if ! command -v apt &>/dev/null; then
  echo "The system is not using apt."
  exit 0
fi

if [[ "$#" -lt 1 || "$1" != "proxy" && "$1" != "server" ]]; then
  echo "Try \"sudo ./install.sh <proxy || server>\""
  exit 0
fi

if [[ "$1" = "proxy" ]]; then
  sudo apt update
  sudo apt install -y python3 python3-venv

  sudo mkdir -p "$PROXY_SCRIPT_INSTALL_DIR"
  sudo cp "$PROXY_SCRIPT_NAME" "$PROXY_SCRIPT_INSTALL_DIR" # do I need to do permission setting for the script in /opt or is it automatic?
  sudo python3 -m venv "$PROXY_SCRIPT_INSTALL_DIR/venv"
  sudo "$PROXY_SCRIPT_ISNTALL_DIR/venv/bin/pip" install -r requirements.txt

  sudo mkdir -p "$PROXY_SERVICE_INSTALL_DIR"
  sudo cp "$PROXY_SERVICE_NAME" "$PROXY_SERVICE_INSTALL_DIR"
  sudo chown root:root "$PROXY_SERVICE_INSTALL_DIR$PROXY_SERVICE_NAME"
  sudo chmod 644 "$PROXY_SERVICE_INSTALL_DIR$PROXY_SERVICE_NAME"
  sudo systemctl daemon-reload
  sudo systemctl enable "$PROXY_SERVICE_NAME"
  sudo systemctl start "$PROXY_SERVICE_NAME"

elif [[ "$1" = "server" ]]; then
  sudo apt update
  sudo apt install -y python3

  sudo mkdir -p "$SERVER_SCRIPT_INSTALL_DIR"
  sudo cp "$SERVER_SCRIPT_NAME" "$SERVER_SCRIPT_INSTALL_DIR"
  (
    crontab -l 2>/dev/null
    echo "*/5 * * * * sudo /home/gal/tools/server-regulator/venv/bin/python /home/gal/tools/server-regulator/server-regulator.py >> /home/gal/tools/server-regulator/regulator.log 2>&1"
  ) | crontab -

fi
