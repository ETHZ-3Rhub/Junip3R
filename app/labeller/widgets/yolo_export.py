import random
import shutil
from pathlib import Path
from typing import Optional, List, Set, Dict, Tuple

import cv2
import yaml
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFileDialog, QDialogButtonBox, QMessageBox, QListWidgetItem

from app.labeller.data.app_model import AppModel
from app.labeller.data.types.abc import IInstanceType, IInstance
from app.labeller.layout.yolo_export import Ui_DYOLOExport


class YoloLabelWriter:
    def __init__(self, instance_types: List[IInstanceType]):
        self._max_num_points = max((len(it.keypoints) for it in instance_types), default=0)

        self._instance_type_map = {instance_type.name: class_index for class_index, instance_type in enumerate(instance_types)}
        self._reverse_instance_type_map = {class_index: instance_type.name for class_index, instance_type in enumerate(instance_types)}

    def save_instances(self, instances: List[IInstance], label_file: Path):
        import csv

        if len(instances) == 0:
            if label_file.exists():
                label_file.unlink()
            return

        with open(label_file, "w", newline='') as file:
            csv_writer = csv.writer(file, delimiter=" ")
            for instance in instances:
                instance_type_name, instance_name, bounding_box, points = instance.type.name, instance.name, instance.box, instance.keypoints

                class_index = self._instance_type_map[instance_type_name]

                (min_x, min_y), (max_x, max_y) = bounding_box.box

                min_x = min(min_x, max_x)
                min_y = min(min_y, max_y)
                max_x = max(min_x, max_x)
                max_y = max(min_y, max_y)

                cx = (min_x + max_x) / 2.0
                cy = (min_y + max_y) / 2.0
                w = max_x - min_x
                h = max_y - min_y

                point_coordinates = []
                for point_index in range(self._max_num_points):
                    if len(points) <= point_index or points[point_index] is None or points[point_index].p is None:
                        point_coordinates.extend([0., 0., 0.])
                    else:
                        point = points[point_index]
                        point_coordinates.extend([point.p[0], point.p[1], point.visibility])

                csv_writer.writerow([class_index, cx, cy, w, h] + point_coordinates)


