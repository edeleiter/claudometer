#!/usr/bin/env python3
"""Deploy script - builds, installs, and runs Claudometer."""

import os
import shutil
import subprocess
import sys
import winreg
from pathlib import Path

INSTALL_DIR = Path(os.environ["LOCALAPPDATA"]) / "Claudometer"
EXE_NAME = "ClaudeMonitor.exe"


def main():
    """Build, install, and run Claudometer."""
    project_root = Path(__file__).parent

    # 1. Build
    print("Building...")
    result = subprocess.run([sys.executable, "build.py"], cwd=project_root)
    if result.returncode != 0:
        print("Build failed!")
        return 1

    # 2. Kill existing instance
    print("Stopping existing instance...")
    subprocess.run(
        ["taskkill", "/f", "/im", EXE_NAME],
        capture_output=True,
    )  # Ignore errors if not running

    # 3. Install to permanent location
    print(f"Installing to {INSTALL_DIR}...")
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy(project_root / "dist" / EXE_NAME, INSTALL_DIR / EXE_NAME)

    # 4. Enable startup (registry entry pointing to installed exe)
    print("Enabling startup...")
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_WRITE,
    ) as key:
        winreg.SetValueEx(
            key, "Claudometer", 0, winreg.REG_SZ, str(INSTALL_DIR / EXE_NAME)
        )

    # 5. Launch detached
    print("Launching...")
    subprocess.Popen(
        [str(INSTALL_DIR / EXE_NAME)],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
    )

    print("\nDone! Claudometer is running in system tray.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
