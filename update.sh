#!/usr/bin/env bash
set -euo pipefail

#
# update.sh — Pull latest changes and deploy to /opt/openclaw
#
# Usage:
#   cd ~/dev/openclaw_kids && ./update.sh
#
# What it does:
#   1. git pull
#   2. Check if .example templates changed upstream (warn if so)
#   3. Copy skills, web source, docker files to /opt/openclaw
#   4. Deploy LOCAL config files (not templates) — never overwrites your settings
#   5. Merge skill entries from your config into the live runtime config
#   6. Rebuild Docker images only if Dockerfiles, compose, or web source changed
#   7. Fix ownership so container (UID 1001) can read mounted files
#   8. Restart both gateway and web services
#
# Safe to run repeatedly. Does not touch .env, alfred-web.env, or credentials.
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="/opt/openclaw"
LIVE_CONFIG="$DEPLOY_DIR/dotopenclaw/openclaw.json"
LOCAL_CONFIG="$SCRIPT_DIR/config/openclaw.kids.json"
JSON_EXAMPLE="$SCRIPT_DIR/config/openclaw.kids.json.example"
COMPASS_EXAMPLE="$SCRIPT_DIR/config/FAMILY_COMPASS.md.example"
COMPASS_LOCAL="$SCRIPT_DIR/config/FAMILY_COMPASS.md"

# ── Preflight ────────────────────────────────────────────────────────────────

if [[ ! -d "$DEPLOY_DIR" ]]; then
  echo "Error: $DEPLOY_DIR does not exist. Run bootstrap.sh first."
  exit 1
fi

# Docker command (with or without sudo)
DOCKER="docker"
if ! docker info &>/dev/null 2>&1; then
  if sudo docker info &>/dev/null 2>&1; then
    DOCKER="sudo docker"
  else
    echo "Error: Docker daemon is not running or current user lacks permission."
    exit 1
  fi
fi

# ── Step 1: Git pull ────────────────────────────────────────────────────────

echo "==> Pulling latest changes..."
cd "$SCRIPT_DIR"
BEFORE_PULL=$(git rev-parse HEAD)
git pull
AFTER_PULL=$(git rev-parse HEAD)

# ── Step 1b: Check if .example templates changed upstream ────────────────────

if [[ "$BEFORE_PULL" != "$AFTER_PULL" ]]; then
  TEMPLATE_CHANGED=false
  if git diff --name-only "$BEFORE_PULL" "$AFTER_PULL" | grep -q "config/openclaw.kids.json.example"; then
    TEMPLATE_CHANGED=true
  fi
  if git diff --name-only "$BEFORE_PULL" "$AFTER_PULL" | grep -q "config/FAMILY_COMPASS.md.example"; then
    TEMPLATE_CHANGED=true
  fi
  if [[ "$TEMPLATE_CHANGED" == "true" ]]; then
    echo ""
    echo "============================================================"
    echo "  NOTICE: Configuration templates were updated upstream."
    echo ""
    echo "  Your local config files were NOT overwritten."
    echo "  To review what changed and update your config, run:"
    echo ""
    echo "    ./configure.sh"
    echo ""
    echo "  Or compare manually:"
    echo "    diff config/openclaw.kids.json config/openclaw.kids.json.example"
    echo "    diff config/FAMILY_COMPASS.md config/FAMILY_COMPASS.md.example"
    echo "============================================================"
    echo ""
  fi
fi

# ── Step 1c: Check that local configs exist ──────────────────────────────────

if [[ ! -f "$LOCAL_CONFIG" ]] || [[ ! -f "$COMPASS_LOCAL" ]]; then
  echo ""
  echo "============================================================"
  echo "  WARNING: Local configuration files not found."
  echo ""
  echo "  Run ./configure.sh to generate them before deploying."
  echo "============================================================"
  echo ""
  read -rp "  Run configure.sh now? (Y/n): " RUN_CONFIGURE
  if [[ "${RUN_CONFIGURE,,}" != "n" ]]; then
    bash "$SCRIPT_DIR/configure.sh"
  else
    echo "  Skipping config deployment. Services may not work correctly."
  fi
fi

# ── Step 2: Check what changed ──────────────────────────────────────────────

NEED_REBUILD=false

for f in Dockerfile.openclaw Dockerfile.web docker-compose.yml requirements-gateway.txt requirements-web.txt; do
  if [[ -f "$SCRIPT_DIR/$f" ]] && [[ -f "$DEPLOY_DIR/$f" ]]; then
    if ! diff -q "$SCRIPT_DIR/$f" "$DEPLOY_DIR/$f" &>/dev/null; then
      echo "    $f changed → rebuild needed"
      NEED_REBUILD=true
    fi
  elif [[ -f "$SCRIPT_DIR/$f" ]]; then
    echo "    $f new → rebuild needed"
    NEED_REBUILD=true
  fi
done

