#!/bin/bash
# Launch World of Tanks with umu-run, managing the G502 profile and optional
# resolution, modpack, and Game Center operations.
set -euo pipefail

export PATH="$PATH:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

export WINEPREFIX="${WOT_PREFIX:-$HOME/Games/WoT/prefix}"
export PROTONPATH="${PROTONPATH:-$HOME/.local/share/Steam/compatibilitytools.d/GE-Proton11-11-x86_64}"
export GAMEID="${GAMEID:-umu-default}"
export WINEFSYNC=1
export WINE_CPU_TOPOLOGY=8:0,1,2,3,4,5,6,7
export PULSE_LATENCY_MSEC=60
export DRI_PRIME=1
export LFX=1

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
# shellcheck source=WoT/g502-profile.sh
source "$SCRIPT_DIR/g502-profile.sh"
GAME_PROFILE=1

PREFERENCES="${WOT_PREFERENCES:-$WINEPREFIX/drive_c/users/steamuser/AppData/Roaming/Wargaming.net/WorldOfTanks/preferences.xml}"
FIX_RES=0
RESET_MOUSE_ONLY=0
INSTALL_MOD=0
INSTALL_MOD_PATH=""
WCG_ONLY=0
MOUSE_PROFILE_ARG=""
RES_WIDTH=4008
RES_HEIGHT=2255
RES_POSITION_X=0
RES_POSITION_Y=0
GAME_ARGS=()
GAME_EXE="$WINEPREFIX/drive_c/Games/World_of_Tanks_NA/win64/WorldOfTanks.exe"
WGC_EXE="$WINEPREFIX/drive_c/Program Files/Wargaming.net/GameCenter/wgc.exe"

on_exit() {
    local exit_status=$?
    restore_desktop_profile
    trap - EXIT
    exit "$exit_status"
}

fix_resolution() {
    if [ ! -f "$PREFERENCES" ]; then
        echo "Error: preferences.xml not found at: $PREFERENCES" >&2
        return 1
    fi

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
}

usage() {
    cat <<EOF
Usage: $(basename "$0") [options] [game arguments]

  --fixres          force the game's borderless window to fill the display
                    before launching (the game resets it on exit)
  --no-fixres       launch without touching preferences.xml (default)
  --width N         borderless window width with --fixres (default 4008)
  --height N        borderless window height with --fixres (default 2255)
  --reset-mouse     set the mouse profile and exit; defaults to the cached profile
  --profile N       profile to apply (0 desktop, 1 gaming; default 1 for the game)
  --install-mod [PATH]
                    run an Aslain's installer and exit; defaults to the newest
                    matching installer in ~/Downloads
  --wcg             open Wargaming Game Center and exit
  -h, --help        show this help

Set WOT_PREFIX to override the default prefix at ~/Games/WoT/prefix.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --fixres)      FIX_RES=1; shift ;;
        --no-fixres)   FIX_RES=0; shift ;;
        --reset-mouse) RESET_MOUSE_ONLY=1; shift ;;
        --wcg)         WCG_ONLY=1; shift ;;
        --install-mod)
            INSTALL_MOD=1
            shift
            if [ $# -ge 1 ] && [ "${1#-}" = "$1" ]; then
                INSTALL_MOD_PATH="$1"
                shift
            fi
            ;;
        --install-mod=*) INSTALL_MOD=1; INSTALL_MOD_PATH="${1#*=}"; shift ;;
        --profile)
            [ $# -ge 2 ] || { usage >&2; echo "Error: --profile needs a value" >&2; exit 1; }
            MOUSE_PROFILE_ARG="$2"
            shift 2
            ;;
        --width)
            [ $# -ge 2 ] || { usage >&2; echo "Error: --width needs a value" >&2; exit 1; }
            RES_WIDTH="$2"
            shift 2
            ;;
        --height)
            [ $# -ge 2 ] || { usage >&2; echo "Error: --height needs a value" >&2; exit 1; }
            RES_HEIGHT="$2"
            shift 2
            ;;
        --width=*)    RES_WIDTH="${1#*=}"; shift ;;
        --height=*)   RES_HEIGHT="${1#*=}"; shift ;;
        --profile=*)  MOUSE_PROFILE_ARG="${1#*=}"; shift ;;
        -h|--help)    usage; exit 0 ;;
        --)
            shift
            GAME_ARGS+=("$@")
            break
            ;;
        *)
            GAME_ARGS+=("$@")
            break
            ;;
    esac
done

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

if [ "$INSTALL_MOD" -eq 1 ]; then
    if [ -n "$INSTALL_MOD_PATH" ]; then
        case "$INSTALL_MOD_PATH" in
            [A-Za-z]:\\*)
                drive="${INSTALL_MOD_PATH:0:1}"
                path_part="${INSTALL_MOD_PATH:2}"
                path_part="${path_part//\\//}"
                case "$drive" in
                    [Zz]) host_path="/${path_part#/}" ;;
                    [Cc]) host_path="$WINEPREFIX/drive_c/${path_part#/}" ;;
                    *)
                        echo "Error: unsupported Windows drive in installer path: $INSTALL_MOD_PATH" >&2
                        exit 1
                        ;;
                esac
                ;;
            /*) host_path="$INSTALL_MOD_PATH" ;;
            *)
                echo "Error: installer path must be absolute: $INSTALL_MOD_PATH" >&2
                exit 1
                ;;
        esac
    else
        host_path=""
        if [ -d "$HOME/Downloads" ]; then
            if ! host_path=$(find "$HOME/Downloads" -maxdepth 1 -type f -name 'Aslains*Installer*.exe' -printf '%T@ %p\n' 2>/dev/null | sort -nr | sed -n '1s/^[^ ]* //p'); then
                echo "Error: failed to search $HOME/Downloads for an Aslains installer." >&2
                exit 1
            fi
        fi
        if [ -z "$host_path" ]; then
            echo "Error: no Aslains installer found in $HOME/Downloads." >&2
            echo "Pass one explicitly: --install-mod /path/to/installer.exe" >&2
            exit 1
        fi
    fi

    if [ ! -f "$host_path" ]; then
        echo "Error: installer not found: $host_path" >&2
        exit 1
    fi

    echo "Running modpack installer: $host_path"
    echo "Close the installer window when it has finished."
    umu-run "$host_path"
    exit $?
fi

if [ "$WCG_ONLY" -eq 1 ]; then
    if [ ! -f "$WGC_EXE" ]; then
        echo "Error: Wargaming Game Center not found at: $WGC_EXE" >&2
        exit 1
    fi
    umu-run "$WGC_EXE"
    exit $?
fi

if [ ! -f "$GAME_EXE" ]; then
    echo "Error: World of Tanks executable not found at: $GAME_EXE" >&2
    exit 1
fi

cd "$(dirname "$GAME_EXE")"
trap on_exit EXIT

if ! set_mouse_profile "$GAME_PROFILE"; then
    echo "Error: could not activate the World of Tanks mouse profile." >&2
    exit 1
fi
PROFILE_ACTIVATED=1
echo "World of Tanks mouse profile activated."

if [ "$FIX_RES" -eq 1 ] && ! fix_resolution; then
    echo "Warning: could not set the borderless window size; continuing anyway." >&2
fi

if command -v gamemoderun >/dev/null; then
    gamemoderun umu-run "$GAME_EXE" "${GAME_ARGS[@]}"
else
    umu-run "$GAME_EXE" "${GAME_ARGS[@]}"
fi
