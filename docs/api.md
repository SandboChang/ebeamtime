# Public API

The package root exposes configuration and report models, `AreaAggregation`,
the estimation entry points, unit helpers, native capability discovery,
diagnostics, report validation, and `__version__`. Submodules remain importable,
but consumers should prefer these root exports.

`ebeamtime` consumes only `extract_gds_polygons` and `read_gds_metadata` from
the documented `gdsdiff` package-root API. Its `ExtractionResult.buffer` is
passed directly to area aggregation without rebuilding polygon arrays on CPU.
