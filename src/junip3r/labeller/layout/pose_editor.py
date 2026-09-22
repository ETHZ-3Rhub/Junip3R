from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QGridLayout, QSizePolicy, QWidget

from junip3r.labeller.widgets.auto_annotated_overlay import AutoAnnotatedOverlay
from junip3r.labeller.widgets.context_overlay import ContextOverlay
from junip3r.labeller.widgets.image_settings_overlay import ImageSettingsOverlay
from junip3r.labeller.widgets.pose_image import PoseImage


class PoseEditorLayout(QWidget):
    _pose_image: PoseImage
    _context_overlay: ContextOverlay
    _settings_overlay: ImageSettingsOverlay
    _auto_annotated_overlay: AutoAnnotatedOverlay

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._build_layout()

    def _build_layout(self) -> None:
        grid_layout = QGridLayout(self)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(0)

        self._pose_image = self._build_pose_image(self)
        grid_layout.addWidget(self._pose_image, 0, 0)

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

        self._context_overlay = ContextOverlay(self)
        overlay_layout.addWidget(
            self._context_overlay, 0, 0,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )

        self._settings_overlay = ImageSettingsOverlay(self)
        overlay_layout.addWidget(
            self._settings_overlay, 0, 2,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
        )

        self._auto_annotated_overlay = AutoAnnotatedOverlay(self)
        overlay_layout.addWidget(
            self._auto_annotated_overlay, 1, 0,
            alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
        )

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
