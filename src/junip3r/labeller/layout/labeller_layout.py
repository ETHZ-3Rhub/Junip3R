from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QStackedWidget, QSpacerItem, QSizePolicy, QLabel, \
    QHBoxLayout, QPushButton

from junip3r.labeller.widgets.editor import Editor


class EditorMainWindowLayout(QMainWindow):
    stk_content: QStackedWidget
    editor: Editor
    btn_open_frame_extractor: QPushButton

    action_export_as_yolo_dataset: QAction
    action_switch_to_frame_extractor: QAction

    def __init__(self, show_frame_extractor: bool = False, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Junip3r Labeller")
        self.resize(800, 600)

        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        export_menu = file_menu.addMenu("Export as...")

        self.action_export_as_yolo_dataset = QAction("Export as YOLO Dataset", self)
        export_menu.addAction(self.action_export_as_yolo_dataset)

        self.action_switch_to_frame_extractor = QAction("Add Video Frames", self)
        if show_frame_extractor:
            window_menu = menu_bar.addMenu("Window")
            window_menu.addAction(self.action_switch_to_frame_extractor)

        self.stk_content = QStackedWidget(self)

        frm_editor = QWidget(self)
        frm_editor_layout = QVBoxLayout(frm_editor)

        self.editor = Editor(self)
        frm_editor_layout.addWidget(self.editor)

        self.stk_content.addWidget(frm_editor)

        frm_no_images = QWidget(self)
        frm_no_images_layout_outer = QHBoxLayout(frm_no_images)
        frm_no_images_layout_outer.setContentsMargins(0, 0, 0, 0)

        frm_no_images_layout_outer.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        frm_no_images_layout_inner = QVBoxLayout(frm_no_images)

        frm_no_images_layout_inner.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        lbl_no_images = QLabel("No images found in project folder", frm_no_images)
        lbl_no_images.setAlignment(Qt.AlignmentFlag.AlignCenter)
        frm_no_images_layout_inner.addWidget(lbl_no_images)

        self.btn_open_frame_extractor = QPushButton("Add Video Frames", frm_no_images)
        frm_no_images_layout_inner.addWidget(self.btn_open_frame_extractor)

        frm_no_images_layout_inner.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        frm_no_images_layout_outer.addLayout(frm_no_images_layout_inner)

        frm_no_images_layout_outer.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.stk_content.addWidget(frm_no_images)

        self.setCentralWidget(self.stk_content)