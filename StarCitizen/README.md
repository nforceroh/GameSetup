# Star Citizen

Two setups are documented here:

- **Linux / Wine** — Star Citizen under the LUG runner in the prefix
  `$HOME/Games/star-citizen` (not part of this repo), installed with the
  [LUG helper](https://github.com/starcitizen-lug/lug-helper), with joystick
  mapping via [BindSight](https://github.com/w00zla/BindSight/) and VR through
  [WiVRn](https://github.com/WiVRn/WiVRn) on a Pico 4 Enterprise.
- **Windows** — a native install that drives the VKB sticks through
  [VJoy](https://virtualjoystick.sourceforge.net/) +
  [JoystickGremlinEx](https://github.com/muchimi/JoystickGremlinEx/).

## Linux / Wine + BindSight

The Wine prefix is `$HOME/Games/star-citizen` (not part of this repo). The game
folders BindSight points at are
`$HOME/Games/star-citizen/drive_c/Program Files/Roberts Space Industries/StarCitizen/{LIVE,PTU,HOTFIX,EPTU}`.

Joystick mapping is done with
[BindSight](https://github.com/w00zla/BindSight/) (v0.17.0), a Star Citizen
input-binding visualizer/mapper. It ships as a `deb`/`rpm`/`AppImage` and
installs the binary as `/usr/bin/bindsight`.

### Joystick detection needs a udev rule for `/dev/hidraw*` (not `sudo`, not the `input` group)

BindSight reads joysticks through **SDL2** (joystick + GameController APIs) and
**hidapi**, which on Linux open the kernel device nodes `/dev/hidraw*` (HID raw)
and `/dev/input/event*` (evdev). Wine uses the `hidraw` nodes as well, so the
same permission problem affects the game itself.

On this machine (Fedora 44) the two kinds of node have **different**
permissions:

| Node | Owner / mode | Reachable by the `input` group? |
|------|--------------|---------------------------------|
| `/dev/input/event*` | `root:input` `0660` | yes |
| `/dev/hidraw6`, `/dev/hidraw9` (the VKB sticks) | `root:root` `0600`, no ACL | **no** |

The user is already in the `input` group (`id -nG` → `sylvain wheel input
gamemode`), and no udev rule matches vendor `231d`, so the open on the `hidraw`
nodes fails with `EACCES` (os error 13) and the sticks are invisible. Running
`sudo bindsight` bypasses the check, which is why it "works" under `sudo` — but
it is a permissions issue, not a BindSight bug. **Adding the user to `input`
does not fix it.**

The symptom in the BindSight log (run as the normal user) is:

```text
[WARN][bindsight_lib::wineorder::linux] Wine cannot open /dev/hidraw9 (231d:0201): Permission denied (os error 13) — the game will not see this device
[WARN][bindsight_lib::wineorder::linux] Wine cannot open /dev/hidraw6 (231d:0200): Permission denied (os error 13) — the game will not see this device
```

`231d:0200` is the VKB Gladiator NXT R and `231d:0201` the VKB Gladiator NXT L.

#### Fix

Install a udev rule that gives the logged-in user access to the `hidraw` nodes
of the joystick vendors. The simplest way is the LUG helper, which ships exactly
this rule:

```bash
lug-helper
```

Then choose **Maintenance and Troubleshooting → Create joystick hidraw rules**.
It writes `/etc/udev/rules.d/40-starcitizen-joystick-uaccess.rules` (path and
content taken from `/usr/bin/lug-helper`, v4.17):

```text
# Set the uaccess tag for raw HID access for VKB/Virpil/Thrustmaster devices in Wine
KERNEL=="hidraw*", ATTRS{idVendor}=="231d|3344|044f", ATTRS{idProduct}=="*", MODE="0660", TAG+="uaccess"
```

The vendor IDs are VKB (`231d`), Virpil (`3344`) and Thrustmaster (`044f`).
`TAG+="uaccess"` makes systemd-logind add an ACL for the active seat's user, so
no group change is needed.

Manual equivalent (the rule above passes `udevadm verify`):

```bash
sudo tee /etc/udev/rules.d/40-starcitizen-joystick-uaccess.rules >/dev/null <<'EOF'
# Set the uaccess tag for raw HID access for VKB/Virpil/Thrustmaster devices in Wine
KERNEL=="hidraw*", ATTRS{idVendor}=="231d|3344|044f", ATTRS{idProduct}=="*", MODE="0660", TAG+="uaccess"
EOF
sudo udevadm control --reload
sudo udevadm trigger --subsystem-match=hidraw --action=add
```

If the ACL does not appear, **unplug and replug** the sticks (this is what the
LUG helper tells you to do).

#### Verify

```bash
ls -l /dev/hidraw*
getfacl /dev/hidraw6 /dev/hidraw9
```

Each VKB node should show a `user:sylvain:rw-` ACL entry (a trailing `+` in the
`ls -l` mode string). Then run `bindsight` **without** `sudo` — the
`Permission denied` warnings should be gone and both sticks detected.

> The rule was **not** applied when this README was written: the rule file did
> not exist and `hidraw6`/`hidraw9` were still `root:root` `0600`. The
> post-fix behaviour above is the documented effect of the rule, not something
> observed here.

### Joystick slot order comes from `Game.log`

BindSight resolves which `js1`/`js2` slot the game assigns each stick from the
game's own `Game.log` (it does not use a live enumeration for ordering). If the
log has no joystick lines, BindSight logs:

```text
[WARN][bindsight_lib] Game.log joystick order: .../LIVE/Game.log: no joystick lines
[ERROR][bindsight_lib] no joystick order: no usable game log (...); joystick input cannot be resolved
```

This happens when the game has not been launched with the sticks connected
since the last log write. Launching Star Citizen with both sticks plugged in
populates the log and the slot-ordering / device-order-fix feature works. This
does **not** block device *detection* — that is purely the `hidraw` udev rule
fix above.

## Linux / Wine: VR (WiVRn + Pico 4 Enterprise)

Star Citizen has **experimental OpenXR VR under Wine**. The LUG wiki's guidance
is to use **Monado** for PCVR/wired headsets (Vive, Index) and **WiVRn** for
standalone headsets
([Head-Tracking → VR](https://wiki.starcitizen-lug.org/Head-Tracking)).
The Pico 4 Enterprise is a standalone Android headset, so it uses WiVRn, which
streams the PC's OpenXR output to it over the network (or USB).

This is working on this machine. `Game.log` of the `LIVE` install records the
game picking up the headset through WiVRn:

```text
<2026-10-22T12:52:20.854Z> [OpenXR] Using PICO 4 Enterprise HMD on WiVRn (Runtime: WiVRn 'v26.9' - 26.9.0)
<2026-10-22T12:52:28.929Z> [OpenXR] VR: DISABLED -> ENABLED
```

### What is installed (verified on this machine)

| Component | Version / value |
|-----------|-----------------|
| PC server | `wivrn` + `wivrn-dashboard` `26.9-2.fc44` (Fedora repo) |
| Headset client | `org.meumeu.wivrn.github` `26.9` (queried over `adb`) |
| OpenXR/OpenVR helpers | `monado` `25.1.0^20261022gitf5da489`, `xrizer` `0.6^20261011git5ae098b` |
| Star Citizen installer | `lug-helper` `4.17-1.fc44` (Fedora Copr `jackgreiner`) |
| Wine runner (in `sc-launch.sh`) | `lug-wine-tkg-git-11.18-1` (`Game.log`: `WINE: 11.18`) |
| GPU | AMD Radeon RX 7900 XTX (RADV); `Game.log` shows the **Vulkan** renderer |

The WiVRn docs require the **headset client and PC server to be the same
version** — both are `26.9` here, so re-check this after any WiVRn update.

### Star Citizen is installed with the LUG helper

Install it as in the [LUG Quick-Start Guide](https://wiki.starcitizen-lug.org/Quick-Start-Guide):
run `lug-helper`, then **Preflight Check** (kernel `vm.max_map_count` and
open-file limits), then **Install Star Citizen Launcher**. The helper keeps its
state in `~/.config/starcitizen-lug/` and generates, in the prefix
`~/Games/star-citizen`:

- `sc-launch.sh` — launch script (v2.5). It sets `WINEPREFIX`, uses the runner
  `runners/lug-wine-tkg-git-11.18-1` (`11.20-1` is also present but unused)
  and starts `RSI Launcher.exe`.
- `rsi launcher.exe.desktop` — copied to `~/.local/share/applications/`, with
  `Exec="/home/sylvain/Games/star-citizen/sc-launch.sh"` and
  `Categories=Game;X-WiVRn-VR;`.

The `X-WiVRn-VR` category is what makes WiVRn list **RSI Launcher** in the
headset's app launcher (WiVRn scans `~/.local/share/applications` and
`/usr/share/applications` for it). The VR settings below are applied in that
generated prefix; the wiki requires a LUG Wine **11.1 or newer**.

### PC side: WiVRn server

1. Install: `sudo dnf install wivrn wivrn-dashboard`.
2. **Avahi** must be running so the headset can discover the PC:
   `systemctl enable --now avahi-daemon` (already `active` and `enabled` here).
3. Start the server with the **WiVRn Dashboard** (`wivrn-dashboard`), or as a
   user service:

   ```bash
   systemctl --user enable --now wivrn
   ```

   The unit (`/usr/lib/systemd/user/wivrn.service`) runs `/usr/bin/wivrn-server`.
   It is currently **disabled and inactive** here, so the server is started
   on demand (dashboard).
4. While a headset is connected, `wivrn-server` points the OpenXR and OpenVR
   configuration at WiVRn and reverts it once the connection ends and all
   running VR applications are closed — so a VR application can only start
   **after** the headset connection is established. A virtual speaker (and a
   microphone, if enabled in the headset app settings) is created; set them as
   the default output/input devices to hear the game in the headset. The setting
   persists across sessions.

Server settings live in `~/.config/wivrn/config.json` (search order:
`/usr/share/wivrn/`, `/etc/wivrn/`, `~/.config/wivrn/`):

```json
{
  "debug-gui": false,
  "hid-forwarding": false,
  "lh-stick-deadzone": 0.0,
  "openvr-compat-path": "/usr/lib64/xrizer/runtime",
  "use-steamvr-lh": false
}
```

`openvr-compat-path` points at **xrizer** (an OpenVR-on-OpenXR layer) for
OpenVR titles; Star Citizen itself uses OpenXR. Pairing data
(`~/.config/wivrn/cookie`, `known_keys.json`) is a secret — do not commit it.

#### Network and firewall

WiVRn needs **UDP 5353** (Avahi/mDNS discovery) and **9757 UDP + TCP** (the
stream). The active firewalld zone here is `FedoraWorkstation` (interface
`eno1`) with services `dhcpv6-client samba-client ssh` and ports
`1025-65535/udp` and `1025-65535/tcp` open:

- `9757` is covered by that port range.
- `5353/udp` is **not** (it is below `1025`, and the `mdns` service is not
  enabled in the zone). If the headset does not find the PC over Wi-Fi, open it:

  ```bash
  sudo firewall-cmd --zone=FedoraWorkstation --add-service=mdns --permanent
  sudo firewall-cmd --reload
  ```

  This is untested here (see *Gaps*); the USB route below avoids discovery.

### Headset side: Pico 4 Enterprise

- The headset enumerates over USB as `2d40:00b7 Pico PICO 4 Enterprise`.
  With USB debugging enabled and authorised on the headset, `adb devices`
  lists it as `device`.
- Pico is not a Meta headset, so the dashboard's first-run wizard leads you to
  **download the correct APK** instead of the Meta Store. An app installed via
  the dashboard or manually via `adb` appears in an **unknown sources** section
  on the headset. The installed package here is `org.meumeu.wivrn.github` (the
  GitHub-release build).
- **Wi-Fi**: start the WiVRn app on the headset. It opens on a server list; the
  PC should be listed with a **connect** button. On first start it asks for the
  optional permissions (microphone, hand tracking, eye tracking, …); the docs
  recommend keeping the default settings.
- **Wired (USB)**: with the server already running and the headset's Wi-Fi
  switched off:

  ```bash
  adb reverse tcp:9757 tcp:9757
  adb shell am start -a android.intent.action.VIEW -d "wivrn+tcp://localhost" org.meumeu.wivrn.github
  ```

  (`org.meumeu.wivrn` is the package name for the store build; this machine
  has the `.github` build.) The dashboard has an `auto_connect_usb` option,
  currently `false` in `~/.config/wivrn/wivrn-dashboard.conf`.

### Launching Star Citizen in VR

Procedure from the LUG wiki:

1. Use a LUG Wine **11.1 or newer** (the runner here is 11.18).
2. Set the game to the **Vulkan** renderer.
3. Start the RSI Launcher and turn on **Settings → {LIVE,PTU} → VR Support**.
4. Connect the headset and make sure the WiVRn session is **active before**
   launching the game.
5. Launch Star Citizen; the game connects to the headset automatically.
6. Turn on **VR** in the in-game settings.

To start it from the headset, pick **RSI Launcher** in WiVRn's launcher (see the
`X-WiVRn-VR` category above). WiVRn can also auto-start an application when the
headset connects (`application` key in `config.json`, or the dashboard) — not
configured here.

#### Tuning and debugging (from the LUG wiki)

Edit the launch script (lug-helper → **Edit launch script**, i.e.
`~/Games/star-citizen/sc-launch.sh`):

- **Cross-eyed view on canted displays**: `export OXR_PARALLEL_VIEWS=1`.
- **OpenXR logging in `Game.log`**: change `WINEDEBUG=-all` to
  `export WINEDEBUG=-all,+openxr`.
- **Headset not found automatically**: add
  `export XR_RUNTIME_JSON=/path/to/openxr/1/active_runtime.json`. The manifest
  the `wivrn` package installs is `/usr/share/openxr/1/openxr_wivrn.json`; its
  `library_path` is relative (`../../../lib64/wivrn/libopenxr_wivrn.so`), so
  reference it in place instead of copying it elsewhere.

To disable the curved menus in VR, add this to a `USER.cfg` in the `LIVE`
folder (none exists on this machine):

```text
r_StereoTheaterModeCanUseCylinder = 0
```

#### State of `sc-launch.sh` on this machine

The script diverges from the lug-helper template by one block, which is
**commented out** (no effect):

```bash
# WiVRn & OpenXR Projection Overrides
#export OXR_PARALLEL_VIEWS=1
#export PRESSURE_VESSEL_VR_RUNTIME=1
#export XR_RUNTIME_JSON="/home/sylvain/.config/openxr/1/wivrn_static.json"
#export PRESSURE_VESSEL_IMPORT_OPENXR_1_RUNTIMES=1
```

- `~/.config/openxr/1/wivrn_static.json` **does not exist**, so that
  `XR_RUNTIME_JSON` line would point at nothing if enabled.
- The `PRESSURE_VESSEL_*` variables are for the Steam Runtime container
  (pressure-vessel), which the lug-helper launch script does not use — it calls
  the Wine runner directly. Their effect on this setup is unverified.
  (`DCS/README.md` documents them for its umu/Steam Runtime setup.)
- `~/.config/openxr/1/active_runtime.json` is a symlink to
  `/usr/share/openxr/1/openxr_monado.json` (Monado). VR still works with it
  (`Game.log` above), consistent with the WiVRn docs: the server switches the
  OpenXR configuration to WiVRn while the headset is connected.
- The script also exports Nvidia shader-cache variables (`__GL_*`) next to the
  Mesa ones. They are the lug-helper template's defaults; the GPU here is AMD.

### Gaps / unverified

- **Pico 4 Enterprise** is not listed separately in the WiVRn docs (only
  *Pico 4*). It works here per `Game.log`, but it is not an officially listed
  headset.
- Whether the missing `5353/udp` / `mdns` rule actually breaks Wi-Fi discovery
  on this machine was not tested; the `Game.log` session may have been over USB.
- How the 2026-10-22 session was started (headset launcher, dashboard or
  PC-side) is not recorded; `Game.log` shows VR toggled on and off several
  times in that session, and session quality was not assessed.
- Whether the Vulkan renderer is selected through the launcher or in-game is
  not recorded (no `USER.cfg`); `Game.log` shows Vulkan in use.
- Whether `OXR_PARALLEL_VIEWS=1` is needed for the Pico 4 Enterprise's
  displays was not tested.
- WiVRn client/server versions must stay matched after updates.

## Windows: VJoy + JoystickGremlinEx

The Windows install of Star Citizen drives the VKB sticks through
[JoystickGremlinEx](https://github.com/muchimi/JoystickGremlinEx/) — a 64-bit
fork of [Joystick Gremlin](https://github.com/JoystickGremlin/JoystickGremlin)
— which remaps the physical sticks onto
[VJoy](https://virtualjoystick.sourceforge.net/) virtual joysticks that the game
reads. The mapping is stored in the profile file
[`sc46gexwithmm_op.82.xml`](sc46gexwithmm_op.82.xml) in this folder.

### Profile overview

`sc46gexwithmm_op.82.xml` is a JoystickGremlinEx profile
(`<profile version="16">`, `start_mode="MM_SCM"`, `default_mode="Default"`,
`force_numlock="True"`). It maps the two physical VKB sticks onto two VJoy
devices and switches behavior per flight mode.

**Input devices** (matched by `device-guid`):

| Device | GUID | Type |
| --- | --- | --- |
| VKBsim Gladiator NXT R | `6c422e005ce711ec8001444553540000` | joystick |
| VKBsim Gladiator NXT L | `6c422e005ce711ec8002444553540000` | joystick |
| Mode Control | `b3b159a04d064bd693f97583ec08b877` | mode |

**VJoy targets:** the profile writes to two virtual joysticks — `vjoy="1"`
(78 remaps) and `vjoy="2"` (63 remaps). The 141 `<vjoyremap>` actions break
down as 127 `VJoyButton`, 10 `VJoyAxis`, and 4 `VJoyHat`.

**Modes:** `Default`, `MM_SCM`, `MM_NAV` (inherits `MM_SCM`),
`MM_NAV_Quantum` (inherits `MM_NAV`), `MM_NAV_Flight` (inherits `MM_NAV`),
`OM_Aux`, `OM_Scan`, `Modifier`, `MM_SCM_Guns`, `MM_SCM_Flight`, and
`MM_SCM_Missiles` (the latter inherit `MM_SCM`). Child modes inherit their
parent's mappings and add overrides.

**Mode Control device:** a `type="mode"` device whose `modecontrol` blocks run
"Mode Enter Actions" / "Mode Exit Actions" when a mode is entered/exited. These
play a per-mode sound (e.g. `C:/Users/Sylvain/Joystick Gremlin Ex/Audio
Files/Computer/SCM_Mode.wav`) and toggle two boolean states, `is_scm_mode` and
`is_nav_mode`, which other mappings key off via `map_to_state`.

**Other elements:** a `<macro>` (with a `<key scan-code="62">` press/release
and a `<pause>`) and `<filter>`/`<deadzone>`/`<mapping>` (curve) entries for
axis shaping.

### Notes

- The audio file paths are absolute Windows paths under
  `C:/Users/Sylvain/Joystick Gremlin Ex/Audio Files/`; they must exist on the
  Windows machine for the mode-enter sounds to play.
- `<removed-devices>` lists five device GUIDs that are explicitly excluded from
  the profile.
- This profile is independent of BindSight: BindSight edits the game's own
  `actionmaps.xml` bindings, while JoystickGremlinEx sits between the physical
  sticks and the game via VJoy.