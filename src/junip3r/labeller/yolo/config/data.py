from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class YoloDataYaml:
    path: Optional[str] = None
    train: Union[str, List[str]] = ""
    val: Union[str, List[str]] = ""
    test: Optional[Union[str, List[str]]] = None

    names: Optional[Union[List[str], Dict[int, str]]] = None
    nc: Optional[int] = None
    channels: Optional[int] = 3

    download: Optional[str] = None

    kpt_shape: Optional[List[int]] = None
    flip_idx: Optional[List[int]] = None
    kpt_names: Optional[Dict[int, List[str]]] = None
    kpt_oks_sigmas: Optional[List[float]] = None

    masks_dir: Optional[str] = None
    label_mapping: Optional[Dict[int, Optional[Union[int, str]]]] = None

    depth_scale: Optional[float] = None
    max_depth: Optional[float] = None

    extras: Dict[str, Any] = field(default_factory=dict)
