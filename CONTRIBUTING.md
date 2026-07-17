# Contributing

Create the platform-specific repository virtual environment described in
`AGENTS.md`, install the sibling `gdsdiff` checkout and `.[test]`, then run:

```bash
TMPDIR=/tmp TEMP=/tmp TMP=/tmp python -m pytest
```

Changes to units, extraction, stage assignment, or backends need focused
contract tests and CPU parity evidence. Do not make GPU toolchains mandatory.
