import logging
from pathlib import Path

from junip3r.logging_setup import create_logging_manager


def _make_logger(name: str = "junip3r.test.logging") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = True
    return logger


def test_start_app_run_creates_files_and_logs(tmp_path: Path):
    manager = create_logging_manager(
        log_root=tmp_path,
        session_id="20260708T010203.456",
        run_mode="standalone",
    )

    context = manager.start_app_run("labeller")
    logger = _make_logger()
    logger.info(
        "operation happened",
        extra={"event_category": "operation", "event_name": "test_operation"},
    )
    manager.close()

    assert context.app_name == "labeller"
    assert context.process_session_id == "20260708T010203.456"
    assert context.info_log_file.exists()
    assert context.debug_log_file.exists()

    info_text = context.info_log_file.read_text(encoding="utf-8")
    debug_text = context.debug_log_file.read_text(encoding="utf-8")

    assert "operation happened" in info_text
    assert "event=operation/test_operation" in info_text
    assert "operation happened" in debug_text


def test_start_app_run_rotates_files(tmp_path: Path):
    manager = create_logging_manager(
        log_root=tmp_path,
        session_id="20260708T010203.456",
        run_mode="integrated",
    )
    logger = _make_logger("junip3r.test.rotation")

    first = manager.start_app_run("labeller")
    logger.info("first run", extra={"event_category": "ui", "event_name": "first"})

    second = manager.start_app_run("frame_extractor")
    logger.info("second run", extra={"event_category": "ui", "event_name": "second"})
    manager.close()

    first_info = first.info_log_file.read_text(encoding="utf-8")
    second_info = second.info_log_file.read_text(encoding="utf-8")

    assert "first run" in first_info
    assert "second run" not in first_info
    assert "second run" in second_info
    assert manager.current_context is None

