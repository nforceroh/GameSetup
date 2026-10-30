#!/bin/bash

PROFILE_CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/g502-profile"
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/wot-launcher"
ERR_LOG="$LOG_DIR/mouse_err.log"
OK_LOG="$LOG_DIR/mouse_success.log"
G502_MATCH="G502"
MOUSE_RETRIES="${MOUSE_RETRIES:-60}"
DESKTOP_PROFILE=0
PROFILE_ACTIVATED=0

log() {
    mkdir -p "$LOG_DIR"
    printf '[%s] %s\n' "$(date)" "$1" >> "$2"
}

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
            mkdir -p "$(dirname "$PROFILE_CACHE")"
            printf '%s\n' "$profile" > "$PROFILE_CACHE"
            log "Switched $device to profile $profile." "$OK_LOG"
            printf '[%s] G502 profile %s applied.\n' "$(date)" "$profile"
            return 0
        fi
        sleep 1
    done

    log "Error: G502 unavailable for profile $profile after $MOUSE_RETRIES attempts." "$ERR_LOG"
    if ! ratbagctl list 2>/dev/null | grep -q "$G502_MATCH"; then
        echo "Hint: ratbagctl does not list the G502. If it lists no devices at all, check for stale Wine processes holding deleted /dev/hidraw nodes (ls -l /proc/[0-9]*/fd 2>/dev/null | grep 'hidraw.*deleted'); killing them and re-plugging the receiver restores the hidraw nodes." >&2
    fi
    return 1
}

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

usage() {
    cat <<EOF
Usage: $(basename "$0") [--help] [--profile] [0|1]

Set the G502 active profile directly:
  $(basename "$0") 0
  $(basename "$0") --profile 1

With no profile argument, re-apply the last profile set (or desktop profile 0
if no profile has been cached).
EOF
}

main() {
    local profile

    case "$#" in
        0) profile="$(cached_mouse_profile)" ;;
        1)
            case "$1" in
                -h|--help) usage; return 0 ;;
                0|1) profile="$1" ;;
                *)
                    usage >&2
                    echo "Error: expected profile 0 or 1, got '$1'." >&2
                    return 2
                    ;;
            esac
            ;;
        2)
            if [ "$1" != "--profile" ]; then
                usage >&2
                echo "Error: expected --profile before the profile number." >&2
                return 2
            fi
            profile="$2"
            ;;
        *)
            usage >&2
            echo "Error: too many arguments." >&2
            return 2
            ;;
    esac

    case "$profile" in
        0|1) set_mouse_profile "$profile" ;;
        *)
            usage >&2
            echo "Error: profile must be 0 or 1, got '$profile'." >&2
            return 2
            ;;
    esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
