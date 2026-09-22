from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence, Mapping, Optional, List, Set, Tuple
from uuid import uuid4

import numpy as np
from PySide6.QtCore import Signal, QObject, Slot, QThread
from PySide6.QtGui import QIcon, Qt
from PySide6.QtWidgets import QComboBox, QDialog, QFormLayout, QLineEdit, QToolButton, QWidgetAction, QVBoxLayout, \
    QDialogButtonBox, QHBoxLayout, QLabel, QCheckBox, QProgressDialog, QMessageBox, QListWidget, QListWidgetItem, \
    QPushButton

from junip3r.common.tags.data import TagValue
from junip3r.labeller.config.data import InstanceType
from junip3r.labeller.data.types.data import Instance
from junip3r.labeller.export.yolo.conversion.mapping_instance_converter import \
    MappingYoloDatasetMetadataGenerator, MappingYoloDatasetGenerator, MappingYoloPoseInstanceConverter, \
    build_instance_type_mapping
from junip3r.labeller.export.yolo.data import ExportMode, YoloDatasetConfig
from junip3r.labeller.export.yolo.export_profile import ExportProfile, IExportProfileRepository
from junip3r.labeller.export.yolo.serialization.yolo_dataset_metadata_writer import YoloPoseDatasetMetadataWriter
from junip3r.labeller.export.yolo.serialization.yolo_dataset_writer import YoloDatasetWriter
from junip3r.labeller.export.yolo.serialization.set_split_writer import SetSplitWriter
from junip3r.labeller.export.yolo.set_split import SetSplitConfig, SetSplit, ISetSplitRepository, NamedSetSplit, \
    resolve_set_assignments
from junip3r.labeller.export.yolo.widgets.manage_items_dialog import ManageItemsDialog, NamedItem
from junip3r.labeller.export.yolo.widgets.named_item_combo_box import NamedItemComboBox
from junip3r.labeller.export.yolo.widgets.set_split_dialog import SetSplitDialog
from junip3r.labeller.model.abc import IReadOnlyAppModel
from junip3r.labeller.yolo.labels.data import YoloBoxInstance


@dataclass
class AppModelYoloImage:
    """A YoloImage with no backing file, whose pixels are loaded from a model on demand.

    Used when the underlying image repository is (fully or partially) in-memory and
    `get_image_file` returns `None` for it.
    """
    app_model: IReadOnlyAppModel
    image_index: int
    name: str
    instances: Sequence[YoloBoxInstance]

    @property
    def image(self) -> Optional[np.ndarray]:
        return self.app_model.get_image(self.image_index)

    @property
    def source_file(self) -> Optional[Path]:
        return self.app_model.get_image_file(self.image_index)


@dataclass
class ExportJob:
    target_folder: Path
    config: YoloDatasetConfig
    instance_types: Sequence[InstanceType]
    set_split_config: SetSplitConfig
    model: IReadOnlyAppModel
    instance_filter: Callable[[Instance], bool]
    image_filter: Callable[[Sequence[Instance]], bool]
    set_mapper: Callable[[str], Optional[str]]
    canceled: bool = False

    def cancel(self):
        self.canceled = True


@dataclass
class TaggedImage:
    name: str
    tags: Mapping[str, TagValue]


