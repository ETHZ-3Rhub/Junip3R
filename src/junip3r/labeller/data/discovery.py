from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

from junip3r.common.discovery import (
    DEFAULT_CONTEXT_EXTENSIONS,
    DEFAULT_IMAGE_EXTENSIONS,
    discover_images,
    find_context_file,
    label_file_for,
)


@dataclass
class LabellerImage:
    image: Path
    label: Path
    context: Optional[Path] = None


def discover_labeller_images(
        project_folder: Path,
        image_extensions: Sequence[str] = DEFAULT_IMAGE_EXTENSIONS,
        context_extensions: Sequence[str] = DEFAULT_CONTEXT_EXTENSIONS,
) -> List[LabellerImage]:
    image_folder = project_folder / "images"
    context_folder = project_folder / "context"
    label_folder = project_folder / "labels"

    return [
        LabellerImage(
            image=image_file,
            label=label_file_for(image_file, label_folder),
            context=find_context_file(image_file, context_folder, context_extensions),
        )
        for image_file in discover_images(image_folder, image_extensions)
    ]
