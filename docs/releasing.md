# Releasing

`ebeamtime` uses GitHub OIDC Trusted Publishing and never stores a PyPI token.
Its candidate release follows a successful `gdsdiff` candidate; its stable
release follows `gdsdiff==0.1.0` on production PyPI.

## One-time setup

1. For a new package name, confirm ownership availability on PyPI and TestPyPI
   immediately before setup. TestPyPI has a separate account database from
   PyPI. For an existing project, manage the publisher from that project's
   publishing settings.
2. Enable two-factor authentication on both accounts and retain recovery codes.
3. Create GitHub environments `testpypi` and `pypi`, protecting `pypi` with a
   required manual approval that the repository owner can perform.
4. Configure pending Trusted Publishers for a new project, or ordinary Trusted
   Publishers for an existing project, with:

   - Owner: `SandboChang`
   - Repository: `ebeamtime`
   - Workflow: `release.yml`
   - Environment: `testpypi` on TestPyPI and `pypi` on PyPI

## Dependency and promotion rules

- Stable metadata uses `gdsdiff>=0.1.0,<0.2`, and the committed lock resolves
  against production PyPI without sibling path sources.
- Future release candidates should normally depend on the latest compatible
  production `gdsdiff`. Use a `gdsdiff` pre-release only when intentionally
  qualifying a coordinated pre-release, and never expose TestPyPI as an extra
  dependency index.
- Candidate tags publish only to TestPyPI. Stable tags promote the exact tested
  files through the protected `pypi` environment and then create a GitHub
  release with explicit repository context and `--verify-tag`. Never reuse or
  replace a published version.
