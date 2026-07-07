import time
from typing import Optional, Tuple, List

import numpy as np
from PySide6.QtCore import QObject, Signal, QThread

from app.labeller.data.repository.abc import TemporalContext
from app.labeller.data.types.abc import IInstance, IInstanceType
from app.labeller.model.editor_model import EditorModel


class ContextLoadWorker(QObject):
    context_loaded = Signal(int, object)

    def __init__(self, model: EditorModel, parent=None):
        super().__init__(parent)
        self._model = model

    def load_context(self, image_index: int):
        context = self._model.get_context(image_index)
        self.context_loaded.emit(image_index, context)

class ImageModel(QObject):
    reset = Signal()

    instance_added = Signal(IInstance)  # instance
    instance_deleted = Signal(object)  # instance
    instance_updated = Signal(IInstance)  # instance

    new_instance_type_changed = Signal(IInstanceType)  # instance_type

    selection_changed = Signal(object, int)  # instance_id, point_index
    settings_changed = Signal(float, float)  # brightness, contrast

    _context_load_requested = Signal(int)

    def __init__(self, model: EditorModel):
        super().__init__()
        self._model = model
        self._image_index = model.get_image_index()

        self._is_context_loaded: bool = False
        self._context: Optional[TemporalContext] = None

        self._context_load_worker = ContextLoadWorker(model)
        self._context_load_worker_thread = QThread()
        self._context_load_worker.moveToThread(self._context_load_worker_thread)

        self._context_load_worker.context_loaded.connect(self._context_loaded)
        self._context_load_requested.connect(self._context_load_worker.load_context)

        self._model.image_index_changed.connect(self._image_index_changed)
        self._model.instance_added.connect(self._instance_added)
        self._model.instance_deleted.connect(self._instance_deleted)
        self._model.instance_updated.connect(self._instance_updated)
        self._model.new_instance_type_changed.connect(self._new_instance_type_changed)
        self._model.selection_changed.connect(self._selection_changed)
        self._model.settings_changed.connect(self._settings_changed)

        self._context_load_worker_thread.start()
        self._context_load_requested.emit(self._image_index)

    def get_num_images(self) -> int:
        return self._model.get_num_images()

    def get_image_index(self) -> int:
        return self._model.get_image_index()

    def get_image_name(self) -> str:
        return self._model.get_image_name(self._image_index)

    def get_image(self) -> np.ndarray:
        return self._model.get_image(self._image_index)

    def get_context(self) -> Optional[TemporalContext]:
        timeout = 5.0  # seconds
        while not self._context_loaded and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1
        if not self._context_loaded:
            return None
        return self._context

    def get_instance_types(self) -> List[IInstanceType]:
        return self._model.get_instance_types(self._image_index)

    def get_instance_type(self, instance_type_name: str) -> IInstanceType:
        return self._model.get_instance_type(self._image_index, instance_type_name)

    def get_new_instance_type(self) -> IInstanceType:
        return self._model.get_new_instance_type(self._image_index)

    def set_new_instance_type(self, instance_type_name: str):
        self._model.set_new_instance_type(self._image_index, instance_type_name)

    def get_instances(self) -> List[IInstance]:
        return self._model.get_instances(self._image_index)

    def get_instance(self, instance_id: str) -> Optional[IInstance]:
        return self._model.get_instance(self._image_index, instance_id)

    def get_selection(self) -> Tuple[Optional[str], Optional[int]]:
        return self._model.get_selection(self._image_index)

    def get_settings(self) -> Tuple[float, float]:
        return self._model.get_settings(self._image_index)

    def rename_instance(self, instance_id: Optional[str], name: str):
        self._model.rename_instance(self._image_index, instance_id, name)

    def set_bounding_box(self, instance_id: Optional[str], box: Tuple[Tuple[float, float], Tuple[float, float]] = None):
        self._model.set_bounding_box(self._image_index, instance_id, box)

    def delete_bounding_box(self, instance_id: Optional[str]):
        self._model.delete_bounding_box(self._image_index, instance_id)

    def place_keypoint(self, instance_id: Optional[str], point_index: int, p: Tuple[float, float], visibility: float = 2.0):
        self._model.place_keypoint(self._image_index, instance_id, point_index, p, visibility)

    def move_keypoint(self, instance_id: str, point_index: int, p: Tuple[float, float]):
        self._model.move_keypoint(self._image_index, instance_id, point_index, p)

    def delete_keypoint(self, instance_id: Optional[str], point_index: int):
        self._model.delete_keypoint(self._image_index, instance_id, point_index)

    def toggle_keypoint_visibility(self, instance_id: str, point_index: int):
        self._model.toggle_keypoint_visibility(self._image_index, instance_id, point_index)

    def delete_instance(self, instance_id: str):
        self._model.delete_instance(self._image_index, instance_id)

    def set_instance_type(self, instance_id: str, instance_type_name: str):
        self._model.set_instance_type(self._image_index, instance_id, instance_type_name)

    def paste_instance(self, instance: IInstance):
        self._model.paste_instance(self._image_index, instance)

    def set_selection(self, instance_id: Optional[str], point_index: int):
        self._model.set_selection(self._image_index, instance_id, point_index)

    def set_instance_selection(self, instance_id: Optional[str]):
        self._model.set_instance_selection(self._image_index, instance_id)

    def set_point_selection(self, point_index: int):
        self._model.set_point_selection(self._image_index, point_index)

    def select_previous_point(self):
        self._model.select_previous_point(self._image_index)

    def select_next_point(self):
        self._model.select_next_point(self._image_index)

    def set_settings(self, brightness: float, contrast: float):
        self._model.set_settings(self._image_index, brightness, contrast)

    def undo(self):
        self._model.undo(self._image_index)

    def redo(self):
        self._model.redo(self._image_index)

    def _image_index_changed(self, image_index: int):
        self._image_index = image_index
        self._is_context_loaded = False
        self._context = None
        self._context_load_requested.emit(image_index)
        self.reset.emit()

    def _context_loaded(self, image_index: int, context: Optional[TemporalContext]):
        if image_index != self._image_index:
            return

        self._context = context
        self._is_context_loaded = True

    def _instance_added(self, image_index: int, instance: IInstance):
        if image_index == self._image_index:
            self.instance_added.emit(instance)

    def _instance_deleted(self, image_index: int, instance_id: str):
        if image_index == self._image_index:
            self.instance_deleted.emit(instance_id)

    def _instance_updated(self, image_index: int, instance: IInstance):
        if image_index == self._image_index:
            self.instance_updated.emit(instance)

    def _new_instance_type_changed(self, image_index: int, instance_type: IInstanceType):
        if image_index == self._image_index:
            self.new_instance_type_changed.emit(instance_type)

    def _selection_changed(self, image_index: int, instance_id: Optional[str], point_index: Optional[int]):
        if image_index == self._image_index:
            self.selection_changed.emit(instance_id, point_index)

    def _settings_changed(self, image_index: int, brightness: float, contrast: float):
        if image_index == self._image_index:
            self.settings_changed.emit(brightness, contrast)
