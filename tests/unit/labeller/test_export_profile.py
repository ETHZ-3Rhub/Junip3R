import pytest

from junip3r.labeller.export.yolo.data import ExportMode
from junip3r.labeller.export.yolo.export_profile import ExportProfile, ExportProfileRepository, ExportProfileSerializer


# --- ExportProfileSerializer -----------------------------------------------------------

def test_serializer_round_trip():
    profile = ExportProfile(
        id="abc", name="Animals", instance_type_names=("fox", "deer"),
        set_split_id="split-1", target_folder="/data/animals", include_empty_images=True,
        mode=ExportMode.DETECT,
    )

    data = ExportProfileSerializer.serialize(profile)
    restored = ExportProfileSerializer.deserialize(data)

    assert restored == profile


def test_serializer_deserialize_fills_defaults():
    data = {"id": "abc", "name": "Default", "mode": "pose"}

    restored = ExportProfileSerializer.deserialize(data)

    assert restored == ExportProfile(id="abc", name="Default")


@pytest.mark.parametrize("mode, mode_name", [(ExportMode.POSE, "pose"), (ExportMode.DETECT, "detect")])
def test_serializer_mode_round_trips_through_its_string_name(mode, mode_name):
    profile = ExportProfile(id="abc", name="Default", mode=mode)

    data = ExportProfileSerializer.serialize(profile)
    assert data["mode"] == mode_name

    restored = ExportProfileSerializer.deserialize(data)
    assert restored.mode == mode


# --- ExportProfileRepository ------------------------------------------------------------

def test_repository_list_returns_empty_for_a_missing_file(tmp_path):
    repository = ExportProfileRepository(tmp_path / "export_profiles.yaml")

    assert repository.list() == []


def test_repository_set_inserts_a_new_profile(tmp_path):
    repository = ExportProfileRepository(tmp_path / "export_profiles.yaml")
    profile = ExportProfile(id="a", name="Default")

    repository.set(profile)

    assert repository.list() == [profile]


def test_repository_set_updates_an_existing_profile_in_place_without_reordering(tmp_path):
    repository = ExportProfileRepository(tmp_path / "export_profiles.yaml")
    first = ExportProfile(id="a", name="First")
    second = ExportProfile(id="b", name="Second")
    repository.set(first)
    repository.set(second)

    renamed_first = ExportProfile(id="a", name="Renamed")
    repository.set(renamed_first)

    assert [p.id for p in repository.list()] == ["a", "b"]
    assert repository.list()[0].name == "Renamed"


def test_repository_get_returns_none_for_an_unknown_id(tmp_path):
    repository = ExportProfileRepository(tmp_path / "export_profiles.yaml")

    assert repository.get("missing") is None


def test_repository_delete_removes_the_matching_profile(tmp_path):
    repository = ExportProfileRepository(tmp_path / "export_profiles.yaml")
    repository.set(ExportProfile(id="a", name="First"))
    repository.set(ExportProfile(id="b", name="Second"))

    repository.delete("a")

    assert [p.id for p in repository.list()] == ["b"]


def test_repository_persists_across_instances(tmp_path):
    path = tmp_path / "export_profiles.yaml"
    ExportProfileRepository(path).set(ExportProfile(id="a", name="Default", instance_type_names=("fox",)))

    reloaded = ExportProfileRepository(path).list()

    assert reloaded == [ExportProfile(id="a", name="Default", instance_type_names=("fox",))]
