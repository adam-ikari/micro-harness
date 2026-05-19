# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for building Spark binary."""

import sys
from pathlib import Path

block_cipher = None

# Get the source directory
src_dir = Path('src/spark')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include spark package
        ('src/spark', 'spark'),
    ],
    hiddenimports=[
        'spark',
        'spark.cli',
        'spark.agent',
        'spark.llm',
        'spark.config',
        'spark.security',
        'spark.history',
        'spark.skills',
        'spark.memory',
        'spark.feedback',
        'spark.builtin',
        'spark.builtin.shell',
        'spark.fs',
        'spark.fs.operations',
        'spark.mcp',
        'spark.errors',
        'textual',
        'textual.app',
        'prompt_toolkit',
        'click',
        'yaml',
        'ollama',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'cv2',
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
    name='spark',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
