# Proton-GE

These notes cover installing and updating GE-Proton for the UMU-based game
setups in this repository, and enabling the host's NTSync driver.

## Using the latest GE-Proton with UMU

Set `PROTONPATH=GE-Proton` to have UMU download and use the latest GE-Proton
automatically. This is the default in
[`../WoT/wot-launcher.sh`](../WoT/wot-launcher.sh), so no manual runner update
is needed when a new release comes out. See the
[UMU manual](https://github.com/Open-Wine-Components/umu-launcher/blob/main/docs/umu.1.scd)
for `PROTONPATH` details.

The local [`updateproton.sh`](updateproton.sh) helper installs a runner into
`~/.local/share/Steam/compatibilitytools.d` for cases where you want to manage
a specific local build. From the repository root, run it with Bash:

```bash
bash Proton-GE/updateproton.sh
```

It downloads the latest release, verifies its checksum, and skips installation
if that release is already present. The script does not change the WoT
launcher's `PROTONPATH`. To run a particular local build, set `PROTONPATH` to
its full path; see the [WoT runner notes](../WoT/README.md#updating-the-proton-runner-and-dxvk).

## Enabling NTSync

```bash
sudo modprobe ntsync
echo ntsync | sudo tee /etc/modules-load.d/ntsync.conf
```

Reboot, then verify that the device exists:

```bash
ls -l /dev/ntsync
```
