from pathlib import Path
from typing import List, Optional, Tuple

from junip3r.frame_extractor.data.types.data import Video


def common_suffix_length(parts_a: tuple, parts_b: tuple) -> int:
    """Return the number of trailing path parts shared between two paths."""
    length = 0
    for a, b in zip(reversed(parts_a), reversed(parts_b)):
        if a == b:
            length += 1
        else:
            break
    return length


def try_remap_path(old_path: Path, new_path: Path, target: Path) -> Optional[Path]:
    """
    Given that old_path was relocated to new_path, attempt to remap `target`
    using the same base-path substitution. Returns the remapped Path if the
    resulting file exists, otherwise None.
    """
    suffix_len = common_suffix_length(old_path.parts, new_path.parts)
    if suffix_len == 0:
        return None

    old_base_parts = old_path.parts[:-suffix_len] if suffix_len < len(old_path.parts) else ()
    new_base_parts = new_path.parts[:-suffix_len] if suffix_len < len(new_path.parts) else ()

    old_base = Path(*old_base_parts) if old_base_parts else Path()
    new_base = Path(*new_base_parts) if new_base_parts else Path()

    try:
        relative = target.relative_to(old_base)
        candidate = new_base / relative
        if candidate.exists():
            return candidate
    except ValueError:
        pass
    return None


def auto_remap_missing_videos(
        old_path: Path,
        new_path: Path,
        missing_videos: List[Video],
) -> Tuple[List[Tuple[Video, Path]], List[Video]]:
    """
    Given that old_path was relocated to new_path, attempt to auto-remap the
    remaining missing videos (at their current known paths) using the same
    base-path substitution. Returns (fixed, still_missing), where each `fixed`
    entry pairs the original video with its newly-resolved path.
    """
    fixed: List[Tuple[Video, Path]] = []
    still_missing: List[Video] = []
    for video in missing_videos:
        remapped = try_remap_path(old_path, new_path, video.path)
        if remapped is not None:
            fixed.append((video, remapped))
        else:
            still_missing.append(video)
    return fixed, still_missing
