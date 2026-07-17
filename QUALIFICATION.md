# Qualification

Qualified on 2026-07-17 under Windows 11 WSL, Linux x86_64, CPython 3.14:

- RC1 CUDA-enabled standalone suite: 47 passed with one expected Apple Metal
  hardware skip and no failures;
- CPU-only behavior remains covered without requiring CUDA compilation;
- all 17 legacy `scgds.ebeamtime` root exports and signatures preserved after
  namespace and development-version normalization; 21 root exports total;
- CLI help byte-for-byte equal to the extraction baseline;
- normalized representative analytical report exactly equal after excluding
  paths, timings, tool version, and the intentionally added schema version;
- `ExtractionResult.buffer` identity proven unchanged into area aggregation;
- CPU seven-run median: 0.022923 s versus 0.024427 s baseline (6.2% faster);
- CUDA correctness: CPU/CUDA area and beam-time parity passed on an NVIDIA
  GeForce RTX 5090 (compute capability 12.0) through WSL2 with Windows display
  driver 596.36, CUDA Toolkit 13.3.1, and nvcc 13.3.73. The default
  `-arch=native` build emitted native SASS without manual nvcc flags;
- CUDA warm-path performance on an identical 500-polygon estimate after one
  warm-up: 0.009390 s standalone versus 0.009338 s embedded across seven-run
  medians (+0.56%, within the 5% parity gate);
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
- clean wheel and sdist installations passed with both `uv` and ordinary `pip`;
  installed artifacts passed explicit cold/warm CUDA preparation, CPU/CUDA area
  parity, packaged-schema validation, and the overlapping-rectangle `0.2 s`
  reference calculation.

Real Apple Metal validation remains outstanding and is nonblocking for the
Linux/WSL CUDA-qualified `0.1.0` release line.

Stable-promotion evidence on 2026-07-18:

- the production-index `uv.lock` resolves `gdsdiff==0.1.0` from
  `https://pypi.org/simple` with no sibling or filesystem source;
- the locked local suite passed 47 tests with only the expected Apple Metal
  hardware skip;
- the stable wheel and sdist passed strict `twine` validation, and the wheel
  contains its schema, typing marker, CUDA source, and Metal source with the
  declared `gdsdiff>=0.1.0,<0.2` dependency;
- a fresh environment installed the wheel outside both source trees, resolved
  `gdsdiff==0.1.0` from production PyPI, passed the installed smoke and
  dependency checks, and proved both imports came from `site-packages`;
- the fresh installed wheel passed verified cold and warm CUDA preparation and
  exact CPU/CUDA area and beam-time parity on the same RTX 5090/CUDA 13.3
  platform.
