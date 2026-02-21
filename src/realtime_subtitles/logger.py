"""
Logging utility for ARIA.

Provides file and console logging with session-based detailed/simple logs.
"""

import logging
import sys
from pathlib import Path
from .timezone_utils import now_in_app_timezone, datetime_from_timestamp


# Global logger instance
_logger = None
_console_mode = "verbose"  # verbose | simple
_simple_logger = None
_simple_file_handler = None
_simple_log_mode = "session"


class _InstantAppendFileHandler(logging.Handler):
    """Append one log line at a time and flush immediately."""

    def __init__(self, file_path: Path, level: int = logging.NOTSET):
        super().__init__(level)
        self.file_path = Path(file_path)

    # Disable logging's default thread lock behavior for this handler.
    def createLock(self):
        self.lock = None

    def acquire(self):
        return

    def release(self):
        return

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
                f.flush()
        except Exception:
            self.handleError(record)


class _ConsoleModeFilter(logging.Filter):
    """Filter console logs based on selected console mode."""

    def filter(self, record: logging.LogRecord) -> bool:
        if _console_mode == "verbose":
            return True
        return bool(getattr(record, "is_transcript", False))


class _ConsoleModeFormatter(logging.Formatter):
    """Switch console format based on current console mode."""

    def format(self, record: logging.LogRecord) -> str:
        if _console_mode == "simple":
            self._style._fmt = "%(asctime)s %(message)s"
            self.datefmt = "%Y-%m-%d %H:%M:%S"
        else:
            self._style._fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            self.datefmt = "%Y-%m-%d %H:%M:%S"
        return super().format(record)

    def formatTime(self, record, datefmt=None):
        dt = datetime_from_timestamp(record.created)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat(sep=" ", timespec="seconds")


class _SimpleFormatter(logging.Formatter):
    """Timezone-aware formatter for transcript/simple logs."""

    def formatTime(self, record, datefmt=None):
        dt = datetime_from_timestamp(record.created)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat(sep=" ", timespec="seconds")


def get_log_dir() -> Path:
    """Get the log directory path."""
    # Use project directory for portability
    current = Path(__file__).resolve()
    project_root = current.parent.parent.parent
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logger(name: str = "ARIA", level: int = logging.DEBUG) -> logging.Logger:
    """
    Set up and return the application logger.
    
    Args:
        name: Logger name
        level: Logging level (default: DEBUG)
    
    Returns:
        Configured logger instance
    """
    global _logger
    
    if _logger is not None:
        return _logger
    
    _logger = logging.getLogger(name)
    _logger.setLevel(level)
    
    # Prevent duplicate handlers
    if _logger.handlers:
        return _logger

    # Log format
    formatter = _ConsoleModeFormatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(_ConsoleModeFilter())
    _logger.addHandler(console_handler)
    
    # Detailed file handler (new file per app run)
    log_dir = get_log_dir()
    ts = now_in_app_timezone().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"detail_{ts}.log"

    file_handler = _InstantAppendFileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    _logger.addHandler(file_handler)
    
    _logger.info(f"Logger initialized. Log file: {log_file}")
    
    return _logger


def get_logger() -> logging.Logger:
    """
    Get the application logger.
    
    Returns:
        Logger instance (creates one if not exists)
    """
    if _logger is None:
        return setup_logger()
    return _logger


def set_console_mode(mode: str) -> None:
    """Set console output mode: verbose or simple."""
    global _console_mode
    if mode not in ("verbose", "simple"):
        return
    _console_mode = mode


def get_console_mode() -> str:
    """Get current console output mode."""
    return _console_mode


def start_simple_log_session() -> Path:
    """Create simple log routing for current run."""
    global _simple_logger, _simple_file_handler

    if _simple_logger is None:
        _simple_logger = logging.getLogger("ARIA_SIMPLE")
        _simple_logger.setLevel(logging.INFO)
        _simple_logger.propagate = False

    # Remove previous handler so each start gets a new file
    if _simple_file_handler is not None:
        try:
            _simple_logger.removeHandler(_simple_file_handler)
            _simple_file_handler.close()
        except Exception:
            pass
        _simple_file_handler = None

    log_dir = get_log_dir()
    ts = now_in_app_timezone().strftime("%Y%m%d_%H%M%S")
    simple_path = log_dir / f"simple_{ts}.log"
    _simple_file_handler = _build_simple_handler(simple_path)
    _simple_logger.addHandler(_simple_file_handler)
    return simple_path


def set_simple_log_mode(mode: str) -> None:
    """Set simple log mode."""
    global _simple_log_mode
    if mode == "session":
        _simple_log_mode = mode


def set_transcript_source(ts_path: str | None) -> None:
    """Backward-compatible no-op after TS tail removal."""
    return


def _build_simple_handler(path: Path) -> _InstantAppendFileHandler:
    handler = _InstantAppendFileHandler(path)
    handler.setLevel(logging.INFO)
    handler.setFormatter(_SimpleFormatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    return handler


# Convenience functions
def debug(msg: str, *args, **kwargs):
    """Log debug message."""
    get_logger().debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """Log info message."""
    get_logger().info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """Log warning message."""
    get_logger().warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """Log error message."""
    get_logger().error(msg, *args, **kwargs)


def exception(msg: str, *args, **kwargs):
    """Log exception with traceback."""
    get_logger().exception(msg, *args, **kwargs)


def transcript(msg: str):
    """Log transcript/translation line to simple log and simple console."""
    if _simple_logger is not None:
        _simple_logger.info(msg)
    if get_console_mode() == "simple":
        get_logger().info(msg, extra={"is_transcript": True})
