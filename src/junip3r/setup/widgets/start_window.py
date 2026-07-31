from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCommandLinkButton,
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)


class StartWindow(QWidget):
    new_project_requested = Signal()
    open_project_requested = Signal(str)

    def __init__(self, recent_projects: list[str] | None = None):
        super().__init__()

        self.setWindowTitle("Junip3R")
        self.resize(720, 520)
        self.setMinimumSize(560, 420)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(32, 32, 32, 32)

        # Stretching above and below keeps the panel vertically centered.
        outer_layout.addStretch()

        panel = QFrame(self)
        panel.setObjectName("welcomePanel")
        panel.setMaximumWidth(620)

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(36, 32, 36, 32)
        panel_layout.setSpacing(14)

        title = QLabel("Welcome to Junip3R", panel)
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_font = title.font()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title.setFont(title_font)

        description = QLabel(
            "Create a new labelling project or continue working "
            "with an existing project.",
            panel,
        )
        description.setObjectName("description")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)

        panel_layout.addWidget(title)
        panel_layout.addWidget(description)
        panel_layout.addSpacing(12)

        self.btn_new_project = QCommandLinkButton(
            "Create a new project",
            "Choose the images, project location, and labelling configuration.",
            panel,
        )
        self.btn_new_project.setIcon(QIcon.fromTheme("document-new"))
        self.btn_new_project.setIconSize(QSize(32, 32))
        self.btn_new_project.setMinimumHeight(76)
        self.btn_new_project.clicked.connect(
            self.new_project_requested.emit
        )

        self.btn_open_project = QCommandLinkButton(
            "Open an existing project",
            "Continue working on a project that has already been created.",
            panel,
        )
        self.btn_open_project.setIcon(QIcon.fromTheme("document-open"))
        self.btn_open_project.setIconSize(QSize(32, 32))
        self.btn_open_project.setMinimumHeight(76)
        self.btn_open_project.clicked.connect(self._open_project)

        panel_layout.addWidget(self.btn_new_project)
        panel_layout.addWidget(self.btn_open_project)

        recent_projects = recent_projects or []

        if recent_projects:
            panel_layout.addSpacing(12)

            recent_title = QLabel("Recent projects", panel)
            recent_title.setObjectName("sectionTitle")
            panel_layout.addWidget(recent_title)

            self.recent_list = QListWidget(panel)
            self.recent_list.setMaximumHeight(130)
            self.recent_list.setAlternatingRowColors(True)

            for project_path in recent_projects:
                path = Path(project_path)

                item = QListWidgetItem(path.name)
                item.setData(
                    Qt.ItemDataRole.UserRole,
                    str(path),
                )
                item.setToolTip(str(path))

                self.recent_list.addItem(item)

            self.recent_list.itemActivated.connect(
                self._open_recent_project
            )

            panel_layout.addWidget(self.recent_list)

        outer_layout.addWidget(
            panel,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )
        outer_layout.addStretch()

        self.setStyleSheet("""
            QFrame#welcomePanel {
                background: palette(base);
                border: 1px solid palette(midlight);
                border-radius: 12px;
            }

            QLabel#description {
                color: palette(mid);
            }

            QLabel#sectionTitle {
                font-weight: bold;
            }

            QCommandLinkButton {
                background: palette(button);
                border: 1px solid palette(mid);
                border-radius: 8px;
                padding: 12px;
                text-align: left;
            }

            QCommandLinkButton:hover {
                background: palette(alternate-base);
                border-color: palette(highlight);
            }

            QCommandLinkButton:focus {
                border: 2px solid palette(highlight);
                padding: 11px;
            }

            QListWidget {
                border: 1px solid palette(midlight);
                border-radius: 6px;
                padding: 3px;
            }
        """)

    def _open_recent_project(self, item: QListWidgetItem):
        project_path = item.data(Qt.ItemDataRole.UserRole)
        self.open_project_requested.emit(project_path)

    def _open_project(self):
        dialog = QtWidgets.QFileDialog()
        dialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFile)  # type: ignore[arg-type]
        dialog.setNameFilter("Junip3R Config File (*.yaml)")
        dialog.setWindowTitle("Select Config File")
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptOpen)

        if dialog.exec():
            config_file = dialog.selectedFiles()[0]
            self.open_project_requested.emit(config_file)


if __name__ == "__main__":
    app = QApplication([])

    window = StartWindow(
        recent_projects=[
            r"C:\Projects\MousePoseStudy",
            r"C:\Projects\PilotDataset",
        ]
    )
    window.show()

    app.exec()