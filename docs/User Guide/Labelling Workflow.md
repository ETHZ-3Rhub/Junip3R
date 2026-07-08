# Labelling workflow

Use the Labeller to create and edit instances, points, and bounding boxes for each image.

## Opening the Labeller

- When you start `Junip3R` and select a `config.yaml` file, the Labeller opens if image files are present in `images`.
- From the Frame Extractor, open it by clicking **Start Labelling**.

## First state when the Labeller opens

- The first image is loaded from `images` (alphabetical order).
- In the instance list, **Add new instance** is selected by default.
- If `instances` (expected instance types) are defined in `config.yaml`, the first expected type is preselected.
- If no expected list is defined, the first configured instance type is selected.

## Creating and deleting instances

When **Add new instance** is selected:

- A new instance is created automatically when you place its first point or bounding box.
- The new instance uses the type shown in the instance type dropdown.
- The instance receives a name and becomes the selected instance.

An instance is deleted automatically when its last point is deleted.

You can also delete an entire instance by selecting it in the instance list and pressing the `Delete` key.

## Point and type progression

- After placing a point, selection advances to the next point of the same instance.
- After placing the last point of an instance, selection moves to **Add new instance** again.
- If expected instances are configured, the type dropdown advances to the next expected type.

Placing the next point then creates a new instance of that currently selected type.

## Selecting and changing instances

- Select any instance or point from the instance and point lists.
- While **Add new instance** is selected, you can change the type for the next instance in the type dropdown.
- If expected instances are configured, manual type changes are usually only needed when an expected instance is missing in the current frame.
- After a manual type change, automatic type selection tries to continue following the expected list for later instances.

When an existing instance is selected, you can also change its type in the dropdown.
If the new type has fewer points, extra points at the end are removed.

## Editing points and bounding boxes

### Points

- Place a point: left-click on the image.
- Move a point: drag with left mouse button.
- Delete a point: right-click the point.

### Bounding boxes

- Place a box: left-click once for the first corner, then left-click again for the opposite corner.
- Delete a box: right-click inside the box area (but not on a point).
- Move a box: not supported.
- Replace a box: select it in the point list and place the two corners again.

## Undo and redo

- Undo: `Ctrl+Z`
- Redo: `Ctrl+Y`

Undo/redo history is tracked per image.

## Image navigation

- Use **Next** and **Previous** buttons.
- Or use `Left Arrow` and `Right Arrow` keys.
- Jump to any image with the image slider.

## Saving and output

- All changes are saved automatically.
- For each image, a matching JSON label file is written to `labels` (next to `images`).

