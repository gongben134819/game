# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


PROJECT_ROOT = Path(SPECPATH).parent
APP_NAME = "".join(chr(code) for code in (0x91D1, 0x5E01, 0x51B2, 0x523A))
ICON_FILE = PROJECT_ROOT / "build" / "windows" / "coinrush.ico"


def collect_files(source_dir, target_dir, suffixes=None):
    files = []
    root = PROJECT_ROOT / source_dir
    if not root.exists():
        return files

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if suffixes and path.suffix.lower() not in suffixes:
            continue
        if path.name in {"save_data.json", "settings_data.json"}:
            continue
        files.append((str(path), str(Path(target_dir) / path.relative_to(root).parent)))
    return files


datas = []
datas += collect_files("assets", "assets")
datas += collect_files("data", "data", {".json"})


a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
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
    icon=str(ICON_FILE) if ICON_FILE.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
