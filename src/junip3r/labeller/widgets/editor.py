from copy import deepcopy
from typing import Optional, cast

from PySide6.QtCore import Qt, QObject, QEvent
from PySide6.QtGui import QAction, QKeySequence, QKeyEvent
from PySide6.QtWidgets import QWidget, QSplitter, QHBoxLayout, QSizePolicy, QVBoxLayout

from junip3r.labeller.model.context_model import ContextModel
from junip3r.labeller.model.delegate_model import DelegateModel
from junip3r.labeller.model.image_model import ImageModel
from junip3r.labeller.model.editor_model import EditorModel
from junip3r.labeller.widgets.image_navigation import ImageNavigation
from junip3r.labeller.widgets.pose_editor import PoseEditor
from junip3r.labeller.widgets.selection_controls import SelectionControls
from junip3r.labeller.widgets.yolo_export import YoloExport


class ModifierTracker(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._model: Optional[ImageModel] = None
        self._context_model: Optional[ContextModel] = None

    def set_model(self, model: Optional[ImageModel]):
        self._model = model

    def set_context_model(self, model: Optional[ContextModel]):
        self._context_model = model

    def eventFilter(self, watched, event):
        if self._model is None:
            return False

        if event.type() == QEvent.Type.KeyPress:
            event = cast(QKeyEvent, event)
            if event.key() == Qt.Key.Key_Control and not event.isAutoRepeat():
                if self._context_model is not None:
                    self._context_model.set_context_enabled(True)
            elif event.key() == Qt.Key.Key_Shift and not event.isAutoRepeat():
                if self._context_model is not None:
                    self._model.set_inspect_mode(True)
        elif event.type() == QEvent.Type.KeyRelease:
            event = cast(QKeyEvent, event)
            if event.key() == Qt.Key.Key_Control:
                if self._context_model is not None:
                    self._context_model.set_context_enabled(False)
            elif event.key() == Qt.Key.Key_Shift:
                self._model.set_inspect_mode(False)

        elif event.type() in (
            QEvent.Type.ApplicationDeactivate,
            QEvent.Type.WindowDeactivate,
        ):
            if self._context_model is not None:
                self._context_model.set_context_enabled(False)
            self._model.set_inspect_mode(False)

        return False


class Editor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.model: Optional[EditorModel] = None
        self.image_model: Optional[ImageModel] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(self)
        splitter.setOrientation(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = QWidget(splitter)

        left_size_policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        left_size_policy.setHorizontalStretch(1)
        left_size_policy.setVerticalStretch(0)
        left.setSizePolicy(left_size_policy)

        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.pose_editor = PoseEditor(left)
        left_layout.addWidget(self.pose_editor)

        self.image_navigation = ImageNavigation(left)
        left_layout.addWidget(self.image_navigation)

        splitter.addWidget(left)

        self.selection_controls = SelectionControls(splitter)
        splitter.addWidget(self.selection_controls)

        layout.addWidget(splitter)

        self.modifier_tracker = ModifierTracker(self)
        self.installEventFilter(self.modifier_tracker)

        self.act_left = QAction(self)
        self.act_left.setShortcuts([
            QKeySequence("Left"),
            QKeySequence("Shift+Left"),
            QKeySequence("Ctrl+Left"),
            QKeySequence("Ctrl+Shift+Left"),
        ])
        self.act_left.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.act_left.triggered.connect(self._previous_image)
        self.addAction(self.act_left)

        self.act_right = QAction(self)
        self.act_right.setShortcuts([
            QKeySequence("Right"),
            QKeySequence("Shift+Right"),
            QKeySequence("Ctrl+Right"),
            QKeySequence("Ctrl+Shift+Right"),
        ])
        self.act_right.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.act_right.triggered.connect(self._next_image)
        self.addAction(self.act_right)

        self.act_up = QAction(self)
        self.act_up.setShortcut(QKeySequence(Qt.Key.Key_Up))
        self.act_up.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.act_up.triggered.connect(self._previous_point)
        self.addAction(self.act_up)

        self.act_down = QAction(self)
        self.act_down.setShortcuts([QKeySequence(Qt.Key.Key_Down), QKeySequence(Qt.Key.Key_Space)])
        self.act_down.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.act_down.triggered.connect(self._next_point)
        self.addAction(self.act_down)

        self.copy_action = QAction(self)
        self.copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        self.copy_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.copy_action.triggered.connect(self._copy_instance)
        self.addAction(self.copy_action)

        self.paste_action = QAction(self)
        self.paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        self.paste_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.paste_action.triggered.connect(self._paste_instance)
        self.addAction(self.paste_action)

        self.delete_action = QAction(self)
        self.delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        self.delete_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.delete_action.triggered.connect(self._delete_instance)
        self.addAction(self.delete_action)

        self.undo_action = QAction(self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.undo_action.triggered.connect(self._undo)
        self.addAction(self.undo_action)

        self.redo_action = QAction(self)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.redo_action.triggered.connect(self._redo)
        self.addAction(self.redo_action)

    def set_model(self, model: Optional[EditorModel]):
        self.model = model

        self.image_navigation.set_model(self.model)

        self.image_model = ImageModel(model) if model is not None else None
        self.modifier_tracker.set_model(self.image_model)

        delegate_model = DelegateModel(self.image_model) if self.image_model is not None else None
        self.pose_editor.set_model(delegate_model)
        self.selection_controls.set_model(delegate_model)

        context_model = ContextModel(model) if model is not None else None
        self.pose_editor.set_context_model(context_model)
        self.modifier_tracker.set_context_model(context_model)

    def export_yolo(self):
        dialog = YoloExport(self.model._model, self)
        dialog.exec()

    def _next_image(self):
        if self.model is not None:
            self.model.next_image()

    def _previous_image(self):
        if self.model is not None:
            self.model.previous_image()

    def _next_point(self):
        if self.image_model is not None:
            self.image_model.select_next_point()

    def _previous_point(self):
        if self.image_model is not None:
            self.image_model.select_previous_point()

    def _copy_instance(self):
        if self.image_model is None:
            return
        instance_id, _ = self.image_model.get_selection()
        if instance_id is None:
            return
        instance = self.image_model.get_instance(instance_id)
        self._copied_instance = deepcopy(instance)

    def _paste_instance(self):
        if self.image_model is None:
            return
        if self._copied_instance is None:
            return
        self.image_model.paste_instance(self._copied_instance)

    def _delete_instance(self):
        if self.image_model is None:
            return
        instance_id, _ = self.image_model.get_selection()
        if instance_id is None:
            return
        self.image_model.delete_instance(instance_id)

    def _undo(self):
        if self.image_model is not None:
            self.image_model.undo()

    def _redo(self):
        if self.image_model is not None:
            self.image_model.redo()
