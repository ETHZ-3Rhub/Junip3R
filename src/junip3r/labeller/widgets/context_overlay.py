from typing import Optional

from PySide6.QtCore import Qt, QSize, Slot
from PySide6.QtWidgets import QFrame, QSizePolicy, QVBoxLayout, QStackedWidget, QWidget, QHBoxLayout, QLabel, QSlider

from junip3r.labeller.model.context_model import ContextState, ContextModel


class ContextOverlay(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.model: Optional[ContextModel] = None

        self.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Maximum,
        )
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

        layout = QVBoxLayout(self)

        self.stk_content = QStackedWidget(self)

        page_context = QWidget()

        page_context_layout = QVBoxLayout(page_context)
        page_context_layout.setContentsMargins(0, 0, 0, 0)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        lbl_context_title = QLabel("Context", page_context)
        header_layout.addWidget(lbl_context_title)

        self.lbl_context_pos = QLabel("0", page_context)
        self.lbl_context_pos.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(self.lbl_context_pos)

        page_context_layout.addLayout(header_layout)

        # Context slider
        slider_layout = QHBoxLayout()
        slider_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_context_min = self._build_lbl_context_min(page_context)
        slider_layout.addWidget(self.lbl_context_min)

        self.sld_context = self._build_sld_context(page_context)
        slider_layout.addWidget(self.sld_context)

        self.lbl_context_max = self._build_lbl_context_max(page_context)
        slider_layout.addWidget(self.lbl_context_max)

        page_context_layout.addLayout(slider_layout)

        self.stk_content.addWidget(page_context)

        page_loading = self._build_context_loading_page()
        self.stk_content.addWidget(page_loading)

        layout.addWidget(self.stk_content)

        self.sld_context.valueChanged.connect(self._set_context_pos)

        self._context_changed(ContextState())

    def set_model(self, model: Optional[ContextModel]):
        if self.model is not None:
            self.model.changed.disconnect(self._context_changed)

        self.model = model

        if self.model is not None:
            self.model.changed.connect(self._context_changed)
        else:
            self._context_changed(ContextState())

    @staticmethod
    def _build_lbl_context_min(parent: QWidget) -> QLabel:
        lbl_context_min = QLabel("0", parent)
        return lbl_context_min

    @staticmethod
    def _build_lbl_context_max(parent: QWidget) -> QLabel:
        lbl_context_max = QLabel("0", parent)
        return lbl_context_max

    @staticmethod
    def _build_sld_context(parent: QWidget) -> QSlider:
        sld_context = QSlider(Qt.Orientation.Horizontal, parent)
        sld_context.setMinimumSize(QSize(50, 0))
        sld_context.setMinimum(-30)
        sld_context.setMaximum(30)
        sld_context.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )
        return sld_context

    @staticmethod
    def _build_context_loading_page() -> QWidget:
        page_loading = QWidget()

        page_loading_layout = QVBoxLayout(page_loading)

        lbl_context_loading = QLabel("Loading context...", page_loading)
        page_loading_layout.addWidget(lbl_context_loading)

        return page_loading

    @Slot()
    def _set_context_pos(self):
        if self.model is None:
            return

        value = self.sld_context.value()
        self.model.set_context_pos(value)

    @Slot(ContextState)
    def _context_changed(self, state: ContextState):
        self.stk_content.setCurrentIndex(0 if state.loaded else 1)

        str_context_pos = f"{state.pos:+d}" if state.pos != 0 else "0"
        self.lbl_context_pos.setText(str_context_pos)

        self.sld_context.setMinimum(state.min)
        self.sld_context.setMaximum(state.max)

        str_context_min = f"{state.min:+d}" if state.min != 0 else "0"
        self.lbl_context_min.setText(str_context_min)
        str_context_max = f"{state.max:+d}" if state.max != 0 else "0"
        self.lbl_context_max.setText(str_context_max)

        self.sld_context.setValue(state.pos)
