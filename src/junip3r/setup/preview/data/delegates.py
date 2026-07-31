import uuid
from dataclasses import dataclass, field
from junip3r.labeller.data.types.delegates import Keypoint, BoundingBox, Polygon, Polyline, Instance


@dataclass
class SetupPreviewKeypoint(Keypoint):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class SetupPreviewBoundingBox(BoundingBox):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class SetupPreviewPolygon(Polygon):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class SetupPreviewPolyline(Polyline):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class SetupPreviewInstance(Instance):
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