class ExportWorker(QObject):
    progress_max_changed = Signal(int)
    progress_value_changed = Signal(int)
    finished = Signal()
    canceled = Signal()
    failed = Signal(str)

    @Slot(object)
    def run(self, job: ExportJob):
        try:
            instance_converter = MappingYoloPoseInstanceConverter(job.config)
            dataset_generator = MappingYoloDatasetGenerator(job.config)
            metadata_generator = MappingYoloDatasetMetadataGenerator(job.config)

            yolo_images = []
            for image_index in range(job.model.get_num_images()):
                image_name = job.model.get_image_name(image_index)
                set_name = job.set_mapper(image_name)
                if set_name is None:
                    continue

                instances = [i for i in job.model.get_instances(image_index) if job.instance_filter(i)]
                if not job.image_filter(instances):
                    continue

                yolo_instances = instance_converter.convert(instances)
                yolo_images.append((set_name, AppModelYoloImage(job.model, image_index, image_name, yolo_instances)))

            dataset = dataset_generator.generate(yolo_images)
            metadata = metadata_generator.generate(job.instance_types)

            dataset_writer = YoloDatasetWriter()
            for completed, total in dataset_writer.write(job.target_folder, dataset):
                self.progress_max_changed.emit(total)
                self.progress_value_changed.emit(completed)
                if job.canceled:
                    break

            dataset_metadata_writer = YoloPoseDatasetMetadataWriter()
            dataset_metadata_writer.write(job.target_folder, metadata)

            set_split_writer = SetSplitWriter()
            set_split_writer.write(job.target_folder, job.set_split_config)

            if job.canceled:
                self.canceled.emit()
            else:
                self.finished.emit()
        except Exception as e:
            self.failed.emit(str(e))
            raise


