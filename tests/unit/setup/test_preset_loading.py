import pytest
import yaml

from junip3r.setup.widgets.new_project_window import load_preset, load_project_as_preset, load_saved_preset


def _write_config(path, mode="freeform"):
    path.write_text(yaml.dump({"mode": mode, "instance_types": [], "instances": []}))


def test_load_preset_requires_a_config_file(tmp_path):
    with pytest.raises(ValueError, match="config"):
        load_preset("name", tmp_path / "missing.yaml", tmp_path / "image.png", tmp_path / "labels.json")


def test_load_preset_image_is_none_when_image_file_is_missing(tmp_path):
    config_file = tmp_path / "config.yaml"
    _write_config(config_file)

    preset = load_preset("name", config_file, tmp_path / "missing_image.png", tmp_path / "missing_labels.json")

    assert preset.image is None
    assert preset.instances == []


def test_load_saved_preset_reads_the_flat_folder_layout(tmp_path):
    preset_folder = tmp_path / "my_template"
    preset_folder.mkdir()
    _write_config(preset_folder / "config.yaml")

    preset = load_saved_preset(preset_folder)

    assert preset.name == "my_template"
    assert preset.image is None


def test_load_project_as_preset_reads_config_from_project_root_and_preview_from_labeller_folder(tmp_path):
    project_folder = tmp_path / "my_project"
    project_folder.mkdir()
    _write_config(project_folder / "config.yaml")

    preset = load_project_as_preset(project_folder)

    assert preset.name == "my_project"
    assert preset.image is None
    assert preset.config_file == project_folder / "config.yaml"


def test_load_project_as_preset_raises_when_project_has_no_config(tmp_path):
    project_folder = tmp_path / "not_a_project"
    project_folder.mkdir()

    with pytest.raises(ValueError):
        load_project_as_preset(project_folder)
