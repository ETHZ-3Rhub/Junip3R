import colorsys
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Set

import yaml
from PySide6.QtCore import QObject
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QMainWindow, QApplication, QFileDialog

from app.frame_extractor.data.repository.abc import IVideoRepository, IFrameSelectionRepository
from app.frame_extractor.data.types.data import Video
from app.frame_extractor.model.frame_extractor_model import FrameExtractorModel
from app.frame_extractor.widgets.frame_extractor import FrameExtractor
from app.labeller.data.app_model import AppModel
from app.labeller.data.repository.abc import IPointSelectionRepository, ISettingsRepository
from app.labeller.data.repository.config import LabellerConfigRepository
from app.labeller.data.repository.context import ContextRepository
from app.labeller.data.repository.image import ImageRepository
from app.labeller.data.repository.label import JuniperLabelRepository
from app.labeller.data.types.abc import BoundingBoxType
from app.labeller.data.types.data import InstanceType, Instance, KeypointType, BoundingBox, Keypoint
from app.labeller.widgets.labeller import Labeller


class MockSelectionRepository(IPointSelectionRepository):
    def __init__(self):
        self._selections: Dict[int, Tuple[Optional[str], Optional[int]]] = {}

    def get_selection(self, image_index: int) -> Tuple[Optional[str], Optional[int]]:
        return self._selections.get(image_index, (None, None))

    def set_selection(self, image_index: int, instance_id: str, point_index: int):
        self._selections[image_index] = (instance_id, point_index)


class MockSettingsRepository(ISettingsRepository):
    def __init__(self):
        self._brightness = 0.0
        self._contrast = 0.0

    def get_settings(self, image_index: int) -> Tuple[float, float]:
        return self._brightness, self._contrast

    def set_settings(self, image_index: int, brightness: float, contrast: float):
        self._brightness = brightness
        self._contrast = contrast


def color_from_hue(hue: float) -> Tuple[int, int, int]:
    color = colorsys.hsv_to_rgb(hue, 1, 1)
    return int(color[0] * 255), int(color[1] * 255), int(color[2] * 255)


def color_from_string(color_string: str) -> Optional[Tuple[int, int, int]]:
    if color_string.startswith("#"):
        return int(color_string[1:3], 16), int(color_string[3:5], 16), int(color_string[5:7], 16)
    else:
        color = QColor(color_string)
        if not color.isValid():
            return None


def load_instance_types(config_file: Path):
    config = yaml.safe_load(open(config_file, 'r'))

    instance_type_dicts = [instance_type for instance_type in config["instance_types"]]
    instance_types = []
    for instance_type_dict in instance_type_dicts:
        name = instance_type_dict["name"]
        points = instance_type_dict["points"]
        colors = instance_type_dict["colors"] if "colors" in instance_type_dict else {}
        skeleton = instance_type_dict["skeleton"]
        skeleton = [(points.index(skeleton_point[0]), points.index(skeleton_point[1])) for skeleton_point in skeleton]

        if "bounding_box_type" not in instance_type_dict:
            bounding_box_type = BoundingBoxType.AUTOMATIC
        else:
            if instance_type_dict["bounding_box_type"] == "automatic":
                bounding_box_type = BoundingBoxType.AUTOMATIC
            elif instance_type_dict["bounding_box_type"] == "manual":
                bounding_box_type = BoundingBoxType.MANUAL
            else:
                raise ValueError(f"Invalid bounding box type: {instance_type_dict['bounding_box_type']}")

        point_types = []
        for point_index, point in enumerate(points):
            color = None
            if point_index in colors:
                color = color_from_string(colors[point_index])
            if color is None:
                point_percentage = point_index / len(points)
                color = color_from_hue(point_percentage)
            point_types.append(KeypointType(point, color))

        instance_types.append(InstanceType(name, bounding_box_type, point_types, skeleton))

    instance_type_names = [instance_type.name for instance_type in instance_types]
    expected_instance_types = [
        instance_types[instance_type_names.index(instance_type_name)]
        for instance_type_name in config["instances"]
    ]

    tags = config["tags"] if "tags" in config else []

    return instance_types, expected_instance_types, tags


bundle_dir = getattr(sys, '_MEIPASS', os.getcwd())
res_folder = Path(os.path.abspath(os.path.join(bundle_dir, 'res')))
app_icon_file = res_folder / "junip3r_icon.png"

app = QApplication(sys.argv)
app.setWindowIcon(QIcon(str(app_icon_file)))


