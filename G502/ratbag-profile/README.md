# G502 ratbag profile CLI

A small Python application that lists and switches existing G502 hardware
profiles through ratbagd's system D-Bus API. It does not call `ratbagctl` or
edit profile settings.

Requires Python 3.11+, ratbagd, and a user authorized to access its D-Bus
service. The Python dependency is [dbus-fast](https://dbus-fast.readthedocs.io/).

From this directory, using [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run g502-profile list
uv run g502-profile switch 1
```

Alternatively, install the project into a virtual environment with
`python -m pip install .`, then use `g502-profile list` or
`g502-profile switch INDEX`.

The switch command reports when ratbagd has queued a commit. Commits are
asynchronous, so that message does not verify the hardware write succeeded.
Device paths are discovered each time; multiple matching G502 devices are
reported as an error rather than choosing one. Disabled profiles are shown in
the list but cannot be activated by this app.

Run the tests with `uv run python -m unittest discover -s tests`.
