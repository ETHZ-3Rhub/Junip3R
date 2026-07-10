from typing import Optional

from PySide6.QtCore import Qt, QObject, QEvent, QPointF
from PySide6.QtWidgets import QWidget

from junip3r.labeller.layout.pose_editor import Ui_PoseEditor
from junip3r.labeller.model.image_model import ImageModel


class PoseEditor(Ui_PoseEditor, QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.model: Optional[ImageModel] = None

        self.frm_context.setVisible(False)

        self.watch_widget_tree(self.frm_context)
        self.watch_widget_tree(self.frm_post_processing)

        self.sld_brightness.setMinimum(0)
        self.sld_brightness.setMaximum(100)
        self.sld_contrast.setMinimum(0)
        self.sld_contrast.setMaximum(100)

        self.sld_brightness.setValue(50)
        self.sld_contrast.setValue(50)

        self.sld_brightness.valueChanged.connect(self._set_settings)
        self.sld_contrast.valueChanged.connect(self._set_settings)

        self.sld_context.sliderMoved.connect(self._set_context_pos)

        self.btn_restore_preferences.clicked.connect(self._restore_settings)

    def set_model(self, model: ImageModel):
        self.model = model
        self.pose_image.set_model(model)

        if self.model is not None:
            self.model.settings_changed.connect(self._settings_changed)
            self._settings_changed(*self.model.get_settings())
            self.model.context_mode_changed.connect(self._context_mode_changed)

    def _set_settings(self):
        if self.model is None:
            return

        brightness = self.sld_brightness.value() / 100 - 0.5
        contrast = self.sld_contrast.value() / 100 - 0.5
        self.model.set_settings(brightness, contrast)

    def _settings_changed(self, brightness: float, contrast: float):
        self.sld_brightness.setValue(int((brightness + 0.5) * 100))
        self.sld_contrast.setValue(int((contrast + 0.5) * 100))

    def _set_context_pos(self, value: int):
        if self.model is None:
            return

        self.model.set_context_pos(value)

    def _context_mode_changed(self, context_loaded: bool, context_mode: bool, context_pos: int):
        self.stk_context.setCurrentIndex(0 if context_loaded else 1)

        if context_loaded and context_mode:
            str_context_pos = f"{context_pos:+d}" if context_pos != 0 else "0"
            self.lbl_context_pos.setText(str_context_pos)
            context = self.model.get_context()

            if context:
                before, current, after = context
                len_before = len(before)
                len_after = len(after)

                self.sld_context.setMinimum(-len_before)
                self.sld_context.setMaximum(len_after)

                if len_before > 0:
                    self.lbl_context_min.setVisible(True)
                    self.lbl_context_min.setText(f"-{len_before}")
                else:
                    self.lbl_context_min.setVisible(False)

                if len_after > 0:
                    self.lbl_context_max.setVisible(True)
                    self.lbl_context_max.setText(f"+{len_after}")
                else:
                    self.lbl_context_max.setVisible(False)

        self.frm_context.setVisible(context_mode)
        self.sld_context.setValue(context_pos)

    def _restore_settings(self):
        if self.model is None:
            return

        self.model.set_settings(0.0, 0.0)

    def watch_widget_tree(self, widget: QWidget) -> None:
        """Watch mouse movement on widget and all current descendants."""
        widget.setMouseTracking(True)
        widget.installEventFilter(self)

        for child in widget.findChildren(QWidget):
            child.setMouseTracking(True)
            child.installEventFilter(self)

    def eventFilter(self, watched, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseMove:
            # Map the event position from the hovered widget to the image label.
            global_pos = watched.mapToGlobal(event.position().toPoint())
            image_pos = self.pose_image.mapFromGlobal(global_pos)

            self.pose_image.handle_mouse_move(image_pos)

        # Do not consume the event. Sliders and other controls still receive it.
        return False