class YoloExport(Ui_DYOLOExport, QDialog):
    def __init__(self, model: AppModel, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.model = model
        self.instance_types = self.model.get_instance_types(0)

        for instance_type in self.instance_types:
            item = QListWidgetItem(instance_type.name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.lst_instance_types.addItem(item)

        self.video_names: Set[str] = set()
        self.image_names: Set[str] = set()

        for image_index in range(self.model.get_num_images()):
            image_instances = self.model.get_instances(image_index)
            if not image_instances:
                continue

            image_name = self.model.get_image_name(image_index)

            video_name = image_name.rsplit("_", maxsplit=1)[0]
            self.video_names.add(video_name)
            self.image_names.add(image_name)

        self.target_folder: Optional[Path] = None
        self.split_file: Optional[Path] = None
        self.split_type: str = "Video"

        self.existing_set_mapping = {}
        self.additional_set_mapping = {}

        self.train_split = int(0.9 * len(self.unassigned_items))

        self.btnbox.button(QDialogButtonBox.StandardButton.Save).setText("Export")

        self.lbl_already_split.setVisible(False)

        self.sld_split.setMinimum(0)
        self.sld_split.setMaximum(len(self.unassigned_items))
        self.sld_split.setValue(self.train_split)

        self.btn_select_target_folder.clicked.connect(self.select_target_folder)
        self.btn_select_split_file.clicked.connect(self.select_set_split_file)
        self.dpd_split_by.currentTextChanged.connect(self.split_type_changed)
        self.sld_split.valueChanged.connect(self.split_changed)

        self._update_slider_labels()

    @property
    def items(self):
        if self.split_type == "Video":
            return self.video_names
        else:
            return self.image_names

    @property
    def unassigned_items(self):
        return self.items - set(self.existing_set_mapping.keys())

    @property
    def set_mapping(self):
        return self.existing_set_mapping | self.additional_set_mapping

    @property
    def selected_instance_types(self):
        checked_items = {
            self.lst_instance_types.item(i).text()
            for i in range(self.lst_instance_types.count())
            if self.lst_instance_types.item(i).checkState() == Qt.CheckState.Checked
        }
        return [it for it in self.instance_types if it.name in checked_items]

    def select_target_folder(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        if dialog.exec():
            selected_folder = dialog.selectedFiles()[0]
            self._set_target_folder(Path(selected_folder))

    def select_set_split_file(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilter("Set Split File (*.txt)")
        if dialog.exec():
            selected_file = dialog.selectedFiles()[0]
            self._set_split_file(Path(selected_file))
        else:
            self._set_split_file(None)

    def split_type_changed(self, text):
        self._set_split_type(text)

    def split_changed(self, value):
        self.train_split = value
        self._update_slider_labels()

    def accept(self):
        if not self.target_folder:
            return

        if self.target_folder.exists() and len(list(self.target_folder.iterdir())) > 0:
            if not self._confirm_overwrite():
                return

        self._split_dataset()
        self._write_split_file(self.target_folder / "set_split.txt")
        self._write_dataset()
        super().accept()

    def _confirm_overwrite(self):
        alert_message = f"The target folder '{self.target_folder}' already exists. Do you want to overwrite it?"
        overwrite = QMessageBox.question(self, "Overwrite Existing Folder", alert_message, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return overwrite == QMessageBox.StandardButton.Yes

    def _update_slider_range(self):
        self.sld_split.setMinimum(0)

        unassigned_items = self.unassigned_items
        maximum = len(unassigned_items)

        self.sld_split.setMaximum(maximum)
        if self.train_split > maximum:
            self.train_split = maximum

        if maximum == 0:
            self.sld_split.setVisible(False)
            self.lbl_already_split.setVisible(True)
        else:
            self.sld_split.setVisible(True)
            self.lbl_already_split.setVisible(False)

        self.sld_split.setValue(self.train_split)
        self._update_slider_labels()

    def _update_slider_labels(self):
        num_items = len(self.items)

        existing_train_items = len([set_name for _, set_name in self.existing_set_mapping.items() if set_name == "train"])
        total_train_items = self.train_split + existing_train_items

        self.lbl_num_train.setText(f"Train {total_train_items}")
        self.lbl_num_val.setText(f"{num_items - total_train_items} Val")

    def _set_target_folder(self, target_folder: Path):
        self.target_folder = target_folder
        self.lbl_target_folder.setText(str(target_folder))

        set_split_file = target_folder / "set_split.txt"
        if set_split_file.exists():
            self._set_split_file(set_split_file)

    def _set_split_file(self, split_file: Optional[Path]):
        self.split_file = split_file
        self.lbl_split_file.setText(str(split_file))

        self.existing_set_mapping = {}
        if split_file is not None:
            self.split_type, self.existing_set_mapping = self._read_split_file(split_file)
            self.dpd_split_by.setCurrentText(self.split_type)

        self._update_slider_range()

    def _set_split_type(self, split_type: str):
        if split_type != self.split_type:
            self.split_type = split_type
            self._set_split_file(None)
        self._update_slider_range()

    def _read_split_file(self, split_file: Path):
        set_mapping = {}
        with open(split_file, "r") as file:
            split_type = file.readline().strip()
            if not split_type in ["Video", "Image"]:
                raise ValueError(f"Invalid split type in split file, expected 'Video' or 'Image', got '{split_type}'")

            for line in file:
                line = line.strip()
                if line:
                    video_image_name, set_name = line.split(",")
                    if set_name not in ["train", "val"]:
                        raise ValueError(f"Invalid set name in split file, expected 'train' or 'val', got '{set_name}'")
                    set_mapping[video_image_name] = set_name
        return split_type, set_mapping

    def _write_split_file(self, split_file: Path):
        with open(split_file, "w") as file:
            file.write(f"{self.split_type}\n")
            for video_image_name, set_name in self.set_mapping.items():
                file.write(f"{video_image_name},{set_name}\n")

    def _split_dataset(self):
        if self.split_type == "Video":
            unassigned_items = self.video_names - set(self.existing_set_mapping.keys())
        else:
            unassigned_items = self.image_names - set(self.existing_set_mapping.keys())

        unassigned_items = list(unassigned_items)
        random.shuffle(unassigned_items)

        train_items = unassigned_items[:self.train_split]
        val_items = unassigned_items[self.train_split:]

        for item in train_items:
            self.additional_set_mapping[item] = "train"
        for item in val_items:
            self.additional_set_mapping[item] = "val"

    def _write_dataset(self):
        self._build_metadata_folder()
        self._write_data_file()

        train_images = []
        val_images = []
        for image_index in range(self.model.get_num_images()):
            if not self.model.get_instances(image_index):
                continue

            image_name = self.model.get_image_name(image_index)
            video_name = image_name.rsplit("_", maxsplit=1)[0]

            if self.split_type == "Video":
                set_name = self.set_mapping.get(video_name, "train")
            else:
                set_name = self.set_mapping.get(image_name, "train")

            if set_name == "train":
                train_images.append(image_index)
            else:
                val_images.append(image_index)

        label_writer = YoloLabelWriter(self.selected_instance_types)
        instance_type_names = {instance_type.name for instance_type in self.selected_instance_types}

        for image_indices, set_name in [(train_images, "train"), (val_images, "val")]:
            set_images_folder = self.target_folder / "images" / set_name
            if set_images_folder.exists():
                shutil.rmtree(set_images_folder)
            set_images_folder.mkdir(parents=True, exist_ok=True)
            set_labels_folder = self.target_folder / "labels" / set_name
            if set_labels_folder.exists():
                shutil.rmtree(set_labels_folder)
            set_labels_folder.mkdir(parents=True, exist_ok=True)

            for image_index in image_indices:
                image_name = self.model.get_image_name(image_index)
                image = self.model.get_image(image_index)

                target_image_file = set_images_folder / f"{image_name}.png"
                target_label_file = set_labels_folder / f"{image_name}.txt"

                instances = self.model.get_instances(image_index)
                instances = [instance for instance in instances if instance.type.name in instance_type_names]
                if not instances:
                    continue

                cv2.imwrite(str(target_image_file), image)
                label_writer.save_instances(instances, target_label_file)

    def _max_num_keypoints(self):
        return max(len(instance_type.keypoints) for instance_type in self.selected_instance_types)

    def _class_name_lookup(self):
        return {class_index: instance_type.name for class_index, instance_type in enumerate(self.selected_instance_types)}

    def _data_dict(self) -> Dict:
        num_keypoints = self._max_num_keypoints()

        data = {
            "path": self.target_folder.as_posix(),
            "names": self._class_name_lookup(),  # Dict of class index to class name
            "kpt_shape": [num_keypoints, 3],
            "train": "images/train",
            "val": "images/val",
        }

        return data

    def _write_data_file(self):
        data_dict = self._data_dict()
        with open(self.target_folder / "data.yaml", "w") as f:
            yaml.dump(data_dict, f)

    def _yolo_output_mapping(self) -> List[Tuple[str, str, int]]:
        output_mapping = []
        for instance_type in self.selected_instance_types:
            output_index = 0
            for point in instance_type.keypoints:
                output_mapping.append((instance_type.name, point.name, output_index))
                output_index += 1
        return output_mapping

    def _build_metadata_folder(self):
        metadata_folder = self.target_folder / "meta"
        metadata_folder.mkdir(parents=True, exist_ok=True)

        instance_types_folder = metadata_folder / "instance_types"
        instance_types_folder.mkdir(parents=True, exist_ok=True)

        for instance_type in self.selected_instance_types:
            instance_type_file = instance_types_folder / f"{instance_type.name}.yaml"

            instance_type_data = {
                "description": "",
                "name": instance_type.name,
                "parent": None
            }

            points = []
            for point in instance_type.keypoints:
                points.append({
                    "name": point.name,
                    "mirror_h": point.name,
                    "mirror_v": point.name,
                })
            instance_type_data["points"] = points

            skeleton = []
            for from_index, to_index in instance_type.skeleton:
                from_point_name = instance_type.keypoints[from_index].name
                to_point_name = instance_type.keypoints[to_index].name
                skeleton.append([from_point_name, to_point_name])
            instance_type_data["skeleton"] = skeleton

            with instance_type_file.open("w") as f:
                yaml.dump(instance_type_data, f)

        output_mapping = self._yolo_output_mapping()
        output_mapping_file = metadata_folder / "output_mapping.csv"
        with output_mapping_file.open("w") as f:
            for instance_name, point_name, output_index in output_mapping:
                f.write(f"{instance_name},{point_name},{output_index}\n")
