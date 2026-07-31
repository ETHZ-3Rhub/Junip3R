from typing import Protocol, Optional, Sequence, Tuple

from junip3r.common.config.abc import ConfigMode
from junip3r.labeller.data.types.abc import LabellerObjectType, Color


class ISetupMember(Protocol):
    @property
    def id(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def type(self) -> LabellerObjectType: ...
    @property
    def size(self) -> Optional[int]: ...
    @property
    def color(self) -> Optional[Color]: ...


class ISetupSkeleton(Protocol):
    @property
    def lines(self) -> Sequence[Tuple[str, str]]: ...  # List of (member_id, member_id) pairs
    @property
    def color(self) -> Optional[Color]: ...


class ISetupInstanceType(Protocol):
    @property
    def id(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def members(self) -> Sequence[ISetupMember]: ...
    @property
    def skeleton(self) -> ISetupSkeleton: ...


class ISetupConfig(Protocol):
    @property
    def mode(self) -> ConfigMode: ...
    @property
    def instance_types(self) -> Sequence[ISetupInstanceType]: ...
    @property
    def expected_instance_types(self) -> Sequence[Tuple[str, ISetupInstanceType]]: ...
