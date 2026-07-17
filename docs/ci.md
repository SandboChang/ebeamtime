# Cross-platform CI

The hosted matrix tests Python 3.10 and 3.14 on Ubuntu, macOS, and Windows with
the exact `uv` release required by `pyproject.toml`. Ordinary CI checks the
committed production-index `uv.lock`, performs a locked sync, and therefore
installs `gdsdiff` and every other dependency reproducibly from production
PyPI. No sibling checkout or private repository credential is used.

Release jobs build artifacts once, preserve their hashes, publish and reinstall
the same files on TestPyPI, and require protected approval before production.
The TestPyPI verification environment installs `gdsdiff` and ordinary
dependencies from production PyPI, then installs only the exact `ebeamtime`
artifact from TestPyPI with `--no-deps`; this avoids dependency confusion.
Only publishing jobs receive OIDC `id-token: write` permission. GitHub Release
creation names `GITHUB_REPOSITORY` explicitly and retains tag verification, so
it does not depend on an implicit checkout.
