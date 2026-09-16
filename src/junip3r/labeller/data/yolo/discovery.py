from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from junip3r.common.discovery import DEFAULT_IMAGE_EXTENSIONS, discover_images

# Keys in a data.yaml that describe the dataset as a whole rather than naming an image
# set - every other string-valued top-level key is treated as a set (train/val/test/...).
_NON_SET_KEYS = {"path", "names", "nc", "kpt_shape", "flip_idx", "flip_v_idx", "download"}


@dataclass
class YoloDatasetImage:
    image: Path
    label: Optional[Path]
    set_name: str


class DuplicateImageNameError(ValueError):
    """Raised when the same image stem appears in more than one set - sets are merged
    into a single flat list for browsing, so a duplicate would be ambiguous."""


def yolo_dataset_root(data_yaml_file: Path, raw: Dict[str, Any]) -> Path:
    path = raw.get("path")
    if path is None:
        return data_yaml_file.parent
    return (data_yaml_file.parent / path).resolve()


def _label_dir_for(dataset_root: Path, set_relative_path: str) -> Path:
    # Mirrors the layout YoloDatasetWriter always produces (images/<set> next to
    # labels/<set>) - see labeller/export/yolo/serialization/yolo_dataset_writer.py.
    if "images" in Path(set_relative_path).parts:
        label_relative = set_relative_path.replace("images", "labels", 1)
    else:
        label_relative = str(Path("labels") / set_relative_path)
    return dataset_root / label_relative


def discover_yolo_dataset_images(
        data_yaml_file: Path,
        raw: Dict[str, Any],
        image_extensions=DEFAULT_IMAGE_EXTENSIONS,
) -> List[YoloDatasetImage]:
    dataset_root = yolo_dataset_root(data_yaml_file, raw)

    set_items = [(key, value) for key, value in raw.items()
                 if key not in _NON_SET_KEYS and isinstance(value, str)]

    images: List[YoloDatasetImage] = []
    seen: Dict[str, str] = {}

    for set_name, set_relative_path in set_items:
        image_dir = dataset_root / set_relative_path
        label_dir = _label_dir_for(dataset_root, set_relative_path)

        for image_file in sorted(discover_images(image_dir, image_extensions)):
            stem = image_file.stem
            if stem in seen:
                raise DuplicateImageNameError(
                    f"Image '{stem}' appears in both '{seen[stem]}' and '{set_name}'")
            seen[stem] = set_name

            label_file = label_dir / f"{stem}.txt"
            images.append(YoloDatasetImage(
                image=image_file,
                label=label_file if label_file.exists() else None,
                set_name=set_name,
            ))

    return images
