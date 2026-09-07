from typing import Optional, Dict, Sequence, cast, Hashable

from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, QPointF, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap, QPolygonF, QPen, QFontMetricsF
from PySide6.QtWidgets import QStyleOptionViewItem, QWidget, QVBoxLayout, QSplitter, QLabel, \
    QListView, QComboBox, QStyledItemDelegate, QApplication, QSizePolicy

from junip3r.labeller.data.types.abc import IInstance, ILabellerObject, IInstanceMember, LabellerObjectType, \
    IInstanceType, Color, IBoundingBox, IKeypoint, IPolygon, IPolyline
from junip3r.labeller.model.pose_image_model import ImageState, ImageStateChangeFlags


class InstanceListModel(QAbstractListModel):
    instance_renamed = Signal(object, object)  # instance_id, new_name

    InstanceIDRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self):
        super().__init__()
        self._instances: Sequence[IInstance] = ()

    def set_instances(self, instances: Sequence[IInstance]):
        self.beginResetModel()
        self._instances = instances
        self.endResetModel()

    def flags(self, index):
        if index.row() == len(self._instances):
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable

    def rowCount(self, parent=None):
        return len(self._instances)

    def data(self, index, role=None):
        instance = self._instances[index.row()]
        if instance is None:
            return None

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
            if value is None or value == "":
                return False
            row = index.row()
            if row == len(self._instances):
                return False
            instance = self._instances[row]
            if instance.instance_id is None:
                return False
            self.instance_renamed.emit(instance.instance_id, value)
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


def _make_box_icon(color: tuple, size: int = 16) -> QIcon:
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


def _make_polygon_icon(
    color: Color,
    size: int = 16,
    num_points: Optional[int] = None,
) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(QColor(*color), 2)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    cx = size / 2.0
    cy = size / 2.0
    radius = (size - 4) / 2.0

    # regular pentagon
    points = [
        QPointF(cx,                   cy - radius),
        QPointF(cx + radius * 0.9511, cy - radius * 0.3090),
        QPointF(cx + radius * 0.5878, cy + radius * 0.8090),
        QPointF(cx - radius * 0.5878, cy + radius * 0.8090),
        QPointF(cx - radius * 0.9511, cy - radius * 0.3090),
    ]
    painter.drawPolygon(QPolygonF(points))

    if num_points is not None:
        text = str(num_points)

        font = painter.font()
        font.setPixelSize(7)
        font.setBold(True)
        painter.setFont(font)

        metrics = QFontMetricsF(font)
        badge_rect = metrics.tightBoundingRect(text).adjusted(-1.5, -0.5, 1.5, 0.5)
        badge_rect.moveBottomRight(QPointF(size - 0.5, size - 0.5))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Qt.GlobalColor.white)
        painter.drawRoundedRect(badge_rect, 1.5, 1.5)

        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(
            badge_rect,
            Qt.AlignmentFlag.AlignCenter,
            text,
        )

    painter.end()
    return QIcon(pixmap)


def _make_polyline_icon(color: tuple, size: int = 16, num_points: Optional[int] = None) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(QColor(*color), 2)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    # 4-point zigzag polyline
    points =[
        QPointF(2, size - 3),
        QPointF(size * 0.33, 3),
        QPointF(size * 0.66, size - 5),
        QPointF(size - 2, 5),
    ]
    painter.drawPolyline(QPolygonF(points))

    if num_points is not None:
        text = str(num_points)

        font = painter.font()
        font.setPixelSize(7)
        font.setBold(True)
        painter.setFont(font)

        metrics = QFontMetricsF(font)
        badge_rect = metrics.tightBoundingRect(text).adjusted(-1.5, -0.5, 1.5, 0.5)
        badge_rect.moveBottomRight(QPointF(size - 0.5, size - 0.5))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Qt.GlobalColor.white)
        painter.drawRoundedRect(badge_rect, 1.5, 1.5)

        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(
            badge_rect,
            Qt.AlignmentFlag.AlignCenter,
            text,
        )

    painter.end()
    return QIcon(pixmap)


class ColorIcon(QStyledItemDelegate):
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


