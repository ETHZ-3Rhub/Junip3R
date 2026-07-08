# Frame extraction

Use Frame Extractor to choose and extract frames from videos into your project.

## Before you start

- A project only needs a `config.yaml` file.
- If you already have images, you can skip frame extraction:
  - Create an `images` folder next to `config.yaml`.
  - Copy image files into `images`.

When you run `Junip3R` and select a `config.yaml` file, the frame extractor opens automatically if no images are found in `images`.

## Add videos

You can add videos in two ways:

- Drag and drop video files into the app.
- Click **Add Videos** and select files in the file explorer.

## Select frames

Frames can be selected manually or automatically.

### Manual selection

1. Double-click a video in the video list to open it in the center player.
2. Navigate with play/pause, the seek bar, or frame-by-frame arrow buttons.
3. Click **Select Frame** to add the currently displayed frame.

### Automatic selection

In the frame selection menu (under the video list), choose:

- **Strategy**: `random` or `kmeans`
- **How many frames** to select
- **Selection mode**:
  - total across videos
  - per video
- **Video scope**:
  - all videos
  - currently displayed videos
  - videos selected in the video list

Click **Select Frames** to run the selection.

#### Random strategy

- **n total frames**: selects `n` frames from all frames across all included videos.
  - Every frame has equal probability, even when video lengths differ.
- **n per video**: selects `n` frames randomly, from each included video.

#### KMeans strategy
For selecting frames that are as diverse as possible

- **n total frames**:
  - Runs KMeans with `n` clusters on all frames from all included videos.
  - Frames are downscaled to `8x8` for clustering.
  - Selects the `n` frames closest to the cluster centroids.
- **n per video**:
  - Runs KMeans with `n` clusters separately for each included video.

## Extract selected frames

After selecting frames, use the frame extraction menu (under the frame list) to choose what to extract:

- **New frames**
  - Extracts only frames that have not been extracted before.
- **All frames**
  - Extracts all frames, even if they have been extracted before, replacing existing files.
- **Frames selected in the frame list**
  - Extracts only the frames that are selected in the frame list.

You can also enable context clip extraction and set the context length in seconds on both sides of each frame.

- Example: `2s` context creates a `4s` clip (`2s` before + `2s` after).

Click **Extract Frames** to export.

## Output locations

- Extracted frames are saved to `images` (next to `config.yaml`).
- Context clips are saved to `context`.

