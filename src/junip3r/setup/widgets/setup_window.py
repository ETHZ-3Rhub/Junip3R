import shutil
from pathlib import Path
from typing import List, Optional, Sequence

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMainWindow, QFrame, QVBoxLayout, QWidget, QSplitter, QPushButton, \
    QFileDialog, QMessageBox, QInputDialog

from junip3r.common.config.abc import ConfigMode
from junip3r.labeller.config.data import InstanceType
from junip3r.labeller.config.parser import InstanceTypeResolver
from junip3r.labeller.data.repository.selection import SelectionRepository
from junip3r.labeller.model.app_model import AppModel
from junip3r.labeller.model.label_model import LabelModel
from junip3r.setup.data.repository.abc import ISetupConfigRepository
from junip3r.setup.data.types.abc import ISetupInstanceType
from junip3r.setup.data.types.data import SetupInstanceType
from junip3r.setup.model.config_model import ConfigState, ConfigModel, ConfigStateChangeFlags
from junip3r.setup.model.setup_preview_pose_image_model import SetupPreviewPoseImageModel
from junip3r.setup.preview.data.repository.setup_preview_image_repository import SetupImageRepository
from junip3r.setup.preview.data.repository.setup_preview_label_repository import SetupPreviewLabelRepository, \
    SetupPreviewConfigRepository
from junip3r.setup.preview.placeholder_image import load_image_rgb
from junip3r.setup.widgets.expected_instance_list import ExpectedInstanceList
from junip3r.setup.widgets.new_project_window import DEFAULT_TEMPLATES_ROOT
from junip3r.setup.widgets.preview_window import PreviewWindow
from junip3r.setup.widgets.setup_controls import SetupControls


