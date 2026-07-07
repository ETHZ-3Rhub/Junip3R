from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from PySide6 import QtGui
from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QImage, QColor, QFont, QPen, QBrush


POINT_RADIUS = 6


@dataclass
class Camera:
    # View (widget) size in pixels
    view_w: int = 1
    view_h: int = 1

    # Camera center in world coords (world origin at image center)
    center_x: float = 0.0
    center_y: float = 0.0

    # zoom = screen_pixels per world_unit (world_unit = image pixel)
    zoom: float = 1.0

    # Drag state
    dragging: bool = False
    drag_anchor_world: Optional[Tuple[float, float]] = None

    def set_view_size(self, w: int, h: int) -> None:
        self.view_w = max(1, int(w))
        self.view_h = max(1, int(h))

    def view_to_world(self, vx: float, vy: float) -> Tuple[float, float]:
        wx = (vx - self.view_w * 0.5) / self.zoom + self.center_x
        wy = (vy - self.view_h * 0.5) / self.zoom + self.center_y
        return wx, wy

    def world_to_view(self, wx: float, wy: float) -> Tuple[float, float]:
        vx = (wx - self.center_x) * self.zoom + self.view_w * 0.5
        vy = (wy - self.center_y) * self.zoom + self.view_h * 0.5
        return vx, vy

    def world_rect_visible(self) -> Tuple[float, float, float, float]:
        half_w = (self.view_w * 0.5) / self.zoom
        half_h = (self.view_h * 0.5) / self.zoom
        left = self.center_x - half_w
        right = self.center_x + half_w
        top = self.center_y - half_h
        bottom = self.center_y + half_h
        return left, top, right, bottom

    # Dragging
    def drag_start(self, mouse_x: float, mouse_y: float) -> None:
        self.dragging = True
        self.drag_anchor_world = self.view_to_world(mouse_x, mouse_y)

    def drag_update(self, mouse_x: float, mouse_y: float) -> None:
        if not self.dragging or self.drag_anchor_world is None:
            return
        ax, ay = self.drag_anchor_world
        self.center_x = ax - (mouse_x - self.view_w * 0.5) / self.zoom
        self.center_y = ay - (mouse_y - self.view_h * 0.5) / self.zoom

    def drag_end(self) -> None:
        self.dragging = False
        self.drag_anchor_world = None

    # Optional: zoom around cursor
    def set_zoom_around(self, new_zoom: float, mouse_x: float, mouse_y: float,
                       min_zoom: float = 0.01, max_zoom: float = 1000.0) -> None:
        new_zoom = max(min_zoom, min(max_zoom, float(new_zoom)))
        if new_zoom == self.zoom:
            return
        wx, wy = self.view_to_world(mouse_x, mouse_y)
        self.zoom = new_zoom
        self.center_x = wx - (mouse_x - self.view_w * 0.5) / self.zoom
        self.center_y = wy - (mouse_y - self.view_h * 0.5) / self.zoom


