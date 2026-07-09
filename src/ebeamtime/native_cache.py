from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

ENV_NATIVE_CACHE_DIR = "SCGDS_EBEAMTIME_NATIVE_CACHE_DIR"


def cached_native_library_path(filename: str) -> Path:
    return native_cache_dir() / filename


def native_cache_dir() -> Path:
    configured = os.environ.get(ENV_NATIVE_CACHE_DIR)
    if configured:
        base = Path(configured).expanduser()
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches" / "scgds" / "ebeamtime" / "native"
    elif os.name == "nt":
        root = os.environ.get("LOCALAPPDATA")
        base = Path(root).expanduser() if root else Path.home() / "AppData" / "Local"
        base = base / "scgds" / "ebeamtime" / "native"
    else:
        root = os.environ.get("XDG_CACHE_HOME")
        base = Path(root).expanduser() if root else Path.home() / ".cache"
        base = base / "scgds" / "ebeamtime" / "native"
    return base / _platform_tag()


def _platform_tag() -> str:
    system = platform.system().lower() or "unknown"
    machine = platform.machine().lower() or "unknown"
    python_tag = f"py{sys.version_info.major}{sys.version_info.minor}"
    return f"{system}-{machine}-{python_tag}"