class YoloExportDialog(QDialog):
    run_export = Signal(object)

    def __init__(self, model: IReadOnlyAppModel, set_split_repository: ISetSplitRepository,
                 export_profile_repository: IExportProfileRepository, parent=None):
        super().__init__(parent)

        self._model = model
        self._set_split_repository = set_split_repository
        self._export_profile_repository = export_profile_repository
        self._current_profile_id: str = ""
        self._progress_dialog: Optional[QProgressDialog] = None
        self._current_job: Optional[ExportJob] = None

        self.setWindowTitle("Export YOLO Dataset")

        self._seed_defaults_if_needed()

        layout = QVBoxLayout(self)

        form_layout = QFormLayout(self)

        self.cmb_profile = NamedItemComboBox(item_label="Profile")
        self.cmb_profile.currentIndexChanged.connect(self._on_profile_combo_changed)
        self.cmb_profile.manage_requested.connect(self._manage_profiles)
        form_layout.addRow("Export Profile:", self.cmb_profile)

        self.cmb_mode = QComboBox()
        self.cmb_mode.addItem("Pose", ExportMode.POSE)
        self.cmb_mode.addItem("Detect", ExportMode.DETECT)
        self.cmb_mode.currentIndexChanged.connect(self._on_mode_changed)
        form_layout.addRow("Mode:", self.cmb_mode)

        self.txt_location = QLineEdit()
        self.txt_location.setText("")
        self.txt_location.editingFinished.connect(self._on_target_folder_edited)

        self.btn_select_folder = QToolButton()
        self.btn_select_folder.setIcon(QIcon.fromTheme("folder"))
        self.btn_select_folder.setToolTip("Select dataset folder")
        self.btn_select_folder.setAutoRaise(True)
        self.btn_select_folder.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_select_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_folder.clicked.connect(self._select_folder)

        self.act_select_folder = QWidgetAction(self.txt_location)
        self.act_select_folder.setDefaultWidget(self.btn_select_folder)

        self.txt_location.addAction(
            self.act_select_folder,
            QLineEdit.ActionPosition.TrailingPosition,
        )

        form_layout.addRow("Target Folder:", self.txt_location)

        self.chk_include_empty = QCheckBox("Include empty images (no instances)")
        self.chk_include_empty.setChecked(False)
        self.chk_include_empty.toggled.connect(self._on_include_empty_toggled)
        form_layout.addRow("", self.chk_include_empty)

        layout.addLayout(form_layout)

        set_split_layout = QHBoxLayout()

        self.cmb_set_split = NamedItemComboBox(item_label="Set Split")
        self.cmb_set_split.currentIndexChanged.connect(self._on_split_combo_changed)
        self.cmb_set_split.manage_requested.connect(self._manage_splits)
        set_split_layout.addWidget(self.cmb_set_split)

        self.btn_set_split = QToolButton()
        self.btn_set_split.setIcon(QIcon.fromTheme("document-properties"))
        self.btn_set_split.setToolTip("Configure the selected set split's content")
        self.btn_set_split.clicked.connect(self._configure_set_split)
        set_split_layout.addWidget(self.btn_set_split)

        form_layout.addRow("Set Split:", set_split_layout)

        stats_layout = QHBoxLayout()

        self.lbl_images_train = QLabel("Train 0 (0%)")
        self.lbl_images_train.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        stats_layout.addWidget(self.lbl_images_train)

        self.lbl_images_val = QLabel("Val 0 (0%)")
        self.lbl_images_val.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        stats_layout.addWidget(self.lbl_images_val)

        self.lbl_images_unassigned = QLabel("Unassigned 0 (0%)")
        self.lbl_images_unassigned.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_images_unassigned.setStyleSheet("color: orange;")
        stats_layout.addWidget(self.lbl_images_unassigned)

        form_layout.addRow("", stats_layout)

        self.lst_instance_types = QListWidget()
        for instance_type in self._model.get_instance_types(0):
            item = QListWidgetItem(instance_type.name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, instance_type)
            self.lst_instance_types.addItem(item)
        self.lst_instance_types.itemChanged.connect(self._on_instance_types_changed)
        form_layout.addRow("Instance Types:", self.lst_instance_types)

        self.btn_export = QPushButton("Export")
        self.btn_export.setAutoDefault(False)
        self.btn_export.setDefault(False)
        self.btn_export.clicked.connect(self._run_export)

        button_row = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_row.addButton(self.btn_export, QDialogButtonBox.ButtonRole.ActionRole)
        button_row.rejected.connect(self.reject)

        btn_close = button_row.button(QDialogButtonBox.StandardButton.Close)
        btn_close.setAutoDefault(False)
        btn_close.setDefault(False)

        layout.addWidget(button_row)

        self._export_worker = ExportWorker()
        self._export_worker_thread = QThread(self)
        self._export_worker.moveToThread(self._export_worker_thread)
        self._export_worker_thread.start()

        self.run_export.connect(self._export_worker.run)

        self._load_current_profile_into_widgets()

    def done(self, result):
        # accept()/reject()/close() all route through here - the single place to make
        # sure the worker thread is stopped no matter how the dialog concludes.
        self._export_worker_thread.quit()
        self._export_worker_thread.wait()
        super().done(result)

    # --- seeding / current profile & split -----------------------------------------

    def _seed_defaults_if_needed(self):
        splits = self._set_split_repository.list()
        if not splits:
            default_split = NamedSetSplit(id=str(uuid4()), name="Default", config=SetSplitConfig())
            self._set_split_repository.set(default_split)
            splits = [default_split]
        default_split_id = splits[0].id

        profiles = self._export_profile_repository.list()
        if not profiles:
            # Matches today's actual default behaviour: every instance type starts
            # checked, no target folder, "include empty" unchecked, pose mode.
            all_instance_type_names = [it.name for it in self._model.get_instance_types(0)]
            default_profile = ExportProfile(
                id=str(uuid4()), name="Default",
                instance_type_names=all_instance_type_names,
                set_split_id=default_split_id,
                mode=ExportMode.POSE,
            )
            self._export_profile_repository.set(default_profile)
            profiles = [default_profile]

        self._current_profile_id = profiles[0].id

    def _current_profile(self) -> ExportProfile:
        profile = self._export_profile_repository.get(self._current_profile_id)
        assert profile is not None, "current_profile_id should always resolve - seeded in _seed_defaults_if_needed"
        return profile

    def _current_split(self) -> NamedSetSplit:
        named_split = self._set_split_repository.get(self._current_profile().set_split_id)
        assert named_split is not None, "profile.set_split_id should always resolve (see _manage_splits' on_delete)"
        return named_split

    def _load_current_profile_into_widgets(self):
        profile = self._current_profile()

        self.cmb_profile.set_items(
            [(p.id, p.name) for p in self._export_profile_repository.list()], self._current_profile_id)

        self.cmb_mode.blockSignals(True)
        self.cmb_mode.setCurrentIndex(self.cmb_mode.findData(profile.mode))
        self.cmb_mode.blockSignals(False)

        self.txt_location.setText(profile.target_folder)

        self.chk_include_empty.blockSignals(True)
        self.chk_include_empty.setChecked(profile.include_empty_images)
        self.chk_include_empty.blockSignals(False)

        self.lst_instance_types.blockSignals(True)
        for i in range(self.lst_instance_types.count()):
            item = self.lst_instance_types.item(i)
            instance_type = item.data(Qt.ItemDataRole.UserRole)
            checked = instance_type.name in profile.instance_type_names
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self.lst_instance_types.blockSignals(False)

        self.cmb_set_split.set_items(self._split_combo_items(), profile.set_split_id)

        self._update_set_split_labels()

    def _split_combo_items(self) -> List[Tuple[str, str]]:
        # The "(used by N profiles)" annotation is computed here, by the dialog that
        # already knows what a "profile" is - NamedItemComboBox just renders whatever
        # display text it's given, it has no notion of "usage" at all.
        profiles = self._export_profile_repository.list()
        items = []
        for named_split in self._set_split_repository.list():
            count = sum(1 for p in profiles if p.set_split_id == named_split.id)
            label = f"{named_split.name}  (used by {count} profiles)" if count > 1 else named_split.name
            items.append((named_split.id, label))
        return items

    # --- export profile: selection / management ------------------------------------

    def _on_profile_combo_changed(self, index: int):
        profile_id = self.cmb_profile.itemData(index)
        if profile_id is None:
            return  # transient sentinel selection mid-revert (see NamedItemComboBox) - ignore
        self._current_profile_id = profile_id
        self._load_current_profile_into_widgets()

    def _manage_profiles(self):
        dialog = ManageItemsDialog("Profile", parent=self)

        def refresh_dialog():
            dialog.set_items([NamedItem(p.id, p.name) for p in self._export_profile_repository.list()])

        def on_create(name: str):
            new_profile = self._create_blank_profile(name)
            refresh_dialog()
            dialog.select_item(new_profile.id)

        def on_duplicate(source_id: str, name: str):
            new_profile = self._duplicate_profile(source_id, name)
            refresh_dialog()
            dialog.select_item(new_profile.id)

        def on_rename(profile_id: str, name: str):
            profile = self._export_profile_repository.get(profile_id)
            if profile is not None:
                profile.name = name
                self._export_profile_repository.set(profile)
            refresh_dialog()

        def on_delete(profile_id: str):
            self._export_profile_repository.delete(profile_id)
            refresh_dialog()

        dialog.create_requested.connect(on_create)
        dialog.duplicate_requested.connect(on_duplicate)
        dialog.rename_requested.connect(on_rename)
        dialog.delete_requested.connect(on_delete)

        refresh_dialog()
        dialog.select_item(self._current_profile_id)
        dialog.exec_()

        selected_id = dialog.selected_id()
        if selected_id is not None:
            self._current_profile_id = selected_id
        self._load_current_profile_into_widgets()

    def _create_blank_profile(self, name: str) -> ExportProfile:
        # "New" starts fresh (default instance-type selection, no target folder) -
        # distinct from "Duplicate", which copies the source profile's settings.
        # Points at the first existing set split rather than spawning a new one, so
        # "New Profile" doesn't quietly grow the set-split list every time it's used.
        all_instance_type_names = [it.name for it in self._model.get_instance_types(0)]
        default_split_id = self._set_split_repository.list()[0].id
        new_profile = ExportProfile(
            id=str(uuid4()), name=name,
            instance_type_names=all_instance_type_names,
            set_split_id=default_split_id,
            mode=ExportMode.POSE,
        )
        self._export_profile_repository.set(new_profile)
        return new_profile

    def _duplicate_profile(self, source_id: str, name: str) -> ExportProfile:
        source = self._export_profile_repository.get(source_id)
        assert source is not None
        new_profile = ExportProfile(
            id=str(uuid4()), name=name,
            instance_type_names=list(source.instance_type_names),
            set_split_id=source.set_split_id,  # shared by reference, not duplicated
            target_folder=source.target_folder,
            include_empty_images=source.include_empty_images,
            mode=source.mode,
        )
        self._export_profile_repository.set(new_profile)
        return new_profile

    # --- named set split: selection / management ------------------------------------

    def _on_split_combo_changed(self, index: int):
        split_id = self.cmb_set_split.itemData(index)
        if split_id is None:
            return  # transient sentinel selection mid-revert - ignore
        profile = self._current_profile()
        profile.set_split_id = split_id
        self._export_profile_repository.set(profile)
        self._load_current_profile_into_widgets()

    def _manage_splits(self):
        dialog = ManageItemsDialog("Set Split", parent=self)

        def refresh_dialog():
            dialog.set_items([NamedItem(s.id, s.name) for s in self._set_split_repository.list()])

        def on_create(name: str):
            new_split = self._create_blank_split(name)
            refresh_dialog()
            dialog.select_item(new_split.id)

        def on_duplicate(source_id: str, name: str):
            new_split = self._duplicate_split(source_id, name)
            refresh_dialog()
            dialog.select_item(new_split.id)

        def on_rename(split_id: str, name: str):
            named_split = self._set_split_repository.get(split_id)
            if named_split is not None:
                named_split.name = name
                self._set_split_repository.set(named_split)
            refresh_dialog()

        def on_delete(split_id: str):
            # Re-point every profile that shared this split, not just the currently
            # active one - ManageItemsDialog already disables Delete at 1 remaining
            # item, so a fallback always exists.
            fallback_id = next(s.id for s in self._set_split_repository.list() if s.id != split_id)
            self._set_split_repository.delete(split_id)
            for profile in self._export_profile_repository.list():
                if profile.set_split_id == split_id:
                    profile.set_split_id = fallback_id
                    self._export_profile_repository.set(profile)
            refresh_dialog()

        dialog.create_requested.connect(on_create)
        dialog.duplicate_requested.connect(on_duplicate)
        dialog.rename_requested.connect(on_rename)
        dialog.delete_requested.connect(on_delete)

        refresh_dialog()
        dialog.select_item(self._current_profile().set_split_id)
        dialog.exec_()

        selected_id = dialog.selected_id()
        if selected_id is not None:
            profile = self._current_profile()
            profile.set_split_id = selected_id
            self._export_profile_repository.set(profile)
        self._load_current_profile_into_widgets()

    def _create_blank_split(self, name: str) -> NamedSetSplit:
        # "New" starts fresh (no grouping/assignments) - distinct from "Duplicate",
        # which copies the source split's content.
        new_split = NamedSetSplit(id=str(uuid4()), name=name, config=SetSplitConfig())
        self._set_split_repository.set(new_split)
        return new_split

    def _duplicate_split(self, source_id: str, name: str) -> NamedSetSplit:
        source = self._set_split_repository.get(source_id)
        assert source is not None
        new_split = NamedSetSplit(
            id=str(uuid4()), name=name,
            config=SetSplitConfig(
                grouping=source.config.grouping,
                group_sets=dict(source.config.group_sets),
                individual_sets=dict(source.config.individual_sets),
                auto_split_ratio=source.config.auto_split_ratio,
            ),
        )
        self._set_split_repository.set(new_split)
        return new_split

    def _configure_set_split(self):
        named_split = self._current_split()
        dialog = SetSplitDialog(self._tagged_images(), named_split.config, parent=self)
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            updated = NamedSetSplit(id=named_split.id, name=named_split.name, config=dialog._model.config)
            self._set_split_repository.set(updated)
            self._load_current_profile_into_widgets()

    # --- current profile's other fields ---------------------------------------------

    def _select_folder(self):
        from PySide6.QtWidgets import QFileDialog

        current_folder = Path(self.txt_location.text())
        while not current_folder.exists():
            current_folder = current_folder.parent
            if current_folder == current_folder.parent:
                current_folder = Path.home()
                break

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Target Dataset Folder",
            str(current_folder),
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )
        if folder:
            # setText() doesn't itself emit editingFinished, so persist explicitly.
            self.txt_location.setText(folder)
            self._on_target_folder_edited()

    def _on_target_folder_edited(self):
        profile = self._current_profile()
        profile.target_folder = self.txt_location.text()
        self._export_profile_repository.set(profile)

    def _on_mode_changed(self, index: int):
        profile = self._current_profile()
        profile.mode = self.cmb_mode.itemData(index)
        self._export_profile_repository.set(profile)

    def _on_include_empty_toggled(self, checked: bool):
        profile = self._current_profile()
        profile.include_empty_images = checked
        self._export_profile_repository.set(profile)
        self._update_set_split_labels()

    def _on_instance_types_changed(self):
        selected_names = []
        for i in range(self.lst_instance_types.count()):
            item = self.lst_instance_types.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                instance_type = item.data(Qt.ItemDataRole.UserRole)
                selected_names.append(instance_type.name)

        profile = self._current_profile()
        profile.instance_type_names = selected_names
        self._export_profile_repository.set(profile)
        self._update_set_split_labels()

    # --- image selection / stats / export -------------------------------------------

    def _selected_instance_types(self) -> List[InstanceType]:
        selected = []
        for i in range(self.lst_instance_types.count()):
            item = self.lst_instance_types.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.data(Qt.ItemDataRole.UserRole))
        return selected

    def _selected_instance_type_names(self) -> Set[str]:
        return {instance_type.name for instance_type in self._selected_instance_types()}

    def _filtered_instances(self, image_index: int, selected_names: Set[str]) -> List[Instance]:
        return [
            instance for instance in self._model.get_instances(image_index)
            if instance.instance_type.name in selected_names
        ]

    def _included_image_indices(self) -> List[int]:
        indices = range(self._model.get_num_images())
        if self.chk_include_empty.isChecked():
            return list(indices)

        selected_names = self._selected_instance_type_names()
        return [
            image_index for image_index in indices
            if self._filtered_instances(image_index, selected_names)
        ]

    def _tagged_images(self) -> List[TaggedImage]:
        images = []
        for image_index in self._included_image_indices():
            image_name = self._model.get_image_name(image_index)
            images.append(TaggedImage(image_name, self._model.get_tags(image_index)))
        return images

    def _update_set_split_labels(self):
        split = SetSplit(self._tagged_images(), self._current_split().config)
        num_images = split.num_images

        train_percent = split.num_train_images / num_images * 100 if num_images > 0 else 0
        val_percent = split.num_val_images / num_images * 100 if num_images > 0 else 0
        unassigned_percent = split.num_unassigned_images / num_images * 100 if num_images > 0 else 0

        self.lbl_images_train.setText(f"Train {split.num_train_images} ({train_percent:.0f}%)")
        self.lbl_images_val.setText(f"Val {split.num_val_images} ({val_percent:.0f}%)")
        self.lbl_images_unassigned.setText(f"Unassigned {split.num_unassigned_images} ({unassigned_percent:.0f}%)")

        if split.num_unassigned_images > 0:
            self.lbl_images_unassigned.setStyleSheet("color: orange;")
        else:
            self.lbl_images_unassigned.setStyleSheet("")

    def _confirm_target_folder(self, target_folder: Path) -> bool:
        """Refuse a folder that looks like a Junip3R project outright; warn on any other non-empty folder.

        Picking the current project folder by mistake is an easy slip when prompted for a
        target folder, and it's a destructive one: the writer removes and recreates
        `<target>/images/<set>` and `<target>/labels/<set>` for every configured set, which
        collide with a project's own images/labels folders. There's no legitimate reason to
        export a dataset into the project it was labelled in, so this case is a hard block
        rather than a dismissable confirmation - export elsewhere and copy files over manually
        if you actually need them inside the project folder.
        """
        if not target_folder.exists() or not any(target_folder.iterdir()):
            return True

        if (target_folder / "config.yaml").exists():
            QMessageBox.critical(
                self,
                "Cannot Export Into a Junip3R Project",
                f"'{target_folder}' looks like a Junip3R project - it contains a config.yaml file.\n\n"
                "Exporting a YOLO dataset here would overwrite or delete files in its images/ and "
                "labels/ folders, permanently destroying your labelled data, so this isn't allowed.\n\n"
                "Choose a different target folder. If you need the dataset inside this project, "
                "export it elsewhere first and copy the files over manually.",
            )
            return False

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Target Folder Is Not Empty")
        box.setText(
            f"'{target_folder}' is not empty.\n\n"
            "Exporting the YOLO dataset here may overwrite or delete existing files in it."
        )
        export_button = box.addButton("Export Anyway", QMessageBox.ButtonRole.DestructiveRole)
        cancel_button = box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(cancel_button)
        box.exec_()
        return box.clickedButton() is export_button

    def _run_export(self):
        target_folder = Path(self.txt_location.text())

        selected_instance_types = self._selected_instance_types()
        if not selected_instance_types:
            QMessageBox.warning(
                self,
                "Nothing to Export",
                "No instance types are selected. Select at least one instance type before exporting.",
            )
            return

        mode = self._current_profile().mode

        class_names = []
        instance_types = {}
        for instance_index, instance_type in enumerate(selected_instance_types):
            class_names.append(instance_type.name)
            instance_types[instance_type.name] = build_instance_type_mapping(instance_type, instance_index, mode)

        dataset_config = YoloDatasetConfig(
            class_names=class_names,
            instance_types=instance_types,
        )

        set_split_config = self._current_split().config
        set_assignments = resolve_set_assignments(self._tagged_images(), set_split_config)
        if not set_assignments:
            QMessageBox.warning(
                self,
                "Nothing to Export",
                "No images are assigned to a set. Configure the set split before exporting.",
            )
            return

        if not self._confirm_target_folder(target_folder):
            return

        selected_names = self._selected_instance_type_names()
        include_empty = self.chk_include_empty.isChecked()

        job = ExportJob(
            target_folder,
            dataset_config,
            selected_instance_types,
            set_split_config,
            self._model,
            instance_filter=lambda instance: instance.instance_type.name in selected_names,
            image_filter=(lambda instances: True) if include_empty else (lambda instances: bool(instances)),
            set_mapper=set_assignments.get,
        )
        self._current_job = job
        self._show_export_progress()
        self.run_export.emit(job)

    def _show_export_progress(self):
        worker = self._export_worker

        progress_dialog = QProgressDialog("Exporting...", "Cancel", 0, 0, self)
        progress_dialog.setWindowTitle("Exporting YOLO Dataset")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.canceled.connect(self._cancel_export)

        self._progress_dialog = progress_dialog

        # Bound Qt slots on self (a QObject with real thread affinity) so AutoConnection
        # correctly queues these onto this (GUI) thread, since worker lives on another one.
        worker.progress_max_changed.connect(progress_dialog.setMaximum)
        worker.progress_value_changed.connect(progress_dialog.setValue)
        worker.finished.connect(self._on_export_finished)
        worker.failed.connect(self._on_export_failed)
        worker.canceled.connect(self._on_export_canceled)

        progress_dialog.show()

    def _cleanup_export_progress(self):
        worker = self._export_worker
        progress_dialog = self._progress_dialog

        worker.progress_max_changed.disconnect(progress_dialog.setMaximum)
        worker.progress_value_changed.disconnect(progress_dialog.setValue)
        worker.finished.disconnect(self._on_export_finished)
        worker.failed.disconnect(self._on_export_failed)
        worker.canceled.disconnect(self._on_export_canceled)

        progress_dialog.deleteLater()
        self._progress_dialog = None
        self._current_job = None

    @Slot()
    def _cancel_export(self):
        if self._current_job is not None:
            self._current_job.cancel()

    @Slot()
    def _on_export_finished(self):
        self._cleanup_export_progress()

    @Slot(str)
    def _on_export_failed(self, message: str):
        self._cleanup_export_progress()
        QMessageBox.critical(self, "Export Failed", message)

    @Slot()
    def _on_export_canceled(self):
        self._cleanup_export_progress()
