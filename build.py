#!/usr/bin/env python3
"""Build script for Claude Usage Monitor."""

import shutil
import subprocess
import sys
from pathlib import Path


def main():
    """Build the application."""
    project_root = Path(__file__).parent
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"

    print("=" * 60)
    print("Claude Usage Monitor - Build Script")
    print("=" * 60)

    # Clean previous builds
    print("\n[1/4] Cleaning previous builds...")
    shutil.rmtree(dist_dir, ignore_errors=True)
    shutil.rmtree(build_dir, ignore_errors=True)
    print("  Done.")

    # Install dependencies using uv
    print("\n[2/4] Installing dependencies with uv...")
    subprocess.run(["uv", "sync", "--all-extras"], check=True)
    print("  Done.")

    # Run PyInstaller via uv
    print("\n[3/4] Building executable...")
    result = subprocess.run(
        ["uv", "run", "pyinstaller", "--clean", "build.spec"],
        capture_output=False,
    )

    if result.returncode != 0:
        print("\n  ERROR: Build failed!")
        return 1

    print("  Done.")

    # Copy additional files to dist
    print("\n[4/4] Copying additional files...")
    if (project_root / "README.md").exists():
        shutil.copy(project_root / "README.md", dist_dir)
    shutil.copy(project_root / "config.example.json", dist_dir)
    print("  Done.")

    # Create release zip
    print("\nCreating release archive...")
    archive_name = dist_dir / "ClaudeMonitor-v1.0.0-win64"
    shutil.make_archive(str(archive_name), "zip", dist_dir)
    print(f"  Created: {archive_name}.zip")

    print("\n" + "=" * 60)
    print("BUILD COMPLETE!")
    print("=" * 60)
    print(f"\nExecutable: {dist_dir / 'ClaudeMonitor.exe'}")
    print(f"Archive:    {archive_name}.zip")

    return 0


if __name__ == "__main__":
    sys.exit(main())