if len(sys.argv) > 1:
    input_path = Path(sys.argv[1])
    if input_path.is_file():
        config_file = input_path
        project_folder = input_path.parent
    else:
        config_file = input_path / "config.yaml"
        project_folder = input_path

    if not config_file.exists():
        print(f"Config file {config_file} does not exist.")
        exit(1)
else:
    dialog = QFileDialog()
    dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
    dialog.setNameFilter("Config File (*.yaml)")
    dialog.setWindowTitle("Select Config File")
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)

    if dialog.exec():
        file_path = dialog.selectedFiles()[0]
        config_file = Path(file_path)
        project_folder = config_file.parent
    else:
        exit(1)


instance_types, expected_instance_types, tags = load_instance_types(config_file)
labeller_config_repository = LabellerConfigRepository(instance_types, expected_instance_types, tags)

def build_labeller_model():
    image_file_endings = [".png", ".jpg", ".jpeg"]
    image_folder = project_folder / "images"
    image_files = [f for f in image_folder.glob("*") if f.suffix.lower() in image_file_endings]
    image_repository = ImageRepository(image_files)

    context_file_endings = [".avi", ".mp4", ".mkv"]
    context_folder = project_folder / "context"
    def find_context_file(image_file: Path) -> Optional[Path]:
        for ending in context_file_endings:
            context_file = context_folder / (image_file.stem + ending)
            if context_file.exists():
                return context_file
        return None
    context_files = [find_context_file(f) for f in image_files]
    context_repository = ContextRepository(context_files)

    label_folder = project_folder / "labels"
    label_files = [label_folder / (image_file.stem + ".json") for image_file in image_files]
    label_repository = JuniperLabelRepository(instance_types, label_files)

    labeller_model = AppModel()
    labeller_model._image_repository = image_repository
    labeller_model._context_repository = context_repository
    labeller_model._config_repository = labeller_config_repository
    labeller_model._label_repository = label_repository
    labeller_model._point_selection_repository = MockSelectionRepository()
    labeller_model._settings_repository = MockSettingsRepository()

    return labeller_model


class MockVideoRepository(IVideoRepository):
    def __init__(self, videos: List[Video]):
        self._videos = videos

    def get_videos(self) -> List[Video]:
        return self._videos

    def set_videos(self, videos: List[Video]):
        self._videos = videos


class MockFrameSelectionRepository(IFrameSelectionRepository):
    def __init__(self):
        self._selected_frames: Dict[str, Set[int]] = {}

    def get_selected_frames(self, video_id: str) -> Set[int]:
        return self._selected_frames.get(video_id, set())

    def set_selected_frames(self, video_id: str, frames: Set[int]):
        self._selected_frames[video_id] = frames


videos = [
    Video("video_0", Path("C:/Users/Me/Projects/BehaviourTrackingData/data/videos/epm_2023/EPM_Frame5.avi")),
    Video("video_1", Path("C:/Users/Me/Projects/BehaviourTrackingData/data/videos/nor_2024_new/GPMN07_NORt_241214_1.avi")),
    Video("video_2", Path("C:/Users/Me/Projects/BehaviourTrackingData/data/videos/epm_2023 - Copy/EPM_Frame5.avi")),
]

frame_extractor_model = FrameExtractorModel()
frame_extractor_model._video_repository = MockVideoRepository(videos)
frame_extractor_model._frame_selection_repository = MockFrameSelectionRepository()


class AppController(QObject):
    def __init__(self):
        super().__init__()
        self.window: Optional[QMainWindow] = None
        self.frame_extractor: Optional[FrameExtractor] = None
        self.labeller: Optional[Labeller] = None

    def show_frame_extractor(self):
        if not self.frame_extractor:
            self.frame_extractor = FrameExtractor()
            self.frame_extractor.set_labeller_callback(self.show_labeller)
        self.frame_extractor.set_model(project_folder, frame_extractor_model)
        self._swap_to(self.frame_extractor)

    def show_labeller(self):
        if not self.labeller:
            self.labeller = Labeller()
            self.labeller.set_frame_extractor_callback(self.show_frame_extractor)
        self.labeller.set_model(build_labeller_model())
        self._swap_to(self.labeller)

    def _swap_to(self, new_window: QMainWindow):
        old = self.window
        self.window = new_window
        self.window.show()
        if old is not None:
            old.close()


controller = AppController()

if build_labeller_model().get_num_images() > 0:
    controller.show_labeller()
else:
    controller.show_frame_extractor()

sys.exit(app.exec())
