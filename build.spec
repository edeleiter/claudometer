# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Claude Usage Monitor."""

from pathlib import Path

block_cipher = None

# Get the base directory
BASE_DIR = Path(SPECPATH)

a = Analysis(
    [str(BASE_DIR / 'src' / 'main.py')],
    pathex=[str(BASE_DIR)],
    binaries=[],
    datas=[
        # Include example config
        (str(BASE_DIR / 'config.example.json'), '.'),
    ],
    hiddenimports=[
        # pystray dependencies
        'pystray._win32',
        'PIL._tkinter_finder',
        # winotify
        'winotify',
        # Windows-specific
        'win32api',
        'win32con',
        'win32gui',
        'win32gui_struct',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'notebook',
        'IPython',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ClaudeMonitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one
    uac_admin=False,
)
