from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel


class AutoAnnotatedOverlay(QLabel):
    """Big "AUTO" label shown over the pose editor when the current image is tagged as
    model-generated (see model/annotation_source.py) - purely decorative, so it stays
    mouse-transparent rather than intercepting clicks meant for the pose image beneath it.
    """

    def __init__(self, parent=None):
        super().__init__("AUTO", parent)

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet(
            "color: #ffdd00;"
            "background-color: rgba(0, 0, 0, 140);"
            "font-size: 28px;"
            "font-weight: bold;"
            "padding: 4px 14px;"
            "border-radius: 4px;"
        )
