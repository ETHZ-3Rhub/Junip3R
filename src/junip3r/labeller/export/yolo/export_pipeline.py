from dataclasses import dataclass, replace
from typing import List, Mapping

from junip3r.common.tags.data import TagValue
from junip3r.labeller.config.data import InstanceType
from junip3r.labeller.export.yolo.conversion.mapping_instance_converter import (
    MappingYoloDatasetGenerator,
    MappingYoloDatasetMetadataGenerator,
    MappingYoloPoseInstanceConverter,
    build_instance_type_mapping,
)
from junip3r.labeller.export.yolo.data import YoloDataset, YoloDatasetConfig, YoloDatasetMetadata, YoloImage
from junip3r.labeller.export.yolo.export_profile import ExportProfile
from junip3r.labeller.export.yolo.set_split import SetSplitConfig, resolve_set_assignments
from junip3r.labeller.model.abc import IReadOnlyAppModel


@dataclass
class TaggedImage:
    name: str
    tags: Mapping[str, TagValue]


def selected_instance_types(profile: ExportProfile, model: IReadOnlyAppModel) -> List[InstanceType]:
    names = set(profile.instance_type_names)
    return [it for it in model.get_instance_types(0) if it.name in names]


def included_image_indices(profile: ExportProfile, model: IReadOnlyAppModel) -> List[int]:
    indices = range(model.get_num_images())
    if profile.include_empty_images:
        return list(indices)

    names = {it.name for it in selected_instance_types(profile, model)}
    return [
        image_index for image_index in indices
        if any(instance.instance_type.name in names for instance in model.get_instances(image_index))
    ]


def tagged_images(profile: ExportProfile, model: IReadOnlyAppModel) -> List[TaggedImage]:
    return [
        TaggedImage(model.get_image_name(image_index), model.get_tags(image_index))
        for image_index in included_image_indices(profile, model)
    ]


def generate_export_mapping(profile: ExportProfile, model: IReadOnlyAppModel) -> YoloDatasetConfig:
    """ExportProfile + model -> the per-instance-type export mapping."""
    types = selected_instance_types(profile, model)
    instance_types = {
        instance_type.name: build_instance_type_mapping(instance_type, index, profile.mode)
        for index, instance_type in enumerate(types)
    }
    return YoloDatasetConfig(class_names=[it.name for it in types], instance_types=instance_types)


def build_yolo_dataset(mapping: YoloDatasetConfig, model: IReadOnlyAppModel,
                        profile: ExportProfile, set_split: SetSplitConfig) -> YoloDataset:
    """mapping + model (+ profile/set split, to decide which images are included and
    which set each lands in) -> the actual exported dataset. Everything here only reads
    label data and image *paths* - never pixel bytes unless there's no backing file to
    point at instead (see YoloImage construction below) - so this is safe to run
    synchronously; only the writer that consumes this needs to run off-thread.
    """
    instance_converter = MappingYoloPoseInstanceConverter(mapping)
    selected_names = set(mapping.class_names)
    set_assignments = resolve_set_assignments(tagged_images(profile, model), set_split)

    yolo_images = []
    for image_index in included_image_indices(profile, model):
        image_name = model.get_image_name(image_index)
        set_name = set_assignments.get(image_name)
        if set_name is None:
            continue

        instances = [i for i in model.get_instances(image_index) if i.instance_type.name in selected_names]
        yolo_instances = instance_converter.convert(instances)

        source_file = model.get_image_file(image_index)
        image = model.get_image(image_index) if source_file is None else None
        yolo_image = YoloImage(name=image_name, instances=yolo_instances, image=image, source_file=source_file)
        yolo_images.append((set_name, yolo_image))

    return MappingYoloDatasetGenerator(mapping).generate(yolo_images)


def generate_export_metadata(profile: ExportProfile, model: IReadOnlyAppModel,
                              mapping: YoloDatasetConfig, set_split: SetSplitConfig) -> YoloDatasetMetadata:
    """profile + model + mapping -> dataset metadata, with the set split bundled in so
    the export worker never needs anything beyond a YoloDataset + YoloDatasetMetadata.
    """
    metadata = MappingYoloDatasetMetadataGenerator(mapping).generate(selected_instance_types(profile, model))
    return replace(metadata, set_split=set_split)
