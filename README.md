# wot-launcher

Launch World of Tanks through Bottles, holding the Logitech G502 on its gaming
profile while the game runs and restoring the desktop profile afterwards.

Optionally forces the game's borderless window to fill the display, since the
game resets that on every exit.

## Install

```bash
./install.sh              # copies both scripts to ~/.local/bin
wot-launcher.sh           # launch the game
reset-mouse-profile.sh 0  # switch the mouse back to desktop
```

`install.sh` is safe to re-run: a file that already matches is left alone, and
each copy is verified against the source with `cmp` after writing.

## Files

| Script | Purpose |
| --- | --- |
| `wot-launcher.sh` | Mouse profile, resolution fix, launch, wait, restore. |
| `reset-mouse-profile.sh` | Standalone mouse switch, for changing profile without launching. |
| `install.sh` | Installs both scripts into `~/.local/bin`. |

`reset-mouse-profile.sh` is a thin wrapper that calls `wot-launcher.sh
--reset-mouse`, so the mouse logic exists in one place only and the two entry
points cannot drift apart:

```bash
reset-mouse-profile.sh        # re-apply the last profile used
reset-mouse-profile.sh 0      # desktop
reset-mouse-profile.sh 1      # gaming
```

Neither script needs `sudo`; `ratbagctl` works as your user.

## Options for wot-launcher.sh

| Option | Effect |
| --- | --- |
| `--fixres` | Set the borderless geometry in `preferences.xml` before launching. |
| `--width N` / `--height N` | Override the size used by `--fixres` (default 4008x2255). |
| `--reset-mouse` | Set the mouse profile and exit, without launching. Re-applies the cached profile unless `--profile` is given. |
| `--profile N` | Mouse profile, `0` (desktop) or `1` (gaming). Defaults to `1` for the game. |
| `--install-mod [PATH]` | Run the Aslain's modpack update and exit, without launching the game. Defaults to the newest installer in `~/Downloads`. |

## Updating the modpack

```bash
wot-launcher.sh --install-mod
```

Runs the newest Aslain's installer found in `~/Downloads` inside the bottle, then
exits. It does **not** switch the mouse profile, apply the resolution fix, or
start the game afterwards — it is a separate operation.

The installer is reached through the bottle's `Z:` drive, which maps to `/`, so
`~/Downloads` appears as `Z:\home\sylvain\Downloads`. This only works because
Bottles has been granted access to it:

```bash
flatpak override --user --filesystem=~/Downloads com.usebottles.bottles
```

Without that override the sandbox cannot see `~/Downloads` at all, and the run
fails. The script checks the host path first and says so rather than handing
Wine a path that will not resolve.

Point it elsewhere by passing a path, as either a host or a Windows path:

```bash
wot-launcher.sh --install-mod                                   # newest in ~/Downloads
wot-launcher.sh --install-mod ~/Downloads/SomeOtherInstaller.exe
wot-launcher.sh --install-mod 'Z:\home\sylvain\Downloads\SomeOtherInstaller.exe'
```

The path is converted to a Windows path automatically, since that is what
`bottles-cli` hands to Wine.

State is kept in:

- `~/.cache/g502-profile` — last mouse profile applied
- `~/.local/state/wot-launcher/mouse_{success,err}.log` — logs

## The resolution fix

`--fixres` is opt-in because WoT rewrites `preferences.xml` on every exit, so
applying it unconditionally would rewrite the file on each launch for nothing.

It edits four keys under `root/devicePreferences`:

```xml
<borderlessWidth> 4008 </borderlessWidth>
<borderlessHeight> 2255 </borderlessHeight>
<borderlessPositionX> 0 </borderlessPositionX>
<borderlessPositionY> 0 </borderlessPositionY>
```

The window is deliberately slightly wider and taller than the panel, which is
why these are not the panel's own resolution.

The edit is made in python rather than with `sed`, because the file is
CRLF-delimited with tab indentation and space-padded values (`<tag> 3840 </tag>`),
and a regex would risk mangling one of those. The values are read back from disk
afterwards to confirm the write landed.

A backup is written to `preferences.xml.bak` on the first run and is **never
overwritten** — re-running would otherwise replace the pristine original with the
already-fixed copy, leaving nothing to roll back to. Override the path with
`WOT_PREFERENCES` if the bottle ever moves.

## Enabling the gamemode CPU / display profile

