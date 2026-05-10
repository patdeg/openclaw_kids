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
  echo ""
  echo "-- AI Provider --"
  echo ""
  echo "  How should your assistant connect to an AI model?"
  echo ""
  echo "  Option A: ChatGPT Plus subscription (family account, OAuth login)"
  echo "  Option B: Demeterics API key (pay-per-use, no subscription needed)"
  echo ""
  read -rp "  Choose (A/B) [A]: " PROVIDER_CHOICE
  PROVIDER_CHOICE="${PROVIDER_CHOICE:-A}"

  if [[ "${PROVIDER_CHOICE^^}" == "B" ]]; then
    echo ""
    echo "  You chose Demeterics. After setup, paste your API key in:"
    echo "    $DEPLOY_DIR/.env  (DEMETERICS_API_KEY=dmt_...)"
    echo ""
    echo "    Creating OpenClaw config with Demeterics provider..."
    cat > "$OPENCLAW_CONFIG" << 'OCEOF'
{
  "gateway": {
    "mode": "local"
  },
  "models": {
    "providers": {
      "demeterics": {
        "baseUrl": "https://api.demeterics.com/groq/v1",
        "api": "openai-completions",
        "headers": {
          "X-Meta-App": "openclaw-kids",
          "X-Meta-Environment": "production"
        },
        "models": [
          {
            "id": "openai/gpt-oss-120b",
            "name": "GPT-OSS 120B (Groq)",
            "api": "openai-completions",
            "contextWindow": 131072,
            "maxTokens": 8192,
            "compat": {
              "maxTokensField": "max_tokens"
            }
          },
          {
            "id": "openai/gpt-oss-20b",
            "name": "GPT-OSS 20B (Groq)",
            "api": "openai-completions",
            "contextWindow": 131072,
            "maxTokens": 8192,
            "compat": {
              "maxTokensField": "max_tokens"
            }
          }
        ]
      }
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "demeterics/openai/gpt-oss-120b",
        "fallbacks": ["demeterics/openai/gpt-oss-20b"]
      }
    }
  }
}
OCEOF
  else
    echo ""
    echo "  You chose ChatGPT Plus. After setup, run ./login.sh to connect."
    echo ""
    echo "    Creating OpenClaw config with OpenAI provider..."
    cat > "$OPENCLAW_CONFIG" << 'OCEOF'
{
  "gateway": {
    "mode": "local"
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "openai-codex/gpt-5.4"
      }
    }
  }
}
OCEOF
  fi
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

# ── Step 8: Fix ownership ─────────────────────────────────────────────────────
# Hand writable volume mounts to the container user (UID 1001)
sudo chown -R 1001:1001 "$DEPLOY_DIR"/{vault,workspace,dotopenclaw,credentials,himalaya}
# Read-only mounts just need to be world-readable
chmod -R a+rX "$DEPLOY_DIR/skills/" "$DEPLOY_DIR/web/" 2>/dev/null || true

# ── Step 9: Build Docker images ──────────────────────────────────────────────
echo "==> Building Docker images (this may take a few minutes)..."
cd "$DEPLOY_DIR"
$DOCKER compose build

# ── Step 10: Install systemd services ────────────────────────────────────────
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

# ── Step 11: Start the stack ─────────────────────────────────────────────────
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
# Detect which provider was configured
if grep -q '"demeterics"' "$OPENCLAW_CONFIG" 2>/dev/null; then
  echo "  1. Add your Demeterics API key:"
  echo ""
  echo "     nano $DEPLOY_DIR/.env"
  echo ""
  echo "     Set DEMETERICS_API_KEY=dmt_... (ask a parent for the key)"
  echo "     Get one at: https://demeterics.ai"
  echo ""
else
  echo "  1. Connect your ChatGPT Plus account:"
  echo ""
  echo "     cd $SCRIPT_DIR && ./login.sh"
  echo ""
  echo "     This opens a browser window. Sign in with the family"
  echo "     ChatGPT Plus account. Once done, the AI backend is live."
fi
echo ""
echo "  2. Copy your web UI password (shown above) somewhere safe."
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
echo "  3. Fill in your API keys (Discord, Canvas, etc.):"
echo ""
echo "     nano $DEPLOY_DIR/.env"
echo ""
echo "  4. Deploy your changes:"
echo ""
echo "     cd $SCRIPT_DIR && ./update.sh"
echo ""
echo "  5. Open the web UI in your browser"
echo ""
echo "  6. Pair Discord:"
echo "     docker exec -it openclaw-gateway openclaw pair discord"
echo "  7. Pair WhatsApp:"
echo "     docker exec -it openclaw-gateway openclaw pair whatsapp"
echo ""
