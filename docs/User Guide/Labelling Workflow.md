# Labelling Workflow

Use the Labeller to create and edit instances and their members (keypoints, bounding
boxes, polygons, polylines - whichever your instance types have) for each image.

## Opening the Labeller

- From Setup: **Window -> Start Labelling** (if images are already in the project) or
  **Add Video Frames -> ... -> Start Labelling** (to extract frames first).
- Opening an existing project from the welcome screen also goes straight to the
  Labeller - if the project has no images yet, it shows a prompt to add some via Frame
  Extractor instead of the editor.

The first image (alphabetical order) loads with **Add new instance** selected in the
Instances list, using the first expected instance type if any are configured (see
[Project Setup](Project%20Setup.md#expected-instances)), otherwise the first configured
instance type.

## Creating and deleting instances

While **Add new instance** is selected in the Instances list:

- Placing a member (a keypoint, the two corners of a bounding box, ...) creates a new
  instance of whatever type is shown in the Instance Type dropdown, names it, and
  selects it.

An instance is deleted automatically once its last member is removed - right-clicking a
member (see [Editing members](#editing-members) below) is usually the fastest way to
get there. To delete a whole instance directly instead, select it in the Instances list
and press `Delete`.

`Ctrl+C` / `Ctrl+V` copies the selected instance and pastes a duplicate with a new id.

## Selection and type progression

- `Up`/`Down` (or `Space`) move the current selection to the previous/next member,
  crossing between instances and wrapping around to **Add new instance**.
- After placing an instance's last member, selection returns to **Add new instance**;
  if expected instances are configured, the Instance Type dropdown advances to the next
  expected type automatically.
- You can change the Instance Type dropdown manually at any time (normally only needed
  when an expected instance is missing from the current image) - automatic advancing
  picks back up from there for later instances.
- Selecting an existing instance also lets you change *its* type from the dropdown.
  Its members are rebuilt to match the new type: data carries over member-by-member for
  as long as the corresponding members are still the same kind, and stops at the first
  mismatch (or if the new type simply has fewer members) - so a type with completely
  different members effectively starts that instance's members over. Selection resets
  to the new type's first member.

## Editing members

### Keypoints

- Place: left-click. Hold `Ctrl` while clicking to place it already marked occluded.
- Move: drag with the left mouse button.
- Mark occluded / visible: `Ctrl` + right-click an existing keypoint to toggle it.
- Delete: right-click the keypoint.

### Bounding boxes

- Place: left-click for the first corner, left-click again for the opposite corner.
- Resize/reposition: drag any corner.
- Delete: right-click inside the box (not on a corner).

### Polygons and polylines

- Place: left-click each point in order.
  - If the member has a fixed point count (set in Project Setup), it's completed
    automatically after the last click.
  - Otherwise, keep clicking to add points, then hold `Ctrl` and click to finish.
- Remove the last point while still placing: right-click.
- Delete an already-placed one: right-click it.

## Other view controls

- Hold `Shift` to show every member's label at once, instead of only the one under
  your cursor.
- If this project has video context (see [Frame Extraction](Frame%20Extraction.md)),
  hold `Ctrl` to preview nearby frames.

## Undo and redo

- Undo: `Ctrl+Z`
- Redo: `Ctrl+Y`

Undo/redo history is tracked per image.

## Image navigation

- Use the **Next**/**Previous** buttons, `Left`/`Right` arrow keys, or the image slider.

## Saving and output

- All changes save automatically - one JSON label file per image, written to `labels`
  (next to `images`).
