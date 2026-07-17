# Cross-platform CI

The hosted matrix tests Python 3.10 and 3.14 on Ubuntu, macOS, and Windows with
the exact `uv` release required by `pyproject.toml`. During the RC phase it
installs the exact `gdsdiff` candidate from TestPyPI with `--no-deps`, after
installing ordinary dependencies from production PyPI. This avoids both a
private repository credential and dependency confusion.

After `gdsdiff==0.1.0` reaches production PyPI, replace the candidate workflow
variable with the stable version, change the runtime dependency to
`gdsdiff>=0.1.0,<0.2`, commit the production-index `uv.lock`, and make locked
sync the ordinary CI path.

Release jobs build artifacts once, preserve their hashes, publish and reinstall
the same files on TestPyPI, and require protected approval before production.
Only publishing jobs receive OIDC `id-token: write` permission.
