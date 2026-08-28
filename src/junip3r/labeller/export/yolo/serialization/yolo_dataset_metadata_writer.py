from pathlib import Path
from typing import Dict, Any

import yaml

from junip3r.labeller.data.types.abc import Color
from junip3r.labeller.export.yolo.data import YoloPoseInstanceType, YoloDatasetMetadata


def _color_to_hex(color: Color) -> str:
    """Convert a Color object to a hex string."""
    return "#{:02x}{:02x}{:02x}".format(*color)


class YoloPoseInstanceTypeSerializer:
    @classmethod
    def serialize(cls, instance_type: YoloPoseInstanceType) -> Dict[str, Any]:
        instance_dict: Dict[str, Any] = {"name": instance_type.name, "description": instance_type.description}

        bounding_box_mode = "automatic" if instance_type.automatic_bounding_box else "manual"
        bounding_box_color = instance_type.bounding_box_color
        if bounding_box_color is not None:
            instance_dict["bounding_box"] = {"mode": bounding_box_mode, "color": _color_to_hex(bounding_box_color)}
        else:
            instance_dict["bounding_box"] = bounding_box_mode

        keypoints = []
        for member in instance_type.keypoints:
            keypoint_dict = {"name": member.name, "mirror_h": member.mirror_h_keypoint_name, "mirror_v": member.mirror_v_keypoint_name}
            color = member.color

            if color is not None:
                keypoint_dict["color"] = _color_to_hex(color)

            keypoints.append(keypoint_dict)

        instance_dict["keypoints"] = keypoints
        instance_dict["skeleton"] = instance_type.skeleton

        return instance_dict


class YoloPoseDatasetMetadataWriter:
    def write(self, target_folder: Path, metadata: YoloDatasetMetadata):
        metadata_folder = target_folder / "meta"
        metadata_folder.mkdir(parents=True, exist_ok=True)

        instance_types_folder = metadata_folder / "instance_types"
        instance_types_folder.mkdir(parents=True, exist_ok=True)

        for instance_type in metadata.instance_types:
            instance_type_file = instance_types_folder / f"{instance_type.name}.yaml"
            instance_type_data = YoloPoseInstanceTypeSerializer.serialize(instance_type)

            with instance_type_file.open("w") as f:
                yaml.dump(instance_type_data, f)

        output_mapping_file = metadata_folder / "output_mapping.csv"
        with output_mapping_file.open("w") as f:
            for instance_name, point_name, output_index in metadata.output_mapping:
                f.write(f"{instance_name},{point_name},{output_index}\n")
