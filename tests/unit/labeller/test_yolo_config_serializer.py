import pytest

from junip3r.labeller.yolo.config.data import YoloDataYaml
from junip3r.labeller.yolo.config.serializer import YoloDataYamlSerializer


def _minimal_config(**overrides):
    fields = dict(
        path=None, train="images/train", val="images/val", test=None,
        names=["mouse", "cat"], nc=2, channels=3, download=None,
        kpt_shape=None, flip_idx=None, kpt_names=None, kpt_oks_sigmas=None,
        masks_dir=None, label_mapping=None, depth_scale=None, max_depth=None,
        extras={},
    )
    fields.update(overrides)
    return YoloDataYaml(**fields)


def test_round_trips_a_minimal_config():
    config = _minimal_config()
    serializer = YoloDataYamlSerializer()

    round_tripped = serializer.deserialize(serializer.serialize(config))

    assert round_tripped == config


def test_serialize_omits_unset_optional_fields():
    config = _minimal_config()

    data = YoloDataYamlSerializer().serialize(config)

    assert "test" not in data
    assert "download" not in data
    assert "kpt_shape" not in data
    assert set(data.keys()) == {"train", "val", "names", "nc", "channels"}


def test_deserialize_requires_train():
    with pytest.raises(ValueError, match="train"):
        YoloDataYamlSerializer().deserialize({"val": "images/val", "names": ["mouse"]})


def test_deserialize_requires_val_or_validation():
    with pytest.raises(ValueError, match="val"):
        YoloDataYamlSerializer().deserialize({"train": "images/train", "names": ["mouse"]})


def test_deserialize_accepts_validation_as_alias_for_val():
    config = YoloDataYamlSerializer().deserialize({
        "train": "images/train", "validation": "images/val", "names": ["mouse"],
    })

    assert config.val == "images/val"


def test_serialize_never_reemits_validation_alias():
    config = _minimal_config()

    data = YoloDataYamlSerializer().serialize(config)

    assert "validation" not in data
    assert data["val"] == "images/val"


def test_deserialize_normalizes_string_keyed_names_mapping():
    config = YoloDataYamlSerializer().deserialize({
        "train": "images/train", "val": "images/val", "names": {"0": "mouse", "1": "cat"},
    })

    assert config.names == {0: "mouse", 1: "cat"}


def test_deserialize_keeps_names_list_as_a_list():
    config = YoloDataYamlSerializer().deserialize({
        "train": "images/train", "val": "images/val", "names": ["mouse", "cat"],
    })

    assert config.names == ["mouse", "cat"]


def test_deserialize_raises_when_names_and_nc_counts_disagree():
    with pytest.raises(ValueError, match="names.*nc|nc.*names"):
        YoloDataYamlSerializer().deserialize({
            "train": "images/train", "val": "images/val", "names": ["mouse", "cat"], "nc": 3,
        })


def test_deserialize_defaults_channels_to_three_when_absent():
    config = YoloDataYamlSerializer().deserialize({
        "train": "images/train", "val": "images/val", "names": ["mouse"],
    })

    assert config.channels == 3


def test_deserialize_keeps_explicit_channels():
    config = YoloDataYamlSerializer().deserialize({
        "train": "images/train", "val": "images/val", "names": ["mouse"], "channels": 1,
    })

    assert config.channels == 1


def test_deserialize_routes_unknown_keys_into_extras():
    config = YoloDataYamlSerializer().deserialize({
        "train": "images/train", "val": "images/val", "names": ["mouse"],
        "minival": "images/minival",
    })

    assert config.extras == {"minival": "images/minival"}


def test_extras_round_trip_back_into_the_output():
    config = _minimal_config(extras={"minival": "images/minival"})

    data = YoloDataYamlSerializer().serialize(config)

    assert data["minival"] == "images/minival"


def test_deserialize_normalizes_kpt_names_and_label_mapping_int_keys():
    config = YoloDataYamlSerializer().deserialize({
        "train": "images/train", "val": "images/val", "names": ["mouse"],
        "kpt_names": {"0": ["nose", "tail"]},
        "label_mapping": {"0": 1, "1": None},
    })

    assert config.kpt_names == {0: ["nose", "tail"]}
    assert config.label_mapping == {0: 1, 1: None}
