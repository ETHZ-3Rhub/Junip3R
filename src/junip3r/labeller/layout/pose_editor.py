from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QGridLayout, QSizePolicy, QWidget

from junip3r.labeller.widgets.context_overlay import ContextOverlay
from junip3r.labeller.widgets.pose_image import PoseImage
from junip3r.labeller.widgets.settings_overlay import SettingsOverlay


class PoseEditorLayout(QWidget):
    pose_image: PoseImage
    context_overlay: ContextOverlay
    settings_overlay: SettingsOverlay

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._build_layout()

    def _build_layout(self) -> None:
        grid_layout = QGridLayout(self)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(0)

        self.pose_image = self._build_pose_image(self)
        grid_layout.addWidget(self.pose_image, 0, 0)

        overlay_layout = self._build_overlays()
        grid_layout.addLayout(overlay_layout, 0, 0)

    def _build_overlays(self) -> QGridLayout:
        overlay_layout = QGridLayout()
        overlay_layout.setContentsMargins(9, 9, 9, 9)
        overlay_layout.setSpacing(6)

        # Let the center expand, keeping the two panels in their corners.
        overlay_layout.setColumnStretch(0, 0)
        overlay_layout.setColumnStretch(1, 1)
        overlay_layout.setColumnStretch(2, 0)

        overlay_layout.setRowStretch(0, 0)
        overlay_layout.setRowStretch(1, 1)

        self.context_overlay = ContextOverlay(self)
        overlay_layout.addWidget(
            self.context_overlay, 0, 0,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )

        self.settings_overlay = SettingsOverlay(self)
        overlay_layout.addWidget(
            self.settings_overlay, 0, 2,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
        )

        #self.pose_image.lower()
        #self.context_overlay.raise_()
        #self.settings_overlay.raise_()

        return overlay_layout

    @staticmethod
    def _build_pose_image(parent: QWidget) -> PoseImage:
        pose_image = PoseImage(parent)
        pose_image.setMinimumSize(QSize(100, 100))
        pose_image.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        pose_image.setScaledContents(True)
        pose_image.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignTop
        )
        pose_image.setText("")
        return pose_image
