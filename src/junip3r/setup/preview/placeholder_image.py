from importlib.resources import files
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


def load_image_rgb(path: Path) -> Optional[np.ndarray]:
    image = cv2.imread(str(path))
    if image is None:
        return None
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def load_placeholder_image() -> Optional[np.ndarray]:
    res_folder = files("junip3r.res")
    return load_image_rgb(Path(str(res_folder / "setup_preview_placeholder.png")))
