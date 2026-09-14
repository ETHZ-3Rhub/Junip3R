import logging
import sys
from importlib.resources import files
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from junip3r.logging_setup import create_logging_manager
from junip3r.frame_extractor.data.repository.image_repository import ImageRepository
from junip3r.frame_extractor.data.repository.tag_repository import TagRepository
from junip3r.frame_extractor.data.repository.video_repository import VideoRepository
from junip3r.frame_extractor.model.frame_extractor_model import FrameExtractorModel
from junip3r.frame_extractor.widgets.frame_extractor import FrameExtractor


logger = logging.getLogger(__name__)


def from_config_file(config_file: Path, integrated: bool = False, parent=None) -> FrameExtractor:
    project_folder = config_file.parent

    video_repository = VideoRepository(project_folder / "_frame_extractor" / "videos.csv")
    frame_repository = ImageRepository(project_folder / "_frame_extractor" / "frames.csv")
    tag_repository = TagRepository(project_folder / "meta" / "tags")

    model = FrameExtractorModel(video_repository, frame_repository, tag_repository)

    frame_extractor = FrameExtractor(integrated=integrated, parent=parent)
    frame_extractor.set_model(model)
    frame_extractor.set_project_folder(project_folder)

    return frame_extractor


def main():
    log_manager = create_logging_manager(run_mode="standalone")
    try:
        app = QApplication(sys.argv)

        res_folder = files("junip3r.res")
        app_icon = QIcon(str(res_folder / "junip3r_logo.png"))

        dialog = QtWidgets.QFileDialog()
        dialog.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFile)  # type: ignore[arg-type]
        dialog.setNameFilter("Junip3R Config File (*.yaml)")
        dialog.setWindowTitle("Select Config File")
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptOpen)

        if dialog.exec():
            file_path = dialog.selectedFiles()[0]
            config_file = Path(file_path)
        else:
            exit(1)

        log_manager.start_app_run("frame_extractor")
        logger.info("starting standalone frame extractor",
                    extra={"event_category": "lifecycle", "event_name": "app_start", "app_name": "frame_extractor"})

        frame_extractor = from_config_file(config_file)
        frame_extractor.show()

        sys.exit(app.exec())
    finally:
        log_manager.close()


if __name__ == "__main__":
    main()
