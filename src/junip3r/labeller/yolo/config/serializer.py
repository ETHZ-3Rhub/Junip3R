from typing import Any, Dict, List, Optional, Union

from junip3r.labeller.yolo.config.data import YoloDataYaml

# Keys consumed into a typed field below - everything else round-trips through `extras`
# (this is how a niche/undocumented key like "minival" survives a read-modify-write
# without needing its own dataclass field - see YoloDataYaml.extras).
_KNOWN_KEYS = {
    "path", "train", "val", "validation", "test",
    "names", "nc", "channels",
    "download",
    "kpt_shape", "flip_idx", "kpt_names", "kpt_oks_sigmas",
    "masks_dir", "label_mapping",
    "depth_scale", "max_depth",
}


def _normalize_int_keys(value: Optional[Dict[Any, Any]]) -> Optional[Dict[int, Any]]:
    if value is None:
        return None
    return {int(key): item for key, item in value.items()}


class YoloDataYamlSerializer:
    def serialize(self, config: YoloDataYaml) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        self._set(data, "path", config.path)
        data["train"] = config.train
        data["val"] = config.val
        self._set(data, "test", config.test)

        self._set(data, "names", config.names)
        self._set(data, "nc", config.nc)
        self._set(data, "channels", config.channels)

        self._set(data, "download", config.download)

        self._set(data, "kpt_shape", config.kpt_shape)
        self._set(data, "flip_idx", config.flip_idx)
        self._set(data, "kpt_names", config.kpt_names)
        self._set(data, "kpt_oks_sigmas", config.kpt_oks_sigmas)

        self._set(data, "masks_dir", config.masks_dir)
        self._set(data, "label_mapping", config.label_mapping)

        self._set(data, "depth_scale", config.depth_scale)
        self._set(data, "max_depth", config.max_depth)

        data.update(config.extras)

        return data

    def deserialize(self, data: Dict[str, Any]) -> YoloDataYaml:
        train = data.get("train")
        if train is None:
            raise ValueError("data.yaml is missing required key 'train'")

        # "validation" is a compatibility alias, normalized to "val" - never round-tripped
        # back out under its own name (see serialize() above).
        val = data.get("val", data.get("validation"))
        if val is None:
            raise ValueError("data.yaml is missing required key 'val' (or its alias 'validation')")

        names = self._deserialize_names(data.get("names"))
        nc = int(data["nc"]) if data.get("nc") is not None else None

        if names is not None and nc is not None and len(names) != nc:
            raise ValueError(f"data.yaml 'names' has {len(names)} entries but 'nc' says {nc}")

        extras = {key: value for key, value in data.items() if key not in _KNOWN_KEYS}

        return YoloDataYaml(
            path=data.get("path"),
            train=train,
            val=val,
            test=data.get("test"),
            names=names,
            nc=nc,
            channels=data.get("channels", 3),
            download=data.get("download"),
            kpt_shape=data.get("kpt_shape"),
            flip_idx=data.get("flip_idx"),
            kpt_names=_normalize_int_keys(data.get("kpt_names")),
            kpt_oks_sigmas=data.get("kpt_oks_sigmas"),
            masks_dir=data.get("masks_dir"),
            label_mapping=_normalize_int_keys(data.get("label_mapping")),
            depth_scale=data.get("depth_scale"),
            max_depth=data.get("max_depth"),
            extras=extras,
        )

    def _deserialize_names(self, names: Any) -> Optional[Union[List[str], Dict[int, str]]]:
        if names is None:
            return None
        if isinstance(names, dict):
            return _normalize_int_keys(names)
        return list(names)

    def _set(self, data: Dict[str, Any], key: str, value: Any) -> None:
        if value is not None:
            data[key] = value
