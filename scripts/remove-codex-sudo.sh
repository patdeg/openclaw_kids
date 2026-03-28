#!/usr/bin/env bash
# remove-codex-sudo.sh — Remove passwordless sudo (back to normal)
#
# Reverses what setup-codex-sudo.sh did. Always run this when you're done
# with a Codex session that needed sudo.

set -euo pipefail

DROP_IN="/etc/sudoers.d/codex-nopasswd"

if [ ! -f "$DROP_IN" ]; then
    echo "Passwordless sudo is not enabled — nothing to remove."
    exit 0
fi

sudo rm -f "$DROP_IN"

if sudo visudo -c > /dev/null 2>&1; then
    echo "Passwordless sudo removed. Sudo now requires your password again."
else
    echo "WARNING: sudoers validation returned an error. Run: sudo visudo -c"
fi
