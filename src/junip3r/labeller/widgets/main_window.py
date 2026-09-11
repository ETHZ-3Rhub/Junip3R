from typing import Optional

from PySide6.QtCore import Signal

from junip3r.common.config.abc import ConfigMode
from junip3r.labeller.data.repository.abc import IContextRepository
from junip3r.labeller.export.yolo.set_split import ISetSplitRepository
from junip3r.labeller.export.yolo.widgets.yolo_export_dialog import YoloExportDialog
from junip3r.labeller.layout.labeller_layout import EditorMainWindowLayout
from junip3r.labeller.model.app_model import AppModel
from junip3r.labeller.model.context_model import ContextModel
from junip3r.labeller.model.image_settings_model import ImageSettingsModel
from junip3r.labeller.model.pose_image_model import PoseImageModel


class EditorMainWindow(EditorMainWindowLayout):
    switch_to = Signal(str)
    closed = Signal()

    def __init__(self, show_frame_extractor: bool = False, parent=None):
        super().__init__(show_frame_extractor, parent)

        self.show_frame_extractor = show_frame_extractor
        self._model: Optional[AppModel] = None
        self._context_model: Optional[ContextModel] = None
        self._set_split_repository: Optional[ISetSplitRepository] = None

        self.action_export_as_yolo_dataset.triggered.connect(self.export_yolo_dataset)

        if self.show_frame_extractor:
            self.action_switch_to_frame_extractor.triggered.connect(self.switch_to_frame_extractor)
            self.btn_open_frame_extractor.clicked.connect(self.switch_to_frame_extractor)
        else:
            self.btn_open_frame_extractor.hide()

    def set_model(self, model: AppModel, context_repository: Optional[IContextRepository] = None,
                  image_settings_model: Optional[ImageSettingsModel] = None):
        self._model = model
        self._context_model = ContextModel(context_repository) if context_repository is not None else None

        pose_image_model = PoseImageModel(model)

        if self._context_model is not None:
            pose_image_model.image_navigation_state_changed.connect(self._context_model.set_image_navigation_state)

        self.editor.set_model(pose_image_model, self._context_model, image_settings_model)

        if model.get_num_images() > 0:
            self.stk_content.setCurrentIndex(0)
        else:
            self.stk_content.setCurrentIndex(1)

    def set_mode(self, mode: ConfigMode):
        self.editor.set_mode(mode)

    def set_set_split_repository(self, set_split_repository: ISetSplitRepository):
        self._set_split_repository = set_split_repository

    def switch_to_frame_extractor(self):
        self.switch_to.emit("frame_extractor")

    def export_yolo_dataset(self):
        if self._model is None or self._set_split_repository is None:
            return
        dialog = YoloExportDialog(self._model, self._set_split_repository, self)
        dialog.exec_()

    def closeEvent(self, event):
        if self._context_model is not None:
            self._context_model.shutdown()
        self.closed.emit()
