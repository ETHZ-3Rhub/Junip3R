from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from junip3r.common.discovery import DEFAULT_IMAGE_EXTENSIONS
from junip3r.labeller.yolo.config.yolo_dataset_config import YoloDatasetConfig


@dataclass
class YoloDatasetImage:
    image: Path
    label: Optional[Path]


def yolo_dataset_root(data_yaml_file: Path, raw: Dict[str, Any]) -> Path:
    path = raw.get("path")
    if path is None:
        return data_yaml_file.parent
    return (data_yaml_file.parent / path).resolve()


def discover_yolo_dataset_images(config: YoloDatasetConfig) -> List[YoloDatasetImage]:
    """Resolves train/val/test the same way Ultralytics does: each entry is either an
    image directory (scanned recursively) or a .txt file listing image paths, one per
    line. All three sets are then concatenated - in train/val/test order - into a
    single flat, browsable list, and each image's label file is found by swapping the
    last "images" path segment for "labels" (Ultralytics' img2label_paths).
    """
    image_files: List[Path] = []
    for entries in (config.train, config.val, config.test):
        if entries is None:
            continue
        for entry in entries:
            image_files.extend(_images_for_entry(entry))

    return [YoloDatasetImage(image=image_file, label=_label_path_for(image_file)) for image_file in image_files]


def _images_for_entry(entry: Path) -> List[Path]:
    if entry.is_dir():
        return sorted(
            f for f in entry.rglob("*")
            if f.is_file() and f.suffix.lower() in DEFAULT_IMAGE_EXTENSIONS
        )
    if entry.is_file():
        return _images_from_list_file(entry)
    raise FileNotFoundError(f"{entry} does not exist")


def _images_from_list_file(list_file: Path) -> List[Path]:
    parent = list_file.parent
    image_files = []

    for line in list_file.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        path = Path(line)
        image_files.append(path if path.is_absolute() else (parent / path).resolve())

    return image_files


def _label_path_for(image_file: Path) -> Optional[Path]:
    # Mirrors Ultralytics' img2label_paths(): swap the last "images" path segment for
    # "labels", then use a .txt extension regardless of the image's own extension.
    parts = list(image_file.parts)
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] == "images":
            label_parts = parts.copy()
            label_parts[index] = "labels"
            label_file = Path(*label_parts).with_suffix(".txt")
            return label_file if label_file.exists() else None
    return None
