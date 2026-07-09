from __future__ import annotations

from enum import Enum


class Backend(str, Enum):
    AUTO = "auto"
    CPU = "cpu"
    CUDA = "cuda"
    METAL = "metal"

    @classmethod
    def coerce(cls, value: "Backend | str") -> "Backend":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).lower())
        except ValueError as exc:
            choices = ", ".join(item.value for item in cls)
            raise ValueError(f"backend must be one of {choices}") from exc
