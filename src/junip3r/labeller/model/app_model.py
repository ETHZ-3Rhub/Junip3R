from pathlib import Path
from typing import Optional, Sequence, List, Iterable

import numpy as np

from junip3r.common.tags.data import Tags
from junip3r.labeller.config.data import InstanceType
from junip3r.labeller.data.repository.abc import IImageRepository, ISelectionRepository, ITagRepository
from junip3r.labeller.data.types.abc import InstanceID, Selection, Point, Box, InstanceMember
from junip3r.labeller.data.types.data import Instance, Keypoint, BoundingBox, Polygon, Polyline
from junip3r.labeller.data.types.mutable import MutableInstance, MutableKeypoint, MutableBoundingBox, \
    MutablePolygon, MutablePolyline, MutableInstanceMember
from junip3r.labeller.model.abc import IUndoModel, IReadOnlyAppModel
from junip3r.labeller.model.label_model import LabelModel


class _NullTagRepository:
    """Used when a real ITagRepository isn't wired up (e.g. the setup preview app)."""

    def get_tags(self, image_index: int) -> Tags:
        return {}

    def set_tags(self, image_index: int, tags: Tags) -> None:
        pass


def _freeze_member(instance_id: str, member: MutableInstanceMember) -> InstanceMember:
    if isinstance(member, MutableKeypoint):
        return Keypoint(instance_id, 0, member.name, member.color, member.p, member.visibility, id=member.id)
    elif isinstance(member, MutableBoundingBox):
        return BoundingBox(instance_id, 0, member.name, member.color, member.box, id=member.id)
    elif isinstance(member, MutablePolygon):
        polygon = Polygon(instance_id, 0, member.name, member.color, member.num_points, [], id=member.id)
        return polygon.with_points(member.points)
    elif isinstance(member, MutablePolyline):
        polyline = Polyline(instance_id, 0, member.name, member.color, member.num_points, [], id=member.id)
        return polyline.with_points(member.points)
    else:
        raise ValueError(f"Unsupported member type: {type(member)}")


def freeze(mutable: MutableInstance) -> Instance:
    members = tuple(_freeze_member(mutable.instance_id, m) for m in mutable.members)
    return Instance(mutable.instance_id, mutable.name, mutable.instance_type, members, mutable.skeleton)


def _thaw_member(member: InstanceMember) -> MutableInstanceMember:
    if isinstance(member, Keypoint):
        return MutableKeypoint(member.id, member.name, member.color, member.p, member.visibility)
    elif isinstance(member, BoundingBox):
        return MutableBoundingBox(member.id, member.name, member.color, member.box)
    elif isinstance(member, Polygon):
        return MutablePolygon(member.id, member.name, member.color, member.num_points, [p.p for p in member.points])
    elif isinstance(member, Polyline):
        return MutablePolyline(member.id, member.name, member.color, member.num_points, [p.p for p in member.points])
    else:
        raise ValueError(f"Unsupported member type: {type(member)}")


def thaw(instance: Instance) -> MutableInstance:
    # AppModel only ever thaws real, already-committed instances - PoseImageModel's
    # synthesized "Add new instance" placeholder (instance_id=None) never reaches
    # set_instances/insert_instance (see SetupPreviewLabelRepository's docstring).
    assert instance.instance_id is not None, "Cannot thaw a placeholder instance (instance_id is None)"
    members = [_thaw_member(m) for m in instance.members]
    return MutableInstance(instance.instance_id, instance.name, instance.instance_type, members, instance.skeleton)


