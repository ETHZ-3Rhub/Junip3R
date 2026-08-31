# Test coverage assessment

This is a survey of the whole `src/junip3r` tree for unit-testability, done to plan an
increase in test coverage. It answers two questions per module: *can this be unit-tested
with plain pytest, no live `QApplication`/event loop* (see the project's standing rule against
headless Qt tests), and *is it worth testing* (does it have real logic, or is it a thin
data holder / GUI glue).

Methodology: `grep -rL PySide6 src/junip3r` found every file that doesn't import PySide6
directly, then each one was read to check for (a) transitive Qt imports (a plain-looking
module that imports a `QObject`-bearing sibling just for a type it also happens to define),
and (b) actual logic worth a regression test vs. trivial pass-through code.

## Legend

- **easy** — pure logic/data, construct inputs and assert outputs, no fixtures needed.
- **moderate** — needs fixtures (tmp files, synthetic images/video via `cv2`, fake
  `Protocol` implementations) but no Qt.
- **transitively Qt** — doesn't import PySide6 itself, but importing it pulls in a module
  that does (usually just to import a plain dataclass living alongside a `QObject`). Still
  testable with plain pytest as long as PySide6 is *importable* (true in dev/CI) — no
  `QApplication` needed, just don't touch the `QObject` classes in that module.
- **hard / GUI** — actually needs a live Qt event loop, widgets, or signal delivery to
  exercise. Out of scope per the project's no-headless-Qt-testing rule; would need the app
  running (see `run` skill) rather than pytest.
- **low value** — testable, but it's a `Protocol` or a dataclass with no computed
  properties/methods; a test would just restate the field list.

## Already covered (before this pass)

- `common/discovery.py`, `labeller/data/discovery.py` — `tests/unit/test_discovery.py`
- `labeller/config/parser.py`, `common/config/serialization.py` (via `parse_config`) —
  `tests/unit/test_config_parser.py`

## Added in this pass

- `tests/unit/test_label_serialization.py` — `common/labels/serialization.py`
- `tests/unit/test_legacy_labels.py` — `common/labels/legacy.py`
- `tests/unit/test_labeller_delegates.py` — `labeller/data/types/delegates.py`
- `tests/unit/test_selection_strategies.py` — `labeller/model/instance_type_selection_strategy.py`, `labeller/model/member_selection_strategy.py`, `setup/model/preview_member_selection_strategy.py`
- `tests/unit/test_app_model.py` — `labeller/model/app_model.py`
- `tests/unit/test_yolo_export.py` — `labeller/export/yolo/conversion/mapping_instance_converter.py`, `labeller/export/yolo/serialization/yolo_label_writer.py`
- `tests/unit/test_set_split.py` — `labeller/export/yolo/set_split.py`
- `tests/unit/test_legacy_label_converter.py` — `labeller/legacy/legacy_label_converter.py`
- `tests/unit/test_labeller_repositories.py` — `labeller/data/repository/{image,context,label}.py`
- `tests/unit/test_frame_extractor_repositories.py` — `frame_extractor/data/repository/{image_repository,tag_repository,video_repository}.py`, `frame_extractor/util/selection/random.py` (`sample_frames_uniform_unique` only)
- `tests/unit/test_setup_config_data.py` — `setup/data/types/data.py`
- `tests/unit/test_config_serialization.py` — `common/config/serialization.py`'s `serialize()` direction

142 tests total, all passing on Windows; CI also runs them on Ubuntu (see the PySide6
headless-import fix in `.github/workflows/unit-tests.yml`).

## common/

