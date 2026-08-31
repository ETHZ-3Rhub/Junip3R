from pathlib import Path

from junip3r.frame_extractor.data.types.data import Video
from junip3r.frame_extractor.util.video_relocation import (
    auto_remap_missing_videos,
    common_suffix_length,
    try_remap_path,
)


def test_common_suffix_length_counts_shared_trailing_parts():
    assert common_suffix_length(Path("/a/b/c.mp4").parts, Path("/x/b/c.mp4").parts) == 2
    assert common_suffix_length(Path("/a/b/c.mp4").parts, Path("/x/y/z.mp4").parts) == 0


def test_try_remap_path_substitutes_the_moved_base_and_checks_existence(tmp_path: Path):
    old_root = tmp_path / "old_root"
    new_root = tmp_path / "new_root"
    (new_root / "session1").mkdir(parents=True)
    (new_root / "session1" / "cam.mp4").touch()

    old_path = old_root / "session1" / "cam.mp4"
    target = old_root / "session1" / "cam.mp4"

    remapped = try_remap_path(old_path, new_root / "session1" / "cam.mp4", target)

    assert remapped == new_root / "session1" / "cam.mp4"


def test_try_remap_path_returns_none_when_no_shared_suffix():
    remapped = try_remap_path(Path("/a/b.mp4"), Path("/x/y.mp4"), Path("/a/other.mp4"))

    assert remapped is None


def test_try_remap_path_returns_none_when_remapped_file_does_not_exist(tmp_path: Path):
    old_root = tmp_path / "old_root"
    new_root = tmp_path / "new_root"
    new_root.mkdir()

    remapped = try_remap_path(old_root / "cam.mp4", new_root / "cam.mp4", old_root / "other.mp4")

    assert remapped is None


def test_auto_remap_missing_videos_splits_fixed_from_still_missing(tmp_path: Path):
    old_root = tmp_path / "old_root"
    new_root = tmp_path / "new_root"
    (new_root / "session1").mkdir(parents=True)
    (new_root / "session1" / "cam2.mp4").touch()

    fixable = Video("b", old_root / "session1" / "cam2.mp4")
    unfixable = Video("c", tmp_path / "unrelated" / "cam3.mp4")

    fixed, still_missing = auto_remap_missing_videos(
        old_root / "session1" / "cam1.mp4",
        new_root / "session1" / "cam1.mp4",
        [fixable, unfixable],
    )

    assert fixed == [(fixable, new_root / "session1" / "cam2.mp4")]
    assert still_missing == [unfixable]
