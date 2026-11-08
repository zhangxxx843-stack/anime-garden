# PyInstaller entry point for the Windows x64 desktop artifact.
# The workflow produces dist/Suishouji.exe and packages it as a zip.
# entry point: windows_app/main.py
from pathlib import Path

project_root = Path(SPECPATH).parent

a = Analysis(
    [str(project_root / "windows_app" / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[(str(project_root / "windows_app" / "style.qss"), "windows_app")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Suishouji',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
