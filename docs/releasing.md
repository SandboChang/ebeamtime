# Releasing

`ebeamtime` uses GitHub OIDC Trusted Publishing and never stores a PyPI token.
Its candidate release follows a successful `gdsdiff` candidate; its stable
release follows `gdsdiff==0.1.0` on production PyPI.

## One-time setup

1. Confirm `ebeamtime` remains unclaimed on PyPI and TestPyPI immediately before
   setup. TestPyPI has a separate account database from PyPI.
2. Enable two-factor authentication on both accounts and retain recovery codes.
3. Create GitHub environments `testpypi` and `pypi`, protecting `pypi` with a
   required manual approval that the repository owner can perform.
4. Configure pending Trusted Publishers with:

   - Owner: `SandboChang`
   - Repository: `ebeamtime`
   - Workflow: `release.yml`
   - Environment: `testpypi` on TestPyPI and `pypi` on PyPI

## Dependency and promotion rules

- Candidate metadata uses `gdsdiff>=0.1.0rc1,<0.2`; candidate CI installs that
  exact dependency from TestPyPI with `--no-deps` after installing ordinary
  dependencies from production PyPI.
- Before stable release, change the dependency to `gdsdiff>=0.1.0,<0.2`, create
  and commit the production-index `uv.lock`, and update candidate workflow
  variables to the stable dependency.
- Candidate tags publish only to TestPyPI. Stable tags promote the exact tested
  files through the protected `pypi` environment and then create a GitHub
  release. Never reuse or replace a published version.
