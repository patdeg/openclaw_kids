#!/usr/bin/env bash
set -euo pipefail

#
# login.sh — Connect your ChatGPT Plus account to OpenClaw
#
# Run this after bootstrap.sh to authenticate the AI backend.
# It opens a browser window for OAuth sign-in.
#
# Usage:
#   ./login.sh
#

echo ""
echo "============================================"
echo "  Connect ChatGPT Plus to OpenClaw"
echo "============================================"
echo ""
echo "  This will open a browser window."
echo "  Sign in with the family ChatGPT Plus account."
echo ""

# Check container is running
if ! docker ps --format '{{.Names}}' | grep -q '^openclaw-gateway$'; then
  echo "  Error: openclaw-gateway container is not running."
  echo "  Run ./bootstrap.sh first."
  exit 1
fi

docker exec -it openclaw-gateway \
  openclaw models auth login --provider openai-codex --set-default

echo ""
echo "============================================"
echo "  Verifying..."
echo "============================================"
echo ""

docker exec openclaw-gateway openclaw models status

echo ""
echo "  If you see openai-codex under 'Providers w/ OAuth/tokens',"
echo "  you're all set! Try chatting at http://$(hostname -I | awk '{print $1}'):8085"
echo ""
