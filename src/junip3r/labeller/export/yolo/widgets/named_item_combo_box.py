from typing import Optional, Sequence, Tuple

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox


class NamedItemComboBox(QComboBox):
    """A QComboBox listing (id, display_text) items plus a trailing "Edit {label}s..."
    entry.

    Real item selection needs nothing special from callers: connect to the ordinary
    `currentIndexChanged` signal and read `currentData()`, same as any other QComboBox.
    The one thing to know: picking the trailing entry never actually becomes "the
    current item" - it's a one-shot action, not a value - so this widget immediately
    reverts the selection back to whatever it was before and emits `manage_requested`
    instead. Because that revert happens synchronously (same call, no repaint in
    between), there's no visible flicker - but `currentIndexChanged`/`currentData()`
    WILL still fire once for the transient sentinel selection before the revert fires
    again with the real value, so a `currentIndexChanged` handler should guard
    `if item_id is None: return`. Owners should connect to `currentIndexChanged`, never
    to `activated` - that's reserved for this widget's own sentinel handling.
    """
    manage_requested = Signal()

    def __init__(self, item_label: str, parent=None):
        super().__init__(parent)
        self._item_label = item_label
        self._last_valid_index = -1
        self.activated.connect(self._on_activated)

    def set_items(self, items: Sequence[Tuple[str, str]], current_id: Optional[str]):
        self.blockSignals(True)
        self.clear()
        for item_id, display_text in items:
            self.addItem(display_text, userData=item_id)
        if items:
            self.insertSeparator(self.count())
        self.addItem(f"Edit {self._item_label}s...", userData=None)

        index = next((i for i, (item_id, _) in enumerate(items) if item_id == current_id), 0 if items else -1)
        if index >= 0:
            self.setCurrentIndex(index)
        self._last_valid_index = index
        self.blockSignals(False)

    def _on_activated(self, index: int):
        if self.itemData(index) is None:
            # Sentinel entry (or, rarely, the separator via keyboard nav) - snap back
            # to the last real selection and ask the owner to manage instead.
            if self._last_valid_index >= 0:
                self.setCurrentIndex(self._last_valid_index)
            if index == self.count() - 1:
                self.manage_requested.emit()
            return

        self._last_valid_index = index
