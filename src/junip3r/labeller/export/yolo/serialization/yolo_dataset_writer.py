import shutil
from pathlib import Path
from typing import Any, Dict, Iterator, List, Sequence, Tuple

import cv2
import yaml

from junip3r.labeller.export.yolo.data import IYoloImage, YoloDataset
from junip3r.labeller.yolo.data_yaml.data import YoloDataYaml
from junip3r.labeller.yolo.data_yaml.serializer import YoloDataYamlSerializer
from junip3r.labeller.yolo.labels.serializer import YoloLabelSerializer

# train/val are always written, even empty - YoloDataYaml requires both, and our own
# YOLO dataset reader expects both directories to exist (see discover_yolo_dataset_images).
_STANDARD_SETS = ("train", "val")


class YoloDatasetWriter:
    def write(self, target_folder: Path, dataset: YoloDataset) -> Iterator[Tuple[int, int]]:
        """Write the dataset to disk, yielding (completed, total) after each image."""
        sets = self._all_sets(dataset)
        self._write_data_file(target_folder, dataset, sets)

        label_serializer = YoloLabelSerializer(keypoint_dims=3)

        total = sum(len(images) for _, images in sets)
        completed = 0

        for set_name, images in sets:
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
                label_file = set_labels_folder / f"{image_name}.txt"

                if image.source_file is not None:
                    image_file = set_images_folder / f"{image_name}{image.source_file.suffix}"
                    shutil.copy2(image.source_file, image_file)
                elif image.image is not None:
                    image_file = set_images_folder / f"{image_name}.png"
                    cv2.imwrite(str(image_file), cv2.cvtColor(image.image, cv2.COLOR_RGB2BGR))
                else:
                    raise ValueError(f"YoloImage '{image_name}' has neither a source_file nor image data")

                label_serializer.write(label_file, image.instances)

                completed += 1
                yield completed, total

    def _all_sets(self, dataset: YoloDataset) -> List[Tuple[str, Sequence[IYoloImage]]]:
        sets_by_name = dict(dataset.sets)
        standard = [(name, sets_by_name.get(name, ())) for name in _STANDARD_SETS]
        extra = [(name, images) for name, images in dataset.sets if name not in _STANDARD_SETS]
        return standard + extra

    def _write_data_file(
            self,
            target_folder: Path,
            dataset: YoloDataset,
            sets: Sequence[Tuple[str, Sequence[IYoloImage]]],
    ) -> None:
        data_yaml = self._data_yaml(target_folder, dataset, sets)
        target_folder.mkdir(parents=True, exist_ok=True)
        with open(target_folder / "data.yaml", "w") as f:
            yaml.dump(YoloDataYamlSerializer().serialize(data_yaml), f)

    def _data_yaml(
            self,
            target_folder: Path,
            dataset: YoloDataset,
            sets: Sequence[Tuple[str, Sequence[IYoloImage]]],
    ) -> YoloDataYaml:
        num_keypoints = dataset.num_keypoints
        names = {i: name for i, name in enumerate(dataset.class_names)}
        set_paths = {set_name: f"images/{set_name}" for set_name, _ in sets}

        flip_h_idx = dataset.flip_h_idx
        if flip_h_idx is not None and len(flip_h_idx) != num_keypoints:
            raise ValueError("flip_h_idx must have same length as num_keypoints")

        # flip_v_idx (vertical-flip keypoint swap) is a Junip3R-specific extension, not
        # a real Ultralytics data.yaml key - same as any non-train/val/test set name -
        # so both round-trip through YoloDataYaml.extras rather than a typed field.
        extras: Dict[str, Any] = {
            set_name: path for set_name, path in set_paths.items() if set_name not in ("train", "val", "test")
        }
        flip_v_idx = dataset.flip_v_idx
        if flip_v_idx is not None:
            if len(flip_v_idx) != num_keypoints:
                raise ValueError("flip_v_idx must have same length as num_keypoints")
            extras["flip_v_idx"] = list(flip_v_idx)

        return YoloDataYaml(
            train=set_paths["train"],
            val=set_paths["val"],
            path=target_folder.as_posix(),
            test=set_paths.get("test"),
            names=names,
            kpt_shape=[num_keypoints, 3],
            flip_idx=list(flip_h_idx) if flip_h_idx is not None else None,
            extras=extras,
        )
