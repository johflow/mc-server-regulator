#!/bin/bash
set -euo pipefail

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

if [[ ! -f ".env" ]]; then
  if [[ "$#" -lt 2 ]]; then
    echo "ERROR: .env file not found! Please create or pass it in as an argument."
    echo "Argument format is: \"sudo ./deploy.sh <proxy || server> <filename.env>\""
    exit 1
  elif [[ ! -f "$2" ]]; then
    echo "ERROR: the environmental variable file "$2" was not found. Please create it or change the argument."
    echo "Script argument format is: \"sudo ./deploy.sh <proxy || server> <filename.env>\""
    exit 1
  else
    source "$2"
    ENVIRONMENTAL_VARIABLES_FILE="$2"
  fi
else
  source .env
  ENVIRONMENTAL_VARIABLES_FILE=".env"
fi

if [[ "$1" = "proxy" ]]; then
  apt update
  apt install -y python3 python3-venv

  echo "Installing $PROXY_SCRIPT_NAME to $PROXY_SCRIPT_INSTALL_DIR"
  mkdir -p "$PROXY_SCRIPT_INSTALL_DIR"
  cp "$PROXY_SCRIPT_NAME" "$PROXY_SCRIPT_INSTALL_DIR/"
  chown root:root "$PROXY_SCRIPT_INSTALL_DIR/$PROXY_SCRIPT_NAME"
  chmod 644 "$PROXY_SCRIPT_INSTALL_DIR/$PROXY_SCRIPT_NAME"

  python3 -m venv "$PROXY_SCRIPT_INSTALL_DIR/venv"
  "$PROXY_SCRIPT_INSTALL_DIR/venv/bin/pip" install -r requirements.txt

  echo "Deploying .env file"
  cp "$ENVIRONMENTAL_VARIABLES_FILE" "$PROXY_SCRIPT_INSTALL_DIR"
  chown root:root "$PROXY_SCRIPT_INSTALL_DIR/$ENVIRONMENTAL_VARIABLES_FILE"
  chmod 600 "$PROXY_SCRIPT_INSTALL_DIR/$ENVIRONMENTAL_VARIABLES_FILE"

  mkdir -p "$PROXY_SERVICE_INSTALL_DIR"
  sed -e "s|__INSTALL_DIR__|${PROXY_SCRIPT_INSTALL_DIR}|g" \
    -e "s|__SCRIPT_NAME__|${PROXY_SCRIPT_NAME}|g" \
    -e "s|__ENVIRONMENT_FILE_PATH__|${PROXY_SCRIPT_INSTALL_DIR}/${ENVIRONMENTAL_VARIABLES_FILE}|g" \
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
  cp "$ENVIRONMENTAL_VARIABLES_FILE" "$SERVER_SCRIPT_INSTALL_DIR"
  python3 -m venv "$SERVER_SCRIPT_INSTALL_DIR/venv"
  "$SERVER_SCRIPT_INSTALL_DIR/venv/bin/pip" install -r requirements.txt
  if ! crontab -l 2>/dev/null | grep -q "$SERVER_SCRIPT_NAME"; then
    echo "Adding cron job..."
    (
      crontab -l 2>/dev/null
      echo "*/5 * * * *  $SERVER_PYTHON_DIR $SERVER_SCRIPT_INSTALL_DIR/$SERVER_SCRIPT_NAME --env $SERVER_SCRIPT_INSTALL_DIR/$ENVIRONMENTAL_VARIABLES_FILE >>  $SERVER_LOG_OUTPUT 2>&1"
    ) | crontab -
  else
    echo "Cron job already exists. Skipping."
  fi
fi

exit 0
