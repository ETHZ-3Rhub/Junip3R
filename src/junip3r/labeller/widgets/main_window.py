from typing import Optional

from PySide6.QtCore import Signal

from junip3r.labeller.layout.labeller_layout import EditorMainWindowLayout
from junip3r.labeller.model.context_model import ContextModel
from junip3r.labeller.model.image_settings_model import ImageSettingsModel
from junip3r.labeller.model.pose_image_model import PoseImageModel


class EditorMainWindow(EditorMainWindowLayout):
    switch_to = Signal(str)
    closed = Signal()

    def __init__(self, show_frame_extractor: bool = False, parent=None):
        super().__init__(show_frame_extractor, parent)

        self.show_frame_extractor = show_frame_extractor

        #self.action_export_as_yolo_dataset.triggered.connect(self.export_yolo_dataset)

        if self.show_frame_extractor:
            self.action_switch_to_frame_extractor.triggered.connect(self.switch_to_frame_extractor)
            self.btn_open_frame_extractor.clicked.connect(self.switch_to_frame_extractor)
        else:
            self.btn_open_frame_extractor.hide()

    def set_model(self, model: PoseImageModel, context_model: Optional[ContextModel] = None, image_settings_model: Optional[ImageSettingsModel] = None):
        self.editor.set_model(model, context_model, image_settings_model)

        if model.get_num_images() > 0:
            self.stk_content.setCurrentIndex(0)
        else:
            self.stk_content.setCurrentIndex(1)

    def switch_to_frame_extractor(self):
        self.switch_to.emit("frame_extractor")

#    def export_yolo_dataset(self):
#        self.editor.export_yolo()

    def closeEvent(self, event):
        self.closed.emit()
