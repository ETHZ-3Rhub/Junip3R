"""Export-profile selector prototype - refined from the "variant C" combo-with-edit-entry
design (liked best, no visible flicker on Windows), with the selector widget's API
cut down per feedback: no more create/duplicate/rename/delete/describe callbacks
threaded through its constructor - it's a plain `QComboBox` subclass now, real item
selection flows through QComboBox's own `currentIndexChanged`/`currentData()`, and the
owning dialog (not the widget) decides what "manage" means and how to format each
item's display text (e.g. the "(used by N profiles)" annotation).

Standalone script, no `junip3r` imports, in-memory fake data only. Run directly.
"""
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple
from uuid import uuid4

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFormLayout, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout,
)

MODES = ["YOLO Pose", "YOLO Detect", "YOLO Segment"]
FAKE_INSTANCE_TYPES = ["deer", "fox", "vegetation_patch", "trail_marker"]


# --- Fake in-memory data model -------------------------------------------------------

@dataclass
class SetSplitConfig:
    id: str
    name: str


@dataclass
class ExportProfile:
    id: str
    name: str
    mode: str
    instance_types: set = field(default_factory=set)
    set_split_id: str = ""


@dataclass
class NamedItem:
    """Only used by ManageItemsDialog's plain list below - the combo box works
    directly with (id, display_text) pairs instead (see NamedItemComboBox.set_items).
    """
    id: str
    name: str


# --- The reusable selector: a plain QComboBox, no business-logic callbacks ----------

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
    `if item_id is None: return` (see _on_profile_changed/_on_split_changed below for
    the pattern).
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


# --- The "Manage ...s" dialog, shared by both the profile and set-split selectors ---

