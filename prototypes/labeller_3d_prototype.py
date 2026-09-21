"""Conceptual prototype: a stereo ("3D") labeller.

Two synthetic camera views of the same wireframe cube are shown in tabs, each using the
real Junip3R `PoseEditor`/`PoseImageModel` widget (fed with in-memory, non-file-backed
repositories) so keypoints can actually be dragged around, including placing extra
instances. A separate, non-modal Qt3D window triangulates each matched instance pair's
keypoints - matched by name within an instance, matched across cameras by creation
order - into 3D and updates live as either tab is edited. The 3D window is itself
editable too: dragging a sphere reprojects that point through each camera's known
projection matrix and writes the result back into both 2D views (the exact inverse of
triangulation), which then re-triangulates and redraws the 3D scene from that.

Deliberately out of scope: lens undistortion (direct linear triangulation/projection
only), disk persistence/project structure, boxes/polygons/polylines. Not part of the
`junip3r` package - a standalone script, run directly.
"""
import sys
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

import cv2
import numpy as np
from PySide6 import Qt3DCore as _qt3dcore_module, Qt3DExtras as _qt3dextras_module, \
    Qt3DRender as _qt3drender_module
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QQuaternion, QVector3D
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QTabWidget, QVBoxLayout, QWidget

# This PySide6 build exposes these modules' classes one level deeper than the module
# itself (e.g. the real classes live on `Qt3DExtras.Qt3DExtras`, not `Qt3DExtras`
# directly) - unwrap that nesting once here so the rest of the file can use the classes
# via the plain `Qt3DCore.QEntity` / `Qt3DExtras.Qt3DWindow` / `Qt3DRender.QPointLight`
# spelling everyone expects.
Qt3DCore = _qt3dcore_module.Qt3DCore
Qt3DExtras = _qt3dextras_module.Qt3DExtras
Qt3DRender = _qt3drender_module.Qt3DRender

from junip3r.common.labels.data import Instance as DataInstance, Keypoint as DataKeypoint
from junip3r.labeller.config.data import InstanceType, MemberType, SkeletonType
from junip3r.labeller.controller.geometry import clamp_to_image01
from junip3r.labeller.data.repository.abc import IImageRepository, ILabelRepository
from junip3r.labeller.data.repository.selection import SelectionRepository
from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.labeller.model.app_model import AppModel
from junip3r.labeller.model.label_model import LabelModel
from junip3r.labeller.model.pose_image_model import PoseImageModel
from junip3r.labeller.widgets.pose_editor import PoseEditor
from junip3r.setup.preview.data.repository.setup_preview_label_repository import SetupPreviewConfigRepository

IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480

CUBE_CORNERS_3D: List[Tuple[float, float, float]] = [
    (x, y, z) for x in (-1.0, 1.0) for y in (-1.0, 1.0) for z in (-1.0, 1.0)
]
CORNER_NAMES = [f"corner_{i}" for i in range(len(CUBE_CORNERS_3D))]
CUBE_EDGES: List[Tuple[int, int]] = [
    (a, b) for a in range(len(CUBE_CORNERS_3D)) for b in range(a + 1, len(CUBE_CORNERS_3D))
    # two corners are connected by a cube edge iff they differ in exactly one coordinate
    if sum(ca != cb for ca, cb in zip(CUBE_CORNERS_3D[a], CUBE_CORNERS_3D[b])) == 1
]


# --- Pinhole camera geometry (no undistortion) -------------------------------------

def build_extrinsics(position, target, up=(0.0, 1.0, 0.0)) -> Tuple[np.ndarray, np.ndarray]:
    position = np.array(position, dtype=np.float64)
    target = np.array(target, dtype=np.float64)
    up = np.array(up, dtype=np.float64)

    forward = target - position
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    down = np.cross(forward, right)

    rotation = np.stack([right, down, forward], axis=0)
    translation = (-rotation @ position).reshape(3, 1)
    return rotation, translation


def projection_matrix(intrinsics: np.ndarray, rotation: np.ndarray, translation: np.ndarray) -> np.ndarray:
    return intrinsics @ np.hstack([rotation, translation])


def project_point(projection: np.ndarray, point_3d: Tuple[float, float, float]) -> Tuple[float, float]:
    homogeneous = np.array([point_3d[0], point_3d[1], point_3d[2], 1.0])
    projected = projection @ homogeneous
    return float(projected[0] / projected[2]), float(projected[1] / projected[2])


