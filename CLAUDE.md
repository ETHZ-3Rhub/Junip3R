# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Junip3R is a PySide6 (Qt) desktop GUI for labelling pose-estimation data: bounding boxes, keypoints,
polygons and polylines, with YOLO detect/pose export. It also extracts frames from video and manages
project setup/config.

## Common commands

```bash
# Install (editable, with dev deps: pytest, pyinstaller)
pip install -e ".[dev]"
# or, since a uv.lock is present:
uv sync

# Run the full test suite (from repo root)
pytest

# Run a single test file / test
pytest tests/unit/test_logging_setup.py
pytest tests/unit/test_logging_setup.py::TestClassName::test_name -v

# Launch the app (start screen -> new project / open project)
junip3r
# or directly against a project config.yaml, skipping the start screen:
junip3r_label
junip3r_frame_extractor

# Build a standalone Windows executable (pyinstaller, --onedir)
build_executable.bat
```

Pytest config lives in `pyproject.toml` (`[tool.pytest.ini_options]`): tests are discovered under
`tests/`, files matching `test_*.py`/`*_test.py`. `tests/unit` and `tests/integration` are the two
suites; `tests/conftest.py` holds shared fixtures.

`_testdata/` contains real fixture projects (config.yaml + images/context/labels folders) used by
tests, but it is gitignored — it exists locally/CI-provisioned, not committed.

## Architecture

### Three sub-apps behind one shell

`src/junip3r/main.py` defines `AppController`, which owns a single top-level `QMainWindow` at a time
and switches between three independent Qt applications, each with its own `from_config_file(...)`
factory and `main()` standalone entry point:

- `junip3r.setup` — project/skeleton configuration editor (`setup/main.py`)
- `junip3r.frame_extractor` — video frame extraction and tagging (`frame_extractor/main.py`)
- `junip3r.labeller` — the labelling editor itself (`labeller/main.py`)

The sub-apps never talk to each other directly; they only emit Qt signals (`switch_to`, `closed`)
that `AppController` listens to. All three can also run standalone via their own `main()` (each pops
a file dialog to pick a project's `config.yaml`) — see the `junip3r_label` / `junip3r_frame_extractor`
console-script entry points in `pyproject.toml`.

A project on disk is a folder containing `config.yaml` plus `images/`, `context/` (optional video
context per image), `labels/`, and `_frame_extractor/` subfolders — see `labeller/main.py`'s
`from_config_file` for exactly how these are located and wired into repositories.

### Per-app layering (repository -> model -> layout -> widgets)

Each sub-app (most fully realized in `labeller/`) follows the same layered split:

- `data/repository/abc.py` — `Protocol` interfaces (`IImageRepository`, `ILabelRepository`,
  `IConfigRepository`, `ISelectionRepository`, `ISettingsRepository`, `IContextRepository`, ...).
  Concrete implementations live alongside (e.g. `image.py`, `label.py`, `context.py`). Prefer
  depending on the protocol, not the concrete class — models are constructed by wiring repository
  implementations together in each sub-app's `main.py`.
- `data/types/` — plain data types/enums shared by repositories and models (`abc.py`, `delegates.py`).
- `model/` — Qt-aware application state (`QObject` subclasses emitting signals), e.g.
  `AppModel` (pure CRUD over repositories), `PoseImageModel`, undo/redo via `undo_commands.py`
  (Qt's Command pattern — commands snapshot state on `redo()`/apply on `undo()`).
- `layout/` — historically **generated** code from `.ui` files via `pyside6-uic`; there's no `.ui`
  toolchain left at all now (no `ui/` folder, no `compile_ui.bat`) — every `layout/*.py` file
  (`labeller_layout.py`, `pose_editor.py`, `frame_extractor.py`) is hand-written, mirroring the old
  `Ui_X`-class-that-the-widget-subclasses shape. `layout/yolo_export.py` (paired with the unused
  `labeller/widgets/yolo_export.py`) is the one exception still literally shaped like raw
  `pyside6-uic` output — it's dead code (superseded by
  `labeller/export/yolo/widgets/yolo_export_dialog.py`), not wired from anywhere, left as-is rather
  than migrated. Some main windows (`labeller`, `frame_extractor`) keep a separate `layout/` module
  per sub-app; others (`setup/widgets/setup_window.py`, and smaller widgets like
  `labeller/widgets/image_navigation.py`) build their whole UI directly in the widget file instead —
  both patterns coexist: separate `layout/` module for top-level main windows, inline for everything
  smaller.
- `widgets/` — hand-written widget/controller code that composes the generated/hand-written layout
  with the model layer (event handling, signal wiring, rendering).
- `controller/` — cross-cutting input controllers (e.g. `editor_controller.py`,
  `camera_navigation.py`) that translate UI events into model operations.

`common/config/` and `common/labels/` hold data types and (de)serialization shared between the
`setup` and `labeller` sub-apps (instance types, members, keypoints, bounding boxes, polygons,
polylines).

`labeller/legacy/legacy_label_converter.py` migrates older CSV-based labels to the current JSON
label format; `labeller/main.py` runs this conversion automatically on project load when it finds
legacy `.csv` labels without a corresponding `.json` file.

`labeller/export/yolo/` converts internal label data to YOLO detect/pose datasets: `conversion/` maps
internal instance types, `serialization/` writes the dataset files (images/labels/metadata), and
`widgets/` hosts the export dialog UI.

### Repo is mid-refactor — expect transient duplicate files

The working tree is actively being restructured (see recent commits like "Another big model
restructuring", "Restructured editor, removed designer layout"). You may find `*_2.py` siblings of
existing modules (e.g. `data/repository/label_2.py` next to `label.py`,
`export/yolo/widgets/set_split_dialog_2.py` next to `set_split_dialog.py`) where only one of the pair
is actually imported/wired up — grep for imports before assuming a file is live. `ARCHITECTURE.md` at
the repo root documents one such in-flight redesign (the `NewInstanceTypeWorkflow` split between
`AppModel` and `EditorModel`) as a design/planning doc, not necessarily the current state of the
code — verify against the actual `model/` files rather than trusting it outright.

### Logging

`logging_setup.py`'s `LoggingManager` writes per-app-run key=value formatted logs (info + debug
level, separate files) to `%LOCALAPPDATA%/ETH3RHub/Junip3R/logs` (or `~/.junip3r/logs`), namespaced
by process session and app name. Distinguishes `run_mode="standalone"` (sub-app launched directly)
from `run_mode="integrated"` (launched from the shared `AppController` shell). Log with
`extra={"event_category": ..., "event_name": ...}` to populate the structured `event` field.

## Docs

User-facing docs are an MkDocs (material theme) site under `docs/`, configured in `mkdocs.yml`
(`site_url: https://ethz-3rhub.github.io/Junip3R`). `docs/index.md` links the User Guide pages and
example `config.yaml` files under `docs/Examples/`.