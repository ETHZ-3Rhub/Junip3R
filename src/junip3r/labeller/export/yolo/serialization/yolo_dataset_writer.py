import shutil
from pathlib import Path
from typing import Dict, Any, Iterator, Tuple

import cv2
import yaml

from junip3r.labeller.export.yolo.data import YoloDataset
from junip3r.labeller.export.yolo.serialization.yolo_label_writer import YOLOPoseLabelWriter


class YoloDatasetWriter:
    def write(self, target_folder: Path, dataset: YoloDataset) -> Iterator[Tuple[int, int]]:
        """Write the dataset to disk, yielding (completed, total) after each image."""
        self._write_data_file(target_folder, dataset)

        total = sum(len(images) for _, images in dataset.sets)
        completed = 0

        for set_name, images in dataset.sets:
            set_images_folder = target_folder / "images" / set_name
            if set_images_folder.exists():
                shutil.rmtree(set_images_folder)
            set_images_folder.mkdir(parents=True, exist_ok=True)
            set_labels_folder = target_folder / "labels" / set_name
            if set_labels_folder.exists():
                shutil.rmtree(set_labels_folder)
            set_labels_folder.mkdir(parents=True, exist_ok=True)

            for image in images:
                image_name = image.name
                image_file = set_images_folder / f"{image_name}.png"
                label_file = set_labels_folder / f"{image_name}.txt"

                cv2.imwrite(str(image_file), image.image)
                YOLOPoseLabelWriter.write_instances(label_file, image.instances)

                completed += 1
                yield completed, total

    def _write_data_file(self, target_folder: Path, dataset: YoloDataset):
        data_dict = self._data_dict(target_folder, dataset)
        target_folder.mkdir(parents=True, exist_ok=True)
        with open(target_folder / "data.yaml", "w") as f:
            yaml.dump(data_dict, f)

    def _data_dict(self, target_folder: Path, dataset: YoloDataset) -> Dict:
        num_keypoints = dataset.num_keypoints
        class_names = {i: name for i, name in enumerate(dataset.class_names)}

        data: Dict[str, Any] = {
            "path": target_folder.as_posix(),
            "names": class_names,  # Dict of class index to class name
            "kpt_shape": [num_keypoints, 3]
        }

        flip_h_idx = dataset.flip_h_idx
        flip_v_idx = dataset.flip_v_idx

        if flip_h_idx is not None:
            if len(flip_h_idx) != num_keypoints:
                raise ValueError("flip_h_idx must have same length as num_keypoints")
            data["flip_idx"] = list(flip_h_idx)
        if flip_v_idx is not None:
            if len(flip_v_idx) != num_keypoints:
                raise ValueError("flip_h_idx must have same length as num_keypoints")
            data["flip_v_idx"] = list(flip_v_idx)

        for set_name, _ in dataset.sets:
            data[set_name] = f"images/{set_name}"

        return data
