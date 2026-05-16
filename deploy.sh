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

if [[ "$#" -lt 1 || "$1" != "proxy" && "$1" != "server" ]]; then
  echo "Try \"sudo ./deploy.sh <proxy || server>\""
  exit 1
fi

if [[ "$1" = "proxy" ]]; then
  echo "Deploying $PROXY_SCRIPT_NAME to $PROXY_SCRIPT_INSTALL_DIR"
  cp "$PROXY_SCRIPT_NAME" "$PROXY_SCRIPT_INSTALL_DIR/"
  echo "Deploying $PROXY_SERVICE_NAME to $PROXY_SERVICE_INSTALL_DIR"
  sed -e "s|__INSTALL_DIR__|${PROXY_SCRIPT_INSTALL_DIR}|g" \
    -e "s|__SCRIPT_NAME__|${PROXY_SCRIPT_NAME}|g" \
    "$PROXY_SERVICE_NAME.template" >"$PROXY_SERVICE_INSTALL_DIR/$PROXY_SERVICE_NAME"
  systemctl daemon-reload
  systemctl restart "$PROXY_SERVICE_NAME"
  echo "Service restarted. Current Status:"
  systemctl status "$PROXY_SERVICE_NAME"
elif [[ "$1" = "server" ]]; then
  echo "Deploying $SERVER_SCRIPT_NAME to $SERVER_SCRIPT_INSTALL_DIR"
  cp "$SERVER_SCRIPT_NAME" "$SERVER_SCRIPT_INSTALL_DIR/"
fi
