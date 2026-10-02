#!/bin/bash
# Switch the Logitech G502 between its desktop (0) and gaming (1) profiles.
#
#   reset-mouse-profile.sh          re-apply the last profile successfully set
#   reset-mouse-profile.sh 0        desktop profile
#   reset-mouse-profile.sh 1        gaming profile
#
# This is a thin wrapper around wot-launcher.sh, which holds the mouse logic, so
# the two entry points cannot drift apart.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
LAUNCHER="$SCRIPT_DIR/wot-launcher.sh"

if [ ! -x "$LAUNCHER" ]; then
    echo "Error: $LAUNCHER is missing or not executable." >&2
    exit 1
fi

case "${1:-}" in
    0|1) profile="$1" ;;
    "")   profile="" ;;
    *)
        echo "Usage: $(basename "$0") [0|1]" >&2
        echo "Error: invalid mouse profile: $1 (expected 0 or 1)" >&2
        exit 1
        ;;
esac

if [ -n "$profile" ]; then
    exec "$LAUNCHER" --reset-mouse --profile "$profile"
fi

exec "$LAUNCHER" --reset-mouse