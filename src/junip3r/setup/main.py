import logging
import sys
from importlib.resources import files
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from junip3r.logging_setup import create_logging_manager
from junip3r.setup.data.repository.config import SetupConfigRepository
from junip3r.setup.widgets.setup_window import SetupMainWindow

logger = logging.getLogger(__name__)


def from_config_file(config_file: Path, integrated: bool = False, parent=None) -> SetupMainWindow:
    config_repository = SetupConfigRepository(config_file)
    setup = SetupMainWindow(config_repository, integrated=integrated, parent=parent)

    return setup


def main():
    log_manager = create_logging_manager(run_mode="standalone")
    try:
        app = QApplication(sys.argv)

        res_folder = files("junip3r.res")
        app_icon = QIcon(str(res_folder / "junip3r_logo.png"))

        app.setWindowIcon(app_icon)

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

        log_manager.start_app_run("setup")
        logger.info("starting standalone setup",
                    extra={"event_category": "lifecycle", "event_name": "app_start", "app_name": "setup"})

        frame_extractor = from_config_file(config_file)
        frame_extractor.show()

        sys.exit(app.exec())
    finally:
        log_manager.close()


if __name__ == "__main__":
    main()