class ManageItemsDialog(QDialog):
    """A plain list + New/Duplicate/Rename/Delete buttons. Edits apply immediately to
    the shared data - there's no separate Cancel, only Close, since there's nothing to
    roll back.

    Signal/slot version: this dialog never touches the owner's data directly. Each
    button just emits a *_requested signal describing what the user asked for; the
    owner (whoever connects to them) is the one who actually mutates its profiles/
    splits list, then calls back into this dialog's own set_items()/select_item()
    slots to reflect the result. That round trip is synchronous (Qt direct connections
    run the connected slot immediately, inside .emit()), so by the time e.g. _create()
    returns from emitting create_requested, the owner has already mutated its data and
    already called set_items()/select_item() back on this dialog - no return value
    needed anywhere.
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


# --- The export dialog layout being prototyped --------------------------------------

class ExportLayoutPrototype(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Export YOLO Dataset - refined combo-with-edit-entry")
        self.resize(560, 520)

        self._splits: List[SetSplitConfig] = []
        self._profiles: List[ExportProfile] = []
        self._current_profile_id: str = ""

        self._seed_default_data()
        self._build_ui()
        self._refresh_all()

    def _seed_default_data(self):
        split = SetSplitConfig(id=str(uuid4()), name="Default")
        self._splits.append(split)

        profile = ExportProfile(
            id=str(uuid4()), name="Default", mode=MODES[0],
            instance_types=set(FAKE_INSTANCE_TYPES), set_split_id=split.id,
        )
        self._profiles.append(profile)
        self._current_profile_id = profile.id

    def _build_ui(self):
        layout = QVBoxLayout(self)

        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Export Profile:"))
        self._profile_combo = NamedItemComboBox(item_label="Profile")
        self._profile_combo.setMinimumWidth(220)
        self._profile_combo.currentIndexChanged.connect(self._on_profile_combo_changed)
        self._profile_combo.manage_requested.connect(self._manage_profiles)
        profile_row.addWidget(self._profile_combo)
        profile_row.addStretch(1)
        layout.addLayout(profile_row)

        form_layout = QFormLayout()

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(MODES)
        self._mode_combo.currentTextChanged.connect(self._on_mode_changed)
        form_layout.addRow("Mode:", self._mode_combo)

        layout.addLayout(form_layout)

        layout.addWidget(QLabel("Instance Types:"))
        self._instance_list = QListWidget()
        for name in FAKE_INSTANCE_TYPES:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self._instance_list.addItem(item)
        self._instance_list.itemChanged.connect(self._on_instance_types_changed)
        layout.addWidget(self._instance_list)

        split_row = QHBoxLayout()
        split_row.addWidget(QLabel("Set Split:"))
        self._split_combo = NamedItemComboBox(item_label="Set Split")
        self._split_combo.setMinimumWidth(220)
        self._split_combo.currentIndexChanged.connect(self._on_split_combo_changed)
        self._split_combo.manage_requested.connect(self._manage_splits)
        split_row.addWidget(self._split_combo)
        split_row.addStretch(1)
        layout.addLayout(split_row)

        layout.addStretch(1)

        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("Target Folder:"))
        self._target_edit = QLineEdit()
        target_row.addWidget(self._target_edit)
        layout.addLayout(target_row)

        export_button = QPushButton("Export")
        export_button.clicked.connect(self._on_export_clicked)
        layout.addWidget(export_button)

    # --- current profile / its fields ---

    def _current_profile(self) -> ExportProfile:
        return next(p for p in self._profiles if p.id == self._current_profile_id)

    def _on_profile_combo_changed(self, index: int):
        profile_id = self._profile_combo.itemData(index)
        if profile_id is None:
            return  # transient sentinel selection mid-revert (see NamedItemComboBox) - ignore
        self._current_profile_id = profile_id
        self._refresh_all()

    def _manage_profiles(self):
        dialog = ManageItemsDialog("Profile", parent=self)

        def refresh_dialog():
            dialog.set_items([NamedItem(p.id, p.name) for p in self._profiles])

        def on_create(name: str):
            new_item = self._create_profile(name)
            refresh_dialog()
            dialog.select_item(new_item.id)

        def on_duplicate(source_id: str, name: str):
            new_item = self._duplicate_profile(source_id, name)
            refresh_dialog()
            dialog.select_item(new_item.id)

        def on_rename(item_id: str, name: str):
            self._rename_profile(item_id, name)
            refresh_dialog()

        def on_delete(item_id: str):
            self._delete_profile(item_id)
            refresh_dialog()

        dialog.create_requested.connect(on_create)
        dialog.duplicate_requested.connect(on_duplicate)
        dialog.rename_requested.connect(on_rename)
        dialog.delete_requested.connect(on_delete)

        refresh_dialog()
        dialog.select_item(self._current_profile_id)
        dialog.exec()

        selected_id = dialog.selected_id()
        if selected_id is not None:
            self._current_profile_id = selected_id
        self._refresh_all()

    def _on_mode_changed(self, mode: str):
        self._current_profile().mode = mode

    def _on_instance_types_changed(self):
        checked = set()
        for i in range(self._instance_list.count()):
            item = self._instance_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                checked.add(item.text())
        self._current_profile().instance_types = checked

    def _create_profile(self, name: str) -> NamedItem:
        return self._duplicate_profile(self._current_profile_id, name)

    def _duplicate_profile(self, source_id: str, name: str) -> NamedItem:
        source = next(p for p in self._profiles if p.id == source_id)
        profile = ExportProfile(
            id=str(uuid4()), name=name, mode=source.mode,
            instance_types=set(source.instance_types), set_split_id=source.set_split_id,
        )
        self._profiles.append(profile)
        return NamedItem(profile.id, profile.name)

    def _rename_profile(self, profile_id: str, name: str):
        next(p for p in self._profiles if p.id == profile_id).name = name

    def _delete_profile(self, profile_id: str):
        self._profiles = [p for p in self._profiles if p.id != profile_id]
        if self._current_profile_id == profile_id:
            self._current_profile_id = self._profiles[0].id

    # --- set split (scoped to the current profile's pointer) ---

    def _on_split_combo_changed(self, index: int):
        split_id = self._split_combo.itemData(index)
        if split_id is None:
            return  # transient sentinel selection mid-revert - ignore
        self._current_profile().set_split_id = split_id
        self._refresh_all()

    def _manage_splits(self):
        dialog = ManageItemsDialog("Set Split", parent=self)

        def refresh_dialog():
            dialog.set_items([NamedItem(s.id, s.name) for s in self._splits])

        def on_create(name: str):
            new_item = self._create_split(name)
            refresh_dialog()
            dialog.select_item(new_item.id)

        def on_duplicate(source_id: str, name: str):
            new_item = self._duplicate_split(source_id, name)
            refresh_dialog()
            dialog.select_item(new_item.id)

        def on_rename(item_id: str, name: str):
            self._rename_split(item_id, name)
            refresh_dialog()

        def on_delete(item_id: str):
            self._delete_split(item_id)
            refresh_dialog()

        dialog.create_requested.connect(on_create)
        dialog.duplicate_requested.connect(on_duplicate)
        dialog.rename_requested.connect(on_rename)
        dialog.delete_requested.connect(on_delete)

        refresh_dialog()
        dialog.select_item(self._current_profile().set_split_id)
        dialog.exec()

        selected_id = dialog.selected_id()
        if selected_id is not None:
            self._current_profile().set_split_id = selected_id
        self._refresh_all()

    def _split_combo_items(self) -> List[Tuple[str, str]]:
        # The "(used by N profiles)" annotation is computed here, by the dialog that
        # already knows what a "profile" is - NamedItemComboBox just renders whatever
        # display text it's given, it has no notion of "usage" at all.
        items = []
        for split in self._splits:
            count = sum(1 for p in self._profiles if p.set_split_id == split.id)
            label = f"{split.name}  (used by {count} profiles)" if count > 1 else split.name
            items.append((split.id, label))
        return items

    def _create_split(self, name: str) -> NamedItem:
        split = SetSplitConfig(id=str(uuid4()), name=name)
        self._splits.append(split)
        return NamedItem(split.id, split.name)

    def _duplicate_split(self, source_id: str, name: str) -> NamedItem:
        split = SetSplitConfig(id=str(uuid4()), name=name)
        self._splits.append(split)
        return NamedItem(split.id, split.name)

    def _rename_split(self, split_id: str, name: str):
        next(s for s in self._splits if s.id == split_id).name = name

    def _delete_split(self, split_id: str):
        self._splits = [s for s in self._splits if s.id != split_id]
        fallback_id = self._splits[0].id
        for profile in self._profiles:
            if profile.set_split_id == split_id:
                profile.set_split_id = fallback_id

    # --- misc ---

    def _refresh_all(self):
        profile = self._current_profile()

        self._profile_combo.set_items(
            [(p.id, p.name) for p in self._profiles], self._current_profile_id)

        self._mode_combo.blockSignals(True)
        self._mode_combo.setCurrentText(profile.mode)
        self._mode_combo.blockSignals(False)

        self._instance_list.blockSignals(True)
        for i in range(self._instance_list.count()):
            item = self._instance_list.item(i)
            checked = item.text() in profile.instance_types
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self._instance_list.blockSignals(False)

        self._split_combo.set_items(self._split_combo_items(), profile.set_split_id)

    def _on_export_clicked(self):
        profile = self._current_profile()
        split = next(s for s in self._splits if s.id == profile.set_split_id)
        QMessageBox.information(
            self,
            "Export (prototype)",
            f"Would export profile \"{profile.name}\" ({profile.mode})\n"
            f"Instance types: {', '.join(sorted(profile.instance_types)) or '(none selected)'}\n"
            f"Using set split \"{split.name}\"\n"
            f"Target folder: {self._target_edit.text() or '(none selected)'}",
        )


def main():
    app = QApplication(sys.argv)
    dialog = ExportLayoutPrototype()
    dialog.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
