# Quick start

This page walks through the fastest path from installation to labelled data.

## 1) Install and launch Junip3R

Install Junip3R (portable ZIP or Python package), then start the app.

- See: [Installation](Installation.md)

## 2) Create a new project folder

1. Create an empty folder for your project.
2. Add a `config.yaml` file with at least one instance type and point list.

- See: [Project Setup](Project%20setup.md)
- Example config files: [`docs/Examples/minimal_config.yaml`](../Examples/minimal_config.yaml), [`docs/Examples/advanced_config.yaml`](../Examples/advanced_config.yaml)

## 3) Open the project

Start Junip3R and select your `config.yaml` file.

- If `images` already contains image files, the Labeller opens directly.
- If no images are present, Frame Extractor opens.

## 4) Add images (two common paths)

### Path A: Extract from videos in Frame Extractor

1. Add videos.
2. Select frames manually or automatically.
3. Click **Extract Frames**.
4. Click **Start Labelling**.

- See: [Frame extraction](Frame%20extraction.md)

### Path B: Use existing images

1. Create an `images` folder next to `config.yaml`.
2. Copy your image files into `images`.
3. Open `config.yaml` in Junip3R.

## 5) Label your data

1. Place points and bounding boxes.
2. Navigate through images and continue labelling.
3. Changes are saved automatically to `labels` as JSON.

- See: [Labelling workflow](Labelling%20workflow.md)

## 6) Export

When labelling is complete, export in your target format.

- See: [Exporting](YOLO Export.md)

## Where to go next

- Common issues: [Troubleshooting](Troubleshooting.md)
