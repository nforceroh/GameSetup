# GameSetup

Setup notes and scripts for my games. Each game gets its own directory with
its own instructions and scripts:

- [`DCS/`](DCS) — Digital Combat Simulator installed and launched through UMU;
  see [`DCS/README.md`](DCS/README.md) for the setup notes.
- [`StarCitizen/`](StarCitizen) — Star Citizen setup (notes pending).
- [`WoT/`](WoT) — World of Tanks, launched through [UMU](https://github.com/Open-Wine-Components/umu-launcher)
  with a Proton/GE-Proton compatibility tool. See [`WoT/README.md`](WoT/README.md)
  for the launcher itself.

## UMU runner management

ProtonPlus is not a suitable runner manager for this UMU-only setup: its runner
management requires a supported launcher integration, such as Steam. Installing
another launcher solely to use ProtonPlus is not needed for this setup.

For WoT, see [`WoT/README.md`](WoT/README.md#updating-the-proton-runner-and-dxvk)
for the current `PROTONPATH`, runner-selection, and DXVK notes.
