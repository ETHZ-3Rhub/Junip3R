from pathlib import Path
from typing import Dict, Sequence

from junip3r.frame_extractor.data.types.data import Video


def deduplicate_video_names(videos: Sequence[Video]) -> Dict[str, str]:
    """Map each video's id to a display name, widened with parent path segments until unique."""

    def get_long_name(path: Path, num_parents: int = 0) -> str:
        if num_parents >= len(path.parents):
            return str(path.as_posix())
        return str(path.relative_to(path.parents[num_parents]).as_posix())

    names = {v.video_id: (v, v.path.name, 0) for v in videos}
    while True:
        videos_per_name = {}
        for video_id, (video, name, path_length) in names.items():
            if name not in videos_per_name:
                videos_per_name[name] = []
            videos_per_name[name].append((video_id, video, path_length))
        duplicates = {name: vids for name, vids in videos_per_name.items() if len(vids) > 1}
        if not duplicates:
            break

        widened = False
        for name, vids in duplicates.items():
            for vid_id, video, num_parents in vids:
                if num_parents >= len(video.path.parents):
                    continue  # already at the full path; can't widen any further
                num_parents += 1
                longer_name = get_long_name(video.path, num_parents)
                names[vid_id] = (video, longer_name, num_parents)
                widened = True

        if not widened:
            # every remaining duplicate is already at its full path (e.g. genuinely
            # identical paths) - give up widening; those names stay non-unique.
            break

    return {video.video_id: name for video, name, _ in names.values()}
