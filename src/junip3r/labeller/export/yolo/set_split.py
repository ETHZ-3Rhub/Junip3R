import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Mapping, Protocol, Dict, Iterable, Any, Sequence
from uuid import uuid4

import yaml

from junip3r.common.tags.data import TagValue


class ITaggedImage(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def tags(self) -> Mapping[str, TagValue]: ...


@dataclass
class SetSplitConfig:
    grouping: Optional[str] = None
    group_sets: Dict[str, str] = field(default_factory=dict)
    individual_sets: Dict[str, str] = field(default_factory=dict)
    auto_split_ratio: float = 0.9


class SetSplitConfigSerializer:
    @classmethod
    def serialize(cls, config: SetSplitConfig) -> Dict[str, Any]:
        return {
            "grouping": config.grouping,
            "group_sets": dict(config.group_sets),
            "individual_sets": dict(config.individual_sets),
            "auto_split_ratio": config.auto_split_ratio,
        }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> SetSplitConfig:
        return SetSplitConfig(
            grouping=data.get("grouping"),
            group_sets=dict(data.get("group_sets", {})),
            individual_sets=dict(data.get("individual_sets", {})),
            auto_split_ratio=data.get("auto_split_ratio", 0.9),
        )

    @classmethod
    def load(cls, path: Path) -> SetSplitConfig:
        with path.open("r") as f:
            data = yaml.safe_load(f)

        if not data:
            return SetSplitConfig()

        return cls.deserialize(data)


@dataclass
class NamedSetSplit:
    """A SetSplitConfig with stable identity, so multiple export profiles can share one
    by reference. SetSplitConfig itself is left alone (no id field) - see
    NamedSetSplitSerializer for why.
    """
    id: str
    name: str
    config: SetSplitConfig = field(default_factory=SetSplitConfig)


class NamedSetSplitSerializer:
    @classmethod
    def serialize(cls, named_split: NamedSetSplit) -> Dict[str, Any]:
        return {
            "id": named_split.id,
            "name": named_split.name,
            **SetSplitConfigSerializer.serialize(named_split.config),
        }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> NamedSetSplit:
        return NamedSetSplit(
            id=data.get("id") or str(uuid4()),
            name=data.get("name", "Default"),
            config=SetSplitConfigSerializer.deserialize(data),
        )


class ISetSplitRepository(Protocol):
    def list(self) -> Sequence[NamedSetSplit]: ...
    def get(self, split_id: str) -> Optional[NamedSetSplit]: ...
    def set(self, named_split: NamedSetSplit) -> None: ...
    def delete(self, split_id: str) -> None: ...


class SetSplitRepository:
    """No cache - every call round-trips through set_split_file, same convention as
    LabelModel elsewhere in this codebase.
    """

    def __init__(self, set_split_file: Path):
        self._set_split_file = set_split_file

    def list(self) -> List[NamedSetSplit]:
        if not self._set_split_file.exists():
            return []

        with self._set_split_file.open("r") as f:
            data = yaml.safe_load(f)

        if not data:
            return []

        if "splits" not in data:
            # Legacy flat single-config shape (pre-named-splits) - wrap it as one named
            # split and persist the new shape immediately. This write is load-bearing,
            # not cosmetic: list() has no cache and is called on every dialog refresh,
            # so without persisting here, the fresh uuid4() below would be regenerated
            # (differently) on every call, and any profile's set_split_id chosen against
            # one call would stop matching by the very next one.
            migrated = NamedSetSplit(id=str(uuid4()), name="Default",
                                      config=SetSplitConfigSerializer.deserialize(data))
            self._write([migrated])
            return [migrated]

        return [NamedSetSplitSerializer.deserialize(d) for d in data["splits"]]

    def get(self, split_id: str) -> Optional[NamedSetSplit]:
        return next((s for s in self.list() if s.id == split_id), None)

    def set(self, named_split: NamedSetSplit) -> None:
        splits = self.list()
        for i, existing in enumerate(splits):
            if existing.id == named_split.id:
                splits[i] = named_split
                break
        else:
            splits.append(named_split)
        self._write(splits)

    def delete(self, split_id: str) -> None:
        self._write([s for s in self.list() if s.id != split_id])

    def _write(self, splits: Sequence[NamedSetSplit]) -> None:
        self._set_split_file.parent.mkdir(parents=True, exist_ok=True)
        with self._set_split_file.open("w") as f:
            yaml.dump({"splits": [NamedSetSplitSerializer.serialize(s) for s in splits]}, f)


class SetSplit:
    """Pure grouping/auto-split logic over a set of tagged images. No Qt dependency."""

    def __init__(self, images: List[ITaggedImage], config: SetSplitConfig):
        self._images = images
        self._config = config

        self._groups: Optional[List[dict]] = None

    @property
    def config(self) -> SetSplitConfig:
        return self._config

    @property
    def grouping(self) -> Optional[str]:
        return self._config.grouping

    @property
    def groups(self) -> List[dict]:
        if self._groups is not None:
            return self._groups

        grouping = self._config.grouping

        images_per_group = {}
        for image in self._images:
            if grouping is None:
                name = image.name
            elif grouping in image.tags:
                name = image.tags[grouping]
            else:
                continue

            if name not in images_per_group:
                images_per_group[name] = []
            images_per_group[name].append(image)

        groups = [{
            "name": group_name,
            "num_images": len(images_per_group[group_name]),
            "set": self._config.group_sets.get(group_name)
        } for group_name in images_per_group]

        self._groups = groups

        return groups

    @property
    def individuals(self) -> List[dict]:
        grouping = self._config.grouping

        return [{
            "name": img.name,
            "num_images": 1,
            "set": self._config.individual_sets.get(img.name)
        } for img in self._images if grouping is not None and grouping not in img.tags]

    @property
    def num_groups(self):
        return len(self.groups)

    @property
    def num_images(self):
        return len(self._images)

    @property
    def num_train(self) -> int:
        return sum(1 for group in self.groups if group["set"] == "train")

    @property
    def num_val(self) -> int:
        return sum(1 for group in self.groups if group["set"] == "val")

    @property
    def num_unassigned(self) -> int:
        return sum(group["num_images"] for group in self.groups if group["set"] is None)

    @property
    def num_train_images(self) -> int:
        return sum(group["num_images"] for group in self.groups if group["set"] == "train")

    @property
    def num_val_images(self) -> int:
        return sum(group["num_images"] for group in self.groups if group["set"] == "val")

    @property
    def num_unassigned_images(self) -> int:
        return self.num_images - self.num_train_images - self.num_val_images

    @property
    def min_ratio(self) -> float:
        if self.num_groups == 0:
            return 0.0

        return self.num_train / self.num_groups

    @property
    def max_ratio(self) -> float:
        if self.num_groups == 0:
            return 0.0

        return (self.num_groups - self.num_val) / self.num_groups

    @property
    def auto_split_ratio(self) -> float:
        return self._config.auto_split_ratio

    @property
    def target_train(self) -> int:
        if self.num_groups == 0:
            return 0
        if self.auto_split_ratio == 0:
            return 0
        if self.auto_split_ratio == 1:
            return self.num_groups
        return min(self.num_groups - 1, max(1, round(self.auto_split_ratio * self.num_groups)))

    @property
    def target_val(self) -> float:
        return self.num_groups - self.target_train

    def set_config(self, config: SetSplitConfig) -> None:
        self._config = config
        self._groups = None

    def set_grouping(self, grouping: Optional[str]) -> None:
        self._config.grouping = grouping
        self._config.group_sets.clear()
        self._groups = None

    def set_auto_split_ratio(self, auto_split_ratio: float) -> None:
        self._config.auto_split_ratio = auto_split_ratio

    def auto_split(self, rng: Optional[random.Random] = None) -> None:
        groups = self.groups
        unassigned_groups = [group for group in groups if group["set"] is None]

        if len(groups) < 2 or not unassigned_groups:
            return

        delta_train = self.target_train - self.num_train

        (rng or random).shuffle(unassigned_groups)
        new_train_groups = unassigned_groups[:delta_train]
        new_val_groups = unassigned_groups[delta_train:]

        for group in new_train_groups:
            self._config.group_sets[group["name"]] = "train"

        for group in new_val_groups:
            self._config.group_sets[group["name"]] = "val"

        self._groups = None

    def assign_group(self, group_name: str, set_name: str) -> None:
        self._config.group_sets[group_name] = set_name
        self._groups = None

    def unassign_all(self) -> None:
        self._config.group_sets.clear()
        self._groups = None


def resolve_set_assignments(images: Iterable[ITaggedImage], config: SetSplitConfig) -> Dict[str, str]:
    """Map each assigned image's name to its set name. Unassigned images are omitted."""
    grouping = config.grouping
    assignments: Dict[str, str] = {}

    for image in images:
        if grouping is None:
            set_name = config.group_sets.get(image.name)
        elif grouping in image.tags:
            set_name = config.group_sets.get(image.tags[grouping])
        else:
            set_name = config.individual_sets.get(image.name)

        if set_name is not None:
            assignments[image.name] = set_name

    return assignments
