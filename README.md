# Junip3R

Junip3R is a desktop GUI for labelling pose-estimation and object-detection data:
bounding boxes, keypoints, polygons, and polylines, with YOLO detect/pose dataset
export. It also extracts labelled frames from video and manages project setup and
configuration, all from one application.

Full documentation: https://ethz-3rhub.github.io/Junip3R

## Features

- Project setup GUI for configuring instance types, keypoints, skeletons, and
  expected instances per image, with a live preview
- Three labelling modes: YOLO pose estimation, YOLO object detection, and a
  freeform native mode for tasks that don't fit the YOLO shapes
- Frame extraction and tagging from video
- A labelling editor for keypoints, bounding boxes, polygons, and polylines, with
  undo/redo
- YOLO dataset export with configurable train/val splits

See the [Quick Start guide](docs/User%20Guide/Quick%20Start.md) for a step-by-step
walkthrough.

## Installation

**Portable executable (Windows, no Python required):** download the latest
release from the
[Releases page](https://github.com/ETHZ-3Rhub/Junip3R/releases/latest), extract
the ZIP, and run `Junip3R.exe`.

**As a Python package** (Python 3.10+):

```bash
python -m pip install "git+https://github.com/ETHZ-3Rhub/Junip3R.git"
junip3r
```

See the [Installation guide](docs/User%20Guide/Installation.md) for details,
including installing a specific branch or release.

## Development

```bash
# Install in editable mode with dev dependencies (pytest, pyinstaller)
pip install -e ".[dev]"

# Run the test suite
pytest

# Build a standalone Windows executable
build_executable.bat
```

See `CLAUDE.md` for an overview of the codebase's architecture.

## License

Junip3R is licensed under the [GNU AGPLv3](LICENSE) or later. It uses PySide6
(LGPLv3) and other third-party packages; see [`licenses/`](licenses/) for their
license notices.
