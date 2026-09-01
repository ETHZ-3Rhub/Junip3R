import json
from pathlib import Path

from junip3r.common.tags.data import Tags


class TagSerializer:
    MAX_TAG_FILE_SIZE = 1 * 1024 * 1024  # 1 MiB

    @classmethod
    def load(cls, tag_file: Path) -> Tags:
        if not tag_file.exists():
            return {}

        size = tag_file.stat().st_size
        if size > cls.MAX_TAG_FILE_SIZE:
            raise ValueError(f"Tag file is too large. Maximum file size is {cls.MAX_TAG_FILE_SIZE / 1024 / 1024:.1f} MiB")

        with tag_file.open("r") as f:
            text = f.read()

        if not text.strip():
            return {}

        data = json.loads(text)
        return dict(data.get("tags", {}))

    @classmethod
    def write(cls, tag_file: Path, tags: Tags) -> None:
        tag_file.parent.mkdir(parents=True, exist_ok=True)
        with tag_file.open("w") as f:
            json.dump({"tags": dict(tags)}, f, indent=4)
