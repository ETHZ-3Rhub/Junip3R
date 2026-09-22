"""Human-in-the-loop labelling prototype: run a trained YoloPoseModel (py3r.pose.yolo)
on the current image and turn its output into labeller Instances by matching instance
type / keypoint names. Quick and dirty on purpose - hardcoded model path, no UI to
configure it, no error handling beyond "skip what doesn't match". See Editor's
act_run_pose_model for the keyboard shortcut that triggers this.
"""
import uuid
from pathlib import Path
from typing import List, Optional, Sequence

import cv2
import numpy as np
from py3r.pose.core.types import PoseInstance
from py3r.pose.yolo.model.yolo_pose_model import YoloPoseModel

from junip3r.labeller.config.data import InstanceType
from junip3r.labeller.data.types.data import BoundingBox, Instance, Keypoint, new_instance

# EDIT ME: point this at a model folder shaped like YoloPoseModel.from_folder expects
# (weights.pt or weights/best.pt, plus meta/instance_types/*.yaml and meta/output_mapping.csv).
MODEL_FOLDER = Path("D:/Experiments/UnifiedTrackingModel/ActualProperSplit/Cassandra_Mouse_V4X_Fixed")
DEVICE = "cuda"
POINT_CONFIDENCE_THRESHOLD = 0.5

_model: Optional[YoloPoseModel] = None


def _get_model() -> YoloPoseModel:
    global _model
    if _model is None:
        _model = YoloPoseModel.from_folder(MODEL_FOLDER, device=DEVICE)
    return _model


def _normalized_point(x: float, y: float, width: int, height: int):
    return x / width, y / height


def _to_labeller_instance(pose_instance: PoseInstance, instance_type: InstanceType, width: int, height: int) -> Instance:
    instance = new_instance(instance_type, str(uuid.uuid4()), pose_instance.id)

    point_by_name = dict(zip(pose_instance.type.point_names, pose_instance.points))

    x1, y1, x2, y2 = pose_instance.box
    box = (_normalized_point(x1, y1, width, height), _normalized_point(x2, y2, width, height))

    for member in instance.members:
        if isinstance(member, BoundingBox):
            instance = instance.replace_member(member.id, member.with_box(box))
        elif isinstance(member, Keypoint) and member.name in point_by_name:
            point = point_by_name[member.name]
            if point.conf is not None and point.conf < POINT_CONFIDENCE_THRESHOLD:
                continue
            p = _normalized_point(point.x, point.y, width, height)
            instance = instance.replace_member(member.id, member.with_p(p).with_visibility(2.0))

    return instance


def predict_instances(image: np.ndarray, instance_types: Sequence[InstanceType]) -> List[Instance]:
    """Run the pose model on `image` and map its output onto `instance_types` by name -
    both the instance type name and each keypoint's name have to match exactly. Anything
    the model predicts that doesn't match a known instance type is silently dropped.
    """
    model = _get_model()
    # The labeller keeps images as RGB arrays (see e.g. YoloDatasetWriter's own
    # cv2.cvtColor(..., COLOR_RGB2BGR) before writing) - the underlying Ultralytics
    # model expects BGR, same as cv2.imread's default.
    pose_instances = model.predict(cv2.cvtColor(image, cv2.COLOR_RGB2BGR))

    types_by_name = {instance_type.name: instance_type for instance_type in instance_types}
    height, width = image.shape[0], image.shape[1]

    instances = []
    for pose_instance in pose_instances:
        instance_type = types_by_name.get(pose_instance.type.name)
        if instance_type is None:
            continue
        instances.append(_to_labeller_instance(pose_instance, instance_type, width, height))

    return instances
