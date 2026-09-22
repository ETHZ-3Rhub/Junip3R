from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Sequence
from uuid import uuid4

import yaml

from junip3r.labeller.export.yolo.data import ExportMode


@dataclass
class ExportProfile:
    """A named, reusable YOLO export configuration: which instance types to include,
    where to export to, which named SetSplit (set_split.py) to use - referenced by
    id, not copied, so multiple profiles can deliberately share one split - and which
    mode (pose/detect) to export them as. Mode applies uniformly to every instance type
    in the profile - matches "one dataset, one kpt_shape" - so the same instance type
    can be exported as pure detect in one profile and full pose in another.
    """
    id: str
    name: str
    instance_type_names: Sequence[str] = field(default_factory=tuple)
    set_split_id: str = ""
    target_folder: str = ""
    include_empty_images: bool = False
    mode: ExportMode = ExportMode.POSE


class ExportProfileSerializer:
    @classmethod
    def serialize(cls, profile: ExportProfile) -> Dict[str, Any]:
        return {
            "id": profile.id,
            "name": profile.name,
            "instance_type_names": list(profile.instance_type_names),
            "set_split_id": profile.set_split_id,
            "target_folder": profile.target_folder,
            "include_empty_images": profile.include_empty_images,
            "mode": cls._serialize_mode(profile.mode),
        }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> ExportProfile:
        return ExportProfile(
            id=data.get("id") or str(uuid4()),
            name=data.get("name", "Default"),
            instance_type_names=tuple(data.get("instance_type_names", [])),
            set_split_id=data.get("set_split_id", ""),
            target_folder=data.get("target_folder", ""),
            include_empty_images=data.get("include_empty_images", False),
            mode=cls._deserialize_mode(data["mode"]),
        )

    @classmethod
    def _serialize_mode(cls, mode: ExportMode) -> str:
        match mode:
            case ExportMode.POSE:
                return "pose"
            case ExportMode.DETECT:
                return "detect"
            case _:
                raise ValueError(f"Unknown mode: {mode}")

    @classmethod
    def _deserialize_mode(cls, mode_name: str) -> ExportMode:
        match mode_name:
            case "pose":
                return ExportMode.POSE
            case "detect":
                return ExportMode.DETECT
            case _:
                raise ValueError(f"Unknown mode: {mode_name!r}")


class IExportProfileRepository(Protocol):
    def list(self) -> Sequence[ExportProfile]: ...
    def get(self, profile_id: str) -> Optional[ExportProfile]: ...
    def set(self, profile: ExportProfile) -> None: ...
    def delete(self, profile_id: str) -> None: ...


class ExportProfileRepository:
    """No cache - every call round-trips through profiles_file, same convention as
    SetSplitRepository/LabelModel elsewhere in this codebase. Brand new concept/file,
    so unlike SetSplitRepository there's no legacy on-disk shape to migrate from.
    """

    def __init__(self, profiles_file: Path):
        self._profiles_file = profiles_file

    def list(self) -> List[ExportProfile]:
        if not self._profiles_file.exists():
            return []

        with self._profiles_file.open("r") as f:
            data = yaml.safe_load(f)

        if not data:
            return []

        return [ExportProfileSerializer.deserialize(d) for d in data.get("profiles", [])]

    def get(self, profile_id: str) -> Optional[ExportProfile]:
        return next((p for p in self.list() if p.id == profile_id), None)

    def set(self, profile: ExportProfile) -> None:
        profiles = self.list()
        for i, existing in enumerate(profiles):
            if existing.id == profile.id:
                profiles[i] = profile
                break
        else:
            profiles.append(profile)
        self._write(profiles)

    def delete(self, profile_id: str) -> None:
        self._write([p for p in self.list() if p.id != profile_id])

    def _write(self, profiles: Sequence[ExportProfile]) -> None:
        self._profiles_file.parent.mkdir(parents=True, exist_ok=True)
        with self._profiles_file.open("w") as f:
            yaml.dump({"profiles": [ExportProfileSerializer.serialize(p) for p in profiles]}, f)
