import colorsys
import logging
from pathlib import Path
from typing import List, cast, Sequence, Tuple, Union, Optional

from junip3r.common.labels.serialization import LabelSerializer
from junip3r.labeller.config.data import InstanceType, MemberSpecs, SkeletonSpecs
from junip3r.labeller.data.repository.abc import ILabelRepository, IConfigRepository
from junip3r.labeller.data.repository.label import InstanceMapper
from junip3r.labeller.data.types.abc import LabellerObjectType, Color
from junip3r.labeller.data.types.data import Keypoint, BoundingBox, Polygon, Polyline, Instance
from junip3r.setup.data.types.abc import ISetupInstanceType, ISetupMember, ISetupSkeleton

logger = logging.getLogger(__name__)

# The labeller's own member classes, which the setup preview uses directly (see
# MemberSpecs/InstanceType's `id` field) instead of maintaining parallel ID-only
# subclasses - only these four concrete types are ever actually constructed here.
PreviewMember = Union[Keypoint, BoundingBox, Polygon, Polyline]


class SetupConfigRepository(IConfigRepository):
    def __init__(self):
        self._instance_types: List[InstanceType] = []
        self._expected_instances: List[InstanceType] = []

    def set_state(self, instance_types: Sequence[InstanceType], expected_instances: Sequence[InstanceType] = ()):
        self._instance_types = list(instance_types)
        self._expected_instances = list(expected_instances)

    def get_instance_types(self, image_index: int) -> List[InstanceType]:
        return self._instance_types

    def get_expected_instances(self, image_index: int) -> List[InstanceType]:
        return self._expected_instances

    def get_tag_names(self, image_index: int) -> List[str]:
        return []


class SetupPreviewLabelRepository(ILabelRepository):
    """Writes through to a project's own _labeller/preview/labels.json on every change,
    like JuniperLabelRepository (labeller/data/repository/label.py) does for a real
    project's label files - except a separate implementation, not a subclass, because
    the two don't actually share as much as they look like they should.
    JuniperLabelRepository builds one InstanceMapper at construction time and never
    changes it, which only works because a real project's config never changes
    mid-session. Setup's does, continuously, so its instance types are updatable via
    set_state instead of fixed at construction - see reconcile_instances below for how
    already-placed instances get carried over to a changed config.

    No project folder is known until SetupMainWindow.set_project_folder runs (unlike a
    real project's label files, known upfront), so the label file is a settable path
    rather than a constructor argument - see set_label_file.

    AppModel only ever calls set_instances with the real committed instance list, never
    with PoseImageModel's synthesized "Add new instance" placeholder (instance_id=None) -
    so this repository, and what it persists, never needs to filter that out.
    """

    def __init__(self):
        self._label_file: Optional[Path] = None
        self._instance_types: Sequence[InstanceType] = []
        self._loader = LabelSerializer()

    def set_label_file(self, label_file: Optional[Path]):
        self._label_file = label_file

    def get_instances(self, image_index: int) -> Sequence[Instance]:
        return self._load()

    def set_instances(self, image_index: int, instances: Sequence[Instance]):
        if self._label_file is None:
            return
        data = InstanceMapper(self._instance_types).to_data(instances)
        self._loader.write_instances(self._label_file, data)

    def set_state(self, instance_types: Sequence[InstanceType]):
        """Update the instance types this repository resolves stored data against,
        carrying already-placed instances over to the new config by matching stable
        member/instance ids (see reconcile_instances) and writing the result straight
        back out - called whenever setup's config changes, since unlike a real project's,
        this one changes live, mid-session.
        """
        old_instances = self._load()
        self._instance_types = list(instance_types)
        new_instances = reconcile_instances(old_instances, self._instance_types)
        self.set_instances(0, new_instances)

    def _load(self) -> List[Instance]:
        if self._label_file is None:
            return []
        data = self._loader.load_instances(self._label_file)
        try:
            return InstanceMapper(self._instance_types).from_data(data)
        except (KeyError, ValueError) as e:
            # config.yaml is meant to be hand-editable, so a persisted preview that no
            # longer matches it (renamed/removed instance type, member count changed) is
            # a real possibility, not just a bug - degrade to empty rather than crash.
            logger.warning(f"Could not restore the persisted preview for this project: {e}")
            return []


def _color_from_hue(hue: float) -> Color:
    color = colorsys.hsv_to_rgb(hue, 1, 1)
    return int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)


