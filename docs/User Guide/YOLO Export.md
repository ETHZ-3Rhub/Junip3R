# Exporting

Junip3R can export project data as a YOLO training dataset.

## Open the export dialog

In the Labeller: **File -> Export as... -> Export as YOLO Dataset**.

## Choose the target folder

Click the folder button next to **Target Folder** and select where the dataset should
be created. If the folder already has files in it, you'll be asked to confirm before
they're overwritten.

## Choose which instance types to include

Check or uncheck instance types in the list - only checked types are included in the
export.

By default, only images containing at least one instance of a checked type are
exported at all. Check **Include empty images (no instances)** to export every image
regardless.

## Assign images to Train/Val

The **Set Split** row shows how many images are currently assigned to each set. Click
its icon button to open the split dialog:

- **Group by** - keep entries together across the split, e.g. by video (if that's one
  of your image tags) instead of assigning each image independently. `Image` assigns
  every image on its own.
- **Auto Split** - drag the slider to your target train/val ratio, then click
  **Split Unassigned** to assign every still-unassigned group accordingly. This never
  touches groups you've already assigned.
- Assign a specific group by hand: change its **Set** column directly in the table
  (Unassigned/Train/Val).
- **Unassign All** clears every assignment and starts over.
- **Import Set Split from File...** loads a `set_split.yaml` from elsewhere (e.g. from
  another dataset's `meta` folder, see below) and replaces all current assignments with
  it, after confirming.

Click **OK** to save your split back to the project - it's reused automatically the
next time you export this project, so re-exporting later (e.g. after labelling more
images) keeps already-assigned images in the same set.

## Export the dataset

Back in the export dialog, click **Export**. This writes the dataset to the target
folder using your current instance type and split settings, including a `meta/set_split.yaml`
file recording the split that was used - the same file you can point **Import Set Split
from File...** at later, from this or another project, to reuse that exact split.
