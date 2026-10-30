# GameSetup

Setup notes and scripts for my games. Each game gets its own directory with its
instructions and scripts.

## World of Tanks

`wot-launcher.sh` runs the game from `~/Games/WoT/prefix` through umu,
switches the Logitech G502 to its gaming profile, and restores the desktop
profile on exit. It can optionally force the game's borderless window to fill
the display, since the game resets that on every exit.

## Install

```bash
./install.sh                          # copies the launcher and helper to ~/.local/bin
wot-launcher.sh                   # launch through umu
wot-launcher.sh --reset-mouse --profile 0  # switch the mouse back to desktop
```

`install.sh` is safe to re-run: a file that already matches is left alone, and
each copy is verified against the source with `cmp` after writing.

## Files

| Script | Purpose |
| --- | --- |
| `wot-launcher.sh` | umu launch, mouse profile, resolution fix, modpack update, and Game Center. |
| `g502-profile.sh` | Shared mouse-profile functions and standalone profile switcher. |
| `install.sh` | Installs the UMU launcher and mouse helper into `~/.local/bin`. |

The launcher sources `g502-profile.sh`, which can also be run directly to
switch profiles without launching a game:

```bash
g502-profile.sh --help
g502-profile.sh             # re-apply the last profile used
g502-profile.sh 0           # desktop
g502-profile.sh --profile 1 # gaming
```

The launcher and mouse helper do not need `sudo`; `ratbagctl` works as your user.

## Options for wot-launcher.sh

| Option | Effect |
| --- | --- |
| `--fixres` | Set the borderless geometry in the UMU prefix before launching. |
| `--width N` / `--height N` | Override the size used by `--fixres` (default 4008x2255). |
| `--reset-mouse` | Set the mouse profile and exit; re-applies the cached profile unless `--profile` is given. |
| `--profile N` | Mouse profile, `0` (desktop) or `1` (gaming). Defaults to `1` for the game. |
| `--install-mod [PATH]` | Run an Aslain's installer through umu and exit. Defaults to the newest installer in `~/Downloads`. |
| `--wcg` | Run Wargaming Game Center through umu and exit. |
| `[game arguments]` | Arguments after `--` are passed to World of Tanks. |

The UMU prefix defaults to `~/Games/WoT/prefix`; set `WOT_PREFIX` to use a
different prefix. `WOT_PREFERENCES` overrides the settings file path.

## Updating the Proton runner and DXVK

The launcher currently pins `PROTONPATH` to the GE-Proton folder named in
`wot-launcher.sh`. Installing a newer runner will not change that default.
To have UMU download and use the latest GE-Proton build, set its `GE-Proton`
codename:

```bash
PROTONPATH=GE-Proton wot-launcher.sh
```

This override applies to that launch only and does not require ProtonPlus or
another launcher. To always use the latest GE-Proton, change the launcher's
`PROTONPATH` default to `GE-Proton`. To pin a particular build instead, set
`PROTONPATH` to its version name or full directory path. UMU also defaults to
UMU-Proton and manages it automatically if `PROTONPATH` is unset.

DXVK is supplied by the selected Proton runner, so selecting a newer
GE-Proton/Proton runner updates DXVK along with the runner's other components.
UMU also updates the Steam Linux Runtime automatically by default; setting
`UMU_RUNTIME_UPDATE=0` disables those runtime updates.

See the [UMU manual](https://github.com/Open-Wine-Components/umu-launcher/blob/main/docs/umu.1.scd)
for `PROTONPATH` and `UMU_RUNTIME_UPDATE` details, and the
[GE-Proton releases](https://github.com/GloriousEggroll/proton-ge-custom/releases)
for runner versions.

## Updating the modpack

```bash
wot-launcher.sh --install-mod
```

Runs the newest Aslain's installer found in `~/Downloads` through umu, then
exits. It does **not** switch the mouse profile, apply the resolution fix, or
start the game afterwards — it is a separate operation.

Point it elsewhere by passing a path, as either a host or a Windows path:

```bash
wot-launcher.sh --install-mod                                   # newest in ~/Downloads
wot-launcher.sh --install-mod ~/Downloads/SomeOtherInstaller.exe
wot-launcher.sh --install-mod 'Z:\home\sylvain\Downloads\SomeOtherInstaller.exe'
```

Host paths and Windows `Z:`/`C:` paths are accepted.

Open Wargaming Game Center in the UMU prefix with:

```bash
wot-launcher.sh --wcg
```

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
`WOT_PREFERENCES` if the prefix or settings location changes.

## Enabling the gamemode CPU / display profile

`wot-launcher.sh` invokes `gamemoderun umu-run` when `gamemoderun` is
available. Gamemode's `[custom]` hooks switch the CPU profile and display mode.

Your existing `/etc/gamemode.ini` already does this correctly and needs no
changes. The notes below explain why it works, and the one trap to be aware of
if you ever edit it.

### 1. Who requests gamemode, and what the known-games list really affects

The UMU launcher requests gamemode with `gamemoderun`. The `start=` and `end=`
hooks below run as soon as the game registers as a gamemode client. The game
being absent from gamemode's list of *known* games only means gamemode does not
apply its built-in per-game tuning, not that custom hooks are skipped.

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
repo directory does not contain one, so the launcher is unaffected — but
it is a reason to be careful about `cd`-ing somewhere unexpected before
launching.

### 3. Enable the service

Enable the service now and on future boots with:

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
