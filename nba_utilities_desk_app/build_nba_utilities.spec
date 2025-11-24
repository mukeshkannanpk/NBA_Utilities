# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for NBA Utilities
This builds the main launcher and all sub-applications
"""

block_cipher = None

# ============================================
# MAIN APPLICATION (home.py)
# ============================================
a_main = Analysis(
    ['home.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('nba-utilities-home.html', '.'),
        ('nba-drive-downloader.html', '.'),
        ('nba-pdf-merger.html', '.'),
        ('icon.ico', '.'),
        ('config.py', '.'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebChannel',
        'appdirs',
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

pyz_main = PYZ(a_main.pure, a_main.zipped_data, cipher=block_cipher)

exe_main = EXE(
    pyz_main,
    a_main.scripts,
    [],
    exclude_binaries=True,
    name='NBA_Utilities',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)

# ============================================
# GLINK EXTRACTOR (Glink.py)
# ============================================
a_glink = Analysis(
    ['Glink.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('nba-drive-downloader.html', '.'),
        ('icon.ico', '.'),
        ('config.py', '.'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebChannel',
        'google.auth',
        'google.oauth2',
        'googleapiclient',
        'pandas',
        'appdirs',
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

pyz_glink = PYZ(a_glink.pure, a_glink.zipped_data, cipher=block_cipher)

exe_glink = EXE(
    pyz_glink,
    a_glink.scripts,
    [],
    exclude_binaries=True,
    name='NBA_GLink_Extractor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)

# ============================================
# PDF MERGER (merger.py)
# ============================================
a_merger = Analysis(
    ['merger.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('nba-pdf-merger.html', '.'),
        ('icon.ico', '.'),
        ('config.py', '.'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebChannel',
        'pikepdf',
        'appdirs',
        'datetime',
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

pyz_merger = PYZ(a_merger.pure, a_merger.zipped_data, cipher=block_cipher)

exe_merger = EXE(
    pyz_merger,
    a_merger.scripts,
    [],
    exclude_binaries=True,
    name='NBA_PDF_Merger',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)

# ============================================
# COLLECT ALL FILES
# ============================================
coll = COLLECT(
    exe_main,
    a_main.binaries,
    a_main.zipfiles,
    a_main.datas,
    
    exe_glink,
    a_glink.binaries,
    a_glink.zipfiles,
    a_glink.datas,
    
    exe_merger,
    a_merger.binaries,
    a_merger.zipfiles,
    a_merger.datas,
    
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NBA_Utilities',
)