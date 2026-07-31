from dataclasses import dataclass
from typing import Optional, Tuple, List, Sequence

import numpy as np
from PySide6 import QtGui
from PySide6.QtCore import QPointF, QRect, QRectF, Qt, QLineF
from PySide6.QtGui import QImage, QColor, QFont, QPen, QBrush

from junip3r.labeller.model.camera_model import CameraState


@dataclass(frozen=True)
class ImageFrame:
    w: int = 1
    h: int = 1

    def with_size(self, w: int, h: int) -> "ImageFrame":
        return ImageFrame(w=max(1, int(w)), h=max(1, int(h)))

    # image pixel coords (0..w, 0..h) <-> world coords (centered)
    def imagepx_to_world(self, ix: float, iy: float) -> Tuple[float, float]:
        return ix - self.w * 0.5, iy - self.h * 0.5

    def world_to_imagepx(self, wx: float, wy: float) -> Tuple[float, float]:
        return wx + self.w * 0.5, wy + self.h * 0.5

    # normalized (0..1) image coords <-> image pixel coords
    def image01_to_imagepx(self, x01: float, y01: float) -> Tuple[float, float]:
        return x01 * self.w, y01 * self.h

    def imagepx_to_image01(self, ix: float, iy: float) -> Tuple[float, float]:
        return ix / self.w, iy / self.h

    def clamp_image_rect(self, left: float, top: float, right: float, bottom: float) -> Optional[Tuple[float, float, float, float]]:
        l = max(0.0, min(float(self.w), left))
        r = max(0.0, min(float(self.w), right))
        t = max(0.0, min(float(self.h), top))
        b = max(0.0, min(float(self.h), bottom))
        if r <= l or b <= t:
            return None
        return l, t, r, b