def resolve_instance_types(instance_types: Sequence[ISetupInstanceType], mode: str) -> List[InstanceType]:
    num_instance_types = len(instance_types)
    return [_resolve_instance_type(instance_type, index, num_instance_types, mode) for index, instance_type in enumerate(instance_types)]


def _resolve_instance_type(instance_type: ISetupInstanceType, index: int, num_instance_types: int, mode: str) -> InstanceType:
    color = _resolve_instance_type_color(instance_type.color, index, num_instance_types)

    # The bounding box is resolved separately from, and kept entirely out of the
    # index/count _resolve_members uses for its per-position hue fallback - otherwise
    # toggling manual/automatic bounding box mode would shift every keypoint's
    # auto-assigned color for no reason. Matches how
    # labeller/config/parser.py::_build_members_yolo_pose keeps num_keypoints/
    # keypoint_index counting only KEYPOINT members, never the bounding box.
    members = _resolve_members(instance_type.members)
    if instance_type.bounding_box:
        # yolo_detect's wire format has no separate name for its one-and-only
        # member - the labeller displays it under the instance type's own name
        # (see labeller/config/parser.py::_build_members_yolo_detect). Its color
        # always comes from the instance type's own resolved color, never from a
        # per-position hue fallback.
        bounding_box_name = instance_type.name if mode == "yolo_detect" else "Bounding Box"
        bounding_box = MemberSpecs(bounding_box_name, LabellerObjectType.BOUNDING_BOX, color, None, id=instance_type.id)
        members = [bounding_box, *members]

    skeleton = _resolve_skeleton(instance_type.skeleton, members)
    return InstanceType(instance_type.name, members, skeleton, color=color, id=instance_type.id)


def _resolve_instance_type_color(color: Optional[Color], index: int, num_instance_types: int) -> Color:
    if color is not None:
        return color
    if num_instance_types <= 1:
        return (0, 0, 255)
    return _color_from_hue(index / num_instance_types)


def _resolve_members(members: Sequence[ISetupMember]) -> List[MemberSpecs]:
    num_members = len(members)
    return [
        MemberSpecs(member.name, member.type, _member_color(member, index, num_members), member.size, id=member.id)
        for index, member in enumerate(members)
    ]


def _member_color(member: ISetupMember, index: int, num_members: int) -> Color:
    if member.color is not None:
        return member.color
    return _color_from_hue(index / num_members)


def _resolve_skeleton(skeleton: ISetupSkeleton, members: Sequence[ISetupMember]) -> SkeletonSpecs:
    member_indices = {member.id: index for index, member in enumerate(members)}
    lines = [(member_indices[source_id], member_indices[target_id]) for source_id, target_id in skeleton.lines]
    color = skeleton.color if skeleton.color is not None else (0, 0, 0)
    return SkeletonSpecs(lines, color)


def reconcile_instances(old_instances: Sequence[Instance], instance_types: Sequence[InstanceType]) -> List[Instance]:
    """Rebuild every already-placed instance against a changed set of resolved instance
    types, carrying placed positions over by matching stable member ids (see
    _copy_instance_data). Frozen Instance/Keypoint/etc. objects bake in their color and
    shape at construction time and never update themselves - the real labeller never
    needs to redo this, since its config never changes mid-session, but setup's does,
    continuously, so without this an already-placed preview instance would never pick up
    a recolor or a member-list edit and would just go stale.

    Called by SetupPreviewLabelRepository.set_state, which loads old_instances itself
    before swapping in the new instance_types - pure computation with no repository
    access of its own.

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
        target_instance = instance_type.new_instance(instance.instance_id, instance.name)
        new_instances.append(_copy_instance_data(instance, target_instance))
    return new_instances


def _copy_instance_data(source_instance: Instance, target_instance: Instance) -> Instance:
    source_members = cast(Tuple[PreviewMember, ...], source_instance.members)
    target_members = list(cast(Tuple[PreviewMember, ...], target_instance.members))

    for member in source_members:
        target_member_index = next((i for i, m in enumerate(target_members) if m.id == member.id), None)
        if target_member_index is None:
            continue
        target_member = target_members[target_member_index]
        new_member = _copy_member_data(member, target_member)
        target_members[target_member_index] = new_member

    return target_instance.with_members(target_members)


def _copy_member_data(source_member: PreviewMember, target_member: PreviewMember) -> PreviewMember:
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
