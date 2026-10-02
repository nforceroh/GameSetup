#!/bin/bash
# Launch World of Tanks, holding the Logitech G502 on its gaming profile while
# the game runs and restoring the desktop profile afterwards.
#
# The mouse and display settings live here rather than in separate scripts,
# because both are applied on the way into a launch. The mouse switch is also
# reachable on its own with --reset-mouse, for when it needs re-applying without
# starting the game.
set -euo pipefail

# Ensure the standard locations are present without discarding the caller's
# PATH, which is where a desktop session puts user-installed tools such as
# flatpak and bottles.
export PATH="$PATH:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

PREFERENCES="${WOT_PREFERENCES:-$HOME/.var/app/com.usebottles.bottles/data/bottles/bottles/WoT/drive_c/users/steamuser/AppData/Roaming/Wargaming.net/WorldOfTanks/preferences.xml}"

PROFILE_CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/g502-profile"
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/wot-launcher"
ERR_LOG="$LOG_DIR/mouse_err.log"
OK_LOG="$LOG_DIR/mouse_success.log"
G502_MATCH="G502"
MOUSE_RETRIES="${MOUSE_RETRIES:-60}"

GAME_PROFILE=1
DESKTOP_PROFILE=0
SPAWN_TIMEOUT=30
BOTTLE="WoT"

# Aslain's WoT Modpack update installer. The bottle's Z: drive maps to /, so a
# host path under ~/Downloads becomes Z:\home\sylvain\Downloads\... . That only
# resolves because Bottles has been granted access to it:
#   flatpak override --user --filesystem=~/Downloads com.usebottles.bottles

# The game's borderless window is deliberately a little wider and taller than
# the panel so it covers the display with no borders, which is why these are not
# the panel's own resolution.
RES_WIDTH=4008
RES_HEIGHT=2255
RES_POSITION_X=0
RES_POSITION_Y=0

PROFILE_ACTIVATED=0

log() {
    mkdir -p "$LOG_DIR"
    printf '[%s] %s\n' "$(date)" "$1" >> "$2"
}

