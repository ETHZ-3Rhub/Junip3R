from dataclasses import dataclass
from typing import Optional, List, Mapping

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer, Signal, QObject
from PySide6.QtWidgets import QApplication, QDialog, QFormLayout, QVBoxLayout, QComboBox, QLabel, QGroupBox, \
    QHBoxLayout, QSlider, QPushButton, QStyledItemDelegate, QHeaderView, QAbstractItemView, \
    QStyleOptionComboBox, QStyle, QTableView, QDialogButtonBox, QMessageBox

from junip3r.labeller.export.yolo.set_split import ITaggedImage, SetSplitConfig, SetSplit

SET_LABELS = {
    None: "Unassigned",
    "train": "Train",
    "val": "Val",
}


class SetAssignmentTableModel(QAbstractTableModel):
    NAME_COLUMN = 0
    NUM_IMAGES_COLUMN = 1
    SET_COLUMN = 2

    SetRole = Qt.ItemDataRole.UserRole + 1

    group_assigned = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._grouping: Optional[str] = None

        self._data = [
            {"name": "image1.jpg", "num_images": 1, "set": None},
            {"name": "image2.jpg", "num_images": 1, "set": None},
        ]

    @property
    def grouping(self) -> Optional[str]:
        return self._grouping

    def set(self, grouping: Optional[str], data: List[dict]):
        self.beginResetModel()
        self._grouping = grouping
        self._data = data
        self.endResetModel()

    def columnCount(self, parent=QModelIndex()):
        return 3

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if (
            orientation != Qt.Orientation.Horizontal
            or role != Qt.ItemDataRole.DisplayRole
        ):
            return None

        if section == self.NAME_COLUMN:
            return "Image" if self._grouping is None else self._grouping

        if section == self.NUM_IMAGES_COLUMN:
            return "Images"

        if section == self.SET_COLUMN:
            return "Set"

        return None

    def data(
        self,
        index: QModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if not index.isValid():
            return None

        row = self._data[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if column == self.NAME_COLUMN:
                return row["name"]

            if column == self.NUM_IMAGES_COLUMN:
                # Replace this with the actual number of images in
                # the group once you have grouped data.
                return row.get("num_images")

            if column == self.SET_COLUMN:
                return SET_LABELS[row["set"]]

        if role == self.SetRole and column == self.SET_COLUMN:
            return row["set"]

        return None

    def setData(
        self,
        index: QModelIndex,
        value,
        role: int = Qt.ItemDataRole.EditRole,
    ):
        if (
            not index.isValid()
            or index.column() != self.SET_COLUMN
            or role != Qt.ItemDataRole.EditRole
        ):
            return False

        row = self._data[index.row()]

        if row["set"] == value:
            return False

        row["set"] = value

        self.dataChanged.emit(
            index,
            index,
            [
                Qt.ItemDataRole.DisplayRole,
                self.SetRole,
            ],
        )

        self.group_assigned.emit(row["name"], value)

        return True

    def flags(self, index: QModelIndex):
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

        if index.column() == self.SET_COLUMN:
            flags |= Qt.ItemFlag.ItemIsEditable

        return flags


class SetComboBoxDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)

        combo.addItem("Unassigned", None)
        combo.addItem("Train", "train")
        combo.addItem("Val", "val")

        # Store the selected value immediately.
        combo.activated.connect(
            lambda: self.commitData.emit(combo)
        )

        # When editing starts because the user clicked the cell,
        # immediately display the popup.
        QTimer.singleShot(0, combo.showPopup)

        return combo

    def setEditorData(self, editor: QComboBox, index: QModelIndex):
        value = index.data(SetAssignmentTableModel.SetRole)

        combo_index = editor.findData(value)
        if combo_index >= 0:
            editor.setCurrentIndex(combo_index)

    def setModelData(
        self,
        editor: QComboBox,
        model: SetAssignmentTableModel,
        index: QModelIndex,
    ):
        model.setData(
            index,
            editor.currentData(),
            Qt.ItemDataRole.EditRole,
        )

    def paint(self, painter, option, index):
        combo_option = QStyleOptionComboBox()

        combo_option.rect = option.rect
        combo_option.currentText = (
            index.data(Qt.ItemDataRole.DisplayRole) or ""
        )
        combo_option.palette = option.palette
        combo_option.fontMetrics = option.fontMetrics
        combo_option.state = option.state
        combo_option.editable = False
        combo_option.frame = True

        style = (
            option.widget.style()
            if option.widget is not None
            else QApplication.style()
        )

        style.drawComplexControl(
            QStyle.ComplexControl.CC_ComboBox,
            combo_option,
            painter,
            option.widget,
        )

        style.drawControl(
            QStyle.ControlElement.CE_ComboBoxLabel,
            combo_option,
            painter,
            option.widget,
        )


class SetSplitModel(QObject):
    """Thin Qt adapter: forwards to a pure SetSplit and signals when it changes."""

    groups_changed = Signal()

    def __init__(self, images: List[ITaggedImage], config: SetSplitConfig):
        super().__init__()

        self._set_split = SetSplit(images, config)

    @property
    def config(self) -> SetSplitConfig:
        return self._set_split.config

    @property
    def grouping(self) -> Optional[str]:
        return self._set_split.grouping

    @property
    def groups(self) -> List[dict]:
        return self._set_split.groups

    @property
    def individuals(self) -> List[dict]:
        return self._set_split.individuals

    @property
    def num_groups(self):
        return self._set_split.num_groups

    @property
    def num_images(self):
        return self._set_split.num_images

    @property
    def num_train(self) -> int:
        return self._set_split.num_train

    @property
    def num_val(self) -> int:
        return self._set_split.num_val

    @property
    def num_unassigned(self) -> int:
        return self._set_split.num_unassigned

    @property
    def num_train_images(self) -> int:
        return self._set_split.num_train_images

    @property
    def num_val_images(self) -> int:
        return self._set_split.num_val_images

    @property
    def num_unassigned_images(self) -> int:
        return self._set_split.num_unassigned_images

    @property
    def min_ratio(self) -> float:
        return self._set_split.min_ratio

    @property
    def max_ratio(self) -> float:
        return self._set_split.max_ratio

    @property
    def auto_split_ratio(self) -> float:
        return self._set_split.auto_split_ratio

    @property
    def target_train(self) -> int:
        return self._set_split.target_train

    @property
    def target_val(self) -> float:
        return self._set_split.target_val

    def set_grouping(self, grouping: Optional[str]):
        self._set_split.set_grouping(grouping)
        self.groups_changed.emit()

    def set_auto_split_ratio(self, auto_split_ratio: float):
        self._set_split.set_auto_split_ratio(auto_split_ratio)

    def auto_split(self):
        self._set_split.auto_split()
        self.groups_changed.emit()

    def assign_group(self, group_name: str, set_name: str):
        self._set_split.assign_group(group_name, set_name)
        self.groups_changed.emit()

    def unassign_all(self):
        self._set_split.unassign_all()
        self.groups_changed.emit()


class SetSplitDialog(QDialog):
    def __init__(self, images: List[ITaggedImage], config: SetSplitConfig = None, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Set Split")

        self._model = SetSplitModel(images, config or SetSplitConfig())
        self._table_model = SetAssignmentTableModel()

        self._table_model.group_assigned.connect(self._model.assign_group)
        self._model.groups_changed.connect(self._groups_changed)

        layout = QVBoxLayout(self)

        grouping_layout = QFormLayout()
        self.dpd_grouping = QComboBox()
        self.dpd_grouping.addItem("Image", None)
        tags = list(set(tag for img in images for tag in img.tags.keys()))
        for tag in tags:
            self.dpd_grouping.addItem(tag, tag)
        self.dpd_grouping.setCurrentIndex(self.dpd_grouping.findData(self._model.grouping))
        self.dpd_grouping.activated.connect(self._grouping_changed)
        grouping_layout.addRow("Group by:", self.dpd_grouping)
        layout.addLayout(grouping_layout)

        frm_auto_split = QGroupBox("Auto Split")
        auto_split_layout = QVBoxLayout(frm_auto_split)

        slider_layout = QHBoxLayout()

        self.lbl_train = QLabel("Train 0 (0%)", frm_auto_split)
        self.lbl_train.setAlignment(Qt.AlignmentFlag.AlignLeft)
        slider_layout.addWidget(self.lbl_train)

        self.lbl_val = QLabel("Val 0 (0%)", frm_auto_split)
        self.lbl_val.setAlignment(Qt.AlignmentFlag.AlignRight)

        slider_layout.addWidget(self.lbl_val)

        auto_split_layout.addLayout(slider_layout)

        self.sld_train_ratio = QSlider(frm_auto_split)
        self.sld_train_ratio.setOrientation(Qt.Orientation.Horizontal)
        self.sld_train_ratio.setMinimum(0)
        self.sld_train_ratio.setMaximum(100)
        self.sld_train_ratio.setSingleStep(5)
        self.sld_train_ratio.setPageStep(5)
        self.sld_train_ratio.setTickInterval(5)
        self.sld_train_ratio.setValue(90)
        self.sld_train_ratio.valueChanged.connect(self._slider_moved)

        def _limit_user_action(action):
            pos = self.sld_train_ratio.sliderPosition()

            while int(self._model.num_groups * pos / 100) < self._model.num_train:
                pos += 1
            while self._model.num_groups - int(self._model.num_groups * pos / 100) < self._model.num_val:
                pos -= 1
            self.sld_train_ratio.setSliderPosition(pos)

        self.sld_train_ratio.actionTriggered.connect(_limit_user_action)

        auto_split_layout.addWidget(self.sld_train_ratio)

        self.lbl_fully_split = QLabel("All images are already assigned")
        self.lbl_fully_split.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_fully_split.setVisible(False)
        auto_split_layout.addWidget(self.lbl_fully_split)

        auto_split_buttons_layout = QHBoxLayout()

        self.btn_split_unassigned = QPushButton("Split Unassigned", self)
        self.btn_split_unassigned.clicked.connect(self._run_auto_split)
        auto_split_buttons_layout.addWidget(self.btn_split_unassigned)

        auto_split_layout.addLayout(auto_split_buttons_layout)

        layout.addWidget(frm_auto_split)

        self.tbl_groups = QTableView(self)
        self.tbl_groups.setModel(self._table_model)
        self.tbl_groups.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_groups.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tbl_groups.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_groups.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.tbl_groups.horizontalHeader().resizeSection(2, 120)

        self.tbl_groups.verticalHeader().setVisible(False)

        self.tbl_groups.setItemDelegateForColumn(SetAssignmentTableModel.SET_COLUMN, SetComboBoxDelegate(self.tbl_groups))

        self._table_model.modelReset.connect(
            lambda: self.tbl_groups.setColumnHidden(
                self._table_model.NUM_IMAGES_COLUMN,
                self._table_model.grouping is None,
            )
        )

        # Clicking an editable cell immediately starts editing.
        self.tbl_groups.clicked.connect(self._table_clicked)

        # Initially there is no grouping, so don't show the
        # "Images" column.
        self.tbl_groups.setColumnHidden(SetAssignmentTableModel.NUM_IMAGES_COLUMN, True)
        layout.addWidget(self.tbl_groups)

        self.btn_reset = QPushButton("Unassign All", self)
        self.btn_reset.clicked.connect(self._unassign_all)
        layout.addWidget(self.btn_reset)

        frm_stats = QGroupBox("Stats")
        stats_layout = QVBoxLayout(frm_stats)

        self.lbl_stats_total_images = QLabel("Total number of images: 0", frm_stats)
        stats_layout.addWidget(self.lbl_stats_total_images)

        lbl_stats_groups_per_set = QLabel("Number of images per set:", frm_stats)
        stats_layout.addWidget(lbl_stats_groups_per_set)

        stats_image_split_layout = QHBoxLayout()

        self.lbl_stats_images_train = QLabel("Train 0 (0%)", frm_stats)
        self.lbl_stats_images_train.setAlignment(Qt.AlignmentFlag.AlignLeft)
        stats_image_split_layout.addWidget(self.lbl_stats_images_train)

        self.lbl_stats_images_unassigned = QLabel("Unassigned 0 (0%)", frm_stats)
        self.lbl_stats_images_unassigned.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_image_split_layout.addWidget(self.lbl_stats_images_unassigned)

        self.lbl_stats_images_val = QLabel("Val 0 (0%)", frm_stats)
        self.lbl_stats_images_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        stats_image_split_layout.addWidget(self.lbl_stats_images_val)

        stats_layout.addLayout(stats_image_split_layout)

        layout.addWidget(frm_stats)

        self.dialog_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.dialog_buttons.accepted.connect(self.accept)
        self.dialog_buttons.rejected.connect(self.reject)
        layout.addWidget(self.dialog_buttons)

        self._groups_changed()

    def _groups_changed(self):
        self._update_slider()
        self._update_stats()
        self._table_model.set(self._model.grouping, self._model.groups)

    def _update_slider(self):
        if self._model.num_unassigned == 0:
            self.lbl_train.setVisible(False)
            self.lbl_val.setVisible(False)
            self.sld_train_ratio.setVisible(False)
            self.btn_split_unassigned.setVisible(False)
            self.lbl_fully_split.setVisible(True)
        else:
            self.lbl_train.setVisible(True)
            self.lbl_val.setVisible(True)
            self.sld_train_ratio.setVisible(True)
            self.btn_split_unassigned.setVisible(True)
            self.lbl_fully_split.setVisible(False)


        self.sld_train_ratio.setValue(int(self._model.auto_split_ratio * 100))
        self.lbl_train.setText(f"Train {self._model.target_train} ({self._model.auto_split_ratio * 100:.0f}%)")
        self.lbl_val.setText(f"Val {self._model.target_val} ({(1 - self._model.auto_split_ratio) * 100:.0f}%)")

    def _update_stats(self):
        self.lbl_stats_total_images.setText(f"Total number of images: {self._model.num_images}")

        train_percent = self._model.num_train_images/self._model.num_images * 100 if self._model.num_images > 0 else 0
        self.lbl_stats_images_train.setText(f"Train: {self._model.num_train_images} ({train_percent:.0f}%)")
        unassigned_percent = self._model.num_unassigned_images/self._model.num_images * 100 if self._model.num_images > 0 else 0
        self.lbl_stats_images_unassigned.setText(f"Unassigned: {self._model.num_unassigned_images} ({unassigned_percent:.0f}%)")
        val_percent = self._model.num_val_images/self._model.num_images * 100 if self._model.num_images > 0 else 0
        self.lbl_stats_images_val.setText(f"Val: {self._model.num_val_images} ({val_percent:.0f}%)")

    def _table_clicked(self, index: QModelIndex):
        if index.column() == SetAssignmentTableModel.SET_COLUMN:
            self.tbl_groups.edit(index)

    def _confirm_unassign_all(self, text: str):
        if self._model.num_train_images == 0 and self._model.num_val_images == 0:
            return True

        confirmation_dialog = QMessageBox()
        confirmation_dialog.setIcon(QMessageBox.Icon.Question)
        confirmation_dialog.setWindowTitle("Confirm unassign all")
        confirmation_dialog.setText(text)
        confirmation_dialog.setStandardButtons(QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Ok)

        res = confirmation_dialog.exec_()

        return res == QMessageBox.StandardButton.Ok

    def _grouping_changed(self):
        if not self._confirm_unassign_all("Changing the grouping will remove all set assignments. Do you want to continue?"):
            self.dpd_grouping.setCurrentIndex(self.dpd_grouping.findData(self._model.grouping))
            return

        self._set_grouping(self.dpd_grouping.currentData())

    def _set_grouping(self, grouping: Optional[str]):
        self._model.set_grouping(grouping)

    def _slider_moved(self):
        value = self.sld_train_ratio.value()
        split_ratio = value / 100
        self._set_split_ratio(split_ratio)

    def _set_split_ratio(self, value):
        self._model.set_auto_split_ratio(value)
        self._update_slider()

    def _run_auto_split(self):
        self._model.auto_split()

    def _unassign_all(self):
        if not self._confirm_unassign_all("Are you sure you want to remove all set assignments?"):
            self.dpd_grouping.setCurrentIndex(self.dpd_grouping.findData(self._model.grouping))
            return

        self._model.unassign_all()


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    @dataclass
    class TaggedImage:
        name: str
        tags: Mapping[str, str]


    images = [
        TaggedImage("video1_frame1.jpg", {"video": "video1", "animal": "a123"}),
        TaggedImage("video1_frame2.jpg", {"video": "video1", "animal": "a123"}),
        TaggedImage("video2_frame1.jpg", {"video": "video2", "animal": "a123"}),
        TaggedImage("video2_frame2.jpg", {"video": "video2", "animal": "a123"}),
        TaggedImage("video3_frame1.jpg", {"video": "video3", "animal": "a223"}),
        TaggedImage("video3_frame2.jpg", {"video": "video3", "animal": "a223"}),
        TaggedImage("video4_frame1.jpg", {"video": "video4", "animal": "a223"}),
        TaggedImage("video4_frame2.jpg", {"video": "video4", "animal": "a223"}),
        TaggedImage("img1.jpg", {}),
        TaggedImage("img2.jpg", {"animal": "a123"}),
    ]

    class MyButton(QPushButton):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.clicked.connect(self._open_split_dialog)

            self._config = None

        def _open_split_dialog(self):
            dialog = SetSplitDialog(images, self._config)
            dialog.exec()

            self._config = dialog._model.config
            print(self._config)

    app = QApplication(sys.argv)
    #dialog = SetSplitDialog(images)
    #dialog.show()

    main = MyButton("Test")

    main.show()



    sys.exit(app.exec_())
