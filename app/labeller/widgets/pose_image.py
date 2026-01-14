from typing import Tuple, List, Optional

import numpy as np
from PySide6 import QtGui
from PySide6.QtGui import Qt, QPainter
from PySide6.QtWidgets import QLabel

from app.labeller.data.types.abc import BoundingBoxType
from app.labeller.model.pose_editor.pose_editor_model import PoseEditorModel
from app.labeller.model.pose_editor.delegates import InstanceDelegate, BoundingBoxDelegate, KeypointDelegate
from app.labeller.widgets.renderer import Renderer, Camera, ImageFrame

POINT_RADIUS = 6
DRAG_THRESHOLD = 1


class PoseImage(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScaledContents(True)
        self.setMouseTracking(True)
        self.setFocusPolicy(QtGui.Qt.FocusPolicy.StrongFocus)

        self.model: Optional[PoseEditorModel] = None

        self.show_all_labels = False
        self.context_mode = False
        self.context_index = 0

        self.brightness = 0.
        self.contrast = 0.

        self.mouse_pos_cp = (0.0, 0.0)
        self.bounding_box_start_pos_i = None

        self.dragging_point = None
        self.dragging_point_start_pos_i = None
        self.dragging_point_current_pos_i = None

        self.camera = Camera()
        self.camera.set_view_size(self.width(), self.height())

        self.image_frame = ImageFrame()

        self.renderer = Renderer(self.camera, self.image_frame)
        #self.setCursor(Qt.CursorShape.BlankCursor)

        self.auto_zoom_locations = {}

    def set_model(self, model: PoseEditorModel):
        if self.model is not None:
            self.model.reset.disconnect(self.reset)
            self.model.instance_added.disconnect(self.update)
            self.model.instance_deleted.disconnect(self.update)
            self.model.instance_updated.disconnect(self.update)
            self.model.selection_changed.disconnect(self.update)
            self.model.settings_changed.disconnect(self._settings_changed)

        self.model = model

        if self.model is not None:
            self.model.reset.connect(self.reset)
            self.model.instance_added.connect(self.update)
            self.model.instance_deleted.connect(self.update)
            self.model.instance_updated.connect(self.update)
            self.model.selection_changed.connect(self.update)
            self.model.settings_changed.connect(self._settings_changed)

        self.reset()

    def reset(self):
        if self.model is not None:
            image = self.model.get_image()
            self.image_frame.set_size(image.shape[1], image.shape[0])

            if self.model.get_selection()[1] is None:
                self.model.set_selection(None, 0)
        else:
            self.image_frame.set_size(100, 100)
        self.update()

    def auto_zoom(self):
        selected_instance_id, selected_member_index = self.model.get_selection()
        selected_instance = self.model.get_instance(selected_instance_id)
        if not selected_instance:
            return
        selected_member = selected_instance.members[selected_member_index]
        if not isinstance(selected_member, KeypointDelegate):
            return
        key = (selected_instance.type.name, selected_member.keypoint_index)
        if key not in self.auto_zoom_locations:
            return
        self.camera.center_x, self.camera.center_y, self.camera.zoom = self.auto_zoom_locations[key]
        self.update()

    def find_keypoint_at_pos(self, p_cp: Tuple[float, float]) -> Optional[KeypointDelegate]:
        instances = self.model.get_instances()
        for instance in reversed(instances):
            for keypoint in reversed(instance.keypoints):
                kp_p_i = keypoint.p

                if kp_p_i is None:
                    continue

                kp_p_ip = self.image_frame.image01_to_imagepx(*kp_p_i)
                kp_p = self.image_frame.imagepx_to_world(*kp_p_ip)
                kp_p_cp = self.camera.world_to_view(*kp_p)
                dist = (p_cp[0] - kp_p_cp[0])**2 + (p_cp[1] - kp_p_cp[1])**2
                if dist < POINT_RADIUS**2:
                    return keypoint
        return None

    def find_bounding_box_at_pos(self, p_cp: Tuple[float, float]) -> Optional[BoundingBoxDelegate]:
        instances = self.model.get_instances()
        for instance in reversed(instances):
            box = instance.box.box
            if box is None:
                continue

            p1_i, p2_i = box
            p1_ip = self.image_frame.image01_to_imagepx(*p1_i)
            p2_ip = self.image_frame.image01_to_imagepx(*p2_i)
            p1 = self.image_frame.imagepx_to_world(*p1_ip)
            p2 = self.image_frame.imagepx_to_world(*p2_ip)
            p1_cp = self.camera.world_to_view(*p1)
            p2_cp = self.camera.world_to_view(*p2)

            if p1_cp[0] <= p_cp[0] <= p2_cp[0] and p1_cp[1] <= p_cp[1] <= p2_cp[1]:
                return instance.box
        return None

    def place(self, p_cp: Tuple[float, float], visible=True):
        p = self.camera.view_to_world(*p_cp)
        p_ip = self.image_frame.world_to_imagepx(*p)
        p_i = self.image_frame.imagepx_to_image01(*p_ip)

        p_i = (max(0.0, p_i[0]), max(0.0, p_i[1]))
        p_i = (min(1.0, p_i[0]), min(1.0, p_i[1]))

        selected_member = self.model.get_selected_member()

        if not selected_member:
            self.model.set_selection(None, 0)
            return

        if isinstance(selected_member, BoundingBoxDelegate):
            if self.bounding_box_start_pos_i is None:
                self.bounding_box_start_pos_i = p_i
            else:
                selected_member.set((self.bounding_box_start_pos_i, p_i))
                self.bounding_box_start_pos_i = None
        elif isinstance(selected_member, KeypointDelegate):
            selected_member.set(p_i, 2.0 if visible else 1.0)
            selected_instance = self.model.get_selected_instance()
            self.auto_zoom_locations[(selected_instance.type.name, selected_member.keypoint_index)] = (self.camera.center_x, self.camera.center_y, self.camera.zoom)

    def delete(self, p_cp: Tuple[int, int]):
        if self.bounding_box_start_pos_i is not None:
            self.bounding_box_start_pos_i = None
            return

        keypoint = self.find_keypoint_at_pos(p_cp)
        if keypoint is not None:
            keypoint.delete()
            return

        box = self.find_bounding_box_at_pos(p_cp)
        if box is not None:
            box.delete()

    def toggle_visibility(self, p_cp: Tuple[int, int]):
        keypoint = self.find_keypoint_at_pos(p_cp)
        if keypoint is not None:
            keypoint.visibility = 1.0 if keypoint.visibility == 2.0 else 2.0

    def stop_context_mode(self):
        self.context_mode = False
        self.context_index = 0
        self.update()

    def mousePressEvent(self, event):
        p_cp = (event.pos().x(), event.pos().y())

        if event.button() == QtGui.Qt.MouseButton.MiddleButton:
            self.camera.drag_start(p_cp[0], p_cp[1])
            self.update()
            return

        if event.button() == QtGui.Qt.MouseButton.RightButton:
            if event.modifiers() & QtGui.Qt.KeyboardModifier.ControlModifier:
                self.toggle_visibility(p_cp)
                self.update()
                return

            self.delete(p_cp)
            self.update()
            return

        if event.button() == QtGui.Qt.MouseButton.LeftButton:
            point = self.find_keypoint_at_pos(p_cp)
            if point is not None:
                p = self.camera.view_to_world(*p_cp)
                p_ip = self.image_frame.world_to_imagepx(*p)
                p_i = self.image_frame.imagepx_to_image01(*p_ip)
                self.dragging_point = point
                self.dragging_point_start_pos_i = p_i
                self.dragging_point_current_pos_i = p_i
            else:
                visible = not event.modifiers() & QtGui.Qt.KeyboardModifier.ControlModifier
                self.place(p_cp, visible)
                self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == QtGui.Qt.MouseButton.MiddleButton:
            self.camera.drag_end()
            return

        p_cp = (event.pos().x(), event.pos().y())
        if event.button() == QtGui.Qt.MouseButton.LeftButton:
            if self.dragging_point is not None and self.dragging_point_start_pos_i is not None:
                dragging_point_start_pos_ip = self.image_frame.image01_to_imagepx(*self.dragging_point_start_pos_i)
                dragging_point_start_pos = self.image_frame.imagepx_to_world(*dragging_point_start_pos_ip)
                dragging_point_start_pos_cp = self.camera.world_to_view(*dragging_point_start_pos)

                dist = (p_cp[0] - dragging_point_start_pos_cp[0]) ** 2 + (p_cp[1] - dragging_point_start_pos_cp[1]) ** 2
                if dist > DRAG_THRESHOLD:
                    self.dragging_point.move(self.dragging_point_current_pos_i)
                else:
                    self.place(dragging_point_start_pos_cp)

            self.dragging_point = None
            self.dragging_point_start_pos_i = None
            self.dragging_point_current_pos_i = None
            self.update()

    def mouseMoveEvent(self, event):
        p_cp = (event.pos().x(), event.pos().y())

        self.mouse_pos_cp = p_cp

        needs_update = False

        if self.camera.dragging:
            self.camera.drag_update(*p_cp)
            needs_update = True

        if self.dragging_point is not None:
            p = self.camera.view_to_world(*p_cp)
            p_ip = self.image_frame.world_to_imagepx(*p)
            p_i = self.image_frame.imagepx_to_image01(*p_ip)
            self.dragging_point_current_pos_i = p_i
            needs_update = True

        current_member = self.model.get_selected_member()
        if isinstance(current_member, BoundingBoxDelegate):
            needs_update = True

        if needs_update:
            self.update()

    def keyPressEvent(self, event):
        if event.key() == QtGui.Qt.Key.Key_Shift:
            self.show_all_labels = True
            self.update()
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == QtGui.Qt.Key.Key_Shift:
            self.show_all_labels = False
            self.update()
        if event.key() == QtGui.Qt.Key.Key_Control:
            self.context_mode = False
            self.context_index = 0
            self.update()
        super().keyReleaseEvent(event)

    def wheelEvent(self, event):
        if not self.hasFocus():
            self.setFocus(Qt.FocusReason.MouseFocusReason)

        if event.modifiers() & QtGui.Qt.KeyboardModifier.ControlModifier:
            context = self.model.get_context()
            if not context:
                return

            before, current, after = context

            context_min = -len(before)
            context_max = len(after)

            self.context_mode = True
            if event.angleDelta().y() > 0:
                self.context_index -= 1
                if self.context_index < context_min:
                    self.context_index = context_min
            else:
                self.context_index += 1
                if self.context_index > context_max:
                    self.context_index = context_max
            self.update()
            return

        zoom = self.camera.zoom
        if event.angleDelta().y() > 0:
            zoom *= 1.1
        else:
            zoom /= 1.1

        mouse_pos = event.position()
        mouse_x = mouse_pos.x()
        mouse_y = mouse_pos.y()

        self.camera.set_zoom_around(zoom, mouse_x, mouse_y)
        self.update()
        super().wheelEvent(event)

    def focusOutEvent(self, e):
        # If focus leaves the label while viewing context, snap back
        if self.context_mode:
            self.context_mode = False
            self.context_index = 0
            self.update()

    def resizeEvent(self, event):
        self.camera.set_view_size(self.width(), self.height())
        self.update()
        super().resizeEvent(event)

    def _settings_changed(self, brightness: float, contrast: float):
        self.brightness = brightness
        self.contrast = contrast
        self.update()

    def _p_or_dragging_p(self, point: KeypointDelegate):
        if not self.dragging_point:
            return point.p
        if point.instance_id != self.dragging_point.instance_id or point.keypoint_index != self.dragging_point.keypoint_index:
            return point.p
        return self.dragging_point_current_pos_i

    def _adjust_brightness_contrast(self, image: np.ndarray, brightness: float, contrast: float) -> np.ndarray:
        """
        Adjust brightness and contrast of a uint8 image.

        brightness: -1 = black, 0 = original, +1 = white
        contrast:   -1 = flat gray, 0 = original, +1 = high contrast
        """

        if image.dtype != np.uint8:
            raise ValueError("Image must be uint8")

        # Contrast scale (alpha)
        alpha = 1.0 + contrast

        # Brightness offset (beta)
        beta = brightness * 255.0

        img = image.astype(np.float32)

        # Apply contrast around midpoint (128)
        img = alpha * (img - 128.0) + 128.0

        # Apply brightness
        img = img + beta

        return np.clip(img, 0, 255).astype(np.uint8)

    def draw_instances(self, painter: QPainter, instances: List[InstanceDelegate]):
        for instance in instances:
            for point_index1, point_index2 in instance.skeleton:
                kp1 = instance.keypoints[point_index1]
                kp2 = instance.keypoints[point_index2]
                p1_i = self._p_or_dragging_p(kp1)
                p2_i = self._p_or_dragging_p(kp2)

                if p1_i is None or p2_i is None or kp1.visibility < 0.5 or kp2.visibility < 0.5:
                    continue

                self.renderer.draw_skeleton_line(painter, p1_i, p2_i, opacity=1)

        for instance in instances:
            if instance.type.box_type == BoundingBoxType.AUTOMATIC:
                continue

            box = instance.box.box
            if box is not None:
                p1, p2 = box
                self.renderer.draw_bounding_box(painter, p1, p2)

        for instance in instances:
            for point in instance.keypoints:
                p = self._p_or_dragging_p(point)
                if p is not None and point.visibility > 0.5:
                    visible = point.visibility > 1.5
                    color = QtGui.QColor(*point.color)
                    self.renderer.draw_point(painter, p, color, visible, opacity=1)

    def draw_all_labels(self, painter, instances: List[InstanceDelegate]):
        for instance in instances:
            points = [point.p for point in instance.keypoints if point.p is not None]
            box = instance.box.box
            if box is not None:
                points.extend(box)

            min_x = min([p[0] for p in points])
            max_x = max([p[0] for p in points])
            min_y = min([p[1] for p in points])
            max_y = max([p[1] for p in points])

            p1_i = (min_x, min_y)
            p2_i = (max_x, max_y)

            self.renderer.draw_instance_label(painter, p1_i, p2_i, instance.name)

            for point in instance.keypoints:
                if point.p is None:
                    continue
                p_image = point.p
                self.renderer.draw_point_label(painter, p_image, point.name)

    def draw_hovered_label(self, painter):
        hover_point = self.find_keypoint_at_pos(self.mouse_pos_cp)

        if hover_point is not None:
            p_image = hover_point.p
            label_str = hover_point.name
            self.renderer.draw_point_label(painter, p_image, label_str)

    def draw_bounding_box_in_progress(self, painter):
        if self.bounding_box_start_pos_i is None:
            return

        p1_i = self.bounding_box_start_pos_i

        p2_cp = self.mouse_pos_cp
        p2 = self.camera.view_to_world(*p2_cp)
        p2_ip = self.image_frame.world_to_imagepx(*p2)
        p2_i = self.image_frame.imagepx_to_image01(*p2_ip)

        p2_i = (max(0.0, p2_i[0]), max(0.0, p2_i[1]))
        p2_i = (min(1.0, p2_i[0]), min(1.0, p2_i[1]))

        self.renderer.draw_bounding_box(painter, p1_i, p2_i)

    def draw_crosshair(self, painter):
        current_member = self.model.get_selected_member()

        if not isinstance(current_member, BoundingBoxDelegate):
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        mouse_pos = self.camera.view_to_world(*self.mouse_pos_cp)
        mouse_pos_ip = self.image_frame.world_to_imagepx(*mouse_pos)
        mouse_pos_i = self.image_frame.imagepx_to_image01(*mouse_pos_ip)

        #self.setCursor(Qt.CursorShape.BlankCursor)
        self.renderer.draw_crosshair(painter, mouse_pos_i)

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QtGui.QPainter(self)

        if self.model:
            image = None
            if self.context_mode:
                context = self.model.get_context()
                if context:
                    before, current, after = context
                    context_frames = before + [current] + after
                    image = context_frames[self.context_index + len(before)]
            if image is None:
                image = self.model.get_image()

            image = self._adjust_brightness_contrast(image, self.brightness, self.contrast)

            self.renderer.draw_image(painter, image)

            instances = self.model.get_instances()
            self.draw_instances(painter, instances)
            if self.show_all_labels:
                self.draw_all_labels(painter, instances)
            self.draw_hovered_label(painter)
            self.draw_bounding_box_in_progress(painter)
            self.draw_crosshair(painter)

        painter.end()
