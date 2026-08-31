from typing import Sequence, Optional, cast, Any

from PySide6.QtGui import QUndoCommand

from junip3r.labeller.data.types.abc import IInstance, InstanceID, Selection, IInstanceType, Point, \
    Box, IKeypoint, IBoundingBox, IPolygon
from junip3r.labeller.model.abc import IChangeTracker, IUndoModel
from junip3r.labeller.model.image_state import ImageStateChangeFlags
from junip3r.labeller.model.instance_type_selection_strategy import EditorInstanceTypeWorkflow


class AddInstance(QUndoCommand):
    def __init__(
            self,
            model: IUndoModel,
            change_tracker: IChangeTracker,
            image_index: int,
            instance: IInstance,
            name: str = "Add Instance",
    ) -> None:
        super().__init__(name)

        self._model = model
        self._change_tracker = change_tracker
        self._image_index = image_index
        self._instance = instance

        self._insertion_index: int | None = None

    def redo(self) -> None:
        self._model.insert_instance(self._image_index, self._instance, self._insertion_index)
        self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.INSTANCES)

    def undo(self) -> None:
        self._model.remove_instance(self._image_index, self._instance.instance_id)
        self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.INSTANCES)


class RemoveInstance(QUndoCommand):
    def __init__(
            self,
            model: IUndoModel,
            change_tracker: IChangeTracker,
            image_index: int,
            instance_id: str,
            name: str = "Remove Instance",
    ) -> None:
        super().__init__(name)

        self._model = model
        self._change_tracker = change_tracker
        self._image_index = image_index
        self._instance_id = instance_id

        self._removed_index: Optional[int] = None
        self._removed_instance: Optional[IInstance] = None

    def redo(self) -> None:
        instances = self._model.get_instances(self._image_index)

        self._removed_index, self._removed_instance = next(
            ((i, inst) for i, inst in enumerate(instances) if inst.instance_id == self._instance_id),
            (None, None)
        )

        self._model.remove_instance(self._image_index, self._instance_id)
        self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.INSTANCES)

    def undo(self) -> None:
        if self._removed_instance is not None:
            self._model.insert_instance(self._image_index, self._removed_instance, self._removed_index)
            self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.INSTANCES)


class ChangeInstanceType(QUndoCommand):
    def __init__(
            self,
            model: IUndoModel,
            change_tracker: IChangeTracker,
            image_index: int,
            instance_id: InstanceID,
            instance_type: IInstanceType,
            name: str = "Change Instance Type",
    ) -> None:
        super().__init__(name)

        self._model = model
        self._change_tracker = change_tracker
        self._image_index = image_index
        self._instance_id = instance_id
        self._instance_type = instance_type

        self._prev_instance: Optional[IInstance] = None

    def redo(self) -> None:
        self._prev_instance = self._model.get_instance(self._image_index, self._instance_id)
        if self._prev_instance is None:
            return

        self._model.change_instance_type(self._image_index, self._instance_id, self._instance_type)
        self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.INSTANCES)

    def undo(self) -> None:
        if self._prev_instance is None:
            return
        self._model.replace_instance(self._image_index, self._instance_id, self._prev_instance)
        self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.INSTANCES)


class RenameInstance(QUndoCommand):
    def __init__(
            self,
            model: IUndoModel,
            change_tracker: IChangeTracker,
            image_index: int,
            instance_id: InstanceID,
            new_name: str,
            name: str = "Rename Instance",
    ) -> None:
        super().__init__(name)

        self._model = model
        self._change_tracker = change_tracker
        self._image_index = image_index
        self._instance_id = instance_id
        self._new_name = new_name

        self._prev_name: str | None = None

    def redo(self) -> None:
        instance = self._model.get_instance(self._image_index, self._instance_id)
        if instance is None:
            return

        self._prev_name = instance.name
        new_instance = instance.with_name(self._new_name)
        self._model.replace_instance(self._image_index, self._instance_id, new_instance)
        self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.INSTANCES)

    def undo(self) -> None:
        if self._prev_name is None:
            return

        instance = self._model.get_instance(self._image_index, self._instance_id)
        if instance is None:
            return

        prev_instance = instance.with_name(self._prev_name)
        self._model.replace_instance(self._image_index, self._instance_id, prev_instance)
        self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.INSTANCES)


class SetSelection(QUndoCommand):
    def __init__(
            self,
            model: IUndoModel,
            change_tracker: IChangeTracker,
            image_index: int,
            selection: Optional[Selection],
            name: str = "Set Selection",
    ) -> None:
        super().__init__(name)

        self._model = model
        self._change_tracker = change_tracker
        self._image_index = image_index
        self._selection = selection

        self._previous_selection: Optional[Selection] = None

    def redo(self) -> None:
        self._previous_selection = self._model.get_selection(self._image_index)

        self._model.set_selection(self._image_index, self._selection)
        self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.SELECTION)

    def undo(self) -> None:
        self._model.set_selection(self._image_index, self._previous_selection)
        self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.SELECTION)


