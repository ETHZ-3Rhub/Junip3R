from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class YoloDataYaml:
    # Training images: an image directory, a .txt file of image paths, or a list of either.
    train: Union[str, List[str]]
    # Validation images, same forms as train.
    val: Union[str, List[str]]
    # Dataset root. Relative paths (including train/val/test below) resolve relative to
    # this file's location, with Ultralytics falling back to its own dataset directory.
    path: Optional[str] = None
    # Test images, same forms as train.
    test: Optional[Union[str, List[str]]] = None

    # Class names, by index.
    names: Optional[Union[List[str], Dict[int, str]]] = None
    # Number of classes. When names is also given, their counts must agree.
    nc: Optional[int] = None
    # Number of image channels (3 = RGB, 1 = grayscale).
    channels: Optional[int] = 3

    # [num_keypoints, dims_per_keypoint] for pose datasets.
    kpt_shape: Optional[List[int]] = None
    # Per-keypoint index to swap with under a horizontal flip (pose datasets).
    flip_idx: Optional[List[int]] = None
    # Per-class keypoint names, by class index (pose datasets).
    kpt_names: Optional[Dict[int, List[str]]] = None
    # Per-keypoint OKS sigma, used for pose evaluation.
    kpt_oks_sigmas: Optional[List[float]] = None

    # Any other top-level keys, preserved as-is for round-tripping - notably "download",
    # and segmentation ("masks_dir", "label_mapping") and depth ("depth_scale",
    # "max_depth") datasets' keys, none of which we support as a typed field. See
    # YoloDataYamlSerializer, which is what actually splits/merges these two.
    extras: Dict[str, Any] = field(default_factory=dict)
