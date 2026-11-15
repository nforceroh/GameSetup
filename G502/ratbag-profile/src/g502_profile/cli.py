"""Command-line entry point for G502 profile management."""

import argparse
import asyncio
import sys

from dbus_fast import BusType
from dbus_fast.aio import MessageBus
from dbus_fast.errors import DBusFastError

from .ratbag import RatbagClient


async def run(args: argparse.Namespace) -> None:
    bus = await asyncio.wait_for(MessageBus(bus_type=BusType.SYSTEM).connect(), timeout=5)
    try:
        client = RatbagClient(bus)
        device = await client.find_device()
        if args.command == "list":
            print(f"{device.name} ({device.path})")
            for profile in await client.profiles(device):
                status = " (active)" if profile.active else " (disabled)" if profile.disabled else ""
                print(f"  profile {profile.index}{status}")
        elif await client.switch(device, args.index):
            print(f"Profile {args.index} selected; hardware commit queued by ratbagd.")
            print("Commit is asynchronous; the hardware write is not confirmed.")
        else:
            print(f"Profile {args.index} is already active; no changes made.")
    finally:
        bus.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage G502 hardware profiles via ratbagd.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list hardware profiles")
    switch = commands.add_parser("switch", help="activate a hardware profile")
    switch.add_argument("index", type=int, help="profile index")
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except (RuntimeError, OSError, DBusFastError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
