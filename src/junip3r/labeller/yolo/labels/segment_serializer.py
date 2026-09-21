import csv
from pathlib import Path
from typing import List, Sequence

from junip3r.labeller.yolo.labels.data import YoloSegmentInstance


class YoloSegmentLabelSerializer:
    """Reads/writes a single YOLO segmentation label .txt file - one instance per line:

        class_index x1 y1 x2 y2 ... xn yn  (n >= 3)

    Kept separate from YoloLabelSerializer rather than folded into it - a segmentation
    instance has no box and a variable-length polygon instead of fixed keypoint slots,
    so there's no shared shape or configuration (like keypoint_dims) to unify around.
    """

    def read(self, label_file: Path) -> List[YoloSegmentInstance]:
        instances: List[YoloSegmentInstance] = []
        for line in label_file.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            instances.append(self._read_line(line.split()))
        return instances

    def write(self, label_file: Path, instances: Sequence[YoloSegmentInstance]) -> None:
        with open(label_file, "w", newline="") as f:
            writer = csv.writer(f, delimiter=" ")
            for instance in instances:
                assert len(instance.polygon) >= 3, "A YOLO segmentation polygon needs at least 3 points"
                polygon_values = [value for point in instance.polygon for value in point]
                writer.writerow([instance.class_index, *polygon_values])

    def _read_line(self, tokens: Sequence[str]) -> YoloSegmentInstance:
        class_index = int(tokens[0])
        values = [float(t) for t in tokens[1:]]
        polygon = [(values[i], values[i + 1]) for i in range(0, len(values), 2)]
        return YoloSegmentInstance(class_index, polygon)