class MemberListModel(QAbstractListModel):
    MemberIDRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self):
        super().__init__()
        self._members: Sequence[IInstanceMember] = ()
        self._icon_cache: Dict[Hashable, QIcon] = {}

    def set_members(self, members: Sequence[IInstanceMember]):
        self.beginResetModel()
        self._members = members
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._members)

    def _get_icon(self, member: IInstanceMember):
        if member.type == LabellerObjectType.BOUNDING_BOX:
            cache_key = (member.type, member.color)
            if cache_key not in self._icon_cache:
                self._icon_cache[cache_key] = _make_box_icon(member.color)
            return self._icon_cache[cache_key]
        elif member.type == LabellerObjectType.KEYPOINT:
            cache_key = (member.type, member.color)
            if cache_key not in self._icon_cache:
                self._icon_cache[cache_key] = _make_keypoint_icon(member.color)
            return self._icon_cache[cache_key]
        elif member.type == LabellerObjectType.POLYGON:
            member = cast(IPolygon, member)
            cache_key = (member.type, member.color, member.num_points)
            if cache_key not in self._icon_cache:
                self._icon_cache[cache_key] = _make_polygon_icon(member.color, 16, member.num_points)
            return self._icon_cache[cache_key]
        elif member.type == LabellerObjectType.POLYLINE:
            member = cast(IPolyline, member)
            cache_key = (member.type, member.color, member.num_points)
            if cache_key not in self._icon_cache:
                self._icon_cache[cache_key] = _make_polyline_icon(member.color, 16, member.num_points)
            return self._icon_cache[cache_key]
        else:
            if "default" not in self._icon_cache:
                self._icon_cache["default"] = QIcon()
            return self._icon_cache["default"]

    def data(self, index, role=None):
        member = self._members[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            return member.name
        elif role == MemberListModel.MemberIDRole:
            return member.id
        elif role == Qt.ItemDataRole.FontRole:
            return QFont("Segoe UI", 12, italic=False)
        elif role == Qt.ItemDataRole.DecorationRole:
            return self._get_icon(member)
        return None


class TypeListModel(QAbstractListModel):
    InstanceTypeRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self):
        super().__init__()
        self._instance_types: Sequence[IInstanceType] = ()

    def set_instance_types(self, instance_types: Sequence[IInstanceType]):
        self.beginResetModel()
        self._instance_types = instance_types
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._instance_types)

    def data(self, index, role=None):
        if role == Qt.ItemDataRole.DisplayRole:
            return self._instance_types[index.row()].name
        elif role == TypeListModel.InstanceTypeRole:
            return self._instance_types[index.row()]
        return None


