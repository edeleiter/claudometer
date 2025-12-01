"""Windows startup registry management for Claudometer."""

import sys
import winreg

APP_NAME = "Claudometer"
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_executable_path() -> str:
    """Get path to executable (frozen exe or python script)."""
    if getattr(sys, "frozen", False):
        return sys.executable
    # For dev: use pythonw to avoid console window
    import os

    return f'pythonw "{os.path.abspath("src/main.py")}"'


def is_startup_enabled() -> bool:
    """Check if startup registry entry exists."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ
        ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False


def enable_startup() -> None:
    """Add registry entry to start app on Windows login."""
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_WRITE
    ) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_executable_path())


def disable_startup() -> None:
    """Remove registry entry."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_WRITE
        ) as key:
            winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass  # Already removed
