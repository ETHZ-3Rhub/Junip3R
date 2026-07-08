import colorsys
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Tuple

import yaml
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QApplication


from junip3r.logging_setup import create_logging_manager
from junip3r.labeller.model.app_model import AppModel
from junip3r.labeller.data.repository.abc import IPointSelectionRepository, ISettingsRepository
from junip3r.labeller.data.repository.config import LabellerConfigRepository
from junip3r.labeller.data.repository.context import ContextRepository
from junip3r.labeller.data.repository.image import ImageRepository
from junip3r.labeller.data.repository.label import JuniperLabelRepository
from junip3r.labeller.data.types.data import BoundingBoxType
from junip3r.labeller.data.types.data import InstanceType, KeypointType
from junip3r.labeller.model.editor_model import EditorModel
from junip3r.labeller.widgets.labeller import Labeller


logger = logging.getLogger(__name__)


class MockSelectionRepository(IPointSelectionRepository):
    def __init__(self):
        self._selections: Dict[int, Tuple[Optional[str], Optional[int]]] = {}
        self._new_instance_type_index: Dict[int, Optional[int]] = {}

    def get_selection(self, image_index: int) -> Tuple[Optional[str], Optional[int]]:
        return self._selections.get(image_index, (None, None))

    def set_selection(self, image_index: int, instance_id: str, point_index: int):
        self._selections[image_index] = (instance_id, point_index)

    def get_new_instance_type_index(self, image_index: int) -> int:
        return self._new_instance_type_index.get(image_index) or 0

    def set_new_instance_type_index(self, image_index: int, instance_type_index: int):
        self._new_instance_type_index[image_index] = instance_type_index


class MockSettingsRepository(ISettingsRepository):
    def __init__(self):
        self._brightness = 0.0
        self._contrast = 0.0

    def get_settings(self, image_index: int) -> Tuple[float, float]:
        return self._brightness, self._contrast

    def set_settings(self, image_index: int, brightness: float, contrast: float):
        self._brightness = brightness
        self._contrast = contrast


def color_from_hue(hue: float) -> Tuple[int, int, int]:
    color = colorsys.hsv_to_rgb(hue, 1, 1)
    return int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)


def color_from_string(color_string: str) -> Tuple[int, int, int]:
    if color_string.startswith("#"):
        return int(color_string[1:3], 16), int(color_string[3:5], 16), int(color_string[5:7], 16)
    else:
        color = QColor(color_string)
        if not color.isValid():
            return 0, 0, 0
        else:
            return color.red(), color.green(), color.blue()


def load_instance_types(config_file: Path):
    config = yaml.safe_load(open(config_file, 'r'))

    instance_type_dicts = [instance_type for instance_type in config["instance_types"]]
    instance_types = []
    for instance_type_dict in instance_type_dicts:
        name = instance_type_dict["name"]
        points = instance_type_dict["points"]
        colors = instance_type_dict["colors"] if "colors" in instance_type_dict else {}
        skeleton = instance_type_dict["skeleton"]
        skeleton = [(points.index(skeleton_point[0]), points.index(skeleton_point[1])) for skeleton_point in skeleton]

        if "skeleton_color" in instance_type_dict:
            skeleton_color = color_from_string(instance_type_dict["skeleton_color"])
        else:
            skeleton_color = (0, 0, 0)

        if "bounding_box_type" not in instance_type_dict:
            bounding_box_type = BoundingBoxType.AUTOMATIC
        else:
            if instance_type_dict["bounding_box_type"] == "automatic":
                bounding_box_type = BoundingBoxType.AUTOMATIC
            elif instance_type_dict["bounding_box_type"] == "manual":
                bounding_box_type = BoundingBoxType.MANUAL
            else:
                raise ValueError(f"Invalid bounding box type: {instance_type_dict['bounding_box_type']}")

        point_types = []
        for point_index, point in enumerate(points):
            color = None
            if point_index < len(colors):
                color = color_from_string(colors[point_index])
            if color is None:
                point_percentage = point_index / len(points)
                color = color_from_hue(point_percentage)
            point_types.append(KeypointType(point, color))

        instance_types.append(InstanceType(name, bounding_box_type, point_types, skeleton, skeleton_color))

    instance_type_names = [instance_type.name for instance_type in instance_types]
    expected_instance_types = [
        instance_types[instance_type_names.index(instance_type_name)]
        for instance_type_name in config["instances"]
    ]

    tags = config.get("tags") or []

    return instance_types, expected_instance_types, tags


def from_config_file(config_file: Path, show_frame_extractor: bool = False, parent=None) -> Labeller:
    project_folder = config_file.parent

    instance_types, expected_instance_types, tags = load_instance_types(config_file)
    labeller_config_repository = LabellerConfigRepository(instance_types, expected_instance_types, tags)

    image_file_endings = [".png", ".jpg", ".jpeg"]
    image_folder = project_folder / "images"
    image_files = [f for f in image_folder.glob("*") if f.suffix.lower() in image_file_endings]
    image_repository = ImageRepository(image_files)

    context_file_endings = [".avi", ".mp4", ".mkv"]
    context_folder = project_folder / "context"
    def find_context_file(image_file: Path) -> Optional[Path]:
        for ending in context_file_endings:
            context_file = context_folder / (image_file.stem + ending)
            if context_file.exists():
                return context_file
        return None

    context_files = [cf for cf in (find_context_file(f) for f in image_files) if cf is not None]
    context_repository = ContextRepository(context_files)

    label_folder = project_folder / "labels"
    label_files = [label_folder / (image_file.stem + ".json") for image_file in image_files]
    label_repository = JuniperLabelRepository(instance_types, label_files)

    labeller_model = AppModel()
    labeller_model._image_repository = image_repository
    labeller_model._context_repository = context_repository
    labeller_model._config_repository = labeller_config_repository
    labeller_model._label_repository = label_repository
    labeller_model._selection_repository = MockSelectionRepository()
    labeller_model._settings_repository = MockSettingsRepository()

    editor_model = EditorModel(labeller_model)

    labeller = Labeller(show_frame_extractor=show_frame_extractor, parent=parent)
    labeller.set_model(editor_model)

    return labeller


if __name__ == "__main__":
    log_manager = create_logging_manager(run_mode="standalone")
    try:
        bundle_dir = getattr(sys, '_MEIPASS', os.getcwd())
        res_folder = Path(os.path.abspath(os.path.join(bundle_dir, '../res')))
        app_icon_file = res_folder / "junip3r_icon.png"

        app = QApplication(sys.argv)

        app_icon = QIcon(str(app_icon_file))
        app.setWindowIcon(app_icon)

        log_manager.start_app_run("labeller")
        logger.info("starting standalone labeller", extra={"event_category": "lifecycle", "event_name": "app_start", "app_name": "labeller"})

        labeller = from_config_file(Path("../../../_testdata/project/config.yaml"), show_frame_extractor=True)
        labeller.show()

        sys.exit(app.exec())
    finally:
        log_manager.close()
