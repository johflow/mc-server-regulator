#!/bin/bash

set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
  echo "Please run this script as root (use sudo)."
  exit 1
fi

if [[ "$#" -lt 1 || "$1" != "proxy" && "$1" != "server" ]]; then
  echo "Try \"sudo ./deploy.sh <proxy || server>\""
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
  echo "Deploying $PROXY_SCRIPT_NAME to $PROXY_SCRIPT_INSTALL_DIR"
  cp "$PROXY_SCRIPT_NAME" "$PROXY_SCRIPT_INSTALL_DIR/"
  chown root:root "$PROXY_SCRIPT_INSTALL_DIR/$PROXY_SCRIPT_NAME"
  chmod 644 "$PROXY_SCRIPT_INSTALL_DIR/$PROXY_SCRIPT_NAME"

  echo "Deploying .env file"
  ENV_BASE_NAME=$(basename "$ENVIRONMENTAL_VARIABLES_FILE")

  cp "$ENVIRONMENTAL_VARIABLES_FILE" "$PROXY_SCRIPT_INSTALL_DIR/$ENV_BASE_NAME"
  chown root:root "$PROXY_SCRIPT_INSTALL_DIR/$ENV_BASE_NAME"
  chmod 600 "$PROXY_SCRIPT_INSTALL_DIR/$ENV_BASE_NAME"

  echo "Deploying requirements"
  "$PROXY_SCRIPT_INSTALL_DIR/venv/bin/pip" install -r requirements.txt

  echo "Deploying $PROXY_SERVICE_NAME to $PROXY_SERVICE_INSTALL_DIR"
  sed -e "s|__INSTALL_DIR__|${PROXY_SCRIPT_INSTALL_DIR}|g" \
    -e "s|__SCRIPT_NAME__|${PROXY_SCRIPT_NAME}|g" \
    -e "s|__ENVIRONMENT_FILE_PATH__|${PROXY_SCRIPT_INSTALL_DIR}/${ENVIRONMENTAL_VARIABLES_FILE}|g" \
    "$PROXY_SERVICE_NAME.template" >"$PROXY_SERVICE_INSTALL_DIR/$PROXY_SERVICE_NAME"
  systemctl daemon-reload
  systemctl restart "$PROXY_SERVICE_NAME"
  echo "Service restarted. Current Status:"
  systemctl status "$PROXY_SERVICE_NAME"
elif [[ "$1" = "server" ]]; then
  echo "Deploying $SERVER_SCRIPT_NAME to $SERVER_SCRIPT_INSTALL_DIR"
  cp "$SERVER_SCRIPT_NAME" "$SERVER_SCRIPT_INSTALL_DIR/"
  echo "Deploying .env file"
  cp "$ENVIRONMENTAL_VARIABLES_FILE" "$SERVER_SCRIPT_INSTALL_DIR"
  chown root:root "$SERVER_SCRIPT_INSTALL_DIR/$ENVIRONMENTAL_VARIABLES_FILE"
  chmod 600 "$SERVER_SCRIPT_INSTALL_DIR/$ENVIRONMENTAL_VARIABLES_FILE"
  python3 -m venv "$SERVER_SCRIPT_INSTALL_DIR/venv"
  "$SERVER_SCRIPT_INSTALL_DIR/venv/bin/pip" install -r requirements.txt
fi