The launcher does **not** run gamemode, and does not need to. **Bottles already
enables gamemode for World of Tanks.** What is left is the configuration: the
`[custom]` hooks that switch the CPU profile and the display mode.

Your existing `/etc/gamemode.ini` already does this correctly and needs no
changes. The notes below explain why it works, and the one trap to be aware of
if you ever edit it.

### 1. Who requests gamemode, and what the known-games list really affects

**Bottles already requests gamemode for the game**, so no extra step is needed
in the launcher. The `start=` and `end=` hooks below run as soon as the game
registers as a gamemode client, and it does — the game being absent from
gamemode's list of *known* games only means gamemode does not apply its
built-in per-game tuning, not that custom hooks are skipped.

So the only thing that needs doing is the config. No `gamemoderun` wrapper
belongs in `wot-launcher.sh`: gamemode would be requested twice, and the
launcher would be assuming something the runner is already responsible for.

What the known-games list *does* affect is the automatic CPU governor and
iopriority tuning. The tuned profile and display mode changes come from your
`[custom]` hooks, not from the list, which is why setting them explicitly is
worth doing here.

### 2. Config files are merged, not shadowed

`gamemoded` loads and **merges** `gamemode.ini` from these directories, in
order, with later files overriding earlier ones key by key:

1. `/usr/share/gamemode/`
2. `/etc/`
3. `$XDG_CONFIG_HOME` or `$HOME/.config/`
4. `$PWD`

So your `/etc/gamemode.ini` **is** read, and it is not dead. The gotcha is the
opposite of what it looks like: because the files merge, a key you set in
`/etc/gamemode.ini` is *not* isolated — you cannot override just one setting
from a user file without inheriting everything else in `/etc`.

Note also that `$PWD` is searched. Running a game from a directory that happens
to contain a `gamemode.ini` will silently change gamemode's behaviour. This
repo directory does not contain one, so `wot-launcher.sh` is unaffected — but
it is a reason to be careful about `cd`-ing somewhere unexpected before
launching.

### 3. Enable the service

`gamemoded` is running now, but the unit is `disabled`, so it will not come back
after a reboot:

```bash
sudo systemctl enable --now gamemoded.service
```

### The config

Your existing `/etc/gamemode.ini` is correct as written and needs no changes.
For reference:

```ini
[custom]
; Switches CPU profile and pushes the gaming display to 144Hz.
start=tuned-adm profile throughput-performance; kscreen-doctor output.DP-1.mode.3840x2160@144

; Drops CPU profile and returns the display to 30Hz so VRAM can drop to
; 96MHz (~30W).
end=tuned-adm profile powersave; kscreen-doctor output.DP-1.mode.3840x2160@30

[gpu]
apply_gpu_optimisations=accept-responsibility
gpu_device=1
amd_performance_level=high
```

Two details worth knowing if you edit it later:

- `script_timeout` is left at its 10s default. The hooks take ~1.1s and
  ~0.04s, so there is no need to raise it.
- `tuned-adm profile` works without `sudo` on this machine, via a polkit rule,
  so the hooks do not need root.

After editing, restart the daemon so it re-reads the config:

```bash
sudo systemctl restart gamemoded.service
```

### A note on DP-1

`DP-1` is the only output on this machine offering `3840x2160@144.00`; the
others top out at 120Hz (HDMI-A-2) and 75Hz (DP-2, DP-4). Connector names are
assigned by enumeration order, so they are worth rechecking if you change
monitors or cables.

## Interaction with the launcher's tuned call

`wot-launcher.sh` ends with `tuned-adm profile powersave`, which overlaps with
gamemode's `end=` hook — both write the same setting, so whichever finishes
last wins. It is deliberately kept, as a floor rather than a duplicate:

- gamemode's `end=` hook also resets the **display mode**, which the launcher
  knows nothing about;
- if gamemode is disabled or its hook fails, the CPU profile would otherwise be
  stranded on `throughput-performance` indefinitely.

`tuned-adm profile` works without `sudo` on this machine (a polkit rule allows
it for this user), so the call cannot block on a password prompt. It was
previously `sudo -n tuned-adm`, which failed silently whenever sudo
authentication was not cached.

To remove it instead, delete the `tuned-adm` call from `on_exit` in
`wot-launcher.sh` — but then nothing outside gamemode is left to put the CPU
profile back.
