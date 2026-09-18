import csv
from pathlib import Path
from typing import List, Sequence

from junip3r.labeller.yolo.labels.data import YoloBoxInstance, YoloKeypoint


class YoloLabelSerializer:
    """Reads/writes a single YOLO detect/pose label .txt file - one instance per line:

        class_index cx cy w h  [x y (v)]*num_keypoints

    A detect-only file simply has no trailing keypoint tokens, which
    YoloBoxInstance.keypoints=() represents directly, so the same read/write path
    handles both - there's no separate "task" switch. keypoint_dims (2, without
    visibility, or 3, with) only matters for a line that does have keypoint tokens - a
    YoloKeypoint is always a full (x, y, visibility) triple regardless, since a missing
    visibility channel on disk means "labeled and visible" (see YoloKeypoint), not
    "unknown" - keypoint_dims just controls how many of its 3 values get written out.

    This is otherwise a pure format reader/writer - it writes whatever coordinates a
    YoloBoxInstance's keypoints already contain (e.g. zeroing an invisible keypoint, if
    wanted, is the caller's decision, not this class's).
    """

    def __init__(self, keypoint_dims: int = 3):
        if keypoint_dims not in (2, 3):
            raise ValueError(f"keypoint_dims must be 2 or 3, got {keypoint_dims}")
        self._keypoint_dims = keypoint_dims

    def read(self, label_file: Path) -> List[YoloBoxInstance]:
        instances: List[YoloBoxInstance] = []
        for line in label_file.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            instances.append(self._read_line(line.split()))
        return instances

    def write(self, label_file: Path, instances: Sequence[YoloBoxInstance]) -> None:
        assert _all_same_keypoint_count(instances), "All instances must have the same number of keypoints"

        with open(label_file, "w", newline="") as f:
            writer = csv.writer(f, delimiter=" ")
            for instance in instances:
                keypoint_values = [
                    value
                    for keypoint in instance.keypoints
                    for value in keypoint[:self._keypoint_dims]
                ]
                writer.writerow([instance.class_index, *instance.box, *keypoint_values])

    def _read_line(self, tokens: Sequence[str]) -> YoloBoxInstance:
        class_index = int(tokens[0])
        cx, cy, w, h = (float(t) for t in tokens[1:5])

        values = [float(t) for t in tokens[5:]]
        dims = self._keypoint_dims
        keypoints = [self._to_keypoint(values[i:i + dims]) for i in range(0, len(values), dims)]

        return YoloBoxInstance(class_index, (cx, cy, w, h), keypoints)

    def _to_keypoint(self, values: Sequence[float]) -> YoloKeypoint:
        if self._keypoint_dims == 2:
            return values[0], values[1], 2.0
        return values[0], values[1], values[2]


def _all_same_keypoint_count(instances: Sequence[YoloBoxInstance]) -> bool:
    if not instances:
        return True
    count = len(instances[0].keypoints)
    return all(len(instance.keypoints) == count for instance in instances)
