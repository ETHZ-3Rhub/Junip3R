from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

from junip3r.labeller.yolo.data_yaml.data import YoloDataYaml


@dataclass
class YoloDatasetConfig:
    """A YoloDataYaml with train/val/test resolved to absolute paths and names always
    populated (auto-generated from nc when absent). See resolve_yolo_data_yaml().
    """

    # Training image directories/files, resolved to absolute paths.
    train: List[Path]
    # Validation image directories/files, resolved to absolute paths.
    val: List[Path]
    # Test image directories/files, resolved to absolute paths.
    test: Optional[List[Path]] = None

    # Class names by index - always populated, generated as {"0", "1", ...} from nc
    # when the source YoloDataYaml had no names.
    names: Dict[int, str] = field(default_factory=dict)
    # Number of image channels (3 = RGB, 1 = grayscale).
    channels: int = 3

    # [num_keypoints, dims_per_keypoint] for pose datasets.
    kpt_shape: Optional[List[int]] = None
    # Per-keypoint index to swap with under a horizontal flip (pose datasets).
    flip_idx: Optional[List[int]] = None
    # Per-class keypoint names, by class index (pose datasets).
    kpt_names: Optional[Dict[int, List[str]]] = None
    # Per-keypoint OKS sigma, used for pose evaluation.
    kpt_oks_sigmas: Optional[List[float]] = None


def resolve_yolo_data_yaml(config: YoloDataYaml, yaml_dir: Path) -> YoloDatasetConfig:
    """Resolves a YoloDataYaml's paths/names against the directory its data.yaml lives
    in - relative paths become absolute, and train/val/test are normalized to lists.
    """
    yaml_dir = Path(yaml_dir).resolve()
    root = (yaml_dir / config.path).resolve() if config.path else yaml_dir

    return YoloDatasetConfig(
        train=_resolve_paths(config.train, root),
        val=_resolve_paths(config.val, root),
        test=_resolve_paths(config.test, root) if config.test is not None else None,
        names=_resolve_names(config.names, config.nc),
        channels=config.channels if config.channels is not None else 3,
        kpt_shape=config.kpt_shape,
        flip_idx=config.flip_idx,
        kpt_names=config.kpt_names,
        kpt_oks_sigmas=config.kpt_oks_sigmas,
    )


def _resolve_paths(entries: Union[str, List[str]], root: Path) -> List[Path]:
    if isinstance(entries, str):
        entries = [entries]
    return [_resolve_path(entry, root) for entry in entries]


def _resolve_path(entry: str, root: Path) -> Path:
    path = Path(entry)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def _resolve_names(
    names: Optional[Union[List[str], Dict[int, str]]],
    nc: Optional[int],
) -> Dict[int, str]:
    if names is not None:
        if isinstance(names, dict):
            return dict(names)
        return {index: name for index, name in enumerate(names)}
    if nc is not None:
        return {index: str(index) for index in range(nc)}
    return {}
