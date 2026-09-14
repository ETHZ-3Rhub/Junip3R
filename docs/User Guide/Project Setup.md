# Project Setup

The recommended way to create a project is the Setup GUI, launched automatically the
first time you create a new project. This page covers that flow. If you'd rather write
`config.yaml` by hand, see [Editing config.yaml manually](#editing-configyaml-manually)
at the end of this page.

## Starting Junip3R

When you launch Junip3R you land on a welcome screen with two choices:

- **Create a new project** - opens the New Project window (below).
- **Open an existing project** - opens a file picker to select an existing project's
  `config.yaml`, then opens that project directly (skipping Setup).

## Creating a new project

- Pick a preset from the list, or `Empty` to start from scratch. Presets include any
  templates you've saved before (see [Saving as a template](#saving-as-a-template)).
- No preset fits? Click **Load Existing Project...** to pull in another project's
  config (and preview image/instances, if any) as a starting point, without saving it
  as a template first.
- Set the **Location** for the new project's folder.
- Choose a **Mode** - see [Modes](#modes) below. This is locked to whatever mode a
  selected preset already uses; only `Empty` lets you choose freely.
- Click **OK**. Starting from `Empty` takes you straight into the Setup window.
  Starting from a preset copies its config into the new location, then asks whether to
  **Continue Setup** (open the Setup window to adjust it further) or **Use as is**
  (skip Setup and open the project directly).

## Modes

Junip3R supports three labelling modes, chosen once per project in the New Project
window:

- **YOLO Pose Estimation** (`yolo_pose`) - keypoints per instance type, each with an
  optional skeleton for visualization, plus an optional bounding box (manual or
  computed automatically from the placed keypoints). This is the primary mode Junip3R
  is built around, and the rest of this User Guide (Quick Start, Labelling Workflow)
  focuses on it.
- **YOLO Object Detection** (`yolo_detect`) - bounding boxes only, no keypoints. Each
  instance type is just a name and a color.
- **Freeform** (`freeform`) - the native, unconstrained format: a freeform list of
  members per instance type (keypoints, bounding boxes, polygons, or polylines, in any
  combination and order), for labelling tasks that don't fit the YOLO shapes above.

The mode determines what the Setup window lets you configure (see below) and the shape
of the exported labels.

## The Setup window

Changes here take effect immediately in the preview.

### Instance Types

- **Add Instance Type** creates a new, empty instance type.
- Double-click a name to rename it.
- Click an instance type's color cell to choose **Automatic** (hue-spaced based on how
  many instance types exist) or **Select Color...** (pick one explicitly).
- Drag rows to reorder them.
- Select a row and click **Remove** to delete it.

### Members (YOLO Pose Estimation and Freeform modes)

Select an instance type to edit its members:

- **YOLO Pose Estimation**: click **Add Keypoint** to add a keypoint, and use the
  **Bounding Box Mode** dropdown (**Manual** or **Automatic**) to control whether this
  instance type also has a bounding box.
- **Freeform**: click **Add Member** and choose **Keypoint**, **Bounding Box**,
  **Polygon**, or **Polyline** - any combination, in any order.
- Double-click a member's name to rename it, click its color cell to set a color (same
  Automatic/Select Color... choice as instance types), drag to reorder, and select +
  **Remove** to delete one.

### Skeleton (YOLO Pose Estimation and Freeform modes)

The Skeleton tab lists connections between the selected instance type's keypoints
(used for visualization, in the preview and in the real Labeller):

- Use the last (empty) row to add a new connection - pick both endpoint keypoints.
- Right-click a row and choose **Delete line** to remove a connection.
- Click the **Color** swatch at the bottom to set the skeleton line color (Automatic or
  a specific color, same as above).

### Expected Instances

A project-wide, ordered list of instance types you expect to label in each image (for
example, one entry per animal in a multi-animal recording). This drives the Labeller's
automatic type selection while placing instances - see
[Labelling Workflow](Labelling%20Workflow.md).

- **Add Instance** and choose an instance type from the dropdown - the same type can be
  added more than once (e.g. "mouse" twice, for two mice per image).
- Drag entries to reorder them.
- Select an entry and click **Remove** to delete it.

### Preview

- **Choose Preview Image...** picks a sample image to preview your instance layout on.
- **Open Preview** opens a separate window with the real Labeller editor, wired to this
  sample image - place, drag, and delete instances exactly as you would when labelling
  for real, to check that your instance types and skeleton look right before committing
  to them. It updates live as you keep editing instance types, and closes automatically
  when you close or leave Setup.

### Saving as a template

**File -> Save as Template...** saves the current config (and preview image/instances,
if any) under a name of your choice, so it shows up as a preset the next time you
create a new project.

## What's next

- No images yet: click **Add Video Frames** to open the Frame Extractor - see
  [Frame Extraction](Frame%20Extraction.md).
- Images already in place: use **Window -> Start Labelling** to open the Labeller - see
  [Labelling Workflow](Labelling%20Workflow.md).

## Editing config.yaml manually

The Setup window is the recommended way to configure a project - this documents the
underlying file format for scripting, or for understanding what Setup actually writes.
The shape of `instance_types` depends on the project's `mode` (see [Modes](#modes)
above); colors are hex strings, and are auto-assigned (hue-spaced across however many
sibling entries exist) wherever they're omitted.

### YOLO Pose Estimation

```yaml
mode: yolo_pose
instance_types:
- name: mouse_top
  bounding_box: manual   # or `automatic`; this is the default if omitted
  color: "#0000ff"       # optional
  keypoints:
  - nose                 # a bare name, or...
  - name: headcentre      # ...{name, color} for an explicit color
    color: "#00ff4c"
  skeleton:               # optional
    color: "#999999"      # optional
    lines:
    - [nose, headcentre]
instances:                # optional - see below
- mouse_top
```

`instances` is an ordered, project-wide list of expected instance types per image (the
same name can appear more than once) - it drives the Labeller's automatic type
selection while placing instances, and applies the same way in every mode below.

### YOLO Object Detection

```yaml
mode: yolo_detect
instance_types:
- cat                    # a bare name, or...
- name: dog               # ...{name, color} for an explicit color
  color: "#ff0000"
instances:
- cat
- dog
```

### Freeform

```yaml
mode: freeform
instance_types:
- name: mouse
  color: "#0000ff"
  members:
  - nose                 # a bare name defaults to a keypoint, or...
  - name: tail             # ...{name, type, color, size} for anything else -
    type: polyline         # type is one of keypoint, bounding_box, polygon, polyline;
    size: 5                # size is the fixed point count (polygon/polyline only,
    color: "#ff0000"       # omit for an unlimited number of points)
  - name: box
    type: bounding_box
  skeleton:
  - [nose, tail]
instances:
- mouse
```

### Example configs

- Minimal example: [`docs/Examples/minimal_config.yaml`](../Examples/minimal_config.yaml)
- Advanced example: [`docs/Examples/advanced_config.yaml`](../Examples/advanced_config.yaml)
