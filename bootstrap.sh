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
sudo mkdir -p "$DEPLOY_DIR"/{workspace,vault,credentials,himalaya,dotopenclaw}
# Reclaim ownership so we can write files (containers may have created files as UID 1001)
sudo chown -R "$(id -u):$(id -g)" "$DEPLOY_DIR"

# ── Step 4: Deploy config ─────────────────────────────────────────────────────
# OpenClaw manages its own config at dotopenclaw/openclaw.json via `openclaw doctor`.
# We only set gateway.mode=local if the config doesn't exist yet.
OPENCLAW_CONFIG="$DEPLOY_DIR/dotopenclaw/openclaw.json"
if [[ ! -f "$OPENCLAW_CONFIG" ]]; then
  echo "    Creating minimal OpenClaw config (openclaw doctor will fill in the rest)..."
  echo '{"gateway":{"mode":"local"}}' > "$OPENCLAW_CONFIG"
fi

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
for f in docker-compose.yml Dockerfile.openclaw Dockerfile.web entrypoint-gateway.sh requirements-gateway.txt requirements-web.txt .dockerignore; do
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

# Substitute assistant name in deployed web files (repo keeps "ATHENA" as placeholder)
DEPLOY_NAME=$(python3 -c "import json; print(json.load(open('$JSON_LOCAL'))['identity']['name'])")
echo "    Assistant name from config: $DEPLOY_NAME"
if [[ -n "$DEPLOY_NAME" ]]; then
  find "$DEPLOY_DIR/web" -type f \( -name '*.html' -o -name '*.js' -o -name '*.json' \) \
    -exec sed -i "s/ATHENA/$DEPLOY_NAME/g" {} +
  echo "    Replaced ATHENA → $DEPLOY_NAME in web files"
fi

# ── Step 7: Check secrets files ───────────────────────────────────────────────
if [[ ! -f "$DEPLOY_DIR/.env" ]]; then
  echo ""
  echo "  Creating .env file at $DEPLOY_DIR/.env from template..."
  cp "$SCRIPT_DIR/.env.example" "$DEPLOY_DIR/.env"
  chmod 600 "$DEPLOY_DIR/.env"
  echo "  Created $DEPLOY_DIR/.env — fill in your API keys before launching."
fi

WEB_ENV="$DEPLOY_DIR/web.env"
if [[ ! -f "$WEB_ENV" ]]; then
  echo ""
  echo "  Creating web env file at $WEB_ENV..."
  cp "$SCRIPT_DIR/web.env.example" "$WEB_ENV"
  chmod 600 "$WEB_ENV"
  # Set the port
  sed -i "s/^WEB_PORT=.*/WEB_PORT=$WEB_PORT/" "$WEB_ENV"
  # Generate secrets so docker compose up doesn't crash on empty values
  GEN_PASSWORD=$(openssl rand -base64 24)
  GEN_SESSION=$(openssl rand -hex 32)
  sed -i "s/^WEB_PASSWORD=.*/WEB_PASSWORD=$GEN_PASSWORD/" "$WEB_ENV"
  sed -i "s/^SESSION_SECRET=.*/SESSION_SECRET=$GEN_SESSION/" "$WEB_ENV"
  echo "  Created $WEB_ENV with auto-generated password and session secret."
  echo ""
  echo "  Your web UI password is:  $GEN_PASSWORD"
  echo "  (saved in $WEB_ENV — you can change it later with: nano $WEB_ENV)"
fi

# ── Step 8: Copy OpenClaw auth and fix ownership ─────────────────────────────
# codex login (Stage 2) stores OAuth credentials in ~/.codex/auth.json
# (or ~/.openclaw/auth.json on older versions).
# The container needs this file to connect to ChatGPT Plus.
AUTH_JSON=""
for candidate in "$HOME/.codex/auth.json" "$HOME/.openclaw/auth.json"; do
  if [[ -f "$candidate" ]]; then
    AUTH_JSON="$candidate"
    break
  fi
done

if [[ -n "$AUTH_JSON" ]]; then
  echo "    Copying ChatGPT auth from $AUTH_JSON..."
  cp "$AUTH_JSON" "$DEPLOY_DIR/dotopenclaw/auth.json"
else
  echo ""
  echo "  WARNING: No auth.json found in ~/.codex/ or ~/.openclaw/"
  echo "  Did you run 'codex login' first? (Stage 2 in README)"
  echo "  Without it, the AI backend won't work."
  echo ""
fi

# Hand writable volume mounts to the container user (UID 1001)
sudo chown -R 1001:1001 "$DEPLOY_DIR"/{vault,workspace,dotopenclaw,credentials,himalaya}
# Read-only mounts just need to be world-readable
chmod -R a+rX "$DEPLOY_DIR/skills/" "$DEPLOY_DIR/web/" 2>/dev/null || true

# ── Step 9: Build Docker images ──────────────────────────────────────────────
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
if [[ -f "$SCRIPT_DIR/systemd/openclaw-web.service" ]]; then
  sudo cp "$SCRIPT_DIR/systemd/openclaw-web.service" "/etc/systemd/system/openclaw-web.service"
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
echo "  4. $DEPLOY_DIR/web.env"
echo "     Web UI password and session secret."
echo "     Edit with:  nano $DEPLOY_DIR/web.env"
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
echo "  1. Copy your web UI password (shown above) somewhere safe."
echo ""
echo "     When you first open the web UI in Chrome, it will ask"
echo "     for this password. After you paste it, Chrome will offer"
echo "     to save it — click YES so you don't need to type it again."
echo ""
echo "     To see it again:  grep WEB_PASSWORD $DEPLOY_DIR/web.env"
echo ""
echo "     IMPORTANT: Do NOT replace the password with a short one."
echo "     The server requires 16+ characters with uppercase,"
echo "     lowercase, digits, and special characters. If the"
echo "     password is too weak, the web server refuses to start"
echo "     and you'll get 'connection refused' in your browser."
echo ""
echo "     To set your display name (shown in the UI):"
echo "     nano $DEPLOY_DIR/web.env    (change WEB_USERNAME)"
echo ""
echo "  2. Fill in your API keys:"
echo ""
echo "     nano $DEPLOY_DIR/.env"
echo ""
echo "  3. Deploy your changes:"
echo ""
echo "     cd $SCRIPT_DIR && ./update.sh"
echo ""
echo "  4. Open the web UI in your browser"
echo ""
echo "  5. Pair Discord:"
echo "     docker exec -it openclaw-gateway openclaw pair discord"
echo "  6. Pair WhatsApp:"
echo "     docker exec -it openclaw-gateway openclaw pair whatsapp"
echo ""
