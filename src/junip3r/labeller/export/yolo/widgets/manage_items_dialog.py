from dataclasses import dataclass
from typing import List, Optional, Sequence

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QDialog, QHBoxLayout, QInputDialog, QListWidget, QMessageBox, QPushButton, QVBoxLayout


@dataclass
class NamedItem:
    id: str
    name: str


class ManageItemsDialog(QDialog):
    """A plain list + New/Duplicate/Rename/Delete buttons. Edits apply immediately to
    the shared data - there's no separate Cancel, only Close, since there's nothing to
    roll back.

    This dialog never touches the owner's data directly. Each button just emits a
    *_requested signal describing what the user asked for; the owner (whoever connects
    to them) is the one who actually mutates its own repository, then calls back into
    this dialog's own set_items()/select_item() slots to reflect the result. That round
    trip is synchronous (Qt direct connections run the connected slot immediately,
    inside .emit()), so by the time e.g. _create() returns from emitting
    create_requested, the owner has already mutated its data and already called
    set_items()/select_item() back on this dialog - no return value needed anywhere.
    """
    create_requested = Signal(str)  # name
    duplicate_requested = Signal(str, str)  # source_id, name
    rename_requested = Signal(str, str)  # id, name
    delete_requested = Signal(str)  # id

    def __init__(self, item_label: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Manage {item_label}s")
        self.resize(320, 360)

        self._item_label = item_label
        self._items: List[NamedItem] = []
        self._selected_id: Optional[str] = None

        layout = QVBoxLayout(self)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self._list)

        button_row = QHBoxLayout()
        self._btn_new = QPushButton("New...")
        self._btn_new.clicked.connect(self._create)
        button_row.addWidget(self._btn_new)

        self._btn_duplicate = QPushButton("Duplicate...")
        self._btn_duplicate.clicked.connect(self._duplicate)
        button_row.addWidget(self._btn_duplicate)

        self._btn_rename = QPushButton("Rename...")
        self._btn_rename.clicked.connect(self._rename)
        button_row.addWidget(self._btn_rename)

        self._btn_delete = QPushButton("Delete")
        self._btn_delete.clicked.connect(self._delete)
        button_row.addWidget(self._btn_delete)

        layout.addLayout(button_row)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

        self._update_button_states()

    def selected_id(self) -> Optional[str]:
        return self._selected_id

    @Slot(list)
    def set_items(self, items: Sequence[NamedItem]):
        """Refresh the displayed list. Keeps the current selection by id if it's
        still present, otherwise falls back to the first item - a plain refresh (e.g.
        after a rename) never jumps to "last" on its own. To land on a specific item
        (e.g. one just created), call select_item() right after this.
        """
        self._items = list(items)
        select_id = self._selected_id

        self._list.blockSignals(True)
        self._list.clear()
        for item in self._items:
            self._list.addItem(item.name)
        self._list.blockSignals(False)

        index = next((i for i, item in enumerate(self._items) if item.id == select_id), 0 if self._items else -1)
        if index >= 0:
            self._list.setCurrentRow(index)
            self._selected_id = self._items[index].id
        else:
            self._selected_id = None

        self._update_button_states()

    @Slot(str)
    def select_item(self, item_id: str):
        """Move the selection onto a specific item - e.g. the one the owner just
        created, after handling create_requested/duplicate_requested.
        """
        index = next((i for i, item in enumerate(self._items) if item.id == item_id), -1)
        if index >= 0:
            self._list.setCurrentRow(index)

    def _current_item(self) -> Optional[NamedItem]:
        row = self._list.currentRow()
        return self._items[row] if 0 <= row < len(self._items) else None

    def _update_button_states(self):
        has_selection = self._current_item() is not None
        self._btn_duplicate.setEnabled(has_selection)
        self._btn_rename.setEnabled(has_selection)
        self._btn_delete.setEnabled(has_selection and len(self._items) > 1)

    def _on_row_changed(self, row: int):
        self._selected_id = self._items[row].id if 0 <= row < len(self._items) else None
        self._update_button_states()

    def _create(self):
        suggested = f"{self._item_label} {len(self._items) + 1}"
        name, ok = QInputDialog.getText(self, f"New {self._item_label}", "Name:", text=suggested)
        if not ok or not name.strip():
            return
        self.create_requested.emit(name.strip())

    def _duplicate(self):
        current = self._current_item()
        if current is None:
            return
        name, ok = QInputDialog.getText(self, f"Duplicate {self._item_label}", "Name:", text=f"Copy of {current.name}")
        if not ok or not name.strip():
            return
        self.duplicate_requested.emit(current.id, name.strip())

    def _rename(self):
        current = self._current_item()
        if current is None:
            return
        name, ok = QInputDialog.getText(self, f"Rename {self._item_label}", "Name:", text=current.name)
        if not ok or not name.strip():
            return
        self.rename_requested.emit(current.id, name.strip())

    def _delete(self):
        current = self._current_item()
        if current is None or len(self._items) <= 1:
            return
        confirm = QMessageBox.question(self, f"Delete {self._item_label}", f"Delete \"{current.name}\"?")
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.delete_requested.emit(current.id)
