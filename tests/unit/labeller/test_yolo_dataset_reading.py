import numpy as np
import pytest
import yaml

from junip3r.common.config.abc import ConfigMode
from junip3r.labeller.data.yolo.config_repository import build_yolo_dataset_schema
from junip3r.labeller.data.yolo.discovery import discover_yolo_dataset_images, yolo_dataset_root
from junip3r.labeller.data.yolo.label_repository import parse_yolo_label_file
from junip3r.labeller.model.app_model import AppModel
from junip3r.labeller.model.label_model import LabelModel
from junip3r.labeller.yolo.config.yolo_dataset_config import YoloDatasetConfig


# --- discovery --------------------------------------------------------------------------

def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def test_yolo_dataset_root_resolves_relative_path(tmp_path):
    data_yaml = tmp_path / "sub" / "data.yaml"
    assert yolo_dataset_root(data_yaml, {}) == data_yaml.parent
    assert yolo_dataset_root(data_yaml, {"path": ".."}) == tmp_path


def test_discover_yolo_dataset_images_merges_sets_in_train_val_test_order(tmp_path):
    _touch(tmp_path / "images" / "train" / "b.jpg")
    _touch(tmp_path / "images" / "train" / "a.jpg")
    _touch(tmp_path / "labels" / "train" / "a.txt")
    _touch(tmp_path / "images" / "val" / "c.jpg")

    config = YoloDatasetConfig(train=[tmp_path / "images" / "train"], val=[tmp_path / "images" / "val"])
    images = discover_yolo_dataset_images(config)

    assert [i.image.name for i in images] == ["a.jpg", "b.jpg", "c.jpg"]
    assert images[0].label == tmp_path / "labels" / "train" / "a.txt"
    assert images[1].label is None  # no b.txt on disk
    assert images[2].label is None  # no labels/val dir at all


def test_discover_yolo_dataset_images_scans_directories_recursively(tmp_path):
    _touch(tmp_path / "images" / "train" / "sub" / "a.jpg")

    config = YoloDatasetConfig(train=[tmp_path / "images" / "train"], val=[])
    images = discover_yolo_dataset_images(config)

    assert [i.image for i in images] == [tmp_path / "images" / "train" / "sub" / "a.jpg"]


def test_discover_yolo_dataset_images_reads_paths_from_a_list_file(tmp_path):
    _touch(tmp_path / "images" / "train" / "a.jpg")
    list_file = tmp_path / "train.txt"
    list_file.write_text("./images/train/a.jpg\n")

    config = YoloDatasetConfig(train=[list_file], val=[])
    images = discover_yolo_dataset_images(config)

    assert [i.image for i in images] == [tmp_path / "images" / "train" / "a.jpg"]


def test_discover_yolo_dataset_images_raises_when_an_entry_does_not_exist(tmp_path):
    config = YoloDatasetConfig(train=[tmp_path / "images" / "train"], val=[])

    with pytest.raises(FileNotFoundError):
        discover_yolo_dataset_images(config)


def test_discover_yolo_dataset_images_allows_duplicate_stems_across_sets(tmp_path):
    # Nothing downstream keys images by name (they're addressed by list index), so a
    # stem appearing in more than one set is fine - both entries are just kept.
    _touch(tmp_path / "images" / "train" / "a.jpg")
    _touch(tmp_path / "images" / "val" / "a.jpg")

    config = YoloDatasetConfig(train=[tmp_path / "images" / "train"], val=[tmp_path / "images" / "val"])
    images = discover_yolo_dataset_images(config)

    assert [i.image for i in images] == [tmp_path / "images" / "train" / "a.jpg", tmp_path / "images" / "val" / "a.jpg"]


# --- config_repository: generic fallback -------------------------------------------------

def _dataset_config(**overrides):
    fields = dict(train=[], val=[])
    fields.update(overrides)
    return YoloDatasetConfig(**fields)


def test_generic_schema_builds_pose_instance_types_from_kpt_shape(tmp_path):
    config = _dataset_config(names={0: "mouse", 1: "cat"}, kpt_shape=[2, 3])
    schema = build_yolo_dataset_schema(tmp_path, config)

    assert schema.mode == ConfigMode.YOLO_POSE
    assert [it.name for it in schema.instance_types] == ["mouse", "cat"]

    mouse = schema.instance_types[0]
    assert [m.name for m in mouse.members] == ["Bounding Box", "kp_0", "kp_1"]
    assert schema.keypoint_output_indices["mouse"] == [0, 1]
    assert schema.class_index_to_instance_type[0] is mouse
    assert schema.class_index_to_instance_type[1] is schema.instance_types[1]


