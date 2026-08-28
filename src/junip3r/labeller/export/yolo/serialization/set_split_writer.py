from pathlib import Path

import yaml

from junip3r.labeller.export.yolo.set_split import SetSplitConfig, SetSplitConfigSerializer


class SetSplitWriter:
    def write(self, target_folder: Path, config: SetSplitConfig):
        metadata_folder = target_folder / "meta"
        metadata_folder.mkdir(parents=True, exist_ok=True)

        with (metadata_folder / "set_split.yaml").open("w") as f:
            yaml.dump(SetSplitConfigSerializer.serialize(config), f)
