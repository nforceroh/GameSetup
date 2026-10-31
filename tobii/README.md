# Tobii Eye Tracker 5 on Linux

This guide covers installing and configuring the Tobii Eye Tracker 5 with
[tobii-faithful](https://github.com/SciFi-Bob/tobii-faithful), a Linux runtime
for head tracking and gaze in games that include Tobii's game integration.

## Install

Download the package for your distribution from the
[latest tobii-faithful release](https://github.com/SciFi-Bob/tobii-faithful/releases).
Connect the tracker, then install the downloaded package.

**Fedora**

```bash
sudo dnf install ./tobii-faithful-*.rpm
```

**Arch Linux, CachyOS, or Garuda**

```bash
sudo pacman -U ./tobii-faithful-*.pkg.tar.zst
```

The Faithful Tobii tray icon should start with your desktop session. If it does
not appear, launch **Faithful Tobii** from your application menu.

## Configure

1. Right-click the tray icon and choose **Open Faithful Tobii**.
2. Select the screen where the tracker is mounted and calibrate it.
3. Open **View Detected Games** and confirm your game is listed. Only games
   shipped with Tobii's official game integration are detected and supported.
4. If needed, disable individual head-tracking axes for a game. Changes apply
   immediately, including while the game is running.
5. Start the game. The tracker should wake when a supported game connects.
   The tray icon shows whether a client is connected.

You can close the settings window when finished; the tracker should return to
sleep when no client needs it.

## Star Citizen in this repository

See the [Star Citizen setup guide](../StarCitizen/README.md) for this
repository's game setup. tobii-faithful reports testing with Star Citizen under
Wine; confirm Star Citizen appears in **View Detected Games** before expecting
the integration to work.

## Troubleshooting

- **Tray icon is missing:** Start **Faithful Tobii** from the application menu.
- **Game is not listed:** Only games with Tobii's official integration are
  detected. Check the project's documentation and release notes for current
  support details.
- **Tracker does not wake in-game:** Confirm the game is listed and enabled in
  **View Detected Games**, and check the project's documentation for any
  game-specific setup requirements.

For further troubleshooting and current compatibility information, see the
[tobii-faithful repository](https://github.com/SciFi-Bob/tobii-faithful).

## Upgrade

Download the newer package from the
[releases page](https://github.com/SciFi-Bob/tobii-faithful/releases) and
install it over the existing version:

```bash
sudo dnf upgrade ./tobii-faithful-*.rpm
sudo pacman -U ./tobii-faithful-*.pkg.tar.zst
```

Settings and calibration are kept during upgrades. The tracker service and
game adapter restart automatically. To use the updated tray and settings
window, quit and reopen them or log out and back in.