def test_generic_schema_without_kpt_shape_is_detect_mode(tmp_path):
    config = _dataset_config(names={0: "mouse"})
    schema = build_yolo_dataset_schema(tmp_path, config)

    assert schema.mode == ConfigMode.YOLO_DETECT
    assert [m.name for m in schema.instance_types[0].members] == ["mouse"]
    assert schema.keypoint_output_indices == {}


def test_generic_schema_uses_kpt_names_when_present(tmp_path):
    config = _dataset_config(
        names={0: "mouse", 1: "cat"},
        kpt_shape=[2, 3],
        kpt_names={0: ["nose", "tail"], 1: ["ear"]},  # cat's list deliberately wrong length
    )
    schema = build_yolo_dataset_schema(tmp_path, config)

    mouse, cat = schema.instance_types
    assert [m.name for m in mouse.members] == ["Bounding Box", "nose", "tail"]
    # Falls back to generic names when the given list doesn't match kpt_shape's count.
    assert [m.name for m in cat.members] == ["Bounding Box", "kp_0", "kp_1"]


# --- config_repository: rich (Junip3R-exported meta/) -------------------------------------

def _write_rich_meta(dataset_root):
    instance_types_dir = dataset_root / "meta" / "instance_types"
    instance_types_dir.mkdir(parents=True)
    with (instance_types_dir / "mouse.yaml").open("w") as f:
        yaml.dump({
            "name": "mouse",
            "description": "",
            "bounding_box": {"mode": "manual", "color": "#ff0000"},
            "keypoints": [
                {"name": "nose", "mirror_h": None, "mirror_v": None, "color": "#00ff00"},
                {"name": "tail", "mirror_h": None, "mirror_v": None},
            ],
            "skeleton": [["nose", "tail"]],
        }, f)

    with (dataset_root / "meta" / "output_mapping.csv").open("w") as f:
        f.write("mouse,nose,0\nmouse,tail,1\n")


def test_rich_schema_reconstructs_names_colors_and_skeleton(tmp_path):
    _write_rich_meta(tmp_path)
    config = _dataset_config(names={0: "mouse"})

    schema = build_yolo_dataset_schema(tmp_path, config)

    assert schema.mode == ConfigMode.YOLO_POSE
    mouse = schema.instance_types[0]
    bbox, nose, tail = mouse.members
    assert (bbox.name, bbox.color) == ("Bounding Box", (255, 0, 0))
    assert (nose.name, nose.color) == ("nose", (0, 255, 0))
    assert tail.name == "tail"
    assert schema.keypoint_output_indices["mouse"] == [0, 1]

    name_to_id = {m.name: m.id for m in mouse.members}
    assert mouse.skeleton.lines == [(name_to_id["nose"], name_to_id["tail"])]


def test_rich_schema_falls_back_to_generic_when_meta_is_incomplete(tmp_path):
    config = _dataset_config(names={0: "mouse", 1: "cat"}, kpt_shape=[0, 3])
    _write_rich_meta(tmp_path)  # only covers "mouse", not "cat"

    schema = build_yolo_dataset_schema(tmp_path, config)

    # Falls back to the fully generic reading, so "cat" doesn't need its own meta file.
    assert schema.mode == ConfigMode.YOLO_DETECT
    assert [it.name for it in schema.instance_types] == ["mouse", "cat"]


# --- label_repository ---------------------------------------------------------------------

def test_parse_yolo_label_file_maps_box_and_keypoints(tmp_path):
    config = _dataset_config(names={0: "mouse"}, kpt_shape=[2, 3])
    schema = build_yolo_dataset_schema(tmp_path, config)

    label_file = tmp_path / "a.txt"
    label_file.write_text("0 0.5 0.5 0.2 0.4 0.3 0.3 1.0 0.0 0.0 0.0\n")

    instances = parse_yolo_label_file(label_file, schema)

    assert len(instances) == 1
    instance = instances[0]
    assert instance.type == "mouse"
    assert instance.name == "mouse 1"

    bbox, kp0, kp1 = instance.members
    (min_x, min_y), (max_x, max_y) = bbox.box
    assert (min_x, min_y, max_x, max_y) == pytest.approx((0.4, 0.3, 0.6, 0.7))
    assert kp0.p == pytest.approx((0.3, 0.3))
    assert kp0.visibility == 1.0
    assert kp1.p is None  # visibility below 0.5 -> treated as unset


