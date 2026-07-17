# Contributing

Create the platform-specific repository virtual environment described in
`AGENTS.md`, install the sibling `gdsdiff` checkout and `.[test]`, then run:

```bash
UV_LINK_MODE=copy uv pip install --python .venv_wsl/bin/python -e ../gdsdiff -e ".[dev]"
TMPDIR=/tmp .venv_wsl/bin/python -m pytest
```

Use the exact `uv` version required by `pyproject.toml`. A committed production
lock follows the stable `gdsdiff` PyPI release; do not commit sibling path
sources. Ordinary `pip` installation remains a release compatibility gate.

Changes to units, extraction, stage assignment, or backends need focused
contract tests and CPU parity evidence. Do not make GPU toolchains mandatory.
