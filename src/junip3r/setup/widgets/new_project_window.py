import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
import yaml
from PySide6.QtCore import Qt, QAbstractListModel, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QVBoxLayout, QFormLayout, QLineEdit, QToolButton, QWidgetAction, \
    QSizePolicy, QHBoxLayout, QListView, QLabel, QFrame, QDialogButtonBox, QComboBox, \
    QStackedWidget, QWidget, QMessageBox, QPushButton

from junip3r.common.config.abc import ConfigMode
from junip3r.common.labels.serialization import LabelSerializer
from junip3r.labeller.config.parser import parse_config
from junip3r.labeller.data.repository.label import InstanceMapper
from junip3r.labeller.config.data import InstanceType
from junip3r.labeller.data.types.data import Instance
from junip3r.labeller.model.camera_model import CameraModel
from junip3r.labeller.widgets.pose_image import PoseImage
from junip3r.setup.preview.placeholder_image import load_image_rgb, load_placeholder_image
from junip3r.setup.widgets.preview_pose_image_controller import PreviewPoseImageController
from junip3r.setup.model.preview_pose_image_model import PreviewPoseImageModel

logger = logging.getLogger(__name__)

# Matches the QComboBox item data set up in NewProjectWindow's mode dropdown below.
_MODE_NAMES = {
    ConfigMode.JUNIPER: "junip3r",
    ConfigMode.YOLO_DETECT: "yolo_detect",
    ConfigMode.YOLO_POSE: "yolo_pose",
}

_LOCAL_APPDATA = os.environ.get("LOCALAPPDATA")
DEFAULT_TEMPLATES_ROOT = (
    Path(_LOCAL_APPDATA) / "ETH3RHub" / "Junip3R" / "templates"
    if _LOCAL_APPDATA is not None else Path.home() / ".junip3r" / "templates"
)


@dataclass
class Preset:
    name: str
    mode: Optional[str] = None
    image: Optional[np.ndarray] = None
    instance_types: List[InstanceType] = field(default_factory=list)
    instances: List[Instance] = field(default_factory=list)

    config_file: Optional[Path] = None


EMPTY_PRESET = Preset("Empty")


def load_preset(name: str, config_file: Path, image_file: Path, labels_file: Path) -> Preset:
    """Build a Preset from a config file plus an optional image/labels pair.

    Only config_file is required. image_file and labels_file may not exist -
    a project may have no preview image yet, or instance types but no example
    instances drawn (LabelSerializer.write_instances deletes labels.json when
    there are no instances to write) - both are valid, partial preview states.
    """
    if not config_file.exists():
        raise ValueError("Preset is missing its config file")

    config_dict = yaml.safe_load(open(config_file, 'r'))
    labeller_config = parse_config(config_dict)
    instance_types = labeller_config.instance_types

    mode = _MODE_NAMES[labeller_config.mode] if len(instance_types) > 0 else None

    image = load_image_rgb(image_file) if image_file.exists() else None

    instances = []
    if labels_file.exists():
        data = LabelSerializer().load_instances(labels_file)
        instances = InstanceMapper(instance_types).from_data(data)

    return Preset(name, mode, image, instance_types, instances, config_file)


def load_saved_preset(preset_folder: Path) -> Preset:
    return load_preset(
        preset_folder.name,
        preset_folder / "config.yaml",
        preset_folder / "image.png",
        preset_folder / "labels.json",
    )


def load_project_as_preset(project_folder: Path) -> Preset:
    preview_folder = project_folder / "_labeller" / "preview"
    return load_preset(
        project_folder.name,
        project_folder / "config.yaml",
        preview_folder / "image.png",
        preview_folder / "labels.json",
    )


def discover_saved_presets(templates_root: Path = DEFAULT_TEMPLATES_ROOT) -> List[Preset]:
    if not templates_root.exists():
        return []

    presets = []
    for preset_folder in sorted(templates_root.iterdir()):
        if not preset_folder.is_dir():
            continue
        try:
            presets.append(load_saved_preset(preset_folder))
        except (ValueError, OSError, yaml.YAMLError) as e:
            logger.warning(f"Skipping invalid template '{preset_folder.name}': {e}")
    return presets


