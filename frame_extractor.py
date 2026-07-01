import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.frame_extractor.data.repository.image_repository import ImageRepository
from app.frame_extractor.data.repository.tag_repository import TagRepository
from app.frame_extractor.data.repository.video_repository import VideoRepository
from app.frame_extractor.model.frame_extractor_model import FrameExtractorModel
from app.frame_extractor.widgets.frame_extractor import FrameExtractor


project_folder = Path("_testdata/project")


video_repository = VideoRepository(project_folder / "_frame_extractor" / "videos.csv")
frame_repository = ImageRepository(project_folder / "_frame_extractor" / "frames.csv")
tag_repository = TagRepository(project_folder / "meta" / "tags")

model = FrameExtractorModel(video_repository, frame_repository, tag_repository)

app = QApplication(sys.argv)

frame_extractor = FrameExtractor()
frame_extractor.set_model(model)
frame_extractor.set_project_folder(project_folder)
frame_extractor.show()

sys.exit(app.exec())
