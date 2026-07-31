from typing import Optional, Dict, Sequence, cast, Hashable

from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, QPointF, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap, QPolygonF, QPen, QFontMetricsF
from PySide6.QtWidgets import QStyleOptionViewItem, QWidget, QVBoxLayout, QLabel, QListView, QStyledItemDelegate

from junip3r.labeller.data.types.abc import ILabellerObject, LabellerObjectType, IInstanceType, \
    Color, IBoundingBox, IKeypoint, IPolygon, IPolyline
from junip3r.labeller.model.pose_image_model import ImageState, ImageStateChangeFlags


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
    def __init__(self):
        super().__init__()
        self._members: Sequence[ILabellerObject] = ()
        self._icon_cache: Dict[Hashable, QIcon] = {}

    def set_members(self, members: Sequence[ILabellerObject]):
        self.beginResetModel()
        self._members = members
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._members)

    def _get_icon(self, member: ILabellerObject):
        if member.type == LabellerObjectType.BOUNDING_BOX:
            member = cast(IBoundingBox, member)
            cache_key = (member.type, member.color)
            if cache_key not in self._icon_cache:
                self._icon_cache[cache_key] = _make_box_icon(member.color)
            return self._icon_cache[cache_key]
        elif member.type == LabellerObjectType.KEYPOINT:
            member = cast(IKeypoint, member)
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
        elif role == Qt.ItemDataRole.FontRole:
            return QFont("Segoe UI", 12, italic=False)
        elif role == Qt.ItemDataRole.DecorationRole:
            return self._get_icon(member)
        return None


class PreviewMemberList(QWidget):
    member_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl_members = QLabel("Members", self)
        #lbl_members.setFont(QFont("Segoe UI", 14, italic=False))
        layout.addWidget(lbl_members)

        self.lst_members = QListView(self)
        layout.addWidget(self.lst_members)

        self.member_list_model: MemberListModel = MemberListModel()

        self.lst_members.setModel(self.member_list_model)
        self.lst_members.setItemDelegate(ColorIcon(self.lst_members))

        # Only react to user interactions (not programmatic selection changes).
        self.lst_members.clicked.connect(self._select_member)

        self._instance_type: Optional[IInstanceType] = None

    def _has_instance_type_changed(self, image_state: ImageState, flags: ImageStateChangeFlags) -> bool:
        if flags & ImageStateChangeFlags.INSTANCES or flags & ImageStateChangeFlags.SELECTION:
            selected_instance = image_state.selected_instance
            instance_type = selected_instance.instance_type if selected_instance is not None else None
            if instance_type != self._instance_type:
                return True
        return False

    def set_image_state(self, image_state: ImageState, flags: ImageStateChangeFlags):
        selected_instance = image_state.selected_instance
        instance_type = selected_instance.instance_type if selected_instance is not None else None

        if flags & ImageStateChangeFlags.ALL or instance_type != self._instance_type:
            self._instance_type = instance_type
            if selected_instance is None:
                self.member_list_model.set_members(())
            else:
                self.member_list_model.set_members(selected_instance.members)

        if flags & ImageStateChangeFlags.INSTANCES or flags & ImageStateChangeFlags.SELECTION:
            selection = image_state.selection
            if selection is None:
                self.lst_members.setCurrentIndex(QModelIndex())
            else:
                instance_id, member_index = selection
                self.lst_members.setCurrentIndex(QModelIndex(self.member_list_model.index(member_index, 0)))

    def _select_member(self, index: QModelIndex):
        if index.isValid():
            member_index = index.row()
            self.member_selected.emit(member_index)