def pixel_to_image01(point_px: Tuple[float, float]) -> Tuple[float, float]:
    return point_px[0] / IMAGE_WIDTH, point_px[1] / IMAGE_HEIGHT


def image01_to_pixel(point_01: Tuple[float, float]) -> Tuple[float, float]:
    return point_01[0] * IMAGE_WIDTH, point_01[1] * IMAGE_HEIGHT


def render_wireframe(points_2d: Sequence[Tuple[float, float]]) -> np.ndarray:
    """A real (if crude) synthetic photo: a blank canvas with the projected cube edges
    drawn on it. Colors are RGB tuples directly (this array is never round-tripped
    through cv2.imread/imwrite, so there is no BGR swap to account for) - PoseImage
    expects RGB uint8 (see PoseImage._numpy_to_qimage_owned).
    """
    image = np.full((IMAGE_HEIGHT, IMAGE_WIDTH, 3), 30, dtype=np.uint8)
    for a, b in CUBE_EDGES:
        pa = tuple(int(round(c)) for c in points_2d[a])
        pb = tuple(int(round(c)) for c in points_2d[b])
        cv2.line(image, pa, pb, color=(80, 200, 255), thickness=2, lineType=cv2.LINE_AA)
    return image


# --- Minimal in-memory repositories (IImageRepository / ILabelRepository) ----------

class InMemoryImageRepository(IImageRepository):
    def __init__(self, image: np.ndarray, name: str):
        self._image = image
        self._name = name

    def get_num_images(self) -> int:
        return 1

    def get_image(self, image_index: int) -> np.ndarray:
        return self._image

    def get_image_name(self, image_index: int) -> str:
        return self._name

    def get_image_file(self, image_index: int):
        return None


class InMemoryLabelRepository(ILabelRepository):
    def __init__(self, instances: List[DataInstance]):
        self._instances = instances

    def get_instances(self, image_index: int) -> Sequence[DataInstance]:
        return self._instances

    def set_instances(self, image_index: int, instances: Sequence[DataInstance]) -> None:
        self._instances = list(instances)


# --- Shared instance type + per-camera seed labels ----------------------------------

def build_cube_instance_type() -> InstanceType:
    members = [
        MemberType(name=name, type=LabellerObjectType.KEYPOINT, color=(255, 90, 90))
        for name in CORNER_NAMES
    ]
    skeleton_lines = [(CORNER_NAMES[a], CORNER_NAMES[b]) for a, b in CUBE_EDGES]
    return InstanceType(
        name="cube",
        members=members,
        skeleton=SkeletonType(lines=skeleton_lines, color=(180, 180, 180)),
        color=(90, 170, 255),
    )


def build_seed_instance(instance_type: InstanceType, points_2d: Sequence[Tuple[float, float]]) -> DataInstance:
    keypoints = [
        DataKeypoint(name=member.name, p=point, visibility=2.0)
        for member, point in zip(instance_type.members, points_2d)
    ]
    return DataInstance(id=str(uuid.uuid4()), type=instance_type.name, name="cube", members=keypoints)


def build_camera_stack(instance_type: InstanceType, image: np.ndarray, image_name: str,
                        points_2d: Sequence[Tuple[float, float]]) -> Tuple[PoseEditor, PoseImageModel]:
    image_repository = InMemoryImageRepository(image, image_name)
    label_repository = InMemoryLabelRepository([build_seed_instance(instance_type, points_2d)])

    config_repository = SetupPreviewConfigRepository()
    config_repository.set_instance_types(0, [instance_type])
    config_repository.set_expected_instances(0, [])

    selection_repository = SelectionRepository()

    label_model = LabelModel(config_repository, label_repository)
    app_model = AppModel(image_repository, label_model, selection_repository)
    pose_image_model = PoseImageModel(app_model)

    pose_editor = PoseEditor()
    pose_editor.set_model(pose_image_model)

    return pose_editor, pose_image_model


# --- Non-modal Qt3D triangulation preview -------------------------------------------

# Cycled by instance-pair index so multiple triangulated cubes stay visually distinct.
GROUP_SPHERE_COLORS = [QColor("orange"), QColor("deepSkyBlue"), QColor("violet"),
                       QColor("yellow"), QColor("mediumSpringGreen")]