| Module | Verdict | Notes |
|---|---|---|
| `config/abc.py` | low value | Just `ConfigMode` enum. |
| `config/data.py` | low value | Plain frozen dataclasses, no methods. Exercised indirectly via `ConfigSerializer` tests. |
| `config/serialization.py` | **easy** | `ConfigSerializer`: `deserialize()` covered via `parse_config`; `serialize()` now covered directly (round trip through `deserialize`, plus the color-key-omitted-when-unset / hex-when-set branches). **Implemented.** |
| `discovery.py` | easy | Covered. |
| `labels/data.py` | low value | Plain dataclasses (`Instance`, `Keypoint`, `BoundingBox`, `Polygon`, `Polyline`), a `.type` property each. |
| `labels/legacy.py` | **easy** | `LegacyLabelLoader` parses the old CSV label format: version-row detection (rewinds if first row isn't `"1.0"`), bounding-box center/size → min/max conversion, keypoint visibility gating (`p = None` if `visibility <= 0.5`). Real logic, zero tests today. **Implemented.** |
| `labels/serialization.py` | **easy** | `LabelSerializer`: JSON round trip, missing-file → `[]`, oversized-file → `ValueError`, version-mismatch → `ValueError`, and `write_instances([])` **deletes** the file rather than writing `{"instances": []}` — a easy-to-miss behavior. **Implemented.** |
| `icons.py` | GUI | `QIcon`/`QPixmap` construction. Skip. |

## labeller/

| Module | Verdict | Notes |
|---|---|---|
| `config/data.py` | low value | `LabellerConfig`/`InstanceType`/`MemberSpecs`/`SkeletonSpecs` — covered indirectly via `test_config_parser.py` (their `.new_instance()` factories are exercised there and in the delegates tests below). |
| `config/parser.py` | easy | Covered. |
| `data/discovery.py` | easy | Covered. |
| `data/repository/abc.py` | low value | Protocols only. |
| `data/repository/config.py`, `selection.py`, `settings.py` | easy, thin | Each is ~10 lines wrapping a dict/dataclass; low individual value but cheap. Left as follow-up (not implemented this pass — see "Not implemented" below). |
| `data/repository/context.py` | **moderate** | `ContextRepository.get_context` reads a video with `cv2`, splits frames into `(before, current, after)` around the midpoint. Needs a synthetic video fixture (`cv2.VideoWriter`). **Implemented.** |
| `data/repository/image.py` | **moderate** | `cv2.imread` + BGR→RGB. Needs a real image file (`cv2.imwrite` in `tmp_path`). **Implemented.** |
| `data/repository/label.py` | **moderate** | `InstanceMapper` (data ↔ runtime instance mapping) + `JuniperLabelRepository`. The mapper is the more interesting unit (member-type dispatch, `instance_type.new_instance` + field copy-back); the repository is a thin wrapper over `LabelSerializer`. **Implemented.** |
| `data/types/abc.py` | low value | Protocols only. |
| `data/types/delegates.py` | **easy, high value** | The actual label geometry (`Keypoint`, `BoundingBox`, `Polygon`, `Polyline`, `Instance`, `Skeleton`, `NewInstance`). Non-trivial logic: `_normalize_box` (min/max swap), `BoundingBox.__post_init__` deriving 4 corners, `Polygon`/`Polyline`/`Instance.bounds` (min/max aggregation over sub-bounds, `None` when nothing is set), `is_set`. This is exactly the kind of file where a silent regression (e.g. bounds computed pre- instead of post-normalization) would be easy to introduce and hard to notice visually. **Implemented.** |
| `export/yolo/conversion/mapping_instance_converter.py` | **easy, high value** | `_box_to_xywh`, and `MappingYoloPoseInstanceConverter.convert`'s per-instance mapping: missing required bounding-box member → `ValueError`, keypoints not in the mapping are silently dropped, low-visibility (`<= 0.5`) keypoints are zeroed out rather than exported as-is. `MappingYoloDatasetMetadataGenerator`/`MappingYoloDatasetGenerator` are thinner but still pure. **Implemented.** |
| `export/yolo/data.py` | low value | Dataclasses; `YoloDatasetConfig.num_keypoints` is the one computed property (covered incidentally). |
| `export/yolo/serialization/set_split_writer.py` | moderate | Thin `yaml.dump` wrapper over `SetSplitConfigSerializer` (which is tested directly). Not implemented — low marginal value once the serializer is covered. |
| `export/yolo/serialization/yolo_dataset_metadata_writer.py` | moderate | File-I/O heavy (writes one YAML per instance type + a CSV); `YoloPoseInstanceTypeSerializer.serialize` itself is pure and the more valuable unit. Not implemented this pass. |
| `export/yolo/serialization/yolo_dataset_writer.py` | moderate | Orchestrates `cv2.imwrite` + label writing per image/set; mostly I/O plumbing over already-tested pieces (`YOLOPoseLabelWriter`). Not implemented this pass. |
| `export/yolo/serialization/yolo_label_writer.py` | **easy** | `YOLOPoseLabelWriter`: asserts all instances share a keypoint count, zeroes out low-visibility keypoints on write. **Implemented.** |
| `export/yolo/set_split.py` | **easy, high value** | The most substantial pure-logic module found: `SetSplitConfigSerializer` round trip, and `SetSplit` — grouping images by tag, group vs. individual set assignment, `min_ratio`/`max_ratio`/`target_train`/`target_val` arithmetic (with off-by-one guards for `num_groups < 2`), `auto_split` (now takes an optional `rng: random.Random`, so a test can assert the exact assignment instead of just counts — see cross-cutting findings), plus the standalone `resolve_set_assignments`. **Implemented.** |
| `legacy/legacy_label_converter.py` | **easy** | Thin glue between `LegacyLabelLoader` and `LabelSerializer`, but derives `bounding_box_type`/`keypoint_names` from a real `IInstanceType.new_instance(...)` call — worth one end-to-end test. **Implemented.** |
| `model/app_model.py` | **moderate, high value** | **Not a `QObject`** — `IUndoModel` (its declared base) is a `Protocol`, now defined in the Qt-free `labeller/model/abc.py` (moved out of `undo_commands.py`, which needs `PySide6.QtGui.QUndoCommand` — see cross-cutting findings). Importing `AppModel` no longer touches PySide6 at all. Core editor state: per-image caching (only re-fetches from a repository when the image index changes or caching is disabled), instance CRUD, and `change_instance_type`'s field-carrying logic (copies over `p`/`box`/`points` from the old instance's members to the new instance type's members of matching type/position, stops at the first type mismatch). **Implemented**, using hand-written fakes for the four repository Protocols. |
| `model/image_state.py` | easy, low-ish value | `ImageState`/`OperationState`/`ImageNavigationState` frozen dataclasses; `selected_instance`/`selected_member` do real lookups (including an out-of-range member-index guard). Not implemented this pass — smaller payoff than the other model modules. |
| `model/instance_type_selection_strategy.py` | **easy, high value** | `EditorInstanceTypeWorkflow`: cursor-based "next unfulfilled expected instance type" logic, with wraparound, for both manual and automatic selection. Subtle enough (cursor advances only on a *found* unfulfilled slot, else holds) that it deserves explicit regression coverage. **Implemented.** |
| `model/member_selection_strategy.py` | **easy, high value** | `EditorMemberSelectionStrategy`: keyboard-driven next/prev member and instance navigation across instance boundaries, plus "prefer the in-progress new instance" fallback. Several branches (empty list, single instance, first/last member). **Implemented.** |
| `model/operations.py` | low value | Frozen dataclasses (`Inspect`, `DrawBox`, `DrawPolygon`, ...); `allow_inspection`/`allow_drag` are one-line derived properties, covered incidentally by nothing else touching them — cheap enough that a small test was added alongside `operations`-adjacent tests. Not implemented as a standalone file this pass. |
| `model/{camera_model,context_model,image_settings_model,pose_image_model}.py` | hard / GUI | All `QObject` subclasses (Qt signals). Skip per no-headless-Qt-testing. |
| `widgets/*`, `layout/*`, `controller/*` | hard / GUI | Rendering, event handling, generated layout code. Skip. |
| `export/yolo/widgets/*.py` | hard / GUI | Dialogs. Skip. |

## frame_extractor/

| Module | Verdict | Notes |
|---|---|---|
| `data/repository/abc.py` | low value | Protocols only. |
| `data/repository/image_repository.py` | **moderate** | CSV round trip (`Frame` list ↔ file), `extracted` flag parsed from `{"1","true","yes"}` (case-insensitive), missing file → `[]`. **Implemented.** |
| `data/repository/tag_repository.py` | **moderate** | JSON round trip keyed by image name; missing file → `({}, [])`. **Implemented.** |
| `data/repository/video_repository.py` | **moderate** | CSV round trip for `Video` list. **Implemented.** |
| `data/types/data.py` | low value | Plain frozen dataclasses. |
| `util/extraction/extraction.py` | moderate, needs real video | `ExtractionCache.extract_frame`/`extract_frame_and_context`: real `cv2.VideoCapture`/`VideoWriter` I/O with padding logic at clip boundaries. Valuable but needs a synthetic multi-frame video fixture and is comparatively expensive to set up well; left as follow-up. |
| `util/selection/abc.py` | low value | Protocol only. |
| `util/selection/kmeans.py` | moderate, needs real video | `KMeansSelectionStrategy` — real logic (frame downsampling, clustering, nearest-frame-to-centroid selection, per-video offset bookkeeping in `select_total`) but requires `sklearn` + real video frames to exercise meaningfully; a synthetic video test would mostly be testing scikit-learn. Left as follow-up. |
| `util/selection/random.py` | **easy** | `sample_frames_uniform_unique`: uniform sampling without replacement across multiple videos, mapped back to (video, frame) pairs via cumulative offsets; raises if `n > total`. `RandomSelectionStrategy` itself needs real video files (`cv2.VideoCapture` frame count) — only the pure sampling function was unit tested. **Implemented** (sampling function only). |

## setup/

| Module | Verdict | Notes |
|---|---|---|
| `data/repository/abc.py` | low value | Protocol only. |
| `data/repository/config.py` | moderate | Thin `yaml` + `ConfigSerializer` + `SetupConfig.from_config/to_config` wrapper; the interesting logic lives in `data/types/data.py`, which is tested directly. Not implemented as a standalone file. |
| `data/types/abc.py` | low value | Protocols only. |
| `data/types/data.py` | **easy, high value** | `SetupMember`/`SetupSkeleton`/`SetupInstanceType`/`SetupConfig`: `from_config`/`to_config` round trips against `common.config.data`, id-based skeleton line remapping (member id ↔ index), and the instance-type mutation helpers (`add_member`, `replace_member`, `remove_member`, `with_lines` dedup via `set()`, `add_line`/`replace_line`/`remove_line`). **Note:** `SetupMember.build()` / `SetupSkeleton.build()` (lines 46 and 84) have **no call sites anywhere in the repo** — dead code from the in-flight refactor mentioned in `ARCHITECTURE.md`; not tested, flagged for removal or wiring up. **Implemented** (the from_config/to_config/mutation methods; `build()` excluded as dead code). |
| `model/preview_member_selection_strategy.py` | **easy** | `PreviewMemberSelectionStrategy` — a variant of `EditorMemberSelectionStrategy` for the read-only preview pane (holds selection instead of falling through to a new instance). **Implemented** alongside the labeller selection-strategy tests. |
| `preview/data/abc.py` | low value | Protocols only. |
| `preview/data/delegates.py` | low value | Trivial subclasses of `labeller.data.types.delegates` adding an `id` field; no new logic. |
| `preview/data/types.py` | low value | Mirrors `labeller/config/data.py` with an `id` field; `.new_instance()` is exercised transitively by `setup_preview_label_repository.py`. |
| `preview/data/repository/setup_preview_label_repository.py` | **moderate** | Imports `ConfigState`/`ConfigStateChangeFlags`, now from the Qt-free `setup/model/config_state.py` (moved out of `config_model.py` — see cross-cutting findings), so this file no longer needs PySide6 at all. Real logic (`_resolve_instance_type`'s per-member auto-hue color fallback, `_copy_instance_data`/`_copy_member_data` preserving matching member data across a config edit) worth testing. Left as follow-up given the extra setup needed to construct fake `ISetupInstanceType` graphs. |
| `model/config_model.py`, `setup_pose_image_model.py` | hard / GUI | `QObject` subclasses. Skip. |
| `widgets/*` | hard / GUI | Skip. |

## Cross-cutting findings

- **Dead code**: `SetupMember.build()` and `SetupSkeleton.build()` in
  `setup/data/types/data.py` have no callers anywhere in the repo (confirmed via grep for
  `.build(`). They look like the intended bridge from a `SetupConfig` to a live
  `LabellerConfig`/preview instance, superseded by `setup_preview_label_repository.py`'s own
  `_resolve_instance_type`. Worth a follow-up decision: wire them up or delete them.
- **Fixed: JSON round trip silently turned some tuples into lists.** `LabelSerializer`
  converted `Polygon`/`Polyline.points` back into tuples on load but left `Keypoint.p`/
  `BoundingBox.box` as plain lists after a save/load round trip. `_keypoint_from_dict`/
  `_bounding_box_from_dict` in `common/labels/serialization.py` now convert them to tuples
  the same way the polygon loaders do (with a `None` guard, since both fields are
  optional).
- `common/labels/serialization.py` has a stray `if __name__ == "__main__":` block
  (lines 140-144) that hardcodes a developer's local path — harmless but not something a
  test should exercise; left as-is since removing it wasn't asked for.

## Testability-driven refactors

Found by looking at what the tests had to work around, not just what they cover:

- **Fixed: Qt-free `Protocol`s were trapped in Qt-coupled files.** Two cases of the same
  shape — a plain `Protocol`/dataclass/`IntFlag` with zero Qt in its own definition, defined
  in the same module as a `QObject`/`QUndoCommand` class, which forced anything depending on
  the interface to have PySide6 importable for no real reason:
  - `IUndoModel`/`IChangeTracker` lived in `labeller/model/undo_commands.py` (which needs
    `PySide6.QtGui.QUndoCommand`) even though `AppModel` — their only implementer — is not a
    `QObject`. Moved to a new `labeller/model/abc.py`, mirroring the `abc.py`-per-layer
    convention already used under `data/repository/` and `data/types/`.
  - `ConfigState`/`ConfigStateChangeFlags` lived in `setup/model/config_model.py` (which
    needs `PySide6.QtCore` for `ConfigModel(QObject)`), even though
    `setup_preview_label_repository.py` only needs them as data. Moved to a new
    `setup/model/config_state.py`, mirroring the existing `labeller/model/image_state.py`
    split (state dataclass + change flags, separate from the `QObject` model). Widgets that
    import `ConfigState`/`ConfigStateChangeFlags` from `config_model` still work unchanged —
    `config_model.py` re-exports them by importing — but they're Qt widgets already, so the
    Qt dependency there is real, not incidental.
  - Net effect: `AppModel` and `setup_preview_label_repository.py` no longer need PySide6
    importable at all (they moved from "transitively Qt" to genuinely Qt-free in this doc's
    own terms).
- **Fixed: `SetSplit.auto_split()` used the global `random` module directly**
  (`random.shuffle(unassigned_groups)`), with no way to inject determinism — which is why
  the original test could only assert train/val *counts*, not the actual assignment.
  Contrast with `frame_extractor/util/selection/random.py`'s
  `sample_frames_uniform_unique(..., seed=...)`, which already took an explicit seed and
  could therefore be asserted exactly. `auto_split` now takes an optional
  `rng: random.Random = None` (falling back to the `random` module when omitted, so all
  existing call sites are unaffected), and `test_set_split.py` has a new test asserting the
  exact group assignment for a fixed seed.

## Not implemented this pass (follow-up candidates, roughly in priority order)

1. `setup/preview/data/repository/setup_preview_label_repository.py` — real logic, just needs more fake-object setup than the others.
2. `frame_extractor/util/extraction/extraction.py` and `util/selection/kmeans.py` — need synthetic multi-frame video fixtures; worth a shared `tests/unit/conftest.py` fixture if tackled.
3. `labeller/export/yolo/serialization/{yolo_dataset_metadata_writer,yolo_dataset_writer}.py` and `set_split_writer.py` — mostly I/O plumbing over already-tested serializers; would mainly catch "did we write to the right path" regressions.
4. `labeller/data/repository/{config,selection,settings}.py` — thin enough that tests would mostly restate the implementation, but cheap if a coverage number is being tracked.
5. `labeller/model/image_state.py`, `model/operations.py` — small derived-property logic, low individual payoff.
