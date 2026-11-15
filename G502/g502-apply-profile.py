#!/usr/bin/env python3
"""Apply a named profile from g502-profiles.json to the G502 via ratbagctl.

Usage:
    g502-apply-profile.py [NAME]          # default: desktop
    g502-apply-profile.py --list
    g502-apply-profile.py --file PATH NAME
"""

import json
import os
import subprocess
import sys
import time

DEFAULT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "g502-profiles.json")
MOUSE_RETRIES = int(os.environ.get("MOUSE_RETRIES", "60"))


def die(msg):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def find_device(match):
    """Return the ratbagctl nickname for the first device matching `match`."""
    out = subprocess.run(["ratbagctl", "list"], capture_output=True, text=True)
    for line in out.stdout.splitlines():
        if match in line:
            return line.split(":", 1)[0].strip()
    return None


def ratbagctl(device, *args, check=True):
    cmd = ["ratbagctl", device, *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        die(f"'{' '.join(cmd)}' failed:\n{result.stderr.strip()}")
    return result


def apply_resolution(device, profile, index, res):
    dpi = res["dpi"]
    ratbagctl(device, "profile", str(profile), "resolution", str(index),
              "dpi", "set", str(dpi))
    if res.get("disabled"):
        ratbagctl(device, "profile", str(profile), "resolution", str(index),
                  "disabled", "set")
    else:
        ratbagctl(device, "profile", str(profile), "resolution", str(index),
                  "enabled", "set")
    if res.get("default"):
        ratbagctl(device, "profile", str(profile), "resolution", "default",
                  "set", str(index))
    if res.get("active"):
        ratbagctl(device, "profile", str(profile), "resolution", "active",
                  "set", str(index))


def apply_button(device, profile, index, action):
    if action == "none":
        ratbagctl(device, "profile", str(profile), "button", str(index),
                  "action", "set", "disabled")
        return
    parts = action.split()
    if parts[0] in ("button", "special", "macro", "key"):
        ratbagctl(device, "profile", str(profile), "button", str(index),
                  "action", "set", *parts)
    else:
        die(f"button {index}: unknown action '{action}' "
            "(expected 'button B', 'special S', 'macro ...', 'key K' or 'none')")


def apply_led(device, profile, led):
    index = str(led["index"])
    if "mode" in led:
        ratbagctl(device, "profile", str(profile), "led", index, "set",
                  "mode", led["mode"])
    if "color" in led:
        ratbagctl(device, "profile", str(profile), "led", index, "set",
                  "color", led["color"])
    if "duration" in led:
        ratbagctl(device, "profile", str(profile), "led", index, "set",
                  "duration", str(led["duration"]))
    if "brightness" in led:
        ratbagctl(device, "profile", str(profile), "led", index, "set",
                  "brightness", str(led["brightness"]))


def apply_profile(device, name, cfg):
    profile = cfg["ratbag_profile"]

    if "rate" in cfg:
        ratbagctl(device, "profile", str(profile), "rate", "set", str(cfg["rate"]))

    for index, res in enumerate(cfg.get("resolutions", [])):
        apply_resolution(device, profile, index, res)

    for index, action in cfg.get("buttons", {}).items():
        apply_button(device, profile, int(index), action)

    for led in cfg.get("leds", []):
        apply_led(device, profile, led)

    ratbagctl(device, "profile", "active", "set", str(profile))


def main():
    args = sys.argv[1:]
    path = DEFAULT_FILE
    name = "desktop"

    while args:
        if args[0] in ("-h", "--help"):
            print(__doc__.strip())
            return 0
        if args[0] == "--list":
            with open(path) as fh:
                profiles = json.load(fh)["profiles"]
            print("\n".join(sorted(profiles)))
            return 0
        if args[0] == "--file":
            if len(args) < 2:
                die("--file needs a path")
            path = args[1]
            args = args[2:]
        else:
            name = args[0]
            args = args[1:]

    try:
        with open(path) as fh:
            data = json.load(fh)
    except FileNotFoundError:
        die(f"profile file not found: {path}")
    except json.JSONDecodeError as exc:
        die(f"{path} is not valid JSON: {exc}")

    profiles = data.get("profiles", {})
    if name not in profiles:
        die(f"unknown profile '{name}'. Available: {', '.join(sorted(profiles))}")

    match = data.get("device", "G502")
    device = None
    for _ in range(MOUSE_RETRIES):
        device = find_device(match)
        if device:
            break
        time.sleep(1)
    if not device:
        die(f"no device matching '{match}' found after {MOUSE_RETRIES} attempts")

    apply_profile(device, name, profiles[name])
    print(f"Applied profile '{name}' to {device}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