def test_parse_yolo_label_file_produces_stable_ids_across_repeated_calls(tmp_path):
    # LabelModel is stateless and re-parses on every read (see its docstring) - if ids
    # were regenerated each call, PoseImageModel's selection would silently stop
    # matching any instance moments after being set, since it's keyed by instance id.
    config = _dataset_config(names={0: "mouse"})
    schema = build_yolo_dataset_schema(tmp_path, config)

    label_file = tmp_path / "a.txt"
    label_file.write_text("0 0.1 0.1 0.1 0.1\n0 0.2 0.2 0.1 0.1\n")

    first = parse_yolo_label_file(label_file, schema)
    second = parse_yolo_label_file(label_file, schema)

    assert [i.id for i in first] == [i.id for i in second]


def test_parse_yolo_label_file_skips_blank_lines_and_numbers_repeated_types(tmp_path):
    config = _dataset_config(names={0: "mouse"})
    schema = build_yolo_dataset_schema(tmp_path, config)

    label_file = tmp_path / "a.txt"
    label_file.write_text("0 0.1 0.1 0.1 0.1\n\n0 0.2 0.2 0.1 0.1\n")

    instances = parse_yolo_label_file(label_file, schema)

    assert [i.name for i in instances] == ["mouse 1", "mouse 2"]


def test_yolo_label_repository_set_instances_is_read_only(tmp_path):
    from junip3r.labeller.data.yolo.label_repository import YoloLabelRepository

    config = _dataset_config(names={0: "mouse"})
    schema = build_yolo_dataset_schema(tmp_path, config)
    repository = YoloLabelRepository([None], schema)

    assert repository.get_instances(0) == []
    with pytest.raises(NotImplementedError):
        repository.set_instances(0, [])


# --- end-to-end: config + label repositories wired through LabelModel/AppModel ------------

class _FakeImageRepository:
    def get_num_images(self):
        return 1

    def get_image(self, image_index):
        return np.zeros((1, 1, 3), dtype=np.uint8)

    def get_image_name(self, image_index):
        return "a"

    def get_image_file(self, image_index):
        return None


class _FakeSelectionRepository:
    def __init__(self):
        self._selection = None

    def get_selection(self, image_index):
        return self._selection

    def set_selection(self, image_index, selection):
        self._selection = selection

    def get_new_instance_type(self, image_index):
        return None

    def set_new_instance_type(self, image_index, instance_type):
        pass


def test_yolo_repositories_produce_resolved_instances_through_app_model(tmp_path):
    from junip3r.labeller.data.yolo.config_repository import YoloConfigRepository
    from junip3r.labeller.data.yolo.label_repository import YoloLabelRepository

    config = _dataset_config(names={0: "mouse"}, kpt_shape=[1, 3])
    schema = build_yolo_dataset_schema(tmp_path, config)

    label_file = tmp_path / "a.txt"
    label_file.write_text("0 0.5 0.5 0.2 0.2 0.5 0.5 2.0\n")

    label_model = LabelModel(YoloConfigRepository(schema), YoloLabelRepository([label_file], schema))
    app_model = AppModel(_FakeImageRepository(), label_model, _FakeSelectionRepository())

    instances = app_model.get_instances(0)

    assert len(instances) == 1
    assert instances[0].instance_type.name == "mouse"
    assert instances[0].members[0].box is not None
    assert instances[0].members[1].p == pytest.approx((0.5, 0.5))


