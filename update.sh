#!/usr/bin/env bash
set -euo pipefail

#
# update.sh — Pull latest changes and deploy to /opt/openclaw
#
# Usage:
#   cd ~/patdeg/openclaw_kids && ./update.sh
#
# What it does:
#   1. git pull
#   2. Copy skills, web source, docker files to /opt/openclaw
#   3. Merge skill entries from kids config into live runtime config
#   4. Rebuild Docker images only if Dockerfiles, compose, or web source changed
#   5. Fix ownership so container (UID 1001) can read mounted files
#   6. Restart both gateway and web services
#
# Safe to run repeatedly. Does not touch .env, alfred-web.env, or credentials.
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="/opt/openclaw"
LIVE_CONFIG="$DEPLOY_DIR/dotopenclaw/openclaw.json"
REPO_CONFIG="$SCRIPT_DIR/config/openclaw.kids.json"

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
git pull

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

# Deploy workspace files
cp -f "$SCRIPT_DIR/config/FAMILY_COMPASS.md" "$DEPLOY_DIR/workspace/FAMILY_COMPASS.md" 2>/dev/null && echo "    FAMILY_COMPASS.md" || true
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

if [[ -f "$REPO_CONFIG" ]] && [[ -f "$LIVE_CONFIG" ]]; then
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
" "$REPO_CONFIG" "$LIVE_CONFIG"
elif [[ -f "$REPO_CONFIG" ]] && [[ ! -f "$LIVE_CONFIG" ]]; then
  echo "==> No live config yet, deploying kids config..."
  mkdir -p "$(dirname "$LIVE_CONFIG")"
  cp "$REPO_CONFIG" "$LIVE_CONFIG"
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
