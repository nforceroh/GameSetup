# Handoff: remove mouse-profile handling from wot-launcher.sh

## Context

LinGHub now owns the mouse. It watches for games and loads the matching profile
into slot 1, restoring the desktop profile into slot 0 when the game exits. The
launcher must stop doing the same job, or the two fight over the mouse.

This was already done for the **installed** copy at
`~/.local/bin/wot-launcher.sh`. This handoff covers the **tracked** copy at
`~/repositories/GameSetup/WoT/wot-launcher.sh`, which still has the old logic.

## Why it matters

Observed on a real launch before the installed copy was fixed:

```
07:01:12  launcher switched the mouse to slot 1
07:01:19  LinGHub noticed the game and wrote the WoT profile into slot 1
```

For those seven seconds the mouse was on slot 1 holding the *previous* profile's
bindings, because the launcher switched the slot before LinGHub had written the
new profile into it. Two writers, one mouse, wrong state in between.

## The two copies

| Path | State |
| --- | --- |
| `~/.local/bin/wot-launcher.sh` | **Already fixed.** 266 lines, no mouse logic. |
| `~/repositories/GameSetup/WoT/wot-launcher.sh` | **Needs fixing.** 310 lines, still has it. |

They are not symlinked. The installed copy is a regular file, so the two have
drifted. The tracked copy is the one in git (`GameSetup` repo).

The fixed copy is the reference implementation. Diffing the two shows exactly
what to remove:

```bash
diff ~/repositories/GameSetup/WoT/wot-launcher.sh ~/.local/bin/wot-launcher.sh
```

## What to remove

Line numbers below are for the **tracked** copy as it stands (310 lines).

### 1. Header comment (lines 2–3)

```bash
# Launch World of Tanks with umu-run, managing the G502 profile and optional
# resolution, modpack, and Game Center operations.
```

Replace with:

```bash
# Launch World of Tanks with umu-run, with optional resolution, modpack, and
# Game Center operations.
#
# The mouse profile is not managed here: LinGHub owns the mouse and switches
# profiles when it detects the game.
```

### 2. Sourcing the helper and the profile variable (lines 17–19)

```bash
SCRIPT_DIR="$HOME/.local/bin"
source "$SCRIPT_DIR/g502-profile.sh"
GAME_PROFILE=1
```

Delete all three. `SCRIPT_DIR` becomes unused once the `source` goes, so it must
go too or shellcheck will flag it.

### 3. Two variable declarations (lines 23 and 28)

```bash
RESET_MOUSE_ONLY=0
MOUSE_PROFILE_ARG=""
```

Delete both.

### 4. The exit trap (lines 38–44)

```bash
on_exit() {
    local exit_status=$?
    restore_desktop_profile
    trap - EXIT
    exit "$exit_status"
}
```

Delete the whole function. Its only job was restoring the desktop profile.

### 5. Usage text (lines 144–145)

```bash
  --reset-mouse     set the mouse profile and exit; defaults to the cached profile
  --profile N       profile to apply (0 desktop, 1 gaming; default 1 for the game)
```

Delete both lines.

### 6. Argument parsing (lines 161, 173–177, 190)

```bash
        --reset-mouse) RESET_MOUSE_ONLY=1; shift ;;
```

```bash
        --profile)
            [ $# -ge 2 ] || { usage >&2; echo "Error: --profile needs a value" >&2; exit 1; }
            MOUSE_PROFILE_ARG="$2"
            shift 2
            ;;
```

```bash
        --profile=*)  MOUSE_PROFILE_ARG="${1#*=}"; shift ;;
```

Delete all three cases.

### 7. Post-parse handling (lines 204–220)

```bash
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
```

Delete both blocks entirely.

### 8. The launch sequence (lines 293–300)

```bash
trap on_exit EXIT

if ! set_mouse_profile "$GAME_PROFILE"; then
    echo "Error: could not activate the World of Tanks mouse profile." >&2
    exit 1
fi
PROFILE_ACTIVATED=1
echo "World of Tanks mouse profile activated."
```

Delete all of it. What remains around it should read:

```bash
cd "$(dirname "$GAME_EXE")"

if [ "$FIX_RES" -eq 1 ] && ! fix_resolution; then
    echo "Warning: could not set the borderless window size; continuing anyway." >&2
fi
```

## What must NOT change

- `fix_resolution()` and the `--fixres` / `--width` / `--height` options
- `--mod`, `--modmgr`, `--wcg` and their handlers
- The `umu-run` / `gamemoderun` launch at the end
- `set -euo pipefail` and the `PATH` export

## Verification

```bash
# 1. Syntax
bash -n ~/repositories/GameSetup/WoT/wot-launcher.sh

# 2. No mouse references remain
grep -n "g502-profile\|set_mouse_profile\|restore_desktop_profile\|cached_mouse_profile\|PROFILE_ACTIVATED\|GAME_PROFILE\|MOUSE_PROFILE_ARG\|RESET_MOUSE_ONLY\|on_exit\|trap\|SCRIPT_DIR" \
  ~/repositories/GameSetup/WoT/wot-launcher.sh
# expect: no output

# 3. Help text no longer mentions the mouse
~/repositories/GameSetup/WoT/wot-launcher.sh --help

# 4. The two copies should now differ only in trivia
diff ~/repositories/GameSetup/WoT/wot-launcher.sh ~/.local/bin/wot-launcher.sh
```

## Note on `g502-profile.sh`

`~/.local/bin/g502-profile.sh` has already been deleted, along with
`~/.cache/g502-profile` and `~/.local/state/wot-launcher/`. If the tracked copy
still sources it, the launcher will fail at startup with
`No such file or directory` — which is another reason this change is urgent
rather than cosmetic.

## After the change

Decide whether the installed copy should be a symlink to the tracked one, so
they cannot drift again:

```bash
ln -sf ~/repositories/GameSetup/WoT/wot-launcher.sh ~/.local/bin/wot-launcher.sh
```

That is a separate decision; the removal above stands either way.
