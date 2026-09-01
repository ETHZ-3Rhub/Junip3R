from pathlib import Path

from junip3r.common.tags.data import Tags
from junip3r.common.tags.serialization import TagSerializer
from junip3r.frame_extractor.data.repository.abc import ITagRepository


class TagRepository(ITagRepository):
    def __init__(self, tag_folder: Path):
        self._tag_folder = tag_folder

    def get_tags(self, image_name: str) -> Tags:
        return TagSerializer.load(self._get_tag_file(image_name))

    def set_tags(self, image_name: str, tags: Tags):
        TagSerializer.write(self._get_tag_file(image_name), tags)

    def _get_tag_file(self, image_name: str) -> Path:
        return self._tag_folder / f"{image_name}.json"
