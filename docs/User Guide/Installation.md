# Installation

Junip3R can be installed in two ways:

1. Use the **portable executable** from the latest GitHub release (no Python setup needed).
2. Install as a **Python package** from GitHub and run it with the `junip3r` command.

## Option 1: Portable executable (ZIP)

Latest release: https://github.com/ETHZ-3Rhub/Junip3R/releases/latest

1. Open the latest release page on GitHub.
2. Download the ZIP file that contains the Windows executable.
3. Extract the ZIP to any folder.
4. Run `Junip3R.exe`.

This installation is self-contained and does not require a separate Python installation.  
The Junip3R.exe file must always be located next to the _internal folder.

## Option 2: Install from GitHub as a package

Repository: https://github.com/ETHZ-3Rhub/Junip3R

### Prerequisites

- Python 3.11 or newer
- pip

### Install

```powershell
python -m pip install "git+https://github.com/ETHZ-3Rhub/Junip3R.git"
```

If you are installing from a specific branch:

```powershell
python -m pip install "git+https://github.com/ETHZ-3Rhub/Junip3R.git@<branch-name>"
```

Or a specific release:

```powershell
python -m pip install "git+https://github.com/ETHZ-3Rhub/Junip3R.git@<release-version>"
```

### Run

```powershell
junip3r
```

## Verify installation

- Portable install: the app opens when you run `Junip3R.exe`.
- Package install: the app opens when you run `junip3r` in a terminal.

## Updating

Portable install: Download the latest release from GitHub and replace the existing version.

Package install:

```powershell
python -m pip install --upgrade "git+https://github.com/ETHZ-3Rhub/Junip3R.git"
```

