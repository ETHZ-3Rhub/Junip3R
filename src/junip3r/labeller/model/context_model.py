from dataclasses import dataclass, replace
from typing import Optional

import numpy as np
from PySide6.QtCore import QObject, Signal, QThread

from junip3r.labeller.data.repository.abc import IContextRepository
from junip3r.labeller.data.types.abc import TemporalContext
from junip3r.labeller.model.image_state import ImageNavigationState


@dataclass(frozen=True)
class ContextState:
    loaded: bool = False
    enabled: bool = False
    pos: int = 0
    context: Optional[TemporalContext] = None

    @property
    def min(self) -> int:
        if self.context is None:
            return 0
        return -len(self.context[0])

    @property
    def max(self) -> int:
        if self.context is None:
            return 0
        return len(self.context[2])

    @property
    def image(self) -> Optional[np.ndarray]:
        if self.context is None:
            return None
        before, current, after = self.context
        context_frames = before + [current] + after
        return context_frames[self.pos + len(before)]


class ContextLoadWorker(QObject):
    context_loaded = Signal(int, object)

    def __init__(self, repo: IContextRepository, parent=None):
        super().__init__(parent)
        self._repo = repo

    def load_context(self, image_index: int):
        context = self._repo.get_context(image_index)
        self.context_loaded.emit(image_index, context)


class ContextModel(QObject):
    changed = Signal(object)

    _context_load_requested = Signal(int)

    def __init__(self, context_repository: IContextRepository):
        super().__init__()

        self._state = ContextState()
        self._image_index = 0

        self._context_load_worker = ContextLoadWorker(context_repository)
        self._context_load_worker_thread = QThread()
        self._context_load_worker.moveToThread(self._context_load_worker_thread)

        self._context_load_worker.context_loaded.connect(self._context_loaded)
        self._context_load_requested.connect(self._context_load_worker.load_context)

        self._context_load_worker_thread.start()
        self._context_load_requested.emit(self._image_index)

    def get_state(self) -> ContextState:
        return self._state

    def set_context_enabled(self, enabled: bool):
        self._state = replace(self._state, enabled=enabled, pos=0)
        self.changed.emit(self._state)

    def set_context_pos(self, pos: int):
        if pos < self._state.min:
            pos = self._state.min
        if pos > self._state.max:
            pos = self._state.max

        self._state = replace(self._state, pos=pos)
        self.changed.emit(self._state)

    def move_context(self, delta: int):
        self.set_context_pos(self._state.pos + delta)

    def set_image_navigation_state(self, state: ImageNavigationState):
        self._image_index = state.image_index
        self._state = replace(self._state, loaded=False, pos=0, context=None)
        self._context_load_requested.emit(self._image_index)
        self.changed.emit(self._state)

    def _context_loaded(self, image_index: int, context: Optional[TemporalContext]):
        if image_index != self._image_index:
            return

        self._state = replace(self._state, loaded=True, context=context)
        self.changed.emit(self._state)

    def shutdown(self):
        # The worker thread runs its own event loop indefinitely once started -
        # without stopping it here, it would get destroyed while still running when
        # this model is torn down, which PySide6 turns into a crash rather than a
        # clean shutdown.
        self._context_load_worker_thread.quit()
        self._context_load_worker_thread.wait()
