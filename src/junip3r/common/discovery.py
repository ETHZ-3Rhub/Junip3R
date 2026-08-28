from pathlib import Path
from typing import List, Optional, Sequence

DEFAULT_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")
DEFAULT_CONTEXT_EXTENSIONS = (".avi", ".mp4", ".mkv")


def discover_images(image_folder: Path, extensions: Sequence[str] = DEFAULT_IMAGE_EXTENSIONS) -> List[Path]:
    return [f for f in image_folder.glob("*") if f.suffix.lower() in extensions]


def find_context_file(
        image_file: Path,
        context_folder: Path,
        extensions: Sequence[str] = DEFAULT_CONTEXT_EXTENSIONS,
) -> Optional[Path]:
    for extension in extensions:
        context_file = context_folder / (image_file.stem + extension)
        if context_file.exists():
            return context_file
    return None


def label_file_for(image_file: Path, label_folder: Path) -> Path:
    return label_folder / (image_file.stem + ".json")
