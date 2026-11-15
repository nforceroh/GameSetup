import contextlib
import importlib.util
import io
import pathlib
import sys
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "g502_dbus_poc", pathlib.Path(__file__).with_name("g502-dbus-poc.py")
)
poc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(poc)


class ProfileSwitchTests(unittest.TestCase):
    def run_main(self, args, profiles, active_after=True):
        with patch.object(sys, "argv", ["g502-dbus-poc.py", *args]), \
                patch.object(poc.Gio, "bus_get_sync", return_value="bus"), \
                patch.object(poc, "find_device", return_value="/device"), \
                patch.object(poc, "get_profiles", return_value=profiles), \
                patch.object(poc, "get_property", return_value=active_after), \
                patch.object(poc, "call_method") as call, \
                contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            result = poc.main()
        return result, call.call_args_list

    def test_selects_profile_then_commits(self):
        result, calls = self.run_main(["1"], [(1, "/profile1", False)])
        self.assertEqual(result, 0)
        self.assertEqual([c.args for c in calls], [
            ("bus", "/profile1", "Profile", "SetActive"),
            ("bus", "/device", "Device", "Commit"),
        ])

    def test_failed_activation_does_not_commit(self):
        result, calls = self.run_main(["1"], [(1, "/profile1", False)], False)
        self.assertEqual(result, 1)
        self.assertEqual([c.args for c in calls], [
            ("bus", "/profile1", "Profile", "SetActive"),
        ])

    def test_active_or_missing_profile_never_writes(self):
        for args, profiles, expected in [
            (["1"], [(1, "/profile1", True)], 0),
            (["2"], [(1, "/profile1", False)], 1),
        ]:
            with self.subTest(args=args):
                result, calls = self.run_main(args, profiles)
                self.assertEqual(result, expected)
                self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
