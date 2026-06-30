#!/usr/bin/env bash
# deploy/setup.sh — Raspberry Pi セットアップスクリプト
# Usage: bash deploy/setup.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVER_DIR="$REPO_DIR/server"
SERVICE_NAME="raspi-iot-server"

echo "==> Repo: $REPO_DIR"

# ── 1. System packages ────────────────────────────────────────────────────────
echo "==> Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-venv python3-pip

# Add current user to dialout group for USB serial access
if ! groups | grep -q dialout; then
  echo "==> Adding $(whoami) to dialout group (re-login required to take effect)"
  sudo usermod -aG dialout "$(whoami)"
fi

# ── 2. Python virtualenv ─────────────────────────────────────────────────────
echo "==> Creating Python virtualenv..."
python3 -m venv "$SERVER_DIR/.venv"
"$SERVER_DIR/.venv/bin/pip" install --upgrade pip -q
"$SERVER_DIR/.venv/bin/pip" install -r "$SERVER_DIR/requirements.txt" -q
echo "==> Python dependencies installed"

# ── 3. .env file ────────────────────────────────────────────────────────────
ENV_FILE="$SERVER_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "==> Creating .env from .env.example..."
  cp "$SERVER_DIR/.env.example" "$ENV_FILE"
  echo "    Edit $ENV_FILE to set SERIAL_PORT if auto-detect fails."
else
  echo "==> .env already exists, skipping"
fi

# ── 4. systemd service ───────────────────────────────────────────────────────
echo "==> Installing systemd service..."
# Substitute actual repo path into service file
ESCAPED_DIR=$(echo "$REPO_DIR" | sed 's/[\/&]/\\&/g')
sed "s|/home/ubuntu/raspi-iot-server|$REPO_DIR|g; s|User=ubuntu|User=$(whoami)|g" \
  "$REPO_DIR/deploy/raspi-iot-server.service" \
  | sudo tee "/etc/systemd/system/$SERVICE_NAME.service" > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
echo "==> Service installed and enabled"

# ── 5. Done ──────────────────────────────────────────────────────────────────
echo ""
echo "✅ Setup complete!"
echo ""
echo "Start the server:   sudo systemctl start $SERVICE_NAME"
echo "Check status:       sudo systemctl status $SERVICE_NAME"
echo "View logs:          sudo journalctl -u $SERVICE_NAME -f"
echo "Dashboard:          http://$(hostname).local:8000"
echo ""
echo "⚠️  If you were just added to the dialout group, please log out and back in."