# Switch the G502 to the given profile.
#
# The mouse is not always enumerated when this runs (it may still be waking, or
# a game may have grabbed the USB device), so keep trying for a while.
set_mouse_profile() {
    local profile="$1" device i

    for ((i = 0; i < MOUSE_RETRIES; i++)); do
        device=$(ratbagctl list 2>/dev/null | awk -F: -v want="$G502_MATCH" '
            $0 ~ want {
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", $1)
                print $1
                exit
            }')
        if [ -n "$device" ] && ratbagctl "$device" profile active set "$profile" 2>/dev/null; then
            # The cache directory may not exist yet on a fresh profile.
            mkdir -p "$(dirname "$PROFILE_CACHE")"
            printf '%s\n' "$profile" > "$PROFILE_CACHE"
            log "Switched $device to profile $profile." "$OK_LOG"
            printf '[%s] G502 profile %s applied.\n' "$(date)" "$profile"
            return 0
        fi
        sleep 1
    done

    log "Error: G502 unavailable for profile $profile after $MOUSE_RETRIES attempts." "$ERR_LOG"
    return 1
}

# The profile to restore when no argument is given: whatever was last applied
# successfully, falling back to the desktop profile.
cached_mouse_profile() {
    if [ -s "$PROFILE_CACHE" ]; then
        cat "$PROFILE_CACHE"
    else
        echo "$DESKTOP_PROFILE"
    fi
}

restore_desktop_profile() {
    if [ "$PROFILE_ACTIVATED" -eq 0 ]; then
        return 0
    fi
    PROFILE_ACTIVATED=0
    if ! set_mouse_profile "$DESKTOP_PROFILE"; then
        echo "Error: could not restore the desktop mouse profile." >&2
    fi
}

on_exit() {
    restore_desktop_profile
    # tuned-adm needs no sudo here (polkit allows it for this user), so this is
    # not an interactive prompt risk. It is kept as a floor: if gamemode's
    # end= hook is ever removed or fails, the desktop still gets its CPU
    # profile back rather than being left on throughput-performance.
    if ! tuned-adm profile powersave; then
        echo "Note: could not restore the powersave CPU profile." >&2
    fi
}

game_running() {
    pgrep -i -f "WorldOfTanks" >/dev/null || pgrep -i -f "wot.exe" >/dev/null
}

# Force the borderless geometry in the bottle's preferences.xml.
#
# The game rewrites this file on every exit, which is why this has to run on the
# way into the launch rather than once by hand.
#
# The edit is made in python rather than with sed: the file is CRLF-delimited
# with tab indentation and space-padded values ("<tag> 3840 </tag>"), and a
# regex would risk mangling one of those. Exit code is the signal for whether
# anything changed: 0 = changed, 3 = already correct.
fix_resolution() {
    if [ ! -f "$PREFERENCES" ]; then
        echo "Error: preferences.xml not found at: $PREFERENCES" >&2
        return 1
    fi

    # Keep the original: the game rewrites the file on exit, so without a backup
    # a bad edit is only recoverable by reinstalling. An existing backup is never
    # overwritten, or a second run would replace the pristine original with the
    # already-fixed copy and leave nothing to roll back to.
    local backup="$PREFERENCES.bak"
    if [ -e "$backup" ]; then
        echo "Backup already exists at $backup (left alone)."
    else
        cp -p "$PREFERENCES" "$backup"
        echo "Backed up to $backup"
    fi

    local status
    set +e
    WOT_PREFS="$PREFERENCES" WOT_WIDTH="$RES_WIDTH" WOT_HEIGHT="$RES_HEIGHT" \
    WOT_X="$RES_POSITION_X" WOT_Y="$RES_POSITION_Y" python3 - <<'PYTHON'
import os
import sys

path = os.environ["WOT_PREFS"]
wanted = {
    "borderlessWidth": os.environ["WOT_WIDTH"],
    "borderlessHeight": os.environ["WOT_HEIGHT"],
    "borderlessPositionX": os.environ["WOT_X"],
    "borderlessPositionY": os.environ["WOT_Y"],
}

with open(path, "rb") as fh:
    raw = fh.read()

text = raw.decode("utf-8", errors="surrogateescape")
crlf = "\r\n" in text
lines = text.split("\r\n") if crlf else text.split("\n")
eol = "\r\n" if crlf else "\n"

changed = []
seen = set()

for i, line in enumerate(lines):
    stripped = line.strip()
    for tag, value in wanted.items():
        open_tag, close_tag = f"<{tag}>", f"</{tag}>"
        if not (stripped.startswith(open_tag) and close_tag in stripped):
            continue
        seen.add(tag)
        current = stripped[len(open_tag):stripped.index(close_tag)]
        new_line = line.replace(
            f"{open_tag}{current}{close_tag}", f"{open_tag} {value} {close_tag}", 1
        )
        if new_line != line:
            changed.append((tag, current.strip(), value))
            lines[i] = new_line

missing = sorted(set(wanted) - seen)
if missing:
    sys.exit(f"error: not found in {path}: {', '.join(missing)}")

if not changed:
    sys.exit(3)

with open(path, "wb") as fh:
    fh.write(eol.join(lines).encode("utf-8", errors="surrogateescape"))

# Read back rather than trusting the write: this is the file the game will read.
with open(path, "rb") as fh:
    after = fh.read().decode("utf-8", errors="surrogateescape")
for tag, value in wanted.items():
    open_tag, close_tag = f"<{tag}>", f"</{tag}>"
    if f"{open_tag} {value} {close_tag}" not in after:
        sys.exit(f"error: {tag} did not read back as {value} after writing")

for tag, before, after_value in changed:
    print(f"set {tag}: {before} -> {after_value}")
PYTHON
    status=$?
    set -e

    if [ "$status" -ne 0 ] && [ "$status" -ne 3 ]; then
        echo "Error: failed to update $PREFERENCES" >&2
        return 1
    fi

    if [ "$status" -eq 3 ]; then
        echo "Borderless window already ${RES_WIDTH}x${RES_HEIGHT}."
    else
        echo "Borderless window set to ${RES_WIDTH}x${RES_HEIGHT} at (${RES_POSITION_X},${RES_POSITION_Y})."
    fi
    return 0
}

# Bottles can return before Wine has registered a process name, so wait for the
# game to appear. Testing for its absence straight away would match nothing and
# exit immediately, leaving the mouse stuck on the gaming profile.
wait_for_game() {
    local i
    for ((i = 0; i < SPAWN_TIMEOUT; i++)); do
        if game_running; then
            return 0
        fi
        sleep 1
    done
    return 1
}

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

  --fixres          force the game's borderless window to fill the display
                    before launching (the game resets it on exit)
  --no-fixres       launch without touching preferences.xml (default)
  --width N         borderless window width, with --fixres  (default 4008)
  --height N        borderless window height, with --fixres (default 2255)
  --reset-mouse     set the mouse profile and exit, without launching the game.
                    Re-applies the last profile used unless --profile is given.
  --profile N       mouse profile to apply (default 1 for the game)
  --install-mod [PATH]
                    run the Aslain's modpack update and exit, without
                    launching the game. PATH may be a host path or a Windows
                    path; it defaults to the newest Aslains installer in
                    ~/Downloads
  -h, --help        show this help
EOF
}

# Resolution fixing is opt-in. WoT rewrites preferences.xml on every exit, so
# applying it unconditionally would rewrite the file on each launch for nothing.
FIX_RES=0
RESET_MOUSE_ONLY=0
INSTALL_MOD=0
INSTALL_MOD_PATH=""
MOUSE_PROFILE_ARG=""

