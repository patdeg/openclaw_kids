#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="/opt/openclaw"

echo "============================================"
echo "  OpenClaw Kids — Setup"
echo "============================================"
echo ""

# ── Step 1: Check Docker ────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  echo "Error: Docker is not installed. Install it first:"
  echo "  curl -fsSL https://get.docker.com | sh"
  exit 1
fi

DOCKER="docker"
if ! docker info &>/dev/null 2>&1; then
  if sudo docker info &>/dev/null 2>&1; then
    DOCKER="sudo docker"
  else
    echo "Error: Docker daemon is not running or current user lacks permission."
    echo "  Add user to docker group: sudo usermod -aG docker \$USER"
    exit 1
  fi
fi

echo "==> Docker $(docker --version | cut -d' ' -f3 | tr -d ',') found"

# ── Step 2: Create directory structure ────────────────────────────────────────
echo "==> Setting up $DEPLOY_DIR..."
sudo mkdir -p "$DEPLOY_DIR"/{workspace,vault,credentials,himalaya}
sudo chown -R "$(id -u):$(id -g)" "$DEPLOY_DIR"

# ── Step 3: Deploy config ─────────────────────────────────────────────────────
CONFIG_SRC="$SCRIPT_DIR/config/openclaw.kids.json"
if [[ ! -f "$CONFIG_SRC" ]]; then
  echo "Error: config file not found: $CONFIG_SRC"
  exit 1
fi

CONFIG_DEST="$DEPLOY_DIR/openclaw.json"
if [[ -f "$CONFIG_DEST" ]]; then
  BACKUP="$CONFIG_DEST.bak.$(date +%Y%m%d%H%M%S)"
  echo "    Backing up existing config to $BACKUP"
  cp "$CONFIG_DEST" "$BACKUP"
fi
echo "    Deploying config..."
cp "$CONFIG_SRC" "$CONFIG_DEST"

# Deploy FAMILY_COMPASS.md into the workspace (loaded as system context)
cp "$SCRIPT_DIR/config/FAMILY_COMPASS.md" "$DEPLOY_DIR/workspace/FAMILY_COMPASS.md"
echo "    Deployed FAMILY_COMPASS.md"

# ── Step 4: Web port ──────────────────────────────────────────────────────────
echo ""
echo "What port should the web UI listen on? (default: 8085)"
read -rp "  Web port [8085]: " WEB_PORT
WEB_PORT="${WEB_PORT:-8085}"
echo "  Web UI will listen on port $WEB_PORT"

# ── Step 5: Deploy files ──────────────────────────────────────────────────────
echo "==> Deploying files to $DEPLOY_DIR..."
for f in docker-compose.yml Dockerfile.openclaw Dockerfile.web entrypoint-gateway.sh requirements-gateway.txt requirements-web.txt; do
  if [[ -f "$SCRIPT_DIR/$f" ]]; then
    cp "$SCRIPT_DIR/$f" "$DEPLOY_DIR/$f"
  fi
done

# Deploy skills
rm -rf "$DEPLOY_DIR/skills"
cp -rf "$SCRIPT_DIR/skills" "$DEPLOY_DIR/skills"

# Deploy web
rm -rf "$DEPLOY_DIR/web"
cp -rf "$SCRIPT_DIR/web" "$DEPLOY_DIR/web"

# ── Step 6: Check secrets files ───────────────────────────────────────────────
if [[ ! -f "$DEPLOY_DIR/.env" ]]; then
  echo ""
  echo "============================================================"
  echo "  IMPORTANT: No .env file found at $DEPLOY_DIR/.env"
  echo ""
  echo "  Create it now:"
  echo "    cp $SCRIPT_DIR/.env.example $DEPLOY_DIR/.env"
  echo "    chmod 600 $DEPLOY_DIR/.env"
  echo "    nano $DEPLOY_DIR/.env"
  echo ""
  echo "  See README.md Stage 7 for how to fill in each key."
  echo "============================================================"
fi

WEB_ENV="$DEPLOY_DIR/alfred-web.env"
if [[ ! -f "$WEB_ENV" ]]; then
  echo ""
  echo "  Creating web env file at $WEB_ENV..."
  cp "$SCRIPT_DIR/alfred-web.env.example" "$WEB_ENV"
  chmod 600 "$WEB_ENV"
  # Set the port
  sed -i "s/^ALFRED_WEB_PORT=.*/ALFRED_WEB_PORT=$WEB_PORT/" "$WEB_ENV"
  echo "  Created $WEB_ENV — fill in GOOGLE_CLIENT_ID, SESSION_SECRET, etc."
fi

# ── Step 7: Build Docker images ──────────────────────────────────────────────
echo "==> Building Docker images (this may take a few minutes)..."
cd "$DEPLOY_DIR"
$DOCKER compose build

# ── Step 8: Install systemd services ─────────────────────────────────────────
echo "==> Installing systemd services..."
for svc in openclaw.service; do
  if [[ -f "$SCRIPT_DIR/systemd/$svc" ]]; then
    sudo cp "$SCRIPT_DIR/systemd/$svc" "/etc/systemd/system/$svc"
  fi
done
# Install web service (renamed from alfred-web)
if [[ -f "$SCRIPT_DIR/systemd/alfred-web.service" ]]; then
  sudo cp "$SCRIPT_DIR/systemd/alfred-web.service" "/etc/systemd/system/openclaw-web.service"
fi
sudo systemctl daemon-reload
sudo systemctl enable openclaw 2>/dev/null || true
sudo systemctl enable openclaw-web 2>/dev/null || true

# ── Step 9: Start the stack ──────────────────────────────────────────────────
echo "==> Starting OpenClaw..."
$DOCKER compose up -d

echo ""
echo "============================================"
echo "  Your AI assistant is running!"
echo "============================================"
echo ""
echo "  Web UI:  http://$(hostname -I | awk '{print $1}'):$WEB_PORT"
echo "  Gateway: http://127.0.0.1:18789"
echo ""
echo "  Verify:  docker ps"
echo ""
echo "  Next steps:"
echo "    1. Fill in your .env file (see README.md Stage 7)"
echo "    2. Open the web UI in your browser"
echo "    3. Pair Discord: docker exec -it openclaw-gateway openclaw pair discord"
echo "    4. Pair WhatsApp: docker exec -it openclaw-gateway openclaw pair whatsapp"
echo ""
echo "  If you haven't named your assistant yet, see README.md Stage 6.5"
echo ""
