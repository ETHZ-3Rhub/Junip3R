from typing import Optional, cast

from PySide6.QtCore import Qt, QObject, QEvent, Signal
from PySide6.QtGui import QAction, QKeySequence, QKeyEvent
from PySide6.QtWidgets import QWidget, QSplitter, QHBoxLayout, QSizePolicy, QVBoxLayout

from junip3r.labeller.model.context_model import ContextModel
from junip3r.labeller.model.image_settings_model import ImageSettingsModel
from junip3r.labeller.model.pose_image_model import PoseImageModel
from junip3r.labeller.widgets.image_navigation import ImageNavigation
from junip3r.labeller.widgets.pose_editor import PoseEditor
from junip3r.labeller.widgets.selection_controls import SelectionControls


class ModifierTracker(QObject):
    set_inspect_all = Signal(bool)
    set_context_mode = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.KeyPress:
            event = cast(QKeyEvent, event)
            if event.key() == Qt.Key.Key_Shift and not event.isAutoRepeat():
                self.set_inspect_all.emit(True)
            elif event.key() == Qt.Key.Key_Control and not event.isAutoRepeat():
                self.set_context_mode.emit(True)
        elif event.type() == QEvent.Type.KeyRelease:
            event = cast(QKeyEvent, event)
            if event.key() == Qt.Key.Key_Shift:
                self.set_inspect_all.emit(False)
            elif event.key() == Qt.Key.Key_Control:
                self.set_context_mode.emit(False)
        elif event.type() in (
                QEvent.Type.ApplicationDeactivate,
                QEvent.Type.WindowDeactivate,
        ):
            self.set_inspect_all.emit(False)
            self.set_context_mode.emit(False)

        return False

class Editor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.model: Optional[PoseImageModel] = None

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
        self.pose_editor.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding))
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
        self.addAction(self.act_left)

        self.act_right = QAction(self)
        self.act_right.setShortcuts([
            QKeySequence("Right"),
            QKeySequence("Shift+Right"),
            QKeySequence("Ctrl+Right"),
            QKeySequence("Ctrl+Shift+Right"),
        ])
        self.act_right.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.addAction(self.act_right)

        self.act_up = QAction(self)
        self.act_up.setShortcut(QKeySequence(Qt.Key.Key_Up))
        self.act_up.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.addAction(self.act_up)

        self.act_down = QAction(self)
        self.act_down.setShortcuts([QKeySequence(Qt.Key.Key_Down), QKeySequence(Qt.Key.Key_Space)])
        self.act_down.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.addAction(self.act_down)

        self.copy_action = QAction(self)
        self.copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        self.copy_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.addAction(self.copy_action)

        self.paste_action = QAction(self)
        self.paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        self.paste_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.addAction(self.paste_action)

        self.delete_action = QAction(self)
        self.delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        self.delete_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.addAction(self.delete_action)

        self.undo_action = QAction(self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.addAction(self.undo_action)

        self.redo_action = QAction(self)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.addAction(self.redo_action)

    def set_model(self, model: PoseImageModel, context_model: Optional[ContextModel] = None, image_settings_model: Optional[ImageSettingsModel] = None):
        self.model = model
        self.pose_editor.set_model(model, context_model, image_settings_model)
        self._connect_model()

    def _connect_model(self):
        assert self.model is not None

        self.model.image_navigation_state_changed.connect(self.image_navigation.set_state)
        self.image_navigation.image_selected.connect(self.model.set_image_index)
        self.image_navigation.set_state(self.model.image_navigation_state)

        self.selection_controls.instance_selected.connect(self.model.select_instance)
        self.selection_controls.member_selected.connect(self.model.select_member)
        self.selection_controls.instance_type_selected.connect(self.model.select_instance_type)
        self.selection_controls.instance_renamed.connect(self.model.rename_instance)
        self.model.image_state_changed.connect(self.selection_controls.set_image_state)

        self.act_left.triggered.connect(self.model.previous_image)
        self.act_right.triggered.connect(self.model.next_image)

        self.act_up.triggered.connect(self.model.previous_selection)
        self.act_down.triggered.connect(self.model.next_selection)

        self.copy_action.triggered.connect(self.model.copy_instance)
        self.paste_action.triggered.connect(self.model.paste_instance)
        self.delete_action.triggered.connect(self.model.delete_instance)

        self.undo_action.triggered.connect(self.model.undo)
        self.redo_action.triggered.connect(self.model.redo)

        self.modifier_tracker.set_inspect_all.connect(self.pose_editor.set_inspect_all)
        self.modifier_tracker.set_context_mode.connect(self.pose_editor.set_context_mode)

        self.model.refresh()
