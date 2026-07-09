from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Literal, Any, cast

from PySide6 import QtWidgets
from PySide6.QtCore import QObject, QCoreApplication
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow

from junip3r.logging_setup import LoggingManager, create_logging_manager
from junip3r.labeller.main import from_config_file as labeller_from_config_file
from junip3r.frame_extractor.main import from_config_file as frame_extractor_from_config_file


AppId = Literal["labeller", "frame_extractor"]
logger = logging.getLogger(__name__)


class AppController(QObject):
    """
    Owns the current main window and the shared config path.

    The two app windows are independent. They only communicate with this
    controller through signals.
    """

    def __init__(self, *, config_file: Path, log_manager: Optional[LoggingManager] = None):
        super().__init__()

        self.config_file = config_file
        self._log_manager = log_manager
        self._current_window: Optional[QMainWindow] = None
        self._current_app: Optional[AppId] = None
        self._switching = False

    def start(self, initial_app: AppId = "labeller") -> None:
        logger.info("starting controller", extra={"event_category": "lifecycle", "event_name": "controller_start", "app_name": initial_app})
        self.switch_to(initial_app)

    def switch_to(self, app_id: AppId) -> None:
        logger.info("switching app", extra={"event_category": "lifecycle", "event_name": "app_switch_requested", "app_name": app_id})
        if self._current_app == app_id and self._current_window is not None:
            return

        old_window = cast(Any, self._current_window)

        old_geometry = None
        old_was_maximized = False

        if old_window is not None:
            old_geometry = old_window.geometry()
            old_was_maximized = old_window.isMaximized()

            self._switching = True
            accepted = old_window.close()
            self._switching = False

            if not accepted:
                return

        if self._log_manager is not None:
            current_context = self._log_manager.current_context
            if current_context is None or current_context.app_name != app_id:
                self._log_manager.start_app_run(app_id)

        new_window = cast(Any, self._create_window(app_id))

        new_window.switch_to.connect(self.switch_to)
        new_window.closed.connect(lambda w=new_window: self._on_window_closed(w))

        if old_geometry is not None:
            new_window.setGeometry(old_geometry)

        self._current_window = new_window
        self._current_app = app_id

        if old_was_maximized:
            new_window.showMaximized()
        else:
            new_window.show()

        new_window.raise_()
        new_window.activateWindow()
        logger.info("app window shown", extra={"event_category": "lifecycle", "event_name": "app_window_shown", "app_name": app_id})

    def _create_window(self, app_id: AppId) -> Any:
        logger.debug("creating window", extra={"event_category": "ui", "event_name": "create_window", "app_name": app_id})
        if app_id == "labeller":
            return labeller_from_config_file(self.config_file, show_frame_extractor=True)

        if app_id == "frame_extractor":
            return frame_extractor_from_config_file(self.config_file, show_labeller=True)

        raise ValueError(f"Unknown app id: {app_id!r}")

    def _on_window_closed(self, window: QMainWindow) -> None:
        if self._switching:
            return

        if window is self._current_window:
            logger.info("current window closed", extra={"event_category": "lifecycle", "event_name": "window_closed", "app_name": self._current_app or "-"})
            self._current_window = None
            self._current_app = None
            QCoreApplication.quit()


def main() -> int:
    bundle_dir = getattr(sys, '_MEIPASS', os.getcwd())
    res_folder = Path(os.path.abspath(os.path.join(bundle_dir, 'res')))
    app_icon_file = res_folder / "junip3r_logo.png"

    log_manager = create_logging_manager(run_mode="integrated")

    app = QApplication(sys.argv)

    app_icon = QIcon(str(app_icon_file))
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

    project_folder = config_file.parent

    image_file_endings = [".png", ".jpg", ".jpeg"]
    image_folder = project_folder / "images"
    image_files = [f for f in image_folder.glob("*") if f.suffix.lower() in image_file_endings]

    if len(image_files) == 0:
        start_app = "frame_extractor"
    else:
        start_app = "labeller"

    log_manager.start_app_run(start_app)

    # Important: during switching we briefly close the old top-level window
    # before showing the new one. Without this, Qt may quit automatically when
    # the last visible top-level window closes.
    app.setQuitOnLastWindowClosed(False)

    controller = AppController(config_file=config_file, log_manager=log_manager)
    controller.start(start_app)

    try:
        return app.exec()
    finally:
        log_manager.close()


if __name__ == "__main__":
    main()
