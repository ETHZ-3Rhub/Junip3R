from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union


@dataclass
class YoloDataYaml:
    path: Optional[str]
    train: Union[str, List[str]]
    val: Union[str, List[str]]
    test: Optional[Union[str, List[str]]]

    names: Optional[Union[List[str], Dict[int, str]]]
    nc: Optional[int]
    channels: Optional[int]

    download: Optional[str]

    kpt_shape: Optional[List[int]]
    flip_idx: Optional[List[int]]
    kpt_names: Optional[Dict[int, List[str]]]
    kpt_oks_sigmas: Optional[List[float]]

    masks_dir: Optional[str]
    label_mapping: Optional[Dict[int, Optional[Union[int, str]]]]

    depth_scale: Optional[float]
    max_depth: Optional[float]

    extras: Dict[str, Any]
