from typing import Protocol

from junip3r.labeller.data.types.abc import ILabellerObject, IKeypoint, IBoundingBox, IPolygon, IPolyline


class ISetupPreviewLabellerObject(ILabellerObject, Protocol):
    @property
    def id(self) -> str: ...


class ISetupPreviewKeypoint(IKeypoint, Protocol):
    @property
    def id(self) -> str: ...


class ISetupPreviewBoundingBox(IBoundingBox, Protocol):
    @property
    def id(self) -> str: ...


class ISetupPreviewPolygon(IPolygon, Protocol):
    @property
    def id(self) -> str: ...


class ISetupPreviewPolyline(IPolyline, Protocol):
    @property
    def id(self) -> str: ...