class PresetModel(QAbstractListModel):
    PresetRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.presets: List[Preset] = []

    def set_presets(self, presets: List[Preset]):
        self.beginResetModel()
        self.presets = presets
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self.presets)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        preset = self.presets[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return preset.name
        elif role == PresetModel.PresetRole:
            return preset
        return None


class InstanceTypeModel(QAbstractListModel):
    InstanceTypeRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.instance_types: List[InstanceType] = []

    def set_instance_types(self, instance_types: List[InstanceType]):
        self.beginResetModel()
        self.instance_types = instance_types
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self.instance_types)

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        instance_type = self.instance_types[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return instance_type.name
        elif role == InstanceTypeModel.InstanceTypeRole:
            return instance_type
        return None


class NewProjectWindow(QWidget):
    setup_requested = Signal(str)
    open_project_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        presets = [EMPTY_PRESET] + discover_saved_presets()

        self.preset_model = PresetModel()
        self.preset_model.set_presets(presets)

        self.instance_type_model = InstanceTypeModel()

        # Default location user home
        location = str(Path.home() / "LabellingProject")

        layout = QVBoxLayout(self)

        content_layout = QHBoxLayout()

        frm_presets = QFrame()
        frm_presets.setFrameShape(QFrame.Shape.StyledPanel)
        frm_presets.setFrameShadow(QFrame.Shadow.Raised)
        presets_layout = QVBoxLayout(frm_presets)
        lbl_presets = QLabel("Presets")
        presets_layout.addWidget(lbl_presets)
        self.lst_presets = QListView()
        self.setStyleSheet("QListView { border: none; }")
        self.lst_presets.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        self.lst_presets.setModel(self.preset_model)
        self.lst_presets.selectionModel().currentChanged.connect(self._set_preset)
        presets_layout.addWidget(self.lst_presets)

        self.btn_load_project = QPushButton("Load Existing Project...")
        self.btn_load_project.clicked.connect(self._load_project_as_template)
        presets_layout.addWidget(self.btn_load_project)

        content_layout.addWidget(frm_presets)

        frm_config = QFrame()
        frm_config.setFrameShape(QFrame.Shape.StyledPanel)
        frm_config.setFrameShadow(QFrame.Shadow.Raised)
        config_layout = QVBoxLayout(frm_config)

        form_layout = QFormLayout()
        self.txt_location = QLineEdit()
        self.txt_location.setText(location)

        self.btn_select_folder = QToolButton()
        self.btn_select_folder.setIcon(QIcon.fromTheme("folder"))
        self.btn_select_folder.setToolTip("Select folder")
        self.btn_select_folder.setAutoRaise(True)
        self.btn_select_folder.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_select_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_folder.clicked.connect(self._select_folder)

        self.act_select_folder = QWidgetAction(self.txt_location)
        self.act_select_folder.setDefaultWidget(self.btn_select_folder)

        self.txt_location.addAction(
            self.act_select_folder,
            QLineEdit.ActionPosition.TrailingPosition,
        )

        form_layout.addRow("Location:", self.txt_location)

        self.dpd_mode = QComboBox()
        self.dpd_mode.addItem("YOLO Pose Estimation", "yolo_pose")
        self.dpd_mode.addItem("YOLO Object Detection", "yolo_detect")
        self.dpd_mode.addItem("Junip3R", "junip3r")

        form_layout.addRow("Mode:", self.dpd_mode)

        config_layout.addLayout(form_layout)

        self.stk_preview = QStackedWidget()

        preview_page = QWidget()
        preview_layout = QHBoxLayout(preview_page)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        #spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        #config_layout.addItem(spacer)

        frm_instance_types = QFrame()
        frm_instance_types.setFrameShape(QFrame.Shape.StyledPanel)
        frm_instance_types.setFrameShadow(QFrame.Shadow.Raised)

        instance_types_layout = QVBoxLayout(frm_instance_types)

        lbl_instance_types = QLabel("Instance Types in Preset:")
        instance_types_layout.addWidget(lbl_instance_types)

        self.lst_instance_types = QListView()
        self.lst_instance_types.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        self.lst_instance_types.setModel(self.instance_type_model)
        instance_types_layout.addWidget(self.lst_instance_types)

        preview_layout.addWidget(frm_instance_types)

        frm_preview_pose_image = QFrame()
        frm_preview_pose_image.setFrameShape(QFrame.Shape.StyledPanel)
        frm_preview_pose_image.setFrameShadow(QFrame.Shadow.Raised)

        preview_pose_image_layout = QVBoxLayout(frm_preview_pose_image)
        preview_pose_image_layout.setContentsMargins(0, 0, 0, 0)

        self.preview_pose_image = PoseImage(self)
        self.preview_pose_image.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.preview_camera_model = CameraModel()
        self.preview_camera_model.set_view_size(self.preview_pose_image.width(), self.preview_pose_image.height())
        self.preview_pose_image.resized.connect(self.preview_camera_model.set_view_size)
        self.preview_camera_model.changed.connect(self.preview_pose_image.set_camera_state)

        self.preview_pose_image_controller = PreviewPoseImageController(self.preview_camera_model)
        self.preview_pose_image.mouse_pressed.connect(self.preview_pose_image_controller.mouse_pressed)
        self.preview_pose_image.mouse_released.connect(self.preview_pose_image_controller.mouse_released)
        self.preview_pose_image.mouse_moved.connect(self.preview_pose_image_controller.mouse_moved)
        self.preview_pose_image.wheel_moved.connect(self.preview_pose_image_controller.wheel_moved)
        self.preview_pose_image_controller.operation_state_changed.connect(self.preview_pose_image.set_operation_state)

        self.preview_pose_image_model = PreviewPoseImageModel()
        self.preview_pose_image_model.image_state_changed.connect(self.preview_pose_image.set_image_state)

        preview_pose_image_layout.addWidget(self.preview_pose_image)

        preview_layout.addWidget(frm_preview_pose_image)
        self.stk_preview.addWidget(preview_page)

        lbl_no_preview = QLabel("No Preview Available")
        lbl_no_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stk_preview.addWidget(lbl_no_preview)

        config_layout.addWidget(self.stk_preview)

        content_layout.addWidget(frm_config, stretch=1)

        layout.addLayout(content_layout)

        btn_row = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        btn_row.accepted.connect(self.accept)
        btn_row.rejected.connect(self.close)
        layout.addWidget(btn_row)

        self.act_select_folder.triggered.connect(self._select_folder)

        self.lst_presets.setCurrentIndex(self.preset_model.index(0, 0))

        self.preview_camera_model.refresh()

    def _set_preset(self):
        preset = self.lst_presets.currentIndex().data(PresetModel.PresetRole)
        if preset.image is None and len(preset.instance_types) == 0:
            self.stk_preview.setCurrentIndex(1)
        else:
            self.stk_preview.setCurrentIndex(0)
        if preset.mode:
            self.dpd_mode.setCurrentIndex(self.dpd_mode.findData(preset.mode))
            self.dpd_mode.setEnabled(False)
        else:
            self.dpd_mode.setEnabled(True)
        self.instance_type_model.set_instance_types(preset.instance_types)
        # Fall back to the generic placeholder so the instance layout is still viewable
        # for a preset/project with instance types but no preview image of its own.
        image = preset.image
        if image is None and len(preset.instance_types) > 0:
            image = load_placeholder_image()
        self.preview_pose_image_model._image = image
        self.preview_pose_image_model._instance_types = preset.instance_types
        self.preview_pose_image_model._instances = preset.instances
        self.preview_pose_image_model.refresh()

    def _load_project_as_template(self):
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Project Config File",
            "",
            "Junip3R Config File (*.yaml)",
        )
        if not file_path:
            return

        project_folder = Path(file_path).parent
        try:
            preset = load_project_as_preset(project_folder)
        except ValueError as e:
            QMessageBox.critical(self, "Could Not Load Project", str(e))
            return

        presets = self.preset_model.presets + [preset]
        self.preset_model.set_presets(presets)
        self.lst_presets.setCurrentIndex(self.preset_model.index(len(presets) - 1, 0))

    def _select_folder(self):
        from PySide6.QtWidgets import QFileDialog

        current_folder = Path(self.txt_location.text())
        while not current_folder.exists():
            current_folder = current_folder.parent
            if current_folder == current_folder.parent:
                current_folder = Path.home()
                break

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Project Location",
            str(current_folder),
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )
        if folder:
            self.txt_location.setText(folder)

    def _confirm_overwrite(self, location: Path) -> bool:
        message_box = QMessageBox()
        message_box.setIcon(QMessageBox.Icon.Question)
        message_box.setWindowTitle("Overwrite Project")
        message_box.setText(f"The folder '{location}' already exists and is not empty.\nDo you want to overwrite it?")
        message_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        message_box.setDefaultButton(QMessageBox.StandardButton.Yes)
        return message_box.exec() == QMessageBox.StandardButton.Yes

    def accept(self):
        if not self.txt_location.text():
            return

        location = Path(self.txt_location.text())
        preset = self.lst_presets.currentIndex().data(PresetModel.PresetRole)

        if location.exists() and list(location.iterdir()):
            if not self._confirm_overwrite(location):
                return

        Path(location).mkdir(parents=True, exist_ok=True)

        config_file = str(location / "config.yaml")

        if preset is EMPTY_PRESET:
            mode = self.dpd_mode.currentData()
            # Create empty config_file
            with open(config_file, "w") as f:
                yaml.dump({"mode": mode, "instance_types": [], "instances": []}, f)
            self.setup_requested.emit(config_file)
        else:
            # Copy preset files to location
            assert preset.config_file is not None
            import shutil
            shutil.copy(preset.config_file, Path(location) / "config.yaml")

            if preset.image is not None or preset.instances:
                preview_folder = location / "_labeller" / "preview"
                preview_folder.mkdir(parents=True, exist_ok=True)
                if preset.image is not None:
                    cv2.imwrite(str(preview_folder / "image.png"), cv2.cvtColor(preset.image, cv2.COLOR_RGB2BGR))
                data = InstanceMapper([]).to_data(preset.instances)
                LabelSerializer().write_instances(preview_folder / "labels.json", data)

            message_box = QMessageBox()
            message_box.setIcon(QMessageBox.Icon.Question)
            message_box.setWindowTitle("Continue Setup?")
            message_box.setText(f"Do you want to continue setting up the project or use the preset as is?")
            btn_setup = QPushButton("Continue Setup")
            btn_finished = QPushButton("Use as is")
            message_box.addButton(btn_setup, QMessageBox.ButtonRole.AcceptRole)
            message_box.addButton(btn_finished, QMessageBox.ButtonRole.AcceptRole)
            message_box.setDefaultButton(btn_setup)
            message_box.exec()
            if message_box.clickedButton() == btn_finished:
                self.open_project_requested.emit(config_file)
            else:
                self.setup_requested.emit(config_file)
