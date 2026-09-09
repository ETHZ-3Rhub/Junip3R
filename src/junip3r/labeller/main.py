import logging
import sys
from pathlib import Path
from importlib.resources import files

import yaml
from PySide6 import QtWidgets
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from junip3r.labeller.config.parser import parse_config
from junip3r.labeller.data.discovery import discover_labeller_images
from junip3r.labeller.data.repository.config import ConfigRepository
from junip3r.labeller.data.repository.context import ContextRepository
from junip3r.labeller.data.repository.image import ImageRepository
from junip3r.labeller.data.repository.label import JuniperLabelRepository
from junip3r.labeller.data.repository.selection import SelectionRepository
from junip3r.labeller.data.repository.tag import TagRepository
from junip3r.labeller.export.yolo.set_split import SetSplitRepository
from junip3r.labeller.legacy.legacy_label_converter import LegacyLabelConverter
from junip3r.labeller.model.app_model import AppModel
from junip3r.labeller.model.context_model import ContextModel
from junip3r.labeller.model.image_settings_model import ImageSettingsModel
from junip3r.labeller.model.label_model import LabelModel
from junip3r.labeller.widgets.main_window import EditorMainWindow
from junip3r.logging_setup import create_logging_manager

logger = logging.getLogger(__name__)


def from_config_file(config_file: Path, integrated: bool = False) -> EditorMainWindow:
    project_folder = config_file.parent
    config = yaml.safe_load(open(config_file, 'r'))

    labeller_config = parse_config(config)
    config_repository = ConfigRepository(labeller_config)

    images = discover_labeller_images(project_folder)
    image_repository = ImageRepository([i.image for i in images])

    context_files = [i.context for i in images]
    if any(cf is not None for cf in context_files):
        context_repository = ContextRepository(context_files)
        context_model = ContextModel(context_repository)
    else:
        context_model = None

    image_settings_model = ImageSettingsModel()

    legacy_converter = LegacyLabelConverter(labeller_config.instance_types)
    for i in images:
        legacy_label_file = i.label.with_suffix(".csv")
        if legacy_label_file.exists() and not i.label.exists():
            legacy_converter.convert_legacy_labels(legacy_label_file, i.label)

    label_repository = JuniperLabelRepository([i.label for i in images])
    label_model = LabelModel(config_repository, label_repository)
    tag_repository = TagRepository(project_folder / "meta" / "tags", [i.image.stem for i in images])

    set_split_repository = SetSplitRepository(project_folder / "_labeller" / "set_split.yaml")

    app_model = AppModel(image_repository, label_model, SelectionRepository(), tag_repository=tag_repository)

    editor = EditorMainWindow(show_frame_extractor=integrated)
    editor.set_model(app_model, context_model, image_settings_model)
    editor.set_mode(labeller_config.mode)
    editor.set_set_split_repository(set_split_repository)

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
