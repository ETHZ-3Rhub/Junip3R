from pathlib import Path
from typing import List

import cv2
import numpy as np

from junip3r.labeller.data.repository.abc import IImageRepository


class ImageRepository(IImageRepository):
    def __init__(self, image_files: List[Path]):
        self._image_files = image_files

    def get_num_images(self) -> int:
        return len(self._image_files)

    def get_image(self, image_index: int) -> np.ndarray:
        image_file = self._image_files[image_index]
        return cv2.imread(str(image_file))

    def get_image_name(self, image_index: int) -> str:
        return self._image_files[image_index].stem