class Renderer:
    KEYPOINT_LINE_WIDTH = 2
    KEYPOINT_RADIUS = 6
    KEYPOINT_RADIUS_HIGHLIGHTED = 7
    BOUNDING_BOX_CORNER_RADIUS_HIGHLIGHTED = 7
    POLYGON_POINT_RADIUS = 4
    POLYGON_POINT_RADIUS_HIGHLIGHTED = 7

    def __init__(self, camera_state: CameraState, frame: ImageFrame, painter: QtGui.QPainter):
        self.camera_state = camera_state
        self.frame = frame
        self.painter = painter

    # ---- Internal mapping helpers ----
    def _image01_to_world(self, p_image01: Tuple[float, float]) -> Tuple[float, float]:
        ix, iy = self.frame.image01_to_imagepx(p_image01[0], p_image01[1])
        return self.frame.imagepx_to_world(ix, iy)

    def _image01_to_view_px(self, p_image01: Tuple[float, float]) -> Tuple[int, int]:
        wx, wy = self._image01_to_world(p_image01)
        vx, vy = self.camera_state.world_to_view(wx, wy)
        return int(vx), int(vy)

    # ---- Main image draw ----
    def draw_image(self, img: QImage) -> ImageFrame:
        """Draw image and return updated frame with image size."""

        # visible rect in world coords
        wl, wt, wr, wb = self.camera_state.world_rect_visible()

        # convert to image pixel coords
        il, it = self.frame.world_to_imagepx(wl, wt)
        ir, ib = self.frame.world_to_imagepx(wr, wb)

        # clamp to image bounds
        clamped = self.frame.clamp_image_rect(il, it, ir, ib)
        if clamped is None:
            return self.frame
        il, it, ir, ib = clamped

        # source rect in image pixels
        src = QRectF(il, it, ir - il, ib - it)

        # destination rect in view pixels, matching the same region
        wcl, wct = self.frame.imagepx_to_world(il, it)
        wcr, wcb = self.frame.imagepx_to_world(ir, ib)
        vtl = QPointF(*self.camera_state.world_to_view(wcl, wct))
        vbr = QPointF(*self.camera_state.world_to_view(wcr, wcb))
        dst = QRectF(vtl, vbr).normalized()

        self.painter.drawImage(dst, img, src)

        return self.frame

    # ---- Overlay methods (ported from your original renderer) ----
    def draw_keypoint(self, p_image01, color: QColor, visible: bool = True, highlighted: bool = False, opacity: float=1.0):
        x, y = self._image01_to_view_px(p_image01)

        radius = self.KEYPOINT_RADIUS_HIGHLIGHTED if highlighted else self.KEYPOINT_RADIUS

        self.painter.setOpacity(opacity)
        if visible:
            self.painter.setPen(QPen(Qt.PenStyle.NoPen))
            self.painter.setBrush(QBrush(color))
            self.painter.drawEllipse(QPointF(x, y), radius, radius)
        else:
            self.painter.setPen(QPen(color, self.KEYPOINT_LINE_WIDTH))
            self.painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            inner_radius = radius - self.KEYPOINT_LINE_WIDTH / 2
            self.painter.drawEllipse(QPointF(x, y), inner_radius, inner_radius)

    def draw_skeleton_line(self, p1_image01, p2_image01, color: QColor, opacity=1.0):
        x1, y1 = self._image01_to_view_px(p1_image01)
        x2, y2 = self._image01_to_view_px(p2_image01)

        self.painter.setOpacity(opacity)
        self.painter.setPen(QPen(color, 2))
        self.painter.drawLine(x1, y1, x2, y2)

    def draw_point_label(self, p_image01, name: str):
        x, y = self._image01_to_view_px(p_image01)

        label_p = (x - 100, y - 41)
        label_rect = QRect(label_p[0], label_p[1], 200, 30)

        self.painter.setOpacity(1.0)
        self.painter.setPen(QPen(QColor(0, 0, 0)))
        self.painter.setBrush(QBrush(QColor(255, 255, 255)))
        self.painter.setFont(QFont("Arial", 15))

        background_rect = self.painter.boundingRect(label_rect, Qt.AlignmentFlag.AlignCenter, name)
        self.painter.fillRect(background_rect, QColor(255, 255, 255))
        self.painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, name)

    def draw_box_label(self, p1_image01, name: str):
        x1, y1 = self._image01_to_view_px(p1_image01)

        self.painter.setOpacity(1.0)

        # label near top-left
        label_p = (x1, y1 - 10)
        label_rect = QRect(label_p[0], label_p[1] - 20, 200, 30)

        self.painter.setPen(QPen(QColor(0, 0, 0)))
        self.painter.setBrush(QBrush(QColor(255, 255, 255)))
        self.painter.setFont(QFont("Arial", 15))

        background_rect = self.painter.boundingRect(label_rect, Qt.AlignmentFlag.AlignVCenter, name)
        self.painter.fillRect(background_rect, QColor(255, 255, 255))
        self.painter.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter, name)


    def draw_instance_label(self, p1_i01, p2_i01, instance_name: str):
        x1, y1 = self._image01_to_view_px(p1_i01)
        x2, y2 = self._image01_to_view_px(p2_i01)

        # expand bbox by 40 px
        x1, y1 = x1 - 40, y1 - 40
        x2, y2 = x2 + 40, y2 + 40

        self.painter.setOpacity(1.0)

        # dashed bbox
        pen = QPen(QColor(0, 0, 0), 1)
        pen.setStyle(Qt.PenStyle.DashLine)
        self.painter.setPen(pen)
        self.painter.setBrush(QBrush(QColor(0, 0, 0, 0)))

        w = x2 - x1
        h = y2 - y1
        if abs(w) > 0.1 and abs(h) > 0.1:
            self.painter.drawRect(x1, y1, w, h)
        else:
            self.painter.drawPoint(x1, y1)

        # label near top-left
        label_p = (x1, y1 - 10)
        label_rect = QRect(label_p[0], label_p[1] - 20, 200, 30)

        self.painter.setPen(QPen(QColor(0, 0, 0)))
        self.painter.setBrush(QBrush(QColor(255, 255, 255)))
        self.painter.setFont(QFont("Arial", 15))

        background_rect = self.painter.boundingRect(label_rect, Qt.AlignmentFlag.AlignVCenter, instance_name)
        self.painter.fillRect(background_rect, QColor(255, 255, 255))
        self.painter.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter, instance_name)

    def draw_current_point_sign(self, instance_name: str, point_name: str, color: QColor):
        label_str = f"{instance_name} - {point_name}"
        label_rect = QRect(0, 0, 1000, 100)

        self.painter.setOpacity(1.0)
        self.painter.setPen(QPen(color, 2))
        self.painter.setBrush(QBrush(QColor(255, 255, 255)))
        self.painter.setFont(QFont("Arial", 50))

        background_rect = self.painter.boundingRect(label_rect, Qt.AlignmentFlag.AlignLeft, label_str)
        self.painter.fillRect(background_rect, QColor(255, 255, 255))
        self.painter.drawText(label_rect, Qt.AlignmentFlag.AlignLeft, label_str)

    def draw_crosshair(self, pos_view: Tuple[float, float]):
        x, y = pos_view

        self.painter.setOpacity(1.0)
        self.painter.setPen(QPen(QColor(0, 0, 0), 1, Qt.PenStyle.DashLine))

        self.painter.drawLine(QLineF(x, 0, x, self.camera_state.view_size[1]))
        self.painter.drawLine(QLineF(0, y, self.camera_state.view_size[0], y))

    def draw_bounding_box(self, p1_image01, p2_image01, color: QColor, opacity=1.0):
        x1, y1 = self._image01_to_view_px(p1_image01)
        x2, y2 = self._image01_to_view_px(p2_image01)

        self.painter.setOpacity(opacity)
        self.painter.setPen(QPen(color, 2))
        self.painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))

        # ensure positive width/height for Qt rect drawing
        left = min(x1, x2)
        top = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        self.painter.drawRect(left, top, w, h)

    def draw_bounding_box_corner(self, p_image01, color: QColor, opacity=1.0):
        x, y = self._image01_to_view_px(p_image01)
        radius = self.BOUNDING_BOX_CORNER_RADIUS_HIGHLIGHTED

        self.painter.setOpacity(opacity)
        self.painter.setPen(QPen(Qt.PenStyle.NoPen))
        self.painter.setBrush(QBrush(color))
        self.painter.drawEllipse(QPointF(x, y), radius, radius)

    def draw_polygon(self, points: Sequence[Tuple[float, float]], color: QColor, opacity=1.0, fill_opacity=0.):
        view_points = [QPointF(*self._image01_to_view_px(p)) for p in points]

        if len(view_points) >= 2:
            self.painter.setOpacity(opacity)
            self.painter.setPen(QPen(color, 1))
            self.painter.setBrush(QBrush(color, Qt.BrushStyle.NoBrush))
            polygon = QtGui.QPolygonF(view_points)
            self.painter.drawPolygon(polygon)

            if fill_opacity > 0:
                self.painter.setOpacity(fill_opacity)
                self.painter.setBrush(QBrush(color, Qt.BrushStyle.SolidPattern))
                self.painter.drawPolygon(polygon)

    def draw_polygon_point(self, p_image01, color: QColor, highlighted=False, opacity=1.0):
        x, y = self._image01_to_view_px(p_image01)
        radius = self.POLYGON_POINT_RADIUS_HIGHLIGHTED if highlighted else self.POLYGON_POINT_RADIUS

        self.painter.setOpacity(opacity)
        self.painter.setPen(QPen(Qt.PenStyle.NoPen))
        self.painter.setBrush(QBrush(color))
        self.painter.drawEllipse(QPointF(x, y), radius, radius)

    def draw_polyline(self, points: List[Tuple[float, float]], color: QColor, opacity=1.0, width=2):
        view_points = [QPointF(*self._image01_to_view_px(p)) for p in points]

        if len(view_points) >= 2:
            self.painter.setOpacity(opacity)
            self.painter.setPen(QPen(color, width))
            self.painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))

            polygon = QtGui.QPolygonF(view_points)
            self.painter.drawPolyline(polygon)
