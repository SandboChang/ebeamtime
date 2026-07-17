# Qualification

Qualified on 2026-07-17 under Windows 11 WSL, Linux x86_64, CPython 3.14:

- focused standalone suite: 37 passed, 1 expected CUDA capability skip;
- all 17 legacy `scgds.ebeamtime` root exports and signatures preserved after
  namespace and development-version normalization; 21 root exports total;
- CLI help byte-for-byte equal to the extraction baseline;
- normalized representative analytical report exactly equal after excluding
  paths, timings, tool version, and the intentionally added schema version;
- `ExtractionResult.buffer` identity proven unchanged into area aggregation;
- CPU seven-run median: 0.022923 s versus 0.024427 s baseline (6.2% faster);
- peak RSS across 21 isolated representative estimation processes: 31,964 KiB
  versus 32,032 KiB embedded (-0.212%); installed report versions remain
  metadata-derived without eagerly importing Python's full distribution
  metadata stack;
- sdist and wheel passed `twine check`; wheel contains the report schema,
  typing marker, CUDA source, and Metal source, with no tests or `scgds` tree;
- wheel metadata contains only abstract dependencies and no local paths;
- clean external virtual environment installed locally built `gdsdiff` and
  `ebeamtime` wheels, passed `pip check`, root imports, CLI help, diagnostics,
  and the unit formula without either source checkout on `sys.path`.

The local NVIDIA RTX 5090 is visible, but `nvcc` is not installed, so the real
CUDA correctness/performance gate remains mandatory before a public release.
Real Apple Metal validation also remains outstanding and is nonblocking for the
private extraction milestone.
