from __future__ import annotations

import logging
import sys
from importlib.resources import files
from pathlib import Path
from typing import Optional, Literal, Any, cast

from PySide6.QtCore import QObject, QCoreApplication
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow

from junip3r.logging_setup import LoggingManager, create_logging_manager
from junip3r.setup.main import from_config_file as setup_from_config_file
from junip3r.labeller.main import from_config_file as labeller_from_config_file
from junip3r.frame_extractor.main import from_config_file as frame_extractor_from_config_file
from junip3r.setup.widgets.new_project_window import NewProjectWindow
from junip3r.setup.widgets.setup_window import SetupMainWindow
from junip3r.setup.widgets.start_window import StartWindow

AppId = Literal["setup", "labeller", "frame_extractor"]
logger = logging.getLogger(__name__)


class AppController(QObject):
    """
    Owns the current main window and the shared config path.

    The two app windows are independent. They only communicate with this
    controller through signals.
    """

    def __init__(self, *, log_manager: Optional[LoggingManager] = None):
        super().__init__()

        self._log_manager = log_manager

        self._config_file: Optional[Path] = None

        self._start_window: Optional[StartWindow] = None
        self._new_project_window: Optional[NewProjectWindow] = None

        self._current_window: Optional[QMainWindow] = None
        self._current_app: Optional[AppId] = None
        self._switching = False

    def start(self) -> None:
        logger.info("starting controller", extra={"event_category": "lifecycle", "event_name": "controller_start"})
        start_window = StartWindow()
        start_window.new_project_requested.connect(self._new_project)
        start_window.open_project_requested.connect(self._open_project)
        self._start_window = start_window

        start_window.show()

    def _open_project(self, config_file: str) -> None:
        QApplication.instance().setQuitOnLastWindowClosed(False)
        self.config_file = Path(config_file)
        self.switch_to("labeller")

        if self._start_window is not None:
            self._start_window.close()
            self._start_window = None

    def _new_project(self) -> None:
        new_project_window = NewProjectWindow()
        new_project_window.setWindowTitle("Junip3r - New Project")
        new_project_window.resize(1400, 800)

        new_project_window.setup_requested.connect(self._new_project_setup)
        new_project_window.open_project_requested.connect(self._new_project_open)
        self._new_project_window = new_project_window

        new_project_window.show()

        if self._start_window is not None:
            self._start_window.close()
            self._start_window = None

    def _new_project_setup(self, config_file: str) -> None:
        QApplication.instance().setQuitOnLastWindowClosed(False)
        self.config_file = Path(config_file)
        self.switch_to("setup")

        if self._new_project_window is not None:
            self._new_project_window.close()
            self._new_project_window = None

    def _new_project_open(self, config_file: str) -> None:
        QApplication.instance().setQuitOnLastWindowClosed(False)
        self.config_file = Path(config_file)
        self.switch_to("frame_extractor")

        if self._new_project_window is not None:
            self._new_project_window.close()
            self._new_project_window = None

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

        new_window = self._create_window(app_id)

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
        assert self.config_file is not None
        if app_id == "setup":
            return setup_from_config_file(self.config_file, integrated=True)

        if app_id == "labeller":
            return labeller_from_config_file(self.config_file, integrated=True)

        if app_id == "frame_extractor":
            return frame_extractor_from_config_file(self.config_file, integrated=True)

        raise ValueError(f"Unknown app id: {app_id!r}")

    def _on_window_closed(self, window: QMainWindow) -> None:
        if self._switching:
            return

        if window is self._current_window:
            logger.info("current window closed", extra={"event_category": "lifecycle", "event_name": "window_closed", "app_name": self._current_app or "-"})
            self._current_window = None
            self._current_app = None
            QCoreApplication.quit()

    def _quit(self) -> None:
        logger.info("quitting application", extra={"event_category": "lifecycle", "event_name": "application_quit"})
        QCoreApplication.quit()
        sys.exit(0)


def main() -> int:
    log_manager = create_logging_manager(run_mode="integrated")

    app = QApplication(sys.argv)

    res_folder = files("junip3r.res")
    app_icon = QIcon(str(res_folder / "junip3r_logo.png"))
    app.setWindowIcon(app_icon)

    # Important: during switching we briefly close the old top-level window
    # before showing the new one. Without this, Qt may quit automatically when
    # the last visible top-level window closes.

    controller = AppController(log_manager=log_manager)
    controller.start()

    try:
        app.exec()
    finally:
        log_manager.close()


if __name__ == "__main__":
    main()