def test_selection_survives_repeated_image_state_recomputation(tmp_path):
    # Reproduces the read-only viewer's real failure mode: PoseImageModel.__init__
    # selects the first instance off one get_instances() call, then get_selected_instance
    # re-resolves it off a second, independent call - if YoloLabelRepository generated a
    # fresh id each parse, this lookup would silently return None (empty member list).
    from junip3r.labeller.data.yolo.config_repository import YoloConfigRepository
    from junip3r.labeller.data.yolo.label_repository import YoloLabelRepository
    from junip3r.labeller.model.pose_image_model import PoseImageModel

    config = _dataset_config(names={0: "mouse"})
    schema = build_yolo_dataset_schema(tmp_path, config)
    label_file = tmp_path / "a.txt"
    label_file.write_text("0 0.5 0.5 0.2 0.2\n")

    label_model = LabelModel(YoloConfigRepository(schema), YoloLabelRepository([label_file], schema))
    app_model = AppModel(_FakeImageRepository(), label_model, _FakeSelectionRepository())

    model = PoseImageModel(app_model, read_only=True)

    selected = model.get_selected_instance()
    assert selected is not None
    assert selected.instance_type.name == "mouse"


def test_round_trips_a_real_junip3r_exported_dataset(tmp_path):
    from junip3r.labeller.config.data import InstanceType, MemberType, SkeletonType
    from junip3r.labeller.data.types.abc import LabellerObjectType
    from junip3r.labeller.export.yolo.conversion.mapping_instance_converter import MappingYoloDatasetMetadataGenerator
    from junip3r.labeller.export.yolo.data import (
        YoloDataset, YoloDatasetConfig, YoloImage, YoloPoseInstance, YoloPoseInstanceTypeConfig,
    )
    from junip3r.labeller.export.yolo.serialization.yolo_dataset_metadata_writer import YoloPoseDatasetMetadataWriter
    from junip3r.labeller.export.yolo.serialization.yolo_dataset_writer import YoloDatasetWriter
    from junip3r.labeller.yolo.config.yolo_dataset_config import resolve_yolo_data_yaml
    from junip3r.labeller.yolo.data_yaml.serializer import YoloDataYamlSerializer

    config = YoloDatasetConfig(
        class_names=["mouse"],
        instance_types={"mouse": YoloPoseInstanceTypeConfig(class_index=0, bounding_box="Bounding Box", keypoints={"nose": 0, "tail": 1})},
    )
    instance_type = InstanceType(
        name="mouse",
        members=[
            MemberType(name="Bounding Box", type=LabellerObjectType.BOUNDING_BOX, color=(255, 0, 0)),
            MemberType(name="nose", type=LabellerObjectType.KEYPOINT, color=(0, 255, 0)),
            MemberType(name="tail", type=LabellerObjectType.KEYPOINT, color=(0, 0, 255)),
        ],
        skeleton=SkeletonType(lines=[], color=(0, 0, 0)),
        color=(255, 0, 0),
    )
    metadata = MappingYoloDatasetMetadataGenerator(config).generate([instance_type])

    image = YoloImage(
        name="a",
        instances=[YoloPoseInstance(class_index=0, box=(0.5, 0.5, 0.2, 0.4), keypoints=[(0.3, 0.3, 2.0), (0.7, 0.7, 1.0)])],
        image=np.zeros((2, 2, 3), dtype=np.uint8),
    )
    # No val images at all - YoloDatasetWriter is expected to still emit a (empty)
    # val set on its own, since YoloDataYaml requires one.
    dataset = YoloDataset(sets=[("train", [image])], class_names=["mouse"], num_keypoints=2)

    target = tmp_path / "export"
    list(YoloDatasetWriter().write(target, dataset))  # write() is a generator - must be consumed to run
    YoloPoseDatasetMetadataWriter().write(target, metadata)

    data_yaml_file = target / "data.yaml"
    raw = yaml.safe_load(data_yaml_file.read_text())
    dataset_root = yolo_dataset_root(data_yaml_file, raw)
    data_yaml = YoloDataYamlSerializer().deserialize(raw)
    resolved = resolve_yolo_data_yaml(data_yaml, data_yaml_file.parent)
    images = discover_yolo_dataset_images(resolved)
    schema = build_yolo_dataset_schema(dataset_root, resolved)

    assert schema.mode == ConfigMode.YOLO_POSE
    instances = parse_yolo_label_file(images[0].label, schema)

    assert len(instances) == 1
    bbox, nose, tail = instances[0].members
    assert nose.p == pytest.approx((0.3, 0.3))
    assert tail.p == pytest.approx((0.7, 0.7))
