from junip3r.common.config.abc import ConfigMode
from junip3r.common.config.data import Config, InstanceTypeConfig, MemberConfig, SkeletonConfig
from junip3r.common.config.serialization import ConfigSerializer
from junip3r.labeller.data.types.abc import LabellerObjectType


def test_serialize_junip3r_round_trips_through_deserialize():
    config = Config(
        mode=ConfigMode.JUNIPER,
        instance_types=[
            InstanceTypeConfig(
                name="mouse",
                members=[
                    MemberConfig(type=LabellerObjectType.KEYPOINT, name="nose", color=(255, 0, 0)),
                    MemberConfig(type=LabellerObjectType.KEYPOINT, name="tail", color=(0, 255, 0)),
                ],
                skeleton=SkeletonConfig(lines=[(0, 1)], color=(153, 153, 153)),
            )
        ],
    )
    config = Config(mode=config.mode, instance_types=config.instance_types, expected_instance_types=config.instance_types)

    serializer = ConfigSerializer()
    config_dict = serializer.serialize(config)
    round_tripped = serializer.deserialize(config_dict)

    assert round_tripped.mode == ConfigMode.JUNIPER
    mouse = round_tripped.instance_types[0]
    assert [m.name for m in mouse.members] == ["nose", "tail"]
    assert [m.color for m in mouse.members] == [(255, 0, 0), (0, 255, 0)]
    assert mouse.skeleton.lines == [(0, 1)]
    assert mouse.skeleton.color == (153, 153, 153)
    assert [it.name for it in round_tripped.expected_instance_types] == ["mouse"]


def test_serialize_yolo_detect_omits_color_key_when_unset():
    config = Config(
        mode=ConfigMode.YOLO_DETECT,
        instance_types=[
            InstanceTypeConfig(name="cat", members=[MemberConfig(type=LabellerObjectType.BOUNDING_BOX, name="cat", color=None)])
        ],
    )

    config_dict = ConfigSerializer().serialize(config)

    assert config_dict["instance_types"] == ["cat"]


def test_serialize_yolo_detect_includes_hex_color_when_set():
    config = Config(
        mode=ConfigMode.YOLO_DETECT,
        instance_types=[
            InstanceTypeConfig(
                name="cat",
                members=[MemberConfig(type=LabellerObjectType.BOUNDING_BOX, name="cat")],
                color=(255, 0, 0),
            )
        ],
    )

    config_dict = ConfigSerializer().serialize(config)

    assert config_dict["instance_types"] == [{"name": "cat", "color": "#ff0000"}]


def test_serialize_yolo_pose_color_is_a_top_level_key_independent_of_bounding_box_mode():
    config = Config(
        mode=ConfigMode.YOLO_POSE,
        instance_types=[
            InstanceTypeConfig(
                name="mouse",
                members=[MemberConfig(name="nose", type=LabellerObjectType.KEYPOINT)],
                color=(255, 0, 0),
            )
        ],
    )

    config_dict = ConfigSerializer().serialize(config)

    mouse = config_dict["instance_types"][0]
    assert mouse["bounding_box"] == "automatic"
    assert mouse["color"] == "#ff0000"


def test_yolo_pose_color_round_trips_through_deserialize_for_both_bounding_box_modes():
    for members in (
        [MemberConfig(name="Bounding Box", type=LabellerObjectType.BOUNDING_BOX), MemberConfig(name="nose", type=LabellerObjectType.KEYPOINT)],
        [MemberConfig(name="nose", type=LabellerObjectType.KEYPOINT)],
    ):
        config = Config(
            mode=ConfigMode.YOLO_POSE,
            instance_types=[InstanceTypeConfig(name="mouse", members=members, color=(255, 0, 0))],
        )

        serializer = ConfigSerializer()
        round_tripped = serializer.deserialize(serializer.serialize(config))

        assert round_tripped.instance_types[0].color == (255, 0, 0)


def test_serialize_junip3r_includes_color_when_set():
    config = Config(
        mode=ConfigMode.JUNIPER,
        instance_types=[InstanceTypeConfig(name="mouse", color=(0, 255, 0))],
    )

    config_dict = ConfigSerializer().serialize(config)

    assert config_dict["instance_types"][0]["color"] == "#00ff00"

    round_tripped = ConfigSerializer().deserialize(config_dict)
    assert round_tripped.instance_types[0].color == (0, 255, 0)
