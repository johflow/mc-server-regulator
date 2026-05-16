#!/bin/bash

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
  sudo cp "$PROXY_SCRIPT_NAME" "$PROXY_SCRIPT_INSTALL_DIR/"
  echo "Deploying $PROXY_SERVICE_NAME to $PROXY_SERVICE_INSTALL_DIR"
  cp "$PROXY_SERVICE_NAME" "$PROXY_SERVICE_INSTALL_DIR/"
  sudo systemctl restart mc-gatekeeper.service
  echo "Service restarted. Current Status:"
  sudo systemctl status mc-gatekeeper.service

elif [[ "$1" = "server" ]]; then
  echo "Deploying to /opt/mc-server-regulator..."
  cp "$SERVER_SCRIPT_NAME" "$SERVER_SCRIPT_INSTALL_DIR/"
  sudo systemctl restart mc-gatekeeper.service
  echo "Service restarted. Current Status:"
  sudo systemctl status mc-gatekeeper.service
fi
