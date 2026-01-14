from typing import Optional

from PySide6 import QtGui
from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget

from app.labeller.data import AppModel
from app.labeller.layout import Ui_LabelEditor
from app.labeller.model.pose_editor.pose_editor_model import PoseEditorModel
from app.labeller.model.pose_editor.delegates import InstanceDelegate


class InstanceListModel(QAbstractListModel):
    InstanceIDRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, model: PoseEditorModel):
        super().__init__()
        self._model = model

        self._instances = []
        self._new_instance = None

        self._model.reset.connect(self.refresh)
        self._model.instance_added.connect(self._instance_added)
        self._model.instance_deleted.connect(self._instance_deleted)
        self._model.instance_updated.connect(self._instance_updated)

    def refresh(self):
        self.beginResetModel()
        self._instances = self._model.get_instances()
        self._new_instance = self._model.get_new_instance_delegate()
        self.endResetModel()

    def find_row_by_id(self, instance_id: Optional[str]) -> int:
        if instance_id is None:
            return len(self._instances)
        for i, instance in enumerate(self._instances):
            if instance.instance_id == instance_id:
                return i
        raise ValueError(f"Instance {instance_id} not found")

    def _instance_added(self, instance: InstanceDelegate):
        index = len(self._instances)
        self.beginInsertRows(QModelIndex(), index, index)
        self._instances.append(instance)
        self.endInsertRows()

    def _instance_deleted(self, instance_id: str):
        row = self.find_row_by_id(instance_id)
        self.beginRemoveRows(QModelIndex(), row, row)
        self._instances.pop(row)
        self.endRemoveRows()

    def _instance_updated(self, instance: InstanceDelegate):
        row = self.find_row_by_id(instance.instance_id)
        index = self.index(row)
        self._instances[row] = instance
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.FontRole])

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable

    def rowCount(self, parent=None):
        return len(self._instances) + 1

    def data(self, index, role=None):
        instance = self._new_instance if index.row() == len(self._instances) else self._instances[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return instance.name
        elif role == InstanceListModel.InstanceIDRole:
            return instance.instance_id
        elif role == Qt.ItemDataRole.FontRole:
            row = index.row()
            if row == len(self._instances):
                return QFont("Segoe UI", 12, italic=True)
        return None

    def setData(self, index, value, role=None):
        if role == Qt.ItemDataRole.EditRole:
            if value is None or value == "":
                return False
            row = index.row()
            instance = self._instances[row]
            self._model.set_instance_name(instance.instance_id, value)
            return True
        return False


class PointListModel(QAbstractListModel):
    def __init__(self, model: PoseEditorModel):
        super().__init__()
        self._model = model

        self._instance: Optional[InstanceDelegate] = None

        self._model.reset.connect(self.refresh)

    def refresh(self):
        self.beginResetModel()
        self._instance = self._model.get_instances()[0]
        self.endResetModel()

    def rowCount(self, parent=None):
        if self._instance is None:
            return 0
        return len(self._instance.members)

    def data(self, index, role=None):
        if self._instance is None:
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            return self._instance.members[index.row()].name
        return None


class LabelEditor(Ui_LabelEditor, QWidget):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setupUi(self)

        self.model: Optional[PoseEditorModel] = None
        self.app_model: Optional[AppModel] = None

        self.instance_list_model: Optional[InstanceListModel] = None
        self.point_list_model: Optional[PointListModel] = None

        self.frm_editor.layout().addWidget(self.pose_image, 0, 0, 2, 2)
        self.frm_editor.layout().addWidget(self.frm_post_processing, 0, 1, 1, 1)
        # Put frm_post_processing on top of the pose_image
        self.frm_post_processing.raise_()

        self.pose_image.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.lst_instances.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.lst_points.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.sld_brightness.setRange(0, 100)
        self.sld_brightness.setValue(50)
        self.sld_contrast.setRange(0, 100)
        self.sld_contrast.setValue(50)

        # Install event filter to prevent the instance type dropdown from changing the selected type when the user scrolls
        self.dpd_instance_type.installEventFilter(self)

        self.sld_image_number.setMinimum(1)
        self.sld_image_number.setMaximum(1)
        self.sld_image_number.valueChanged.connect(self._select_image)

        self.clipped_instance = None

    def set_model(self, model: PoseEditorModel, app_model: AppModel):
        self.model = model
        self.app_model = app_model

        self.instance_list_model = InstanceListModel(self.model)
        self.lst_instances.setModel(self.instance_list_model)
        self.instance_list_model.refresh()

        self.point_list_model = PointListModel(self.model)
        self.lst_points.setModel(self.point_list_model)
        self.point_list_model.refresh()

        self.app_model.image_changed.connect(self._image_changed)

        self.model.reset.connect(self._reset)
        self.model.selection_changed.connect(self._selection_changed)

        self.lst_instances.selectionModel().currentChanged.connect(self._select_instance)
        self.lst_points.selectionModel().currentChanged.connect(self._select_point)

        self.sld_image_number.setMinimum(1)
        self.sld_image_number.setMaximum(self.app_model.get_num_images())

        self.btn_next_image.clicked.connect(self.app_model.next_image)
        self.btn_previous_image.clicked.connect(self.app_model.previous_image)

        self.pose_image.set_model(model)

        self._image_changed(self.app_model.get_image_index())
        self._reset()

    def _select_image(self):
        self.app_model.set_image_index(self.sld_image_number.value() - 1)

    def _select_instance(self):
        row = self.lst_instances.currentIndex().row()
        if row == -1:
            # Select "Add new instance"
            row = self.instance_list_model.find_row_by_id(None) - 1
            self.lst_instances.setCurrentIndex(self.instance_list_model.index(row))
            self.model.set_instance_selection(None)
            return
        instance_id = self.lst_instances.currentIndex().data(InstanceListModel.InstanceIDRole)
        self.model.set_instance_selection(instance_id)

    def _select_point(self):
        row = self.lst_points.currentIndex().row()
        if row == -1:
            # Select first point
            self.lst_points.setCurrentIndex(self.point_list_model.index(0))
            self.model.set_point_selection(0)
            return
        self.model.set_point_selection(row)

    def _reset(self):
        self._selection_changed()

    def _image_changed(self, image_index: int):
        self.sld_image_number.setValue(image_index + 1)
        self.lbl_current_image.setText(self.app_model.get_image_name(image_index))
        self.lbl_image_number.setText(f"{image_index + 1}/{self.app_model.get_num_images()}")

    def _selection_changed(self):
        instance_id, point_index = self.model.get_selection()
        instance_row = self.instance_list_model.find_row_by_id(instance_id)
        self.lst_instances.setCurrentIndex(self.instance_list_model.index(instance_row))
        if point_index is not None:
            self.lst_points.setCurrentIndex(self.point_list_model.index(point_index))
        else:
            self.lst_points.setCurrentIndex(QModelIndex())

    def keyPressEvent(self, event):
        # For some reason Enter key is called Return, not Enter
        if event.key() == QtGui.Qt.Key.Key_Return or event.key() == QtGui.Qt.Key.Key_Right:
            self.app_model.next_image()
        elif event.key() == QtGui.Qt.Key.Key_Backspace or event.key() == QtGui.Qt.Key.Key_Left:
            self.app_model.previous_image()
        elif event.key() == QtGui.Qt.Key.Key_Space or event.key() == QtGui.Qt.Key.Key_Down:
            self.model.next_point()
        elif event.key() == QtGui.Qt.Key.Key_Up:
            self.model.previous_point()
        elif event.key() == QtGui.Qt.Key.Key_C and event.modifiers() == QtGui.Qt.KeyboardModifier.ControlModifier:
            pass
        elif event.key() == QtGui.Qt.Key.Key_V and event.modifiers() == QtGui.Qt.KeyboardModifier.ControlModifier:
            pass
        elif event.key() == QtGui.Qt.Key.Key_Delete:
            instance_id = self.lst_instances.selectedIndexes()[0].data(InstanceListModel.InstanceIDRole)
            if instance_id is None:
                return
            self.model.delete_instance(instance_id)
        elif event.key() == QtGui.Qt.Key.Key_Z and event.modifiers() == QtGui.Qt.KeyboardModifier.ControlModifier:
            self.model.undo()
        elif event.key() == QtGui.Qt.Key.Key_Y and event.modifiers() == QtGui.Qt.KeyboardModifier.ControlModifier:
            self.model.redo()
        self.pose_image.keyPressEvent(event)

    def keyReleaseEvent(self, event):
        self.pose_image.keyReleaseEvent(event)

    def eventFilter(self, obj, event):
        # Prevent the instance type dropdown from changing the selected type when the user scrolls
        if obj == self.dpd_instance_type:
            if event.type() == 31:
                event.ignore()
                return True
        return False
