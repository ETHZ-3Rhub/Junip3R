# Quick Start (Pose Estimation)

The fastest path from installing Junip3R to labelled pose-estimation data. Junip3R also
supports object-detection-only and fully custom labelling - see
[Project Setup](Project%20Setup.md) for those.

## 1) Install and launch Junip3R

Install Junip3R (portable ZIP or Python package), then start the app.

- See: [Installation](Installation.md)

## 2) Create a project

On the welcome screen, click **Create a new project**.

- Pick `Empty`, set a **Location**, and choose **YOLO Pose Estimation** as the **Mode**.
- Click **OK** - this opens the Setup window.
- Add an instance type and give it a few keypoints (and a bounding box, if you want
  one) - see [Project Setup](Project%20Setup.md#the-setup-window) for every option
  (colors, skeleton lines, expected instances per image, previewing your layout).

Already have a similar project? Pick **Use Project as Template...** or a saved template
instead of `Empty`, to start from an existing config rather than from scratch.

## 3) Get images into the project

### Path A: Extract frames from video

1. From the Setup window, click **Add Video Frames**.
2. Click **Add Videos**, then select frames manually or automatically.
3. Click **Extract Frames**.
4. Click **Start Labelling**.

- See: [Frame Extraction](Frame%20Extraction.md)

### Path B: Use images you already have

1. Copy your image files into the project's `images` folder yourself.
2. From the Setup window, use **Window -> Start Labelling** to go straight to
   labelling, skipping Frame Extractor.

## 4) Label your data

- Click on the image to place a keypoint (or the two corners of a bounding box).
- Navigate between images with **Next**/**Previous**, the arrow keys, or the slider.
- Everything saves automatically to `labels` as you go.

- See: [Labelling Workflow](Labelling%20Workflow.md) for the rest of the interactions
  (dragging, deleting, undo/redo, changing an instance's type, and more).

## 5) Export

In the Labeller: **File -> Export as... -> Export as YOLO Dataset**.

- See: [Exporting](YOLO%20Export.md)

## Where to go next

- Common issues: [Troubleshooting](Troubleshooting.md)
