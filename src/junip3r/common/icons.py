from typing import Optional

from PySide6.QtCore import QPointF
from PySide6.QtGui import Qt, QIcon, QPixmap, QPainter, QColor, QPen, QPolygonF, QFontMetricsF

from junip3r.labeller.data.types.abc import Color


def make_keypoint_icon(color: tuple, size: int = 16) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(*color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(1, 1, size - 2, size - 2)
    painter.end()
    return QIcon(pixmap)


def make_bounding_box_icon(color: tuple, size: int = 16) -> QIcon:
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


def make_polygon_icon(
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


def make_polyline_icon(color: tuple, size: int = 16, num_points: Optional[int] = None) -> QIcon:
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