class AdvanceNewInstanceType(QUndoCommand):
    def __init__(
            self,
            model: IUndoModel,
            change_tracker: IChangeTracker,
            workflow: EditorInstanceTypeWorkflow,
            image_index: int,
            name: str = "Advance New Instance Type",
    ) -> None:
        super().__init__(name)

        self._model = model
        self._workflow = workflow
        self._change_tracker = change_tracker
        self._image_index = image_index

        self._prev_workflow_state: Any = None
        self._previous_instance_type: IInstanceType | None = None

    def redo(self) -> None:
        self._prev_workflow_state = self._workflow.capture_state()
        self._previous_instance_type = self._model.get_new_instance_type(self._image_index)
        assert self._previous_instance_type is not None

        instances = self._model.get_instances(self._image_index)
        existing_instance_types = [instance.instance_type for instance in instances]
        next_new_instance_type = self._workflow.automatic_selection(existing_instance_types, self._previous_instance_type)

        self._model.set_new_instance_type(self._image_index, next_new_instance_type)
        self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.INSTANCES)

    def undo(self) -> None:
        self._model.set_new_instance_type(self._image_index, self._previous_instance_type)
        self._workflow.restore_state(self._prev_workflow_state)
        self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.INSTANCES)


class SetKeypoint(QUndoCommand):
    def __init__(
            self,
            model: IUndoModel,
            change_tracker: IChangeTracker,
            image_index: int,
            instance_id: str,
            member_index: int,
            point: Point | None,
            visibility: float = 0.0,
            name: str = "Set Keypoint",
    ) -> None:
        super().__init__(name)

        self._model = model
        self._change_tracker = change_tracker
        self._image_index = image_index
        self._instance_id = instance_id
        self._member_index = member_index
        self._point = point
        self._visibility = visibility

        self._previous_point: Point | None = None
        self._previous_visibility: float = 0.0

    def redo(self) -> None:
        keypoint = cast(IKeypoint, self._model.get_member(self._image_index, (self._instance_id, self._member_index)))
        self._previous_point = keypoint.p
        self._previous_visibility = keypoint.visibility

        self._model.set_keypoint(self._image_index, (self._instance_id, self._member_index), self._point, self._visibility)
        self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.INSTANCES)


    def undo(self) -> None:
        self._model.set_keypoint(self._image_index, (self._instance_id, self._member_index), self._previous_point, self._previous_visibility)
        self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.INSTANCES)


class SetBoundingBox(QUndoCommand):
    def __init__(
            self,
            model: IUndoModel,
            change_tracker: IChangeTracker,
            image_index: int,
            instance_id: str,
            member_index: int,
            box: Box | None,
            name: str = "Set Bounding Box",
    ) -> None:
        super().__init__(name)

        self._model = model
        self._change_tracker = change_tracker
        self._image_index = image_index
        self._instance_id = instance_id
        self._member_index = member_index
        self._box = box

        self._previous_box: Box | None = None

    def redo(self) -> None:
        bounding_box = cast(IBoundingBox, self._model.get_member(self._image_index, (self._instance_id, self._member_index)))
        self._previous_box = bounding_box.box

        self._model.set_bounding_box(self._image_index, (self._instance_id, self._member_index), self._box)
        self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.INSTANCES)

    def undo(self) -> None:
        self._model.set_bounding_box(self._image_index, (self._instance_id, self._member_index), self._previous_box)
        self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.INSTANCES)


class SetPolygon(QUndoCommand):
    def __init__(
            self,
            model: IUndoModel,
            change_tracker: IChangeTracker,
            image_index: int,
            instance_id: str,
            member_index: int,
            points: Sequence[Point],
            name: str = "Set Polygon",
    ) -> None:
        super().__init__(name)

        self._model = model
        self._change_tracker = change_tracker
        self._image_index = image_index
        self._instance_id = instance_id
        self._member_index = member_index
        self._points = points

        self._previous_points: Sequence[Point] = []

    def redo(self) -> None:
        polygon = cast(IPolygon, self._model.get_member(self._image_index, (self._instance_id, self._member_index)))
        self._previous_points = [p.p for p in polygon.points]

        self._model.set_polygon(self._image_index, (self._instance_id, self._member_index), self._points)
        self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.INSTANCES)

    def undo(self) -> None:
        self._model.set_polygon(self._image_index, (self._instance_id, self._member_index), self._previous_points)
        self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.INSTANCES)


class SetPolygonPoint(QUndoCommand):
    def __init__(
            self,
            model: IUndoModel,
            change_tracker: IChangeTracker,
            image_index: int,
            instance_id: str,
            member_index: int,
            polygon_point_index: int,
            point: Point,
            name: str = "Set Polygon Point",
    ) -> None:
        super().__init__(name)

        self._model = model
        self._change_tracker = change_tracker
        self._image_index = image_index
        self._instance_id = instance_id
        self._member_index = member_index
        self._polygon_point_index = polygon_point_index
        self._point = point

        self._previous_point: Point | None = None

    def redo(self) -> None:
        member = cast(IPolygon, self._model.get_member(self._image_index, (self._instance_id, self._member_index)))
        polygon_point = member.points[self._polygon_point_index]
        self._previous_point = polygon_point.p

        self._model.set_polygon_point(self._image_index, (self._instance_id, self._member_index), self._polygon_point_index, self._point)
        self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.INSTANCES)


    def undo(self) -> None:
        if self._previous_point is None:
            return
        self._model.set_polygon_point(self._image_index, (self._instance_id, self._member_index), self._polygon_point_index, self._previous_point)
        self._change_tracker.set_flags(self._image_index, ImageStateChangeFlags.INSTANCES)
