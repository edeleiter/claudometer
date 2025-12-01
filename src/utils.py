"""Utility functions for Claude Usage Monitor."""

import logging
import os
import subprocess
import sys
import winreg
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

logger = logging.getLogger(__name__)

APP_NAME = "ClaudeUsageMonitor"
STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def setup_logging(log_dir: Path, debug: bool = False) -> logging.Logger:
    """
    Configure application logging with rotation.

    Args:
        log_dir: Directory for log files
        debug: Enable debug level logging

    Returns:
        Configured root logger
    """
    log_file = log_dir / "claude_monitor.log"

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler with rotation (5MB max, keep 3 backups)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Remove existing handlers
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)

    # Console handler only in debug mode
    if debug:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(console_handler)

    return root_logger


def format_relative_time(iso_timestamp: str | None) -> str:
    """
    Format an ISO timestamp as relative time (e.g., "in 2h 15m").

    Args:
        iso_timestamp: ISO 8601 formatted timestamp string

    Returns:
        Human-readable relative time string
    """
    if not iso_timestamp:
        return "unknown"

    try:
        # Parse ISO timestamp
        reset_time = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)

        diff = reset_time - now

        if diff.total_seconds() <= 0:
            return "now"

        total_seconds = int(diff.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 and days == 0:  # Only show minutes if less than a day
            parts.append(f"{minutes}m")

        if not parts:
            return "< 1m"

        return "in " + " ".join(parts)

    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse timestamp {iso_timestamp}: {e}")
        return "unknown"


def get_executable_path() -> str:
    """Get path to executable (handles both frozen and script mode)."""
    if getattr(sys, "frozen", False):
        return sys.executable
    else:
        return f'"{sys.executable}" "{Path(__file__).parent / "main.py"}"'


def is_startup_enabled() -> bool:
    """Check if app is set to start with Windows."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_KEY,
            0,
            winreg.KEY_READ,
        )
        try:
            winreg.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except WindowsError as e:
        logger.error(f"Failed to check startup status: {e}")
        return False


def enable_startup() -> bool:
    """Add app to Windows startup."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        try:
            exe_path = get_executable_path()
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
            logger.info(f"Added to startup: {exe_path}")
            return True
        finally:
            winreg.CloseKey(key)
    except WindowsError as e:
        logger.error(f"Failed to enable startup: {e}")
        return False


def disable_startup() -> bool:
    """Remove app from Windows startup."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        try:
            winreg.DeleteValue(key, APP_NAME)
            logger.info("Removed from startup")
            return True
        except FileNotFoundError:
            # Already not in startup
            return True
        finally:
            winreg.CloseKey(key)
    except WindowsError as e:
        logger.error(f"Failed to disable startup: {e}")
        return False


def set_startup(enabled: bool) -> bool:
    """Set startup state."""
    if enabled:
        return enable_startup()
    else:
        return disable_startup()


def open_file_in_editor(file_path: Path) -> bool:
    """
    Open a file in the default text editor.

    Args:
        file_path: Path to file to open

    Returns:
        True if successful
    """
    try:
        if sys.platform == "win32":
            os.startfile(str(file_path))
        else:
            subprocess.run(["xdg-open", str(file_path)], check=True)
        return True
    except Exception as e:
        logger.error(f"Failed to open file: {e}")
        return False


def open_url(url: str) -> bool:
    """
    Open a URL in the default browser.

    Args:
        url: URL to open

    Returns:
        True if successful
    """
    try:
        if sys.platform == "win32":
            os.startfile(url)
        else:
            subprocess.run(["xdg-open", url], check=True)
        return True
    except Exception as e:
        logger.error(f"Failed to open URL: {e}")
        return False
