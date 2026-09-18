from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence, Mapping, Optional, List, Set

import numpy as np
from PySide6.QtCore import Signal, QObject, Slot, QThread
from PySide6.QtGui import QIcon, Qt
from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QToolButton, QWidgetAction, QVBoxLayout, \
    QDialogButtonBox, QHBoxLayout, QLabel, QCheckBox, QProgressDialog, QMessageBox, QListWidget, QListWidgetItem, \
    QPushButton

from junip3r.common.tags.data import TagValue
from junip3r.labeller.config.data import InstanceType
from junip3r.labeller.data.types.abc import LabellerObjectType
from junip3r.labeller.data.types.data import Instance
from junip3r.labeller.export.yolo.conversion.mapping_instance_converter import \
    MappingYoloDatasetMetadataGenerator, MappingYoloDatasetGenerator, MappingYoloPoseInstanceConverter
from junip3r.labeller.export.yolo.data import YoloDatasetConfig, YoloPoseInstanceTypeConfig
from junip3r.labeller.export.yolo.serialization.yolo_dataset_metadata_writer import YoloPoseDatasetMetadataWriter
from junip3r.labeller.export.yolo.serialization.yolo_dataset_writer import YoloDatasetWriter
from junip3r.labeller.export.yolo.serialization.set_split_writer import SetSplitWriter
from junip3r.labeller.export.yolo.set_split import SetSplitConfig, SetSplit, ISetSplitRepository, resolve_set_assignments
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

    def __init__(self, model: IReadOnlyAppModel, set_split_repository: ISetSplitRepository, parent=None):
        super().__init__(parent)

        self._model = model
        self._set_split_repository = set_split_repository
        self._set_split_config: SetSplitConfig = self._set_split_repository.get()
        self._progress_dialog: Optional[QProgressDialog] = None
        self._current_job: Optional[ExportJob] = None

        layout = QVBoxLayout(self)

        form_layout = QFormLayout(self)
        self.txt_location = QLineEdit()
        self.txt_location.setText("")

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
        self.chk_include_empty.toggled.connect(self._update_set_split_labels)
        form_layout.addRow("", self.chk_include_empty)

        layout.addLayout(form_layout)

        set_split_layout = QHBoxLayout()

        self.lbl_images_train = QLabel("Train 0 (0%)")
        self.lbl_images_train.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        set_split_layout.addWidget(self.lbl_images_train)

        self.lbl_images_val = QLabel("Val 0 (0%)")
        self.lbl_images_val.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        set_split_layout.addWidget(self.lbl_images_val)

        self.lbl_images_unassigned = QLabel("Unassigned 0 (0%)")
        self.lbl_images_unassigned.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_images_unassigned.setStyleSheet("color: orange;")
        set_split_layout.addWidget(self.lbl_images_unassigned)

        self.btn_set_split = QToolButton()
        self.btn_set_split.setIcon(QIcon.fromTheme("document-properties"))
        self.btn_set_split.clicked.connect(self._configure_set_split)
        set_split_layout.addWidget(self.btn_set_split)

        form_layout.addRow("Set Split:", set_split_layout)

        self.lst_instance_types = QListWidget()
        for instance_type in self._model.get_instance_types(0):
            item = QListWidgetItem(instance_type.name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, instance_type)
            self.lst_instance_types.addItem(item)
        self.lst_instance_types.itemChanged.connect(self._update_set_split_labels)
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

        self._update_set_split_labels()

    def done(self, result):
        # accept()/reject()/close() all route through here - the single place to make
        # sure the worker thread is stopped no matter how the dialog concludes.
        self._export_worker_thread.quit()
        self._export_worker_thread.wait()
        super().done(result)

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
            self.txt_location.setText(folder)

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

    def _configure_set_split(self):
        dialog = SetSplitDialog(self._tagged_images(), self._set_split_config, parent=self)
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            self._set_split_config = dialog._model.config
            self._set_split_repository.set(self._set_split_config)
            self._update_set_split_labels()

    def _update_set_split_labels(self):
        split = SetSplit(self._tagged_images(), self._set_split_config)
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

        class_names = []
        instance_types = {}
        for instance_index, instance_type in enumerate(selected_instance_types):
            class_names.append(instance_type.name)

            bounding_box_member = next(
                (member for member in instance_type.members if member.type == LabellerObjectType.BOUNDING_BOX),
                None,
            )
            bounding_box_name = bounding_box_member.name if bounding_box_member is not None else None

            keypoint_mapping = {}
            keypoint_members = (member for member in instance_type.members if member.type == LabellerObjectType.KEYPOINT)
            for keypoint_index, keypoint in enumerate(keypoint_members):
                keypoint_mapping[keypoint.name] = keypoint_index

            instance_types[instance_type.name] = YoloPoseInstanceTypeConfig(instance_index, bounding_box_name, keypoint_mapping)

        dataset_config = YoloDatasetConfig(
            class_names=class_names,
            instance_types=instance_types,
        )

        set_assignments = resolve_set_assignments(self._tagged_images(), self._set_split_config)
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
            self._set_split_config,
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
