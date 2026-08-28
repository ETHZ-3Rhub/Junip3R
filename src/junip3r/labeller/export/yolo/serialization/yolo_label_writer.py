import csv
from _csv import Writer
from pathlib import Path
from typing import Sequence

from junip3r.labeller.export.yolo.data import YoloPoseInstance


class YOLOPoseLabelWriter:
    @classmethod
    def write_instances(cls, label_file: Path, instances: Sequence[YoloPoseInstance]):
        assert _all_instances_same_num_keypoints(instances), "All instances must have the same number of keypoints"

        with open(label_file, 'w', newline='') as f:
            writer = csv.writer(f, delimiter=' ')
            for instance in instances:
                cls.write_pose_instance(writer, instance)

    @classmethod
    def write_pose_instance(cls, writer: Writer, instance: YoloPoseInstance) -> None:
        box = list(instance.box)

        keypoint_values = []
        for keypoint in instance.keypoints:
            if keypoint is None or keypoint[2] < 0.5:
                keypoint = (0., 0., 0.)
            keypoint_values.extend(keypoint)

        writer.writerow([instance.class_index] + box + keypoint_values)


def _all_instances_same_num_keypoints(instances: Sequence[YoloPoseInstance]) -> bool:
    if not instances:
        return True
    num_keypoints = len(instances[0].keypoints)
    return all(len(i.keypoints) == num_keypoints for i in instances)