class AppModel(IUndoModel, IReadOnlyAppModel):
    """Instance/member data goes through a LabelModel, which resolves a type-unaware
    repository's DTOs against the current instance types into a mutable working copy
    (MutableInstance) - "structural" methods (get_instances, set_instances, insert/
    remove/replace_instance, change_instance_type) freeze/thaw between that and the
    immutable Instance callers see; field-level setters (set_keypoint & co.) mutate a
    fetched MutableInstance directly. See labeller/model/label_model.py.
    """

    def __init__(
            self,
            image_repository: IImageRepository,
            label_model: LabelModel,
            selection_repository: ISelectionRepository,
            tag_repository: Optional[ITagRepository] = None,
            parent=None
    ):
        super().__init__(parent)

        self._image_repository = image_repository
        self._label_model = label_model
        self._selection_repository = selection_repository
        self._tag_repository = tag_repository or _NullTagRepository()

        self._num_images = self._image_repository.get_num_images()

    def get_num_images(self) -> int:
        return self._num_images

    def get_image(self, image_index: int) -> np.ndarray:
        return self._image_repository.get_image(image_index)

    def get_image_name(self, image_index: int) -> str:
        return self._image_repository.get_image_name(image_index)

    def get_image_file(self, image_index: int) -> Optional[Path]:
        return self._image_repository.get_image_file(image_index)

    def get_instance_types(self, image_index: int) -> Sequence[InstanceType]:
        return self._label_model.get_instance_types(image_index)

    def get_expected_instances(self, image_index: int) -> Sequence[InstanceType]:
        return self._label_model.get_expected_instances(image_index)

    def get_instances(self, image_index: int) -> Sequence[Instance]:
        return [freeze(instance) for instance in self._label_model.get_instances(image_index)]

    def get_tags(self, image_index: int) -> Tags:
        return self._tag_repository.get_tags(image_index)

    def set_tags(self, image_index: int, tags: Tags) -> None:
        self._tag_repository.set_tags(image_index, tags)

    def get_instance(self, image_index: int, instance_id: InstanceID) -> Optional[Instance]:
        instances = self.get_instances(image_index)
        return next((instance for instance in instances if instance.instance_id == instance_id), None)

    def set_instances(self, image_index: int, instances: Sequence[Instance]) -> None:
        self._label_model.set_instances(image_index, [thaw(instance) for instance in instances])

    def insert_instance(self, image_index: int, instance: Instance, insertion_index: int = None) -> None:
        instances = list(self.get_instances(image_index))
        if insertion_index is None:
            instances.append(instance)
        else:
            instances.insert(insertion_index, instance)
        self.set_instances(image_index, instances)

    def remove_instance(self, image_index: int, instance_id: InstanceID) -> None:
        instances = self.get_instances(image_index)
        instances = [instance for instance in instances if instance.instance_id != instance_id]
        self.set_instances(image_index, instances)

    def replace_instance(self, image_index: int, instance_id: InstanceID, instance: Instance) -> None:
        instances = self.get_instances(image_index)
        instances = [instance if inst.instance_id == instance_id else inst for inst in instances]
        self.set_instances(image_index, instances)

    def change_instance_type(self, image_index: int, instance_id: InstanceID, instance_type: InstanceType) -> None:
        instances = self._get_instances(image_index)
        self._get_instance(instances, instance_id).change_instance_type(instance_type)
        self._label_model.set_instances(image_index, instances)

    def get_selection(self, image_index: int) -> Optional[Selection]:
        return self._selection_repository.get_selection(image_index)

    def set_selection(self, image_index: int, selection: Optional[Selection]) -> None:
        self._selection_repository.set_selection(image_index, selection)

    def get_new_instance_type(self, image_index: int) -> InstanceType | None:
        return self._selection_repository.get_new_instance_type(image_index)

    def set_new_instance_type(self, image_index: int, instance_type: InstanceType | None) -> None:
        self._selection_repository.set_new_instance_type(image_index, instance_type)

    def get_member(self, image_index: int, selection: Selection) -> Optional[InstanceMember]:
        instance_id, member_id = selection
        instance = self.get_instance(image_index, instance_id)
        if instance is None:
            return None
        return instance.get_member(member_id)

    def _get_instances(self, image_index: int) -> List[MutableInstance]:
        return self._label_model.get_instances(image_index)

    def _get_instance(self, instances: Iterable[MutableInstance], instance_id: InstanceID) -> MutableInstance:
        # A caller reaching this is expected to have already resolved instance_id to a
        # real instance (e.g. via get_instance/get_member, which stay Optional-returning
        # lookups precisely so callers can check first and no-op instead of ever calling
        # through here) - a missing instance at this point is a caller bug, not a
        # legitimate runtime state.
        instance = next((instance for instance in instances if instance.instance_id == instance_id), None)
        if instance is None:
            raise ValueError(f"No instance with id {instance_id!r} on image")
        return instance

    def set_keypoint(self, image_index: int, selection: Selection, point: Point | None,
                     visibility: float = 2.0) -> None:
        instance_id, member_id = selection
        instances = self._get_instances(image_index)
        keypoint = self._get_instance(instances, instance_id).get_keypoint(member_id)
        keypoint.p = point
        keypoint.visibility = visibility
        self._label_model.set_instances(image_index, instances)

    def set_bounding_box(self, image_index: int, selection: Selection, box: Box | None) -> None:
        instance_id, member_id = selection
        instances = self._get_instances(image_index)
        bounding_box = self._get_instance(instances, instance_id).get_bounding_box(member_id)
        bounding_box.box = box
        self._label_model.set_instances(image_index, instances)

    def set_polygon(self, image_index: int, selection: Selection, points: Sequence[Point]) -> None:
        instance_id, member_id = selection
        instances = self._get_instances(image_index)
        polygon = self._get_instance(instances, instance_id).get_polygon(member_id)
        polygon.points = list(points)
        self._label_model.set_instances(image_index, instances)

    def set_polyline(self, image_index: int, selection: Selection, points: Sequence[Point]) -> None:
        instance_id, member_id = selection
        instances = self._get_instances(image_index)
        polyline = self._get_instance(instances, instance_id).get_polyline(member_id)
        polyline.points = list(points)
        self._label_model.set_instances(image_index, instances)

    def set_polygon_point(self, image_index: int, selection: Selection, point_index: int, point: Point) -> None:
        instance_id, member_id = selection
        instances = self._get_instances(image_index)
        polygon = self._get_instance(instances, instance_id).get_polygon(member_id)
        polygon.points[point_index] = point
        self._label_model.set_instances(image_index, instances)

    def set_polyline_point(self, image_index: int, selection: Selection, point_index: int, point: Point) -> None:
        instance_id, member_id = selection
        instances = self._get_instances(image_index)
        polyline = self._get_instance(instances, instance_id).get_polyline(member_id)
        polyline.points[point_index] = point
        self._label_model.set_instances(image_index, instances)
