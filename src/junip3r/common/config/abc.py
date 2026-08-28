from enum import Enum, auto


class ConfigMode(Enum):
    JUNIPER = auto()
    YOLO_DETECT = auto()
    YOLO_POSE = auto()
