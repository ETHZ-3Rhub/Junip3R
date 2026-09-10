from typing import List, Sequence

from junip3r.labeller.config.data import InstanceType
from junip3r.labeller.data.types.abc import InstanceMember
from junip3r.labeller.data.types.data import Keypoint, BoundingBox, Polygon, Polyline, Instance, new_instance
from junip3r.labeller.model.image_state import ImageStateChangeFlags
from junip3r.labeller.model.pose_image_model import PoseImageModel


class SetupPreviewPoseImageModel(PoseImageModel):
    """Reconciles the preview's already-placed instances against a changed config,
    since unlike a real project's, setup's config changes live, mid-session. Everything
    it touches goes through self._model (the same AppModel the base class already
    holds) - no separately-injected repository reference.
    """

    def set_config(self, instance_types: Sequence[InstanceType], expected_instances: Sequence[InstanceType]):
        image_index = self._image_index

        old_instances = self._model.get_instances(image_index)
        self._model.set_instance_types(image_index, instance_types)
        self._model.set_expected_instances(image_index, expected_instances)
        new_instances = reconcile_instances(old_instances, instance_types)
        self._model.set_instances(image_index, new_instances)

        old_new_type = self._model.get_new_instance_type(image_index)
        if old_new_type is not None:
            new_type = next((it for it in instance_types if it.name == old_new_type.name), None)
            self._model.set_new_instance_type(image_index, new_type)

        self._instance_type_selection_workflows.pop(image_index, None)
        self.invalidate_undo_stack()

        self.set_flags(image_index, ImageStateChangeFlags.ALL)
        self._flush()


def reconcile_instances(old_instances: Sequence[Instance], instance_types: Sequence[InstanceType]) -> List[Instance]:
    """Rebuild every already-placed instance against a changed set of resolved instance
    types, carrying placed positions over by matching stable member ids (see
    _copy_instance_data). Frozen Instance/Keypoint/etc. objects bake in their color and
    shape at construction time and never update themselves - the real labeller never
    needs to redo this, since its config never changes mid-session, but setup's does,
    continuously, so without this an already-placed preview instance would never pick up
    a recolor or a member-list edit and would just go stale.

    Called from set_config above, which loads old_instances itself (via
    AppModel.get_instances, before swapping in the new instance_types) and writes the
    result back (via AppModel.set_instances) - this stays pure computation with no
    repository access of its own. Needed no changes for the mutable/DTO layer LabelModel
    added: it operates on immutable Instance objects, which is exactly what AppModel's
    get_instances/set_instances already traffic in.

    This only reshapes what's already placed - it never seeds new instances. Seeding
    preview instances from `expected_instance_types` was a bug this replaced: expected
    instances are just a labelling-workflow hint, not a cap on how many instances the
    preview (or a real image) can hold.
    """
    new_instances = []
    for instance in old_instances:
        instance_type = next((it for it in instance_types if it.id == instance.instance_type.id), None)
        if instance_type is None:
            continue  # the instance's type was deleted from the config
        target_instance = new_instance(instance_type, instance.instance_id, instance.name)
        new_instances.append(_copy_instance_data(instance, target_instance))
    return new_instances


def _copy_instance_data(source_instance: Instance, target_instance: Instance) -> Instance:
    source_members = source_instance.members
    target_members = list(target_instance.members)

    for member in source_members:
        target_member_index = next((i for i, m in enumerate(target_members) if m.id == member.id), None)
        if target_member_index is None:
            continue
        target_member = target_members[target_member_index]
        new_member = _copy_member_data(member, target_member)
        target_members[target_member_index] = new_member

    return target_instance.with_members(target_members)


def _copy_member_data(source_member: InstanceMember, target_member: InstanceMember) -> InstanceMember:
    if isinstance(source_member, Keypoint) and isinstance(target_member, Keypoint):
        new_member = target_member.with_p(source_member.p)
    elif isinstance(source_member, BoundingBox) and isinstance(target_member, BoundingBox):
        new_member = target_member.with_box(source_member.box)
    elif isinstance(source_member, Polygon) and isinstance(target_member, Polygon):
        new_member = target_member.with_points([p.p for p in source_member.points])
    elif isinstance(source_member, Polyline) and isinstance(target_member, Polyline):
        new_member = target_member.with_points([p.p for p in source_member.points])
    else:
        raise ValueError(f"Unknown member type: {source_member.type}")
    return new_member