# Check if web source changed
if [[ -d "$DEPLOY_DIR/web" ]]; then
  if ! diff -rq "$SCRIPT_DIR/web" "$DEPLOY_DIR/web" --exclude='.env' --exclude='alfred' --exclude='openclaw.db' --exclude='__debug_bin*' &>/dev/null 2>&1; then
    echo "    web/ source changed → rebuild needed"
    NEED_REBUILD=true
  fi
else
  echo "    web/ not deployed yet → rebuild needed"
  NEED_REBUILD=true
fi

# ── Step 3: Deploy files ────────────────────────────────────────────────────

echo "==> Deploying skills..."
rsync -a --delete "$SCRIPT_DIR/skills/" "$DEPLOY_DIR/skills/"

echo "==> Deploying docker files..."
for f in docker-compose.yml Dockerfile.openclaw Dockerfile.web entrypoint-gateway.sh requirements-gateway.txt requirements-web.txt; do
  if [[ -f "$SCRIPT_DIR/$f" ]]; then
    cp "$SCRIPT_DIR/$f" "$DEPLOY_DIR/$f"
  fi
done

echo "==> Deploying web source..."
rm -rf "$DEPLOY_DIR/web"
cp -rf "$SCRIPT_DIR/web" "$DEPLOY_DIR/web"

# Deploy workspace files from LOCAL copies (not templates)
if [[ -f "$COMPASS_LOCAL" ]]; then
  cp -f "$COMPASS_LOCAL" "$DEPLOY_DIR/workspace/FAMILY_COMPASS.md" && echo "    FAMILY_COMPASS.md (from local config)" || true
else
  echo "    FAMILY_COMPASS.md skipped (no local config — run ./configure.sh)"
fi
if [[ -f "$SCRIPT_DIR/TOOLS.md" ]]; then
  cp -f "$SCRIPT_DIR/TOOLS.md" "$DEPLOY_DIR/workspace/TOOLS.md" && echo "    TOOLS.md" || true
fi
if [[ -f "$SCRIPT_DIR/HEARTBEAT.md" ]]; then
  cp -f "$SCRIPT_DIR/HEARTBEAT.md" "$DEPLOY_DIR/workspace/HEARTBEAT.md" && echo "    HEARTBEAT.md" || true
fi

# ── Step 3b: Fix ownership ──────────────────────────────────────────────────
# The openclaw-gateway container runs as UID 1001. Ensure deployed files are
# owned by the deploying user and world-readable so the container can read
# them via volume mounts.

echo "==> Fixing file ownership..."
sudo chown -R "$(id -u):$(id -g)" "$DEPLOY_DIR/skills/" 2>/dev/null || true
sudo chown -R "$(id -u):$(id -g)" "$DEPLOY_DIR/web/" 2>/dev/null || true
sudo chown -R "$(id -u):$(id -g)" "$DEPLOY_DIR/workspace/" 2>/dev/null || true
chmod -R a+rX "$DEPLOY_DIR/skills/" 2>/dev/null || true
chmod -R a+rX "$DEPLOY_DIR/web/" 2>/dev/null || true
chmod -R a+rX "$DEPLOY_DIR/workspace/" 2>/dev/null || true

# ── Step 4: Merge skill entries into live config ─────────────────────────────

if [[ -f "$LOCAL_CONFIG" ]] && [[ -f "$LIVE_CONFIG" ]]; then
  echo "==> Merging skill entries into live config..."
  python3 -c "
import json, sys, shutil

repo_path = sys.argv[1]
live_path = sys.argv[2]

with open(repo_path) as f:
    repo = json.load(f)
with open(live_path) as f:
    live = json.load(f)

repo_skills = repo.get('skills', {}).get('entries', {})
live_skills = live.setdefault('skills', {}).setdefault('entries', {})

changed = False
for name, entry in repo_skills.items():
    if name not in live_skills:
        live_skills[name] = entry
        print(f'    + Added skill: {name}')
        changed = True
    elif live_skills[name] != entry:
        live_skills[name] = entry
        print(f'    ~ Updated skill: {name}')
        changed = True

if changed:
    backup = live_path + '.bak'
    shutil.copy2(live_path, backup)
    with open(live_path, 'w') as f:
        json.dump(live, f, indent=2)
        f.write('\n')
    print(f'    Config updated (backup: {backup})')
else:
    print('    All skills already registered')
" "$LOCAL_CONFIG" "$LIVE_CONFIG"
elif [[ -f "$LOCAL_CONFIG" ]] && [[ ! -f "$LIVE_CONFIG" ]]; then
  echo "==> No live config yet, deploying local config..."
  mkdir -p "$(dirname "$LIVE_CONFIG")"
  cp "$LOCAL_CONFIG" "$LIVE_CONFIG"
fi

# ── Step 5: Rebuild if needed, then restart ──────────────────────────────────

cd "$DEPLOY_DIR"

if [[ "$NEED_REBUILD" == "true" ]]; then
  echo "==> Rebuilding Docker images..."
  $DOCKER compose build
fi

# Always use "up -d" instead of "restart" — restart does NOT reload .env changes
echo "==> Restarting services..."
$DOCKER compose up -d

# ── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo "==> Update complete!"
$DOCKER compose ps
