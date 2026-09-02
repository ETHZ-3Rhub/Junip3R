from pathlib import Path
from typing import Optional, Sequence

import cv2
import numpy as np

from junip3r.common.labels.serialization import LabelSerializer
from junip3r.labeller.data.repository.label import InstanceMapper
from junip3r.labeller.data.types.abc import IInstance


class PreviewPersistenceRepository:
    """Writes the setup preview's current image/instances into a project's
    _labeller/preview/ folder on every change, so any project can later be
    used as a template - see load_project_as_preset in new_project_window.py.
    """

    def __init__(self, preview_folder: Path):
        self._preview_folder = preview_folder

    def save(self, image: Optional[np.ndarray], instances: Sequence[IInstance]) -> None:
        self._preview_folder.mkdir(parents=True, exist_ok=True)

        if image is not None:
            cv2.imwrite(str(self._preview_folder / "image.png"), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))

        data = InstanceMapper([]).to_data(instances)
        LabelSerializer().write_instances(self._preview_folder / "labels.json", data)
