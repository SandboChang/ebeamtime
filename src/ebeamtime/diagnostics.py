from __future__ import annotations

import json
import platform
import sys
from typing import Any, Sequence

from .native import discover_native_capabilities
from .native_cache import ENV_NATIVE_CACHE_DIR, LEGACY_ENV_NATIVE_CACHE_DIR, native_cache_dir


def backend_diagnostics() -> dict[str, Any]:
    """Return CPU-safe runtime and optional-backend diagnostics."""

    return {
        "python": {"implementation": platform.python_implementation(), "version": platform.python_version()},
        "platform": {"system": platform.system(), "machine": platform.machine()},
        "native_cache": {
            "path": str(native_cache_dir()),
            "environment": ENV_NATIVE_CACHE_DIR,
            "legacy_environment": LEGACY_ENV_NATIVE_CACHE_DIR,
        },
        "capabilities": discover_native_capabilities().to_json(),
    }


def main(argv: Sequence[str] | None = None) -> int:
    if argv:
        print("ebeamtime-diagnostics does not accept arguments", file=sys.stderr)
        return 2
    print(json.dumps(backend_diagnostics(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