class SelectionControls(QWidget):
    instance_selected = Signal(object)
    member_selected = Signal(object)
    instance_type_selected = Signal(object)

    instance_renamed = Signal(object, object)  # instance_id, new_name

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(self)
        splitter.setOrientation(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        frm_instances = QWidget(splitter)
        frm_instances_layout = QVBoxLayout(frm_instances)
        frm_instances_layout.setContentsMargins(0, 0, 0, 0)

        lbl_instances = QLabel("Instances", frm_instances)
        lbl_instances.setFont(QFont("Segoe UI", 14, italic=False))
        frm_instances_layout.addWidget(lbl_instances)

        self.lst_instances = QListView(frm_instances)
        frm_instances_layout.addWidget(self.lst_instances)

        splitter.addWidget(frm_instances)

        frm_instance_type = QWidget(splitter)
        frm_instance_type.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed))
        frm_instance_type_layout = QVBoxLayout(frm_instance_type)
        frm_instance_type_layout.setContentsMargins(0, 0, 0, 0)

        lbl_instance_type = QLabel("Instance Type", frm_instance_type)
        lbl_instance_type.setFont(QFont("Segoe UI", 14, italic=False))
        frm_instance_type_layout.addWidget(lbl_instance_type)

        self.dpd_instance_type = QComboBox(frm_instance_type)
        self.dpd_instance_type.setFont(QFont("Segoe UI", 12, italic=False))
        frm_instance_type_layout.addWidget(self.dpd_instance_type)

        frm_members = QWidget(splitter)
        frm_members_layout = QVBoxLayout(frm_members)
        frm_members_layout.setContentsMargins(0, 0, 0, 0)

        lbl_members = QLabel("Members", frm_members)
        lbl_members.setFont(QFont("Segoe UI", 14, italic=False))
        frm_members_layout.addWidget(lbl_members)

        self.lst_members = QListView(frm_members)
        frm_members_layout.addWidget(self.lst_members)

        splitter.addWidget(frm_members)

        layout.addWidget(splitter)

        self.instance_list_model: InstanceListModel = InstanceListModel()
        self.member_list_model: MemberListModel = MemberListModel()
        self.type_list_model: TypeListModel = TypeListModel()

        self.lst_instances.setModel(self.instance_list_model)
        self.lst_members.setModel(self.member_list_model)
        self.lst_members.setItemDelegate(ColorIcon(self.lst_members))
        self.dpd_instance_type.setModel(self.type_list_model)

        self.dpd_instance_type.installEventFilter(self)

        # Only react to user interactions (not programmatic selection changes).
        self.lst_instances.clicked.connect(self._select_instance)
        self.lst_members.clicked.connect(self._select_member)
        self.dpd_instance_type.activated.connect(self._select_instance_type)

        self.instance_list_model.instance_renamed.connect(self.instance_renamed)

        self._instance_type: Optional[IInstanceType] = None

    def _has_instance_type_changed(self, image_state: ImageState, flags: ImageStateChangeFlags) -> bool:
        if flags & ImageStateChangeFlags.INSTANCES or flags & ImageStateChangeFlags.SELECTION:
            selected_instance = image_state.selected_instance
            instance_type = selected_instance.instance_type if selected_instance is not None else None
            if instance_type != self._instance_type:
                return True
        return False

    def _get_members(self, image_state: ImageState):
        selected_instance = image_state.selected_instance
        return selected_instance.members if selected_instance is not None else ()

    def set_image_state(self, image_state: ImageState, flags: ImageStateChangeFlags):
        if flags & ImageStateChangeFlags.INSTANCES:
            self.instance_list_model.set_instances(image_state.instances)

        if flags & ImageStateChangeFlags.INSTANCE_TYPES:
            self.type_list_model.set_instance_types(image_state.instance_types)

        selected_instance = image_state.selected_instance
        instance_type = selected_instance.instance_type if selected_instance is not None else None

        if flags & ImageStateChangeFlags.ALL or instance_type != self._instance_type:
            self._instance_type = instance_type
            self.dpd_instance_type.setCurrentText(instance_type.name if instance_type is not None else "")
            self.member_list_model.set_members(self._get_members(image_state))

        if flags & ImageStateChangeFlags.INSTANCES or flags & ImageStateChangeFlags.SELECTION:
            selection = image_state.selection
            if selection is None:
                self.lst_instances.setCurrentIndex(QModelIndex())
                self.lst_members.setCurrentIndex(QModelIndex())
                return
            else:
                instance_id, member_id = selection

                instance_index = next((i for i, inst in enumerate(image_state.instances) if inst.instance_id == instance_id), None)
                if instance_index is not None:
                    self.lst_instances.setCurrentIndex(QModelIndex(self.instance_list_model.index(instance_index, 0)))
                    # Resolved fresh from the current member list, not trusted as a row
                    # number carried over from elsewhere - a config edit can reorder
                    # members between two selections.
                    selected_members = image_state.instances[instance_index].members
                    member_row = next((i for i, m in enumerate(selected_members) if m.id == member_id), None)
                    if member_row is not None:
                        self.lst_members.setCurrentIndex(QModelIndex(self.member_list_model.index(member_row, 0)))
                    else:
                        self.lst_members.setCurrentIndex(QModelIndex())
                else:
                    self.lst_instances.setCurrentIndex(QModelIndex())
                    self.lst_members.setCurrentIndex(QModelIndex())

    def _set_instances(self, instances: Sequence[IInstance]):
        self.instance_list_model.set_instances(instances)
        self._instance_ids = [inst.instance_id for inst in instances]

    def _select_instance(self, index: QModelIndex):
        if index.isValid():
            instance_id = index.data(InstanceListModel.InstanceIDRole)
            self.instance_selected.emit(instance_id)

    def _select_member(self, index: QModelIndex):
        if index.isValid():
            member_id = index.data(MemberListModel.MemberIDRole)
            if member_id is not None:
                self.member_selected.emit(member_id)

    def _select_instance_type(self, *_):
        instance_type = self.dpd_instance_type.currentData(TypeListModel.InstanceTypeRole)
        self.instance_type_selected.emit(instance_type)

    def eventFilter(self, obj, event):
        # Prevent the instance type dropdown from changing the selected type when the user scrolls
        if obj == self.dpd_instance_type:
            if event.type() == 31:
                event.ignore()
                return True
        return False


if __name__ == "__main__":

    app = QApplication([])
    icon = _make_polygon_icon((255, 0, 0), size=16, num_points=5)
    image = QLabel()
    image.setPixmap(icon.pixmap(320, 320))
    image.show()

    app.exec_()
