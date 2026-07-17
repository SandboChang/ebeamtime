# Contributing

Create the platform-specific repository virtual environment described in
`AGENTS.md`, then synchronize and test the committed production lock. On WSL:

```bash
UV_PROJECT_ENVIRONMENT=.venv_wsl UV_LINK_MODE=copy uv sync --locked --no-dev
UV_PROJECT_ENVIRONMENT=.venv_wsl_test UV_LINK_MODE=copy uv sync --locked --extra test
TMPDIR=/tmp .venv_wsl_test/bin/python -m pytest
```

Use the exact `uv` version required by `pyproject.toml`. The committed lock must
resolve from production indexes and must not contain sibling path sources. For
coordinated unpublished changes, an editable sibling may be installed into the
environment explicitly for that local test, but do not record it in project
metadata or the lock. Ordinary `pip` installation remains a release
compatibility gate. Keep WSL test dependencies in `.venv_wsl_test`;
`.venv_wsl` is the clean runtime environment.

Changes to units, extraction, stage assignment, or backends need focused
contract tests and CPU parity evidence. Do not make GPU toolchains mandatory.