class SetupMainWindow(QMainWindow):
    switch_to = Signal(str)
    closed = Signal()
    resolved_config_changed = Signal(list, list)

    def __init__(self, config_repository: ISetupConfigRepository, integrated: bool = False, parent=None):
        super().__init__(parent)

        self._model = ConfigModel(config_repository)
        self._state: ConfigState = ConfigState()

        self.image_repository = SetupImageRepository()
        self.config_repository = SetupPreviewConfigRepository()
        self.label_repository = SetupPreviewLabelRepository()
        self.selection_repository = SelectionRepository()

        self.label_model = LabelModel(self.config_repository, self.label_repository)
        self.preview_app_model = AppModel(self.image_repository, self.label_model, self.selection_repository)
        self.preview_pose_image_model = SetupPreviewPoseImageModel(self.preview_app_model)

        self._project_folder: Optional[Path] = None

        self.setWindowTitle("Junip3R Project Setup")

        menu_bar = self.menuBar()

        self.file_menu = menu_bar.addMenu("File")
        self.action_save_as_template = self.file_menu.addAction("Save as Template...")

        self.action_switch_to_frame_extractor = QAction("Add Video Frames", self)
        self.action_switch_to_labeller = QAction("Start Labelling", self)

        if integrated:
            self.window_menu = menu_bar.addMenu("Window")
            self.window_menu.addAction(self.action_switch_to_frame_extractor)
            self.window_menu.addAction(self.action_switch_to_labeller)

        content = QWidget()
        content_layout = QVBoxLayout(content)

        splitter = QSplitter(self)
        splitter.setOrientation(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        self.setup_controls = SetupControls(self)

        splitter.addWidget(self.setup_controls)

        right = QFrame()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.expected_instance_list = ExpectedInstanceList()
        right_layout.addWidget(self.expected_instance_list)

        self.btn_choose_preview_image = QPushButton("Choose Preview Image...")
        self.btn_choose_preview_image.setIcon(QIcon.fromTheme("emblem-photos"))
        self.btn_choose_preview_image.clicked.connect(self._choose_preview_image)
        right_layout.addWidget(self.btn_choose_preview_image)

        self.btn_open_preview = QPushButton("Open Preview \u2b95")
        self.btn_open_preview.clicked.connect(self._open_preview)
        right_layout.addWidget(self.btn_open_preview)

        self.btn_open_frame_extractor = QPushButton(u"Add Video Frames \u2b95")
        self.btn_open_frame_extractor.clicked.connect(self._switch_to_frame_extractor)
        right_layout.addWidget(self.btn_open_frame_extractor)

        splitter.addWidget(right)

        content_layout.addWidget(splitter)

        self.setCentralWidget(content)

        self.preview_window = PreviewWindow(self)
        self.preview_window.set_model(self.preview_pose_image_model)
        self.preview_window.set_mode(self._model.mode)

        self.action_switch_to_frame_extractor.triggered.connect(self._switch_to_frame_extractor)
        self.action_switch_to_labeller.triggered.connect(self._switch_to_labeller)
        self.action_save_as_template.triggered.connect(self._save_as_template)

        self._model.changed.connect(self.setup_controls.set_state)
        self._model.changed.connect(self.set_state)
        self.resolved_config_changed.connect(self.preview_pose_image_model.set_config)

        self.setup_controls.instance_type_selected.connect(self._model.select_instance_type)

        self.setup_controls.instance_type_added.connect(self._model.create_instance_type)
        self.setup_controls.member_added.connect(self._model.create_member)

        self.setup_controls.instance_type_removed.connect(self._model.remove_instance_type)
        self.setup_controls.member_removed.connect(self._model.remove_member)

        self.setup_controls.instance_type_renamed.connect(self._model.rename_instance_type)
        self.setup_controls.instance_type_color_changed.connect(self._model.set_instance_type_color)
        self.setup_controls.instance_types_reordered.connect(self._model.reorder_instance_types)

        self.setup_controls.bounding_box_mode_changed.connect(self._model.set_bounding_box_mode)

        self.setup_controls.member_renamed.connect(self._model.rename_member)
        self.setup_controls.member_color_changed.connect(self._model.set_member_color)
        self.setup_controls.members_reordered.connect(self._model.reorder_members)

        self.setup_controls.skeleton_line_added.connect(self._model.add_skeleton_line)
        self.setup_controls.skeleton_line_updated.connect(self._model.update_skeleton_line)
        self.setup_controls.skeleton_line_removed.connect(self._model.remove_skeleton_line)

        self.setup_controls.skeleton_color_changed.connect(self._model.set_skeleton_color)

        self.expected_instance_list.instance_added.connect(self._model.add_expected_instance_type)
        self.expected_instance_list.instance_removed.connect(self._model.remove_expected_instance_type)
        self.expected_instance_list.instances_reordered.connect(self._model.reorder_expected_instance_types)

        self._model.refresh()

    def set_project_folder(self, project_folder: Path):
        """Point the preview's image/label repositories at this project's own
        _labeller/preview/ folder. Both are settable-path, cache-free file facades (see
        SetupImageRepository, SetupPreviewLabelRepository) - once pointed here, they
        transparently pick up whatever's already there (e.g. copied from a template, or
        left over from a previous setup session), with no separate "restore" step:
        get_instances() maps the file through the current resolved instance types itself,
        degrading to empty (with a logged warning) if a hand-edited config.yaml no longer
        matches what was saved.
        """
        self._project_folder = project_folder
        preview_folder = project_folder / "_labeller" / "preview"
        self.image_repository.set_image_file(preview_folder / "image.png")
        self.label_repository.set_label_file(preview_folder / "labels.json")
        self.preview_pose_image_model.refresh()

    def set_state(self, state: ConfigState, flags: ConfigStateChangeFlags):
        self._state = state
        instance_types = resolve_instance_types(state.instance_types, state.mode)
        expected_instances = [
            resolved for _, setup_type in state.expected_instance_types
            if (resolved := next((it for it in instance_types if it.id == setup_type.id), None)) is not None
        ]
        self.resolved_config_changed.emit(instance_types, expected_instances)
        self.preview_pose_image_model.refresh()

        self.expected_instance_list.set_state(state, flags)

    def _open_preview(self):
        self.preview_window.show()
        self.preview_window.raise_()
        self.preview_window.activateWindow()

    def _choose_preview_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Preview Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*)",
        )
        if not file_path:
            return

        image = load_image_rgb(Path(file_path))
        if image is None:
            QMessageBox.critical(self, "Could Not Load Image", f"Failed to read image from '{file_path}'.")
            return

        self.image_repository.set_image(image)
        self.preview_pose_image_model.refresh()

    def _save_as_template(self):
        if self._project_folder is None:
            return

        name, ok = QInputDialog.getText(self, "Save as Template", "Template name:")
        name = name.strip()
        if not ok or not name:
            return

        template_folder = DEFAULT_TEMPLATES_ROOT / name
        if template_folder.exists():
            overwrite = QMessageBox.question(
                self,
                "Template Already Exists",
                f"A template named '{name}' already exists. Overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if overwrite != QMessageBox.StandardButton.Yes:
                return

        template_folder.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self._project_folder / "config.yaml", template_folder / "config.yaml")

        preview_folder = self._project_folder / "_labeller" / "preview"
        for filename in ("image.png", "labels.json"):
            source_file = preview_folder / filename
            if source_file.exists():
                shutil.copy2(source_file, template_folder / filename)

        QMessageBox.information(self, "Template Saved", f"Saved template '{name}'.")

    def _switch_to_frame_extractor(self):
        self.switch_to.emit("frame_extractor")

    def _switch_to_labeller(self):
        self.switch_to.emit("labeller")

    def closeEvent(self, event):
        # preview_window is a separate top-level window (parented to self only for
        # ownership, never embedded in a layout) - Qt doesn't cascade close() to it,
        # so it would otherwise keep floating after setup itself closes (standalone,
        # or via AppController.switch_to() closing this window when leaving setup).
        self.preview_window.close()
        self.closed.emit()


_MODE_BY_STRING = {"freeform": ConfigMode.FREEFORM, "yolo_pose": ConfigMode.YOLO_POSE, "yolo_detect": ConfigMode.YOLO_DETECT}


def resolve_instance_types(instance_types: Sequence[ISetupInstanceType], mode: str) -> List[InstanceType]:
    config_mode = _MODE_BY_STRING[mode]
    resolver = InstanceTypeResolver(config_mode)
    num_instance_types = len(instance_types)
    return [
        resolver.resolve_instance_type(SetupInstanceType.to_config(it, config_mode), index, num_instance_types)
        for index, it in enumerate(instance_types)
    ]