while [ $# -gt 0 ]; do
    case "$1" in
        --fixres)      FIX_RES=1; shift ;;
        --no-fixres)   FIX_RES=0; shift ;;
        --reset-mouse) RESET_MOUSE_ONLY=1; shift ;;
        --install-mod)
            INSTALL_MOD=1
            # Optional path: consume the next argument only if it is not
            # another option. `shift` before the test, so $2 is the right one.
            shift
            if [ $# -ge 1 ] && [ "${1#-}" = "$1" ]; then
                INSTALL_MOD_PATH="$1"
                shift
            fi
            ;;
        --install-mod=*) INSTALL_MOD=1; INSTALL_MOD_PATH="${1#*=}"; shift ;;
        --profile)     [ $# -ge 2 ] || { usage >&2; echo "Error: --profile needs a value" >&2; exit 1; }
                       MOUSE_PROFILE_ARG="$2"; shift 2 ;;
        --width)       [ $# -ge 2 ] || { usage >&2; echo "Error: --width needs a value" >&2; exit 1; }
                       RES_WIDTH="$2"; shift 2 ;;
        --height)      [ $# -ge 2 ] || { usage >&2; echo "Error: --height needs a value" >&2; exit 1; }
                       RES_HEIGHT="$2"; shift 2 ;;
        --width=*)    RES_WIDTH="${1#*=}";    shift ;;
        --height=*)   RES_HEIGHT="${1#*=}";   shift ;;
        --profile=*)  MOUSE_PROFILE_ARG="${1#*=}"; shift ;;
        -h|--help)    usage; exit 0 ;;
        *)             usage >&2; echo "Error: unknown argument: $1" >&2; exit 1 ;;
    esac
done

# --reset-mouse reuses --profile/--width/--height as the profile to apply, so a
# single set of numeric options serves both the game and the standalone switch.
if [ -n "$MOUSE_PROFILE_ARG" ]; then
    case "$MOUSE_PROFILE_ARG" in
        0|1) ;;
        *) echo "Error: --profile must be 0 or 1 (got '$MOUSE_PROFILE_ARG')" >&2; exit 1 ;;
    esac
    if [ "$RESET_MOUSE_ONLY" -eq 1 ]; then
        set_mouse_profile "$MOUSE_PROFILE_ARG"
        exit $?
    fi
    GAME_PROFILE="$MOUSE_PROFILE_ARG"
fi

if [ "$RESET_MOUSE_ONLY" -eq 1 ]; then
    set_mouse_profile "$(cached_mouse_profile)"
    exit $?
fi

# The modpack update is its own operation: it must not switch the mouse to the
# gaming profile, apply the resolution fix, or start the game afterwards. So it
# returns before any of that.
if [ "$INSTALL_MOD" -eq 1 ]; then
    if [ "$(id -u)" -eq 0 ]; then
        echo "Warning: running as root; Bottles will use root's config." >&2
    fi

    # A path may be given as a host path (/home/...) or a Windows path (Z:\... or
    # C:\...). Whichever form it arrives in, it has to end up as a Windows path,
    # because that is what bottles-cli passes to Wine.
    win_path=""
    if [ -n "$INSTALL_MOD_PATH" ]; then
        case "$INSTALL_MOD_PATH" in
            [A-Za-z]:\\*)
                win_path="$INSTALL_MOD_PATH"
                host_path="/${win_path#?:}"
                host_path="/${host_path//\\//}"
                ;;
            /*)
                host_path="$INSTALL_MOD_PATH"
                # Z: maps to /, so the host path is the same path on the drive.
                win_path="Z:${host_path//\//\\}"
                ;;
            *)
                echo "Error: --install-mod path must be absolute: $INSTALL_MOD_PATH" >&2
                exit 1
                ;;
        esac
    else
        # No path given: take the most recent Aslains installer in ~/Downloads.
        host_path=$(ls -t "$HOME"/Downloads/Aslains*Installer*.exe 2>/dev/null | head -1 || true)
        if [ -z "$host_path" ]; then
            echo "Error: no Aslains installer found in $HOME/Downloads." >&2
            echo "Pass one explicitly: --install-mod /path/to/installer.exe" >&2
            exit 1
        fi
        win_path="Z:${host_path//\//\\}"
    fi

    if [ ! -f "$host_path" ]; then
        echo "Error: installer not found: $host_path" >&2
        exit 1
    fi

    echo "Running modpack installer: $win_path"
    echo "Close the installer window when it has finished."
    flatpak run --command=bottles-cli com.usebottles.bottles run -b "$BOTTLE" -e "$win_path"
    exit $?
fi

trap on_exit EXIT

if [ "$(id -u)" -eq 0 ]; then
    echo "Warning: running as root; the game and Bottles will use root's config." >&2
fi

if ! set_mouse_profile "$GAME_PROFILE"; then
    echo "Error: could not activate the World of Tanks mouse profile." >&2
    exit 1
fi
PROFILE_ACTIVATED=1
echo "World of Tanks mouse profile activated."

# Applied after the profile switch, and inside the trap, so a failure here still
# puts the mouse profile back.
if [ "$FIX_RES" -eq 1 ]; then
    if ! fix_resolution; then
        echo "Warning: could not set the borderless window size; continuing anyway." >&2
    fi
fi

flatpak run --command=bottles-cli com.usebottles.bottles run -b "$BOTTLE" -p "WorldOfTanks"

if ! wait_for_game; then
    echo "Error: World of Tanks did not appear within ${SPAWN_TIMEOUT}s." >&2
    exit 1
fi

echo "Waiting for World of Tanks to exit..."
while game_running; do
    sleep 3
done

echo "World of Tanks has closed."
