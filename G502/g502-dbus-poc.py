#!/usr/bin/env python3
"""List or switch G502 hardware profiles through ratbagd's system D-Bus API."""

import argparse
import sys

try:
    from gi.repository import Gio, GLib
except ModuleNotFoundError as exc:
    if exc.name != "gi":
        raise
    sys.exit("Error: PyGObject is required (install your distribution's python3-gi package).")


SERVICE = "org.freedesktop.ratbag1"
ROOT = "/org/freedesktop/ratbag1"


def get_property(bus, path, interface, name):
    reply = bus.call_sync(
        SERVICE, path, "org.freedesktop.DBus.Properties", "Get",
        GLib.Variant("(ss)", (f"{SERVICE}.{interface}", name)),
        None, Gio.DBusCallFlags.NONE, 5000, None,
    )
    return reply.unpack()[0]


def call_method(bus, path, interface, method):
    reply = bus.call_sync(
        SERVICE, path, f"{SERVICE}.{interface}", method,
        None, None, Gio.DBusCallFlags.NONE, 5000, None,
    )
    result = reply.unpack()[0]
    if result != 0:
        raise RuntimeError(f"{interface}.{method} returned error {result}")


def find_device(bus):
    version = get_property(bus, ROOT, "Manager", "APIVersion")
    if version != 2:
        raise RuntimeError(f"unsupported ratbagd API version {version} (expected 2)")
    devices = get_property(bus, ROOT, "Manager", "Devices")
    matches = [
        path for path in devices
        if "G502" in get_property(bus, path, "Device", "Name")
    ]
    if not matches:
        raise RuntimeError("no G502 found")
    if len(matches) > 1:
        raise RuntimeError("multiple G502 devices found; cannot choose safely")
    return matches[0]


def get_profiles(bus, device):
    paths = get_property(bus, device, "Device", "Profiles")
    return [
        (get_property(bus, path, "Profile", "Index"), path,
         get_property(bus, path, "Profile", "IsActive"))
        for path in paths
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", nargs="?", type=int,
                        help="profile index to activate; omit to list profiles")
    args = parser.parse_args()

    try:
        bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        device = find_device(bus)
        profiles = get_profiles(bus, device)
        if args.profile is None:
            print(f"{get_property(bus, device, 'Device', 'Name')} ({device})")
            for index, _, active in profiles:
                print(f"  profile {index}{' (active)' if active else ''}")
            return 0

        selected = next((p for p in profiles if p[0] == args.profile), None)
        if selected is None:
            raise RuntimeError(f"profile {args.profile} not found")
        if selected[2]:
            print(f"Profile {args.profile} is already active; no changes made.")
            return 0

        call_method(bus, selected[1], "Profile", "SetActive")
        if not get_property(bus, selected[1], "Profile", "IsActive"):
            raise RuntimeError(f"ratbagd did not activate profile {args.profile}")
        call_method(bus, device, "Device", "Commit")
        print(f"Profile {args.profile} selected; hardware commit queued by ratbagd.")
        print("Commit is asynchronous; this does not confirm the hardware write succeeded.")
        return 0
    except (GLib.Error, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
