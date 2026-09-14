from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLayout,
                               QMainWindow, QMenu, QMenuBar, QPushButton, QSplitter, QStatusBar, QVBoxLayout, QWidget)

from junip3r.frame_extractor.widgets.extraction_controls import ExtractionControls
from junip3r.frame_extractor.widgets.frame_list import FrameList
from junip3r.frame_extractor.widgets.selection_controls import SelectionControls
from junip3r.frame_extractor.widgets.video_list import VideoList
from junip3r.frame_extractor.widgets.video_player import VideoPlayer


class FrameExtractorLayout(QMainWindow):
    action_open_setup: QAction
    action_open_labeller: QAction

    btn_add_videos: QPushButton
    video_list: VideoList
    selection_controls: SelectionControls

    video_player: VideoPlayer

    frame_list: FrameList
    extraction_controls: ExtractionControls
    btn_open_labeller: QPushButton

    menubar: QMenuBar
    menu_window: QMenu
    statusbar: QStatusBar

    def __init__(self, parent=None):
        super().__init__(parent)

        self.resize(1089, 703)
        self.setAcceptDrops(True)
        self.setWindowTitle("Junip3R Frame Extractor")

        self.action_open_setup = QAction("Open Project Setup", self)
        self.action_open_labeller = QAction("Open Labeller", self)

        central_widget = QWidget(self)
        horizontal_layout = QHBoxLayout(central_widget)

        splitter = QSplitter(central_widget)
        splitter.setOrientation(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(9)
        splitter.setChildrenCollapsible(False)

        splitter.addWidget(self._build_video_pane(splitter))
        self.video_player = VideoPlayer(splitter)
        splitter.addWidget(self.video_player)
        splitter.addWidget(self._build_frame_pane(splitter))

        horizontal_layout.addWidget(splitter)
        self.setCentralWidget(central_widget)

        self.menubar = self.menuBar()
        self.menu_window = self.menubar.addMenu("Window")
        self.menu_window.addAction(self.action_open_setup)
        self.menu_window.addAction(self.action_open_labeller)

        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)

    def _build_video_pane(self, parent: QWidget) -> QFrame:
        frame = QFrame(parent)
        frame.setMinimumSize(0, 0)
        frame.setFrameShape(QFrame.Shape.NoFrame)
        frame.setFrameShadow(QFrame.Shadow.Raised)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Videos", frame))

        self.btn_add_videos = QPushButton("Add Videos", frame)
        layout.addWidget(self.btn_add_videos)

        self.video_list = VideoList(frame)
        layout.addWidget(self.video_list)

        layout.addWidget(QLabel("Select Frames", frame))

        self.selection_controls = SelectionControls(frame)
        layout.addWidget(self.selection_controls)

        return frame

    def _build_frame_pane(self, parent: QWidget) -> QFrame:
        frame = QFrame(parent)
        frame.setMinimumSize(0, 0)
        frame.setFrameShape(QFrame.Shape.NoFrame)
        frame.setFrameShadow(QFrame.Shadow.Raised)

        layout = QVBoxLayout(frame)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Selected Frames", frame))

        self.frame_list = FrameList(frame)
        layout.addWidget(self.frame_list)

        layout.addWidget(QLabel("Extract Frames", frame))

        self.extraction_controls = ExtractionControls(frame)
        layout.addWidget(self.extraction_controls)

        self.btn_open_labeller = QPushButton("Next: Start Labelling \u2b95", frame)
        layout.addWidget(self.btn_open_labeller)

        return frame
