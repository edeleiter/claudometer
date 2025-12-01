"""Configuration management for Claude Usage Monitor."""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

APP_NAME = "ClaudeMonitor"

DEFAULT_CONFIG = {
    "organization_id": "",
    "session_cookie": "",
    "poll_interval_seconds": 300,
    "notification_thresholds": [50, 75, 90],
    "start_with_windows": False,
    "debug_mode": False,
}


def get_app_data_dir() -> Path:
    """
    Get appropriate directory for app data.

    Priority:
    1. CLAUDE_MONITOR_DATA env var (for portability)
    2. Same directory as exe (for portable mode if config exists there)
    3. %LOCALAPPDATA%/ClaudeMonitor (standard Windows location)
    """
    # Check environment variable
    if env_path := os.environ.get("CLAUDE_MONITOR_DATA"):
        path = Path(env_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    # Check if running as frozen exe
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        # Check if config exists next to exe (portable mode)
        if (exe_dir / "config.json").exists():
            return exe_dir

    # Default to LOCALAPPDATA
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        app_dir = Path(local_app_data) / APP_NAME
    else:
        # Fallback to user home
        app_dir = Path.home() / ".claude-monitor"

    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_config_path() -> Path:
    """Get path to config file."""
    return get_app_data_dir() / "config.json"


def get_log_dir() -> Path:
    """Get path to log directory."""
    log_dir = get_app_data_dir() / "logs"
    log_dir.mkdir(exist_ok=True)
    return log_dir


class ConfigManager:
    """Manages application configuration."""

    def __init__(self, config_path: Path | None = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Optional custom config path. Uses default if not provided.
        """
        self.config_path = config_path or get_config_path()
        self.config: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        """Load configuration from file, merging with defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # Merge with defaults (handles new config options)
                config = {**DEFAULT_CONFIG, **loaded}
                logger.info(f"Loaded config from {self.config_path}")
                return config
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load config: {e}")
                return DEFAULT_CONFIG.copy()
        logger.info("No config file found, using defaults")
        return DEFAULT_CONFIG.copy()

    def save(self) -> bool:
        """
        Save configuration to file.

        Returns:
            True if save was successful, False otherwise.
        """
        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Saved config to {self.config_path}")
            return True
        except IOError as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def is_configured(self) -> bool:
        """Check if required configuration is present."""
        return bool(self.config.get("organization_id")) and bool(
            self.config.get("session_cookie")
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self.config[key] = value

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access to config values."""
        return self.config[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dict-like setting of config values."""
        self.config[key] = value

    def __contains__(self, key: str) -> bool:
        """Check if key exists in config."""
        return key in self.config
