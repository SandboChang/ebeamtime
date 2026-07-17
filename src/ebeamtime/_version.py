from __future__ import annotations

import sys
from pathlib import Path


def _installed_distribution_version(distribution_name: str, fallback: str) -> str:
    """Read an unpacked wheel's version without importing metadata machinery."""

    normalized_name = distribution_name.lower().replace("-", "_").replace(".", "_")
    for entry in sys.path:
        root = Path(entry or ".")
        if not root.is_dir():
            continue
        try:
            candidates = root.glob(f"{normalized_name}-*.dist-info/METADATA")
            for metadata_path in candidates:
                metadata_name = None
                metadata_version = None
                for line in metadata_path.read_text(encoding="utf-8").splitlines():
                    if line.startswith("Name: "):
                        metadata_name = line[6:].strip().lower().replace("-", "_").replace(".", "_")
                    elif line.startswith("Version: "):
                        metadata_version = line[9:].strip()
                    if metadata_name is not None and metadata_version is not None:
                        break
                if metadata_name == normalized_name and metadata_version:
                    return metadata_version
        except (OSError, UnicodeError):
            continue
    return fallback


__version__ = _installed_distribution_version("ebeamtime", "0.1.0.dev0")
