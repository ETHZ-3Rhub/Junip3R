from typing import Optional, List

from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget

from app.labeller.data.types.abc import IInstanceType
from app.labeller.layout.selection_controls import Ui_SelectionControls
from app.labeller.model.pose_editor.delegates import InstanceDelegate
from app.labeller.model.pose_editor.pose_editor_model import PoseEditorModel


class InstanceListModel(QAbstractListModel):
    InstanceIDRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self):
        super().__init__()
        self._model: Optional[PoseEditorModel] = None

        self._instances = []
        self._new_instance = None

    def set_model(self, model: Optional[PoseEditorModel]):
        if self._model is not None:
            self._model.reset.disconnect(self.refresh)
            self._model.instance_added.disconnect(self._instance_added)
            self._model.instance_deleted.disconnect(self._instance_deleted)
            self._model.instance_updated.disconnect(self._instance_updated)

        self._model = model

        if self._model is not None:
            self._model.reset.connect(self.refresh)
            self._model.instance_added.connect(self._instance_added)
            self._model.instance_deleted.connect(self._instance_deleted)
            self._model.instance_updated.connect(self._instance_updated)

        self.refresh()

    def refresh(self):
        self.beginResetModel()
        if self._model is not None:
            self._instances = self._model.get_instances()
            self._new_instance = self._model.get_new_instance_delegate()
        else:
            self._instances = []
            self._new_instance = None
        self.endResetModel()

    def find_row_by_id(self, instance_id: Optional[str]) -> int:
        if instance_id is None:
            return len(self._instances)  # New instance row
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
        if instance.instance_id is None:
            self._new_instance = instance
        else:
            self._instances[row] = instance
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.FontRole])

    def flags(self, index):
        if index.row() == len(self._instances):
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable

    def rowCount(self, parent=None):
        return len(self._instances) + (1 if self._new_instance is not None else 0)

    def data(self, index, role=None):
        instance = self._new_instance if index.row() == len(self._instances) else self._instances[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return instance.name
        elif role == InstanceListModel.InstanceIDRole:
            return instance.instance_id
        elif role == Qt.ItemDataRole.FontRole:
            if instance.instance_id is None:
                return QFont("Segoe UI", 12, italic=True)
            else:
                return QFont("Segoe UI", 12, italic=False)
        return None

    def setData(self, index, value, role=None):
        if role == Qt.ItemDataRole.EditRole:
            if self._model is None:
                return False
            if value is None or value == "":
                return False
            row = index.row()
            if row == len(self._instances):
                return False
            instance = self._instances[row]
            self._model.set_instance_name(instance.instance_id, value)
            return True
        return False


class PointListModel(QAbstractListModel):
    def __init__(self):
        super().__init__()
        self._model: Optional[PoseEditorModel] = None
        self._instance: Optional[InstanceDelegate] = None

    def set_model(self, model: Optional[PoseEditorModel]):
        if self._model is not None:
            self._model.reset.disconnect(self.refresh)
            self._model.selection_changed.disconnect(self._selection_changed)
            self._model.instance_updated.disconnect(self._instance_updated)
        self._model = model
        if self._model is not None:
            self._model.reset.connect(self.refresh)
            self._model.selection_changed.connect(self._selection_changed)
            self._model.instance_updated.connect(self._instance_updated)
        self.refresh()

    def refresh(self):
        self.beginResetModel()
        if self._model is not None:
            self._instance = self._model.get_selected_instance()
        else:
            self._instance = None
        self.endResetModel()

    def _selection_changed(self, instance_id: Optional[str], _: Optional[int]):
        if self._instance is None or self._instance.instance_id != instance_id:
            self.refresh()

    def _instance_updated(self, instance: InstanceDelegate):
        if self._instance is not None and self._instance.instance_id == instance.instance_id:
            instance_type_changed = self._instance.type != instance.type
            self._instance = instance
            if instance_type_changed:
                self.refresh()

    def rowCount(self, parent=None):
        if self._instance is None:
            return 0
        return len(self._instance.members)

    def data(self, index, role=None):
        if self._instance is None:
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            return self._instance.members[index.row()].name
        elif role == Qt.ItemDataRole.FontRole:
            return QFont("Segoe UI", 12, italic=False)
        return None


class TypeListModel(QAbstractListModel):
    InstanceTypeRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self):
        super().__init__()
        self._model: Optional[PoseEditorModel] = None

        self._instance_types: List[IInstanceType] = []

    def set_model(self, model: Optional[PoseEditorModel]):
        #if self._model is not None:
        #    self._model.reset.disconnect(self.refresh)

        self._model = model

        #if self._model is not None:
        #    self._model.reset.connect(self.refresh)

        self.refresh()

    def refresh(self):
        self.beginResetModel()
        if self._model is not None:
            self._instance_types = self._model.get_instance_types()
        else:
            self._instance_types = []
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._instance_types)

    def data(self, index, role=None):
        if role == Qt.ItemDataRole.DisplayRole:
            return self._instance_types[index.row()].name
        elif role == TypeListModel.InstanceTypeRole:
            return self._instance_types[index.row()]
        return None


