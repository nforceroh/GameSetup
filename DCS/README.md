# DCS World

DCS World is installed and launched through [UMU](https://github.com/Open-Wine-Components/umu-launcher)
with a GE-Proton compatibility tool, the same way as [`../WoT`](../WoT). There is
no Steam install and no desktop launcher script in this repo (yet) — the notes
below are the commands, run by hand, that get DCS and its common add-ons
working.

This machine's prefix is `$HOME/Games/dcs` (≈259 GB; not part of this repo).
DCS itself lives at
`$WINEPREFIX/drive_c/Program Files/Eagle Dynamics/DCS World/`, with
`bin/DCS.exe` (single-thread), `bin-mt/DCS.exe` (multithread), and
`bin/DCS_updater.exe`.

## Quoting `WINEPREFIX`

Use `$HOME/Games/dcs`, not a quoted `"~/Games/dcs"` — `~` is only expanded by
the shell when it is unquoted and at the start of a word, so
`WINEPREFIX="~/Games/dcs"` passes the literal string `~/Games/dcs` through to
`umu-run`, not your home directory. Either `WINEPREFIX=$HOME/Games/dcs` or
`WINEPREFIX="$HOME/Games/dcs"` expands correctly.

## Installing / updating DCS

Download `DCS_World_web.exe` from the
[official downloads page](https://www.digitalcombatsimulator.com/en/downloads/world/)
into `$HOME/Downloads`, then run it through umu to install into the prefix:

```bash
WINEPREFIX=$HOME/Games/dcs GAMEID=223750 PROTONPATH=GE-Proton \
  umu-run "$HOME/Downloads/DCS_World_web.exe"
```

Re-run the bundled updater the same way whenever DCS needs patching:

```bash
WINEPREFIX=$HOME/Games/dcs GAMEID=223750 PROTONPATH=GE-Proton \
  umu-run "$WINEPREFIX/drive_c/Program Files/Eagle Dynamics/DCS World/bin/DCS_updater.exe"
```

`223750` is DCS World's Steam app ID, confirmed on its
[Steam store page](https://store.steampowered.com/app/223750/DCS_World/).
`GAMEID` only has to be *a* value — arbitrary or a umu-database entry — it is
not required to be exact; per the [umu manual](https://github.com/Open-Wine-Components/umu-launcher/blob/main/docs/umu.1.scd),
an unset or unmatched `GAMEID` just skips automatic protonfixes and (if
`WINEPREFIX` is unset) changes the default prefix location. The
[umu-database](https://github.com/Open-Wine-Components/umu-database) lists this
standalone (non-Steam) installer as `DCS World,none,none,umu-223750,dcs,standalone ED version`,
but there is currently no `umu-223750.py`/`223750.py` game-specific fix in
[umu-protonfixes](https://github.com/Open-Wine-Components/umu-protonfixes), so
the exact `GAMEID` string makes no behavioral difference today either way.
`PROTONPATH=GE-Proton` tells umu to fetch and use the latest
[GE-Proton](https://github.com/GloriousEggroll/proton-ge-custom/releases)
build automatically (umu manual, example 10); this prefix's metadata records
`GE-Proton11-11`, the latest build as of this writing. Pin a specific build
instead by setting `PROTONPATH` to its version name or full path, same as in
[`../WoT/README.md`](../WoT/README.md#updating-the-proton-runner-and-dxvk).

`winetricks.log` in this prefix records `d3dx11_43`, `d3dcompiler_43`, and
`d3dcompiler_47` as already installed — real [winetricks](https://github.com/Winetricks/winetricks)
verbs for D3D11/HLSL compiler DLLs commonly needed by DX11 titles. They are
noted here as this prefix's observed state, not as a prescribed step.

## VR / OpenXR (Monado)

These steps come from a
[DCS-on-Linux VR tutorial](https://www.youtube.com/watch?v=jENf9XTqbwY) and are
labeled as such below; only the registry key and the Steam Runtime
(`PRESSURE_VESSEL_*`) environment variables were independently verified
against upstream source/docs.

Proton's `vrclient`/`wineopenxr` wait on a DWORD value named `state` under
`HKEY_CURRENT_USER\Software\Wine\VR` before creating an OpenXR instance —
confirmed in
[`wineopenxr/openxr_loader.c`](https://github.com/ValveSoftware/Proton/blob/experimental/wineopenxr/openxr_loader.c#L113-L152)
in the Proton source, where it blocks on that value being non-zero. Normally
Steam's `steam.exe` shim sets it once SteamVR is ready; outside Steam, the
tutorial sets it manually with `umu-run regedit`, creating
`HKEY_CURRENT_USER\Software\Wine\VR` with a DWORD `State` = `1`.

For running against a standalone Monado OpenXR runtime (as opposed to
SteamVR), the tutorial's launch command was:

```bash
WINEDEBUG=-all,+openxr \
PRESSURE_VESSEL_IMPORT_OPENXR_1_RUNTIMES=1 \
PRESSURE_VESSEL_FILESYSTEMS_RW=/run/user/1000/monado_comp_ipc \
WINEPREFIX=$HOME/Games/dcs GAMEID=223750 PROTONPATH=GE-Proton \
  umu-run rundll32 wineopenxr.dll,wineopenxr_init_registry
```

Both `PRESSURE_VESSEL_IMPORT_OPENXR_1_RUNTIMES` and
`PRESSURE_VESSEL_FILESYSTEMS_RW` are real Steam Linux Runtime
(pressure-vessel) container options — see the
[`pressure-vessel wrap(1)` man page](https://gitlab.steamos.cloud/steamrt/steam-runtime-tools/-/raw/main/pressure-vessel/wrap.1.md):
the former is equivalent to `--import-openxr-1-runtimes` (auto-detect an
OpenXR 1 runtime advertised on the host), and the latter bind-mounts a path
read/write inside the container — here, Monado's IPC socket. The
`monado_comp_ipc` socket name itself is hard-coded in pressure-vessel's own
[`wrap-openxr.c`](https://gitlab.steamos.cloud/steamrt/steam-runtime-tools/-/raw/main/pressure-vessel/wrap-openxr.c)
(citing Monado's own socket-naming source), confirming this is the correct
socket path to expose, not a tutorial invention. Adjust `/run/user/1000` to
your own UID if different (`echo $UID`).

**Correction to the tutorial's command:** the screenshot's
`rundll32 wineprefix.dll,openxr_init_registry` does not match any real DLL or
export; Proton's actual module/export, confirmed by grepping
[`ValveSoftware/Proton`](https://github.com/ValveSoftware/Proton) sources
(`wineopenxr/wineopenxr.spec`, `wineopenxr/openxr_loader.c`), is
`wineopenxr.dll` exporting `wineopenxr_init_registry` — used above instead.
Note also that some GE-Proton builds write their own VR state into
`HKCU\Software\Wine\XR` rather than `...\Wine\VR`; this is unverified against
the GE-Proton source for the build pinned here and is mentioned only in case
the manual `Wine\VR` key does not appear to take effect.

## .NET runtime (for SRS)

[DCS-SimpleRadioStandalone](https://github.com/ciribob/DCS-SimpleRadioStandalone)
needs a Windows .NET runtime installed in the prefix. **The version required
depends on the SRS release, and has changed since the tutorial was recorded:**

- SRS [2.3.4.0](https://github.com/ciribob/DCS-SimpleRadioStandalone/releases/tag/2.3.4.0)
  (the version in the tutorial/screenshot) shipped "Fix for Linux (!!!)
  confirmed working under wine with .NET desktop 9 (and .net 9)" — i.e. .NET 9.
- The current latest, [2.4.1.0](https://github.com/ciribob/DCS-SimpleRadioStandalone/releases/tag/2.4.1.0),
  upgraded to .NET 10 and links directly to the
  [.NET 10 Desktop Runtime x64 installer](https://dotnet.microsoft.com/en-us/download/dotnet/thank-you/runtime-desktop-10.0.3-windows-x64-installer)
  in its release notes.

Install whichever **Desktop Runtime** (not the full SDK) matches the SRS
build you actually install, from the
[official .NET downloads page](https://dotnet.microsoft.com/en-us/download/dotnet)
(the tutorial's SDK 9.0.310 installer is one option among several and is
heavier than necessary; current SDK listed there is 9.0.320). Run the
installer through umu the same way as DCS, keeping Monado's socket writable if
you need OpenXR to keep working afterwards:

```bash
PRESSURE_VESSEL_FILESYSTEMS_RW=/run/user/1000/monado_comp_ipc \
WINEPREFIX=$HOME/Games/dcs GAMEID=223750 PROTONPATH=GE-Proton \
  umu-run "$HOME/Downloads/windowsdesktop-runtime-<version>-win-x64.exe"
```

## SRS (Simple Radio Standalone)

Get the current release from the
[SRS releases page](https://github.com/ciribob/DCS-SimpleRadioStandalone/releases)
rather than the tutorial's pinned
[2.3.4.0](https://github.com/ciribob/DCS-SimpleRadioStandalone/releases/tag/2.3.4.0) —
2.4.1.0 is current as of this writing and matches the .NET 10 runtime above.
Extract the release zip, then run `Installer.exe` through umu with the same
prefix and environment as DCS:

```bash
PRESSURE_VESSEL_FILESYSTEMS_RW=/run/user/1000/monado_comp_ipc \
WINEPREFIX=$HOME/Games/dcs GAMEID=223750 PROTONPATH=GE-Proton \
  umu-run "$HOME/Downloads/DCS-SimpleRadioStandalone-<version>/Installer.exe"
```

Choose the full install and uncheck the desktop-icon option (there is no
Windows desktop in this setup). Re-run the DCS updater afterwards, since SRS's
installer also drops an export/plugin into the DCS `Scripts` folder that the
updater can overwrite.

## Optional: Apache font fix

Some DCS UI text (and SRS's overlay) renders with missing glyphs under Wine
because `seguisym.ttf` (Segoe UI Symbol) is a licensed Microsoft font not
included by default. If you have a copy, place it at
`$WINEPREFIX/drive_c/windows/Fonts/seguisym.ttf`. This repo does not include
or redistribute the font — Microsoft's fonts are proprietary and not
redistributable; source it from your own licensed Windows install.

## Gaps / unverified

- The exact `State` registry value's case (`State` vs `state`) does not
  matter — Windows registry value names are case-insensitive — but the key
  path (`Software\Wine\VR`) and value type (`REG_DWORD`) do, per the Proton
  source cited above.
- Whether this GE-Proton build (`GE-Proton11-11`) writes VR state to
  `Wine\VR` or `Wine\XR` was not checked against its actual source; treat the
  `Wine\XR` note above as a troubleshooting hint, not a confirmed fact.
- No local DCS launch script or desktop entry exists yet in this repo (unlike
  `WoT/wot-launcher.sh`); the commands above are run ad hoc.
