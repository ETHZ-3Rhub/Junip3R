# Exporting

Junip3R can export project data as a YOLO training dataset.

## Open the export dialog

In the Labeller, open:

**File -> Export as... -> YOLO Training Dataset**

## Choose the target folder

- In the YOLO export dialog, click the folder button next to **Target Folder**.
- Select the folder where the dataset should be created.

## Choose how to split the dataset

Use the **Train/Val split by:** dropdown to choose how data is grouped:

- **Video**: all images from the same video stay in the same set
- **Image**: each image is assigned independently

Use the slider below the dropdown to choose how many videos or images go into each set.

## Choose which instance types to include

In the instance type list, enable or disable types using the checkboxes.

Only checked instance types are included in the exported dataset.

## Export the dataset

Click **Export** to generate the YOLO dataset.

The export uses the selected split settings and writes the dataset to the target folder.

## Reusing an existing split

The exported dataset includes a `set_split.txt` file that records which images or videos were assigned to each set.

If you open the export dialog again and select the same target folder:

- the existing split is loaded automatically
- the same images or videos stay in the same sets
- this helps keep training results consistent and comparable

If new images or videos have been added, you can use the slider to assign the new items as well.

If everything is already assigned, the slider is replaced with the message:

`set is already fully split`

## Using a split from another dataset folder

When exporting to a different target folder, you can still reuse an older split.

- Click the file button next to **Existing split file:**
- Select the `set_split.txt` file from an existing dataset folder

This applies the same split layout to the new export.
