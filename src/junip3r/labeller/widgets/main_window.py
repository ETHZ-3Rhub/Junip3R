from PySide6.QtCore import Signal

from junip3r.labeller.layout.labeller_layout import EditorMainWindowLayout
from junip3r.labeller.model.editor_model import EditorModel


class EditorMainWindow(EditorMainWindowLayout):
    switch_to = Signal(str)
    closed = Signal()

    def __init__(self, show_frame_extractor: bool = False, parent=None):
        super().__init__(show_frame_extractor, parent)

        self.show_frame_extractor = show_frame_extractor

        self.action_export_as_yolo_dataset.triggered.connect(self.export_yolo_dataset)

        if self.show_frame_extractor:
            self.action_switch_to_frame_extractor.triggered.connect(self.switch_to_frame_extractor)
            self.btn_open_frame_extractor.clicked.connect(self.switch_to_frame_extractor)
        else:
            self.btn_open_frame_extractor.hide()

    def set_model(self, model: EditorModel):
        if model.get_num_images() > 0:
            self.editor.set_model(model)
            self.stk_content.setCurrentIndex(0)
        else:
            self.editor.set_model(None)
            self.stk_content.setCurrentIndex(1)

    def switch_to_frame_extractor(self):
        self.switch_to.emit("frame_extractor")

    def export_yolo_dataset(self):
        self.editor.export_yolo()

    def closeEvent(self, event):
        self.closed.emit()
