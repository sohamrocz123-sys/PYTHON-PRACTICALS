# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification file for File Organizer GUI."""

import os
from pathlib import Path
import customtkinter
import tkinterdnd2

block_cipher = None

# Locate package asset paths
ctk_dir = os.path.dirname(customtkinter.__file__)
tkdnd_dir = os.path.dirname(tkinterdnd2.__file__)

added_datas = [
    (ctk_dir, 'customtkinter'),
    (tkdnd_dir, 'tkinterdnd2'),
    ('config.json', '.'),
    ('assets', 'assets'),
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=added_datas,
    hiddenimports=[
        'tkinterdnd2',
        'customtkinter',
        'watchdog',
        'watchdog.observers',
        'watchdog.events',
        'PIL',
        'PIL.Image',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='FileOrganizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (GUI mode)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join('assets', 'icon.ico'),
)
