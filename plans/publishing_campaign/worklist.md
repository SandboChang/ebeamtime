# Publishing Campaign Worklist

The authoritative sequence is shared with the sibling `gdsdiff` campaign.
`ebeamtime` hardening and publication starts after the `gdsdiff` release gate is
green, and production publication requires `gdsdiff==0.1.0` on PyPI.

- Reproducible `uv` environment: complete with a production-index lock
- Backend contract and CUDA preparation hardening: complete
- Schema and installed-package qualification: complete
- Hosted CI and Trusted Publishing workflows: complete; publishers and
  protected environments configured
- TestPyPI candidate: complete
- Production PyPI `0.1.0`: complete

On 2026-07-18 public tag `v0.1.0rc1` at commit `5ad2a87` passed the full
Ubuntu/macOS/Windows Python 3.10/3.14 matrix in Actions run `29594180829`.
Trusted Publishing run `29594180909` built once, uploaded signed artifacts to
TestPyPI, and passed a clean indexed install with the independently published
`gdsdiff==0.1.0rc1`. The indexed wheel SHA-256 is
`189f686bcbf646459c264135de31f2c9f50f360c163af58ad2dea2c13e3ca565`;
the sdist SHA-256 is
`99d9276b5f314b805b8dbbefb5592e979aeb82b32702e3c247be472b87d7f763`.
Both files were byte-identical to the immutable GitHub workflow artifact.

Stable preparation on 2026-07-18 resolved `gdsdiff==0.1.0` exclusively from
production PyPI into the committed `uv.lock`. The synchronized WSL environment
passed 47 tests with only the expected Apple Metal hardware skip. A fresh
site-packages-only wheel installation pulled production `gdsdiff==0.1.0`,
passed dependency and installed-package smoke checks, performed verified cold
and warm CUDA preparation, and matched CPU/CUDA area and beam-time results on
the RTX 5090. Hosted main CI run `29596395412` then passed the complete
Ubuntu/macOS/Windows Python 3.10/3.14 matrix and package smoke gate on commit
`b576653`, which was annotated as `v0.1.0`.
The stable TestPyPI upload succeeded in run `29596491385`, but uv retained its
first negative Simple API response during the bounded visibility loop. The
workflow now uses `--refresh-package ebeamtime`; a fresh rerun verified the
indexed artifact successfully, and the production job is waiting at its
protected approval gate.

WSL environment isolation was requalified on 2026-07-18 after separating the
clean runtime environment from test tooling. `.venv_wsl` was recreated from
the production-index lock with `--no-dev` and contains no pytest installation;
`.venv_wsl_test` was recreated with the test extra and passes the locked
dependency check. The complete suite passed from `.venv_wsl_test` with 47
passed and the single expected Apple Metal hardware skip; CUDA exercised the
prepared RTX 5090 / CUDA Toolkit 13.3 backend.

Protected release run `29596491385` completed after production approval. PyPI
published wheel SHA-256
`ae54b3afeb6146e80b8efd5818d0e0a633a198fb660d71df5129dbc3cd0c0064`
and sdist SHA-256
`5c09be0be6f87575ccb5d4c32d9d70610f9b7c4c9477942418facc7c3411058e`.
The production files and public GitHub Release `v0.1.0` assets are byte-for-byte
identical to the immutable Actions artifact, including `SHA256SUMS`; both
manifests pass. The first local comparison glob addressed the artifact parent
instead of its downloaded `packages/` directory, and the first manifest check
ran one directory too high. Repeating both commands from the artifact's actual
layout completed successfully without changing any files.

A fresh production-only scgds consumer environment installed
`ebeamtime==0.1.0` and `gdsdiff==0.1.0` from PyPI with no source checkout on
`sys.path`, passed dependency and facade/CLI smoke checks, completed cold
isolated CUDA preparation, and produced exact CPU/CUDA parity for the known
`2 polygons / 200 um^2 / 0.2 s` calculation.
