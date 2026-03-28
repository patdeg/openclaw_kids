#!/usr/bin/env bash
# setup-codex-sudo.sh — Temporarily enable passwordless sudo for Codex sessions
#
# Codex runs commands in a sandbox that can't access the sudo credential cache.
# This script adds a sudoers drop-in that lets your user run sudo without a
# password. Run remove-codex-sudo.sh when you're done.

set -euo pipefail

USER_NAME="$(logname 2>/dev/null || echo "$USER")"
DROP_IN="/etc/sudoers.d/codex-nopasswd"

if [ -f "$DROP_IN" ]; then
    echo "Passwordless sudo is already enabled for $USER_NAME."
    echo "Run remove-codex-sudo.sh when you're done with Codex."
    exit 0
fi

echo "$USER_NAME ALL=(ALL) NOPASSWD: ALL" | sudo tee "$DROP_IN" > /dev/null
sudo chmod 440 "$DROP_IN"

# Validate — a broken sudoers file can lock you out
if sudo visudo -c > /dev/null 2>&1; then
    echo "Passwordless sudo enabled for $USER_NAME."
    echo "Run remove-codex-sudo.sh when you're done with Codex."
else
    echo "ERROR: sudoers validation failed — rolling back!"
    sudo rm -f "$DROP_IN"
    exit 1
fi
