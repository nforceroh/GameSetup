import unittest
from types import SimpleNamespace

from dbus_fast import MessageType, Variant

from g502_profile.ratbag import ROOT, RatbagClient


class FakeBus:
    def __init__(self):
        self.calls = []
        self.activate = True
        self.fail_commit = False
        self.values = {
            (ROOT, "Manager", "APIVersion"): ("i", 2),
            (ROOT, "Manager", "Devices"): ("ao", ["/device"]),
            ("/device", "Device", "Name"): ("s", "Logitech G502"),
            ("/device", "Device", "Profiles"): ("ao", ["/profile0", "/profile1"]),
            ("/profile0", "Profile", "Index"): ("u", 0),
            ("/profile0", "Profile", "IsActive"): ("b", True),
            ("/profile0", "Profile", "Disabled"): ("b", False),
            ("/profile1", "Profile", "Index"): ("u", 1),
            ("/profile1", "Profile", "IsActive"): ("b", False),
            ("/profile1", "Profile", "Disabled"): ("b", False),
        }

    async def call(self, message):
        self.calls.append((message.path, message.member))
        if message.member == "Get":
            interface, name = message.body
            signature, value = self.values[(message.path, interface.rsplit(".", 1)[-1], name)]
            return SimpleNamespace(message_type=MessageType.METHOD_RETURN,
                                   body=[Variant(signature, value)])
        if message.member == "SetActive" and self.activate:
            self.values[(message.path, "Profile", "IsActive")] = ("b", True)
        if message.member == "Commit" and self.fail_commit:
            return SimpleNamespace(message_type=MessageType.ERROR,
                                   body=["commit denied"], error_name="test.Error")
        return SimpleNamespace(message_type=MessageType.METHOD_RETURN, body=[0])


class RatbagClientTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bus = FakeBus()
        self.client = RatbagClient(self.bus)
        self.device = await self.client.find_device()

    async def test_discovers_device_and_profiles(self):
        self.assertEqual(self.device.name, "Logitech G502")
        profiles = await self.client.profiles(self.device)
        self.assertEqual([(p.index, p.active) for p in profiles], [(0, True), (1, False)])

    async def test_switch_activates_and_commits(self):
        self.assertTrue(await self.client.switch(self.device, 1))
        methods = [(path, method) for path, method in self.bus.calls if method != "Get"]
        self.assertEqual(methods, [("/profile1", "SetActive"), ("/device", "Commit")])

    async def test_active_or_missing_profile_does_not_write(self):
        self.assertFalse(await self.client.switch(self.device, 0))
        with self.assertRaisesRegex(RuntimeError, "profile 9 not found"):
            await self.client.switch(self.device, 9)
        self.assertFalse(any(method != "Get" for _, method in self.bus.calls))

    async def test_failed_activation_does_not_commit(self):
        self.bus.activate = False
        with self.assertRaisesRegex(RuntimeError, "did not activate"):
            await self.client.switch(self.device, 1)
        self.assertNotIn(("/device", "Commit"), self.bus.calls)

    async def test_disabled_profile_does_not_write(self):
        self.bus.values[("/profile1", "Profile", "Disabled")] = ("b", True)
        with self.assertRaisesRegex(RuntimeError, "profile 1 is disabled"):
            await self.client.switch(self.device, 1)
        self.assertFalse(any(method != "Get" for _, method in self.bus.calls))

    async def test_commit_error_is_reported(self):
        self.bus.fail_commit = True
        with self.assertRaisesRegex(RuntimeError, "commit denied"):
            await self.client.switch(self.device, 1)

    async def test_rejects_multiple_matching_devices(self):
        self.bus.values[(ROOT, "Manager", "Devices")] = ("ao", ["/device", "/other"])
        self.bus.values[("/other", "Device", "Name")] = ("s", "Another G502")
        with self.assertRaisesRegex(RuntimeError, "multiple G502"):
            await self.client.find_device()


if __name__ == "__main__":
    unittest.main()