@dataclass
class _InstanceGroup:
    """One triangulated instance's worth of Qt3D entities (8 corner spheres + 12 edge
    cylinders). `root_entity` owns every entity below it, so dropping a group is just
    reparenting/deleting this one entity.
    """
    root_entity: "Qt3DCore.QEntity"
    sphere_transforms: Dict[str, "Qt3DCore.QTransform"] = field(default_factory=dict)
    edge_items: Dict[Tuple[str, str], Tuple["Qt3DExtras.QCylinderMesh", "Qt3DCore.QTransform"]] = \
        field(default_factory=dict)
    # Components that only need to stay alive (no direct lookup) - notably the corner
    # QObjectPickers. Kept unparented and referenced only from here, rather than
    # constructor-parented to their entity like the other components: combining a
    # constructor-parented QObjectPicker with a constructor-parented QTransform on the
    # same entity reproducibly crashed ("QTransform already deleted") in this PySide6
    # build, so picking's aliveness is deliberately handled the older, more conservative
    # way (a plain Python reference) instead.
    extra_refs: List[object] = field(default_factory=list)


class TriangulationPreviewWindow(Qt3DExtras.Qt3DWindow):
    """A separate top-level window (QWindow, never .exec()'d - inherently non-modal)
    showing one triangulated group of entities per matched instance pair (see
    LabellerPrototypeWindow._triangulate_and_push). Groups are built/torn down on demand
    as the number of matched instances changes; each group's own entities are built once
    and updated in place afterward, same as the original single-cube version.
    """

    # (group_index, corner_name, world_x, world_y, world_z) - emitted while a sphere is
    # being dragged, so the owner can reproject that 3D position into both 2D views.
    point_dragged = Signal(int, str, float, float, float)

    def __init__(self):
        super().__init__()
        self.setTitle("3D Triangulated Preview")
        # A bare QWindow shown without an explicit size comes up at a tiny default
        # geometry - easy to mistake for "nothing rendered".
        self.resize(900, 700)
        self.defaultFrameGraph().setClearColor(QColor(45, 45, 55))

        picking_settings = self.renderSettings().pickingSettings()
        picking_settings.setPickMethod(Qt3DRender.QPickingSettings.PickMethod.TrianglePicking)
        picking_settings.setPickResultMode(Qt3DRender.QPickingSettings.PickResultMode.NearestPick)

        self._root_entity = Qt3DCore.QEntity()
        self._edges: List[Tuple[str, str]] = [(CORNER_NAMES[a], CORNER_NAMES[b]) for a, b in CUBE_EDGES]
        self._groups: List[_InstanceGroup] = []
        # (plane_point, plane_normal) for the point currently being dragged, or None -
        # set on picker press, cleared on release. See _unproject/_intersect_ray_plane.
        self._active_drag_plane: "Tuple[QVector3D, QVector3D] | None" = None

        self._build_lighting()
        self._build_camera()

        self.setRootEntity(self._root_entity)

    def _build_lighting(self):
        light_entity = Qt3DCore.QEntity(self._root_entity)
        light = Qt3DRender.QPointLight(light_entity)
        light.setColor(QColor("white"))
        light.setIntensity(1.0)
        light_entity.addComponent(light)

        light_transform = Qt3DCore.QTransform(light_entity)
        light_transform.setTranslation(QVector3D(10.0, 10.0, 10.0))
        light_entity.addComponent(light_transform)

    def _build_camera(self):
        camera = self.camera()
        camera.lens().setPerspectiveProjection(45.0, 16.0 / 9.0, 0.1, 1000.0)
        camera.setPosition(QVector3D(0.0, 2.0, 8.0))
        camera.setViewCenter(QVector3D(0.0, 0.0, 0.0))

        # QOrbitCameraController has no public API to rebind which mouse button orbits
        # (it's hardcoded to the left button, same as QObjectPicker's drag) - rather than
        # reimplementing camera navigation by hand, it's simplest to just disable orbit
        # for the duration of a point drag (see _on_sphere_pressed/_released), so the two
        # never actually fight over left-click at the same time.
        self._orbit_controller = Qt3DExtras.QOrbitCameraController(self._root_entity)
        self._orbit_controller.setCamera(camera)
        self._orbit_controller.setLinearSpeed(20.0)
        self._orbit_controller.setLookSpeed(180.0)

    def closeEvent(self, event):
        # Qt3DWindow doesn't reinitialize its GL surface cleanly after a real close
        # (reopening the same instance came back blank and laggy) - hide instead, so
        # the native surface/context stays alive and "Show 3D Preview" just re-shows it.
        event.ignore()
        self.hide()

    def _unproject(self, screen_pos) -> Tuple[QVector3D, QVector3D]:
        """The mouse ray for the current camera, in world space. QObjectPicker's own
        `worldIntersection` is only trustworthy for the initial press (a real mesh hit);
        once dragging moves the point away from the ray, it stops reflecting a sensible
        position (observed as the point drifting toward the camera) - so drags compute
        their own ray/plane intersection instead (see _on_sphere_dragged).
        """
        camera = self.camera()
        inverse_view_projection, invertible = (camera.projectionMatrix() * camera.viewMatrix()).inverted()
        if not invertible:
            return camera.position(), camera.viewVector().normalized()

        width = max(self.width(), 1)
        height = max(self.height(), 1)
        ndc_x = (2.0 * screen_pos.x() / width) - 1.0
        ndc_y = 1.0 - (2.0 * screen_pos.y() / height)

        near_point = inverse_view_projection.map(QVector3D(ndc_x, ndc_y, -1.0))
        far_point = inverse_view_projection.map(QVector3D(ndc_x, ndc_y, 1.0))
        direction = far_point - near_point
        if direction.length() > 1e-9:
            direction = direction.normalized()
        return near_point, direction

    @staticmethod
    def _intersect_ray_plane(ray_origin: QVector3D, ray_direction: QVector3D,
                              plane_point: QVector3D, plane_normal: QVector3D) -> "QVector3D | None":
        denominator = QVector3D.dotProduct(ray_direction, plane_normal)
        if abs(denominator) < 1e-9:
            return None
        t = QVector3D.dotProduct(plane_point - ray_origin, plane_normal) / denominator
        if t < 0:
            return None
        return ray_origin + ray_direction * t

    def _build_group(self, group_index: int, sphere_color: QColor) -> _InstanceGroup:
        group_root = Qt3DCore.QEntity(self._root_entity)
        group = _InstanceGroup(root_entity=group_root)

        for name in CORNER_NAMES:
            entity = Qt3DCore.QEntity(group_root)

            # entity.addComponent() registers a component for rendering, but does not
            # take QObject ownership of it (Qt3D components can be shared across
            # entities) - passing `entity` as the constructor's parent is what actually
            # keeps these alive; without it, mesh/material had no reference anywhere and
            # were garbage-collected right after this loop body, leaving empty entities.
            mesh = Qt3DExtras.QSphereMesh(entity)
            mesh.setRadius(0.08)

            material = Qt3DExtras.QPhongMaterial(entity)
            material.setDiffuse(sphere_color)

            transform = Qt3DCore.QTransform(entity)

            # dragEnabled keeps `moved` firing (with a recomputed world-space pick
            # position) for as long as the button stays down, even once the mouse
            # ray no longer intersects this tiny sphere - that's what makes a real drag
            # possible instead of only a single click-triggered pick.
            # Deliberately NOT constructor-parented to `entity` like the other
            # components above (see _InstanceGroup.extra_refs) - kept alive via
            # extra_refs instead.
            picker = Qt3DRender.QObjectPicker()
            picker.setDragEnabled(True)
            picker.pressed.connect(lambda event: self._on_sphere_pressed(event))
            picker.moved.connect(lambda event, gi=group_index, n=name: self._on_sphere_dragged(gi, n, event))
            picker.released.connect(lambda event: self._on_sphere_released())

            entity.addComponent(mesh)
            entity.addComponent(material)
            entity.addComponent(transform)
            entity.addComponent(picker)

            group.sphere_transforms[name] = transform
            group.extra_refs.append(picker)

        for a, b in self._edges:
            entity = Qt3DCore.QEntity(group_root)

            mesh = Qt3DExtras.QCylinderMesh(entity)
            mesh.setRadius(0.02)
            mesh.setRings(2)
            mesh.setSlices(8)

            material = Qt3DExtras.QPhongMaterial(entity)
            material.setDiffuse(QColor("lightGray"))

            transform = Qt3DCore.QTransform(entity)

            entity.addComponent(mesh)
            entity.addComponent(material)
            entity.addComponent(transform)

            group.edge_items[(a, b)] = (mesh, transform)

        return group

    def _on_sphere_pressed(self, event):
        # Disable orbit for the duration of this drag (see _build_camera) and fix the
        # drag plane at the point's real position/depth, facing the camera, so the drag
        # has a well-defined 3D meaning instead of drifting once the mouse ray leaves
        # the (tiny) sphere mesh.
        self._orbit_controller.setEnabled(False)
        plane_point = event.worldIntersection()
        plane_normal = self.camera().viewVector().normalized()
        self._active_drag_plane = (plane_point, plane_normal)

    def _on_sphere_released(self):
        self._orbit_controller.setEnabled(True)
        self._active_drag_plane = None

    def _on_sphere_dragged(self, group_index: int, name: str, event):
        if self._active_drag_plane is None:
            return
        plane_point, plane_normal = self._active_drag_plane

        ray_origin, ray_direction = self._unproject(event.position())
        world_pos = self._intersect_ray_plane(ray_origin, ray_direction, plane_point, plane_normal)
        if world_pos is None:
            return

        self.point_dragged.emit(group_index, name, world_pos.x(), world_pos.y(), world_pos.z())

    def _set_group_count(self, count: int):
        while len(self._groups) < count:
            group_index = len(self._groups)
            color = GROUP_SPHERE_COLORS[group_index % len(GROUP_SPHERE_COLORS)]
            self._groups.append(self._build_group(group_index, color))
        while len(self._groups) > count:
            group = self._groups.pop()
            # Drop it from the scene graph before releasing the last Python reference,
            # so its (now-orphaned) entities/components actually get cleaned up.
            group.root_entity.setParent(None)
            group.root_entity.deleteLater()

    def update_scene(self, points_by_group: List[Dict[str, Tuple[float, float, float]]]):
        self._set_group_count(len(points_by_group))
        for group, points in zip(self._groups, points_by_group):
            self._update_group(group, points)

    @staticmethod
    def _update_group(group: _InstanceGroup, points: Dict[str, Tuple[float, float, float]]):
        for name, (x, y, z) in points.items():
            transform = group.sphere_transforms.get(name)
            if transform is not None:
                transform.setTranslation(QVector3D(x, y, z))

        for (a, b), (mesh, transform) in group.edge_items.items():
            point_a = points.get(a)
            point_b = points.get(b)
            if point_a is None or point_b is None:
                continue

            vector_a = QVector3D(*point_a)
            vector_b = QVector3D(*point_b)
            direction = vector_b - vector_a
            length = direction.length()

            mesh.setLength(max(length, 0.001))
            transform.setTranslation((vector_a + vector_b) * 0.5)
            if length > 1e-6:
                rotation = QQuaternion.rotationTo(QVector3D(0.0, 1.0, 0.0), direction.normalized())
                transform.setRotation(rotation)


