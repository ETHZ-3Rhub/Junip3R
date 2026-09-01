from pathlib import Path
from typing import Optional, Sequence, cast

import numpy as np

from junip3r.labeller.data.repository.abc import ILabelRepository, IImageRepository, IConfigRepository, \
    ISelectionRepository
from junip3r.labeller.data.types.abc import InstanceID, Selection, Point, Box, IKeypoint, IInstance, IInstanceType, \
    ILabellerObject, IBoundingBox, IPolygon, IPolyline, LabellerObjectType
from junip3r.labeller.model.abc import IUndoModel, IReadOnlyAppModel


class AppModel(IUndoModel, IReadOnlyAppModel):
    """Stateless application model: every read goes straight to the repositories.

    Holds no per-image-index state, so it's safe to use from any thread and to construct
    multiple instances over the same repositories. Callers that repeatedly re-read the same
    value (e.g. the interactive editor re-displaying the current image after every edit)
    should cache at their own layer if that turns out to matter - see PoseImageModel's image
    cache for an example.
    """

    def __init__(
            self,
            image_repository: IImageRepository,
            config_repository: IConfigRepository,
            label_repository: ILabelRepository,
            selection_repository: ISelectionRepository,
            parent=None
    ):
        super().__init__(parent)

        self._image_repository = image_repository
        self._config_repository = config_repository
        self._label_repository = label_repository
        self._selection_repository = selection_repository

        self._num_images = self._image_repository.get_num_images()

    def get_num_images(self) -> int:
        return self._num_images

    def get_image(self, image_index: int) -> np.ndarray:
        return self._image_repository.get_image(image_index)

    def get_image_name(self, image_index: int) -> str:
        return self._image_repository.get_image_name(image_index)

    def get_image_file(self, image_index: int) -> Optional[Path]:
        return self._image_repository.get_image_file(image_index)

    def get_instance_types(self, image_index: int) -> Sequence[IInstanceType]:
        return self._config_repository.get_instance_types(image_index)

    def get_expected_instances(self, image_index: int) -> Sequence[IInstanceType]:
        return self._config_repository.get_expected_instances(image_index)

    def get_instances(self, image_index: int) -> Sequence[IInstance]:
        return self._label_repository.get_instances(image_index)

    def get_instance(self, image_index: int, instance_id: InstanceID) -> Optional[IInstance]:
        instances = self.get_instances(image_index)
        return next((instance for instance in instances if instance.instance_id == instance_id), None)

    def set_instances(self, image_index: int, instances: Sequence[IInstance]) -> None:
        self._label_repository.set_instances(image_index, list(instances))

    def insert_instance(self, image_index: int, instance: IInstance, insertion_index: int = None) -> None:
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

    def replace_instance(self, image_index: int, instance_id: InstanceID, instance: IInstance) -> None:
        instances = self.get_instances(image_index)
        instances = [instance if inst.instance_id == instance_id else inst for inst in instances]
        self.set_instances(image_index, instances)

    def change_instance_type(self, image_index: int, instance_id: InstanceID, instance_type: IInstanceType) -> None:
        instance = self.get_instance(image_index, instance_id)
        if instance is None:
            return
        # TODO: Gneerate correct name
        new_instance = instance_type.new_instance(instance_id=instance.instance_id, name=instance_type.name)

        for member_index, (old_member, new_member) in enumerate(zip(instance.members, new_instance.members)):
            if old_member.type != new_member.type:
                break
            if old_member.type == LabellerObjectType.KEYPOINT:
                new_member = new_member.with_p(old_member.p)
            elif old_member.type == LabellerObjectType.BOUNDING_BOX:
                new_member = new_member.with_box(old_member.box)
            elif old_member.type == LabellerObjectType.POLYGON:
                new_member = new_member.with_points(old_member.points)
            elif old_member.type == LabellerObjectType.POLYLINE:
                new_member = new_member.with_points(old_member.points)
            new_instance = new_instance.replace_member(member_index, new_member)

        self.replace_instance(image_index, instance_id, new_instance)

    def get_selection(self, image_index: int) -> Optional[Selection]:
        return self._selection_repository.get_selection(image_index)

    def set_selection(self, image_index: int, selection: Optional[Selection]) -> None:
        self._selection_repository.set_selection(image_index, selection)

    def get_new_instance_type(self, image_index: int) -> IInstanceType | None:
        return self._selection_repository.get_new_instance_type(image_index)

    def set_new_instance_type(self, image_index: int, instance_type: IInstanceType | None) -> None:
        self._selection_repository.set_new_instance_type(image_index, instance_type)

    def get_member(self, image_index: int, selection: Selection) -> ILabellerObject:
        instance_id, member_index = selection
        instance = self.get_instance(image_index, instance_id)
        assert instance is not None
        return instance.members[member_index]

    def set_keypoint(self, image_index: int, selection: Selection, point: Point | None,
                     visibility: float = 2.0) -> None:
        instance_id, member_index = selection
        instance = self.get_instance(image_index, instance_id)
        if instance is None:
            return
        member = cast(IKeypoint, instance.members[member_index])
        member = member.with_p(point)
        member = member.with_visibility(visibility)
        instance = instance.replace_member(member_index, member)
        self.replace_instance(image_index, instance_id, instance)

    def set_bounding_box(self, image_index: int, selection: Selection, box: Box | None) -> None:
        instance_id, member_index = selection
        instance = self.get_instance(image_index, instance_id)
        if instance is None:
            return
        member = cast(IBoundingBox, instance.members[member_index])
        member = member.with_box(box)
        instance = instance.replace_member(member_index, member)
        self.replace_instance(image_index, instance_id, instance)

    def set_polygon(self, image_index: int, selection: Selection, points: Sequence[Point]) -> None:
        instance_id, member_index = selection
        instance = self.get_instance(image_index, instance_id)
        if instance is None:
            return
        member = cast(IPolygon, instance.members[member_index])
        member = member.with_points(points)
        instance = instance.replace_member(member_index, member)
        self.replace_instance(image_index, instance_id, instance)

    def set_polyline(self, image_index: int, selection: Selection, points: Sequence[Point]) -> None:
        instance_id, member_index = selection
        instance = self.get_instance(image_index, instance_id)
        if instance is None:
            return
        member = cast(IPolyline, instance.members[member_index])
        member = member.with_points(points)
        instance = instance.replace_member(member_index, member)
        self.replace_instance(image_index, instance_id, instance)

    def set_polygon_point(self, image_index: int, selection: Selection, point_index: int, point: Point) -> None:
        instance_id, member_index = selection
        instance = self.get_instance(image_index, instance_id)
        if instance is None:
            return
        member = cast(IPolygon, instance.members[member_index])
        member = member.replace_point(point_index, point)
        instance = instance.replace_member(member_index, member)
        self.replace_instance(image_index, instance_id, instance)

    def set_polyline_point(self, image_index: int, selection: Selection, point_index: int, point: Point) -> None:
        instance_id, member_index = selection
        instance = self.get_instance(image_index, instance_id)
        if instance is None:
            return
        member = cast(IPolyline, instance.members[member_index])
        member = member.replace_point(point_index, point)
        instance = instance.replace_member(member_index, member)
        self.replace_instance(image_index, instance_id, instance)
