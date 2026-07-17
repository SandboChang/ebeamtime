from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ._version import __version__
from .api import estimate_gds_write_time
from .config import EstimateConfig, LayerSpec, exposures_from_cli, load_project_estimate_config
from .report import days_from_seconds, hours_from_seconds
from .semantics import Backend


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ebeamtime",
        description="Estimate analytical ebeam write time from GDS area, dose, and beam current.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("gds", type=Path)
    parser.add_argument("--project-config", type=Path, help="Trusted Python project config defining ebeamtime_layer_exposures; loading executes the file.")
    parser.add_argument("--top")
    parser.add_argument("--exposure", action="append", default=[], metavar="L:D:DOSE_UC_CM2:CURRENT_NA")
    parser.add_argument("--writefield-indicator-layer", help="Layer spec L:D, or config variable name when --project-config is used.")
    parser.add_argument("--max-write-field-um", type=_parse_size, metavar="WIDTH,HEIGHT")
    parser.add_argument("--stage-speed-mm-s", type=float)
    parser.add_argument("--stage-settle-s", type=float)
    parser.add_argument("--ignore-stage", action="store_true", help="Ignore project write-field/stage settings and report beam-on time only.")
    parser.add_argument("--backend", choices=[item.value for item in Backend], default=Backend.AUTO.value)
    parser.add_argument("--require-gpu", action="store_true")
    parser.add_argument("--gpu-min-polygons", type=int, default=4096)
    parser.add_argument("--json-report", type=Path)
    parser.add_argument("--quiet", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        config = _config_from_args(args)
        result = estimate_gds_write_time(config, json_report_path=args.json_report)
    except Exception as exc:
        print(f"ebeamtime: {exc}", file=sys.stderr)
        return 2
    if not args.quiet:
        _print_report(result.report)
    return 0


def _config_from_args(args) -> EstimateConfig:
    backend = Backend.coerce(args.backend)
    if args.project_config is not None:
        indicator = args.writefield_indicator_layer
        config = load_project_estimate_config(
            args.project_config,
            gds_path=args.gds,
            top=args.top,
            backend=backend,
            require_gpu=args.require_gpu,
            writefield_indicator_layer=indicator,
            max_write_field_um=args.max_write_field_um,
            stage_speed_mm_s=args.stage_speed_mm_s,
            stage_settle_s=args.stage_settle_s,
            ignore_stage=args.ignore_stage,
            gpu_min_polygons=args.gpu_min_polygons,
        )
        return config
    if not args.exposure:
        raise ValueError("provide --project-config or at least one --exposure")
    indicator_layer = LayerSpec.parse(args.writefield_indicator_layer) if args.writefield_indicator_layer else None
    return EstimateConfig(
        gds_path=args.gds,
        top=args.top,
        exposures=exposures_from_cli(args.exposure),
        writefield_indicator_layer=indicator_layer,
        max_write_field_um=args.max_write_field_um,
        stage_speed_mm_s=args.stage_speed_mm_s,
        stage_settle_s=0.0 if args.stage_settle_s is None else args.stage_settle_s,
        ignore_stage=args.ignore_stage,
        backend=backend,
        require_gpu=args.require_gpu,
        gpu_min_polygons=args.gpu_min_polygons,
    )


def _print_report(report) -> None:
    total_min = report.total_s / 60.0
    total_hr = hours_from_seconds(report.total_s)
    total_days = days_from_seconds(report.total_s)
    print(
        "status=estimated backend={backend} top={top} total_s={total_s:.6g} total_min={total_min:.6g} total_hr={total_hr:.6g} total_days={total_days:.6g}".format(
            backend=report.backend["name"],
            top=report.top_name,
            total_s=report.total_s,
            total_min=total_min,
            total_hr=total_hr,
            total_days=total_days,
        )
    )
    print("layer                 L:D       polygons       area_um2      dose      current_nA     beam_on_s    beam_on_hr  beam_on_days")
    for layer in report.layers:
        print(
            "{name:<20} {layer:>7} {count:>10} {area:>14.6g} {dose:>9.6g} {current:>13.6g} {time_s:>13.6g} {time_hr:>11.6g} {time_days:>13.6g}".format(
                name=layer.config_name,
                layer=f"{layer.layer.layer}:{layer.layer.datatype}",
                count=layer.polygon_count,
                area=layer.area_um2,
                dose=layer.dose_uC_cm2,
                current=layer.beam_current_nA,
                time_s=layer.beam_on_s,
                time_hr=hours_from_seconds(layer.beam_on_s),
                time_days=days_from_seconds(layer.beam_on_s),
            )
        )
    if report.stage.enabled:
        print(
            "stage fields={fields} distance_um={distance:.6g} movement_s={move_s:.6g} movement_hr={move_hr:.6g} movement_days={move_days:.6g} settle_s={settle_s:.6g} settle_hr={settle_hr:.6g} settle_days={settle_days:.6g} total_s={total_s:.6g} total_hr={total_hr:.6g} total_days={total_days:.6g}".format(
                fields=report.stage.field_count,
                distance=report.stage.movement_distance_um,
                move_s=report.stage.movement_s,
                move_hr=hours_from_seconds(report.stage.movement_s),
                move_days=days_from_seconds(report.stage.movement_s),
                settle_s=report.stage.settle_s,
                settle_hr=hours_from_seconds(report.stage.settle_s),
                settle_days=days_from_seconds(report.stage.settle_s),
                total_s=report.stage.total_s,
                total_hr=hours_from_seconds(report.stage.total_s),
                total_days=days_from_seconds(report.stage.total_s),
            )
        )


def _parse_size(value: str) -> tuple[float, float]:
    normalized = value.lower().replace("x", ",")
    parts = [part.strip() for part in normalized.split(",") if part.strip()]
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("size must have form WIDTH,HEIGHT")
    width = float(parts[0])
    height = float(parts[1])
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("size values must be positive")
    return width, height
