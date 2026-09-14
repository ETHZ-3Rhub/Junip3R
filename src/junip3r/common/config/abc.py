from enum import Enum, auto


class ConfigMode(Enum):
    FREEFORM = auto()
    YOLO_DETECT = auto()
    YOLO_POSE = auto()