@dataclass
class ImageFrame:
    w: int = 1
    h: int = 1

    def set_size(self, w: int, h: int) -> None:
        self.w = max(1, int(w))
        self.h = max(1, int(h))

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
    def __init__(self, camera: Camera, frame: ImageFrame):
        self.camera = camera
        self.frame = frame

    # ---- Internal mapping helpers ----
    def _image01_to_world(self, p_image01: Tuple[float, float]) -> Tuple[float, float]:
        ix, iy = self.frame.image01_to_imagepx(p_image01[0], p_image01[1])
        return self.frame.imagepx_to_world(ix, iy)

    def _image01_to_view_px(self, p_image01: Tuple[float, float]) -> Tuple[int, int]:
        wx, wy = self._image01_to_world(p_image01)
        vx, vy = self.camera.world_to_view(wx, wy)
        return int(vx), int(vy)

    def _numpy_to_qimage_owned(self, img: np.ndarray) -> QImage:
        """
        Build a QImage and deep-copy it so Qt owns the memory safely.
        Supports uint8 grayscale (H,W) and uint8 RGB (H,W,3).
        """
        if img.dtype != np.uint8:
            img = img.astype(np.uint8, copy=False)

        if img.ndim == 2:
            h, w = img.shape
            q = QImage(img.data, w, h, img.strides[0], QImage.Format.Format_Grayscale8)
            return q.copy()

        if img.ndim == 3 and img.shape[2] == 3:
            h, w, _ = img.shape

            # If coming from OpenCV (BGR), uncomment this:
            # img = img[:, :, ::-1].copy()

            q = QImage(img.data, w, h, img.strides[0], QImage.Format.Format_RGB888)
            return q.copy()

        raise ValueError(f"Unsupported image shape: {img.shape}")

    # ---- Main image draw ----
    def draw_image(self, painter: QtGui.QPainter, img: np.ndarray) -> None:
        self.frame.set_size(img.shape[1], img.shape[0])
        qimg = self._numpy_to_qimage_owned(img)

        # visible rect in world coords
        wl, wt, wr, wb = self.camera.world_rect_visible()

        # convert to image pixel coords
        il, it = self.frame.world_to_imagepx(wl, wt)
        ir, ib = self.frame.world_to_imagepx(wr, wb)

        # clamp to image bounds
        clamped = self.frame.clamp_image_rect(il, it, ir, ib)
        if clamped is None:
            return
        il, it, ir, ib = clamped

        # source rect in image pixels
        src = QRectF(il, it, ir - il, ib - it)

        # destination rect in view pixels, matching the same region
        wcl, wct = self.frame.imagepx_to_world(il, it)
        wcr, wcb = self.frame.imagepx_to_world(ir, ib)
        vtl = QPointF(*self.camera.world_to_view(wcl, wct))
        vbr = QPointF(*self.camera.world_to_view(wcr, wcb))
        dst = QRectF(vtl, vbr).normalized()

        painter.drawImage(dst, qimg, src)

    # ---- Overlay methods (ported from your original renderer) ----
    def draw_point(self, painter: QtGui.QPainter, p_image01, color: QColor, visible=True, opacity=1.0):
        x, y = self._image01_to_view_px(p_image01)

        painter.setOpacity(opacity)
        if visible:
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.setBrush(QBrush(color))
        else:
            painter.setPen(QPen(color, 2))
            painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))

        painter.drawEllipse(QPoint(x, y), POINT_RADIUS, POINT_RADIUS)

    def draw_skeleton_line(self, painter: QtGui.QPainter, p1_image01, p2_image01, color: QColor, opacity=1.0):
        x1, y1 = self._image01_to_view_px(p1_image01)
        x2, y2 = self._image01_to_view_px(p2_image01)

        painter.setOpacity(opacity)
        painter.setPen(QPen(color, 2))
        painter.drawLine(x1, y1, x2, y2)

    def draw_point_label(self, painter: QtGui.QPainter, p_image01, label_str: str):
        x, y = self._image01_to_view_px(p_image01)

        label_p = (x - 100, y - 41)
        label_rect = QRect(label_p[0], label_p[1], 200, 30)

        painter.setOpacity(1.0)
        painter.setPen(QPen(QColor(0, 0, 0)))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setFont(QFont("Arial", 15))

        background_rect = painter.boundingRect(label_rect, Qt.AlignmentFlag.AlignCenter, label_str)
        painter.fillRect(background_rect, QColor(255, 255, 255))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label_str)

    def draw_instance_label(self, painter: QtGui.QPainter, p1_i01, p2_i01, instance_name: str):
        x1, y1 = self._image01_to_view_px(p1_i01)
        x2, y2 = self._image01_to_view_px(p2_i01)

        # expand bbox by 40 px
        x1, y1 = x1 - 40, y1 - 40
        x2, y2 = x2 + 40, y2 + 40

        painter.setOpacity(1.0)

        # dashed bbox
        pen = QPen(QColor(0, 0, 0), 1)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))

        w = x2 - x1
        h = y2 - y1
        if abs(w) > 0.1 and abs(h) > 0.1:
            painter.drawRect(x1, y1, w, h)
        else:
            painter.drawPoint(x1, y1)

        # label near top-left
        label_p = (x1, y1 - 10)
        label_rect = QRect(label_p[0], label_p[1] - 20, 200, 30)

        painter.setPen(QPen(QColor(0, 0, 0)))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setFont(QFont("Arial", 15))

        background_rect = painter.boundingRect(label_rect, Qt.AlignmentFlag.AlignVCenter, instance_name)
        painter.fillRect(background_rect, QColor(255, 255, 255))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter, instance_name)

    def draw_current_point_sign(self, painter: QtGui.QPainter, instance_name: str, point_name: str, color: QColor):
        label_str = f"{instance_name} - {point_name}"
        label_rect = QRect(0, 0, 1000, 100)

        painter.setOpacity(1.0)
        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setFont(QFont("Arial", 50))

        background_rect = painter.boundingRect(label_rect, Qt.AlignmentFlag.AlignLeft, label_str)
        painter.fillRect(background_rect, QColor(255, 255, 255))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignLeft, label_str)

    def draw_crosshair(self, painter: QtGui.QPainter, p_image01):
        x, y = self._image01_to_view_px(p_image01)

        painter.setOpacity(1.0)
        painter.setPen(QPen(QColor(0, 0, 0), 1, Qt.PenStyle.DashLine))
        painter.drawLine(0, y, self.camera.view_w, y)
        painter.drawLine(x, 0, x, self.camera.view_h)

    def draw_bounding_box(self, painter: QtGui.QPainter, p1_image01, p2_image01, opacity=1.0):
        x1, y1 = self._image01_to_view_px(p1_image01)
        x2, y2 = self._image01_to_view_px(p2_image01)

        painter.setOpacity(opacity)
        painter.setPen(QPen(QColor(0, 0, 255), 2))
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))

        # ensure positive width/height for Qt rect drawing
        left = min(x1, x2)
        top = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        painter.drawRect(left, top, w, h)
