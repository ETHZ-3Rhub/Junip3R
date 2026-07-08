from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


LOCAL_APPDATA = os.environ.get("LOCALAPPDATA")

if LOCAL_APPDATA is not None:
    DEFAULT_LOG_ROOT = Path(LOCAL_APPDATA) / "ETH3RHub" / "Junip3R" / "logs"
else:
    DEFAULT_LOG_ROOT = Path.home() / ".junip3r" / "logs"

DEFAULT_LOGGER_NAME = "junip3r"


@dataclass(frozen=True)
class AppRunLogContext:
    run_mode: str
    app_name: str
    process_session_id: str
    app_run_id: str
    app_run_index: int
    started_at: datetime
    log_dir: Path
    info_log_file: Path
    debug_log_file: Path


class _ContextFilter(logging.Filter):
    def __init__(self, manager: "LoggingManager"):
        super().__init__()
        self._manager = manager

    def filter(self, record: logging.LogRecord) -> bool:
        context = self._manager.current_context
        record.process_session_id = context.process_session_id if context else "-"
        record.app_name = context.app_name if context else "-"
        record.app_run_id = context.app_run_id if context else "-"
        record.app_run_index = context.app_run_index if context else -1
        record.run_mode = context.run_mode if context else "-"
        record.event_category = getattr(record, "event_category", "-")
        record.event_name = getattr(record, "event_name", "-")
        return True


class _KeyValueFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).astimezone().isoformat(timespec="milliseconds")
        parts = [
            timestamp,
            record.levelname,
            record.name,
            f"session={getattr(record, 'process_session_id', '-')}",
            f"app={getattr(record, 'app_name', '-')}",
            f"run={getattr(record, 'app_run_id', '-')}",
            f"idx={getattr(record, 'app_run_index', -1)}",
            f"mode={getattr(record, 'run_mode', '-')}",
            f"event={getattr(record, 'event_category', '-')}/{getattr(record, 'event_name', '-')}",
            record.getMessage(),
        ]
        if record.exc_info:
            parts.append(self.formatException(record.exc_info))
        return " | ".join(str(part) for part in parts)


class LoggingManager:
    """Manage one process session and one active app-run log pair at a time."""

    def __init__(
        self,
        *,
        log_root: Optional[Path] = None,
        logger_name: str = DEFAULT_LOGGER_NAME,
        run_mode: str = "standalone",
        enable_console: bool = False,
        session_id: Optional[str] = None,
    ):
        self._log_root = Path(log_root or DEFAULT_LOG_ROOT)
        self._logger_name = logger_name
        self._run_mode = run_mode
        self._enable_console = enable_console
        self._process_started_at = datetime.now().astimezone()
        self._process_session_id = session_id or self._process_started_at.strftime("%Y%m%dT%H%M%S.%f")[:-3]
        self._app_run_index = 0
        self._current_context: Optional[AppRunLogContext] = None
        self._current_handlers: list[logging.Handler] = []

        self._logger = logging.getLogger(self._logger_name)
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False
        self._reset_managed_handlers()

    @property
    def process_session_id(self) -> str:
        return self._process_session_id

    @property
    def current_context(self) -> Optional[AppRunLogContext]:
        return self._current_context

    @property
    def log_root(self) -> Path:
        return self._log_root

    def _reset_managed_handlers(self) -> None:
        for handler in list(self._logger.handlers):
            if getattr(handler, "_junip3r_managed", False):
                self._logger.removeHandler(handler)
                handler.close()

    def _make_handler(self, path: Path, level: int) -> logging.Handler:
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setLevel(level)
        handler.setFormatter(_KeyValueFormatter())
        handler.addFilter(_ContextFilter(self))
        handler._junip3r_managed = True  # type: ignore[attr-defined]
        return handler

    def start_app_run(self, app_name: str) -> AppRunLogContext:
        self.close_current_app_run()

        self._app_run_index += 1
        started_at = datetime.now().astimezone()
        app_run_id = started_at.strftime("%Y%m%dT%H%M%S")
        run_dir = self._log_root / self._process_session_id[:8] / app_name
        run_dir.mkdir(parents=True, exist_ok=True)

        info_log_file = run_dir / f"{app_name}_{app_run_id}_run-{self._app_run_index:04d}_info.log"
        debug_log_file = run_dir / f"{app_name}_{app_run_id}_run-{self._app_run_index:04d}_debug.log"

        info_handler = self._make_handler(info_log_file, logging.INFO)
        debug_handler = self._make_handler(debug_log_file, logging.DEBUG)
        self._logger.addHandler(info_handler)
        self._logger.addHandler(debug_handler)
        self._current_handlers = [info_handler, debug_handler]

        if self._enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(_KeyValueFormatter())
            console_handler.addFilter(_ContextFilter(self))
            console_handler._junip3r_managed = True  # type: ignore[attr-defined]
            self._logger.addHandler(console_handler)
            self._current_handlers.append(console_handler)

        self._current_context = AppRunLogContext(
            run_mode=self._run_mode,
            app_name=app_name,
            process_session_id=self._process_session_id,
            app_run_id=app_run_id,
            app_run_index=self._app_run_index,
            started_at=started_at,
            log_dir=run_dir,
            info_log_file=info_log_file,
            debug_log_file=debug_log_file,
        )

        self._logger.info(
            "started app run",
            extra={"event_category": "lifecycle", "event_name": "app_run_started"},
        )
        assert self._current_context is not None
        return self._current_context

    def close_current_app_run(self) -> None:
        if self._current_context is None:
            self._remove_handlers()
            return

        self._logger.info(
            "ending app run",
            extra={"event_category": "lifecycle", "event_name": "app_run_ending"},
        )
        self._remove_handlers()
        self._current_context = None

    def _remove_handlers(self) -> None:
        for handler in self._current_handlers:
            self._logger.removeHandler(handler)
            handler.flush()
            handler.close()
        self._current_handlers = []

    def close(self) -> None:
        self.close_current_app_run()


def create_logging_manager(
    *,
    log_root: Optional[Path] = None,
    run_mode: str = "standalone",
    enable_console: bool = False,
    session_id: Optional[str] = None,
    logger_name: str = DEFAULT_LOGGER_NAME,
) -> LoggingManager:
    return LoggingManager(
        log_root=log_root,
        run_mode=run_mode,
        enable_console=enable_console,
        session_id=session_id,
        logger_name=logger_name,
    )

