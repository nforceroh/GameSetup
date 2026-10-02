#!/bin/bash
# Install wot-launcher.sh and reset-mouse-profile.sh into ~/.local/bin.
#
# Safe to re-run: files that already match are left alone.

set -euo pipefail

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST_DIR="$HOME/.local/bin"
SCRIPTS=(wot-launcher.sh reset-mouse-profile.sh)

mkdir -p "$DEST_DIR"

for script in "${SCRIPTS[@]}"; do
    src="$SRC_DIR/$script"
    dest="$DEST_DIR/$script"

    if [ ! -f "$src" ]; then
        echo "error: $src is missing" >&2
        exit 1
    fi

    if [ -f "$dest" ] && cmp -s "$src" "$dest"; then
        echo "unchanged  $dest"
        continue
    fi

    install -m 0755 "$src" "$dest"

    # Read back from disk rather than trusting install's exit status: the whole
    # point of this script is that the copy in ~/.local/bin is what gets run.
    if ! cmp -s "$src" "$dest"; then
        echo "error: $dest does not match $src after install" >&2
        exit 1
    fi
    echo "installed  $dest"
done

echo
echo "Launch with: wot-launcher.sh"
