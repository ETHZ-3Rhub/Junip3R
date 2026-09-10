from pathlib import Path
from typing import List, Sequence, Optional

from junip3r.common.labels.data import Instance as DataInstance
from junip3r.common.labels.serialization import LabelSerializer
from junip3r.labeller.config.data import InstanceType
from junip3r.labeller.data.repository.abc import ILabelRepository, IConfigRepository


class SetupPreviewConfigRepository(IConfigRepository):
    def __init__(self):
        self._instance_types: List[InstanceType] = []
        self._expected_instances: List[InstanceType] = []

    def set_instance_types(self, image_index: int, instance_types: Sequence[InstanceType]) -> None:
        self._instance_types = list(instance_types)

    def set_expected_instances(self, image_index: int, expected_instances: Sequence[InstanceType]) -> None:
        self._expected_instances = list(expected_instances)

    def get_instance_types(self, image_index: int) -> List[InstanceType]:
        return self._instance_types

    def get_expected_instances(self, image_index: int) -> List[InstanceType]:
        return self._expected_instances

    def get_tag_names(self, image_index: int) -> List[str]:
        return []


class SetupPreviewLabelRepository(ILabelRepository):
    """Type-unaware DTO I/O, like JuniperLabelRepository (labeller/data/repository/
    label.py) - except the label file is a settable path rather than a constructor
    argument, since no project folder is known until SetupMainWindow.set_project_folder
    runs (see set_label_file).

    Resolving these DTOs against instance types is LabelModel's job, not this
    repository's. Reconciling already-placed instances against a changed config (since
    unlike a real project's, setup's config changes live, mid-session) is
    SetupPreviewPoseImageModel.set_config's job - see reconcile_instances in
    setup/model/setup_preview_pose_image_model.py.
    """

    def __init__(self):
        self._label_file: Optional[Path] = None
        self._loader = LabelSerializer()

    def set_label_file(self, label_file: Optional[Path]):
        self._label_file = label_file

    def get_instances(self, image_index: int) -> Sequence[DataInstance]:
        if self._label_file is None:
            return []
        return self._loader.load_instances(self._label_file)

    def set_instances(self, image_index: int, instances: Sequence[DataInstance]) -> None:
        if self._label_file is None:
            return
        self._loader.write_instances(self._label_file, list(instances))
