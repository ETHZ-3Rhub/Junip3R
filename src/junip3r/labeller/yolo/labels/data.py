from dataclasses import dataclass, field
from typing import Sequence, Tuple

YoloBox = Tuple[float, float, float, float]  # cx, cy, w, h
YoloPoint = Tuple[float, float]  # x, y
# x, y, visibility (0 = not labeled, 1 = labeled but not visible, 2 = labeled and
# visible). A 2-value data.yaml (kpt_shape[1] == 2) has no visibility channel on disk
# at all - Ultralytics defines that as "every keypoint is labeled and visible", not
# "visibility unknown" - so YoloLabelSerializer always fills it in as 2.0 on read, and
# a keypoint here is always a full triple regardless of keypoint_dims.
YoloKeypoint = Tuple[float, float, float]


@dataclass
class YoloBoxInstance:
    class_index: int
    box: YoloBox
    # Empty for a detect-only dataset - the two are otherwise the same format, so
    # there's no separate "detect" type: a detect instance is just a YoloBoxInstance
    # with no keypoints.
    keypoints: Sequence[YoloKeypoint] = field(default_factory=list)


@dataclass
class YoloSegmentInstance:
    class_index: int
    # Normalized (x, y) polygon vertices, at least 3.
    polygon: Sequence[YoloPoint]