# --- Main window: tabbed stereo editors + live triangulation ------------------------

class LabellerPrototypeWindow(QMainWindow):
    def __init__(self, cameras: Dict[str, Tuple[PoseEditor, PoseImageModel, np.ndarray]],
                 preview_window: TriangulationPreviewWindow):
        super().__init__()
        self.setWindowTitle("3D Labeller Prototype")

        self._cameras = cameras
        self._preview_window = preview_window

        tabs = QTabWidget()
        for name, (editor, _, _) in cameras.items():
            tabs.addTab(editor, name)

        show_preview_button = QPushButton("Show 3D Preview")
        show_preview_button.clicked.connect(self._show_preview)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(tabs)
        layout.addWidget(show_preview_button)
        self.setCentralWidget(central)

        for _, pose_image_model, _ in cameras.values():
            pose_image_model.image_state_changed.connect(self._on_state_changed)

        self._preview_window.point_dragged.connect(self._on_3d_point_dragged)

        self._triangulate_and_push()

    def _show_preview(self):
        self._preview_window.show()
        self._preview_window.requestActivate()

    def _on_state_changed(self, state, flags):
        self._triangulate_and_push()

    def _triangulate_and_push(self):
        names = list(self._cameras.keys())
        if len(names) != 2:
            return

        _, model_a, projection_a = self._cameras[names[0]]
        _, model_b, projection_b = self._cameras[names[1]]

        # Instances are matched across the two views by creation order (the n-th
        # placed instance in camera A pairs with the n-th in camera B) - there's no
        # richer cross-view identity than that here, so extra/unmatched trailing
        # instances on either side are simply not shown until the other view catches up.
        instances_a = self._current_instances_keypoints(model_a)
        instances_b = self._current_instances_keypoints(model_b)

        points_by_group: List[Dict[str, Tuple[float, float, float]]] = []
        for points_a, points_b in zip(instances_a, instances_b):
            common_names = [name for name in points_a if name in points_b]
            if not common_names:
                points_by_group.append({})
                continue

            array_a = np.array([points_a[name] for name in common_names], dtype=np.float64).T
            array_b = np.array([points_b[name] for name in common_names], dtype=np.float64).T

            triangulated = cv2.triangulatePoints(projection_a, projection_b, array_a, array_b)
            triangulated /= triangulated[3]
            points_by_group.append({name: tuple(triangulated[:3, i]) for i, name in enumerate(common_names)})

        self._preview_window.update_scene(points_by_group)

    @staticmethod
    def _current_instances_keypoints(pose_image_model: PoseImageModel) -> List[Dict[str, Tuple[float, float]]]:
        """One dict of {keypoint name -> pixel position} per placed instance, in
        creation order. The always-present "add new instance" placeholder (every
        keypoint unset) is skipped via `is_set`, so it never claims a pairing slot.
        """
        result: List[Dict[str, Tuple[float, float]]] = []
        for instance in pose_image_model.get_instances():
            if not instance.is_set:
                continue
            points: Dict[str, Tuple[float, float]] = {}
            for member in instance.members:
                if member.type == LabellerObjectType.KEYPOINT and member.p is not None:
                    points[member.name] = image01_to_pixel(member.p)
            result.append(points)
        return result

    def _on_3d_point_dragged(self, group_index: int, name: str, x: float, y: float, z: float):
        """The inverse of triangulation: reproject the dragged 3D point through each
        camera's known (fixed) projection matrix and write the result back into that
        camera's own keypoint - the same "n-th placed instance" pairing used going the
        other way in _triangulate_and_push. Re-triangulating afterward (both
        move_keypoint calls flow synchronously back through _on_state_changed) is what
        actually redraws the 3D preview, so this never touches it directly.
        """
        for _, pose_image_model, projection in self._cameras.values():
            instance = self._nth_set_instance(pose_image_model, group_index)
            if instance is None:
                continue
            member = next((m for m in instance.members if m.name == name), None)
            if member is None:
                continue

            instance_id, member_id = member.path
            point_px = project_point(projection, (x, y, z))
            point_01 = clamp_to_image01(pixel_to_image01(point_px))
            pose_image_model.move_keypoint(instance_id, member_id, point_01)

    @staticmethod
    def _nth_set_instance(pose_image_model: PoseImageModel, index: int):
        set_index = -1
        for instance in pose_image_model.get_instances():
            if not instance.is_set:
                continue
            set_index += 1
            if set_index == index:
                return instance
        return None


