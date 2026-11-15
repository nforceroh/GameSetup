"""Minimal client for ratbagd's system D-Bus profile API."""

import asyncio
from dataclasses import dataclass

from dbus_fast import Message, MessageType, Variant
from dbus_fast.aio import MessageBus


SERVICE = "org.freedesktop.ratbag1"
ROOT = "/org/freedesktop/ratbag1"
PROPERTIES = "org.freedesktop.DBus.Properties"


@dataclass(frozen=True)
class Profile:
    index: int
    path: str
    active: bool
    disabled: bool


@dataclass(frozen=True)
class Device:
    name: str
    path: str


class RatbagClient:
    """Use an already-connected system bus to manage a single G502."""

    def __init__(self, bus: MessageBus):
        self._bus = bus

    async def _call(self, message: Message) -> Message:
        try:
            reply = await asyncio.wait_for(self._bus.call(message), timeout=5)
        except TimeoutError as exc:
            raise RuntimeError(f"D-Bus call {message.member} timed out") from exc
        if reply.message_type == MessageType.ERROR:
            detail = reply.body[0] if reply.body else reply.error_name
            raise RuntimeError(f"D-Bus call {message.member} failed: {detail}")
        return reply

    async def _property(self, path: str, interface: str, name: str):
        reply = await self._call(Message(
            destination=SERVICE, path=path, interface=PROPERTIES, member="Get",
            signature="ss", body=[f"{SERVICE}.{interface}", name],
        ))
        value = reply.body[0]
        if not isinstance(value, Variant):
            raise RuntimeError(f"invalid D-Bus response for {interface}.{name}")
        return value.value

    async def _method(self, path: str, interface: str, method: str) -> None:
        reply = await self._call(Message(
            destination=SERVICE, path=path,
            interface=f"{SERVICE}.{interface}", member=method,
        ))
        if reply.body[0] != 0:
            raise RuntimeError(f"{interface}.{method} returned error {reply.body[0]}")

    async def find_device(self) -> Device:
        version = await self._property(ROOT, "Manager", "APIVersion")
        if version != 2:
            raise RuntimeError(f"unsupported ratbagd API version {version} (expected 2)")
        paths = await self._property(ROOT, "Manager", "Devices")
        matches = []
        for path in paths:
            name = await self._property(path, "Device", "Name")
            if "G502" in name:
                matches.append(Device(name, path))
        if not matches:
            raise RuntimeError("no G502 found")
        if len(matches) > 1:
            raise RuntimeError("multiple G502 devices found; cannot choose safely")
        return matches[0]

    async def profiles(self, device: Device) -> list[Profile]:
        paths = await self._property(device.path, "Device", "Profiles")
        profiles = []
        for path in paths:
            index = await self._property(path, "Profile", "Index")
            active = await self._property(path, "Profile", "IsActive")
            disabled = await self._property(path, "Profile", "Disabled")
            profiles.append(Profile(index, path, active, disabled))
        return profiles

    async def switch(self, device: Device, index: int) -> bool:
        """Select a profile and queue its commit; return False if already active."""
        selected = next((p for p in await self.profiles(device) if p.index == index), None)
        if selected is None:
            raise RuntimeError(f"profile {index} not found")
        if selected.active:
            return False
        if selected.disabled:
            raise RuntimeError(f"profile {index} is disabled")
        await self._method(selected.path, "Profile", "SetActive")
        if not await self._property(selected.path, "Profile", "IsActive"):
            raise RuntimeError(f"ratbagd did not activate profile {index}")
        await self._method(device.path, "Device", "Commit")
        return True
