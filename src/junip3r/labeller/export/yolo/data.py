from dataclasses import dataclass, field
from typing import Sequence, Mapping, Tuple, Optional, Protocol, Callable

import numpy as np

from junip3r.labeller.data.types.abc import Color

YoloBox = Tuple[float, float, float, float]  # cx, cy, w, h
YoloKeypoint = Tuple[float, float, float]  # x, y, visibility


@dataclass
class YoloPoseInstance:
    class_index: int
    box: YoloBox
    keypoints: Sequence[YoloKeypoint]


class IYoloImage(Protocol):
    """An exported image; pixels may be held in memory or loaded lazily from disk."""
    @property
    def name(self) -> str: ...
    @property
    def image(self) -> np.ndarray: ...
    @property
    def instances(self) -> Sequence[YoloPoseInstance]: ...


@dataclass
class YoloImage:
    name: str
    image: np.ndarray
    instances: Sequence[YoloPoseInstance]


@dataclass
class LazyYoloImage:
    name: str
    load: Callable[[], np.ndarray]
    instances: Sequence[YoloPoseInstance]

    @property
    def image(self) -> np.ndarray:
        return self.load()


@dataclass
class YoloPoseInstanceTypeConfig:
    class_index: int
    bounding_box: Optional[str]
    keypoints: Mapping[str, int]


@dataclass
class YoloDatasetConfig:
    class_names: Sequence[str]
    instance_types: Mapping[str, YoloPoseInstanceTypeConfig]

    @property
    def num_keypoints(self) -> int:
        return max(
            (output_index + 1
             for instance_type in self.instance_types.values()
             for output_index in instance_type.keypoints.values()),
            default=0,
        )


@dataclass
class YoloKeypointType:
    name: str
    color: Optional[Color] = None
    mirror_h_keypoint_name: Optional[str] = None
    mirror_v_keypoint_name: Optional[str] = None


@dataclass
class YoloPoseInstanceType:
    name: str
    description: str = ""
    keypoints: Sequence[YoloKeypointType] = field(default_factory=tuple)
    skeleton: Sequence[Tuple[str, str]] = field(default_factory=tuple)
    automatic_bounding_box: bool = False
    bounding_box_color: Optional[Color] = None


@dataclass
class YoloDatasetMetadata:
    instance_types: Sequence[YoloPoseInstanceType]
    output_mapping: Sequence[Tuple[str, str, int]]


@dataclass
class YoloDataset:
    sets: Sequence[Tuple[str, Sequence[IYoloImage]]] = ()
    class_names: Sequence[str] = ()
    num_keypoints: int = 0
    flip_h_idx: Optional[Sequence[int]] = None
    flip_v_idx: Optional[Sequence[int]] = None
