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

# ── Step 2: Run configure.sh if local configs are missing ───────────────────
JSON_LOCAL="$SCRIPT_DIR/config/openclaw.kids.json"
COMPASS_LOCAL="$SCRIPT_DIR/config/FAMILY_COMPASS.md"

if [[ ! -f "$JSON_LOCAL" ]] || [[ ! -f "$COMPASS_LOCAL" ]]; then
  echo ""
  echo "==> Local configuration files not found. Running configure.sh..."
  echo ""
  bash "$SCRIPT_DIR/configure.sh"
else
  echo ""
  echo "  Local config files found."
  read -rp "  Do you want to reconfigure? (y/N): " RECONFIG
  if [[ "${RECONFIG,,}" == "y" ]]; then
    bash "$SCRIPT_DIR/configure.sh"
  fi
fi

# Verify local configs exist after configure
if [[ ! -f "$JSON_LOCAL" ]]; then
  echo "Error: config/openclaw.kids.json not found. Run ./configure.sh first."
  exit 1
fi
if [[ ! -f "$COMPASS_LOCAL" ]]; then
  echo "Error: config/FAMILY_COMPASS.md not found. Run ./configure.sh first."
  exit 1
fi

# ── Step 3: Create directory structure ────────────────────────────────────────
echo "==> Setting up $DEPLOY_DIR..."
sudo mkdir -p "$DEPLOY_DIR"/{workspace,vault,credentials,himalaya}
sudo chown -R "$(id -u):$(id -g)" "$DEPLOY_DIR"

# ── Step 4: Deploy config ─────────────────────────────────────────────────────
CONFIG_DEST="$DEPLOY_DIR/openclaw.json"
if [[ -f "$CONFIG_DEST" ]]; then
  BACKUP="$CONFIG_DEST.bak.$(date +%Y%m%d%H%M%S)"
  echo "    Backing up existing config to $BACKUP"
  cp "$CONFIG_DEST" "$BACKUP"
fi
echo "    Deploying config..."
cp "$JSON_LOCAL" "$CONFIG_DEST"

# Deploy FAMILY_COMPASS.md into the workspace (loaded as system context)
cp "$COMPASS_LOCAL" "$DEPLOY_DIR/workspace/FAMILY_COMPASS.md"
echo "    Deployed FAMILY_COMPASS.md"

# ── Step 5: Web port ──────────────────────────────────────────────────────────
echo ""
echo "What port should the web UI listen on? (default: 8085)"
read -rp "  Web port [8085]: " WEB_PORT
WEB_PORT="${WEB_PORT:-8085}"
echo "  Web UI will listen on port $WEB_PORT"

# ── Step 6: Deploy files ──────────────────────────────────────────────────────
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

# ── Step 7: Check secrets files ───────────────────────────────────────────────
if [[ ! -f "$DEPLOY_DIR/.env" ]]; then
  echo ""
  echo "  Creating .env file at $DEPLOY_DIR/.env from template..."
  cp "$SCRIPT_DIR/.env.example" "$DEPLOY_DIR/.env"
  chmod 600 "$DEPLOY_DIR/.env"
  echo "  Created $DEPLOY_DIR/.env — fill in your API keys before launching."
fi

WEB_ENV="$DEPLOY_DIR/alfred-web.env"
if [[ ! -f "$WEB_ENV" ]]; then
  echo ""
  echo "  Creating web env file at $WEB_ENV..."
  cp "$SCRIPT_DIR/alfred-web.env.example" "$WEB_ENV"
  chmod 600 "$WEB_ENV"
  # Set the port
  sed -i "s/^ALFRED_WEB_PORT=.*/ALFRED_WEB_PORT=$WEB_PORT/" "$WEB_ENV"
  echo "  Created $WEB_ENV — fill in WEB_PASSWORD, SESSION_SECRET, etc."
fi

# ── Step 8: Build Docker images ──────────────────────────────────────────────
echo "==> Building Docker images (this may take a few minutes)..."
cd "$DEPLOY_DIR"
$DOCKER compose build

# ── Step 9: Install systemd services ─────────────────────────────────────────
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

# ── Step 10: Start the stack ─────────────────────────────────────────────────
echo "==> Starting OpenClaw..."
$DOCKER compose up -d

# ── Final Summary ────────────────────────────────────────────────────────────
ASSISTANT_NAME=$(python3 -c "import json; print(json.load(open('$JSON_LOCAL'))['identity']['name'])" 2>/dev/null || echo "your assistant")

echo ""
echo "============================================"
echo "  $ASSISTANT_NAME is running!"
echo "============================================"
echo ""
echo "  Web UI:  http://$(hostname -I | awk '{print $1}'):$WEB_PORT"
echo "  Gateway: http://127.0.0.1:18789"
echo ""
echo "  Verify:  docker ps"
echo ""
echo "--------------------------------------------"
echo "  YOUR CONFIGURATION FILES"
echo "--------------------------------------------"
echo ""
echo "  These files control your setup. They are"
echo "  YOUR local copies — git will never touch them."
echo ""
echo "  1. config/openclaw.kids.json"
echo "     Your assistant's name, schedule, and skills."
echo "     Edit with:  nano $SCRIPT_DIR/config/openclaw.kids.json"
echo ""
echo "  2. config/FAMILY_COMPASS.md"
echo "     How your AI talks to you — personality, values, safety."
echo "     Edit with:  nano $SCRIPT_DIR/config/FAMILY_COMPASS.md"
echo ""
echo "  3. $DEPLOY_DIR/.env"
echo "     Secrets: Discord token, Canvas API key, etc."
echo "     Edit with:  nano $DEPLOY_DIR/.env"
echo ""
echo "  4. $DEPLOY_DIR/alfred-web.env"
echo "     Web UI password and session secret."
echo "     Edit with:  nano $DEPLOY_DIR/alfred-web.env"
echo ""
echo "  IMPORTANT: After editing ANY config file, run:"
echo ""
echo "    cd $SCRIPT_DIR && ./update.sh"
echo ""
echo "  This deploys your changes and restarts the services."
echo "  You can also re-run ./configure.sh to change your"
echo "  assistant's name, schedule, or personal details."
echo ""
echo "--------------------------------------------"
echo "  NEXT STEPS"
echo "--------------------------------------------"
echo ""
echo "  1. Fill in your .env file:  nano $DEPLOY_DIR/.env"
echo "  2. Open the web UI in your browser"
echo "  3. Pair Discord:"
echo "     docker exec -it openclaw-gateway openclaw pair discord"
echo "  4. Pair WhatsApp:"
echo "     docker exec -it openclaw-gateway openclaw pair whatsapp"
echo ""
