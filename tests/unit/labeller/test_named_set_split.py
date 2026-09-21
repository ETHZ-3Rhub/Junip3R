import yaml

from junip3r.labeller.export.yolo.set_split import (
    NamedSetSplit,
    NamedSetSplitSerializer,
    SetSplitConfig,
    SetSplitConfigSerializer,
    SetSplitRepository,
)


# --- NamedSetSplitSerializer ----------------------------------------------------------

def test_named_set_split_serializer_round_trip():
    named_split = NamedSetSplit(
        id="abc", name="Environment",
        config=SetSplitConfig(grouping="video", group_sets={"a": "train"}, auto_split_ratio=0.8),
    )

    data = NamedSetSplitSerializer.serialize(named_split)
    restored = NamedSetSplitSerializer.deserialize(data)

    assert restored == named_split


def test_named_set_split_serializer_generates_an_id_when_absent():
    # A plain SetSplitConfigSerializer dict has no "id"/"name" keys at all.
    data = SetSplitConfigSerializer.serialize(SetSplitConfig())

    restored = NamedSetSplitSerializer.deserialize(data)

    assert restored.id  # non-empty, generated
    assert restored.name == "Default"


# --- SetSplitRepository ---------------------------------------------------------------

def test_repository_list_returns_empty_for_a_missing_file(tmp_path):
    repository = SetSplitRepository(tmp_path / "set_split.yaml")

    assert repository.list() == []


def test_repository_migrates_a_legacy_flat_file_into_one_named_default_split(tmp_path):
    path = tmp_path / "set_split.yaml"
    config = SetSplitConfig(grouping="video", group_sets={"a": "train"}, auto_split_ratio=0.8)
    path.write_text(yaml.dump(SetSplitConfigSerializer.serialize(config)))

    repository = SetSplitRepository(path)
    splits = repository.list()

    assert len(splits) == 1
    assert splits[0].name == "Default"
    assert splits[0].config == config


def test_repository_migration_id_is_stable_across_repeated_calls(tmp_path):
    """Regression test: list() has no cache and is called on every dialog refresh, so
    the id minted while migrating a legacy file must be persisted immediately - not
    re-randomized on every subsequent call.
    """
    path = tmp_path / "set_split.yaml"
    path.write_text(yaml.dump(SetSplitConfigSerializer.serialize(SetSplitConfig())))
    repository = SetSplitRepository(path)

    first_id = repository.list()[0].id
    second_id = repository.list()[0].id

    assert first_id == second_id


def test_repository_migration_persists_the_new_shape_to_disk(tmp_path):
    path = tmp_path / "set_split.yaml"
    path.write_text(yaml.dump(SetSplitConfigSerializer.serialize(SetSplitConfig())))
    SetSplitRepository(path).list()

    with path.open("r") as f:
        data = yaml.safe_load(f)

    assert "splits" in data


def test_repository_set_inserts_a_new_split(tmp_path):
    repository = SetSplitRepository(tmp_path / "set_split.yaml")
    named_split = NamedSetSplit(id="a", name="Default", config=SetSplitConfig())

    repository.set(named_split)

    assert repository.list() == [named_split]


def test_repository_set_updates_an_existing_split_in_place_without_reordering(tmp_path):
    repository = SetSplitRepository(tmp_path / "set_split.yaml")
    first = NamedSetSplit(id="a", name="First", config=SetSplitConfig())
    second = NamedSetSplit(id="b", name="Second", config=SetSplitConfig())
    repository.set(first)
    repository.set(second)

    renamed_first = NamedSetSplit(id="a", name="Renamed", config=SetSplitConfig())
    repository.set(renamed_first)

    assert [s.id for s in repository.list()] == ["a", "b"]
    assert repository.list()[0].name == "Renamed"


def test_repository_get_returns_none_for_an_unknown_id(tmp_path):
    repository = SetSplitRepository(tmp_path / "set_split.yaml")

    assert repository.get("missing") is None


def test_repository_delete_removes_the_matching_split(tmp_path):
    repository = SetSplitRepository(tmp_path / "set_split.yaml")
    repository.set(NamedSetSplit(id="a", name="First", config=SetSplitConfig()))
    repository.set(NamedSetSplit(id="b", name="Second", config=SetSplitConfig()))

    repository.delete("a")

    assert [s.id for s in repository.list()] == ["b"]
