from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Sequence, Mapping, Tuple, Optional, Protocol

import numpy as np

from junip3r.labeller.data.types.abc import Color
from junip3r.labeller.yolo.labels.data import YoloBoxInstance


class ExportMode(Enum):
    POSE = auto()
    DETECT = auto()


class IYoloImage(Protocol):
    """An exported image; pixels may come from a backing file, from memory, or both."""
    @property
    def name(self) -> str: ...
    @property
    def instances(self) -> Sequence[YoloBoxInstance]: ...
    @property
    def image(self) -> Optional[np.ndarray]: ...
    @property
    def source_file(self) -> Optional[Path]:
        """The file this image's pixels were loaded from, if any.

        Writers may copy this file directly instead of reading `image` and re-encoding it,
        which is faster and avoids lossy re-compression. At least one of `source_file` and
        `image` must be set.
        """
        ...


@dataclass
class YoloImage:
    name: str
    instances: Sequence[YoloBoxInstance]
    image: Optional[np.ndarray] = None
    source_file: Optional[Path] = None


@dataclass
class YoloPoseInstanceTypeConfig:
    class_index: int
    # Tight box around these members' own bounds - a Keypoint contributes its single
    # point, a BoundingBox contributes its own two corners. A single explicit
    # bounding-box member is just the N=1 case of the same computation (the tight box
    # around one box's own corners is that box). Empty = no box.
    bounding_box_members: Sequence[str] = field(default_factory=tuple)
    keypoints: Mapping[str, int] = field(default_factory=dict)


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
    color: Optional[Color] = None


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
