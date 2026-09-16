from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from PySide6.QtCore import QModelIndex, Qt, Signal
from PySide6.QtGui import QFont, QIcon, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QLabel, QToolButton, QTreeView, QVBoxLayout, QWidget,
)

PresetRole = Qt.ItemDataRole.UserRole + 1


@dataclass(frozen=True)
class PresetListEntry:
    """A single selectable row in PresetList.

    `key` is a stable identity used to re-find this entry across a
    set_sections() refresh (e.g. to restore the previous selection) - it's
    compared by equality instead of `payload` itself, since payload may end
    up being something without a cheap/safe __eq__ (a Preset with an image
    array, for instance).
    """
    key: str
    name: str
    payload: Any
    tooltip: str = ""


def _make_header_item(title: str) -> QStandardItem:
    item = QStandardItem(title)
    item.setFlags(Qt.ItemFlag.ItemIsEnabled)
    font = QFont()
    font.setBold(True)
    item.setFont(font)
    return item


def _make_entry_item(entry: PresetListEntry) -> QStandardItem:
    item = QStandardItem(entry.name)
    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
    if entry.tooltip:
        item.setToolTip(entry.tooltip)
    item.setData(entry, PresetRole)
    return item


class PresetListModel(QStandardItemModel):
    """Tree model grouping PresetListEntry rows under non-selectable section
    headers (one top-level row per section, presets as its children).
    Sections with no entries are dropped entirely rather than shown empty.

    A section title of None means "no header" - its entries are appended
    directly as top-level rows instead of nested under a header item. Since
    they end up with no children of their own, they get no expand arrow
    either, so this doubles as the way to put a non-collapsible entry (e.g.
    "Empty") above the grouped sections.
    """

    def set_sections(self, sections: List[Tuple[Optional[str], List[PresetListEntry]]]):
        self.clear()
        for title, entries in sections:
            if not entries:
                continue
            if title is None:
                for entry in entries:
                    self.appendRow(_make_entry_item(entry))
                continue
            header_item = _make_header_item(title)
            self.appendRow(header_item)
            for entry in entries:
                header_item.appendRow(_make_entry_item(entry))

    def first_entry_index(self) -> QModelIndex:
        for row in range(self.rowCount()):
            index = self.index(row, 0)
            if self.flags(index) & Qt.ItemFlag.ItemIsSelectable:
                return index
            if self.rowCount(index) > 0:
                return self.index(0, 0, index)
        return QModelIndex()

    def find_entry_index_by_key(self, key: str) -> QModelIndex:
        for row in range(self.rowCount()):
            index = self.index(row, 0)
            entry = index.data(PresetRole)
            if entry is not None and entry.key == key:
                return index
            for child_row in range(self.rowCount(index)):
                child_index = self.index(child_row, 0, index)
                child_entry = child_index.data(PresetRole)
                if child_entry is not None and child_entry.key == key:
                    return child_index
        return QModelIndex()


class PresetTreeView(QTreeView):
    """QTreeView that skips non-selectable (header) rows during keyboard nav,
    and restores the previous selection if a mouse press lands the current
    index on one (QAbstractItemView's default press handling otherwise runs
    ClearAndSelect on the clicked index regardless of selectability). Letting
    the base class handle the press first - rather than swallowing the event
    outright - keeps clicks on the expand/collapse arrow working.
    """

    def mousePressEvent(self, event):
        previous_current = self.currentIndex()

        super().mousePressEvent(event)

        current = self.currentIndex()
        if current.isValid() and not (self.model().flags(current) & Qt.ItemFlag.ItemIsSelectable):
            if previous_current.isValid():
                self.setCurrentIndex(previous_current)

    def moveCursor(self, action, modifiers):
        index = super().moveCursor(action, modifiers)
        model = self.model()
        if model is None:
            return index

        forward = action not in (
            QAbstractItemView.CursorAction.MoveUp,
            QAbstractItemView.CursorAction.MoveLeft,
            QAbstractItemView.CursorAction.MovePrevious,
        )

        while index.isValid() and not (model.flags(index) & Qt.ItemFlag.ItemIsSelectable):
            next_index = self.indexBelow(index) if forward else self.indexAbove(index)
            if not next_index.isValid():
                break
            index = next_index

        return index


class PresetList(QWidget):
    """Grouped, single-scrollbar preset picker for multiple sources (builtin,
    local templates, GitHub repos, imported projects, ...). Each source is a
    section header with its presets as children; sections with no presets
    aren't shown. The widget doesn't know how to fetch presets itself - the
    owner feeds it rows via set_sections() and reacts to refresh_requested
    to go re-fetch them (from local disk and/or network, so it shouldn't
    block here) and call set_sections() again.
    """

    preset_selected = Signal(object)  # the selected entry's payload, or None
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._model = PresetListModel(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Presets"))
        top_bar.addStretch(1)

        self.btn_refresh = QToolButton()
        self.btn_refresh.setIcon(QIcon.fromTheme("view-refresh"))
        self.btn_refresh.setToolTip("Refresh")
        self.btn_refresh.setAutoRaise(True)
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_requested)
        top_bar.addWidget(self.btn_refresh)

        layout.addLayout(top_bar)

        self.tree_view = PresetTreeView(self)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        # Padding, rather than a custom delegate, is the easy way to grow QTreeView row height.
        self.tree_view.setStyleSheet("QTreeView::item { padding: 6px 2px; }")
        self.tree_view.setModel(self._model)
        self.tree_view.selectionModel().currentChanged.connect(self._current_changed)
        layout.addWidget(self.tree_view)

    def set_sections(
        self,
        sections: List[Tuple[Optional[str], List[PresetListEntry]]],
        select_key: Optional[str] = None,
    ):
        """Replace all rows. Re-selects the entry matching `select_key` if
        it's still present, otherwise falls back to the first entry, or no
        selection if the tree ends up empty. Note the model reset this
        triggers clears the current selection first, so preset_selected(None)
        may fire transiently before the restored/fallback selection does.
        """
        self._model.set_sections(sections)

        index = self._model.find_entry_index_by_key(select_key) if select_key is not None else QModelIndex()
        if not index.isValid():
            index = self._model.first_entry_index()

        self.tree_view.setCurrentIndex(index)

    def selected_key(self) -> Optional[str]:
        entry = self.tree_view.currentIndex().data(PresetRole)
        return entry.key if entry is not None else None

    def _current_changed(self, current: QModelIndex, _previous: QModelIndex):
        entry = current.data(PresetRole) if current.isValid() else None
        self.preset_selected.emit(entry.payload if entry is not None else None)
