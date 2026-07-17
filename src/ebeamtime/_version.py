from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


try:
    __version__ = version("ebeamtime")
except PackageNotFoundError:  # Source tree without an installed distribution.
    __version__ = "0.1.0.dev0"