class SelectionControls(Ui_SelectionControls, QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.model: Optional[PoseEditorModel] = None

        self.instance_list_model: Optional[InstanceListModel] = InstanceListModel()
        self.point_list_model: Optional[PointListModel] = PointListModel()
        self.type_list_model: Optional[TypeListModel] = TypeListModel()

        self.frm_tag_list.setVisible(False)

        self.lst_instances.setModel(self.instance_list_model)
        self.lst_points.setModel(self.point_list_model)
        self.dpd_instance_type.setModel(self.type_list_model)

        self.dpd_instance_type.installEventFilter(self)

        self.lst_instances.selectionModel().currentChanged.connect(self._select_instance)
        self.lst_points.selectionModel().currentChanged.connect(self._select_point)

        self.dpd_instance_type.currentIndexChanged.connect(self._select_instance_type)

    def set_model(self, model: Optional[PoseEditorModel]):
        if self.model is not None:
            self.model.selection_changed.disconnect(self._selection_changed)
            self.model.instance_updated.disconnect(self._instance_updated)
            self.instance_list_model.set_model(None)
            self.point_list_model.set_model(None)
            self.type_list_model.set_model(None)

        self.model = model

        self.instance_list_model.set_model(model)
        self.point_list_model.set_model(model)
        self.type_list_model.set_model(model)

        if self.model is not None:
            self.model.selection_changed.connect(self._selection_changed)
            self.model.instance_updated.connect(self._instance_updated)

            instance_id, point_index = self.model.get_selection()
        else:
            instance_id = None
            point_index = None

        self._selection_changed(instance_id, point_index)


    def _selection_changed(self, instance_id: Optional[str] = None, point_index: Optional[int] = None):
        instance_row = self.instance_list_model.find_row_by_id(instance_id)
        self.lst_instances.setCurrentIndex(self.instance_list_model.index(instance_row))
        if point_index is not None:
            self.lst_points.setCurrentIndex(self.point_list_model.index(point_index))
        else:
            self.lst_points.setCurrentIndex(QModelIndex())
        self._instance_updated(self.model.get_selected_instance())

    def _instance_updated(self, instance: InstanceDelegate):
        if instance.is_selected:
            self.dpd_instance_type.setCurrentText(instance.type.name)

    def _select_instance(self):
        row = self.lst_instances.currentIndex().row()
        if row == -1:
            # TODO: This is fragile. Don't want to rely on the position (and presence) of the "Add new instance" item.
            if self.instance_list_model.rowCount() >= 1:
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
            if self.point_list_model.rowCount() >= 1:
                # Select first point
                self.lst_points.setCurrentIndex(self.point_list_model.index(0))
                self.model.set_point_selection(0)
            return
        self.model.set_point_selection(row)

    def _select_instance_type(self):
        instance_type = self.dpd_instance_type.currentData(TypeListModel.InstanceTypeRole)
        selected_instance = self.model.get_selected_instance()
        if selected_instance is not None:
            selected_instance.type = instance_type

    def eventFilter(self, obj, event):
        # Prevent the instance type dropdown from changing the selected type when the user scrolls
        if obj == self.dpd_instance_type:
            if event.type() == 31:
                event.ignore()
                return True
        return False
