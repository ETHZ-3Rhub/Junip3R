from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from junip3r.labeller.data.repository.abc import IImageRepository
from junip3r.setup.preview.placeholder_image import load_image_rgb, load_placeholder_image


class SetupImageRepository(IImageRepository):
    """Disk-backed, single-image facade for the setup preview, mirroring
    SetupPreviewLabelRepository: cache-free (get_image reads straight from disk on every
    call) and settable-path rather than fixed at construction like the real labeller's
    ImageRepository, since no project folder is known until
    SetupMainWindow.set_project_folder runs.

    Falls back to the bundled placeholder image whenever no preview image has been
    chosen yet (or the file can't be read), so the preview editor always has something
    to show.
    """

    def __init__(self):
        self._image_file: Optional[Path] = None

    def set_image_file(self, image_file: Optional[Path]):
        self._image_file = image_file

    def set_image(self, image: np.ndarray):
        if self._image_file is None:
            return
        self._image_file.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(self._image_file), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))

    def get_num_images(self) -> int:
        return 1

    def get_image(self, image_index: int) -> np.ndarray:
        image = load_image_rgb(self._image_file) if self._image_file is not None else None
        if image is None:
            image = load_placeholder_image()
        assert image is not None, "Failed to load the setup preview placeholder image"
        return image

    def get_image_name(self, image_index: int) -> str:
        return "preview"

    def get_image_file(self, image_index: int) -> Optional[Path]:
        return self._image_file
