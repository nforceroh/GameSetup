# Installing umu-launcher on Fedora

Fedora 45 does not have an umu-launcher RPM available in this setup, so build
umu-launcher from the upstream source repository. These commands install it
system-wide under `/usr/local`.

## Install build dependencies

```bash
sudo dnf install git make scdoc cargo cmake gcc gcc-c++ libzstd-devel \
  python3 python3-devel python3-build python3-installer python3-hatchling \
  python3-hatch-vcs python3-wheel
```

## Clone and build

From the GameSetup repository root, clone upstream beside it:

```bash
git clone https://github.com/Open-Wine-Components/umu-launcher /home/sylvain/repositories/umu-launcher
cd /home/sylvain/repositories/umu-launcher
```

```bash
cd /home/sylvain/repositories/umu-launcher
git submodule update --init --recursive
```

Configure the install prefix, build, and install:

```bash
./configure.sh --prefix=/usr/local
make
sudo make install
```

Verify that the command is on your `PATH` and runs:

```bash
command -v umu-run
umu-run --help
```

To install only for your user instead, use `./configure.sh --user-install`
instead of the `/usr/local` configure command, then run `make install` without
`sudo`. This puts `umu-run` in `~/.local/bin`; add that directory to `PATH` if
it is not already there.

See the [upstream repository](https://github.com/Open-Wine-Components/umu-launcher)
for the latest build requirements and installation options.
