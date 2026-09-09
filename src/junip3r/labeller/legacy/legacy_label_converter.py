from pathlib import Path
from typing import Sequence

from junip3r.common.labels.legacy import LegacyLabelLoader, InstanceType as LegacyInstanceType
from junip3r.common.labels.serialization import LabelSerializer
from junip3r.labeller.config.data import InstanceType
from junip3r.labeller.data.types.abc import LabellerObjectType


class LegacyLabelConverter:
    def __init__(self, instance_types: Sequence[InstanceType]):
        legacy_instance_types = []
        for instance_type in instance_types:
            name = instance_type.name
            bounding_box_type = "automatic"
            keypoint_names = []
            for member_specs in instance_type.members:
                if member_specs.type == LabellerObjectType.BOUNDING_BOX:
                    bounding_box_type = "manual"
                elif member_specs.type == LabellerObjectType.KEYPOINT:
                    keypoint_names.append(member_specs.name)
            legacy_instance_types.append(LegacyInstanceType(name, bounding_box_type, keypoint_names))

        self._legacy_loader = LegacyLabelLoader(legacy_instance_types)
        self._label_loader = LabelSerializer()

    def convert_legacy_labels(self, label_file: Path, new_label_file: Path) -> Path:
        instances = self._legacy_loader.load_instances(label_file)
        self._label_loader.write_instances(new_label_file, instances)
        return new_label_file
