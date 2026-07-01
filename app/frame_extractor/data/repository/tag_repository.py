import json
from pathlib import Path
from typing import Tuple, Dict, List

from app.frame_extractor.data.repository.abc import ITagRepository


class TagRepository(ITagRepository):
    def __init__(self, tag_folder: Path):
        self._tag_folder = tag_folder

    def get_tags(self, image_name: str) -> Tuple[Dict[str, str], List[str]]:
        tag_file = self._get_tag_file(image_name)
        if not tag_file.exists():
            return {}, []

        with tag_file.open("r") as f:
            tag_data = json.load(f)

        return tag_data["kw_tags"], tag_data["tags"]

    def set_tags(self, image_name: str, kw_tags: Dict[str, str], tags: List[str]):
        self._tag_folder.mkdir(parents=True, exist_ok=True)

        tag_file = self._get_tag_file(image_name)
        tag_data = {
            "kw_tags": kw_tags,
            "tags": tags
        }

        with tag_file.open("w") as f:
            json.dump(tag_data, f, indent=4)

    def _get_tag_file(self, image_name: str) -> Path:
        return self._tag_folder / f"{image_name}.json"
