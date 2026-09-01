from pathlib import Path
from typing import Sequence

from junip3r.common.tags.data import Tags
from junip3r.common.tags.serialization import TagSerializer
from junip3r.labeller.data.repository.abc import ITagRepository


class TagRepository(ITagRepository):
    def __init__(self, tag_folder: Path, image_names: Sequence[str]):
        self._tag_folder = tag_folder
        self._image_names = image_names

    def get_tags(self, image_index: int) -> Tags:
        return TagSerializer.load(self._get_tag_file(image_index))

    def set_tags(self, image_index: int, tags: Tags):
        TagSerializer.write(self._get_tag_file(image_index), tags)

    def _get_tag_file(self, image_index: int) -> Path:
        return self._tag_folder / f"{self._image_names[image_index]}.json"
