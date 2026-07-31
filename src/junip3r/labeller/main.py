import logging
import sys
from pathlib import Path
from importlib.resources import files
from typing import Optional, Dict, Tuple, List

import yaml
from PySide6 import QtWidgets
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from junip3r.labeller.config.parser import parse_config
from junip3r.labeller.data.repository.abc import ISelectionRepository, ISettingsRepository, IConfigRepository
from junip3r.labeller.data.repository.context import ContextRepository
from junip3r.labeller.data.repository.image import ImageRepository
from junip3r.labeller.data.repository.label import JuniperLabelRepository
from junip3r.labeller.data.types.abc import IInstanceType, Selection
from junip3r.labeller.legacy.legacy_label_converter import LegacyLabelConverter
from junip3r.labeller.model.app_model import AppModel
from junip3r.labeller.model.context_model import ContextModel
from junip3r.labeller.model.image_settings_model import ImageSettingsModel
from junip3r.labeller.model.pose_image_model import PoseImageModel
from junip3r.labeller.widgets.main_window import EditorMainWindow
from junip3r.logging_setup import create_logging_manager

logger = logging.getLogger(__name__)


class ConfigRepository(IConfigRepository):
    def __init__(self, instance_types: List[IInstanceType], expected_instance_types: List[IInstanceType]):
        self._instance_types = instance_types
        self._expected_instance_types = expected_instance_types

    def get_instance_types(self, image_index: int) -> List[IInstanceType]:
        return self._instance_types

    def get_expected_instances(self, image_index: int) -> List[IInstanceType]:
        return self._expected_instance_types

    def get_tag_names(self, image_index: int) -> List[str]: ...


class SelectionRepository(ISelectionRepository):
    def __init__(self):
        self._selections: Dict[int, Optional[Selection]] = {}
        self._new_instance_types: Dict[int, Optional[IInstanceType]] = {}

    def get_selection(self, image_index: int) -> Optional[Selection]:
        return self._selections.get(image_index, (None, 0))

    def set_selection(self, image_index: int, selection: Optional[Selection]):
        self._selections[image_index] = selection

    def get_new_instance_type(self, image_index: int) -> Optional[IInstanceType]:
        return self._new_instance_types.get(image_index, None)

    def set_new_instance_type(self, image_index: int, instance_type: Optional[IInstanceType]):
        self._new_instance_types[image_index] = instance_type


class SettingsRepository(ISettingsRepository):
    def __init__(self):
        self._brightness = 0.0
        self._contrast = 0.0

    def get_settings(self, image_index: int) -> Tuple[float, float]:
        return self._brightness, self._contrast

    def set_settings(self, image_index: int, brightness: float, contrast: float):
        self._brightness = brightness
        self._contrast = contrast


def from_config_file(config_file: Path, integrated: bool = False) -> EditorMainWindow:
    project_folder = config_file.parent
    config = yaml.safe_load(open(config_file, 'r'))

    mode, instance_types, expected_instance_types, tags = parse_config(config)
    config_repository = ConfigRepository(instance_types, expected_instance_types)

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

    context_files = [cf for cf in (find_context_file(f) for f in image_files)]
    if any(cf is not None for cf in context_files):
        context_repository = ContextRepository(context_files)
        context_model = ContextModel(context_repository)
    else:
        context_model = None

    image_settings_model = ImageSettingsModel()

    label_folder = project_folder / "labels"
    def find_legacy_label_file(image_file: Path) -> Optional[Tuple[Path, Path]]:
        label_file = label_folder / (image_file.stem + ".csv")
        if label_file.exists():
            new_label_file = label_folder / (image_file.stem + ".json")
            if not new_label_file.exists():
                return label_file, new_label_file
        return None

    legacy_label_files = [lf for lf in (find_legacy_label_file(f) for f in image_files) if lf is not None]
    if len(legacy_label_files) > 0:
        legacy_converter = LegacyLabelConverter(instance_types)
        for old_file, new_file in legacy_label_files:
            legacy_converter.convert_legacy_labels(old_file, new_file)

    def find_label_file(image_file: Path) -> Path:
        label_file = label_folder / (image_file.stem + ".json")
        return label_file

    label_files = [lf for lf in (find_label_file(f) for f in image_files)]
    label_repository = JuniperLabelRepository(instance_types, label_files)

    app_model = AppModel(image_repository, config_repository, label_repository, SelectionRepository())
    pose_image_model = PoseImageModel(app_model)

    if context_model is not None:
        pose_image_model.image_navigation_state_changed.connect(context_model.set_image_navigation_state)

    editor = EditorMainWindow(show_frame_extractor=integrated)
    editor.set_model(pose_image_model, context_model, image_settings_model)

    return editor


def main():
    _excepthook = sys.excepthook

    def exception_hook(exctype, value, traceback):
        logger.critical(
            "Unhandled exception", exc_info=(exctype, value, traceback)
        )
        _excepthook(exctype, value, traceback)

    sys.excepthook = exception_hook

    log_manager = create_logging_manager(run_mode="standalone")

    try:
        app = QApplication(sys.argv)

        dialog = QtWidgets.QFileDialog()
        dialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFile)  # type: ignore[arg-type]
        dialog.setNameFilter("Junip3R Config File (*.yaml)")
        dialog.setWindowTitle("Select Config File")
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptOpen)

        if dialog.exec():
            file_path = dialog.selectedFiles()[0]
            config_file = Path(file_path)
        else:
            exit(1)

        res_folder = files("junip3r.res")
        app_icon = QIcon(str(res_folder / "junip3r_logo.png"))
        app.setWindowIcon(app_icon)

        log_manager.start_app_run("viewer")
        logger.info("starting standalone viewer", extra={"event_category": "lifecycle", "event_name": "app_start", "app_name": "viewer"})

        window = from_config_file(config_file)
        window.show()

        sys.exit(app.exec())
    finally:
        log_manager.close()


if __name__ == "__main__":
    main()