def main():
    app = QApplication(sys.argv)

    instance_type = build_cube_instance_type()
    intrinsics = np.array([[600.0, 0.0, IMAGE_WIDTH / 2], [0.0, 600.0, IMAGE_HEIGHT / 2], [0.0, 0.0, 1.0]])

    camera_specs = {
        "Camera A": ((-1.0, 0.0, -6.0), (0.0, 0.0, 0.0)),
        "Camera B": ((1.0, 0.0, -6.0), (0.0, 0.0, 0.0)),
    }

    cameras: Dict[str, Tuple[PoseEditor, PoseImageModel, np.ndarray]] = {}
    for name, (position, target) in camera_specs.items():
        rotation, translation = build_extrinsics(position, target)
        projection = projection_matrix(intrinsics, rotation, translation)
        points_2d_px = [project_point(projection, corner) for corner in CUBE_CORNERS_3D]
        image = render_wireframe(points_2d_px)

        # The labeller stores/edits keypoints in normalized [0,1] image-fraction
        # coordinates (see EditorController._finish_drag_keypoint -> clamp_to_image01,
        # and Renderer.draw_keypoint(p_image01, ...)) - not pixels. Seed in that space so
        # a freshly-dragged point (also image01) stays on the same scale as an untouched
        # one; pixel_to_image01/image01_to_pixel below convert back at the triangulation
        # boundary, where our pixel-based intrinsics/projection matrices need real pixels.
        points_2d_image01 = [pixel_to_image01(p) for p in points_2d_px]

        editor, pose_image_model = build_camera_stack(instance_type, image, name, points_2d_image01)
        cameras[name] = (editor, pose_image_model, projection)

    preview_window = TriangulationPreviewWindow()

    main_window = LabellerPrototypeWindow(cameras, preview_window)
    main_window.resize(1000, 700)
    main_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
