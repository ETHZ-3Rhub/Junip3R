from typing import Optional, List

from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QWidget

from junip3r.labeller.data.types.abc import IInstanceType, IInstance
from junip3r.labeller.layout.selection_controls import Ui_SelectionControls
from junip3r.labeller.model.delegate_model import BoundingBoxDelegate, InstanceDelegate, DelegateModel
from junip3r.labeller.model.image_model import ImageModel


class InstanceListModel(QAbstractListModel):
    InstanceIDRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self):
        super().__init__()
        self._model: Optional[ImageModel] = None

        self._instances: List[InstanceDelegate] = []
        self._new_instance = None

    def set_model(self, model: Optional[ImageModel]):
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
            dm = DelegateModel(self._model)
            self._instances = dm.get_instances()
            self._new_instance = dm.get_instance(None)
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

    def _instance_added(self, instance: IInstance):
        index = len(self._instances)
        self.beginInsertRows(QModelIndex(), index, index)
        self._instances.append(InstanceDelegate.from_instance(instance))
        self.endInsertRows()

    def _instance_deleted(self, instance_id: str):
        row = self.find_row_by_id(instance_id)
        self.beginRemoveRows(QModelIndex(), row, row)
        self._instances.pop(row)
        self.endRemoveRows()

    def _instance_updated(self, instance: IInstance):
        row = self.find_row_by_id(instance.id)
        index = self.index(row)
        self._instances[row] = InstanceDelegate.from_instance(instance)
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
            self._model.rename_instance(instance.instance_id, value)
            return True
        return False


