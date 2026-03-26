#!/bin/bash
# Clean stale Chromium singleton locks from previous ungraceful shutdowns.
# Without this, the browser tool times out because Chromium refuses to start
# when it finds locks from a dead process.
find "$HOME/.openclaw/browser" -name 'SingletonLock' -o -name 'SingletonSocket' -o -name 'SingletonCookie' 2>/dev/null | xargs rm -f

# Auto-fix config issues (allowFrom, plugin slots, etc.) before starting
openclaw doctor --fix --force --non-interactive 2>&1 || true

exec openclaw gateway --port 18789
