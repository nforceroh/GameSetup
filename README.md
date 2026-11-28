# GameSetup

Setup notes and scripts for Linux gaming tools and game installations.

## Python environment

The repository uses [`uv`](https://docs.astral.sh/uv/) to manage its Python
virtual environment.

From the repository root, create `.venv`:

```bash
uv venv
```

Activate it in the current shell:

```bash
source .venv/bin/activate
```

The current Python scripts use only the Python standard library, so there are
no third-party Python dependencies to install. Individual scripts may document
additional requirements in their own setup notes.

## Games

### Digital Combat Simulator

[`DCS/`](DCS) contains setup notes for installing and launching DCS through UMU.
See [`DCS/README.md`](DCS/README.md) for details.

### Star Citizen

[`StarCitizen/`](StarCitizen) contains setup scripts and notes. Full setup
documentation is still pending.

### World of Tanks

[`WoT/`](WoT) contains setup notes for launching World of Tanks through
[UMU](https://github.com/Open-Wine-Components/umu-launcher) with Proton or
GE-Proton. See [`WoT/README.md`](WoT/README.md) for:

- [Updating the Proton runner and DXVK](WoT/README.md#updating-the-proton-runner-and-dxvk)
- `PROTONPATH` and runner selection

## Shared tools

- [`umu-launcher/`](umu-launcher) — Fedora installation notes for UMU and the
  `umu-run` command.
- [`Proton-GE/`](Proton-GE) — GE-Proton updater and NTSync setup.
