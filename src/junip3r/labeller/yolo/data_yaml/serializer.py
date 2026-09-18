from typing import Any, Dict, List, Optional, Union

from junip3r.labeller.yolo.data_yaml.data import YoloDataYaml

# Keys consumed into a typed field below - everything else round-trips through `extras`
# (this is how a niche/undocumented key like "minival" survives a read-modify-write
# without needing its own dataclass field - see YoloDataYaml.extras).
_KNOWN_KEYS = {
    "path", "train", "val", "validation", "test",
    "names", "nc", "channels",
    "kpt_shape", "flip_idx", "kpt_names", "kpt_oks_sigmas",
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

        self._set(data, "kpt_shape", config.kpt_shape)
        self._set(data, "flip_idx", config.flip_idx)
        self._set(data, "kpt_names", config.kpt_names)
        self._set(data, "kpt_oks_sigmas", config.kpt_oks_sigmas)

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
            kpt_shape=data.get("kpt_shape"),
            flip_idx=data.get("flip_idx"),
            kpt_names=_normalize_int_keys(data.get("kpt_names")),
            kpt_oks_sigmas=data.get("kpt_oks_sigmas"),
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
