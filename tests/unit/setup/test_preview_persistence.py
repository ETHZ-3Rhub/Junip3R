import cv2
import numpy as np

from junip3r.labeller.config.data import InstanceType, MemberSpecs, SkeletonSpecs
from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.setup.preview.data.repository.preview_persistence import PreviewPersistenceRepository


def _instance():
    instance_type = InstanceType(
        "mouse", [MemberSpecs("nose", LabellerObjectType.KEYPOINT, (255, 0, 0))], SkeletonSpecs([], (0, 0, 0))
    )
    instance = instance_type.new_instance("i1", "Mouse 1")
    return instance.replace_member(0, instance.members[0].with_p((0.5, 0.5)))


def test_save_writes_image_and_labels(tmp_path):
    repository = PreviewPersistenceRepository(tmp_path / "preview")
    image = np.zeros((2, 2, 3), dtype=np.uint8)
    image[:, :] = (10, 20, 30)  # RGB

    repository.save(image, [_instance()])

    image_file = tmp_path / "preview" / "image.png"
    labels_file = tmp_path / "preview" / "labels.json"
    assert image_file.exists()
    assert labels_file.exists()

    saved_bgr = cv2.imread(str(image_file))
    saved_rgb = cv2.cvtColor(saved_bgr, cv2.COLOR_BGR2RGB)
    assert tuple(saved_rgb[0, 0]) == (10, 20, 30)


def test_save_with_no_image_skips_writing_an_image_file(tmp_path):
    repository = PreviewPersistenceRepository(tmp_path / "preview")

    repository.save(None, [])

    assert not (tmp_path / "preview" / "image.png").exists()


def test_save_with_no_instances_does_not_leave_a_stale_labels_file(tmp_path):
    repository = PreviewPersistenceRepository(tmp_path / "preview")
    repository.save(None, [_instance()])
    assert (tmp_path / "preview" / "labels.json").exists()

    repository.save(None, [])

    assert not (tmp_path / "preview" / "labels.json").exists()
