from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QWidget

from app.labeller.model.pose_editor.controller import Controller
from app.labeller.data.app_model import AppModel
from app.labeller.layout.editor import Ui_Editor
from app.labeller.model.pose_editor.pose_editor_model import PoseEditorModel
from app.labeller.widgets.yolo_export import YoloExport


class Editor(Ui_Editor, QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.model: Optional[AppModel] = None
        self.pose_editor_model: Optional[PoseEditorModel] = None

        self.act_left = QAction(self)
        self.act_left.setShortcut(QKeySequence(Qt.Key.Key_Left))
        self.act_left.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.act_left.triggered.connect(self._previous_image)
        self.addAction(self.act_left)

        self.act_right = QAction(self)
        self.act_right.setShortcut(QKeySequence(Qt.Key.Key_Right))
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

        self.auto_zoom_action = QAction(self)
        self.auto_zoom_action.setShortcut(QKeySequence(Qt.Key.Key_Q))
        self.auto_zoom_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.auto_zoom_action.triggered.connect(self.pose_editor.pose_image.auto_zoom)
        self.addAction(self.auto_zoom_action)

    def set_model(self, model: AppModel):
        self.model = model
        self.pose_editor_model = PoseEditorModel(model, Controller(model))
        self.pose_editor.set_model(self.pose_editor_model)
        self.selection_controls.set_model(self.pose_editor_model)
        self.image_navigation.set_model(self.model)

    def export_yolo(self):
        print("Exporting YOLO")
        dialog = YoloExport(self.model, self)
        dialog.exec()

    def _next_image(self):
        if self.model is not None:
            self.model.next_image()

    def _previous_image(self):
        if self.model is not None:
            self.model.previous_image()

    def _next_point(self):
        if self.pose_editor_model is not None:
            self.pose_editor_model.next_point()

    def _previous_point(self):
        if self.pose_editor_model is not None:
            self.pose_editor_model.previous_point()

    def _copy_instance(self):
        if self.pose_editor_model is None:
            return
        self.pose_editor_model.copy_instance()

    def _paste_instance(self):
        if self.pose_editor_model is None:
            return
        self.pose_editor_model.paste_instance()

    def _delete_instance(self):
        if self.pose_editor_model is None:
            return
        instance = self.pose_editor_model.get_selected_instance()
        if instance.instance_id is None:
            return
        instance.delete()

    def _undo(self):
        if self.pose_editor_model is not None:
            self.pose_editor_model.undo()

    def _redo(self):
        if self.pose_editor_model is not None:
            self.pose_editor_model.redo()
