from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path

import gdstk
import jsonschema

import ebeamtime
import gdsdiff


def main() -> int:
    for package in (ebeamtime, gdsdiff):
        package_path = Path(package.__file__).resolve()
        if "site-packages" not in package_path.parts:
            raise RuntimeError(f"{package.__name__} did not resolve from site-packages: {package_path}")
    if ebeamtime.__version__ != version("ebeamtime"):
        raise RuntimeError("runtime and distribution versions differ")
    schema = json.loads(files("ebeamtime").joinpath("schemas/ebeamtime-report-v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)

    with tempfile.TemporaryDirectory(prefix="ebeamtime-installed-smoke-") as directory:
        root = Path(directory)
        gds_path = _write_gds(root / "overlap.gds")
        exposure = ebeamtime.EbeamLayerExposure("metal", ebeamtime.LayerSpec(1, 0), 100, 1)
        result = ebeamtime.estimate_gds_write_time(
            ebeamtime.EstimateConfig(gds_path, (exposure,), backend="cpu")
        )
        layer = result.report.layers[0]
        if layer.polygon_count != 2 or abs(layer.area_um2 - 200.0) > 1e-9 or abs(layer.beam_on_s - 0.2) > 1e-12:
            raise RuntimeError("known-area ebeamtime smoke result is incorrect")
        jsonschema.validate(result.report.to_json_dict(), schema)
        completed = subprocess.run(
            [sys.executable, "-m", "ebeamtime", "--version"], check=False, text=True, capture_output=True
        )
        if completed.returncode or completed.stdout.strip() != f"ebeamtime {version('ebeamtime')}":
            raise RuntimeError(completed.stderr or completed.stdout)
    return 0


def _write_gds(path: Path) -> Path:
    library = gdstk.Library(unit=1e-6, precision=1e-9)
    top = library.new_cell("TOP")
    top.add(
        gdstk.rectangle((0, 0), (10, 10), layer=1, datatype=0),
        gdstk.rectangle((0, 0), (10, 10), layer=1, datatype=0),
    )
    library.write_gds(path)
    return path


if __name__ == "__main__":
    raise SystemExit(main())