def _make_keypoint_icon(color: tuple, size: int = 16) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(*color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(1, 1, size - 2, size - 2)
    painter.end()
    return QIcon(pixmap)


def _make_rect_icon(color: tuple, size: int = 16) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    pen = painter.pen()
    pen.setColor(QColor(*color))
    pen.setWidth(2)
    painter.setPen(pen)
    painter.drawRect(2, 2, size - 4, size - 4)
    painter.end()
    return QIcon(pixmap)


class ColorIconDelegate(QStyledItemDelegate):
    def initStyleOption(self, option: QStyleOptionViewItem, index):
        super().initStyleOption(option, index)
        option.icon = QIcon()  # prevent Qt from drawing (and tinting) the icon itself

    def paint(self, painter, option, index):
        super().paint(painter, option, index)  # selection highlight + text
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        if icon is not None:
            size = option.decorationSize
            x = option.rect.left() + 4
            y = option.rect.top() + (option.rect.height() - size.height()) // 2
            icon.paint(painter, x, y, size.width(), size.height())


class PointListModel(QAbstractListModel):
    def __init__(self):
        super().__init__()
        self._model: Optional[ImageModel] = None
        self._instance: Optional[InstanceDelegate] = None
        self._icon_cache: dict[tuple, QIcon] = {}

    def set_model(self, model: Optional[ImageModel]):
        if self._model is not None:
            self._model.reset.disconnect(self.refresh)
            self._model.selection_changed.disconnect(self._selection_changed)
            self._model.instance_updated.disconnect(self._instance_updated)
            self._model.new_instance_type_changed.disconnect(self._new_instance_type_changed)
        self._model = model
        if self._model is not None:
            self._model.reset.connect(self.refresh)
            self._model.selection_changed.connect(self._selection_changed)
            self._model.instance_updated.connect(self._instance_updated)
            self._model.new_instance_type_changed.connect(self._new_instance_type_changed)
        self.refresh()

    def refresh(self):
        self.beginResetModel()
        if self._model is not None:
            dm = DelegateModel(self._model)
            self._instance = dm.get_selected_instance()
        else:
            self._instance = None
        self.endResetModel()

    def _selection_changed(self, instance_id: Optional[str], _: Optional[int]):
        if self._instance is None or self._instance.instance_id != instance_id:
            self.refresh()

    def _instance_updated(self, instance: IInstance):
        if self._instance is not None and self._instance.instance_id == instance.id:
            instance_type_changed = self._instance.type != instance.type
            self._instance = InstanceDelegate.from_instance(instance)
            if instance_type_changed:
                self.refresh()

    def _new_instance_type_changed(self, instance_type: IInstanceType):
        if self._instance is not None and self._instance.instance_id is None and self._instance.type != instance_type:
            self.refresh()

    def rowCount(self, parent=None):
        if self._instance is None:
            return 0
        return len(self._instance.members)

    def data(self, index, role=None):
        if self._instance is None:
            return None

        member = self._instance.members[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            return member.name
        elif role == Qt.ItemDataRole.FontRole:
            return QFont("Segoe UI", 12, italic=False)
        elif role == Qt.ItemDataRole.DecorationRole:
            color = member.color
            cache_key = (type(member), color)
            if cache_key not in self._icon_cache:
                if isinstance(member, BoundingBoxDelegate):
                    self._icon_cache[cache_key] = _make_rect_icon(color)
                else:
                    self._icon_cache[cache_key] = _make_keypoint_icon(color)
            return self._icon_cache[cache_key]
        return None


class TypeListModel(QAbstractListModel):
    InstanceTypeRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self):
        super().__init__()
        self._model: Optional[ImageModel] = None

        self._instance_types: List[IInstanceType] = []

    def set_model(self, model: Optional[ImageModel]):
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

        self.model: Optional[ImageModel] = None

        self.instance_list_model: InstanceListModel = InstanceListModel()
        self.point_list_model: PointListModel = PointListModel()
        self.type_list_model: TypeListModel = TypeListModel()

        self.frm_tag_list.setVisible(False)

        self.lst_instances.setModel(self.instance_list_model)
        self.lst_points.setModel(self.point_list_model)
        self.lst_points.setItemDelegate(ColorIconDelegate(self.lst_points))
        self.dpd_instance_type.setModel(self.type_list_model)

        self.dpd_instance_type.installEventFilter(self)

        self.lst_instances.selectionModel().currentChanged.connect(self._select_instance)
        self.lst_points.selectionModel().currentChanged.connect(self._select_point)

        self.dpd_instance_type.currentIndexChanged.connect(self._select_instance_type)

        self.point_list_model.modelReset.connect(self._point_list_model_reset)

    def set_model(self, model: Optional[ImageModel]):
        if self.model is not None:
            self.model.selection_changed.disconnect(self._selection_changed)
            self.model.instance_updated.disconnect(self._instance_updated)
            self.model.new_instance_type_changed.disconnect(self._new_instance_type_changed)
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
            self.model.new_instance_type_changed.connect(self._new_instance_type_changed)

            instance_id, point_index = self.model.get_selection()
            self._selection_changed(instance_id, point_index)

    def _selection_changed(self, instance_id: Optional[str] = None, point_index: Optional[int] = None):
        assert self.model is not None, "Model not set"

        instance_row = self.instance_list_model.find_row_by_id(instance_id)
        self.lst_instances.setCurrentIndex(self.instance_list_model.index(instance_row))
        if point_index is not None:
            self.lst_points.setCurrentIndex(self.point_list_model.index(point_index))
        else:
            self.lst_points.setCurrentIndex(QModelIndex())

        if instance_id is None:
            instance_type = self.model.get_new_instance_type()
        else:
            instance = self.model.get_instance(instance_id)
            assert instance is not None, f"Instance {instance_id} not found"
            instance_type = instance.type

        self.dpd_instance_type.setCurrentText(instance_type.name)

    def _instance_updated(self, instance: IInstance):
        assert self.model is not None, "Model not set"

        selected_instance_id, _ = self.model.get_selection()
        if selected_instance_id is not None and instance.id == selected_instance_id:
            self.dpd_instance_type.setCurrentText(instance.type.name)

    def _new_instance_type_changed(self, instance_type: IInstanceType):
        assert self.model is not None, "Model not set"

        selected_instance_id, _ = self.model.get_selection()
        if selected_instance_id is None:
            self.dpd_instance_type.setCurrentText(instance_type.name)

    def _select_instance(self):
        if self.model is None:
            return

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
        if self.model is None:
            return

        row = self.lst_points.currentIndex().row()
        if row == -1:
            if self.point_list_model.rowCount() >= 1:
                # Select first point
                self.lst_points.setCurrentIndex(self.point_list_model.index(0))
                self.model.set_point_selection(0)
            return
        self.model.set_point_selection(row)

    def _select_instance_type(self):
        if self.model is None:
            return

        instance_type = self.dpd_instance_type.currentData(TypeListModel.InstanceTypeRole)
        instance_id = self.lst_instances.currentIndex().data(InstanceListModel.InstanceIDRole)

        if instance_id is None:
            self.model.set_new_instance_type(instance_type.name)
        else:
            self.model.set_instance_type(instance_id, instance_type.name)

    def _point_list_model_reset(self):
        if self.model is None:
            return

        instance_id, point_index = self.model.get_selection()
        if point_index is not None:
            self.lst_points.setCurrentIndex(self.point_list_model.index(point_index))

    def eventFilter(self, obj, event):
        # Prevent the instance type dropdown from changing the selected type when the user scrolls
        if obj == self.dpd_instance_type:
            if event.type() == 31:
                event.ignore()
                return True
        return False
